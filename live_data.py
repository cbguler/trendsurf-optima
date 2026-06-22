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
# USD bazli emtia filtresi (kullanici karari, 19-20 Haziran 2026 - VIII oturum)
# Tarim emtialari ve enerji (Brent/WTI/Dogalgaz) Turkiye'de fiziki olarak
# alinip-satilamayan, dunya borsalarinda USD ile fiyatlanan turetilmis
# varliklardir; portfoye eklenebilir nitelikte degiller.
#
# Paladyum ve Bakir geri eklendi: USD bazli olsa da degerli/endustriyel metal
# olarak yatirim sayilabilir; worker.py CSV'ye yfinance ile yaziyor (× USDTRY).
# ----------------------------------------------------------------------------
EXCLUDED_USD_COMMODITIES = {
    "BRENT_TRY", "PETROL_TRY", "DOGALGAZ_TRY",
    "BUGDAY_TRY", "MISIR_TRY", "SOYA_TRY", "KAKAO_TRY",
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
}

# MADEN: TRY-direkt gram bazli kiymetli madenler + sikke altinlar
# (canlidoviz.com'dan gercek zamanli TL fiyat)
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
    "ONS_ALTIN_TRY":  "ons-altin",       # canlidoviz bunu TL olarak yayinliyor
}

# Yeni sikke varliklarinin gosterim isimleri (CSV'deki "Ad" sutununa karsilik gelir)
_NEW_MADEN_DISPLAY = {
    "CEYREK_ALTIN":     "Çeyrek Altın",
    "YARIM_ALTIN":      "Yarım Altın",
    "TAM_ALTIN":        "Tam Altın",
    "CUMHURIYET_ALTIN": "Cumhuriyet Altını",
    "ATA_ALTIN":        "Ata Altını",
    "ONS_ALTIN_TRY":    "Ons Altın (TL)",
}

# Mevcut ALTIN_TRY adini gunceller: "Altin (TL)" yerine "Gram Altın" diye gosterilir
_MADEN_AD_GUNCELLE = {
    "ALTIN_TRY":  "Gram Altın",
    "GUMUS_TRY":  "Gram Gümüş",
    "PLATIN_TRY": "Gram Platin",
}

# KRIPTO: BTC -> "BTCTRY", ETH -> "ETHTRY" (BtcTurk borsasindan TRY cifti)
def _kripto_bp_code(ticker: str) -> str:
    t = ticker.upper().strip()
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
            return (None, 50.0, 0.0)
        # Close sutununu bul
        col = None
        for c in ("Close", "close", "PRICE", "price"):
            if c in h.columns:
                col = c
                break
        if col is None:
            return (None, 50.0, 0.0)
        closes = pd.to_numeric(h[col], errors="coerce").dropna()
        if closes.empty:
            return (None, 50.0, 0.0)
        son = float(closes.iloc[-1])
        rsi = _compute_rsi(closes)
        ret = _compute_ret_1m(closes)
        return (son, rsi, ret)
    except Exception:
        return (None, 50.0, 0.0)


def extend_maden_universe(df: pd.DataFrame) -> pd.DataFrame:
    """Mevcut CSV'de olmayan yeni MADEN sikkelerini DataFrame'e satir olarak ekler.

    Eklenecek satirlar: ceyrek/yarim/tam/cumhuriyet/ata altin + ons-altin (TL).
    Her satir icin canli fiyat, RSI ve Ret1M borsapy tarihçesinden hesaplanir.
    CSV dosyasi degismez, sadece bellekteki DataFrame genisletilir.
    """
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
            "Vol":        0.0,
            "YF_Symbol":  "",
            "_tcmb_guncellendi": "",
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
        "ONS_ALTIN_TRY": "ons-altin",
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
    """Portfoy degerleme icin SATIS fiyati (kullanicinin satarsa elime gececek).

    Mantik:
      - MADEN (4 ana metal): Harem alis fiyati (varsa)
      - Diger varliklar:     mevcut Son_Fiyat (canlidoviz mid / yfinance last)

    Bu fonksiyon portfoyde gosterilen "Guncel Fiyat" sutunu icin kullanilir;
    K/Z hesabi bu fiyat uzerinden yapilir, gercek satis senaryosuna yakin olur.

    Returns: { ticker: price_tl } - her ticker icin bir fiyat
    """
    out = {}
    if df is None or df.empty or "Ticker" not in df.columns or "Son_Fiyat" not in df.columns:
        return out

    # Once Harem alis fiyatlari (sadece 4 metal icin)
    harem = get_harem_buy_prices()

    # df'ten ticker -> Son_Fiyat dict'i
    son_fiyat_map = dict(zip(df["Ticker"].astype(str), pd.to_numeric(df["Son_Fiyat"], errors="coerce")))

    for t in tickers:
        t = str(t)
        if t in harem and harem[t] > 0:
            out[t] = harem[t]  # Satis fiyati = Harem alis (kullanici satinca alacagi)
        else:
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
    """borsapy'den DOVIZ + MADEN anlik fiyatlari getir. 5 dk cache."""
    if not BORSAPY_OK:
        return {}
    out = {}
    for ticker, bp_code in _DOVIZ_TO_BP.items():
        try:
            v = _safe_current(bp.FX(bp_code))
            if v is not None:
                out[ticker] = _normalize_fx_price(ticker, v)
        except Exception:
            continue
    for ticker, bp_code in _MADEN_TO_BP.items():
        try:
            v = _safe_current(bp.FX(bp_code))
            if v is not None:
                out[ticker] = v
        except Exception:
            continue
    return out


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_live_kripto(tickers_key: tuple) -> dict:
    """borsapy'den kripto TRY fiyatlari getir. 5 dk cache."""
    if not BORSAPY_OK:
        return {}
    out = {}
    for t in tickers_key:
        try:
            v = _safe_current(bp.Crypto(_kripto_bp_code(t)))
            if v is not None:
                out[t] = v
        except Exception:
            continue
    return out


