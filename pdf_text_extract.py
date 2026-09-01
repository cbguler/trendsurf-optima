"""
pdf_text_extract.py

Fiyat Tespit Raporu PDF'lerini düz metne çeviren yardımcı fonksiyon.

Akış:
  1) Önce pdfplumber ile normal metin katmanı denenir (İntegral/SOHO gibi
     metin tabanlı raporlar için hızlı ve %100 doğru).
  2) Sayfada metin katmanı yoksa (KAP'a gönderilen çoğu Fiyat Tespit Raporu
     taranmış/görsel PDF olabiliyor — Gedik, Halk Yatırım, İnfo Yatırım
     örneklerinde gözlemlendi) sayfa görsele çevrilip ÖNCE OCR.space
     Engine 3 (ücretsiz, kartsız bulut API) ile, o başarısız olursa yerel
     Türkçe Tesseract ile metne çevrilir.

v2.0.7.225 (1 Eylül 2026, Bahri'nin bulgusu — Halka Arz sayfasında Graham
Değeri/Çarpan Bazlı Değer sürekli boş kalıyordu): GERÇEK bir sorunlu rapor
(Kapeks Kimya/TSKB Fiyat Tespit Raporu, tamamen taranmış) üzerinde ölçüldü:
  - Yerel Tesseract (ön-işleme denemeleri dahil): 47 rakamdan sadece 9-10'u
    doğru (görüntü ön-işleme "iyileştirmeleri" bazen daha da kötüleştirdi).
  - OCR.space Engine 3: 47/47 DOĞRU, üstelik çıktı hazır Markdown tablo.
Bu yüzden artık ÖNCELİKLİ yöntem OCR.space; Tesseract SADECE API anahtarı
yoksa veya çağrı herhangi bir nedenle başarısız olursa (ağ hatası, kota
aşımı, dosya boyutu vb.) devreye giren YEDEK yöntemdir - sistem "OCR hiç
yapılamadı" diye tamamen durmaz, sessizce Tesseract'a düşer.

requirements.txt'e eklenmesi gerekenler: pdfplumber, pypdf, pytesseract,
requests, Pillow (hepsi zaten mevcut).
Sistem paketi (GitHub Actions / apt): tesseract-ocr, tesseract-ocr-tur
  -> apt-get install -y tesseract-ocr tesseract-ocr-tur (YEDEK yöntem için
  hâlâ gerekli - OCR.space kullanılamazsa devreye girer.)
GitHub Actions secret: OCRSPACE_API_KEY (https://ocr.space/ocrapi/freekey -
  ücretsiz, kredi kartı istemiyor, ayda 25.000 istek Engine 1/2 + ayrıca
  2.500 istek Engine 3 için).
"""

import re
from typing import Optional


def _sayfa_metin_var_mi(sayfa) -> bool:
    """pdfplumber sayfasında gerçek metin karakteri (char objesi) var mı."""
    try:
        return len(sayfa.chars) > 0
    except Exception:
        return False


def _markdown_tablo_duzlestir(metin: str) -> str:
    """OCR.space Engine 3, tablo içeriğini Markdown formatında döndürür
    ('| hücre1 | hücre2 |' satırları + '|---|---|' ayırıcı satırları).
    Mevcut parser'lar (fiyat_tespit_parser.py / temel_deger_hesaplama.py)
    düz, boşlukla ayrılmış token'lar bekliyor - bu yüzden '|' karakterlerini
    boşluğa çevirip SADECE '-'/'|'/':' içeren ayırıcı satırları atarız.
    Regex/parser mantığı hiç değişmeden aynı şekilde çalışmaya devam eder."""
    satirlar = []
    for satir in metin.splitlines():
        s = satir.strip()
        if not s:
            satirlar.append(satir)
            continue
        if re.fullmatch(r"[\|\-\s:]+", s):
            continue  # "|---|---|" ayırıcı satırı - atla
        if "|" in s:
            s = " ".join(p.strip() for p in s.split("|") if p.strip())
        satirlar.append(s)
    return "\n".join(satirlar)


