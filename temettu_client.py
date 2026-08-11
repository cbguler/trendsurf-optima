"""
temettu_client.py — TrendSurf Optima
BIST Temettü Endeksi (XTMTU) üyelerini KAP RSC endpoint'inden çeker,
yfinance'den temettü verilerini zenginleştirir.
Cache: 4 saat
"""
import os, json, time, re
from typing import Optional
import pandas as pd
from scoring import optima_score

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR  = os.path.join(BASE_DIR, "halka_arz_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "temettu.json")
CACHE_TTL  = 3600 * 4

KAP_RSC_URL    = "https://www.kap.org.tr/tr/Endeksler"
KAP_RSC_PARAMS = ["J6jXR9MGxbMRrb36", "i18u-12zDWg0QaGd", "xharz0001", "endeks001"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/x-component, */*",
    "RSC": "1",
    "Referer": "https://www.kap.org.tr/tr/Endeksler",
}

# ── Cache ─────────────────────────────────────────────────────────────────────

def _read_cache() -> Optional[list]:
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        if time.time() - os.path.getmtime(CACHE_FILE) > CACHE_TTL:
            return None
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _write_cache(rows: list):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ── KAP RSC çekimi ────────────────────────────────────────────────────────────

def _fetch_xtmtu_from_kap() -> list:
    """
    KAP RSC endpoint'inden XTMTU üyelerini çeker.
    XTMTU bloğu: "BIST TEMETT" anahtar kelimesinden sonra gelen stockCode listesi.
    """
    try:
        import requests
        text = None
        for rsc in KAP_RSC_PARAMS:
            try:
                r = requests.get(KAP_RSC_URL, params={"_rsc": rsc},
                                 headers=HEADERS, timeout=15)
                if r.status_code == 200 and "stockCode" in r.text:
                    r.encoding = "utf-8"
                    text = r.text
                    break
            except Exception:
                continue
        if not text:
            r = requests.get(KAP_RSC_URL, headers=HEADERS, timeout=15)
            if r.status_code == 200 and "stockCode" in r.text:
                text = r.text

        if not text:
            return []

        # XTMTU bloğunu bul — "BIST TEMETT" veya "XTMTU" veya "XTM25"
        xtmtu_pos = -1
        for kw in ["BIST TEMETT", "XTMTU", "XTM25", "TEMETT"]:
            idx = text.find(kw)
            if idx >= 0:
                xtmtu_pos = idx
                break

        if xtmtu_pos < 0:
            return []

        # XTMTU bloğundan sonraki ticker'ları parse et
        # Bir sonraki endeks bloğuna kadar al (güvenli sınır: 100 üye)
        text_after = text[xtmtu_pos:]

        # Bloğun bitişini bul — bir sonraki endeks kodu gelince dur
        # XTMTU'dan sonra farklı bir endeks kodu {"code":"XXXX"} gelir
        next_block = re.search(r'"code"\s*:\s*"X[A-Z0-9]{3,5}"\s*,\s*"content"', text_after[50:])
        if next_block:
            text_after = text_after[:next_block.start() + 50]

        pattern = r'"stockCode"\s*:\s*"([A-Z0-9]+)"\s*,\s*"title"\s*:\s*"([^"]+)"\s*,\s*"mkkMemberOid"\s*:\s*"([^"]+)"'
        matches = re.findall(pattern, text_after)
        if not matches:
            pattern2 = r'"stockCode"\s*:\s*"([A-Z0-9]+)"\s*,\s*"title"\s*:\s*"([^"]+)"'
            matches = [(m[0], m[1], "") for m in re.findall(pattern2, text_after)]

        rows = []
        seen = set()
        for match_item in matches[:100]:
            code  = match_item[0]
            title = match_item[1]
            mkk   = match_item[2] if len(match_item) > 2 else ""
            if code in seen or len(code) > 8:
                continue
            seen.add(code)
            kap_url = (f"https://www.kap.org.tr/tr/sirket-bilgileri/ozet/{mkk}"
                       if mkk else f"https://www.kap.org.tr/tr/Sirketler/{code}")
            rows.append({
                "Ticker":  code,
                "Şirket":  _fix_encoding(title),
                "KAP_URL": kap_url,
            })
        return rows

    except Exception:
        return []

def _fix_encoding(text: str) -> str:
    """KAP RSC yanitindaki bozuk Turkce karakterleri duzelt."""
    import re as _re
    if not text:
        return text

    # 1. latin-1 → UTF-8 dönüşümü dene (KAP'ın en yaygın encoding hatası)
    try:
        candidate = text.encode("latin-1").decode("utf-8")
        # Dönüşüm anlamlıysa (Türkçe harf içeriyorsa) kullan
        tr_chars = set("ğĞışİöÖüÜçÇşŞ")
        if any(c in candidate for c in tr_chars):
            text = candidate
    except Exception:
        pass

    # 2. Kalan multi-byte bozuklukları FIX_MAP ile düzelt
    FIX_MAP = {
        "Ä°": "İ", "ÄŸ": "ğ", "Äž": "Ğ", "Ä±": "ı",
        "Ã–": "Ö", "Ã¶": "ö", "Ãœ": "Ü", "Ã¼": "ü",
        "Ã‡": "Ç", "Ã§": "ç",
        "Åž": "Ş", "Å": "ş", "åž": "ş",
        "â€™": "'", "Â°": "°", "Â ": " ", "Â": "",
        # Unicode sahtesi — yanlış decode edilmiş karakterler
        "Ā°": "İ",    # Ā° → İ
        "Ā±": "ı",    # Ā± → ı
        "Ā": "ğ",    # Ā → ğ
        "Ā": "Ğ",    # Ā → Ğ
        "Ā": "Ü",    # Ā → Ü
        "Ā": "Ş",    # Ā → Ş
        "ā": "ı",
        "Ş": "Ş",
        "ş": "ş",
    }
    for bad, good in sorted(FIX_MAP.items(), key=lambda x: -len(x[0])):
        text = text.replace(bad, good)

    # 3. Tekil Ä → İ (son çare)
    text = _re.sub(r"Ä([A-ZÇĞİÖŞÜa-zçğışöşü])", lambda m: "Ğ" + m.group(1), text)
    text = text.replace("Ä", "İ")
    return text

# ── Temettü verisi çekimi ─────────────────────────────────────────────────────

def _fetch_dividend_data(ticker: str, cur_price: float) -> dict:
    """yfinance'den temettü verilerini çeker."""
    result = {
        "div_per_share": 0.0,
        "div_yield":     0.0,
        "ex_date":       "—",
        "frequency":     "—",
        "annual_div":    0.0,
    }
    try:
        import yfinance as yf
        import datetime
        info = yf.Ticker(f"{ticker}.IS").info

        div_rate  = float(info.get("dividendRate")  or 0)
        div_yield = float(info.get("dividendYield") or 0)
        ex_ts     = info.get("exDividendDate")
        freq      = info.get("dividendFrequency")

        if div_rate > 0:
            result["div_per_share"] = round(div_rate, 4)
            result["annual_div"]    = round(div_rate, 4)

        if 0 < div_yield <= 0.6:
            result["div_yield"] = round(div_yield * 100, 2)
        elif result["div_per_share"] > 0 and cur_price > 0:
            result["div_yield"] = round(result["div_per_share"] / cur_price * 100, 2)

        if ex_ts:
            try:
                result["ex_date"] = datetime.datetime.fromtimestamp(ex_ts).strftime("%d.%m.%Y")
            except Exception:
                pass

        result["frequency"] = {1: "Yıllık", 2: "Yarıyıllık", 4: "Çeyreklik"}.get(freq, "Yıllık")

    except Exception:
        pass
    return result

# ── CSV zenginleştirme ────────────────────────────────────────────────────────

def _enrich(rows: list) -> list:
    """v2.0.7.132 (Bahri'nin bulgusu, 10 Ağustos 2026 — TUPRS'ın Ana
    Sayfa'da 83,0, burada 68,0 görünmesi): eskiden Optima_Skor CSV'den
    (worker.py'nin son çalışmasındaki DONMUŞ değer) DOĞRUDAN kopyalanıyordu
    - Ana Sayfa ise BIST için seans içi canlı fiyat yenilemesinden sonra
    optima_score()'u YENİDEN HESAPLIYOR, bu yüzden iki sayı farklı
    çıkabiliyordu. Artık burada da RSI/Ret1M/Vol (+ PB/PE/DY varsa) CSV'den
    okunup scoring.py'deki AYNI optima_score() ile YENİDEN HESAPLANIYOR -
    en azından FORMÜL tutarlılığı garanti (ikisi de aynı girdilerden aynı
    sonucu üretir). NOT: bu hâlâ CSV'deki RSI/Ret1M'i kullanıyor (Ana
    Sayfa'nın yaptığı gibi TEMETTÜ sayfasına özel bir canlı fiyat yenilemesi
    EKLENMEDİ - "sistem çok ağırlaşmış" şikayeti nedeniyle ekstra bir ağ
    çağrısı eklemek yerine formül tutarlılığı önceliklendirildi)."""
    csv_path = os.path.join(BASE_DIR, "optimized_universe.csv")
    if not os.path.exists(csv_path):
        return rows
    try:
        df_uni = pd.read_csv(csv_path).set_index("Ticker")
        for r in rows:
            t = r["Ticker"]
            if t in df_uni.index:
                row = df_uni.loc[t]
                rsi   = float(row.get("RSI", 0) or 0)
                ret1m = float(row.get("Ret1M", 0) or 0)
                vol   = float(row.get("Vol", 30) or 30)
                pb = row.get("PB"); pe = row.get("PE"); dy = row.get("DY")
                has_fund = any(v is not None and str(v) != "nan" and float(v or 0) > 0
                              for v in (pb, pe, dy))
                r["Son_Fiyat"]   = float(row.get("Son_Fiyat", 0) or 0)
                r["RSI"]         = rsi
                r["Ret1M"]       = ret1m
                r["Optima_Skor"] = optima_score(
                    rsi, ret1m, vol=vol, has_fundamental=has_fund,
                    pb=pb, pe=pe, dy=dy)
            else:
                r.update({"Son_Fiyat": 0.0, "RSI": 0.0, "Ret1M": 0.0, "Optima_Skor": 0.0})
    except Exception:
        pass
    return rows

# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def fetch_temettu_list(force_refresh: bool = False) -> pd.DataFrame:
    """
    XTMTU üyelerini temettü verileriyle döner.
    Sütunlar: Ticker, Şirket, Son_Fiyat, RSI, Ret1M, Optima_Skor,
              div_per_share, div_yield, ex_date, frequency,
              Toplam_Getiri
    """
    if not force_refresh:
        cached = _read_cache()
        if cached:
            # v2.0.7.133 (Bahri'nin bulgusu, 10 Ağustos 2026 — TUPRS 63,0
            # vs 83,0, scoring.py birleştirmesinden SONRA bile devam etti):
            # kök neden formül değil, ÖNBELLEK TAZELİĞİ farkıydı - bu 4
            # saatlik önbellek Optima_Skor'u da (pahalı XTMTU/temettü
            # verisiyle birlikte) donduruyordu, Ana Sayfa/BIST ise
            # load_universe()'in 10 dakikalık önbelleğini kullanıyordu.
            # Çözüm: önbellekten dönerken bile Optima_Skor/RSI/Ret1M/
            # Son_Fiyat CSV'den YENİDEN okunup taze hesaplanıyor - bu ucuz
            # bir yerel disk okuması (ağ çağrısı DEĞİL), performansı
            # etkilemez. Sadece pahalı kısımlar (XTMTU üye listesi, yfinance
            # temettü verisi) 4 saat önbellekli kalıyor.
            cached = _enrich(cached)
            return pd.DataFrame(cached)

    # XTMTU üyelerini çek
    rows = _fetch_xtmtu_from_kap()
    if not rows:
        return pd.DataFrame()

    # CSV'den fiyat/skor ekle
    rows = _enrich(rows)

    # Temettü verisi — yfinance (paralel)
    print(f"  Temettü verisi çekiliyor ({len(rows)} hisse)...")
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _get_div(r):
        t = r["Ticker"]
        p = r.get("Son_Fiyat", 0)
        d = _fetch_dividend_data(t, p)
        r.update(d)
        # Toplam tahmini getiri = Optima Skor bazlı momentum + temettü verimi
        r["Toplam_Getiri"] = round(
            float(r.get("Ret1M", 0)) + float(r.get("div_yield", 0)), 2
        )
        return r

    enriched = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_get_div, r): r for r in rows}
        for fut in as_completed(futures):
            try:
                enriched.append(fut.result())
            except Exception:
                enriched.append(futures[fut])

    df = pd.DataFrame(enriched)

    # v2.0.7.16 - ONCEKI SIRALAMA HATASI (Bahri'nin 11 Temmuz geri bildirimi):
    # yfinance'in "exDividendDate" alani GELECEKTEKI degil, KAYITLARDAKI EN SON
    # BILINEN ex-temettu tarihini doner - sirket bu yil icin henuz yeni bir
    # dagitim aciklamadiysa bu tarih 1 yil kadar ESKI olabilir. Onceki kod
    # sadece "ascending=True" ile SAF KRONOLOJIK sirlardi - bu, eski bir tarihi
    # (kucuk sayisal deger) gelecekteki bir tarihten (buyuk deger) ONCE
    # gosteriyordu; yani 1 yil once gecmis bir ex-date, listenin TEPESINE
    # cikiyordu. Duzeltme: once GELECEK (bugun dahil) tarihler en yakindan en
    # uzaga, SONRA GECMIS tarihler en yeniden en eskiye, EN SONDA tarihsiz
    # kayitlar (verim'e gore azalan) - boylece "yakinda gelecek" ex-date'ler
    # gercekten en ustte cikar, cok eski gecmis kayitlar en altta kalir.
    from datetime import datetime as _dt_srt
    df["_ex_dt"] = pd.to_datetime(df["ex_date"], format="%d.%m.%Y", errors="coerce")
    _bugun = pd.Timestamp(_dt_srt.now().date())
    df["_grup"] = df["_ex_dt"].apply(
        lambda d: 2 if pd.isna(d) else (0 if d >= _bugun else 1))
    df["_sort_val"] = df["_ex_dt"].apply(lambda d: 0 if pd.isna(d) else d.value)
    # grup 0 (gelecek): kucukten buyuge (en yakin once). grup 1 (gecmis):
    # buyukten kucuge (en yeni gecmis once) -> isareti ters cevirip yine artan sirala.
    df["_sort_val2"] = df.apply(
        lambda r: r["_sort_val"] if r["_grup"] != 1 else -r["_sort_val"], axis=1)
    df = df.sort_values(["_grup", "_sort_val2", "div_yield"],
                        ascending=[True, True, False])
    # v2.0.7.17 - Gorsel netlik icin Durum etiketi (Bahri'nin talebi):
    # "Yaklasiyor" (bugun dahil gelecek), "Gecti" (gecmis ex-date, hala
    # referans/verim bilgisi olarak listede kalir), "—" (tarih bulunamadi).
    df["Durum"] = df["_grup"].map({0: "Yaklaşıyor", 1: "Geçti", 2: "—"})
    df = df.drop(columns=["_ex_dt", "_grup", "_sort_val", "_sort_val2"])
    df = df.reset_index(drop=True)

    _write_cache(df.to_dict("records"))
    return df
