"""
live_data.py - TrendSurf Optima v1.6+
=====================================
Borsapy tabanli canli veri katmani.

Birincil kaynak: borsapy 0.10+ (canlidoviz.com, BtcTurk, TradingView)
Yedek           : mevcut yfinance / Bigpara / TCMB modulleri (cagri disi)

Bu modul mevcut clientlari (bigpara_client, tcmb_client, tefas_client)
DEGISTIRMEZ. Sadece "once borsapy dene, basarisizsa CSV/yfinance kullan"
mantigini bir katman yukaridan ekler.

Borsapy kurulu degilse modul sessizce devre disi olur ve mevcut akis
hicbir degisiklik olmadan calismaya devam eder.

Lisans notu: borsapy "kisisel ve egitim amacli" kullanim icin lisanslidir.
Bu proje (TrendSurf Optima) kullanici tarafindan kisisel + aile aboneligi
icin gelistirilmistir, ticari kullanim soz konusu degildir.
"""

import streamlit as st
import pandas as pd
import time as _time

# ----------------------------------------------------------------------------
# v1.9.3 — PROFILLEME ARACI
# ----------------------------------------------------------------------------
# Her ana fonksiyon kendi son cagri suresini buraya yazar. Streamlit
# admin tanilama panelinden okunur. Sandboxa veya production'a ek bir
# bagimlilik yok; sadece dict + time.perf_counter.
_TIMINGS: dict = {}


def get_timings() -> dict:
    """Son cagrilarin sureleri (saniye). v1.9.3+ tanilama icin."""
    return dict(_TIMINGS)


def reset_timings() -> None:
    """Tanilama panelinden manuel temizleme icin."""
    _TIMINGS.clear()


def _timed_block(name: str):
    """Context manager - 'with _timed_block(\"refresh_bist\"):' kullanim."""
    class _T:
        def __enter__(self_):
            self_.t0 = _time.perf_counter()
            return self_
        def __exit__(self_, *exc):
            _TIMINGS[name] = _time.perf_counter() - self_.t0
            # Streamlit Cloud Logs'a da yansisin
            try:
                print(f"[timing] {name}: {_TIMINGS[name]:.3f}s")
            except Exception:
                pass
            return False
    return _T()


# ----------------------------------------------------------------------------
# Borsapy guvenli import
# ----------------------------------------------------------------------------
try:
    import borsapy as bp
    BORSAPY_OK = True
    BORSAPY_ERROR = None
    BORSAPY_VERSION = getattr(bp, "__version__", "0.10+")
except Exception as e:
    bp = None
    BORSAPY_OK = False
    BORSAPY_ERROR = str(e)
    BORSAPY_VERSION = None


# ----------------------------------------------------------------------------
# Sistemde takip edilmeyen varliklar (filter_universe ile evrenden cikariliyor)
# ----------------------------------------------------------------------------
# 1) USD bazli emtia filtresi (kullanici karari, 19-20 Haziran 2026 - VIII oturum)
#    Tarim emtialari ve enerji (Brent/WTI/Dogalgaz) Turkiye'de fiziki olarak
#    alinip-satilamayan, dunya borsalarinda USD ile fiyatlanan turetilmis
#    varliklardir; portfoye eklenebilir nitelikte degiller.
#
#    Paladyum ve Bakir geri eklendi: USD bazli olsa da degerli/endustriyel metal
#    olarak yatirim sayilabilir; worker.py CSV'ye yfinance ile yaziyor (× USDTRY).
#
# 2) v1.9.10 - Guvenilir TL fiyat kaynagi olmayan varliklar (27 Haziran 2026 - X oturum)
#    - ONS_ALTIN_TRY: canlidoviz.com "ons-altin" endpoint'i USD veriyor olabilir;
#      bu nedenle CSV ve UI'da gercek TL fiyatin yaklasik 1/47'si goruluyordu
#      (~106k TL gosterirken gercek ~188k TL/ons). Cozum: tamamen cikar.
#      Yatirimci ihtiyac duyarsa: gram altin × 31.1035 ile manuel hesap yapabilir.
#    - BNB: BtcTurk borsasinda BNB/TRY paritesi YOK (regulatif sebep, BtcTurk
#      Binance'in rakibi). borsapy.Crypto("BNBTRY") 404 doner, CSV'deki USD
#      fiyat TL etiketiyle gosteriliyordu (603 gorulurken gercek ~26.300 TL).
#      Cozum: tamamen cikar. Diger kriptolar (BTC, ETH, SOL, XRP, AVAX, vb.)
#      BtcTurk'ta TRY pariteleri var, dogru calismaya devam ediyor.
# ----------------------------------------------------------------------------
EXCLUDED_USD_COMMODITIES = {
    # USD bazli emtialar
    "BRENT_TRY", "PETROL_TRY", "DOGALGAZ_TRY",
    "BUGDAY_TRY", "MISIR_TRY", "SOYA_TRY", "KAKAO_TRY",
    # v1.9.10 - Guvenilir TL fiyat kaynagi olmayan varliklar
    "ONS_ALTIN_TRY",   # canlidoviz endpoint'i USD veriyor (~1/47 gosteriyordu)
    "BNB",             # BtcTurk'ta BNB/TRY paritesi yok (~1/44 gosteriyordu)
    # v2.0.7.38 - Bahri BtcTurk'un 185 TRY paritesini tek tek kontrol etti
    # (13 Temmuz): ICP/TRY YOK. BNB ile ayni durum - gecmis USD verisi
    # (yfinance) var ama gercek TL islem fiyati yok; sentetik USD*kur
    # cevrimi Bahri'nin temel ilkesi geregi YASAK. Fiyatsiz gorunmesindense
    # evrenden cikarilir.
    "ICP",             # BtcTurk'ta ICP/TRY paritesi yok (dogrulandi 13.07.2026)
}


