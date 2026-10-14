"""v2.0.7.415: kademeli yas kesintisi (BIST + KRIPTO + TEFAS). 1 yildan genc x0,70; 1-2 yil x0,80; 2-3 yil x0,90; 3 yil+ 1,00.
Bir yil: BIST 260 islem gunu, KRIPTO 365 takvim gunu, TEFAS 365 takvim gunu (arsiv). Ag/veritabani kullanilmaz.
Calistir: python3 test_yas_kademe.py"""
import sys
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


import scoring as S
import tefas_client as tc
import uyari_katmani as U


def test_kademe_sinirlari():
    for kat, (a, b, c) in (("BIST", (260, 520, 780)), ("KRIPTO", (365, 730, 1095))):
        ok(S.yas_kademesi(kat, a - 1) == 0 and S.yas_kademesi(kat, a) == 1, f"{kat}: 1 yil siniri {a}")
        ok(S.yas_kademesi(kat, b - 1) == 1 and S.yas_kademesi(kat, b) == 2, f"{kat}: 2 yil siniri {b}")
        ok(S.yas_kademesi(kat, c - 1) == 2 and S.yas_kademesi(kat, c) == 3, f"{kat}: 3 yil siniri {c}")
        ok(S.yas_kademesi(kat, 5000) == 3, f"{kat}: cok eski -> 3")
        for bilinmeyen in (None, 0, -5, float("nan"), "x"):
            ok(S.yas_kademesi(kat, bilinmeyen) is None, f"{kat}: bilinmeyen {bilinmeyen!r} -> None")
    ok(S.yas_kademesi("TEFAS", 10) is None and S.yas_kademesi("DOVIZ", 10) is None, "TEFAS/DOVIZ Gecmis_Gun ile kademelenmez")
    ok([S.yas_carpani(k) for k in (0, 1, 2, 3, None)] == [0.70, 0.80, 0.90, 1.0, 1.0], "carpanlar 0,70/0,80/0,90/1,00")


def test_fon_kademesi():
    simdi = pd.Series([1.0] * 6 + [0.0])
    e1 = pd.Series([np.nan, 0.9, 0.9, 0.9, np.nan, 0.9, 0.9])
    e2 = pd.Series([np.nan, np.nan, 0.8, 0.8, np.nan, 0.8, 0.8])
    e3 = pd.Series([np.nan, np.nan, np.nan, 0.7, np.nan, 0.7, 0.7])
    k = tc.fon_yas_kademesi(simdi, [e1, e2, e3], min_kapsam=0.3)
    ok(list(k.iloc[:4]) == [0, 1, 2, 3], "fon: hic yok 0 / yalniz 1y 1 / 1y+2y 2 / hepsi 3")
    ok(k.iloc[4] == 0, "hicbir tarihte fiyati olmayan fon genc (0)")
    ok(k.iloc[5] == 3, "tam gecmisli fon 3")
    ok(k.iloc[6] is None, "bugun fiyati olmayan fon bilinmiyor")
    # arsiv bosluğu: 3 yil onceki fiyati var, 1-2 yil onceki yok -> genc sayilmaz (derin fiyat sig tarihleri de kapsar)
    k2 = tc.fon_yas_kademesi(pd.Series([1.0, 1.0]), [pd.Series([0.9, np.nan]), pd.Series([0.9, np.nan]),
                                                     pd.Series([0.9, 0.9])], min_kapsam=0.4)
    ok(list(k2) == [3, 3], "derin tarihte fiyati olan fon arsiv boslugu yuzunden genc sayilmaz")
    # kapsam guvencesi: 3 yil kapsami dusukse 3 yil esiginde karar verilmez (None), 1-2 yil kararlari korunur
    simdi8 = pd.Series([1.0] * 8)
    e1 = pd.Series([0.9] * 8)
    e2 = pd.Series([0.9] * 4 + [np.nan] * 4)
    e3 = pd.Series([0.9] + [np.nan] * 7)
    k3 = tc.fon_yas_kademesi(simdi8, [e1, e2, e3], min_kapsam=0.5)
    ok(list(k3.iloc[:4]) == [None] * 4 and list(k3.iloc[4:]) == [1] * 4,
       "3 yil kapsami <%50: 2 yili olanlar bilinmiyor (None), 2 yili olmayanlar kademe 1")
    ok(all(v is None for v in tc.fon_yas_kademesi(simdi8, [pd.Series([np.nan] * 8)] * 3)), "arsiv bos -> hepsi None")
    ok(all(v is None for v in tc.fon_yas_kademesi(pd.Series([0.0, 0.0]), [pd.Series([1.0, 1.0])] * 3)), "fiyatli fon yok -> None")


