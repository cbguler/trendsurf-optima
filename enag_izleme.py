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

v2.0.7.438 (12 Kasim 2026): Halk TV TEK kaynakti ve GitHub calistiricisina 23 Ekim'den beri ULASILAMADI (once
SSL hatasi, 6 Kasim'dan beri Cloudflare HTTP 403) - Ekim ENAG orani (3 Kasim'da aciklandi) hic kaydedilmedi,
grafikteki ENAG cizgisi Kasim basindaki sicramayi gostermedi ve is "basarili" gorundugu icin kimse fark etmedi.
Artik: (1) Halk TV yine ilk denenir; (2) eksik ay varsa YEDEK kaynak: Bing Haber RSS (haber basligi + ozet metni);
yedek yalniz EN AZ 2 BAGIMSIZ HABER SITESI ayni (ay, oran) degerini veriyorsa kabul eder, celisen deger varsa
yazmaz, mevcut bir ayi ASLA ezmez; (3) onceki ay 10'una kadar hala yoksa is KIRMIZI biter (GitHub bildirimi) -
sessiz basarisizlik bitti.

NOT: Bu script HER ÇALIŞTIRILDIĞINDA `/enflasyon` sayfasını kontrol
eder - günde birkaç kez çalıştırılması TAMAMEN ZARARSIZ (idempotent:
`enag_oran_kaydet` zaten var olan bir ayı sessizce GÜNCELLER, tekrar
tekrar EKLEMEZ) - ENAG ayda sadece 1 kez yayınladığı için pratikte
ayda sadece 1 kez GERÇEK bir yazma olur.
"""
import datetime
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


# ── v2.0.7.438: YEDEK KAYNAK (Bing Haber RSS) + coklu kaynak onayi ───────────────────────────────────────
_AY_ADLARI = ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık"]
_AY_ARAMA_ADI = {a: i + 1 for i, a in enumerate(_AY_ADLARI)}
_AY_DESENI = re.compile(r"\b(ocak|şubat|subat|mart|nisan|mayıs|mayis|haziran|temmuz|ağustos|agustos|eylül|eylul|ekim|kasım|kasim|aralık|aralik)\w*",
                        re.IGNORECASE)
_YUZDE_YEDEK_DESENI = re.compile(r"(?:yüzde|%)\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
_TUIK_DESENI = re.compile(r"T[ÜU]İK|TUIK|T[ÜU]FE|TÜİK", re.IGNORECASE)
_ENFLASYON_IPUCU = re.compile(r"enflasyon|fiyatlar|tüketici fiyat|e-endeks", re.IGNORECASE)
_MIN_BAGIMSIZ_KAYNAK = 2


_ASCII_AY = {"subat": "şubat", "mayis": "mayıs", "agustos": "ağustos", "eylul": "eylül", "kasim": "kasım", "aralik": "aralık"}


def _ay_no_bul(token: str):
    t = _kucult(token)
    return _AY_ARAMA_ADI.get(_ASCII_AY.get(t, t))


def _kucult(t: str) -> str:
    return t.replace("İ", "i").replace("I", "ı").lower()


def cumleden_aylik_oran(cumle: str):
    """Tek bir cumleden (ay_no, oran) ya da None. Yalniz ENAG'a atfedilmis, tek ayli, TUIK karismamis ve
    'yillik' kelimesinden ONCE tam bir 'yuzde X' iceren cumlede doner (tahmin yok)."""
    if not cumle:
        return None
    c = _html.unescape(cumle)
    c = re.sub(r"E-T[ÜU]FE", "e-endeks", c, flags=re.IGNORECASE)
    if not re.search(r"ENAG", c, re.IGNORECASE) or _TUIK_DESENI.search(c) or not _ENFLASYON_IPUCU.search(c):
        return None
    aylar = {_ay_no_bul(m.group(1)) for m in _AY_DESENI.finditer(c)}
    aylar.discard(None)
    if len(aylar) != 1:
        return None
    yi = re.search(r"y[ıi]llık", c, re.IGNORECASE)
    parca = c[:yi.start()] if yi else c
    bulunan = _YUZDE_YEDEK_DESENI.findall(parca)
    if len(bulunan) != 1:
        return None
    try:
        oran = float(bulunan[0].replace(",", "."))
    except ValueError:
        return None
    if not (0 < oran < 30):
        return None
    return aylar.pop(), oran


def _yayin_ayi_yili(ay_no: int, yayin: "datetime.date"):
    """ENAG ayi ayin ilk gunlerinde (sonraki ay) aciklar: yayin tarihi ile ay arasi 1-2 ay olmali. (yil, ay) ya da None."""
    fark = (yayin.month - ay_no) % 12
    if fark not in (1, 2):
        return None
    return (yayin.year if yayin.month > ay_no else yayin.year - 1), ay_no


def yedek_gozlemler(ogeler: list, bugun) -> list:
    """Haber ogelerinden [(yil_ay, oran, kaynak_alan_adi)]. oge: {'title','desc','url','pub'(datetime.date)}."""
    sonuc = []
    for o in ogeler:
        pub = o.get("pub")
        if not pub or not (0 <= (bugun - pub).days <= 75):
            continue
        host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", o.get("url") or "").split("/")[0].lower())
        if not host:
            continue
        for metin in (o.get("title") or "", o.get("desc") or ""):
            for cumle in re.split(r"(?<=[.!?:])\s+|\s*\|\s*|\s+-\s+", metin):
                r = cumleden_aylik_oran(cumle)
                if r is None:
                    continue
                ya = _yayin_ayi_yili(r[0], pub)
                if ya is None:
                    continue
                sonuc.append((f"{ya[0]:04d}-{ya[1]:02d}", r[1], host))
    return sonuc


def kaynaklar_arasi_karar(gozlemler: list, en_az: int = _MIN_BAGIMSIZ_KAYNAK) -> dict:
    """{yil_ay: oran}: yalniz en az `en_az` BAGIMSIZ site ayni orani veriyorsa VE celisen deger daha zayif degilse
    (kazanan destegi >= 2 x ikinci destegi). Aksi halde o ay icin HICBIR sey dondurulmez."""
    gruplar = {}
    for ya, oran, host in gozlemler:
        gruplar.setdefault(ya, {}).setdefault(round(oran, 4), set()).add(host)
    karar = {}
    for ya, d in gruplar.items():
        sirali = sorted(d.items(), key=lambda kv: -len(kv[1]))
        ust_oran, ust_host = sirali[0]
        ikinci = len(sirali[1][1]) if len(sirali) > 1 else 0
        if len(ust_host) >= en_az and len(ust_host) >= 2 * ikinci:
            karar[ya] = ust_oran
        else:
            print(f"[enag_izleme] YEDEK {ya}: onay yetersiz/celiskili {({o: sorted(h) for o, h in d.items()})} - YAZILMADI.")
    return karar


def _bing_haberleri(sorgu: str) -> list:
    import datetime as _dt
    import email.utils as _eu
    import urllib.parse as _up
    try:
        r = requests.get("https://www.bing.com/news/search", params={"q": sorgu, "format": "rss", "setlang": "tr"},
                         headers=_HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"[enag_izleme] Bing Haber HTTP {r.status_code} ({sorgu})")
            return []
    except Exception as e:
        print(f"[enag_izleme] Bing Haber cekilemedi: {type(e).__name__}: {str(e)[:120]}")
        return []
    ogeler = []
    for it in re.findall(r"<item>.*?</item>", r.text, re.S):
        def al(k):
            m = re.search(rf"<{k}[^>]*>(.*?)</{k}>", it, re.S)
            return _html.unescape(m.group(1)) if m else ""
        u = re.search(r"url=([^&]+)", al("link"))
        try:
            pub = _eu.parsedate_to_datetime(al("pubDate")).date()
        except Exception:
            continue
        ogeler.append({"title": al("title"), "desc": al("description"),
                       "url": _up.unquote(u.group(1)) if u else "", "pub": pub})
    return ogeler


def _eksik_aylar(mevcut: dict, bugun, geri: int = 3) -> list:
    """Son `geri` TAMAMLANMIS ay (bugunku ay haric) icinde DB'de olmayanlar; en eski kayitli aydan eskisi aranmaz."""
    ilk = min(mevcut) if mevcut else None
    y, a, liste = bugun.year, bugun.month, []
    for _ in range(geri):
        a -= 1
        if a == 0:
            y, a = y - 1, 12
        k = f"{y:04d}-{a:02d}"
        if k not in mevcut and (ilk is None or k >= ilk):
            liste.append(k)
    return sorted(liste)


