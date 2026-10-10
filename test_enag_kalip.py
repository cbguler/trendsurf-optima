# -*- coding: utf-8 -*-
"""v2.0.7.400: ENAG izleme - Halk TV metin kalibi degisimine dayanikli ayiklama + grafikte Eylul katkisi.
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


def test_eski_ve_yeni_kalip():
    eski = ("Son dakika... ENAG Ağustos 2026 enflasyonunu açıkladı. Buna göre aylık enflasyon yüzde 2,24 artarken "
            "yıllık yüzde 49,03 oldu.")
    yeni = ("Son dakika verisi geldi... ENAG Eylül 2026 enflasyonunu açıkladı. ENAG&#039;a göre eylülde fiyatlar "
            "yüzde 2,10 artarken, yıllık artış yüzde 46,61 oldu.")
    ok(E.metinden_oran_cikar(eski) == (8, 2026, 2.24), "eski kalip: Agustos 2,24")
    ok(E.metinden_oran_cikar(yeni) == (9, 2026, 2.10), "yeni kalip (HTML varlikli): Eylul 2,10, yillik 46,61 degil")


def test_reddedilenler():
    ok(E.metinden_oran_cikar("")[0] is None and E.metinden_oran_cikar(None)[0] is None, "bos metin")
    ok(E.metinden_oran_cikar("ENAG Eylül 2026 enflasyonunu açıkladı. Yıllık yüzde 46,61 oldu.")[0] is None,
       "yalniz yillik oran varsa aylik UYDURULMAZ")
    ok(E.metinden_oran_cikar("ENAG Eylül 2026 enflasyonunu açıkladı. Fiyatlar yüzde 2,10 ve yüzde 3,00 arttı, yıllık yüzde 40 oldu.")[0] is None,
       "aylik parcada iki oran: belirsiz, reddedilir")
    ok(E.metinden_oran_cikar("ENAG Eylül 2026 enflasyonunu açıkladı. Fiyatlar yüzde 45 artarken yıllık yüzde 46 oldu.")[0] is None,
       "makul aralik disi (>=30) reddedilir")
    ok(E.metinden_oran_cikar("ENAG Fooay 2026 enflasyonunu açıkladı. Fiyatlar yüzde 2,1 artarken yıllık yüzde 46 oldu.")[0] is None,
       "taninmayan ay adi reddedilir")
    ok(E.metinden_oran_cikar("TÜİK Eylül 2026 enflasyonunu açıkladı. Fiyatlar yüzde 2,1 arttı, yıllık yüzde 30 oldu.")[0] is None,
       "ENAG olmayan haber reddedilir")


class _Cevap:
    def __init__(self, metin, kod=200):
        self.text, self.status_code = metin, kod


def _sahte_requests(sayfalar):
    def get(url, **kw):
        return _Cevap(sayfalar.get(url, ""), 200 if url in sayfalar else 404)
    return get


def test_akis_ve_idempotans():
    kok = "https://halktv.com.tr"
    etiket = kok + "/enflasyon"
    a_ey = kok + "/ekonomi/son-dakika-enag-eylul-ayi-enflasyonunu-acikladi-1059437h"
    a_ag = kok + "/ekonomi/son-dakika-enag-acikladi-ilk-enflasyon-verisi-geldi-1052768h"
    sayfalar = {
        etiket: f'<a href="{a_ey}">x</a><a href="{a_ey}">y</a><a href="{a_ag}">z</a>',
        a_ey: '<meta name="description" content="Son dakika... ENAG Eylül 2026 enflasyonunu açıkladı. ENAG&#039;a göre eylülde fiyatlar yüzde 2,10 artarken, yıllık artış yüzde 46,61 oldu.">',
        a_ag: '<meta name="description" content="Son dakika... ENAG Ağustos 2026 enflasyonunu açıkladı. Buna göre aylık enflasyon yüzde 2,24 artarken yıllık yüzde 49,03 oldu.">',
    }
    ok(E._enag_haberini_bul.__doc__ is not None, "dokuman")
    orj_get, orj_db = E.requests.get, E.db
    kayit = {"2026-08": 2.24}
    yazilan = []

    class SahteDb:
        @staticmethod
        def init_db(): pass
        @staticmethod
        def enag_oranlari_getir(): return dict(kayit)
        @staticmethod
        def enag_oran_kaydet(k, o):
            kayit[k] = o; yazilan.append((k, o)); return True

    E.requests.get, E.db = _sahte_requests(sayfalar), SahteDb
    try:
        ok(E._enag_haberini_bul(etiket, kok) == [a_ey, a_ag], "adaylar sirali ve tekil")
        E.calistir()
        ok(yazilan == [("2026-09", 2.10)], f"yalniz eksik Eylul yazilir, Agustos zaten var (yazilan: {yazilan})")
        yazilan.clear()
        E.calistir()
        ok(yazilan == [], "ikinci calistirma hicbir sey yazmaz (idempotent)")
    finally:
        E.requests.get, E.db = orj_get, orj_db


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


if __name__ == "__main__":
    for ad, fn in list(globals().items()):
        if ad.startswith("test_"):
            fn()
    print(f"test_enag_kalip: {_n['ok']}/{_n['ok']} OK")
    sys.exit(0)
