"""v2.0.7.389: Degerli Madenler kendi TL arsivi + canlidoviz kesintisinde yedek basamagi.
Calistir: python3 test_maden_arsiv.py"""
import os, re, sys, tempfile, warnings
warnings.filterwarnings("ignore")
import pandas as pd

import maden_arsiv as ma

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def _gunluk(n, bitis=None, baslangic_fiyat=1000.0, adim=1.0):
    """bitis gunune kadar n ardisik takvim gunu, her gun +adim."""
    bitis = pd.Timestamp(bitis or ma.bugun_trt())
    idx = pd.date_range(end=bitis, periods=n, freq="D")
    return pd.Series([baslangic_fiyat + adim * i for i in range(n)], index=idx)


def _arsive_yaz(yol, ticker_seri):
    a = ma.bos_arsiv()
    for t, s in ticker_seri.items():
        for ts, v in s.items():
            a["seriler"][t][ts.strftime("%Y-%m-%d")] = float(v)
    ma.kaydet(a, yol)


# ---------------------------------------------------------------- saf arsiv
def test_kapsam_8_varlik_9_tur_haric():
    ok(len(ma.ARSIV_KEYLERI) == 8, "arsiv 8 varlik")
    for yasak in ("GRAM_HAS_ALTIN", "AYAR14_ALTIN", "AYAR18_ALTIN", "BILEZIK22_ALTIN", "IKIBUCUK_ALTIN",
                  "BESLI_ALTIN", "GREMSE_ALTIN", "RESAT_ALTIN", "HAMIT_ALTIN"):
        ok(yasak not in ma.ARSIV_KEYLERI, f"{yasak} arsive girmez (18 Temmuz 2026 karari: yalniz fiyat)")
    import live_data as ld
    ok(set(ma.ARSIV_KEYLERI) == set(ld._MADEN_TO_BP), "arsiv kapsami = canlidoviz gecmisi olan 8 varlik")


def test_truncgil_ayristirma():
    veri = {
        "gram-altin": {"Selling": "6.644,78"}, "gumus": {"Selling": "96,37"}, "gram-platin": {"Selling": "2.680,54"},
        "ceyrek-altin": {"Selling": "10.816,51"}, "yarim-altin": {"Selling": "21.633,02"},
        "tam-altin": {"Selling": "43.133,73"}, "cumhuriyet-altini": {"Selling": "44.569,00"},
        "ata-altin": {"Selling": "44.721,47"},
        "gram-has-altin": {"Selling": "6.700,00"},        # 9 fiyat-yalniz tur: arsive girmemeli
        "ons": {"Selling": "$4.000,76"},
    }
    f = ma.truncgil_fiyatlari(veri)
    ok(len(f) == 8 and abs(f["ALTIN_TRY"] - 6644.78) < 1e-9, "8 varlik, TR sayi bicimi dogru")
    ok(abs(f["CUMHURIYET_ALTIN"] - 44569.0) < 1e-9, "cumhuriyet-altini anahtari eslesir")
    ok("GRAM_HAS_ALTIN" not in f, "fiyat-yalniz turler ayiklanir")
    ok(ma.truncgil_fiyatlari({"gram-altin": {"Selling": "$6.644,78"}}) == {}, "'$' (USD) deger reddedilir")
    ok(ma.truncgil_fiyatlari({"gram-altin": {"Selling": ""}}) == {} and ma.truncgil_fiyatlari(None) == {}, "bos/None guvenli")


def test_nokta_ekle_idempotent_ve_saf():
    a = ma.bos_arsiv()
    ma.nokta_ekle(a, {"ALTIN_TRY": 6600.0, "GRAM_HAS_ALTIN": 1.0, "GUMUS_TRY": 0.0, "PLATIN_TRY": "x"}, "2026-10-10")
    ok(a["seriler"]["ALTIN_TRY"] == {"2026-10-10": 6600.0}, "gecerli nokta eklendi")
    ok("GRAM_HAS_ALTIN" not in a["seriler"], "kapsam disi ticker eklenmez")
    ok(a["seriler"]["GUMUS_TRY"] == {} and a["seriler"]["PLATIN_TRY"] == {}, "0 / sayi olmayan deger eklenmez")
    ma.nokta_ekle(a, {"ALTIN_TRY": 6650.0}, "2026-10-10")
    ok(a["seriler"]["ALTIN_TRY"] == {"2026-10-10": 6650.0}, "ayni gun tekrar -> uzerine yazar (tek nokta)")
    ma.nokta_ekle(a, {"ALTIN_TRY": 6700.0}, "2026-10-11")
    ok(len(a["seriler"]["ALTIN_TRY"]) == 2, "yeni gun yeni nokta")


