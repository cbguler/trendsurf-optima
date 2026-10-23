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
import pandas as pd

ESIK_GUN = 10


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


def aciklama(gun) -> str:
    g = int(float(gun))
    return (f"Son {g} işlem gününde bu hissede hiç işlem gerçekleşmedi (hacim 0, fiyat değişmedi). "
            "Tahta kapalı olabilir (KAP'ta işlem sırası kapatma bildirimi olabilir) ya da likidite "
            "çok düşük olabilir; alınıp satılamayabilir. Optima Skor 0'a sabitlenmiştir; "
            "alım/satım sinyali üretilmez. İşlem yeniden başlayınca uyarı kendiliğinden kalkar.")
