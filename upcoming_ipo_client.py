"""
upcoming_ipo_client.py — TrendSurf Optima v2.0.6.4
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

v2.0.6.4 (10 Temmuz 2026): Supabase kalici katmani (ipo_valuations tablosu).
Sorun: Zorla Yenile ile hesaplanan arz fiyati/Graham/Carpan degerleri yalnizca
konteynerin YEREL dosyasina (upcoming_ipo_cache/*.json) yaziliyordu; Streamlit
Cloud yeniden baslayinca dosyalar repodan sifirlaniyor ve repodaki cache gece
worker'inin Actions ortaminda basarisiz olan cikarimi yuzunden null kaliyordu -
degerler her yeniden baslatmada kayboluyordu. Cozum: basarili (dolu) sonuclar
Supabase'e UPSERT edilir ve okumada yerel null alanlarin uzerine bindirilir.
Kurallar: (1) null ASLA dolu degeri ezmez (SQL'de COALESCE + alan bazli merge),
(2) Supabase erisilemezse davranis eskisiyle birebir ayni (fail-soft),
(3) yalnizca en az bir alani dolu kayitlar yazilir.
"""
import os, json, time, re
from typing import Optional
import pandas as pd

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR  = os.path.join(BASE_DIR, "upcoming_ipo_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "upcoming_ipo.json")
CACHE_TTL  = 3600 * 12  # 12 saat — halka arz takvimi gun icinde sik degismez

KAP_SEARCH_URL = "https://www.kap.org.tr/tr/bildirim-sorgu-sonuc"

# v2.0.4.1 (2 Temmuz 2026): İki asama takip ediliyor:
#   1) "SPK Onayına Sunulan"   -> basvuru yapildi, henuz onaylanmadi
#   2) "SPK Tarafından Onaylanan" -> onaylandi, talep toplama surecinde/yakinda
# (ISVEA, EKIM, GOLDA gibi sirketler 2. kategoride cikar - Bahri'nin
# 2 Temmuz 2026'da fark ettigi eksiklik.)
KAP_CATEGORIES = [
    {
        "key": "basvuru",
        "durum_label": "Başvuru Yapıldı SPK Onayı Bekleniyor",
        "params": {
            "srcbar": "Y", "cmp": "Y", "cat": "4",
            "s": "4028328d5988e2630159d9aebd742fd4",
            "st": "İzahname (SPK Onayına Sunulan)",
            "kw": "izahname", "slf": "ALL",
        },
    },
    {
        "key": "onaylandi",
        "durum_label": "Onaylandı Talep Toplanıyor Yakında",
        "params": {
            "srcbar": "Y", "cmp": "Y", "cat": "4",
            "s": "4028328d5988e2630159d9b261b72ffe",
            "st": "İzahname (SPK Tarafından Onaylanan)",
            "kw": "izahname", "slf": "ALL",
        },
    },
]

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

# v2.0.4.8 (4 Temmuz 2026): Fiyat Tespit Raporu PDF ekini indirip icinden
# arz fiyati + iskonto oranini otomatik cikaran Faz 2 entegrasyonu.
#
# KAP'in dahili (kimlik dogrulama gerektirmeyen, herkese acik) API'si:
#   1) attachment-detail -> bildirimin ek dosyalarinin objId'sini verir
#   2) file/download/{objId} -> PDF baytlarini Java byte[] serialization
#      ile SARMALANMIS olarak doner (ilk 2 byte: 0xAC 0xED). Gercek PDF'i
#      almak icin bu sarmalayici sokulmeli (_unwrap_java_pdf).
#
# Bu iki endpoint KAP'in resmi/ucretli "Veri Yayin Servisi" REST API'si
# DEGILDIR (o, sozlesme + API key gerektirir) - bunlar kap.org.tr web
# sitesinin kendisinin kullandigi, herkese acik dahili servislerdir.
KAP_ATTACHMENT_DETAIL_URL = "https://www.kap.org.tr/tr/api/notification/attachment-detail/{disclosure_index}"
KAP_FILE_DOWNLOAD_URL = "https://www.kap.org.tr/tr/api/file/download/{obj_id}"

# Fiyat Tespit Raporu sonuclari (arz fiyati/iskonto) ayri bir cache'te
# tutulur - bir bildirim ASLA degismeyecegi icin (yayinlanmis rapor sabit)
# bu cache SURESIZ gecerlidir, CACHE_TTL uygulanmaz.
FIYAT_TESPIT_SONUC_CACHE = os.path.join(CACHE_DIR, "fiyat_tespit_sonuclari.json")

# Fiyat Tespit Raporu'nun "Degerleme Ozeti / Sonuc" tablosu bazen erken
# (orn. ORZAX'ta 60 sayfalik raporun 8. sayfasi), bazen gec (orn. SOHO'da
# 64 sayfalik raporun 10. VE 66. sayfasi) gorulebiliyor. Tum raporu OCR'dan
# gecirmek (bazilari 60+ sayfa) GitHub Actions'ta pahali/yavas olacagindan,
# once ilk N sayfa, bulunamazsa son N sayfa denenir.
FIYAT_TESPIT_TARAMA_SAYFA_SAYISI = 15
# Bir calistirmada en fazla kac YENI rapor indirilip islensin (guvenlik
# siniri - ayni gun cok sayida yeni IPO bildirimi gelirse calisma suresi
# patlamasin diye).
FIYAT_TESPIT_MAX_YENI_ISLEME = 10
# v2.0.7.222 (Bahri'nin talebi, 31 Ağustos 2026 — "maliyetten ziyade
# işlemleri çok yavaşlatıyordu asıl mesele zamanın çok uzamasıydı"):
# v2.0.7.221'de orta sayfalara da OCR eklendi (Graham/Çarpan verisi
# çoğunlukla taranmış orta sayfalarda) - ama workflow'un 45 DAKİKALIK
# SERT ZAMAN AŞIMI sınırı var (`update_data.yml`), ve şu an TÜM
# bekleyen adaylar bu veriden yoksun, yani İLK çalıştırmada hepsi
# birden pahalı OCR'a girecek. Bu sabit, `FIYAT_TESPIT_MAX_YENI_ISLEME`
# ile AYNI kurulu desen - bir belgede en fazla kaç orta sayfa OCR
# edilsin (patolojik derecede uzun - 150+ sayfalık - belgelerde
# çalışma süresi patlamasın diye). Tipik belgeler (TERA örneğinde 83
# sayfa, ~53 orta sayfa) bu sınırın altında kalır, sorunsuz taranır.
ORTA_SAYFA_OCR_MAX_SAYFA = 40


# ── v2.0.6.4: Supabase kalici katmani (ipo_valuations) ───────────────────────
# Yayinlanmis bir Fiyat Tespit Raporu'nun icerigi degismez; bu yuzden bir kez
# dogru cikarilan deger kalicidir. Yerel JSON cache konteyner omruyle sinirli
# oldugundan dolu sonuclar Supabase'de saklanir. Baglanti/sorgu zaman sinirli
# (data_health_check v2.0.6.3 dersinden: Supabase arizasinda askida kalinmaz).

IPO_VALUATIONS_ALANLAR = ("arz_fiyati", "iskonto_orani", "tip",
                          "graham_degeri", "carpan_bazli_deger")

# Sayfa her aciliste Supabase'e gitmemek icin kisa omurlu modul ici memo.
_SUPABASE_MEMO = {"ts": 0.0, "data": None}
_SUPABASE_MEMO_TTL = 600  # 10 dk


def _supabase_conn():
    """Zaman sinirli Supabase baglantisi; kurulamazsa None (fail-soft).
    URL cozumu db.py._get_db_url ile ortak: once env SUPABASE_DB_URL
    (GitHub Actions), sonra Streamlit secrets (Streamlit Cloud)."""
    try:
        from db import _get_db_url
        url = _get_db_url()
    except Exception:
        url = os.environ.get("SUPABASE_DB_URL", "") or ""
    if not url:
        return None
    try:
        import psycopg2
        return psycopg2.connect(url, connect_timeout=10,
                                options="-c statement_timeout=15000")
    except Exception as e:
        print(f"[upcoming-ipo] Supabase baglantisi kurulamadi: {e}", flush=True)
        return None


def _supabase_sonuclari_oku(memo_kullan: bool = True) -> dict:
    """ipo_valuations -> {disclosure_index(str): {alan: deger}}.
    Hata durumunda bos dict (davranis Supabase'siz halle ayni kalir)."""
    if memo_kullan and _SUPABASE_MEMO["data"] is not None and \
            (time.time() - _SUPABASE_MEMO["ts"]) < _SUPABASE_MEMO_TTL:
        return _SUPABASE_MEMO["data"]
    conn = _supabase_conn()
    if conn is None:
        return _SUPABASE_MEMO["data"] or {}
    out = {}
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT disclosure_index, arz_fiyati, iskonto_orani, tip, "
            "graham_degeri, carpan_bazli_deger FROM ipo_valuations")
        for r in cur.fetchall():
            out[str(r[0])] = {
                "arz_fiyati":         float(r[1]) if r[1] is not None else None,
                "iskonto_orani":      float(r[2]) if r[2] is not None else None,
                "tip":                r[3],
                "graham_degeri":      float(r[4]) if r[4] is not None else None,
                "carpan_bazli_deger": float(r[5]) if r[5] is not None else None,
            }
        _SUPABASE_MEMO["data"] = out
        _SUPABASE_MEMO["ts"] = time.time()
    except Exception as e:
        print(f"[upcoming-ipo] Supabase ipo_valuations okunamadi: {e}", flush=True)
        return _SUPABASE_MEMO["data"] or {}
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return out


