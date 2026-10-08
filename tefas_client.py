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
                   "1y": 370, "3y": 1100, "5y": 1800}
    # v2.0.7.340 (2 Ekim 2026): app.py'deki _fetch_tefas_hist_cached()'te
    # bulunan AYNI "5y" sinir-asimi hatasi (bkz. o dosyadaki yorum) -
    # tutarlilik icin burada da ayni degere cekildi.
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
            # v2.0.7.335 (2 Ekim 2026, Bahri'nin bulgusu - CVL/BAG gibi
            # fonların Detay grafiginin "imkansız derecede pürüzsüz"
            # göründüğü, gerçek günlük dalgalanma hiç yansımadığı):
            # KESİN KÖK NEDEN BULUNDU - pytefas'ın döndürdüğü yanıtta
            # (YAT/EMK/BYF üçünde de AYNI) "price" sütununun yanı sıra
            # HER ZAMAN None degerli bir "exchange_bulletin_price" sütunu
            # da var. Alt-dize eslestirmesi ("price" in cl) bu ikincisini
            # de yakalayip İKİSİNİ BİRDEN "Close"a esliyordu - rename
            # sonrası df["Close"] bir Series degil bir DataFrame oluyor,
            # pd.to_numeric(df["Close"]) de "TypeError: arg must be a
            # list, tuple, 1-d array, or Series" ile patlıyordu. Bu hata
            # asagidaki except'e dusup SESSIZCE yutuluyordu, ÜÇ fon
            # turunde de (YAT/EMK/BYF) AYNI sekilde tekrarlandigi icin
            # TÜM denemeler basarisiz oluyor, fonksiyon bos DataFrame
            # donup sentetik fallback'e dusuluyordu - CANLI DOGRULANDI.
            # SONUÇ: bu, SADECE CVL/BAG'a ozgu degil, `fetch_fund_history`
            # ile cagrilan TÜM TEFAS fonlarinin Detay grafigini (pytefas
            # gercekten erisilebilir olsa BILE) baştan beri sentetige
            # ZORLUYORDU. ÇÖZÜM: önce TAM esitlik (==) denenir (gercek
            # sütun adlari zaten tam olarak "price"/"date") - sadece hic
            # tam eslesme yoksa, "bulletin" iceren sutunlari HARIC
            # TUTARAK alt-dize aramasina dusulur (gelecekteki olasi
            # varyasyonlara karsi guvenlik agi).
            col_map = {}
            _tam_price = [c for c in df.columns if c.lower() in ("price", "fiyat")]
            _tam_date  = [c for c in df.columns if c.lower() in ("date", "tarih")]
            if _tam_price:
                col_map[_tam_price[0]] = "Close"
            if _tam_date:
                col_map[_tam_date[0]] = "date"
            if not _tam_price or not _tam_date:
                for c_name in df.columns:
                    if c_name in col_map:
                        continue
                    cl = c_name.lower()
                    if not _tam_price and ("price" in cl or "fiyat" in cl) and "bulletin" not in cl:
                        col_map[c_name] = "Close"
                    elif not _tam_date and ("date" in cl or "tarih" in cl):
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


def _optimized_universe_satiri_bul(ticker: str):
    """v2.0.7.319 (16 Eylul 2026, Bahri'nin bulgusu - "birden fazla TEFAS
    fonu ayni gunde birlikte anormal bir dusus gosteriyor"): KOK NEDEN -
    `_synthetic_from_excel` SADECE `load_excel_all()`'un BEFAS-yerel-
    Excel eslesmesine guveniyordu; CVL/HTS/HOY/BAG gibi bazi fonlar o
    yerel Excel'de eslesmiyor, Son_Fiyat SESSIZCE 0.0 kaliyordu -
    `_synthetic_price_series` de fiyat<=0 oldugunda rastgele "100.0"a
    yaslaniyordu (CVL testinde CANLI dogrulandi: seri TAM 100.0000'de
    bitiyordu). Oysa `optimized_universe.csv` (update_tefas_evening.py
    tarafindan yazilan, "onceki gecerli fiyati asla sifira ezme"
    korumasi OLAN, ANA portfoy tablosunun zaten dogru gosterdigi
    kaynak) HER ZAMAN dogru bir fiyata sahip. Bu fonksiyon O dosyayi
    ONCE dener - bulamazsa None doner, cagiran eski BEFAS yontemine
    duser."""
    try:
        _csv_yolu = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "optimized_universe.csv")
        if not os.path.exists(_csv_yolu):
            return None
        df = pd.read_csv(_csv_yolu, on_bad_lines="skip")
        match = df[(df["Ticker"] == ticker.upper()) & (df["Kategori"] == "TEFAS")]
        if match.empty:
            return None
        row = match.iloc[0]
        if float(row.get("Son_Fiyat", 0) or 0) <= 0:
            return None
        return row
    except Exception:
        return None


