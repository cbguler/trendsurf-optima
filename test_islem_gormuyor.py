# -*- coding: utf-8 -*-
"""v2.0.7.431: fiilen islem gormeyen hisse (hacim 0 + fiyat sabit) tespiti, uyari katmani, worker kablolamasi ve
KAP 'Kapatilmasi ve Acilmasi' siniflandirmasi. Ag/veritabani KULLANILMAZ. Calistir: python test_islem_gormuyor.py"""
import datetime as dt
import sys
import types
import warnings

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

import islem_gormuyor as IG
import kap_risk as K
import uyari_katmani as U

_n = {"ok": 0}


def ok(kosul, mesaj):
    if not kosul:
        print("BASARISIZ:", mesaj)
        sys.exit(1)
    _n["ok"] += 1


def seri(c, v):
    ix = pd.bdate_range(end="2026-10-23", periods=len(c))
    return pd.Series(c, index=ix, dtype=float), pd.Series(v, index=ix, dtype=float)


# --- sifir_hacim_gun ---
c, v = seri([9.3] * 30, [0] * 30)
ok(IG.sifir_hacim_gun(c, v) == 30, "tum seri hacim 0 + fiyat sabit: 30")
c, v = seri([9.3] * 30, [5e6] * 20 + [0] * 10)
ok(IG.sifir_hacim_gun(c, v) == 10, "son 10 seans hacim 0: 10")
c, v = seri([9.3] * 30, [5e6] * 29 + [0])
ok(IG.sifir_hacim_gun(c, v) == 1, "yalniz son seans 0: 1")
c, v = seri([9.3] * 30, [0] * 29 + [5e6])
ok(IG.sifir_hacim_gun(c, v) == 0, "son seans islem gordu: 0 (sayac sifirlanir)")
c, v = seri([9.0] * 20 + [9.3] * 10, [0] * 30)
ok(IG.sifir_hacim_gun(c, v) == 10, "fiyat degisen bolum sayilmaz (son fiyatla ayni olanlar): 10")
c, v = seri([9.3] * 30, [0] * 20 + [np.nan] * 5 + [0] * 5)
ok(IG.sifir_hacim_gun(c, v) == 5, "NaN hacim sayaci keser (eksik veri alarm uretmez): 5")
c, v = seri([9.3] * 30, [np.nan] * 30)
ok(IG.sifir_hacim_gun(c, v) == 0, "tum hacim NaN: 0")
ok(IG.sifir_hacim_gun(None, None) == 0 and IG.sifir_hacim_gun(pd.Series(dtype=float), pd.Series(dtype=float)) == 0, "bos/None guvenli")
c, v = seri([9.3] * 5, [0] * 5)
c.iloc[2] = np.nan
ok(IG.sifir_hacim_gun(c, v) == 4, "NaN kapanis dusurulur, kalan 4 seans sayilir")

# --- isaretli_mi ---
ok(IG.isaretli_mi(10) and IG.isaretli_mi("66") and IG.isaretli_mi(66.0), "esik ve ustu isaretli")
ok(not IG.isaretli_mi(9) and not IG.isaretli_mi(None) and not IG.isaretli_mi(float("nan")) and not IG.isaretli_mi("abc"), "esik alti/bos/bozuk isaretsiz")
ok("66" in IG.aciklama(66.0) and "0'a sabit" in IG.aciklama(66), "aciklama sayi ve skor 0 icerir")

# --- uyari katmani ---
import db


def df0():
    sat = lambda t, kat, skor, g: {"Ticker": t, "Ad": t, "Kategori": kat, "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0,
                                   "Vol": 30.0, "Optima_Skor": skor, "Gecmis_Gun": 900.0, "Islem_Yok_Gun": g}
    return pd.DataFrame([sat("UMPAS", "BIST", 33.0, 66.0), sat("NORM", "BIST", 80.0, 0.0), sat("BOS", "BIST", 80.0, None),
                         sat("ESIK", "BIST", 80.0, 10.0), sat("ALT", "BIST", 80.0, 9.0),
                         sat("KRIPT", "KRIPTO", 70.0, 66.0), sat("KAPA", "BIST", 80.0, 66.0)])


