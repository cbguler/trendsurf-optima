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
# v2.0.4.55: BRENT_TRY/PETROL_TRY kaldirildi - Bigpara'nin bu sayfalari
# sadece uluslararasi ham petrol varil fiyatini (USD) gosteriyor, gercek
# bir Turkiye TL piyasasi degil (Turkiye'deki gercek TL akaryakit piyasasi
# rafine urunler - benzin/motorin, litre bazli, EPDK duzenlemeli - ham
# petrolden farkli bir urun ve eşel mobil gibi mekanizmalarla ham petrol
# fiyatina birebir bagli bile degil).
MADEN_PAGES = {
    "ALTIN_TRY":    "https://bigpara.hurriyet.com.tr/altin/gram-altin-fiyati/",
    "GUMUS_TRY":    "https://bigpara.hurriyet.com.tr/altin/gumus-fiyatlari/",
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

# v2.0.4.55: Platin icin GERCEK bir Turkiye TL piyasasi var (Akbank,
# Papara, doviz.com gibi kurumlar gram bazinda TL alis/satis yapiyor) -
# Bigpara'da bu sayfa sadece USD/ons gosterdigi icin doviz.com kullaniliyor
# (sayfa yapisi guvenilir: hem tekrar eden bir cumle kalibi hem
# yapilandirilmis bir tablo var).
# v2.0.7.76: Paladyum bu yedekten cikarildi (Bahri'nin talebi - RSI/Ret1M
# icin hicbir kaynakta gecmis veri bulunamadigindan sistem disi birakildi).
DOVIZCOM_PAGES = {
    "PLATIN_TRY":   "https://altin.doviz.com/gram-platin",
}

def _fetch_dovizcom_gram_fiyat(url: str) -> float:
    """doviz.com'un tekrar eden cumle kalibini hedefler:
    '...fiyatı, anlık olarak 2.539,70 TL'ye karşılık gelmektedir.'"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return 0.0
        m = re.search(
            r'anl[ıi]k olarak[\s\S]{0,20}?([\d\.,]+)\s*TL',
            r.text, re.IGNORECASE
        )
        if m:
            return _safe_float(m.group(1))
    except Exception:
        pass
    return 0.0

def _fetch_platin_dovizcom() -> dict:
    result = {}
    val = _fetch_dovizcom_gram_fiyat(DOVIZCOM_PAGES["PLATIN_TRY"])
    if 500 < val < 20000:
        result["PLATIN_TRY"] = round(val, 4)
    return result


# v2.0.4.58: Truncgil Finans - ucretsiz, API anahtari gerektirmeyen, TEK
# istekte tum degerli madenleri (+ 60 doviz + onlarca altin sikke turu)
# yapilandirilmis JSON (Buying/Selling alanlari net) olarak veren kaynak.
# Bahri'nin gercek bir istekle dogruladigi yanit uzerinden test edildi -
# artik ALTIN/GUMUS/PLATIN icin BIRINCIL kaynak bu. Bigpara/
# doviz.com sentence-pattern yontemleri SADECE bu kaynak basarisiz olursa
# devreye giren yedek olarak kaliyor.
TRUNCGIL_URL = "https://finans.truncgil.com/v3/today.json"
TRUNCGIL_MADEN_KEYLERI = {
    "ALTIN_TRY":    "gram-altin",
    "GUMUS_TRY":    "gumus",
    "PLATIN_TRY":   "gram-platin",
    # v2.0.7.43 - GENISLEME (Bahri'nin talebi): Bahri'nin bizzat cektigi
    # gercek Truncgil yanitinda (13 Temmuz 2026) bu 9 ek altin/gumus
    # turunun de "Buying"/"Selling" alanlariyla yapilandirilmis, guvenilir
    # sekilde mevcut oldugu goruldu. "ons" haric tutuldu - USD bazli oldugu
    # icin sentetik cevrim gerektirir (Bahri'nin yasak ilkesi, bkz. MADEN
    # bolumu). "cumhuriyet-altini" (Truncgil'deki gercek anahtar - sondaki
    # "i" dikkat) - bizim mevcut CUMHURIYET_ALTIN ticker'imizden AYRI, o
    # farkli bir kaynaktan (canlidoviz) zaten geliyor; burada CATE_ALTIN
    # gibi cakismayi onlemek icin farkli bir ticker adi kullanildi.
    "GRAM_HAS_ALTIN":  "gram-has-altin",
    "AYAR14_ALTIN":    "14-ayar-altin",
    "AYAR18_ALTIN":    "18-ayar-altin",
    "BILEZIK22_ALTIN": "22-ayar-bilezik",
    "IKIBUCUK_ALTIN":  "ikibucuk-altin",
    "BESLI_ALTIN":     "besli-altin",
    "GREMSE_ALTIN":    "gremse-altin",
    "RESAT_ALTIN":     "resat-altin",
    "HAMIT_ALTIN":     "hamit-altin",
}

# v2.0.7.43 - Truncgil'in ayni yanitinda "Type":"Currency" ile isaretli
# 63 doviz kodu da var. Sadece 12'sini (USD/EUR/GBP/JPY/CHF/AUD/CAD/NZD/
# NOK/SEK/DKK/CNY) kullaniyorduk. Kalan ~51'i de guvenilir tek istekte
# (ayni Truncgil cagrisi) mevcut - MADEN'deki gibi BIRINCIL fiyat kaynagi
# burasi olacak; RSI/momentum icin yfinance best-effort denenir (bulunamazsa
# MADEN'deki Bigpara-kaynakli varliklar gibi notr RSI=50/Ret1M=0 ile kalir -
# bu bir hata degil, "gercek fiyat var ama teknik gostergeler icin
# yeterli/guvenilir gecmis veri yok" durumudur).
TRUNCGIL_DOVIZ_KODLARI = [
    "RUB", "AED", "KWD", "ZAR", "BHD", "LYD", "SAR", "IQD", "ILS", "INR",
    "MXN", "HUF", "BRL", "IDR", "CZK", "PLN", "RON", "ARS", "ALL", "AZN",
    "BAM", "CLP", "COP", "CRC", "DZD", "EGP", "HKD", "ISK", "KRW", "KZT",
    "LBP", "LKR", "MAD", "MDL", "MKD", "MYR", "OMR", "PEN", "PHP", "PKR",
    "QAR", "RSD", "SGD", "SYP", "THB", "TWD", "UAH", "UYU", "GEL", "TND",
    "BGN",
]

def _safe_float_tr(s) -> float:
    """Truncgil'in TR bicimli sayi metnini float'a cevirir.
    '6.281,55' -> 6281.55"""
    if not s:
        return 0.0
    try:
        s = str(s).strip()
        s = s.replace(".", "").replace(",", ".")
        return float(s)
    except Exception:
        return 0.0


def _usd_bazli_mi(s) -> bool:
    """v2.0.7.44 - Bahri'nin acik talimati: Truncgil yanitinda bazi
    alanlar (orn. 'ons': '$4.000,76') USD bazlidir - basindaki '$' isareti
    bunu gosterir. Boyle bir deger TL degilmis gibi sisteme MONTE
    EDILEMEZ (sentetik USD->TL cevrimi Bahri'nin kirmizi cizgisi).
    Onceden _safe_float_tr bu '$' isaretini sessizce kirpip sayiyi TL
    gibi kabul ediyordu - bu KRITIK bir hataydi, artik acikca reddedilir."""
    return isinstance(s, str) and s.strip().startswith("$")


def fetch_truncgil_maden() -> dict:
    """Truncgil'den madenleri (artik 13 tur - 4 ana + 9 yeni sikke/ayar)
    TEK istekte ceker. Basarisiz olursa bos dict doner (cagiran taraf
    Bigpara/doviz.com yedegine duser)."""
    try:
        r = requests.get(TRUNCGIL_URL, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return {}
        data = r.json()
        result = {}
        for ticker, key in TRUNCGIL_MADEN_KEYLERI.items():
            if key in data and isinstance(data[key], dict):
                _ham = data[key].get("Selling")
                if _usd_bazli_mi(_ham):
                    print(f"  [Truncgil] UYARI: {ticker} ({key}) USD bazli "
                          f"donuyor ('{_ham}') - sentetik cevrim yasak, ATLANDI.")
                    continue
                satis = _safe_float_tr(_ham)
                if satis > 0:
                    result[ticker] = round(satis, 4)
        return result
    except Exception as e:
        print(f"  [Truncgil] Maden cekimi basarisiz: {type(e).__name__}: {e}")
        return {}


def fetch_truncgil_doviz() -> dict:
    """v2.0.7.43 - Truncgil'in AYNI yanitindaki "Type":"Currency" ile
    isaretli ~51 EK doviz kodunu (RUB, AED, KWD, ZAR, ... vb.) tek istekte
    ceker. Anahtar = doviz kodu (orn. "RUB"), deger = 1 birimin TL satis
    fiyati. Basarisiz olursa bos dict doner - cagiran taraf o kodlari
    sessizce atlar, mevcut 12 ana doviz etkilenmez.
    v2.0.7.44 - USD-bazli donen degerler (bkz. _usd_bazli_mi) acikca
    reddedilir, sisteme hic girmez."""
    try:
        r = requests.get(TRUNCGIL_URL, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return {}
        data = r.json()
        result = {}
        for kod in TRUNCGIL_DOVIZ_KODLARI:
            entry = data.get(kod)
            if isinstance(entry, dict) and entry.get("Type") == "Currency":
                _ham = entry.get("Selling")
                if _usd_bazli_mi(_ham):
                    print(f"  [Truncgil] UYARI: {kod} USD bazli donuyor "
                          f"('{_ham}') - sentetik cevrim yasak, ATLANDI.")
                    continue
                satis = _safe_float_tr(_ham)
                if satis > 0:
                    result[kod] = round(satis, 6)
        return result
    except Exception as e:
        print(f"  [Truncgil] Doviz cekimi basarisiz: {type(e).__name__}: {e}")
        return {}


def fetch_truncgil_usdtry() -> float:
    """Truncgil'den USD/TRY satis kurunu ceker (kripto TL cevrimi vb. icin
    gerektiginde kullanilabilir, yfinance'e alternatif/yedek)."""
    try:
        r = requests.get(TRUNCGIL_URL, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return 0.0
        data = r.json()
        if "USD" in data:
            return _safe_float_tr(data["USD"].get("Selling"))
    except Exception:
        pass
    return 0.0


def fetch_all_bigpara(force_refresh: bool = False, usdtry: float = 38.0) -> dict:
    """
    Truncgil (birincil, tum 4 maden tek istekte) + Bigpara/doviz.com
    (yedek, sadece Truncgil'in getiremedigi icin) + kripto TL fiyatlarini
    ceker.
    Returns: {"ALTIN_TRY": 6250.5, "BTC": 3800000.0, ...}
    """
    if not force_refresh:
        cached = _read_cache()
        if cached:
            return cached

    print("  [Truncgil/Bigpara] Maden ve kripto TL fiyatlari cekiliyor...")
    result = {}

    truncgil_maden = fetch_truncgil_maden()
    result.update(truncgil_maden)
    if truncgil_maden:
        print(f"  [Truncgil] {len(truncgil_maden)} maden fiyati alindi (birincil): {list(truncgil_maden.keys())}")

    _eksik = [t for t in ("ALTIN_TRY", "GUMUS_TRY") if t not in result]
    if _eksik:
        maden = _fetch_maden_bigpara()
        for t in _eksik:
            if t in maden:
                result[t] = maden[t]
                print(f"  [Bigpara] {t}: yedek kaynaktan alindi")

    _eksik2 = [t for t in ("PLATIN_TRY",) if t not in result]
    if _eksik2:
        platin = _fetch_platin_dovizcom()
        for t in _eksik2:
            if t in platin:
                result[t] = platin[t]
                print(f"  [doviz.com] {t}: yedek kaynaktan alindi")

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
