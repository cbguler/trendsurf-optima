# -*- coding: utf-8 -*-
"""
kap_risk.py - TrendSurf Optima
KAP bildirimlerinden HISSE BAZLI risk uyarisi cikarma (siniflandirma + gosterim yardimcilari).

v2.0.7.373 (8 Ekim 2026, Bahri'nin bulgusu - ENERY): KAP'ta cikan bildirimler daha once SADECE
portfoydeki hisseler icin ve SADECE bilgi amacli izleniyordu; hicbiri skora/sinyale yansimiyordu.
Bu modul, KAP'in TOPLU bildirim listesinden (tum sirketler, tarih araligi) gelen bildirimleri
siniflandirir ve her hisse icin "su an gecerli" risk listesini cikarir.

Streamlit'e VE veritabanina bagimli DEGILDIR (kap_risk_tarama.py tarar/saklar, app.py gosterir).

BILDIRIM SOZLUGU (kap_risk_tarama.py normallestirir):
    {"id": int, "tarih": datetime, "gonderen": str (KAP'taki gonderen),
     "konu": str (bildirim turu/basligi), "ozet": str (KAP'in kisa basligi),
     "gonderen_kodlar": [TICKER...] (bildirimi gonderen sirketin kodlari),
     "ilgili_kodlar": [TICKER...] (Borsa/KAP/SPK bildirimlerinde konu olan sirketler),
     "metin": str (tam metin; SADECE VBTS ve sermaye bildirimleri icin cekilir, digerlerinde bos)}

SINIFLANDIRMA ILKELERI (CANLI KAP verisinde dogrulandi - basliga bakmak TEK BASINA YETMEZ):
  * "SPK Islem Yasagi Nedeniyle Pay Duyurusu" KISI bazli bir yasagi duyurur ve THYAO, AKBNK gibi
    onlarca sirketi "ilgili sirket" olarak listeler -> hisse riski DEGIL, BILEREK yok sayilir.
  * VBTS/brut takas tedbirleri "BISTECH Pay Piyasasi Alim Satim Sistemi Duyurusu" konusuyla, birden
    cok hisseyi iceren duyuru olarak gelir; hangi hissenin hangi asamada oldugu ve BITIS TARIHI
    metindeki "XXXX.E payları ... kadar ..." cumlesinden okunur.
  * Sirketin KENDI gonderdigi bildirimler (sermaye, denetim, geri alim...) sadece gonderen sirketin
    koduna yazilir (Borsa/KAP/SPK bildirimleri ise "ilgili" kodlara).
  * Risk listesi her seferinde bildirim arsivinden SIFIRDAN hesaplanir: hisse yeniden islemeye
    acilinca ya da suresi dolunca uyari kendiliginden kalkar.

SEVIYELER:  AGIR  -> Optima Skor 0, sinyal "KAP UYARISI"
            ORTA  -> Optima Skor x0.5, sinyal "KAP DIKKAT"
            BILGI -> skor/sinyal DEGISMEZ, sadece detay seridinde bilgi (geri alim, bedelsiz vb.)
"""
import datetime
import html as _html
import re

SEVIYE_AGIR = "AGIR"
SEVIYE_ORTA = "ORTA"
SEVIYE_BILGI = "BILGI"
_SIDDET = {SEVIYE_AGIR: 3, SEVIYE_ORTA: 2, SEVIYE_BILGI: 1}

SINYAL_KAP_AGIR = "KAP UYARISI"
SINYAL_KAP_ORTA = "KAP DİKKAT"
SKOR_CARPANI = {SEVIYE_AGIR: 0.0, SEVIYE_ORTA: 0.5, SEVIYE_BILGI: 1.0}

