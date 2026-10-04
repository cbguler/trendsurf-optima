# -*- coding: utf-8 -*-
"""
tefas_gecmis_derin_doldur.py - TEFAS fiyat arşivini (tefas_fiyat_gecmisi) geriye
doğru doldurur. GitHub Actions'taki "TEFAS Gecmis Derin Doldur" workflow'u çalıştırır.

v2.0.7.362 (3 Ekim 2026 gece, Bahri'nin canlı logu - YAT 1 yıllık parçada 16/16
deneme "hız sınırı" ile başarısız): KESİN KÖK NEDEN pytefas kaynağından ve canlı
ölçümden bulundu:
  * Crawler.fetch() uzun aralığı 28 günlük parçalara bölüp ART ARDA (aralarında
    bekleme olmadan) HTTP isteği yapıyor; 1 yıl ≈ 13 istek.
  * Sunucu RASTGELE aralıklarla HTTP 429 döndürüyor (ratelimit başlığı YOK; canlı
    ölçüm: 6 istekten sonra bile, 429 anlık - 0,1 sn).
  * Ben Crawler(max_retry=1) kullanıyordum: kütüphane 429'da 30 sn bekleyip
    PES EDİYOR ve o ana kadar çekilen TÜM sayfaları çöpe atıyordu. 13 sayfanın
    hepsinin hiç 429 yemeden geçmesi ihtimali düşük -> YAT 16/16 başarısız.
YENİ TASARIM: her istek TAM OLARAK 28 günlük bir pencere (tek HTTP isteği), her
pencere AYRI yeniden denenir (429 -> kütüphanenin kendi 30 sn beklemesi), başarılı
pencere HEMEN veritabanına yazılır. Tek bir 429 sadece o pencerenin ~4 sn'lik işini
etkiler, hiçbir şey kaybolmaz. İstekler arasında kısa bekleme (429 görülürse artan).
Sıralama: ÖNCE en yeni pencere (tüm türler), sonra bir öncekiler.

Ortam değişkenleri: TEFAS_DERIN_YIL_SAYISI (5), TEFAS_DERIN_BASLANGIC_YIL (0),
TEFAS_DERIN_SURE_DAKIKA (105). Test: TEFAS_DERIN_KURU=1 (veritabanına yazmaz),
TEFAS_DERIN_MAKS_PENCERE=N (sadece ilk N pencere).
İdempotent: tekrar çalıştırmak zararsız (ON CONFLICT DO UPDATE).
"""
import math
import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

YIL_SAYISI = int(os.environ.get("TEFAS_DERIN_YIL_SAYISI", "5") or 5)
BASLANGIC_YIL = int(os.environ.get("TEFAS_DERIN_BASLANGIC_YIL", "0") or 0)
SURE_DAKIKA = float(os.environ.get("TEFAS_DERIN_SURE_DAKIKA", "105") or 105)
KURU = os.environ.get("TEFAS_DERIN_KURU", "") == "1"
MAKS_PENCERE = int(os.environ.get("TEFAS_DERIN_MAKS_PENCERE", "0") or 0)
PENCERE_GUN = 28          # pytefas MAX_DAYS_PER_REQUEST: tam 1 HTTP istegi
TURLER = ["YAT", "EMK", "BYF"]
MAKS_DENEME = 8           # pencere basina (429'da kutuphane zaten ~30 sn bekliyor)
TEMEL_BEKLEME = 1.5       # basarili istekler arasi (sn)


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


def arsiv_sayisi():
    try:
        from db import get_conn
        c = get_conn()
        n = c.execute("SELECT COUNT(*) AS n FROM tefas_fiyat_gecmisi").fetchone()
        c.close()
        return int(list(n.values())[0])
    except Exception:
        return None


def pencere_cek(crawler, kind, bas, bit):
    """Tek 28 gunluk pencere = tek HTTP istegi. (df, deneme_sayisi, 429_sayisi)"""
    from pytefas import TefasRateLimitError, TefasAPIError
    s, e = bas.strftime("%Y-%m-%d"), bit.strftime("%Y-%m-%d")
    r429 = 0
    for n in range(1, MAKS_DENEME + 1):
        try:
            return crawler.fetch(start=s, end=e, kind=kind), n, r429
        except TefasRateLimitError:
            r429 += 1                 # kutuphane 30 sn bekleyip pes etti, tekrar deneriz
        except TefasAPIError as ex:       # kalici hata (orn. "5 yildan eski olamaz"): tekrar denemek anlamsiz
            log(f"    [{kind}] {s}..{e}: TEFAS API hatasi, tekrar denenmeyecek: {str(ex)[:90]}")
            return None, n, r429
        except Exception as ex:
            log(f"    [{kind}] {s}..{e}: {type(ex).__name__}: {str(ex)[:80]} (deneme {n}/{MAKS_DENEME})")
            time.sleep(5)
    return None, MAKS_DENEME, r429