def _supabase_sonuclari_yaz(cache: dict):
    """En az bir alani dolu kayitlari UPSERT eder. COALESCE(EXCLUDED.alan,
    ipo_valuations.alan): yeni deger doluysa yazilir, null ise MEVCUT DEGER
    KORUNUR - null asla dolu degeri ezmez (kirmizi cizgi)."""
    rows = [(k,
             v.get("arz_fiyati"), v.get("iskonto_orani"), v.get("tip"),
             v.get("graham_degeri"), v.get("carpan_bazli_deger"))
            for k, v in cache.items()
            if isinstance(v, dict) and
            any(v.get(a) is not None for a in IPO_VALUATIONS_ALANLAR)]
    if not rows:
        return
    conn = _supabase_conn()
    if conn is None:
        return
    try:
        cur = conn.cursor()
        cur.executemany("""
            INSERT INTO ipo_valuations
              (disclosure_index, arz_fiyati, iskonto_orani, tip,
               graham_degeri, carpan_bazli_deger, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (disclosure_index) DO UPDATE SET
              arz_fiyati         = COALESCE(EXCLUDED.arz_fiyati,         ipo_valuations.arz_fiyati),
              iskonto_orani      = COALESCE(EXCLUDED.iskonto_orani,      ipo_valuations.iskonto_orani),
              tip                = COALESCE(EXCLUDED.tip,                ipo_valuations.tip),
              graham_degeri      = COALESCE(EXCLUDED.graham_degeri,      ipo_valuations.graham_degeri),
              carpan_bazli_deger = COALESCE(EXCLUDED.carpan_bazli_deger, ipo_valuations.carpan_bazli_deger),
              updated_at         = NOW()
        """, rows)
        conn.commit()
        # Memo'yu gecersiz kil - bir sonraki okuma taze veriyi alsin.
        _SUPABASE_MEMO["data"] = None
        print(f"[upcoming-ipo] Supabase ipo_valuations: {len(rows)} kayit "
              f"UPSERT edildi.", flush=True)
    except Exception as e:
        print(f"[upcoming-ipo] Supabase ipo_valuations yazilamadi: {e}", flush=True)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _url_disclosure_index(url) -> Optional[str]:
    """'https://www.kap.org.tr/tr/Bildirim/1624187' -> '1624187'."""
    if not url:
        return None
    son = str(url).rstrip("/").rsplit("/", 1)[-1]
    return son if son.isdigit() else None


def _supabase_degerleri_df_e_uygula(df: pd.DataFrame) -> pd.DataFrame:
    """Cache'ten donen listede (12 saatlik erken-donus yolu dahil) BOS kalan
    deger kolonlarini Supabase'deki dolu degerlerle doldurur. Yereldeki dolu
    deger her zaman korunur (taze parser sonucu > eski kayit)."""
    if df.empty or "Fiyat_Tespit_URL" not in df.columns:
        return df
    kolon_map = {"Arz_Fiyati": "arz_fiyati", "Iskonto_Orani": "iskonto_orani",
                 "Graham_Degeri": "graham_degeri",
                 "Carpan_Bazli_Deger": "carpan_bazli_deger"}
    # Hicbir deger eksik degilse Supabase'e hic gitme.
    eksik_var = any(
        col in df.columns and df[col].isna().any() for col in kolon_map)
    if not eksik_var:
        return df
    sb = _supabase_sonuclari_oku()
    if not sb:
        return df
    doldurulan = 0
    for i, row in df.iterrows():
        idx = _url_disclosure_index(row.get("Fiyat_Tespit_URL"))
        if not idx or idx not in sb:
            continue
        kayit = sb[idx]
        for col, alan in kolon_map.items():
            if col not in df.columns:
                continue
            mevcut = df.at[i, col]
            if (mevcut is None or (isinstance(mevcut, float) and pd.isna(mevcut))) \
                    and kayit.get(alan) is not None:
                df.at[i, col] = kayit[alan]
                doldurulan += 1
    if doldurulan:
        print(f"[upcoming-ipo] Supabase'den {doldurulan} bos alan dolduruldu.",
              flush=True)
    return df


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


# ── Fiyat Tespit Raporu sonuc cache'i (suresiz - rapor icerigi degismez) ──────

