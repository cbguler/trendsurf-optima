"""
TrendSurf Optima — Veri Motoru (worker.py)
Çalıştırma: python worker.py
Görev: TEFAS Excel + BIST + Kripto + Maden + Döviz verilerini çekerek
       optimized_universe.csv dosyasını oluşturur.
"""

import pandas as pd
import os
import sys
from datetime import datetime, timedelta

# --- BIST, Kripto, Maden, Döviz sabit evren tanımları ---
BIST_TICKERS = [
    "THYAO","GARAN","ISCTR","AKBNK","YKBNK","SISE","KCHOL","SAHOL","TUPRS","EREGL",
    "FROTO","TOASO","BIMAS","ARCLK","ASELS","TAVHL","EKGYO","ENKAI","TKFEN","PGSUS",
    "TCELL","TTKOM","PETKM","AKSEN","GUBRF","CCOLA","AEFES","ULKER","TATGD","DOAS",
    "MGROS","SOKM","LOGO","INDES","NETAS","OTKAR","KORDS","BRISA","SARKY","SASA",
    "VESTL","VESBE","DOHOL","HALKB","VAKBN","TSKB","ALBRK","KLNMA","ZOREN","AYGAZ",
    "KONTR","KOZAL","MAVI","DESA","NUHCM","CIMSA","AKCNS","BUCIM","GOLTS","BTCIM",
    "EGEEN","DMSAS","ISDMR","KRDMD","BRSAN","CELHA","BOLUC","ADANA","USAK","EGSER",
    "CLEBI","MPARK","SELEC","ECZYT","DEVA","HEKTS","LKMNH","ANSGR","ANHYT","RAYSG",
    "SKBNK","QNBTR","ISCTR","ISATR","VAKBN","TRGYO","ISGYO","EKGYO","KRGYO","SNGYO",
    "KLGYO","NUGYO","IHLGM","MRGYO","RYGYO","DZGYO","HLGYO","OZKGY","TSGYO","AKFGY",
]

KRIPTO_TICKERS = [
    ("BTC","BTC-USD"), ("ETH","ETH-USD"), ("BNB","BNB-USD"), ("SOL","SOL-USD"),
    ("ADA","ADA-USD"), ("XRP","XRP-USD"), ("DOGE","DOGE-USD"), ("DOT","DOT-USD"),
    ("AVAX","AVAX-USD"), ("MATIC","MATIC-USD"), ("LINK","LINK-USD"), ("LTC","LTC-USD"),
    ("ATOM","ATOM-USD"), ("UNI","UNI-USD"), ("ALGO","ALGO-USD"),
]

MADEN_TICKERS = [
    ("ALTIN_USD","GC=F"), ("GUMUS_USD","SI=F"), ("PLATIN_USD","PL=F"),
    ("BAKIR_USD","HG=F"), ("PETROL_USD","CL=F"), ("DOGALGAZ_USD","NG=F"),
]

DOVIZ_TICKERS = [
    ("USDTRY","USDTRY=X"), ("EURTRY","EURTRY=X"), ("GBPTRY","GBPTRY=X"),
    ("JPYTRY","JPYTRY=X"), ("EURUSD","EURUSD=X"), ("GBPUSD","GBPUSD=X"),
    ("CHFTRY","CHFTRY=X"),
]

OUTPUT_PATH = "optimized_universe.csv"


