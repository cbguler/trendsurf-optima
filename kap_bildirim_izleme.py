# -*- coding: utf-8 -*-
"""
kap_bildirim_izleme.py — TrendSurf Optima
Hisse-özel KAP bildirim tespit katmanı (v2.0.7.302, 15 Eylül 2026, O&M4,
Bahri'nin bulgusu — "CATES'te VBTS tedbiri haberini haber_izleme hiç
yakalamadı, ilginç bir haber aldım, gözden kaçırıyor mu?").

haber_izleme.py'den KASITLI olarak AYRI bir script - o 6 MAKRO kalıbı
(jeopolitik/petrol/fed/kredi_notu/kripto_olay/tcmb_kredibilite) genel
RSS akışlarında arıyor; bu script ise PORTFÖYDEKİ HER TICKER için
KAP'ın (Kamuyu Aydınlatma Platformu) o şirkete özel bildirimlerini
(VBTS tedbiri, sermaye artırımı, temettü kararı, vb.) takip ediyor.
Bu, tamamen farklı bir veri şekli (hisse bazlı, skor değiştirmeyen,
salt-okunur bilgilendirme) olduğu için beklenti_otomatik_tespit
tablosunun (onay/red akışlı, skor formülüne uygulanan) İÇİNE
SIKIŞTIRILMADI - ayrı bir tablo (kap_bildirim_takip) kullanıyor.

VERİ KAYNAĞI: KAP'ın RESMİ REST API'si ("KAP Veri Yayın Servisi")
GERÇEK ZAMANLI erişim için Borsa İstanbul A.Ş. ile ÜCRETLİ bir veri
dağıtım sözleşmesi imzalanmasını GEREKTİRİYOR - bu proje için kapalı
bir yol (Bahri'nin standing "ücretsiz olmayan hiçbir şeyi kurmayız"
ilkesiyle çelişiyor). Bunun yerine KAP'ın HERKESE AÇIK web sitesindeki,
kimlik doğrulama GEREKTİRMEYEN bir uç nokta kullanılıyor:

    https://www.kap.org.tr/tr/api/batch-news/file-by-year/{mkkMemberOid}/{yıl}

Bu, şirketin o yılki TÜM bildirimlerini (.doc uzantılı ama aslında
düz HTML) döndürüyor - CANLI test edildi (15 Eylül 2026, CATES ile):
bugünkü VBTS tedbiri bildirimi TAM METİN olarak, haberdeki metinle
BİREBİR eşleşerek bulundu. `mkkMemberOid`, KAP_BIST.xlsx'teki slug
üzerinden `sirket-bilgileri/ozet/{slug}` sayfasının HTML'sine gömülü
JSON'dan çıkarılıyor (kap_client.py'nin ZATEN kullandığı AYNI slug
kaynağı - yeni bir dosya/eşleme GEREKMEDİ).

NOT (kap_client.py'deki UYARIYLA AYNI): KAP.org.tr bazı IP'lerden 403
dönebilir - bu durumda o ticker için o turda hiçbir şey tespit
edilmez, uygulama çalışmaya devam eder, bir SONRAKİ turda tekrar
denenir.

Tetikleme: GitHub Actions'ın kendi `schedule` tetikleyicisi BİLEREK
KULLANILMADI - bugün (14-15 Eylül 2026, aynı O&M4 oturumu) TEFAS
güncellemesinde KANITLANMIŞ "GitHub'ın schedule'ı best-effort, sık
aralıklarda GÜVENİLMEZ" sorunu (bkz. v2.0.7.297, v2.0.7.301) burada
TEKRARLANMASIN diye - sadece workflow_dispatch var, tetikleme
cron-job.org'dan (Bahri'nin dashboard'dan kuracağı) yapılacak.
"""
import os
import sys
import re
import time
import datetime

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from kap_client import KAP_SLUG_MAP, KAP_HEADERS