def _synthetic_from_excel(ticker: str, period: str = "1y",
                           excel_dir: str = "") -> pd.DataFrame:
    """Excel getiri verilerinden sentetik günlük seri üretir."""
    # v2.0.7.319: ONCE optimized_universe.csv (guvenilir, sifira
    # dusurulmez) denenir - bkz. _optimized_universe_satiri_bul.
    row = _optimized_universe_satiri_bul(ticker)
    if row is None:
        df_all = load_excel_all(excel_dir)
        if df_all.empty:
            return pd.DataFrame()
        match = df_all[df_all["Ticker"] == ticker.upper()]
        if match.empty:
            return pd.DataFrame()
        row = match.iloc[0]
    base = float(row.get("Son_Fiyat", 0) or 0)
    if base <= 0:
        # v2.0.7.319: eski davranis (rastgele "100.0" varsayimi) BILEREK
        # KALDIRILDI - gercekten hicbir gecerli fiyat bulunamadiysa
        # UYDURMAK yerine bos seri donduruluyor (grafik "veri yok"
        # gosterir, yanlis bir sayi GOSTERMEZ).
        return pd.DataFrame()
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
    # v2.0.7.319 (16 Eylul 2026): eskiden fiyat<=0 oldugunda rastgele
    # "100.0" varsayiliyordu - bu TAM OLARAK CVL/HTS/HOY/BAG'da
    # gorulen "ayni gunde birden fazla fonun anormal dususu" hatasinin
    # kok nedeniydi. Artik gecerli bir fiyat yoksa BOS SERI donuluyor -
    # cagiran (_synthetic_from_excel) zaten bunu bu noktaya varmadan
    # kontrol ediyor, ama defansif olarak burada da tekrarlandi.
    if base_price <= 0:
        return pd.DataFrame()
    # v2.0.7.321 (17 Eylul 2026, Bahri'nin bulgusu - "son veri 1 eylul
    # tarihinden, grafiklerde anormallikler var"): KOK NEDEN BULUNDU VE
    # CANLI DOGRULANDI - burada "today" ILK KURULUMDAN BERI (ilk yukleme
    # commit'i) YANLISLIKLA ayin 1'ine SABITLENIYORDU (.replace(day=1)).
    # Bu, sentetik seriyi kullanan HER fon icin (ILU/BAG/CVL/HTS/HOY gibi
    # pytefas'ta eslesmeyenler) en son noktayi HER ZAMAN ayin 1'inde
    # bitiriyordu - bugun ayin kaci olursa olsun. CANLI TEST (fix
    # oncesi): ILU/BAG/CVL ucu de "son tarih: 2026-09-01" ile bitti (asil
    # bugun 17 Eylul). Bu ayrica ikinci bir gorsel bozulmaya yol aciyordu:
    # _hist_canli_ile_tamamla() (v2.0.7.289) son tarih bugunden ONCEYSE
    # tek bir "bugun" barı ekliyor - ayin 1'i ile bugun arasinda haftalarca
    # bosluk oldugunda bu, grafikte "duz cizgiyle bugune sicrama" ve
    # buna bagli olarak MA20/MA50 hareketli ortalamalarinin o bosluk
    # boyunca gercek disi bir egim cizmesine yol aciyordu. COZUM: "today"
    # artik GERCEK bugun - .replace(day=1) kaldirildi.
    today = datetime.now()
    base  = base_price
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
            df = None
            # v2.0.7.188 (Bahri'nin bulgusu, 25 Ağustos 2026 — "HTS/HOY
            # hâlâ 0, ama TEFAS'ın kendi sitesinde gerçek fiyatları var"):
            # KÖK NEDEN CANLI TESTLE KANITLANDI - `c.fetch()` çağrısı
            # TEFAS'ın kendi API'sinden ARA SIRA 503 (geçici sunucu
            # hatası) alıyor - CANLI TEST: 1. deneme 503 ile başarısız,
            # 2. deneme (hemen ardından, yeni bir Crawler ile) 6112
            # satırla BAŞARILI oldu. Bu fonksiyonda HİÇ retry YOKTU -
            # bir kez 503 alınınca o KIND (YAT dahil - HTS/HOY'un
            # kategorisi) o tur için TAMAMEN atlanıyordu. Bu, HTS/HOY'a
            # özgü bir sorun DEĞİL - TEFAS'ın API'sinin genel, geçici
            # güvenilmezliği. Çözüm: 3 deneme, aralarda kısa bekleme.
            for _deneme in range(3):
                try:
                    print(f"  [pytefas] {kind} fiyatlari cekiliyor (deneme {_deneme+1}/3)...")
                    df = c.fetch(start=start, end=end, kind=kind)
                    break  # basarili (bos bile olsa exception yok) - dur
                except Exception as e:
                    print(f"  [pytefas {kind}] deneme {_deneme+1}/3 basarisiz: "
                          f"{type(e).__name__}: {e}")
                    if _deneme < 2:
                        import time as _time_pytefas
                        _time_pytefas.sleep(3)
            if df is None:
                print(f"  [pytefas {kind}] 3 deneme de basarisiz - bu tur icin atlaniyor.")
                continue
            try:
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


