# -*- coding: utf-8 -*-
"""v2.0.7.402: XHARZ tablosunda kalici Arz Fiyati/Iskonto/Graham/Carpan sutunlari + halka arz deger arsivi.
Calistir: python3 test_ipo_xharz_deger.py (ag/veritabani yok; arsiv sahtelenir)."""
import json
import sys

import pandas as pd

import upcoming_ipo_client as U

_n = {"ok": 0}


def ok(k, m):
    assert k, "BASARISIZ: " + m
    _n["ok"] += 1


def test_ad_anahtari():
    a = U.ad_anahtari("Net Global Endüstriyel Yatırımlar A.Ş")
    b = U.ad_anahtari("NET GLOBAL ENDÜSTRİYEL YATIRIMLAR A.Ş.")
    ok(a == b == "AD:NET GLOBAL ENDUSTRIYEL YATIRIMLAR", f"Turkce harf/ek katlama: {a!r} {b!r}")
    ok(U.ad_anahtari("İNTETRA TEKNOLOJİ VE BİLİŞİM HİZMETLERİ A.Ş.") == U.ad_anahtari("İntetra Teknoloji ve Bilişim Hizmetleri A.Ş"),
       "Intetra iki yazim ayni anahtar")
    ok(U.ad_anahtari("NETCAD YAZILIM A.Ş.") != U.ad_anahtari("Net Global Endüstriyel Yatırımlar A.Ş"), "farkli sirketler eslesmez")
    ok(U.ad_anahtari("A.Ş.") == "" and U.ad_anahtari(None) == "" and U.ad_anahtari(float("nan")) == "", "anlamsiz ad -> bos")
    ok(U._ticker_anahtari("netgl") == "T:NETGL" and U._ticker_anahtari("") == "" and U._ticker_anahtari("TOO LONG X") == "", "ticker anahtari")


class _Sahte:
    """arsiv/ft kaynaklarini bellekte sahteler."""
    def __init__(self, arsiv, ft):
        self.arsiv, self.ft = arsiv, ft
        self.orj = (U._arsiv_oku, U._ft_ticker_degerleri)
    def __enter__(self):
        U._arsiv_oku = lambda: self.arsiv
        U._ft_ticker_degerleri = lambda: self.ft
    def __exit__(self, *a):
        U._arsiv_oku, U._ft_ticker_degerleri = self.orj


def _xharz():
    return pd.DataFrame([
        {"Ticker": "KPEKS", "Şirket": "KAPEKS KİMYA SANAYİ A.Ş.", "Son_Fiyat": 1.0, "RSI": 50.0, "Ret1M": 1.0, "Optima_Skor": 50.0},
        {"Ticker": "NETCD", "Şirket": "NETCAD YAZILIM A.Ş.", "Son_Fiyat": 2.0, "RSI": 50.0, "Ret1M": 1.0, "Optima_Skor": 40.0},
        {"Ticker": "GOLDA", "Şirket": "GOLDA GIDA SANAYİ VE TİCARET A.Ş.", "Son_Fiyat": 3.0, "RSI": 50.0, "Ret1M": 1.0, "Optima_Skor": 45.0},
    ])


def _uni():
    return pd.DataFrame([
        {"Ticker": "NETGL", "Ad": "NET GLOBAL ENDÜSTRİYEL YATIRIMLAR A.Ş.", "Kategori": "BIST", "Son_Fiyat": 13.0, "RSI": 55.0, "Ret1M": 2.0, "Optima_Skor": 60.0},
        {"Ticker": "INTET", "Ad": "İNTETRA TEKNOLOJİ VE BİLİŞİM HİZMETLERİ A.Ş.", "Kategori": "BIST", "Son_Fiyat": 51.7, "RSI": 50.0, "Ret1M": 1.0, "Optima_Skor": 50.0},
        {"Ticker": "BKRGY", "Ad": "BAKIRCI GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.", "Kategori": "BIST", "Son_Fiyat": 5.7, "RSI": 50.0, "Ret1M": 1.0, "Optima_Skor": 50.0},
        {"Ticker": "THYAO", "Ad": "TÜRK HAVA YOLLARI A.O.", "Kategori": "BIST", "Son_Fiyat": 300.0, "RSI": 50.0, "Ret1M": 1.0, "Optima_Skor": 70.0},
        {"Ticker": "KPEKS", "Ad": "KAPEKS KİMYA SANAYİ A.Ş.", "Kategori": "BIST", "Son_Fiyat": 1.0, "RSI": 50.0, "Ret1M": 1.0, "Optima_Skor": 50.0},
    ])