# kural -> (seviye, gecerlilik penceresi gun, kullaniciya gosterilen kisa ad)
KURALLAR = {
    "VBTS_BRUT_TAKAS":    (SEVIYE_AGIR, 30, "VBTS: brüt takas tedbiri"),
    "VBTS_TEK_FIYAT":     (SEVIYE_AGIR, 30, "VBTS: tek fiyat tedbiri"),
    "VBTS_ACIGA_SATIS":   (SEVIYE_ORTA, 30, "VBTS: açığa satış ve kredili işlem yasağı"),
    "SIRA_KAPALI":        (SEVIYE_AGIR, 60, "Pay işlem sırası kapatıldı"),
    "SPK_TEDBIR":         (SEVIYE_ORTA, 30, "SPK tedbir kararı"),
    "SIRKET_UYARI":       (SEVIYE_ORTA, 90, "Borsa İstanbul şirket uyarısı"),
    "YAKIN_IZLEME":       (SEVIYE_ORTA, 60, "Yakın İzleme Pazarı'na alındı"),
    "DENETIM_OLUMSUZ":    (SEVIYE_AGIR, 120, "Bağımsız denetim: olumsuz görüş / görüş bildirmeme"),
    "DENETIM_SARTLI":     (SEVIYE_ORTA, 120, "Bağımsız denetim: şartlı görüş"),
    "FIN_TABLO_GEC":      (SEVIYE_ORTA, 45, "Finansal rapor ek süre talebi (geç finansal tablo)"),
    "KONKORDATO_IFLAS":   (SEVIYE_AGIR, 90, "Konkordato / iflas"),
    "KONKORDATO_ANILDI":  (SEVIYE_ORTA, 60, "Özel durum açıklamasında konkordato/iflas geçiyor"),
    "FAALIYET_DURDURMA":  (SEVIYE_ORTA, 60, "Faaliyetlerin kısmen/tamamen durdurulması"),
    "TTK_376":            (SEVIYE_ORTA, 90, "TTK 376: sermaye kaybı / borca batıklık işlemi"),
    "SERMAYE_BEDELLI":    (SEVIYE_ORTA, 45, "Bedelli sermaye artırımı"),
    "SERMAYE_AZALTIM":    (SEVIYE_ORTA, 45, "Sermaye azaltımı"),
    "SERMAYE_BEDELSIZ":   (SEVIYE_BILGI, 45, "Bedelsiz sermaye artırımı"),
    "SERMAYE_DIGER":      (SEVIYE_BILGI, 45, "Sermaye artırımı/azaltımı bildirimi (türü belirlenemedi)"),
    "PAZAR_DEGISIKLIGI":  (SEVIYE_BILGI, 45, "Pay piyasası/pazar değişikliği (yön belirlenemedi)"),
    "GERI_ALIM":          (SEVIYE_BILGI, 14, "Pay geri alımı (genelde nötr/olumlu; risk değil)"),
    "GERI_ALINAN_SATIS":  (SEVIYE_BILGI, 30, "Geri alınan payların elden çıkarılması"),
    # v2.0.7.399: FON bildirimleri (KAP fonlar ucu). Anahtar "F:KOD" (hisse kodlariyla cakismasin).
    "FON_TASFIYE":        (SEVIYE_AGIR, 180, "Fon tasfiye kararı"),
    "FON_KARSILIK":       (SEVIYE_ORTA, 60, "Fon portföyündeki bir kıymet için karşılık ayrıldı (itfa/kupon ödenmedi)"),
    "FON_YAN_HESAP":      (SEVIYE_ORTA, 90, "Fon yan hesap (side pocket) oluşturdu"),
}

# v2.0.7.398 (Bahri'nin istegi, backlog 7): "pay geri alimi" varsayilan olarak BILGI'dir (skor/sinyal
# degismez; ENERY ornegi: bildirim olumlu/notr). Anahtar ACIKSA geri alim ORTA sayilir: skor x0,5 ve
# "KAP DIKKAT" etiketi (14 gun). Anahtar: ortam degiskeni KAP_GERI_ALIM_SKOR_DUSUR = 1/true/evet/acik
# (GitHub: Settings > Secrets and variables > Actions > Variables; kap_risk_tarama.yml okur). Degisiklik
# bir sonraki taramada (cron ~15 dk) uygulanir: riskler her seferinde arsivden sifirdan hesaplanir.
GERI_ALIM_ANAHTAR_ENV = "KAP_GERI_ALIM_SKOR_DUSUR"
_ACIK_DEGERLER = {"1", "true", "evet", "acik", "açık", "on", "yes"}


def geri_alim_skor_dusur_acik() -> bool:
    import os
    return str(os.environ.get(GERI_ALIM_ANAHTAR_ENV, "") or "").strip().lower() in _ACIK_DEGERLER