def test_kaydet_yukle_gidis_donus_ve_bozuk_dosya():
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "a.json")
        ok(ma.yukle(yol)["seriler"]["ALTIN_TRY"] == {}, "dosya yok -> bos arsiv (hata yok)")
        a = ma.nokta_ekle(ma.bos_arsiv(), {"ALTIN_TRY": 6644.78}, "2026-10-10")
        ma.kaydet(a, yol)
        ok(ma.yukle(yol)["seriler"]["ALTIN_TRY"] == {"2026-10-10": 6644.78}, "gidis-donus ayni")
        open(yol, "w").write("{bozuk")
        ok(ma.yukle(yol)["seriler"]["ALTIN_TRY"] == {}, "bozuk dosya -> bos arsiv, cokme yok")
        ok(not os.path.exists(yol + ".tmp"), "gecici dosya kalmaz")


def test_gece_guncelle_kaynak_yoksa_nokta_eklemez():
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "a.json")
        ok(ma.gece_guncelle(yol, fiyatlar={}) == {}, "fiyat yok -> bos doner")
        ok(not os.path.exists(yol), "fiyat yokken dosya bile yazilmaz (uydurma yok)")
        ma.gece_guncelle(yol, fiyatlar={"ALTIN_TRY": 6644.78}, tarih="2026-10-10")
        ma.gece_guncelle(yol, fiyatlar={"ALTIN_TRY": 6700.0}, tarih="2026-10-11")
        ok(len(ma.yukle(yol)["seriler"]["ALTIN_TRY"]) == 2, "iki gece = iki nokta")


# ---------------------------------------------------------------- ozet
def test_ozet_yetersiz_veride_none():
    ok(ma.ozet(None) is None and ma.ozet(pd.Series(dtype=float)) is None, "bos -> None")
    ok(ma.ozet(_gunluk(21)) is None, "21 nokta < 22 -> None")
    # 40 nokta ama 30 gun oncesi referansi olmayan seyrek seri (her 0.5 gun degil; ilk 10 gun yok)
    s = _gunluk(25)
    ok(ma.ozet(s) is None, "25 gunluk arsiv ~1 ay degil -> Ret1M icin referans yok -> None (uydurma yok)")


def test_ozet_degerler_dogru():
    s = _gunluk(60, adim=2.0)                       # 1000 .. 1118, her gun +2
    oz = ma.ozet(s)
    ok(oz is not None and oz["n"] == 60, "60 gunluk arsivden ozet uretilir")
    ref = s.iloc[-1 - 30]                           # tam 30 gun once
    beklenen = round((s.iloc[-1] - ref) / ref * 100, 4)
    ok(abs(oz["ret1m"] - beklenen) < 1e-9, f"Ret1M elle hesapla ayni ({beklenen})")
    ok(oz["rsi"] == 100.0, "yalniz yukselen seri -> RSI 100")
    ok(0.0 <= oz["skor"] <= 100.0 and oz["son"] == float(s.iloc[-1]), "skor 0-100, son fiyat dogru")
    ok(oz["son_tarih"] == s.index[-1].strftime("%Y-%m-%d"), "son tarih dogru")


def test_ozet_formulleri_live_data_ile_tutarli():
    import numpy as np
    import live_data as ld
    rng = np.random.default_rng(7)
    s = pd.Series(1000 * np.exp(np.cumsum(rng.normal(0, 0.01, 120))),
                  index=pd.date_range(end=ma.bugun_trt(), periods=120, freq="D"))
    ok(ma._rsi(s) == ld._compute_rsi(s), "RSI formulu live_data ile birebir")
    ok(ma._dd_duzeltmesi(s) == ld._hacim_dd_duzeltmesi_maden(s, None, 0.0)[1], "DD duzeltmesi live_data ile birebir")
    dusen = pd.Series([1000.0 * (0.97 ** i) for i in range(60)], index=pd.date_range(end=ma.bugun_trt(), periods=60, freq="D"))
    ok(ma._dd_duzeltmesi(dusen) == ld._hacim_dd_duzeltmesi_maden(dusen, None, 0.0)[1] == -7, "derin dusus -> -7 (iki taraf ayni)")
    oz = ma.ozet(s)
    from scoring import optima_score
    taban = optima_score(oz["rsi"], oz["ret1m"], vol=oz["vol"], has_fundamental=False)
    ok(abs(oz["skor"] - max(0, min(100, round(taban + ma._dd_duzeltmesi(s), 1)))) < 1e-9, "skor = scoring.optima_score + DD")


