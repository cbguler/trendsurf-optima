# -*- coding: utf-8 -*-
"""
test_maden_kaynak.py
TrendSurf Optima - Oturum XVIII tanilama betigi

AMAC: Degerli Madenler kategorisindeki 18 varliktan hangilerinin
gercek GECMIS FIYAT verisine (RSI/Ret1M hesaplayabilecek kadar)
ulasabildigini, hangi kaynaktan (canlidoviz metal ID, Harem/doviz.com
kurum arsivi, veya hicbiri) test eder.

Bu betik SADECE OKUMA yapar, hicbir dosyayi degistirmez.
Calistirma: python test_maden_kaynak.py
Gereksinim: pip install borsapy requests (zaten requirements.txt'te var)

Cikti: konsola Turkce rapor + ayni klasore maden_kaynak_raporu.txt
"""

import sys
print("Betik basladi - kutuphaneler yukleniyor...", flush=True)

import json
import time
import traceback
from datetime import datetime, timedelta

try:
    import requests
except Exception as e:
    print(f"[KRITIK HATA] 'requests' kutuphanesi yuklenemedi: {e}", flush=True)
    print("Cozum: pip install requests --break-system-packages  (veya sadece: pip install requests)", flush=True)
    input("Cikmak icin Enter'a basin...")
    sys.exit(1)

try:
    import borsapy as bp
    BORSAPY_OK = True
    print("borsapy basariyla yuklendi.", flush=True)
except Exception as e:
    BORSAPY_OK = False
    print(f"[UYARI] borsapy import edilemedi: {e}", flush=True)
    print("Cozum: pip install borsapy --break-system-packages  (veya sadece: pip install borsapy)", flush=True)

RAPOR_SATIRLARI = []


def yaz(satir=""):
    print(satir, flush=True)
    RAPOR_SATIRLARI.append(satir)


def basarili_ozet(df, kaynak_adi):
    """DataFrame'den kisa bir ozet satiri uretir (son deger, kayit sayisi)."""
    try:
        if df is None or df.empty:
            return None
        col = None
        for c in ("Close", "close"):
            if c in df.columns:
                col = c
                break
        if col is None:
            return None
        seri = df[col].dropna()
        if seri.empty:
            return None
        son = float(seri.iloc[-1])
        return f"{len(seri)} kayit, son deger={son:,.2f}, kaynak={kaynak_adi}"
    except Exception:
        return None


# ============================================================
# BOLUM 1: borsapy canlidoviz METAL_IDS - 9 varlik
# ============================================================
yaz("=" * 70)
yaz("BOLUM 1: canlidoviz metal ID'leri (borsapy uzerinden) - 9 varlik")
yaz("=" * 70)

CANLIDOVIZ_METALLER = [
    "gram-altin", "ceyrek-altin", "yarim-altin", "tam-altin",
    "cumhuriyet-altin", "ata-altin", "gram-gumus", "ons-altin",
    "gram-platin",
]

sonuc_canlidoviz = {}

if BORSAPY_OK:
    for slug in CANLIDOVIZ_METALLER:
        try:
            df = bp.FX(slug).history(period="3mo", interval="1d")
            ozet = basarili_ozet(df, "canlidoviz")
            if ozet:
                yaz(f"  [OK]   {slug:20s} -> {ozet}")
                sonuc_canlidoviz[slug] = True
            else:
                yaz(f"  [BOS]  {slug:20s} -> veri donmedi (bos DataFrame)")
                sonuc_canlidoviz[slug] = False
        except Exception as e:
            yaz(f"  [HATA] {slug:20s} -> {type(e).__name__}: {e}")
            sonuc_canlidoviz[slug] = False
        time.sleep(0.3)
else:
    yaz("  borsapy yuklu olmadigi icin atlandi.")

yaz("")

# ============================================================
# BOLUM 2: Harem kurumsal tarihce (borsapy institution_history)
# ============================================================
yaz("=" * 70)
yaz("BOLUM 2: Harem kurumsal tarihce (borsapy institution_history) - 4 varlik")
yaz("=" * 70)

