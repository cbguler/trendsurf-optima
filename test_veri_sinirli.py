# -*- coding: utf-8 -*-
"""v2.0.7.378: 260 islem gunu kurali (scoring), KAP birim carpani ve slug yedegi, worker Gecmis_Gun,
optimizer dislamasi. Calistir: python test_veri_sinirli.py. Ag KULLANILMAZ (sahte nesnelerle)."""
import sys
import pandas as pd

import scoring as S

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def test_esik_ve_bayrak():
    ok(S.GECMIS_GUN_ESIK == 260, "esik 260")
    ok(S.sinirli_veri_mi("BIST", 10.0, 259) is True, "259 gun -> sinirli")
    ok(S.sinirli_veri_mi("BIST", 10.0, 260) is False, "260 gun tam esik -> sinirli degil")
    ok(S.sinirli_veri_mi("BIST", 10.0, 66) is True, "66 gun")
    ok(S.sinirli_veri_mi("BIST", 10.0, None) is False, "bilinmiyor -> bayrak yok")
    ok(S.sinirli_veri_mi("BIST", 10.0, float("nan")) is False, "NaN -> bayrak yok")
    ok(S.sinirli_veri_mi("BIST", 10.0, 0) is False, "0 = bilinmiyor")
    ok(S.sinirli_veri_mi("BIST", 0.0, 50) is False, "fiyati olmayan -> bayrak yok")
    ok(S.sinirli_veri_mi("KRIPTO", 5.0, 50) is False, "yalniz BIST")
    ok(S.sinirli_veri_mi("TEFAS", 5.0, 50) is False, "yalniz BIST (TEFAS)")
    ok(S.gecmis_gun_say(pd.Series([1.0, None, 2.0, float("nan"), 3.0])) == 3, "NaN'siz gun sayisi")


def test_sinyal_siniri():
    for lbl in ("GÜÇLÜ AL", "KADEMELİ AL"):
        ok(S.sinyal_sinirla(lbl, "x", True) == ("TUT İZLE", "sig-t"), f"{lbl} sinirli -> TUT IZLE")
        ok(S.sinyal_sinirla(lbl, "x", False) == (lbl, "x"), f"{lbl} sinirsiz -> degismez")
    for lbl in ("TUT İZLE", "KADEMELİ SAT", "NET SAT"):
        ok(S.sinyal_sinirla(lbl, "c", True) == (lbl, "c"), f"{lbl} sinirli olsa da degismez (AL degil)")


def test_kap_birim_ve_slug():
    import kap_client as K

    def tb(v):
        return [pd.DataFrame([["Sunum Para Birimi", None, v]])]

    for v, beklenen, isaret in [("TL", 1.0, None), ("1000TL", 1000.0, None), ("1000000TL", 1e6, None),
                                ("1.000TL", 1000.0, None), ("USD", 1.0, "USD"), ("1000USD", 1.0, "1000USD")]:
        r = {}
        ok(K._kap_birim_carpani(tb(v), r) == beklenen, f"carpan {v}")
        ok(r.get("kap_para_birimi") == isaret, f"TL disi isaretleme {v}")
    ok(K._kap_birim_carpani([pd.DataFrame([["x", 1]])], {}) == 1.0, "birim satiri yoksa 1")
    # tutarlar carpanla gelir
    df = pd.DataFrame([["Sunum Para Birimi", None, "1000TL"], ["Toplam Varlıklar", None, "32.055.164"]])
    r = {}
    K._parse_kap_financials([df], r)
    ok(r["kap_total_assets"] == 32055164000.0, "1000TL tutari 1000 ile carpilir (VEYAS)")
    # xlsx'teki yeni hisseler
    for t in "ALBTN BETAE BKRGY CITAS EKIM GOLDA INTET ISVEA KARCL KPEKS MASFN NETGL NTGAZ ORZAX QUICK SARAE SOHOE SSAAT TKNKA USHOL VEYAS".split():
        ok(t in K.KAP_SLUG_MAP, f"{t} KAP_BIST.xlsx'te")
    ok(K.KAP_SLUG_MAP["ORZAX"].startswith("6234-orzaks"), "ORZAX slug")
    # canli yedek: xlsx'te olmayan kod, sahte liste; basarisizlikta geri cekilme
    import kap_evren
    orj = kap_evren.kap_bist_listesini_cek
    K._CANLI_SLUG.update({"harita": None, "son_deneme": 0.0})
    cagri = {"n": 0}

    def sahte(*a, **k):
        cagri["n"] += 1
        return [{"kodlar": ["YENIX", "YNX"], "ad": "Yeni", "slug": "9999-yeni"}]
    try:
        kap_evren.kap_bist_listesini_cek = sahte
        ok(K.slug_getir("yenix") == "9999-yeni" and K.slug_getir("YNX") == "9999-yeni", "yedek canli arama")
        ok(K.slug_getir("ORZAX").startswith("6234"), "xlsx onceligi")
        ok(K.slug_getir("YOKYOK") is None and cagri["n"] == 1, "bilinmeyen kod None, liste tekrar cekilmez")

        def patla(*a, **k):
            cagri["n"] += 1
            raise kap_evren.KapListeHata("x")
        K._CANLI_SLUG.update({"harita": None, "son_deneme": 0.0})
        kap_evren.kap_bist_listesini_cek = patla
        cagri["n"] = 0
        ok(K.slug_getir("YENIX") is None and K.slug_getir("YENIX") is None and cagri["n"] == 1,
           "liste cekilemezse None ve 10 dk geri cekilme (tek deneme)")
    finally:
        kap_evren.kap_bist_listesini_cek = orj
        K._CANLI_SLUG.update({"harita": None, "son_deneme": 0.0})