# ----------------------------------------------------------------------------
# Ticker -> borsapy sembol esleme tablolari
# ----------------------------------------------------------------------------
# DOVIZ: "USDTRY" -> borsapy.FX("USD") (TRY zaten implicit)
_DOVIZ_TO_BP = {
    "USDTRY": "USD", "EURTRY": "EUR", "GBPTRY": "GBP",
    "JPYTRY": "JPY", "CHFTRY": "CHF", "AUDTRY": "AUD",
    "CADTRY": "CAD", "NZDTRY": "NZD", "NOKTRY": "NOK",
    "SEKTRY": "SEK", "DKKTRY": "DKK", "CNYTRY": "CNY",
    # v2.0.7.80 - KRITIK DUZELTME (Bahri'nin bulgusu, ZARTRY ornegi):
    # bu sozluk eskiden SADECE 12 ana dovizi taniyordu. 51 genisleme
    # dovizi (worker.py'de DOVIZ_GENISLEME) icin worker.py kendi
    # _canlidoviz_hesapla() fonksiyonuyla bp.FX(kod).history() ile GERCEK
    # tarihsel veri alabiliyordu (Harem'e ihtiyac yok - MADEN'deki 9
    # metal gibi dogrudan canlidoviz endpoint'i), ama Detay sayfasinin
    # kendi get_fx_history() fonksiyonu bu kodlari hic bilmedigi icin
    # dogrudan bp.FX(...) denemeden, guvenilmez tek-sembol yfinance
    # sorgusuna (\"ZARTRY=X\" gibi) dusuyordu - "gecmis fiyat verisi
    # yuklenemedi" hatasi ve bos MA/DD tablosunun sebebi buydu. Kodlar
    # worker.py'deki _DOVIZ_TRUNCGIL_KOD ile BIREBIR AYNI (tek kaynak).
    "RUBTRY": "RUB", "AEDTRY": "AED", "KWDTRY": "KWD", "ZARTRY": "ZAR",
    "BHDTRY": "BHD", "LYDTRY": "LYD", "SARTRY": "SAR", "IQDTRY": "IQD",
    "ILSTRY": "ILS", "INRTRY": "INR", "MXNTRY": "MXN", "HUFTRY": "HUF",
    "BRLTRY": "BRL", "IDRTRY": "IDR", "CZKTRY": "CZK", "PLNTRY": "PLN",
    "RONTRY": "RON", "ARSTRY": "ARS", "ALLTRY": "ALL", "AZNTRY": "AZN",
    "BAMTRY": "BAM", "CLPTRY": "CLP", "COPTRY": "COP", "CRCTRY": "CRC",
    "DZDTRY": "DZD", "EGPTRY": "EGP", "HKDTRY": "HKD", "ISKTRY": "ISK",
    "KRWTRY": "KRW", "KZTTRY": "KZT", "LBPTRY": "LBP", "LKRTRY": "LKR",
    "MADTRY": "MAD", "MDLTRY": "MDL", "MKDTRY": "MKD", "MYRTRY": "MYR",
    "OMRTRY": "OMR", "PENTRY": "PEN", "PHPTRY": "PHP", "PKRTRY": "PKR",
    "QARTRY": "QAR", "RSDTRY": "RSD", "SGDTRY": "SGD", "SYPTRY": "SYP",
    "THBTRY": "THB", "TWDTRY": "TWD", "UAHTRY": "UAH", "UYUTRY": "UYU",
    "GELTRY": "GEL", "TNDTRY": "TND", "BGNTRY": "BGN",
}

# MADEN: TRY-direkt gram bazli kiymetli madenler + sikke altinlar
# (canlidoviz.com'dan gercek zamanli TL fiyat)
# v1.9.10 - ONS_ALTIN_TRY cikarildi (canlidoviz endpoint'i guvenilir TL vermiyor)
_MADEN_TO_BP = {
    "ALTIN_TRY":      "gram-altin",
    "GUMUS_TRY":      "gram-gumus",
    "PLATIN_TRY":     "gram-platin",
    # v1.6.1 - sikke altinlar (Turk yatirimcisinin yaygin tuttugu fiziki ureunler)
    "CEYREK_ALTIN":   "ceyrek-altin",
    "YARIM_ALTIN":    "yarim-altin",
    "TAM_ALTIN":      "tam-altin",
    "CUMHURIYET_ALTIN": "cumhuriyet-altin",
    "ATA_ALTIN":      "ata-altin",
}

# Yeni sikke varliklarinin gosterim isimleri (CSV'deki "Ad" sutununa karsilik gelir)
# v1.9.10 - ONS_ALTIN_TRY display'den cikarildi
_NEW_MADEN_DISPLAY = {
    "CEYREK_ALTIN":     "Çeyrek Altın",
    "YARIM_ALTIN":      "Yarım Altın",
    "TAM_ALTIN":        "Tam Altın",
    "CUMHURIYET_ALTIN": "Cumhuriyet Altını",
    "ATA_ALTIN":        "Ata Altını",
}

