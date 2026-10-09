"""
kap_client.py — BIST Temel Analiz Modülü v2
==================================================
VERİ KAYNAKLARI (öncelik sırasıyla):
  1. yfinance  → F/K, PD/DD, ROE, Ciro, Net Kar, Temettü vb. (hızlı, güvenilir)
  2. KAP API   → Türkçe bilanço kalemleri (Dönen Varlık, KV Borç, Özkaynak, Sermaye)

NOT: KAP.org.tr, bazı IP adreslerinden 403 döndürebilir.
     Bu durumda yfinance verileri kullanılır ve BIST temel skorun %70'i kapsanmış olur.
     Uygulama çalışmaya devam eder; KAP kısmı 'Veri alınamadı' olarak görünür.
"""

import requests
import streamlit as st
from typing import Optional

# ─── KAP SLUG HARİTASI (Bahri'nin onayladığı KAP_BIST.xlsx'ten) ──
# v2.0.7.67 - KRITIK DUZELTME (Bahri'nin bulgusu, 16 Temmuz 2026): daha
# once burada SADECE 65 sirketlik ELLE yazilmis kucuk bir liste vardi.
# Ama Bahri sistemi ilk kurarken KAP_BIST.xlsx dosyasini TAM OLARAK bu
# amac icin (ticker -> KAP finansal-bilgiler URL'si, 730 sirket) zaten
# vermisti - bu dosya repoda DURUYORDU ama worker.py sadece isim
# sutununu (kolon 1) okuyup URL sutununu (kolon 2) hic kullanmiyordu.
# Simdi bu HAZIR, ONAYLI kaynak dogrudan buradan okunuyor - elle
# yazilmis kucuk liste TAMAMEN TERK EDILDI.
#
# v2.0.7.378 (9 Ekim 2026, Bahri'nin talebi): onceki surumde yeni halka
# arzlarin otomatik eklenmemesi BILINCLI idi; Bahri artik tersini istedi
# ("yfinance gibi ikincil degil birincil kaynaktan alinsin"). Bu yuzden:
#   1) ORZAX dahil 21 yeni hisse KAP_BIST.xlsx'e eklendi (KAP'in kendi listesinden),
#   2) xlsx'te olmayan bir kod icin KAP'in resmi BIST listesine canli bakan
#      slug_getir() yedegi eklendi (asagida) - gelecekteki yeni hisseler dosyayi
#      elle guncellemeden KAP birincil verisini alir.
def _kap_slug_map_yukle() -> dict:
    import os, glob
    result = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = (
        glob.glob(os.path.join(base_dir, "KAP_BIST.xlsx")) +
        glob.glob(os.path.join(base_dir, "KAP_BIST*.xlsx")) +
        glob.glob(os.path.join(base_dir, "kap_bist*.xlsx"))
    )
    if not candidates:
        print("[kap_client] UYARI: KAP_BIST.xlsx bulunamadi, KAP verisi devre disi.")
        return result
    try:
        import pandas as _pd
        df = _pd.read_excel(candidates[0], header=None)
        for _, row in df.iterrows():
            ticker_raw = str(row.iloc[0]).strip()
            url_raw = str(row.iloc[2]).strip() if len(row) > 2 else ""
            if ticker_raw in ("nan", "") or url_raw in ("nan", ""):
                continue
            # ".../sirket-finansal-bilgileri/{slug}" -> sadece {slug} kismi
            slug = url_raw.rstrip("/").split("/")[-1]
            if not slug:
                continue
            for t in ticker_raw.split(","):
                t = t.strip().upper()
                if t:
                    result[t] = slug
        print(f"[kap_client] KAP_BIST.xlsx: {len(result)} sirket icin KAP slug'i yuklendi.")
    except Exception as e:
        print(f"[kap_client] KAP_BIST.xlsx okunamadi: {e}")
    return result


KAP_SLUG_MAP = _kap_slug_map_yukle()

# v2.0.7.378 - xlsx'te olmayan kodlar icin KAP'in resmi listesinden CANLI yedek arama.
# Sonuc surec boyunca bellekte tutulur; liste cekilemezse 10 dk boyunca tekrar denenmez
# (her hisse tiklamasinda KAP'i yormamak icin). Hata durumunda None doner -> yfinance'e dusulur.
_CANLI_SLUG = {"harita": None, "son_deneme": 0.0}
_CANLI_GERI_CEKILME_SN = 600


