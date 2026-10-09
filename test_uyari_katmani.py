# -*- coding: utf-8 -*-
"""v2.0.7.380: uyari_katmani.py (tedbir/KAP/SINIRLI VERI ortak katmani) + e-posta etiketleri + optimizer.
Calistir: python test_uyari_katmani.py. Ag/veritabani KULLANILMAZ (db fonksiyonlari sahteyle degistirilir)."""
import ast
import datetime as dt
import sys

import pandas as pd

import uyari_katmani as U

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def _df():
    return pd.DataFrame([
        {"Ticker": "AAA", "Ad": "A", "Kategori": "BIST", "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0, "Vol": 30.0,
         "Optima_Skor": 85.0, "Gecmis_Gun": 500.0},
        {"Ticker": "KAPA", "Ad": "K", "Kategori": "BIST", "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0, "Vol": 30.0,
         "Optima_Skor": 85.0, "Gecmis_Gun": 500.0},
        {"Ticker": "KAPO", "Ad": "K2", "Kategori": "BIST", "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0, "Vol": 30.0,
         "Optima_Skor": 90.0, "Gecmis_Gun": 500.0},
        {"Ticker": "YENI", "Ad": "Y", "Kategori": "BIST", "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0, "Vol": 30.0,
         "Optima_Skor": 85.0, "Gecmis_Gun": 66.0},
        {"Ticker": "TDBR", "Ad": "T", "Kategori": "BIST", "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0, "Vol": 30.0,
         "Optima_Skor": 85.0, "Gecmis_Gun": 500.0},
        {"Ticker": "FON1", "Ad": "BIR FON", "Kategori": "TEFAS", "Son_Fiyat": 1.0, "RSI": 50.0, "Ret1M": 5.0,
         "Vol": 5.0, "Optima_Skor": 85.0, "Gecmis_Gun": None},
    ])


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


def test_katman_davranisi():
    db, orj = _sahte_db()
    try:
        d = U.uyari_katmanini_uygula(_df()).set_index("Ticker")
    finally:
        _geri(db, orj)
    ok(d.loc["AAA", "Piyasa_Tedbiri"] == "" and d.loc["AAA", "Optima_Skor"] == 85.0 and not d.loc["AAA", "Veri_Sinirli"],
       "etiketsiz hisse aynen kalir")
    ok(d.loc["TDBR", "Piyasa_Tedbiri"] != "" and d.loc["TDBR", "Optima_Skor"] == 0.0, "tedbirli: etiket + skor 0")
    ok(d.loc["KAPA", "Piyasa_Tedbiri"] == "KAP UYARISI" and d.loc["KAPA", "Optima_Skor"] == 0.0, "KAP UYARISI: skor 0")
    ok(d.loc["KAPO", "Piyasa_Tedbiri"] == "KAP DİKKAT" and d.loc["KAPO", "Optima_Skor"] == 45.0, "KAP DIKKAT: skor x0.5")
    ok(bool(d.loc["YENI", "Veri_Sinirli"]) and d.loc["YENI", "Optima_Skor"] == 85.0, "66 gun -> sinirli, skor degismez")
    ok(not d.loc["FON1", "Veri_Sinirli"], "TEFAS asla sinirli veri degil")


def test_ikinci_uygulama_cifte_islemez():
    db, orj = _sahte_db()
    try:
        d1 = U.uyari_katmanini_uygula(_df())
        d2 = U.uyari_katmanini_uygula(d1.copy())
    finally:
        _geri(db, orj)
    ok(list(d1["Optima_Skor"]) == list(d2["Optima_Skor"]), "KAP carpani ikinci uygulamada tekrar islenmez")


def test_db_hatasinda_df_doner():
    import db
    orj = (db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri)

    def patla():
        raise RuntimeError("db yok")
    db.get_aktif_piyasa_tedbirleri = patla
    db.get_aktif_kap_riskleri = patla
    try:
        d = U.uyari_katmanini_uygula(_df())
    finally:
        _geri(db, orj)
    ok(len(d) == 6 and "Veri_Sinirli" in d.columns and bool(d.set_index("Ticker").loc["YENI", "Veri_Sinirli"]),
       "tedbir/KAP adimlari atlansa da df doner, sinirli veri yine hesaplanir")
    ok(U.uyari_katmanini_uygula(None) is None, "None -> None")


