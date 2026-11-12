# -*- coding: utf-8 -*-
"""
spk_hisse_tedbir.py - SPK bultenlerinden HISSE (BIST) icin iki tur tedbir cikarir ve ONAYSIZ, OTOMATIK uygular.

v2.0.7.437 (12 Kasim 2026, Bahri'nin karari): "Tumu" suc duyurulari kalici 0; kisilere gecici islem yasagi olan
hisseler yasak SURESINCE 0; "aday olarak yazilmasin, otomatik olarak 0'lansin, bana tekrar sorulmasin".

  SUC       "<Sirket> (KOD) pay piyasasinda ... sorumlulugu bulunan sahislar hakkinda ... suc duyurusunda
            bulunulmasina karar verilmistir" (SPKn 107/1 islem bazli, 107/2 bilgi bazli). Hisse islem gormeye devam
            eder, suc duyurusu hisseyi islem yapan SORUMLU KISILERE yoneliktir. KALICI kural (bitis yok).
  YASAK     "<Sirket> (KOD) pay piyasasinda ... piyasa dolandiriciligi fiilinin islendigine dair MAKUL SUPHE
            bulunmasi nedeniyle ... kisiler hakkinda <tarih> tarihli islemlerden baslamak uzere borsalarda
            6 ay suresiyle gecici islem yasagi uygulanmasina karar verilmistir" (V-101.1 Teblig 5/1, 6/1).
            Yasak kisilere uygulanir; hisse manipulasyon SUPHESI altindadir. Kural yasak suresi KADAR gecerli
            (bitis_tarihi); sure dolunca skor kendiliginden doner.

Bu modul SAF (veritabani/ag yok): metin -> kayitlar (cikarma), kayitlar + mevcut kurallar -> eylem plani (karar).
Uygulamayi spk_bulten_izleme.py yapar. 2022-2026/79 bultenlerinde (343+ bulten) uc BAGIMSIZ yontemle
(bolum basligi, harfli madde, cumle anahtari) capraz dogrulandi: 33 suc duyurulu, 89 yasakli hisse.
"""
import calendar
import re
from datetime import date, datetime, timedelta

from piyasa_tedbir import tr_harf_norm

TUR_SUC = "SUC"
TUR_YASAK = "YASAK"

# kural tedbir_turu
TEDBIR_SUC = "MANIPULASYON_SUPHESI"            # mevcut tur (3 tohum kural, onay penceresi ile AYNI)
TEDBIR_YASAK = "ISLEM_YASAGI_SUPHESI"          # yeni tur (yasak SURESINCE gecerli)
KALICI_TURLER = {"MANIPULASYON_SUPHESI", "SUC_DUYURUSU", "ISLEME_KAPATMA", "ISLEM_DURDURMA_TASFIYE",
                 "TASFIYE_VE_ISLEME_KAPATMA", "TASFIYE", "TASFIYE_IZNI"}

KAYNAK_GECMIS = "SPK_BULTEN_GECMIS"            # gecmis taramasi (bildirim e-postasi ATLAR)
KAYNAK_CANLI = "SPK_BULTEN_OTO"                # canli izleyicinin onaysiz uyguladigi

# --- anahtarlar (tr_harf_norm uzerinde: buyuk harf, Turkce harfler sadelesmis) -------------------
SUC_RX = re.compile(r"SUC DUYURU\w*\s+(?:LARININ\s+)?(?:YAPILMASINA|BULUNULMASINA)\s+KARAR|"
                    r"SUC DUYURUSUNDA BULUNULMASINA|SUC DUYURUSUNUN YAPILMASINA")
YASAK_RX = re.compile(r"MAKUL SUPHE|GECICI ISLEM YASAGI\w*\s+UYGULANMASINA|ISLEM YAPMAKTAN YASAKLANMASINA")
SINIR_RX = re.compile(r"KARAR VERILMISTIR|UYGULANMASINA|YAPILMASINA KARAR")
TICKER_RX = re.compile(r"\(([A-Z0-9]{3,6})\)")
BASLANGIC_RX = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s+TARIHLI\s+ISLEMLER\w*\s+BASLAMAK")
SURE_RX = re.compile(r"(\d{1,2})\s+AY\s+SURE")
UZAT_RX = re.compile(r"UZATILMASINA KARAR")
DOLACAK_RX = re.compile(r"DOLACAGI TARIHTEN\s*\((\d{1,2})\.(\d{1,2})\.(\d{4})")
MADDE_RX = re.compile(r"107/([12])|107 NCI MADDESININ (BIRINCI|IKINCI)")