def slug_getir(ticker: str) -> Optional[str]:
    t = str(ticker or "").strip().upper()
    if not t:
        return None
    if t in KAP_SLUG_MAP:
        return KAP_SLUG_MAP[t]
    import time as _time
    if _CANLI_SLUG["harita"] is None:
        if _time.time() - _CANLI_SLUG["son_deneme"] < _CANLI_GERI_CEKILME_SN:
            return None
        _CANLI_SLUG["son_deneme"] = _time.time()
        try:
            import kap_evren as _ke
            h = {}
            for k in _ke.kap_bist_listesini_cek(deneme=2):
                for kod in k["kodlar"]:
                    h.setdefault(kod, k["slug"])
            _CANLI_SLUG["harita"] = h
            print(f"[kap_client] KAP canli listeden {len(h)} kod icin yedek slug haritasi yuklendi.")
        except Exception as e:
            print(f"[kap_client] KAP canli liste yedegi alinamadi: {e}")
            return None
    return _CANLI_SLUG["harita"].get(t)

KAP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Origin": "https://kap.org.tr",
    "Referer": "https://kap.org.tr/",
}


# ─── YARDIMCILAR ─────────────────────────────────────────────

def _safe_float(v) -> Optional[float]:
    if v is None or v == "": return None
    try:
        return float(str(v).replace(",", ".").replace(" ", "").replace("₺", ""))
    except: return None

def _safe_float_kap_tr(v) -> Optional[float]:
    """v2.0.7.66 - KAP'in HTML tablolarindaki BUYUK Turkce formatli sayilar
    icin (orn. '45.269.483.033' -> 45269483033.0, nokta binlik ayiraci).
    _safe_float'tan AYRI tutuldu - o fonksiyon yfinance'in zaten duz
    ondalikli (42.5 gibi) degerlerini parse ediyor, oraya Turkce binlik
    ayirac mantigi eklemek yfinance tarafini bozardi."""
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "-", "—", "nan", "NaN", "None"):
        return None
    try:
        # Turkce format: nokta binlik ayiraci, virgul (varsa) ondalik ayiraci
        s = s.replace(".", "").replace(",", ".").replace("₺", "").replace(" ", "")
        return float(s)
    except (ValueError, TypeError):
        return None

def _fmt_mil(v, suffix="₺") -> str:
    if v is None: return "—"
    try:
        f = float(v)
        if abs(f) >= 1e12: return f"{f/1e12:.2f} Trilyon {suffix}"
        if abs(f) >= 1e9:  return f"{f/1e9:.2f} Milyar {suffix}"
        if abs(f) >= 1e6:  return f"{f/1e6:.2f} Milyon {suffix}"
        return f"{f:,.0f} {suffix}"
    except: return "—"

def _fmt_ratio(v, suffix="") -> str:
    if v is None: return "—"
    try: return f"{float(v):.2f}{suffix}"
    except: return "—"

def _fmt_pct(v) -> str:
    if v is None: return "—"
    try: return f"{float(v)*100:.2f}%"
    except: return "—"


# ─── KAYNAK 1: yfinance ──────────────────────────────────────

