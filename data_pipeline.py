import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta

# ── Sembol dönüşüm tablosu (yfinance için) ──────────────────────────────────
_MADEN_MAP = {
    "XAUUSD": "GC=F",  "GOLD":   "GC=F",
    "XAGUSD": "SI=F",  "SILVER": "SI=F",
    "XPTUSD": "PL=F",  "PLATINUM":"PL=F",
    "XPDUSD": "PA=F",  "PALLADIUM":"PA=F",
    "XCUUSD": "HG=F",  "COPPER": "HG=F",
    "XNGUSD": "NG=F",  "NATURALGAZ":"NG=F",
    "XBRUSD": "BZ=F",  "BRENT":  "BZ=F",
    "XWTIUSD":"CL=F",  "WTI":    "CL=F",
    "WTIUSD": "CL=F",  "OIL":    "CL=F",
}

_KRIPTO_USDT = {  # USDT ekli tickerları temizle
    "BTCUSDT":"BTC", "ETHUSDT":"ETH", "BNBUSDT":"BNB",
    "SOLUSDT":"SOL", "XRPUSDT":"XRP", "ADAUSDT":"ADA",
    "DOTUSDT":"DOT", "AVAXUSDT":"AVAX","MATICUSDT":"MATIC",
    "DOGEUSDT":"DOGE","LTCUSDT":"LTC", "LINKUSDT":"LINK",
}

def _format_yf_symbol(ticker: str, category: str) -> str:
    """Ticker ve kategori bilgisinden doğru yfinance sembolünü üretir."""
    t = ticker.upper().strip()
    cat = category.upper()

    if cat == "BIST":
        return t if t.endswith(".IS") else f"{t}.IS"

    if cat == "DOVIZ":
        # TRY çiftleri: EURTRY -> EURTRY=X
        if t.endswith("TRY") or t.endswith("TRY=X"):
            base = t.replace("=X", "")
            return f"{base}=X"
        # USD/EUR çapraz: EURUSD -> EURUSD=X
        if len(t) == 6 and t.isalpha():
            return f"{t}=X"
        return t

    if cat == "MADEN":
        return _MADEN_MAP.get(t, t)

    if cat == "KRIPTO":
        # USDT ekli tickerları temizle
        clean = _KRIPTO_USDT.get(t, t.replace("USDT", "").replace("BUSD", ""))
        # -USD suffix yoksa ekle
        if "-" not in clean:
            return f"{clean}-USD"
        return clean

    return t


    _tefas_kind_cache = {}
    _excel_loaded = False

    def __init__(self):
        pass

    def _clean_price(self, val):
        """Resmi API'den gelen Turkce ondalik ve metin bicimlerini sayiya temizler."""
        if val is None:
            return 0.0
        try:
            return float(val)
        except ValueError:
            val_str = str(val).strip()
            if ',' in val_str and '.' in val_str:
                if val_str.find('.') < val_str.find(','):
                    val_str = val_str.replace('.', '').replace(',', '.')
                else:
                    val_str = val_str.replace(',', '')
            elif ',' in val_str:
                val_str = val_str.replace(',', '.')
            try:
                return float(val_str)
            except:
                return 0.0

    def _get_tefas_kind(self, ticker: str) -> str:
        """Fon kodunun hangi Excel kumesine ait oldugunu bularak API'ye iletir."""
        ticker = ticker.upper().strip()
        
        if not DataPipeline._excel_loaded:
            # Dosya isimleri tamamen Ingilizce karakter standartina getirildi
            mapping = {
                "Menkul_Kiymet_Yatirim_Fonlari_EXCEL_Tum_Veri_2026-05-26.xlsx": "YAT",
                "Emeklilik_Fonlari_EXCEL_Tum_Veri_2026-05-26.xlsx": "EMK",
                "Borsa_Yatirim_Fonlari_EXCEL_Tum_Veri_2026-05-26.xlsx": "BYF"
            }
            for filename, kind in mapping.items():
                if os.path.exists(filename):
                    try:
                        # header=4 ile meta satirlari atlanarak dogrudan veriye erisilir
                        df = pd.read_excel(filename, header=4, usecols=['Fon Kodu'])
                        for code in df['Fon Kodu'].dropna().astype(str).str.upper().str.strip().values:
                            DataPipeline._tefas_kind_cache[code] = kind
                    except Exception as e:
                        print(f"Excel indeksleme hatasi ({filename}): {str(e)}")
            DataPipeline._excel_loaded = True
            
        return DataPipeline._tefas_kind_cache.get(ticker, "YAT")

    def get_live_price(self, ticker: str, category: str) -> float:
        try:
            if category.upper() == "TEFAS":
                try:
                    from tefas_client import fetch_fund_history
                    kind = self._get_tefas_kind(ticker)
                    hist = fetch_fund_history(ticker, kind, "1mo")
                    if hist is not None and not hist.empty:
                        return float(hist["Close"].iloc[-1])
                except Exception as e:
                    print(f"TEFAS anlik fiyat cekme hatasi ({ticker}): {e}")
                return 0.0

            # BIST, Doviz, Maden ve Kripto icin sembol formatlama
            formatted_ticker = _format_yf_symbol(ticker, category)

            asset = yf.Ticker(formatted_ticker)
            df = asset.history(period="1d")
            if not df.empty:
                return round(float(df['Close'].iloc[-1]), 4)
            
            price = asset.fast_info.get('last_price')
            return round(float(price), 4) if price else 0.0
        except Exception as e:
            print(f"Veri cekme hatasi ({ticker}): {str(e)}")
            return 0.0

    def get_historical_data(self, ticker: str, category: str, period: str = "1y") -> pd.DataFrame:
        try:
            if category.upper() == "TEFAS":
                try:
                    from tefas_client import fetch_fund_history
                    kind = self._get_tefas_kind(ticker)
                    return fetch_fund_history(ticker, kind, period)
                except Exception as e:
                    print(f"TEFAS gecmis veri hatasi ({ticker}): {e}")
                return pd.DataFrame()

            # YFinance OHLC verisi cekimi
            ticker_formatted = _format_yf_symbol(ticker, category)
            asset = yf.Ticker(ticker_formatted)
            hist = asset.history(period=period)
            return hist[['Open', 'High', 'Low', 'Close']] if not hist.empty else pd.DataFrame()

        except Exception as e:
            print(f"Gecmis veri hatasi ({ticker}): {str(e)}")
            return pd.DataFrame()