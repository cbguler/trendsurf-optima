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

# ─── KAP SLUG HARİTASI ─────────────────────────────────────
# worker.py ile uyumlu — en sık kullanılan 100 şirket
KAP_SLUG_MAP = {
    "THYAO":"1107-turk-hava-yollari-a-o","GARAN":"2422-turkiye-garanti-bankasi-a-s",
    "ISCTR":"2425-turkiye-is-bankasi-a-s","AKBNK":"2413-akbank-t-a-s",
    "YKBNK":"2429-yapi-ve-kredi-bankasi-a-s","SISE":"1087-turkiye-sise-ve-cam-fabrikalari-a-s",
    "KCHOL":"1005-koc-holding-a-s","SAHOL":"976-haci-omer-sabanci-holding-a-s",
    "TUPRS":"1105-tupras-turkiye-petrol-rafinerileri-a-s",
    "EREGL":"944-eregli-demir-ve-celik-fabrikalari-t-a-s",
    "FROTO":"956-ford-otomotiv-sanayi-a-s","TOASO":"1096-tofas-turk-otomobil-fabrikasi-a-s",
    "BIMAS":"1406-bim-birlesik-magazalar-a-s","ARCLK":"863-arcelik-a-s",
    "ASELS":"866-aselsan-elektronik-sanayi-ve-ticaret-a-s",
    "TAVHL":"1452-tav-havalimanlari-holding-a-s",
    "EKGYO":"1531-emlak-konut-gayrimenkul-yatirim-ortakligi-a-s",
    "ENKAI":"942-enka-insaat-ve-sanayi-a-s","TKFEN":"1470-tekfen-holding-a-s",
    "PGSUS":"1710-pegasus-hava-tasimaciligi-a-s",
    "TCELL":"1103-turkcell-iletisim-hizmetleri-a-s",
    "TTKOM":"1473-turk-telekomunikasyon-a-s","PETKM":"1053-petkim-petrokimya-holding-a-s",
    "AKSEN":"1505-aksa-enerji-uretim-a-s",
    "GUBRF":"974-gubre-fabrikalari-t-a-s","CCOLA":"1424-coca-cola-icecek-a-s",
    "AEFES":"858-anadolu-efes-biracilik-ve-malt-sanayii-a-s",
    "ULKER":"859-ulker-biskuvi-sanayi-a-s","TATGD":"1091-tat-gida-sanayi-a-s",
    "DOAS":"1391-dogus-otomotiv-servis-ve-ticaret-a-s",
    "MGROS":"1494-migros-ticaret-a-s","SOKM":"3913-sok-marketler-ticaret-a-s",
    "LOGO":"1016-logo-yazilim-sanayi-ve-ticaret-a-s",
    "OTKAR":"1046-otokar-otomotiv-ve-savunma-sanayi-a-s",
    "BRISA":"891-brisa-bridgestone-sabanci-lastik-sanayi-ve-ticaret-a-s",
    "SARKY":"1067-sarkuysan-elektrolitik-bakir-sanayi-ve-ticaret-a-s",
    "SASA":"1068-sasa-polyester-sanayi-a-s",
    "VESTL":"1122-vestel-elektronik-sanayi-ve-ticaret-a-s",
    "VESBE":"1419-vestel-beyaz-esya-sanayi-ve-ticaret-a-s",
    "DOHOL":"919-dogan-sirketler-grubu-holding-a-s",
    "HALKB":"2423-turkiye-halk-bankasi-a-s","VAKBN":"2428-turkiye-vakiflar-bankasi-t-a-o",
    "TSKB":"2427-turkiye-sinai-kalkinma-bankasi-a-s",
    "ALBRK":"2414-albaraka-turk-katilim-bankasi-a-s",
    "ZOREN":"1133-zorlu-enerji-elektrik-uretim-a-s","AYGAZ":"873-aygaz-a-s",
    "TRGYO":"1524-torunlar-gayrimenkul-yatirim-ortakligi-a-s",
    "ISGYO":"987-is-gayrimenkul-yatirim-ortakligi-a-s",
    "MAVI":"3843-mavi-giyim-sanayi-ve-ticaret-a-s",
    "DESA":"1389-desa-deri-sanayi-ve-ticaret-a-s",
    "NUHCM":"1042-nuh-cimento-sanayi-a-s","CIMSA":"908-cimsa-cimento-sanayi-ve-ticaret-a-s",
    "AKCNS":"838-akcansa-cimento-sanayi-ve-ticaret-a-s",
    "ISDMR":"2528-iskenderun-demir-ve-celik-a-s",
    "KRDMD":"994-kardemir-karabuk-demir-celik-sanayi-ve-ticaret-a-s",
    "EGEEN":"930-ege-endustri-ve-ticaret-a-s",
    "CLEBI":"903-celebi-hava-servisi-a-s",
    "MPARK":"2118-mlp-saglik-hizmetleri-a-s",
    "ANSGR":"856-anadolu-anonim-turk-sigorta-sirketi",
    "ANHYT":"860-anadolu-hayat-emeklilik-a-s",
    "TTRAK":"1393-turk-traktor-ve-ziraat-makineleri-a-s",
    "KORDS":"1009-kordsa-teknik-tekstil-a-s",
    "INDES":"1390-indeks-bilgisayar-sistemleri-muhendislik-sanayi-ve-ticaret-a-s",
    "NETAS":"1041-netas-telekomunikasyon-a-s",
    # v2.0.7.66 - Bahri'nin bulgusu uzerine dogrulandi (web_fetch ile
    # gercek KAP sayfasindan teyit edildi, 15 Temmuz 2026):
    "AHGAZ":"3064-ahlatci-dogal-gaz-dagitim-enerji-ve-yatirim-a-s",
}

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
    slug = KAP_SLUG_MAP.get(ticker.upper())
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
            try:
                tablolar = _pd.read_html(_io.StringIO(r.text), flavor="lxml")
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
    for df in tablolar:
        if df.shape[1] < 2:
            continue
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
                    result[alan] = deger
                    break


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
    if ticker in KAP_SLUG_MAP:
        kap_data = _fetch_kap(ticker)
        result.update(kap_data)
    else:
        result["_kap_available"] = False
        result["_kap_note"] = "Veri kaynağı: yfinance"

    return result


