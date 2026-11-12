# -*- coding: utf-8 -*-
"""ENAG izleme (v2.0.7.439: Halk TV kaynak olarak KALDIRILDI; yalniz coklu haber kaynagi onayi) + grafikte ay katkisi.
Calistir: python3 test_enag_kalip.py. Ag/veritabani KULLANILMAZ (sahte requests ve sahte db)."""
import ast
import datetime as dt
import sys

import pandas as pd

import enag_izleme as E

_n = {"ok": 0}


def ok(k, m):
    assert k, "BASARISIZ: " + m
    _n["ok"] += 1


class _Cevap:
    def __init__(self, metin, kod=200):
        self.text, self.status_code = metin, kod


def _seri_fonksiyonu():
    src = open("app.py", encoding="utf-8").read()
    for n in ast.parse(src).body:
        if isinstance(n, ast.FunctionDef) and n.name == "_enflasyon_gunluk_seri":
            ns = {"pd": pd}
            exec(compile(ast.Module([n], []), "app.py", "exec"), ns)
            return ns["_enflasyon_gunluk_seri"]
    raise AssertionError("_enflasyon_gunluk_seri bulunamadi")


def test_grafik_serisi_eylul_katkisi():
    f = _seri_fonksiyonu()
    gun = pd.date_range("2026-08-03", "2026-10-10")
    import datetime as _d

    class _Tarih(_d.date):
        @classmethod
        def today(cls): return _d.date(2026, 10, 10)
    import builtins  # app fonksiyonu 'import datetime as _dt_es' yapar: gercek today yerine sabit tarih icin yamala
    import datetime
    orj = datetime.date
    datetime.date = _Tarih
    try:
        s_eksik, eksik = f({"2026-08": 2.24}, gun, _d.date(2026, 8, 3))
        s_tam, eksik2 = f({"2026-08": 2.24, "2026-09": 2.10}, gun, _d.date(2026, 8, 3))
    finally:
        datetime.date = orj
    ok(eksik2 == [] and eksik == ["2026-09"], "Eylul eksikse uyari listesinde")
    ok(abs(s_eksik.iloc[-1] - 2.24) < 1e-9, "Eylul yokken cizgi son degerde duz (kullanicinin gordugu durum)")
    beklenen = ((1.0224) * (1.0210) - 1) * 100
    ok(abs(s_tam.iloc[-1] - beklenen) < 1e-9, f"Eylul varken 1 Ekim'de zincirleme sicrama: {beklenen:.4f}")
    ok(abs(s_tam.loc["2026-09-30"] - 2.24) < 1e-9 and abs(s_tam.loc["2026-10-01"] - beklenen) < 1e-9,
       "sicrama tam 1 Ekim'de")


# ── v2.0.7.438: yedek kaynak (Bing Haber) + coklu kaynak onayi + gecikme alarmi ──────────────────────
def test_cumle_ayiklama_gercek_ifadeler():
    f = E.cumleden_aylik_oran
    ok(f("Son dakika... ENAG verilerine göre ekim ayında enflasyon aylık bazda yüzde 2,68 artarken yıllık yüzde 45,12 olarak gerçekleşti.") == (10, 2.68), "Sozcu")
    ok(f("ENAG ise ekim ayı enflasyonunu yüzde 2,68, yıllık enflasyonu yüzde 45,12 olarak açıkladı.") == (10, 2.68), "T24 (yillik sonra)")
    ok(f("ENAG'ın hesaplamalarına göre, Tüketici Fiyat Endeksi (E-TÜFE) ekim ayında yüzde 2,68 artarken ...") == (10, 2.68), "E-TUFE TUIK sayilmaz")
    ok(f("ENAG ekimde aylık enflasyonu yüzde 2,68, yıllık enflasyonu yüzde 45,12 açıkladı") == (10, 2.68), "Son Dakika")
    ok(f("ENAG ekim enflasyonunu yüzde 2,68, TÜİK yüzde 2,58 olarak açıkladı") is None, "TUIK karisan cumle reddedilir")
    ok(f("Ekim ayı enflasyonu TÜİK'e göre yüzde 29,77; ENAG'a göre 45,12") is None, "TUIK + oransiz")
    ok(f("ENAG'a göre yıllık enflasyon yüzde 45,12 oldu ekim") is None, "yalniz yillik oran: aylik UYDURULMAZ")
    ok(f("ENAG ekim ayında gıda fiyatlarının yüzde 3,5, ulaşımın yüzde 4 arttığını açıkladı") is None, "iki oran belirsiz")
    ok(f("TÜİK ekim ayında enflasyon yüzde 2,58 arttı") is None, "ENAG olmayan")
    ok(f("ENAG ekim ve eylül enflasyonunu yüzde 2,5 açıkladı") is None, "iki ay belirsiz")