def _fetch_yfinance(ticker: str) -> dict:
    """yfinance'den temel finansal verileri çeker, veri kalitesini doğrular."""
    try:
        import yfinance as yf
        info = yf.Ticker(f"{ticker}.IS").info

        def _v(key):
            return _safe_float(info.get(key))

        # ── Ham değerler ───────────────────────────────
        pe        = _v("trailingPE")
        forward_pe= _v("forwardPE")
        pb        = _v("priceToBook")
        beta      = _v("beta")
        div_yield = _v("dividendYield")
        net_income= _v("netIncomeToCommon")

        # ── Veri Kalitesi Filtreleri (return'dan ÖNCE) ─
        # F/K: negatif = zararda, anlamsız
        if pe is not None and pe < 0:         pe = None
        # İleriye F/K: çok yüksek veya negatif
        if forward_pe is not None and (forward_pe < 0 or forward_pe > 500): forward_pe = None
        # PD/DD: 0 veya negatif
        if pb is not None and pb <= 0:         pb = None
        # Beta: 0'a çok yakın veya negatif → güvenilmez
        if beta is not None and abs(beta) < 0.05: beta = None
        # Temettü: yfinance %5 için 0.05 saklar; >0.5 = %50 → gerçek dışı
        if div_yield is not None and div_yield > 0.5: div_yield = None

        return {
            # Değerleme
            "market_cap":     _v("marketCap"),
            "pe_ratio":       pe,
            "forward_pe":     forward_pe,
            "pb_ratio":       pb,
            "ps_ratio":       _v("priceToSalesTrailing12Months"),
            "peg_ratio":      _v("pegRatio"),
            "ev":             _v("enterpriseValue"),
            # Kârlılık
            "eps":            _v("trailingEps"),
            "revenue":        _v("totalRevenue"),
            "gross_profit":   _v("grossProfits"),
            "ebitda":         _v("ebitda"),
            "net_income":     net_income,
            "op_margin":      _v("operatingMargins"),
            "net_margin":     _v("profitMargins"),
            "gross_margin":   _v("grossMargins"),
            # Bilanço
            "equity":         _v("bookValue"),
            "current_ratio":  _v("currentRatio"),
            "quick_ratio":    _v("quickRatio"),
            "debt_equity":    _v("debtToEquity"),
            "total_cash":     _v("totalCash"),
            "total_debt":     _v("totalDebt"),
            # Verimlilik
            "roe":            _v("returnOnEquity"),
            "roa":            _v("returnOnAssets"),
            # Piyasa
            "beta":           beta,
            "div_yield":      div_yield,
            "div_rate":       _v("dividendRate"),
            "payout_ratio":   _v("payoutRatio"),
            "week52_high":    _v("fiftyTwoWeekHigh"),
            "week52_low":     _v("fiftyTwoWeekLow"),
            "avg_volume":     _v("averageVolume"),
            # Kimlik
            "sector":         str(info.get("sector",  "—")),
            "industry":       str(info.get("industry", "—")),
            "employees":      _v("fullTimeEmployees"),
            "description":    str(info.get("longBusinessSummary", ""))[:300],
            # v2.0.7.381: Yahoo, sirketin RAPOR para birimi (financialCurrency) ile islem para birimini (currency)
            # karistirabiliyor (THYAO: bilanco USD, fiyat TRY -> PD/DD 18,1). Bu iki alan olmadan tutarlilik
            # kontrol edilemezdi.
            "financial_currency": (str(info.get("financialCurrency")).upper() if info.get("financialCurrency") else None),
            "currency":       (str(info.get("currency")).upper() if info.get("currency") else None),
            "price":          _v("currentPrice") or _v("regularMarketPrice") or _v("previousClose"),
            "_source":        "yfinance",
        }
    except Exception as e:
        return {"_source": "yfinance_error", "_error": str(e)}


# ─── KAYNAK 2: KAP.org.tr ────────────────────────────────────

def _fetch_kap(ticker: str) -> dict:
    """
    KAP'tan Türkçe bilanço kalemlerini çeker.
    Çalışmazsa boş dict döner — yfinance verisi yeterli olur.

    v2.0.7.66 - TAM YENIDEN YAZILDI (Bahri'nin bulgusu, 15 Temmuz):
    Onceki surum tamamen HAYALI/DOGRULANMAMIS JSON API adreslerine
    (orn. "kap.org.tr/tr/api/financialReport/{id}/summary") istek
    atiyordu - bunlar gercekte HICBIR ZAMAN calisan endpoint'ler
    degildi, bu yuzden AHGAZ dahil NEREDEYSE HICBIR hisse icin KAP
    verisi gelmiyordu. Bahri'nin verdigi gercek KAP sayfasini
    (kap.org.tr/tr/sirket-finansal-bilgileri/{slug}) inceledim: bu
    JS gerektirmeyen, SUNUCU TARAFINDA RENDER EDILMIS normal bir HTML
    sayfasi - icinde gercek <table> etiketleriyle bilanco/gelir tablosu
    var. Artik bu GERCEK, DOGRULANMIS sayfa cekilip pandas.read_html
    ile ayristiriliyor - JSON API varsayimi tamamen terk edildi.
    """
    slug = slug_getir(ticker)
    if not slug:
        return {"_kap_available": False,
                "_kap_note": "Veri kaynağı: yfinance"}

    result = {"_kap_available": True}
    url = f"https://kap.org.tr/tr/sirket-finansal-bilgileri/{slug}"

    try:
        r = requests.get(url, headers=KAP_HEADERS, timeout=10)
        if r.status_code == 200 and r.text and len(r.text) > 500:
            import pandas as _pd
            import io as _io
            # v2.0.7.66 - KRITIK: read_html'e HAM STRING verilirse pandas
            # bunu dosya YOLU saniyor (FileNotFoundError firlatiyor) -
            # io.StringIO ile sarmalamak SART. Yerel testle dogrulandi.
            # v2.0.7.381: pandas.read_html yerine METIN tabanli okuyucu (sondaki sifiri kaybetme hatasi)
            try:
                tablolar = _kap_tablolar_metin(r.text)
            except Exception:
                tablolar = _pd.read_html(_io.StringIO(r.text))
            _parse_kap_financials(tablolar, result)
            if len(result) > 1:  # "_kap_available" disinda en az 1 alan geldiyse
                result["_kap_source"] = url
    except Exception as e:
        result["_kap_err"] = str(e)[:80]

    if "_kap_source" not in result:
        result["_kap_available"] = False
        result["_kap_note"] = "Veri kaynağı: yfinance"

    return result


