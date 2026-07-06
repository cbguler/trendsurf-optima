"""
update_tefas_evening.py — TrendSurf Optima
Akşam TEFAS NAV güncellemesi için hafif, bağımsız script.

Neden ayrı bir script?
worker.py, TEFAS + BIST (772 hisse) + Kripto + Maden/Döviz + Halka Arz PDF/OCR
işlemlerinin TAMAMINI sırayla yapıyor (birkaç dakika sürüyor). TEFAS fonları
akşam (~19:00-21:00 TRT) NAV yayınlıyor; bunu yakalamak için worker.py'nin
TAMAMINI tekrar çalıştırmaya gerek yok — sadece TEFAS kısmını izole edip
optimized_universe.csv'deki TEFAS satırlarını güncelliyoruz, diğer tüm
satırlar (BIST/Kripto/Maden/Döviz) dokunulmadan kalıyor.

Kullanım: python update_tefas_evening.py
"""
import os
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "optimized_universe.csv")


def main():
    print(f"[tefas-aksam] Baslatiliyor - {pd.Timestamp.now()}")

    if not os.path.exists(CSV_PATH):
        print(f"[tefas-aksam] HATA: {CSV_PATH} bulunamadi. Once worker.py "
              f"tam calistirilmali (universe dosyasini olusturur).")
        sys.exit(1)

    # worker.py'deki mevcut TEFAS mantigini oldugu gibi yeniden kullan -
    # kod tekrarindan kacinmak icin (iki yerde ayni mantigin farkli
    # sekilde bozulma riskini onler).
    try:
        from worker import load_tefas
    except Exception as e:
        print(f"[tefas-aksam] HATA: worker.py'den load_tefas import edilemedi: {e}")
        sys.exit(1)

    df_t = load_tefas()
    if df_t.empty:
        print("[tefas-aksam] TEFAS verisi bos geldi, CSV'ye dokunulmadi.")
        sys.exit(1)

    # pytefas ile guncel NAV fiyatlarini cek (worker.py'nin ana akisiyla ayni adim)
    try:
        from tefas_client import fetch_all_current_prices
        fund_list = df_t[["Ticker", "TEFAS_Kind"]].to_dict("records")
        pytefas_prices = fetch_all_current_prices(fund_list)
        if pytefas_prices:
            df_t["Son_Fiyat"] = df_t["Ticker"].map(pytefas_prices).combine_first(df_t["Son_Fiyat"])
            ok = (df_t["Son_Fiyat"] > 0).sum()
            print(f"[tefas-aksam] pytefas fiyat guncellendi: {ok}/{len(df_t)} fon")
    except Exception as e:
        print(f"[tefas-aksam] pytefas fiyat guncelleme atlandi: {e}")

    # Mevcut CSV'yi oku, TEFAS D I S I satirlari koru, TEFAS satirlarini
    # tamamen yeni (aksam) veriyle degistir.
    df_mevcut = pd.read_csv(CSV_PATH, on_bad_lines="skip")
    df_non_tefas = df_mevcut[df_mevcut["Kategori"] != "TEFAS"].copy()

    df_yeni = pd.concat([df_non_tefas, df_t], ignore_index=True, sort=False)

    onceki_tefas_sayisi = (df_mevcut["Kategori"] == "TEFAS").sum()
    yeni_tefas_sayisi = (df_yeni["Kategori"] == "TEFAS").sum()
    yeni_fiyatli = (df_t["Son_Fiyat"] > 0).sum()

    df_yeni.to_csv(CSV_PATH, index=False)

    print(f"[tefas-aksam] TAMAM: {onceki_tefas_sayisi} -> {yeni_tefas_sayisi} TEFAS "
          f"satiri ({yeni_fiyatli} fiyatli). Toplam satir: {len(df_yeni)}")


if __name__ == "__main__":
    main()
