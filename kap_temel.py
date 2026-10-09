"""v2.0.7.381 - KAP (BIRINCIL kaynak) ile PD/DD ve F/K hesabi.

NEDEN (Bahri, 9 Ekim 2026, THYAO "Temel Skor 0/25" bulgusu): PROJE_NOTLARI'ndaki kaynak tablosuna gore BIST temel
analizinde 1. kaynak KAP, 2. kaynak yfinance'tir. Ama Optima Temel Skoru (PD/DD, F/K, temettu) gecelik
worker'da yalniz yfinance'ten besleniyordu; Yahoo'nun para birimi karmasasi (THYAO: bilanco USD, fiyat TL ->
PD/DD 18,1; F/K yok) buyuk bir sirketin Temel Skorunu 0 yapiyordu. Bu modul rakamlari KAP'tan hesaplar,
yfinance yalniz yedek (ve temettu) olarak kalir.

Formuller (hicbiri tahmin degil; her sonuc kaynagi/donemiyle etiketli):
  Piyasa degeri = guncel fiyat x KAP 'Toplam Pay Adedi'   (KAP sirket-bilgileri/genel; BIST'te 1 lot = 1 TL nominal,
                   bu yuzden pay adedi 1 TL'lik pay sayisidir). Birden fazla pay grubu (KRDMA/B/D gibi) varsa her
                   grubun adedi kendi borsa fiyatiyla carpilip toplanir.
  PD/DD         = Piyasa degeri / KAP 'Ana Ortakliga Ait Ozkaynaklar' (son donem; bankalarda 'Ozkaynaklar').
  F/K           = Piyasa degeri / KAP ana ortaklik net kari.
                   * son KAP donemi yillik (12. ay) ise bu TAM 12 aylik (iz. 12A) F/K'dir.
                   * son donem ara donem (3/6/9. ay) ise KAP sayfasinda onceki yilin ayni donemi YOKTUR; iz. 12A
                     hesaplanamaz. Bu durumda SON TAM YIL (YYYY-1/12) net kari kullanilir ve F/K 'YILLIK' diye
                     etiketlenir. Ara donem zarar ise F/K bos birakilir (zarar). Yillandirma YAPILMAZ (tahmin olur).
  Temettu verimi KAP'ta bulunmaz; yfinance'ten (TL'lik temettu / TL fiyat, para birimi sorunu yok) alinir.
Para birimi TL degilse (USD/EUR sunan sirketler) piyasa degeri o para birimine guncel kurla cevrilir (PD/DD ve
F/K birimsiz oranlardir); kur bulunamazsa oran hesaplanmaz."""
import re
import time
from typing import Optional

import requests

from kap_client import KAP_HEADERS, slug_getir, _kap_tablolar_metin

FIN_URL = "https://kap.org.tr/tr/sirket-finansal-bilgileri/{slug}"
GENEL_URL = "https://kap.org.tr/tr/sirket-bilgileri/genel/{slug}"

_DONEM_RE = re.compile(r"\d{4}/\d{1,2}")
_BIRIM_RE = re.compile(r"(\d{1,3}(?:\.?\d{3})*)?([A-Z]{2,4})")

# Etiket oncelik sirasi (ilk bulunan kullanilir). Bankalar/sigorta farkli etiket kullanir.
OZKAYNAK_ETIKETLERI = ("Ana Ortaklığa Ait Özkaynaklar", "Özkaynaklar", "Toplam Özkaynaklar")
NET_KAR_ETIKETLERI = (
    "Dönem Kârının (Zararının) Dağılımı, Ana Ortaklık Payları",
    "Dönem Kârının (Zararının) Dağılımı, Grubun Kârı (Zararı)",
    "Net Dönem Kârı (Zararı)",
)


def tr_sayi(v) -> Optional[float]:
    """'119.470.352,22' -> 119470352.22 ; '745.430' -> 745430.0 ; '-' / '' -> None. Yalniz METIN alir."""
    if v is None:
        return None
    s = str(v).strip().replace(" ", "")
    if s in ("", "-", "—", "nan", "NaN", "None"):
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def birim_coz(v) -> Optional[tuple]:
    """'1000000TL' -> (1_000_000.0, 'TL') ; 'USD' -> (1.0, 'USD') ; taninmazsa None."""
    s = str(v or "").strip().upper().replace(" ", "")
    if not s or s == "NAN":
        return None
    m = _BIRIM_RE.fullmatch(s)
    if not m:
        return None
    kat = float(m.group(1).replace(".", "")) if m.group(1) else 1.0
    para = "TL" if m.group(2) in ("TL", "TRY") else m.group(2)
    return kat, para


