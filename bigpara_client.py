"""
bigpara_client.py — TrendSurf Optima
Bigpara.com'dan maden ve kripto TL bazlı fiyatları çeker.
Yedek kaynak olarak worker.py tarafından kullanılır.
"""

import os, json, time, re
import requests
import pandas as pd

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR  = os.path.join(BASE_DIR, "halka_arz_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "bigpara_cache.json")
CACHE_TTL  = 3600 * 2  # 2 saatlik cache

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Referer": "https://bigpara.hurriyet.com.tr/",
}

# Bigpara sayfaları → TrendSurf Ticker eşlemesi
MADEN_PAGES = {
    "ALTIN_TRY":    "https://bigpara.hurriyet.com.tr/altin/gram-altin-fiyati/",
    "GUMUS_TRY":    "https://bigpara.hurriyet.com.tr/altin/gumus-fiyatlari/",
    "BRENT_TRY":    "https://bigpara.hurriyet.com.tr/emtia/brent-petrol-fiyatlari/",
    "PETROL_TRY":   "https://bigpara.hurriyet.com.tr/emtia/petrol-fiyatlari/",
}

# Kripto sayfaları
KRIPTO_PAGES = {
    "BTC":  "https://bigpara.hurriyet.com.tr/kripto-para/bitcoin-fiyati/",
    "ETH":  "https://bigpara.hurriyet.com.tr/kripto-para/ethereum-fiyati/",
    "BNB":  "https://bigpara.hurriyet.com.tr/kripto-para/bnb-fiyati/",
    "SOL":  "https://bigpara.hurriyet.com.tr/kripto-para/solana-fiyati/",
    "XRP":  "https://bigpara.hurriyet.com.tr/kripto-para/xrp-fiyati/",
    "ADA":  "https://bigpara.hurriyet.com.tr/kripto-para/cardano-fiyati/",
    "DOGE": "https://bigpara.hurriyet.com.tr/kripto-para/dogecoin-fiyati/",
    "AVAX": "https://bigpara.hurriyet.com.tr/kripto-para/avalanche-fiyati/",
    "LINK": "https://bigpara.hurriyet.com.tr/kripto-para/chainlink-fiyati/",
    "LTC":  "https://bigpara.hurriyet.com.tr/kripto-para/litecoin-fiyati/",
    "DOT":  "https://bigpara.hurriyet.com.tr/kripto-para/polkadot-fiyati/",
    "ATOM": "https://bigpara.hurriyet.com.tr/kripto-para/cosmos-fiyati/",
    "TRX":  "https://bigpara.hurriyet.com.tr/kripto-para/tron-fiyati/",
}

# ── Cache ──────────────────────────────────────────────────────────────────────

def _read_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        if time.time() - os.path.getmtime(CACHE_FILE) > CACHE_TTL:
            return None
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _write_cache(data: dict):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ── Yardımcı ──────────────────────────────────────────────────────────────────

def _safe_float(v) -> float:
    if v is None:
        return 0.0
    try:
        s = str(v).strip()
        # Türkçe format: 6.224,56 → 6224.56
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return 0.0

def _fetch_price_from_page(url: str, min_val: float = 0.0) -> float:
    """Bigpara HTML sayfasından fiyat çeker."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return 0.0
        text = r.text

        # Önce JSON veri bloklarını ara (data-price, data-value gibi)
        patterns = [
            r'"last"\s*:\s*([\d,\.]+)',
            r'"price"\s*:\s*([\d,\.]+)',
            r'"alis"\s*:\s*([\d,\.]+)',
            r'"satis"\s*:\s*([\d,\.]+)',
            r'data-price="([\d,\.]+)"',
            r'data-value="([\d,\.]+)"',
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                val = _safe_float(m.group(1))
                if val > min_val:
                    return val

        # HTML içinde fiyat sayısı ara (büyük rakam = TL fiyatı)
        # Altın için 1000+ TL, kripto BTC için 1.000.000+ TL
        numbers = re.findall(r'([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2,4})?)', text)
        candidates = []
        for n in numbers:
            val = _safe_float(n)
            if val > min_val:
                candidates.append(val)
        if candidates:
            # En çok geçen makul değeri döndür
            from collections import Counter
            rounded = [round(v, -1) for v in candidates if v > min_val]
            if rounded:
                most_common = Counter(rounded).most_common(1)[0][0]
                # O değere en yakın gerçek değeri bul
                close = [v for v in candidates if abs(v - most_common) < most_common * 0.05]
                if close:
                    return round(sum(close) / len(close), 4)
    except Exception:
        pass
    return 0.0

# ── Maden fiyatları ───────────────────────────────────────────────────────────

def _fetch_satis_fiyati_cumle(url: str) -> float:
    """Bigpara sayfalarinda tutarli sekilde tekrar eden dogal dil cumlesini
    hedefler: 'alış fiyatı 6.245,00 TL, satış fiyatı 6.245,94 TL seklindedir.'
    Bu cumle, sayfanin SEO/aciklama metninin bir parcasi oldugundan JS
    calismadan da (requests.get() ile) HTML icinde bulunuyor ve sayfadaki
    onlarca diger sayidan (haftalik/aylik/yillik dusuk-yuksek, onceki
    kapanislar vb.) FARKLI olarak tek ve net bir yerde geciyor - bu yuzden
    aralik-bazli tahminden cok daha guvenilir."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return 0.0
        m = re.search(
            r'sat[ıi]ş\s*fiyat[ıi]\s*([\d\.,]+)\s*TL',
            r.text, re.IGNORECASE
        )
        if m:
            return _safe_float(m.group(1))
    except Exception:
        pass
    return 0.0

