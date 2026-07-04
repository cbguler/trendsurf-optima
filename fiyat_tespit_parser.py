"""
fiyat_tespit_parser.py

Fiyat Tespit Raporu PDF'lerinden (metne çevrilmiş haliyle) halka arz fiyatı
ve iskonto oranını çıkaran parser.

Şu ana kadar gözlemlenen 3 tablo mimarisi (4 örnek rapor üzerinden):

  TİP A — Kademeli tek akış (Gedik/GOLDA, Halk Yatırım/İSVEA)
    "... Özsermaye Değeri -> İskonto -> İskonto Sonrası Pay Değeri (=arz fiyatı)"
    Etiket varyasyonları:
      - "Halka Arz Pay Başına Değer"
      - "İskonto Sonrası 1 TL Nominal Pay Değeri"
      - "İskonto Sonrası Pay Değeri"

  TİP B — Ağırlıklı özet tablosu (İnfo Yatırım/ORZAX)
    "Değerleme Özeti" tablosu: İNA + Yurtdışı Benzerler + BİST çarpanı satırları,
    en altta "Halka Arz Piyasa Değer" -> "Halka Arz İskontosu" -> "Nihai Değer"
    satırı ve o satıra karşılık gelen "Pay Başı Değer (TL)" sütunu.

  TİP C — Değerleme Sonucu tablosu (İntegral/SOHO)
    "... Değerleme Sonucu" başlıklı tablo; satırlar:
      Özkaynak Değeri / Halka Arz İskontosu / İskontolu Özkaynak Değeri /
      Çıkarılmış Sermaye / "Halka Arz Fiyatı" (doğrudan arz fiyatı, en açık etiket)

Not: Bu modül düz metin (PDF'ten çıkarılmış text) üzerinde çalışır.
PDF -> text dönüşümü upcoming_ipo_client.py tarafındaki mevcut extraction
akışıyla (pdfplumber / pypdf, hangisi kullanılıyorsa) sağlanmalı.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class FiyatTespitSonucu:
    tip: str                     # "A", "B", "C" veya "BILINMEYEN"
    arz_fiyati: Optional[float]  # TL, pay başına
    iskonto_orani: Optional[float]  # yüzde, örn. 20.0 = %20
    eslesen_etiket: Optional[str]   # hangi regex/etiket eşleşti (debug için)
    ham_deger_metni: Optional[str]  # eşleşen ham metin parçası


def _tr_sayi_to_float(s: str) -> Optional[float]:
    """'69,00' -> 69.0 ,  '1.500.000.000' -> 1500000000.0"""
    if not s:
        return None
    s = s.strip()
    # Türkçe format: nokta binlik ayraç, virgül ondalık ayraç
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


_NUM = r"([\d\.,]+)"

# --- TİP A: kademeli tek akış -------------------------------------------------
_TIP_A_ETIKETLER = [
    r"Halka Arz Pay Başına Değer",
    r"İskonto Sonrası\s+1\s*TL\s*Nominal Pay Değeri",
    r"İskonto Sonrası\s+Pay\s+Değeri",
    r"İskonto Sonrası.*?Nominal Pay Değeri",
]

# --- TİP B: ağırlıklı özet tablosu (Nihai Değer satırı) ----------------------
_TIP_B_BASLIK = r"Değerleme Özeti"
# "Nihai" -> OCR bazen "Nihal" okuyor (ı/l karışıklığı); [iİlİ] ile tolere ediyoruz
_TIP_B_NIHAI_SATIR = r"Niha[iİlL]\s+Değer\s+" + _NUM + r"\s+.*?" + _NUM

# --- TİP C: Değerleme Sonucu tablosu (doğrudan "Halka Arz Fiyatı") -----------
_TIP_C_BASLIK = r"Değerleme Sonucu"
_TIP_C_ETIKET = r"Halka Arz Fiyatı\s*" + _NUM

# --- İskonto oranı (tüm tipler için ortak arama) -----------------------------
_ISKONTO_PATTERNS = [
    r"Halka Arz İskontosu[^%\d]*?(-?\d{1,3}[.,]?\d{0,2})\s*%",
    r"Halka Arz İskontosu[^%\d]*?%\s*(\d{1,3}[.,]?\d{0,2})",
    r"%\s*(\d{1,3}[.,]?\d{0,2})\s*(?:oranında )?halka arz iskontosu",
    r"halka arz iskontosunun.*?%\s*(\d{1,3}[.,]?\d{0,2})",
    # OCR fallback: "%" karakteri taranmış PDF'lerde sıkça bozuluyor
    # (örn. "%37,00" -> "637,00" veya "37,009"). Bu yüzden yüzde işareti
    # şart koşulmadan, etiketten hemen sonraki sayıyı da kabul ediyoruz.
    # Düşük öncelikli (en son denenir) çünkü daha az güvenilir.
    r"Halka Arz İskontosu\s*[:\-]?\s*(\d{1,3}[.,]\d{2})",
]


def _iskonto_bul(metin: str) -> Optional[float]:
    for pat in _ISKONTO_PATTERNS:
        m = re.search(pat, metin, re.IGNORECASE | re.DOTALL)
        if m:
            val = _tr_sayi_to_float(m.group(1))
            if val is not None:
                return abs(val)
    return None


def _tip_a_dene(metin: str) -> Optional[FiyatTespitSonucu]:
    for etiket in _TIP_A_ETIKETLER:
        # etiketten sonra gelen ilk sayısal değeri yakala (aynı satır veya
        # tablo hücresi olabileceğinden esnek boşluk/karakter toleransı)
        pat = etiket + r"[^\d\-]{0,40}" + _NUM
        m = re.search(pat, metin, re.IGNORECASE | re.DOTALL)
        if m:
            deger = _tr_sayi_to_float(m.group(1))
            if deger is not None:
                return FiyatTespitSonucu(
                    tip="A",
                    arz_fiyati=deger,
                    iskonto_orani=_iskonto_bul(metin),
                    eslesen_etiket=etiket,
                    ham_deger_metni=m.group(0),
                )
    return None


def _tip_b_dene(metin: str) -> Optional[FiyatTespitSonucu]:
    # Not: "Değerleme Özeti" başlığı OCR'da bozulabileceğinden ön koşul
    # olarak aranmıyor; "Nihai Değer" satırı zaten yeterince spesifik.
    m = re.search(_TIP_B_NIHAI_SATIR, metin, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    # "Nihai Değer   21.183   ...   69,00" -> son yakalanan grup pay başı değeri
    pay_basi = _tr_sayi_to_float(m.group(2))
    return FiyatTespitSonucu(
        tip="B",
        arz_fiyati=pay_basi,
        iskonto_orani=_iskonto_bul(metin),
        eslesen_etiket="Nihai Değer (ağırlıklı özet tablo)",
        ham_deger_metni=m.group(0),
    )


def _tip_c_dene(metin: str) -> Optional[FiyatTespitSonucu]:
    # Not: "Değerleme Sonucu" başlığını ön koşul olarak ARAMIYORUZ.
    # OCR (özellikle taranmış/görsel PDF'lerde) tablo başlık satırlarını
    # renkli/arka planlı hücre olduğu için genelde eksik veya bozuk okuyor
    # (örn. "Değerleme Sonucu" -> sadece "Değerle"). "Halka Arz Fiyatı" +
    # sayı kombinasyonu tek başına zaten yeterince ayırt edici bir etiket.
    m = re.search(_TIP_C_ETIKET, metin, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    deger = _tr_sayi_to_float(m.group(1))
    if deger is None:
        return None
    return FiyatTespitSonucu(
        tip="C",
        arz_fiyati=deger,
        iskonto_orani=_iskonto_bul(metin),
        eslesen_etiket="Halka Arz Fiyatı (Değerleme Sonucu tablosu)",
        ham_deger_metni=m.group(0),
    )


def fiyat_tespit_ayikla(metin: str) -> FiyatTespitSonucu:
    """
    Fiyat Tespit Raporu metnini (PDF'ten çıkarılmış text) alır, arz fiyatı ve
    iskonto oranını üç bilinen tabloya göre çıkarmaya çalışır.

    Öncelik sırası: C -> B -> A
    (C ve B daha spesifik başlıklara bağlı olduğundan yanlış pozitif riski
    daha düşük; A en genel/gevşek eşleşme olduğundan son sırada denenir.)
    """
    for fn in (_tip_c_dene, _tip_b_dene, _tip_a_dene):
        sonuc = fn(metin)
        if sonuc is not None:
            return sonuc

    return FiyatTespitSonucu(
        tip="BILINMEYEN",
        arz_fiyati=None,
        iskonto_orani=_iskonto_bul(metin),
        eslesen_etiket=None,
        ham_deger_metni=None,
    )


if __name__ == "__main__":
    # Hızlı manuel test için minik örnekler (gerçek rapor metinlerinden kısaltılmış)
    ornek_b = """
    Değerleme Özeti
    Metodolojiler Değer Ağırlık Pay Başı Değer (TL)
    İNA 24.504 50,0% 79,82
    Halka Arz Piyasa Değer 26.557 100% 86,51
    Halka Arz İskontosu -20%
    Nihai Değer 21.183 69,00
    """
    ornek_c = """
    Soho Giyim ve Enerji A.Ş. Değerleme Sonucu
    Özkaynak Değeri 4.923.634.174
    Halka Arz İskontosu 37,00%
    İskontolu Özkaynak Değeri 3.101.889.529
    Halka Arz Fiyatı 15,00
    """
    ornek_a = """
    Halka Arz Öncesi 1 TL Nominal Pay Değeri 28,64
    Halka Arz İskontosu %27,03
    İskonto Sonrası 1 TL Nominal Pay Değeri 20,90
    """

    for isim, ornek in [("B (ORZAX)", ornek_b), ("C (SOHO)", ornek_c), ("A (İSVEA)", ornek_a)]:
        r = fiyat_tespit_ayikla(ornek)
        print(f"--- {isim} ---")
        print(r)
        print()
