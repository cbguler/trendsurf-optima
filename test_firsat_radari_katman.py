# -*- coding: utf-8 -*-
"""v2.0.7.419: Firsat Radari alarm skoru = uygulamada gorunen skor (yas/tedbir/KAP katmani).
Calistir: python3 test_firsat_radari_katman.py. Ag/veritabani KULLANILMAZ (db fonksiyonlari sahteyle degistirilir)."""
import datetime as dt
import sys
import warnings
warnings.filterwarnings("ignore")

import pandas as pd

import firsat_radari as R
import uyari_katmani as U

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def _satir(t, kat, gun=900.0, kademe=None, ad="X"):
    return {"Ticker": t, "Ad": ad, "Kategori": kat, "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0,
            "Vol": 30.0, "Optima_Skor": None, "Gecmis_Gun": gun, "Yas_Kademe": kademe}


def _uni():
    return pd.DataFrame([
        _satir("ESKI", "BIST", 900),           # 3 yil+  -> x1,00
        _satir("B1", "BIST", 400),             # 1-2 yil -> x0,80
        _satir("B2", "BIST", 600),             # 2-3 yil -> x0,90
        _satir("B0", "BIST", 100),             # 1 yildan genc -> x0,70 + sinirli
        _satir("C0", "KRIPTO", 200),           # kripto kademe 0
        _satir("C1", "KRIPTO", 400),           # kripto 1-2 yil (365 gun = 1 yil)
        _satir("KAPA", "BIST", 900),           # KAP AGIR -> 0
        _satir("KAPO", "BIST", 400),           # KAP ORTA (x0,5) + yas x0,8 -> x0,4
        _satir("TDBR", "BIST", 900),           # tedbir -> 0
        _satir("F1", "TEFAS", None, kademe=1, ad="BIR FON"),
        _satir("F0", "TEFAS", None, kademe=0, ad="GENC FON"),
        _satir("FX", "TEFAS", None, kademe=None, ad="BILINMEYEN"),
    ])


def _sonuc(skor=90.0):
    return {r["Ticker"]: {"kategori": r["Kategori"], "skor": skor, "fiyat": 10.0, "rsi": 50.0, "ret1m": 5.0}
            for r in _uni().to_dict("records")}


def _sahte_db():
    import db
    tedbir = [{"eslesme_turu": "TICKER", "deger": "TDBR", "tedbir_turu": "BRUT_TAKAS"}]
    riskler = {
        "KAPA": [{"kural": "DENETIM_OLUMSUZ", "seviye": "AGIR", "ad": "Denetim", "tarih": dt.datetime(2026, 9, 1)}],
        "KAPO": [{"kural": "VBTS_ACIGA_SATIS", "seviye": "ORTA", "ad": "VBTS", "tarih": dt.datetime(2026, 9, 14)}],
    }
    orj = (getattr(db, "get_aktif_piyasa_tedbirleri", None), getattr(db, "get_aktif_kap_riskleri", None))
    db.get_aktif_piyasa_tedbirleri = lambda: tedbir
    db.get_aktif_kap_riskleri = lambda: riskler
    return db, orj


def _geri(db, orj):
    db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj


def _carpanlar():
    db, orj = _sahte_db()
    try:
        return R._katman_carpanlari(_uni(), _sonuc())
    finally:
        _geri(db, orj)


def test_carpanlar():
    c, s = _carpanlar()
    g = lambda kat, t: c.get((kat, t))
    ok(g("BIST", "ESKI") == 1.0, "3 yil+ BIST carpan 1,0")
    ok(g("BIST", "B1") == 0.8 and g("BIST", "B2") == 0.9 and g("BIST", "B0") == 0.7, "BIST kademe carpanlari 0,8/0,9/0,7")
    ok(g("KRIPTO", "C0") == 0.7 and g("KRIPTO", "C1") == 0.8, "KRIPTO kademe carpanlari")
    ok(g("BIST", "KAPA") == 0.0 and g("BIST", "TDBR") == 0.0, "KAP AGIR ve tedbir carpani 0")
    ok(abs(g("BIST", "KAPO") - 0.4) < 1e-9, "KAP ORTA x0,5 ile yas x0,8 birlesir = 0,4")
    ok(g("TEFAS", "F1") == 0.8 and g("TEFAS", "F0") == 0.7, "TEFAS Yas_Kademe carpani")
    ok(g("TEFAS", "FX") == 1.0, "yasi bilinmeyen fon: carpan 1,0 (dokunulmaz)")
    ok(s == {("BIST", "B0"), ("KRIPTO", "C0"), ("TEFAS", "F0")}, f"sinirli veri kumesi yalniz kademe 0: {s}")


