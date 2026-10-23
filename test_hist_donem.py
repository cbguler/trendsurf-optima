# -*- coding: utf-8 -*-
"""v2.0.7.433: app._get_hist_cached BIST dali - borsapy period (bar sayisi) -> takvim penceresine kirpma.
app.py import edilmez (Streamlit sayfasi calisir); fonksiyon AST ile cikarilip sahte borsapy ile calistirilir.
Calistir: python test_hist_donem.py"""
import ast
import datetime
import sys
import types

import numpy as np
import pandas as pd

_n = {"ok": 0}


def ok(k, m):
    if not k:
        print("BASARISIZ:", m)
        sys.exit(1)
    _n["ok"] += 1


src = open("app.py", encoding="utf-8").read()
tree = ast.parse(src)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_get_hist_cached")
fn.decorator_list = []
mod = ast.Module(body=[fn], type_ignores=[])
ns = {"pd": pd}


class _HistEmptyError(Exception):
    pass


ns["_HistEmptyError"] = _HistEmptyError
exec(compile(mod, "app_fn", "exec"), ns)
f = ns["_get_hist_cached"]


def bars(n, son):
    ix = pd.bdate_range(end=pd.Timestamp(son), periods=n)
    ix = (ix + pd.Timedelta(hours=9)).tz_localize("Europe/Istanbul")
    c = np.linspace(10, 12, n)
    return pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c, "Volume": 1e6}, index=ix)


BUGUN = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date()
VERI = {"AKT": bars(1825, BUGUN), "STALE": bars(90, datetime.date(2025, 9, 26))}
ADET = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "5y": 1825}
yahoo_cagri = []


class _Tk:
    def __init__(self, t):
        self.t = t

    def history(self, period=None, interval=None):
        return VERI[self.t].tail(ADET.get(period, 90))


bp = types.ModuleType("borsapy")
bp.Ticker = _Tk
sys.modules["borsapy"] = bp
yfm = types.ModuleType("yfinance")


class _YT:
    def __init__(self, s):
        yahoo_cagri.append(s)

    def history(self, **kw):
        return pd.DataFrame()


yfm.Ticker = _YT
sys.modules["yfinance"] = yfm
dp = types.ModuleType("data_pipeline")
dp._format_yf_symbol = lambda t, c: t + ".IS"
sys.modules["data_pipeline"] = dp

for per, ay in (("1mo", 1), ("3mo", 3), ("6mo", 6), ("1y", 12), ("5y", 60)):
    h = f("AKT", "", "BIST", per)
    ilk = h.index[0].tz_localize(None).normalize() if h.index.tz is not None else h.index[0]
    ok(ilk >= pd.Timestamp(BUGUN) - pd.DateOffset(months=ay), f"{per}: pencere disina tasan bar yok ({ilk.date()})")
    ok(len(h) < ADET[per], f"{per}: bar sayisi {len(h)} < borsapy ham {ADET[per]}")
    ok(len(h) >= 5, f"{per}: yeterli bar")

try:
    f("STALE", "", "BIST", "3mo")
    ok(False, "bayat hisse: hata beklenirdi")
except _HistEmptyError:
    ok(True, "")
ok(yahoo_cagri == [], f"bayat hisse icin Yahoo'ya dusulmedi ({yahoo_cagri})")
print(f"TUM TESTLER GECTI ({_n['ok']} kontrol)")
