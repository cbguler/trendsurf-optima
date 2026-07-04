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


# --- OCR toleransı: Türkçe karaktersiz (ASCII-katlanmış) eşleştirme ----------
# Taranmış/görsel PDF'lerde Tesseract Türkçe karakterleri (ş, ı, ğ, ö, ü, ç)
# sıklıkla bozuyor (örn. "Değer" -> "Deger", "Başına" -> "Basina"). Bu yüzden
# etiket eşleştirmesi HER ZAMAN normalize edilmiş (ASCII-katlanmış) metin
# üzerinde yapılır. Karakter-karakter (1-e-1) bir çeviri olduğu için string
# uzunluğu/konumları değişmez - sayıları (rakam/noktalama) etkilemez, bu
# yüzden normalize edilmiş metinden yakalanan sayı gruplari orijinaliyle
# birebir aynıdır.
_TR_NORMALIZE_MAP = str.maketrans({
    "ş": "s", "Ş": "S", "İ": "I", "ı": "i", "I": "I",
    "ğ": "g", "Ğ": "G", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U",
    "ç": "c", "Ç": "C",
})


def _normalize_tr(metin: str) -> str:
    return metin.translate(_TR_NORMALIZE_MAP)


_NUM = r"([\d\.,]+)"

# --- TİP A: kademeli tek akış -------------------------------------------------
# Not: etiketler ASCII-katlanmış (normalize edilmiş) yazılıyor çünkü eşleştirme
# HER ZAMAN _normalize_tr() uygulanmış metin üzerinde yapılıyor (bkz. asağıda
# _iskonto_bul/_tip_*_dene fonksiyonları) - bu, OCR'ın "Değer"i "Deger" olarak
# okuduğu (Türkçe karakteri kaybettiği) durumlarda da eşleşmeyi sağlar.
_TIP_A_ETIKETLER = [
    r"Halka Arz Pay Basina Deger",
    r"Iskonto Sonrasi\s+1\s*TL\s*Nominal Pay Degeri",
    r"Iskonto Sonrasi\s+Pay\s+Degeri",
    r"Iskonto Sonrasi.*?Nominal Pay Degeri",
]

# --- TİP B: ağırlıklı özet tablosu (Nihai Değer satırı) ----------------------
_TIP_B_BASLIK = r"Degerleme Ozeti"
# "Nihai" -> OCR bazen "Nihal"/"Nihai" -> "1" okuyor (ı/l/1 karışıklığı)
_TIP_B_NIHAI_SATIR = r"Niha[iI1lL]\s+Deger\s+" + _NUM + r"\s+.*?" + _NUM

# --- TİP C: Değerleme Sonucu tablosu (doğrudan "Halka Arz Fiyatı") -----------
_TIP_C_BASLIK = r"Degerleme Sonucu"
_TIP_C_ETIKET = r"Halka Arz Fiyati\s*" + _NUM

# --- İskonto oranı (tüm tipler için ortak arama) -----------------------------
_ISKONTO_PATTERNS = [
    r"Halka Arz Iskontosu[^%\d]*?(-?\d{1,3}[.,]?\d{0,2})\s*%",
    r"Halka Arz Iskontosu[^%\d]*?%\s*(\d{1,3}[.,]?\d{0,2})",
    r"%\s*(\d{1,3}[.,]?\d{0,2})\s*(?:oraninda )?halka arz iskontosu",
    r"halka arz iskontosunun.*?%\s*(\d{1,3}[.,]?\d{0,2})",
    # OCR fallback: "%" karakteri taranmış PDF'lerde sıkça bozuluyor
    # (örn. "%37,00" -> "637,00" veya "37,009"). Bu yüzden yüzde işareti
    # şart koşulmadan, etiketten hemen sonraki sayıyı da kabul ediyoruz.
    # Düşük öncelikli (en son denenir) çünkü daha az güvenilir.
    r"Halka Arz Iskontosu\s*[:\-]?\s*(\d{1,3}[.,]\d{2})",
]


def _iskonto_bul(metin: str) -> Optional[float]:
    metin_n = _normalize_tr(metin)
    for pat in _ISKONTO_PATTERNS:
        m = re.search(pat, metin_n, re.IGNORECASE | re.DOTALL)
        if m:
            val = _tr_sayi_to_float(m.group(1))
            if val is not None:
                return abs(val)
    return None


