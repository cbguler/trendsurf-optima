"""
tefas_client.py v7 — pytefas tabanlı TEFAS Veri Modülü
=======================================================
Kaynak: pytefas (pip install pytefas)
Endpoint: https://www.tefas.gov.tr/api/funds/fonGnlBlgSiraliGetir
YAT + EMK + BYF — tüm fon tipleri destekleniyor.
Gerçek günlük NAV fiyatları, 1 yıla kadar geçmiş.
"""

import glob
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict

TEFAS_FILE_KIND = {
    "Borsa_Yatirim": "BYF",
    "Emeklilik":     "EMK",
    "Menkul_Kiymet": "YAT",
}

_EXCEL_CACHE: Optional[pd.DataFrame] = None
_EXCEL_PATH: str = ""
_PYTEFAS_OK: Optional[bool] = None   # None=henüz test edilmedi


def _find_excel_dir() -> str:
    candidates = [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    for d in candidates:
        if glob.glob(os.path.join(d, "*Yatirim_Fonlari*.xlsx")):
            return d
    return os.getcwd()


def _check_pytefas() -> bool:
    """pytefas'ın çalışıp çalışmadığını test eder."""
    global _PYTEFAS_OK
    if _PYTEFAS_OK is not None:
        return _PYTEFAS_OK
    try:
        from pytefas import Crawler
        c = Crawler()
        today = datetime.now()
        start = (today - timedelta(days=3)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        df = c.fetch(start=start, end=end, kind="YAT", fund_code="AAL")
        _PYTEFAS_OK = not df.empty
        if _PYTEFAS_OK:
            print("  [pytefas] TEFAS API erisilebilir — gercek veriler kullanilacak.")
        else:
            print("  [pytefas] Bos yanit — Excel fallback aktif.")
    except Exception as e:
        print(f"  [pytefas] Erisim hatasi ({e}) — Excel fallback aktif.")
        _PYTEFAS_OK = False
    return _PYTEFAS_OK


# ── RSI yardımcısı ──────────────────────────────────────────
def _calc_rsi(prices: pd.Series, period: int = 14) -> float:
    p = prices.dropna()
    if len(p) < period + 1:
        return 50.0
    d = p.diff()
    g = d.where(d > 0, 0.0).rolling(period).mean()
    l = (-d.where(d < 0, 0.0)).rolling(period).mean()
    ll = l.iloc[-1]
    if ll == 0:
        return 100.0
    return round(100 - (100 / (1 + g.iloc[-1] / ll)), 1)


def _rsi_from_rets(ret1m, ret3m, ret1y) -> float:
    """v2.0.7.78 - DUZELTME (Bahri'nin bulgusu, DTH ornegi): eskiden
    eksik donem (None/NaN yerine 0.0 varsayilan) agirlikli ortalamaya
    SIFIR getiri olarak giriyordu - bu, henuz 1 yillik (ya da 3 aylik)
    gecmisi olmayan ama gercekte yukselmis bir fonun RSI'sini yapay
    olarak asagi cekiyordu (DTH: gercek RSI ~61 yerine 59 cikiyordu).
    Artik eksik donemler agirlikli ortalamadan TAMAMEN CIKARILIR, kalan
    donemlerin agirliklari kendi aralarinda yeniden olceklenir. Hicbir
    donem yoksa (cok nadir) notr RSI=50.0 donulur."""
    bilesenler = [(ret1m, 0.5), (ret3m, 0.3), (ret1y, 0.2)]
    gecerli = [(v, w) for v, w in bilesenler if v is not None]
    if not gecerli:
        return 50.0
    toplam_agirlik = sum(w for _, w in gecerli)
    momentum = sum(v * w for v, w in gecerli) / toplam_agirlik
    return round(max(15.0, min(85.0, 50.0 + (momentum / 30.0) * 20.0)), 1)


# ── BEFAS günlük fiyat dosyası ───────────────────────────────
def _load_befas_prices(excel_dir: str = "") -> dict:
    if not excel_dir:
        excel_dir = _find_excel_dir()
    files = sorted(glob.glob(os.path.join(excel_dir,
                                          "Fon_Verileri_EXCEL_*.xlsx")), reverse=True)
    if not files:
        return {}
    try:
        df = pd.read_excel(files[0], header=4)
        df.columns = (["Fon_Kodu","Fon_Adi","Tarih","Fiyat"]
                      + list(df.columns[4:]))
        df = df.dropna(subset=["Fon_Kodu"])
        df["Fon_Kodu"] = df["Fon_Kodu"].astype(str).str.strip().str.upper()
        df["Fiyat"] = pd.to_numeric(df["Fiyat"], errors="coerce").fillna(0.0)
        prices = df[df["Fiyat"] > 0].set_index("Fon_Kodu")["Fiyat"].to_dict()
        print(f"  [BEFAS] {os.path.basename(files[0])}: {len(prices)} fon fiyati yuklendi.")
        return prices
    except Exception as e:
        print(f"  [BEFAS] Okuma hatasi: {e}")
        return {}


# ── Excel'den fon listesi ────────────────────────────────────
def load_excel_all(excel_dir: str = "") -> pd.DataFrame:
    global _EXCEL_CACHE, _EXCEL_PATH
    if not excel_dir:
        excel_dir = _find_excel_dir()
    if _EXCEL_CACHE is not None and _EXCEL_PATH == excel_dir:
        return _EXCEL_CACHE

    rows = []
    for fpath in sorted(glob.glob(os.path.join(excel_dir, "*.xlsx"))):
        fname = os.path.basename(fpath)
        if "KAP" in fname.upper() or "Fon_Verileri" in fname:
            continue
        kind = "YAT"
        for key, val in TEFAS_FILE_KIND.items():
            if key in fname:
                kind = val
                break
        try:
            df = pd.read_excel(fpath, header=4)
        except Exception as e:
            print(f"  [Excel] {fname} okunamadi: {e}")
            continue
        df.columns = [str(c).strip() for c in df.columns]
        if "Fon Kodu" not in df.columns:
            continue
        col_risk = next((c for c in df.columns if "Risk" in c), None)
        col_tur  = next((c for c in df.columns if "Semsiye" in c
                         or "Şemsiye" in c), None)
        for _, row in df.iterrows():
            kod = str(row.get("Fon Kodu","")).strip().upper()
            if not kod or kod == "NAN" or len(kod) > 8:
                continue
            def _pct(col_name):
                v = row.get(col_name)
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    # v2.0.7.78 - DUZELTME (Bahri'nin bulgusu, DTH ornegi:
                    # 6 Ay/1 Yil "%0,00" gosteriyordu ama fon o donemde
                    # acikca yukselmisti). Eskiden burada 0.0 donuyordu -
                    # "veri yok" (fon o kadar eski degil / Excel'de bos)
                    # ile "gercekten %0 getiri" ayirt edilemiyordu. Artik
                    # None doner - asagida RSI hesabinda eksik donem
                    # agirlikli ortalamadan CIKARILIR (sifir sayilmaz),
                    # ekranda da bos gosterilir (fmt_tr None/NaN icin
                    # bos metin donduruyor, v2.0.7.76).
                    return None
                v = float(v)
                return round(v * 100, 4) if abs(v) <= 2.0 else round(v, 4)
            ret1m_raw = _pct("1 Ay (%)")
            ret3m_raw = _pct("3 Ay (%)")
            ret6m_raw = _pct("6 Ay (%)")
            ret1y_raw = _pct("1 Yıl (%)")
            ret3y_raw = _pct("3 Yıl (%)")
            ret5y_raw = _pct("5 Yıl (%)")
            # Ret1M sadece optima_score()'un dogrudan girdisi oldugu icin
            # (RSI/Ret3M/Ret6M/Ret1Y/Ret3Y/Ret5Y'nin aksine) NaN kabul
            # etmez - eksikse 0.0'a duser (cok nadir: ~1348 fonun 12'si).
            ret1m = ret1m_raw if ret1m_raw is not None else 0.0
            risk_v = (int(float(row.get(col_risk,4) or 4))
                      if col_risk and pd.notna(row.get(col_risk,4)) else 4)
            # Risk degerinden yillik volatilite tahmini (TEFAS resmi risk skalasi 1-7)
            RISK_TO_VOL = {1: 3.0, 2: 7.0, 3: 12.0, 4: 18.0,
                           5: 25.0, 6: 33.0, 7: 42.0}
            rows.append({
                "Ticker":     kod,
                "Ad":         str(row.get("Fon Adı", kod)).strip()[:80],
                "Kategori":   "TEFAS",
                "TEFAS_Kind": kind,
                "Tur":        str(row.get(col_tur,"")) if col_tur else "",
                "Risk_Deger": risk_v,
                "Son_Fiyat":  0.0,
                "RSI":        _rsi_from_rets(ret1m_raw, ret3m_raw, ret1y_raw),
                "Ret1M":  ret1m,
                "Ret3M":  ret3m_raw,
                "Ret6M":  ret6m_raw,
                "Ret1Y":  ret1y_raw,
                "Ret3Y":  ret3y_raw,
                "Ret5Y":  ret5y_raw,
                "Vol":    RISK_TO_VOL.get(risk_v, 18.0),
                "YF_Symbol": "",
            })
    if not rows:
        _EXCEL_CACHE = pd.DataFrame()
        return _EXCEL_CACHE

    df_out = (pd.DataFrame(rows)
              .drop_duplicates(subset=["Ticker"], keep="last")
              .reset_index(drop=True))

    # BEFAS fiyatları eşleştir
    befas = _load_befas_prices(excel_dir)
    if befas:
        df_out["Son_Fiyat"] = df_out["Ticker"].map(befas).fillna(0.0)
        print(f"  [BEFAS] {(df_out['Son_Fiyat']>0).sum()}/{len(df_out)} fona gercek fiyat eslesti.")

    _EXCEL_CACHE = df_out
    _EXCEL_PATH  = excel_dir
    print(f"  [TEFAS Excel] {len(df_out)} fon: "
          f"BYF={len(df_out[df_out.TEFAS_Kind=='BYF'])} "
          f"EMK={len(df_out[df_out.TEFAS_Kind=='EMK'])} "
          f"YAT={len(df_out[df_out.TEFAS_Kind=='YAT'])}")
    return df_out


# ── Geçmiş fiyat serisi ──────────────────────────────────────
def fetch_fund_history(ticker: str, kind: str, period: str = "1y",
                       excel_dir: str = "") -> pd.DataFrame:
    """
    Fon için günlük geçmiş NAV serisi.
    1. pytefas ile gerçek API (çalışıyorsa)
    2. Excel getiri + BEFAS baz fiyat → sentetik seri (fallback)
    """
    # pytefas dene
    if _check_pytefas():
        try:
            hist = _fetch_via_pytefas(ticker, kind, period)
            if hist is not None and not hist.empty and len(hist) >= 5:
                return hist
        except Exception as e:
            print(f"  [pytefas] {ticker} hata: {e}")

    # Fallback: Excel sentetik seri
    return _synthetic_from_excel(ticker, period, excel_dir)


def _fetch_via_pytefas(ticker: str, kind: str,
                       period: str = "1y") -> pd.DataFrame:
    """pytefas ile gerçek günlük NAV verisi."""
    from pytefas import Crawler
    period_days = {"1mo": 35, "3mo": 95, "6mo": 190,
                   "1y": 370, "3y": 1100, "5y": 1830}
    days = period_days.get(period, 370)
    today = datetime.now()
    start = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    end   = today.strftime("%Y-%m-%d")

    c = Crawler()
    # Önce belirtilen kind ile dene, başarısız olursa diğerlerini dene
    for try_kind in [kind] + [k for k in ["YAT","EMK","BYF"] if k != kind]:
        try:
            df = c.fetch(start=start, end=end,
                         kind=try_kind, fund_code=ticker)
            if df.empty:
                continue
            # Sütun isimlerini normalize et
            col_map = {}
            for c_name in df.columns:
                cl = c_name.lower()
                if "price" in cl or "fiyat" in cl:
                    col_map[c_name] = "Close"
                elif "date" in cl or "tarih" in cl:
                    col_map[c_name] = "date"
            df = df.rename(columns=col_map)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).set_index("date").sort_index()
            if "Close" not in df.columns:
                continue
            df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
            df = df.dropna(subset=["Close"])
            if len(df) < 2:
                continue
            df["Open"]  = df["Close"].shift(1).fillna(df["Close"])
            df["High"]  = df[["Open","Close"]].max(axis=1)
            df["Low"]   = df[["Open","Close"]].min(axis=1)
            return df[["Open","High","Low","Close"]]
        except Exception as e:
            continue
    return pd.DataFrame()


def _synthetic_from_excel(ticker: str, period: str = "1y",
                           excel_dir: str = "") -> pd.DataFrame:
    """Excel getiri verilerinden sentetik günlük seri üretir."""
    df_all = load_excel_all(excel_dir)
    if df_all.empty:
        return pd.DataFrame()
    match = df_all[df_all["Ticker"] == ticker.upper()]
    if match.empty:
        return pd.DataFrame()
    row = match.iloc[0]
    base = float(row.get("Son_Fiyat", 0) or 0)
    return _synthetic_price_series(
        ret1m=float(row.get("Ret1M",0) or 0),
        ret3m=float(row.get("Ret3M",0) or 0),
        ret6m=float(row.get("Ret6M",0) or 0),
        ret1y=float(row.get("Ret1Y",0) or 0),
        ret3y=float(row.get("Ret3Y",0) or 0),
        ret5y=float(row.get("Ret5Y",0) or 0),
        period=period, base_price=base,
    )


def _synthetic_price_series(
        ret1m, ret3m, ret6m, ret1y, ret3y, ret5y,
        period="1y", base_price=0.0) -> pd.DataFrame:
    today = datetime.now().replace(day=1)
    base  = base_price if base_price > 0 else 100.0
    raw_points: Dict[int, float] = {0: base}
    for ret, months in [(ret1m,1),(ret3m,3),(ret6m,6),
                        (ret1y,12),(ret3y,36),(ret5y,60)]:
        if ret != 0.0:
            raw_points[months] = round(base / (1 + ret / 100.0), 4)

    period_days = {"1mo":35,"3mo":95,"6mo":190,"1y":370,"3y":1100,"5y":1830}
    max_m = min(max(raw_points.keys()), period_days.get(period,370)//30)
    if max_m == 0:
        return pd.DataFrame()

    sorted_pts = sorted(raw_points.items())
    dated = [(today - timedelta(days=30*m), p) for m, p in sorted_pts
             if m <= max_m]
    dated.sort(key=lambda x: x[0])

    rows = []
    for i in range(len(dated)-1):
        dt_a, p_a = dated[i]
        dt_b, p_b = dated[i+1]
        n = max(1, (dt_b-dt_a).days)
        for d_off in range(n):
            dt = dt_a + timedelta(days=d_off)
            if dt.weekday() >= 5:
                continue
            t = d_off / n
            price = round(p_a + t*(p_b-p_a), 4)
            noise = price * 0.003
            rows.append({"date":dt,"Open":round(price-noise*.5,4),
                         "High":round(price+noise,4),
                         "Low":round(price-noise,4),"Close":price})
    if dated:
        lp = base
        noise = lp * 0.003
        rows.append({"date":dated[-1][0],"Open":round(lp-noise*.5,4),
                     "High":round(lp+noise,4),"Low":round(lp-noise,4),
                     "Close":lp})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("date").set_index("date")
    df.index = pd.DatetimeIndex(df.index)
    return df[~df.index.duplicated(keep="last")]


# ── Uyumluluk fonksiyonları ──────────────────────────────────
def fetch_all_current_prices(fund_list: list, **kw) -> dict:
    """
    pytefas ile tüm fonlar için güncel NAV fiyatı.
    YAT + EMK + BYF tek seferde çeker.
    """
    if not _check_pytefas():
        return {}
    try:
        from pytefas import Crawler
        today = datetime.now()
        # TEFAS 1 ay sınırı var, 3 günlük pencere yeterli
        start = (today - timedelta(days=4)).strftime("%Y-%m-%d")
        end   = today.strftime("%Y-%m-%d")
        c = Crawler()
        prices = {}
        for kind in ["YAT", "EMK", "BYF"]:
            try:
                print(f"  [pytefas] {kind} fiyatlari cekiliyor...")
                df = c.fetch(start=start, end=end, kind=kind)
                if df.empty:
                    print(f"  [pytefas] {kind}: bos dondu")
                    continue
                # Sütun isimlerini bul
                col_price = next((c2 for c2 in df.columns
                                  if c2.lower() in ("price","fiyat")), None)
                col_code  = next((c2 for c2 in df.columns
                                  if c2.lower() in ("fund_code","fonkodu","code","kod")), None)
                col_date  = next((c2 for c2 in df.columns
                                  if c2.lower() in ("date","tarih")), None)
                if not col_price or not col_code:
                    # Kolon adlarını göster
                    print(f"  [pytefas] {kind} kolon adlari: {list(df.columns)}")
                    continue
                # Her fon için en son tarihli satırı al
                if col_date:
                    df["_dt"] = pd.to_datetime(df[col_date], errors="coerce")
                    latest = (df.sort_values("_dt")
                                .groupby(col_code, as_index=False)
                                .last())
                else:
                    latest = df.groupby(col_code, as_index=False).last()

                for _, row in latest.iterrows():
                    kod = str(row[col_code]).strip().upper()
                    p   = float(row.get(col_price, 0) or 0)
                    if p > 0:
                        prices[kod] = p

                print(f"  [pytefas] {kind}: {len([k for k in prices])} fon fiyati (kumulatif)")
            except Exception as e:
                print(f"  [pytefas {kind}] hata: {e}")

        print(f"  [pytefas] Toplam {len(prices)} fon fiyati alindi.")
        return prices
    except Exception as e:
        print(f"  [pytefas] fetch_all_current_prices hatasi: {e}")
        return {}


def fetch_bulk_metrics(fund_list: list, top_n: int = 500,
                       excel_dir: str = "") -> dict:
    df_all = load_excel_all(excel_dir)
    if df_all.empty:
        return {}
    results = {}
    for row in df_all.head(top_n).itertuples():
        results[row.Ticker] = {
            "rsi":   float(row.RSI),
            "ret1m": float(row.Ret1M),
            "ret3m": float(row.Ret3M),
            "ret1y": float(row.Ret1Y),
        }
    return results


def calc_tefas_metrics(ticker: str, kind: str, **kw) -> dict:
    df_all = load_excel_all()
    match = df_all[df_all["Ticker"] == ticker.upper()]
    if match.empty:
        return {"rsi":50.0,"ret1m":0.0,"ret3m":0.0,"ret1y":0.0,"last_price":0.0}
    row = match.iloc[0]
    return {"rsi":float(row.RSI),"ret1m":float(row.Ret1M),
            "ret3m":float(row.Ret3M),"ret1y":float(row.Ret1Y),
            "last_price":float(row.Son_Fiyat)}