def _read_fiyat_tespit_sonuc_cache() -> dict:
    cache = {}
    if os.path.exists(FIYAT_TESPIT_SONUC_CACHE):
        try:
            with open(FIYAT_TESPIT_SONUC_CACHE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    # v2.0.6.4: Supabase'deki dolu alanlar yerel null'larin uzerine bindirilir.
    # Yereldeki dolu deger korunur (taze parser sonucu eski kaydi ezmez).
    # Boylece daha once basariyla cikarilmis bir deger icin PDF yeniden
    # indirilmez ve konteyner sifirlansa da deger kaybolmaz.
    try:
        sb = _supabase_sonuclari_oku()
        for key, kayit in sb.items():
            if key not in cache or not isinstance(cache.get(key), dict):
                cache[key] = dict(kayit)
                continue
            for alan in IPO_VALUATIONS_ALANLAR:
                if cache[key].get(alan) is None and kayit.get(alan) is not None:
                    cache[key][alan] = kayit[alan]
    except Exception as e:
        print(f"[upcoming-ipo] Supabase overlay atlandi (hata): {e}", flush=True)
    return cache


def _write_fiyat_tespit_sonuc_cache(cache: dict):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(FIYAT_TESPIT_SONUC_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    # v2.0.6.4: Dolu sonuclar kalici katmana da yazilir (fail-soft).
    try:
        _supabase_sonuclari_yaz(cache)
    except Exception as e:
        print(f"[upcoming-ipo] Supabase yazimi atlandi (hata): {e}", flush=True)


# ── Fiyat Tespit Raporu PDF indirme ve fiyat/iskonto cikarma (v2.0.4.8) ───────

def _unwrap_java_pdf(raw: bytes) -> bytes:
    """KAP'in file/download endpoint'i PDF'i Java byte[] serialization ile
    sarmalayarak doner (ilk 2 byte: 0xAC 0xED). Gercek PDF baytlarini cikarir.
    Sarmalayici yoksa (ileride KAP degistirebilir) oldugu gibi dondurur."""
    if raw[:2] != b"\xac\xed":
        return raw
    import struct
    idx = raw.index(b"\x78\x70", 10)
    arr_len = struct.unpack(">I", raw[idx + 2:idx + 6])[0]
    return raw[idx + 6:idx + 6 + arr_len]


def _fetch_attachment_obj_id(disclosure_index) -> Optional[str]:
    """Bildirimin ek dosyalarindan ilkinin objId'sini alir (Fiyat Tespit
    Raporu bildirimlerinde tipik olarak tek ek dosya vardir)."""
    try:
        import requests
        url = KAP_ATTACHMENT_DETAIL_URL.format(disclosure_index=disclosure_index)
        headers = dict(HEADERS)
        headers["Referer"] = KAP_DETAIL_URL.format(disclosure_index=disclosure_index)
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data or not isinstance(data, list):
            return None
        attachments = data[0].get("attachments", [])
        if not attachments:
            return None
        return attachments[0].get("objId")
    except Exception as e:
        print(f"[upcoming-ipo] attachment-detail hatasi (idx={disclosure_index}): {e}", flush=True)
        return None


def _download_pdf_bytes(obj_id: str) -> Optional[bytes]:
    try:
        import requests
        url = KAP_FILE_DOWNLOAD_URL.format(obj_id=obj_id)
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200 or len(r.content) < 100:
            return None
        return _unwrap_java_pdf(r.content)
    except Exception as e:
        print(f"[upcoming-ipo] PDF indirme hatasi (objId={obj_id}): {e}", flush=True)
        return None


def _extract_temel_deger(metin: str, arz_fiyati: Optional[float] = None) -> dict:
    """v2.0.4.9: Rapor metninden (ayni pdf_to_text ciktisi) BAGIMSIZ Graham
    Sayisi + Carpan Bazli Deger hesaplar (temel_deger_hesaplama.py).
    En son hesaplanan (en guncel donem) degerler doner. Hata/veri eksikligi
    durumunda None doner - IPO satiri etkilenmez, sadece bu sutunlar bos kalir.
    arz_fiyati: fiyat_tespit_ayikla'nin zaten buldugu Pay Basi Deger - Hisse
    Sayisi metinde bulunamazsa Piyasa Degeri/arz_fiyati ile turetilir."""
    try:
        from temel_deger_hesaplama import hedef_fiyat_hesapla
        donemler = hedef_fiyat_hesapla(metin, arz_fiyati=arz_fiyati)
    except Exception as e:
        print(f"[upcoming-ipo] Temel değer hesaplama atlandı (hata): {e}", flush=True)
        return {"graham_degeri": None, "carpan_bazli_deger": None}

    graham = None
    carpan = None
    for dv in donemler:
        if dv.graham_degeri is not None:
            graham = dv.graham_degeri
        if dv.carpan_bazli_deger is not None:
            carpan = dv.carpan_bazli_deger  # en son (en guncel donem) deger kalir

    # Not: Graham/Carpan bulunamazsa (OCR bazi raporlarda rakamlari bile
    # bozuyor - orn. GOLDA/TSK/TERA) sessizce None donuyoruz. Bilerek
    # tahmini bir sayi UYDURMUYORUZ - yanlis bir finansal rakami dogruymus
    # gibi gostermek, bos birakmaktan cok daha kotu bir sonuc olur.
    return {"graham_degeri": graham, "carpan_bazli_deger": carpan}


def _extract_fiyat_ve_iskonto(pdf_bytes: bytes) -> dict:
    """PDF baytlarini gecici dosyaya yazip pdf_text_extract + fiyat_tespit_parser
    ile isler. Once ilk N sayfa (Tip B ozetleri genelde erken sayfalarda -
    orn. ORZAX), bulunamazsa son N sayfa (Tip A/C "Sonuc" bolumleri genelde
    son sayfalarda - orn. SOHO, GOLDA/ISVEA) denenir. Sonuc bulunamazsa
    tum degerler None doner - HATA DEGILDIR, IPO satiri gosterilmeye devam
    eder, sadece fiyat/iskonto sutunlari bos kalir."""
    bos_sonuc = {"arz_fiyati": None, "iskonto_orani": None, "tip": None,
                  "graham_degeri": None, "carpan_bazli_deger": None}
    try:
        import tempfile
        import pdfplumber
        from pdf_text_extract import pdf_to_text, _sayfa_metin_var_mi, _ocr_sayfa
        from fiyat_tespit_parser import fiyat_tespit_ayikla
    except ImportError as e:
        print(f"[upcoming-ipo] fiyat tespit parser modulleri bulunamadi: {e}", flush=True)
        return bos_sonuc

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        # 1) Ilk N sayfa
        metin = pdf_to_text(tmp_path, max_pages=FIYAT_TESPIT_TARAMA_SAYFA_SAYISI)
        sonuc = fiyat_tespit_ayikla(metin)
        metin_son = None

        # 2) Bulunamadiysa son N sayfa
        if sonuc.tip == "BILINMEYEN":
            with pdfplumber.open(tmp_path) as pdf:
                toplam_sayfa = len(pdf.pages)
                print(f"[upcoming-ipo] Ilk {FIYAT_TESPIT_TARAMA_SAYFA_SAYISI} sayfada eslesme yok, "
                      f"toplam sayfa: {toplam_sayfa}, son {FIYAT_TESPIT_TARAMA_SAYFA_SAYISI} deneniyor", flush=True)
                if toplam_sayfa > FIYAT_TESPIT_TARAMA_SAYFA_SAYISI:
                    parcalar = []
                    for sayfa in pdf.pages[-FIYAT_TESPIT_TARAMA_SAYFA_SAYISI:]:
                        if _sayfa_metin_var_mi(sayfa):
                            parcalar.append(sayfa.extract_text() or "")
                        else:
                            parcalar.append(_ocr_sayfa(sayfa))
                    metin_son = "\n\n".join(parcalar)
                    sonuc = fiyat_tespit_ayikla(metin_son)
                    if sonuc.tip == "BILINMEYEN":
                        print(f"[upcoming-ipo] Son-{FIYAT_TESPIT_TARAMA_SAYFA_SAYISI}-sayfa "
                              f"da eslesme yok (arz fiyati bos kalacak)", flush=True)
                    else:
                        print(f"[upcoming-ipo] Son-{FIYAT_TESPIT_TARAMA_SAYFA_SAYISI}-sayfa "
                              f"eslesme bulundu: tip={sonuc.tip}, arz_fiyati={sonuc.arz_fiyati}", flush=True)
                else:
                    print(f"[upcoming-ipo] Toplam sayfa ({toplam_sayfa}) "
                          f"<= {FIYAT_TESPIT_TARAMA_SAYFA_SAYISI}, son-sayfa denemesi atlandi "
                          f"(ilk taramayla ayni sayfalar olurdu)", flush=True)

        # v2.0.4.18: Graham/Carpan hesaplamasi ARTIK sadece ilk N sayfayla
        # SINIRLI DEGIL - eger son N sayfa da tarandiysa (metin_son doluysa)
        # ikisi birlestirilip verilir. Onceden sadece 'metin' (ilk N sayfa)
        # kullaniliyordu, bu da "ozet kutusu" ilk sayfalarda olmayan (veya
        # son taramada bulunan) raporlarda Graham/Carpan'in hep bos kalmasina
        # sebep oluyordu.
        metin_birlesik = metin + ("\n\n" + metin_son if metin_son else "")
        temel = _extract_temel_deger(metin_birlesik, arz_fiyati=sonuc.arz_fiyati)
        # v2.0.7.223 (Bahri'nin bulgusu, 31 Ağustos 2026 — OCR düzeltmesi
        # sonrası bile Graham/Çarpan sütunları boş kaldı, ama log'da bu
        # değerlerin BULUNUP BULUNMADIĞINA dair hiçbir satır yoktu - sadece
        # arz_fiyati için vardı): TEŞHİS EKSİKLİĞİ GİDERİLDİ. Artık her
        # aşamadan sonra Graham/Çarpan durumu AÇIKÇA loglanıyor - bir
        # sonraki çalıştırmada, sorunun "OCR metni üretmiyor" mu yoksa
        # "metin üretiliyor ama regex/parser bulamıyor" mu olduğu netleşecek.
        print(f"[upcoming-ipo] İlk+son sayfa sonrası: "
              f"graham={temel.get('graham_degeri')}, "
              f"carpan={temel.get('carpan_bazli_deger')}", flush=True)

        # v2.0.6: ORTA SAYFA DENEMESI (Format-2). TERA gibi raporlarda tam
        # Bilanco/Gelir Tablosu belgenin ORTASINDA (orn. 83 sayfalik raporda
        # s.63-66) - ilk+son 15 taramasi bunlari hic gormuyor. Ilk+son
        # tarama Graham/Carpan uretemediyse, orta sayfalar taranip
        # yeniden denenir.
        #
        # v2.0.7.221 (Bahri'nin talebi, 31 Ağustos 2026 — "Graham Değeri
        # ve Çarpan Bazlı Değer sütunlarının boş kalması sorun, bu
        # değerlerin tabloda görünmesini sağla"): KESİN KÖK NEDEN
        # BULUNDU - eskiden orta sayfalarda SADECE metin katmanı olanlar
        # okunuyordu, taranmış (görsel) sayfalar "maliyet düşük olsun"
        # diye BİLEREK OCR'sız atlanıyordu. Ama TAM OLARAK Bilanço/Gelir
        # Tablosu gibi kritik finansal tablolar çoğu izahnamede
        # SAYFA GÖRÜNTÜSÜ (taranmış) olarak gömülü - bu yüzden Graham/
        # Çarpan hesaplaması için gereken veri hiç okunamıyordu. Bahri
        # doğruluğun maliyetten önemli olduğunu belirtti - artık orta
        # sayfalarda da (ilk+son N sayfa taramasıyla AYNI şekilde)
        # metin katmanı yoksa OCR uygulanıyor, hiçbir sayfa atlanmıyor.
        if temel.get("graham_degeri") is None and temel.get("carpan_bazli_deger") is None:
            try:
                with pdfplumber.open(tmp_path) as pdf:
                    n = len(pdf.pages)
                    if n > FIYAT_TESPIT_TARAMA_SAYFA_SAYISI:
                        # v2.0.6.1: Fiyat ILK 15 sayfada bulunduysa son-15
                        # taramasi hic yapilmamis olur (metin_son bos) -
                        # oysa FD/FAVOK carpan tablolari genelde raporun
                        # SONUNDADIR (TERA s.82). metin_son bossa kalan TUM
                        # sayfalar (orta+son), doluysa yalnizca orta taranir.
                        bitis = (n if not metin_son
                                 else n - FIYAT_TESPIT_TARAMA_SAYFA_SAYISI)
                        orta_parcalar = []
                        # v2.0.7.222: OCR edilen sayfa sayisini ayrica say -
                        # sinir SADECE OCR gereken (metin katmani olmayan)
                        # sayfalar icin gecerli, ucretsiz/hizli metin
                        # katmani cikarma bu sinirdan ETKILENMEZ.
                        _ocr_edilen_sayfa_sayisi = 0
                        for sayfa in pdf.pages[FIYAT_TESPIT_TARAMA_SAYFA_SAYISI:bitis]:
                            try:
                                if _sayfa_metin_var_mi(sayfa):
                                    orta_parcalar.append(sayfa.extract_text() or "")
                                elif _ocr_edilen_sayfa_sayisi < ORTA_SAYFA_OCR_MAX_SAYFA:
                                    # v2.0.7.221: eskiden "continue" (atla) -
                                    # artik son-N-sayfa mantigiyla AYNI
                                    # sekilde OCR uygulaniyor.
                                    # v2.0.7.222: ama patolojik derecede uzun
                                    # belgelerde calisma suresi patlamasin
                                    # diye bir ust sinira tabi.
                                    orta_parcalar.append(_ocr_sayfa(sayfa))
                                    _ocr_edilen_sayfa_sayisi += 1
                                # else: sinir asildi, bu sayfa (OCR
                                # gerektirdigi icin) sessizce atlanir.
                            except Exception:
                                continue
                        if _ocr_edilen_sayfa_sayisi >= ORTA_SAYFA_OCR_MAX_SAYFA:
                            print(f"[upcoming-ipo] Orta sayfa OCR siniri "
                                  f"({ORTA_SAYFA_OCR_MAX_SAYFA}) asildi - "
                                  f"kalan gorsel sayfalar atlandi", flush=True)
                        if orta_parcalar:
                            print(f"[upcoming-ipo] Kalan {len(orta_parcalar)} sayfa "
                                  f"(metin + OCR) Format-2 icin tarandi", flush=True)
                            temel2 = _extract_temel_deger(
                                metin_birlesik + "\n\n" + "\n\n".join(orta_parcalar),
                                arz_fiyati=sonuc.arz_fiyati)
                            # v2.0.7.223: orta sayfa taramasi Graham/Carpan
                            # ACISINDAN basarili mi degil mi - acikca logla.
                            print(f"[upcoming-ipo] Orta sayfa (Format-2) sonrasi: "
                                  f"graham={temel2.get('graham_degeri')}, "
                                  f"carpan={temel2.get('carpan_bazli_deger')}", flush=True)
                            for k in temel:
                                if temel[k] is None:
                                    temel[k] = temel2.get(k)
            except Exception as e:
                print(f"[upcoming-ipo] Orta sayfa denemesi hatasi: {e}", flush=True)

        # v2.0.7.223: NIHAI sonuc - bu belge icin Graham/Carpan sonunda
        # bulundu mu bulunamadi mi, hangi asamada olursa olsun tek satirda
        # ozetleniyor.
        print(f"[upcoming-ipo] NIHAI SONUC: arz_fiyati={sonuc.arz_fiyati}, "
              f"graham={temel.get('graham_degeri')}, "
              f"carpan={temel.get('carpan_bazli_deger')}", flush=True)
        return {
            "arz_fiyati": sonuc.arz_fiyati,
            "iskonto_orani": sonuc.iskonto_orani,
            "tip": sonuc.tip if sonuc.tip != "BILINMEYEN" else None,
            "graham_degeri": temel.get("graham_degeri"),
            "carpan_bazli_deger": temel.get("carpan_bazli_deger"),
        }
    except Exception as e:
        print(f"[upcoming-ipo] Fiyat/iskonto cikarma hatasi: {e}", flush=True)
        return bos_sonuc
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _disclosure_fiyat_tespit_sonucunu_getir(disclosure_index, cache: dict) -> dict:
    """Tek bir bildirim icin (cache'te yoksa) PDF'i indirip fiyat/iskonto
    cikarir; cache'te varsa dogrudan onu doner. cache SURESIZ gecerlidir -
    yayinlanmis bir Fiyat Tespit Raporu'nun icerigi degismez.

    v2.0.5.8 istisnasi: cache'teki sonucun arz_fiyati BOS ise yeniden
    denenir. Boylece parser'a eklenen yeni desenler (orn. TERA'nin Tip
    'Iskontosu Sonrasi Pay Degeri' etiketi) eski null sonuclara da geriye
    donuk uygulanir - onceden null bir kez yazildi mi sonsuza dek donuk
    kaliyordu. Maliyet sinirli: null satir sayisi az ve her kosuda zaten
    FIYAT_TESPIT_MAX_YENI_ISLEME siniri gecerli."""
    key = str(disclosure_index)
    if key in cache and cache[key].get("arz_fiyati") is not None:
        return cache[key]
    if key in cache:
        print(f"[upcoming-ipo] {key}: cache'te arz_fiyati bos - "
              f"guncel parser ile yeniden deneniyor", flush=True)

    sonuc = {"arz_fiyati": None, "iskonto_orani": None, "tip": None,
              "graham_degeri": None, "carpan_bazli_deger": None}
    obj_id = _fetch_attachment_obj_id(disclosure_index)
    if obj_id:
        pdf_bytes = _download_pdf_bytes(obj_id)
        if pdf_bytes:
            sonuc = _extract_fiyat_ve_iskonto(pdf_bytes)

    # v2.0.5.8: Yeniden denemede eski sonuctaki dolu alanlari (orn. iskonto)
    # yeni sonuc bosaltmasin - alan bazinda birlestir.
    if key in cache:
        eski = cache[key]
        for alan in sonuc:
            if sonuc[alan] is None and eski.get(alan) is not None:
                sonuc[alan] = eski[alan]

    cache[key] = sonuc
    return sonuc



# v2.0.4.7 (3 Temmuz 2026): Fiyat Tespit Raporu eslestirmesi eklendi.
# v2.0.4.8 (4 Temmuz 2026): PDF eki indirilip icinden arz fiyati/iskonto
# otomatik cikarilmaya baslandi (yukaridaki _extract_fiyat_ve_iskonto vb.).
# Bu AYRI bir kategori - yeni IPO ADAYI listesi UretMEZ (cunku Fiyat Tespit
# Raporu bildirimleri mevcut sirketlerin sermaye artirimlarini da icerir,
# izahname kadar guvenilir bir "yeni/mevcut" ayrimi yok bu kategoride).
# Bunun yerine: yukaridaki KAP_CATEGORIES'ten zaten "yeni IPO" olarak
# siniflandirilmis satirlara, EGER kodlari eslesirse, gercek Fiyat Tespit
# Raporu linkini VE (bulunabilirse) arz fiyati/iskonto oranini EKLER.
FIYAT_TESPIT_PARAMS = {
    "srcbar": "Y", "cmp": "Y", "cat": "4",
    "s": "8aca490d4f2b6b39014f2c32b50a04bf",
    "st": "Fiyat Tespit Raporu",
    "kw": "fiyat tespit", "slf": "ALL",
}


def _fetch_fiyat_tespit_map() -> tuple:
    """Fiyat Tespit Raporu bildirimlerini ceker. Iki deger dondurur:
      1) code_map: her ticker kodu icin EN GUNCEL bildirimin KAP linki
         {"GOLDA": {"url": ..., "tarih": ...}, ...} (basit/hizli arama icin)
      2) disclosures: HER bildirimin TAM kod kumesini (stockCode+relatedStocks)
         iceren liste - v2.0.7.237'de eklendi, bkz. asagidaki not.
    Bir sirketin birden fazla bolumlu raporu olabilir (orn. Golda icin
    "Sayfa 1-36" + "Sayfa 37-72") - en yeni publishDate kazanir.
    Hata durumunda SESSIZCE (bos dict, bos liste) doner - cagiran taraf
    link gostermez, ama IPO listesi kendisi etkilenmez.

    v2.0.7.237 (Bahri'nin bulgusu - Kapeks/Bewen karisikligi): SADECE
    code_map (kod -> TEK en guncel bildirim) yeterli DEGIL - iki farkli
    sirket AYNI paylasilan/genel kodu (ornek "TSK, TSKB" - ortak araci
    kurum TSKB) kullanabiliyor, bu durumda code_map o kod icin sadece
    TEK (en guncel) sirketi hatirlar, digeri "kaybolur". 'disclosures'
    listesi, eslestirme sirasinda HANGI bildirimin sorgulanan satirin
    kod kumesiyle EN COK ORTUSTUGUNU (kesisim buyuklugu) bulabilmek icin
    tutuluyor - bu, salt "en guncel" secmekten cok daha guvenilir."""
    try:
        html_text = _fetch_kap_html(FIYAT_TESPIT_PARAMS)
        if not html_text:
            return {}, []
        raw_records = _extract_disclosure_json(html_text)
        if not raw_records:
            return {}, []

        code_map = {}
        disclosures = []
        for rec in raw_records:
            d = rec.get("disclosureBasic", {})
            idx = d.get("disclosureIndex", "")
            if not idx:
                continue
            publish_date = d.get("publishDate", "")
            url = KAP_DETAIL_URL.format(disclosure_index=idx)

            # v2.0.7.237: DD.MM.YYYY bicimini dogru KRONOLOJIK karsilastirma
            # icin sortlanabilir YYYYMMDDHHMMSS anahtarina cevir - duz metin
            # karsilastirmasi GUN basamagini ONCE kiyasladigi icin YANLIS
            # sonuc verebiliyordu (ornek: '25.07...' metin olarak '07.08...'
            # dan BUYUK gorunur, ama takvimde 07 Agustos 25 Temmuz'dan daha
            # yenidir). Bu, Kapeks/Bewen karisikligina KATKIDA BULUNAN ikinci
            # bir hataydi (temettu_client.py'deki ayni sinif hatanin
            # esdegeri - bkz. v2.0.7.230).
            try:
                gun, ay, geri = publish_date.split(".", 2)
                yil = geri[:4]
                saat_kismi = geri[4:].strip().replace(":", "").replace(" ", "")
                sirala_anahtari = f"{yil}{ay}{gun}{saat_kismi}"
            except Exception:
                sirala_anahtari = publish_date

            # stockCode + relatedStocks icindeki TUM kodlari cikar (virgul/boslukla ayrik)
            raw_codes = f"{d.get('stockCode','')},{d.get('relatedStocks','')}"
            codes = [c.strip().upper() for c in re.split(r"[,\s]+", raw_codes)
                     if c.strip() and 2 <= len(c.strip()) <= 8]
            if not codes:
                continue

            bildirim = {"url": url, "tarih": publish_date, "disclosure_index": idx,
                        "_sirala": sirala_anahtari, "_kodlar": set(codes)}
            disclosures.append(bildirim)

            for code in codes:
                existing = code_map.get(code)
                if existing is None or sirala_anahtari > existing.get("_sirala", ""):
                    code_map[code] = bildirim

        print(f"[upcoming-ipo] Fiyat Tespit Raporu: {len(raw_records)} bildirim -> "
              f"{len(code_map)} benzersiz ticker eslesti", flush=True)
        return code_map, disclosures
    except Exception as e:
        print(f"[upcoming-ipo] Fiyat Tespit Raporu eslestirmesi atlandi (hata): {e}", flush=True)
        return {}, []


# ── KAP'tan cekim ve JSON cikarma (2 Temmuz 2026'da dogrulanan yontem) ────────

def _fetch_kap_html(params: dict) -> Optional[str]:
    try:
        import requests
        r = requests.get(KAP_SEARCH_URL, params=params,
                          headers=HEADERS, timeout=20)
        if r.status_code == 200 and len(r.text) > 1000:
            r.encoding = "utf-8"
            print(f"[upcoming-ipo] KAP HTML yanit alindi ({params.get('st','')[:30]}): "
                  f"{len(r.text)} karakter", flush=True)
            return r.text
        print(f"[upcoming-ipo] KAP HTTP durumu: {r.status_code}, "
              f"uzunluk: {len(r.text) if r.text else 0}", flush=True)
    except Exception as e:
        print(f"[upcoming-ipo] KAP fetch hatasi: {e}", flush=True)
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
        print(f"[upcoming-ipo] JSON parse basarili: {len(parsed)} kayit", flush=True)
        return parsed

    except json.JSONDecodeError as e:
        print(f"[upcoming-ipo] JSON decode hatasi: {e}", flush=True)
        return []
    except Exception as e:
        print(f"[upcoming-ipo] Parse hatasi: {e}", flush=True)
        return []


# ── Ana fonksiyon ──────────────────────────────────────────────────────────────

def fetch_upcoming_ipos(force_refresh: bool = False) -> pd.DataFrame:
    """
    Yaklasan halka arzlari (henuz BIST evreninde olmayan, izahname surecindeki
    sirketleri) DataFrame olarak dondurur. İKİ KAP kategorisini birlestirir:
    "Onayina Sunulan" (basvuru asamasi) + "Tarafindan Onaylanan" (onaylandi,
    talep toplama surecinde/yakinda).

    Kolonlar: Tarih, Kod, Sirket, Konu, Ozet, Durum, Detay_URL, Fiyat_Tespit_URL,
    Arz_Fiyati, Iskonto_Orani (son ikisi Fiyat Tespit Raporu PDF'inden otomatik
    cikarilir - bulunamazsa None kalir, bu HATA DEGILDIR).
    Bos DataFrame donebilir (veri yoksa veya hepsi mevcut sirket ise) — bu
    HATA DEGILDIR, "su an yeni halka arz yok" olarak yorumlanmalidir.
    """
    if not force_refresh:
        cached = _read_cache()
        if cached is not None:
            print(f"[upcoming-ipo] Cache kullanildi: {len(cached)} satir", flush=True)
            # v2.0.6.4: Erken-donus yolunda da Supabase kalici katmani
            # uygulanir - repodan gelen cache'te (deploy sonrasi ilk acilis)
            # deger kolonlari null olabilir; daha once basariyla hesaplanmis
            # degerler burada geri doldurulur. Zorla Yenile'ye gerek kalmaz.
            return _supabase_degerleri_df_e_uygula(pd.DataFrame(cached))

    all_new_rows = []
    any_fetch_succeeded = False

    for cat in KAP_CATEGORIES:
        html_text = _fetch_kap_html(cat["params"])
        if not html_text:
            print(f"[upcoming-ipo] '{cat['key']}' kategorisi cekilemedi, atlaniyor", flush=True)
            continue
        any_fetch_succeeded = True

        raw_records = _extract_disclosure_json(html_text)
        if not raw_records:
            print(f"[upcoming-ipo] '{cat['key']}' kategorisinde kayit bulunamadi", flush=True)
            continue

        for rec in raw_records:
            d = rec.get("disclosureBasic", {})
            kod_raw = d.get("stockCode", "") or ""
            summary = d.get("summary", "") or ""
            summary_lower = summary.lower()

            # v2.0.4.2 (2 Temmuz 2026): 131 kayitlik gercek "Onaylanan" verisiyle
            # kalibre edildi. Onceki kural ("Halka Arz Basvurusu" ifadesi) sadece
            # "Onayina Sunulan" (basvuru) asamasinda gecerliydi - GOLDA, ISVEA,
            # ORZAX, EKIM, BETAE gibi "Onaylanan" asamasindaki gercek yeni IPO'lar
            # bu ifadeyi HIC kullanmiyor, bunun yerine sadece "[Sirket Adi] A.S.
            # ...Izahnamesi" diyor (cogu zaman bir araci kurum - INFO, HALKI, VKY,
            # TSKB - uzerinden bildiriliyor, kendi stockCode'u degil).
            #
            # Kural (iki kategori icin de gecerli, 15/15 gercek ornekte dogrulandi):
            #   1) "Halka Arz Başvurusu" / "Pay Halka Arz" ifadesi varsa -> YENI IPO
            #   2) "Sermaye Artır..." ifadesi varsa (1'de degilse) -> MEVCUT sirket
            #   3) "Varant" / "Sertifika" ifadesi varsa -> MEVCUT sirket (kendi
            #      varant/sertifika ihraci, capraz kontrol degil)
            #   4) Ozette "A.S." / "AS" (sirket unvani) geciyorsa VE 3 degilse -> YENI IPO
            #   5) Digerleri -> belirsiz, guvenli tarafta kal, ELE
            has_warrant = "varant" in summary_lower or "sertifika" in summary_lower
            has_capital_increase = "sermaye artır" in summary_lower or "sermaye artir" in summary_lower
            has_ipo_phrase = "halka arz başvuru" in summary_lower or "halka arz basvuru" in summary_lower \
                              or "pay halka arz" in summary_lower
            has_company_suffix = bool(re.search(r'a\.?ş\.?\b', summary_lower)) \
                                  or bool(re.search(r'a\.?o\.?\b', summary_lower))

            if has_ipo_phrase:
                is_new_ipo = True
            elif has_capital_increase:
                is_new_ipo = False
            elif has_company_suffix and not has_warrant:
                is_new_ipo = True
            else:
                is_new_ipo = False

            if not is_new_ipo:
                continue

            idx = d.get("disclosureIndex", "")
            related = d.get("relatedStocks", "") or ""

            # v2.0.4.2: Ozette gecen sirket adini cikar (araci kurum uzerinden
            # bildirilen IPO'larda "Sirket" alani yanlislikla araci kurumun
            # adini gosterirdi - orn. EKIM'in bildirimi VAKIF YATIRIM üzerinden
            # yapiliyor ama kullaniciya "EKIM" gostermek daha anlamli).
            display_company = d.get("companyTitle", "")
            # v2.0.5.7: Sonlandirici olarak "A.S." yaninda "Anonim Sirketi" de
            # kabul edilir. Onceki regex sadece A.S. aradigi icin, unvani
            # "... Anonim Sirketi" ile biten sirketlerde (orn. Saat ve Saat)
            # ilk A.S.'yi ta duyuru metnindeki "Borsa Istanbul A.S"de bulup
            # aradaki her seyi isim saniyordu.
            name_match = re.search(
                r'^([A-ZÇĞİÖŞÜ][\wÇĞİÖŞÜçğıöşü\s\.\'&,-]*?'
                r'(?:[Aa]\.?[Şş]\.?|Anonim Şirket(?:i)?|[Aa]\.?[Oo]\.?))\b', summary)
            if name_match:
                candidate = name_match.group(1).strip()
                # v2.0.5.7: Duyuru kaliplarindan tasan kuyruklari kes
                # (orn. "... A.S. Paylarinin Halka Arzina Iliskin ...")
                candidate = re.split(
                    r'\s+(?:Paylar[ıi]n[ıi]n|Pay\s+Halka|Halka\s+Arz[ıi]na)\b',
                    candidate)[0].strip()
                # Cok kisa veya anlamsiz eslesmeleri (orn. sadece "A.Ş.") ele
                if len(candidate) > 8:
                    display_company = candidate

            all_new_rows.append({
                "Tarih":     d.get("publishDate", ""),
                "Kod":       kod_raw,
                "Sirket":    display_company,
                "Konu":      d.get("title", ""),
                "Ozet":      summary,
                "Durum":     cat["durum_label"],
                "Detay_URL": KAP_DETAIL_URL.format(disclosure_index=idx) if idx else "",
                "_dedup_key": f"{kod_raw}|{related}",
                # v2.0.7.237: relatedStocks AYRICA saklanıyor - "Kod" alanı
                # (stockCode) çoğu zaman şirketin KENDİ ticker'ı değil,
                # aracı kurumun genel kodu (ör. "TSK, TSKB" = TSKB'nin TÜM
                # müşterileri için aynı) - bu tek başına iki farklı şirketi
                # (Kapeks/Bewen gibi) ayırt edemiyor. relatedStocks ise
                # şirkete ÖZEL kodu (ör. "KPEKS", "BEWEN") içeriyor -
                # Fiyat Tespit Raporu eşleştirmesinde ikisi BİRLİKTE
                # kullanılacak (bkz. _en_iyi_eslesme).
                "_related_kod": related,
            })

        print(f"[upcoming-ipo] '{cat['key']}' kategorisi: {len(raw_records)} bildirim tarandi", flush=True)

    if not any_fetch_succeeded:
        print("[upcoming-ipo] Hicbir kategori cekilemedi — eski cache/bos donuluyor")
        cached = _read_cache()
        if cached is not None:
            # v2.0.7: Bu yedek yol da Supabase overlay'inden gecer - KAP'in
            # tamamen erisilemez oldugu anda Zorla Yenile'ye basilirsa bile
            # kalici katmandaki degerler bos gosterilmez.
            return _supabase_degerleri_df_e_uygula(pd.DataFrame(cached))
        return pd.DataFrame(columns=["Tarih","Kod","Sirket","Konu","Ozet","Durum",
                                       "Detay_URL","Fiyat_Tespit_URL",
                                       "Arz_Fiyati","Iskonto_Orani",
                                       "Graham_Degeri","Carpan_Bazli_Deger"])

    # Tarihe gore azalan sirala (en yeni basvuru/onay en ustte)
    df = pd.DataFrame(all_new_rows)
    if not df.empty:
        try:
            df["_sort_key"] = pd.to_datetime(df["Tarih"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
            df = df.sort_values("_sort_key", ascending=False).drop(columns=["_sort_key"])
        except Exception:
            pass

        # v2.0.4.2: Ayni IPO adayinin (ayni stockCode + relatedStocks kombinasyonu)
        # birden fazla "Bolum" bildirimi olabilir (GOLDA icin 24 tane gibi) -
        # sadece EN GUNCEL kaydi tut, digerleri "detay" linkinden erisilebilir.
        if "_dedup_key" in df.columns:
            df = df.drop_duplicates(subset="_dedup_key", keep="first").drop(columns=["_dedup_key"])

        # v2.0.4.7: Fiyat Tespit Raporu eslestirmesi - her satirin Kod alanindaki
        # ticker(lar) icin gercek fiyat tespit raporu linki varsa ekle. Hata
        # olursa (KAP erisilemez vb.) tum satirlar icin bos kalir, IPO listesi
        # kendisi etkilenmez.
        df["Fiyat_Tespit_URL"] = ""
        df["Arz_Fiyati"] = None
        df["Iskonto_Orani"] = None
        df["Graham_Degeri"] = None
        df["Carpan_Bazli_Deger"] = None
        try:
            ft_map, ft_disclosures = _fetch_fiyat_tespit_map()
            if ft_map:
                def _kodlari_cikar(ham):
                    return {c.strip().upper() for c in re.split(r"[,\s]+", str(ham)) if c.strip()}

                def _en_iyi_eslesme(row):
                    # v2.0.7.237 (Bahri'nin bulgusu - Kapeks/Bewen karisikligi):
                    # Basit "kod -> EN GUNCEL bildirim" eslestirmesi yeterli
                    # degildi - iki farkli sirket AYNI paylasilan/genel kodu
                    # (ornek "TSK, TSKB" - ortak araci kurum TSKB; hatta "YAT",
                    # "YFMEN" gibi bazi kodlar da iki sirket arasinda ortak
                    # cikabiliyor) kullanabiliyor. Sadece "en son tarihli"
                    # secmek, satirin KENDI ozel kodunu (ornek "BEWEN")
                    # gormezden gelip paylasilan kodun EN GUNCEL sahibine
                    # (ornek Kapeks) yanlislikla yonlendirebiliyordu.
                    #
                    # Cozum: satirin TUM kodlarini (Kod + relatedStocks) bir
                    # kume olarak al, HER aday Fiyat Tespit Raporu bildirimiyle
                    # KESISIM BUYUKLUGUNU hesapla - en cok ORTUSEN bildirim
                    # kazanir (esitlikte en guncel olan). Bu, "Kapeks" satirinin
                    # kendi 5 kodundan (TSK,TSKB,KPEKS,YAT,YFMEN,ZRY) kendi
                    # raporuyla 6/6 orusurken Bewen'in raporuyla sadece
                    # kismi ortustugunu doğru ayirt eder.
                    satir_kodlari = (_kodlari_cikar(row.get("Kod", "")) |
                                      _kodlari_cikar(row.get("_related_kod", "")))
                    if not satir_kodlari or not ft_disclosures:
                        return None
                    en_iyi = None
                    en_iyi_skor = -1
                    for bildirim in ft_disclosures:
                        skor = len(satir_kodlari & bildirim["_kodlar"])
                        if skor == 0:
                            continue
                        if (skor > en_iyi_skor or
                                (skor == en_iyi_skor and
                                 bildirim.get("_sirala", "") > en_iyi.get("_sirala", ""))):
                            en_iyi_skor = skor
                            en_iyi = bildirim
                    return en_iyi

                eslesmeler = df.apply(_en_iyi_eslesme, axis=1)
                if "_related_kod" in df.columns:
                    df = df.drop(columns=["_related_kod"])
                df["Fiyat_Tespit_URL"] = eslesmeler.apply(lambda h: h["url"] if h else "")
                eslesen = (df["Fiyat_Tespit_URL"] != "").sum()
                print(f"[upcoming-ipo] Fiyat Tespit Raporu eslesen satir sayisi: {eslesen}/{len(df)}", flush=True)

                # v2.0.4.8: Eslesen raporlarin PDF'ini indirip arz fiyati/iskonto
                # cikar. Cache'lenmis (daha once islenmis) raporlar ANINDA
                # doner (indirme/OCR YAPILMAZ). Sadece cache'te olmayan YENI
                # raporlar icin indirme yapilir, bu da FIYAT_TESPIT_MAX_YENI_ISLEME
                # ile sinirlanir (bir calistirmada calisma suresi patlamasin diye).
                ft_sonuc_cache = _read_fiyat_tespit_sonuc_cache()
                yeni_islenen_sayisi = 0
                cache_degisti = False

                for i, hit in eslesmeler.items():
                    if not hit:
                        continue
                    idx = hit.get("disclosure_index")
                    if not idx:
                        continue
                    key = str(idx)
                    # v2.0.4.14: force_refresh=True iken, daha önce sonucu
                    # BULUNAMAMIŞ (arz_fiyati=None) kayıtları cache'ten
                    # kaldırıp yeniden denenmesini sağlıyoruz - başarılı
                    # (arz_fiyati dolu) kayıtlara dokunmuyoruz, boşuna
                    # yeniden indirme/OCR yapılmasın diye.
                    # v2.0.4.18: Graham_Degeri de eksikse (arz_fiyati bulunmus
                    # olsa bile) yine yeniden deneniyor - cunku bu iki deger
                    # ayri asamalarda hesaplaniyor, biri bulunup digeri
                    # bulunamamis olabilir (orn. GOLDA/TSK).
                    if (force_refresh and key in ft_sonuc_cache and
                            (ft_sonuc_cache[key].get("arz_fiyati") is None
                             or ft_sonuc_cache[key].get("graham_degeri") is None)):
                        del ft_sonuc_cache[key]
                        cache_degisti = True
                    if key not in ft_sonuc_cache:
                        if yeni_islenen_sayisi >= FIYAT_TESPIT_MAX_YENI_ISLEME:
                            continue  # bu calistirmada limit doldu, sonraki calistirmada denenir
                        yeni_islenen_sayisi += 1
                        cache_degisti = True

                    sonuc = _disclosure_fiyat_tespit_sonucunu_getir(idx, ft_sonuc_cache)
                    df.at[i, "Arz_Fiyati"] = sonuc.get("arz_fiyati")
                    df.at[i, "Iskonto_Orani"] = sonuc.get("iskonto_orani")
                    df.at[i, "Graham_Degeri"] = sonuc.get("graham_degeri")
                    df.at[i, "Carpan_Bazli_Deger"] = sonuc.get("carpan_bazli_deger")

                if cache_degisti:
                    _write_fiyat_tespit_sonuc_cache(ft_sonuc_cache)

                bulunan = df["Arz_Fiyati"].notna().sum()
                print(f"[upcoming-ipo] Arz fiyati cikarilan satir sayisi: {bulunan}/{len(df)} "
                      f"(bu calistirmada {yeni_islenen_sayisi} yeni rapor islendi)", flush=True)
        except Exception as e:
            print(f"[upcoming-ipo] Fiyat Tespit Raporu satir eslestirme/cikarma atlandi (hata): {e}", flush=True)

    # v2.0.7.14/15 - Islem gormeye baslamis (BIST evrenine gecmis) sirketleri
    # "Yaklasan Halka Arzlar" listesinden otomatik dus.
    #
    # v2.0.7.14'te KAYNAK olarak optimized_universe.csv'nin TUM BIST kategorisi
    # kullanilmisti - bu YANLIS cikti (Bahri'nin 11 Temmuz geri bildirimi ile
    # tespit edildi): O dosyada IKI farkli false-positive kaynagi var:
    #   1) KOD CAKISMASI - "TERA" hem KAP'in YENI IPO adayi "SA-RA Enerji"ye
    #      atadigi iliskili-hisse referans kodu HEM DE zaten yillardir islem
    #      goren alakasiz "TERA Yatirim Menkul Degerler A.S."nin gercek
    #      ticker'i. Genel BIST listesiyle karsilastirma bu tesadufi cakismayi
    #      "zaten islem goruyor" sanip HALA BEKLEYEN gercek bir IPO'yu
    #      listeden yanlislikla dusurebilirdi.
    #   2) STUB KAYITLAR - worker.py, BIST_TICKERS statik listesindeki HER
    #      ticker icin (fiyat gelsin gelmesin) bir satir yazar; fiyat
    #      gelmeyenler "(islem gormuyor)" etiketiyle Son_Fiyat=0 olarak
    #      Kategori=BIST'e ISTE bu sekilde giriyor - yani "BIST'te" olmak
    #      "zaten islem goruyor" anlamina gelmiyor.
    #
    # KESIN COZUM: Genel CSV yerine SADECE bist_universe_dynamic Supabase
    # tablosu kullanilir - bu tablo YALNIZCA XHARZ (BIST Halka Arz Endeksi)
    # uyeligiyle ONAYLANMIS, gercekten mezun olmus ticker'lari icerir
    # (worker.py _detect_and_register_new_bist_listings, bkz. Oturum XII).
    # Baglanti/tablo erisilemezse SESSIZCE hicbir satir dusurulmez (fail-safe
    # - yanlis dusurmektense hic dusurmemek tercih edilir).
    if not df.empty:
        try:
            _conn_bud = _supabase_conn()
            if _conn_bud is not None:
                _cur_bud = _conn_bud.cursor()
                _cur_bud.execute("SELECT ticker FROM bist_universe_dynamic")
                _mezun_tickers = {
                    str(r[0]).strip().upper() for r in _cur_bud.fetchall() if r[0]
                }
                _conn_bud.close()
                if _mezun_tickers:
                    def _mezun_mu(kod_raw):
                        codes = [c.strip().upper() for c in re.split(r"[,\s]+", str(kod_raw)) if c.strip()]
                        return any(c in _mezun_tickers for c in codes)
                    _mask_mezun = df["Kod"].apply(_mezun_mu)
                    _dusenler = df.loc[_mask_mezun, "Kod"].tolist()
                    if _dusenler:
                        df = df[~_mask_mezun].reset_index(drop=True)
                        print(f"[upcoming-ipo] {len(_dusenler)} sirket XHARZ ile "
                              f"mezun oldugu icin listeden dusuruldu: {_dusenler}",
                              flush=True)
        except Exception as e:
            print(f"[upcoming-ipo] Mezuniyet filtresi atlandi (hata): {e}", flush=True)

    print(f"[upcoming-ipo] TOPLAM yeni halka arz adayi (iki kategori birlesik): {len(df)}", flush=True)

    _write_cache(df.to_dict("records"))
    return df


def get_upcoming_ipo_summary() -> str:
    """Ozet metin — Halka Arz sayfasinda basliginda gosterilebilir."""
    df = fetch_upcoming_ipos()
    if df.empty:
        return "Su anda takip edilen yeni halka arz basvurusu bulunmuyor."
    return f"{len(df)} yeni halka arz basvurusu (SPK onay surecinde)"
