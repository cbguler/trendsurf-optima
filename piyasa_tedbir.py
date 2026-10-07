# -*- coding: utf-8 -*-
"""
piyasa_tedbir.py - Piyasa tedbiri (SPK karari) kurallari icin PAYLASILAN yardimcilar.

spk_bulten_izleme.py (tarayici) ve app.py (onay penceresi) AYNI mantigi kullanir; bu
yuzden onay penceresinde gosterilen "etkilenecek varliklar" ile load_universe()'in
gercekte sifirlayacagi varliklar HER ZAMAN ayni olur. Streamlit'e bagimli DEGILDIR.

v2.0.7.366 (4 Ekim 2026) - Otomatik piyasa tedbiri izleme.
"""
import re

import pandas as pd

# Turkce harfleri sadelestir (uzunluk KORUNUR: her harf tek harfe doner) - boylece
# normallestirilmis metindeki konumlar orijinal metinle birebir hizali kalir.
_TR_HARITA = str.maketrans({"İ": "I", "ı": "I", "Ş": "S", "ş": "S", "Ğ": "G", "ğ": "G",
                            "Ü": "U", "ü": "U", "Ö": "O", "ö": "O", "Ç": "C", "ç": "C"})

# tedbir_turu -> kullaniciya gosterilen ad
TEDBIR_ETIKET = {
    "ISLEME_KAPATMA": "TEFAS'ta alım-satıma kapatıldı",
    "TASFIYE": "Zorunlu tasfiye kararı",
    "TASFIYE_IZNI": "Gönüllü tasfiye izni",
    "MANIPULASYON_SUPHESI": "Piyasa dolandırıcılığı suç duyurusu",
    "SUC_DUYURUSU": "Suç duyurusu",
    "YUKSEK_MINIMUM_TUTAR": "Aracı kurum minimum tutar şartı",
    "KALDIRMA": "Tedbirin kaldırılması",
    "KISMI_KALDIRMA": "Tedbir kısmen kaldırılıyor (bazı fonlar yeniden açılıyor)",
}

# Etkilenen varlik sayisi bu esigi asarsa onay penceresinde ayrica uyarilir
GENIS_ETKI_ESIGI = 250


def tr_harf_norm(s) -> str:
    """Buyuk harfe cevir + Turkce harfleri sadelestir. UZUNLUK KORUNUR (konum hizasi)."""
    return "" if s is None else str(s).translate(_TR_HARITA).upper()


def tr_norm(s) -> str:
    """tr_harf_norm + bosluklari teke indir. Birlesik noktali i (i + U+0307: `.title()`/AI ciktisinda
    'İ'nin ayrisik hali) de temizlenir; aksi halde 'Capi̇tal' evren adiyla eslesmez."""
    return re.sub(r"\s+", " ", tr_harf_norm(s).replace("\u0307", "")).strip()


def sirket_anahtari(ad):
    """Fon adindan portfoy yonetim sirketi anahtari:
    'BULLS PORTFÖY PARA PİYASASI (TL) FONU' -> 'BULLS PORTFOY';
    'A1 CAPİTAL PORTFÖY ...' -> 'A1 CAPITAL PORTFOY'. 'PORTFÖY' kelimesi 1-3. sirada
    yoksa None (ornegin emeklilik fonlari)."""
    kelimeler = tr_norm(ad).split(" ")
    for i, k in enumerate(kelimeler):
        if k == "PORTFOY" and 1 <= i <= 3:
            return " ".join(kelimeler[:i + 1])
    return None


def sirket_degeri(ad, anahtar: str) -> str:
    """Fon adinin, `anahtar` kadar kelimelik ORIJINAL (buyuk harf) on eki.
    load_universe() `deger in str(Ad).upper()` ile ARAR - kural degeri bu yuzden fon
    adindaki YAZIMLA (Turkce harfler dahil) birebir ayni olmali; bunu garanti eder."""
    k = len(anahtar.split(" "))
    return " ".join(str(ad).upper().split()[:k])


def esleyen_maske(df: pd.DataFrame, eslesme_turu: str, deger: str) -> pd.Series:
    """load_universe()'in kullandigi eslemenin BIREBIR AYNISI (app.py ~satir 925-937)."""
    if df is None or df.empty:
        return pd.Series(dtype=bool)
    if eslesme_turu == "SIRKET_ADI":
        return (df["Kategori"] == "TEFAS") & df["Ad"].apply(lambda ad: deger in str(ad).upper())
    if eslesme_turu == "TICKER":
        return df["Ticker"].astype(str).str.upper() == str(deger)
    return pd.Series(False, index=df.index)


def kapsanan_maske(df: pd.DataFrame, kurallar) -> pd.Series:
    """Verilen kural listesinin ({'eslesme_turu','deger'}) TOPLAMINDA kapsadigi varliklar."""
    maske = pd.Series(False, index=df.index)
    for k in kurallar or []:
        maske = maske | esleyen_maske(df, k["eslesme_turu"], k["deger"])
    return maske


def etki_ozeti(df: pd.DataFrame, eslesme_turu: str, deger: str, n_ornek: int = 6) -> dict:
    """{'adet': N, 'ornekler': [(Ticker, Ad), ...], 'genis': bool}"""
    m = esleyen_maske(df, eslesme_turu, deger)
    sub = df[m] if len(m) else df.iloc[0:0]
    ornek = [(str(r.Ticker), str(r.Ad)) for r in sub.head(n_ornek).itertuples()]
    return {"adet": int(len(sub)), "ornekler": ornek, "genis": len(sub) > GENIS_ETKI_ESIGI}
