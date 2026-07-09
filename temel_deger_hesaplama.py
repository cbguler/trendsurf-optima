"""
temel_deger_hesaplama.py  (v2 - ozet kutusu tabanli)

Fiyat Tespit Raporu'nun BAŞINDA yer alan kompakt "hızlı bakış" özet kutusundan
(Gelir Özeti + Bilanço + Piyasa Çarpanları) 4 dönemlik (2023, 2024, 2025,
2026T) BAĞIMSIZ hedef fiyat hesaplar.

NEDEN DETAYLI TABLOLAR (Bilanço/Net Borç sayfaları) DEĞİL DE ÖZET KUTUSU:
Raporların ortasindaki detayli, cok sutunlu finansal tablo sayfalari
(orn. tam Bilanço, Net Borç & Kaldırac tablosu) OCR acisindan cok daha
kirilgan cikti - sayilarin arasina gurultu karakterleri ("(o", harfler)
karisip guvenilir cikarim yapmayi zorlastiriyor. Buna karsin, raporun
basinda yer alan kompakt "hizli bakis" kutusu (Gelir Ozeti + Bilanco +
Deger Carpanlari + Piyasa Carpanlari tek bir yogun ama duzenli blokta)
belirgin sekilde daha temiz OCR sonucu veriyor (ORZAX ornegiyle dogrulandi).
Bu yuzden ana kaynak olarak bu ozet kutusu kullaniliyor.

VERI KISITI: Ozet kutusundaki Bilanço alt-tablosu SADECE EN GUNCEL donemi
(orn. 2026-03) icerir, tum 4 donemi degil. Bu yuzden:
  - Çarpan Bazlı Değer: 4 donem icin de hesaplanir (EBITDA serisi 4 donem
    mevcut), ancak Net Borç duzeltmesi TUM donemler icin EN GUNCEL bilinen
    Net Borç rakamiyla yapilir (tarihsel Net Borc serisi guvenilir OCR
    edilemedigi icin bir yaklastirmadir - bu acikca not edilir).
  - Graham Sayisi: SADECE en guncel donem icin hesaplanir (cunku Ozkaynak
    sadece o donem icin guvenilir mevcuttur).

Iki yontem de raporun kendi INA/degerleme agirliklandirmasindan BAGIMSIZDIR.
"""

import re
import math
from dataclasses import dataclass, field
from typing import Optional


