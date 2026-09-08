# -*- coding: utf-8 -*-
"""
test_tefas_bulk_fizibilite.py
TrendSurf Optima - Oturum XVIII tanilama betigi (2. bolum)

AMAC: worker.py'yi TEFAS icin de BIST gibi TAM Optima Skoru (DD/hacim
cezasi dahil) hesaplayacak sekilde genisletmeden ONCE, 1340 fonun
gecmis NAV serisini toplu cekmenin GERCEKTEN ne kadar surdugunu ve
paralel (ThreadPoolExecutor) calisirsa ne kadar hizlandigini olcer.

Bu betik SADECE OLCUM yapar, hicbir dosyayi degistirmez, CSV/DB'ye
yazmaz. Proje klasorunde calistirilmali (TEFAS Excel dosyalari orada).

Calistirma: python test_tefas_bulk_fizibilite.py
Cikti: konsola Turkce rapor + ayni klasore tefas_fizibilite_raporu.txt
"""

import sys
print("Betik basladi - kutuphaneler yukleniyor...", flush=True)

import time
import random
import traceback
from datetime import datetime

try:
    import pandas as pd
except Exception as e:
    print(f"[KRITIK HATA] 'pandas' yuklenemedi: {e}", flush=True)
    input("Cikmak icin Enter'a basin...")
    sys.exit(1)

RAPOR_SATIRLARI = []


def yaz(satir=""):
    print(satir, flush=True)
    RAPOR_SATIRLARI.append(satir)


