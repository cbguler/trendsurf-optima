# -*- coding: utf-8 -*-
"""
spk_tedbir_fonlari.py - SPK tarafindan TEFAS'ta islem/alim-satima
kapatilan veya tasfiye kararı verilen portfoy yonetim sirketlerinin
listesi.

v2.0.7.322 (17 Eylul 2026, Bahri'nin bulgusu/talebi - SPK'nin 17 Eylul
2026 tarihli ve 2026/60 sayili Bulteni): Pusula Portföy'de başlayan ve
Tera Portföy'un iki fonunda temerrut ilanina kadar buyuyen likidite
krizi sonrasi SPK, Tera/Pusula/Hedef/Atlas/A1 Capital/Pardus/Bulls
Portföy olmak uzere 7 portfoy yonetim sirketinin (PYS) TEFAS'ta islem
goren TUM yatirim fonlarinin alim ve satima kapatilmasina, bunlardan
toplam 130 tanesinin de Kurulca belirlenecek yontemle tasfiye
edilmesine karar verdi (kaynak: SPK 17.09.2026 tarihli 2026/60 sayili
Haftalik Bulteni). ONEMLI: karar hisse senetlerini DEGIL, sadece bu 7
sirketin kurdugu TEFAS fonlarini kapsiyor.

Karar SIRKET bazinda TUM fonlari kapsadigi icin (sadece tasfiye
listesindeki 130 fon degil - trendsurf-optima evreninde bu 7 sirkete
ait toplam 117 fon bulundu, tasfiye listesindeki 130'un TAMAMI degil
ama hepsi ayni sekilde islem goremez durumda), burada TICKER bazinda
degil SIRKET ADI bazinda eslestirme yapiliyor - boylece bu sirketlerin
CSV'ye yeni girecek/simdi eksik olan fonlari da otomatik yakalanir.

Bu liste SPK'nin karari GECERLI oldugu surece burada kalmali. Karar
kaldirilir/degisirse (SPK'nin yeni bir bulteniyle) buradan
cikarilmali - kap_bildirim_izleme.py / haber_izleme.py gelecekte bu
tur SPK/KAP bultenlerini otomatik izleyip bu listeyi guncelleyecek
sekilde genisletilebilir (Bahri'nin talebi, henuz YAPILMADI - bkz.
PROJE_NOTLARI.md).
"""

TASFIYE_KAPSAMINDAKI_SIRKETLER = [
    "TERA PORTFÖY",
    "PUSULA PORTFÖY",
    "HEDEF PORTFÖY",
    "ATLAS PORTFÖY",
    "A1 CAPİTAL PORTFÖY",
    "A1 PORTFÖY",
    "PARDUS PORTFÖY",
    "BULLS PORTFÖY",
]


def tasfiye_kapsaminda_mi(ad: str) -> bool:
    """Bir TEFAS fonunun adi, SPK tarafindan TEFAS'ta alim-satima
    kapatilan 7 portfoy yonetim sirketinden birine ait olup olmadigini
    kontrol eder (sirket adi, fon adinin herhangi bir yerinde
    gecebilir - fon adlari genelde sirket adiyla baslar ama bazen
    kurucu unvanindan sonra gelir, orn. emeklilik fonlarinda)."""
    if not ad:
        return False
    ad_u = str(ad).upper()
    return any(sirket in ad_u for sirket in TASFIYE_KAPSAMINDAKI_SIRKETLER)