def _norm(s) -> str:
    return " ".join(str(s).split()).casefold()


def kap_seriler(tablolar: list) -> dict:
    """KAP finansal tablolarindan {etiket: {donem: (deger, para)}} cikarir. Her sutunun kendi 'Sunum Para
    Birimi' carpani uygulanir (GARAN: 2023-2025 sutunlari 1000TL, 2026/06 sutunu 1000000TL olabiliyor)."""
    seri = {}
    baslik, birimler = None, {}
    for df in tablolar:
        if df.shape[1] < 2:
            continue
        kol = [str(c).strip() for c in df.columns]
        if any(_DONEM_RE.fullmatch(k) for k in kol):
            baslik, birimler = kol, {}
        ilk = df.iloc[:, 0].astype(str).str.strip()
        # birim satiri (ayni tabloda)
        for _, satir in df[ilk == "Sunum Para Birimi"].iterrows():
            for j in range(1, len(satir)):
                b = birim_coz(satir.iloc[j])
                if b:
                    birimler[j] = b
        if baslik is None or len(baslik) != df.shape[1]:
            continue
        for _, satir in df.iterrows():
            etiket = str(satir.iloc[0]).strip()
            if not etiket or etiket == "Sunum Para Birimi":
                continue
            for j in range(1, len(satir)):
                donem = baslik[j]
                if not _DONEM_RE.fullmatch(donem):
                    continue
                x = tr_sayi(satir.iloc[j])
                b = birimler.get(j)
                if x is None or b is None:
                    continue
                seri.setdefault(_norm(etiket), {}).setdefault(donem, (x * b[0], b[1]))
    return seri


def _donem_anahtar(d: str):
    y, m = d.split("/")
    return int(y), int(m)


def _en_guncel(seri: dict, etiketler) -> Optional[tuple]:
    """(donem, deger, para, etiket) - ilk bulunan etiketin EN GUNCEL donemi."""
    for e in etiketler:
        s = seri.get(_norm(e))
        if s:
            d = max(s, key=_donem_anahtar)
            return d, s[d][0], s[d][1], e
    return None


def pay_adetleri(html: str) -> dict:
    """KAP 'genel' sayfasindaki 'Fiili Dolasimdaki Paylar' tablosundan {borsa_kodu: toplam_pay_adedi}."""
    sonuc = {}
    for df in _kap_tablolar_metin(html):
        kol = [str(c).strip() for c in df.columns]
        satirlar = df.values.tolist()
        if "Borsa Kodu" in kol:
            basliklar = kol
        elif satirlar and str(satirlar[0][0]).strip() == "Borsa Kodu":
            basliklar, satirlar = [str(x).strip() for x in satirlar[0]], satirlar[1:]
        else:
            continue
        try:
            ik = basliklar.index("Toplam Pay Adedi")
        except ValueError:
            continue
        for s in satirlar:
            kod = str(s[0]).strip().upper()
            adet = tr_sayi(s[ik]) if ik < len(s) else None
            if re.fullmatch(r"[A-Z0-9]{3,6}", kod) and adet and adet > 0:
                sonuc[kod] = adet
        if sonuc:
            break
    return sonuc


def _cek(url: str, deneme: int = 3, bekle: float = 2.0) -> Optional[str]:
    for i in range(deneme):
        try:
            r = requests.get(url, headers=KAP_HEADERS, timeout=30)
            if r.status_code == 200 and r.text and len(r.text) > 500:
                return r.text
        except Exception:
            pass
        time.sleep(bekle * (i + 1))
    return None


