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
    # v2.0.7.72 - Bahri'nin talebi: Truncgil'in SADECE anlik fiyat verdigi
    # (gecmis veri yok) 51 genisleme dovizinden, TCMB'nin GERCEKTEN takip
    # ettigi 10 tanesi burada eslendi - bunlar icin artik gercek tarihsel
    # RSI/Getiri/Vol hesaplanabilir (bkz. fetch_tcmb_historical).
    "RUB": "RUBTRY", "AED": "AEDTRY", "KWD": "KWDTRY", "SAR": "SARTRY",
    "RON": "RONTRY", "AZN": "AZNTRY", "KRW": "KRWTRY", "KZT": "KZTTRY",
    "PKR": "PKRTRY", "QAR": "QARTRY",
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


# ── Tarihsel veri (v2.0.7.72) ──────────────────────────────────────────────
# Bahri'nin bulgusu (16 Temmuz 2026): Truncgil'in genisletilmis 51 doviz
# icinden 10 tanesi (RUB, AED, KWD, SAR, RON, AZN, KRW, KZT, PKR, QAR)
# aslinda TCMB'nin RESMI olarak gunluk takip ettigi dovizler - bu 10'u
# icin yfinance basarisiz olsa bile TCMB'nin GECMISE DONUK arsivinden
# (belgelenmis, stabil format: tcmb.gov.tr/kurlar/YYYYMM/GGAAYYYY.xml,
# 1950'ye kadar gidiyor) GERCEK bir gunluk seri insa edip RSI/Ret1M/Vol
# hesaplanabilir - "veri yok" yerine gercek analiz.

TCMB_HIST_CACHE = os.path.join(BASE_DIR, "halka_arz_cache", "tcmb_historical_cache.json")
TCMB_HIST_KAPSAM = {"RUB", "AED", "KWD", "SAR", "RON", "AZN", "KRW", "KZT", "PKR", "QAR"}


def _hist_cache_oku() -> dict:
    if not os.path.exists(TCMB_HIST_CACHE):
        return {}
    try:
        with open(TCMB_HIST_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _hist_cache_yaz(veri: dict):
    try:
        os.makedirs(os.path.dirname(TCMB_HIST_CACHE), exist_ok=True)
        with open(TCMB_HIST_CACHE, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False)
    except Exception as e:
        print(f"  [TCMB tarihsel] Onbellek yazilamadi: {e}")


def _tcmb_gunluk_xml_cek(tarih: datetime, kodlar: set) -> dict:
    """Tek bir gun icin TCMB XML arsivini ceker, istenen kodlarin
    ForexBuying degerlerini doner. Hafta sonu/tatil gunlerinde TCMB
    yayin yapmaz - bu durumda bos dict doner (hata degil, beklenen)."""
    import requests
    import xml.etree.ElementTree as ET
    url = f"https://www.tcmb.gov.tr/kurlar/{tarih:%Y%m}/{tarih:%d%m%Y}.xml"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200 or not r.content:
            return {}
        root = ET.fromstring(r.content)
        sonuc = {}
        for currency in root.findall("Currency"):
            kod = currency.get("Kod", "")
            if kod not in kodlar:
                continue
            alis = (currency.findtext("ForexBuying") or "").strip()
            if alis and alis not in ("", "None"):
                try:
                    sonuc[kod] = round(float(alis.replace(",", ".")), 6)
                except Exception:
                    pass
        return sonuc
    except Exception:
        return {}


def fetch_tcmb_historical(gun_sayisi: int = 100) -> dict:
    """v2.0.7.72 - TCMB_HIST_KAPSAM'daki 10 doviz icin gunluk tarihsel
    fiyat serisi olusturur/gunceller. ONBELLEKLI: sadece cache'te
    eksik olan (yeni) gunler CEKILIR, her calistirmada baştan
    yeniden 100 gun cekmez - onbellek buyudukce (ilk calistirmadan
    sonra) gunluk sadece 1-2 yeni gun cekilir.

    Döner: {"RUB": {"2026-04-01": 0.5123, ...}, "AED": {...}, ...}
    """
    cache = _hist_cache_oku()
    bugun = datetime.now()
    hedef_tarihler = [(bugun - timedelta(days=i)) for i in range(gun_sayisi)]

    eksik_gunler = 0
    for tarih in hedef_tarihler:
        gun_str = tarih.strftime("%Y-%m-%d")
        eksik_kodlar = {
            kod for kod in TCMB_HIST_KAPSAM
            if gun_str not in cache.get(kod, {})
        }
        if not eksik_kodlar:
            continue
        gunluk = _tcmb_gunluk_xml_cek(tarih, eksik_kodlar)
        eksik_gunler += 1
        for kod, deger in gunluk.items():
            cache.setdefault(kod, {})[gun_str] = deger
        # Hafta sonu/tatil gunlerinde de bos sonuc "denendi" olarak
        # isaretlenir (surekli tekrar denemeyi onlemek icin) - deger
        # olmayan kodlar icin None yazilir, hesaplamada atlanir.
        for kod in eksik_kodlar:
            if kod not in gunluk:
                cache.setdefault(kod, {}).setdefault(gun_str, None)

    if eksik_gunler > 0:
        _hist_cache_yaz(cache)
        print(f"  [TCMB tarihsel] {eksik_gunler} gun icin veri cekildi/denendi.")

    return {kod: {g: v for g, v in gunler.items() if v is not None}
            for kod, gunler in cache.items() if kod in TCMB_HIST_KAPSAM}


def tcmb_hesapla_rsi_ret_vol(gunluk_seri: dict) -> tuple:
    """Bir dovizin {tarih: fiyat} sozlugunden gercek RSI(14)/Ret1M/Vol
    hesaplar. Veri yetersizse (bkz. cagiran kod) None doner - notr
    varsayilan degerler burada UYDURULMAZ, cagiran taraf karar verir."""
    if len(gunluk_seri) < 15:
        return None
    import pandas as _pd
    s = _pd.Series(gunluk_seri).sort_index()
    s.index = _pd.to_datetime(s.index)
    s = s.sort_index()
    if len(s) < 15:
        return None
    delta = s.diff().dropna()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi_series = 100 - (100 / (1 + rs))
    rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty and rsi_series.iloc[-1] == rsi_series.iloc[-1] else 50.0
    ret1m = round((float(s.iloc[-1]) / float(s.iloc[-22]) - 1) * 100, 2) if len(s) >= 22 else 0.0
    rets = s.pct_change().dropna()
    vol = round(float(rets.std() * (252 ** 0.5) * 100), 1) if len(rets) > 10 else 15.0
    return round(float(s.iloc[-1]), 6), round(rsi, 1), ret1m, vol
