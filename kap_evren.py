# -*- coding: utf-8 -*-
"""
kap_evren.py - KAP'in resmi "BIST sirketleri" listesinden hisse evrenini TAMAMLAMA mantigi.

v2.0.7.374 (8 Ekim 2026, Bahri'nin bulgusu): KAP risk taramasi (v2.0.7.373) CITAS, EKIM, GOLDA,
KPEKS, ORZAX, ALBTN, KARCL, MASFN, QUICK, TKNKA icin bildirim buldu ama bu hisseler uygulamanin
evreninde yoktu (worker.py'deki sabit 771'lik liste + XHARZ'dan gelen dinamik liste kapsamiyordu).
Uyari gosterilecek satir olmadigi icin kullanici bu hisselerin risklerini goremiyordu.

Bu modul SAF mantiktir (streamlit/pandas/yfinance'e bagimli degil, ag erisimi sadece
`kap_bist_listesini_cek` icinde):
  - kap_bist_listesini_ayristir(html)  : KAP sayfasindan (kodlar, ad, slug) kayitlari
  - kap_bist_listesini_cek()           : canli sayfa, SAGLIK KONTROLLU (sayfa yapisi degisirse
                                         bos liste degil HATA verir - sessiz "hic eksik yok" olmaz)
  - eksik_adaylar(kap, mevcut, diger)  : evrende olmayan kodlar + baska kategoriyle cakisanlar
"""
import html as _html
import re
import time

KAP_BIST_URL = "https://kap.org.tr/tr/bist-sirketler"

# Sayfa su an ~710 satir dondurur. Bunun cok altinda bir sonuc, sayfa yapisinin degistigi
# anlamina gelir - o durumda hicbir sey eklenmez ve hata acikca bildirilir.
MIN_BEKLENEN_SATIR = 500

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# <a href="/tr/sirket-bilgileri/ozet/{slug}"><div>KODLAR</div></a></td><td ...><a ...>AD</a>
_SATIR = re.compile(
    r'<a href="/tr/sirket-bilgileri/ozet/([a-z0-9\-]+)"><div>([^<]*)</div></a></td>'
    r'\s*<td[^>]*>\s*<a href="[^"]*">([^<]*)</a>',
    re.S,
)


class KapListeHata(Exception):
    pass


def _kodlari_ayir(s) -> list:
    out = []
    for k in re.split(r"[,\s]+", str(s or "").strip()):
        k = k.strip().upper()
        if k and k not in out:
            out.append(k)
    return out


def kap_bist_listesini_ayristir(html_metni: str) -> list:
    """[{'kodlar': [..], 'ad': str, 'slug': str}, ...] - sayfa sirasiyla."""
    sonuc = []
    for slug, kodlar, ad in _SATIR.findall(html_metni or ""):
        kodlar = _kodlari_ayir(_html.unescape(kodlar))
        if not kodlar:
            continue
        sonuc.append({"kodlar": kodlar,
                      "ad": re.sub(r"\s+", " ", _html.unescape(ad)).strip(),
                      "slug": slug})
    return sonuc


def kap_bist_listesini_cek(deneme: int = 3) -> list:
    """Canli KAP BIST sirket listesi. Hata/yapi degisikligi -> KapListeHata (sessiz bos liste YOK)."""
    import requests
    son = ""
    for i in range(1, deneme + 1):
        try:
            r = requests.get(KAP_BIST_URL, headers=_HEADERS, timeout=40)
            if r.status_code == 200:
                kayitlar = kap_bist_listesini_ayristir(r.text)
                if len(kayitlar) < MIN_BEKLENEN_SATIR:
                    raise KapListeHata(
                        f"KAP BIST listesi beklenenden kisa ({len(kayitlar)} < {MIN_BEKLENEN_SATIR}); "
                        f"sayfa yapisi degismis olabilir")
                return kayitlar
            son = f"HTTP {r.status_code}"
        except KapListeHata:
            raise
        except Exception as e:
            son = f"{type(e).__name__}: {e}"
        time.sleep(5 * i)
    raise KapListeHata(f"KAP BIST listesi cekilemedi: {son}")


def eksik_adaylar(kap_kayitlari: list, mevcut, diger_kategori_kodlari=()) -> tuple:
    """KAP listesinde olup evrende (mevcut) bulunmayan kodlar.

    Donus: (adaylar, cakisanlar)
      adaylar   : [{'ticker','ad','slug'}] - sirali, tekil
      cakisanlar: baska kategoriyle (KRIPTO/DOVIZ/MADEN/TEFAS) ayni koda sahip olanlar - EKLENMEZ
                  (sessiz veri kaybi olmasin diye cagiran taraf bunlari acikca loglamali)
    """
    mevcut = {str(t).upper() for t in mevcut}
    diger = {str(t).upper() for t in diger_kategori_kodlari}
    adaylar, cakisanlar, goruldu = [], [], set()
    for k in kap_kayitlari:
        for t in k["kodlar"]:
            if t in goruldu or t in mevcut:
                continue
            goruldu.add(t)
            if len(t) < 2 or len(t) > 8 or not t.isalnum():
                continue
            if t in diger:
                cakisanlar.append(t)
                continue
            adaylar.append({"ticker": t, "ad": k["ad"][:200], "slug": k["slug"]})
    adaylar.sort(key=lambda a: a["ticker"])
    return adaylar, sorted(cakisanlar)
