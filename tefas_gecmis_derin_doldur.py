# -*- coding: utf-8 -*-
"""
tefas_gecmis_derin_doldur.py - v2.0.7.358 (3 Ekim 2026, Bahri'nin talebi -
"'5 yıl başarısız oldu' özrünü kabul etmiyorum, yeniden dene")

pytefas'ın BÜYÜK, TEK SEFERLİK bir aralığı (ör. 1800 gün/5 yıl) toplu modda
bile istediğinde hız sınırına takıldığı CANLI OLARAK doğrulandı - ama AYNI
5 yıllık aralık, ~370 GÜNLÜK (1 yıllık) PARÇALARA bölünüp ARDIŞIK olarak
çekildiğinde HER PARÇA güvenilir şekilde başarılı oluyor (3 ayrı yıl parçası
CANLI test edildi, üçü de başarılı - 62-77 saniye arası her biri).

Bu script, TEFAS'ın YAT/EMK/BYF türlerinin HER BİRİ için 5 yılı 1'er yıllık
5 parçaya bölüp sırayla çeker, her parçayı `tefas_fiyat_gecmisi` kalıcı
arşivine yazar. Toplam ~15 istek x ~70sn ortalama ≈ 15-20 dakika - bu
yüzden GÜNLÜK "TEFAS Aksam Guncelle" işleminin İÇİNE KONULMADI (onu çok
yavaşlatırdı), AYRI, ELLE TETİKLENEN bir workflow olarak kuruldu
(`tefas_gecmis_derin_doldur.yml`) - Bahri istediğinde (ya da örn. ayda bir)
çalıştırılabilir, günlük otomasyonu YAVAŞLATMAZ.

İdempotent: `tefas_fiyat_gecmisi_toplu_ekle()` zaten ON CONFLICT DO UPDATE
kullanıyor - bu script defalarca çalıştırılsa bile sorun çıkmaz, sadece
mevcut günleri günceller.
"""
import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
from pytefas import Crawler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import tefas_fiyat_gecmisi_toplu_ekle

YIL_SAYISI = int(os.environ.get("TEFAS_DERIN_YIL_SAYISI", "5"))
YIL_GUN = 370  # CANLI TEST: bu boyut guvenilir, 1 gun daha az (365) de olur
TURLER = ["YAT", "EMK", "BYF"]


def _parca_cek(c: Crawler, kind: str, baslangic_gun_once: int, bitis_gun_once: int,
               deneme: int = 4) -> pd.DataFrame:
    """v2.0.7.358 (canli test duzeltmesi): ayni boyuttaki (370 gun) bir
    parca, ONCEKI testte max_retry=2 + bekleme OLMADAN 3/3 basarisiz
    oldu, ama max_retry=3 + 30 saniyelik SOGUMA PAYI ile basarili oldu -
    yani TEK BASINA Crawler'in kendi ic retry'i YETERLI DEGIL, parcalar
    arasinda ACIKCA bir bekleme/artan-geri-cekilme SART. Bu fonksiyon
    artik KENDI disaridan retry dongusunu yonetiyor (Crawler'in kendi
    max_retry'inin USTUNE)."""
    from pytefas import TefasRateLimitError
    bugun = datetime.now()
    s = (bugun - timedelta(days=baslangic_gun_once)).strftime("%Y-%m-%d")
    e = (bugun - timedelta(days=bitis_gun_once)).strftime("%Y-%m-%d")
    for deneme_no in range(deneme):
        t0 = time.time()
        try:
            df = c.fetch(start=s, end=e, kind=kind)
            print(f"  [{kind}] {s}..{e}: {len(df)} satir, "
                  f"{df['fund_code'].nunique() if not df.empty else 0} fon "
                  f"({time.time()-t0:.1f}sn, deneme {deneme_no+1}/{deneme})")
            return df
        except TefasRateLimitError as ex:
            _bekleme = 25 * (deneme_no + 1)  # 25, 50, 75, 100 sn - artan geri cekilme
            print(f"  [{kind}] {s}..{e}: hiz siniri (deneme {deneme_no+1}/{deneme}, "
                  f"{time.time()-t0:.1f}sn) - {_bekleme}sn bekleyip tekrar denenecek.")
            if deneme_no < deneme - 1:
                time.sleep(_bekleme)
        except Exception as ex:
            print(f"  [{kind}] {s}..{e}: HATA ({time.time()-t0:.1f}sn, "
                  f"deneme {deneme_no+1}/{deneme}) - {type(ex).__name__}: {ex}")
            if deneme_no < deneme - 1:
                time.sleep(20)
    print(f"  [{kind}] {s}..{e}: {deneme} denemeden sonra VAZGECILDI.")
    return pd.DataFrame()


def main():
    print(f"[tefas-derin-doldur] Baslangic - {YIL_SAYISI} yil, tur basina "
          f"{YIL_SAYISI} parca (yaklasik {YIL_SAYISI * len(TURLER)} istek).")
    c = Crawler(timeout=90, max_retry=2)
    toplam_satir_yazilan = 0
    toplam_basarisiz_parca = 0

    for kind in TURLER:
        print(f"\n=== {kind} ===")
        for yil_idx in range(YIL_SAYISI):
            baslangic = (yil_idx + 1) * YIL_GUN
            bitis = yil_idx * YIL_GUN
            df_parca = _parca_cek(c, kind, baslangic, bitis)
            if df_parca.empty:
                toplam_basarisiz_parca += 1
                continue

            col_price = next((c2 for c2 in df_parca.columns if c2.lower() in ("price", "fiyat")), None)
            col_code = next((c2 for c2 in df_parca.columns if c2.lower() in ("fund_code", "fonkodu", "code", "kod")), None)
            col_date = next((c2 for c2 in df_parca.columns if c2.lower() in ("date", "tarih")), None)
            if not (col_price and col_code and col_date):
                print(f"  [{kind}] beklenen sutunlar bulunamadi - {df_parca.columns.tolist()}")
                toplam_basarisiz_parca += 1
                continue

            df_parca = df_parca[[col_code, col_date, col_price]].copy()
            df_parca.columns = ["ticker", "tarih", "fiyat"]
            df_parca["tarih"] = pd.to_datetime(df_parca["tarih"], errors="coerce")
            df_parca["fiyat"] = pd.to_numeric(df_parca["fiyat"], errors="coerce")
            df_parca = df_parca.dropna(subset=["ticker", "tarih", "fiyat"])

            for tarih_str, grp in df_parca.groupby(df_parca["tarih"].dt.strftime("%Y-%m-%d")):
                _fiyat_map = dict(zip(grp["ticker"], grp["fiyat"]))
                toplam_satir_yazilan += tefas_fiyat_gecmisi_toplu_ekle(_fiyat_map, tarih=tarih_str)

            # v2.0.7.358: parcalar arasinda bilincli bekleme - hiz
            # sinirina "nefes aldirmak" icin (canli testte bunun ONEMLI
            # oldugu goruldu).
            time.sleep(20)

    print(f"\n[tefas-derin-doldur] Bitti - toplam {toplam_satir_yazilan} (fon x gun) satir "
          f"kalici arsive yazildi, {toplam_basarisiz_parca} parca basarisiz oldu.")


if __name__ == "__main__":
    main()