# Mevcut ALTIN_TRY adini gunceller: "Altin (TL)" yerine "Gram Altın" diye gosterilir
_MADEN_AD_GUNCELLE = {
    "ALTIN_TRY":  "Gram Altın",
    "GUMUS_TRY":  "Gram Gümüş",
    "PLATIN_TRY": "Gram Platin",
}

# v2.0.7.39 - 185+ kriptoya genisleme: worker.py artik BtcTurk'teki TUM
# TRY paritelerini dinamik cekiyor, BIST ile cakisanlari (LINK->CLINK
# ornegindeki gibi) "C" onekiyle yeniden adlandirip esap kripto_parite_
# map.json dosyasina yaziyor. Burada o dosya okunur - boylece "C" ile
# baslayan GERCEK sembolleri (CHZ, COTI gibi) yanlislikla cakisma sanip
# kirpma riski olmadan, SADECE worker.py'nin tespit ettigi gercek
# cakismalar dogru sekilde cozulur. Dosya yoksa/okunamazsa (ilk kurulum,
# worker henuz hic calismadi) CLINK icin eski bilinen esleme yedek olarak
# kullanilir, boylece gecici bir bozulma olmaz.
def _kripto_parite_haritasi_yukle() -> dict:
    try:
        import json as _json_lp
        with open("kripto_parite_map.json", encoding="utf-8") as f:
            return _json_lp.load(f)
    except Exception:
        return {"CLINK": "LINKTRY"}  # worker henuz hic calismadiysa yedek


_KRIPTO_PARITE_MAP = _kripto_parite_haritasi_yukle()


# KRIPTO: BTC -> "BTCTRY", ETH -> "ETHTRY" (BtcTurk borsasindan TRY cifti)
def _kripto_bp_code(ticker: str) -> str:
    t = ticker.upper().strip()
    if t in _KRIPTO_PARITE_MAP:
        return _KRIPTO_PARITE_MAP[t]
    if t.endswith("TRY"):
        return t
    return f"{t}TRY"


# canlidoviz.com Japon Yen'ini "100 Japon Yeni" basina TL olarak yayinliyor
# (borsapy source: _providers/canlidoviz.py satir 40 yorumu: '100 Japon Yeni').
# Bizim CSV ve UI 'per 1 yen' kullaniyor (0.2870 TL/yen gibi). Bu yuzden
# JPYTRY icin borsapy degerini 100'e bolmemiz gerekiyor. Diger 64 para
# birimi per-1 oldugu icin sadece JPY ozel davranis ister.
_PER_N_UNITS = {
    "JPYTRY": 100.0,
}


def _normalize_fx_price(ticker: str, price: float) -> float:
    """canlidoviz.com'un 'per N birim' konvansiyonunu CSV/UI 'per 1' formatina cevir."""
    if price is None:
        return None
    divisor = _PER_N_UNITS.get(ticker.upper())
    if divisor and divisor != 1.0:
        return float(price) / divisor
    return float(price)


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------
def filter_universe(df: pd.DataFrame) -> pd.DataFrame:
    """USD bazli emtialari (Brent/WTI/Bugday vb.) varlik evreninden cikar."""
    if df is None or df.empty or "Ticker" not in df.columns:
        return df
    return df[~df["Ticker"].isin(EXCLUDED_USD_COMMODITIES)].reset_index(drop=True)


def rename_existing_maden(df: pd.DataFrame) -> pd.DataFrame:
    """Mevcut MADEN satirlarinin gosterim adlarini netlestir.

    Eski CSV: ALTIN_TRY -> "Altin (TL)"  (yaniltici, hangi altin belli degil)
    Yeni:                  "Gram Altın"  (net)
    """
    if df is None or df.empty or "Ad" not in df.columns:
        return df
    for ticker, yeni_ad in _MADEN_AD_GUNCELLE.items():
        mask = df["Ticker"] == ticker
        if mask.any():
            df.loc[mask, "Ad"] = yeni_ad
    return df


def _compute_rsi(closes: pd.Series, period: int = 14) -> float:
    """Klasik Wilder RSI hesabi - history'den son 14+ kapanis fiyatiyla."""
    try:
        if closes is None or len(closes) < period + 1:
            return 50.0
        delta = closes.diff().dropna()
        gain = delta.clip(lower=0).rolling(window=period, min_periods=period).mean()
        loss = -delta.clip(upper=0).rolling(window=period, min_periods=period).mean()
        if loss.iloc[-1] == 0:
            return 100.0
        rs = gain.iloc[-1] / loss.iloc[-1]
        rsi = 100.0 - (100.0 / (1.0 + rs))
        if pd.isna(rsi):
            return 50.0
        return float(round(rsi, 1))
    except Exception:
        return 50.0


