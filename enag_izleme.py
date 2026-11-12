# -*- coding: utf-8 -*-
"""
enag_izleme.py - TrendSurf Optima. TAM OTOMATIK ENAG aylik enflasyon orani tespiti (elle giris YOK).

v2.0.7.439 (12 Kasim 2026, Bahri'nin karari): HALK TV KAYNAK OLARAK BIR DAHA KULLANILMAYACAK (kurum devlet
tarafindan el konulup kayyim atandi). Bu betigin onceki surumleri ENAG'i yalniz Halk TV haberinden aliyordu
(v2.0.7.317); Halk TV'ye GitHub calistiricisindan 23 Ekim'den beri ulasilamadigi icin Ekim 2026 orani de
kaydedilmemisti (v2.0.7.438'de teshis edildi). Artik tek yontem COKLU HABER KAYNAGI ONAYI:

  * Arama: Bing Haber RSS + Google Haberler RSS (ikisi de herkese acik, anahtarsiz). Halk TV (halktv.com.tr) sonuclari
    ACIKCA yok sayilir.
  * Ayiklama: haber baslik/ozet metninden cumle duzeyinde - ENAG'a atfedilmis, tek ay adi, TUIK/TUFE karismamis,
    'yillik' kelimesinden once TAM BIR 'yuzde X', 0 < X < 30; ay/yil yayin tarihinden (1-2 ay onceki ay) cikar.
  * Onay: en az 2 BAGIMSIZ site ayni (ay, oran) degerini vermeli; celiskide kazanan >= 2x destek; aksi halde YAZILMAZ.
    Mevcut (kayitli) bir ayi ASLA ezmez, yalniz eksik ayi yazar. Hicbir zaman tahmin/uydurma deger yazmaz.
  * Alarm: onceki ayin orani ayin 10'undan sonra hala yoksa is KIRMIZI biter (cikis kodu 1 -> GitHub bildirimi).

Her calistirmada yalniz son 3 tamamlanmis ay icinde DB'de OLMAYAN aylar aranir; ENAG ayda bir (genelde 1-5'i)
acikladigi icin gunluk calistirma zararsizdir (idempotent).
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

# ── Coklu haber kaynagi onayi (Bing Haber + Google Haberler RSS) ───────────────────────────────────────
_AY_ADLARI = ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık"]
_AY_ARAMA_ADI = {a: i + 1 for i, a in enumerate(_AY_ADLARI)}
_AY_DESENI = re.compile(r"\b(ocak|şubat|subat|mart|nisan|mayıs|mayis|haziran|temmuz|ağustos|agustos|eylül|eylul|ekim|kasım|kasim|aralık|aralik)\w*",
                        re.IGNORECASE)
_YUZDE_YEDEK_DESENI = re.compile(r"(?:yüzde|%)\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
_TUIK_DESENI = re.compile(r"T[ÜU]İK|TUIK|T[ÜU]FE|TÜİK", re.IGNORECASE)
_ENFLASYON_IPUCU = re.compile(r"enflasyon|fiyatlar|tüketici fiyat|e-endeks", re.IGNORECASE)
_MIN_BAGIMSIZ_KAYNAK = 2
# Bahri'nin karari (12 Kasim 2026): bu alan adlari HICBIR KOSULDA kaynak sayilmaz.
_YASAKLI_KAYNAKLAR = ("halktv.com.tr",)


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


def haber_gozlemleri(ogeler: list, bugun) -> list:
    """Haber ogelerinden [(yil_ay, oran, kaynak_alan_adi)]. oge: {'title','desc','url','pub'(datetime.date)}."""
    sonuc = []
    for o in ogeler:
        pub = o.get("pub")
        if not pub or not (0 <= (bugun - pub).days <= 75):
            continue
        host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", o.get("url") or "").split("/")[0].lower())
        if not host or any(host == y or host.endswith("." + y) for y in _YASAKLI_KAYNAKLAR):
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


def _google_haberleri(sorgu: str) -> list:
    """Google Haberler RSS: baslik ('... - Kaynak' son eki atilir) + <source url> alan adi. Ozet yok (baslik tekrari)."""
    import email.utils as _eu
    try:
        r = requests.get("https://news.google.com/rss/search",
                         params={"q": sorgu + " when:45d", "hl": "tr", "gl": "TR", "ceid": "TR:tr"},
                         headers=_HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"[enag_izleme] Google Haberler HTTP {r.status_code} ({sorgu})")
            return []
    except Exception as e:
        print(f"[enag_izleme] Google Haberler cekilemedi: {type(e).__name__}: {str(e)[:120]}")
        return []
    ogeler = []
    for it in re.findall(r"<item>.*?</item>", r.text, re.S):
        t = re.search(r"<title>(.*?)</title>", it, re.S)
        src = re.search(r'<source[^>]*url="([^"]+)"', it)
        pd_ = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
        if not (t and src and pd_):
            continue
        try:
            pub = _eu.parsedate_to_datetime(pd_.group(1)).date()
        except Exception:
            continue
        baslik = re.sub(r"\s+-\s+[^-]+$", "", _html.unescape(t.group(1)))
        ogeler.append({"title": baslik, "desc": "", "url": src.group(1), "pub": pub})
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


def haberlerden_tamamla(eksik: list, bugun) -> dict:
    """Eksik aylar icin Bing Haber + Google Haberler'den {yil_ay: oran} (coklu kaynak onayli)."""
    gozlem = []
    for k in eksik:
        ay_no = int(k[5:])
        ay_adi = _AY_ADLARI[ay_no - 1]
        for sorgu in (f"ENAG {ay_adi} ayı enflasyonu açıkladı", f"ENAG {ay_adi} {k[:4]} enflasyonu aylık yüzde"):
            gozlem += haber_gozlemleri(_bing_haberleri(sorgu), bugun)
            gozlem += haber_gozlemleri(_google_haberleri(sorgu), bugun)
    return {k: v for k, v in kaynaklar_arasi_karar([g for g in gozlem if g[0] in eksik]).items()}


