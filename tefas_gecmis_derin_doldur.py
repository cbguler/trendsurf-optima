# -*- coding: utf-8 -*-
"""
tefas_gecmis_derin_doldur.py - TEFAS fiyat arşivini (tefas_fiyat_gecmisi) geriye
doğru doldurur. GitHub Actions'ta elle tetiklenen "TEFAS Gecmis Derin Doldur"
workflow'u çalıştırır.

v2.0.7.359 (3 Ekim 2026, Bahri'nin bulgusu - "1 saati geçti, bir türlü
durmadı, 1,5 saat sonra hata verdi"): Logdan KESİN kök neden bulundu:
  1) Veritabanına yazma SATIR SATIR INSERT ile yapılıyordu (her gidiş-geliş
     ~130 ms) - tek bir günün ~2000 satırı ~4,5 DAKİKA sürüyordu, bir yıllık
     parçada 250+ gün olduğundan sadece YAZMA işi saatler sürerdi. Artık
     db.tefas_fiyat_gecmisi_df_ekle() ile binlerce satır TEK sorguda yazılıyor.
  2) Çıktı tamponlandığı için ilerleme satırları logda HİÇ görünmüyordu
     (workflow'da `python -u` + her print'te flush ile giderildi).
  3) Sadece evrendeki TEFAS fonları (optimized_universe.csv) yazılıyor - TEFAS'ın
     toplu sorgusu evrenimizde olmayan ~700 fon daha döndürüyordu (gereksiz
     veritabanı alanı).
  4) Süre sınırı: script kendi bütçesini (varsayılan 105 dk) izler, yeni bir
     parçaya başlamadan önce yeterli süre kalmadıysa TEMİZ şekilde durur ve
     hangi parçaların eksik kaldığını yazar (yarım kalan iş boşa gitmez,
     her parça yazıldıkça kalıcıdır).
Sıralama: ÖNCE en yeni yıl (tüm türler için), sonra bir önceki yıl... böylece
süre bitse bile en değerli (en yeni) veri tüm türlerde hazır olur.

Ortam değişkenleri: TEFAS_DERIN_YIL_SAYISI (5), TEFAS_DERIN_BASLANGIC_YIL (0,
kaldığın yerden devam için), TEFAS_DERIN_SURE_DAKIKA (105).
İdempotent: tekrar çalıştırmak zararsız (ON CONFLICT DO UPDATE).
"""
import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

YIL_SAYISI = int(os.environ.get("TEFAS_DERIN_YIL_SAYISI", "5") or 5)
BASLANGIC_YIL = int(os.environ.get("TEFAS_DERIN_BASLANGIC_YIL", "0") or 0)
SURE_DAKIKA = float(os.environ.get("TEFAS_DERIN_SURE_DAKIKA", "105") or 105)
PARCA_GUN = 365
ORTUSME_GUN = 5          # parçalar arası boşluk kalmasın
TURLER = ["YAT", "EMK", "BYF"]
DENEME = 4
PARCA_ARASI_BEKLEME = 15


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def evren_tickerlari():
    try:
        df = pd.read_csv("optimized_universe.csv", on_bad_lines="skip")
        t = set(df.loc[df["Kategori"] == "TEFAS", "Ticker"].astype(str))
        log(f"Evren: {len(t)} TEFAS fonu (yalnizca bunlar arsive yazilacak).")
        return t or None
    except Exception as e:
        log(f"UYARI: optimized_universe.csv okunamadi ({e}) - tum fonlar yazilacak.")
        return None


def parca_cek(crawler, kind, bas_gun, bit_gun):
    from pytefas import TefasRateLimitError
    bugun = datetime.now()
    s = (bugun - timedelta(days=bas_gun)).strftime("%Y-%m-%d")
    e = (bugun - timedelta(days=bit_gun)).strftime("%Y-%m-%d")
    for n in range(1, DENEME + 1):
        t0 = time.time()
        try:
            df = crawler.fetch(start=s, end=e, kind=kind)
            log(f"  [{kind}] {s}..{e}: {len(df)} satir, "
                f"{df['fund_code'].nunique() if not df.empty else 0} fon "
                f"({time.time()-t0:.0f}sn, deneme {n}/{DENEME})")
            return df
        except TefasRateLimitError:
            bekle = 25 * n
            log(f"  [{kind}] {s}..{e}: hiz siniri (deneme {n}/{DENEME}, {time.time()-t0:.0f}sn) "
                f"- {bekle}sn bekleniyor")
            if n < DENEME:
                time.sleep(bekle)
        except Exception as ex:
            log(f"  [{kind}] {s}..{e}: HATA {type(ex).__name__}: {ex} (deneme {n}/{DENEME})")
            if n < DENEME:
                time.sleep(20)
    log(f"  [{kind}] {s}..{e}: {DENEME} denemeden sonra VAZGECILDI")
    return None


