# -*- coding: utf-8 -*-
"""v2.0.7.429: msci_izleme.py + otomatik MSCI seridi testleri (ag/DB gerektirmez)."""
import ast
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msci_izleme as m
import piyasa_rejimi as pr

_n = {"ok": 0}


def ok(c, msg):
    if not c:
        print("BASARISIZ:", msg)
        sys.exit(1)
    _n["ok"] += 1


# --- gercek MSCI listesinden (20 Ekim 2026) kesit ---
LISTE = """
<table><tr><td valign="top">Date</td><td>Title</td></tr>
<tr><td valign="top">16 Oct 2026</td>
 <td valign="top"><a href="DocGet?pub_key=jghgtF7epXI%3D&lang=en&format=html">GLOBAL INDUSTRY CLASSIFICATION STANDARD (GICS) CHANGES</a></td></tr>
<tr><td valign="top">15 Oct 2026</td>
 <td valign="top"><a href="DocGet?pub_key=g3LK9l%2Bo2iA%3D&lang=en&format=html">MSCI IMPLEMENTS A FREEZE ON THE MSCI TURKEY INDEXES</a></td></tr>
<tr><td valign="top">15 Oct 2026</td>
 <td valign="top"><a href="DocGet?pub_key=cOQ9FiTsR0g%3D&lang=en&format=html">MSCI LAUNCHES A CONSULTATION ON A PROPOSAL TO RECLASSIFY INDONESIA FROM EMERGING MARKET TO STANDALONE MARKET STATUS</a></td></tr>
<tr><td valign="top">01 Oct 2026</td>
 <td valign="top"><a href="DocGet?pub_key=AAA%3D&lang=en&format=html">US: WARNER BROS DISCOVERY</a></td></tr>
<tr><td valign="top">30 Sep 2026</td>
 <td valign="top"><a href="DocGet?pub_key=BBB%3D&lang=en&format=html">TR: AKBANK</a></td></tr>
</table>"""
L = m.liste_ayikla(LISTE)
ok(len(L) == 5, f"5 satir ayiklanmali: {len(L)}")
ok(L[1]["baslik"] == "MSCI IMPLEMENTS A FREEZE ON THE MSCI TURKEY INDEXES", "baslik")
ok(L[1]["tarih"] == date(2026, 10, 15), "tarih")
ok(L[1]["pub_key"] == "g3LK9l%2Bo2iA%3D", "pub_key (url-kodlu, sabit)")
ok(L[1]["url"].startswith("https://app2.msci.com/webapp/index_ann/DocGet?pub_key=g3LK9l"), "mutlak url")
ok("&amp;" not in L[1]["url"], "html varlik cozumu")
ok(m.liste_ayikla("") == [] and m.liste_ayikla("<html>degisti</html>") == [], "bos/bozuk liste -> []")

# --- ilgili sayma ---
ok(m.baslikta_turkiye_mi("MSCI IMPLEMENTS A FREEZE ON THE MSCI TURKEY INDEXES"), "TURKEY basliga")
ok(m.baslikta_turkiye_mi("Türkiye endeksleri"), "Turkce yazim")
ok(m.baslikta_turkiye_mi("TR: AKBANK"), "TR: sirket duyurusu")
ok(not m.baslikta_turkiye_mi("US: WARNER BROS DISCOVERY") and not m.baslikta_turkiye_mi("TRANSPORT"), "yanlis pozitif yok")
ok(m.metin_konusu_mu("MSCI LAUNCHES A CONSULTATION ON A PROPOSAL TO RECLASSIFY INDONESIA"), "konu: istisare")
ok(not m.metin_konusu_mu("LIST OF METHODOLOGY BOOKS UPDATED"), "konu degil")

metin_serit = ("MSCI IMPLEMENTS A FREEZE ON THE MSCI TURKEY INDEXES STANDARD ANNOUNCEMENTS - October 15, 2026 "
               "Announcement for October 15, 2026 MSCI IMPLEMENTS A FREEZE ON THE MSCI TURKEY INDEXES "
               "MSCI announced that it will apply a freeze on certain index related changes for Turkish equity "
               "securities, effective immediately. MSCI highlighted serious concerns.")
al = m.turkiye_alintisi(metin_serit, "MSCI IMPLEMENTS A FREEZE ON THE MSCI TURKEY INDEXES")
ok(al.startswith("MSCI announced that it will apply a freeze"), f"alinti basliksiz baslamali: {al}")
ok(m.turkiye_alintisi("Hicbir sey yok burada.") is None, "Turkiye yoksa None")
ok(len(m.turkiye_alintisi("Turkey " + "x" * 600 + ".")) <= 400, "alinti kisaltilir")
ok(m.metni_temizle("<p>A <b>B</b></p><script>x()</script>") .startswith("A B"), "html temizleme")

# degerlendir: baslik Turkiye -> metin cekilip alinti; konu -> metinde Turkiye varsa; yoksa ilgisiz
cagri = []
def fake(url):
    cagri.append(url)
    return metin_serit
r = m.degerlendir(L[1], fake)
ok(r[0] is True and r[1] == "baslikta Turkiye geciyor" and r[2].startswith("MSCI announced"), f"baslik eslesmesi: {r}")
r = m.degerlendir(L[3], fake)   # US sirketi
ok(r == (False, None, None) and len(cagri) == 1, "ilgisiz baslik icin metin CEKILMEZ")
r = m.degerlendir(L[2], lambda u: "Indonesia reclassification text only.")
ok(r == (False, None, None), "konu uygun ama metinde Turkiye yok -> ilgisiz")
r = m.degerlendir(L[2], lambda u: "The proposal also mentions Turkey as a comparison. Other text.")
ok(r[0] is True and r[1] == "metinde Turkiye geciyor" and "Turkey" in r[2], f"metinde Turkiye: {r}")
r = m.degerlendir(L[4], fake)
ok(r[0] is True and "TR:" in r[1], "TR: sirket duyurusu ilgili")
def patlayan(u):
    raise RuntimeError("ag yok")