def yedek_kaynaktan_tamamla(eksik: list, bugun) -> dict:
    """Eksik aylar icin Bing Haber'den {yil_ay: oran} (coklu kaynak onayli)."""
    gozlem = []
    for k in eksik:
        ay_no = int(k[5:])
        ay_adi = _AY_ADLARI[ay_no - 1]
        for sorgu in (f"ENAG {ay_adi} ayı enflasyonu açıkladı", f"ENAG {ay_adi} {k[:4]} enflasyonu aylık yüzde"):
            gozlem += yedek_gozlemler(_bing_haberleri(sorgu), bugun)
    return {k: v for k, v in kaynaklar_arasi_karar([g for g in gozlem if g[0] in eksik]).items()}


def calistir(bugun=None) -> int:
    """0: tamam. 1: onceki ayin ENAG orani ayin 10'undan sonra HALA yok (is kirmizi biter, GitHub bildirir)."""
    bugun = bugun or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date()
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

    # v2.0.7.438: Halk TV'den gelmeyen aylar icin coklu kaynak onayli yedek (mevcut ayi ASLA ezmez).
    mevcut = db.enag_oranlari_getir()
    eksik = _eksik_aylar(mevcut, bugun)
    if eksik:
        print(f"[enag_izleme] Eksik ay(lar): {eksik} - yedek kaynak (Bing Haber, en az {_MIN_BAGIMSIZ_KAYNAK} bagimsiz site) deneniyor.")
        for k, oran in sorted(yedek_kaynaktan_tamamla(eksik, bugun).items()):
            if db.enag_oran_kaydet(k, oran):
                print(f"[enag_izleme] KAYDEDILDI (yedek, coklu kaynak): {k} -> %{oran}")
                yazilan += 1
            else:
                print(f"[enag_izleme] KAYIT BASARISIZ (yedek): {k} -> %{oran}")
    if not yazilan:
        print("[enag_izleme] Bu turda yeni/degisen ENAG verisi yazilmadi.")

    onceki = f"{bugun.year - 1:04d}-12" if bugun.month == 1 else f"{bugun.year:04d}-{bugun.month - 1:02d}"
    mevcut = db.enag_oranlari_getir()
    if bugun.day >= 10 and mevcut and onceki not in mevcut and onceki >= min(mevcut):
        print(f"::error::ENAG {onceki} orani ayin {bugun.day}'unde HALA yok - hicbir kaynaktan dogrulanamadi. "
              f"Grafikteki ENAG cizgisi bu ayi 0% sayiyor.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(calistir())