def kural_bilgisi(kural: str) -> tuple:
    """KURALLAR[kural] -> (seviye, pencere gun, ad). GERI_ALIM icin anahtar acikse seviye ORTA."""
    seviye, pencere, ad = KURALLAR[kural]
    if kural == "GERI_ALIM" and geri_alim_skor_dusur_acik():
        return (SEVIYE_ORTA, pencere, "Pay geri alımı (ayar gereği skor düşürüldü; bildirim kendisi risk değil)")
    return (seviye, pencere, ad)


K_VBTS = "BISTECH Pay Piyasası Alım Satım Sistemi Duyurusu"
K_SPK_TEDBIR = "Sermaye Piyasası Kurulu Tedbir Kararı"
K_SIRA = "Pay İşlem Sırası Kapatma / Açma"
K_UYARI = "Şirketin Uyarılması"
K_FIN_GEC = "Finansal Rapor Ek Süre Taleplerine İlişkin SPK Değerlendirmesi"
K_DENETIM_OLUMSUZ = "Bağımsız Denetim Raporunun Olumsuz Görüş İçermesi veya Görüş Bildirmekten Kaçınılması"
K_FAALIYET = "Faaliyetlerin Kısmen veya Tamamen Durdurulması ya da İmkansız Hale Gelmesi"
K_SERMAYE = ("Sermaye Artırımı - Azaltımı İşlemlerine İlişkin Bildirim", "Sermaye Artırımı veya Azaltımı Bildirimi")
K_GERI_ALIM = "Payların Geri Alınmasına İlişkin Bildirim"
K_GERI_SATIS = "Geri Alınan Payların Elden Çıkarılması"
K_TTK376 = "TTK'nın 376. Maddesi Kapsamında Yapılan İşlemler"
K_GENEL = "Özel Durum Açıklaması (Genel)"
K_PAZAR = ("Pazar Değişikliği", "Pazar Geçiş Başvurusu")

# Risk uretebilecek konular (tarayici sadece bunlari saklar; geri kalan ~%95 atilir)
ILGILI_KONULAR = {K_VBTS, K_SPK_TEDBIR, K_SIRA, K_UYARI, K_FIN_GEC, K_DENETIM_OLUMSUZ, K_FAALIYET,
                  K_GERI_ALIM, K_GERI_SATIS, K_TTK376, K_GENEL, *K_SERMAYE, *K_PAZAR}
_KONKORDATO = re.compile(r"konkordato|\b[iİ]flas", re.IGNORECASE)


def _kucuk(s) -> str:
    """Turkce'ye duyarli kucuk harf ('İ'.lower() birlesik noktali i uretir: 'İzleme' -> 'i̇zleme' -> aramalar bozulur)."""
    return str(s or "").replace("İ", "i").replace("I", "ı").lower()


def _vbts_ozeti_mi(ozet: str) -> bool:
    o = _kucuk(ozet)
    return "volatilite bazlı" in o or "vbts" in o or "brüt takas" in o or "tek fiyat" in o


# ───────────────────────────── FON bildirimleri (v2.0.7.399) ─────────────────────────────
FON_ONEK = "F:"
K_FON_TASFIYE = "Fon Tasfiye Duyurusu"
# Metni incelenecek fon bildirim konulari (geri kalan ~%99'u rutin rapor: gider, portfoy dagilimi, komisyon...)
FON_METIN_KONULARI = {"Genel Açıklama", "Özel Durum Açıklaması (Genel)", "Fonlara İlişkin Duyuru"}
_FON_ADAY_RX = re.compile(r"karşılık|yan hesap|side pocket|temerrüt|tasfiye", re.IGNORECASE)
_FON_KARSILIK_RX = re.compile(r"karşılık\s+ayr", re.IGNORECASE)
# "karsilik ayrilmasina gerek yoktur / ayrilmayacaktir" gibi OLUMSUZLAMA risk degildir
_FON_KARSILIK_YOK_RX = re.compile(
    r"karşılık\s+ayr[ıi]lma(?:y|dı|mı|ma[sz])|karşılık[^.]{0,60}(?:gerek|ihtiyaç)[^.]{0,20}(?:yok|bulunma|duyulma)",
    re.IGNORECASE)
_FON_YAN_HESAP_RX = re.compile(r"yan hesap|side pocket", re.IGNORECASE)
_FON_YAN_HESAP_OLUSTU_RX = re.compile(r"oluştur|oluştu", re.IGNORECASE)


def fon_anahtari(kod: str) -> str:
    return FON_ONEK + str(kod or "").strip().upper()