ARSIV = {
    U.ad_anahtari("Net Global Endüstriyel Yatırımlar A.Ş"): {"sirket": "Net Global", "arz_fiyati": 20.0, "iskonto_orani": 20.0,
        "graham_degeri": None, "carpan_bazli_deger": None, "fiyat_tespit_url": "https://www.kap.org.tr/tr/Bildirim/1659236"},
    U.ad_anahtari("İntetra Teknoloji ve Bilişim Hizmetleri A.Ş"): {"sirket": "Intetra", "arz_fiyati": 53.6, "iskonto_orani": 20.0,
        "graham_degeri": 20.6, "carpan_bazli_deger": 73.7, "fiyat_tespit_url": ""},
    # Bakirci: adi arsivde ama HIC degeri yok -> ek satir olmaz
    U.ad_anahtari("Bakırcı Gayrimenkul Yatırım Ortaklığı A.Ş"): {"sirket": "Bakirci", "arz_fiyati": None, "iskonto_orani": None,
        "graham_degeri": None, "carpan_bazli_deger": None, "fiyat_tespit_url": ""},
    "T:GOLDA": {"sirket": "Golda", "arz_fiyati": 10.0, "iskonto_orani": 15.0, "graham_degeri": 5.0, "carpan_bazli_deger": 9.0, "fiyat_tespit_url": ""},
}
FT = {"KPEKS": {"arz_fiyati": 94.0, "iskonto_orani": 20.0, "graham_degeri": 53.7, "carpan_bazli_deger": 80.58,
                "fiyat_tespit_url": "https://www.kap.org.tr/tr/Bildirim/1645057"}}


def test_kolonlar_kalici_ve_bos():
    with _Sahte({}, {}):
        df, ek = U.xharz_ipo_degerlerini_ekle(_xharz(), _uni())
    for k in U.IPO_DEGER_KOLONLARI:
        ok(k in df.columns, f"{k} kolonu her zaman var")
    ok(df["Graham_Degeri"].isna().all() and (df["Fiyat_Tespit_URL"] == "").all(), "veri yokken hucreler bos")
    ok(len(ek) == 0 and len(df) == 3, "arsiv yokken ek satir yok, uyeler korunur")


def test_eslesme_ve_ek_satirlar():
    with _Sahte(ARSIV, FT):
        df, ek = U.xharz_ipo_degerlerini_ekle(_xharz(), _uni())
    d = df.set_index("Ticker")
    ok(d.loc["KPEKS", "Graham_Degeri"] == 53.7 and d.loc["KPEKS", "Arz_Fiyati"] == 94.0, "Fiyat Tespit kaynagindan (ticker) degerler")
    ok(d.loc["KPEKS", "Fiyat_Tespit_URL"].endswith("1645057"), "rapor linki")
    ok(d.loc["GOLDA", "Arz_Fiyati"] == 10.0 and d.loc["GOLDA", "Carpan_Bazli_Deger"] == 9.0, "T: anahtariyla arsivden")
    ok(pd.isna(d.loc["NETCD", "Arz_Fiyati"]) and pd.isna(d.loc["NETCD", "Graham_Degeri"]),
       "NETCAD (farkli sirket) Net Global degerlerini ALMAZ")
    ek = ek.set_index("Ticker")
    ok(set(ek.index) == {"NETGL", "INTET"}, f"ek satirlar: yalniz adi tam eslesen ve degeri olan evren hisseleri ({set(ek.index)})")
    ok(ek.loc["INTET", "Graham_Degeri"] == 20.6 and ek.loc["INTET", "Carpan_Bazli_Deger"] == 73.7, "INTET degerleri")
    ok(ek.loc["NETGL", "Arz_Fiyati"] == 20.0 and pd.isna(ek.loc["NETGL", "Graham_Degeri"]), "NETGL: arz var, Graham bos (uydurulmaz)")
    ok(ek.loc["NETGL", "Durum"].startswith("XHARZ dışı") and ek.loc["NETGL", "Son_Fiyat"] == 13.0, "ek satir durum ve fiyat evrenden")
    ok("BKRGY" not in ek.index and "THYAO" not in ek.index and "KPEKS" not in ek.index, "degersiz/ilgisiz/zaten-uye satir eklenmez")


