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
    GEREKTİRMEYEN bir ücretsiz katmanı var.

    v2.0.7.160 DÜZELTMESİ: Buradaki eski "günde 250-500 istek" ifadesi
    DOĞRULANMAMIŞ bir iddiaydı, kaldırıldı. 19 Ağustos 2026'da yapılan
    araştırmada üçüncü taraf kaynaklar gemini-2.5-flash için günlük
    20 / 50 / 250 / 500 / 1500 gibi BİRBİRİYLE ÇELİŞEN rakamlar verdi
    ve Aralık 2025'te limitin bir kez düşürüldüğü bildirildi. Gerçek
    limit bilinmiyor - bu yüzden kod artık kotanın cömert olduğunu
    VARSAYMIYOR, _GUNLUK_AI_BUTCESI ile kendi sayacını tutuyor.

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


# ══════════════════════════════════════════════════════════════
# v2.0.7.160: Toplu ceviri (SADECE Ingilizce kaynaklar)
# ══════════════════════════════════════════════════════════════
# Bahri'nin karari (19 Agustos 2026): 5 kaynagin 3'u (AA Ekonomi,
# Investing.com TR, BloombergHT) ZATEN TURKCE - onlara hic dokunulmaz.
# Sadece BBC World ve Al Jazeera cevrilir.
_INGILIZCE_KAYNAKLAR = {"BBC World", "Al Jazeera"}

# GUNLUK GEMINI CAGRI BUTCESI. Gemini ucretsiz katmanin gercek gunluk
# limiti BELIRSIZ (ucuncu taraf kaynaklar 20/50/250/500/1500 gibi
# celiskili rakamlar veriyor, Aralik 2025'te bir kez dusuruldugu
# bildirildi - bkz. PROJE_NOTLARI.md). Bu yuzden kotanin comert oldugu
# VARSAYILMIYOR: gunluk toplam cagri bu sayiyi asinca CEVIRI durur
# (haberler orijinal Ingilizce basligiyla gorunmeye devam eder),
# ama TESPIT DOGRULAMASI durmaz - o sistemin asil isi, ceviri kozmetik.
_GUNLUK_AI_BUTCESI = 120
_CEVIRI_ONCELIK_ESIGI = 100  # bu sayiyi asinca ceviri durur, dogrulama devam


def _toplu_ceviri(basliklar):
    """v2.0.7.160: Bir turdaki TUM yeni Ingilizce baslikleri TEK Gemini
    istegiyle cevirir (baslik basina ayri istek atmak gunluk kotayi
    hizla tuketirdi - 10 dakikada bir calisan bir script icin bu fark
    kritik). Girdi: [(url, baslik), ...] Cikti: {url: turkce_baslik}.

    HATA DURUMUNDA BOS SOZLUK doner - cagiran taraf orijinal basligi
    kullanmaya devam eder, hicbir sey cokmez."""
    if not basliklar:
        return {}
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return {}
    try:
        import requests
        numarali = "\n".join(f"{i+1}. {b}" for i, (_u, b) in enumerate(basliklar))
        prompt = f"""Aşağıdaki İngilizce haber başlıklarını Türkçeye çevir.

{numarali}

KURALLAR:
- Sadece çeviri yap, yorum ekleme, başlığa olmayan bilgi EKLEME.
- Özel isimleri (kurum, kişi, yer) Türkçede yaygın kullanılan haliyle yaz.
- Haber başlığı üslubunu koru, kısa tut.
- SADECE şu JSON formatında cevap ver, başka hiçbir metin ekleme:
{{"ceviriler": {{"1": "birinci başlığın çevirisi", "2": "ikinci başlığın çevirisi"}}}}"""
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               "gemini-2.5-flash:generateContent")
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=45,
        )
        resp.raise_for_status()
        metin = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        metin = metin.replace("```json", "").replace("```", "").strip()
        ceviriler = json.loads(metin).get("ceviriler", {})
        sonuc = {}
        for i, (u, _b) in enumerate(basliklar):
            tr = ceviriler.get(str(i + 1)) or ceviriler.get(i + 1)
            if tr and str(tr).strip():
                sonuc[u] = str(tr).strip()[:300]
        return sonuc
    except Exception as e:
        print(f"[haber_izleme] Toplu ceviri hatasi: {type(e).__name__}: {e}")
        return {}