def _compute_ret_1m(closes: pd.Series) -> float:
    """1 ay onceki kapanisa gore yuzdesel getiri (yaklasik 22 isgunu)."""
    try:
        if closes is None or len(closes) < 22:
            return 0.0
        son = float(closes.iloc[-1])
        ay_once = float(closes.iloc[max(0, len(closes) - 22)])
        if ay_once == 0 or pd.isna(son) or pd.isna(ay_once):
            return 0.0
        return float(round((son - ay_once) / ay_once * 100.0, 4))
    except Exception:
        return 0.0


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_maden_history_summary(bp_code: str) -> tuple:
    """Bir madenin 1 aylik tarihcesinden anlik fiyat, RSI, Ret1M dondur.

    Returns: (son_fiyat, rsi, ret1m) - hata olursa (None, 50.0, 0.0)
    """
    if not BORSAPY_OK:
        return (None, 50.0, 0.0)
    try:
        h = bp.FX(bp_code).history(period="3mo", interval="1d")
        if h is None or h.empty:
            print(f"  [live_data] MADEN history BOS ({bp_code}) - CSV degeri korunacak")
            return (None, 50.0, 0.0)
        # Close sutununu bul
        col = None
        for c in ("Close", "close", "PRICE", "price"):
            if c in h.columns:
                col = c
                break
        if col is None:
            print(f"  [live_data] MADEN history Close sutunu yok ({bp_code}), kolonlar: {list(h.columns)}")
            return (None, 50.0, 0.0)
        closes = pd.to_numeric(h[col], errors="coerce").dropna()
        if closes.empty:
            return (None, 50.0, 0.0)
        son = float(closes.iloc[-1])
        rsi = _compute_rsi(closes)
        ret = _compute_ret_1m(closes)
        print(f"  [live_data] MADEN history OK ({bp_code}): son={son}, son_veri_tarihi={h.index[-1] if hasattr(h,'index') else '?'}")
        return (son, rsi, ret)
    except Exception as e:
        # v2.0.4.47: Daha once tamamen sessizdi - artik logluyoruz.
        print(f"  [live_data] MADEN history hatasi ({bp_code}): {type(e).__name__}: {e}")
        return (None, 50.0, 0.0)


def extend_maden_universe(df: pd.DataFrame) -> pd.DataFrame:
    """Mevcut CSV'de olmayan yeni MADEN sikkelerini DataFrame'e satir olarak ekler.

    Eklenecek satirlar: ceyrek/yarim/tam/cumhuriyet/ata altin + ons-altin (TL).
    Her satir icin canli fiyat, RSI ve Ret1M borsapy tarihçesinden hesaplanir.
    CSV dosyasi degismez, sadece bellekteki DataFrame genisletilir.
    """
    with _timed_block("extend_maden_universe"):
        if df is None or "Ticker" not in df.columns:
            return df

        yeni_satirlar = []
        for ticker, ad in _NEW_MADEN_DISPLAY.items():
            # CSV'de zaten varsa atla
            if (df["Ticker"] == ticker).any():
                continue
            bp_code = _MADEN_TO_BP.get(ticker)
            if not bp_code:
                continue
            son, rsi, ret1m = _fetch_maden_history_summary(bp_code)
            # Fiyat yoksa satiri ekleme (anlamsiz olur)
            if son is None or son <= 0:
                continue
            row = {
                "Ticker":     ticker,
                "Ad":         ad,
                "Kategori":   "MADEN",
                "TEFAS_Kind": "",
                "Tur":        "",
                "Risk_Deger": "",
                "Son_Fiyat":  float(son),
                "RSI":        float(rsi),
                "Ret1M":      float(ret1m),
                "Ret3M":      0.0,
                "Ret6M":      0.0,
                "Ret1Y":      0.0,
                "Ret3Y":      0.0,
                "Ret5Y":      0.0,
                "Vol":        25.0,
                "YF_Symbol":  "",
                "_tcmb_guncellendi": "",
                # v2.0.7.33 - KRITIK DUZELTME (Bahri'nin 12 Temmuz bulgusu):
                # Bu satirlar Optima_Skor'u hic yazmiyordu -> asagidaki
                # "df.columns'da olmayan sutunlari 0.0 ile doldur" adimi
                # bunu SESSIZCE 0.0 yapiyordu (NaN degil!). app.py'deki
                # canli skor tamamlama mantigi ise SADECE NaN olan
                # skorlari yeniden hesapliyor - 0.0 "zaten hesaplanmis
                # gecerli bir skor" sanilip hic dokunulmuyordu. Sonuc:
                # Ceyrek/Yarim/Tam/Cumhuriyet/Ata Altin HER ZAMAN
                # Optima Skor=0 gosteriyordu. Simdi acikca NaN yazilarak
                # app.py'nin optima_score(RSI,Ret1M,Vol) ile gercek bir
                # skor hesaplamasi saglaniyor.
                "Optima_Skor": float("nan"),
            }
            yeni_satirlar.append(row)

        if not yeni_satirlar:
            return df

        ek_df = pd.DataFrame(yeni_satirlar)
        # df'deki tum sutunlar varsa onlari kullan, eksikse default
        for c in df.columns:
            if c not in ek_df.columns:
                ek_df[c] = "" if df[c].dtype == object else 0.0
        ek_df = ek_df[df.columns]
        return pd.concat([df, ek_df], ignore_index=True)


