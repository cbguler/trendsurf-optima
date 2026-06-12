"""
tcmb_client.py — TrendSurf Optima
TCMB döviz kurlarını iki kademeli kaynaktan çeker.

Kademe 1: TCMB EVDS API (günlük resmi kur, JSON)
Kademe 2: TCMB Bugünkü Kurlar XML (gerçek zamanlı, API key gerektirmez)
Cache: 1 saat
"""
import os, json, time
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "halka_arz_cache", "tcmb_kurlar.json")
CACHE_TTL  = 3600  # 1 saat

# TCMB EVDS API key — email_config.json veya sabit
EVDS_KEY_FILE = os.path.join(BASE_DIR, "email_config.json")
EVDS_API_KEY  = ""  # email_config.json dosyasından okunur

# EVDS seri kodları: TRY karşılığı alış kurları
EVDS_SERIES = {
    "USDTRY": "TP.DK.USD.A",
    "EURTRY": "TP.DK.EUR.A",
    "GBPTRY": "TP.DK.GBP.A",
    "JPYTRY": "TP.DK.JPY.A",
    "CHFTRY": "TP.DK.CHF.A",
    "AUDTRY": "TP.DK.AUD.A",
    "CADTRY": "TP.DK.CAD.A",
    "SEKTRY": "TP.DK.SEK.A",
    "NOKTRY": "TP.DK.NOK.A",
    "DKKTRY": "TP.DK.DKK.A",
    "CNYTRY": "TP.DK.CNY.A",
    "NZDTRY": "TP.DK.NZD.A",
}

# TCMB XML'deki Kod → ticker eşlemesi
XML_CODE_MAP = {
    "USD": "USDTRY", "EUR": "EURTRY", "GBP": "GBPTRY",
    "JPY": "JPYTRY", "CHF": "CHFTRY", "AUD": "AUDTRY",
    "CAD": "CADTRY", "SEK": "SEKTRY", "NOK": "NOKTRY",
    "DKK": "DKKTRY", "CNY": "CNYTRY", "NZD": "NZDTRY",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# ── Cache ─────────────────────────────────────────────────────────────────────

def _read_cache() -> Optional[dict]:
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
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


# ── Kademe 1: TCMB EVDS API ──────────────────────────────────────────────────

def _fetch_evds() -> dict:
    """
    TCMB EVDS API'den son iş günü döviz kurlarını çeker.
    Döner: {"USDTRY": 32.50, "EURTRY": 35.20, ...}
    """
    try:
        import requests
        # API key'i config dosyasından da okuyabilir
        api_key = EVDS_API_KEY
        try:
            with open(EVDS_KEY_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("tcmb_key"):
                    api_key = cfg["tcmb_key"]
        except Exception:
            pass

        series_str = "-".join(EVDS_SERIES.values())
        end_date   = datetime.now().strftime("%d-%m-%Y")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%d-%m-%Y")

        url = (
            f"https://evds2.tcmb.gov.tr/service/evds/"
            f"series={series_str}"
            f"&startDate={start_date}&endDate={end_date}"
            f"&type=json&key={api_key}"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return {}

        # Bazı durumlarda EVDS HTML veya boş yanıt dönebilir
        if not r.text.strip().startswith("{") and not r.text.strip().startswith("["):
            return {}
        data = r.json()
        items = data.get("items", data.get("data", []))
        if not items:
            return {}

        # Son satırı al (en güncel)
        last = items[-1]
        result = {}
        reverse_map = {v: k for k, v in EVDS_SERIES.items()}
        for series_code, ticker in reverse_map.items():
            val = last.get(series_code)
            if val and str(val).strip() not in ("", "None", "ND"):
                try:
                    result[ticker] = float(str(val).replace(",", "."))
                except Exception:
                    pass

        print(f"  [TCMB EVDS] {len(result)} kur alındı.")
        return result

    except Exception as e:
        print(f"  [TCMB EVDS] Hata: {e}")
        return {}


# ── Kademe 2: TCMB XML ───────────────────────────────────────────────────────

def _fetch_tcmb_xml() -> dict:
    """
    TCMB'nin bugünkü kurlar XML'inden döviz çeker. API key gerektirmez.
    URL: https://www.tcmb.gov.tr/kurlar/today.xml
    """
    try:
        import requests
        import xml.etree.ElementTree as ET

        r = requests.get(
            "https://www.tcmb.gov.tr/kurlar/today.xml",
            headers=HEADERS, timeout=15
        )
        if r.status_code != 200:
            return {}

        root = ET.fromstring(r.content)
        result = {}

        for currency in root.findall("Currency"):
            kod = currency.get("Kod", "")
            ticker = XML_CODE_MAP.get(kod)
            if not ticker:
                continue

            # Önce ForexBuying (döviz alış), yoksa BanknoteBuying
            alis = (
                currency.findtext("ForexBuying") or
                currency.findtext("BanknoteBuying") or ""
            ).strip()

            if alis and alis not in ("", "None"):
                try:
                    val = float(alis.replace(",", "."))
                    # JPY ve bazı kurlar 100 birim üzerinden verilir
                    if kod == "JPY":
                        val = val / 100.0
                    result[ticker] = round(val, 6)
                except Exception:
                    pass

        print(f"  [TCMB XML] {len(result)} kur alındı.")
        return result

    except Exception as e:
        print(f"  [TCMB XML] Hata: {e}")
        return {}


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def fetch_doviz_rates(force_refresh: bool = False) -> dict:
    """
    Döviz kurlarını döner. {"USDTRY": 32.50, "EURTRY": 35.20, ...}
    Kademe 1: EVDS API → Kademe 2: TCMB XML → Kademe 3: Cache
    """
    if not force_refresh:
        cached = _read_cache()
        if cached:
            return cached

    # Kademe 1: EVDS
    rates = _fetch_evds()

    # Kademe 2: XML (EVDS başarısızsa veya eksikse)
    if len(rates) < 6:
        xml_rates = _fetch_tcmb_xml()
        # Eksik kurları XML'den tamamla
        for ticker, val in xml_rates.items():
            if ticker not in rates:
                rates[ticker] = val

    if rates:
        rates["_kaynak"] = "TCMB EVDS" if len(rates) > 6 else "TCMB XML"
        rates["_tarih"]  = datetime.now().strftime("%d.%m.%Y %H:%M")
        _write_cache(rates)

    return rates


def enrich_worker_doviz(all_rows: list, force_refresh: bool = False) -> list:
    """
    worker.py'deki döviz satırlarını TCMB verileriyle günceller.
    all_rows: build() içindeki tüm satır listesi
    Döner: USDTRY, EURTRY vb. satırlarının Son_Fiyat'ı TCMB ile güncellenmiş liste
    """
    rates = fetch_doviz_rates(force_refresh)
    if not rates:
        return all_rows

    for row in all_rows:
        ticker = row.get("Ticker", "")
        if ticker in rates and row.get("Kategori") == "DOVIZ":
            old_price = row.get("Son_Fiyat", 0)
            new_price = rates[ticker]
            if new_price > 0:
                row["Son_Fiyat"] = new_price
                row["_tcmb_guncellendi"] = True

    return all_rows


if __name__ == "__main__":
    print("TCMB döviz kurları test:")
    rates = fetch_doviz_rates(force_refresh=True)
    for k, v in rates.items():
        if not k.startswith("_"):
            print(f"  {k}: {v}")
    print(f"\nKaynak: {rates.get('_kaynak','?')} | Tarih: {rates.get('_tarih','?')}")