def _fetch_maden_bigpara() -> dict:
    """Bigpara'dan maden TL fiyatlarını çeker.

    v2.0.4.46: Onceki surum, sayfadaki "4000-15000 arasindaki ILK sayiyi"
    alan kaba bir regex kullaniyordu. Bigpara'nin sayfasinda (Alis, Satis,
    Onceki Hafta Kapanisi, Aylik/Yillik Dusuk-Yuksek gibi) o aralikta
    ONLARCA sayi bulundugundan, hangisinin yakalanacagi sayfa yapisindaki
    kucuk degisikliklere gore degisiyordu - bu da uygulamanin gunler
    boyunca yanlis/eski bir rakamda "donmus" gorunmesine sebep oluyordu
    (Son_Fiyat degisse bile hep BASKA yanlis bir alani okuyordu). Test
    ettigimde istatistiksel (en sik gecen deger) yaklasim bile bu sayfada
    yeterince kesin degildi - altin gibi dusuk oynaklikli bir varlikta
    haftalik/aylik dusuk-yuksek degerleri de birbirine cok yakin oldugundan
    yanlislikla "yakin" sayilip ortalamaya karisabiliyordu.
    Duzeltme: once Bigpara'nin HER SAYFASINDA ayni sekilde tekrar eden
    "...satis fiyati X TL seklindedir" cumlesi hedefleniyor (en guvenilir),
    o bulunamazsa etiketli JSON alanlarina (_fetch_price_from_page), o da
    olmazsa aralik-bazli tahmine dusuluyor.
    """
    result = {}

    # Altın: gram altın TL fiyatı
    val = _fetch_satis_fiyati_cumle(MADEN_PAGES["ALTIN_TRY"])
    if not (4000 < val < 15000):
        val = _fetch_price_from_page(MADEN_PAGES["ALTIN_TRY"], min_val=4000.0)
    if 4000 < val < 15000:
        result["ALTIN_TRY"] = round(val, 4)
    elif val > 0:
        print(f"  [Bigpara] Altın: sayfa degeri ({val}) beklenen aralik disinda, atlandi")

    # Gümüş: gram gümüş TL fiyatı
    val = _fetch_satis_fiyati_cumle(MADEN_PAGES["GUMUS_TRY"])
    if not (50 < val < 1000):
        val = _fetch_price_from_page(MADEN_PAGES["GUMUS_TRY"], min_val=50.0)
    if 50 < val < 1000:
        result["GUMUS_TRY"] = round(val, 4)

    # Brent petrol: TL bazlı
    val = _fetch_satis_fiyati_cumle(MADEN_PAGES["BRENT_TRY"])
    if not (500 < val < 10000):
        val = _fetch_price_from_page(MADEN_PAGES["BRENT_TRY"], min_val=500.0)
    if 500 < val < 10000:
        result["BRENT_TRY"] = round(val, 4)

    return result

# ── Kripto fiyatları ──────────────────────────────────────────────────────────

