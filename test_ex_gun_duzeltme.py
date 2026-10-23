"""v2.0.7.430: sermaye artirimi hak kullanim (ex) gunu boslugu duzeltmesi testleri (agsiz, veritabansiz).
Calistir: python test_ex_gun_duzeltme.py"""
import datetime
import sys
import types
import warnings

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

import ex_gun_duzeltme as X
import kap_risk

_n = {"ok": 0}


def ok(kosul, mesaj):
    if not kosul:
        print("BASARISIZ:", mesaj)
        sys.exit(1)
    _n["ok"] += 1


def yakin(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol


def seri(degerler, bitis=datetime.date(2026, 10, 20)):
    """Is gunu (takvim gunu degil) indeksli kapanis serisi: son deger `bitis`te."""
    gunler = pd.bdate_range(end=pd.Timestamp(bitis), periods=len(degerler))
    return pd.Series(list(map(float, degerler)), index=gunler)


def bld(gun, ozet, kodlar=("AAA",), konu=None):
    return {"id": 1, "tarih": datetime.datetime.combine(gun, datetime.time(10, 0)),
            "konu": konu or kap_risk.K_SERMAYE[0], "ozet": ozet,
            "gonderen_kodlar": list(kodlar), "ilgili_kodlar": [], "metin": ""}


BUGUN = datetime.date(2026, 10, 20)

# --- surec_haritasi: yalniz artirim bildirimleri, azaltim ve baska konu haric ---
b = [bld(BUGUN - datetime.timedelta(days=10), "Bedelli Sermaye Artırımı", ("AAA",)),
     bld(BUGUN - datetime.timedelta(days=11), "Bedelsiz Sermaye Artırımı", ("BBB",)),
     bld(BUGUN - datetime.timedelta(days=12), "Sermaye Azaltımı", ("CCC",)),
     bld(BUGUN - datetime.timedelta(days=13), "Bedelli Sermaye Artırımı", ("DDD",), konu="Genel Kurul"),
     bld(BUGUN - datetime.timedelta(days=14), "Sermaye Artırımı Tescili", ("EEE",))]
h = X.surec_haritasi(b)
ok(set(h) == {"AAA", "BBB", "EEE"}, f"surec haritasi: bedelli+bedelsiz+belirsiz tur, azaltim ve baska konu haric ({sorted(h)})")
ok(X.surec_haritasi(None) == {} and X.surec_haritasi([]) == {}, "bos girdi -> bos sozluk")
ok(X.surec_haritasi([{"konu": kap_risk.K_SERMAYE[0]}]) == {}, "tarihsiz bildirim yoksayilir")

# --- duzelt: temel senaryo (hak kullanim gunu -50%, KAP sureci var) ---
duz = [20.0] * 30 + [10.0] * 3
s = seri(duz)
bt = [BUGUN - datetime.timedelta(days=20)]
y, l = X.duzelt(s, bt)
ok(len(l) == 1 and yakin(l[0][1], 0.5), f"tek bosluk bulundu, oran 0.5 ({l})")
ok(yakin(y.iloc[-1], 10.0), "son fiyat DEGISMEZ")
ok(yakin(y.iloc[0], 10.0) and yakin(y.max(), 10.0), "gecmis seri gozlenen orana gore geriye cekildi (hepsi 10)")
ok(abs(((y / y.cummax()) - 1).min()) < 1e-9, "duzeltmeden sonra MaxDD sifir")
ok(yakin(s.iloc[0], 20.0), "girdi serisi yerinde DEGISTIRILMEZ")

# --- duzelt: surec yoksa / cok eskiyse / dususten >3 gun sonra ise dokunma ---
y, l = X.duzelt(s, [])
ok(l == [] and y is s, "bildirim yok: seri aynen (ayni nesne)")
y, l = X.duzelt(s, None)
ok(l == [], "bildirim None: seri aynen")
gap_gunu = s.index[30].date()
y, l = X.duzelt(s, [gap_gunu - datetime.timedelta(days=X.ARSIV_GUN + 5)])
ok(l == [], "bildirim arsiv penceresinden eski: duzeltme yok")
y, l = X.duzelt(s, [gap_gunu + datetime.timedelta(days=X.SONRA_GUN + 2)])
ok(l == [], "bildirim dususten cok sonra: duzeltme yok")
y, l = X.duzelt(s, [gap_gunu + datetime.timedelta(days=X.SONRA_GUN)])
ok(len(l) == 1, "bildirim dususten 3 gun sonra: kabul")
y, l = X.duzelt(s, [gap_gunu])
ok(len(l) == 1, "bildirim dusus gunu: kabul")

# --- esik: kucuk dusus (gercek piyasa hareketi) dokunulmaz ---
kucuk = seri([20.0] * 30 + [18.0] * 3)      # -%10 (limit dusus) -> duzeltme yok
y, l = X.duzelt(kucuk, bt)
ok(l == [] and yakin(y.iloc[0], 20.0), "-%10 dusus (esik alti): duzeltme yok, KAP sureci olsa bile")
sinir = seri([20.0] * 30 + [17.6] * 3)      # -%12 tam esik: dahil degil (r > 1-esik)
y, l = X.duzelt(sinir, bt)
ok(l == [], "tam esik (-%12) altinda sayilmaz")
iki = seri([20.0] * 30 + [17.0] * 3)        # -%15 -> duzeltilir
y, l = X.duzelt(iki, bt)
ok(len(l) == 1 and yakin(y.iloc[0], 17.0), "-%15 dusus + surec: duzeltilir")

# --- yukselis boslugu (ters bolunme vb.) dokunulmaz ---
yuk = seri([10.0] * 30 + [20.0] * 3)
y, l = X.duzelt(yuk, bt)
ok(l == [], "yukari bosluk duzeltilmez")

# --- iki ayri ex gunu (bedelsiz sonra bedelli): carpanlar birikir ---
ik = seri([40.0] * 20 + [20.0] * 20 + [15.0] * 10)
y, l = X.duzelt(ik, [BUGUN - datetime.timedelta(days=50)])
ok(len(l) == 2, f"iki bosluk bulundu ({l})")
ok(yakin(y.iloc[0], 15.0) and yakin(y.iloc[-1], 15.0) and yakin(y.iloc[25], 15.0), "iki oran birikerek uygulandi")

# --- bozuk veri: sifir/NaN/kisa seri guvenli ---
ok(X.duzelt(seri([1.0, 2.0]), bt)[1] == [], "cok kisa seri: dokunma")
sf = seri([20.0] * 10 + [0.0] + [10.0] * 5)
y, l = X.duzelt(sf, bt)
ok(isinstance(y, pd.Series), "sifir fiyat patlatmaz")
ok(X.duzelt(None, bt) == (None, []), "None seri guvenli")

# --- uygula: surecler None/bos ise seri AYNEN ---
ok(X.uygula("AAA", s, None) is s, "surecler None: ayni nesne")
ok(X.uygula("AAA", s, {}) is s, "surecler bos: ayni nesne")
ok(X.uygula("ZZZ", s, {"AAA": bt}) is s, "baska hissenin sureci: dokunma")
ok(yakin(X.uygula("aaa", s, {"AAA": bt}).iloc[0], 10.0), "ticker buyuk/kucuk harf duyarsiz")

# --- radar entegrasyonu: sahte yfinance ile tara_bist ---
fake = types.ModuleType("yfinance")


def _indir(syms, **kw):
    n = 70
    gunler = pd.bdate_range(end=pd.Timestamp(BUGUN), periods=n)
    cerceveler = {}
    for sym in syms:
        if sym == "AAA.IS":      # hak kullanim gunu: son 3 gunden once -%60 bosluk
            kap = [20.0] * (n - 5) + [8.0] * 5
        else:                    # sakin hisse
            kap = [20.0] * n
        cerceveler[sym] = pd.DataFrame({"Close": kap, "Volume": [1e6] * n}, index=gunler)
    return pd.concat(cerceveler, axis=1)


fake.download = _indir
sys.modules["yfinance"] = fake
import firsat_radari as fr

t0 = fr.tara_bist(["AAA", "BBB"], {})
t1 = fr.tara_bist(["AAA", "BBB"], {}, {"AAA": [BUGUN - datetime.timedelta(days=30)]})
ok(t0["AAA"]["ret1m"] < -50, f"duzeltmesiz: sahte cokus Ret1M ({t0['AAA']['ret1m']})")
ok(abs(t1["AAA"]["ret1m"]) < 1e-6, f"duzeltmeli: Ret1M ~0 ({t1['AAA']['ret1m']})")
ok(t1["AAA"]["skor"] > t0["AAA"]["skor"], f"duzeltme skoru yukseltir ({t0['AAA']['skor']} -> {t1['AAA']['skor']})")
ok(yakin(t1["AAA"]["fiyat"], 8.0), "radar fiyati degismez")
ok(t1["BBB"] == t0["BBB"], "surec olmayan hisse etkilenmez")

# --- gece worker entegrasyonu ---
import worker as wk
w0 = wk.batch_bist(["AAA", "BBB"])
w1 = wk.batch_bist(["AAA", "BBB"], {"AAA": [BUGUN - datetime.timedelta(days=30)]})
ok(w0["AAA"]["ret1m"] < -50 and abs(w1["AAA"]["ret1m"]) < 1e-6, f"worker Ret1M duzeltmesi ({w0['AAA']['ret1m']} -> {w1['AAA']['ret1m']})")
ok(w1["AAA"]["dd_adj"] == 0 and w0["AAA"]["dd_adj"] == -3, f"worker MaxDD cezasi kalkti ({w0['AAA']['dd_adj']} -> {w1['AAA']['dd_adj']})")
ok(w1["BBB"] == w0["BBB"], "worker: surec olmayan hisse etkilenmez")
ok(abs(t1["AAA"]["ret1m"] - w1["AAA"]["ret1m"]) < 1e-6, "radar ve worker AYNI Ret1M")

print(f"TUM TESTLER GECTI ({_n['ok']} kontrol)")