def test_yayin_ayi_yili():
    d = dt.date
    ok(E._yayin_ayi_yili(10, d(2026, 11, 3)) == (2026, 10), "Kasim'da Ekim")
    ok(E._yayin_ayi_yili(12, d(2027, 1, 4)) == (2026, 12), "Ocak'ta Aralik onceki yil")
    ok(E._yayin_ayi_yili(11, d(2026, 11, 3)) is None, "ayni ay (beklenti haberi) reddedilir")
    ok(E._yayin_ayi_yili(5, d(2026, 11, 3)) is None, "cok eski ay reddedilir")


def _oge(host, metin, pub=dt.date(2026, 11, 3)):
    return {"title": metin, "desc": "", "url": f"https://{host}/x", "pub": pub}


def test_coklu_kaynak_karari():
    b = dt.date(2026, 11, 12)
    m = "ENAG ekim ayında enflasyon aylık bazda yüzde 2,68 artarken yıllık yüzde 45,12 oldu."
    g = E.haber_gozlemleri([_oge("www.sozcu.com.tr", m), _oge("t24.com.tr", m), _oge("sozcu.com.tr", m)], b)
    ok(E.kaynaklar_arasi_karar(g) == {"2026-10": 2.68}, "2 bagimsiz site (www. soyulur, ayni site tekrari sayilmaz)")
    ok(E.kaynaklar_arasi_karar(E.haber_gozlemleri([_oge("sozcu.com.tr", m), _oge("sozcu.com.tr", m)], b)) == {},
       "tek site (tekrar etse de) YETERSIZ")
    ok(E.kaynaklar_arasi_karar(E.haber_gozlemleri([_oge("a.com", m), _oge("b.com", m.replace("2,68", "2,86"))], b)) == {},
       "celiskili 1-1: yazilmaz")
    ok(E.kaynaklar_arasi_karar(E.haber_gozlemleri(
        [_oge("a.com", m), _oge("b.com", m), _oge("c.com", m.replace("2,68", "2,86")),
         _oge("d.com", m.replace("2,68", "2,86"))], b)) == {}, "2'ye 2: yazilmaz")
    ok(E.kaynaklar_arasi_karar(E.haber_gozlemleri(
        [_oge("a.com", m), _oge("b.com", m), _oge("c.com", m.replace("2,68", "2,86"))], b)) == {"2026-10": 2.68},
       "2'ye 1: kabul (tek sapan kaynak onayi bozmaz, kazanan 2x desteklenir)")
    ok(E.haber_gozlemleri([_oge("a.com", m, dt.date(2026, 8, 1))], b) == [], "75 gunden eski haber yok sayilir")


def test_eksik_aylar():
    b = dt.date(2026, 11, 12)
    ok(E._eksik_aylar({"2026-08": 2.24, "2026-09": 2.1}, b) == ["2026-10"], "yalniz Ekim eksik")
    ok(E._eksik_aylar({"2026-09": 2.1}, b) == ["2026-10"], "en eski kayittan onceki aylar (Agustos) aranmaz")
    ok(E._eksik_aylar({}, b) == ["2026-08", "2026-09", "2026-10"], "bos DB: son 3 ay")
    ok(E._eksik_aylar({"2026-10": 2.68}, dt.date(2027, 1, 5)) == ["2026-11", "2026-12"], "yil asimi, Ekim zaten var")


_RSS = ('<?xml version="1.0"?><rss><channel>' + "".join(
    f"<item><title>{t}</title><link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;url=https%3a%2f%2f{h}%2fhaber-{i}&amp;c=1</link>"
    f"<description>{dsc}</description><pubDate>Tue, 03 Nov 2026 08:00:00 GMT</pubDate></item>"
    for i, (h, t, dsc) in enumerate([
        ("www.sozcu.com.tr", "Son dakika... ENAG ekim ayı enflasyon rakamlarını açıkladı", "ENAG verilerine göre ekim ayında enflasyon aylık bazda yüzde 2,68 artarken yıllık yüzde 45,12 oldu."),
        ("t24.com.tr", "ENAG açıkladı: Ekim ayı enflasyonu ne kadar oldu?", "ENAG'ın hesaplamalarına göre, Tüketici Fiyat Endeksi (E-TÜFE) ekim ayında yüzde 2,68 artarken"),
        ("evrensel.com.tr", "TÜİK ekim ayı enflasyonunu açıkladı", "TÜİK verilerine göre tüketici fiyatları ekimde yüzde 2,58 arttı."),
    ])) + "</channel></rss>")


