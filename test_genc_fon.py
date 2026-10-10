"""v2.0.7.392: genc TEFAS fonu (~1 yildan kisa gecmis): SINIRLI VERI uyarisi + AL siniri + Optima Skor x0,5.
Calistir: python3 test_genc_fon.py (ag/veritabani kullanilmaz)"""
import sys, types, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


import tefas_client as tc
import uyari_katmani as U


def _db_bos():
    import db
    orj = (db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri)
    db.get_aktif_piyasa_tedbirleri = lambda: []
    db.get_aktif_kap_riskleri = lambda: {}
    return db, orj


def _db_geri(db, orj):
    db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj


def _df():
    def f(t, genc, skor=np.nan, fiyat=1.0, kat="TEFAS", gun=None):
        return {"Ticker": t, "Ad": t, "Kategori": kat, "Son_Fiyat": fiyat, "RSI": 50.0, "Ret1M": 6.0, "Vol": 10.0,
                "Optima_Skor": skor, "Gecmis_Gun": gun, "Genc_Fon": genc, "Getiri_Tarihi": pd.Timestamp.now().strftime("%Y-%m-%d")}
    return pd.DataFrame([
        f("GNC1", True),                    # skoru bos -> hesaplanip x0,5
        f("GNC2", "True", skor=80.0),       # CSV'den metin geldi -> 80 -> 40
        f("ESKI", False, skor=80.0),        # genc degil
        f("BLNM", None, skor=80.0),         # bilinmiyor (bos) -> dokunulmaz
        f("NOPR", True, skor=80.0, fiyat=0.0),  # fiyati yok
        f("HSSE", True, skor=80.0, kat="BIST", gun=500.0),   # BIST'te Genc_Fon anlamsiz
    ])


def test_katman_bayrak_ve_skor():
    from scoring import optima_score
    db, orj = _db_bos()
    try:
        d = U.uyari_katmanini_uygula(_df()).set_index("Ticker")
    finally:
        _db_geri(db, orj)
    ham = round(optima_score(50.0, 6.0, vol=10.0), 1)
    ok(bool(d.loc["GNC1", "Veri_Sinirli"]) and d.loc["GNC1", "Optima_Skor"] == round(ham * 0.5, 1),
       f"skoru bos genc fon: formulle hesaplanip yariya iner ({ham} -> {d.loc['GNC1','Optima_Skor']})")
    ok(bool(d.loc["GNC2", "Veri_Sinirli"]) and d.loc["GNC2", "Optima_Skor"] == 40.0, "CSV metni 'True' da taninir; 80 -> 40")
    ok(not d.loc["ESKI", "Veri_Sinirli"] and d.loc["ESKI", "Optima_Skor"] == 80.0, "genc olmayan fon aynen kalir")
    ok(not d.loc["BLNM", "Veri_Sinirli"] and d.loc["BLNM", "Optima_Skor"] == 80.0, "Genc_Fon bos (bilinmiyor) -> hicbir sey yapilmaz")
    ok(not d.loc["NOPR", "Veri_Sinirli"] and d.loc["NOPR", "Optima_Skor"] == 80.0, "fiyati olmayan fon isaretlenmez")
    ok(not d.loc["HSSE", "Veri_Sinirli"] and d.loc["HSSE", "Optima_Skor"] == 80.0, "BIST satirinda Genc_Fon yok sayilir")


def test_ikinci_uygulama_cifte_yariya_indirmez():
    db, orj = _db_bos()
    try:
        d1 = U.uyari_katmanini_uygula(_df())
        d2 = U.uyari_katmanini_uygula(d1.copy())
    finally:
        _db_geri(db, orj)
    ok(list(d1["Optima_Skor"].fillna(-1)) == list(d2["Optima_Skor"].fillna(-1)), "ikinci uygulamada skor tekrar yariya inmez")


def test_sinyal_siniri_ve_aciklama():
    db, orj = _db_bos()
    try:
        d = U.uyari_katmanini_uygula(_df()).set_index("Ticker")
    finally:
        _db_geri(db, orj)
    ok(U.get_signal_row(d.loc["GNC2"], 90, 50, "YUKSELIS") == ("TUT İZLE", "sig-t"), "genc fon: AL -> TUT IZLE")
    ok(U.get_signal_row(d.loc["ESKI"], 90, 50, "YUKSELIS")[0] == "GÜÇLÜ AL", "genc olmayan fon: sinyal degismez")
    a = U.veri_sinirli_aciklama(d.loc["GNC2"])
    ok("Genç fon" in a and "yarıya" in a and "AL sinyali" in a, "TEFAS'a ozgu aciklama metni")
    ok("Yeni halka arz" not in a, "halka arz metni TEFAS'ta cikmaz")
    ok("Yeni halka arz" in U.veri_sinirli_aciklama(pd.Series({"Kategori": "BIST", "Gecmis_Gun": 66.0})),
       "BIST aciklamasi degismedi")


def test_tedbirli_genc_fon_sifir_kalir():
    import db
    orj = (db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri)
    db.get_aktif_piyasa_tedbirleri = lambda: [{"eslesme_turu": "TICKER", "deger": "GNC2", "tedbir_turu": "BRUT_TAKAS"}]
    db.get_aktif_kap_riskleri = lambda: {}
    try:
        d = U.uyari_katmanini_uygula(_df()).set_index("Ticker")
    finally:
        db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj
    ok(d.loc["GNC2", "Optima_Skor"] == 0.0, "tedbirli genc fon: skor 0 (0 x 0,5 = 0)")


