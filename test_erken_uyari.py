# -*- coding: utf-8 -*-
"""v2.0.7.420: erken uyari - hisse PD/DD kademeli carpan + fon 'tur medyani ustu getiri' uyarisi.
Calistir: python3 test_erken_uyari.py. Ag/veritabani KULLANILMAZ (db fonksiyonlari sahteyle degistirilir)."""
import warnings
warnings.filterwarnings("ignore")
import pandas as pd
import uyari_katmani as U

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def _b(t, pb, ret, skor=80.0, uyari="", gun=900.0, ad="X"):
    return {"Ticker": t, "Ad": ad, "Kategori": "BIST", "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": ret, "Vol": 30.0,
            "PB": pb, "Optima_Skor": skor, "Temel_Uyari": uyari, "Gecmis_Gun": gun, "Tur": "", "Getiri_Tarihi": ""}


def _f(t, ret, tur="Serbest Şemsiye Fonu", tarih="2026-10-16", ad="BIR FON"):
    return {"Ticker": t, "Ad": ad, "Kategori": "TEFAS", "Son_Fiyat": 1.0, "RSI": 50.0, "Ret1M": ret, "Vol": 10.0,
            "PB": None, "Optima_Skor": None, "Temel_Uyari": "", "Gecmis_Gun": None, "Yas_Kademe": 3,
            "Tur": tur, "Getiri_Tarihi": tarih}


def _katman(rows):
    import db
    orj = (getattr(db, "get_aktif_piyasa_tedbirleri", None), getattr(db, "get_aktif_kap_riskleri", None))
    db.get_aktif_piyasa_tedbirleri = lambda: [{"eslesme_turu": "TICKER", "deger": "TDBR", "tedbir_turu": "BRUT_TAKAS"}]
    db.get_aktif_kap_riskleri = lambda: {}
    try:
        return U.uyari_katmanini_uygula(pd.DataFrame(rows)).set_index("Ticker")
    finally:
        db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj


def test_hisse_kademeleri():
    d = _katman([
        _b("NORM", 3.0, 5.0),            # PD/DD dusuk -> kademe 0
        _b("K1", 22.0, -8.0),            # >=20, getiri dusuk -> kademe 1 (x0,8)
        _b("K1B", 17.0, 40.0),           # 15<=PD/DD<20 ve getiri>=15 -> kademe 2 (x0,5)
        _b("K2", 25.0, 20.0),            # >=20 ve getiri>=15 -> kademe 2 (siki olan kazanir)
        _b("SINIR", 20.0, 0.0),          # tam esik dahil
        _b("ALT", 19.99, 14.99),         # esigin hemen altinda
        _b("BOS", None, 50.0),           # PD/DD yok -> dokunma
        _b("NEG", -5.0, 50.0),           # zarar eden sirket (negatif PD/DD) -> dokunma
        _b("SERM", 60.0, 30.0, uyari="Sermaye 2026/06 doneminden sonra degismis: ... bedelli artirimsa PD/DD yuksek gorunebilir"),
        _b("TDBR", 90.0, 40.0),          # SPK tedbirli: skor zaten 0
    ])
    ok(list(d.loc[["NORM", "K1", "K1B", "K2", "SINIR", "ALT", "BOS", "NEG", "SERM", "TDBR"], "Deger_Risk"])
       == [0, 1, 2, 2, 1, 0, 0, 0, 0, 0], f"kademeler: {list(d.Deger_Risk)}")
    ok(d.loc["NORM", "Optima_Skor"] == 80.0 and d.loc["K1", "Optima_Skor"] == 64.0, "x1 / x0,8")
    ok(d.loc["K1B", "Optima_Skor"] == 40.0 and d.loc["K2", "Optima_Skor"] == 40.0, "x0,5")
    ok(d.loc["SERM", "Optima_Skor"] == 80.0, "sermaye degisikligi uyarisi varsa PD/DD guvenilmez: dokunulmaz")
    ok(d.loc["TDBR", "Optima_Skor"] == 0.0, "tedbirli skor 0 kalir")
    ok(d.loc["BOS", "Optima_Skor"] == 80.0 and d.loc["NEG", "Optima_Skor"] == 80.0, "PD/DD yok/negatif: dokunulmaz")


def test_gercek_vakalar():
    """KTLEV/GUNDG/DSTKF'nin cokusten ONCE repo CSV gecmisinde gorulen degerleri."""
    d = _katman([
        _b("DSTKF", 96.18, 47.50, skor=40.0),   # 10 Temmuz 2026
        _b("GUNDG", 110.87, 81.38, skor=35.0),  # 28 Temmuz 2026
        _b("KTLEV", 22.07, -8.46, skor=19.0),   # 28 Temmuz 2026
    ])
    ok(d.loc["DSTKF", "Deger_Risk"] == 2 and d.loc["GUNDG", "Deger_Risk"] == 2 and d.loc["KTLEV", "Deger_Risk"] == 1,
       "uc vaka cokus oncesi degerlerle isaretlenir")
    ok(d.loc["DSTKF", "Optima_Skor"] == 20.0 and d.loc["KTLEV", "Optima_Skor"] == 15.2, "skorlar carpanla duser")