def _akis(sayfalar, kayit0, bugun, istekler=None):
    orj_get, orj_db = E.requests.get, E.db
    kayit, yazilan = dict(kayit0), []

    class SahteDb:
        @staticmethod
        def init_db(): pass
        @staticmethod
        def enag_oranlari_getir(): return dict(kayit)
        @staticmethod
        def enag_oran_kaydet(k, o):
            kayit[k] = o; yazilan.append((k, o)); return True

    def get(url, **kw):
        if istekler is not None:
            istekler.append(url)
        if "bing.com/news" in url:
            return _Cevap(sayfalar.get("bing", ""), 200 if "bing" in sayfalar else 503)
        return _Cevap("", 403)                      # Halk TV: Cloudflare 403 (gercek durum)
    E.requests.get, E.db = get, SahteDb
    try:
        kod = E.calistir(bugun)
    finally:
        E.requests.get, E.db = orj_get, orj_db
    return kod, yazilan, kayit


def test_halktv_engelli_yedek_ekimi_yazar():
    kod, yz, kayit = _akis({"bing": _RSS}, {"2026-08": 2.24, "2026-09": 2.10}, dt.date(2026, 11, 12))
    ok(yz == [("2026-10", 2.68)], f"yalniz haber kaynaklariyla Ekim yazilir (yazilan: {yz})")
    ok(kod == 0, "yazildi: is yesil")
    kod2, yz2, _ = _akis({"bing": _RSS}, kayit, dt.date(2026, 11, 13))
    ok(yz2 == [] and kod2 == 0, "ikinci calisma idempotent")


def test_yedek_mevcut_ayi_ezmez():
    kod, yz, kayit = _akis({"bing": _RSS}, {"2026-08": 2.24, "2026-09": 2.10, "2026-10": 2.70}, dt.date(2026, 11, 12))
    ok(yz == [] and kayit["2026-10"] == 2.70 and kod == 0, "kayitli ay yedekle degistirilmez")


def test_hicbir_kaynak_yoksa_alarm():
    kod, yz, _ = _akis({}, {"2026-08": 2.24, "2026-09": 2.10}, dt.date(2026, 11, 12))
    ok(yz == [] and kod == 1, "ayin 10'undan sonra hala yoksa cikis kodu 1 (is kirmizi)")
    kod, yz, _ = _akis({}, {"2026-08": 2.24, "2026-09": 2.10}, dt.date(2026, 11, 5))
    ok(yz == [] and kod == 0, "ayin 1-9'u arasi alarm YOK (ENAG henuz aciklamamis olabilir)")
    tek = _RSS.replace("t24.com.tr", "sozcu.com.tr").replace("www.sozcu", "sozcu")
    kod, yz, _ = _akis({"bing": tek}, {"2026-08": 2.24, "2026-09": 2.10}, dt.date(2026, 11, 12))
    ok(yz == [] and kod == 1, "tek bagimsiz site: yazilmaz, alarm")


def test_halktv_kaynak_degil():
    b = dt.date(2026, 11, 12)
    m = "ENAG ekim ayında enflasyon aylık bazda yüzde 2,68 artarken yıllık yüzde 45,12 oldu."
    ok(E.haber_gozlemleri([_oge("halktv.com.tr", m), _oge("www.halktv.com.tr", m)], b) == [], "Halk TV haberleri yok sayilir")
    ok(E.kaynaklar_arasi_karar(E.haber_gozlemleri([_oge("halktv.com.tr", m), _oge("sozcu.com.tr", m)], b)) == {},
       "Halk TV + 1 site: onay SAYILMAZ (tek gecerli kaynak)")
    ok(E.kaynaklar_arasi_karar(E.haber_gozlemleri([_oge("halktv.com.tr", m), _oge("a.com", m), _oge("b.com", m)], b))
       == {"2026-10": 2.68}, "diger iki site yine yeterli")
    ist = []
    _akis({"bing": _RSS}, {"2026-08": 2.24, "2026-09": 2.10}, dt.date(2026, 11, 12), ist)
    ok(ist and not any("halktv" in u for u in ist), "Halk TV'ye HIC istek atilmaz")
    kaynak = open("enag_izleme.py", encoding="utf-8").read()
    ok("halktv.com.tr/enflasyon" not in kaynak and "_enag_haberini_bul" not in kaynak, "Halk TV'ye ozgu kod kalmadi")


def test_workflow_kirmizi_biter_ve_not():
    w = open(".github/workflows/enag_izleme.yml", encoding="utf-8").read()
    ok("python enag_izleme.py" in w, "workflow betigi cagirir (cikis kodu is durumunu belirler)")


if __name__ == "__main__":
    for ad, fn in list(globals().items()):
        if ad.startswith("test_"):
            fn()
    print(f"test_enag_kalip: {_n['ok']}/{_n['ok']} OK")
    sys.exit(0)