SPAN_AZAMI = 1100            # anahtardan geriye bakilan azami karakter (giris basina; sinir: onceki giris sonu)
GERI_BAKIS_ILERI = 1800      # yasak tarihleri anahtardan sonra bu kadar karakter icinde aranir


def ay_ekle(d: date, ay: int) -> date:
    y = d.year + (d.month - 1 + ay) // 12
    m = (d.month - 1 + ay) % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _hizala(metin: str):
    duz = re.sub(r"\s+", " ", metin or "")
    n = tr_harf_norm(duz).replace("̇", "")
    if len(n) != len(duz):                       # savunma: hizalama bozulursa normallestirilmis ile devam
        n = tr_harf_norm(duz)
        duz = n
    return duz, n


def _alinti(duz: str, bas: int, son: int, azami: int = 240) -> str:
    s = duz[max(0, bas):son].strip()
    return s[-azami:] if len(s) > azami else s


def _giris_ticker(n: str, anahtar_bas: int, bist: set, yakinlik: int = None) -> list:
    """Anahtardan geriye, ayni girisin konusu olan BIST tickerlari (onceki girisin sonundan sonrasi)."""
    on = n[max(0, anahtar_bas - SPAN_AZAMI):anahtar_bas]
    kes = max((m.end() for m in SINIR_RX.finditer(on)), default=0)
    blok_bas = max(0, anahtar_bas - SPAN_AZAMI) + kes
    blok = n[blok_bas:anahtar_bas]
    sonuc = []
    for m in TICKER_RX.finditer(blok):
        tk = m.group(1)
        if tk not in bist:
            continue
        if "IDARI PARA" in blok[m.end():]:           # bu giris degil, idari para cezasi satiri
            continue
        if yakinlik is not None and anahtar_bas - (blok_bas + m.start()) > yakinlik:
            continue
        if tk not in sonuc:
            sonuc.append(tk)
    return sonuc


def _madde(n: str, tk: str, anahtar_bas: int) -> str:
    """Suc duyurusu maddesi (107/1 islem, 107/2 bilgi bazli): bilgi amaclidir. Girisin KENDI hissesinin
    gectigi yerden (onceki girisin tablosuna bakmamak icin) anahtardan 400 karakter sonrasina kadar ilk 107 ifadesi."""
    bas = n.rfind("(" + tk + ")", 0, anahtar_bas)
    m = MADDE_RX.search(n[max(bas, 0):anahtar_bas + 400])
    if not m:
        return ""
    return "107/" + (m.group(1) or ("1" if m.group(2) == "BIRINCI" else "2"))