HAREM_DESTEKLI = ["gram-altin", "gram-gumus", "ons-altin", "gram-platin"]
sonuc_harem = {}

if BORSAPY_OK:
    for slug in HAREM_DESTEKLI:
        try:
            df = bp.FX(slug).institution_history("harem", period="3mo")
            ozet = basarili_ozet(df, "harem")
            if ozet:
                yaz(f"  [OK]   {slug:20s} -> {ozet}")
                sonuc_harem[slug] = True
            else:
                yaz(f"  [BOS]  {slug:20s} -> veri donmedi (bos DataFrame)")
                sonuc_harem[slug] = False
        except Exception as e:
            yaz(f"  [HATA] {slug:20s} -> {type(e).__name__}: {e}")
            sonuc_harem[slug] = False
        time.sleep(0.3)
else:
    yaz("  borsapy yuklu olmadigi icin atlandi.")

yaz("")

# ============================================================
# BOLUM 3: Eksik 9 tur + Paladyum icin dogrudan doviz.com arsiv API'si
# borsapy'nin METAL_SLUGS sozlugu bu turleri tanimiyor, o yuzden
# kutuphaneyi atlayip ayni API'ye (api.doviz.com/api/v12/assets/.../archive)
# dogrudan istek atiyoruz. Harem kurum ID = 23, Kapalicarsi = 20.
# ============================================================
yaz("=" * 70)
yaz("BOLUM 3: Eksik turler icin dogrudan doviz.com arsiv API testi (aday slug'lar)")
yaz("=" * 70)

import re

FALLBACK_TOKEN = "7e2a5e914861aac18902c544e17f1156e08e5245c113470f74bcd5402f1a926d"
ARCHIVE_BASE = "https://api.doviz.com/api/v12/assets"

_TAZE_TOKEN_CACHE = {"token": None, "denendi": False}


def taze_token_al():
    """doviz.com anasayfasindan canli Bearer token cikarmayi dener.
    Basarisiz olursa None doner (cagiran yer FALLBACK_TOKEN'a duser)."""
    if _TAZE_TOKEN_CACHE["denendi"]:
        return _TAZE_TOKEN_CACHE["token"]
    _TAZE_TOKEN_CACHE["denendi"] = True
    patterns = [
        r'token["\']?\s*:\s*["\']([a-f0-9]{64})["\']',
        r"Bearer\s+([a-f0-9]{64})",
    ]
    for url in ("https://www.doviz.com/", "https://altin.doviz.com/gram-altin", "https://kur.doviz.com/"):
        try:
            r = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=10,
            )
            html = r.text
            for p in patterns:
                m = re.search(p, html, re.IGNORECASE)
                if m:
                    token = m.group(1)
                    _TAZE_TOKEN_CACHE["token"] = token
                    yaz(f"  [token] Taze token bulundu ({url}): {token[:12]}...")
                    return token
            yaz(f"  [token] {url} sayfasinda token deseni bulunamadi.")
        except Exception as e:
            yaz(f"  [token] {url} cekimi basarisiz ({type(e).__name__}: {e}).")
    yaz("  [token] Hicbir sayfadan taze token cikarilamadi, FALLBACK_TOKEN kullanilacak.")
    return None


def gecerli_token():
    return taze_token_al() or FALLBACK_TOKEN

# Bahri'nin tickerlarina karsilik gelen, doviz.com'da yaygin kullanilan
# aday slug isimleri. Birden fazla aday deneniyor, ilk basarili olan kabul edilir.
ADAY_SLUGLAR = {
    "GRAM_HAS_ALTIN": ["gram-has-altin", "has-altin"],
    "AYAR14_ALTIN":   ["14-ayar-altin", "on-dort-ayar-altin"],
    "AYAR18_ALTIN":   ["18-ayar-altin", "on-sekiz-ayar-altin"],
    "BILEZIK22_ALTIN": ["22-ayar-bilezik", "bilezik"],
    "IKIBUCUK_ALTIN": ["ikibucuk-altin", "iki-bucuk-altin"],
    "BESLI_ALTIN":    ["besli-altin"],
    "GREMSE_ALTIN":   ["gremse-altin"],
    "RESAT_ALTIN":    ["resat-altin"],
    "HAMIT_ALTIN":    ["hamit-altin"],
    "PALADYUM_TRY":   ["gram-paladyum", "paladyum"],
}

