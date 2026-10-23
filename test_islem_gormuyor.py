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
import worker as wk

r = wk.batch_bist(["UMP", "AKT"])
ok(r["UMP"]["islem_yok_gun"] == 70, f"worker: kapali hisse 70 seans ({r['UMP'].get('islem_yok_gun')})")
ok(r["AKT"]["islem_yok_gun"] == 0, "worker: aktif hisse 0")
print(f"TUM TESTLER GECTI ({_n['ok']} kontrol)")