orj = (getattr(db, "get_aktif_piyasa_tedbirleri", None), getattr(db, "get_aktif_kap_riskleri", None))
db.get_aktif_piyasa_tedbirleri = lambda: [{"eslesme_turu": "TICKER", "deger": "KAPA", "tedbir_turu": "MANIPULASYON_SUPHESI"}]
db.get_aktif_kap_riskleri = lambda: {}
try:
    d = U.uyari_katmanini_uygula(df0()).set_index("Ticker")
finally:
    db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj
ok(d.loc["UMPAS", "Piyasa_Tedbiri"] == "İŞLEME KAPALI" and d.loc["UMPAS", "Optima_Skor"] == 0.0, "UMPAS: ISLEME KAPALI, skor 0")
ok("66" in d.loc["UMPAS", "Tedbir_Aciklama"], "UMPAS aciklamasinda gun sayisi")
ok(d.loc["NORM", "Piyasa_Tedbiri"] == "" and d.loc["NORM", "Optima_Skor"] == 80.0, "islem goren hisse etkilenmez")
ok(d.loc["BOS", "Piyasa_Tedbiri"] == "" and d.loc["BOS", "Optima_Skor"] == 80.0, "bilinmeyen (bos) etkilenmez")
ok(d.loc["ESIK", "Piyasa_Tedbiri"] != "" and d.loc["ALT", "Piyasa_Tedbiri"] == "", "esik: 10 isaretli, 9 degil")
ok(d.loc["KRIPT", "Piyasa_Tedbiri"] == "", "yalniz BIST kategorisi")
ok(d.loc["KAPA", "Piyasa_Tedbiri"] != "İŞLEME KAPALI" and d.loc["KAPA", "Optima_Skor"] == 0.0, "mevcut SPK tedbiri korunur (ustune yazilmaz)")
ok("Islem_Yok_Gun" in d.columns, "kolon korunur")
# kolon yoksa eski davranis
d2 = df0().drop(columns=["Islem_Yok_Gun"])
db.get_aktif_piyasa_tedbirleri = lambda: []
db.get_aktif_kap_riskleri = lambda: {}
try:
    d2 = U.uyari_katmanini_uygula(d2).set_index("Ticker")
finally:
    db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj
ok((d2["Piyasa_Tedbiri"] == "").all(), "Islem_Yok_Gun kolonu yoksa hicbir sey degismez")

# --- KAP: kapatma/acma siniflandirmasi ---
def sira(ozet):
    b = {"id": 1, "tarih": dt.datetime(2026, 10, 5, 9), "konu": K.K_SIRA, "ozet": ozet,
         "gonderen_kodlar": [], "ilgili_kodlar": ["XXXX"], "metin": ""}
    return [x[1] for x in K.siniflandir(b)]


ok(sira("Pay Sırasının İşleme Kapatılması") == ["SIRA_KAPALI"], "kapatilmasi -> KAPALI")
ok(sira("Pay Sıralarının İşleme Kapatılması") == ["SIRA_KAPALI"], "cogul kapatilmasi -> KAPALI")
ok(sira("Pay Sırasının Geçici Olarak İşleme Kapatılması") == ["SIRA_KAPALI"], "gecici kapatma -> KAPALI")
ok(sira("Pay Sırasının İşleme Açılması") == ["SIRA_ACIK"], "acilmasi -> ACIK")
ok(sira("Pay Sırasının İşleme Kapatılması ve Açılması") == ["SIRA_ACIK"], "kapatilmasi VE acilmasi -> ACIK (eskiden KAPALI sayiliyordu)")
ok(sira("Pay Sırasının İşleme Açılması ve Kapatılması") == ["SIRA_KAPALI"], "once acilma sonra kapatma -> KAPALI")
ok(sira("Baska bir sey") == [], "ilgisiz ozet: kural yok")

