"""
temettu_client.py — TrendSurf Optima
BIST Temettü Endeksi (XTMTU) üyelerini KAP RSC endpoint'inden çeker.

v2.0.7.229 (1 Eylül 2026): Temettü verisi artık yfinance YERİNE doğrudan
KAP'ın "Kar Payı Dağıtımı" bildirimlerinden (subjectOid ile filtrelenmiş
bildirim-sorgu-sonuc sorgusu) çekiliyor - Bahri'nin talebiyle yfinance'e
tamamen veda edildi. Bu bildirimlerin PDF eki bile yok; veri doğrudan KAP
API yanıtında YAPILANDIRILMIŞ HTML tablosu olarak geliyor - OCR/PDF
gerekmiyor, doğrudan BeautifulSoup ile parse ediliyor.

ÖNEMLİ - KAPSAM SINIRI: KAP'ın bildirim-sorgu-sonuc uç noktası (denendi,
doğrulandı) tarih aralığı parametresi ne verilirse verilsin platform
genelinde SADECE EN SON ~29 "Kar Payı Dağıtımı" bildirimini döndürüyor
(muhtemelen sunucu tarafı sabit bir üst sınır, gerçek sayfalama/tarih
filtresi bulunamadı). Türkiye'de temettüler çoğunlukla Mart-Haziran
arasında yoğunlaşıyor - bu pencerenin dışında kalan (daha eski) bir
XTMTU üyesi için bu API'den veri gelMEYECEK, satır BOŞ kalacak (ESKİ
YANLIŞ VERİ GÖSTERMEK YERİNE - proje ilkesi). yfinance'e geri dönüş
YOKTUR (Bahri'nin açık talebi) - kapsam dışı kalan hisseler için satır
sessizce boş kalır, sonraki bir oturumda gerçek sayfalama/tarih
parametresi bulunursa genişletilebilir.

ÖNEMLİ - VERİM (%) HESABI: KAP'ın döndürdüğü "Brüt(%)" / "Net(%)"
alanları PİYASA FİYATINA göre DEĞİL, 1 TL NOMİNAL DEĞERE göre yüzdedir
(ör. "%952" gibi anlamsız görünen değerler bu yüzden - 1 TL'lik nominal
üzerinden). Bu yüzden verim YÜZDESİ HER ZAMAN kendimiz hesaplıyoruz:
(Brüt TL pay başı temettü) / (güncel piyasa fiyatı) * 100.

Cache: XTMTU üye listesi + temettü detayları 4 saat; ham KAP bildirim
detayları (disclosure_index başına) SÜRESİZ (yayınlanmış bildirim
değişmez - Fiyat Tespit Raporu önbelleğiyle aynı ilke).
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

# ── v2.0.7.230 (1 Eylül 2026, Bahri'nin Chrome DevTools ile bulduğu
# GERÇEK API): KAP "Kar Payı Dağıtımı" bildirim sorgusu ─────────────────────
# v2.0.7.229'da kullanılan GET bildirim-sorgu-sonuc uç noktası aslında
# sitenin arama kutusu OTOMATİK TAMAMLAMA (öneri) özelliğiydi - KAP'ın
# kendi sayfasındaki bir uyarı bunun "geçmişe dönük 30 gün"le sınırlı
# olduğunu söylüyordu, ki canlı testte de öyle çıktı (hep 29 kayıt).
# Bahri, KAP'ın "Detaylı Sorgulama" sayfasında gerçek bir tarih aralığı
# aratıp Chrome DevTools Network sekmesinden GERÇEK isteği yakaladı:
# POST https://www.kap.org.tr/tr/api/disclosure/members/byCriteria
# JSON gövdeli, fromDate/toDate (YYYY-MM-DD) ve subjectList (subjectOid
# dizisi) destekli TAM sorgu API'si - sayfalama/kısıtlama YOK. Test:
# 2026-01-01 → 2026-09-01 aralığında 1233 kayıt döndü, XTMTU'nun 25
# üyesinin TAMAMI (25/25) bu veri setinde bulundu (önceki yöntemde 0/25).
KAP_BILDIRIM_KRITER_URL = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
KAP_BILDIRIM_DETAY_URL  = "https://www.kap.org.tr/tr/api/notification/attachment-detail/{idx}"
KAP_BILDIRIM_LINK_URL   = "https://www.kap.org.tr/tr/Bildirim/{idx}"
KAP_KAR_PAYI_S_HASH     = "4028328d5988e2630159d5fb51c81fe6"  # "Kar Payı Dağıtımı" subjectOid
KAP_KAR_PAYI_GERI_GUN   = 365  # kayan 12 aylık pencere - yil donumunde kapsam sifirlanmasin diye
HEADERS_BILDIRIM = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu",
}

KAR_PAYI_DETAY_CACHE_FILE = os.path.join(CACHE_DIR, "kar_payi_detay.json")

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

# ── v2.0.7.229: Kar Payı Dağıtımı detay önbelleği (SÜRESİZ) ─────────────────
# Fiyat Tespit Raporu önbelleğiyle AYNI ilke: yayınlanmış bir bildirimin
# içeriği değişmez (şirket düzeltme yaparsa YENİ bir disclosure_index ile
# yeni bildirim yayınlar), bu yüzden disclosure_index başına süresiz
# önbelleklenebilir - her çalıştırmada aynı bildirimi tekrar indirip
# parse etmeye gerek yok.

def _read_kar_payi_detay_cache() -> dict:
    try:
        with open(KAR_PAYI_DETAY_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_kar_payi_detay_cache(cache: dict):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(KAR_PAYI_DETAY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _fetch_kar_payi_map() -> dict:
    """Son 12 ayın (kayan pencere) 'Kar Payı Dağıtımı' bildirimlerini
    KAP'ın GERÇEK detaylı sorgulama API'sinden (byCriteria, JSON POST)
    çeker, her ticker kodu icin EN GUNCEL bildirimin disclosure_index'ini
    dondurur: {"TBORG": {"disclosure_index": 1654862, "tarih": "..."}, ...}

    v2.0.7.230: Bahri'nin Chrome DevTools ile yakaladigi gercek API -
    v2.0.7.229'daki GET tabanli yontemin "son 30 gunle sinirli" sorununu
    tamamen cozdu (canli testte 1233 kayit, XTMTU'nun 25/25 uyesi
    bulundu - onceki yontemde 0/25)."""
    try:
        import requests
        from datetime import datetime, timedelta
        bugun = datetime.now()
        baslangic = bugun - timedelta(days=KAP_KAR_PAYI_GERI_GUN)
        payload = {
            "fromDate": baslangic.strftime("%Y-%m-%d"),
            "toDate": bugun.strftime("%Y-%m-%d"),
            "memberType": "IGS",
            "mkkMemberOidList": [], "bdkMemberOidList": [],
            "bdkReview": "", "disclosureClass": "", "disclosureIndexList": [],
            "fromSrc": False, "inactiveMkkMemberOidList": [], "index": "",
            "isLate": "", "mainSector": "", "marketOid": "", "period": "",
            "ruleType": "", "sector": "", "srcCategory": "", "subSector": "",
            "subjectList": [KAP_KAR_PAYI_S_HASH], "term": "", "year": "",
        }
        headers = dict(HEADERS_BILDIRIM)
        headers["Content-Type"] = "application/json"
        headers["Origin"] = "https://www.kap.org.tr"
        r = requests.post(KAP_BILDIRIM_KRITER_URL, headers=headers,
                           json=payload, timeout=30)
        if r.status_code != 200:
            print(f"[temettu_client] KAP byCriteria HTTP durumu: {r.status_code}",
                  flush=True)
            return {}
        raw_records = r.json()
        if not isinstance(raw_records, list):
            return {}

        code_map = {}
        for rec in raw_records:
            idx = rec.get("disclosureIndex")
            if not idx:
                continue
            publish_date = rec.get("publishDate", "")
            # v2.0.7.230: DD.MM.YYYY bicimini dogru KRONOLOJIK karsilastirma
            # icin sortlanabilir YYYYMMDDHHMMSS anahtarina cevir - duz metin
            # karsilastirmasi (upcoming_ipo_client.py'nin eski oruntusu) ay/
            # gun sinirlarinda YANLIS sonuc verebiliyordu (ornek: '05.09...'
            # ile '31.08...' metin olarak karsilastirilinca 31.08 'daha
            # buyuk/yeni' cikar, oysa 05.09 gercekte daha yenidir).
            try:
                gun, ay, geri = publish_date.split(".", 2)
                yil = geri[:4]
                saat_kismi = geri[4:].strip().replace(":", "").replace(" ", "")
                sirala_anahtari = f"{yil}{ay}{gun}{saat_kismi}"
            except Exception:
                sirala_anahtari = publish_date
            raw_codes = f"{rec.get('stockCodes','') or ''},{rec.get('relatedStocks','') or ''}"
            codes = [c.strip().upper() for c in re.split(r"[,\s]+", raw_codes) if c.strip()]
            for code in codes:
                if len(code) < 2 or len(code) > 8:
                    continue
                existing = code_map.get(code)
                if existing is None or sirala_anahtari > existing.get("_sirala", ""):
                    code_map[code] = {"disclosure_index": idx, "tarih": publish_date,
                                       "_sirala": sirala_anahtari}
        print(f"[temettu_client] Kar Payı Dağıtımı ({baslangic.strftime('%d.%m.%Y')} - "
              f"{bugun.strftime('%d.%m.%Y')}): {len(raw_records)} bildirim -> "
              f"{len(code_map)} benzersiz ticker eslesti", flush=True)
        return code_map
    except Exception as e:
        print(f"[temettu_client] Kar Payı Dağıtımı eslestirmesi atlandi (hata): {e}", flush=True)
        return {}


def _tr_sayi(s) -> Optional[float]:
    """KAP'in Turkce sayi bicimini (virgul ondalik, opsiyonel nokta
    binlik ayiraci) float'a cevirir. '9,5209164' -> 9.5209164"""
    if s is None:
        return None
    s = str(s).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _kar_payi_bildirimi_parse_et(disclosure_index, ticker: str) -> dict:
    """Tek bir 'Kar Payı Dağıtımı' bildiriminin HTML govdesini indirip
    yapilandirilmis veriye cevirir. PDF/OCR YOK - dogrudan KAP API
    yanitindaki HTML tablosu BeautifulSoup ile parse ediliyor.

    v2.0.7.230 (Bahri'nin canli testte bulduğu ISCTR ornegiyle):
    BAZI sirketlerin (ornek: Is Bankasi - ISATR/ISBTR/ISCTR/ISKUR) TEK
    bir bildirimde BIRDEN FAZLA pay grubu/ticker'i vardir, HER GRUBUN
    kar payi tutari FARKLIDIR. Eskiden kod "Islem Gormuyor" olmayan ILK
    pozitif satiri aliyordu - bu, ISCTR sorgulanirken yanlislikla A
    Grubu'nun (ISATR) degerini donduruyordu (46,92 TL yerine gercek
    0,54 TL). Artik `ticker` parametresiyle DOGRU satir eslestiriliyor.

    Doner: {"brut_tl": float|None, "net_tl": float|None,
            "ex_date": "gg.aa.yyyy"|None, "odeme_tarihi": "gg.aa.yyyy"|None,
            "odeme_sekli": str|None, "pay_kodu": str|None}
    Bulunamayan/parse edilemeyen alanlar None kalir - UYDURMA YOK."""
    bos = {"brut_tl": None, "net_tl": None, "ex_date": None,
           "odeme_tarihi": None, "odeme_sekli": None, "pay_kodu": None}
    try:
        from bs4 import BeautifulSoup
        import requests
        url = KAP_BILDIRIM_DETAY_URL.format(idx=disclosure_index)
        headers = dict(HEADERS_BILDIRIM)
        headers["Referer"] = KAP_BILDIRIM_LINK_URL.format(idx=disclosure_index)
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return bos
        data = r.json()
        if not data or not data[0].get("disclosureBody"):
            return bos
        html = data[0]["disclosureBody"][0]
        soup = BeautifulSoup(html, "html.parser")

        sonuc = dict(bos)
        ticker_u = (ticker or "").strip().upper()

        # --- Para tablosu: basligi 'Brüt(TL)' iceren herhangi bir tablo ---
        for table in soup.find_all("table"):
            baslik_hucreleri = table.find_all("tr")[0].find_all("td") if table.find_all("tr") else []
            baslik_metni = [td.get_text(strip=True) for td in baslik_hucreleri]
            if not any("Brüt(TL)" in b or "Brut(TL)" in b for b in baslik_metni):
                continue
            brut_idx = next((i for i, b in enumerate(baslik_metni) if "Brüt(TL)" in b), None)
            net_idx = next((i for i, b in enumerate(baslik_metni) if "Net(TL)" in b), None)
            odeme_idx = next((i for i, b in enumerate(baslik_metni) if b == "Ödeme"), None)
            if brut_idx is None:
                continue
            veri_satirlari = table.find_all("tr")[1:]

            secilen = None
            # 1. ONCELIK: "Pay Grup Bilgileri" hucresinde TAM OLARAK aranan
            # ticker kodu geçen satır (virgülle ayrılmış parçalardan biri
            # birebir eşleşmeli - "ISCTR" ile "ISCTRX" gibi yanlış kısmi
            # eşleşmeler önlensin diye).
            if ticker_u:
                for tr in veri_satirlari:
                    cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if not cells:
                        continue
                    parcalar = [p.strip().upper() for p in cells[0].split(",")]
                    if ticker_u in parcalar:
                        secilen = cells
                        break
            # 2. YEDEK (ticker eşleşmesi yoksa - ör. tek satırlık basit
            # raporlar): "Islem Gormuyor" OLMAYAN ilk pozitif satır.
            if secilen is None:
                for tr in veri_satirlari:
                    cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if not cells:
                        continue
                    ilk_hucre = cells[0]
                    if "İşlem Görmüyor" in ilk_hucre or "Islem Gormuyor" in ilk_hucre:
                        continue
                    brut_val = _tr_sayi(cells[brut_idx]) if brut_idx < len(cells) else None
                    if brut_val and brut_val > 0:
                        secilen = cells
                        break
            if secilen is None and veri_satirlari:
                secilen = [td.get_text(strip=True) for td in veri_satirlari[0].find_all("td")]
            if secilen:
                if brut_idx < len(secilen):
                    sonuc["brut_tl"] = _tr_sayi(secilen[brut_idx])
                if net_idx is not None and net_idx < len(secilen):
                    sonuc["net_tl"] = _tr_sayi(secilen[net_idx])
                if odeme_idx is not None and odeme_idx < len(secilen):
                    sonuc["odeme_sekli"] = secilen[odeme_idx]
                sonuc["pay_kodu"] = secilen[0]
            break

        # --- Tarih tablosu: basligi 'Kesinleşen'/'Teklif Edilen' iceren ---
        for table in soup.find_all("table"):
            baslik_hucreleri = table.find_all("tr")[0].find_all("td") if table.find_all("tr") else []
            baslik_metni = [td.get_text(strip=True) for td in baslik_hucreleri]
            if not any("Hak Kullanım Tarihi" in b for b in baslik_metni):
                continue
            kesin_idx = next((i for i, b in enumerate(baslik_metni)
                                if b.startswith("Kesinleşen")), None)
            teklif_idx = next((i for i, b in enumerate(baslik_metni)
                                 if b.startswith("Teklif")), None)
            odeme_tarihi_idx = next((i for i, b in enumerate(baslik_metni)
                                       if b.startswith("Ödeme Tarihi")), None)
            veri_satirlari = table.find_all("tr")[1:]
            if veri_satirlari:
                cells = [td.get_text(strip=True) for td in veri_satirlari[0].find_all("td")]
                hedef_idx = kesin_idx if kesin_idx is not None else teklif_idx
                if hedef_idx is not None and hedef_idx < len(cells) and cells[hedef_idx]:
                    sonuc["ex_date"] = cells[hedef_idx]
                if odeme_tarihi_idx is not None and odeme_tarihi_idx < len(cells):
                    sonuc["odeme_tarihi"] = cells[odeme_tarihi_idx]
            break

        return sonuc
    except Exception as e:
        print(f"[temettu_client] Bildirim {disclosure_index} parse hatasi: {e}", flush=True)
        return bos