# ---------------------------------------------------------------- canlidoviz kesintisi
def _kesinti(monkey_arsiv_yolu):
    import live_data as ld
    ld._fetch_maden_history_canlidoviz = lambda bp_code: (None, 50.0, 0.0, None)   # 502 simulasyonu
    ma.ARSIV_DOSYASI = monkey_arsiv_yolu
    ld._MADEN_ARSIV_KULLANILAN.clear()
    return ld


def test_kesintide_ozet_arsivden():
    import live_data as ld
    orijinal = ld._fetch_maden_history_canlidoviz
    eski_yol = ma.ARSIV_DOSYASI
    try:
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "a.json")
            _arsive_yaz(yol, {"ALTIN_TRY": _gunluk(60, adim=2.0)})
            ld = _kesinti(yol)
            son, rsi, ret, skor = ld._fetch_maden_history_summary("gram-altin")
            ok(son is not None and skor is not None and rsi == 100.0, "canlidoviz yok -> arsivden RSI/Ret1M/skor")
            ok("ALTIN_TRY" in ld._MADEN_ARSIV_KULLANILAN, "arsiv kullanimi kayda gecer (gizlenmez)")
            ok(ld.status_summary()["maden_arsiv_kullanilan"] == ["ALTIN_TRY"], "durum raporunda gorunur")
            ok(ld._fetch_maden_history_summary("gram-gumus")[0] is None, "arsivi bos varlik -> veri yok")
            # arsiv eski (son nokta 10 gun once) -> kullanilmaz
            _arsive_yaz(yol, {"ALTIN_TRY": _gunluk(60, bitis=pd.Timestamp(ma.bugun_trt()) - pd.Timedelta(days=10))})
            ok(ld._fetch_maden_history_summary("gram-altin")[0] is None, "bayat arsiv fiyat/skor olarak kullanilmaz")
            # kapsam disi kod (Truncgil'in fiyat-yalniz turleri canlidoviz kodu tasimaz) -> veri yok
            ok(ld._fetch_maden_history_summary("gram-has-altin")[0] is None, "kapsam disi kod -> veri yok")
    finally:
        ld._fetch_maden_history_canlidoviz = orijinal
        ma.ARSIV_DOSYASI = eski_yol


def test_canlidoviz_calisirken_arsiv_kullanilmaz():
    import live_data as ld
    orijinal = ld._fetch_maden_history_canlidoviz
    eski_yol = ma.ARSIV_DOSYASI
    try:
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "a.json")
            _arsive_yaz(yol, {"ALTIN_TRY": _gunluk(60, adim=2.0)})
            ma.ARSIV_DOSYASI = yol
            ld._MADEN_ARSIV_KULLANILAN.clear()
            ld._fetch_maden_history_canlidoviz = lambda bp: (7000.0, 55.5, 3.3, 66.6)
            ok(ld._fetch_maden_history_summary("gram-altin") == (7000.0, 55.5, 3.3, 66.6),
               "canlidoviz varsa AYNEN o doner, arsivle karistirilmaz")
            ok(not ld._MADEN_ARSIV_KULLANILAN, "arsiv kullanilmadi")
    finally:
        ld._fetch_maden_history_canlidoviz = orijinal
        ma.ARSIV_DOSYASI = eski_yol


def _df_17():
    return pd.DataFrame([{
        "Ticker": "ALTIN_TRY", "Ad": "Gram Altın", "Kategori": "MADEN", "Son_Fiyat": 6644.78, "RSI": 50.0,
        "Ret1M": 0.0, "Ret3M": 0.0, "Ret6M": 0.0, "Ret1Y": 0.0, "Ret3Y": 0.0, "Ret5Y": 0.0, "Vol": 25.0,
        "YF_Symbol": "", "TEFAS_Kind": "", "Tur": "", "Risk_Deger": "", "_tcmb_guncellendi": "",
        "Optima_Skor": 0.0, "_gecmis_veri_yok": True}])


