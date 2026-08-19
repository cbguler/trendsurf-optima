# -*- coding: utf-8 -*-
"""
haber_izleme.py — TrendSurf Optima
Beklenti Modu'nun OTOMATIK haber TESPİT katmani (v2.0.7.154/155/156,
Bahri'nin talebi, 18 Agustos 2026).

GitHub Actions uzerinde 10 dakikada bir calisir:
  1) 5 RSS haber kaynagini (Turkiye + kuresel) okur
  2) Her YENI haberi (daha once islenmemis) anahtar kelime on-filtresinden
     gecirir (6 Beklenti Modu kalibi: jeopolitik/petrol/fed/kredi_notu/
     kripto_olay/tcmb_kredibilite)
  3) On-filtreden gecen haberleri Google Gemini API ile DOGRULAR
     (gercekten ilgili kalibi mi anlatiyor, hangi siddette)
  4) Dogrulanan tespitleri Supabase'e "bekliyor" durumunda yazar.

v2.0.7.156 (Bahri'nin bulgusu, KRİTİK tasarım düzeltmesi - "hemen
otomatik uygula" YANLIŞ anlaşılmıştı): bu script SADECE TESPIT EDER ve
Supabase'e yazar - Optima Skor'a OTOMATİK UYGULAMAZ. app.py, bekleyen
tespitleri kullanıcıya (haber + AI gerekçesi + tahmini puan etkisiyle)
gösterir, kullanıcı Onayla/Reddet der, SADECE ONAYLANANLAR uygulanır.
Bu script'in KENDİSİNDE bu değişiklik için kod değişikliği GEREKMEDİ -
sadece db.py'deki tablo şeması ve app.py'nin okuma/uygulama mantığı
değişti (onay_durumu='bekliyor' varsayılanı zaten buradan
`otomatik_tespit_ekle()` ile ekleniyordu).

v2.0.7.155 (Bahri'nin talebi: "ucretli ise kurmayacagim, ucretsiz
alternatif bulalim"): Anthropic API'den Google Gemini API'ye gecildi -
Gemini'nin kredi karti GEREKTIRMEYEN gercek bir ucretsiz katmani var
(dogrulandi: Agustos 2026, gemini-2.5-flash modeli gunde 250-500 istek
civari ucretsiz limit - 10 dakikada bir calisan bu script icin fazlasiyla
yeterli).

GUVENLIK: GEMINI_API_KEY GitHub Secrets'tan okunur, koda YAZILMAZ
(bu repo public).

Kalip tanimlari (_KALIP_TABLOSU/_KALIP_ISIM) app.py'deki ile AYNI olmali
- burada KOPYALANMISTIR (worker.py/firsat_radari.py'nin app.py'yi
guvenle import edemedigi ile AYNI kisit - bu da bagimsiz bir script).
Yeni bir kalip eklenirse HER IKI yerde de guncellenmelidir.
"""
import os
import sys
import json
import time
import datetime

import feedparser

# ══════════════════════════════════════════════════════════════
# RSS kaynaklari - dogrudan test edildi (2026-08-18), hepsi HTTP 200
# ══════════════════════════════════════════════════════════════
_RSS_KAYNAKLARI = [
    ("AA Ekonomi", "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Investing.com TR", "https://tr.investing.com/rss/news_25.rss"),
    ("BloombergHT", "https://www.bloomberght.com/rss"),
]

# ══════════════════════════════════════════════════════════════
# Anahtar kelime on-filtresi (Turkce + Ingilizce - kaynaklar karisik)
# ══════════════════════════════════════════════════════════════
_ANAHTAR_KELIMELER = {
    "jeopolitik": [
        "savaş", "çatışma", "saldırı", "gerilim", "işgal", "füze", "ordu",
        "askeri operasyon", "ateşkes", "bombalama",
        "war", "conflict", "attack", "invasion", "missile", "military",
        "ceasefire", "airstrike", "troops", "strike on",
    ],
    "petrol": [
        "petrol", "opec", "hürmüz", "boğazı", "ambargo", "üretim kesintisi",
        "boru hattı", "rafineri", "tanker",
        "oil", "strait of hormuz", "pipeline", "refinery", "crude",
    ],
    "fed": [
        "fed", "fomc", "faiz kararı", "ecb", "avrupa merkez bankası",
        "federal reserve", "interest rate decision", "rate hike",
        "rate cut", "powell", "lagarde",
    ],
    "kredi_notu": [
        "kredi notu", "moody's", "s&p", "fitch", "not indirimi",
        "credit rating", "sovereign rating", "downgrade",
    ],
    "kripto_olay": [
        "halving", "kripto düzenleme", "borsa çöktü", "bitcoin hack",
        "crypto regulation", "exchange collapse", "sec lawsuit",
    ],
    "tcmb_kredibilite": [
        "tcmb", "ppk", "para politikası kurulu", "faiz indirimi",
        "merkez bankası bağımsızlığı",
    ],
}