def _kap_tablolar_metin(html: str) -> list:
    """v2.0.7.381 - KAP sayfasindaki TUM <table>'lari METIN olarak (DataFrame, dtype=str) dondurur.

    Neden pandas.read_html degil: read_html hucreleri SAYIYA cevirir; KAP'in '745.430' (= 745 bin 430,
    Turkce binlik noktasi) hucresi 745.43 (float) olur, sondaki sifir kaybolur ve _safe_float_kap_tr bunu
    74543 okurdu (10/100/1000 kat kucuk deger). Canli KAP sayfasinda dogrulandi (THYAO Hasilat 2024/12).
    Burada metin oldugu gibi korunur; ilk satirda <th> varsa o satir sutun basligi olur (read_html ile ayni)."""
    import pandas as _pd
    import lxml.html as _lh
    doc = _lh.fromstring(html)
    sonuc = []
    for tb in doc.xpath("//table"):
        satirlar, baslik = [], None
        for i, tr in enumerate(tb.xpath(".//tr")):
            hucreler = tr.xpath("./th|./td")
            if not hucreler:
                continue
            metin = [" ".join(h.text_content().split()) for h in hucreler]
            if not satirlar and baslik is None and all(h.tag == "th" for h in hucreler):
                baslik = metin
                continue
            satirlar.append(metin)
        if not satirlar and baslik is None:
            continue
        n = max([len(r) for r in satirlar] + [len(baslik or [])])
        satirlar = [r + [""] * (n - len(r)) for r in satirlar]
        kolonlar = (baslik + [f"c{j}" for j in range(len(baslik), n)]) if baslik else list(range(n))
        sonuc.append(_pd.DataFrame(satirlar, columns=kolonlar, dtype=str))
    return sonuc


import re as _re_donem
_KAP_DONEM_RE = _re_donem.compile(r"\d{4}/\d{1,2}")


def _kap_birim_carpani(tablolar: list, result: dict) -> float:
    """Ilk 'Sunum Para Birimi' satirindan carpan: TL -> 1, 1000TL -> 1000, 1000000TL -> 1000000. TL disi para birimi
    (USD, EUR ...) tutarlari TL gibi gosterilmesin diye result['kap_para_birimi'] ile isaretlenir
    ve carpan 1 kalir (donusum YAPILMAZ - kur uydurulmaz)."""
    import re as _re
    for df in tablolar:
        if df.shape[1] < 2:
            continue
        ilk = df.iloc[:, 0].astype(str).str.strip()
        e = df[ilk == "Sunum Para Birimi"]
        if e.empty:
            continue
        satir = e.iloc[0]
        for i in range(len(satir) - 1, 0, -1):
            v = str(satir.iloc[i]).strip().upper().replace(" ", "")
            if v in ("", "NAN"):
                continue
            m = _re.fullmatch(r"(\d{1,3}(?:\.?\d{3})*)?([A-Z]{2,4})", v)
            if not m:
                result["kap_para_birimi"] = v
                return 1.0
            kat = float(m.group(1).replace(".", "")) if m.group(1) else 1.0
            if m.group(2) not in ("TL", "TRY"):
                result["kap_para_birimi"] = v
                return 1.0
            return kat
        break
    return 1.0