def _fon_mu(b: dict) -> bool:
    gk = b.get("gonderen_kodlar") or []
    return bool(gk) and all(str(k).startswith(FON_ONEK) for k in gk)


def _fon_ilgili_mi(b: dict) -> bool:
    konu = (b.get("konu") or "").strip()
    if konu == K_FON_TASFIYE:
        return True
    return konu in FON_METIN_KONULARI and bool(_FON_ADAY_RX.search(_kucuk_fon(b.get("ozet"))))


def _kucuk_fon(s) -> str:
    return _kucuk(s)


def _fon_siniflandir(b: dict) -> list:
    konu = (b.get("konu") or "").strip()
    ozet = re.sub(r"\s+", " ", str(b.get("ozet") or "")).strip()
    metin = b.get("metin") or ""
    gk = list(b.get("gonderen_kodlar") or [])
    out = []
    if konu == K_FON_TASFIYE:
        for k in dict.fromkeys(gk):
            out.append((k, "FON_TASFIYE", None, ozet or konu))
        return out
    if konu not in FON_METIN_KONULARI:
        return out
    tam = _kucuk(ozet + " " + metin)
    kural = None
    if _FON_YAN_HESAP_RX.search(tam) and _FON_YAN_HESAP_OLUSTU_RX.search(tam):
        kural = "FON_YAN_HESAP"
    elif _FON_KARSILIK_RX.search(tam) and not _FON_KARSILIK_YOK_RX.search(tam):
        kural = "FON_KARSILIK"
    if kural:
        for k in dict.fromkeys(gk):
            out.append((k, kural, None, ozet or konu))
    return out


def metin_gerekli_mi(b: dict) -> bool:
    """Bu bildirimin tam metni (ek istek) gerekli mi? SADECE VBTS (asama + bitis tarihi). Diger turler KAP'in
    kisa basligiyla (ozet) siniflanir: sermaye bildirimlerinin sayfa metni tutarsiz yapida (canli denendi) ve
    ozet turu zaten soyluyor ('Bedelsiz Sermaye Artirimi...', 'Tahsisli ...')."""
    if _fon_mu(b):
        return (b.get("konu") or "").strip() in FON_METIN_KONULARI and _fon_ilgili_mi(b)
    return (b.get("konu") or "") == K_VBTS and _vbts_ozeti_mi(b.get("ozet"))


def ilgili_mi(b: dict) -> bool:
    """Bildirim risk uretebilecek turde mi (saklanmaya deger)?"""
    if _fon_mu(b):
        return _fon_ilgili_mi(b)
    konu = b.get("konu") or ""
    if konu == K_VBTS:
        return _vbts_ozeti_mi(b.get("ozet"))
    if konu == K_GENEL:
        return bool(_KONKORDATO.search(b.get("ozet") or ""))
    if konu in ILGILI_KONULAR:
        return True
    return bool(_KONKORDATO.search(konu) or ("denetim" in _kucuk(konu) and "şartlı" in _kucuk(konu)))


# ───────────────────────────── metin yardimcilari ─────────────────────────────
def temiz_metin(ham, sinir: int = 3000) -> str:
    """HTML parcasini duz metne cevir (kesilmis son etiket dahil), bosluklari teke indir."""
    s = re.sub(r"<[^>]*>", " ", str(ham or ""))
    s = re.sub(r"<[^>]*$", " ", s)
    s = _html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:sinir]


def kodlari_ayir(v) -> list:
    """'AKBNK, GARAN' -> ['AKBNK','GARAN'] (None/bos -> [])."""
    if not v:
        return []
    return [k.strip().upper() for k in re.split(r"[,\s;]+", str(v)) if k.strip()]


def _tarihler(metin: str) -> list:
    out = []
    for g, a, y in re.findall(r"\b(\d{1,2})[/.](\d{1,2})[/.](20\d{2})\b", metin or ""):
        try:
            out.append(datetime.date(int(y), int(a), int(g)))
        except ValueError:
            pass
    return out