# ════════════════════════════════════════════════════════════════════════════
# v2.0.7.363 - GERCEK getiri/RSI (bayat Excel'in yerine) - TEK ORTAK kaynak
# ════════════════════════════════════════════════════════════════════════════
# Bahri'nin bulgusu (4 Ekim 2026): ILU, Ana Sayfa bütçe tablosuna "78,7 puan,
# 1A getiri +%12,80, RSI 53,1" ile girdi; oysa Detay'da skor 0,0 ve grafik düşüşteydi.
# Kök neden (1/2): TEFAS getirileri repodaki "*_2026-05-26.xlsx" statik dosyalarından
# (26.05.2026 dışa aktarımı) geliyordu. v2.0.7.352 bunu SADECE günlük işte
# düzeltmişti; worker.py'nin gece tam çalışması (02:00 TRT) CSV'yi tekrar Excel'den
# kurup düzeltmeyi SİLİYORDU. Artık İKİSİ de bu tek fonksiyonu çağırıyor.

GETIRI_TARIHI_KOLONU = "Getiri_Tarihi"   # getirinin hesaplandigi son NAV tarihi (YYYY-MM-DD)

# v2.0.7.371 (8 Ekim 2026, Bahri'nin bulgusu - DFI): TEFAS'ta fiyati 0,0000'a dusen fonlar.
# DFI 25 Eylul'den beri 0,0000 yayinliyor (fon buyuklugu 0,01 TL); CSV'de ise 24 Eylul'un son
# sifir-olmayan fiyati (0,4058) "son fiyat" diye duruyordu, cunku "fiyat alinamayan fonun onceki
# satirini koru" korumasi (v2.0.7.174/186) SIFIR fiyati da "alinamadi" sayip eski satiri geri
# yaziyordu. Gercek sifir (TEFAS acikca 0 yayinliyor) ile eksik veri (hic gelmedi) AYRI
# ele alinmali: ilki korunmaz, ikincisi korunur.
NAV_DURUMU_KOLONU = "NAV_Durumu"   # "SIFIR" = TEFAS yakin zamandan beri 0 fiyat yayinliyor
NAV_SIFIR_MIN_GUN = 3              # en az bu kadar ARDISIK son kayit 0 olmali (tek gunluk glitch degil)
NAV_SIFIR_MAKS_YAS_GUN = 10        # son kayit en fazla bu kadar gun eski olmali (veri tazeligi)