def _parse_kap_financials(tablolar: list, result: dict):
    """v2.0.7.66 - TAM YENIDEN YAZILDI: KAP'in GERCEK sayfa yapisi
    pandas.read_html() ile bir DataFrame LISTESI olarak gelir (JSON
    degil). Her tablonun ilk sutunu Turkce satir etiketleri (orn.
    "Dönen Varlıklar"), diger sutunlar donemler (en sagdaki = en
    guncel/"cari donem"). Bu fonksiyon etiketlere gore satirlari bulup
    EN SON (en sagdaki, bos olmayan) donem degerini alir."""
    satir_etiket_map = {
        "Dönen Varlıklar":            "kap_current_assets",
        "Duran Varlıklar":            "kap_noncurrent_assets",
        "Toplam Varlıklar":           "kap_total_assets",
        "Kısa Vadeli Yükümlülükler":  "kap_short_term_debt",
        "Uzun Vadeli Yükümlülükler":  "kap_long_term_debt",
        "Toplam Yükümlülükler":       "kap_total_liabilities",
        "Ana Ortaklığa Ait Özkaynaklar": "kap_equity",
        "Toplam Özkaynaklar":         "kap_total_equity",
        "Ödenmiş Sermaye":            "kap_paid_capital",
        "Hasılat":                    "kap_revenue",
        "Esas Faaliyet Kârı (Zararı)":"kap_operating_income",
        "Brüt Kâr (Zarar)":           "kap_gross_profit",
        "Net Dönem Kârı (Zararı)":    "kap_net_income",
    }
    # v2.0.7.378 - "Sunum Para Birimi" satiri: TL / 1000TL / USD ... Bazi sirketler (orn. VEYAS)
    # "1000TL" sunar; birim okunmazsa tutarlar 1000 kat kucuk gorunurdu.
    carpan = _kap_birim_carpani(tablolar, result)
    # v2.0.7.379: her alanin KAP donemi (sutun basligi, orn. "2026/06"). Bilanco tablosunun basligi kendi
    # sutunlarinda, gelir tablosu satirlari ise basligi onceki "KAR VEYA ZARAR..." tablosunda tasir.
    donemler = {}
    son_baslik = None
    for df in tablolar:
        if df.shape[1] < 2:
            continue
        basliklar = [str(c).strip() for c in df.columns]
        if any(_KAP_DONEM_RE.fullmatch(b) for b in basliklar):
            son_baslik = basliklar
        ilk_sutun = df.iloc[:, 0].astype(str).str.strip()
        for etiket, alan in satir_etiket_map.items():
            if alan in result:
                continue  # zaten baska bir tablodan bulunmus (ilkini koru)
            eslesen = df[ilk_sutun == etiket]
            if eslesen.empty:
                continue
            satir = eslesen.iloc[0]
            # En sagdaki (en guncel donem) BOS OLMAYAN degeri al
            for sutun_idx in range(len(satir) - 1, 0, -1):
                deger = _safe_float_kap_tr(satir.iloc[sutun_idx])
                if deger is not None:
                    result[alan] = deger * carpan
                    ref = basliklar if any(_KAP_DONEM_RE.fullmatch(b) for b in basliklar) else (
                        son_baslik if son_baslik and len(son_baslik) == len(basliklar) else None)
                    if ref and _KAP_DONEM_RE.fullmatch(ref[sutun_idx]):
                        donemler[alan] = ref[sutun_idx]
                    break
    if donemler:
        result["kap_donemler"] = donemler


# ─── ANA FONKSİYONLAR ────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)  # 24 saat cache
def fetch_kap_fundamentals(ticker: str) -> dict:
    """
    Temel analiz verisi çeker.
    yfinance (birincil) + KAP (ikincil/Türkçe kalemler).
    """
    ticker = ticker.upper()
    result = {}

    # 1. yfinance
    yf_data = _fetch_yfinance(ticker)
    result.update(yf_data)

    # 2. KAP (slug haritasındaysa)
    if slug_getir(ticker):
        kap_data = _fetch_kap(ticker)
        result.update(kap_data)
    else:
        result["_kap_available"] = False
        result["_kap_note"] = "Veri kaynağı: yfinance"

    # 3. v2.0.7.381: Yahoo rapor para birimi (financialCurrency) fiyat para biriminden farklıysa (THYAO USD,
    # DOCO EUR) Yahoo'nun F/K ve PD/DD'si fiyatla farklı para biriminde hesaplanmıştır -> kullanılmaz
    # (ekrandaki ve skordaki PD/DD/F/K CSV'deki KAP tabanlı değerlerdir, bkz. temel_satiri()).
    fc, cur = result.get("financial_currency"), result.get("currency") or "TRY"
    if fc and fc != cur:
        result["_para_uyumsuz"] = fc
        for k in ("pe_ratio", "forward_pe", "pb_ratio"):
            result[k] = None

    return result