def test_hata_olursa_kolonlar_bos():
    orj = U._arsiv_oku
    U._arsiv_oku = lambda: (_ for _ in ()).throw(RuntimeError("db yok"))
    try:
        df, ek = U.xharz_ipo_degerlerini_ekle(_xharz(), _uni())
    finally:
        U._arsiv_oku = orj
    ok(all(k in df.columns for k in U.IPO_DEGER_KOLONLARI) and len(df) == 3 and len(ek) == 0, "hata: kolonlar var, bos, sayfa bozulmaz")


def test_adaylar_arsive_yazilir():
    yazilan = []
    orj = U._arsiv_yaz
    U._arsiv_yaz = lambda k: yazilan.extend(k)
    try:
        df = pd.DataFrame([{"Sirket": "Net Global Endüstriyel Yatırımlar A.Ş", "_related_kod": "NETGL, XYZ", "Arz_Fiyati": 20.0,
                            "Iskonto_Orani": 20.0, "Graham_Degeri": None, "Carpan_Bazli_Deger": float("nan"),
                            "Fiyat_Tespit_URL": "u"}])
        U.arsive_adaylari_yaz(df)
    finally:
        U._arsiv_yaz = orj
    an = {k["anahtar"]: k for k in yazilan}
    ok(set(an) == {"AD:NET GLOBAL ENDUSTRIYEL YATIRIMLAR", "T:NETGL", "T:XYZ"}, f"ad ve iliskili kodlar anahtar olur ({set(an)})")
    k = an["T:NETGL"]
    ok(k["arz_fiyati"] == 20.0 and k["graham_degeri"] is None and k["carpan_bazli_deger"] is None, "NaN/None -> None (0 degil)")
    U.arsive_adaylari_yaz(pd.DataFrame())  # bos: hata vermez
    ok(True, "bos df hata vermez")


def test_tohum_ve_kaynak_baglantilari():
    t = json.load(open("ipo_arsiv_tohum.json", encoding="utf-8"))
    ok(len(t) == 3 and all(U.ad_anahtari(x["sirket"]) and U._ticker_anahtari(x["ticker"]) for x in t), "tohum: 3 kayit, ad ve ticker anahtari gecerli")
    ok({x["ticker"] for x in t} == {"NETGL", "INTET", "BKRGY"}, "tohum tickerlari")
    src = open("upcoming_ipo_client.py", encoding="utf-8").read()
    i, j = src.index("arsive_adaylari_yaz(df)"), src.index("SELECT ticker FROM bist_universe_dynamic")
    ok(i < j, "arsive yazma, mezun filtresinden ONCE")
    dbs = open("db.py", encoding="utf-8").read()
    ok("CREATE TABLE IF NOT EXISTS ipo_xharz_degerler" in dbs and '"ipo_xharz_degerler"' in dbs, "db.py: tablo + RLS listesi")
    app = open("app.py", encoding="utf-8").read()
    ok("xharz_ipo_degerlerini_ekle(df_ipo, df_uni)" in app and '"Graham_Degeri"' in app and "Çarpan Bazlı Değer (₺)" in app, "app.py sutunlari")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"test_ipo_xharz_deger: {_n['ok']}/{_n['ok']} OK")
    sys.exit(0)
