# -*- coding: utf-8 -*-
"""v2.0.7.401: Halka Arz sayfasinda genc varlik (SINIRLI VERI) kisiti yok; diger sayfalarda/uyarilarda degisiklik yok.
Calistir: python3 test_halka_arz_sinirli.py (ag/veritabani yok; streamlit sahtelenir)."""
import ast
import sys

_n = {"ok": 0}


def ok(k, m):
    assert k, "BASARISIZ: " + m
    _n["ok"] += 1


SRC = open("app.py", encoding="utf-8").read()
TREE = ast.parse(SRC)


class _SahteSt:
    def __init__(self): self.cikti = []
    def markdown(self, metin, **kw): self.cikti.append(metin)


def _ozet_fonksiyonu(st):
    for n in TREE.body:
        if isinstance(n, ast.FunctionDef) and n.name == "_uyari_ozeti_goster":
            ns = {"st": st}
            exec(compile(ast.Module([n], []), "app.py", "exec"), ns)
            return ns["_uyari_ozeti_goster"]
    raise AssertionError("_uyari_ozeti_goster yok")


HARITA = {
    "NETCD": ("SINIRLI VERİ", "kisa gecmis"),
    "EMPAE": ("SINIRLI VERİ", "kisa gecmis"),
    "SAMAT": ("KAP DİKKAT", "bedelli"),
    "ENERY": ("KAP BİLGİ", "geri alim"),
}


def test_varsayilan_serit_cizilir():
    st = _SahteSt()
    _ozet_fonksiyonu(st)(["NETCD", "EMPAE", "SAMAT", "ENERY"], HARITA)
    tum = " ".join(st.cikti)
    ok("Sınırlı veri: 2 hissenin" in tum, "diger sayfalar icin sinirli veri seridi AYNEN calisir")
    ok("SAMAT" in tum and "ENERY" in tum, "KAP DIKKAT ve KAP BILGI seritleri")


def test_halka_arzda_serit_yok_ama_uyarilar_var():
    st = _SahteSt()
    _ozet_fonksiyonu(st)(["NETCD", "EMPAE", "SAMAT", "ENERY"], HARITA, sinirli_goster=False)
    tum = " ".join(st.cikti)
    ok("Sınırlı veri" not in tum and "NETCD" not in tum and "EMPAE" not in tum, "Halka Arz: sinirli veri seridi yok")
    ok("SAMAT" in tum and "KAP DİKKAT" in tum, "Halka Arz: KAP DIKKAT uyarisi hala gorunur")
    ok("ENERY" in tum, "Halka Arz: KAP BILGI notu hala gorunur")


def test_halka_arz_blogu_ve_diger_cagri():
    i = SRC.index('page=="Halka Arz"') if 'page=="Halka Arz"' in SRC else SRC.index("Halka Arz Takip")
    j = SRC.index('elif page=="Temettü"')
    blok = SRC[i:j]
    ok('v[0] != "SINIRLI VERİ"' in blok, "Halka Arz blogu SINIRLI VERI etiketini haritadan cikarir (Uyari sutunu da temiz)")
    ok("sinirli_goster=False" in blok, "Halka Arz blogu seridi kapatir")
    t = SRC[j:j + 12000]
    ok("_uyari_ozeti_goster(df_show[\"Ticker\"].tolist(), _tm_uyari)" in t, "Temettu cagrisi degismedi (varsayilan: serit acik)")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"test_halka_arz_sinirli: {_n['ok']}/{_n['ok']} OK")
    sys.exit(0)