def temel_satiri(row) -> dict:
    """CSV satırından (worker'ın KAP-öncelikli hesabı) Temel Skor girdilerini ve kaynak etiketlerini çıkarır.
    Dönüş: {'pb','pe','dy','kaynak','donem','fk_tur'} - değerler yoksa None."""
    def al(k):
        try:
            v = row.get(k)
        except Exception:
            return None
        if v is None:
            return None
        try:
            if v != v:
                return None
        except Exception:
            pass
        return v
    def say(v):
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None
    return {"pb": say(al("PB")), "pe": say(al("PE")), "dy": say(al("DY")),
            "kaynak": al("Temel_Kaynak"), "donem": al("Temel_Donem"), "fk_tur": al("Temel_FK_Tur"),
            "fk_donem": al("Temel_FK_Donem"), "uyari": al("Temel_Uyari"), "pd": say(al("Temel_PD"))}


def kaynak_notu(raw: dict, temel: dict = None) -> str:
    """Detay sayfasındaki 'Kaynak:' alt yazısı (v2.0.7.381: KAP birincil)."""
    kay = (temel or {}).get("kaynak") or ""
    d = (temel or {}).get("donem")
    if kay == "KAP":
        n = f"KAP (PD/DD ve F/K, {d} bilançosu) + yfinance (temettü, piyasa verileri)" if d else "KAP + yfinance"
    elif kay.startswith("yfinance"):
        n = "yfinance (bu hisse için KAP verisinden oran hesaplanamadı)"
    else:
        n = "yfinance"
        if raw.get("_kap_available"): n += " + KAP"
        elif raw.get("_kap_note"):    n += f" | KAP: {raw['_kap_note']}"
    if raw.get("_para_uyumsuz"):
        n += f" | yfinance rapor para birimi {raw['_para_uyumsuz']}: tutar satırları o birimde"
    if (temel or {}).get("uyari"):
        n += f" | Not: {temel['uyari']}"
    return n


