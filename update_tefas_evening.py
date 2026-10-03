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

    # v2.0.7.352 (3 Ekim 2026, Bahri'nin bulgusu - ILU'nun "1 Aylık Getiri
    # %+12,80" diye gösterdiği değer, GERÇEK 31 günlük grafiğin GÖSTERDİĞİ
    # ~-%23 düşüşle TAMAMEN ÇELİŞİYORDU): KÖK NEDEN BULUNDU VE ÇÖK CİDDİ -
    # TÜM TEFAS fonlarının "1 Ay/3 Ay/6 Ay Getiri" değerleri, repodaki
    # "*_2026-05-26.xlsx" dosyalarından (worker.py'nin `load_tefas()`'ı
    # üzerinden) geliyordu - bu dosyaların İÇİNDEKİ "Dışa Aktarım Tarihi"
    # alanı doğrulandı: TAM OLARAK 26.05.2026 - yani bu veriler NEREDEYSE
    # 5 AYDIR hiç yenilenmemiş, TEK SEFERLİK statik dosyalar! ILU'nun CSV'deki
    # Ret1M değeri (12.8014), bu dosyadaki "1 Ay (%)" sütunuyla (0.128014)
    # BİREBİR eşleşiyordu - yani Optima Skor, 1348 TEFAS fonunun TAMAMI için
    # NEREDEYSE 5 AYLIK BAYAT momentum verisiyle hesaplanıyordu!
    #
    # ÇÖZÜM - CANLI ÖLÇÜLDÜ VE ÇOK DEĞERLİ: pytefas'ın `fund_code`
    # VERİLMEDEN (fetch_all_current_prices'ın zaten kullandığı teknik)
    # çağrılması, TÜM fonların GERÇEK GEÇMİŞİNİ TEK istekte döndürüyor -
    # "3 Ay" (95 gün) için 2055 fon / 137.884 satır SADECE 13 saniyede!
    # Bu toplu veriden HER fon için GERÇEK, GÜNCEL Ret1M/Ret3M ve RSI
    # hesaplanıp CSV'nin bayat Excel-kaynaklı değerlerinin ÜZERİNE
    # YAZILIYOR - artık kimse 5 ay önceki bir performansa göre "AL" önerisi
    # almayacak. Aynı toplu veri, kalıcı fiyat arşivini de (tefas_fiyat_
    # gecmisi) TEK SEFERDE ~95 gün geriye DOLDURUYOR - v2.0.7.350'nin
    # "günde 1 satır" birikimini aylarca beklemek yerine, BUGÜN 95 günlük
    # gerçek veri hazır oluyor.
    try:
        from pytefas import Crawler
        from datetime import datetime, timedelta
        import db as _db_mod

        c = Crawler(timeout=60, max_retry=2)
        bugun = datetime.now()
        # v2.0.7.354 (3 Ekim 2026, Bahri'nin talebi - "en az 365 gün
        # görebilmem lazım, 95 günü hâlâ aşamıyorum"): varsayılan 95 gün
        # (HIZLI, ~13sn - her 30 dk'lık sık çalışmada kalıyor) - ama
        # TEFAS_GECMIS_DERINLIK ortam değişkeniyle İSTEĞE BAĞLI olarak
        # daha derin (CANLI TEST: 370 gün = 1 yıl GÜVENİLİR çalışıyor,
        # ~77sn; 1800 gün/5 yıl ise toplu modda bile hız sınırına takılıp
        # BAŞARISIZ oluyor) bir "derin doldurma" çalıştırılabilir - bkz.
        # yeni "TEFAS Gecmis Derin Doldur" workflow'u (elle tetiklenir,
        # günlük sık çalışmayı YAVAŞLATMAZ).
        _derinlik_gun = int(os.environ.get("TEFAS_GECMIS_DERINLIK", "95"))
        start = (bugun - timedelta(days=_derinlik_gun)).strftime("%Y-%m-%d")
        end   = bugun.strftime("%Y-%m-%d")
        toplam_fon = 0
        toplam_arsiv_satir = 0

        for kind in ["YAT", "EMK", "BYF"]:
            try:
                df_bulk = c.fetch(start=start, end=end, kind=kind)
            except Exception as _e_kind:
                print(f"[tefas-aksam] Toplu gecmis ({kind}) cekilemedi: {_e_kind}")
                continue
            if df_bulk is None or df_bulk.empty:
                print(f"[tefas-aksam] Toplu gecmis ({kind}): bos dondu.")
                continue

            col_price = next((c2 for c2 in df_bulk.columns if c2.lower() in ("price","fiyat")), None)
            col_code  = next((c2 for c2 in df_bulk.columns if c2.lower() in ("fund_code","fonkodu","code","kod")), None)
            col_date  = next((c2 for c2 in df_bulk.columns if c2.lower() in ("date","tarih")), None)
            if not (col_price and col_code and col_date):
                print(f"[tefas-aksam] Toplu gecmis ({kind}): beklenen sutunlar bulunamadi - {df_bulk.columns.tolist()}")
                continue

            df_bulk = df_bulk[[col_code, col_date, col_price]].copy()
            df_bulk.columns = ["ticker", "tarih", "fiyat"]
            df_bulk["tarih"] = pd.to_datetime(df_bulk["tarih"], errors="coerce")
            df_bulk["fiyat"] = pd.to_numeric(df_bulk["fiyat"], errors="coerce")
            df_bulk = df_bulk.dropna(subset=["ticker", "tarih", "fiyat"]).sort_values(["ticker", "tarih"])

            # Her fon icin GERCEK Ret1M/Ret3M/RSI hesapla
            from worker import calc_rsi
            _yeni_ret1m, _yeni_ret3m, _yeni_rsi = {}, {}, {}
            for ticker, grp in df_bulk.groupby("ticker"):
                s = grp.set_index("tarih")["fiyat"]
                if len(s) < 2:
                    continue
                son = float(s.iloc[-1])
                _ay_once = s[s.index <= (s.index[-1] - pd.Timedelta(days=30))]
                if not _ay_once.empty and _ay_once.iloc[-1] > 0:
                    _yeni_ret1m[ticker] = round((son / float(_ay_once.iloc[-1]) - 1) * 100, 2)
                _uc_ay_once = s[s.index <= (s.index[-1] - pd.Timedelta(days=90))]
                if not _uc_ay_once.empty and _uc_ay_once.iloc[-1] > 0:
                    _yeni_ret3m[ticker] = round((son / float(_uc_ay_once.iloc[-1]) - 1) * 100, 2)
                _yeni_rsi[ticker] = calc_rsi(s)

            _mask_kind = df_t["TEFAS_Kind"] == kind
            df_t.loc[_mask_kind, "Ret1M"] = df_t.loc[_mask_kind, "Ticker"].map(_yeni_ret1m).combine_first(df_t.loc[_mask_kind, "Ret1M"])
            df_t.loc[_mask_kind, "Ret3M"] = df_t.loc[_mask_kind, "Ticker"].map(_yeni_ret3m).combine_first(df_t.loc[_mask_kind, "Ret3M"])
            df_t.loc[_mask_kind, "RSI"]   = df_t.loc[_mask_kind, "Ticker"].map(_yeni_rsi).combine_first(df_t.loc[_mask_kind, "RSI"])
            toplam_fon += len(_yeni_ret1m)
            print(f"[tefas-aksam] {kind}: {len(_yeni_ret1m)} fon icin GERCEK Ret1M/Ret3M/RSI hesaplandi "
                  f"({df_bulk['ticker'].nunique()} fon, {len(df_bulk)} satir toplu veriden).")

            # Ayni toplu veriyi kalici arsive de yaz (gun bazinda, en son
            # fiyat tekrar etmesin diye drop_duplicates)
            try:
                for tarih_str, grp_tarih in df_bulk.groupby(df_bulk["tarih"].dt.strftime("%Y-%m-%d")):
                    _fiyat_map = dict(zip(grp_tarih["ticker"], grp_tarih["fiyat"]))
                    toplam_arsiv_satir += _db_mod.tefas_fiyat_gecmisi_toplu_ekle(_fiyat_map, tarih=tarih_str)
            except Exception as _arsiv_err:
                print(f"[tefas-aksam] {kind}: kalici arsive toplu yazma atlandi: {_arsiv_err}")

        print(f"[tefas-aksam] GERCEK Ret1M/Ret3M/RSI guncellendi: {toplam_fon} fon. "
              f"Kalici arsive toplam {toplam_arsiv_satir} (fon x gun) satir yazildi.")
    except Exception as e:
        print(f"[tefas-aksam] Toplu gercek getiri/RSI guncellemesi atlandi: {e}")

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