# --- worker.batch_bist kablolama (sahte yfinance) ---
fake = types.ModuleType("yfinance")


def _indir(syms, **kw):
    n = 70
    ix = pd.bdate_range(end=pd.Timestamp("2026-10-23"), periods=n)
    fr = {}
    for sym in syms:
        if sym == "UMP.IS":
            fr[sym] = pd.DataFrame({"Close": [9.3] * n, "Volume": [0.0] * n}, index=ix)
        else:
            fr[sym] = pd.DataFrame({"Close": list(np.linspace(10, 12, n)), "Volume": [1e6] * n}, index=ix)
    return pd.concat(fr, axis=1)


fake.download = _indir
sys.modules["yfinance"] = fake
sys.modules["borsapy"] = None      # v2.0.7.432: agsiz test - borsapy import edilemez -> Yahoo yedek yolu
import worker as wk

r = wk.batch_bist(["UMP", "AKT"])
ok(r["UMP"]["islem_yok_gun"] == 67, f"worker: kapali hisse 67 seans (3 ay penceresi) ({r['UMP'].get('islem_yok_gun')})")
ok(r["AKT"]["islem_yok_gun"] == 0, "worker: aktif hisse 0")
# --- v2.0.7.434: ayni sirketin islem goren kodu aciklamaya eklenir (ISATR/ISCTR) ---
import json
import os
import tempfile

PAY = {"ISATR": {"ISATR": 1000.0, "ISBTR": 29000.0, "ISCTR": 24999970000.0, "ISKUR": 2458.0},
       "KRDMA": {"KRDMA": 100.0, "KRDMD": 300.0}}
a = IG.aciklama(280, "ISATR", PAY, {"ISCTR", "ISBTR"})
ok("ISCTR (24.999.970.000 pay)" in a and "ISBTR (" not in a, "islem goren en buyuk kardes kod (ISCTR) secilir")
ok("1.000 adettir (%0,000004)" in a and "25.000.002.458" in a, "kendi pay adedi, toplam ve yuzde dogru")
ok("mali durumu hakkında değil" in a and "Optima Skor 0'a sabit" in a, "banka sagligi aciklamasi + eski metin korunur")
b = IG.aciklama(280, "ISATR", PAY, set())
ok("pay kodu:" not in b and "mali durumu hakkında değil" in b, "olcumle dogrulanan islem goren kardes yoksa kod ADI VERILMEZ")
ok(IG.aciklama(66, "UMPAS", PAY, {"ISCTR"}) == IG.aciklama(66), "tek kodlu sirket: metin degismez")
ok(IG.aciklama(66, "UMPAS") == IG.aciklama(66), "paylar verilmezse eski metin")
ok(IG.aciklama(66, "UMPAS", None, None) == IG.aciklama(66), "paylar None guvenli")
ok(IG.kardes_notu("ISATR", {"ISATR": {"ISATR": 1.0}}, {"X"}) == "", "tek elemanli grup: not yok")
ok(IG.kardes_notu("XXX", PAY, {"ISCTR"}) == "", "tabloda olmayan kod: not yok")
ok(IG.kardes_notu("ISATR", {"ISATR": {"ISATR": 0.0, "ISCTR": 0.0}}, {"ISCTR"}) == "", "toplam 0: patlamaz, not yok")
ok(IG._tr_yuzde(0.5) == "%50" and IG._tr_yuzde(0.0123) == "%1,2" and IG._tr_yuzde(0.2111) == "%21,1", "yuzde bicimi")