KURUM_ID = {"harem": 23, "kapalicarsi": 20}


def get_headers(origin="https://altin.doviz.com"):
    return {
        "Accept": "*/*",
        "Authorization": f"Bearer {gecerli_token()}",
        "Origin": origin,
        "Referer": f"{origin}/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TrendSurfOptima/diagnostic",
        "X-Requested-With": "XMLHttpRequest",
    }


def dogrudan_arsiv_dene(slug, kurum_slug="harem", gun=90):
    kurum_id = KURUM_ID[kurum_slug]
    api_slug = f"{kurum_id}-{slug}"
    url = f"{ARCHIVE_BASE}/{api_slug}/archive"
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=gun)
    params = {"start": int(start_dt.timestamp()), "end": int(end_dt.timestamp())}
    try:
        r = requests.get(url, headers=get_headers(), params=params, timeout=10)
        if r.status_code != 200:
            return (False, f"HTTP {r.status_code}")
        data = r.json()
        archive = data.get("data", {}).get("archive", [])
        if not archive:
            return (False, "arsiv bos")
        son = archive[-1]
        son_close = son.get("close")
        return (True, f"{len(archive)} kayit, son_close={son_close}")
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")


yaz("  Taze token deneniyor (birden fazla doviz.com sayfasindan)...")
_ilk_token = gecerli_token()
yaz(f"  Kullanilacak token onizleme: {str(_ilk_token)[:12]}...")
yaz("")

sonuc_eksik = {}

for ticker, adaylar in ADAY_SLUGLAR.items():
    bulundu = False
    for slug in adaylar:
        for kurum in ("harem", "kapalicarsi"):
            ok, mesaj = dogrudan_arsiv_dene(slug, kurum)
            if ok:
                yaz(f"  [OK]   {ticker:18s} -> slug='{slug}' kurum={kurum}: {mesaj}")
                sonuc_eksik[ticker] = {"slug": slug, "kurum": kurum, "mesaj": mesaj}
                bulundu = True
                break
            else:
                yaz(f"  [red]  {ticker:18s} -> slug='{slug}' kurum={kurum}: {mesaj}")
            time.sleep(0.25)
        if bulundu:
            break
    if not bulundu:
        yaz(f"  [YOK]  {ticker:18s} -> denenen hicbir aday/kurum kombinasyonu calismadi")
        sonuc_eksik[ticker] = None

yaz("")
yaz("=" * 70)
yaz("OZET")
yaz("=" * 70)
yaz(f"canlidoviz (9 varlik) calisan sayisi : {sum(1 for v in sonuc_canlidoviz.values() if v)}/9")
yaz(f"Harem kurumsal (4 varlik) calisan sayisi: {sum(1 for v in sonuc_harem.values() if v)}/4")
yaz(f"Eksik 10 tur icin bulunan kaynak sayisi : {sum(1 for v in sonuc_eksik.values() if v)}/10")
yaz("")
yaz("Not: Bu betik hicbir dosyayi degistirmedi. Ciktiyi (bu ekran + ayni")
yaz("klasordeki maden_kaynak_raporu.txt) Claude'a iletirsen, hangi turun")
yaz("hangi kaynaga baglanacagini netlestirip kodu (v2.0.7.76) yazariz.")

with open("maden_kaynak_raporu.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(RAPOR_SATIRLARI))

print("\n[Rapor 'maden_kaynak_raporu.txt' dosyasina da kaydedildi.]", flush=True)
input("\nTamamlandi. Pencereyi kapatmak icin Enter'a basin...")
