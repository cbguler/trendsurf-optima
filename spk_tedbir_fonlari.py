# -*- coding: utf-8 -*-
"""
spk_tedbir_fonlari.py - SPK'nin Eylul 2026 fon/manipulasyon krizi
kapsaminda tedbir aldigi TEFAS fonlari VE BIST hisseleri listesi.

v2.0.7.322 (17 Eylul 2026, Bahri'nin bulgusu/talebi - SPK'nin 17 Eylul
2026 tarihli ve 2026/60 sayili Bulteni): Pusula Portföy'de başlayan ve
Tera Portföy'un iki fonunda temerrut ilanina kadar buyuyen likidite
krizi sonrasi SPK, Tera/Pusula/Hedef/Atlas/A1 Capital/Pardus/Bulls
Portföy olmak uzere 7 portfoy yonetim sirketinin (PYS) TEFAS'ta islem
goren TUM yatirim fonlarinin alim ve satima kapatilmasina, bunlardan
toplam 130 tanesinin de Kurulca belirlenecek yontemle tasfiye
edilmesine karar verdi (kaynak: SPK 17.09.2026 tarihli 2026/60 sayili
Haftalik Bulteni). ONEMLI: bu KARAR hisse senetlerini DEGIL, sadece bu
7 sirketin kurdugu TEFAS fonlarini kapsiyor - hisse tarafi asagida
AYRI bir mekanizma (v2.0.7.331).

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


# v2.0.7.331 (20 Eylul 2026, Bahri'nin talebi - "fon krizine baktigimizda
# bir cok hisse ve fonun cop olmasi gibi bir sorun ortaya cikiyor, bunlari
# ayiklamamiz gerekecek"): Yukaridaki fon krizinin BIST HISSE tarafi -
# SPK'nin 16 Eylul 2026 tarihli 2026/59 sayili Bulteni'nde, asagidaki 3
# hissenin pay piyasasinda "ekonomik gerceklikle aciklanamayacak fiyat
# hareketleri" (piyasa dolandiriciligi) tespit edildi. Bu hisseler
# Pusula/Tera fonlarinin YOGUNLASMIS pozisyonlariyla suni sekilde
# sisirilmis (Katilimevim/Gundogdu: Pusula grubuyla AYNI sirketler
# grubu; Destek Finans: Tera fonlarinin agirlikli pozisyonu) - 38-44
# kisi hakkinda Cumhuriyet Bassavciligina suc duyurusunda bulunuldu,
# bazilarina 2 yil islem yasagi ve lisans iptali getirildi. Yil basindan
# bu yana %140-300+ yukselmis olan bu hisseler, suni destegi saglayan
# fonlar artik alici olamadigindan/tasfiye sürecindeyken cokme riski
# COK YUKSEK - TICKER bazinda eslestirme (fon listesinin aksine, bunlar
# belirli sirket adi kaliplariyla degil, KAP'ta kayitli TEK TEK
# hisseler).
MANIPULASYON_SUPHESIYLE_ISLEM_YASAKLI_HISSELER = [
    "KTLEV",  # Katilimevim Tasarruf Finansman A.S.
    "GUNDG",  # Gundogdu Gida Sut Urunleri Sanayi ve Dis Ticaret A.S.
    "DSTKF",  # Destek Finans Faktoring A.S.
]


def hisse_manipulasyon_supheli_mi(ticker: str) -> bool:
    """Bir BIST hissesinin SPK'nin 16 Eylul 2026 (2026/59) Bulteni'nde
    piyasa dolandiriciligi tespit edilen ve haklarinda suc duyurusu/
    islem yasagi karari verilen 3 hisseden biri olup olmadigini
    kontrol eder."""
    if not ticker:
        return False
    return str(ticker).upper().strip() in MANIPULASYON_SUPHESIYLE_ISLEM_YASAKLI_HISSELER
