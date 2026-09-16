# -*- coding: utf-8 -*-
"""
enag_izleme.py — TrendSurf Optima (v2.0.7.314, 16 Eylül 2026, O&M4,
Bahri'nin talebi)

DENEYSEL ilk deneme: ENAG'ın aylık E-TÜFE bülteni PDF'ini OTOMATIK
çekip aylık oranı çıkarmaya çalışır. Bahri'nin kendisi bunun "belki
işe yarar belki yaramaz" bir deneme olduğunu, elle giriş sisteminin
(app.py'deki "ENAG Aylık Enflasyon Oranlarını Gir" bölümü) HER
DURUMDA yedek olarak kaldığını onayladı.

NEDEN BELİRSİZ: enagrup.org, Claude'un kendi test ortamından TAMAMEN
ERİŞİLEMEZ bulundu - bu bir robots.txt kuralı DEĞİL, Cloudflare'in
bağlantıyı TLS aşamasında reddetmesi (HTTP 525), HEM ana sayfa HEM
PDF dosyaları için aynı şekilde. Bu engelin GitHub Actions runner'ının
FARKLI ağ kökeninden de geçerli olup olmadığı BİLİNMİYOR - bu script
bunu CANLI olarak test ediyor. Ayrıca bültenin GERÇEK HTML yapısı ve
metin ifadesi (hangi cümle kalıbıyla oranın yazıldığı) hiç
GÖRÜLEMEDİ - aşağıdaki regex'ler kamuya açık haber alıntılarından
("E-TÜFE ... yüzde X,XX artmıştır" gibi) türetildi, TAHMİNİ - gerçek
bülten metniyle eşleşmeyebilir.

BAŞARISIZLIK STRATEJİSİ: her adımda AYRINTILI log yazdırır - hangi
adımda (bağlantı mı, sayfa yapısı mı, regex mi) durduğunu KESİN
olarak göstermek için. Herhangi bir adım başarısız olursa DÜŞÜK
GÜVENLE bir sayı UYDURMAZ - sessizce çıkar, veritabanına HİÇBİR ŞEY
yazmaz, elle giriş yedek olarak kalır."""
import os
import re
import sys
import tempfile

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
}


def _son_bulten_pdf_linkini_bul() -> str:
    """ENAG ana sayfasını çeker, içindeki bülten PDF linklerini
    (regex: .../bulten/<sayı>.pdf) bulur, en YÜKSEK sayılı olanı
    (muhtemelen en yeni) döner. Bulamazsa boş string döner."""
    try:
        r = requests.get("https://enagrup.org/", headers=_HEADERS, timeout=20)
        print(f"[enag_izleme] Ana sayfa HTTP durumu: {r.status_code}")
        if r.status_code != 200:
            return ""
        _linkler = re.findall(r'https?://enagrup\.org/bulten/(\d+)\.pdf', r.text)
        if not _linkler:
            # Bagil (goreli) link olabilir - domain olmadan da dene.
            _linkler = re.findall(r'/bulten/(\d+)\.pdf', r.text)
        if not _linkler:
            print("[enag_izleme] Ana sayfada bulten PDF linki bulunamadi - "
                  "sayfa yapisi degismis olabilir.")
            return ""
        _en_yuksek = max(_linkler, key=int)
        _url = f"https://enagrup.org/bulten/{_en_yuksek}.pdf"
        print(f"[enag_izleme] Bulunan en guncel bulten: {_url}")
        return _url
    except Exception as e:
        print(f"[enag_izleme] Ana sayfa cekilemedi: {type(e).__name__}: {e}")
        return ""


