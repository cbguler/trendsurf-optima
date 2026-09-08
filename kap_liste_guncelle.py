"""
kap_liste_guncelle.py
======================
KAP_BIST.xlsx dosyasini KAP'in kendi "bist-sirketler" sayfasindan
otomatik olarak GUNCELLER - Bahri'nin talebi (16 Temmuz 2026):
"mevcut sirketleri taransın, eksik olanı benim formata göre eklesin".

NASIL CALISIR:
  1. https://kap.org.tr/tr/bist-sirketler sayfasini ceker (bu sayfa
     JS gerektirmeyen, sunucu tarafinda render edilmis duz HTML'dir -
     dogrulandi, VBA/Excel makrosunun basaramayacagi JS-render sorunu
     burada YOK).
  2. Sayfadaki her "[TICKER](.../sirket-bilgileri/ozet/{slug})" linkini
     regex ile ayiklayip ticker -> slug eslemesi cikarir.
  3. Mevcut KAP_BIST.xlsx'teki ticker listesiyle karsilastirir.
  4. YENI bulunan sirketleri, MEVCUT FORMATA (Ticker | Ad | KAP URL | bos)
     birebir uyacak sekilde, "sirket-finansal-bilgileri/{slug}" URL'si
     ile yeni bir dosyaya (KAP_BIST_guncel.xlsx) ekler - orijinal dosyaya
     DOKUNMAZ, boylece Bahri onaylamadan hicbir sey degismez.
  5. Kaybolan (borsadan cikmis/birlesmis olabilecek) sirketleri de
     ayrica raporlar - bunlar dosyadan OTOMATIK SILINMEZ, sadece
     bilgi amacli listelenir (Bahri karar verir).

BILEREK YARI-OTOMATIK: Bahri'nin acik talebi geregi yeni sirketler
sessizce/otomatik olarak canli sisteme dahil edilmez. Bu betik sadece
bir ONERI/TASLAK dosyasi (KAP_BIST_guncel.xlsx) uretir - Bahri inceleyip
onayladiktan sonra bu dosyayi KAP_BIST.xlsx olarak repoya yukler.

KULLANIM:
  python kap_liste_guncelle.py
  (KAP_BIST.xlsx ile ayni klasorde calistirilmali)

CIKTI:
  - Ekrana: yeni bulunan / kaybolan sirketlerin listesi
  - KAP_BIST_guncel.xlsx: mevcut dosya + yeni sirketler eklenmis hali
"""
import re
import sys
import requests
import pandas as pd
from datetime import datetime

KAP_URL = "https://kap.org.tr/tr/bist-sirketler"
MEVCUT_DOSYA = "KAP_BIST.xlsx"
CIKTI_DOSYA = "KAP_BIST_guncel.xlsx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# [TICKER](.../sirket-bilgileri/ozet/{slug})  -> hem ticker hem ad ayni
# linki kullandigi icin ikisi de eslesir, asagida tekillestiriliyor.
TICKER_SLUG_DESENI = re.compile(
    r"\[([A-Z0-9\s]+)\]\(https://kap\.org\.tr/tr/sirket-bilgileri/ozet/([a-z0-9\-]+)\)"
)


def kap_sirket_listesini_cek() -> dict:
    """KAP'in bist-sirketler sayfasindan CANLI ticker->slug esemesi ceker."""
    print(f"[{datetime.now():%H:%M:%S}] KAP'tan sirket listesi cekiliyor: {KAP_URL}")
    r = requests.get(KAP_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    if len(r.text) < 5000:
        raise RuntimeError(
            "Sayfa icerigi cok kisa geldi - KAP'in sayfa yapisi degismis "
            "olabilir, bu betigin regex'inin guncellenmesi gerekebilir."
        )

    sonuc = {}
    for ticker_grubu, slug in TICKER_SLUG_DESENI.findall(r.text):
        for t in ticker_grubu.split():
            t = t.strip().upper()
            if t and t not in sonuc:
                sonuc[t] = slug
    print(f"[{datetime.now():%H:%M:%S}] KAP'tan {len(sonuc)} sirket/ticker cekildi.")
    return sonuc


def mevcut_dosyayi_oku(yol: str) -> tuple[pd.DataFrame, dict]:
    """Mevcut KAP_BIST.xlsx'i okur, ticker->slug eslemesini cikarir."""
    df = pd.read_excel(yol, header=None)
    mevcut_slug = {}
    for _, row in df.iterrows():
        ticker_raw = str(row.iloc[0]).strip()
        url_raw = str(row.iloc[2]).strip() if len(row) > 2 else ""
        if ticker_raw in ("nan", "") or url_raw in ("nan", ""):
            continue
        slug = url_raw.rstrip("/").split("/")[-1]
        for t in ticker_raw.split(","):
            t = t.strip().upper()
            if t:
                mevcut_slug[t] = slug
    return df, mevcut_slug


def main():
    kap_canli = kap_sirket_listesini_cek()
    df_mevcut, mevcut_slug = mevcut_dosyayi_oku(MEVCUT_DOSYA)
    print(f"[{datetime.now():%H:%M:%S}] Mevcut dosyada {len(mevcut_slug)} ticker var.")

    yeni_tickerlar = sorted(set(kap_canli) - set(mevcut_slug))
    kaybolan_tickerlar = sorted(set(mevcut_slug) - set(kap_canli))

    print("\n" + "=" * 60)
    print(f"YENİ BULUNAN {len(yeni_tickerlar)} ŞİRKET (dosyaya eklenecek):")
    for t in yeni_tickerlar:
        print(f"  + {t}  ->  {kap_canli[t]}")

    print(f"\nKAYBOLAN {len(kaybolan_tickerlar)} ŞİRKET (bilgi amaçlı, OTOMATİK SİLİNMEDİ):")
    for t in kaybolan_tickerlar:
        print(f"  - {t}  (borsadan çıkmış/birleşmiş olabilir, kontrol edin)")
    print("=" * 60 + "\n")

    if not yeni_tickerlar:
        print("Eklenecek yeni şirket yok, dosya zaten güncel.")
        return

    yeni_satirlar = []
    for t in yeni_tickerlar:
        slug = kap_canli[t]
        # Ad bilgisi bu sayfada ayri bir alan olarak gelmiyor (ticker ve ad
        # ayni linki paylasiyor) - slug'dan okunabilir bir ad turetiliyor,
        # Bahri dosyayi acinca gerekirse elle duzeltebilir.
        ad_tahmini = slug.split("-", 1)[1].replace("-", " ").upper() if "-" in slug else slug.upper()
        url = f"https://kap.org.tr/tr/sirket-finansal-bilgileri/{slug}"
        yeni_satirlar.append([t, ad_tahmini, url, None])

    df_yeni = pd.DataFrame(yeni_satirlar)
    df_sonuc = pd.concat([df_mevcut, df_yeni], ignore_index=True)
    df_sonuc.to_excel(CIKTI_DOSYA, header=False, index=False)
    print(f"'{CIKTI_DOSYA}' oluşturuldu — {len(yeni_tickerlar)} yeni satır eklendi.")
    print("Lütfen inceleyip onayladıktan sonra bu dosyayı KAP_BIST.xlsx olarak")
    print("projeye yükleyin (isim/ünvan alanlarını gerekirse düzeltin).")


if __name__ == "__main__":
    main()
