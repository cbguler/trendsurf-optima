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

    # v2.0.7.174 (Bahri'nin bulgusu, 21 Ağustos 2026 — "HTS güncel
    # değeri, güncellendiği halde neden 0?"): KRİTİK VERİ KAYBI HATASI
    # BULUNDU. KÖK NEDEN: bu turda pytefas 1348 fonun 1230'u için fiyat
    # getirdi (log: "1230/1348 fon") - GERİ KALAN 118 fon (HTS dahil)
    # için pytefas BAŞARISIZDI. Bu fonlar BEFAS'ın günlük Excel'inde de
    # yoksa (HTS gibi bazı "Serbest Fon" türleri için olabiliyor),
    # `load_excel_all()`'daki taban değer olan Son_Fiyat=0.0 HİÇ
    # DEĞİŞMEDEN kalıyordu - VE ÖNCEKİ CSV'DEKİ GEÇERLİ FİYAT HİÇ
    # KONTROL EDİLMEDEN SIFIRLA EZİLİYORDU. Sonuç: HTS'nin gerçek
    # fiyatı (TEFAS'ın kendi sitesinde doğrulandı: 59,04 TL) bir gecede
    # 0'a düştü, Portföyüm'de sahte bir "%100 zarar" gösterdi.
    # ÇÖZÜM: worker.py'nin MADEN döngüsündeki "Kademe 3: Son CSV'den
    # tamamla" ile AYNI felsefe - bu turda fiyat alınamayan (Son_Fiyat<=0)
    # her TEFAS satırı için, ÖNCEKİ CSV'de o ticker için GEÇERLİ
    # (>0) bir fiyat varsa, o SATIRIN TAMAMI (fiyat + RSI/Ret1M/Vol)
    # AYNEN korunur - sadece fiyatı yamalayıp RSI'yi güncel bırakmak
    # yerine, tutarlı bir "önceki bilinen durum" satırı taşınır.
    _onceki_tefas_fiyat = (
        df_mevcut[df_mevcut["Kategori"] == "TEFAS"]
        .drop_duplicates(subset=["Ticker"], keep="last")
        .set_index("Ticker")
    )
    _korunan_sayisi = 0
    for _idx in df_t.index[df_t["Son_Fiyat"].fillna(0) <= 0]:
        _tkr = df_t.at[_idx, "Ticker"]
        if _tkr in _onceki_tefas_fiyat.index:
            _onceki_fiyat = float(_onceki_tefas_fiyat.at[_tkr, "Son_Fiyat"] or 0)
            if _onceki_fiyat > 0:
                for _col in df_t.columns:
                    if _col in _onceki_tefas_fiyat.columns:
                        df_t.at[_idx, _col] = _onceki_tefas_fiyat.at[_tkr, _col]
                _korunan_sayisi += 1
    if _korunan_sayisi:
        print(f"[tefas-aksam] {_korunan_sayisi} fon bu turda fiyat alamadı - "
              f"ÖNCEKİ GEÇERLİ FİYATLARI KORUNDU (sıfıra düşürülmedi).")

    df_yeni = pd.concat([df_non_tefas, df_t], ignore_index=True, sort=False)

    onceki_tefas_sayisi = (df_mevcut["Kategori"] == "TEFAS").sum()
    yeni_tefas_sayisi = (df_yeni["Kategori"] == "TEFAS").sum()
    yeni_fiyatli = (df_t["Son_Fiyat"] > 0).sum()

    df_yeni.to_csv(CSV_PATH, index=False)

    print(f"[tefas-aksam] TAMAM: {onceki_tefas_sayisi} -> {yeni_tefas_sayisi} TEFAS "
          f"satiri ({yeni_fiyatli} fiyatli). Toplam satir: {len(df_yeni)}")


if __name__ == "__main__":
    main()