def _bulten_pdf_indir(url: str) -> str:
    """PDF'i indirir, gecici bir dosyaya yazar, dosya yolunu doner.
    Basarisizsa bos string doner."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=30)
        print(f"[enag_izleme] PDF indirme HTTP durumu: {r.status_code}, "
              f"boyut: {len(r.content)} bayt")
        if r.status_code != 200 or len(r.content) < 1000:
            return ""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(r.content)
            return tmp.name
    except Exception as e:
        print(f"[enag_izleme] PDF indirilemedi: {type(e).__name__}: {e}")
        return ""


def _bulten_metninden_oran_cikar(metin: str):
    """DENEYSEL - gercek bulten metni hic GORULMEDIGI icin bu
    kaliplarin gercekte eslesip eslesmeyecegi BILINMIYOR. Bircok olasi
    ifade kalibi deneniyor, ilk eslesen kullanilir. (oran, kalip_aciklamasi)
    ya da (None, None) doner."""
    _kaliplar = [
        (r"E-?T[ÜU]FE[’'`]?[^.]{0,80}?yüzde\s+([\d]+[,.][\d]+)", "E-TÜFE ... yüzde X"),
        (r"aylık\s+(?:bazda\s+)?%?\s*([\d]+[,.][\d]+)\s*(?:oranında)?\s*art", "aylık % X arttı"),
        (r"bir\s+önceki\s+aya\s+göre\s+%?\s*([\d]+[,.][\d]+)", "bir önceki aya göre % X"),
        (r"aylık\s+değişim[^0-9]{0,20}%?\s*([\d]+[,.][\d]+)", "aylık değişim: % X"),
    ]
    for _desen, _aciklama in _kaliplar:
        _m = re.search(_desen, metin, re.IGNORECASE)
        if _m:
            try:
                _oran = float(_m.group(1).replace(",", "."))
                if 0 < _oran < 30:  # makul aylik enflasyon araligi - guvenlik kontrolu
                    return _oran, _aciklama
            except ValueError:
                continue
    return None, None


def calistir():
    print("[enag_izleme] Baslangic - bu DENEYSEL bir ilk deneme, "
          "basarisiz olursa elle giris yedek olarak kalir.")

    _pdf_url = _son_bulten_pdf_linkini_bul()
    if not _pdf_url:
        print("[enag_izleme] DURDURULDU: bulten linki bulunamadi. "
              "Elle giris kullanilmaya devam edilmeli.")
        return

    _pdf_yolu = _bulten_pdf_indir(_pdf_url)
    if not _pdf_yolu:
        print("[enag_izleme] DURDURULDU: PDF indirilemedi.")
        return

    try:
        from pdf_text_extract import pdf_to_text
        _metin = pdf_to_text(_pdf_yolu, max_pages=3)
        print(f"[enag_izleme] PDF'ten {len(_metin)} karakter metin cikarildi "
              f"(ilk 3 sayfa).")
    except Exception as e:
        print(f"[enag_izleme] DURDURULDU: PDF metne cevrilemedi: "
              f"{type(e).__name__}: {e}")
        return
    finally:
        try:
            os.unlink(_pdf_yolu)
        except Exception:
            pass

    _oran, _kalip = _bulten_metninden_oran_cikar(_metin)
    if _oran is None:
        print("[enag_izleme] DURDURULDU: metin icinde taninan bir oran "
              "kalibi bulunamadi - bulten ifadesi tahmin edilenden "
              "FARKLI olabilir. Ilk 1500 karakter (elle kontrol icin):")
        print(_metin[:1500])
        return

    print(f"[enag_izleme] Oran BULUNDU: %{_oran} (eslesen kalip: '{_kalip}') - "
          f"ANCAK hangi aya ait oldugu METIN ICERISINDEN GUVENILIR sekilde "
          f"COZULEMEDI (ay/yil ayri bir dogrulama gerektirir). Bu yuzden "
          f"OTOMATIK KAYDEDILMIYOR - sonuc sadece log'a yaziliyor, Bahri'nin "
          f"gozden gecirip dogruysa elle onaylamasi/girmesi bekleniyor.")
    print(f"[enag_izleme] Bitti.")


if __name__ == "__main__":
    calistir()
