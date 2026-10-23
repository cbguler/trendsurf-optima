# -*- coding: utf-8 -*-
"""
v2.0.7.432 - BIST fiyat/hacim GECMISI icin TEK kaynak katmani (radar + gece worker'i).

KARAR KAYDI (Bahri, 23 Ekim 2026 - "birincil kaynak o muydu bu muydu tartismasi bitsin"):
  Kaynak onceligi, KONUYA GORE, kalici olarak:
    1) KAP            : temel analiz (F/K, PD/DD, bilanco), olay bilgisi (sermaye artirimi, tahta
                        kapatma/acma, SPK tedbiri, temettu, pay adedi). KAP gunluk fiyat/hacim
                        serisi YAYIMLAMAZ; fiyat icin kullanilamaz.
    2) borsapy        : BIST fiyat/hacim GECMISI (RSI, Ret1M, volatilite, MaxDD, trend, hacim trendi).
                        Sermaye islemleri (bedelli/bedelsiz/bolunme) icin DUZELTILMIS seri verir.
    3) Yahoo (yfinance): yalnizca YEDEK. borsapy'de o hisse icin veri yoksa/hata/zaman asimi varsa.
  Gerekce (23 Ekim 2026 olcumu, 631 BIST hissesi): borsapy 632/632 hissede veri verdi (8 paralel is
  parcacigi, ~80 sn); son kapanislar Yahoo ile uyumlu; hak kullanim gunu sahte cokusleri yok
  (KRTEK MaxDD Yahoo -%79,8 / borsapy -%33,5; CVKMD -%70,6 / -%31,0). Yahoo bedelli artirimlari
  duzeltmiyor ve hacim/kapali hisse bilgisi guvenilmez.
  TEMETTU KARARI: seri FIYAT GETIRISI esaslidir (temettu duzeltmesi YOK). borsapy temettuyu duzeltmez;
  Yahoo yedegi de bu yuzden auto_adjust=False (yalniz bolunme-duzeltmeli) cekilir -> iki kaynak AYNI
  anlamda. Temettu zaten skorun ayri bilesenidir (DY, KAP kaynakli); getiriye ayrica katmak ayni
  etkiyi IKI KEZ saymak olurdu. Ekranda gorunen fiyat/getiri de ham fiyat getirisidir.
  Bu uc madde yeniden tartisilmaz; degisiklik ancak olculmus bir hata bulgusuyla yapilir.

Her hisse icin TEK kaynaktan tam seri doner (kaynaklar bir seri icinde KARISTIRILMAZ).
"""
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as _FutTimeout

import numpy as np
import pandas as pd

import islem_gormuyor as _ig

MAKS_ISCI = 8
TOPLAM_ZAMAN_ASIMI = 240       # sn: tum borsapy cekimi icin ust sinir (olcum: 632 hisse ~80 sn)
PENCERE_AY = 3                 # Yahoo "3mo" ile ayni takvim penceresi
MIN_BAR = 22                   # Ret1M icin gerekli


class Veri:
    """Bir hissenin gecmisi. df: Close/Volume kolonlu, tz-suz gun indeksli (pencereye kirpilmis) ya da None.
    kaynak: 'borsapy' | 'yahoo' | None. son_bar: kaynaktaki SON bar tarihi (pencere disi olsa da). islem_yok_gun:
    hissede ardisik islem yapilmayan is gunu sayisi (bilinmiyorsa None)."""
    __slots__ = ("df", "kaynak", "son_bar", "islem_yok_gun")

    def __init__(self, df=None, kaynak=None, son_bar=None, islem_yok_gun=None):
        self.df, self.kaynak, self.son_bar, self.islem_yok_gun = df, kaynak, son_bar, islem_yok_gun


def _bugun():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date()


def _normalize(h):
    """borsapy/yfinance DataFrame -> Close/Volume, tz-suz normalize gun indeksi, artan, NaN kapanissiz. Yoksa None."""
    if h is None or not hasattr(h, "columns") or len(h) == 0 or "Close" not in h.columns:
        return None
    d = pd.DataFrame({"Close": pd.to_numeric(h["Close"], errors="coerce"),
                      "Volume": pd.to_numeric(h["Volume"], errors="coerce") if "Volume" in h.columns else np.nan})
    ix = pd.to_datetime(d.index)
    if getattr(ix, "tz", None) is not None:
        ix = ix.tz_localize(None)
    d.index = ix.normalize()
    d = d[~d.index.duplicated(keep="last")].sort_index()
    d = d.dropna(subset=["Close"])
    return d if len(d) else None


def _kirp(d, bugun):
    esik = pd.Timestamp(bugun) - pd.DateOffset(months=PENCERE_AY)
    return d[d.index >= esik]


def _is_gunu_farki(son_bar, bugun) -> int:
    return int(np.busday_count(son_bar, bugun))


def _borsapy_tek(t):
    import borsapy as bp
    return t, bp.Ticker(t).history(period="3mo", interval="1d")


