# -*- coding: utf-8 -*-
"""v2.0.7.432: fiyat_kaynagi (borsapy birincil, Yahoo yedek) testleri. Ag KULLANILMAZ (sahte borsapy/yfinance).
Calistir: python test_fiyat_kaynagi.py"""
import datetime
import sys
import types
import warnings

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

_n = {"ok": 0}


def ok(k, m):
    if not k:
        print("BASARISIZ:", m)
        sys.exit(1)
    _n["ok"] += 1


BUGUN = datetime.date(2026, 10, 23)
CAGRI = {"yahoo": [], "bp": []}


def bp_df(n, fiyat=10.0, son=BUGUN, hacim=1e6, tz=True):
    ix = pd.bdate_range(end=pd.Timestamp(son), periods=n)
    if tz:
        ix = (ix + pd.Timedelta(hours=9)).tz_localize("Europe/Istanbul")
    return pd.DataFrame({"Open": fiyat, "High": fiyat, "Low": fiyat, "Close": np.linspace(fiyat, fiyat * 1.1, n),
                         "Volume": hacim}, index=ix)


BP = {
    "AKT": bp_df(90),                                     # aktif, 90 bar (pencereden uzun)
    "UMP": bp_df(30, 9.3, son=datetime.date(2024, 9, 30), hacim=5e4),   # 2024'te biten gecmis (kapali)
    "BOS": pd.DataFrame(),                                # borsapy bos doner -> Yahoo
    "KISA": bp_df(5),                                     # cok kisa (yeni hisse) -> borsapy yine kullanilir
}
HATA = {"PATLAK"}


class _Tk:
    def __init__(self, t):
        self.t = t

    def history(self, period=None, interval=None):
        CAGRI["bp"].append(self.t)
        if self.t in HATA:
            raise RuntimeError("baglanti")
        return BP.get(self.t, pd.DataFrame())


bpmod = types.ModuleType("borsapy")
bpmod.Ticker = _Tk
sys.modules["borsapy"] = bpmod


def _indir(syms, **kw):
    CAGRI["yahoo"].append((list(syms), kw))
    n = 67
    ix = pd.bdate_range(end=pd.Timestamp(BUGUN), periods=n)
    fr = {s: pd.DataFrame({"Close": np.linspace(5, 6, n), "Volume": [2e6] * n}, index=ix) for s in syms
          if s not in ("YOKYAHOO.IS",)}
    if len(syms) == 1:
        return next(iter(fr.values())) if fr else pd.DataFrame()
    return pd.concat(fr, axis=1) if fr else pd.DataFrame()


yf = types.ModuleType("yfinance")
yf.download = _indir
sys.modules["yfinance"] = yf
import fiyat_kaynagi as FK

logs = []
r = FK.bist_gecmis(["AKT", "UMP", "BOS", "KISA", "PATLAK", "YOKYAHOO"], bugun=BUGUN, log=lambda m: logs.append(m))
ok(r["AKT"].kaynak == "borsapy", "aktif hisse borsapy'den")
ok(r["AKT"].df.index.tz is None, "indeks tz-suz")
ok(r["AKT"].df.index[0] >= pd.Timestamp(BUGUN) - pd.DateOffset(months=3), "pencere 3 takvim ayina kirpildi")
ok(len(r["AKT"].df) < 90 and len(r["AKT"].df) >= 60, f"90 bar -> ~3 ay ({len(r['AKT'].df)})")
ok(r["AKT"].islem_yok_gun == 0, "aktif hisse islem_yok_gun 0")
ok(r["UMP"].kaynak == "borsapy" and r["UMP"].df is None, "kapali hisse: borsapy'de pencerede bar yok -> df None (Yahoo'ya DUSMEZ)")
ok(r["UMP"].islem_yok_gun > 500 and r["UMP"].son_bar == datetime.date(2024, 9, 30), "kapali hisse islem_yok_gun buyuk, son bar tarihi")
ok("UMP.IS" not in [s for c in CAGRI["yahoo"] for s in c[0]], "kapali hisse icin Yahoo'ya gidilmedi")
ok(r["BOS"].kaynak == "yahoo" and r["BOS"].df is not None, "borsapy bos -> Yahoo yedek")
ok(r["PATLAK"].kaynak == "yahoo", "borsapy hata -> Yahoo yedek")
ok(r["KISA"].kaynak == "borsapy" and len(r["KISA"].df) == 5, "kisa gecmis borsapy'de kalir (radar kapisi 22 bar kuralini uygular)")
ok(r["YOKYAHOO"].kaynak is None and r["YOKYAHOO"].df is None and r["YOKYAHOO"].islem_yok_gun is None, "hicbirinde yok: bos Veri")
yahoo_kw = CAGRI["yahoo"][0][1]
ok(yahoo_kw.get("auto_adjust") is False, "Yahoo yedegi temettu DUZELTMESIZ (auto_adjust=False) - karar kaydi")
ok(CAGRI["yahoo"][0][0] == ["BOS.IS", "PATLAK.IS", "YOKYAHOO.IS"], f"Yahoo'ya yalniz eksikler gitti ({CAGRI['yahoo'][0][0]})")
ok(any("2 Yahoo" in m or "Yahoo (yedek)" in m for m in logs), "kaynak ozeti loglandi")

# borsapy hic yoksa -> hepsi Yahoo
sys.modules["borsapy"] = None
import importlib
importlib.reload(FK)
r2 = FK.bist_gecmis(["AKT", "BOS"], bugun=BUGUN, log=lambda m: None)
ok(r2["AKT"].kaynak == "yahoo" and r2["BOS"].kaynak == "yahoo", "borsapy import edilemez: tum hisseler Yahoo")
ok(r2["AKT"].islem_yok_gun == 0, "Yahoo yolunda islem_yok_gun hacim sayacindan (aktif: 0)")

# Yahoo hacim 0 + fiyat sabit
def _indir0(syms, **kw):
    n = 67
    ix = pd.bdate_range(end=pd.Timestamp(BUGUN), periods=n)
    return pd.DataFrame({"Close": [9.3] * n, "Volume": [0.0] * n}, index=ix)


yf.download = _indir0
r3 = FK.bist_gecmis(["DON"], bugun=BUGUN, log=lambda m: None)
ok(r3["DON"].kaynak == "yahoo" and r3["DON"].islem_yok_gun == 67, f"Yahoo yolu: hacim 0 + sabit fiyat 67 seans ({r3['DON'].islem_yok_gun})")
print(f"TUM TESTLER GECTI ({_n['ok']} kontrol)")