def test_toplu_guncelleme_yas_kademe_kolonu():
    import db
    import types
    rng = np.random.default_rng(7)
    idx = pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=70)
    ser = lambda: pd.Series(1 + np.cumsum(rng.normal(0, 0.003, 70)), index=idx)

    class Crawler:
        def __init__(self, *a, **k): pass
        def fetch(self, start=None, end=None, kind=None, fund_code=None):
            if kind != "YAT":
                return pd.DataFrame()
            rows = []
            for kod in ("F0", "F1", "F2", "F3", "F4", "F5"):
                for t, p in ser().items():
                    rows.append({"fund_code": kod, "date": t, "price": p})
            return pd.DataFrame(rows)
    m = types.ModuleType("pytefas")
    m.Crawler = Crawler
    sys.modules["pytefas"] = m

    def arsiv(hedef, tolerans_gun=10):
        gun = (pd.Timestamp.now().normalize() - pd.Timestamp(hedef)).days
        if gun > 1000:                                    # 3 yil
            return {"F3": 0.5, "F4": 0.5, "F5": 0.5}
        if gun > 600:                                     # 2 yil
            return {"F2": 0.5, "F3": 0.5, "F4": 0.5, "F5": 0.5}
        return {"F1": 0.5, "F2": 0.5, "F3": 0.5, "F4": 0.5, "F5": 0.5}   # 1 yil (ve 6 ay)
    db.tefas_arsiv_fiyatlari = arsiv
    df = pd.DataFrame([{"Ticker": t, "TEFAS_Kind": "YAT", "Son_Fiyat": 1.0, "Ret1M": 0.0, "Ret3M": None,
                        "RSI": 50.0, "Vol": 18.0} for t in ("F0", "F1", "F2", "F3", "F4", "F5")])
    out, _, _ = tc.gercek_getiri_rsi_guncelle(df, log=lambda m: None)
    k = out.set_index("Ticker")["Yas_Kademe"]
    ok(k["F3"] == 3 and k["F2"] == 2 and k["F1"] == 1 and k["F0"] == 0, f"arsivden 0/1/2/3 kademeleri ({dict(k)})")
    ok("Ret2Y_YAS" not in out.columns, "yas kademesi icin kullanilan 2 yillik sorgu CSV'ye getiri kolonu yazmaz")
    db.tefas_arsiv_fiyatlari = lambda *a, **k: None
    out2, _, _ = tc.gercek_getiri_rsi_guncelle(df.copy(), log=lambda m: None)
    ok(all(v is None or v != v for v in out2["Yas_Kademe"]), "arsiv yoksa Yas_Kademe BOS (kesinti uygulanmaz)")


def test_kripto_yas_hesabi():
    import worker
    bugun = datetime(2026, 10, 14)
    ilk = {"YENI": bugun - timedelta(days=100), "ORTA": bugun - timedelta(days=500), "ESKI": bugun - timedelta(days=2000),
           "SIFIR": bugun - timedelta(days=40)}
    cagrilar = []

    def getir(parite, bas):
        cagrilar.append(parite)
        t = parite[:-3]
        if t == "HATA":
            raise RuntimeError("btcturk")
        if t == "BOS":
            return pd.Series(dtype=float)
        bas_gun = max(ilk[t], bas)
        idx = pd.date_range(bas_gun, bugun, freq="D")
        s = pd.Series(10.0, index=idx)
        if t == "SIFIR":                      # ilk 30 gun fiyat 0 (islem yok) -> sayilmaz
            s.iloc[:30] = 0.0
        return s
    par = {t: t + "TRY" for t in ("YENI", "ORTA", "ESKI", "SIFIR", "HATA", "BOS")}
    r = worker._kripto_gecmis_gun_hesapla(par, {"HATA": 77.0}, getir=getir, bugun=bugun, log=lambda m: None)
    ok(r["YENI"] == 100 and r["ORTA"] == 500, "ilk fiyat tarihinden takvim gunu")
    ok(r["ESKI"] >= 1095, "3 yildan eski -> 1095 ustu (pencere siniri)")
    ok(r["SIFIR"] == 10, "fiyati 0 olan gunler sayilmaz (ilk gercek fiyat)")
    ok(r["HATA"] == 77 and "BOS" not in r, "hata: onceki deger korunur; bos veri: bilinmiyor (uydurma yok)")
    cagrilar.clear()
    r2 = worker._kripto_gecmis_gun_hesapla(par, {"ESKI": 2000.0, "YENI": 100.0}, getir=getir, bugun=bugun, log=lambda m: None)
    ok("ESKITRY" not in cagrilar and "YENITRY" in cagrilar, "3 yili dolmus varlik bir daha sorgulanmaz, gencler sorgulanir")
    ok(r2["ESKI"] == 2000, "onceki deger aynen korunur")
    ok(S.yas_kademesi("KRIPTO", r["YENI"]) == 0 and S.yas_kademesi("KRIPTO", r["ORTA"]) == 1
       and S.yas_kademesi("KRIPTO", r["ESKI"]) == 3, "kademeler")