def _borsapy_toplu(tickers, bugun, log=print):
    """{ticker: Veri} yalnizca borsapy'den veri GELEN hisseler icin. borsapy yoksa/zaman asimi -> eksik hisseler
    sonuca konmaz (cagiran Yahoo'ya duser)."""
    out = {}
    try:
        import borsapy  # noqa: F401
    except Exception as e:
        log(f"[fiyat-kaynagi] borsapy yok, tum hisseler Yahoo'ya dusuyor: {type(e).__name__}")
        return out
    ex = ThreadPoolExecutor(max_workers=MAKS_ISCI)
    try:
        fs = {ex.submit(_borsapy_tek, t): t for t in tickers}
        try:
            for f in as_completed(fs, timeout=TOPLAM_ZAMAN_ASIMI):
                try:
                    t, h = f.result()
                    d = _normalize(h)
                    if d is None:
                        continue
                    son = d.index[-1].date()
                    pen = _kirp(d, bugun)
                    out[t] = Veri(pen if len(pen) else None, "borsapy", son, None)
                    gap = _is_gunu_farki(son, bugun)
                    sifir = _ig.sifir_hacim_gun(pen["Close"], pen["Volume"]) if len(pen) else 0
                    out[t].islem_yok_gun = max(gap, sifir)
                except Exception:
                    continue
        except _FutTimeout:
            log(f"[fiyat-kaynagi] borsapy toplu cekim {TOPLAM_ZAMAN_ASIMI} sn'de bitmedi; "
                f"gelmeyen hisseler Yahoo'ya dusuyor ({len(out)}/{len(tickers)} geldi).")
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    return out


def _yahoo_toplu(tickers, bugun, log=print):
    out = {}
    if not tickers:
        return out
    try:
        import yfinance as yf
    except Exception as e:
        log(f"[fiyat-kaynagi] KRITIK: yfinance da import edilemedi: {type(e).__name__}: {str(e)[:150]}")
        return out
    for i in range(0, len(tickers), 200):
        parca = tickers[i:i + 200]
        syms = [f"{t}.IS" for t in parca]
        try:
            # auto_adjust=False: bolunme-duzeltmeli ama TEMETTU duzeltmesiz = borsapy ile ayni anlam (bkz. karar kaydi)
            raw = yf.download(syms, period="3mo", progress=False, auto_adjust=False, group_by="ticker")
        except Exception as e:
            log(f"[fiyat-kaynagi] Yahoo parti {i // 200 + 1} hatasi: {type(e).__name__}: {str(e)[:150]}")
            continue
        for t, sym in zip(parca, syms):
            try:
                if len(syms) == 1:
                    sub = raw
                else:
                    sub = raw[sym] if sym in raw.columns.get_level_values(0) else None
                d = _normalize(sub)
                if d is None:
                    continue
                pen = _kirp(d, bugun)
                v = Veri(pen if len(pen) else None, "yahoo", d.index[-1].date(), None)
                v.islem_yok_gun = _ig.sifir_hacim_gun(pen["Close"], pen["Volume"]) if len(pen) else None
                out[t] = v
            except Exception:
                continue
    return out


def bist_gecmis(tickers, bugun=None, log=print) -> dict:
    """{ticker: Veri}. Once borsapy, gelmeyen/bos hisseler icin Yahoo. Hicbirinde yoksa Veri() (kaynak None)."""
    bugun = bugun or _bugun()
    tickers = list(dict.fromkeys(tickers))
    sonuc = _borsapy_toplu(tickers, bugun, log)
    eksik = [t for t in tickers if t not in sonuc]
    if eksik:
        y = _yahoo_toplu(eksik, bugun, log)
        sonuc.update(y)
    nb = sum(1 for v in sonuc.values() if v.kaynak == "borsapy")
    ny = sum(1 for v in sonuc.values() if v.kaynak == "yahoo")
    log(f"[fiyat-kaynagi] BIST gecmisi: {nb} borsapy, {ny} Yahoo (yedek), "
        f"{len(tickers) - nb - ny} hicbirinde yok.")
    for t in tickers:
        sonuc.setdefault(t, Veri())
    return sonuc


# v2.0.7.433: borsapy `history(period=...)` TAKVIM penceresi DEGIL, BAR SAYISI uygular (olculdu, 23 Ekim 2026):
# "1mo"=30 bar, "3mo"=90, "6mo"=180, "1y"=365, "5y"=1825. THYAO "1y" -> 528 takvim gunu (17 ay), "5y" -> 7,3 yil;
# seyrek islem goren ISATR "3mo" -> 2021-03-17..2025-09-26 (4,5 yil, son islem 26.9.2025). Uygulama detay sayfasi bu
# serileri "3 Ay"/"1 Yil" diye gosteriyordu. Bu yardimci seriyi gercek takvim penceresine kirpar.
DONEM_AY = {"1mo": 1, "3mo": 3, "6mo": 6, "1y": 12, "2y": 24, "3y": 36, "5y": 60}


def donem_kirp(df, period, bugun=None):
    """df'i `period` takvim penceresine (bugunden geriye) kirpar. Bilinmeyen/`max` donem -> df aynen.
    Indeks tz'li ya da tz'siz olabilir (orijinal indeks korunur)."""
    ay = DONEM_AY.get(str(period))
    if ay is None or df is None or len(df) == 0:
        return df
    esik = pd.Timestamp(bugun or _bugun()) - pd.DateOffset(months=ay)
    ix = pd.to_datetime(df.index)
    if getattr(ix, "tz", None) is not None:
        ix = ix.tz_localize(None)
    return df[ix.normalize() >= esik]