with tempfile.TemporaryDirectory() as td:
    yol = os.path.join(td, "o.json")
    ok(IG.paylar_yukle(yol) == {}, "dosya yok -> bos")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"veri": {"ISATR": {"paylar": {"isatr": 1000, "ISCTR": 5000}}, "TEK": {"paylar": {"TEK": 5}}, "BOZ": None}}, f)
    pp = IG.paylar_yukle(yol)
    ok(set(pp) == {"ISATR"} and pp["ISATR"] == {"ISATR": 1000.0, "ISCTR": 5000.0}, "yalniz cok kodlu sirketler, kodlar buyuk harf")
    with open(yol, "w") as f:
        f.write("{bozuk")
    os.utime(yol, (1, 1))
    ok(IG.paylar_yukle(yol) == {}, "bozuk dosya -> bos")
gercek = IG.paylar_yukle()
ok({"ISATR", "ISCTR", "KRDMA"} <= set(gercek), "depodaki gercek KAP onbellegi okunur (ISATR/ISCTR/KRDMA)")

def df1():
    sat = lambda t, g: {"Ticker": t, "Ad": t, "Kategori": "BIST", "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0,
                        "Vol": 30.0, "Optima_Skor": 80.0, "Gecmis_Gun": 900.0, "Islem_Yok_Gun": g}
    return pd.DataFrame([sat("ISATR", 280.0), sat("ISCTR", 0.0), sat("ISBTR", 0.0), sat("ISKUR", 120.0), sat("UMPAS", 66.0)])

db.get_aktif_piyasa_tedbirleri = lambda: []
db.get_aktif_kap_riskleri = lambda: {}
try:
    e = U.uyari_katmanini_uygula(df1()).set_index("Ticker")
finally:
    db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj
ok("ISCTR (" in e.loc["ISATR", "Tedbir_Aciklama"] and "ISKUR (" not in e.loc["ISATR", "Tedbir_Aciklama"],
   "uyari katmani: ISATR aciklamasi ISCTR'yi gosterir, islem gormeyen ISKUR'u degil")
ok("ISCTR" in e.loc["ISKUR", "Tedbir_Aciklama"], "ISKUR icin de ayni not")
ok("pay tablosuna" not in e.loc["UMPAS", "Tedbir_Aciklama"], "tek kodlu UMPAS: ek not yok")
ok(e.loc["ISCTR", "Piyasa_Tedbiri"] == "" and e.loc["ISCTR", "Optima_Skor"] == 80.0, "islem goren ISCTR etkilenmez")
ok(e.loc["ISATR", "Optima_Skor"] == 0.0, "ISATR skoru yine 0")

# --- v2.0.7.435: detay sayfasinda islem gormeyen hissede Yahoo satirlari / teknik gostergeler gizlenir ---
ok(IG.satir_kapali_mi({"Kategori": "BIST", "Islem_Yok_Gun": 280.0}) is True, "kapali BIST satiri")
ok(IG.satir_kapali_mi({"Kategori": "BIST", "Islem_Yok_Gun": 9.0}) is False, "esik alti: gizleme yok")
ok(IG.satir_kapali_mi({"Kategori": "BIST", "Islem_Yok_Gun": None}) is False, "bilinmeyen: gizleme yok")
ok(IG.satir_kapali_mi({"Kategori": "BIST"}) is False, "kolon yok: gizleme yok")
ok(IG.satir_kapali_mi({"Kategori": "KRIPTO", "Islem_Yok_Gun": 99.0}) is False, "yalniz BIST")
ok(IG.satir_kapali_mi(pd.Series({"Kategori": "BIST", "Islem_Yok_Gun": 66.0})) is True, "pandas Series satiri")
ok(IG.satir_kapali_mi(pd.Series({"Kategori": "BIST", "Islem_Yok_Gun": float("nan")})) is False, "NaN: gizleme yok")
ok(IG.satir_kapali_mi(None) is False, "None patlatmaz")
tablo = {"Piyasa Değeri (KAP pay adedi × fiyat)": "319.91 Milyar", "F/K Oranı (KAP, 2025/12 yıllık net kâr)": "4.71",
         "PD/DD Oranı (KAP, 2026/06)": "0.59", "Hisse Başı Kazanç (yfinance)": "0.00", "Ciro (Yıllık, yfinance)": "420 Milyar",
         "Temettü Dağıtım Oranı": "1727.09%", "Beta": "0.16", "52H Yüksek": "4950000", "52H Düşük": "4950000",
         "Sektör": "Financial Services", "Endüstri": "Banks - Regional", "Net Kâr (KAP, 2026/06)": "41.95 Milyar",
         "Ödenmiş Sermaye (KAP, 2026/06)": "25.00 Milyar", "Faaliyet Marjı": "12.96%", "F/K Oranı (iz. 12A, yfinance)": "9"}