def safe_float(val):
    """Her türlü girişi float'a çevirir, başaramazsa 0.0 döner."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except:
        s = str(val).strip().replace(" ", "")
        s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 and "." in s and s.rfind(".") < s.rfind(",") else s.replace(",", ".")
        try:
            return float(s)
        except:
            return 0.0


def fetch_yfinance_price(yf_ticker: str) -> float:
    """yfinance üzerinden son kapanış fiyatını getirir."""
    try:
        import yfinance as yf
        tk = yf.Ticker(yf_ticker)
        hist = tk.history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 4)
        p = tk.fast_info.get("last_price")
        return round(float(p), 4) if p else 0.0
    except Exception as e:
        print(f"  [UYARI] yfinance ({yf_ticker}): {e}")
        return 0.0


def load_tefas_from_excel() -> pd.DataFrame:
    """
    3 TEFAS Excel dosyasından fon kodlarını ve son fiyatları okur.
    Dosya isim kalıpları esnektir — tarih kısmı değişse de bulur.
    """
    import glob
    rows = []

    kat_map = {
        "Menkul_Kiymet": "TEFAS",
        "Emeklilik": "TEFAS",
        "Borsa_Yatirim": "TEFAS",
        "menkul": "TEFAS",
        "emeklilik": "TEFAS",
        "borsa": "TEFAS",
        "TEFAS": "TEFAS",
        "tefas": "TEFAS",
    }

    excel_files = glob.glob("*.xlsx") + glob.glob("*.xls")
    if not excel_files:
        print("  [UYARI] Klasörde Excel dosyası bulunamadı. TEFAS atlanıyor.")
        return pd.DataFrame(rows)

    print(f"  Bulunan Excel dosyaları: {excel_files}")

    for fpath in excel_files:
        # Kategori tespiti
        cat = "TEFAS"
        fname_lower = fpath.lower()
        for key, val in kat_map.items():
            if key.lower() in fname_lower:
                cat = val
                break

        for header_row in [4, 3, 2, 1, 0]:
            try:
                df = pd.read_excel(fpath, header=header_row)
                # Fon Kodu sütununu bul
                kod_col = None
                for c in df.columns:
                    if "kod" in str(c).lower() or "code" in str(c).lower():
                        kod_col = c
                        break
                if kod_col is None:
                    continue

                # Fiyat sütununu bul
                fiyat_col = None
                for c in df.columns:
                    cl = str(c).lower()
                    if any(x in cl for x in ["fiyat","price","değer","deger","birim"]):
                        fiyat_col = c
                        break

                for _, row in df.iterrows():
                    ticker = str(row[kod_col]).strip().upper()
                    if not ticker or ticker == "NAN" or len(ticker) > 8:
                        continue

                    price = 0.0
                    if fiyat_col and fiyat_col in row:
                        price = safe_float(row[fiyat_col])

                    # Fon adı bulmaya çalış
                    ad_col = None
                    for c in df.columns:
                        if "ad" in str(c).lower() or "isim" in str(c).lower() or "name" in str(c).lower():
                            ad_col = c
                            break
                    name = str(row[ad_col]).strip() if ad_col else ticker

                    rows.append({
                        "Ticker": ticker,
                        "Ad": name[:60],
                        "Kategori": cat,
                        "Son_Fiyat": price,
                        "Kaynak": fpath,
                    })
                print(f"  [{fpath}] {len([r for r in rows if r['Kaynak']==fpath])} fon okundu (header={header_row})")
                break  # Bu header_row çalıştı, sonraki dosyaya geç
            except Exception as e:
                continue

    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        # Mükerrer kaldır, son kaydı tut
        df_out = df_out.drop_duplicates(subset=["Ticker"], keep="last")
    return df_out


def build_universe():
    """Ana fonksiyon: tüm varlık sınıflarını toplar, CSV'ye yazar."""
    print("\n" + "="*55)
    print("  TrendSurf Optima — Evren Oluşturma Başladı")
    print("="*55)

    all_rows = []

    # ── 1. TEFAS Fonları (Excel'den) ──────────────────────────
    print("\n[1/4] TEFAS fonları Excel'den okunuyor...")
    df_tefas = load_tefas_from_excel()
    if not df_tefas.empty:
        # Fiyatı 0 olan fonlar için API'ye gitme (çok yavaş olur)
        # Sadece mevcut fiyatı kaydet; canlı fiyat app.py'de istek üzerine çekilir
        for _, row in df_tefas.iterrows():
            all_rows.append({
                "Ticker": row["Ticker"],
                "Ad": row["Ad"],
                "Kategori": "TEFAS",
                "Son_Fiyat": row["Son_Fiyat"],
            })
        print(f"  {len(df_tefas)} TEFAS fonu eklendi.")
    else:
        print("  TEFAS verisi bulunamadi. Excel dosyalarini kontrol edin.")

    # ── 2. BIST Hisseleri (yfinance) ──────────────────────────
    print(f"\n[2/4] {len(BIST_TICKERS)} BIST hissesi yfinance'den cekiliyor...")
    bist_ok = 0
    for tkr in BIST_TICKERS:
        yf_sym = tkr if tkr.endswith(".IS") else tkr + ".IS"
        price = fetch_yfinance_price(yf_sym)
        all_rows.append({
            "Ticker": tkr,
            "Ad": tkr,
            "Kategori": "BIST",
            "Son_Fiyat": price,
        })
        if price > 0:
            bist_ok += 1
    print(f"  {bist_ok}/{len(BIST_TICKERS)} BIST hissesi fiyati alindi.")

    # ── 3. Kripto ────────────────────────────────────────────
    print(f"\n[3/4] {len(KRIPTO_TICKERS)} kripto varlik yfinance'den cekiliyor...")
    for tkr, yf_sym in KRIPTO_TICKERS:
        price = fetch_yfinance_price(yf_sym)
        all_rows.append({
            "Ticker": tkr,
            "Ad": tkr,
            "Kategori": "KRIPTO",
            "Son_Fiyat": price,
        })

    # ── 4. Maden & Döviz ─────────────────────────────────────
    print(f"\n[4/4] Maden ({len(MADEN_TICKERS)}) ve Doviz ({len(DOVIZ_TICKERS)}) cekiliyor...")
    for tkr, yf_sym in MADEN_TICKERS:
        price = fetch_yfinance_price(yf_sym)
        all_rows.append({
            "Ticker": tkr,
            "Ad": tkr,
            "Kategori": "MADEN",
            "Son_Fiyat": price,
        })
    for tkr, yf_sym in DOVIZ_TICKERS:
        price = fetch_yfinance_price(yf_sym)
        all_rows.append({
            "Ticker": tkr,
            "Ad": tkr,
            "Kategori": "DOVIZ",
            "Son_Fiyat": price,
        })

    # ── Kaydet ───────────────────────────────────────────────
    df_final = pd.DataFrame(all_rows)
    df_final = df_final[df_final["Ticker"].str.len() > 0]
    df_final = df_final.drop_duplicates(subset=["Ticker"], keep="last")
    df_final = df_final.reset_index(drop=True)

    df_final.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print("\n" + "="*55)
    print(f"  TAMAMLANDI: {len(df_final)} varlik kaydedildi -> {OUTPUT_PATH}")
    by_cat = df_final.groupby("Kategori").size()
    for cat, cnt in by_cat.items():
        print(f"    {cat}: {cnt}")
    print("="*55 + "\n")


if __name__ == "__main__":
    build_universe()