def test_uygulamayla_ayni_skor():
    """Radarin etkin skoru == uygulamanin gosterecegi skor (ayni ham skordan)."""
    c, _ = _carpanlar()
    ham = 88.0
    db, orj = _sahte_db()
    try:
        d = _uni()
        d["Optima_Skor"] = ham
        d = U.uyari_katmanini_uygula(d)
    finally:
        _geri(db, orj)
    for _, r in d.iterrows():
        beklenen = round(ham * c[(r["Kategori"], r["Ticker"])], 1)
        ok(abs(float(r["Optima_Skor"]) - beklenen) < 0.051,
           f"{r['Ticker']}: uygulama {r['Optima_Skor']} radar {beklenen}")


def test_alarm_ham_degil_etkin_skorla():
    c, s = _carpanlar()
    sonuc = _sonuc(90.0)
    # onceden hicbiri kayitli degil: ham 90 >= 85 esik -> eskiden HEPSI alarm olurdu
    tetik = R._radar_tetikleyicileri(sonuc, {}, {}, c, s)
    kimler = {t for t, *_ in tetik}
    # B2: 90*0,9 = 81 < 85 -> alarm OLMAMALI
    ok("B2" not in kimler, "B2 etkin 81 < 85: alarm yok")
    ok("B1" not in kimler and "KAPO" not in kimler and "KAPA" not in kimler and "TDBR" not in kimler,
       "yas/KAP/tedbirle dusen varliklar alarm uretmez")
    ok("B0" not in kimler and "C0" not in kimler and "F0" not in kimler, "sinirli veri alarm uretmez")
    ok(kimler == {"ESKI", "FX"}, f"alarm: yalniz carpani 1 olanlar (ESKI, FX): {kimler}")
    # carpansiz (eski davranis) hepsi alarm
    eski_dav = {t for t, *_ in R._radar_tetikleyicileri(sonuc, {}, {})}
    ok(len(eski_dav) == len(sonuc), "carpan verilmezse ESKI davranis (ham skor, hepsi alarm)")


def test_esik_kesisi_etkin_skorla_tutarli():
    c, s = _carpanlar()
    # ESKI carpan 1: onceki 80 -> yeni 90 esigi keser
    # B2 carpan 0,9: onceki ham 95, yeni ham 98: etkin 85.5 / 88.2 -> onceki zaten >= 85 -> ESIK kesisi YOK
    sonuc = {"B2": {"kategori": "BIST", "skor": 98.0, "fiyat": 10.0, "rsi": 50.0, "ret1m": 5.0}}
    onceki = {"B2": (95.0, None)}
    ok(R._radar_tetikleyicileri(sonuc, onceki, {}, c, s) == [], "ham 95 -> 98 (etkin 85,5 -> 88,2): zaten esik ustunde, alarm yok")
    # onceki ham 90 (etkin 81) -> yeni ham 96 (etkin 86,4): esigi etkin skorla keser -> alarm, skorlar etkin
    sonuc["B2"]["skor"] = 96.0
    onceki = {"B2": (90.0, None)}
    t = R._radar_tetikleyicileri(sonuc, onceki, {}, c, s)
    ok(len(t) == 1 and t[0][1] == "esik", "etkin 81 -> 86,4 esigi keser")
    ok(t[0][2] == 86.4 and t[0][3] == 81.0, f"alarm etkin skorlari tasir: {t[0][2:4]}")
    ok(t[0][4].get("ham_skor") == 96.0 and t[0][4].get("carpan") == 0.9, "mail icin ham skor ve carpan notu")
    ok(sonuc["B2"]["skor"] == 96.0 and "ham_skor" not in sonuc["B2"], "Supabase'e yazilan kayit (sonuc) HAM kalir")


def test_katman_calismazsa_eski_davranis():
    def patlayan(df):
        raise RuntimeError("katman yok")
    c, s = R._katman_carpanlari(_uni(), _sonuc(), katman=patlayan)
    ok(c == {} and s == set(), "katman hata verirse bos sonuc")
    tetik = R._radar_tetikleyicileri(_sonuc(90.0), {}, {}, c, s)
    ok(len(tetik) == len(_sonuc()), "katman yoksa alarm KAYBOLMAZ (ham skor)")
    c2, s2 = R._katman_carpanlari(_uni(), {})
    ok(c2 == {} and s2 == set(), "bos sonuc")


def test_mail_ham_skor_notu():
    import re
    kaynak = open("firsat_radari.py", encoding="utf-8").read()
    ok("(ham {v['ham_skor']:.1f}, x{v['carpan']:.2f})" in kaynak, "mail satirinda ham skor notu")
    ok("INSERT INTO intraday_scores" in kaynak and "_upsert(conn, sonuc)" in kaynak,
       "upsert hala sonuc (ham) uzerinden")
    ok("_radar_tetikleyicileri(sonuc, onceki, ad_map, _carpan, _sinirli)" in kaynak, "main carpani tetikleyiciye geciriyor")


if __name__ == "__main__":
    for ad, fn in sorted(globals().items()):
        if ad.startswith("test_") and callable(fn):
            fn()
    print(f"{_n['ok']} kontrol gecti")
    print("TUM TESTLER GECTI")
