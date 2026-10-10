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
import html as _html
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
# v2.0.7.400: Halk TV haber metninin kalibi degisti (Eylul 2026: "ENAG'a gore eylulde fiyatlar yuzde 2,10
# artarken, yillik artis yuzde 46,61 oldu"; eski kalip: "aylik enflasyon yuzde 2,24 artarken yillik ...").
# Eski regex yalniz "aylik enflasyon yuzde" kalibini taniyordu, bu yuzden Eylul orani HIC kaydedilmedi ve
# grafikteki ENAG cizgisi Eylul'u katmadan duz kaldi. Artik kalip-bagimsiz, ama TAHMIN YAPMAZ: baslik
# ("ENAG <Ay> <Yil> enflasyonunu acikladi") ile "yillik" kelimesi arasindaki metinde TAM BIR "yuzde X" varsa
# o aylik orandir; yoksa ya da birden fazlaysa reddeder.
_ENAG_BASLIK_DESENI = re.compile(r"ENAG\s+(\w+)\s+(\d{4})\s+enflasyonunu\s+açıkladı", re.IGNORECASE)
_YUZDE_DESENI = re.compile(r"yüzde\s+(\d+(?:[.,]\d+)?)", re.IGNORECASE)


def metinden_oran_cikar(metin: str):
    """Meta aciklama metninden (ay_no, yil, aylik_oran) ya da (None, None, None). Yalniz kesin eslesmede doner."""
    if not metin:
        return None, None, None
    metin = _html.unescape(metin)
    b = _ENAG_BASLIK_DESENI.search(metin)
    if not b:
        return None, None, None
    ay_no = _AYLAR_TR_SOZLUK.get(b.group(1).lower())
    if ay_no is None:
        return None, None, None
    kalan = metin[b.end():]
    yi = re.search(r"yıllık", kalan, re.IGNORECASE)
    aylik_parca = kalan[:yi.start()] if yi else kalan
    bulunan = _YUZDE_DESENI.findall(aylik_parca)
    if len(bulunan) != 1:
        return None, None, None
    try:
        oran = float(bulunan[0].replace(",", "."))
    except ValueError:
        return None, None, None
    if not (0 < oran < 30):
        return None, None, None
    return ay_no, int(b.group(2)), oran


def _enag_haberini_bul(etiket_sayfasi_url: str, site_kok: str) -> str:
    """Etiket/kategori sayfasindaki linkler arasinda "enag" geceni
    bulur, TAM URL olarak doner. Bulamazsa bos string doner."""
    try:
        r = requests.get(etiket_sayfasi_url, headers=_HEADERS, timeout=20)
        print(f"[enag_izleme] {etiket_sayfasi_url} HTTP durumu: {r.status_code}")
        if r.status_code != 200:
            return []
    except Exception as e:
        print(f"[enag_izleme] {etiket_sayfasi_url} cekilemedi: {type(e).__name__}: {e}")
        return []
    _linkler = re.findall(r'href="(' + re.escape(site_kok) + r'/[^"]*enag[^"]*)"',
                           r.text, re.IGNORECASE)
    if not _linkler:
        print(f"[enag_izleme] {etiket_sayfasi_url} icinde ENAG gecen link bulunamadi.")
        return []
    _tekil = list(dict.fromkeys(_linkler))[:4]
    print(f"[enag_izleme] Bulunan aday(lar): {_tekil}")
    return _tekil


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
    _ay_no, _yil, _oran = metinden_oran_cikar(_kaynak_metin)
    if _ay_no is None:
        print("[enag_izleme] Meta aciklamada ay/oran kesin olarak ayiklanamadi (tahmin edilmedi). "
              "Meta aciklama (varsa):", _meta.group(1) if _meta else "(yok)")
        return None, None, None
    return _ay_no, _yil, _oran


def calistir():
    print("[enag_izleme] Baslangic.")
    db.init_db()
    yazilan = 0
    for _kaynak_adi, _etiket_url, _site_kok in _KAYNAKLAR:
        for _makale_url in _enag_haberini_bul(_etiket_url, _site_kok):
            _ay, _yil, _oran = _makaleden_oran_cikar(_makale_url)
            if _ay is None:
                continue
            _yil_ay_key = f"{_yil:04d}-{_ay:02d}"
            _mevcut = db.enag_oranlari_getir()
            if _yil_ay_key in _mevcut and abs(_mevcut[_yil_ay_key] - _oran) < 0.001:
                print(f"[enag_izleme] {_yil_ay_key} zaten kayitli (%{_oran}) - degisiklik yok.")
                continue
            if db.enag_oran_kaydet(_yil_ay_key, _oran):
                print(f"[enag_izleme] KAYDEDILDI: {_yil_ay_key} -> %{_oran} (kaynak: {_kaynak_adi}, {_makale_url})")
                yazilan += 1
            else:
                print(f"[enag_izleme] KAYIT BASARISIZ: {_yil_ay_key} -> %{_oran}")
    if not yazilan:
        print("[enag_izleme] Bu turda yeni/degisen ENAG verisi yazilmadi.")


if __name__ == "__main__":
    calistir()