def _kar_payi_detay_getir(disclosure_index, ticker: str, detay_cache: dict) -> dict:
    """Onbellekten (suresiz) doner, yoksa indirip parse eder ve
    onbellege yazar. cagiran taraf onbellegi diske YAZMAKTAN sorumludur
    (toplu is bittikten sonra tek seferde - performans icin).

    v2.0.7.230: onbellek anahtari artik SADECE disclosure_index DEGIL,
    "disclosure_index:ticker" - cunku tek bir bildirimde birden fazla
    pay grubu/ticker olabiliyor (bkz. yukaridaki fonksiyon notu), her
    birinin degeri farkli, aynı anahtar altinda saklanamazlar."""
    key = f"{disclosure_index}:{ticker.upper()}"
    if key in detay_cache:
        return detay_cache[key]
    sonuc = _kar_payi_bildirimi_parse_et(disclosure_index, ticker)
    detay_cache[key] = sonuc
    return sonuc

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

# ── Temettü verisi çekimi ─────────────────────────────────────────────────────

def _fetch_dividend_data(ticker: str, cur_price: float, kar_payi_map: dict,
                          detay_cache: dict) -> dict:
    """KAP'ın 'Kar Payı Dağıtımı' bildiriminden temettü verilerini çeker.

    v2.0.7.229 (1 Eylül 2026, Bahri'nin talebi): yfinance TAMAMEN
    KALDIRILDI, yerine doğrudan KAP kullanılıyor. Önceki v2.0.7.220
    düzeltmesi yfinance'in dividendYield birim belirsizliğini (oran mı
    yüzde mi) *yorumlamaya* çalışıyordu - KAP'a geçilince bu belirsizlik
    tamamen ortadan kalktı: KAP'ın kendi yüzde alanı zaten kullanılmıyor
    (bkz. modül başı not - nominal değere göre, piyasa fiyatına göre
    DEĞİL), verim HER ZAMAN kendimiz (brüt TL / güncel fiyat) hesaplıyoruz
    - tek, tutarlı, belirsizliksiz bir yöntem.

    ticker kar_payi_map'te yoksa (KAP'ın döndürdüğü ~29 bildirimlik
    pencerede bu hisse için son dönemde bildirim yoksa) SESSİZCE boş
    sonuç döner - UYDURMA YOK, eski/yanlış bir değer göstermektense
    satır boş kalır (bkz. modül başı 'KAPSAM SINIRI' notu)."""
    result = {
        "div_per_share": 0.0,
        "div_yield":     0.0,
        "ex_date":       "—",
        "frequency":     "—",
        "annual_div":    0.0,
    }
    eslesme = kar_payi_map.get(ticker.upper())
    if not eslesme:
        return result

    detay = _kar_payi_detay_getir(eslesme["disclosure_index"], ticker, detay_cache)
    brut = detay.get("brut_tl")
    if brut and brut > 0:
        result["div_per_share"] = round(brut, 4)
        result["annual_div"]    = round(brut, 4)
        if cur_price and cur_price > 0:
            result["div_yield"] = round(brut / cur_price * 100, 2)

    if detay.get("ex_date"):
        result["ex_date"] = detay["ex_date"]
    if detay.get("odeme_sekli"):
        # KAP'ta cogunlukla "Peşin" (tek seferde) goruluyor - Turkiye'de
        # temettu dagitim kararlari yilda bir kez alindigi icin "Yıllık"
        # olarak etiketleniyor (odeme TAKSITLE yapilsa bile karar yillik).
        result["frequency"] = "Yıllık"

    return result