def kayitlari_cikar(metin: str, bist: set, bulten_no: str, bulten_tarihi: date, url: str = "") -> list:
    """Bir bultenin metninden hisse kayitlari:
    {'ticker','tur','bulten','bulten_tarihi','url','madde','baslangic','bitis','tahmini','alinti'}."""
    duz, n = _hizala(metin)
    sonuc, gorulen = [], set()
    for m in SUC_RX.finditer(n):
        for tk in _giris_ticker(n, m.start(), bist):
            if (tk, TUR_SUC) in gorulen:
                continue
            gorulen.add((tk, TUR_SUC))
            sonuc.append({"ticker": tk, "tur": TUR_SUC, "bulten": bulten_no, "bulten_tarihi": bulten_tarihi,
                          "url": url, "madde": _madde(n, tk, m.start()),
                          "baslangic": None, "bitis": None, "tahmini": False,
                          "alinti": _alinti(duz, m.start() - 200, m.end() + 20)})
    for m in YASAK_RX.finditer(n):
        tickerlar = _giris_ticker(n, m.start(), bist)
        if not tickerlar:
            continue
        ileri = n[m.start():m.start() + GERI_BAKIS_ILERI]
        # Giris sonu: sonraki "KARAR VERILMISTIR" (tarih/sure o cumlede); sonraki girise TASMASIN
        bit = SINIR_RX.search(ileri, 40)
        cumle = ileri[:bit.end()] if bit else ileri
        b, s = BASLANGIC_RX.search(cumle), SURE_RX.search(cumle)
        ay = int(s.group(1)) if s else 6
        try:
            baslangic = date(int(b.group(3)), int(b.group(2)), int(b.group(1))) if b else None
        except ValueError:
            baslangic = None
        tahmini = baslangic is None
        if baslangic is None:
            baslangic = bulten_tarihi + timedelta(days=1)       # tarih bulunamazsa: bulten ertesi gunu (TAHMINI)
        bitis = ay_ekle(baslangic, ay)
        for tk in tickerlar:
            if (tk, TUR_YASAK, bulten_no) in gorulen:
                continue
            gorulen.add((tk, TUR_YASAK, bulten_no))
            sonuc.append({"ticker": tk, "tur": TUR_YASAK, "bulten": bulten_no, "bulten_tarihi": bulten_tarihi,
                          "url": url, "madde": "", "baslangic": baslangic, "bitis": bitis, "tahmini": tahmini,
                          "alinti": _alinti(duz, m.start() - 220, m.end() + 20)})
    # Yasak SURESI UZATMA kararlari ("... yasak suresinin dolacagi tarihten baslamak uzere 6 ay sureyle uzatilmasina
    # karar verilmistir"). Baslangic tarihi bazen yazili (08.05.2022 gun sonu), bazen yok -> plan_olustur
    # onceki yasagin bitisine ekler.
    for m in UZAT_RX.finditer(n):
        if "ISLEM YA" not in n[max(0, m.start() - 500):m.start()] or "YASAG" not in n[max(0, m.start() - 500):m.start()]:
            continue
        pencere = n[max(0, m.start() - 260):m.start() + 20]
        s_ = SURE_RX.search(pencere)
        ay = int(s_.group(1)) if s_ else 6
        d = DOLACAK_RX.search(n[max(0, m.start() - 500):m.start()])
        try:
            baslangic = date(int(d.group(3)), int(d.group(2)), int(d.group(1))) if d else None
        except ValueError:
            baslangic = None
        for tk in _giris_ticker(n, m.start(), bist):
            if (tk, TUR_YASAK, bulten_no) in gorulen:
                continue
            gorulen.add((tk, TUR_YASAK, bulten_no))
            sonuc.append({"ticker": tk, "tur": TUR_YASAK, "bulten": bulten_no, "bulten_tarihi": bulten_tarihi,
                          "url": url, "madde": "", "baslangic": baslangic, "bitis": ay_ekle(baslangic, ay) if baslangic else None,
                          "tahmini": baslangic is None, "uzatma": True, "uzatma_ay": ay,
                          "alinti": _alinti(duz, m.start() - 240, m.end() + 20)})
    return sonuc


def _uzatmalari_coz(kayitlar: list, mevcut: dict) -> list:
    """Baslangici yazili olmayan UZATMA kayitlarinin bitisini hesaplar: ayni hissenin ONCEKI yasak bitisi
    (kayitlardan, yoksa aktif kuralin bitis_tarihi) + uzatma suresi. Onceki yasak yoksa bulten tarihi + sure (TAHMINI)."""
    cikti = []
    for k in sorted(kayitlar, key=lambda x: (x["ticker"], x["bulten_tarihi"])):
        if k.get("uzatma") and k["bitis"] is None:
            onceki = [x["bitis"] for x in kayitlar if x["ticker"] == k["ticker"] and x["tur"] == TUR_YASAK
                      and x["bitis"] is not None and x["bulten_tarihi"] < k["bulten_tarihi"]]
            m = (mevcut or {}).get(k["ticker"])
            if m and m.get("aktif") and _gun(m.get("bitis_tarihi")):
                onceki.append(_gun(m["bitis_tarihi"]))
            temel = max(onceki) if onceki else k["bulten_tarihi"]
            k = {**k, "bitis": ay_ekle(temel, k["uzatma_ay"]), "tahmini": not onceki}
        cikti.append(k)
    return cikti


# ════════════════════════════════════════════════════════════════════════════════════════
# Karar: kayitlar + mevcut kurallar -> eylem plani
# ════════════════════════════════════════════════════════════════════════════════════════
def _gun(x):
    if x is None:
        return None
    if isinstance(x, datetime):
        return x.date()
    return x


def _kaynak_metni(k: dict) -> str:
    """Kullaniciya gosterilen kaynak ifadesi (detay seridinde parantez icinde cikar)."""
    t = k["bulten_tarihi"].strftime("%d.%m.%Y")
    if k["tur"] == TUR_YASAK:
        return (f"SPK Bülteni {k['bulten']} ({t}); kişilere geçici işlem yasağı "
                f"{k['bitis'].strftime('%d.%m.%Y')} tarihine kadar")
    return f"SPK Bülteni {k['bulten']} ({t}); piyasa dolandırıcılığı suç duyurusu"