def test_kap_donem_etiketi():
    import kap_client as K
    bilanco = pd.DataFrame([["Sunum Para Birimi", None, None, "TL"], ["Toplam Varlıklar", None, None, "10.111.895.062"]],
                           columns=["FİNANSAL DURUM TABLOSU", "u1", "u2", "2026/06"])
    gelir_baslik = pd.DataFrame([["Sunum Para Birimi", None, None, "TL"]],
                                columns=["KAR VEYA ZARAR VE DİĞER KAPSAMLI GELİR TABLOSU", "u1", "u2", "2026/06"])
    gelir_satir = pd.DataFrame([["Hasılat", None, None, "4.525.914.424"]], columns=["0", "1", "2", "3"])
    r = {}
    K._parse_kap_financials([bilanco, gelir_baslik, gelir_satir], r)
    ok(r["kap_donemler"]["kap_total_assets"] == "2026/06", "bilanco alani kendi basligindan donem alir")
    ok(r["kap_donemler"]["kap_revenue"] == "2026/06", "gelir satiri onceki baslik tablosundan donem alir")
    g = K.fundamentals_to_display(r)
    ok("Toplam Varlık (KAP, 2026/06)" in g and "Ciro (KAP, 2026/06)" in g, "etikette donem")
    # donem yoksa eski etiket
    r2 = {"kap_total_assets": 5.0e9, "_kap_available": True}
    g2 = K.fundamentals_to_display(r2)
    ok("Toplam Varlık (KAP)" in g2, "donem bilinmiyorsa eski etiket (uydurma donem yok)")
    # cok donemli baslik: en sagdaki dolu sutunun donemi
    b = pd.DataFrame([["Toplam Varlıklar", "1.000", "2.000", None]], columns=["FİNANSAL DURUM TABLOSU", "2024/12", "2025/12", "2026/06"])
    r3 = {}
    K._parse_kap_financials([b], r3)
    ok(r3["kap_total_assets"] == 2000.0 and r3["kap_donemler"]["kap_total_assets"] == "2025/12",
       "en sagdaki DOLU sutunun donemi (bos 2026/06 degil)")


def test_worker_gecmis_gun():
    import sys as _s, types
    import numpy as np
    import worker

    idx = pd.date_range("2025-01-01", periods=300, freq="B")
    kisa = pd.Series(np.nan, index=idx)
    kisa.iloc[-40:] = 5.0
    uzun = pd.Series(7.0, index=idx)
    raw = pd.concat({"AAA.IS": pd.DataFrame({"Close": kisa}), "BBB.IS": pd.DataFrame({"Close": uzun})}, axis=1)
    cagrilar = []
    sahte_yf = types.ModuleType("yfinance")

    def download(syms, **k):
        cagrilar.append(list(syms))
        return raw[[c for c in raw.columns if c[0] in syms]]
    sahte_yf.download = download
    orj = _s.modules.get("yfinance")
    _s.modules["yfinance"] = sahte_yf
    try:
        s = worker._gecmis_gun_hesapla(["AAA", "BBB", "CCC"], {"CCC": 400.0})
        ok(s["AAA"] == 40 and s["BBB"] == 300, "gun sayilari dogru")
        ok(s["CCC"] == 400, "onceden >=260 olan korunur")
        ok(all("CCC.IS" not in c for c in cagrilar), "onceden >=260 olan tekrar sorgulanmaz")

        def patla(*a, **k):
            raise RuntimeError("yahoo")
        sahte_yf.download = patla
        s = worker._gecmis_gun_hesapla(["AAA", "CCC"], {"AAA": 33.0, "CCC": 400.0})
        ok(s == {"AAA": 33, "CCC": 400}, "indirme hatasinda onceki degerler korunur, uydurma yok")
        s = worker._gecmis_gun_hesapla(["AAA"], {})
        ok(s == {}, "hata + onceki yok -> bilinmiyor (bos)")
    finally:
        if orj is not None:
            _s.modules["yfinance"] = orj
        else:
            del _s.modules["yfinance"]


def test_optimizer_dislar():
    import portfoy_optimizasyon as P
    rows = []
    for t, sinirli in (("AAA", False), ("BBB", True), ("CCC", False)):
        rows.append({"Ticker": t, "Ad": t, "Kategori": "BIST", "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0,
                     "Vol": 30.0, "Optima_Skor": 90.0, "Veri_Sinirli": sinirli})
    df = pd.DataFrame(rows)
    s = P.optimize_portfolio(df, 100000, {"BIST": 1.0}, 3)
    secilen = {x["ticker"] for x in s["secilenler"]}
    ok("BBB" not in secilen and {"AAA", "CCC"} <= secilen, "sinirli veri otomatik oneriye alinmaz")
    s2 = P.optimize_portfolio(df, 100000, {"BIST": 1.0}, 3, watchlist_mode=True)
    ok("BBB" in {x["ticker"] for x in s2["secilenler"]}, "izleme listesi modunda kullanici secimi korunur")
    df2 = df.drop(columns=["Veri_Sinirli"])
    s3 = P.optimize_portfolio(df2, 100000, {"BIST": 1.0}, 3)
    ok(len(s3["secilenler"]) == 3, "kolon yoksa davranis degismez")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"veri_sinirli testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