def ana_program():
    yaz("=" * 70)
    yaz("TEFAS TOPLU GECMIS VERI FIZIBILITE TESTI")
    yaz(f"Baslangic: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    yaz("=" * 70)

    try:
        from tefas_client import load_excel_all, fetch_fund_history, _check_pytefas
    except Exception as e:
        yaz(f"[KRITIK HATA] tefas_client import edilemedi: {e}")
        yaz("Bu betigi proje klasorunde (tefas_client.py'nin yaninda) calistirdiginizdan emin olun.")
        return

    yaz("\n[1/4] pytefas erisilebilirlik kontrolu...")
    pytefas_ok = _check_pytefas()
    yaz(f"  pytefas API erisilebilir mi: {pytefas_ok}")
    if not pytefas_ok:
        yaz("  UYARI: pytefas erisilemiyor - tum fonlar sentetik fallback'e")
        yaz("  dusecek demektir, bulk gecmis veri toplama su an ANLAMSIZ olur.")
        yaz("  (Internet baglantisini/pytefas kurulumunu kontrol edin.)")

    yaz("\n[2/4] Fon listesi yukleniyor (Excel)...")
    df_all = load_excel_all()
    if df_all.empty:
        yaz("[KRITIK HATA] Excel'den fon listesi bos geldi. Proje klasorunde")
        yaz("TEFAS xlsx dosyalari var mi kontrol edin.")
        return
    toplam_fon = len(df_all)
    yaz(f"  Toplam fon sayisi: {toplam_fon}")
    yaz(f"  Kind dagilimi: {df_all['TEFAS_Kind'].value_counts().to_dict()}")

    # Orneklem: her Kind turunden orantili, toplam ~25 fon
    ORNEKLEM_BOYUTU = 25
    orneklem = (df_all.groupby("TEFAS_Kind", group_keys=False)
                .apply(lambda g: g.sample(min(len(g), max(1, ORNEKLEM_BOYUTU * len(g) // toplam_fon)),
                                          random_state=42)))
    if len(orneklem) > ORNEKLEM_BOYUTU:
        orneklem = orneklem.sample(ORNEKLEM_BOYUTU, random_state=42)
    orneklem_listesi = list(zip(orneklem["Ticker"], orneklem["TEFAS_Kind"]))
    yaz(f"  Test orneklemi: {len(orneklem_listesi)} fon secildi.")

    # ============================================================
    # BOLUM 3: SIRALI (sequential) zamanlama
    # ============================================================
    yaz("\n[3/4] SIRALI cekim testi basliyor (fon basina tek tek)...")
    sirali_sureler = []
    sirali_basarili = 0
    sirali_basarisiz = []
    t0_genel = time.time()
    for i, (ticker, kind) in enumerate(orneklem_listesi, 1):
        t0 = time.time()
        try:
            hist = fetch_fund_history(ticker, kind, period="1y")
            sure = time.time() - t0
            sirali_sureler.append(sure)
            gercek_mi = hist is not None and not hist.empty and len(hist) >= 5
            if gercek_mi:
                sirali_basarili += 1
                yaz(f"  [{i:2d}/{len(orneklem_listesi)}] {ticker:8s} ({kind}) -> {sure:5.2f}s, {len(hist)} kayit")
            else:
                sirali_basarisiz.append(ticker)
                yaz(f"  [{i:2d}/{len(orneklem_listesi)}] {ticker:8s} ({kind}) -> {sure:5.2f}s, BOS/YETERSIZ")
        except Exception as e:
            sure = time.time() - t0
            sirali_sureler.append(sure)
            sirali_basarisiz.append(ticker)
            yaz(f"  [{i:2d}/{len(orneklem_listesi)}] {ticker:8s} ({kind}) -> {sure:5.2f}s, HATA: {type(e).__name__}: {e}")
    sirali_toplam = time.time() - t0_genel

    ort_sure = sum(sirali_sureler) / len(sirali_sureler) if sirali_sureler else 0
    yaz(f"\n  SIRALI ozet: {len(orneklem_listesi)} fon, toplam {sirali_toplam:.1f}s, "
        f"ortalama {ort_sure:.2f}s/fon, basarili {sirali_basarili}/{len(orneklem_listesi)}")
    tahmini_sirali_dk = (ort_sure * toplam_fon) / 60
    yaz(f"  TAHMIN (sirali, tum {toplam_fon} fon): ~{tahmini_sirali_dk:.1f} dakika")

    # ============================================================
    # BOLUM 4: PARALEL (ThreadPoolExecutor) zamanlama - BIST'teki
    # gibi ayni desen. Farkli bir orneklem kullanilir (sunucu tarafinda
    # "isinma"/cache etkisini bastan elemek icin farkli fonlar secilir).
    # ============================================================
    yaz("\n[4/4] PARALEL cekim testi basliyor (ThreadPoolExecutor, 8 worker)...")
    from concurrent.futures import ThreadPoolExecutor

    kalan = df_all[~df_all["Ticker"].isin(orneklem["Ticker"])]
    if len(kalan) >= ORNEKLEM_BOYUTU:
        orneklem2 = kalan.sample(ORNEKLEM_BOYUTU, random_state=7)
    else:
        orneklem2 = df_all.sample(min(ORNEKLEM_BOYUTU, toplam_fon), random_state=7)
    orneklem2_listesi = list(zip(orneklem2["Ticker"], orneklem2["TEFAS_Kind"]))

    def _tek_fon_cek(item):
        ticker, kind = item
        t0 = time.time()
        try:
            hist = fetch_fund_history(ticker, kind, period="1y")
            sure = time.time() - t0
            gercek_mi = hist is not None and not hist.empty and len(hist) >= 5
            return (ticker, kind, sure, gercek_mi, None)
        except Exception as e:
            sure = time.time() - t0
            return (ticker, kind, sure, False, str(e))

    t0_par = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        sonuclar = list(ex.map(_tek_fon_cek, orneklem2_listesi))
    paralel_toplam = time.time() - t0_par

    paralel_basarili = sum(1 for r in sonuclar if r[3])
    for ticker, kind, sure, ok, err in sonuclar:
        durum = "OK" if ok else f"BOS/HATA ({err})" if err else "BOS/YETERSIZ"
        yaz(f"  {ticker:8s} ({kind}) -> {sure:5.2f}s, {durum}")

    yaz(f"\n  PARALEL ozet (8 worker): {len(orneklem2_listesi)} fon, toplam "
        f"{paralel_toplam:.1f}s duvar-saati, basarili {paralel_basarili}/{len(orneklem2_listesi)}")
    tahmini_paralel_dk = (paralel_toplam / len(orneklem2_listesi) * toplam_fon) / 60
    yaz(f"  TAHMIN (paralel 8 worker, tum {toplam_fon} fon): ~{tahmini_paralel_dk:.1f} dakika")

    yaz("\n" + "=" * 70)
    yaz("GENEL OZET")
    yaz("=" * 70)
    yaz(f"Toplam fon sayisi           : {toplam_fon}")
    yaz(f"Sirali tahmini sure         : ~{tahmini_sirali_dk:.1f} dakika")
    yaz(f"Paralel (8 worker) tahmini  : ~{tahmini_paralel_dk:.1f} dakika")
    yaz(f"Sirali basari orani         : {sirali_basarili}/{len(orneklem_listesi)}")
    yaz(f"Paralel basari orani        : {paralel_basarili}/{len(orneklem2_listesi)}")
    yaz("")
    yaz("Not: Bu betik hicbir dosyayi degistirmedi/yazmadi. Ciktiyi (bu ekran")
    yaz("+ ayni klasordeki tefas_fizibilite_raporu.txt) Claude'a iletirsen,")
    yaz("worker.py'nin TEFAS icin tam skor on-hesaplamasini (BIST'teki gibi)")
    yaz("gece calismasina eklemenin mumkun/mantikli olup olmadigina karar")
    yaz("verip kodu yazariz.")


try:
    ana_program()
except Exception as e:
    print(f"\n[BEKLENMEYEN HATA] {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()

with open("tefas_fizibilite_raporu.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(RAPOR_SATIRLARI))
print("\n[Rapor 'tefas_fizibilite_raporu.txt' dosyasina da kaydedildi.]", flush=True)
input("\nTamamlandi. Pencereyi kapatmak icin Enter'a basin...")