def _tr_sayi_to_float(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.strip()
    negatif = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace(".", "").replace(",", ".")
    try:
        v = float(s)
        return -v if negatif else v
    except ValueError:
        return None


_SAYI = r"\(?-?[\d.,]+\)?"


def _etiketten_sonraki_sayilar(metin: str, etiket_pattern: str,
                                  pencere: int = 120, adet: int = 4) -> list:
    """Bir etiketten (orn. 'EBITDA') sonraki, TABLO SATIRI gibi görünen
    (yani hemen ardından sayı gelen) ilk eşleşmeyi bulur, sonra sırayla
    token'ları (sayı veya 'm.d.' placeholder) toplar. İlk gerçek olmayan
    token'da (dipnot, cümle vb.) durur - böylece dipnot sızması engellenir.
    'm.d.' (veri yok) görülünce None ekleyip HEMEN durur, çünkü bu genelde
    satırın son/eksik hücresidir, ardından gelen metin başka bir bağlamdır.
    """
    # Ardindan gercekten sayi gelen ilk esleşmeyi bul (duz metindeki tesadufi
    # kelime gecmelerini - orn. "...EBITDA rakamina gore 8,2x..." - eler)
    for m in re.finditer(etiket_pattern, metin, re.IGNORECASE):
        sonrasi = metin[m.end(): m.end() + 5]
        if re.match(r"\s*\(?-?\d", sonrasi):
            break
    else:
        return []

    kalan = metin[m.end(): m.end() + pencere]
    tokenlar = kalan.split()
    sonuc = []
    for tok in tokenlar:
        if len(sonuc) >= adet:
            break
        if re.fullmatch(r"m\.?d\.?", tok, re.IGNORECASE):
            sonuc.append(None)
            break  # m.d. sonrasi genelde dipnot/farkli baglam - dur
        if re.fullmatch(_SAYI, tok):
            v = _tr_sayi_to_float(tok)
            if v is not None:
                sonuc.append(v)
                continue
        break  # sayi/placeholder olmayan ilk token -> satir bitti
    return sonuc


def _tek_sayi_bul(metin: str, etiket_pattern: str, pencere: int = 60) -> Optional[float]:
    sonuc = _etiketten_sonraki_sayilar(metin, etiket_pattern, pencere, adet=1)
    return sonuc[0] if sonuc else None


_DONEM_ETIKETLERI = ["2023", "2024", "2025", "2026T"]


# ── v2.0.6: FORMAT-2 - tam finansal tablolu raporlar (TERA tarzi) ─────────────
# Bazi raporlarda (orn. Tera Yatirim / SA-RA) ozet kutusu HIC yok; bunun
# yerine tam Bilanço + Gelir Tablosu (cok sutunlu, donem basliklariyla) ve
# FD/FAVOK carpan tablolari var. Format-2 SADECE ozet-kutusu yontemi hicbir
# sonuc uretemediginde denenir - mevcut davranisi degistirmez.
#
# Guvenlik ilkesi: sutun sayisi ile tablo tarih basligi BIREBIR hizalanmadan
# hicbir rakam kullanilmaz - hizalama tutmuyorsa None doner (yanlis finansal
# rakam basmak, bos birakmaktan cok daha kotudur).

_F2_TR_MAP = str.maketrans({
    "ş": "s", "Ş": "S", "İ": "I", "ı": "i",
    "ğ": "g", "Ğ": "G", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U",
    "ç": "c", "Ç": "C",
    # Sapkali harfler (orn. "Donem KÂRI/Zarari") - v2.0.6
    "â": "a", "Â": "A", "î": "i", "Î": "I", "û": "u", "Û": "U",
})

_F2_TARIH = r"\d{2}\.\d{2}\.\d{4}"


def _f2_tarih_dizileri(norm: str) -> list:
    """Metindeki 'tablo tarih basligi' dizilerini bulur: art arda gelen
    >=3 tarih tokeni. Donus: [(baslangic_pozisyonu, [tarih, ...]), ...]"""
    diziler = []
    for m in re.finditer(r"(?:%s[\s|]{0,6}){3,}" % _F2_TARIH, norm):
        tarihler = re.findall(_F2_TARIH, m.group(0))
        diziler.append((m.start(), tarihler))
    return diziler


def _f2_satir_sayilari(norm: str, pos: int, pencere: int = 300, adet: int = 8) -> list:
    """pos'tan (etiket sonu) itibaren tablo satiri sayilarini toplar;
    sayi olmayan ilk token'da durur (dipnot sizmasini engeller)."""
    kalan = norm[pos: pos + pencere]
    sonuc = []
    for tok in kalan.split():
        if len(sonuc) >= adet:
            break
        if re.fullmatch(_SAYI, tok):
            v = _tr_sayi_to_float(tok)
            if v is not None:
                sonuc.append(v)
                continue
        break
    return sonuc


def _f2_ltm_net_kar(norm: str) -> Optional[float]:
    """Gelir tablosundaki 'Donem Kari/Zarari' satirindan LTM (son 12 ay)
    net kar hesaplar: LTM = SonTamYil - GecenYilAraDonem + SonAraDonem.
    Satirin sayilari, ait oldugu tablonun tarih basligiyla BIREBIR ayni
    adette olmali ve baslikta [31.12.(Y-1), ara(Y-1), ara(Y)] uclusu
    bulunmali - aksi halde None (tahmin yok)."""
    tarih_dizileri = _f2_tarih_dizileri(norm)
    if not tarih_dizileri:
        return None

    for m in re.finditer(r"Donem(?:\s+Net)?\s+Kari\s*/\s*Zarari", norm, re.IGNORECASE):
        sayilar = _f2_satir_sayilari(norm, m.end())
        if len(sayilar) < 4:
            continue
        # Bu satirdan ONCEKI en yakin tarih basligi bu tablonun basligidir
        onceki = [d for d in tarih_dizileri if d[0] < m.start()]
        if not onceki:
            continue
        tarihler = onceki[-1][1]
        if len(tarihler) != len(sayilar):
            continue  # hizalama tutmuyor - bu satiri kullanma

        # Tarihleri (gun, ay, yil) olarak coz
        try:
            parsed = [tuple(int(x) for x in t.split(".")) for t in tarihler]
        except Exception:
            continue
        # Son sutun bir ARA donem olmali (ay != 12)
        g_son, a_son, y_son = parsed[-1]
        if a_son == 12:
            continue
        # Ayni gun/ay, bir onceki yil ara donemi ve (y_son-1) tam yili bul
        idx_ara_onceki = idx_tam_yil = None
        for i, (g, a, y) in enumerate(parsed[:-1]):
            if (g, a) == (g_son, a_son) and y == y_son - 1:
                idx_ara_onceki = i
            if (g, a) == (31, 12) and y == y_son - 1:
                idx_tam_yil = i
        if idx_ara_onceki is None or idx_tam_yil is None:
            continue

        return sayilar[idx_tam_yil] - sayilar[idx_ara_onceki] + sayilar[-1]
    return None


def _f2_carpan_ozkaynak_medyani(norm: str) -> Optional[float]:
    """FD/FAVOK carpan tablolarindan (yurtici/yurtdisi benzerler) her
    tablonun urettigi Ozkaynak Degeri'ni toplar, MEDYANini dondurur.
    Satir bicimi: 'FD / FAVOK <carpan> <FAVOK> <Ozkaynak Degeri> ...'"""
    degerler = []
    for m in re.finditer(r"FD\s*/\s*FAVOK", norm, re.IGNORECASE):
        sayilar = _f2_satir_sayilari(norm, m.end(), pencere=120, adet=3)
        if len(sayilar) < 3:
            continue
        carpan, favok, ozk = sayilar[0], sayilar[1], sayilar[2]
        # Makullluk suzgeci: carpan kucuk bir kat sayi, FAVOK/Ozkaynak buyuk TL
        if 0 < carpan < 100 and favok > 1e6 and ozk > 1e6:
            degerler.append(ozk)
    if not degerler:
        return None
    degerler.sort()
    n = len(degerler)
    return degerler[n // 2] if n % 2 else (degerler[n//2 - 1] + degerler[n//2]) / 2


def _format2_hesapla(metin: str) -> Optional["DonemDegerleme"]:
    """Format-2 ana akisi. Basari kosullari saglanmazsa None."""
    norm = metin.translate(_F2_TR_MAP)

    # 1) Pay adedi (tek degerli, guvenli capalar). "Halka Arz EDILECEK Pay
    # Adedi" satirina yanlislikla takilmamak icin lookbehind korumasi var.
    hisse = _tek_sayi_bul(norm, r"(?<!Edilecek )Pay\s+Adedi")
    if not hisse:
        hisse = _tek_sayi_bul(norm, r"Halka\s+Arz\s+Oncesi\s+Odenmis\s+Sermaye")
    if not hisse or hisse < 1_000_000:
        return None

    # 2) Bilanco ozkaynagi: BUYUK HARF 'OZKAYNAKLAR' satiri (degerleme
    # tablolarindaki 'Ozkaynak Degeri' ile karismaz), satirin SON sayisi
    # = en guncel donem. (case-sensitive arama bilincli.)
    ozkaynak = None
    m_ozk = re.search(r"OZKAYNAKLAR\b", norm)
    if m_ozk:
        sayilar = _f2_satir_sayilari(norm, m_ozk.end())
        if sayilar and sayilar[-1] > 1e6:
            ozkaynak = sayilar[-1]

    # 3) LTM net kar (tarih basligiyla hizalanarak)
    ltm_net_kar = _f2_ltm_net_kar(norm)

    # 4) Carpan bazli deger (FD/FAVOK tablolarinin medyan ozkaynagi / pay adedi)
    carpan_ozk = _f2_carpan_ozkaynak_medyani(norm)

    dv = DonemDegerleme(donem_etiketi="LTM (Format-2)")
    dv.notlar.append("Format-2: ozet kutusu yok, tam finansal tablolardan cikarildi")

    if carpan_ozk:
        dv.carpan_bazli_deger = carpan_ozk / hisse
        dv.notlar.append("Carpan: rapor FD/FAVOK tablolarinin medyan Ozkaynak Degeri / Pay Adedi")

    if ltm_net_kar is not None and ozkaynak:
        dv.net_kar_mtl = ltm_net_kar / 1_000_000
        dv.eps = ltm_net_kar / hisse
        dv.bvps = ozkaynak / hisse
        if dv.eps > 0 and dv.bvps > 0:
            dv.graham_degeri = math.sqrt(22.5 * dv.eps * dv.bvps)
            dv.notlar.append("Graham: Net Kar = LTM (son tam yil - gecen yil ara donem "
                             "+ son ara donem), Ozkaynak = bilanco en guncel donem")
        else:
            dv.notlar.append("Graham: negatif EPS/BVPS")

    if dv.graham_degeri is None and dv.carpan_bazli_deger is None:
        return None
    return dv


@dataclass
class DonemDegerleme:
    donem_etiketi: str
    ebitda_mtl: Optional[float] = None
    net_kar_mtl: Optional[float] = None
    eps: Optional[float] = None
    bvps: Optional[float] = None
    graham_degeri: Optional[float] = None
    carpan_bazli_deger: Optional[float] = None
    notlar: list = field(default_factory=list)


def hedef_fiyat_hesapla(metin: str, arz_fiyati: Optional[float] = None) -> list:
    """Ana fonksiyon: rapor ozet kutusu metnini alir, 4 donem icin
    Carpan Bazli Deger + (sadece guncel donem icin) Graham Sayisi hesaplar.

    arz_fiyati: Eger 'Hisse Sayısı' etiketi metinde bulunamazsa (bazen ayrı,
    uzak bir sayfada oluyor - orn. ORZAX'ta özet kutusu sayfa 6'da ama Hisse
    Sayısı sayfa 37'de), hisse sayisi 'Piyasa Değeri' (mTL) / arz_fiyati
    formuluyle TURETILIR. arz_fiyati disaridan (fiyat_tespit_parser'in zaten
    bulmus oldugu Pay Basi Deger) verilir - boylece ayri bir sayfaya gitmeye
    GEREK KALMAZ.
    """
    ebitda_serisi = _etiketten_sonraki_sayilar(metin, r"EBITDA(?!\s*Mar)", pencere=100)
    net_kar_serisi = _etiketten_sonraki_sayilar(metin, r"Net\s*Kar\b", pencere=100)

    ozkaynak_guncel = _tek_sayi_bul(metin, r"Özkaynak\b")
    net_borc_guncel = _tek_sayi_bul(metin, r"Net\s*Borç[-–]\S*")
    hisse_sayisi = _tek_sayi_bul(metin, r"Hisse\s*Say[iı]s[iı]")

    if hisse_sayisi and hisse_sayisi < 100_000:
        hisse_sayisi *= 1_000_000  # milyon adet -> adet

    if not hisse_sayisi and arz_fiyati:
        piyasa_degeri_mtl = _tek_sayi_bul(metin, r"Piyasa\s*Değeri\b")
        if piyasa_degeri_mtl:
            hisse_sayisi = (piyasa_degeri_mtl * 1_000_000) / arz_fiyati

    medyan_carpan = None
    for pat in [r"Yurtdışı Çarpanlar\S*\s+(" + _SAYI + r")\s*[xX]",
                 r"BİST Sağlık\s*&?\s*İlaç\s+(" + _SAYI + r")\s*[xX]"]:
        m = re.search(pat, metin, re.IGNORECASE)
        if m:
            v = _tr_sayi_to_float(m.group(1))
            if v and 0 < v < 100:
                medyan_carpan = v
                break

    if ozkaynak_guncel is not None:
        ozkaynak_guncel *= 1_000_000  # mTL -> TL
    if net_borc_guncel is not None:
        net_borc_guncel *= 1_000_000  # mTL -> TL

    sonuclar = []
    for i, etiket in enumerate(_DONEM_ETIKETLERI):
        dv = DonemDegerleme(donem_etiketi=etiket)
        dv.ebitda_mtl = ebitda_serisi[i] if i < len(ebitda_serisi) else None
        dv.net_kar_mtl = net_kar_serisi[i] if i < len(net_kar_serisi) else None

        if not hisse_sayisi:
            dv.notlar.append("Hisse sayısı bulunamadı")
            sonuclar.append(dv)
            continue

        if dv.ebitda_mtl is not None and medyan_carpan is not None:
            ebitda_tl = dv.ebitda_mtl * 1_000_000
            net_borc = net_borc_guncel if net_borc_guncel is not None else 0.0
            firma_degeri = ebitda_tl * medyan_carpan
            dv.carpan_bazli_deger = (firma_degeri - net_borc) / hisse_sayisi
            if net_borc_guncel is not None:
                dv.notlar.append("Net Borç en güncel dönem rakamıyla yaklaşık alınmıştır")
        else:
            eksik = []
            if dv.ebitda_mtl is None: eksik.append("EBITDA")
            if medyan_carpan is None: eksik.append("medyan çarpan")
            dv.notlar.append(f"Çarpan bazlı değer: {', '.join(eksik)} eksik")

        sonuclar.append(dv)

    # --- Graham Sayisi: EN SON AÇIKLANAN Net Kar (m.d. olmayan) + EN GÜNCEL
    # Özkaynak birlestirilerek hesaplanir. Donemler arasi kucuk bir uyumsuzluk
    # olabilir (orn. Net Kar 2025 sonu, Ozkaynak 2026/03) - bu acikca not
    # edilir. Bu, "hicbir Graham degeri verememek" yerine daha faydali bir
    # yaklastirmadir.
    son_acik_index = None
    for i in range(len(sonuclar) - 1, -1, -1):
        if sonuclar[i].net_kar_mtl is not None:
            son_acik_index = i
            break

    if son_acik_index is not None and ozkaynak_guncel:
        dv = sonuclar[son_acik_index]
        net_kar_tl = dv.net_kar_mtl * 1_000_000
        dv.eps = net_kar_tl / hisse_sayisi if hisse_sayisi else None
        dv.bvps = ozkaynak_guncel / hisse_sayisi if hisse_sayisi else None
        if dv.eps and dv.bvps and dv.eps > 0 and dv.bvps > 0:
            dv.graham_degeri = math.sqrt(22.5 * dv.eps * dv.bvps)
            if dv.donem_etiketi != _DONEM_ETIKETLERI[-1]:
                dv.notlar.append(
                    f"Graham: {dv.donem_etiketi} Net Kar'ı + en güncel "
                    f"dönem Özkaynak'ı birlikte kullanılmıştır (dönem uyumsuzluğu olabilir)")
        else:
            dv.notlar.append("Graham: negatif EPS/BVPS")

    for dv in sonuclar:
        if dv.graham_degeri is None and "Graham" not in " ".join(dv.notlar):
            dv.notlar.append("Graham: bu dönem için hesaplanmadı (bkz. en son açıklanan dönem)")

    # ── v2.0.6: FORMAT-2 YEDEGI ──────────────────────────────────────────
    # Ozet kutusu yontemi hicbir deger uretemediyse (TERA gibi ozet kutusuz,
    # tam finansal tablolu raporlar) Format-2 denenir. Ozet kutusu kismen
    # bile sonuc urettiyse Format-2 HIC devreye girmez - mevcut davranis
    # birebir korunur.
    if not any(d.graham_degeri is not None or d.carpan_bazli_deger is not None
               for d in sonuclar):
        f2 = _format2_hesapla(metin)
        if f2 is not None:
            sonuclar.append(f2)

    return sonuclar


if __name__ == "__main__":
    with open("orzax_ozet_kutusu_ocr.txt", "r", encoding="utf-8") as f:
        metin = f.read()

    print("=== ORZAX gerçek OCR metni üzerinden hesaplama ===\n")
    for dv in hedef_fiyat_hesapla(metin):
        print(f"--- {dv.donem_etiketi} ---")
        print(f"  EBITDA: {dv.ebitda_mtl} mTL | Net Kar: {dv.net_kar_mtl} mTL")
        if dv.eps is not None:
            print(f"  EPS: {dv.eps:.2f} | BVPS: {dv.bvps:.2f}")
        print(f"  Graham Değeri: {dv.graham_degeri}")
        print(f"  Çarpan Bazlı Değer: {dv.carpan_bazli_deger}")
        if dv.notlar:
            print(f"  Notlar: {dv.notlar}")
        print()