def _ocr_sayfa_ocrspace(im) -> Optional[str]:
    """Bir PIL Image'i OCR.space Engine 3 API'siyle metne çevirir.

    OCRSPACE_API_KEY ortam değişkeni yoksa veya herhangi bir hata olursa
    (ağ, kota, zaman aşımı, beklenmeyen yanıt) SESSİZCE None döner - hata
    fırlatmaz, çağıran taraf (_ocr_sayfa) bunu yerel Tesseract'a düşme
    sinyali olarak kullanır."""
    import os
    api_key = os.environ.get("OCRSPACE_API_KEY")
    if not api_key:
        return None
    try:
        import io
        import requests

        # Ücretsiz katman dosya boyutu sınırı 1 MB - JPEG kalitesini bu
        # sınırın güvenli şekilde altında kalacak şekilde kademeli düşür.
        buf = io.BytesIO()
        im_rgb = im.convert("RGB")
        kalite = 85
        while True:
            buf.seek(0)
            buf.truncate()
            im_rgb.save(buf, format="JPEG", quality=kalite)
            if buf.tell() < 950_000 or kalite <= 40:
                break
            kalite -= 15
        buf.seek(0)

        r = requests.post(
            "https://api.ocr.space/parse/image",
            headers={"apikey": api_key},
            files={"file": ("sayfa.jpg", buf, "image/jpeg")},
            data={"language": "auto", "OCREngine": 3, "isTable": "true"},
            timeout=60,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("IsErroredOnProcessing"):
            return None
        if data.get("OCRExitCode") not in (1, 2):
            return None
        sonuclar = data.get("ParsedResults") or []
        if not sonuclar:
            return None
        ham = sonuclar[0].get("ParsedText") or ""
        if not ham.strip():
            return None
        return _markdown_tablo_duzlestir(ham)
    except Exception:
        return None


def _ocr_sayfa(sayfa, resolution: int = 300) -> str:
    """Bir pdfplumber sayfasını görsele çevirip metne çevirir.

    Öncelik: OCR.space Engine 3 (bkz. modül başı not - 47/47 doğruluk).
    OCR.space kullanılamazsa (anahtar yok veya çağrı başarısız) yerel
    Türkçe Tesseract'a (eski davranış) sessizce düşülür.

    Not: --psm 4 bazı yoğun/çok sütunlu sayfalarda daha temiz sonuç verse de
    (ör. ORZAX örneğinde), TÜM sayfalara varsayılan olarak uygulandığında
    başka bir sayfada yanlış bir "Nihai Değer" benzeri örüntü oluşturup
    YANLIŞ bir sayının sessizce doğru kabul edilmesine yol açtığı gözlendi.
    Bu yüzden Tesseract yedeğinde güvenli tarafta kalınıp varsayılan
    (psm 3) kullanılıyor.
    """
    import sys
    im = sayfa.to_image(resolution=resolution).original

    ocrspace_metin = _ocr_sayfa_ocrspace(im)
    if ocrspace_metin is not None:
        print("[pdf_text_extract] OCR: OCR.space Engine 3 kullanildi", file=sys.stderr)
        return ocrspace_metin

    print("[pdf_text_extract] OCR: OCR.space kullanilamadi (anahtar yok veya "
          "hata) - yerel Tesseract'a dusuluyor", file=sys.stderr)
    import pytesseract
    return pytesseract.image_to_string(im, lang="tur")


def pdf_to_text(pdf_path: str, max_pages: Optional[int] = None,
                 ocr_resolution: int = 300) -> str:
    """
    PDF dosyasını düz metne çevirir. Her sayfa için önce metin katmanı
    denenir; yoksa otomatik olarak Türkçe OCR'a düşer. Sayfalar arasına
    çift satır sonu koyar ki regex'ler tablo/paragraf sınırlarını daha
    rahat ayırt edebilsin.

    max_pages: Fiyat Tespit Raporu'nun "Değerleme Sonucu" bölümü genelde
    son sayfalarda olur; çok sayfalı raporlarda (SOHO 64 sayfa gibi) OCR
    performans/maliyet açısından pahalı olduğundan sınırlama faydalı
    olabilir. None = tüm sayfalar.
    """
    import pdfplumber

    parcalar = []
    ocr_kullanilan_sayfalar = []

    with pdfplumber.open(pdf_path) as pdf:
        sayfalar = pdf.pages if max_pages is None else pdf.pages[:max_pages]
        for i, sayfa in enumerate(sayfalar):
            if _sayfa_metin_var_mi(sayfa):
                metin = sayfa.extract_text() or ""
            else:
                metin = _ocr_sayfa(sayfa, resolution=ocr_resolution)
                ocr_kullanilan_sayfalar.append(i)
            parcalar.append(metin)

    tam_metin = "\n\n".join(parcalar)

    if ocr_kullanilan_sayfalar:
        # Debug/log amaçlı: hangi sayfalarda OCR'a düşüldüğünü stderr'e yaz.
        import sys
        print(f"[pdf_to_text] OCR kullanılan sayfalar (0-indeks): "
              f"{ocr_kullanilan_sayfalar}", file=sys.stderr)

    return tam_metin


if __name__ == "__main__":
    import sys
    yol = sys.argv[1] if len(sys.argv) > 1 else None
    if not yol:
        print("Kullanım: python pdf_text_extract.py <pdf_yolu>")
        sys.exit(1)
    print(pdf_to_text(yol)[:3000])
