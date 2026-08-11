"""
halka_arz_client.py — TrendSurf Optima
BIST Halka Arz (XHARZ) endeks üyelerini KAP RSC endpoint'inden çeker.

Kaynak: https://www.kap.org.tr/tr/Endeksler (Next.js RSC)
Fallback: Yerel Endeksler.xlsx
Cache: 4 saat
"""
import os, json, time, re, io
from typing import Optional
import pandas as pd
from scoring import optima_score

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR  = os.path.join(BASE_DIR, "halka_arz_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "halka_arz.json")
CACHE_TTL  = 3600 * 4

ENDEKSLER_FILE = os.path.join(BASE_DIR, "Endeksler.xlsx")

KAP_RSC_URL = "https://www.kap.org.tr/tr/Endeksler"
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

def _fetch_from_kap_rsc() -> list:
    """
    KAP'ın Next.js RSC endpoint'inden XHARZ üyelerini çeker.
    stockCode + title alanlarını parse eder.
    """
    try:
        import requests

        text = None
        # Bilinen _rsc parametrelerini dene
        for rsc in KAP_RSC_PARAMS:
            try:
                r = requests.get(
                    KAP_RSC_URL,
                    params={"_rsc": rsc},
                    headers=HEADERS,
                    timeout=15
                )
                if r.status_code == 200 and "stockCode" in r.text:
                    r.encoding = "utf-8"
                    text = r.text
                    break
            except Exception:
                continue

        # Parametre bulunamazsa parametresiz dene
        if not text:
            try:
                r = requests.get(KAP_RSC_URL, headers=HEADERS, timeout=15)
                if r.status_code == 200 and "stockCode" in r.text:
                    r.encoding = "utf-8"
                    text = r.text
            except Exception:
                pass

        if not text:
            return []

        # XHARZ bloğunu bul — "BIST HALKA ARZ" veya "XHARZ" geçtikten sonraki üyeleri al
        # Yapı: {"stockCode":"AAGYO","title":"AĞAOĞLU...","mkkMemberOid":"..."}
        # Tüm stockCode/title çiftlerini çek
        # stockCode + title + mkkMemberOid birlikte parse et
        pattern = r'"stockCode"\s*:\s*"([A-Z0-9]+)"\s*,\s*"title"\s*:\s*"([^"]+)"\s*,\s*"mkkMemberOid"\s*:\s*"([^"]+)"'
        all_matches = re.findall(pattern, text)
        # Eğer üçlü pattern tutmazsa ikili dene
        if not all_matches:
            pattern2 = r'"stockCode"\s*:\s*"([A-Z0-9]+)"\s*,\s*"title"\s*:\s*"([^"]+)"'
            all_matches = [(m[0], m[1], "") for m in re.findall(pattern2, text)]

        if not all_matches:
            return []

        # XHARZ bloğunu tespit et:
        # Metin içinde "HALKA ARZ" veya "XHARZ" geçen pozisyondan sonraki ticker'lar
        xharz_pos = -1
        for kw in ["HALKA ARZ", "XHARZ", "halka-arz"]:
            idx = text.find(kw)
            if idx >= 0:
                xharz_pos = idx
                break

        if xharz_pos >= 0:
            text_after = text[xharz_pos:]
            matches = re.findall(pattern, text_after)
            if not matches:
                matches = [(m[0], m[1], "") for m in re.findall(
                    r'"stockCode"\s*:\s*"([A-Z0-9]+)"\s*,\s*"title"\s*:\s*"([^"]+)"',
                    text_after)]
            matches = matches[:200]
        else:
            matches = all_matches[:200]

        rows = []
        seen = set()
        for match_item in matches:
            code  = match_item[0]
            title = match_item[1]
            mkk_id = match_item[2] if len(match_item) > 2 else ""
            if code in seen or len(code) > 8:
                continue
            seen.add(code)
            kap_url = (f"https://www.kap.org.tr/tr/sirket-bilgileri/ozet/{mkk_id}"
                       if mkk_id else f"https://www.kap.org.tr/tr/Sirketler/{code}")
            rows.append({
                "Şirket":         _fix_encoding(title if isinstance(title, str) else match_item[1]),
                "Ticker":         code,
                "Sektör":         "—",
                "Aracı_Kurum":    "—",
                "Fiyat_Araligi":  "—",
                "Başvuru_Başlangıç": "—",
                "Başvuru_Bitiş":  "—",
                "Borsa_Tarihi":   "—",
                "Bildirim_Tarihi": "—",
                "Durum":          "Endeks Üyesi",
                "KAP_URL":        kap_url,
                "Kaynak":         "KAP XHARZ",
                "Başlık":         "BIST Halka Arz Endeksi (XHARZ) Üyesi",
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


# ── Excel fallback ────────────────────────────────────────────────────────────

def _parse_xharz_from_excel(excel_bytes: bytes) -> list:
    try:
        df = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=0, header=None)
    except Exception:
        return []

    start_idx = None
    for i, row in df.iterrows():
        if "HALKA ARZ" in str(row.iloc[0]).upper():
            start_idx = i + 1
            break

    if start_idx is None:
        return []

    rows = []
    for i in range(start_idx, len(df)):
        row = df.iloc[i]
        kod = str(row.iloc[1]).strip()
        ad  = str(row.iloc[2]).strip() if len(row) > 2 else ""
        if kod in ("nan", "", "Kod"):
            if ad in ("nan", "", "Şirket Unvanı"):
                break
            continue
        if not kod or kod == "nan":
            break
        rows.append({
            "Şirket":         ad if ad != "nan" else kod,
            "Ticker":         kod,
            "Sektör":         "—",
            "Aracı_Kurum":    "—",
            "Fiyat_Araligi":  "—",
            "Başvuru_Başlangıç": "—",
            "Başvuru_Bitiş":  "—",
            "Borsa_Tarihi":   "—",
            "Bildirim_Tarihi": "—",
            "Durum":          "Endeks Üyesi",
            "KAP_URL":        f"https://www.kap.org.tr/tr/sirket-bilgileri/ozet/{kod}",
            "Kaynak":         "Endeksler.xlsx",
            "Başlık":         "BIST Halka Arz Endeksi (XHARZ) Üyesi",
        })
    return rows


# ── CSV zenginleştirme ────────────────────────────────────────────────────────

def _enrich_from_csv(rows: list, df_uni_hazir=None) -> list:
    """v2.0.7.138 (Bahri'nin bulgusu, 11 Ağustos 2026): Fırsat Radarı
    overlay eksikliği bulunup düzeltildi.

    v2.0.7.141 (Bahri'nin bulgusu — TUPRS BIST'te 68,0'a düşmüşken
    Temettü'de hâlâ 63,0 kalması): fallback yoldaki "CSV'den RSI/Ret1M
    okuyup scoring.py ile YENİDEN HESAPLA" yaklaşımı YANLIŞTI - worker.py
    CSV'ye yazarken scoring.py'nin temel formülüne EK bir "Hacim/Düşüş
    Düzeltmesi" uyguluyor, bu düzeltme scoring.py'de yok, yeniden
    hesaplamak HER ZAMAN worker.py'nin gerçek skorundan sapıyordu. Artık
    fallback yolu da (birincil df_uni_hazir yolu gibi) DOĞRUDAN
    KOPYALIYOR, yeniden hesaplamıyor - worker.py zaten TAM ve DOĞRU
    hesabı yapıyor."""
    if df_uni_hazir is not None and not df_uni_hazir.empty:
        try:
            _du = df_uni_hazir.set_index("Ticker")
            for r in rows:
                t = r["Ticker"]
                if t in _du.index:
                    row = _du.loc[t]
                    r["Son_Fiyat"]   = float(row.get("Son_Fiyat", 0) or 0)
                    r["RSI"]         = float(row.get("RSI", 0) or 0)
                    r["Ret1M"]       = float(row.get("Ret1M", 0) or 0)
                    _skor = row.get("Optima_Skor")
                    r["Optima_Skor"] = float(_skor) if (_skor is not None and _skor == _skor) else 0.0
                else:
                    r.update({"Son_Fiyat": 0.0, "RSI": 0.0, "Ret1M": 0.0, "Optima_Skor": 0.0})
        except Exception:
            pass
        return rows

    csv_path = os.path.join(BASE_DIR, "optimized_universe.csv")
    if not os.path.exists(csv_path):
        return rows
    try:
        df_uni = pd.read_csv(csv_path).set_index("Ticker")
        for r in rows:
            t = r["Ticker"]
            if t in df_uni.index:
                row = df_uni.loc[t]
                r["Son_Fiyat"]   = float(row.get("Son_Fiyat", 0) or 0)
                r["RSI"]         = float(row.get("RSI", 0) or 0)
                r["Ret1M"]       = float(row.get("Ret1M", 0) or 0)
                _skor = row.get("Optima_Skor")
                r["Optima_Skor"] = float(_skor) if (_skor is not None and _skor == _skor) else 0.0
            else:
                r.update({"Son_Fiyat": 0.0, "RSI": 0.0, "Ret1M": 0.0, "Optima_Skor": 0.0})
    except Exception:
        pass

    try:
        from db import get_intraday_overlay
        _rd_map = get_intraday_overlay(45)
        if _rd_map:
            for r in rows:
                _ov = _rd_map.get(r.get("Ticker"))
                if not _ov:
                    continue
                if _ov.get("fiyat") is not None:
                    r["Son_Fiyat"] = float(_ov["fiyat"])
                if _ov.get("rsi") is not None:
                    r["RSI"] = float(_ov["rsi"])
                if _ov.get("ret1m") is not None:
                    r["Ret1M"] = float(_ov["ret1m"])
                if _ov.get("skor") is not None:
                    r["Optima_Skor"] = float(_ov["skor"])
    except Exception:
        pass
    return rows


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def fetch_ipo_list(force_refresh: bool = False, df_uni_hazir=None) -> pd.DataFrame:
    """v2.0.7.138: df_uni_hazir - app.py'nin zaten yüklediği (Fırsat Radarı
    overlay'i dahil) df_uni verilirse, önbellekten dönerken bile
    Optima_Skor/RSI/Ret1M taze hesaplanır (bkz. _enrich_from_csv notu)."""
    if not force_refresh:
        cached = _read_cache()
        if cached:
            cached = _enrich_from_csv(cached, df_uni_hazir)
            return pd.DataFrame(cached)

    # Kademe 1: KAP RSC (canlı, otomatik)
    rows = _fetch_from_kap_rsc()

    # Kademe 2: Yerel Excel fallback
    if not rows and os.path.exists(ENDEKSLER_FILE):
        try:
            with open(ENDEKSLER_FILE, "rb") as f:
                rows = _parse_xharz_from_excel(f.read())
        except Exception:
            pass

    if not rows:
        return pd.DataFrame(columns=[
            "Şirket", "Ticker", "Durum", "KAP_URL", "Kaynak",
            "Son_Fiyat", "RSI", "Ret1M", "Optima_Skor"
        ])

    rows = _enrich_from_csv(rows, df_uni_hazir)
    df = pd.DataFrame(rows).reset_index(drop=True)
    _write_cache(df.to_dict("records"))
    return df


def get_ipo_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"toplam": 0, "aktif": 0, "yaklasan": 0, "tamamlanan": 0}
    return {
        "toplam":     len(df),
        "aktif":      0,
        "yaklasan":   0,
        "tamamlanan": 0,
    }