def _df():
    def f(t, kat, gun=None, skor=80.0, **ek):
        d = {"Ticker": t, "Ad": t, "Kategori": kat, "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 6.0, "Vol": 30.0,
             "Optima_Skor": skor, "Gecmis_Gun": gun}
        d.update(ek)
        return d
    return pd.DataFrame([
        f("K0", "KRIPTO", 100), f("K1", "KRIPTO", 400), f("K2", "KRIPTO", 800), f("K3", "KRIPTO", 1500),
        f("KB", "KRIPTO", None), f("KN", "KRIPTO", 100, Son_Fiyat=0.0),
        f("B0", "BIST", 100), f("B1", "BIST", 300), f("B2", "BIST", 600), f("B3", "BIST", 900),
        f("T1", "TEFAS", None, skor=np.nan, Yas_Kademe=1.0), f("T2", "TEFAS", None, Yas_Kademe=2),
        f("T3", "TEFAS", None, Yas_Kademe=3), f("TB", "TEFAS", None, Yas_Kademe=np.nan),
        f("TG", "TEFAS", None, Genc_Fon=True), f("DV", "DOVIZ", 50),
    ])


def _uygula(df):
    import db
    orj = (db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri)
    db.get_aktif_piyasa_tedbirleri = lambda: []
    db.get_aktif_kap_riskleri = lambda: {}
    try:
        return U.uyari_katmanini_uygula(df)
    finally:
        db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj


def test_katman_skor_ve_bayrak():
    d = _uygula(_df()).set_index("Ticker")
    sk = d["Optima_Skor"]
    ok([sk["K0"], sk["K1"], sk["K2"], sk["K3"]] == [56.0, 64.0, 72.0, 80.0], "kripto 80 -> 56 / 64 / 72 / 80")
    ok([sk["B0"], sk["B1"], sk["B2"], sk["B3"]] == [56.0, 64.0, 72.0, 80.0], "BIST 80 -> 56 / 64 / 72 / 80 (260/520/780 gun)")
    from scoring import optima_score
    ham = round(optima_score(50.0, 6.0, vol=30.0), 1)
    ok(sk["T1"] == round(ham * 0.8, 1), f"TEFAS kademe 1: bos skor formulle uretilip x0,80 ({ham} -> {sk['T1']})")
    ok(sk["T2"] == 72.0 and sk["T3"] == 80.0, "TEFAS kademe 2 x0,90; kademe 3 aynen")
    ok(sk["TB"] == 80.0, "TEFAS kademe bilinmiyor -> dokunulmaz")
    ok(sk["TG"] == 56.0, "eski CSV (yalniz Genc_Fon=True): kademe 0 kabul edilir, x0,70")
    ok(sk["KB"] == 80.0 and sk["KN"] == 80.0, "yas bilinmiyor / fiyati yok -> dokunulmaz")
    ok(sk["DV"] == 80.0, "DOVIZ kapsam disi")
    sn = d["Veri_Sinirli"]
    ok(bool(sn["K0"]) and bool(sn["B0"]) and bool(sn["TG"]), "1 yildan genc: SINIRLI VERI bayragi (kripto dahil)")
    ok(not any(bool(sn[t]) for t in ("K1", "K2", "K3", "B1", "B2", "B3", "T1", "T2", "T3", "TB", "KB", "KN", "DV")),
       "1 yildan buyuklerde bayrak (AL siniri) yok")
    ok(list(d.loc[["K0", "K1", "K2", "K3", "T1", "KB"], "Yas_Kesinti"]) == [30, 20, 10, 0, 20, 0], "Yas_Kesinti yuzdesi")
    ok(U.get_signal_row(d.loc["K0"], 90, 50, "YUKSELIS") == ("TUT İZLE", "sig-t"), "genc kripto: AL -> TUT IZLE")
    ok(U.get_signal_row(d.loc["K1"], 90, 50, "YUKSELIS")[0] == "GÜÇLÜ AL", "1-2 yil: AL siniri yok (yalniz skor eksilir)")