def nav_sifir_fonlari(parcalar, bugun=None, min_gun: int = NAV_SIFIR_MIN_GUN,
                      maks_yas_gun: int = NAV_SIFIR_MAKS_YAS_GUN) -> set:
    """Son `min_gun`+ kaydi ARDISIK 0 olan, oncesinde pozitif fiyati bulunan ve son kaydi taze
    (<= maks_yas_gun gun) olan fon kodlari. `parcalar`: [ticker, tarih, fiyat] DataFrame listesi.
    Hic fiyati olmayan (hep 0) fon ya da TEFAS'tan hic gelmeyen fon BURADA sayilmaz."""
    bugun = pd.Timestamp(bugun if bugun is not None else datetime.now()).normalize()
    sonuc = set()
    for d in parcalar or []:
        if d is None or len(d) == 0:
            continue
        for ticker, grp in d.sort_values(["ticker", "tarih"]).groupby("ticker"):
            f = pd.to_numeric(grp["fiyat"], errors="coerce").dropna().to_numpy()
            if len(f) <= min_gun or (f[-min_gun:] > 0).any() or not (f[:-min_gun] > 0).any():
                continue
            son_tarih = pd.Timestamp(grp["tarih"].iloc[-1]).normalize()
            if (bugun - son_tarih).days > maks_yas_gun:
                continue
            sonuc.add(str(ticker))
    return sonuc


def onceki_satiri_koru(df_t: pd.DataFrame, onceki_tefas: pd.DataFrame) -> int:
    """Bu turda fiyat alinamayan (Son_Fiyat<=0) TEFAS satirlari icin, onceki CSV'de GECERLI (>0)
    fiyat varsa o satirin TAMAMINI geri yazar (v2.0.7.174/186). v2.0.7.371: NAV_Durumu=="SIFIR"
    olan fonlar (TEFAS acikca 0 yayinliyor) ATLANIR - bu 'veri yok' degil, 'fiyat gercekten 0'.
    onceki_tefas: Ticker index'li DataFrame. Dondurur: korunan fon sayisi."""
    if df_t is None or df_t.empty or onceki_tefas is None or len(onceki_tefas) == 0:
        return 0
    sifir_isaretli = (df_t[NAV_DURUMU_KOLONU].astype(str).str.upper() == "SIFIR"
                      if NAV_DURUMU_KOLONU in df_t.columns else pd.Series(False, index=df_t.index))
    korunan = 0
    for idx in df_t.index[(pd.to_numeric(df_t["Son_Fiyat"], errors="coerce").fillna(0) <= 0)]:
        if bool(sifir_isaretli.get(idx, False)):
            continue
        tkr = df_t.at[idx, "Ticker"]
        if tkr in onceki_tefas.index:
            try:
                onceki_fiyat = float(onceki_tefas.at[tkr, "Son_Fiyat"] or 0)
            except Exception:
                onceki_fiyat = 0.0
            if onceki_fiyat > 0:
                for col in df_t.columns:
                    if col in onceki_tefas.columns:
                        df_t.at[idx, col] = onceki_tefas.at[tkr, col]
                korunan += 1
    return korunan


def rsi14(s, p: int = 14) -> float:
    """worker.calc_rsi ile BIREBIR ayni formul (dongusel import olmasin diye burada)."""
    s = s.dropna()
    if len(s) < p + 1:
        return 50.0
    d = s.diff()
    g = d.where(d > 0, 0.0).rolling(p).mean()
    l = (-d.where(d < 0, 0.0)).rolling(p).mean()
    ll = l.iloc[-1]
    if ll == 0:
        return 100.0
    return round(100 - (100 / (1 + g.iloc[-1] / ll)), 1)


