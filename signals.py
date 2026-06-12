import pandas as pd
import numpy as np
from data_pipeline import DataPipeline

class SignalEngine:
    def __init__(self):
        self.pipeline = DataPipeline()
        
        # Sistem Kuralları gereği ek başarı primi alacak varlık listeleri
        self.yuksek_temettu_bist = ["EREGL", "TUPRS", "FROTO", "TOASO", "AKSA", "BIMAS", "TTRAK", "ISCTR"]
        self.nakit_akis_tefas = ["IPV", "KUB", "DBK", "FUB", "GSP", "FON", "EUR"]
        self.kripto_pasif_gelir = ["BTC", "ETH", "BNB", "SOL", "DOT", "AVAX"]

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """
        Geçmiş fiyat serisinden otonom 14 günlük RSI değerini hesaplar.
        """
        # GÜNCELLEME: DataFrame gelmesi durumunda indikatörün çökmemesi için Close serisini ayıklıyoruz
        if isinstance(prices, pd.DataFrame):
            prices = prices['Close'] if 'Close' in prices.columns else prices.iloc[:, 0]

        if len(prices) < period + 1:
            return 50.0
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        if loss.iloc[-1] == 0:
            return 100.0 if gain.iloc[-1] > 0 else 50.0
            
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        return round(float(rsi), 2)

    def calculate_ma_trend(self, prices: pd.Series, period: int = 20) -> str:
        """
        Son fiyat ile 20 günlük Hareketli Ortalamayı kıyaslayarak yönü saptar.
        """
        # GÜNCELLEME: DataFrame gelmesi durumunda indikatörün çökmemesi için Close serisini ayıklıyoruz
        if isinstance(prices, pd.DataFrame):
            prices = prices['Close'] if 'Close' in prices.columns else prices.iloc[:, 0]

        if len(prices) < period:
            return "YUKSELIS"
        
        ma = prices.rolling(window=period).mean().iloc[-1]
        last_price = prices.iloc[-1]
        
        return "YUKSELIS" if last_price >= ma else "DUSUS"

    def generate_master_signal(self, ticker: str, category: str, base_score: float) -> dict:
        """
        Sistem Kuralları hiyerarşisine göre tek karar mercii olan Master Sinyali üretir.
        """
        live_price = self.pipeline.get_live_price(ticker, category)
        hist_prices = self.pipeline.get_historical_data(ticker, category, period="1y")
        
        if hist_prices.empty:
            rsi = 50.0
            ma_trend = "YUKSELIS"
        else:
            rsi = self.calculate_rsi(hist_prices)
            ma_trend = self.calculate_ma_trend(hist_prices)
        
        temel_skor = base_score
        ticker_upper = ticker.upper()
        category_upper = category.upper()
        
        # --- Ek Getiri ve Pasif Gelir Katmanları Prim Entegrasyonu ---
        if category_upper == "BIST":
            if any(x in ticker_upper for x in self.yuksek_temettu_bist):
                temel_skor += 10
        elif category_upper == "TEFAS":
            if any(x in ticker_upper for x in self.nakit_akis_tefas):
                temel_skor += 10
        elif category_upper == "KRIPTO":
            if any(x in ticker_upper for x in self.kripto_pasif_gelir):
                temel_skor += 10
                
        if temel_skor > 100:
            temel_skor = 100
            
        # --- Temel Skor Hakimiyeti ve Lineer Karar Ağacı ---
        if temel_skor >= 85:
            if ma_trend == "YUKSELIS" and 35 <= rsi <= 65:
                signal = "GÜÇLÜ AL"
            else:
                signal = "KADEMELİ AL"
        elif temel_skor >= 65:
            if ma_trend == "YUKSELIS" or (35 <= rsi <= 65):
                signal = "KADEMELİ AL"
            else:
                signal = "TUT İZLE"
        elif temel_skor >= 40:
            if ma_trend == "DUSUS" and rsi > 70:
                signal = "KADEMELİ SAT"
            else:
                signal = "TUT İZLE"
        else:
            signal = "NET SAT / NAKDE GEÇ"
            
        return {
            "ticker": ticker,
            "price": live_price,
            "rsi": rsi,
            "trend": ma_trend,
            "final_score": temel_skor,
            "master_signal": signal
        }

if __name__ == "__main__":
    engine = SignalEngine()
    print("Sinyal motoru testi baslatildi...")
    print("EREGL Sinyal Analizi:", engine.generate_master_signal("EREGL", "BIST", 80.0))
    print("BTC Sinyal Analizi:", engine.generate_master_signal("BTC", "KRIPTO", 75.0))