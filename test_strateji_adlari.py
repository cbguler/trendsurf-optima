# -*- coding: utf-8 -*-
"""v2.0.7.404: Butce Dagilim Stratejisi secenek adlari. Calistir: python3 test_strateji_adlari.py (ag/veritabani yok)."""
import re
import sys

import portfoy_optimizasyon as P

_n = {"ok": 0}


def ok(k, m):
    assert k, "BASARISIZ: " + m
    _n["ok"] += 1


def test_adlar_ve_kodlar():
    ok(P.STRATEJI_SECENEK == {"kuresel": "Optimal Dağılım", "kategori_guvenceli": "Kategorik Dağılım"}, "secenek adlari")
    ok(P.STRATEJI_ETIKET == P.STRATEJI_SECENEK, "etiket ve secenek ayni (tek kaynak)")
    ok(P.STRATEJILER == ("kuresel", "kategori_guvenceli") and set(P.STRATEJI_ACIKLAMA) == set(P.STRATEJILER),
       "strateji KODLARI degismedi (kayitli kullanici tercihleri gecerli)")


def test_eski_ad_kalmadi():
    for f in ("app.py", "emailer.py", "emailer_standalone.py", "portfoy_optimizasyon.py"):
        s = open(f, encoding="utf-8").read()
        ok(not re.search(r"En yüksek skorlular|Her kategoriden skorlular", s), f"{f}: eski ad yok")


def test_uygulama_ve_eposta_ayni_kaynagi_kullanir():
    app = open("app.py", encoding="utf-8").read()
    em = open("emailer.py", encoding="utf-8").read()
    ok("STRATEJI_SECENEK['kuresel']" in app and "STRATEJI_SECENEK[_sonuc['strateji']]" in app, "app.py etiketleri sabitten alir")
    ok("STRATEJI_SECENEK.get(_sonuc.get('strateji')" in em, "e-posta etiketi sabitten alir")
    ok('"Bütçe Dağılım Stratejisi"' in app, "basliginin kendisi degismedi")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"test_strateji_adlari: {_n['ok']}/{_n['ok']} OK")
    sys.exit(0)
