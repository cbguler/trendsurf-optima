"""v2.0.7.389 - Degerli Madenler icin KENDI TL fiyat arsivimiz.

Neden var (Bahri, 10 Ekim 2026): maden gecmisi (RSI / Ret1M / Optima Skor / grafik) tek bir kaynaktan
(canlidoviz, borsapy uzerinden) geliyordu; o kaynak 502 verince liste 17'den 12'ye dustu, skorlar 0 oldu.
Dayaniklilik icin her gece Truncgil'in TL satis fiyati bu dosyaya yazilir; canlidoviz erisilemezse
teknik gostergeler BU arsivden hesaplanir. Capraz fiyat YOK: arsivdeki her deger Truncgil'in dogrudan
verdigi TL fiyattir (USD x kur donusumu yapilmaz; '$' ile baslayan alan reddedilir).

Kurallar (PROJE_NOTLARI):
- Kapsam yalniz canlidoviz gecmisi olan 8 varlik. Truncgil'in diger 9 turu (ayar/bilezik/has vb.) 18 Temmuz
  2026 kararina gore YALNIZ fiyat gosterir; bu arsive girmez, teknik gosterge uretilmez.
- Iki kaynak ASLA birlestirilmez (canlidoviz serisi + arsiv serisi tek seride dikilmez). Ya biri ya digeri.
- Yeterli veri yoksa uydurma yok: ozet() None doner -> arayuzde "veri yok".

Bu modul Streamlit'e bagimli degildir (worker.py ve uygulama ikisi de kullanir).
"""
import datetime as _dt
import json
import os

import pandas as pd

ARSIV_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maden_tl_gecmis.json")
TRUNCGIL_URL = "https://finans.truncgil.com/v3/today.json"

# bizim ticker -> Truncgil anahtari. Yalniz canlidoviz gecmisi olan 8 varlik.
ARSIV_KEYLERI = {
    "ALTIN_TRY":        "gram-altin",
    "GUMUS_TRY":        "gumus",
    "PLATIN_TRY":       "gram-platin",
    "CEYREK_ALTIN":     "ceyrek-altin",
    "YARIM_ALTIN":      "yarim-altin",
    "TAM_ALTIN":        "tam-altin",
    "CUMHURIYET_ALTIN": "cumhuriyet-altini",   # Truncgil'deki gercek anahtar sonda 'i' ile
    "ATA_ALTIN":        "ata-altin",
}

MAKS_GUN = 1900          # dosya sismesin; ~5 yil
SON_FIYAT_MAKS_YAS_GUN = 3   # arsivin son noktasi bundan eskiyse fiyat olarak kullanilmaz
RSI_PERIYOT = 14
RET_1M_GUN = 30          # 1 aylik getiri referansi (takvim gunu)
RET_1M_TOLERANS_GUN = 5  # referans noktasi 30 gun oncesinden en fazla bu kadar sapabilir
MIN_NOKTA = 22           # ozet icin gereken en az arsiv noktasi


def _tr_float(s) -> float:
    """'6.281,55' -> 6281.55 ; '$' ile baslayan (USD) deger 0.0 doner (reddedilir)."""
    if not isinstance(s, str):
        return 0.0
    s = s.strip()
    if not s or s.startswith("$"):
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", "."))
    except Exception:
        return 0.0


def truncgil_fiyatlari(data: dict) -> dict:
    """today.json sozlugunden {ticker: TL satis fiyati} (yalniz arsiv kapsamindaki 8 varlik)."""
    out = {}
    if not isinstance(data, dict):
        return out
    for ticker, key in ARSIV_KEYLERI.items():
        d = data.get(key)
        if isinstance(d, dict):
            p = _tr_float(d.get("Selling"))
            if p > 0:
                out[ticker] = round(p, 4)
    return out


