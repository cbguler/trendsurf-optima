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

    # v2.0.7.363: gercek Ret1M/Ret3M/RSI (+ arsivden Ret6M/1Y/3Y/5Y) hesabi artik
    # tefas_client.gercek_getiri_rsi_guncelle()'de - worker.py'nin gece tam
    # calismasi da AYNI fonksiyonu cagiriyor (bayat Excel degerleri geri
    # gelmesin: ILU vakasi). Ayrintili kok neden notu o fonksiyonun basinda.
    _arsiv_parcalar = []
    try:
        from tefas_client import gercek_getiri_rsi_guncelle
        df_t, _arsiv_parcalar, _ozet = gercek_getiri_rsi_guncelle(
            df_t, derinlik_gun=int(os.environ.get("TEFAS_GECMIS_DERINLIK", "95") or 95),
            log=lambda m: print(f"[tefas-aksam] {m}"))
        print(f"[tefas-aksam] GERCEK getiri/RSI guncellendi: {_ozet['guncellenen']} fon "
              f"(uzun vade arsivden: {_ozet['uzun_vade']}, hatali tur: {_ozet['kind_hata'] or '-'}).")
    except Exception as e:
        print(f"[tefas-aksam] Toplu gercek getiri/RSI guncellemesi atlandi: {e}")

    # v2.0.7.359 (3 Ekim 2026, Bahri'nin bulgusu - TEFAS Derin Doldur loguyla
    # ortaya cikti): kalici fiyat arsivine yazma ESKIDEN (a) satir satir INSERT
    # ile (95 gun x ~2000 fon = ~130 bin ayri sorgu, saatler surecek bir is) ve
    # (b) bu workflow'da SUPABASE_DB_URL / psycopg2-binary OLMADIGI icin
    # SESSIZCE BASARISIZ olarak yapiliyordu - yani gunluk arsiv birikimi hic
    # calismamisti. Artik: sadece SON N gun (varsayilan 10; derin gecmisi
    # "TEFAS Gecmis Derin Doldur" tamamlar), sadece evrendeki fonlar, TEK toplu
    # sorgu, ve hata olsa bile CSV guncellemesini ETKILEMEZ.
    try:
        if _arsiv_parcalar:
            _son_gun = int(os.environ.get("TEFAS_ARSIV_SON_GUN", "10") or 10)
            _tum = pd.concat(_arsiv_parcalar, ignore_index=True)
            _esik = _tum["tarih"].max() - pd.Timedelta(days=_son_gun)
            _tum = _tum[_tum["tarih"] >= _esik]
            _evren = set(df_t["Ticker"].astype(str))
            import db as _db_mod
            _yazilan = _db_mod.tefas_fiyat_gecmisi_df_ekle(_tum, izinli_tickerlar=_evren)
            if _yazilan > 0:
                print(f"[tefas-aksam] Kalici fiyat arsivine yazildi: {_yazilan} (fon x gun) satir "
                      f"(son {_son_gun} gun, yalnizca evren fonlari).")
            else:
                print("[tefas-aksam] UYARI: Kalici fiyat arsivine HICBIR satir yazilamadi "
                      "(SUPABASE_DB_URL secret'i / veritabani erisimi kontrol edilmeli) - "
                      "CSV guncellemesi bundan ETKILENMEDI.")
    except Exception as _arsiv_err:
        print(f"[tefas-aksam] Kalici arsive yazma atlandi (CSV guncellemesi ETKILENMEDI): {_arsiv_err}")

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
    # v2.0.7.371: mantik tefas_client.onceki_satiri_koru()'ya tasindi (worker.py ile ORTAK).
    # TEFAS'in acikca 0 yayinladigi fonlar (NAV_Durumu="SIFIR", orn. DFI) GERI YUKLENMEZ.
    from tefas_client import onceki_satiri_koru
    _korunan_sayisi = onceki_satiri_koru(df_t, _onceki_tefas_fiyat)
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