def test_sinyal_etiketi():
    row = pd.Series({"Piyasa_Tedbiri": "KAP DİKKAT"})
    ok(U.get_signal_row(row, 90, 50, "YUKSELIS") == ("KAP DİKKAT", "sig-kap-orta"), "tedbir etiketi onceliklidir")
    ok(U.get_signal_row(pd.Series({"Veri_Sinirli": True}), 90, 50, "YUKSELIS") == ("TUT İZLE", "sig-t"), "sinirli: AL -> TUT IZLE")
    ok(U.get_signal_row(pd.Series({"Veri_Sinirli": False}), 90, 50, "YUKSELIS")[0] == "GÜÇLÜ AL", "sinirsiz: GUCLU AL")
    ok(U.get_signal_row(None, 70, 50, "YUKSELIS")[0] == "KADEMELİ AL", "satir yoksa saf get_signal")
    # app.py'deki SIG_COLORS ile ayni renkler (tek kaynak sapmasin)
    src = open("app.py", encoding="utf-8").read()
    for n in ast.parse(src).body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SIG_COLORS":
            ok(ast.literal_eval(n.value) == U.SINYAL_RENK, "app.SIG_COLORS == uyari_katmani.SINYAL_RENK")
            break
    else:
        ok(False, "SIG_COLORS bulunamadi")


def test_eposta_etiketleri():
    import emailer as E
    db, orj = _sahte_db()
    try:
        d = U.uyari_katmanini_uygula(_df())
    finally:
        _geri(db, orj)
    def et(t):
        r = E._satir_bul(d, t, "BIST")
        return E._sinyal_ve_renk(r, E._optima_score(r) if E._optima_score(r) else 0.0)[0]
    ok(et("AAA") == "GÜÇLÜ AL", "etiketsiz hisse: e-postanin mevcut eslemesi")
    ok(et("KAPA") == "KAP UYARISI", "KAP UYARISI e-postada gorunur (skor 0 olsa da)")
    ok(et("KAPO") == "KAP DİKKAT", "KAP DIKKAT e-postada gorunur")
    ok(et("YENI") == "TUT İZLE", "sinirli veri: e-postada AL yok")
    ok(et("TDBR") not in ("GÜÇLÜ AL", "KADEMELİ AL", "SAT", "—"), "tedbir etiketi e-postada")
    ok(E._sinyal_ve_renk(None, 85.0)[0] == "GÜÇLÜ AL", "satir yoksa eski davranis")
    ok(E._satir_bul(d, "FON1", "BIST") is None and E._satir_bul(d, "FON1", "TEFAS") is not None, "kategori eslesmesi")
    # portfoy bolumu: tedbirli pozisyon etiketle, veri-yok pozisyon "—"
    html = E._build_portfolio_section(
        [{"ticker": "KAPA", "adet": 10, "maliyet": 5.0, "asset_type": "BIST"},
         {"ticker": "YOKTUR", "adet": 1, "maliyet": 1.0, "asset_type": "BIST"}], d)
    ok("KAP UYARISI" in html.replace("<br>", " "), "portfoy bolumunde KAP UYARISI (skor 0 olsa da etiket gorunur)")
    ok("<b>0</b>" in html, "KAP UYARISI satirinda skor 0 gosterilir")
    yok_satir = html[html.index("YOKTUR"):]
    ok("—" in yok_satir.split("</tr>")[0], "tabloda olmayan pozisyon: eski davranis (—)")
    ok(E._optima_score(E._satir_bul(d, "KAPA", "BIST")) == 0.0, "KAP UYARISI satirinda skor 0 (yedek formul 0'i yeniden hesaplamaz)")
    ok(E._optima_score(E._satir_bul(d, "AAA", "BIST")) == 85.0, "etiketsiz satirda skor aynen")
    nosc = pd.Series({"Ticker": "Z", "RSI": 50.0, "Ret1M": 1.0, "Vol": 30.0, "Optima_Skor": 0.0})
    ok(E._optima_score(nosc) > 0, "etiketsiz ve skoru 0 olan satirda eski yedek formul korunur")


def test_optimizer_etiketliyi_onermez():
    import portfoy_optimizasyon as P
    db, orj = _sahte_db()
    try:
        d = U.uyari_katmanini_uygula(_df())
    finally:
        _geri(db, orj)
    s = P.optimize_portfolio(d, 100000, {"BIST": 1.0}, 5)
    sec = {x["ticker"] for x in s["secilenler"]}
    ok(sec == {"AAA"}, f"yalniz etiketsiz+yeterli gecmisli hisse onerilir (secilen: {sec})")
    s2 = P.optimize_portfolio(d, 100000, {"BIST": 1.0}, 5, watchlist_mode=True)
    ok({"AAA", "YENI"} <= {x["ticker"] for x in s2["secilenler"]}, "izleme listesi modunda sinirli veri hissesi kullanici icin listelenir")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"uyari_katmani testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