def _tip_a_dene(metin: str) -> Optional[FiyatTespitSonucu]:
    metin_n = _normalize_tr(metin)
    for etiket in _TIP_A_ETIKETLER:
        # etiketten sonra gelen ilk sayısal değeri yakala (aynı satır veya
        # tablo hücresi olabileceğinden esnek boşluk/karakter toleransı)
        pat = etiket + r"[^\d\-]{0,40}" + _NUM
        m = re.search(pat, metin_n, re.IGNORECASE | re.DOTALL)
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
    metin_n = _normalize_tr(metin)
    m = re.search(_TIP_B_NIHAI_SATIR, metin_n, re.IGNORECASE | re.DOTALL)
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
    metin_n = _normalize_tr(metin)
    m = re.search(_TIP_C_ETIKET, metin_n, re.IGNORECASE | re.DOTALL)
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


# --- TİP D: anlatım cümlesi (çok sütunlu tablolar OCR'da bozulunca) ----------
# GOLDA örneğinde görüldü: iki sütunlu "Halka Arza İlişkin Bilgiler" tablosu
# OCR tarafından "önce tüm etiketler, sonra tüm değerler" şeklinde (sütun
# sütun) okunuyor - bu da etiketle sayıyı birbirinden yüzlerce karakter
# uzağa düşürüyor, Tip A/B/C'nin "etiket + yakın sayı" mantığı bu durumda
# hiç çalışmıyor. Ama raporlar genelde AYRICA duz bir anlatım cümlesiyle de
# sonucu tekrarlıyor - örn. GOLDA: "...pay başına değer 9,20 TL olarak
# belirlenmiş olup..." / TSK (Beta Enerji): "...halka arz birim pay fiyat,
# 40,00 TL olarak hesaplanmıştır...". Bu cümleler duz metin oldugu icin OCR
# kalitesi tablo hücrelerine gore cok daha iyi oluyor. "halka arz" ifadesinden
# sonraki (80 karaktere kadar) ilk sayı + "TL olarak" kalıbını arıyoruz.
_TIP_D_PATTERNS = [
    r"halka\s+arz[^\d]{0,80}" + _NUM + r"\s*TL\s+olarak",
]


def _tip_d_dene(metin: str) -> Optional[FiyatTespitSonucu]:
    metin_n = _normalize_tr(metin)
    for pat in _TIP_D_PATTERNS:
        for m in re.finditer(pat, metin_n, re.IGNORECASE | re.DOTALL):
            # Guvenlik kontrolu: bazi raporlarda ONCE iskonto-oncesi
            # (ara) deger anlatim cumlesiyle veriliyor, hemen ardindan
            # "%X halka arz iskontosu sonrasi..." diye devam ediyor - bu
            # durumda yakaladigimiz sayi YANLIS (nihai arz fiyati degil,
            # iskonto uygulanmadan onceki ara deger). Eslesmeden sonraki
            # ~200 karakterde "iskontosu sonras" gecerse bu sinyal olarak
            # kabul edilip bu eslesme atlanir, bir sonraki denenir.
            sonrasi = metin_n[m.end(): m.end() + 200]
            if re.search(r"iskontosu\s+sonras", sonrasi, re.IGNORECASE):
                continue
            deger = _tr_sayi_to_float(m.group(1))
            if deger is not None:
                return FiyatTespitSonucu(
                    tip="D",
                    arz_fiyati=deger,
                    iskonto_orani=_iskonto_bul(metin),
                    eslesen_etiket="Anlatım cümlesi ('halka arz ... TL olarak')",
                    ham_deger_metni=m.group(0),
                )
    return None


def fiyat_tespit_ayikla(metin: str) -> FiyatTespitSonucu:
    """
    Fiyat Tespit Raporu metnini (PDF'ten çıkarılmış text) alır, arz fiyatı ve
    iskonto oranını üç bilinen tabloya göre çıkarmaya çalışır.

    Öncelik sırası: C -> B -> A -> D
    (C ve B daha spesifik başlıklara bağlı olduğundan yanlış pozitif riski
    daha düşük; A tablo-tabanlı gevşek eşleşme; D en son denenir çünkü
    duz anlatım cümlesine dayanıyor, tablo eşleşmesi kadar spesifik değil.)
    """
    for fn in (_tip_c_dene, _tip_b_dene, _tip_a_dene, _tip_d_dene):
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