def cek_truncgil(timeout: int = 10) -> dict:
    """Truncgil'den bugunku TL fiyatlari. Basarisizsa {} (arsive sifir nokta eklenir, uydurma yok)."""
    try:
        import requests
        r = requests.get(TRUNCGIL_URL, timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0 (TrendSurfOptima maden arsivi)"})
        if r.status_code != 200:
            return {}
        return truncgil_fiyatlari(r.json())
    except Exception as e:
        print(f"  [maden_arsiv] Truncgil cekimi basarisiz: {type(e).__name__}: {e}")
        return {}


def bugun_trt() -> str:
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d")
    except Exception:
        return (_dt.datetime.utcnow() + _dt.timedelta(hours=3)).strftime("%Y-%m-%d")


def bos_arsiv() -> dict:
    return {"surum": 1,
            "kaynak": "Truncgil today.json - Selling (TL), gece worker kaydi; capraz fiyat yok",
            "seriler": {t: {} for t in ARSIV_KEYLERI}}


def yukle(yol: str = None) -> dict:
    yol = yol or ARSIV_DOSYASI
    try:
        with open(yol, encoding="utf-8") as f:
            a = json.load(f)
        if not isinstance(a, dict) or not isinstance(a.get("seriler"), dict):
            return bos_arsiv()
        for t in ARSIV_KEYLERI:
            a["seriler"].setdefault(t, {})
        return a
    except Exception:
        return bos_arsiv()


def kaydet(arsiv: dict, yol: str = None) -> None:
    yol = yol or ARSIV_DOSYASI
    tmp = yol + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(arsiv, f, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, yol)


def nokta_ekle(arsiv: dict, fiyatlar: dict, tarih: str) -> dict:
    """Saf: ayni tarih tekrar eklenirse uzerine yazar (idempotent). Yalniz fiyat>0 olanlar eklenir."""
    for t, p in (fiyatlar or {}).items():
        if t not in ARSIV_KEYLERI:
            continue
        try:
            p = float(p)
        except Exception:
            continue
        if p > 0:
            arsiv["seriler"].setdefault(t, {})[tarih] = round(p, 4)
    for t, s in arsiv["seriler"].items():
        if len(s) > MAKS_GUN:
            for k in sorted(s)[: len(s) - MAKS_GUN]:
                del s[k]
    return arsiv


def gece_guncelle(yol: str = None, fiyatlar: dict = None, tarih: str = None) -> dict:
    """worker.py cagirir: bugunun fiyatini arsive ekler. Eklenen {ticker: fiyat} doner."""
    fiyatlar = cek_truncgil() if fiyatlar is None else fiyatlar
    if not fiyatlar:
        print("  [maden_arsiv] Bugun Truncgil fiyati alinamadi - arsive nokta EKLENMEDI.")
        return {}
    a = yukle(yol)
    nokta_ekle(a, fiyatlar, tarih or bugun_trt())
    kaydet(a, yol)
    print(f"  [maden_arsiv] {len(fiyatlar)} varlik arsive yazildi ({tarih or bugun_trt()}).")
    return fiyatlar


def seri(arsiv: dict, ticker: str) -> pd.Series:
    """Tarih indeksli kapanis (Truncgil Selling) serisi; yoksa bos."""
    s = (arsiv or {}).get("seriler", {}).get(ticker, {})
    if not s:
        return pd.Series(dtype=float)
    out = pd.Series({pd.Timestamp(k): float(v) for k, v in s.items()}).sort_index()
    return out[out > 0]


# ---- teknik ozet: RSI ve DD duzeltmesi live_data ile birebir (test_maden_arsiv dogrular); Ret1M takvim gunu
# (30 gun) bazli, volatilite arsivin takvim-gunu ornekleme sikligina gore yillandirilir ----
def _rsi(closes: pd.Series, period: int = RSI_PERIYOT) -> float:
    if closes is None or len(closes) < period + 1:
        return 50.0
    delta = closes.diff().dropna()
    gain = delta.clip(lower=0).rolling(window=period, min_periods=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period, min_periods=period).mean()
    if loss.iloc[-1] == 0:
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return 50.0 if pd.isna(rsi) else float(round(rsi, 1))


def _ret_1m(closes: pd.Series):
    """Son noktadan ~30 takvim gunu once (+-5) en yakin noktaya gore % getiri; yoksa None."""
    son_t = closes.index[-1]
    hedef = son_t - pd.Timedelta(days=RET_1M_GUN)
    aday = closes[(closes.index >= hedef - pd.Timedelta(days=RET_1M_TOLERANS_GUN))
                  & (closes.index <= hedef + pd.Timedelta(days=RET_1M_TOLERANS_GUN))]
    if aday.empty:
        return None
    ref = float(aday.iloc[(abs((aday.index - hedef).days)).argmin()])
    son = float(closes.iloc[-1])
    if ref <= 0:
        return None
    return float(round((son - ref) / ref * 100.0, 4))


def _vol_yillik(closes: pd.Series) -> float:
    """Noktalar takvim gunu araliklidir: getiriyi arada gecen gun sayisinin karekokune bol, 365 ile yillandir."""
    if len(closes) < 11:
        return 25.0
    r = closes.pct_change().dropna()
    gun = pd.Series(closes.index, index=closes.index).diff().dt.days.reindex(r.index).clip(lower=1)
    norm = r / (gun ** 0.5)
    return round(float(norm.std() * (365 ** 0.5) * 100), 1)


def _dd_duzeltmesi(closes: pd.Series) -> int:
    """live_data._hacim_dd_duzeltmesi_maden'in DD kismi (hacim verisi yok -> hacim duzeltmesi 0)."""
    if closes is None or len(closes) < 20:
        return 0
    win = closes.tail(252) if len(closes) >= 252 else closes
    max_dd = float(((win - win.cummax()) / win.cummax() * 100).min())
    if max_dd < -70:
        return -7
    if max_dd < -50:
        return -3
    return 0


def ozet(closes: pd.Series):
    """Arsiv serisinden (son, rsi, ret1m, vol, skor, n) ; yeterli veri yoksa None (uydurma yok).

    Gereken: en az MIN_NOKTA nokta VE ~30 gun oncesine ait bir nokta (yani arsiv ~1 ay birikmis olmali).
    """
    try:
        if closes is None:
            return None
        closes = pd.to_numeric(closes, errors="coerce").dropna()
        closes = closes[closes > 0].sort_index()
        if len(closes) < MIN_NOKTA:
            return None
        ret = _ret_1m(closes)
        if ret is None:
            return None
        from scoring import optima_score
        rsi = _rsi(closes)
        vol = _vol_yillik(closes)
        taban = optima_score(rsi, ret, vol=vol, has_fundamental=False)
        skor = max(0.0, min(100.0, round(taban + _dd_duzeltmesi(closes), 1)))
        return {"son": float(closes.iloc[-1]), "rsi": rsi, "ret1m": ret, "vol": vol,
                "skor": skor, "n": int(len(closes)), "son_tarih": closes.index[-1].strftime("%Y-%m-%d")}
    except Exception as e:
        print(f"  [maden_arsiv] ozet hatasi: {type(e).__name__}: {e}")
        return None


def son_fiyat(arsiv: dict, ticker: str, bugun: str = None):
    """Arsivdeki son fiyat (tarih, fiyat); cok eskiyse None. Teknik veri gerektirmez (yalniz fiyat)."""
    s = seri(arsiv, ticker)
    if s.empty:
        return None
    bugun_ts = pd.Timestamp(bugun or bugun_trt())
    if (bugun_ts - s.index[-1]).days > SON_FIYAT_MAKS_YAS_GUN:
        return None
    return (s.index[-1].strftime("%Y-%m-%d"), float(s.iloc[-1]))