def _ozet(metin: str, n: int = 260) -> str:
    """Gosterim ozeti: KAP ust bilgisini (gonderim tarihi/tipi/ilgili sirketler) ayikla."""
    m = str(metin or "")
    if m.startswith("Gönderim Tarihi:"):
        m = re.sub(r"^.*?Bildirim Tipi:\w*\s*Yıl:\s*Periyot:\s*", "", m)
    m = re.sub(r"İlgili Şirketler \[[^\]]*\]\s*İlgili Fonlar \[[^\]]*\]\s*(Türkçe)?\s*", "", m)
    m = re.sub(r"^Özet Bilgi\s*", "", m).strip()
    return m[:n].strip()


# ───────────────────────────── siniflandirma ─────────────────────────────
def _sermaye_turu(ozet: str, metin: str = "") -> str:
    """Sermaye bildiriminin turu, KAP'in kisa basligindan (ozet): bedelsiz / bedelli(+tahsisli) / azaltim / diger.
    'Bedelsiz Pay Alma Hakki' bedelli DEGILDIR (canli veride yanlis eslesme bulundu)."""
    o = _kucuk(ozet)
    iptal = any(k in o for k in ("vazgeç", "vazgec", "kaldırıl", "kaldiril", "iptal", "reddedil"))
    if iptal and "bedelsiz" not in o:
        return "SERMAYE_DIGER"            # basvurudan vazgecme / islemden kaldirma: risk degil
    if "bedelsiz" in o:
        return "SERMAYE_BEDELSIZ"
    if "bedelli" in o or "rüçhan" in o or "tahsisli" in o:
        return "SERMAYE_BEDELLI"
    if "azaltım" in o or "azaltılması" in o or "azaltilmasi" in o or "azaltım" in _kucuk((metin or "")[:400]):
        if "geri alınan" in o or "itfa" in o:
            return "SERMAYE_DIGER"          # geri alinan payin iptali sermayeyi azaltir ama risk degil
        return "SERMAYE_AZALTIM"
    return "SERMAYE_DIGER"


def _vbts_satirlari(b: dict) -> list:
    """VBTS/brut takas/tek fiyat duyurusu -> [(ticker, kural, bitis_date|None, cumle)]."""
    metin = b.get("metin") or ""
    sonuc = []
    for cumle in re.split(r"(?<=[.!])\s+(?=[A-ZÇĞİÖŞÜ])", metin):
        kodlar = re.findall(r"(?<![A-Z0-9])([A-Z][A-Z0-9]{1,5})\.E(?![A-Z0-9])", cumle)
        if not kodlar:
            continue
        cl = _kucuk(cumle)
        if "brüt takas" in cl:
            kural = "VBTS_BRUT_TAKAS"
        elif "tek fiyat" in cl:
            kural = "VBTS_TEK_FIYAT"
        elif "açığa satış" in cl or "kredili" in cl:
            kural = "VBTS_ACIGA_SATIS"
        else:
            continue
        t = _tarihler(cumle)
        for k in dict.fromkeys(kodlar):
            sonuc.append((k, kural, max(t) if t else None, cumle))
    if not sonuc:
        # metin alinamadi/ayristirilamadi: guvenli taraf - ilgili kodlara ORTA (acigaSatis) seviyesinde uyar
        ozet = (b.get("ozet") or "")
        for k in b.get("ilgili_kodlar") or []:
            sonuc.append((k, "VBTS_ACIGA_SATIS", None, ozet))
    return sonuc


def _kendi_konkordato_mu(ozet: str) -> bool:
    """Ozel durum basligi sirketin KENDI konkordato/iflasini mi anlatiyor (AGIR), yoksa baska bir
    kurulusun (fon kullanicisi, istirak, musteri...) mi (ORTA)? Canli ornekler: 'Konkordato Talebi
    Kapsaminda Gecici Muhlet...' (sirketin kendisi) / 'Fon Kullanicisi X A.S. Hakkinda Konkordato...' (baskasi)."""
    o = _kucuk(ozet).strip()
    baskasi = ("fon kullanıcısı", "fon kullanicisi", "iştirak", "istirak", "bağlı ortaklık", "bagli ortaklik",
               "müşteri", "musteri", "borçlu", "borclu", "ihraççı", "ihracci", "grup şirket")
    if any(k in o for k in baskasi):
        return False
    # surmekte olan/biten planin rutin bildirimi (ornek: 'Konkordato 58. Taksit Odemesi', EMNIS) yeni bir
    # konkordato talebi DEGILDIR: ORTA (sirket hala zor durumda) ama AGIR (skor 0) degil
    if any(k in o for k in ("taksit", "sona er", "tamamlan", "kaldırıl", "kaldiril")):
        return False
    return bool(re.match(r"^(konkordato|iflas)", o) or "konkordato talebi" in o or "geçici mühlet" in o
                or "gecici muhlet" in o or "iflas" in o[:60])