@st.cache_data(ttl=300, show_spinner=False)
def get_harem_buy_prices() -> dict:
    """Portfoy degerleme icin Harem'in alis fiyatlari (kullanicinin satinca alacagi).

    Sadece 4 metal icin Harem-ozel verisi var: gram-altin, gram-gumus,
    gram-platin, ons-altin. Diger MADEN varliklarinda canlidoviz mid kullanilir.

    Returns: { ticker: buy_price_tl }   - hata olursa eksik anahtar
    """
    if not BORSAPY_OK:
        return {}
    out = {}
    HAREM_DESTEKLI = {
        "ALTIN_TRY":     "gram-altin",
        "GUMUS_TRY":     "gram-gumus",
        "PLATIN_TRY":    "gram-platin",
        # v1.9.10 - ONS_ALTIN_TRY cikarildi (universe'den de cikarildi)
    }
    for ticker, bp_code in HAREM_DESTEKLI.items():
        try:
            inst = bp.FX(bp_code).institution_rate("harem")
            if isinstance(inst, dict):
                buy = inst.get("buy")
                if buy is not None:
                    f = float(buy)
                    if f > 0:
                        out[ticker] = f
        except Exception:
            continue
    return out


def portfolio_value_prices(df: pd.DataFrame, tickers: list) -> dict:
    """Portfoy degerleme icin guncel piyasa fiyati.

    v1.8.2: Tek fiyat kaynagi - Son_Fiyat (canlidoviz mid).
    Onceden 4 metal icin Harem alis fiyati kullaniliyordu (v1.6.1) ama
    Madenler sayfasi piyasa fiyati gosterdigi icin kafa karistiriciydi.
    Artik her yerde ayni fiyat (Son_Fiyat) gosterilir.

    Returns: { ticker: price_tl } - her ticker icin Son_Fiyat
    """
    out = {}
    if df is None or df.empty or "Ticker" not in df.columns or "Son_Fiyat" not in df.columns:
        return out

    son_fiyat_map = dict(zip(df["Ticker"].astype(str),
                              pd.to_numeric(df["Son_Fiyat"], errors="coerce")))

    for t in tickers:
        t = str(t)
        v = son_fiyat_map.get(t)
        if v is not None and not pd.isna(v) and v > 0:
            out[t] = float(v)
    return out