def fundamentals_to_display(raw: dict) -> dict:
    """Ham veriyi ekrana uygun formata çevirir — Türkçe etiketler."""

    # yfinance verileri
    yf = {
        "Piyasa Değeri":        _fmt_mil(raw.get("market_cap")),
        "F/K Oranı (İz. 12A)":  _fmt_ratio(raw.get("pe_ratio")),
        "İleriye Dön. F/K":     _fmt_ratio(raw.get("forward_pe")),
        "PD/DD Oranı":          _fmt_ratio(raw.get("pb_ratio")),
        "Hisse Başı Kazanç":    _fmt_ratio(raw.get("eps"), " ₺"),
        "Ciro (Yıllık)":        _fmt_mil(raw.get("revenue")),
        "Net Kâr":              _fmt_mil(raw.get("net_income")),
        "FAVÖK":                _fmt_mil(raw.get("ebitda")),
        "Faaliyet Marjı":       _fmt_pct(raw.get("op_margin")),
        "Net Kâr Marjı":        _fmt_pct(raw.get("net_margin")),
        "Özkaynak (Defter)":    _fmt_ratio(raw.get("equity"), " ₺/hisse"),
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
    for field, (label, unit) in kap_fields.items():
        if raw.get(field) is not None:
            yf[label] = _fmt_mil(raw[field])

    # KAP durumu
    # v2.0.7.50 - DUZELTME: "_kap_note" alani duz "Veri kaynağı: yfinance"
    # metniydi - "KAP Durumu" satirinin ETIKETIYLE uyumsuzdu (etiket KAP'in
    # durumunu soruyor, icerik yfinance'ten bahsediyordu). Artik etiketle
    # tutarli, acik bir ifade kullaniliyor.
    if not raw.get("_kap_available", True):
        yf["KAP Durumu"] = "Bilanço verisi bulunamadı (yfinance kullanılıyor)"

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
    slug = KAP_SLUG_MAP.get(ticker.upper())
    if slug:
        return f"https://kap.org.tr/tr/sirket-finansal-bilgileri/{slug}"
    return None