def arsiv_sayisi():
    try:
        from db import get_conn
        c = get_conn()
        n = c.execute("SELECT COUNT(*) AS n FROM tefas_fiyat_gecmisi").fetchone()
        c.close()
        return int(list(n.values())[0])
    except Exception:
        return None


def main():
    from pytefas import Crawler
    import db

    baslangic = time.time()
    son_an = baslangic + SURE_DAKIKA * 60
    log(f"Basladi: {YIL_SAYISI} yil, baslangic yili={BASLANGIC_YIL}, sure butcesi={SURE_DAKIKA:.0f} dk.")

    n0 = arsiv_sayisi()
    if n0 is None:
        log("Arsiv tablosu okunamadi - init_db() ile olusturuluyor...")
        try:
            db.init_db()
            n0 = arsiv_sayisi()
        except Exception as e:
            log(f"HATA: veritabani hazirlanamadi: {e}")
            sys.exit(1)
    log(f"Arsivde baslangicta {n0} satir var.")

    izinli = evren_tickerlari()
    crawler = Crawler(timeout=120, max_retry=1)   # tekrar denemeyi kendimiz yonetiyoruz
    yazilan_toplam, eksik, yazma_hatasi = 0, [], 0

    durdu = False
    for yil_idx in range(BASLANGIC_YIL, YIL_SAYISI):
        for kind in TURLER:
            kalan_dk = (son_an - time.time()) / 60
            if kalan_dk < 8:
                log(f"SURE BITIYOR (kalan {kalan_dk:.1f} dk) - yeni parcaya baslanmiyor.")
                durdu = True
                eksik.append((yil_idx, kind))
                continue
            bas_gun = (yil_idx + 1) * PARCA_GUN + ORTUSME_GUN
            bit_gun = yil_idx * PARCA_GUN
            log(f"--- Yil {yil_idx+1}/{YIL_SAYISI} | {kind} (kalan sure {kalan_dk:.0f} dk) ---")
            df = parca_cek(crawler, kind, bas_gun, bit_gun)
            if df is None or df.empty:
                eksik.append((yil_idx, kind))
                continue
            kol = {c.lower(): c for c in df.columns}
            try:
                d = df[[kol["fund_code"], kol["date"], kol["price"]]].copy()
            except KeyError:
                log(f"  [{kind}] beklenen sutunlar yok: {df.columns.tolist()}")
                eksik.append((yil_idx, kind))
                continue
            d.columns = ["ticker", "tarih", "fiyat"]
            t0 = time.time()
            n = db.tefas_fiyat_gecmisi_df_ekle(d, izinli_tickerlar=izinli)
            log(f"  [{kind}] arsive yazildi: {n} satir ({time.time()-t0:.0f}sn)")
            if n == 0:
                yazma_hatasi += 1
                eksik.append((yil_idx, kind))
            yazilan_toplam += n
            time.sleep(PARCA_ARASI_BEKLEME)

    n1 = arsiv_sayisi()
    log(f"BITTI: {yazilan_toplam} satir yazildi, arsiv {n0} -> {n1} satir, "
        f"toplam sure {(time.time()-baslangic)/60:.1f} dk.")
    if eksik:
        log("EKSIK PARCALAR (yil_indeksi, tur): " + ", ".join(f"({y},{k})" for y, k in eksik))
        log("Eksikleri tamamlamak icin workflow'u tekrar calistirin "
            "(isterseniz 'baslangic_yil' ile kaldiginiz yildan).")
    if yazma_hatasi:
        log("HATA: bazi parcalar veritabanina YAZILAMADI (SUPABASE_DB_URL/ag sorunu olabilir).")
        sys.exit(1)


if __name__ == "__main__":
    main()
