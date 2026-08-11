# -*- coding: utf-8 -*-
"""
scoring.py - Optima Skor hesaplama mantığının TEK, PAYLAŞILAN kaynağı.

v2.0.7.132 (Bahri'nin bulgusu, 10 Ağustos 2026): TUPRS'ın Ana Sayfa'da
83,0, Temettü sayfasında 68,0 görünmesi araştırıldı. Kök neden: bu üç
fonksiyon (_teknik_alt_skor, _temel_alt_skor, optima_score) o zamana
kadar SADECE app.py içinde tanımlıydı. temettu_client.py app.py'yi
GÜVENLE import EDEMEZ (app.py Streamlit UI kodunu modül seviyesinde
çalıştırır - import etmek tüm sayfayı render etmeye çalışırdı), bu
yüzden temettu_client.py Optima_Skor'u optimized_universe.csv'den
DOĞRUDAN, YENİDEN HESAPLAMADAN kopyalıyordu - worker.py'nin son
çalışmasındaki DONMUŞ değer, Ana Sayfa'nın (BIST için seans içi canlı
fiyat yenilemesinden sonra) YENİDEN HESAPLADIĞI CANLI değerden farklı
çıkabiliyordu.

Çözüm: bu üç fonksiyon buraya (bağımsız, Streamlit'e bağımlı olmayan bir
modüle) taşındı - hem app.py hem temettu_client.py buradan import eder,
tek kaynak, iki kopya yok.
"""


def _teknik_alt_skor(rsi, ret1m, vol=30.0):
    """RSI Zonu (0-25) + Momentum (0-35) + Volatilite (0-15) = maks 75.
    v2.0.7.79'da optima_score()'dan ayrildi (Bahri'nin talebi, YAYLA
    ornegi) - "Skor Bilesimi" paneli artik BUNU dogrudan cagirir, boylece
    ekranda gorunen "Teknik Skor" gercekten bu fonksiyonun urettigi HAM
    (normalize edilmemis) degerdir, /70 gibi yanlis bir etiketle 0-100
    olcekli baska bir sayi gosterilmez."""
    if 40 <= rsi <= 60: rsi_s = 25
    elif 35 <= rsi <= 65: rsi_s = 18
    elif 30 <= rsi < 35 or 65 < rsi <= 70: rsi_s = 10
    else: rsi_s = 0

    if ret1m >= 30: mom = 35
    elif ret1m >= 20: mom = 30
    elif ret1m >= 10: mom = 24
    elif ret1m >= 5: mom = 18
    elif ret1m >= 0: mom = 10
    elif ret1m >= -5: mom = 4
    else: mom = 0

    if vol < 20: vol_s = 15
    elif vol < 35: vol_s = 10
    elif vol < 55: vol_s = 5
    else: vol_s = 0

    return rsi_s + mom + vol_s   # maks 75


def _temel_alt_skor(pb=None, pe=None, dy=None):
    """F/K + PD/DD + Temettu = maks 25.
    v2.0.7.79 (Bahri'nin talebi, YAYLA ornegi): eskiden ekranda gosterilen
    "Temel Skor" burada degil, kap_client.py'deki AYRI ve FARKLI esik
    degerlerine (F/K<8 vb.) sahip score_from_fundamentals() ile
    hesaplaniyordu - ekranda gorunen sayi Master Skor'u hic etkilemiyordu.
    Artik TEK kaynak burasi: hem "Skor Bilesimi" paneli hem Master Skor'un
    kendisi (optima_score() araciligiyla) AYNI bu fonksiyonu kullanir.
    kap_client.score_from_fundamentals() artik hicbir yerde cagrilmiyor."""
    fund_s = 0
    if pe and 0 < float(pe) < 12: fund_s += 10
    elif pe and 0 < float(pe) < 25: fund_s += 5
    if pb and 0 < float(pb) < 1.5: fund_s += 8
    elif pb and 0 < float(pb) < 3: fund_s += 4
    if dy and float(dy) > 0.08: fund_s += 7
    elif dy and float(dy) > 0.04: fund_s += 3
    return min(25, fund_s)   # maks 25


def optima_score(rsi, ret1m, vol=30.0, has_fundamental=False, pb=None, pe=None, dy=None):
    """
    Optima Skoru (0-100): teknik + temel faktörler.
    Ağırlıklar: RSI Zonu 25%, Momentum 35%, Volatilite 15% (teknik toplam
    75), Temel analiz 25%. v2.0.7.79'da _teknik_alt_skor()/_temel_alt_skor()
    yardımcılarına bölündü - dış davranış (dönen sayı) DEĞİŞMEDİ, sadece
    tek kaynak haline getirildi. v2.0.7.132'de app.py'den scoring.py'ye
    taşındı (bkz. modül docstring'i).
    """
    teknik = _teknik_alt_skor(rsi, ret1m, vol)   # 0-75

    if has_fundamental:
        temel = _temel_alt_skor(pb, pe, dy)      # 0-25
        return min(100, round(teknik + temel, 1))

    # Temel analiz verisi YOKSA: 75 üzerinden hesaplanan skoru 100'e normalize et
    # Böylece TEFAS/Kripto/Döviz/Maden varlıkları BIST ile adil karşılaştırılır
    return min(100, round(teknik * (100.0 / 75.0), 1))


def get_signal(score, rsi, trend):
    """v2.0.7.68 - KRITIK DUZELTME (Bahri'nin bulgusu, CNYTRY ornegi):
    onceki halde skor<40 oldugunda trend/RSI NE OLURSA OLSUN kosulsuz
    "NET SAT" veriliyordu - diger tum esikler (40/60/80) trend/RSI
    kontrolu yaparken bu en alttaki esik hicbir kontrol yapmiyordu.
    Artik bu esik de digerleriyle TUTARLI: trend hala YUKSELIS ise
    "TUT IZLE" (temkinli), sadece trend de DUSUS/zayifsa "NET SAT"."""
    if score >= 80: lbl, cls = ("GÜÇLÜ AL", "sig-g") if trend == "YUKSELIS" and 35 <= rsi <= 65 else ("KADEMELİ AL", "sig-k")
    elif score >= 60: lbl, cls = ("KADEMELİ AL", "sig-k") if (trend == "YUKSELIS" or 35 <= rsi <= 65) else ("TUT İZLE", "sig-t")
    elif score >= 40: lbl, cls = ("KADEMELİ SAT", "sig-s") if trend == "DUSUS" and rsi > 70 else ("TUT İZLE", "sig-t")
    else: lbl, cls = ("TUT İZLE", "sig-t") if trend == "YUKSELIS" else ("NET SAT", "sig-n")
    return lbl, cls