_KALIP_ISIM = {
    "jeopolitik": "Jeopolitik gerilim/çatışma",
    "petrol": "Petrol arz şoku (Ortadoğu/OPEC)",
    "fed": "Merkez bankası (Fed/ECB/TCMB) şahin sürprizi",
    "kredi_notu": "Kredi notu düşürülmesi (S&P/Moody's/Fitch)",
    "kripto_olay": "Kripto düzenleme/halving şoku",
    "tcmb_kredibilite": "TCMB para politikası kredibilite kaybı",
}

# v2.0.7.157 (Bahri'nin talebi, 18 Ağustos 2026): AI'nin ürettiği doğal
# cümlede "XXX varlıklarının Optima Skorlarını artırmamız/azaltmamız
# gerekir" derken HANGİ kategorilerden bahsedeceğini bilmesi için -
# app.py'deki _KALIP_TABLOSU ile AYNI olmalı (yön/kategori eşlemesi,
# tam sayısal puan değil - o hesap zaten app.py'de risk/şiddet
# çarpanlarıyla ayrıca yapılıyor).
_KALIP_KATEGORI_YONU = {
    "jeopolitik": {"MADEN": "artış", "DOVIZ": "artış", "BIST": "azalış"},
    "petrol": {"MADEN": "artış", "DOVIZ": "artış", "BIST": "azalış"},
    "fed": {"MADEN": "azalış", "DOVIZ": "artış", "BIST": "azalış"},
    "kredi_notu": {"DOVIZ": "artış", "BIST": "azalış"},
    "kripto_olay": {"KRIPTO": "azalış"},
    "tcmb_kredibilite": {"DOVIZ": "artış", "MADEN": "artış", "BIST": "azalış"},
}
_KATEGORI_ISIM_TR = {
    "MADEN": "Değerli Maden", "DOVIZ": "Döviz", "BIST": "BIST",
    "KRIPTO": "Kripto",
}


def _on_filtre_eslesen_kaliplar(baslik, ozet):
    """Basit anahtar kelime eslestirmesi - kucuk/buyuk harf duyarsiz.
    Eslesen TUM kaliplari doner (bir haber birden fazla kaliba
    eslesebilir, orn. hem 'jeopolitik' hem 'petrol')."""
    metin = f"{baslik} {ozet}".lower()
    eslesenler = []
    for kalip_key, kelimeler in _ANAHTAR_KELIMELER.items():
        for kelime in kelimeler:
            if kelime.lower() in metin:
                eslesenler.append(kalip_key)
                break
    return eslesenler


def _ai_dogrula(kalip_key, baslik, ozet, kaynak):
    """v2.0.7.155 (Bahri'nin talebi, 18 Ağustos 2026 — "ücretli ise
    kurmayacağım, ücretsiz alternatif bulalım"): Anthropic API yerine
    Google Gemini API kullanıyor - Gemini'nin gerçek, kredi kartı
    GEREKTİRMEYEN bir ücretsiz katmanı var (doğrulandı: Ağustos 2026,
    gemini-2.5-flash modeli günde 250-500 istek civarı ücretsiz limit -
    bizim senaryomuzda [10 dakikada bir tarama, çoğu turda hiç eşleşme
    yok] bu limite yaklaşmamız bile beklenmez).

    Haberin GERÇEKTEN o kalıbı anlatıp anlatmadığını ve şiddetini
    doğrular. (eşleşme:bool, şiddet:str, gerekçe:str) döner. Hata
    durumunda (eşleşme=False, ...) - yani BAŞARISIZ doğrulama OTOMATİK
    OLARAK REDDEDİLİR (güvenli taraf), asla varsayılan olarak kabul
    edilmez."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[haber_izleme] GEMINI_API_KEY tanimli degil, AI dogrulama atlaniyor.")
        return False, None, "API anahtari yok"
    try:
        import requests
        kalip_aciklama = _KALIP_ISIM.get(kalip_key, kalip_key)
        _yon_haritasi = _KALIP_KATEGORI_YONU.get(kalip_key, {})
        _kategori_aciklama = "; ".join(
            f"{_KATEGORI_ISIM_TR.get(k, k)} kategorisi {v}"
            for k, v in _yon_haritasi.items())
        prompt = f"""Bir finansal haber izleme sistemisin. Aşağıdaki haberin