def main():
    from pytefas import Crawler
    import db

    t_basla = time.time()
    son_an = t_basla + SURE_DAKIKA * 60
    toplam_pencere = math.ceil(YIL_SAYISI * 365 / PENCERE_GUN)
    ilk_pencere = int(BASLANGIC_YIL * 365 / PENCERE_GUN)
    _bp = os.environ.get("TEFAS_DERIN_BASLANGIC_PENCERE", "").strip()
    if _bp.isdigit():
        ilk_pencere = int(_bp)        # tam pencere numarasindan devam (loglardaki [N/66])
    son_pencere = min(toplam_pencere, ilk_pencere + MAKS_PENCERE) if MAKS_PENCERE else toplam_pencere
    log(f"Basladi: {YIL_SAYISI} yil = {toplam_pencere} pencere x {len(TURLER)} tur "
        f"(baslangic pencere {ilk_pencere}, sure butcesi {SURE_DAKIKA:.0f} dk{', KURU CALISMA' if KURU else ''}).")

    n0 = None
    if not KURU:
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
    crawler = Crawler(timeout=60, max_retry=1)   # pencere basina tekrar denemeyi biz yonetiyoruz
    bugun = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # TEFAS: "Baslangic Tarihi 5 yildan eski olamaz" (canli log: son pencere bu yuzden
    # 8 kez bosuna denendi). En eski gecerli gun = bugun - 5 yil (+2 gun guvenlik payi).
    try:
        en_eski = bugun.replace(year=bugun.year - 5) + timedelta(days=2)
    except ValueError:               # 29 Subat
        en_eski = bugun - timedelta(days=1825) + timedelta(days=2)

    yazilan_toplam = istek_sayisi = toplam_429 = yazma_hatasi = 0
    eksik, bekleme, sakin_kalan = [], TEMEL_BEKLEME, 0
    durdu = False

    for w in range(ilk_pencere, son_pencere):
        bit = bugun - timedelta(days=w * PENCERE_GUN)
        bas = bit - timedelta(days=PENCERE_GUN - 1)
        if bit < en_eski:
            continue                  # tamamen 5 yil siniri disinda
        if bas < en_eski:
            bas = en_eski             # son pencere kirpilir
        for kind in TURLER:
            kalan_dk = (son_an - time.time()) / 60
            if kalan_dk < 3:
                if not durdu:
                    log(f"SURE BITIYOR (kalan {kalan_dk:.1f} dk) - yeni istek yapilmiyor.")
                durdu = True
                eksik.append((w, kind))
                continue
            t0 = time.time()
            df, deneme, r429 = pencere_cek(crawler, kind, bas, bit)
            istek_sayisi += 1
            toplam_429 += r429
            if r429:
                bekleme, sakin_kalan = 5.0, 6        # 429 goruldu: bir sure daha yavas git
            elif sakin_kalan > 0:
                sakin_kalan -= 1
                if sakin_kalan == 0:
                    bekleme = TEMEL_BEKLEME
            if df is None:
                eksik.append((w, kind))
                log(f"[{w+1}/{toplam_pencere}] {kind} {bas.date()}..{bit.date()}: VAZGECILDI "
                    f"({MAKS_DENEME} deneme, {r429} adet 429)")
                continue
            satir = 0
            if not df.empty:
                kol = {c.lower(): c for c in df.columns}
                try:
                    d = df[[kol["fund_code"], kol["date"], kol["price"]]].copy()
                    d.columns = ["ticker", "tarih", "fiyat"]
                    if KURU:
                        satir = len(d[d["ticker"].astype(str).isin(izinli)]) if izinli else len(d)
                    else:
                        satir = db.tefas_fiyat_gecmisi_df_ekle(d, izinli_tickerlar=izinli)
                        if satir == 0:
                            yazma_hatasi += 1
                            eksik.append((w, kind))
                except KeyError:
                    log(f"    [{kind}] beklenen sutunlar yok: {df.columns.tolist()}")
                    eksik.append((w, kind))
            yazilan_toplam += satir
            log(f"[{w+1}/{toplam_pencere}] {kind} {bas.date()}..{bit.date()}: {len(df)} satir cekildi, "
                f"{satir} yazildi ({time.time()-t0:.0f}sn, 429={r429})")
            time.sleep(bekleme)

        if (w - ilk_pencere + 1) % 10 == 0:
            gecen = (time.time() - t_basla) / 60
            tamam = w - ilk_pencere + 1
            kalan_pencere = son_pencere - w - 1
            log(f"--- ILERLEME: {tamam} pencere tamam, ~{gecen/tamam*kalan_pencere:.0f} dk kaldi tahmini "
                f"(gecen {gecen:.0f} dk, toplam 429: {toplam_429}) ---")

    n1 = arsiv_sayisi() if not KURU else None
    log(f"BITTI: {istek_sayisi} istek, {yazilan_toplam} satir yazildi, toplam 429 = {toplam_429}, "
        f"arsiv {n0} -> {n1} satir, sure {(time.time()-t_basla)/60:.1f} dk.")
    if eksik:
        ilk_eksik_yil = min(w for w, _ in eksik) * PENCERE_GUN // 365
        log(f"EKSIK ({len(eksik)} pencere/tur): " + ", ".join(f"({w},{k})" for w, k in eksik[:30])
            + (" ..." if len(eksik) > 30 else ""))
        log(f"Tamamlamak icin workflow'u tekrar calistirin (baslangic_yil={ilk_eksik_yil}; "
            f"idempotent, zaten yazilanlar zarar gormez).")
    if yazma_hatasi:
        log("HATA: bazi pencereler veritabanina YAZILAMADI (SUPABASE_DB_URL/ag sorunu olabilir).")
        sys.exit(1)


if __name__ == "__main__":
    main()