# ══════════════════════════════════════════════════════════════
# Bilinen ROUTINE (sık tekrar eden, genelde bilgilendirme dışı
# değeri düşük) bildirim başlıkları - bunlar "onemli_mi=False" ile
# kaydedilir, app.py varsayılan görünümde GİZLER ama "tümünü göster"
# ile hâlâ erişilebilir. CANLI test edilen CATES örneğinde 49
# bildirimin büyük kısmının bu TEK türden (devre kesici) olduğu
# görüldü - filtrelenmezse gerçek sinyal (VBTS gibi) kaybolur.
_ROUTIN_BASLIKLAR = {
    "Pay Bazında Devre Kesici Bildirimi",
}

# mkkMemberOid'leri tekrar tekrar KAP'tan cekmemek icin yerel cache.
_OID_CACHE_YOLU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "kap_mkk_oid_cache.json")


def _oid_cache_yukle() -> dict:
    import json
    try:
        with open(_OID_CACHE_YOLU, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _oid_cache_kaydet(cache: dict):
    import json
    try:
        with open(_OID_CACHE_YOLU, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[kap_bildirim_izleme] oid cache yazilamadi: {e}")


def _mkk_member_oid_bul(ticker: str, cache: dict) -> str:
    """KAP_BIST.xlsx'teki slug'i kullanarak sirketin ozet sayfasini
    ceker, gomulu JSON'dan mkkMemberOid'i regex ile cikarir. Cache'te
    varsa AG HIC KULLANILMAZ."""
    if ticker in cache:
        return cache[ticker]
    slug_url = KAP_SLUG_MAP.get(ticker)
    if not slug_url:
        return ""
    slug = slug_url.rstrip("/").split("/")[-1]
    try:
        r = requests.get(f"https://www.kap.org.tr/tr/sirket-bilgileri/ozet/{slug}",
                          headers=KAP_HEADERS, timeout=15)
        if r.status_code != 200:
            return ""
        m = re.search(r'\\?"mkkMemberOid\\?"\s*:\s*\\?"([a-f0-9]+)\\?"', r.text)
        if not m:
            return ""
        oid = m.group(1)
        cache[ticker] = oid
        return oid
    except Exception as e:
        print(f"[kap_bildirim_izleme] {ticker} icin mkkMemberOid bulunamadi: {e}")
        return ""


# v2.0.7.302: her bildirim iki <h1> (gonderen + konu baslik) ve hemen
# ardindan "Gonderim Tarihi:" iceriyor - CANLI test edilen CATES
# ornekte 49/49 bildirim bu desenle EKSIKSIZ yakalandi.
_BILDIRIM_DESENI = re.compile(
    r'<h1[^>]*>([^<]*)</h1>\s*<h1[^>]*>([^<]*)</h1>\s*<div>\s*'
    r'Gönderim Tarihi:([\d.]+ [\d:]+)\s*</div>',
    re.DOTALL,
)


def _yillik_bildirimleri_cek(mkk_member_oid: str, yil: int) -> list:
    """Donus: [{"gonderen":..., "baslik":..., "tarih": datetime, "icerik_ozet":...}]

    NOT: KAP bu uc noktadan yaniti bir ZIP ARSIVI olarak donuyor - icinde
    TEK bir ".doc" uzantili dosya var, ama o dosyanin KENDISI aslinda
    duz HTML (Word/Excel'in eski "HTML'i .doc olarak kaydet" hilesi).
    Once zip'i acmak GEREKIYOR - bu adim atlanirsa (ilk denemede oldugu
    gibi) ham ZIP baytlari UTF-8 olarak cozulmeye calisilir ve hicbir
    "Gönderim Tarihi" deseni eslesmez, sessizce 0 bildirim doner."""
    import io
    import zipfile

    url = f"https://www.kap.org.tr/tr/api/batch-news/file-by-year/{mkk_member_oid}/{yil}"
    try:
        r = requests.get(url, headers=KAP_HEADERS, timeout=25)
        if r.status_code != 200:
            return []
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            iç_dosyalar = z.namelist()
            if not iç_dosyalar:
                return []
            metin = z.read(iç_dosyalar[0]).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[kap_bildirim_izleme] yillik bildirim cekilemedi ({mkk_member_oid}): {e}")
        return []

    sonuc = []
    for gonderen, baslik, tarih_str in _BILDIRIM_DESENI.findall(metin):
        try:
            tarih = datetime.datetime.strptime(tarih_str.strip(), "%d.%m.%Y %H:%M:%S")
        except ValueError:
            continue
        # Icerik ozeti: "Gönderim Tarihi:"nden hemen sonraki kisim
        # SADECE metadata (Bildirim Tipi, Yil, Periyot, Ilgili
        # Sirketler/Fonlar) - GERCEK aciklama metni "Bildirim İçeriği"
        # basligindan SONRAKI "Açıklamalar" alt basligindan sonra
        # geliyor (CANLI test sirasinda bulundu - "Açıklamalar" kelimesi
        # metinde İKİ KEZ geçiyor: once BOŞ bir tablo sütun başlığı
        # olarak, sonra GERÇEK içeriğin hemen öncesinde - ilkini almak
        # sadece metadata veriyordu, "Bildirim İçeriği" çapa olarak
        # kullanılınca ikincisi doğru yakalanıyor).
        idx = metin.find(f"Gönderim Tarihi:{tarih_str}")
        icerik_ozet = ""
        if idx >= 0:
            parca = metin[idx:idx + 6000]
            icerik_idx = parca.find("Bildirim İçeriği")
            if icerik_idx >= 0:
                parca = parca[icerik_idx + len("Bildirim İçeriği"):]
                aciklama_idx = parca.find("Açıklamalar")
                if aciklama_idx >= 0:
                    parca = parca[aciklama_idx + len("Açıklamalar"):]
            duz = re.sub(r"<[^>]+>", " ", parca)
            duz = re.sub(r"\s+", " ", duz).strip()
            icerik_ozet = duz[:600]
        sonuc.append({
            "gonderen": gonderen.strip(),
            "baslik": baslik.strip(),
            "tarih": tarih,
            "icerik_ozet": icerik_ozet,
        })
    return sonuc


def calistir():
    """v2.0.7.311 (15 Eylul 2026, O&M4): v2.0.7.310'da eklenen
    db.toplu_mod_ac()/kapat() KALDIRILDI - haber_izleme.py'nin canli
    log'unda bu mekanizmanin hicbir zaman gercekten calismadigi
    (baglanti hep "canli degil" sayilip yeniden aciliyordu) bulundu,
    muhtemelen Supabase'in transaction pooler baglanti turuyle uyumsuz.
    Detaylar icin PROJE_NOTLARI.md v2.0.7.311 girdisine bakin."""
    _calistir_asil()


def _calistir_asil():
    db.init_db()
    tickerlar = db.get_tum_portfoy_tickerlari()
    print(f"[kap_bildirim_izleme] {len(tickerlar)} ticker kontrol edilecek: {tickerlar}")

    cache = _oid_cache_yukle()
    yil = datetime.datetime.now().year
    esik_tarih = datetime.datetime.now() - datetime.timedelta(hours=36)

    toplam_yeni = 0
    for ticker in tickerlar:
        oid = _mkk_member_oid_bul(ticker, cache)
        if not oid:
            print(f"[kap_bildirim_izleme] {ticker}: mkkMemberOid bulunamadi, atlaniyor.")
            continue

        bildirimler = _yillik_bildirimleri_cek(oid, yil)
        yeni_sayisi = 0
        for b in bildirimler:
            if b["tarih"] < esik_tarih:
                continue  # eski bildirim, zaten islenmis olmali
            onemli_mi = b["baslik"] not in _ROUTIN_BASLIKLAR
            eklendi = db.kap_bildirim_ekle(
                ticker=ticker, kap_baslik=b["baslik"], gonderen=b["gonderen"],
                gonderim_tarihi=b["tarih"], icerik_ozet=b["icerik_ozet"],
                onemli_mi=onemli_mi)
            if eklendi:
                yeni_sayisi += 1
        print(f"[kap_bildirim_izleme] {ticker}: {len(bildirimler)} bildirim tarandi, "
              f"{yeni_sayisi} yeni/guncellendi (36 saatlik pencere).")
        toplam_yeni += yeni_sayisi
        time.sleep(1)  # KAP'a nazik davran - ardisik hizli istek yok

    _oid_cache_kaydet(cache)
    db.kap_bildirim_temizle(gun=14)
    print(f"[kap_bildirim_izleme] Bitti. Toplam yeni kayit: {toplam_yeni}")


if __name__ == "__main__":
    calistir()