# ── CSV zenginleştirme ────────────────────────────────────────────────────────

def _enrich(rows: list, df_uni_hazir=None) -> list:
    """v2.0.7.141 (Bahri'nin bulgusu, 11 Ağustos 2026 — TUPRS BIST'te
    68,0'a düşmüşken burada hâlâ 63,0 kalması): v2.0.7.132'nin "CSV'den
    RSI/Ret1M okuyup scoring.py ile YENİDEN HESAPLA" yaklaşımı YANLIŞTI -
    worker.py'nin CSV'ye yazdığı Optima_Skor, scoring.py'nin temel
    formülüne EK olarak bir "Hacim/Düşüş Düzeltmesi" (_score_adj + _dd_adj)
    içeriyor - bu düzeltme scoring.py'de YOK, bu yüzden yeniden hesaplamak
    HER ZAMAN worker.py'nin gerçek skorundan farklı (TUPRS örneğinde tam
    +5,0 fark) bir sayı üretiyordu. **Doğru çözüm CSV'deki Optima_Skor'u
    DOĞRUDAN KOPYALAMAK, yeniden hesaplamak DEĞİL** - worker.py zaten TAM
    ve DOĞRU hesabı yapıyor.

    v2.0.7.134/135'in ASIL bulduğu gerçek sorun (Fırsat Radarı overlay
    eksikliği) hâlâ geçerli ve burada düzeltiliyor: eğer çağıran taraf
    (app.py) zaten yüklenmiş, overlay'i İÇEREN df_uni'yi verirse
    (df_uni_hazir), doğrudan ondan okunur (hızlı, ekstra sorgu yok, TAM
    parite). Verilmezse kendi CSV okuması + kendi overlay sorgusu yapılır
    - AMA HİÇBİR DURUMDA yeniden hesaplama YAPILMAZ, sadece kopyalanır."""
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