def test_extend_kesintide_satirlar_kaybolmaz():
    import live_data as ld
    orijinal = ld._fetch_maden_history_canlidoviz
    eski_yol = ma.ARSIV_DOSYASI
    coin = ["CEYREK_ALTIN", "YARIM_ALTIN", "TAM_ALTIN", "CUMHURIYET_ALTIN", "ATA_ALTIN"]
    try:
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "a.json")
            # (1) hic arsiv yok -> eskisi gibi satir eklenmez (uydurma fiyat yok)
            ld = _kesinti(yol)
            ok(len(ld.extend_maden_universe(_df_17())) == 1, "arsiv bos -> sikke satiri eklenmez")
            # (2) 3 gunluk arsiv: fiyat var, teknik yok -> 5 satir, 'veri yok' bayragi, skor bos
            _arsive_yaz(yol, {t: _gunluk(3, baslangic_fiyat=10000.0) for t in coin})
            out = ld.extend_maden_universe(_df_17())
            ok(len(out) == 6, "yalniz fiyat birikmis -> 5 sikke satiri korunur")
            r = out[out["Ticker"] == "CEYREK_ALTIN"].iloc[0]
            ok(r["Son_Fiyat"] == 10002.0 and bool(r["_gecmis_veri_yok"]) is True, "fiyat = arsivin son Truncgil fiyati, bayrak: veri yok")
            ok(r["Ad"] == "Çeyrek Altın" and r["Kategori"] == "MADEN", "ad/kategori dogru")
            # (3) 60 gunluk arsiv: teknik de var
            _arsive_yaz(yol, {t: _gunluk(60, baslangic_fiyat=10000.0, adim=5.0) for t in coin})
            out = ld.extend_maden_universe(_df_17())
            r = out[out["Ticker"] == "ATA_ALTIN"].iloc[0]
            ok(len(out) == 6 and bool(r["_gecmis_veri_yok"]) is False and r["Optima_Skor"] > 0 and r["RSI"] == 100.0,
               "yeterli birikim -> teknik gostergeler ve skor dolu, bayrak temiz")
            # (4) bayat arsiv -> satir yok
            _arsive_yaz(yol, {t: _gunluk(60, bitis=pd.Timestamp(ma.bugun_trt()) - pd.Timedelta(days=9)) for t in coin})
            ok(len(ld.extend_maden_universe(_df_17())) == 1, "bayat arsiv fiyati kullanilmaz")
    finally:
        ld._fetch_maden_history_canlidoviz = orijinal
        ma.ARSIV_DOSYASI = eski_yol


def test_grafik_arsivden_ve_donem_kirpma():
    import live_data as ld
    eski_yol = ma.ARSIV_DOSYASI
    try:
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "a.json")
            ma.ARSIV_DOSYASI = yol
            ok(ld._maden_arsiv_grafik("ALTIN_TRY", "1mo").empty, "arsiv bos -> bos grafik (veri yok)")
            _arsive_yaz(yol, {"ALTIN_TRY": _gunluk(100, adim=1.0)})
            g = ld._maden_arsiv_grafik("ALTIN_TRY", "1mo")
            ok(32 >= len(g) >= 31 and list(g.columns) == ["Open", "High", "Low", "Close"], "1 ay ~31 nokta, OHLC kolonlari")
            ok((g["Open"] == g["Close"]).all() and (g["High"] == g["Low"]).all(), "gunde tek fiyat: O=H=L=C (sahte mum uretilmez)")
            ok(len(ld._maden_arsiv_grafik("ALTIN_TRY", "3mo")) > len(g), "daha uzun donem daha fazla nokta")
            ok("arsiv" in g.attrs.get("kaynak", "").lower(), "kaynak etiketi tasinir")
    finally:
        ma.ARSIV_DOSYASI = eski_yol


# ---------------------------------------------------------------- kural taramasi
def test_modul_capraz_fiyat_icermez():
    src = open("maden_arsiv.py", encoding="utf-8").read()
    kod = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    govde = re.sub(r'""".*?"""', "", kod, flags=re.S)
    for yasak in ("yfinance", "yf.", "31.1035", "usdtry", "USDTRY", "GC=F", "SI=F", "PL=F"):
        ok(yasak not in govde, f"maden_arsiv.py kodunda '{yasak}' yok")


def test_workflow_arsivi_commit_eder():
    y = open(".github/workflows/update_data.yml", encoding="utf-8").read()
    ok("git add -f maden_tl_gecmis.json" in y, "workflow arsiv dosyasini commit eder")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"maden_arsiv testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