def fundamentals_to_display(raw: dict, temel: dict = None) -> dict:
    """Ham veriyi ekrana uygun formata çevirir — Türkçe etiketler.
    v2.0.7.381: `temel` (temel_satiri() çıktısı) verilirse PD/DD ve F/K satırları Temel Skor'un KULLANDIĞI
    değerlerdir (KAP tabanlı, kaynak+dönem etiketli); Yahoo'nun rapor para birimi farklıysa (USD/EUR) Yahoo'nun
    tutar satırları para birimiyle etiketlenir."""
    fc = raw.get("_para_uyumsuz")
    sfx = {"USD": " $", "EUR": " €"}.get(fc, f" {fc}") if fc else " ₺"
    et = f", {fc}" if fc else ""

    # yfinance verileri
    yf = {
        "Piyasa Değeri":        _fmt_mil(raw.get("market_cap")),
        "F/K Oranı (İz. 12A)":  _fmt_ratio(raw.get("pe_ratio")),
        "İleriye Dön. F/K":     _fmt_ratio(raw.get("forward_pe")),
        "PD/DD Oranı":          _fmt_ratio(raw.get("pb_ratio")),
        f"Hisse Başı Kazanç (yfinance{et})":    _fmt_ratio(raw.get("eps"), sfx),
        f"Ciro (Yıllık, yfinance{et})":        _fmt_mil(raw.get("revenue"), sfx.strip()),
        f"Net Kâr (yfinance{et})":              _fmt_mil(raw.get("net_income"), sfx.strip()),
        f"FAVÖK (yfinance{et})":                _fmt_mil(raw.get("ebitda"), sfx.strip()),
        "Faaliyet Marjı":       _fmt_pct(raw.get("op_margin")),
        "Net Kâr Marjı":        _fmt_pct(raw.get("net_margin")),
        f"Özkaynak (Defter, yfinance{et})":    _fmt_ratio(raw.get("equity"), sfx + "/hisse"),
        "Cari Oran":            _fmt_ratio(raw.get("current_ratio")),
        "Asit-Test Oranı":      _fmt_ratio(raw.get("quick_ratio")),
        "Borç/Özkaynak":        _fmt_ratio(raw.get("debt_equity")),
        "Özkaynak Kârlılığı":   _fmt_pct(raw.get("roe")),
        "Aktif Kârlılığı":      _fmt_pct(raw.get("roa")),
        "Temettü Getirisi":     _fmt_pct(raw.get("div_yield")) if raw.get("div_yield") else "—",
        "Temettü Dağıtım Oranı":_fmt_pct(raw.get("payout_ratio")) if raw.get("payout_ratio") else "—",
        "Beta":                 _fmt_ratio(raw.get("beta")),
        "52H Yüksek":           _fmt_ratio(raw.get("week52_high"), " ₺"),
        "52H Düşük":            _fmt_ratio(raw.get("week52_low"), " ₺"),
        "Sektör":               raw.get("sector", "—"),
        "Endüstri":             raw.get("industry", "—"),
    }

    # v2.0.7.381: Temel Skor'un kullandığı PD/DD ve F/K (KAP tabanlı) - Yahoo'nun aynı adlı satırlarının YERİNE
    if temel and (temel.get("pb") is not None or temel.get("pe") is not None or temel.get("pd") is not None):
        kay = temel.get("kaynak") or ""
        d = temel.get("donem")
        yeni_pb = yeni_fk = None
        if temel.get("pb") is not None:
            yeni_pb = (f"PD/DD Oranı ({kay}{', ' + str(d) if d and kay == 'KAP' else ''})" if kay else "PD/DD Oranı",
                       _fmt_ratio(temel["pb"]))
        if temel.get("pe") is not None:
            tur = temel.get("fk_tur")
            if tur == "TTM":
                fd = temel.get("fk_donem") or d
                lab = f"F/K Oranı (KAP, iz. 12A, {fd})" if fd else "F/K Oranı (KAP, iz. 12A)"
            elif tur == "YILLIK":
                fd = temel.get("fk_donem")
                lab = f"F/K Oranı (KAP, {fd} yıllık net kâr)" if fd else "F/K Oranı (KAP, son tam yıl net kârı)"
            elif tur == "yfinance":
                lab = "F/K Oranı (iz. 12A, yfinance)"
            else:
                lab = "F/K Oranı"
            yeni_fk = (lab, _fmt_ratio(temel["pe"]))
        sirali = {}
        for k, v in yf.items():
            if k == "F/K Oranı (İz. 12A)":
                if yeni_fk: sirali[yeni_fk[0]] = yeni_fk[1]
            elif k == "PD/DD Oranı":
                if yeni_pb: sirali[yeni_pb[0]] = yeni_pb[1]
            elif k == "İleriye Dön. F/K":
                continue
            elif k == "Piyasa Değeri" and kay == "KAP" and temel.get("pd"):
                # v2.0.7.385: PD/DD'nin payı olan piyasa değeri (KAP pay adedi x fiyat) - Yahoo'nun pay adedi
                # KAP'tan farklı olabilir (ORZAX: 246,4M vs 338,5M)
                sirali["Piyasa Değeri (KAP pay adedi × fiyat)"] = _fmt_mil(temel["pd"])
            else:
                sirali[k] = v
        yf = sirali

    # KAP ek verileri (varsa)
    kap_fields = {
        "kap_current_assets":    ("Dönen Varlık (KAP)", "₺"),
        "kap_noncurrent_assets": ("Duran Varlık (KAP)", "₺"),
        "kap_total_assets":      ("Toplam Varlık (KAP)", "₺"),
        "kap_short_term_debt":   ("KV Borç (KAP)", "₺"),
        "kap_long_term_debt":    ("UV Borç (KAP)", "₺"),
        "kap_total_liabilities": ("Toplam Yükümlülük (KAP)", "₺"),
        "kap_equity":            ("Özkaynak (KAP)", "₺"),
        "kap_total_equity":      ("Toplam Özkaynak (KAP)", "₺"),
        "kap_revenue":           ("Ciro (KAP)", "₺"),
        "kap_net_income":        ("Net Kâr (KAP)", "₺"),
        "kap_operating_income":  ("Faaliyet Kârı (KAP)", "₺"),
        "kap_gross_profit":      ("Brüt Kâr (KAP)", "₺"),
        "kap_market_cap":        ("PD (KAP)", "₺"),
        "kap_paid_capital":      ("Ödenmiş Sermaye (KAP)", "₺"),
    }
    donemler = raw.get("kap_donemler") or {}
    for field, (label, unit) in kap_fields.items():
        if raw.get(field) is not None:
            d = donemler.get(field)
            # v2.0.7.379: KAP dönemi etikette ("Ciro (KAP, 2026/06)") - yfinance satırları farklı dönem olabilir
            yf[label.replace("(KAP)", f"(KAP, {d})") if d else label] = _fmt_mil(raw[field])

    # v2.0.7.385 (Bahri: "iki veri arasinda fark varsa KAP verileri onceliklidir"): KAP'ta karsiligi olan Yahoo
    # tutar satirlari kalkar (Yahoo 12 aylik, KAP son donem - iki rakami yan yana gostermek kafa karistirir);
    # marjlar KAP'in kendi (ayni donem) ciro/kar rakamlarindan hesaplanir. KAP'ta karsiligi olmayanlar Yahoo etiketli kalir.
    def _kap_var(alan):
        return raw.get(alan) is not None

    def _sil(onek):
        for _k in [k for k in yf if k.startswith(onek)]:
            del yf[_k]

    if _kap_var("kap_revenue"):
        _sil("Ciro (Yıllık, yfinance")
    if _kap_var("kap_net_income"):
        _sil("Net Kâr (yfinance")
    if _kap_var("kap_equity") or _kap_var("kap_total_equity"):
        _sil("Özkaynak (Defter, yfinance")
    gelir = raw.get("kap_revenue")
    for _alan, _etiket, _yf_etiket in (("kap_operating_income", "Faaliyet Marjı", "Faaliyet Marjı"),
                                       ("kap_net_income", "Net Kâr Marjı", "Net Kâr Marjı")):
        _d = donemler.get(_alan)
        if gelir and gelir > 0 and raw.get(_alan) is not None and _d and _d == donemler.get("kap_revenue"):
            yf.pop(_yf_etiket, None)
            yf[f"{_etiket} (KAP, {_d})"] = _fmt_pct(raw[_alan] / gelir)
        elif _yf_etiket in yf:
            yf[f"{_yf_etiket} (yfinance)"] = yf.pop(_yf_etiket)

    # KAP durumu
    # v2.0.7.50 - DUZELTME: "_kap_note" alani duz "Veri kaynağı: yfinance"
    # metniydi - "KAP Durumu" satirinin ETIKETIYLE uyumsuzdu (etiket KAP'in
    # durumunu soruyor, icerik yfinance'ten bahsediyordu). Artik etiketle
    # tutarli, acik bir ifade kullaniliyor.
    if not raw.get("_kap_available", True):
        yf["KAP Durumu"] = "Bilanço verisi bulunamadı (yfinance kullanılıyor)"
    elif raw.get("kap_para_birimi"):
        yf["KAP Para Birimi"] = (f"{raw['kap_para_birimi']} (KAP tutarları bu birimde, TL'ye "
                                 f"çevrilmedi; yukarıdaki (KAP) satırlarındaki ₺ simgesi geçerli değil)")

    # Boş alanları kaldır
    return {k: v for k, v in yf.items() if v != "—"}