def _safe_current(bp_obj) -> float | None:
    """borsapy nesnesinden anlik fiyati guvenli sekilde al.

    borsapy 0.10+ icin:
      - FX.current  -> dict {'symbol','last','open','high','low','update_time'}
      - Crypto.current -> dict {'symbol','last','open','high','low','bid','ask',...}
      - Ticker.fast_info -> dict (yfinance uyumlu)
    Hepsinde fiyat 'last' anahtarinda. Eski surumler veya degisiklikler icin
    bircok olasi anahtar denenir; hepsi bos ise history son satira duser.
    """
    # 1. .current ya da .info (dict beklenir)
    for attr in ("current", "info", "fast_info"):
        try:
            v = getattr(bp_obj, attr, None)
        except Exception:
            v = None
        if v is None:
            continue
        # Dict mi?
        if isinstance(v, dict):
            for key in ("last", "lastPrice", "last_price", "price",
                        "regularMarketPrice", "close", "Close",
                        "sell", "ask"):
                if key in v and v[key] is not None:
                    try:
                        f = float(v[key])
                        if f > 0:
                            return f
                    except (TypeError, ValueError):
                        continue
            continue  # Dict ama bilinen anahtar yok -> sonraki attr
        # Sayisal mi?
        try:
            f = float(v)
            if f > 0:
                return f
        except (TypeError, ValueError):
            continue
    # 2. Son care: history son satir
    try:
        h = bp_obj.history(period="5d", interval="1d")
        if h is not None and not h.empty:
            for col in ("Close", "close", "PRICE", "price"):
                if col in h.columns:
                    f = float(h[col].iloc[-1])
                    if f > 0:
                        return f
    except Exception:
        pass
    return None


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_live_fx_maden() -> dict:
    """borsapy'den DOVIZ, Truncgil'den MADEN anlik fiyatlari getir. 5 dk cache.

    v2.0.4.49: MADEN (ALTIN_TRY vb.) canli fiyat cekimi KALDIRILMISTI.
    Kanit: admin tanilama kutusuyla dogrulandi - CSV (Bigpara, worker.py
    tarafindan her gece guncelleniyor) 6252.5 gibi taze bir deger
    gosterirken, bu fonksiyonun borsapy uzerinden (canlidoviz.com'a
    dayanan) getirdigi "canli" deger gunlerdir sabit 6277.78'de donuk
    kaliyordu ve CSV'nin dogru degerinin uzerine yaziyordu.

    v2.0.4.58: MADEN GERI EKLENDI - bu sefer canlidoviz/borsapy DEGIL,
    Truncgil Finans (ucretsiz, yapilandirilmis JSON, gercek veriyle test
    edildi) kullaniliyor. Boylece Madenler de Doviz/Kripto gibi 5 dk'lik
    hizli katmanda, GitHub Actions'i beklemeden guncelleniyor.
    """
    out = {}

    try:
        from bigpara_client import fetch_truncgil_maden
        truncgil_maden = fetch_truncgil_maden()
        for ticker, v in truncgil_maden.items():
            out[ticker] = v
            print(f"  [live_data] MADEN canli fiyat OK ({ticker}/Truncgil): {v}")
        if not truncgil_maden:
            print("  [live_data] MADEN canli fiyat BOS (Truncgil) - CSV degeri korunacak")
    except Exception as e:
        print(f"  [live_data] MADEN canli fiyat hatasi (Truncgil): {type(e).__name__}: {e}")

    if not BORSAPY_OK:
        print("  [live_data] BORSAPY_OK=False, DOVIZ canli fiyat atlandi")
        return out
    for ticker, bp_code in _DOVIZ_TO_BP.items():
        try:
            v = _safe_current(bp.FX(bp_code))
            if v is not None:
                out[ticker] = _normalize_fx_price(ticker, v)
                print(f"  [live_data] DOVIZ canli fiyat OK ({ticker}/{bp_code}): {out[ticker]}")
            else:
                print(f"  [live_data] DOVIZ canli fiyat BOS/None ({ticker}/{bp_code}) - CSV degeri korunacak")
        except Exception as e:
            print(f"  [live_data] DOVIZ canli fiyat hatasi ({ticker}/{bp_code}): {type(e).__name__}: {e}")
            continue
    return out


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_live_kripto(tickers_key: tuple) -> dict:
    """borsapy'den kripto TRY fiyatlari getir. 5 dk cache."""
    if not BORSAPY_OK:
        print("  [live_data] BORSAPY_OK=False, KRIPTO canli fiyat atlandi")
        return {}
    out = {}
    for t in tickers_key:
        try:
            v = _safe_current(bp.Crypto(_kripto_bp_code(t)))
            if v is not None:
                out[t] = v
                print(f"  [live_data] KRIPTO canli fiyat OK ({t}): {v}")
            else:
                print(f"  [live_data] KRIPTO canli fiyat BOS/None ({t}) - CSV degeri korunacak")
        except Exception as e:
            print(f"  [live_data] KRIPTO canli fiyat hatasi ({t}): {type(e).__name__}: {e}")
            continue
    return out


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_live_bist(tickers_key: tuple) -> dict:
    """borsapy.download ile BIST hisselerinin son kapanis fiyatlarini batch cek.

    5 dk cache. BIST regulatif olarak 15 dakika gecikmeli yayinlandigi icin
    5 dk cache mantikli (canli ile aradaki en buyuk fark ~20 dk olur).

    Args:
        tickers_key: BIST ticker'larin tuple'i (cache key icin hashable olmali)

    Returns:
        {ticker: son_fiyat} dict. Hata olursa bos dict.

    v1.9.5: borsapy.download (sirali, 770 ticker icin 344s) yerine
            ThreadPoolExecutor ile paralel borsapy.Ticker.fast_info/history
            (30 worker -> beklenen ~20-30s).
    """
    if not BORSAPY_OK or not tickers_key:
        return {}

    from concurrent.futures import ThreadPoolExecutor

    def _fetch_one(ticker: str):
        """Tek bir BIST hissesinin son fiyatini al. Once fast_info dene
        (en hizli), sonra history (yedek)."""
        try:
            tobj = bp.Ticker(ticker)
            # 1) En hizli: fast_info.last_price
            try:
                fi = tobj.fast_info
                # FastInfo objesi olarak veya dict olarak gelebilir
                v = None
                if hasattr(fi, "last_price"):
                    v = fi.last_price
                if v is None and hasattr(fi, "todict"):
                    v = fi.todict().get("last_price") or fi.todict().get("regularMarketPrice")
                if v is not None and float(v) > 0:
                    return ticker, float(v)
            except Exception:
                pass
            # 2) Yedek: 1 gunluk history (yine de hizli)
            try:
                h = tobj.history(period="2d", interval="1d")
                if h is not None and len(h) > 0:
                    for col in ("Close", "close", "CLOSE"):
                        if col in h.columns:
                            close = h[col].dropna()
                            if not close.empty:
                                v = float(close.iloc[-1])
                                if v > 0:
                                    return ticker, v
                            break
            except Exception:
                pass
        except Exception:
            pass
        return ticker, None

    out: dict = {}
    try:
        # 30 paralel worker -> 770 ticker / 30 ~= 26 ticker per thread
        with ThreadPoolExecutor(max_workers=30) as ex:
            for ticker, price in ex.map(_fetch_one, tickers_key):
                if price is not None and price > 0:
                    out[ticker] = price
    except Exception:
        return out

    return out


def refresh_bist(df: pd.DataFrame) -> pd.DataFrame:
    """BIST hisselerinin Son_Fiyat'ini borsapy ile (15dk gecikmeli) canli yenile.

    v1.9.0: Worker.py/CSV bagimliligini BIST icin de kaldirir. Yedek: borsapy
    cagrisi basarisiz olursa CSV'deki Son_Fiyat (worker.py cikti si) korunur.

    TEFAS dokunulmaz (gunluk NAV, regulatif).
    """
    with _timed_block("refresh_bist"):
        if df is None or df.empty or not BORSAPY_OK:
            return df
        if "Kategori" not in df.columns or "Son_Fiyat" not in df.columns:
            return df

        bist_tickers = sorted(
            df[df["Kategori"] == "BIST"]["Ticker"].dropna().astype(str).tolist()
        )
        if not bist_tickers:
            return df

        prices = _fetch_live_bist(tuple(bist_tickers))
        if not prices:
            return df

        df = df.copy()
        mask = (df["Kategori"] == "BIST") & df["Ticker"].isin(prices.keys())
        if mask.any():
            df.loc[mask, "Son_Fiyat"] = df.loc[mask, "Ticker"].map(prices).astype(float)

        return df