r = m.degerlendir(L[1], patlayan)
ok(r[0] is True and r[2] is None, "baslik eslesir, metin alinamazsa yine ilgili (alintisiz)")
r = m.degerlendir(L[2], patlayan)
ok(r[0] is False, "belirsizse (metin yok) ilgili SAYILMAZ")

# --- otomatik serit kayitlari ---
bugun = date(2026, 10, 20)
dz = [
    {"pub_key": "k1", "tarih": "2026-10-15", "baslik": "MSCI IMPLEMENTS A FREEZE ON THE MSCI TURKEY INDEXES",
     "url": "https://x/1", "alinti": "a"},
    {"pub_key": "k2", "tarih": "2026-10-19", "baslik": "MSCI LAUNCHES A CONSULTATION ON TURKEY",
     "url": "https://x/2", "alinti": "MSCI announced a consultation on Turkey."},
    {"pub_key": "k3", "tarih": "2026-08-01", "baslik": "ESKI TURKEY DUYURU", "url": "https://x/3", "alinti": None},
    {"pub_key": "k4", "tarih": "bozuk", "baslik": "X", "url": "", "alinti": None},
    {"pub_key": "k5", "tarih": "2026-10-25", "baslik": "GELECEK TARIHLI", "url": "", "alinti": None},
]
o = pr.otomatik_rejimler(dz, "Ana Sayfa", bugun=bugun)
ok(len(o) == 1 and o[0]["id"] == "msci-duyuru-k2", f"yalniz yeni+kapsanmamis: {[x['id'] for x in o]}")
ok(o[0]["rozet"] == "MSCI DUYURUSU" and "20" in o[0]["baslik"], "rozet/baslik")
ok("MSCI announced a consultation on Turkey." in o[0]["ozet"], "alinti AYNEN ozette")
ok(o[0]["kaynaklar"][0][1] == "https://x/2", "kaynak MSCI baglantisi")
ok(pr.otomatik_rejimler(dz, "Döviz", bugun=bugun) == [], "kapsam disi sayfa")
ok(pr.otomatik_rejimler(None, "BIST", bugun=bugun) == [] and pr.otomatik_rejimler([], "BIST") == [], "bos girdi")
ok("MSCI IMPLEMENTS A FREEZE ON THE MSCI TURKEY INDEXES".upper() in
   {t.upper() for r_ in pr.REJIMLER for t in r_.get("kapsadigi_duyurular", ())}, "elle ozetlenen duyuru kapsanmis")

# --- baglantilar ---
db_src = open("db.py", encoding="utf-8").read()
ok(db_src.count('"msci_duyuru"') >= 2, "msci_duyuru RLS + grant listelerinde")
ok("CREATE TABLE IF NOT EXISTS msci_duyuru" in db_src, "tablo init_db'de")
yml = open(".github/workflows/msci_izleme.yml", encoding="utf-8").read()
ok("python -u msci_izleme.py" in yml and "ubuntu-26.04" in yml and "SUPABASE_DB_URL_SESSION" in yml, "workflow")
ok("cron:" in yml and "workflow_dispatch" in yml and "kuru" in yml, "workflow tetikleyiciler")
app = open("app.py", encoding="utf-8").read()
ok("_msci_duyurulari_yukle" in app and "otomatik_rejimler" in app, "app.py baglantisi")

# --- app yardimcisi gercekten cizer (AppTest) ---
agac = ast.parse(app)
fn = next(n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name == "_piyasa_rejimi_goster")
fn_src = ast.get_source_segment(app, fn)
from streamlit.testing.v1 import AppTest
sahte = ("def _msci_duyurulari_yukle():\n    return [{'pub_key': 'k2', 'tarih': %r, 'baslik': 'MSCI LAUNCHES A CONSULTATION ON TURKEY', "
         "'url': 'https://www.msci.com/x', 'alinti': 'MSCI announced a consultation on Turkey.'}]\n"
         % (date.today() - timedelta(days=1)).isoformat())
at = AppTest.from_string("import streamlit as st\n" + sahte + fn_src + "\n_piyasa_rejimi_goster('Ana Sayfa')\n_piyasa_rejimi_goster('Döviz')\n")
at.run(timeout=30)
ok(not at.exception, f"hata olmamali: {at.exception}")
govde = " ".join(x.value for x in at.markdown)
ok("PİYASA REJİMİ" in govde and "MSCI DUYURUSU" in govde, "elle + otomatik serit birlikte cizilmeli")
ok(govde.count("MSCI DUYURUSU") == 1 and govde.count("PİYASA REJİMİ") == 1, "Doviz'de cizilmemeli")
ok(len(at.expander) == 2, "iki ayrinti kutusu")
# otomatik kaynak hatasi curated seridi bozmamali
at2 = AppTest.from_string("import streamlit as st\ndef _msci_duyurulari_yukle():\n    raise RuntimeError('db yok')\n"
                          + fn_src + "\n_piyasa_rejimi_goster('Ana Sayfa')\n")
at2.run(timeout=30)
ok(not at2.exception and "PİYASA REJİMİ" in " ".join(x.value for x in at2.markdown), "otomatik kaynak patlarsa elle serit yine cizilir")

print(f"{_n['ok']} kontrol gecti")
print("TUM TESTLER GECTI")