def hesapla(ticker: str, fiyat: float, fiyatlar: dict = None, kurlar: dict = None,
            fin_html: str = None, genel_html: str = None) -> dict:
    """Tek hisse icin KAP'tan PD/DD ve F/K. Her zaman bir sozluk doner:
      pb, pe (None olabilir), pe_tur ('TTM'|'YILLIK'|None), pe_durum ('hesaplandi'|'zarar'|'yok'),
      donem (ozkaynak donemi), kar_donem, piyasa_degeri, ozkaynak, net_kar, para, pay_adedi, pay_kaynak, notlar[]"""
    out = {"pb": None, "pe": None, "pe_tur": None, "pe_durum": "yok", "donem": None, "kar_donem": None,
           "piyasa_degeri": None, "ozkaynak": None, "net_kar": None, "para": None,
           "pay_adedi": None, "pay_kaynak": None, "notlar": []}
    notlar = out["notlar"]
    fiyatlar = fiyatlar or {}
    kurlar = kurlar or {}
    if not fiyat or fiyat <= 0:
        notlar.append("fiyat yok")
        return out
    slug = slug_getir(ticker)
    if not slug:
        notlar.append("KAP sirket sayfasi (slug) yok")
        return out

    fin_html = fin_html or _cek(FIN_URL.format(slug=slug))
    if not fin_html:
        notlar.append("KAP finansal sayfasi alinamadi")
        return out
    seri = kap_seriler(_kap_tablolar_metin(fin_html))

    oz = _en_guncel(seri, OZKAYNAK_ETIKETLERI)
    if not oz:
        notlar.append("KAP'ta ozkaynak satiri bulunamadi")
        return out
    donem, ozkaynak, para, _etiket = oz
    out.update(donem=donem, ozkaynak=ozkaynak, para=para)

    # ── pay adedi ve piyasa degeri (TL) ──────────────────────
    genel_html = genel_html or _cek(GENEL_URL.format(slug=slug))
    paylar = pay_adetleri(genel_html) if genel_html else {}
    pd_tl = None
    if paylar:
        if ticker in paylar and len(paylar) == 1:
            adet = paylar[ticker]
            pd_tl = fiyat * adet
        elif ticker in paylar:
            adet = sum(paylar.values())
            eksik = [k for k in paylar if k != ticker and not fiyatlar.get(k)]
            pd_tl = sum(a * ((fiyat if k == ticker else fiyatlar.get(k)) or fiyat) for k, a in paylar.items())
            notlar.append("birden fazla pay grubu: " + ", ".join(sorted(paylar)) +
                          (f" (fiyati olmayan grup {','.join(eksik)} icin {ticker} fiyati kullanildi)" if eksik else ""))
        elif len(paylar) == 1:
            kod, adet = next(iter(paylar.items()))
            pd_tl = fiyat * adet
            notlar.append(f"KAP pay tablosunda kod {kod} (aranan {ticker})")
        else:
            adet = None
        if pd_tl:
            out.update(pay_adedi=adet, pay_kaynak="KAP genel")
            # donem sonundan sonra sermaye degismis mi (bedelsiz: sorun yok, fiyat zaten ayarli; bedelli: ozkaynak
            # henuz yansimadigi icin PD/DD yuksek gorunebilir) - karar vermeden yalnizca isaretle
            _sm = _en_guncel(seri, ("Ödenmiş Sermaye",))
            if _sm and _sm[2] == "TL" and _sm[1] > 0 and abs(sum(paylar.values()) - _sm[1]) / _sm[1] > 0.10:
                notlar.append(f"sermaye {_sm[0]} doneminden sonra degismis: {_sm[1]:,.0f} -> {sum(paylar.values()):,.0f} pay")
    if not pd_tl:
        # yedek: son donem odenmis sermaye (TL ise; 1 lot = 1 TL nominal). Donem sonu degeri - sonradan olan
        # sermaye artirimlarini icermeyebilir; bu yuzden etiketlenir.
        sm = _en_guncel(seri, ("Ödenmiş Sermaye",))
        if sm and sm[2] == "TL":
            pd_tl = fiyat * sm[1]
            out.update(pay_adedi=sm[1], pay_kaynak=f"KAP odenmis sermaye ({sm[0]})")
            notlar.append("pay adedi KAP genel sayfasindan alinamadi; donem sonu odenmis sermaye kullanildi")
        else:
            notlar.append("pay adedi bulunamadi")
            return out
    out["piyasa_degeri"] = pd_tl

    # ── para birimi ──────────────────────────────────────────
    if para == "TL":
        pd_p = pd_tl
    else:
        kur = kurlar.get(para)
        if not kur:
            notlar.append(f"KAP tutarlari {para}; {para}TRY kuru yok")
            return out
        pd_p = pd_tl / kur
        notlar.append(f"KAP tutarlari {para}: piyasa degeri guncel {para}TRY kuruyla ({kur:g}) {para}'ye cevrildi")

    # ── PD/DD ────────────────────────────────────────────────
    if ozkaynak > 0:
        out["pb"] = pd_p / ozkaynak
    else:
        notlar.append("ozkaynak negatif/sifir: PD/DD anlamsiz")

    # ── F/K ──────────────────────────────────────────────────
    kd = _en_guncel(seri, NET_KAR_ETIKETLERI)
    if not kd:
        notlar.append("KAP'ta net kar satiri yok")
        return out
    k_donem, kar, k_para, _ke = kd
    out["kar_donem"], out["net_kar"] = k_donem, kar
    if k_para != para:
        notlar.append("bilanco ve gelir tablosu para birimleri farkli: F/K hesaplanmadi")
        return out
    yil, ay = _donem_anahtar(k_donem)
    if ay == 12:
        kullan, tur, kd_donem = kar, "TTM", k_donem
    else:
        # ara donem: iz. 12A icin onceki yilin ayni donemi gerekir, sayfada yok -> son tam yil
        etiket = _ke
        tam = seri.get(_norm(etiket), {}).get(f"{yil - 1}/12")
        if kar < 0:
            out["pe_durum"] = "zarar"
            notlar.append(f"{k_donem} donemi zarar: F/K yok")
            return out
        if not tam or tam[1] != k_para:
            notlar.append(f"{yil - 1}/12 yillik net kar KAP sayfasinda yok: F/K hesaplanmadi")
            return out
        kullan, tur, kd_donem = tam[0], "YILLIK", f"{yil - 1}/12"
    out["kar_donem"] = kd_donem
    if kullan > 0:
        out["pe"] = pd_p / kullan
        out["pe_tur"] = tur
        out["pe_durum"] = "hesaplandi"
    else:
        out["pe_durum"] = "zarar"
        notlar.append(f"{kd_donem} net kar <= 0: F/K yok")
    return out