def refresh_fx_maden_kripto(df: pd.DataFrame) -> pd.DataFrame:
    """DOVIZ + MADEN + KRIPTO satirlarinin Son_Fiyat'ini canli verilerle uzerine yaz.

    v1.8: MADEN tickerlari icin ek olarak RSI ve Ret1M da borsapy history'den
    yeniden hesaplanir (boylece altin trendi optimizatore yansir).

    v1.9.4: MADEN history call'lari ThreadPoolExecutor ile paralelize edildi
            (5 sıralı çağrı yerine eş zamanlı, ~5x speedup beklenir).
    v1.9.4: Alt-seviye timing'ler (sub-step) eklendi.

    BIST ve TEFAS:
      - BIST: v1.9.0'da refresh_bist() ile ayri fonksiyon olarak eklendi (borsapy.download batch)
      - TEFAS: 1347 fon, gunluk NAV (regulatif), worker.py sorumlu
    """
    with _timed_block("refresh_fx_maden_kripto"):
        if df is None or df.empty:
            return df
        if "Ticker" not in df.columns or "Son_Fiyat" not in df.columns:
            return df

        # v1.9.4 alt-timing: DOVIZ canlidoviz cagrisi
        with _timed_block("  sub.fx_maden_live"):
            live = _fetch_live_fx_maden()

        # v1.9.4 alt-timing: KRIPTO BtcTurk
        with _timed_block("  sub.kripto_live"):
            kripto_list = df[df["Kategori"] == "KRIPTO"]["Ticker"].dropna().astype(str).tolist()
            if kripto_list:
                live.update(_fetch_live_kripto(tuple(sorted(kripto_list))))

        if live:
            mask = df["Ticker"].isin(live.keys())
            if mask.any():
                df.loc[mask, "Son_Fiyat"] = df.loc[mask, "Ticker"].map(live).astype(float)

        # v1.8 - MADEN tickerlari icin RSI ve Ret1M'i borsapy history'den tazele
        # v1.9.4: ThreadPoolExecutor ile paralelize (5 ticker es zamanli)
        if "RSI" in df.columns and "Ret1M" in df.columns:
            with _timed_block("  sub.maden_history_parallel"):
                from concurrent.futures import ThreadPoolExecutor

                # Sadece df'de var olan MADEN tickerlari al
                to_fetch = []
                for ticker, bp_code in _MADEN_TO_BP.items():
                    if (df["Ticker"] == ticker).any():
                        to_fetch.append((ticker, bp_code))

                if to_fetch:
                    # Paralel cagri (her birinin cache_data koruması var, kosey durumlarda hizli doner)
                    def _fetch_one(item):
                        ticker, bp_code = item
                        son, rsi, ret = _fetch_maden_history_summary(bp_code)
                        return (ticker, son, rsi, ret)

                    with ThreadPoolExecutor(max_workers=min(8, len(to_fetch))) as ex:
                        results = list(ex.map(_fetch_one, to_fetch))

                    # Sonuclari df'ye yaz
                    # v2.0.4.49: Son_Fiyat ARTIK MADEN icin bu kaynaktan
                    # yazilmiyor (asagidaki not - ayni borsapy/canlidoviz
                    # kaynagi fiyat icin donuk/guvenilmez cikti). RSI ve
                    # Ret1M icin gorece daha az riskli oldugundan (ve
                    # Optima Skoru'nun bir bileseni oldugundan) korunuyor.
                    # v2.0.7.76: RSI/Ret1M yalnizca fetch GERCEKTEN basariliysa
                    # (son is not None) yazilir; basarisizsa worker.py'nin
                    # gece hesapladigi deger dokunulmadan korunur. Ayrica
                    # basarili fetch'te "_gecmis_veri_yok" bayragi temizlenir
                    # - aksi halde app.py bu satirlarin Optima Skor'unu
                    # (ekranda gercek RSI/Ret1M gorunse bile) 0'a sifirlamaya
                    # devam ediyordu (ALTIN_TRY/GUMUS_TRY/PLATIN_TRY hatasi).
                    _has_flag_col = "_gecmis_veri_yok" in df.columns
                    for ticker, son, rsi, ret in results:
                        row_mask = df["Ticker"] == ticker
                        if not row_mask.any():
                            continue
                        if son is None:
                            continue
                        df.loc[row_mask, "RSI"]   = float(rsi)
                        df.loc[row_mask, "Ret1M"] = float(ret)
                        if _has_flag_col:
                            df.loc[row_mask, "_gecmis_veri_yok"] = False

        return df


