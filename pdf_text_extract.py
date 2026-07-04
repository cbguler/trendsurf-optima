"""
pdf_text_extract.py

Fiyat Tespit Raporu PDF'lerini düz metne çeviren yardımcı fonksiyon.

Akış:
  1) Önce pdfplumber ile normal metin katmanı denenir (İntegral/SOHO gibi
     metin tabanlı raporlar için hızlı ve %100 doğru).
  2) Sayfada metin katmanı yoksa (KAP'a gönderilen çoğu Fiyat Tespit Raporu
     taranmış/görsel PDF olabiliyor — Gedik, Halk Yatırım, İnfo Yatırım
     örneklerinde gözlemlendi) sayfa görsele çevrilip Türkçe OCR
     (tesseract + tur dil paketi) ile metne çevrilir.

requirements.txt'e eklenmesi gerekenler: pdfplumber, pypdf, pytesseract
Sistem paketi (GitHub Actions / apt): tesseract-ocr, tesseract-ocr-tur
  -> apt-get install -y tesseract-ocr tesseract-ocr-tur
"""

from typing import Optional


def _sayfa_metin_var_mi(sayfa) -> bool:
    """pdfplumber sayfasında gerçek metin karakteri (char objesi) var mı."""
    try:
        return len(sayfa.chars) > 0
    except Exception:
        return False


def _ocr_sayfa(sayfa, resolution: int = 300) -> str:
    """Bir pdfplumber sayfasını görsele çevirip Türkçe OCR ile metne çevirir.

    Not: --psm 4 bazı yoğun/çok sütunlu sayfalarda daha temiz sonuç verse de
    (ör. ORZAX örneğinde), TÜM sayfalara varsayılan olarak uygulandığında
    başka bir sayfada yanlış bir "Nihai Değer" benzeri örüntü oluşturup
    YANLIŞ bir sayının sessizce doğru kabul edilmesine yol açtığı gözlendi.
    Bu yüzden güvenli tarafta kalınıp varsayılan (psm 3) kullanılıyor;
    zor sayfalar için hedefli/sayfa bazlı psm ayarı ayrı bir iyileştirme
    konusu olarak bırakılmıştır.
    """
    import pytesseract
    im = sayfa.to_image(resolution=resolution).original
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
