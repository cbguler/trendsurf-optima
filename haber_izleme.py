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
Gemini'nin kredi karti GEREKTIRMEYEN gercek bir ucretsiz katmani var.
Gunluk cagri LIMITI KESIN OLARAK BILINMIYOR (bkz. v2.0.7.160 notu,
PROJE_NOTLARI.md) - bu yuzden kod kendi butcesini tutuyor
(_GUNLUK_AI_BUTCESI), kotanin comert oldugu VARSAYILMIYOR.

GUVENLIK: GEMINI_API_KEY GitHub Secrets'tan okunur, koda YAZILMAZ
(bu repo public).

v2.0.7.162 (Bahri'nin talebi, 19 Agustos 2026 - "kaliplara daha sonra
ekleme yapilabilir hale getirilebilir mi"): Kalip tanimlari ARTIK BURADA
KOPYA TUTULMUYOR - db.get_kaliplar() ile Supabase'den, app.py ile AYNI
kaynaktan okunuyor. Yeni kalip/kelime/etki eklemek Admin Paneli > "Kalip
Yonetimi" bolumunden yapilir, HICBIR DOSYADA kod degisikligi gerekmez.
"""
import os
import sys
import json
import re  # v2.0.7.161: kelime siniri eslestirmesi icin
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
    # v2.0.7.180 (Bahri'nin talebi, 22 Ağustos 2026 — "başka kaynak
    # bulamıyor muyuz?"): Dünya Gazetesi eklendi. Canlı test edildi
    # (22 Ağustos 14:31 TRT) - genel bir akış (BBC/Al Jazeera gibi,
    # ekonomi dışı içerik de var) ama Türkiye'nin köklü finans
    # gazetelerinden biri, gerçek ekonomi haberleri içeriyor. Zaten
    # Türkçe - _INGILIZCE_KAYNAKLAR setine EKLENMEDİ (çeviri gerekmiyor,
    # AA Ekonomi/Investing.com TR/BloombergHT ile aynı kategori).
    ("Dünya Gazetesi", "https://www.dunya.com/rss"),
    # v2.0.7.181 (Bahri'nin talebi, 22 Ağustos 2026 — "Anka Haber Ajansı,
    # T24, Euronews, Sözcü, Halk TV, Reuters, Xinhua, AFP - hangilerini
    # dahil edebiliriz"): 8 aday tek tek canlı test edildi. Kullanılamayan
    # 5'i (Anka - herkese açık RSS yok/şifreli abonelik, T24 - eski RSS
    # adresleri 404, Reuters - resmi RSS yıllar önce kapatıldı, Xinhua -
    # RSS'i 2017'den beri donmuş, AFP - sadece kurumsal/basın bülteni
    # RSS'i var, haber içeriği yok) eklenmedi. Çalışan 3'ü Bahri'nin
    # onayıyla eklendi:
    ("Sözcü Ekonomi", "https://www.sozcu.com.tr/feeds-rss-category-ekonomi"),
    ("Euronews Türkçe", "https://tr.euronews.com/rss"),
    # Halk TV: teknik olarak çalışıyor ama akışın büyük kısmı magazin/
    # asayiş/spor - ekonomi içerik oranı düşük, ayrıca CHP'ye tarihsel
    # bağı olan muhalif çizgide bir yayın organı (Bahri'ye bu şekilde
    # bildirildi, kararı onun). Anahtar kelime filtresi zaten alakasız
    # içeriği eleyecek.
    ("Halk TV", "https://www.halktv.com.tr/service/rss.php"),
]

# ══════════════════════════════════════════════════════════════
# v2.0.7.162 (Bahri'nin talebi, 19 Ağustos 2026 — "anahtar kelime
# ön-filtresi ve kalıplara daha sonra ekleme yapılabilir hale getirilebilir
# mi"): Kalıp tanımları ARTIK KODA GÖMÜLÜ DEĞİL, Supabase'deki
# haber_kaliplari/haber_kalip_kelime/haber_kalip_etki tablolarında.
# app.py İLE AYNI KAYNAKTAN okunuyor (db.get_kaliplar) - önceki sürümde
# burada olduğu gibi elle kopya tutmak GEREKMİYOR, "iki yerde de
# güncelle" riski ortadan kalktı. Yeni kalıp/kelime eklemek Admin
# Paneli > "Kalıp Yönetimi" bölümünden yapılır.
#
# Kelime sınırı eşleştirme kuralı (v2.0.7.161'de bulunan "warning"
# tuzağının çözümü) AYNEN KORUNUYOR: Türkçe sondan eklemeli olduğu için
# \bkelime\w*, İngilizce'de sadece çoğul olduğu için \bkelimes?\b.
_DERLENMIS_KALIPLAR = {}
_KALIP_ISIM = {}
_KALIP_KATEGORI_YONU = {}
_KATEGORI_ISIM_TR = {  # bu genel bir eşleme, kalıba özel değil - sabit kalır
    "MADEN": "Değerli Maden", "DOVIZ": "Döviz", "BIST": "BIST",
    "KRIPTO": "Kripto",
}


def _kaliplari_yukle():
    """v2.0.7.162: Script başlangıcında BİR KEZ çağrılır (main() içinde) -
    Supabase'den aktif kalıpları okuyup yukarıdaki 3 modül-seviyesi
    sözlüğü doldurur. DB ERİŞİLEMEZSE sözlükler BOŞ kalır - bu turda
    hiçbir haber hiçbir kalıba eşleşmez. Bu KASITLI: hata durumunda
    'her şeyi tespit et' değil 'hiçbir şey tespit etme' yönünde
    yanılmak güvenli taraftır (yanlış pozitif üretmemek)."""
    global _DERLENMIS_KALIPLAR, _KALIP_ISIM, _KALIP_KATEGORI_YONU
    from db import get_kaliplar
    try:
        kaliplar = get_kaliplar(sadece_aktif=True)
    except Exception as e:
        print(f"[haber_izleme] KALIP VERISI OKUNAMADI: {e} - bu turda "
              f"hicbir kalip aktif olmayacak, tum haberler atlanacak.")
        return

    _yeni_derlenmis, _yeni_isim, _yeni_yon = {}, {}, {}
    for k in kaliplar:
        kk = k["kalip_key"]
        _yeni_isim[kk] = k["ad"]
        _parcalar = []
        for _k_tr in k["kelimeler"].get("tr", []):
            _parcalar.append(re.escape(_k_tr.lower()) + r"\w*")
        for _k_en in k["kelimeler"].get("en", []):
            _parcalar.append(re.escape(_k_en.lower()) + r"s?\b")
        if _parcalar:
            _yeni_derlenmis[kk] = re.compile(
                r"\b(?:" + "|".join(_parcalar) + r")", re.IGNORECASE | re.UNICODE)
        # Yön puanın İŞARETİNDEN türetilir - ayrı saklanmaz (tek doğruluk
        # kaynağı: haber_kalip_etki.puan, iki yerde tutup sapma riski yok).
        _yeni_yon[kk] = {kat: ("artış" if puan > 0 else "azalış")
                         for kat, puan in k["etkiler"].items()}

    _DERLENMIS_KALIPLAR = _yeni_derlenmis
    _KALIP_ISIM = _yeni_isim
    _KALIP_KATEGORI_YONU = _yeni_yon
    print(f"[haber_izleme] {len(_DERLENMIS_KALIPLAR)} aktif kalip yuklendi: "
          f"{list(_DERLENMIS_KALIPLAR.keys())}")


def _on_filtre_eslesen_kaliplar(baslik, ozet):
    """v2.0.7.161: Kelime SINIRINA saygili eslestirme (eski surum duz
    alt-dize ariyordu, "warning" icindeki "war" yuzunden alakasiz haberler
    takiliyordu - bkz. yukaridaki not).
    Eslesen TUM kaliplari doner (bir haber birden fazla kaliba eslesebilir,
    orn. hem 'jeopolitik' hem 'petrol')."""
    metin = f"{baslik} {ozet}".lower()
    return [kk for kk, kalip in _DERLENMIS_KALIPLAR.items()
            if kalip.search(metin)]


# v2.0.7.164 (Bahri'nin bulgusu, 19 Ağustos 2026 - Actions logu ile
# doğrulandı): Gemini 429 "Too Many Requests" döndürüyor - bugünkü toplam
# çağrı sadece 20 (kendi koyduğumuz 120 bütçesinin çok altında) ve bu
# turdaki TEK Gemini isteği (çeviri) bile 429 aldı. Üçüncü taraf kaynaklar
# gemini-2.5-flash için dakikalık limit olarak 5/10/15 gibi BİRBİRİYLE
# ÇELİŞEN ama HEPSİ ÇOK DÜŞÜK rakamlar veriyor - bu, günlük kotadan çok
# DAKİKALIK limitin (ya da bu projeye özgü daha sıkı bir kotanın)
# vurulduğuna işaret ediyor. Kesin rakam Google AI Studio/Cloud Console'un
# kendi kota sayfasından görülmeli (bkz. PROJE_NOTLARI.md) - koda tahmini
# bir sayı gömülmedi, bunun yerine 429'a karşı TEK SEFERLİK, KISA bir
# bekleme + yeniden deneme eklendi (dakikalık pencere resetlenene kadar
# beklemek, aynı dakika içinde tekrar denemekten daha güvenilir)."""
# v2.0.7.164: Bir turda BİRDEN FAZLA on-filtre eşleşmesi varsa, her biri
# ayrı bir Gemini çağrısı yapar. 429 her çağrıda 65 sn beklenip yeniden
# denenirse, çok sayıda eşleşme olan bir turda TÜM 10 dakikalık workflow
# zaman aşımı retry beklemelerinde tükenebilir. Bu yüzden: bir kez
# "ardışık 429" (yani bekleyip tekrar denedik, YİNE 429) görülürse, bu
# TURUN GERİ KALANINDA artık BEKLEMEDEN (retry=1) denenir - hız için
# doğruluktan ödün verilmez, sadece gereksiz bekleme kesilir.
_ardisik_429_goruldu = False


def _gemini_istek_gonder(url, headers, payload, timeout=30, deneme=2, bekleme_sn=65):
    """requests.post'u SARMALAR - 429 (rate limit) alırsa `bekleme_sn`
    kadar bekleyip BİR KEZ DAHA dener (dakikalık pencerenin resetlenmesi
    için 65 sn - 60 sn'lik pencereden biraz fazla, güvenlik payı).
    429 DIŞINDAKİ hatalarda (400/401/500 vb.) YENİDEN DENEMEZ - bunlar
    beklemekle düzelmez (ör. geçersiz anahtar), zaman kaybettirir.
    Bu turda DAHA ÖNCE bekleyip tekrar deneyip YİNE 429 aldıysak, bir
    daha BEKLEMEZ (workflow'un 10 dakikalık zaman aşımını retry
    beklemelerinde tüketmemek için - bkz. yukarıdaki not).
    Son denemede de başarısız olursa exception'ı OLDUĞU GİBİ fırlatır -
    çağıran taraf (mevcut try/except) zaten güvenli şekilde ele alıyor."""
    global _ardisik_429_goruldu
    import requests
    _bu_cagrida_deneme = 1 if _ardisik_429_goruldu else deneme
    for _deneme_no in range(1, _bu_cagrida_deneme + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as e:
            _kod = e.response.status_code if e.response is not None else None
            if _kod == 429 and _deneme_no < _bu_cagrida_deneme:
                print(f"[haber_izleme] 429 alindi (deneme {_deneme_no}/{_bu_cagrida_deneme}) - "
                      f"{bekleme_sn} sn bekleyip tekrar denenecek.")
                time.sleep(bekleme_sn)
                continue
            if _kod == 429:
                _ardisik_429_goruldu = True
                print("[haber_izleme] 429 tekrarlandi - bu turun geri kalaninda "
                      "artik beklenmeyecek (zaman asimini korumak icin).")
            raise


def _ai_dogrula_prompt_olustur(kalip_key, baslik, ozet, kaynak):
    """v2.0.7.183: Gemini VE Groq'un AYNI prompt'u kullanması icin ortak
    fonksiyona cikarildi - iki saglayici arasinda tutarlilik saglar,
    ayni metni iki yerde elle senkron tutma riskini ortadan kaldirir."""
    kalip_aciklama = _KALIP_ISIM.get(kalip_key, kalip_key)
    _yon_haritasi = _KALIP_KATEGORI_YONU.get(kalip_key, {})
    _kategori_aciklama = "; ".join(
        f"{_KATEGORI_ISIM_TR.get(k, k)} kategorisi {v}"
        for k, v in _yon_haritasi.items())
    return f"""Bir finansal haber izleme sistemisin. Aşağıdaki haberin
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


def _gemini_ai_dogrula(kalip_key, baslik, ozet, kaynak):
    """v2.0.7.155/160: Google Gemini API ile dogrulama (bkz. asagidaki
    _ai_dogrula'nin genel aciklamasi). v2.0.7.183'te bu fonksiyon
    _ai_dogrula'dan bu isimle ayrildi - artik SADECE Gemini'yi dener,
    yedeklemeyi cagiran taraf (_ai_dogrula) yapiyor."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None  # None = "bu saglayici hic denenmedi", False DEGIL
    try:
        import requests
        prompt = _ai_dogrula_prompt_olustur(kalip_key, baslik, ozet, kaynak)
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               "gemini-2.5-flash:generateContent")
        resp = _gemini_istek_gonder(
            url,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            payload={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        veri_ham = resp.json()
        metin = veri_ham["candidates"][0]["content"]["parts"][0]["text"].strip()
        metin = metin.replace("```json", "").replace("```", "").strip()
        veri = json.loads(metin)
        return (bool(veri.get("eslesme", False)),
                veri.get("siddet", "Orta"),
                str(veri.get("gerekce", ""))[:400])
    except Exception as e:
        print(f"[haber_izleme] Gemini AI dogrulama hatasi: {type(e).__name__}: {e}")
        # v2.0.7.185 (Bahri'nin bulgusu, 25 Ağustos 2026 — canlı log):
        # KRİTİK HATA - eskiden burada `return False, None, ...` vardı,
        # yani Gemini 429/hata aldığında bu SONUÇ "Gemini'nin KESİN
        # CEVABI" (red) sayılıyordu ve _ai_dogrula HİÇ GROQ'A
        # DÜŞMÜYORDU - "AI REDDETTI" mesajı gerçekte Groq'a hiç şans
        # verilmeden yazılıyordu. ÇÖZÜM: artık None dönüyor - tıpkı
        # "anahtar yok" durumu gibi "bu sağlayıcı denenemedi" anlamına
        # geliyor, _ai_dogrula bunun üzerine Groq'u dener. Sadece HER
        # İKİ sağlayıcı da başarısız olursa gerçek bir red verilir.
        return None


def _groq_ai_dogrula(kalip_key, baslik, ozet, kaynak):
    """v2.0.7.183 (Bahri'nin talebi, 25 Ağustos 2026 — "ücretsiz başka
    metod yok mu"): Gemini kotası güvenilmez çıktığı için (bkz.
    PROJE_NOTLARI.md - defalarca 429, gerçek kota rakamı hiç netleşmedi,
    Bahri faturalandırmayı reddetti) GERÇEK, kart GEREKTİRMEYEN bir
    ikinci ücretsiz katman: Groq (console.groq.com). OpenAI-uyumlu API,
    llama-3.3-70b-versatile modeli - birden fazla bağımsız kaynakta
    "kart istemiyor, cömert, güvenilir" diye doğrulandı (Ağustos 2026
    araştırması). Groq'un `response_format: json_object` desteği
    SAYESİNDE Gemini'deki gibi ```json` temizleme triklerine gerek
    YOK - model DOĞRUDAN geçerli JSON döndürüyor.

    AYNI prompt, AYNI dönüş formatı (eşleşme/şiddet/gerekçe) - çağıran
    taraf hangi sağlayıcının cevap verdiğini bilmesine gerek duymuyor."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None  # None = "bu saglayici hic denenmedi"
    try:
        import requests
        prompt = _ai_dogrula_prompt_olustur(kalip_key, baslik, ozet, kaynak)
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
            timeout=30,
        )
        resp.raise_for_status()
        metin = resp.json()["choices"][0]["message"]["content"].strip()
        veri = json.loads(metin)
        return (bool(veri.get("eslesme", False)),
                veri.get("siddet", "Orta"),
                str(veri.get("gerekce", ""))[:400])
    except Exception as e:
        print(f"[haber_izleme] Groq AI dogrulama hatasi: {type(e).__name__}: {e}")
        # v2.0.7.185: Gemini ile AYNI tutarlilik - None doner, cunku
        # _ai_dogrula zaten Groq'tan SONRA gelen kod bloğunda bunu
        # dogru sekilde "hicbir saglayici basarili olmadi" diye
        # yorumluyor. Groq zincirin SON halkasi oldugu icin sonuc
        # pratikte ayni (haber reddedilir), ama tutarli semantik
        # ("None = bu saglayici kesin bir cevap vermedi") ileride
        # ucuncu bir saglayici eklenirse ayni hatanin tekrarlanmasini
        # onler.
        return None


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

    v2.0.7.183 (Bahri'nin talebi - "ücretsiz başka metod yok mu"):
    Google AI Studio'nun Rate Limit sayfası incelendi - "Tier 1"
    etiketi altında görünen cömert rakamlar (RPD 163/10.000 vb.)
    GERÇEK UYGULANAN limitle ÇELİŞİYORDU çünkü faturalandırma
    ("Set up prepay") aktive edilmemişti. Bahri kart eklemeyi
    AÇIKÇA REDDETTİ (finansal karar, saygı duyuldu). ÇÖZÜM: Gemini
    ARTIK TEK BAŞINA DEĞİL - ÖNCE Gemini denenir, BAŞARISIZ olursa
    (kota/hata/anahtar eksik) Groq'a (ikinci, tamamen ücretsiz,
    kart istemeyen bir sağlayıcı) düşülür. Çeviri katmanındaki
    (v2.0.7.176) İKİ KATMANLI mimariyle AYNI felsefe.

    Haberin GERÇEKTEN o kalıbı anlatıp anlatmadığını ve şiddetini
    doğrular. (eşleşme:bool, şiddet:str, gerekçe:str) döner. Hata
    durumunda (eşleşme=False, ...) - yani BAŞARISIZ doğrulama OTOMATİK
    OLARAK REDDEDİLİR (güvenli taraf), asla varsayılan olarak kabul
    edilmez."""
    sonuc = _gemini_ai_dogrula(kalip_key, baslik, ozet, kaynak)
    if sonuc is not None:
        return sonuc
    sonuc = _groq_ai_dogrula(kalip_key, baslik, ozet, kaynak)
    if sonuc is not None:
        return sonuc
    # v2.0.7.185: Bu satira iki farkli sebepten dusulebilir - (a) ne
    # GEMINI_API_KEY ne GROQ_API_KEY tanimli, VEYA (b) ikisi de
    # tanimli ama IKISI DE basarisiz oldu (ag hatasi, 429, gecersiz
    # yanit vb.) - mesaj artik ikisini de dogru yansitiyor.
    print("[haber_izleme] AI dogrulama BASARISIZ - ne Gemini ne Groq "
          "gecerli bir sonuc dondurdu (anahtar eksik VEYA ikisi de "
          "hata verdi - yukaridaki satirlara bak). Bu haber icin "
          "varsayilan olarak REDDEDILDI (guvenli taraf).")
    return False, None, "Ne Gemini ne Groq gecerli bir sonuc dondurdu"


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


def _toplu_ceviri(haberler):
    """v2.0.7.160: Bir turdaki TUM yeni Ingilizce basliklari TEK Gemini
    istegiyle cevirir (baslik basina ayri istek atmak gunluk kotayi
    hizla tuketirdi - 10 dakikada bir calisan bir script icin bu fark
    kritik).

    v2.0.7.179 (Bahri'nin talebi - "başlığı çevirebiliyorsak özeti de
    çevirebiliriz"): Girdi ARTIK 3'lu: [(url, baslik, ozet), ...].
    Cikti da genisledi: {url: {"baslik_tr": ..., "ozet_tr": ...}}.
    Ozet BOSSA sadece baslik cevrilir, ozet_tr o url icin None doner.

    HATA DURUMUNDA BOS SOZLUK doner - cagiran taraf orijinal basligi/
    ozeti kullanmaya devam eder, hicbir sey cokmez."""
    if not haberler:
        return {}
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return {}
    try:
        import requests
        satirlar = []
        for i, (_u, b, o) in enumerate(haberler):
            satirlar.append(f"{i+1}. BAŞLIK: {b}")
            if o:
                satirlar.append(f"   ÖZET: {o}")
        numarali = "\n".join(satirlar)
        prompt = f"""Aşağıdaki İngilizce haber başlıklarını ve (varsa) özetlerini Türkçeye çevir.

{numarali}

KURALLAR:
- Sadece çeviri yap, yorum ekleme, olmayan bilgi EKLEME.
- Özel isimleri (kurum, kişi, yer) Türkçede yaygın kullanılan haliyle yaz.
- Başlık üslubunu koru (kısa), özet üslubunu koru (birkaç cümle olabilir).
- ÖZET verilmeyen maddeler için "ozet" alanını boş bırak ("").
- SADECE şu JSON formatında cevap ver, başka hiçbir metin ekleme:
{{"ceviriler": {{"1": {{"baslik": "birinci başlığın çevirisi", "ozet": "birinci özetin çevirisi"}}, "2": {{"baslik": "...", "ozet": "..."}}}}}}"""
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               "gemini-2.5-flash:generateContent")
        resp = _gemini_istek_gonder(
            url,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            payload={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=45,
        )
        metin = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        metin = metin.replace("```json", "").replace("```", "").strip()
        ceviriler = json.loads(metin).get("ceviriler", {})
        sonuc = {}
        for i, (u, _b, _o) in enumerate(haberler):
            c = ceviriler.get(str(i + 1)) or ceviriler.get(i + 1) or {}
            if not isinstance(c, dict):
                continue  # beklenmeyen format - bu maddeyi atla, cokme
            bt = str(c.get("baslik", "")).strip()
            ot = str(c.get("ozet", "")).strip()
            if bt or ot:
                sonuc[u] = {
                    "baslik_tr": bt[:300] if bt else None,
                    "ozet_tr": ot[:500] if ot else None,
                }
        return sonuc
    except Exception as e:
        print(f"[haber_izleme] Toplu ceviri hatasi: {type(e).__name__}: {e}")
        return {}


def _ucretsiz_yedek_ceviri(haberler):
    """v2.0.7.176 (Bahri'nin talebi, 21 Ağustos 2026 — "haberleri
    translate edemiyorsan en azından çevir"): Gemini kotası güvenilmez
    çıktığı için (bkz. PROJE_NOTLARI.md v2.0.7.164 - 429 hataları) API
    anahtarı GEREKTİRMEYEN, ücretsiz bir yedek katman. `deep-translator`
    kütüphanesi Google Translate'in genel web arayüzünü kullanıyor -
    gayri resmi ama yaygın kullanılan, kota/anahtar sorunu YOK.

    Gemini'den DAHA BASİT: tek tek cümle çevirisi yapıyor, Gemini'nin
    "özel isimleri Türkçe yaygın haliyle yaz" gibi ince ayarları YOK -
    ama HİÇBİR ZAMAN kota/429 yüzünden tamamen durmuyor. İki katman
    birlikte: Gemini önce denenir (daha kaliteli), o başarısız/
    yetersiz kalırsa kalan haberler bu fonksiyona düşer.

    v2.0.7.179 (Bahri'nin talebi - "özeti de çevirebiliriz"): Girdi
    ARTIK 3'lu: [(url, baslik, ozet), ...]. Çıktı:
    {url: {"baslik_tr": ..., "ozet_tr": ...}}.

    v2.0.7.184 (Bahri'nin bulgusu, 25 Ağustos 2026 — canlı log):
    KRİTİK HATA BULUNDU VE DÜZELTİLDİ. Eskiden `translate_batch` TEK
    BİR çağrıyla TÜM başlıkları/özetleri çeviriyordu - ama
    `translate_batch` TÜM LİSTE İÇİN TEK BİR exception fırlatıyor,
    YANİ TEK BİR SORUNLU MADDE (ör. Google'ın çeviremediği bir başlık
    - canlıda görülen: "TranslationNotFound... No translation was
    found") TÜM 40 HABERLİK TURU ÇÖKERTIYORDU - 39 tanesi gayet
    çevrilebilir olsa bile. ÇÖZÜM: artık HER başlık/özet TEK TEK,
    KENDİ try/except'i İÇİNDE çevriliyor - biri başarısız olursa
    SADECE O ATLANIR, diğerleri ETKİLENMEZ.

    HATA DURUMUNDA (bir maddede) o maddenin çevirisi atlanır - çağıran
    taraf orijinal başlığı/özeti kullanmaya devam eder, hiçbir şey
    çökmez."""
    if not haberler:
        return {}
    try:
        from deep_translator import GoogleTranslator
        _cevirmen = GoogleTranslator(source="en", target="tr")
    except Exception as e:
        print(f"[haber_izleme] Ucretsiz yedek ceviri - kutuphane yuklenemedi: "
              f"{type(e).__name__}: {e}")
        return {}

    sonuc = {}
    _basarisiz_sayisi = 0
    for u, b, o in haberler:
        bt, ot = None, None
        try:
            tr = _cevirmen.translate(b)
            if tr and str(tr).strip():
                bt = str(tr).strip()[:300]
        except Exception as e:
            _basarisiz_sayisi += 1
            print(f"[haber_izleme] Ucretsiz yedek - baslik cevrilemedi "
                  f"(atlaniyor, diger haberler etkilenmez): {type(e).__name__}: {e}")
        if o:
            try:
                tr = _cevirmen.translate(o)
                if tr and str(tr).strip():
                    ot = str(tr).strip()[:500]
            except Exception as e:
                print(f"[haber_izleme] Ucretsiz yedek - ozet cevrilemedi "
                      f"(atlaniyor): {type(e).__name__}: {e}")
        if bt or ot:
            sonuc[u] = {"baslik_tr": bt, "ozet_tr": ot}
    if _basarisiz_sayisi:
        print(f"[haber_izleme] Ucretsiz yedek: {_basarisiz_sayisi}/{len(haberler)} "
              f"basliğin cevirisi basarisiz oldu (tek tek denendigi icin "
              f"diger {len(haberler) - _basarisiz_sayisi} basarili oldu).")
    return sonuc


def main():
    global _ardisik_429_goruldu
    _ardisik_429_goruldu = False  # v2.0.7.164: her tur temiz baslar

    from db import (haber_islendi_mi, haber_islendi_isaretle, otomatik_tespit_ekle,
                    haber_akisi_ekle, haber_akisi_ceviri_yaz, haber_akisi_temizle,
                    ai_cagri_sayisi_bugun, ai_cagri_kaydet, get_cevrilmemis_haberler)

    print(f"[haber_izleme] Baslangic: {datetime.datetime.now().isoformat()}")
    # v2.0.7.162: kaliplar HER TURDA yeniden yuklenir (script her calistiginda
    # tazeden basliyor, onceki turdan hafiza yok) - Admin Panelinde yapilan
    # bir degisiklik EN GEC 10 dakika icinde (bir sonraki tur) devreye girer.
    _kaliplari_yukle()
    if not _DERLENMIS_KALIPLAR:
        print("[haber_izleme] UYARI: hic aktif kalip yuklenemedi - bu tur "
              "hicbir haberi tespit edemeyecek (haberler yine de akisa "
              "yazilacak, sadece eslesen_kalip hep bos kalacak).")
    toplam_haber = 0
    on_filtre_gecen = 0
    ai_dogrulanan = 0
    akisa_eklenen = 0

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
            # v2.0.7.179: ozet artik Haberler sayfasinda KULLANICIYA
            # DOGRUDAN gosteriliyor (once sadece AI prompt'u icin
            # perde arkasinda kullaniliyordu). Bazi RSS kaynaklari
            # ozet alaninda HTML etiketi (<p>, <a> vb.) barindirabiliyor -
            # temizlenmezse ekranda ciplak etiket olarak gorunurdu.
            if ozet:
                ozet = re.sub(r"<[^>]+>", " ", ozet)
                ozet = re.sub(r"\s+", " ", ozet).strip()

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
                yayin_zamani=yayin_zamani, ozet=ozet[:500] if ozet else None)
            akisa_eklenen += 1

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

    # ── v2.0.7.161: TOPLU CEVIRI (veritabani tabanli, kendini onarir) ──
    # v2.0.7.160'ta bu blok bellekteki `ceviri_kuyrugu`ndan besleniyordu:
    # o turda Gemini cagrisi basarisiz olursa haberler SONSUZA KADAR
    # Ingilizce kaliyordu. Artik veritabanindaki cevrilmemis satirlar
    # okunuyor - sorun cozulunce birikmis basliklar kendiliginden cevriliyor.
    #
    # v2.0.7.176 (Bahri'nin talebi, 21 Ağustos 2026 — "haberleri translate
    # edemiyorsan en azından çevir"): ARTIK İKİ KATMANLI. Gemini kotası
    # güvenilmez çıktı (bkz. v2.0.7.164 - aynı gün içinde bile 429
    # alınabiliyor). Gemini ÖNCE denenir (daha kaliteli - özel isimleri
    # Türkçe yaygın haliyle yazıyor), ama Gemini NEYİ ÇEVİREMEZSE
    # (kota doldu / API hatası / anahtar eksik / kısmen başarısız),
    # KALAN başlıklar HER ZAMAN `_ucretsiz_yedek_ceviri`ye düşer - bu
    # katman API anahtarı/kota GEREKTİRMEZ, bizim günlük AI bütçemizden
    # BAĞIMSIZDIR. Sonuç: çeviri artık HİÇBİR ZAMAN tamamen durmaz.
    cevrilen = 0
    cevrilen_gemini = 0
    cevrilen_yedek = 0
    bekleyen_ceviri = get_cevrilmemis_haberler(sorted(_INGILIZCE_KAYNAKLAR), limit=40)
    if bekleyen_ceviri:
        _cevrilenler_url = set()
        _bugunku = ai_cagri_sayisi_bugun()
        if _bugunku >= _CEVIRI_ONCELIK_ESIGI:
            print(f"[haber_izleme] Gemini ceviri ATLANDI - gunluk AI butcesi "
                  f"({_bugunku}/{_CEVIRI_ONCELIK_ESIGI}) doldu. Ucretsiz yedege gecilecek.")
        elif not os.environ.get("GEMINI_API_KEY", ""):
            print("[haber_izleme] Gemini ceviri ATLANDI - GEMINI_API_KEY ortam "
                  "degiskeni BOS/TANIMSIZ. Ucretsiz yedege gecilecek.")
        else:
            print(f"[haber_izleme] Gemini ile ceviri deneniyor: {len(bekleyen_ceviri)} haber (baslik+ozet)...")
            ceviriler = _toplu_ceviri(bekleyen_ceviri)
            ai_cagri_kaydet(1)
            for u, c in ceviriler.items():
                haber_akisi_ceviri_yaz(u, baslik_tr=c.get("baslik_tr"), ozet_tr=c.get("ozet_tr"))
                _cevrilenler_url.add(u)
                cevrilen_gemini += 1
            if cevrilen_gemini:
                print(f"[haber_izleme] Gemini {cevrilen_gemini} haber cevirdi.")

        # v2.0.7.176: Gemini'nin CEVİREMEDİĞİ (yukarıda atlandıysa TÜMÜ,
        # kısmen başarısız olduysa KALANI) her zaman ücretsiz yedeğe düşer.
        _kalan = [(u, b, o) for u, b, o in bekleyen_ceviri if u not in _cevrilenler_url]
        if _kalan:
            print(f"[haber_izleme] Ucretsiz yedek ile ceviri deneniyor: {len(_kalan)} haber (baslik+ozet)...")
            yedek_ceviriler = _ucretsiz_yedek_ceviri(_kalan)
            for u, c in yedek_ceviriler.items():
                haber_akisi_ceviri_yaz(u, baslik_tr=c.get("baslik_tr"), ozet_tr=c.get("ozet_tr"))
                cevrilen_yedek += 1
            if cevrilen_yedek:
                print(f"[haber_izleme] Ucretsiz yedek {cevrilen_yedek} haber cevirdi.")

        cevrilen = cevrilen_gemini + cevrilen_yedek
        if cevrilen == 0:
            print("[haber_izleme] UYARI: NE Gemini NE ucretsiz yedek basarili oldu - "
                  "yukaridaki hata satirlarina bak. Basliklar Ingilizce kalacak, "
                  "sonraki turda tekrar denenecek.")

    haber_akisi_temizle(7)  # 7 gunden eskiyi sil - tablo sinirsiz buyumesin

    print(f"[haber_izleme] Bitti: {toplam_haber} haber tarandi, "
          f"{akisa_eklenen} akisa eklendi, {cevrilen} baslik cevrildi "
          f"(Gemini: {cevrilen_gemini}, ucretsiz yedek: {cevrilen_yedek}), "
          f"{on_filtre_gecen} on-filtreden gecti, {ai_dogrulanan} AI ile dogrulandi. "
          f"Bugunku toplam AI cagrisi: {ai_cagri_sayisi_bugun()}/{_GUNLUK_AI_BUTCESI}")


if __name__ == "__main__":
    main()