GERÇEKTEN "{kalip_aciklama}" kategorisine ait, PİYASALARI ETKİLEYECEK
ÖNEMLİ bir olayı anlatıp anlatmadığını değerlendir.

Haber başlığı: {baslik}
Haber özeti: {ozet}
Kaynak: {kaynak}

Bu kalıp eşleşirse, normalde şu yönde etki beklenir: {_kategori_aciklama}

ÖNEMLİ: Sadece GERÇEKTEN önemli, taze, piyasa etkisi olası bir olaysa
eşleşme=true de. Genel yorum/analiz makaleleri, geçmiş olayların tekrar
anılması, veya kategoriye YÜZEYSEL benzeyen ama önemsiz haberler için
eşleşme=false de. Şüpheye düşersen false de (temkinli ol).

Eşleşirse, kullanıcıya sunulacak DOĞAL, AKICI BİR TÜRKÇE CÜMLE yaz -
TAM OLARAK şu kalıpta: "[Kaynak] kaynağından alınan habere göre,
[haberin somut içeriği - varsa haberdeki SAYISAL/SOMUT detayı (ör. '25
baz puan artış', '%X üretim kesintisi' gibi) MUTLAKA dahil et], bu
durumda [ilgili kategori(ler)]'in Optima Skorlarını [artırmamız/
azaltmamız] gerekir." - haberde somut bir sayı YOKSA sayı uydurma,
sadece "artış/azalış" yönünü belirt.

SADECE şu JSON formatında cevap ver, başka hiçbir metin ekleme:
{{"eslesme": true/false, "siddet": "Düşük"/"Orta"/"Yüksek", "gerekce": "yukarıdaki kalıpta doğal cümle (max 400 karakter)"}}"""
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               "gemini-2.5-flash:generateContent")
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        veri_ham = resp.json()
        metin = veri_ham["candidates"][0]["content"]["parts"][0]["text"].strip()
        metin = metin.replace("```json", "").replace("```", "").strip()
        veri = json.loads(metin)
        return (bool(veri.get("eslesme", False)),
                veri.get("siddet", "Orta"),
                str(veri.get("gerekce", ""))[:400])
    except Exception as e:
        print(f"[haber_izleme] AI dogrulama hatasi: {type(e).__name__}: {e}")
        return False, None, f"AI hatasi: {e}"


def main():
    from db import haber_islendi_mi, haber_islendi_isaretle, otomatik_tespit_ekle

    print(f"[haber_izleme] Baslangic: {datetime.datetime.now().isoformat()}")
    toplam_haber = 0
    on_filtre_gecen = 0
    ai_dogrulanan = 0

    for kaynak_adi, rss_url in _RSS_KAYNAKLARI:
        try:
            feed = feedparser.parse(rss_url)
        except Exception as e:
            print(f"[haber_izleme] {kaynak_adi} RSS okunamadi: {e}")
            continue

        for entry in feed.entries[:30]:  # her kaynaktan en yeni 30 haber
            url = entry.get("link", "")
            if not url:
                continue
            toplam_haber += 1

            if haber_islendi_mi(url):
                continue  # zaten islenmis, atla

            baslik = entry.get("title", "")
            ozet = entry.get("summary", "") or entry.get("description", "")

            eslesenler = _on_filtre_eslesen_kaliplar(baslik, ozet)
            if not eslesenler:
                haber_islendi_isaretle(url)  # eslesmeyen haberi de isaretle - tekrar bakma
                continue

            on_filtre_gecen += 1
            print(f"[haber_izleme] ON-FILTRE ESLESTI ({kaynak_adi}): {baslik[:80]} -> {eslesenler}")

            for kalip_key in eslesenler:
                eslesme, siddet, gerekce = _ai_dogrula(kalip_key, baslik, ozet, kaynak_adi)
                if eslesme:
                    otomatik_tespit_ekle(
                        kalip_key=kalip_key, siddet=siddet or "Orta",
                        haber_basligi=baslik[:300], haber_url=url,
                        haber_kaynak=kaynak_adi, ai_gerekce=gerekce)
                    ai_dogrulanan += 1
                    print(f"[haber_izleme] AI DOGRULADI: {kalip_key} ({siddet}) - {gerekce}")
                else:
                    print(f"[haber_izleme] AI REDDETTI ({kalip_key}): {gerekce}")

            haber_islendi_isaretle(url)
            time.sleep(1)  # API rate limit icin kucuk bir bekleme

    print(f"[haber_izleme] Bitti: {toplam_haber} haber tarandi, "
          f"{on_filtre_gecen} on-filtreden gecti, {ai_dogrulanan} AI ile dogrulandi.")


if __name__ == "__main__":
    main()
