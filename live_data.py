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
# USD bazli emtia filtresi (kullanici karari, 19 Haziran 2026 - VIII oturum)
# Brent / WTI / Bakir / Paladyum / Tarim emtialari Turkiye'de fiziki olarak
# alip-satilamayan, dunya borsalarinda USD ile fiyatlanan turetilmis varliklar.
# Bu kategorideki varliklar sadece referans gosterge degerinde, portfoye
# eklenebilir nitelikte degiller; bu yuzden tamamen evrenden cikariliyor.
# ----------------------------------------------------------------------------
EXCLUDED_USD_COMMODITIES = {
    "BRENT_TRY", "PETROL_TRY", "DOGALGAZ_TRY",
    "BAKIR_TRY", "PALADYUM_TRY",
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

# MADEN: sadece TRY-direkt gram bazli kiymetli madenler
# (canlidoviz.com'dan gercek zamanli TL fiyat)
_MADEN_TO_BP = {
    "ALTIN_TRY":  "gram-altin",
    "GUMUS_TRY":  "gram-gumus",
    "PLATIN_TRY": "gram-platin",
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
    """USD bazli emtialari (Brent/WTI/Bakir vb.) varlik evreninden cikar.

    CSV'nin kendisini degistirmez, sadece bellekteki DataFrame'i filtreler.
    worker.py guncellense de guncellenmese de UI'a yansiyan evren temiz olur.
    """
    if df is None or df.empty or "Ticker" not in df.columns:
        return df
    return df[~df["Ticker"].isin(EXCLUDED_USD_COMMODITIES)].reset_index(drop=True)


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

    BIST ve TEFAS dokunulmaz:
      - BIST: 770 ticker, batch refresh v1.7'de eklenecek
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

    if not live:
        return df

    mask = df["Ticker"].isin(live.keys())
    if mask.any():
        df.loc[mask, "Son_Fiyat"] = df.loc[mask, "Ticker"].map(live).astype(float)
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