def calistir(bugun=None) -> int:
    """0: tamam. 1: onceki ayin ENAG orani ayin 10'undan sonra HALA yok (is kirmizi biter, GitHub bildirir)."""
    bugun = bugun or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date()
    print("[enag_izleme] Baslangic.")
    db.init_db()
    yazilan = 0
    mevcut = db.enag_oranlari_getir()
    eksik = _eksik_aylar(mevcut, bugun)
    if eksik:
        print(f"[enag_izleme] Eksik ay(lar): {eksik} - haber kaynaklari (Bing Haber + Google Haberler, "
              f"en az {_MIN_BAGIMSIZ_KAYNAK} bagimsiz site) taraniyor.")
        for k, oran in sorted(haberlerden_tamamla(eksik, bugun).items()):
            if db.enag_oran_kaydet(k, oran):
                print(f"[enag_izleme] KAYDEDILDI: {k} -> %{oran} (coklu kaynak onayli)")
                yazilan += 1
            else:
                print(f"[enag_izleme] KAYIT BASARISIZ: {k} -> %{oran}")
    if not yazilan:
        print("[enag_izleme] Bu turda yeni ENAG verisi yazilmadi.")

    onceki = f"{bugun.year - 1:04d}-12" if bugun.month == 1 else f"{bugun.year:04d}-{bugun.month - 1:02d}"
    mevcut = db.enag_oranlari_getir()
    if bugun.day >= 10 and mevcut and onceki not in mevcut and onceki >= min(mevcut):
        print(f"::error::ENAG {onceki} orani ayin {bugun.day}'unde HALA yok - hicbir kaynaktan dogrulanamadi. "
              f"Grafikteki ENAG cizgisi bu ayi 0% sayiyor.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(calistir())