def main():
    from db import (haber_islendi_mi, haber_islendi_isaretle, otomatik_tespit_ekle,
                    haber_akisi_ekle, haber_akisi_ceviri_yaz, haber_akisi_temizle,
                    ai_cagri_sayisi_bugun, ai_cagri_kaydet)

    print(f"[haber_izleme] Baslangic: {datetime.datetime.now().isoformat()}")
    toplam_haber = 0
    on_filtre_gecen = 0
    ai_dogrulanan = 0
    akisa_eklenen = 0
    # v2.0.7.160: bu turda cevrilecek Ingilizce basliklar burada birikir,
    # tur sonunda TEK istekle cevrilir (baslik basina ayri istek DEGIL).
    ceviri_kuyrugu = []

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

            # v2.0.7.160: yayin zamani RSS'ten alinmaya calisilir - yoksa
            # None kalir, db tarafi eklenme_zamani'na duser (COALESCE).
            yayin_zamani = None
            try:
                _pp = entry.get("published_parsed") or entry.get("updated_parsed")
                if _pp:
                    yayin_zamani = datetime.datetime(*_pp[:6])
            except Exception:
                yayin_zamani = None

            eslesenler = _on_filtre_eslesen_kaliplar(baslik, ozet)

            # v2.0.7.160 (Bahri'nin talebi - Haberler sayfasi): ESLESSIN
            # YA DA ESLESMESIN her haber akisa yazilir. Eslesmeyenler
            # "sistem calisiyor, ortalik sakin" bilgisini tasidigi icin
            # EN AZ eslesenler kadar degerli - eskiden atiliyorlardi.
            haber_akisi_ekle(
                haber_url=url, kaynak=kaynak_adi, baslik=baslik[:300],
                eslesen_kalip=",".join(eslesenler) if eslesenler else None,
                yayin_zamani=yayin_zamani)
            akisa_eklenen += 1
            if kaynak_adi in _INGILIZCE_KAYNAKLAR:
                ceviri_kuyrugu.append((url, baslik[:300]))

            if not eslesenler:
                haber_islendi_isaretle(url)  # eslesmeyen haberi de isaretle - tekrar bakma
                continue

            on_filtre_gecen += 1
            print(f"[haber_izleme] ON-FILTRE ESLESTI ({kaynak_adi}): {baslik[:80]} -> {eslesenler}")

            for kalip_key in eslesenler:
                if ai_cagri_sayisi_bugun() >= _GUNLUK_AI_BUTCESI:
                    print("[haber_izleme] GUNLUK AI BUTCESI DOLDU - dogrulama atlaniyor.")
                    break
                eslesme, siddet, gerekce = _ai_dogrula(kalip_key, baslik, ozet, kaynak_adi)
                ai_cagri_kaydet(1)
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

    # ── v2.0.7.160: TOPLU CEVIRI (tur sonunda, tek istek) ──────────────
    # Butce esigi asildiysa ceviri HIC yapilmaz - haberler orijinal
    # Ingilizce basligiyla gorunur. Tespit dogrulamasi bundan etkilenmez
    # (yukarida ayri butce kontrolu var, esigi daha yuksek).
    cevrilen = 0
    if ceviri_kuyrugu:
        if ai_cagri_sayisi_bugun() >= _CEVIRI_ONCELIK_ESIGI:
            print(f"[haber_izleme] Ceviri butcesi doldu - {len(ceviri_kuyrugu)} "
                  f"baslik orijinal haliyle kalacak.")
        else:
            # Cok uzun listeyi tek istege sikistirmamak icin 40'lik parcalar
            for i in range(0, len(ceviri_kuyrugu), 40):
                parca = ceviri_kuyrugu[i:i + 40]
                ceviriler = _toplu_ceviri(parca)
                ai_cagri_kaydet(1)
                for u, tr in ceviriler.items():
                    haber_akisi_ceviri_yaz(u, tr)
                    cevrilen += 1

    haber_akisi_temizle(7)  # 7 gunden eskiyi sil - tablo sinirsiz buyumesin

    print(f"[haber_izleme] Bitti: {toplam_haber} haber tarandi, "
          f"{akisa_eklenen} akisa eklendi, {cevrilen} baslik cevrildi, "
          f"{on_filtre_gecen} on-filtreden gecti, {ai_dogrulanan} AI ile dogrulandi. "
          f"Bugunku toplam AI cagrisi: {ai_cagri_sayisi_bugun()}/{_GUNLUK_AI_BUTCESI}")


if __name__ == "__main__":
    main()