def refresh_bist_selective(df: pd.DataFrame, tickers: list) -> pd.DataFrame:
    """Sadece belirli BIST tickerlarini canli yenile (v1.9.7).

    Tum 770 ticker yerine sadece kullanicinin portfoyundeki + Top N
    optimizasyon adaylari icin canli refresh yapilir. 1-50 ticker = 1-5 sn.

    Args:
        df: Ana evren DataFrame
        tickers: Yenilenecek BIST tickerlari listesi (string list)

    Returns:
        Belirtilen tickerlar canli, digerleri degistirilmeden DataFrame.

    Performans:
        - 1 ticker  -> ~0.5s
        - 5 ticker  -> ~1s   (portfoy senaryosu)
        - 50 ticker -> ~3-5s (optimizasyon senaryosu)
    """
    with _timed_block("refresh_bist_selective"):
        if df is None or df.empty or not BORSAPY_OK:
            return df
        if not tickers:
            return df
        if "Kategori" not in df.columns or "Son_Fiyat" not in df.columns:
            return df

        # Tickerlari sanitize et + sadece df'de var olanlar
        wanted = set()
        for t in tickers:
            if t and isinstance(t, str):
                wanted.add(t.strip().upper())
        if not wanted:
            return df

        # Sadece df'de mevcut olan BIST tickerlari
        bist_mask = df["Kategori"] == "BIST"
        actual = sorted(
            t for t in df.loc[bist_mask, "Ticker"].dropna().astype(str)
            if t in wanted
        )
        if not actual:
            return df

        # _fetch_live_bist zaten paralel + cache_data ile sarmalanmis
        prices = _fetch_live_bist(tuple(actual))
        if not prices:
            return df

        df = df.copy()
        mask = bist_mask & df["Ticker"].isin(prices.keys())
        if mask.any():
            df.loc[mask, "Son_Fiyat"] = df.loc[mask, "Ticker"].map(prices).astype(float)
        return df


# ----------------------------------------------------------------------------
# Tarihsel veri (OHLC) - app.py'deki _CROSS blogunu degistirir
# ----------------------------------------------------------------------------
def _normalize_ohlc(h) -> pd.DataFrame:
    """borsapy'den gelen DataFrame'i Open/High/Low/Close[+Volume] standartina indirge.

    v2.0.3: Volume kolonu varsa korunur (KRIPTO icin BtcTurk 24h hacim verir).
    DOVIZ/MADEN icin Volume genelde yoktur veya 0'dir.
    """
    if h is None or len(h) == 0:
        return pd.DataFrame()
    cols_lower = {c.lower(): c for c in h.columns}
    want = ("open", "high", "low", "close")
    out_cols = [cols_lower[w] for w in want if w in cols_lower]
    if len(out_cols) != 4:
        return pd.DataFrame()
    # v2.0.3: Volume varsa ekle (opsiyonel)
    if "volume" in cols_lower:
        out_cols.append(cols_lower["volume"])
    out = h[out_cols].copy()
    new_names = ["Open", "High", "Low", "Close"]
    if "volume" in cols_lower:
        new_names.append("Volume")
    out.columns = new_names
    out = out.dropna(subset=["Open", "High", "Low", "Close"])
    return out


@st.cache_data(ttl=900, show_spinner=False)
def get_fx_history(ticker: str, period: str = "1mo") -> pd.DataFrame:
    """DOVIZ ticker (USDTRY, JPYTRY, vb.) icin TRY-direkt OHLC tarihce.

    Capraz kur (cross-rate) matematigi YOK - canlidoviz.com'dan dogrudan
    TRY cifti aliniyor. Bos donerse cagiran yfinance fallback uygulamali.
    JPYTRY icin canlidoviz 'per 100 yen' verdigi icin tum OHLC degerleri
    100'e bolunur (per 1 yen format'ina cevirmek icin).
    """
    if not BORSAPY_OK:
        return pd.DataFrame()
    bp_code = _DOVIZ_TO_BP.get(ticker.upper())
    if not bp_code:
        return pd.DataFrame()
    try:
        h = bp.FX(bp_code).history(period=period, interval="1d")
        out = _normalize_ohlc(h)
        if not out.empty:
            divisor = _PER_N_UNITS.get(ticker.upper())
            if divisor and divisor != 1.0:
                # v2.0.3: Volume varsa o satiri bolme (sadece OHLC bolunmeli)
                ohlc_cols = [c for c in ["Open","High","Low","Close"] if c in out.columns]
                out[ohlc_cols] = out[ohlc_cols] / divisor
        return out
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900, show_spinner=False)
def get_maden_history(ticker: str, period: str = "1mo") -> pd.DataFrame:
    """MADEN ticker (ALTIN_TRY, GUMUS_TRY, PLATIN_TRY) icin gercek zamanli TL OHLC."""
    if not BORSAPY_OK:
        return pd.DataFrame()
    bp_code = _MADEN_TO_BP.get(ticker.upper())
    if not bp_code:
        return pd.DataFrame()
    try:
        h = bp.FX(bp_code).history(period=period, interval="1d")
        return _normalize_ohlc(h)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900, show_spinner=False)
def get_kripto_history(ticker: str, period: str = "1mo") -> pd.DataFrame:
    """KRIPTO ticker (BTC, ETH, vb.) icin TRY-direkt OHLC tarihce (BtcTurk)."""
    if not BORSAPY_OK:
        return pd.DataFrame()
    try:
        h = bp.Crypto(_kripto_bp_code(ticker)).history(period=period, interval="1d")
        return _normalize_ohlc(h)
    except Exception:
        return pd.DataFrame()


# ----------------------------------------------------------------------------
# Tani / durum raporu
# ----------------------------------------------------------------------------
def status_summary() -> dict:
    """Borsapy entegrasyonu durumu - Admin sayfasinda gosterilebilir."""
    return {
        "borsapy_yuklu":      BORSAPY_OK,
        "borsapy_versiyon":   BORSAPY_VERSION,
        "borsapy_hata":       BORSAPY_ERROR,
        "doviz_ticker_sayi":  len(_DOVIZ_TO_BP),
        "maden_ticker_sayi":  len(_MADEN_TO_BP),
        "haric_tutulan_emtia": sorted(EXCLUDED_USD_COMMODITIES),
    }
