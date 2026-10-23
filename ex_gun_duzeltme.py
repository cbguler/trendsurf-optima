# -*- coding: utf-8 -*-
"""
v2.0.7.430 - Sermaye artirimi HAK KULLANIM (ex) GUNU BOSLUGUNUN etkisizlestirilmesi.

SORUN (Bahri'nin "sermaye artirimi" olay calismasi, 23 Ekim 2026):
Borsa Istanbul, bedelli/bedelsiz artirimin hak kullanim gunu hissenin baz fiyatini
mekanik olarak duzeltir. Yahoo Finance ise bedelsiz bolunmelerin bir kismini (~%14) ve
bedelli (ruchan) artirimlarin NEREDEYSE HEPSINI (361 olayin 17'sinde duzeltme var)
fiyat serisine yansitmaz. Sonuc: seride tek gunde buyuk bir "cokus" gorunur. Radar
(firsat_radari.tara_bist) ve gece worker'i (worker.batch_bist) bu 3 aylik seriden
RSI / Ret1M / volatilite / maksimum dusus (MaxDD) / trend hesapladigi icin SAHTE cokus
skora girer (MaxDD cezasi -7/-3 puan, Ret1M, RSI).

COZUM (yaklasik, tam duzeltme DEGIL):
Bir hissenin serisinde tek gunluk dusus ESIK'i asiyorsa VE KAP arsivinde (kap_risk_bildirim)
o hisse icin dususten onceki ARSIV_GUN gun icinde ya da dususten en cok 3 gun sonra
bedelli/bedelsiz sermaye artirimi bildirimi varsa, o gunden ONCEKI tum kapanislar
gozlenen orana (kapanis[g] / kapanis[g-1]) gore geriye dogru carpilir. Son fiyat DEGISMEZ.

BILINEN SINIRLAR (kasitli, belgelenmis):
- Duzeltme orani, hakkin mekanik etkisi ile o gunun gercek piyasa hareketini AYIRMAZ;
  o gunun tum getirisi seriden cikarilir. Sapma kucuk ve bilinen yonde (o gunun gercek
  hareketi gizlenir).
- ESIK altindaki mekanik dususler (kucuk oranli bedelli) yakalanmaz; bunlarin etkisi de
  zaten kucuktur.
- Hacim serisi duzeltilmez (bedelsizde pay adedi degisir; Yahoo hacmi kismen duzeltir).
- Uygulama yalnizca radar ve gece worker'inin SKOR GIRDILERINDE; uygulama icindeki detay
  sayfasi grafikleri degismez.
- ESIK gecmis veride belirlendi (bkz. PROJE_NOTLARI v430): bu bir buluşsal esiktir.
"""
import datetime

import pandas as pd

# Tek gunluk dusus esigi. BIST'te hisselerde gunluk fiyat limiti %10 oldugu varsayimiyla
# (DOGRULANMADI; gecmis veride 2021+ doneminde -%10,5 altina dusen gun sayisi yilda ~10-35
# ve 2024-26'da bunlarin cogu sermaye artirimi sureciyle ortusuyor) bunun uzerindeki tek gunluk
# dusus piyasa hareketi degil mekanik duzeltmedir.
ESIK = 0.12
# kap_risk_tarama arsivi 130 gun saklar (ARSIV_GUN).
ARSIV_GUN = 130
SONRA_GUN = 3          # ex-gunu bildirimi dususten birkac gun sonra gelebilir

_TURLER = ("SERMAYE_BEDELLI", "SERMAYE_BEDELSIZ", "SERMAYE_DIGER")


def _gun(d):
    if isinstance(d, datetime.datetime):
        return d.date()
    if isinstance(d, datetime.date):
        return d
    return pd.Timestamp(d).date()


def surec_haritasi(bildirimler) -> dict:
    """KAP arsiv bildirimlerinden {TICKER: [bildirim_tarihi(date), ...]}: yalnizca bedelli/
    bedelsiz/belirsiz-tur SERMAYE ARTIRIMI bildirimleri (azaltim haric). Hata -> bos sozluk."""
    out = {}
    try:
        import kap_risk
        for b in (bildirimler or []):
            if b.get("konu") not in kap_risk.K_SERMAYE or not b.get("tarih"):
                continue
            if kap_risk._sermaye_turu(b.get("ozet") or "", b.get("metin") or "") not in _TURLER:
                continue
            kodlar = b.get("gonderen_kodlar") or b.get("ilgili_kodlar") or []
            for k in kodlar:
                out.setdefault(str(k).upper(), []).append(_gun(b["tarih"]))
    except Exception as e:  # asla radar/worker'i durdurma
        print(f"[ex-gun] surec haritasi hatasi (duzeltme yapilmayacak): {type(e).__name__}: {str(e)[:150]}")
        return {}
    return out


def surec_haritasi_yukle(gun: int = ARSIV_GUN) -> dict:
    """Supabase arsivinden surec haritasi. DB yoksa/hata -> {} (duzeltme yapilmaz, skor eskisi gibi)."""
    try:
        import db
        return surec_haritasi(db.kap_risk_bildirimleri_oku(gun))
    except Exception as e:
        print(f"[ex-gun] KAP arsivi okunamadi (duzeltme yapilmayacak): {type(e).__name__}: {str(e)[:150]}")
        return {}


def duzelt(close: pd.Series, bildirim_tarihleri, esik: float = ESIK):
    """(duzeltilmis_seri, [(tarih, oran), ...]). Bildirim yoksa ya da bosluk yoksa seri AYNEN doner.
    close: artan tarih indeksli kapanis serisi (NaN'siz). Son deger degismez."""
    if close is None or len(close) < 3 or not bildirim_tarihleri:
        return close, []
    try:
        tarihler = sorted({_gun(d) for d in bildirim_tarihleri})
        idx = [_gun(x) for x in close.index]
        v = close.astype(float).values
        oranlar = []      # (konum, oran)
        for i in range(1, len(v)):
            if v[i - 1] <= 0 or v[i] <= 0:
                continue
            r = v[i] / v[i - 1]
            if r > 1.0 - esik:
                continue
            g = idx[i]
            alt = g - datetime.timedelta(days=ARSIV_GUN)
            ust = g + datetime.timedelta(days=SONRA_GUN)
            if any(alt <= t <= ust for t in tarihler):
                oranlar.append((i, r))
        if not oranlar:
            return close, []
        carpan = [1.0] * len(v)
        for i, r in oranlar:
            for j in range(i):
                carpan[j] *= r
        yeni = close.copy().astype(float)
        yeni.iloc[:] = [v[j] * carpan[j] for j in range(len(v))]
        return yeni, [(idx[i], round(float(r), 4)) for i, r in oranlar]
    except Exception as e:
        print(f"[ex-gun] duzeltme hatasi (seri aynen kullanildi): {type(e).__name__}: {str(e)[:150]}")
        return close, []


def uygula(ticker: str, close: pd.Series, surecler: dict, etiket: str = "ex-gun"):
    """Radar/worker icin tek cagri: surecler None/bos ise seri AYNEN doner. Duzeltme yapildiysa loglar."""
    if not surecler:
        return close
    yeni, liste = duzelt(close, surecler.get(str(ticker).upper()))
    if liste:
        print(f"[{etiket}] {ticker}: ex-gun boslugu duzeltildi "
              + ", ".join(f"{t} oran {o}" for t, o in liste))
    return yeni
