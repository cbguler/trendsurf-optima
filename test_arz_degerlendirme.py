# -*- coding: utf-8 -*-
"""v2.0.7.406: Arz Fiyati renk kurali (ortak arz_konumu), XHARZ tablosunda renkli Arz Fiyati hucresi ve belirgin
'Nasil okunur' kutusu. Calistir: python3 test_arz_degerlendirme.py (ag/veritabani yok)."""
import ast
import re

import pandas as pd

_n = {"ok": 0}


def ok(k, m):
    assert k, "BASARISIZ: " + m
    _n["ok"] += 1


SRC = open("app.py", encoding="utf-8").read()
TREE = ast.parse(SRC)
NS = {"pd": pd}
for n in TREE.body:
    if isinstance(n, ast.FunctionDef) and n.name in ("fmt_tr", "arz_konumu", "halka_arz_nasil_okunur_html", "_xharz_tablo_html"):
        exec(compile(ast.Module([n], []), "app.py", "exec"), NS)
    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in ("_XH_SUTUNLAR", "_XH_BASLIK_IPUCU", "ARZ_RENKLER"):
        exec(compile(ast.Module([n], []), "app.py", "exec"), NS)
K = NS["arz_konumu"]
R = NS["ARZ_RENKLER"]
nan = float("nan")

# konum kurali
ok(K(10, 20, 30) == "alt", "iki degerin de altinda -> alt")
ok(K(25, 20, 30) == "icinde", "arada -> icinde")
ok(K(20, 20, 30) == "icinde" and K(30, 20, 30) == "icinde", "sinirda -> icinde")
ok(K(40, 20, 30) == "ust", "ikisinin de ustunde -> ust")
ok(K(25, 30, 20) == "icinde", "sira onemsiz")
ok(K(10, 20, None) == "alt" and K(40, None, 30) == "ust" and K(30, None, 30) == "icinde", "tek deger: o degerle kiyas")
ok(K(10, nan, nan) is None and K(10, None, None) is None, "iki deger de yok -> renksiz")
ok(K(None, 20, 30) is None and K(nan, 20, 30) is None, "arz yok -> renksiz")
ok(K(53.6, 20.607, 73.69) == "icinde", "INTET gercek degerleri: sari")

# XHARZ tablosu hucre renkleri
df = pd.DataFrame([
    {"Ticker": "AAA", "Şirket": "A", "Durum": "", "Arz_Fiyati": 10.0, "Graham_Degeri": 20.0, "Carpan_Bazli_Deger": 30.0, "Uyari": ""},
    {"Ticker": "BBB", "Şirket": "B", "Durum": "", "Arz_Fiyati": 25.0, "Graham_Degeri": 20.0, "Carpan_Bazli_Deger": 30.0, "Uyari": ""},
    {"Ticker": "CCC", "Şirket": "C", "Durum": "", "Arz_Fiyati": 40.0, "Graham_Degeri": 20.0, "Carpan_Bazli_Deger": 30.0, "Uyari": ""},
    {"Ticker": "DDD", "Şirket": "D", "Durum": "", "Arz_Fiyati": 40.0, "Graham_Degeri": None, "Carpan_Bazli_Deger": None, "Uyari": ""},
    {"Ticker": "EEE", "Şirket": "E", "Durum": "", "Arz_Fiyati": None, "Graham_Degeri": 20.0, "Carpan_Bazli_Deger": 30.0, "Uyari": ""},
])
html = NS["_xharz_tablo_html"](df)
satirlar = re.findall(r"<tr>(.*?)</tr>", html.split("<tbody>")[1], re.S)
# Arz Fiyati sutununun indeksi
idx = [c[0] for c in NS["_XH_SUTUNLAR"] if c[0] in df.columns].index("Arz_Fiyati")
def hucre(i):
    return re.findall(r"<td[^>]*>.*?</td>", satirlar[i], re.S)[idx]
ok(R["alt"] in hucre(0), "XHARZ: yesil hucre")
ok(R["icinde"] in hucre(1), "XHARZ: sari hucre")
ok(R["ust"] in hucre(2), "XHARZ: kirmizi hucre")
ok("background" not in hucre(3), "XHARZ: degerler yoksa renksiz")
ok("background" not in hucre(4), "XHARZ: arz fiyati yoksa renksiz")

# Aciklama kutusu
kutu = NS["halka_arz_nasil_okunur_html"]("<b>Ek</b>")
ok("Nasıl okunur" in kutu and "22,5" in kutu and "EBITDA" in kutu and "sektör medyan" in kutu, "yontem metni")
ok(all(R[k] in kutu for k in R), "uc renk kutuda")
ok("Yeşil" in kutu and "Sarı" in kutu and "Kırmızı" in kutu, "renk adlari")
ok("tavsiyesi" in kutu and "<b>Ek</b>" in kutu, "uyari ve ek not")
ok(all(ord(ch) < 0x2600 for ch in kutu), "emoji yok")
ok("border:2px solid" in kutu and "font-size:15px" in kutu, "belirgin kutu stili")

# sayfa baglantisi: iki tablo da ayni kutuyu kullanir, eski soluk not yok
ok(SRC.count("halka_arz_nasil_okunur_html(") >= 3, "iki sayfa blogu kutuyu cagiriyor")
ok("color:#333333; font-size:14px; line-height:1.5; margin-top:10px;" not in SRC, "eski soluk not kaldirildi")
ok("def _arz_renk" in SRC and "arz_konumu(arz, graham, carpan)" in SRC, "Yaklasan tablosu ortak kurali kullanir")
print(f"test_arz_degerlendirme: {_n['ok']}/{_n['ok']} OK")
