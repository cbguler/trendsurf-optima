# -*- coding: utf-8 -*-
"""v2.0.7.403: Halka Arz XHARZ tablosu - iki satirli basliklar, sirket adi sutunu yok, sabit genislik (yatay kaydirma yok).
Calistir: python3 test_xharz_tablo.py (ag/veritabani yok)."""
import ast
import re
import sys

import pandas as pd

_n = {"ok": 0}


def ok(k, m):
    assert k, "BASARISIZ: " + m
    _n["ok"] += 1


SRC = open("app.py", encoding="utf-8").read()
TREE = ast.parse(SRC)


def _yukle():
    ns = {"pd": pd}
    for n in TREE.body:
        if isinstance(n, ast.FunctionDef) and n.name == "fmt_tr":
            exec(compile(ast.Module([n], []), "app.py", "exec"), ns)
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in ("_XH_SUTUNLAR", "_XH_BASLIK_IPUCU"):
            exec(compile(ast.Module([n], []), "app.py", "exec"), ns)
        if isinstance(n, ast.FunctionDef) and n.name == "_xharz_tablo_html":
            exec(compile(ast.Module([n], []), "app.py", "exec"), ns)
    return ns


NS = _yukle()
SUT = NS["_XH_SUTUNLAR"]
HTML = NS["_xharz_tablo_html"]


def _df():
    return pd.DataFrame([
        {"Ticker": "INTET", "Şirket": "İNTETRA <TEKNOLOJİ> A.Ş.", "Durum": "XHARZ dışı (yeni işlem görüyor)", "Son_Fiyat": 50.1,
         "RSI": 55.04, "Ret1M": -3.456, "Optima_Skor": 27.0, "Arz_Fiyati": 53.6, "Iskonto_Orani": 20.0, "Graham_Degeri": 20.607,
         "Carpan_Bazli_Deger": 73.69, "Uyari": "KAP DİKKAT", "Fiyat_Tespit_URL": "https://www.kap.org.tr/tr/Bildirim/1654263",
         "KAP_URL": "https://www.kap.org.tr/tr/Bildirim/1"},
        {"Ticker": "ZRGYO", "Şirket": "ZİRAAT GYO", "Durum": "", "Son_Fiyat": 19.0, "RSI": 40.7, "Ret1M": -4.33, "Optima_Skor": 66.0,
         "Arz_Fiyati": None, "Iskonto_Orani": float("nan"), "Graham_Degeri": None, "Carpan_Bazli_Deger": None, "Uyari": "",
         "Fiyat_Tespit_URL": "", "KAP_URL": None},
        {"Ticker": "KTLEV", "Şirket": "X", "Durum": "", "Son_Fiyat": 1.0, "RSI": 50.0, "Ret1M": 0.0, "Optima_Skor": 0.0, "Arz_Fiyati": None,
         "Iskonto_Orani": None, "Graham_Degeri": None, "Carpan_Bazli_Deger": None, "Uyari": "SPK TEDBİRİ", "Fiyat_Tespit_URL": "", "KAP_URL": ""},
    ])


def test_yapi():
    h = HTML(_df())
    basliklar = re.findall(r"<th[^>]*>(.*?)</th>", h)
    ok(len(basliklar) == 12, f"12 sutun ({len(basliklar)})")
    ok(not any("Şirket" in b for b in basliklar), "sirket adi SUTUNU yok")
    ok(all("<br>" in b for b in basliklar if b != "Uyarı"), "tum basliklar (Uyari haric) iki satir")
    ok(sum(c[2] for c in SUT) == 100, f"genislikler toplam %100 ({sum(c[2] for c in SUT)})")
    masaustu = h.split("@media")[0]
    ok("table-layout:fixed" in masaustu and "overflow-x:hidden" in masaustu and "min-width" not in masaustu,
       "masaustu: sabit yerlesim, yatay kaydirma yok, min-width yok")
    ok("max-width: 820px" in h and "overflow-x:auto" in h.split("@media")[1], "yalniz dar ekranda (telefon) yatay kaydirma acilir")
    ok("position:sticky" in h and "max-height:640px" in h, "sabit baslik + dikey kaydirma")
    ok(len(re.findall(r"<tr>", h)) == 4, "1 baslik + 3 veri satiri")


def test_icerik():
    h = HTML(_df())
    ok('title="İNTETRA &lt;TEKNOLOJİ&gt; A.Ş."' in h, "sirket adi ticker uzerinde ipucu olarak, HTML kacisli")
    ok("<b>INTET</b><sup" in h and h.count("<sup") == 1, "yalniz XHARZ disi satirda * isareti")
    ok(">50,1000<" in h and ">55,0<" in h and ">-3,46<" in h and ">27,0<" in h, "Turkce sayi bicimi (fiyat 4, RSI 1, getiri 2, skor 1)")
    ok(">53,60<" in h and ">20,61<" in h and ">73,69<" in h, "arz/graham/carpan 2 ondalik")
    ok("Rapor</a>" in h and "Görüntüle</a>" in h and h.count("<a ") == 2, "yalniz gercek linkler (bos link yok)")
    ok("color:#b45309" in h and "color:#8e1b10" in h, "KAP DIKKAT turuncu, tedbir kirmizi")
    ok('<td style="text-align:right;"></td>' in h and 'class="xh-uyari"' in h, "degersiz hucre BOS (nokta/tire yok); uyari hucresi sarar")


def test_sayfa_baglantisi():
    ok("st.markdown(_xharz_tablo_html(df_show" in SRC, "sayfa yeni tabloyu kullanir")
    i = SRC.index('elif page=="Halka Arz":')
    j = SRC.index('elif page=="Temettü"')
    ok("st.dataframe(tablo_df" not in SRC[i:j], "Halka Arz sayfasinda eski st.dataframe tablosu yok")
    ok("CSV İndir" in SRC[i:j], "CSV indirme duruyor")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"test_xharz_tablo: {_n['ok']}/{_n['ok']} OK")
    sys.exit(0)