def score_from_fundamentals(raw: dict, current_price: float) -> float:
    """
    Temel analiz verilerinden 0-30 arası puan üretir.
    Bu puan teknik skor (%70) ile birleşerek Master Skor oluşturur.

    KRITER            PUAN   MANTIK
    F/K < 8           10     Değer yatırımı fırsatı
    F/K 8-15          7      Makul değerleme
    F/K 15-25         3      Normal
    PD/DD < 1         8      Defter değerinin altında
    PD/DD 1-2         5      Makul
    Temettü > %8      7      Yüksek nakit getirisi
    Temettü > %4      4      İyi temettü
    Net Kâr > 0       5      Kârlı şirket
    """
    score = 0.0

    pe = raw.get("pe_ratio")
    if pe:
        try:
            pe = float(pe)
            if 0 < pe < 8:   score += 10
            elif pe < 15:    score += 7
            elif pe < 25:    score += 3
        except: pass

    pb = raw.get("pb_ratio")
    if pb:
        try:
            pb = float(pb)
            if 0 < pb < 1:   score += 8
            elif pb < 2:     score += 5
            elif pb < 3.5:   score += 2
        except: pass

    dy = raw.get("div_yield")
    if dy:
        try:
            dy = float(dy)
            if dy > 0.08:    score += 7
            elif dy > 0.04:  score += 4
            elif dy > 0.02:  score += 2
        except: pass

    ni = raw.get("net_income") or raw.get("kap_net_income")
    if ni:
        try:
            if float(ni) > 0: score += 5
        except: pass

    return min(30.0, round(score, 1))


def get_kap_url(ticker: str) -> Optional[str]:
    """KAP sayfası URL'sini döner."""
    slug = slug_getir(ticker)
    if slug:
        return f"https://kap.org.tr/tr/sirket-finansal-bilgileri/{slug}"
    return None