# -*- coding: utf-8 -*-
"""v2.0.7.398: pay geri alimi skor dusurme anahtari (KAP_GERI_ALIM_SKOR_DUSUR). Varsayilan KAPALI = BILGI."""
import datetime as dt
import os
import sys

import pandas as pd

import kap_risk as K

BUGUN = dt.date(2026, 10, 8)
_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def b(konu, ozet="", tarih=dt.datetime(2026, 10, 7, 18, 30), gk=(), i=1):
    return {"id": i, "tarih": tarih, "gonderen": "X", "konu": konu, "ozet": ozet,
            "gonderen_kodlar": list(gk), "ilgili_kodlar": [], "metin": ""}


def _anahtar(deger):
    if deger is None:
        os.environ.pop(K.GERI_ALIM_ANAHTAR_ENV, None)
    else:
        os.environ[K.GERI_ALIM_ANAHTAR_ENV] = deger


def test_varsayilan_kapali_bilgi():
    _anahtar(None)
    ok(not K.geri_alim_skor_dusur_acik(), "tanimsiz = kapali")
    r = K.riskleri_hesapla([b(K.K_GERI_ALIM, "Pay Geri Alım İşlemleri", gk=["ENERY"])], BUGUN)
    ok(r["ENERY"][0]["seviye"] == K.SEVIYE_BILGI, "kapaliyken BILGI (eski davranis)")
    for bos in ("", "0", "hayir", "kapali", "  "):
        _anahtar(bos)
        ok(not K.geri_alim_skor_dusur_acik(), f"'{bos}' = kapali")


def test_acikken_orta_ve_carpan():
    for deger in ("1", "true", "TRUE", "evet", "Açık", " yes "):
        _anahtar(deger)
        ok(K.geri_alim_skor_dusur_acik(), f"'{deger}' = acik")
    _anahtar("1")
    r = K.riskleri_hesapla([b(K.K_GERI_ALIM, "Pay Geri Alım İşlemleri", gk=["ENERY"])], BUGUN)
    x = r["ENERY"][0]
    ok(x["kural"] == "GERI_ALIM" and x["seviye"] == K.SEVIYE_ORTA, "acikken ORTA")
    ok("ayar gereği" in x["ad"] and "risk değil" in x["ad"], "etiket metni durust: ayar gereği, bildirim risk degil")
    ok(K.etiket(K.en_siddetli(r["ENERY"])) == K.SINYAL_KAP_ORTA, "sinyal KAP DIKKAT")
    df = pd.DataFrame({"Ticker": ["ENERY", "THYAO"], "Kategori": ["BIST", "BIST"]})
    o = K.kap_isaretle(df, r)
    ok(o.loc[0, "KAP_Seviye"] == "ORTA" and o.loc[0, "KAP_Carpan"] == 0.5, "skor carpani 0,5")
    ok("ayar gereği" in o.loc[0, "KAP_Aciklama"] and o.loc[0, "KAP_Bilgi"] == "", "etiketli aciklamada; bilgi seridinde degil")
    ok(o.loc[1, "KAP_Carpan"] == 1.0, "baska hisse etkilenmez")


def test_pencere_ve_diger_kurallar_ayni():
    _anahtar("1")
    ok(K.riskleri_hesapla([b(K.K_GERI_ALIM, "x", dt.datetime(2026, 10, 7), gk=["ENERY"])], dt.date(2026, 10, 30)) == {},
       "acikken de 14 gun sonra kalkar")
    ok(K.riskleri_hesapla([b(K.K_GERI_ALIM, "x", dt.datetime(2026, 10, 7), gk=["ENERY"])], dt.date(2026, 10, 20)) != {},
       "13 gun icinde gecerli")
    ok(K.kural_bilgisi("GERI_ALINAN_SATIS")[0] == K.SEVIYE_BILGI, "geri alinan pay satisi BILGI kalir")
    ok(K.kural_bilgisi("SERMAYE_BEDELSIZ")[0] == K.SEVIYE_BILGI, "bedelsiz BILGI kalir")
    ok(K.kural_bilgisi("VBTS_BRUT_TAKAS")[0] == K.SEVIYE_AGIR, "agir kurallar ayni")
    ok(K.KURALLAR["GERI_ALIM"][0] == K.SEVIYE_BILGI, "KURALLAR sabiti degismez (anahtar yalniz hesapta)")
    _anahtar(None)
    ok(K.kural_bilgisi("GERI_ALIM") == K.KURALLAR["GERI_ALIM"], "kapaliyken birebir sabit")


def test_agir_risk_geri_alimdan_once():
    _anahtar("1")
    r = K.riskleri_hesapla([b(K.K_GERI_ALIM, "geri alim", gk=["ATEKS"], i=1),
                            b(K.K_DENETIM_OLUMSUZ, "Denetim", dt.datetime(2026, 10, 1), gk=["ATEKS"], i=2)], BUGUN)
    ok(K.en_siddetli(r["ATEKS"]) == K.SEVIYE_AGIR, "AGIR + geri alim: en siddetli AGIR")
    df = pd.DataFrame({"Ticker": ["ATEKS"], "Kategori": ["BIST"]})
    ok(K.kap_isaretle(df, r).loc[0, "KAP_Carpan"] == 0.0, "carpan 0 (agir kazanir)")


def test_workflow_degiskeni():
    w = open(".github/workflows/kap_risk_tarama.yml", encoding="utf-8").read()
    ok("KAP_GERI_ALIM_SKOR_DUSUR: ${{ vars.KAP_GERI_ALIM_SKOR_DUSUR }}" in w, "workflow repo Variable'ini ortama verir")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    _anahtar(None)
    print(f"test_geri_alim_anahtar: {_n['ok']}/{_n['ok']} OK")
    sys.exit(0)
