# -*- coding: utf-8 -*-
"""
enag_izleme.py — TrendSurf Optima (v2.0.7.317, 16 Eylül 2026, Bahri'nin
talebi: "elle giriş asla olmamalı, otomatik giriş ve otonom yönetim
esas olmalıdır")

TAM OTOMATİK ENAG aylık enflasyon oranı tespiti. Önceki versiyon
(v2.0.7.314) enagrup.org'un kendi PDF bültenini çekmeyi deniyordu -
o site Claude'un test ortamından Cloudflare TLS seviyesinde (HTTP 525)
TAMAMEN ERİŞİLEMEZ bulunmuştu (robots.txt değil, gerçek bağlantı reddi,
hem HTML hem PDF için).

YENİ YÖNTEM (CANLI DOĞRULANDI - tahmin değil): Halk TV, ENAG her ay
duyurduğunda NEREDEYSE ANINDA "Son dakika | ENAG ... enflasyonunu
açıkladı" başlıklı bir haber yayınlıyor - ve bu haberin META
AÇIKLAMASI ("meta description") her zaman şu KALIPTA: "... ENAG
<AY> <YIL> enflasyonunu açıkladı. Buna göre aylık enflasyon yüzde
<ORAN> artarken yıllık yüzde <YILLIK> oldu." Bu, hem CANLI test edildi
(Ağustos 2026 haberiyle - "ENAG Ağustos 2026 enflasyonunu açıkladı...
aylık enflasyon yüzde 2,24") hem de Halk TV'nin kendi
`/enflasyon` etiket sayfasının düz `requests` ile (JS gerekmeden)
erişilebilir olduğu doğrulandı.

Akış: `/enflasyon` sayfasını çek → linkler arasında "enag" geceni
bul → o makaleyi çek → meta açıklamasından ay/yıl/oranı regex ile
çıkar → Supabase'e YAZ (`enag_oran_kaydet`). Hiçbir adımda elle
müdahale YOK - bulamazsa/parse edemezse sessizce çıkar, BİR SONRAKİ
otomatik çalıştırmada tekrar dener (ENAG'ın kendisi geç açıklarsa
diye) - asla YANLIŞ/UYDURMA bir değer YAZMAZ.

NOT: Bu script HER ÇALIŞTIRILDIĞINDA `/enflasyon` sayfasını kontrol
eder - günde birkaç kez çalıştırılması TAMAMEN ZARARSIZ (idempotent:
`enag_oran_kaydet` zaten var olan bir ayı sessizce GÜNCELLER, tekrar
tekrar EKLEMEZ) - ENAG ayda sadece 1 kez yayınladığı için pratikte
ayda sadece 1 kez GERÇEK bir yazma olur.
"""
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,*/*",
}

_AYLAR_TR_SOZLUK = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "mayis": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "agustos": 8, "eylül": 9, "eylul": 9, "ekim": 10, "kasım": 11,
    "kasim": 11, "aralık": 12, "aralik": 12,
}

_KAYNAKLAR = [
    ("Halk TV", "https://halktv.com.tr/enflasyon", "https://halktv.com.tr"),
]

_META_DESC_DESENI = re.compile(r'<meta name="description" content="([^"]*)"')
_ENAG_ORAN_DESENI = re.compile(
    r"ENAG\s+(\w+)\s+(\d{4})\s+enflasyonunu açıkladı.*?"
    r"aylık enflasyon yüzde\s+([\d,]+)", re.IGNORECASE)


def _enag_haberini_bul(etiket_sayfasi_url: str, site_kok: str) -> str:
    """Etiket/kategori sayfasindaki linkler arasinda "enag" geceni
    bulur, TAM URL olarak doner. Bulamazsa bos string doner."""
    try:
        r = requests.get(etiket_sayfasi_url, headers=_HEADERS, timeout=20)
        print(f"[enag_izleme] {etiket_sayfasi_url} HTTP durumu: {r.status_code}")
        if r.status_code != 200:
            return ""
    except Exception as e:
        print(f"[enag_izleme] {etiket_sayfasi_url} cekilemedi: {type(e).__name__}: {e}")
        return ""
    _linkler = re.findall(r'href="(' + re.escape(site_kok) + r'/[^"]*enag[^"]*)"',
                           r.text, re.IGNORECASE)
    if not _linkler:
        print(f"[enag_izleme] {etiket_sayfasi_url} icinde ENAG gecen link bulunamadi.")
        return ""
    print(f"[enag_izleme] Bulunan aday: {_linkler[0]}")
    return _linkler[0]


def _makaleden_oran_cikar(makale_url: str):
    """(ay_no, yil, oran) ya da (None, None, None) doner."""
    try:
        r = requests.get(makale_url, headers=_HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"[enag_izleme] Makale cekilemedi, HTTP {r.status_code}")
            return None, None, None
    except Exception as e:
        print(f"[enag_izleme] Makale cekilemedi: {type(e).__name__}: {e}")
        return None, None, None

    _meta = _META_DESC_DESENI.search(r.text)
    _kaynak_metin = _meta.group(1) if _meta else r.text
    _m = _ENAG_ORAN_DESENI.search(_kaynak_metin)
    if not _m:
        print("[enag_izleme] Meta aciklamada beklenen kalip bulunamadi. "
              "Meta aciklama (varsa):", _meta.group(1) if _meta else "(yok)")
        return None, None, None

    _ay_adi, _yil_str, _oran_str = _m.groups()
    _ay_no = _AYLAR_TR_SOZLUK.get(_ay_adi.lower())
    if _ay_no is None:
        print(f"[enag_izleme] Taninmayan ay adi: '{_ay_adi}'")
        return None, None, None
    try:
        _oran = float(_oran_str.replace(",", "."))
    except ValueError:
        return None, None, None
    if not (0 < _oran < 30):
        print(f"[enag_izleme] Oran ({_oran}) makul aralik disinda - guvenlik "
              f"icin reddedildi.")
        return None, None, None
    return _ay_no, int(_yil_str), _oran


def calistir():
    print("[enag_izleme] Baslangic.")
    db.init_db()

    for _kaynak_adi, _etiket_url, _site_kok in _KAYNAKLAR:
        _makale_url = _enag_haberini_bul(_etiket_url, _site_kok)
        if not _makale_url:
            continue
        _ay, _yil, _oran = _makaleden_oran_cikar(_makale_url)
        if _ay is None:
            continue

        _yil_ay_key = f"{_yil:04d}-{_ay:02d}"
        _mevcut = db.enag_oranlari_getir()
        if _yil_ay_key in _mevcut and abs(_mevcut[_yil_ay_key] - _oran) < 0.001:
            print(f"[enag_izleme] {_yil_ay_key} zaten kayitli (%{_oran}) - "
                  f"degisiklik yok.")
            return

        if db.enag_oran_kaydet(_yil_ay_key, _oran):
            print(f"[enag_izleme] KAYDEDILDI: {_yil_ay_key} -> %{_oran} "
                  f"(kaynak: {_kaynak_adi}, {_makale_url})")
        else:
            print(f"[enag_izleme] KAYIT BASARISIZ: {_yil_ay_key} -> %{_oran}")
        return

    print("[enag_izleme] Hicbir kaynaktan yeni veri bulunamadi/dogrulanamadi - "
          "bu turda hicbir sey yazilmadi.")


if __name__ == "__main__":
    calistir()