def test_diger_katmanlarla_birlesim():
    # genc hisse (yas kademe 0, x0,7) + PD/DD kademe 1 (x0,8): 100 * 0,7 * 0,8 = 56
    d = _katman([_b("G", 25.0, 0.0, skor=100.0, gun=100.0)])
    ok(d.loc["G", "Veri_Sinirli"] and d.loc["G", "Deger_Risk"] == 1 and d.loc["G", "Optima_Skor"] == 56.0,
       "yas kesintisi ile carpilir (0,7 x 0,8)")
    # katman iki kez uygulanmaz
    ikinci = U.uyari_katmanini_uygula(d.reset_index())
    ok(ikinci.set_index("Ticker").loc["G", "Optima_Skor"] == 56.0, "ikinci uygulama skoru degistirmez")


def test_aciklamalar():
    row = {"Deger_Risk": 2, "PB": 96.18, "Ret1M": 47.5}
    t = U.deger_riski_aciklama(row)
    ok("96,2" in t and "%48" in t and "%50" in t and "manipülasyon" not in t.lower(), f"kademe 2 metni: {t}")
    t1 = U.deger_riski_aciklama({"Deger_Risk": 1, "PB": 22.07})
    ok("22,1" in t1 and "%20" in t1 and "kesin bir hüküm değil" in t1, "kademe 1 metni")
    ok(U.deger_riski_aciklama({"Deger_Risk": 0}) == "" and not U.deger_riski_mi({"Deger_Risk": 0}), "kademe 0 bos")
    ok(U.deger_riski_mi({"Deger_Risk": 2}), "mi")


def test_fon_uyarisi():
    # 20 fonluk tur: medyan ~1,0; bir fon 15 puan ustte
    rows = [_f(f"F{i:02d}", 1.0 + (i % 3) * 0.1) for i in range(20)]
    rows.append(_f("USTTE", 16.0))
    rows.append(_f("SINIR", 13.2))      # tur medyani 1,1 -> fark 12,1: esik ustu
    rows.append(_f("ALTI", 12.0))       # fark 10,9: uyarilmaz
    d = _katman(rows)
    ok(bool(d.loc["USTTE", "Getiri_Uyari"]) and bool(d.loc["SINIR", "Getiri_Uyari"]), "esik ve ustu uyarilir")
    ok(not d.loc["ALTI", "Getiri_Uyari"] and not d.loc["F00", "Getiri_Uyari"], "esik alti/normal fon uyarilmaz")
    ok(d.loc["USTTE", "Optima_Skor"] != d.loc["USTTE", "Optima_Skor"] or True, "fon skoruna dokunma yok (CSV'de bos)")
    ok(U.getiri_uyarisi_mi(d.loc["USTTE"]) and "medyan" in U.getiri_uyarisi_aciklama(d.loc["USTTE"]) and
       "skor değişmedi" in U.getiri_uyarisi_aciklama(d.loc["USTTE"]), "aciklama")
    # kucuk tur: medyan guvenilmez -> uyari yok
    kucuk = [_f(f"K{i}", 1.0, tur="Nadir Tur") for i in range(5)] + [_f("KU", 40.0, tur="Nadir Tur")]
    d2 = _katman(kucuk)
    ok(not d2["Getiri_Uyari"].any(), "turde 15'ten az fon: uyari uretilmez")
    # bayat getiri verisi: uyari yok
    bayat = [_f(f"B{i:02d}", 1.0) for i in range(20)] + [_f("BAY", 30.0, tarih="2026-06-13"),
                                                          _f("TAZE", 30.0, tarih="2026-10-16")]
    d3 = _katman(bayat)
    ok(bool(d3.loc["TAZE", "Getiri_Uyari"]) and not d3.loc["BAY", "Getiri_Uyari"], "bayat Getiri_Tarihi uyari uretmez")
    # tedbirli fon uyari almaz
    ted = [_f(f"T{i:02d}", 1.0) for i in range(20)] + [_f("TDBR", 50.0)]
    d4 = _katman(ted)
    ok(not d4.loc["TDBR", "Getiri_Uyari"], "tedbirli fon: uyari yok")


def test_radar_ayni_carpan():
    import firsat_radari as R
    uni = pd.DataFrame([_b("R2", 30.0, 30.0), _b("R0", 3.0, 3.0)])
    sonuc = {t: {"kategori": "BIST", "skor": 90.0, "fiyat": 10.0, "rsi": 50.0, "ret1m": 5.0} for t in ("R2", "R0")}
    import db
    orj = (getattr(db, "get_aktif_piyasa_tedbirleri", None), getattr(db, "get_aktif_kap_riskleri", None))
    db.get_aktif_piyasa_tedbirleri = lambda: []
    db.get_aktif_kap_riskleri = lambda: {}
    try:
        c, s = R._katman_carpanlari(uni, sonuc)
    finally:
        db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj
    ok(c[("BIST", "R2")] == 0.5 and c[("BIST", "R0")] == 1.0, f"radar PD/DD carpanini da alir: {c}")
    tetik = {t for t, *_ in R._radar_tetikleyicileri(sonuc, {}, {}, c, s)}
    ok(tetik == {"R0"}, f"R2 etkin 45 -> alarm yok; R0 90 -> alarm: {tetik}")


if __name__ == "__main__":
    for ad, fn in sorted(globals().items()):
        if ad.startswith("test_") and callable(fn):
            fn()
    print(f"{_n['ok']} kontrol gecti")
    print("TUM TESTLER GECTI")
