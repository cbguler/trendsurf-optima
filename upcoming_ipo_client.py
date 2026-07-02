"""
upcoming_ipo_client.py — TrendSurf Optima v2.0.4
Yaklasan Halka Arzlar (henuz borsada islem gormeyen, izahname surecindeki
sirketler) icin KAP "Bildirim Sorgulama" sonuclarini ceker.

Kaynak: https://www.kap.org.tr (Kamuyu Aydinlatma Platformu) — resmi, kamuya
acik SPK/Borsa Istanbul duzenleyici platformu.

2 Temmuz 2026: Gercek KAP sonuc sayfasinin HTML kaynagi (view-source) manuel
incelendi ve JSON veri yapisi DOGRULANDI. Next.js React Server Components
(RSC) mimarisi kullanan sayfa, veriyi <script>self.__next_f.push([1,"..."])
</script> icinde escape edilmis JSON string olarak gomuyor:

  "data":[{"disclosureBasic":{"publishDate":"03.06.2026 19:08:18",
  "disclosureIndex":1612738,"stockCode":"SEK, SKBNK","companyTitle":
  "ŞEKERBANK T.A.Ş.","title":"İzahname (SPK Onayına Sunulan)","summary":
  "Bedelli Sermaye Artırımına İlişkin...","attachmentCount":1,...}}, ...]

Bu yuzden basit bir `requests.get()` (JS calistirmaya, Selenium'a, RSC
header'larina GEREK YOK) + regex ile "data":[...] blogunu cikarip
escape'i geri alarak (\\" -> ") json.loads() ile parse ediliyor.
Bu yontem 2 Temmuz 2026'da gercek HTML uzerinde test edilip dogrulandi.

ONEMLI AYRIM: KAP'taki "Izahname (SPK Onayina Sunulan)" kategorisi hem YENI
halka arz adaylarini hem de MEVCUT borsada islem goren sirketlerin sermaye
artirimi izahnamelerini ayni kategoride listeler (orn. SEKERBANK, TEB Yatirim
gibi zaten BIST'te olan sirketler de bu listede cikar). Bu yuzden sonuclar
worker.py'deki BIST_TICKERS (771 hisse) listesiyle karsilastirilir:
  - Kod zaten BIST_TICKERS'ta VARSA -> mevcut sirket, sermaye artirimi, ELENIR
  - Kod BIST_TICKERS'ta YOKSA -> yeni halka arz adayi, GOSTERILIR

Kademeli veri cekme:
  Kademe 1 — KAP HTML fetch + RSC-gomulu JSON regex/parse (dogrulanmis yontem)
  Kademe 2 — Yerel cache (son basarili cekim, en fazla 12 saat eski)
  Kademe 3 — Bos liste (hata durumunda worker.py/app.py CRASH ETMEZ)
"""
import os, json, time, re
from typing import Optional
import pandas as pd

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR  = os.path.join(BASE_DIR, "upcoming_ipo_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "upcoming_ipo.json")
CACHE_TTL  = 3600 * 12  # 12 saat — halka arz takvimi gun icinde sik degismez

KAP_SEARCH_URL = "https://www.kap.org.tr/tr/bildirim-sorgu-sonuc"
KAP_SEARCH_PARAMS = {
    "srcbar": "Y",
    "cmp": "Y",
    "cat": "4",
    "s": "4028328d5988e2630159d9aebd742fd4",  # "Izahname (SPK Onayina Sunulan)" konu ID'si
    "st": "İzahname (SPK Onayına Sunulan)",
    "kw": "izahname",
    "slf": "ALL",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu",
}

# KAP bildirim detay sayfasi (izahname PDF eki buradan gorulebilir)
KAP_DETAIL_URL = "https://www.kap.org.tr/tr/Bildirim/{disclosure_index}"


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


# NOT: v2.0.4 ilk tasariminda BIST_TICKERS ile karsilastirma denendi ama
# guvenilmez cikti (bkz. fetch_upcoming_ipos icindeki aciklama). Su an
# filtreleme sadece KAP'in "summary" metnindeki terminolojiye dayaniyor.


# ── KAP'tan cekim ve JSON cikarma (2 Temmuz 2026'da dogrulanan yontem) ────────

def _fetch_kap_html() -> Optional[str]:
    try:
        import requests
        r = requests.get(KAP_SEARCH_URL, params=KAP_SEARCH_PARAMS,
                          headers=HEADERS, timeout=20)
        if r.status_code == 200 and len(r.text) > 1000:
            r.encoding = "utf-8"
            print(f"[upcoming-ipo] KAP HTML yanit alindi: {len(r.text)} karakter")
            return r.text
        print(f"[upcoming-ipo] KAP HTTP durumu: {r.status_code}, "
              f"uzunluk: {len(r.text) if r.text else 0}")
    except Exception as e:
        print(f"[upcoming-ipo] KAP fetch hatasi: {e}")
    return None


def _extract_disclosure_json(html_text: str) -> list:
    """
    HTML icindeki self.__next_f.push([1,"...\"data\":[{...}]...")
    RSC bloğundan "data":[...] JSON dizisini cikarir.

    Yontem: "data":[ ile SERVER_BASE_URL arasindaki escape edilmis JSON'u
    bulup ters egik cizgi escape'ini geri alarak parse eder.
    (2 Temmuz 2026'da gercek HTML uzerinde dogrulandi.)
    """
    try:
        # Once escape'i geri al (tum metin uzerinde - guvenli, HTML disinda
        # baska \\" kalibi olma ihtimali cok dusuk bu baglamda)
        unescaped = html_text.replace('\\"', '"').replace('\\\\', '\\')

        m = re.search(r'"data":(\[\{.*?"fundCode":(?:null|"[^"]*")\}\}\])',
                       unescaped)
        if not m:
            # Alternatif: SERVER_BASE_URL sinirlayicisiyla dene
            m = re.search(r'"data":(\[\{.*?\}\])\s*,\s*"SERVER_BASE_URL"',
                           unescaped)
        if not m:
            print("[upcoming-ipo] 'data' JSON blogu bulunamadi (regex eslesmedi)")
            return []

        parsed = json.loads(m.group(1))
        print(f"[upcoming-ipo] JSON parse basarili: {len(parsed)} kayit")
        return parsed

    except json.JSONDecodeError as e:
        print(f"[upcoming-ipo] JSON decode hatasi: {e}")
        return []
    except Exception as e:
        print(f"[upcoming-ipo] Parse hatasi: {e}")
        return []


# ── Ana fonksiyon ──────────────────────────────────────────────────────────────

def fetch_upcoming_ipos(force_refresh: bool = False) -> pd.DataFrame:
    """
    Yaklasan halka arzlari (henuz BIST evreninde olmayan, izahname surecindeki
    sirketleri) DataFrame olarak dondurur.

    Kolonlar: Tarih, Kod, Sirket, Konu, Ozet, Durum, Detay_URL
    Bos DataFrame donebilir (veri yoksa veya hepsi mevcut sirket ise) — bu
    HATA DEGILDIR, "su an yeni halka arz yok" olarak yorumlanmalidir.
    """
    if not force_refresh:
        cached = _read_cache()
        if cached is not None:
            print(f"[upcoming-ipo] Cache kullanildi: {len(cached)} satir")
            return pd.DataFrame(cached)

    html_text = _fetch_kap_html()
    if not html_text:
        print("[upcoming-ipo] Canli cekim basarisiz — eski cache/bos donuluyor")
        cached = _read_cache()
        if cached is not None:
            return pd.DataFrame(cached)
        return pd.DataFrame(columns=["Tarih","Kod","Sirket","Konu","Ozet","Durum","Detay_URL"])

    raw_records = _extract_disclosure_json(html_text)
    if not raw_records:
        print("[upcoming-ipo] Kayit bulunamadi — eski cache/bos donuluyor")
        cached = _read_cache()
        if cached is not None:
            return pd.DataFrame(cached)
        return pd.DataFrame(columns=["Tarih","Kod","Sirket","Konu","Ozet","Durum","Detay_URL"])

    # v2.0.4 duzeltme (2 Temmuz 2026): BIST_TICKERS ile karsilastirma GUVENILMEZ
    # cikti - ALNUS ve MRBAS gibi gercek yeni halka arz adaylari bile zaten
    # BIST_TICKERS'ta (hardcoded 771 liste onceden rezerve edilmis / guncel
    # olmayan girisler icerebiliyor). Bunun yerine KAP'in kendi "summary"
    # metnindeki terminolojiye bakiyoruz:
    #   "Sermaye Artırımı..." -> MEVCUT sirket, sermaye artirimi -> ELE
    #   "Halka Arz Başvurusu..." / "Pay Halka Arz..." -> YENI aday -> GOSTER
    new_rows = []
    for rec in raw_records:
        d = rec.get("disclosureBasic", {})
        kod_raw = d.get("stockCode", "") or ""
        summary = d.get("summary", "") or ""
        summary_lower = summary.lower()

        is_capital_increase = "sermaye artır" in summary_lower or "sermaye artir" in summary_lower
        is_new_ipo = "halka arz başvuru" in summary_lower or "halka arz basvuru" in summary_lower \
                     or "pay halka arz" in summary_lower

        if is_capital_increase and not is_new_ipo:
            continue  # mevcut sirket, sermaye artirimi - atla
        if not is_new_ipo:
            continue  # ne yeni IPO ne sermaye artirimi ifadesi net degil - guvenli tarafta kal, atla

        idx = d.get("disclosureIndex", "")
        new_rows.append({
            "Tarih":     d.get("publishDate", ""),
            "Kod":       kod_raw,
            "Sirket":    d.get("companyTitle", ""),
            "Konu":      d.get("title", ""),
            "Ozet":      summary,
            "Durum":     "Başvuru Yapıldı - SPK Onayı Bekleniyor",
            "Detay_URL": KAP_DETAIL_URL.format(disclosure_index=idx) if idx else "",
        })

    print(f"[upcoming-ipo] Toplam {len(raw_records)} bildirim, "
          f"{len(raw_records) - len(new_rows)} mevcut sirket/belirsiz elendi, "
          f"{len(new_rows)} yeni halka arz adayi kaldi")

    _write_cache(new_rows)
    return pd.DataFrame(new_rows)


def get_upcoming_ipo_summary() -> str:
    """Ozet metin — Halka Arz sayfasinda basliginda gosterilebilir."""
    df = fetch_upcoming_ipos()
    if df.empty:
        return "Su anda takip edilen yeni halka arz basvurusu bulunmuyor."
    return f"{len(df)} yeni halka arz basvurusu (SPK onay surecinde)"
