# -*- coding: utf-8 -*-
"""
v2.0.7.431 - "Fiilen islem gormuyor" tespiti (hacim tabanli, KAP bildiriminden BAGIMSIZ).

SORUN (Bahri'nin sorusu, 23 Ekim 2026: "tahtasi kapatilan hisseler"): KAP "Pay Islem Sirasi
Kapatma/Acma" bildirimi AGIR risk olarak skoru 0'lar, ama kural 60 gun sonra biter ve arsiv 130 gun
tutar. Borsa her acilista bildirim yayimlamadigindan "acilis bildirimi yok" = "hala kapali" DEGILDIR
(canli veri: POLHO ve YYAPI kapatma bildirimi olup acilis bildirimi olmayan ama aktif islem goren
hisseler). Tersine UMPAS 1.10.2024'te kapatildi, son 66 seansin HEPSINDE hacim 0 ve fiyat 9,30'da sabit;
KAP uyarisi 60 gun sonra dustugu icin 33 puanla "normal" gorunuyordu.

COZUM: son seanslarda hacim TAM 0 ve kapanis degismiyorsa hisse fiilen islem gormuyordur. Bu, KAP
bildirimine bakmaz: kapatma bildirimi, yeniden acilista bildirim olmamasi ya da haber olsa da
olmasa da isler. Islem yeniden baslayinca (hacim > 0) sayac kendiliginden sifirlanir ve uyari kalkar.

SINIRLAR (kasitli): (1) Bu bir KAPATMA kaniti degil, "hic islem gerceklesmedi" kanitidir; cok dusuk
likiditeli ama kapali olmayan bir hisse de (orn. ISATR) ayni sekilde isaretlenir - aciklama bunu
soyler. (2) Hacim NaN (Yahoo'da yok) ise sayac KIRILIR (NaN sifir sayilmaz): veri eksikligi yanlis
alarm uretmesin. (3) Esik 10 seans: canli evrende (631 fiyatli hisse) 3 ile 20 seans arasinda hicbir
hisse yok (yalniz UMPAS ve ISATR >= 20), yani esik secimi sonucu degistirmiyor.
"""
import json
import os

import pandas as pd

ESIK_GUN = 10
_KAP_ONBELLEK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kap_temel_onbellek.json")
_paylar_onbellegi = {"mtime": None, "veri": {}}


def sifir_hacim_gun(close, volume) -> int:
    """Seri SONUNDAN geriye: hacmi tam 0 olan ve kapanisi son kapanisla AYNI olan ardisik seans sayisi.
    NaN hacim ya da NaN kapanis sayaci keser. Hesaplanamazsa 0."""
    try:
        if close is None or volume is None:
            return 0
        c = pd.Series(close).astype(float)
        v = pd.Series(volume).reindex(c.index).astype(float)
        c = c.dropna()
        if c.empty:
            return 0
        v = v.reindex(c.index)
        son = float(c.iloc[-1])
        n = 0
        for cv, vv in zip(c.values[::-1], v.values[::-1]):
            if pd.isna(vv) or float(vv) != 0.0 or float(cv) != son:
                break
            n += 1
        return n
    except Exception:
        return 0


def isaretli_mi(gun) -> bool:
    """CSV'den gelen Islem_Yok_Gun (sayi/NaN/metin) esigi asiyor mu."""
    try:
        return pd.notna(gun) and float(gun) >= ESIK_GUN
    except Exception:
        return False


def paylar_yukle(yol: str = None) -> dict:
    """KAP ham veri onbelleginden {TICKER: {borsa_kodu: pay_adedi}} (yalniz BIRDEN FAZLA kodu olan sirketler).
    Dosya yok/bozuk -> {} (aciklama eski, genel haliyle kalir). Dosya degismedikce yeniden okunmaz."""
    yol = yol or _KAP_ONBELLEK
    try:
        mt = os.path.getmtime(yol)
        if _paylar_onbellegi["mtime"] == (yol, mt):
            return _paylar_onbellegi["veri"]
        with open(yol, encoding="utf-8") as f:
            ham = json.load(f).get("veri", {})
        out = {}
        for t, v in ham.items():
            p = (v or {}).get("paylar") or {}
            if len(p) > 1:
                out[str(t).upper()] = {str(k).upper(): float(a) for k, a in p.items()}
        _paylar_onbellegi["mtime"], _paylar_onbellegi["veri"] = (yol, mt), out
        return out
    except Exception:
        return {}


def _tr_say(x) -> str:
    return f"{float(x):,.0f}".replace(",", ".")


def _tr_yuzde(oran) -> str:
    """oran (0-1) -> '%0,000004' gibi; cok kucuk degerlerde anlamli basamaklar korunur."""
    y = float(oran) * 100
    t = f"{y:.1f}" if y >= 1 else (f"{y:.2f}" if y >= 0.01 else f"{y:.8f}")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return "%" + t.replace(".", ",")


def kardes_notu(ticker, paylar, islem_gorenler) -> str:
    """Ayni KAP sirketinin birden fazla borsa kodu varsa ve bu kod islem gormuyorsa kisa not; yoksa ''.
    paylar: paylar_yukle() sonucu. islem_gorenler: fiilen islem gordugu OLCULMUS (Islem_Yok_Gun < ESIK) kodlar.
    Islem goren kardes kod = pay adedi en buyuk olan; olcumle dogrulanamazsa kod ADI VERILMEZ."""
    try:
        t = str(ticker).upper()
        grup = (paylar or {}).get(t)
        if not grup or t not in grup or len(grup) < 2:
            return ""
        toplam = sum(grup.values())
        kendi = grup[t]
        cumle = (f" KAP pay tablosuna göre aynı şirketin toplam {_tr_say(toplam)} payı vardır; "
                 f"bu kodun payı {_tr_say(kendi)} adettir ({_tr_yuzde(kendi / toplam)}).")
        adaylar = {k: a for k, a in grup.items() if k != t and k in (islem_gorenler or ())}
        if adaylar:
            k = max(adaylar, key=adaylar.get)
            cumle += f" İşlem gören en büyük pay kodu: {k} ({_tr_say(adaylar[k])} pay)."
        cumle += " Bu uyarı şirketin mali durumu hakkında değil, bu kodun işlem görmemesi hakkındadır."
        return cumle
    except Exception:
        return ""


def aciklama(gun, ticker=None, paylar=None, islem_gorenler=None) -> str:
    g = int(float(gun))
    return (f"Son {g} işlem gününde bu hissede hiç işlem gerçekleşmedi (hacim 0, fiyat değişmedi). "
            "Tahta kapalı olabilir (KAP'ta işlem sırası kapatma bildirimi olabilir) ya da likidite "
            "çok düşük olabilir; alınıp satılamayabilir. Optima Skor 0'a sabitlenmiştir; "
            "alım/satım sinyali üretilmez. İşlem yeniden başlayınca uyarı kendiliğinden kalkar."
            + (kardes_notu(ticker, paylar, islem_gorenler) if ticker else ""))