def siniflandir(b: dict) -> list:
    """Tek bildirim -> [(ticker, kural, bitis_date|None, ozet_metin)]. Risk degilse []."""
    if _fon_mu(b):
        return _fon_siniflandir(b)
    konu = str(b.get("konu") or "").strip()
    ozet = str(b.get("ozet") or "").strip()
    ol = _kucuk(ozet)
    gk = list(b.get("gonderen_kodlar") or [])
    ik = list(b.get("ilgili_kodlar") or [])
    metin = b.get("metin") or ""
    hedef3 = ik or gk          # Borsa/KAP/SPK bildirimleri: konu olan sirketler
    out = []

    def ekle(kodlar, kural, bitis=None, aciklama=None):
        for k in dict.fromkeys(kodlar):
            out.append((k, kural, bitis, aciklama if aciklama is not None else (ozet or konu)))

    if konu == K_VBTS:
        if _vbts_ozeti_mi(ozet):
            for k, kural, bitis, cumle in _vbts_satirlari(b):
                out.append((k, kural, bitis, cumle))
    elif konu == K_SPK_TEDBIR:
        ekle(ik + gk, "SPK_TEDBIR")
    elif konu == K_SIRA:
        if "kapatıl" in ol or "kapatil" in ol:
            ekle(hedef3, "SIRA_KAPALI")
        elif "açıl" in ol or "acil" in ol:
            ekle(hedef3, "SIRA_ACIK")
    elif konu == K_UYARI:
        ekle(hedef3, "SIRKET_UYARI")
    elif konu == K_FIN_GEC:
        ekle(hedef3, "FIN_TABLO_GEC")
    elif konu in K_PAZAR:
        ekle(hedef3, "YAKIN_IZLEME" if "yakın izleme" in ol else "PAZAR_DEGISIKLIGI")
    elif konu == K_DENETIM_OLUMSUZ:
        ekle(gk, "DENETIM_OLUMSUZ")
    elif "denetim" in _kucuk(konu) and "şartlı" in _kucuk(konu):
        ekle(gk, "DENETIM_SARTLI")
    elif konu == K_FAALIYET:
        ekle(gk, "FAALIYET_DURDURMA")
    elif konu == K_TTK376:
        ekle(gk, "TTK_376")
    elif konu in K_SERMAYE:
        ekle(gk, _sermaye_turu(ozet, metin), None, ozet)
    elif konu == K_GERI_ALIM:
        ekle(gk, "GERI_ALIM")
    elif konu == K_GERI_SATIS:
        ekle(gk, "GERI_ALINAN_SATIS")
    elif _KONKORDATO.search(konu):
        ekle(gk or ik, "KONKORDATO_IFLAS")
    elif konu == K_GENEL and _KONKORDATO.search(ozet):
        ekle(gk, "KONKORDATO_IFLAS" if _kendi_konkordato_mu(ozet) else "KONKORDATO_ANILDI")
    return out


def riskleri_hesapla(bildirimler, bugun: datetime.date = None) -> dict:
    """Bildirim arsivinden her hissenin SU AN GECERLI risklerini hesaplar.
    Donus: {TICKER: [{kural, seviye, ad, baslik, tarih, bitis, ozet}, ...]} (siddete gore azalan).
    Her (hisse, kural) icin EN YENI bildirim kullanilir; islem sirasi acma/kapatma en son olaya gore."""
    bugun = bugun or datetime.date.today()
    liste = sorted([b for b in (bildirimler or []) if b.get("tarih")], key=lambda x: x["tarih"], reverse=True)

    en_yeni = {}   # (ticker, kural) -> (b, bitis, ozet)
    sira_son = {}  # ticker -> (kural, b, ozet)
    for b in liste:
        for ticker, kural, bitis, ozet in siniflandir(b):
            if kural in ("SIRA_KAPALI", "SIRA_ACIK"):
                sira_son.setdefault(ticker, (kural, b, ozet))   # liste yeniden eskiye: ilk = en son olay
                continue
            anahtar = (ticker, kural)
            if anahtar not in en_yeni:
                en_yeni[anahtar] = (b, bitis, ozet)
            elif bitis and (en_yeni[anahtar][1] is None or bitis > en_yeni[anahtar][1]):
                en_yeni[anahtar] = (b, bitis, ozet)
    for ticker, (kural, b, ozet) in sira_son.items():
        if kural == "SIRA_KAPALI":
            en_yeni[(ticker, "SIRA_KAPALI")] = (b, None, ozet)

    sonuc = {}
    for (ticker, kural), (b, bitis, ozet) in en_yeni.items():
        seviye, pencere, ad = kural_bilgisi(kural)
        t = b["tarih"]
        gonderim = t.date() if isinstance(t, datetime.datetime) else t
        son = bitis if bitis else gonderim + datetime.timedelta(days=pencere)
        if son < bugun:
            continue
        sonuc.setdefault(ticker, []).append({
            "kural": kural, "seviye": seviye, "ad": ad, "baslik": b.get("konu", ""),
            "tarih": t, "bitis": son, "ozet": _ozet(ozet)})
    for lst in sonuc.values():
        lst.sort(key=lambda r: (-_SIDDET[r["seviye"]], -r["tarih"].timestamp()))
    return sonuc