def _fetch_kripto_bigpara(usdtry: float = 38.0) -> dict:
    """
    Bigpara kripto sayfalarından TL fiyatları çeker.
    Eğer sayfa USD fiyatı veriyorsa USDTRY ile çarpar.
    """
    result = {}

    # BTC: milyonlar mertebesinde TL fiyatı
    try:
        r = requests.get(KRIPTO_PAGES["BTC"], headers=HEADERS, timeout=10)
        if r.status_code == 200:
            nums = re.findall(r'(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2,4})?)', r.text)
            for n in nums:
                val = _safe_float(n)
                if 1_000_000 < val < 20_000_000:  # BTC TL aralığı
                    result["BTC"] = round(val, 2)
                    break
            if "BTC" not in result:
                # USD fiyatı × USDTRY dene
                for n in nums:
                    val = _safe_float(n)
                    if 50_000 < val < 500_000:  # BTC USD aralığı
                        result["BTC"] = round(val * usdtry, 2)
                        break
    except Exception:
        pass

    # ETH
    try:
        r = requests.get(KRIPTO_PAGES["ETH"], headers=HEADERS, timeout=10)
        if r.status_code == 200:
            nums = re.findall(r'(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2,4})?)', r.text)
            for n in nums:
                val = _safe_float(n)
                if 50_000 < val < 5_000_000:  # ETH TL aralığı
                    result["ETH"] = round(val, 2)
                    break
                elif 1_000 < val < 20_000:  # USD aralığı
                    result["ETH"] = round(val * usdtry, 2)
                    break
    except Exception:
        pass

    # Diğer kriptolar (daha küçük değerler)
    small_cryptos = {
        "BNB": (500, 2000),   # USD aralığı
        "SOL": (100, 1000),
        "XRP": (0.1, 20),
        "ADA": (0.1, 5),
        "DOGE": (0.05, 2),
        "AVAX": (5, 200),
        "LINK": (5, 200),
        "LTC": (50, 500),
        "DOT": (2, 100),
        "ATOM": (2, 100),
        "TRX": (0.01, 1),
    }
    for ticker, (usd_min, usd_max) in small_cryptos.items():
        if ticker not in KRIPTO_PAGES:
            continue
        try:
            r = requests.get(KRIPTO_PAGES[ticker], headers=HEADERS, timeout=8)
            if r.status_code == 200:
                nums = re.findall(r'(\d+(?:[.,]\d+)?)', r.text)
                for n in nums:
                    val = _safe_float(n)
                    if usd_min < val < usd_max:
                        result[ticker] = round(val * usdtry, 4)
                        break
                    elif usd_min * usdtry < val < usd_max * usdtry:
                        result[ticker] = round(val, 4)
                        break
        except Exception:
            pass

    return result

# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def fetch_all_bigpara(force_refresh: bool = False, usdtry: float = 38.0) -> dict:
    """
    Bigpara'dan tüm maden ve kripto TL fiyatlarını çeker.
    Returns: {"ALTIN_TRY": 6250.5, "BTC": 3800000.0, ...}
    """
    if not force_refresh:
        cached = _read_cache()
        if cached:
            return cached

    print("  [Bigpara] Maden ve kripto TL fiyatlari cekiliyor...")
    result = {}

    maden = _fetch_maden_bigpara()
    result.update(maden)

    kripto = _fetch_kripto_bigpara(usdtry=usdtry)
    result.update(kripto)

    ok = len([v for k, v in result.items() if isinstance(v, float) and v > 0])
    print(f"  [Bigpara] {ok} varlik fiyati alindi: {list(result.keys())}")

    _write_cache(result)
    return result

def enrich_worker_maden(all_rows: list, bigpara_data: dict, usdtry: float) -> list:
    """
    worker.py'deki maden satırlarını Bigpara TL fiyatlarıyla günceller.
    Sadece yfinance'den fiyat gelemediyse (Son_Fiyat == 0) devreye girer.
    """
    for r in all_rows:
        if r.get("Kategori") != "MADEN":
            continue
        ticker = r.get("Ticker", "")
        cur_p  = float(r.get("Son_Fiyat", 0))
        if cur_p > 0:
            continue
        bp_p = bigpara_data.get(ticker, 0.0)
        if isinstance(bp_p, (int, float)) and bp_p > 0:
            r["Son_Fiyat"] = bp_p
            r["_bigpara"]  = True
            print(f"    [Bigpara] {ticker}: {bp_p:.4f} TL")
    return all_rows

def enrich_worker_kripto(all_rows: list, bigpara_data: dict, usdtry: float) -> list:
    """
    worker.py'deki kripto satırlarını Bigpara TL fiyatlarıyla günceller.
    Sadece yfinance'den fiyat gelemediyse devreye girer.
    """
    for r in all_rows:
        if r.get("Kategori") != "KRIPTO":
            continue
        ticker = r.get("Ticker", "")
        cur_p  = float(r.get("Son_Fiyat", 0))
        if cur_p > 0:
            continue
        bp_p = bigpara_data.get(ticker, 0.0)
        if isinstance(bp_p, (int, float)) and bp_p > 0:
            r["Son_Fiyat"] = bp_p
            r["_bigpara"]  = True
            print(f"    [Bigpara] {ticker}: {bp_p:.4f} TL")
    return all_rows

if __name__ == "__main__":
    import os, sys
    # USDTRY'yi yfinance'den al
    try:
        import yfinance as yf
        _s = yf.download("USDTRY=X", period="2d", progress=False, auto_adjust=True)
        usdtry = float(_s["Close"].dropna().iloc[-1]) if not _s.empty else 38.0
    except Exception:
        usdtry = 38.0
    print(f"Bigpara test... (USDTRY: {usdtry:.4f})")
    data = fetch_all_bigpara(force_refresh=True, usdtry=usdtry)
    for k, v in data.items():
        print(f"  {k}: {v:,.4f} TL")
