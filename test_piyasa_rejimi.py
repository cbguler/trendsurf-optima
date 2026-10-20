"""v2.0.7.426: piyasa rejimi bilgi seridi testleri. Calistir: python test_piyasa_rejimi.py"""
import ast
import sys
import warnings
from datetime import date

warnings.filterwarnings("ignore")
import piyasa_rejimi as pr

_n = {"ok": 0}


def ok(kosul, mesaj):
    if not kosul:
        print("BASARISIZ:", mesaj)
        sys.exit(1)
    _n["ok"] += 1


# --- veri butunlugu ---
ids = [r["id"] for r in pr.REJIMLER]
ok(len(ids) == len(set(ids)), "id'ler benzersiz olmali")
for r in pr.REJIMLER:
    for k in ("id", "rozet", "baslik", "ozet", "ayrinti", "kaynaklar", "kapsam", "baslangic"):
        ok(k in r, f"{r['id']}: {k} alani eksik")
    ok(all(u.startswith("https://") for _, u in r["kaynaklar"]), "kaynaklar https olmali")
    ok(len(r["kaynaklar"]) >= 1, "en az bir kaynak olmali")

# --- tarih mantigi ---
ok(pr.aktif_rejimler("Ana Sayfa", date(2026, 10, 15)) == [], "baslangictan once gizli")
ok(len(pr.aktif_rejimler("Ana Sayfa", date(2026, 10, 16))) == 1, "baslangic gunu gorunur")
ok(len(pr.aktif_rejimler("Ana Sayfa", date(2027, 6, 30))) == 1, "bitis yoksa surer")
ok(len(pr.aktif_rejimler("BIST", date(2026, 10, 20))) == 1, "BIST'te gorunur")
ok(len(pr.aktif_rejimler("TEFAS", date(2026, 10, 20))) == 1, "TEFAS'ta gorunur")
ok(pr.aktif_rejimler("Döviz", date(2026, 10, 20)) == [], "Doviz'de gorunmez")
ok(pr.aktif_rejimler("Portföyüm", date(2026, 10, 20)) == [], "Portfoyum'de gorunmez")

# bitis tarihi: o gun dahil degil, ertesi gunden gizli degil - o gunden itibaren gizli
_orj = list(pr.REJIMLER)
pr.REJIMLER[:] = [dict(_orj[0], bitis="2026-11-01")]
ok(len(pr.aktif_rejimler("Ana Sayfa", date(2026, 10, 31))) == 1, "bitisten bir gun once gorunur")
ok(pr.aktif_rejimler("Ana Sayfa", date(2026, 11, 1)) == [], "bitis gunu gizli")
pr.REJIMLER[:] = _orj

# --- skoru degistirmez: modul skorlama koduna dokunmaz ---
src = open("piyasa_rejimi.py", encoding="utf-8").read()
ok("scoring" not in src and "Optima_Skor" not in src.replace("Optima Skor'u", ""), "skorlamaya bagimli olmamali")
ok("Optima Skor'u DEĞİŞTİRMEZ" in pr.REJIMLER[0]["ayrinti"][-1], "metin skoru degistirmedigini soylemeli")

# --- app.py entegrasyonu: 3 cagri noktasi + yardimci ---
app = open("app.py", encoding="utf-8").read()
ok("def _piyasa_rejimi_goster(sayfa):" in app, "yardimci tanimli")
ok('_piyasa_rejimi_goster("Ana Sayfa")' in app, "Ana Sayfa'da cagriliyor")
ok('cat_code in ("BIST", "TEFAS")' in app and "_piyasa_rejimi_goster(page)" in app, "BIST/TEFAS'ta cagriliyor")

# --- yardimci gercekten cizer (AppTest, app.py'den cikarilan fonksiyonla) ---
agac = ast.parse(app)
fn = next(n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name == "_piyasa_rejimi_goster")
fn_src = ast.get_source_segment(app, fn)
from streamlit.testing.v1 import AppTest

at = AppTest.from_string("import streamlit as st\n" + fn_src + "\n_piyasa_rejimi_goster('Ana Sayfa')\n"
                         "_piyasa_rejimi_goster('Döviz')\n")
at.run(timeout=30)
ok(not at.exception, f"hata olmamali: {at.exception}")
govde = " ".join(m.value for m in at.markdown)
ok("PİYASA REJİMİ" in govde and "MSCI" in govde, "serit metni cizilmeli")
ok(govde.count("PİYASA REJİMİ") == 1, "yalniz kapsamdaki sayfada (Doviz'de degil) cizilmeli")
ok(any("bloomberght.com" in m.value for m in at.markdown), "kaynak baglantisi cizilmeli")
ok(len(at.expander) == 1, "ayrinti kutusu bir kez cizilmeli")

print(f"{_n['ok']} kontrol gecti")
print("TUM TESTLER GECTI")