sade = IG.yahoo_satirlarini_ayikla(tablo)
ok(list(sade) == ["Piyasa Değeri (KAP pay adedi × fiyat)", "F/K Oranı (KAP, 2025/12 yıllık net kâr)", "PD/DD Oranı (KAP, 2026/06)",
                  "Sektör", "Endüstri", "Net Kâr (KAP, 2026/06)", "Ödenmiş Sermaye (KAP, 2026/06)"],
   f"yalniz KAP etiketli + sektor/endustri, sira korunur ({list(sade)})")
ok(IG.yahoo_satirlarini_ayikla({}) == {} and IG.yahoo_satirlarini_ayikla(None) == {}, "bos girdi guvenli")
ok(len(tablo) == 15, "girdi sozlugu degistirilmez")
ok("Yahoo" in IG.GIZLENDI_NOTU and "KAP" in IG.GIZLENDI_NOTU, "gizleme notu")

# app.py'deki skor bilesimi yardimcisi (AST ile cikarilir) ve uc detay blogunun baglantilari
import ast
_src = open("app.py", encoding="utf-8").read()
_tree = ast.parse(_src)
_fn = [n for n in _tree.body if isinstance(n, ast.FunctionDef) and n.name == "_skor_bilesim_ic_html"]
ok(len(_fn) == 1, "app.py'de _skor_bilesim_ic_html var")
_ns = {"fmt_tr": lambda v, n=1: f"{float(v):.{n}f}".replace(".", ",")}
exec(compile(ast.Module(body=_fn, type_ignores=[]), "app_parca", "exec"), _ns)
_acik = _ns["_skor_bilesim_ic_html"](True, -18.0, 18.0)
ok("0'a sabitlenmiştir" in _acik and "/ 75" not in _acik and "/ 25" not in _acik, "kapali: teknik/temel dokumu yok")
_norm = _ns["_skor_bilesim_ic_html"](False, 42.5, 18.0, "Temettü")
ok("42,5 / 75" in _norm and "18,0 / 25" in _norm and "Temettü" in _norm, "normal hisse: eski dokum aynen")
ok(_src.count("_kapali_mi(") == 6 and _src.count("_yahoo_ayikla(") == 3 and _src.count("_skor_bilesim_ic_html(_kpl_") == 3,
   "uc blokta da (ana, portfoy, kategori) baglanti var")
ok(_src.count("if not _kpl_ana:") == 1 and _src.count("if not _kpl_pf:") == 1 and _src.count("if not _kpl_cat:") == 1,
   "teknik gostergeler kutusu uc blokta da kosullu")

import re as _re
ok(not _re.search(r"^[ \t]*\{_trend_\w+\}[ \t]*$", _src, _re.M),
   "v436: ozet serit sablonunda tek basina {_trend_*} satiri yok (bos satir + girinti markdown'da kod blogu olur)")
ok(len(_re.findall(r"\{_trend_(?:ana|pf|cat)\}Optima Skor:", _src)) == 3, "uc blokta da Optima Skor ayni satirda")
print(f"TUM TESTLER GECTI ({_n['ok']} kontrol)")
