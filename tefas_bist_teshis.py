# -*- coding: utf-8 -*-
"""
TESHIS SCRIPTI - Portfoyum grafiklerindeki anormallik icin.

app.py'nin _get_hist_cached() fonksiyonunun BIST icin kullandigi AYNI iki
kaynagi (once borsapy, basarisiz olursa yfinance) her ticker icin ayri
ayri deniyor ve son 20 gunun Close degerlerini yazdiriyor. Amac: hangi
ticker'in hangi kaynaktan, ne kadar anormal bir deger aldigini gormek.

Calistirma (proje klasorunde, sanal ortam varsa aktifken):
    python tefas_bist_teshis.py

NOT: Bu script'i Claude'un sanal ortaminda calistirmayi denedim ama hem
borsapy hem yfinance TUM 5 ticker icin veri donmedi (THYAO gibi bilinen
buyuk bir hisse ile sorunsuz calisti) - bu, benim ortamimin bu kucuk/az
islem goren hisseler icin engellenmis/kisitli olmasindan kaynaklaniyor
olabilir. Senin normal internet baglantinla calistirinca gercek sonucu
gorecegiz.
"""
import sys

TICKERS = ["HTS", "MTG", "HOY", "CVL", "BAG"]


def test_borsapy(ticker):
    try:
        import borsapy as bp
        h = bp.Ticker(ticker).history(period="3mo", interval="1d")
        if h is None or h.empty:
            return None, "bos DataFrame dondu"
        return h, None
    except Exception as e:
        return None, str(e)


def test_yfinance(ticker):
    try:
        import yfinance as yf
        sym = ticker if ticker.endswith(".IS") else f"{ticker}.IS"
        h = yf.Ticker(sym).history(period="3mo", auto_adjust=True)
        if h is None or h.empty:
            return None, "bos DataFrame dondu"
        return h, None
    except Exception as e:
        return None, str(e)


def anomali_var_mi(close_serisi):
    """Medyanin 3 katindan fazla sapan (yukari ya da asagi) deger var mi?"""
    medyan = close_serisi.median()
    if medyan <= 0:
        return []
    sapmalar = []
    for tarih, deger in close_serisi.items():
        if deger <= 0 or deger > medyan * 3 or deger < medyan / 3:
            sapmalar.append((tarih, deger))
    return sapmalar


def main():
    print("=" * 70)
    print("BIST TICKER TESHIS - borsapy (birincil) + yfinance (yedek)")
    print("=" * 70)

    for ticker in TICKERS:
        print(f"\n--- {ticker} ---")

        h_bp, err_bp = test_borsapy(ticker)
        if h_bp is not None:
            print(f"  [borsapy] BASARILI - {len(h_bp)} satir")
            kaynak, h = "borsapy", h_bp
        else:
            print(f"  [borsapy] BASARISIZ: {err_bp}")
            h_yf, err_yf = test_yfinance(ticker)
            if h_yf is not None:
                print(f"  [yfinance] BASARILI (yedek devreye girdi) - {len(h_yf)} satir")
                kaynak, h = "yfinance", h_yf
            else:
                print(f"  [yfinance] BASARISIZ: {err_yf}")
                print(f"  SONUC: {ticker} icin HICBIR kaynak veri donmedi.")
                continue

        print(f"  Kullanilan kaynak: {kaynak}")
        print(f"  Son 10 gunun Close degerleri:")
        print(h["Close"].tail(10).to_string())

        sapmalar = anomali_var_mi(h["Close"])
        if sapmalar:
            print(f"  *** ANORMALLIK BULUNDU (medyanin 3 katindan fazla sapma) ***")
            for tarih, deger in sapmalar:
                print(f"      {tarih}: {deger}")
        else:
            print(f"  Anormallik yok (bu {len(h)} satirlik pencerede).")

    print("\n" + "=" * 70)
    print("BITTI. Yukaridaki ciktinin tamamini kopyalayip paylas.")
    print("=" * 70)


if __name__ == "__main__":
    main()