def fetch_temettu_list(force_refresh: bool = False, df_uni_hazir=None) -> pd.DataFrame:
    """
    XTMTU üyelerini temettü verileriyle döner.
    Sütunlar: Ticker, Şirket, Son_Fiyat, RSI, Ret1M, Optima_Skor,
              div_per_share, div_yield, ex_date, frequency,
              Toplam_Getiri

    v2.0.7.141: df_uni_hazir - app.py'nin zaten yüklediği (Fırsat Radarı
    overlay'i dahil) df_uni verilirse, _enrich() kendi CSV okumasını/
    Supabase sorgusunu YAPMAZ, doğrudan bundan okur (hızlı + tam parite).
    """
    if not force_refresh:
        cached = _read_cache()
        if cached:
            # v2.0.7.133/141: önbellekten dönerken bile Optima_Skor/RSI/
            # Ret1M/Son_Fiyat her seferinde TAZE alınıyor (kopyalanıyor,
            # YENİDEN HESAPLANMIYOR - bkz. _enrich() notu) - ya doğrudan
            # hazır df_uni'den (hızlı, ekstra sorgu yok) ya da
            # (verilmemişse) kendi CSV+overlay sorgusundan. Sadece pahalı
            # kısımlar (XTMTU üye listesi, KAP temettü bildirim detayları -
            # detay zaten ayrıca SÜRESİZ önbellekli, bkz. modül başı) 4 saat
            # önbellekli kalıyor.
            cached = _enrich(cached, df_uni_hazir)
            return pd.DataFrame(cached)

    # XTMTU üyelerini çek
    rows = _fetch_xtmtu_from_kap()
    if not rows:
        return pd.DataFrame()

    # CSV'den (veya hazır df_uni'den) fiyat/skor ekle
    rows = _enrich(rows, df_uni_hazir)

    # Temettü verisi — KAP "Kar Payı Dağıtımı" bildirimleri (paralel)
    # v2.0.7.229: yfinance yerine KAP. Once TUM ticker'lar icin tek bir
    # bildirim haritasi cekiliyor (1 istek), sonra her hisse icin (varsa)
    # kendi bildirim detayi aciliyor - detay onbellegi SURESIZ oldugu icin
    # daha once gorulmus bir bildirim tekrar indirilmiyor.
    print(f"  Temettü verisi çekiliyor (KAP - {len(rows)} hisse)...")
    kar_payi_map = _fetch_kar_payi_map()
    detay_cache = _read_kar_payi_detay_cache()
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _get_div(r):
        t = r["Ticker"]
        p = r.get("Son_Fiyat", 0)
        d = _fetch_dividend_data(t, p, kar_payi_map, detay_cache)
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

    # Bu calistirmada yeni parse edilen bildirim detaylari (varsa) diske
    # yaziliyor - suredzz onbellek boylece kalici hale geliyor.
    _write_kar_payi_detay_cache(detay_cache)

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