# ───────────────────────────── gosterim (DataFrame) ─────────────────────────────
def en_siddetli(riskler) -> str:
    """Risk listesinin en yuksek seviyesi ('' = risk yok)."""
    s = ""
    for r in riskler or []:
        v = r.get("seviye")
        if _SIDDET.get(v, 0) > _SIDDET.get(s, 0):
            s = v
    return s


def etiket(seviye: str) -> str:
    return {SEVIYE_AGIR: SINYAL_KAP_AGIR, SEVIYE_ORTA: SINYAL_KAP_ORTA}.get(seviye, "")


def _tarih_str(t) -> str:
    try:
        return t.strftime("%d.%m.%Y")
    except Exception:
        return str(t)[:10]


def aciklama_metni(riskler) -> str:
    """Detay seridi icin tek metin."""
    parcalar = []
    for r in riskler or []:
        parcalar.append(f"{r['ad']} ({_tarih_str(r['tarih'])} tarihli KAP bildirimi)")
    return "; ".join(parcalar)


def kap_isaretle(df, riskler_tickera):
    """df (Ticker, Kategori) icin {KAP_Seviye, KAP_Aciklama, KAP_Bilgi, KAP_Carpan} dondurur.
    riskler_tickera: {TICKER: [risk,...]}. SADECE Kategori == 'BIST' satirlari degerlendirilir.
    KAP_Seviye: AGIR/ORTA/'' (BILGI tek basina seviye vermez, sadece KAP_Bilgi'ye yazilir).
    v2.0.7.399: BIST hisseleri ticker ile, TEFAS fonlari "F:KOD" ile eslesir."""
    import pandas as pd
    cikti = pd.DataFrame({"KAP_Seviye": "", "KAP_Aciklama": "", "KAP_Bilgi": "", "KAP_Carpan": 1.0},
                         index=df.index)
    if df is None or df.empty or not riskler_tickera:
        return cikti
    kat = df["Kategori"].astype(str).str.upper()
    hedef = (kat == "BIST") | (kat == "TEFAS")
    tk = df["Ticker"].astype(str).str.upper()
    for idx in df.index[hedef]:
        # v2.0.7.399: TEFAS fonlari "F:KOD" anahtariyla aranir (hisse kodlariyla cakismaz)
        anahtar = (FON_ONEK + tk.at[idx]) if kat.at[idx] == "TEFAS" else tk.at[idx]
        riskler = riskler_tickera.get(anahtar)
        if not riskler:
            continue
        sev = en_siddetli(riskler)
        etiketli = [r for r in riskler if r["seviye"] in (SEVIYE_AGIR, SEVIYE_ORTA)]
        bilgi = [r for r in riskler if r["seviye"] == SEVIYE_BILGI]
        cikti.at[idx, "KAP_Bilgi"] = aciklama_metni(bilgi)
        if sev in (SEVIYE_AGIR, SEVIYE_ORTA):
            cikti.at[idx, "KAP_Seviye"] = sev
            cikti.at[idx, "KAP_Aciklama"] = aciklama_metni(etiketli)
            cikti.at[idx, "KAP_Carpan"] = SKOR_CARPANI[sev]
    return cikti