def test_optimizer_genc_fonu_almaz_izleme_listesinde_tutar():
    import portfoy_optimizasyon as P
    db, orj = _db_bos()
    try:
        d = _df()
        d["Optima_Skor"] = d["Optima_Skor"].fillna(80.0)
        d.loc[d.Ticker == "GNC1", "Optima_Skor"] = 80.0
        d = U.uyari_katmanini_uygula(d)
    finally:
        _db_geri(db, orj)
    # genc fonun skoru yariya indigi icin zaten esik altinda; bayrak ayrica da disarida birakir: skoru elle yuksek tut
    d.loc[d.Ticker == "GNC2", "Optima_Skor"] = 95.0
    d.loc[d.Ticker == "ESKI", "Optima_Skor"] = 90.0
    s = P.optimize_portfolio(d, 100000, {"TEFAS": 1.0}, 5)
    sec = {x["ticker"] for x in s["secilenler"]}
    ok("GNC2" not in sec and "ESKI" in sec, f"otomatik oneri genc fonu almaz (secilen: {sec})")
    s2 = P.optimize_portfolio(d, 100000, {"TEFAS": 1.0}, 5, watchlist_mode=True)
    ok("GNC2" in {x["ticker"] for x in s2["secilenler"]}, "izleme listesi modunda kullanicinin secimi korunur")


def test_isaretle_fonksiyonu():
    simdi = pd.Series([1.0, 2.0, 3.0, 0.0, 4.0])
    eski = pd.Series([0.9, np.nan, 2.5, np.nan, np.nan])
    r = tc.genc_fon_isaretle(simdi, eski, min_kapsam=0.4)
    ok(list(r.iloc[:3]) == [False, True, False], "eski fiyati olan False, olmayan True")
    ok(r.iloc[3] is None, "bugun fiyati olmayan fon bilinmiyor (None)")
    ok(r.iloc[4] == True, "fiyati olup 1 yil oncesi olmayan genc")
    ok(tc.genc_fon_isaretle(simdi, pd.Series([np.nan] * 5)) is None, "arsiv hic kapsamiyorsa kimse genc sayilmaz (None)")
    ok(tc.genc_fon_isaretle(simdi, pd.Series([0.9, np.nan, np.nan, np.nan, np.nan])) is None, "kapsam %25 < %50 -> None (arsiv yetersiz)")
    ok(tc.genc_fon_isaretle(pd.Series([0.0, 0.0]), pd.Series([1.0, 1.0])) is None, "hic fiyatli fon yoksa None")


def _sahte_pytefas(seriler):
    class Crawler:
        def __init__(self, *a, **k): pass
        def fetch(self, start=None, end=None, kind=None, fund_code=None):
            rows = []
            for kod, s in seriler.get(kind, {}).items():
                for t, p in s.items():
                    rows.append({"fund_code": kod, "date": t, "price": p})
            return pd.DataFrame(rows)
    m = types.ModuleType("pytefas")
    m.Crawler = Crawler
    sys.modules["pytefas"] = m


def test_toplu_guncelleme_genc_fon_kolonu():
    import db
    rng = np.random.default_rng(5)
    idx = pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=70)
    ser = lambda: pd.Series(1 + np.cumsum(rng.normal(0, 0.003, 70)), index=idx)
    _sahte_pytefas({"YAT": {"OLD1": ser(), "OLD2": ser(), "YNG1": ser()}, "EMK": {}, "BYF": {}})
    df = lambda: pd.DataFrame([{"Ticker": t, "TEFAS_Kind": "YAT", "Son_Fiyat": 1.0, "Ret1M": 0.0, "Ret3M": None,
                                "RSI": 50.0, "Vol": 18.0} for t in ("OLD1", "OLD2", "YNG1")])
    # arsiv: OLD1/OLD2 icin 1 yil onceki fiyat var, YNG1 icin yok -> kapsam 2/3
    db.tefas_arsiv_fiyatlari = lambda hedef, tolerans_gun=10: {"OLD1": 0.8, "OLD2": 0.9}
    out, _, _ = tc.gercek_getiri_rsi_guncelle(df(), log=lambda m: None)
    g = out.set_index("Ticker")["Genc_Fon"]
    ok(g["OLD1"] == False and g["OLD2"] == False and g["YNG1"] == True, "arsivde 1 yil oncesi olmayan fon genc isaretlenir")
    # arsive ulasilamadi -> kimse genc sayilmaz
    db.tefas_arsiv_fiyatlari = lambda *a, **k: None
    out2, _, _ = tc.gercek_getiri_rsi_guncelle(df(), log=lambda m: None)
    ok(out2["Genc_Fon"].isna().all() or all(v is None for v in out2["Genc_Fon"]), "arsiv yoksa Genc_Fon BOS (kimse genc sayilmaz)")
    # arsiv cok kisitli (yalniz 1/3 kapsam) -> kimse genc sayilmaz
    db.tefas_arsiv_fiyatlari = lambda hedef, tolerans_gun=10: {"OLD1": 0.8}
    out3, _, _ = tc.gercek_getiri_rsi_guncelle(df(), log=lambda m: None)
    ok(all(v is None for v in out3["Genc_Fon"]), "arsiv yetersiz kapsamli -> Genc_Fon BOS")


def test_worker_yedek_yolu_ve_workflow():
    src = open("worker.py", encoding="utf-8").read()
    ok('"Vol_Kaynak", "Genc_Fon"]' in src, "gercek getiri hesaplanamazsa onceki Genc_Fon korunur")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"genc_fon testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
