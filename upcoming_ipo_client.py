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

# v2.0.4.1 (2 Temmuz 2026): İki asama takip ediliyor:
#   1) "SPK Onayına Sunulan"   -> basvuru yapildi, henuz onaylanmadi
#   2) "SPK Tarafından Onaylanan" -> onaylandi, talep toplama surecinde/yakinda
# (ISVEA, EKIM, GOLDA gibi sirketler 2. kategoride cikar - Bahri'nin
# 2 Temmuz 2026'da fark ettigi eksiklik.)
KAP_CATEGORIES = [
    {
        "key": "basvuru",
        "durum_label": "Başvuru Yapıldı - SPK Onayı Bekleniyor",
        "params": {
            "srcbar": "Y", "cmp": "Y", "cat": "4",
            "s": "4028328d5988e2630159d9aebd742fd4",
            "st": "İzahname (SPK Onayına Sunulan)",
            "kw": "izahname", "slf": "ALL",
        },
    },
    {
        "key": "onaylandi",
        "durum_label": "Onaylandı - Talep Toplanıyor/Yakında",
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
    if not os.path.exists(FIYAT_TESPIT_SONUC_CACHE):
        return {}
    try:
        with open(FIYAT_TESPIT_SONUC_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_fiyat_tespit_sonuc_cache(cache: dict):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(FIYAT_TESPIT_SONUC_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


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
        print(f"[upcoming-ipo] attachment-detail hatasi (idx={disclosure_index}): {e}")
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
        print(f"[upcoming-ipo] PDF indirme hatasi (objId={obj_id}): {e}")
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
        print(f"[upcoming-ipo] Temel değer hesaplama atlandı (hata): {e}")
        return {"graham_degeri": None, "carpan_bazli_deger": None}

    graham = None
    carpan = None
    for dv in donemler:
        if dv.graham_degeri is not None:
            graham = dv.graham_degeri
        if dv.carpan_bazli_deger is not None:
            carpan = dv.carpan_bazli_deger  # en son (en guncel donem) deger kalir
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
        print(f"[upcoming-ipo] fiyat tespit parser modulleri bulunamadi: {e}")
        return bos_sonuc

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        # 1) Ilk N sayfa
        metin = pdf_to_text(tmp_path, max_pages=FIYAT_TESPIT_TARAMA_SAYFA_SAYISI)
        sonuc = fiyat_tespit_ayikla(metin)

        # 2) Bulunamadiysa son N sayfa
        if sonuc.tip == "BILINMEYEN":
            with pdfplumber.open(tmp_path) as pdf:
                toplam_sayfa = len(pdf.pages)
                if toplam_sayfa > FIYAT_TESPIT_TARAMA_SAYFA_SAYISI:
                    parcalar = []
                    for sayfa in pdf.pages[-FIYAT_TESPIT_TARAMA_SAYFA_SAYISI:]:
                        if _sayfa_metin_var_mi(sayfa):
                            parcalar.append(sayfa.extract_text() or "")
                        else:
                            parcalar.append(_ocr_sayfa(sayfa))
                    metin_son = "\n\n".join(parcalar)
                    sonuc = fiyat_tespit_ayikla(metin_son)

        temel = _extract_temel_deger(metin, arz_fiyati=sonuc.arz_fiyati)

        return {
            "arz_fiyati": sonuc.arz_fiyati,
            "iskonto_orani": sonuc.iskonto_orani,
            "tip": sonuc.tip if sonuc.tip != "BILINMEYEN" else None,
            "graham_degeri": temel.get("graham_degeri"),
            "carpan_bazli_deger": temel.get("carpan_bazli_deger"),
        }
    except Exception as e:
        print(f"[upcoming-ipo] Fiyat/iskonto cikarma hatasi: {e}")
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
    yayinlanmis bir Fiyat Tespit Raporu'nun icerigi degismez."""
    key = str(disclosure_index)
    if key in cache:
        return cache[key]

    sonuc = {"arz_fiyati": None, "iskonto_orani": None, "tip": None,
              "graham_degeri": None, "carpan_bazli_deger": None}
    obj_id = _fetch_attachment_obj_id(disclosure_index)
    if obj_id:
        pdf_bytes = _download_pdf_bytes(obj_id)
        if pdf_bytes:
            sonuc = _extract_fiyat_ve_iskonto(pdf_bytes)

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


def _fetch_fiyat_tespit_map() -> dict:
    """Fiyat Tespit Raporu bildirimlerini ceker, her ticker kodu icin EN GUNCEL
    bildirimin KAP linkini dondurur: {"GOLDA": {"url": ..., "tarih": ...}, ...}
    Bir sirketin birden fazla bolumlu raporu olabilir (orn. Golda icin
    "Sayfa 1-36" + "Sayfa 37-72") - en yeni publishDate kazanir.
    Hata durumunda SESSIZCE bos sozluk doner - cagiran taraf link gostermez,
    ama IPO listesi kendisi etkilenmez."""
    try:
        html_text = _fetch_kap_html(FIYAT_TESPIT_PARAMS)
        if not html_text:
            return {}
        raw_records = _extract_disclosure_json(html_text)
        if not raw_records:
            return {}

        code_map = {}
        for rec in raw_records:
            d = rec.get("disclosureBasic", {})
            idx = d.get("disclosureIndex", "")
            if not idx:
                continue
            publish_date = d.get("publishDate", "")
            url = KAP_DETAIL_URL.format(disclosure_index=idx)

            # stockCode + relatedStocks icindeki TUM kodlari cikar (virgul/boslukla ayrik)
            raw_codes = f"{d.get('stockCode','')},{d.get('relatedStocks','')}"
            codes = [c.strip().upper() for c in re.split(r"[,\s]+", raw_codes) if c.strip()]

            for code in codes:
                if len(code) < 2 or len(code) > 8:
                    continue
                existing = code_map.get(code)
                if existing is None or publish_date > existing.get("tarih", ""):
                    code_map[code] = {"url": url, "tarih": publish_date,
                                        "disclosure_index": idx}

        print(f"[upcoming-ipo] Fiyat Tespit Raporu: {len(raw_records)} bildirim -> "
              f"{len(code_map)} benzersiz ticker eslesti")
        return code_map
    except Exception as e:
        print(f"[upcoming-ipo] Fiyat Tespit Raporu eslestirmesi atlandi (hata): {e}")
        return {}


# ── KAP'tan cekim ve JSON cikarma (2 Temmuz 2026'da dogrulanan yontem) ────────

def _fetch_kap_html(params: dict) -> Optional[str]:
    try:
        import requests
        r = requests.get(KAP_SEARCH_URL, params=params,
                          headers=HEADERS, timeout=20)
        if r.status_code == 200 and len(r.text) > 1000:
            r.encoding = "utf-8"
            print(f"[upcoming-ipo] KAP HTML yanit alindi ({params.get('st','')[:30]}): "
                  f"{len(r.text)} karakter")
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
            print(f"[upcoming-ipo] Cache kullanildi: {len(cached)} satir")
            return pd.DataFrame(cached)

    all_new_rows = []
    any_fetch_succeeded = False

    for cat in KAP_CATEGORIES:
        html_text = _fetch_kap_html(cat["params"])
        if not html_text:
            print(f"[upcoming-ipo] '{cat['key']}' kategorisi cekilemedi, atlaniyor")
            continue
        any_fetch_succeeded = True

        raw_records = _extract_disclosure_json(html_text)
        if not raw_records:
            print(f"[upcoming-ipo] '{cat['key']}' kategorisinde kayit bulunamadi")
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
            name_match = re.search(r'^([A-ZÇĞİÖŞÜ][\wÇĞİÖŞÜçğıöşü\s\.\'&,-]*?[Aa]\.?[Şş]\.?)\b', summary)
            if name_match:
                candidate = name_match.group(1).strip()
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
            })

        print(f"[upcoming-ipo] '{cat['key']}' kategorisi: {len(raw_records)} bildirim tarandi")

    if not any_fetch_succeeded:
        print("[upcoming-ipo] Hicbir kategori cekilemedi — eski cache/bos donuluyor")
        cached = _read_cache()
        if cached is not None:
            return pd.DataFrame(cached)
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
            ft_map = _fetch_fiyat_tespit_map()
            if ft_map:
                def _en_iyi_eslesme(kod_raw):
                    codes = [c.strip().upper() for c in re.split(r"[,\s]+", str(kod_raw)) if c.strip()]
                    best = None
                    for c in codes:
                        hit = ft_map.get(c)
                        if hit and (best is None or hit["tarih"] > best["tarih"]):
                            best = hit
                    return best

                eslesmeler = df["Kod"].apply(_en_iyi_eslesme)
                df["Fiyat_Tespit_URL"] = eslesmeler.apply(lambda h: h["url"] if h else "")
                eslesen = (df["Fiyat_Tespit_URL"] != "").sum()
                print(f"[upcoming-ipo] Fiyat Tespit Raporu eslesen satir sayisi: {eslesen}/{len(df)}")

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
                      f"(bu calistirmada {yeni_islenen_sayisi} yeni rapor islendi)")
        except Exception as e:
            print(f"[upcoming-ipo] Fiyat Tespit Raporu satir eslestirme/cikarma atlandi (hata): {e}")

    print(f"[upcoming-ipo] TOPLAM yeni halka arz adayi (iki kategori birlesik): {len(df)}")

    _write_cache(df.to_dict("records"))
    return df


def get_upcoming_ipo_summary() -> str:
    """Ozet metin — Halka Arz sayfasinda basliginda gosterilebilir."""
    df = fetch_upcoming_ipos()
    if df.empty:
        return "Su anda takip edilen yeni halka arz basvurusu bulunmuyor."
    return f"{len(df)} yeni halka arz basvurusu (SPK onay surecinde)"