def gercek_getiri_rsi_guncelle(df_t: pd.DataFrame, derinlik_gun: int = 95, log=print):
    """TEFAS satirlarinin Ret1M/Ret3M/RSI degerlerini GERCEK gunluk fiyatlardan
    yeniden hesaplar (pytefas toplu sorgu, fund_code VERILMEDEN), Ret6M/Ret1Y/Ret3Y/
    Ret5Y'yi kalici fiyat arsivinden (varsa) hesaplar ve getirinin hangi NAV
    tarihine ait oldugunu `Getiri_Tarihi` kolonuna yazar.

    Dondurur: (df_t, arsiv_parcalari, ozet). `arsiv_parcalari`: arsive yazilabilecek
    ham [ticker, tarih, fiyat] DataFrame listesi. Hesaplanamayan fonlarin
    `Getiri_Tarihi`si BOS kalir -> optimizer bunlari 'bayat veri' sayip onermez."""
    from pytefas import Crawler
    ozet = {"guncellenen": 0, "uzun_vade": False, "kind_hata": [], "nav_sifir": []}
    if df_t is None or df_t.empty:
        return df_t, [], ozet

    crawler = Crawler(timeout=60, max_retry=4)   # her 28 gunluk sayfa AYRI yeniden denenir
    bugun = datetime.now()
    start = (bugun - timedelta(days=derinlik_gun)).strftime("%Y-%m-%d")
    end = bugun.strftime("%Y-%m-%d")
    if GETIRI_TARIHI_KOLONU not in df_t.columns:
        df_t[GETIRI_TARIHI_KOLONU] = None
    else:
        df_t[GETIRI_TARIHI_KOLONU] = None   # onceki degerler gecerli sayilmaz: yeniden dogrulanacak
    df_t[NAV_DURUMU_KOLONU] = ""            # v2.0.7.371: her turda yeniden belirlenir

    parcalar, son_fiyat_tarihi = [], {}
    for kind in ["YAT", "EMK", "BYF"]:
        try:
            df_bulk = crawler.fetch(start=start, end=end, kind=kind)
        except Exception as e:
            log(f"[getiri] Toplu gecmis ({kind}) cekilemedi: {type(e).__name__}: {str(e)[:120]}")
            ozet["kind_hata"].append(kind)
            continue
        if df_bulk is None or df_bulk.empty:
            log(f"[getiri] Toplu gecmis ({kind}): bos dondu.")
            continue
        kol = {c.lower(): c for c in df_bulk.columns}
        try:
            d = df_bulk[[kol["fund_code"], kol["date"], kol["price"]]].copy()
        except KeyError:
            log(f"[getiri] ({kind}) beklenen sutunlar yok: {df_bulk.columns.tolist()}")
            continue
        d.columns = ["ticker", "tarih", "fiyat"]
        d["tarih"] = pd.to_datetime(d["tarih"], errors="coerce")
        d["fiyat"] = pd.to_numeric(d["fiyat"], errors="coerce")
        d = d.dropna(subset=["ticker", "tarih", "fiyat"]).sort_values(["ticker", "tarih"])

        r1, r3, rsi, tarih = {}, {}, {}, {}
        for ticker, grp in d.groupby("ticker"):
            s = grp.set_index("tarih")["fiyat"]
            if len(s) < 15:                       # RSI(14) icin yeterli veri yok
                continue
            son = float(s.iloc[-1])
            a = s[s.index <= (s.index[-1] - pd.Timedelta(days=30))]
            if a.empty or a.iloc[-1] <= 0:
                continue                           # 1 aylik getiri hesaplanamaz
            r1[ticker] = round((son / float(a.iloc[-1]) - 1) * 100, 2)
            b = s[s.index <= (s.index[-1] - pd.Timedelta(days=90))]
            if not b.empty and b.iloc[-1] > 0:
                r3[ticker] = round((son / float(b.iloc[-1]) - 1) * 100, 2)
            rsi[ticker] = rsi14(s)
            tarih[ticker] = s.index[-1].strftime("%Y-%m-%d")

        m = df_t["TEFAS_Kind"] == kind
        tk = df_t.loc[m, "Ticker"].astype(str)
        df_t.loc[m, "Ret1M"] = tk.map(r1).combine_first(df_t.loc[m, "Ret1M"])
        df_t.loc[m, "Ret3M"] = tk.map(r3).combine_first(df_t.loc[m, "Ret3M"])
        df_t.loc[m, "RSI"] = tk.map(rsi).combine_first(df_t.loc[m, "RSI"])
        df_t.loc[m, GETIRI_TARIHI_KOLONU] = tk.map(tarih)
        son_fiyat_tarihi.update(tarih)
        log(f"[getiri] {kind}: {len(r1)} fon icin GERCEK Ret1M/Ret3M/RSI hesaplandi "
            f"({d['ticker'].nunique()} fon, {len(d)} satir).")
        parcalar.append(d)

    # Uzun vadeli getiriler: kalici fiyat arsivinden (Excel'in 5 aylik bayat degerleri yerine).
    # Once BOSALTILIR: arsive ulasilamazsa/hesaplanamazsa 5 aylik bayat Excel degeri
    # gostermektense bos birakmak dogrudur (bir sonraki calismada dolar).
    if son_fiyat_tarihi:
        for _k in ("Ret6M", "Ret1Y", "Ret3Y", "Ret5Y"):
            df_t[_k] = np.nan
        try:
            import db as _db
            son_gun = max(pd.to_datetime(list(son_fiyat_tarihi.values())))
            fiyat_simdi = pd.to_numeric(df_t["Son_Fiyat"], errors="coerce")
            tk_all = df_t["Ticker"].astype(str)
            for kol_adi, gun in (("Ret6M", 182), ("Ret1Y", 365), ("Ret3Y", 1095), ("Ret5Y", 1825)):
                hedef = (son_gun - pd.Timedelta(days=gun)).strftime("%Y-%m-%d")
                gecmis = _db.tefas_arsiv_fiyatlari(hedef, tolerans_gun=10)
                if gecmis is None:
                    log(f"[getiri] {kol_adi}: arsive ulasilamadi - bos birakildi (bayat Excel degeri gosterilmez).")
                    continue
                eski = tk_all.map(gecmis)
                getiri = ((fiyat_simdi / eski - 1) * 100).round(2)
                getiri = getiri.where((eski > 0) & (fiyat_simdi > 0))
                df_t[kol_adi] = getiri          # hesaplanamayanlar (fon o tarihte yoktu) BOS
                log(f"[getiri] {kol_adi}: {int(getiri.notna().sum())} fon icin arsivden hesaplandi.")
                ozet["uzun_vade"] = True
        except Exception as e:
            log(f"[getiri] Uzun vadeli getiriler atlandi: {type(e).__name__}: {str(e)[:120]}")

    # v2.0.7.371: NAV'i 0'a dusen fonlar. Son_Fiyat 0'lanir (Excel/pytefas'taki bayat deger de ezilir),
    # RSI 0 (anlamsiz 'notr' degil), getiriler -%100, NAV_Durumu="SIFIR" -> onceki_satiri_koru atlar.
    try:
        sifir = nav_sifir_fonlari(parcalar, bugun)
        if sifir:
            m0 = df_t["Ticker"].astype(str).isin(sifir)
            df_t.loc[m0, "Son_Fiyat"] = 0.0
            df_t.loc[m0, "RSI"] = 0.0
            for _k in ("Ret1M", "Ret3M", "Ret6M", "Ret1Y", "Ret3Y", "Ret5Y"):
                if _k in df_t.columns:
                    df_t.loc[m0, _k] = -100.0
            df_t.loc[m0, NAV_DURUMU_KOLONU] = "SIFIR"
            ozet["nav_sifir"] = sorted(df_t.loc[m0, "Ticker"].astype(str))
            log(f"[getiri] NAV SIFIR (TEFAS 0 fiyat yayinliyor): {', '.join(ozet['nav_sifir'])}")
    except Exception as e:
        log(f"[getiri] NAV sifir tespiti atlandi: {type(e).__name__}: {str(e)[:120]}")

    ozet["guncellenen"] = int(df_t[GETIRI_TARIHI_KOLONU].notna().sum())   # yalnizca evrendeki fonlar
    return df_t, parcalar, ozet