def test_sinyal_skoru_izler():
    # skor 80 olan 1-2 yillik varlik 64'e iner: GUCLU AL (>=80) yerine KADEMELI AL (>=60) etiketi
    d = _uygula(_df()).set_index("Ticker")
    lbl, _ = U.get_signal_row(d.loc["K1"], d.loc["K1", "Optima_Skor"], 50, "YUKSELIS")
    ok(lbl == "KADEMELİ AL", f"eksilen skor sinyali de dusurur ({lbl})")
    lbl3, _ = U.get_signal_row(d.loc["K3"], d.loc["K3", "Optima_Skor"], 50, "YUKSELIS")
    ok(lbl3 == "GÜÇLÜ AL", "3 yil+ varlik degismez")


def test_ikinci_uygulama_cifte_islemez():
    d1 = _uygula(_df())
    d2 = _uygula(d1.copy())
    ok(list(d1["Optima_Skor"].fillna(-1)) == list(d2["Optima_Skor"].fillna(-1)), "ikinci uygulamada skor tekrar eksilmez")


def test_tedbirli_ve_kap_ile_birlikte():
    import db
    orj = (db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri)
    db.get_aktif_piyasa_tedbirleri = lambda: [{"eslesme_turu": "TICKER", "deger": "K1", "tedbir_turu": "BRUT_TAKAS"}]
    db.get_aktif_kap_riskleri = lambda: {}
    try:
        d = U.uyari_katmanini_uygula(_df()).set_index("Ticker")
    finally:
        db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj
    ok(d.loc["K1", "Optima_Skor"] == 0.0, "tedbirli genc varlik: skor 0 kalir (0 x k = 0)")


def test_aciklamalar():
    d = _uygula(_df()).set_index("Ticker")
    a = U.veri_sinirli_aciklama(d.loc["K0"])
    ok("Genç kripto" in a and "100 günlük" in a and "%30" in a and "AL sinyali" in a, "kripto kademe 0 metni")
    b = U.veri_sinirli_aciklama(d.loc["B0"])
    ok("Yeni halka arz" in b and "100 işlem günü" in b and "%30" in b, "BIST kademe 0 metni")
    t = U.veri_sinirli_aciklama(d.loc["TG"])
    ok("Genç fon" in t and "%30" in t, "fon kademe 0 metni")
    y = U.yas_kesinti_aciklama(d.loc["K1"])
    ok("%20" in y and "1 ile 2 yıl" in y, "kademe 1 aciklamasi")
    ok("%10" in U.yas_kesinti_aciklama(d.loc["K2"]), "kademe 2 aciklamasi")
    ok(U.yas_kesinti_mi(d.loc["K1"]) and U.yas_kesinti_mi(d.loc["T2"]), "kademe 1-2 serit icin isaretli")
    ok(not U.yas_kesinti_mi(d.loc["K0"]) and not U.yas_kesinti_mi(d.loc["K3"]) and not U.yas_kesinti_mi(d.loc["KB"]),
       "kademe 0 (kendi seridi var), 3 ve bilinmeyende yok")
    ok(U.yas_kesinti_aciklama(d.loc["K3"]) == "", "kademe 3: aciklama yok")


def test_optimizer_genc_kripto_almaz():
    import portfoy_optimizasyon as P
    rows = []
    for t, g in (("AAA", 1500), ("BBB", 100), ("CCC", 2000)):
        rows.append({"Ticker": t, "Ad": t, "Kategori": "KRIPTO", "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0,
                     "Vol": 60.0, "Optima_Skor": 99.0, "Gecmis_Gun": g})
    d = _uygula(pd.DataFrame(rows))
    d["Optima_Skor"] = 99.0
    s = P.optimize_portfolio(d, 100000, {"KRIPTO": 1.0}, 3)
    sec = {x["ticker"] for x in s["secilenler"]}
    ok("BBB" not in sec and {"AAA", "CCC"} <= sec, f"otomatik oneri 1 yildan genc kriptoyu almaz ({sec})")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"yas_kademe testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