def refresh_fx_maden_kripto(df: pd.DataFrame) -> pd.DataFrame:
    """DOVIZ + MADEN + KRIPTO satirlarinin Son_Fiyat'ini canli verilerle uzerine yaz.

    v1.8: MADEN tickerlari icin ek olarak RSI ve Ret1M da borsapy history'den
    yeniden hesaplanir (boylece altin trendi optimizatore yansir).

    BIST ve TEFAS dokunulmaz:
      - BIST: 770 ticker, batch refresh v1.9'da eklenecek
      - TEFAS: 1347 fon, gunluk NAV (regulatif), worker.py sorumlu
    """
    if df is None or df.empty:
        return df
    if "Ticker" not in df.columns or "Son_Fiyat" not in df.columns:
        return df

    live = _fetch_live_fx_maden()

    kripto_list = df[df["Kategori"] == "KRIPTO"]["Ticker"].dropna().astype(str).tolist()
    if kripto_list:
        live.update(_fetch_live_kripto(tuple(sorted(kripto_list))))

    if live:
        mask = df["Ticker"].isin(live.keys())
        if mask.any():
            df.loc[mask, "Son_Fiyat"] = df.loc[mask, "Ticker"].map(live).astype(float)

    # v1.8 - MADEN tickerlari icin RSI ve Ret1M'i borsapy history'den tazele
    # (Sadece _MADEN_TO_BP'de tanimli olanlar - BAKIR/PALADYUM USD-derived,
    # onlarin RSI/Ret1M CSV'de kalan worker.py degerlerini kullanir)
    if "RSI" in df.columns and "Ret1M" in df.columns:
        for ticker, bp_code in _MADEN_TO_BP.items():
            row_mask = df["Ticker"] == ticker
            if not row_mask.any():
                continue
            son, rsi, ret = _fetch_maden_history_summary(bp_code)
            # Son_Fiyat'i taze borsapy degeriyle de guncelle (live'da yoksa fallback)
            if son is not None and son > 0:
                df.loc[row_mask, "Son_Fiyat"] = float(son)
            # RSI ve Ret1M her zaman guncellenir (history bos donerse default 50/0)
            df.loc[row_mask, "RSI"]   = float(rsi)
            df.loc[row_mask, "Ret1M"] = float(ret)

    return df


# ----------------------------------------------------------------------------
# Tarihsel veri (OHLC) - app.py'deki _CROSS blogunu degistirir
# ----------------------------------------------------------------------------
def _normalize_ohlc(h) -> pd.DataFrame:
    """borsapy'den gelen DataFrame'i Open/High/Low/Close standartina indirge."""
    if h is None or len(h) == 0:
        return pd.DataFrame()
    cols_lower = {c.lower(): c for c in h.columns}
    want = ("open", "high", "low", "close")
    out_cols = [cols_lower[w] for w in want if w in cols_lower]
    if len(out_cols) != 4:
        return pd.DataFrame()
    out = h[out_cols].copy()
    out.columns = ["Open", "High", "Low", "Close"]
    out = out.dropna()
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
                out = out / divisor
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