def plan_olustur(kayitlar: list, mevcut: dict, bugun: date, baska_kategori: set = None) -> list:
    """Kayitlardan uygulanacak EYLEMLER. `mevcut`: {TICKER: {'aktif','tedbir_turu','bitis_tarihi',
    'kaldirilma_tarihi'}} (piyasa_tedbir_listesi, TICKER kurallari). `baska_kategori`: BIST disinda ayni koda
    sahip varlik kodlari (TICKER kurali kategoriye bakmaz; cakisma varsa yazilmaz).
    Eylem: {'islem': 'YAZ'|'ATLA', 'neden', 'ticker', 'tur', 'tedbir_turu', 'bitis', 'kayit', 'kaynak_aciklama'}.
    Ilkeler:
      * Bitmis yasak yazilmaz (skor etkisi yok).
      * Ayni hisse: kalici kural (suc/kapatma) yasaktan SIKIDIR; yasak kalici kurali ezmez, suc yasak kuralini yukseltir.
      * Kullanici/onay penceresiyle KALDIRILMIS kural, kaldirmadan SONRAKI bir bulten yoksa yeniden acilmaz.
    """
    baska_kategori = baska_kategori or set()
    en_iyi = {}
    for k in _uzatmalari_coz(kayitlar, mevcut):
        a = en_iyi.get((k["ticker"], k["tur"]))
        if a is None:
            en_iyi[(k["ticker"], k["tur"])] = k
        elif k["tur"] == TUR_YASAK:
            if k["bitis"] > a["bitis"]:
                en_iyi[(k["ticker"], k["tur"])] = k
        elif k["bulten_tarihi"] > a["bulten_tarihi"]:
            en_iyi[(k["ticker"], k["tur"])] = k
    plan = []
    mevcut = dict(mevcut or {})        # plan icinde yazilanlar da sonraki kararlara yansir (suc, ayni hissenin yasagini ezer)
    for (tk, tur), k in sorted(en_iyi.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        tedbir = TEDBIR_SUC if tur == TUR_SUC else TEDBIR_YASAK
        bitis = None if tur == TUR_SUC else k["bitis"]
        eylem = {"islem": "ATLA", "neden": "", "ticker": tk, "tur": tur, "tedbir_turu": tedbir,
                 "bitis": bitis, "kayit": k, "kaynak_aciklama": _kaynak_metni(k)}
        if tk in baska_kategori:
            eylem["neden"] = "ayni kod baska kategoride de var (yanlis eslesme riski)"
        elif tur == TUR_YASAK and bitis <= bugun:
            eylem["neden"] = "yasak suresi dolmus"
        else:
            m = mevcut.get(tk)
            if m and m.get("aktif"):
                m_bitis, m_tur = _gun(m.get("bitis_tarihi")), m.get("tedbir_turu")
                kalici = m_bitis is None
                if tur == TUR_SUC and kalici and m_tur in KALICI_TURLER:
                    eylem["neden"] = "zaten kalici kural var"
                elif tur == TUR_YASAK and kalici and m_tur in KALICI_TURLER:
                    eylem["neden"] = "daha siki kalici kural var"
                elif tur == TUR_YASAK and not kalici and m_bitis >= bitis:
                    eylem["neden"] = "ayni veya daha uzun yasak kurali var"
                else:
                    eylem["islem"], eylem["neden"] = "YAZ", "mevcut gecici kural yukseltiliyor/uzatiliyor"
            elif m and not m.get("aktif") and m.get("kaldirilma_tarihi") is not None \
                    and k["bulten_tarihi"] <= _gun(m["kaldirilma_tarihi"]):
                eylem["neden"] = "kural bu bultenden SONRA elle/onayla kaldirilmis"
            else:
                eylem["islem"], eylem["neden"] = "YAZ", "yeni kural"
        if eylem["islem"] == "YAZ":
            mevcut[tk] = {"aktif": True, "tedbir_turu": tedbir, "bitis_tarihi": bitis, "kaldirilma_tarihi": None}
        plan.append(eylem)
    return plan


def evren_bist(df) -> tuple:
    """(bist_tickerlari, baska_kategoride_ayni_kod) - optimized_universe DataFrame'inden."""
    kat = df["Kategori"].astype(str)
    tk = df["Ticker"].astype(str).str.upper()
    bist = set(tk[kat == "BIST"])
    baska = set(tk[kat != "BIST"]) & bist
    return bist, baska