# ───────────────────────────────────────────────────────────
#  KAP + yfinance birlesimi (KAP birincil)
# ───────────────────────────────────────────────────────────
PB_TUTARLILIK_ALT, PB_TUTARLILIK_UST = 0.6, 1.6


def _sayi(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def yahoo_tutarli_mi(yf: dict, kap_pb: Optional[float]) -> Optional[bool]:
    """Yahoo'nun mali verisi (F/K, PD/DD) fiyatla AYNI para biriminde mi?
    1) KAP PD/DD varsa: Yahoo PD/DD'si KAP'inkinin 0,6-1,6 kati araliginda ise tutarli (para birimi karisikligi
       oranlari 10-100 kat bozar: THYAO 18,1 vs 0,39). 2) KAP yoksa Yahoo'nun financialCurrency == currency
       bilgisi. Bilinmiyorsa None."""
    if not yf:
        return None
    ypb = _sayi(yf.get("pb_ratio"))
    if kap_pb and ypb:
        return PB_TUTARLILIK_ALT <= ypb / kap_pb <= PB_TUTARLILIK_UST
    fc, cur = yf.get("financial_currency"), yf.get("currency") or "TRY"
    if fc:
        return fc == cur
    return None


def oranlari_birlestir(kap: Optional[dict], yf: Optional[dict], fiyat: float, kurlar: dict = None) -> tuple:
    """(pb, pe, dy, meta). Oncelik: KAP -> yfinance (yalniz para birimi tutarliysa veya kurla cevrilebiliyorsa).
    meta: {'kaynak': 'KAP'|'yfinance'|'yfinance (kurla)'|'', 'donem': 'YYYY/AA'|None,
           'fk_tur': 'TTM'|'YILLIK'|'yfinance'|None, 'fk_donem': F/K'da kullanilan KAP net kar donemi|None, 'notlar': [...]}"""
    kap = kap or {}
    yf = yf or {}
    kurlar = kurlar or {}
    meta = {"kaynak": "", "donem": None, "fk_tur": None, "fk_donem": None, "uyari": None, "notlar": list(kap.get("notlar") or []),
            # Yahoo bu gece bu hisse icin gercekten yanit verdi mi (temettu verimi kaynagi)?
            "yf_ok": (yf.get("_source") == "yfinance") and any(
                _sayi(yf.get(k)) is not None for k in ("pb_ratio", "pe_ratio", "div_yield", "market_cap", "equity"))}
    fc, cur = yf.get("financial_currency"), yf.get("currency") or "TRY"
    tutarli = yahoo_tutarli_mi(yf, kap.get("pb"))

    # ── PD/DD ──
    pb = None
    if kap.get("pb") is not None:
        pb = kap["pb"]
        meta["kaynak"], meta["donem"] = "KAP", kap.get("donem")
    elif yf:
        ypb = _sayi(yf.get("pb_ratio"))
        defter = _sayi(yf.get("equity"))          # Yahoo bookValue: hisse basi, RAPOR para biriminde
        if tutarli is not False and fc in (None, cur) and ypb:
            pb = ypb
            meta["kaynak"] = "yfinance"
        elif fc and fc != cur and fiyat and defter and defter > 0 and kurlar.get(fc):
            pb = fiyat / (defter * kurlar[fc])
            meta["kaynak"] = "yfinance (kurla)"
            meta["notlar"].append(f"yfinance rapor para birimi {fc}: defter degeri guncel {fc}TRY kuruyla cevrildi")
        elif fc and fc != cur:
            meta["notlar"].append(f"yfinance rapor para birimi {fc} != {cur}: PD/DD alinmadi")

    # ── F/K ──
    pe = None
    ype = _sayi(yf.get("pe_ratio"))
    if kap.get("pe_durum") == "hesaplandi" and kap.get("pe_tur") == "TTM":
        pe, meta["fk_tur"], meta["fk_donem"] = kap["pe"], "TTM", kap.get("kar_donem")
    elif kap.get("pb") is not None:
        # KAP bilancosu var ama son donem ara donem (veya net kar satiri yok): iz. 12A KAP'ta hesaplanamaz.
        if ype and tutarli:
            pe, meta["fk_tur"] = ype, "yfinance"
            meta["notlar"].append("F/K: yfinance iz. 12A (KAP PD/DD ile para birimi tutarliligi dogrulandi)")
        elif kap.get("pe_durum") == "hesaplandi":
            pe, meta["fk_tur"], meta["fk_donem"] = kap["pe"], kap.get("pe_tur"), kap.get("kar_donem")
    elif yf:
        if ype and tutarli is not False and fc in (None, cur):
            pe, meta["fk_tur"] = ype, "yfinance"
        elif fc and fc != cur:
            # DOCO ornegi: Yahoo'da defter degeri EUR, hisse basi kar ise TL'ye cevrilmis olabiliyor (ayni
            # kayit icinde tutarsiz) - hangisinin hangi para biriminde oldugu dogrulanamadigindan F/K alinmaz.
            meta["notlar"].append(f"F/K alinmadi: yfinance rapor para birimi {fc} != {cur}, hisse basi kar para birimi dogrulanamiyor")

    # Kullaniciya gosterilecek tek satirlik uyari: sermaye bilanco doneminden sonra degistiyse (bedelli artirimda
    # ozkaynak henuz yansimadigi icin KAP tabanli PD/DD yuksek gorunebilir; bedelsizde sorun yok - fiyat ayarli)
    uyari = next((n for n in meta["notlar"] if n.startswith("sermaye ")), None)
    if uyari and meta["kaynak"] == "KAP":
        meta["uyari"] = uyari[0].upper() + uyari[1:] + "; bedelli artirimsa PD/DD yuksek gorunebilir"
    dy = _sayi(yf.get("div_yield")) if yf else None
    if pb is not None and not (pb > 0):
        pb = None
    if pe is not None and not (pe > 0):
        pe = None
    return pb, pe, dy, meta
