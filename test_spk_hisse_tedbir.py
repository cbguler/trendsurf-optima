# -*- coding: utf-8 -*-
"""v2.0.7.437: SPK bultenlerinden hisse suc duyurusu / kisilere islem yasagi cikarma + ONAYSIZ otomatik uygulama.
Ag/veritabani yok: bulten metinleri GERCEK bultenlerden (2026/50, 2026/77, 2025/55, 2025/14, 2022/22, 2023/72) alinan
ifadelerle kurulmus, sahte db/liste/metin fonksiyonlari kullanilir."""
import os
import sys
from datetime import date, datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spk_bulten_izleme as S
import spk_hisse_tedbir as H

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


BIST = {"TRALT", "GOZDE", "ALKLC", "NTHOL", "EGEEN", "JANTS", "BASGZ", "FROTO", "GARAN", "EUKYO", "AVTUR", "KTLEV", "IEYHO"}
BUGUN = date(2026, 11, 12)
SABLON_YASAK = ("{ad} ({tk}) pay piyasasında gerçekleştirilen işlemlerde 6362 sayılı Sermaye Piyasası Kanunu'nun (SPKn) "
                "107/1 veya 104 üncü maddelerinde sayılan fiilin işlendiğine dair makul şüphe bulunması nedeniyle; "
                "6362 sayılı SPKn'nun 1 inci maddesi çerçevesinde yatırımcıların hak ve yararlarının korunmasını teminen, "
                "6362 sayılı SPKn'nun 128/1- (a) maddesine dayanarak yapay piyasa oluşturmaya yönelik işlemlerin "
                "engellenmesi amacıyla; 6362 sayılı SPKn'nun 101/1 maddesi ve V-101.1 sayılı Bilgi Suistimali ve Piyasa "
                "Dolandırıcılığı İncelemelerinde Uygulanacak Tedbirler Tebliği'nin 5/1 ve 6/1 maddeleri uyarınca; aşağıdaki "
                "tabloda bilgilerine yer verilen kişiler hakkında {bas} tarihli işlemlerden başlamak üzere borsalarda 6 ay "
                "süreyle geçici işlem yasağı uygulanmasına karar verilmiştir. T.C. MKK İlgili Tebliğ İşlem Yasağı Adı Soyadı "
                "Kimlik No Sicil No Maddesi Süresi Mehmet Emre CİHANGİR 20*******82 12534785 5/1-6/1 6 ay")
BASLIK = ("SERMAYE PİYASASI KURULU BÜLTENİ 2026/50 11/08/2026 A. SUÇ DUYURUSU, İDARİ PARA CEZASI İLE DİĞER YAPTIRIM VE "
          "TEDBİRLER 1. Diğer Yaptırım, Tedbir ve İşlem Yasakları ")


def _yasak_metin():
    return (BASLIK + "a) " + SABLON_YASAK.format(ad="Türk Altın İşletmeleri AŞ", tk="TRALT", bas="12.08.2026")
            + " b) " + SABLON_YASAK.format(ad="Gözde Girişim Sermayesi Yatırım Ortaklığı AŞ", tk="GOZDE", bas="12.08.2026")
            + " B. DİĞER ÖZEL DURUMLAR")


SUC_METIN = ("SERMAYE PİYASASI KURULU BÜLTENİ 2026/77 27/10/2026 A. SUÇ DUYURUSU, İDARİ PARA CEZASI İLE DİĞER YAPTIRIM VE "
             "TEDBİRLER 1. Suç Duyuruları a) Altınkılıç Gıda ve Süt Sanayi Ticaret AŞ (ALKLC) hakkında yapılan inceleme "
             "sonucunda, aşağıdaki tabloda yer alan suç duyurularının yapılmasına karar verilmiştir. (Bknz. 2. Diğer Yaptırım) "
             "Suç Duyurusuna Neden Olan Eylem 107 nci maddesinin birinci fıkrası Bülent UYGUN 34*******58 12343589 "
             "b) Net Holding AŞ (NTHOL) pay piyasasında gerçekleştirilen işlemlerde sorumluluğu bulunan aşağıdaki tabloda yer "
             "alan şahıslar hakkında 6362 sayılı Sermaye Piyasası Kanunu’nun (SPKn) 107 nci maddesinin ikinci fıkrası "
             "kapsamında işlem yapılmak üzere, 6362 sayılı SPKn’nun 115 inci maddesi uyarınca Cumhuriyet Başsavcılığı’na "
             "suç duyurusunda bulunulmasına karar verilmiştir. Ad Soyad Ali VELİ")

IPC_METIN = ("2. İdari Para Cezaları a) Ford Otomotiv Sanayi AŞ (FROTO) payına dayalı 30.09.2022 vade tarihli FRSPK satım "
             "varantı piyasasında 01.08.2022-15.08.2022 döneminde gerçekleştirilen işlemler ile ilgili olarak yapılan "
             "inceleme sonucunda, aşağıdaki tabloda yer alan idari para cezalarının uygulanmasına karar verilmiştir. "
             "İPC Uygulanan Eylemin Aykırılık Teşkil Verilen Düzenleme Zafer ŞAKAKLI 284.801,40 "
             "b) Türkiye Garanti Bankası AŞ (GARAN) pay piyasasında yapılan inceleme sonucunda, 6362 sayılı SPKn "
             "107 nci maddesinin birinci fıkrası uyarınca suç duyurusunda bulunulmasına karar verilmiştir.")


def kay(metin, no="2026/50", t=date(2026, 8, 11)):
    return H.kayitlari_cikar(metin, BIST, no, t, "http://x")


def test_yasak_cikarma_ve_tarih():
    k = [x for x in kay(_yasak_metin()) if x["tur"] == "YASAK"]
    ok({x["ticker"] for x in k} == {"TRALT", "GOZDE"}, "iki giris, iki hisse (harfli madde siniri)")
    ok(all(x["baslangic"] == date(2026, 8, 12) for x in k), "baslangic tarihi bultenden okunur")
    ok(all(x["bitis"] == date(2027, 2, 12) for x in k), "bitis = baslangic + 6 ay")
    ok(not any(x["tahmini"] for x in k), "tarih yazili -> tahmini degil")
    ok(not [x for x in kay(_yasak_metin()) if x["tur"] == "SUC"], "yasak girisi suc duyurusu sayilmaz")


def test_yasak_tarihsiz_tahmini():
    m = _yasak_metin().replace("12.08.2026 tarihli işlemlerden başlamak üzere ", "")
    k = [x for x in kay(m) if x["tur"] == "YASAK"]
    ok(all(x["tahmini"] and x["bitis"] == date(2027, 2, 12) for x in k), "tarih yoksa bulten ertesi gunu + 6 ay, TAHMINI isareti")


def test_suc_cikarma_ve_madde():
    k = [x for x in kay(SUC_METIN, "2026/77", date(2026, 10, 27)) if x["tur"] == "SUC"]
    ok({x["ticker"] for x in k} == {"ALKLC", "NTHOL"}, "iki suc duyurusu girisi (eski yazim dahil)")
    ok(all(x["bitis"] is None for x in k), "suc duyurusu kalici (bitis yok)")
    md = {x["ticker"]: x["madde"] for x in k}
    ok(md["NTHOL"] == "107/2", "madde: ikinci fikra -> 107/2")


def test_ipc_ve_varant_alinmaz():
    k = kay(IPC_METIN, "2023/13", date(2023, 3, 2))
    ok("FROTO" not in {x["ticker"] for x in k}, "varant IPC maddesindeki hisse (FROTO) alinmaz")
    ok({x["ticker"] for x in k} == {"GARAN"}, "ayni metinde sonraki GERCEK suc duyurusu yine alinir (sinir calisir)")


def test_evren_disi_ticker_alinmaz():
    m = SUC_METIN.replace("(ALKLC)", "(ZZZZZ)")
    ok("ZZZZZ" not in {x["ticker"] for x in kay(m)}, "evrende olmayan kod alinmaz")


def test_cok_sirketli_yasak():
    m = (BASLIK + "a) Ege Endüstri ve Ticaret AŞ (EGEEN) ile Jantsa Jant Sanayi ve Ticaret AŞ (JANTS) pay piyasalarında "
         "gerçekleştirilen işlemlerde ve sosyal medyada yer alan paylaşımlarda 6362 sayılı SPKn'nun 107/2 maddesinde sayılan "
         "fiilin işlendiğine dair makul şüphe bulunması nedeniyle; V-101.1 Tebliği'nin 5/1 ve 6/1 maddeleri uyarınca; "
         "aşağıdaki kişiler hakkında 22.12.2023 tarihli işlemlerden başlamak üzere borsalarda 6 ay süreyle geçici işlem "
         "yasağı uygulanmasına karar verilmiştir.")
    ok({x["ticker"] for x in kay(m, "2023/80", date(2023, 12, 21)) if x["tur"] == "YASAK"} == {"EGEEN", "JANTS"},
       "bir giriste iki sirket: ikisi de yakalanir")


def test_uzatma_tarihli_ve_tarihsiz():
    tarihli = ("b) Başkent Doğalgaz Dağıtım GYO AŞ (BASGZ) pay piyasasında 26.10.2021-05.11.2021 döneminde gerçekleştirilen "
               "işlemler nedeniyle, V-101.1 Tebliği'nin 5/1 ve 6/1 maddeleri kapsamında, aşağıdaki tabloda yer alan kişiler "
               "hakkında uygulanmakta olan geçici işlem yasağının, 6/1 maddesi kapsamında, yasak süresinin dolacağı tarihten "
               "(08.05.2022 gün sonu) başlamak üzere 6 ay süreyle uzatılmasına karar verilmiştir. Kenan YÜKSEK 6 ay")
    k = [x for x in kay(tarihli, "2022/22", date(2022, 4, 28)) if x["tur"] == "YASAK"]
    ok(len(k) == 1 and k[0]["ticker"] == "BASGZ" and k[0]["bitis"] == date(2022, 11, 8), "tarihli uzatma: 08.05.2022 + 6 ay")
    tarihsiz = tarihli.replace("(08.05.2022 gün sonu) ", "")
    k2 = [x for x in kay(tarihsiz, "2026/80", date(2026, 11, 20)) if x["tur"] == "YASAK"]
    ok(len(k2) == 1 and k2[0]["bitis"] is None and k2[0]["uzatma"], "tarihsiz uzatma bitisi plan asamasinda cozulur")
    ilk = {"ticker": "BASGZ", "tur": "YASAK", "bulten": "2026/60", "bulten_tarihi": date(2026, 9, 1), "url": "",
           "madde": "", "baslangic": date(2026, 9, 2), "bitis": date(2027, 3, 2), "tahmini": False, "alinti": ""}
    p = H.plan_olustur([ilk] + k2, {}, BUGUN, set())
    e = [x for x in p if x["ticker"] == "BASGZ"][0]
    ok(e["islem"] == "YAZ" and e["bitis"] == date(2027, 9, 2), "tarihsiz uzatma = onceki yasak bitisi + 6 ay")
    p2 = H.plan_olustur(k2, {"BASGZ": {"aktif": True, "tedbir_turu": "ISLEM_YASAGI_SUPHESI",
                                      "bitis_tarihi": date(2026, 12, 1), "kaldirilma_tarihi": None}}, BUGUN, set())
    ok(p2[0]["bitis"] == date(2027, 6, 1), "canli akis: uzatma, aktif kuralin bitisine eklenir")


def test_ay_ekle_ay_sonu():
    ok(H.ay_ekle(date(2026, 8, 31), 6) == date(2027, 2, 28), "31 Agustos + 6 ay = 28 Subat")
    ok(H.ay_ekle(date(2026, 8, 12), 6) == date(2027, 2, 12), "12 Agustos + 6 ay")
    ok(H.ay_ekle(date(2026, 11, 30), 3) == date(2027, 2, 28), "yil asimi")


def _kayit(tk, tur, no="2026/50", t=date(2026, 8, 11), bitis=None):
    return {"ticker": tk, "tur": tur, "bulten": no, "bulten_tarihi": t, "url": "", "madde": "", "baslangic": None,
            "bitis": bitis, "tahmini": False, "alinti": "a"}


def test_plan_yeni_ve_sureli():
    p = H.plan_olustur([_kayit("ALKLC", "SUC"), _kayit("TRALT", "YASAK", bitis=date(2027, 2, 12)),
                        _kayit("GOZDE", "YASAK", bitis=date(2026, 11, 12))], {}, BUGUN, set())
    d = {e["ticker"]: e for e in p}
    ok(d["ALKLC"]["islem"] == "YAZ" and d["ALKLC"]["bitis"] is None and d["ALKLC"]["tedbir_turu"] == "MANIPULASYON_SUPHESI",
       "suc: kalici, MANIPULASYON_SUPHESI")
    ok(d["TRALT"]["islem"] == "YAZ" and d["TRALT"]["tedbir_turu"] == "ISLEM_YASAGI_SUPHESI", "aktif yasak yazilir")
    ok(d["GOZDE"]["islem"] == "ATLA" and "dolmus" in d["GOZDE"]["neden"], "bitis bugun veya gecmis -> yazilmaz")


def test_plan_suc_yasagi_ezer_yasak_suci_ezmez():
    p = H.plan_olustur([_kayit("IEYHO", "YASAK", bitis=date(2026, 12, 5)), _kayit("IEYHO", "SUC")], {}, BUGUN, set())
    d = {e["tur"]: e for e in p}
    ok(d["SUC"]["islem"] == "YAZ" and d["YASAK"]["islem"] == "ATLA", "ayni planda suc yazilir, yasak kalici kurali EZMEZ")
    mevcut = {"IEYHO": {"aktif": True, "tedbir_turu": "ISLEM_YASAGI_SUPHESI", "bitis_tarihi": date(2026, 12, 5),
                        "kaldirilma_tarihi": None}}
    p2 = H.plan_olustur([_kayit("IEYHO", "SUC")], mevcut, BUGUN, set())
    ok(p2[0]["islem"] == "YAZ", "mevcut gecici yasak kurali, suc ile kalici kurala yukseltilir")


def test_plan_mevcut_kalici_kural_atlanir():
    mevcut = {"KTLEV": {"aktif": True, "tedbir_turu": "MANIPULASYON_SUPHESI", "bitis_tarihi": None, "kaldirilma_tarihi": None}}
    p = H.plan_olustur([_kayit("KTLEV", "SUC"), _kayit("KTLEV", "YASAK", bitis=date(2027, 1, 1))], mevcut, BUGUN, set())
    ok(all(e["islem"] == "ATLA" for e in p), "tohumlanmis/onayli kalici kural varsa ikisi de atlanir")
    uzun = {"TRALT": {"aktif": True, "tedbir_turu": "ISLEM_YASAGI_SUPHESI", "bitis_tarihi": date(2027, 3, 1), "kaldirilma_tarihi": None}}
    ok(H.plan_olustur([_kayit("TRALT", "YASAK", bitis=date(2027, 2, 12))], uzun, BUGUN, set())[0]["islem"] == "ATLA",
       "ayni veya daha uzun yasak varsa tekrar yazilmaz (idempotent)")
    kisa = {"TRALT": {"aktif": True, "tedbir_turu": "ISLEM_YASAGI_SUPHESI", "bitis_tarihi": date(2027, 1, 1), "kaldirilma_tarihi": None}}
    ok(H.plan_olustur([_kayit("TRALT", "YASAK", bitis=date(2027, 2, 12))], kisa, BUGUN, set())[0]["islem"] == "YAZ",
       "daha uzun yeni yasak mevcut gecici kurali uzatir")


def test_plan_elle_kaldirilan_kural_saygi():
    kald = {"ALKLC": {"aktif": False, "tedbir_turu": "MANIPULASYON_SUPHESI", "bitis_tarihi": None,
                      "kaldirilma_tarihi": datetime(2026, 11, 1, 10, 0)}}
    eski = H.plan_olustur([_kayit("ALKLC", "SUC", t=date(2026, 10, 22))], kald, BUGUN, set())[0]
    ok(eski["islem"] == "ATLA" and "kaldirilmis" in eski["neden"], "kaldirmadan ONCEKI bultenle yeniden acilmaz")
    yeni = H.plan_olustur([_kayit("ALKLC", "SUC", t=date(2026, 11, 6))], kald, BUGUN, set())[0]
    ok(yeni["islem"] == "YAZ", "kaldirmadan SONRAKI yeni bulten kurali yeniden acar")


def test_plan_baska_kategori_cakismasi():
    p = H.plan_olustur([_kayit("ABC", "SUC")], {}, BUGUN, {"ABC"})
    ok(p[0]["islem"] == "ATLA" and "baska kategori" in p[0]["neden"], "ayni kod baska kategoride varsa yazilmaz")


def test_evren_bist():
    df = pd.DataFrame({"Ticker": ["AAAA", "BBB", "BBB", "CCCC"], "Kategori": ["BIST", "BIST", "TEFAS", "TEFAS"]})
    bist, baska = H.evren_bist(df)
    ok(bist == {"AAAA", "BBB"} and baska == {"BBB"}, "evren_bist: BIST kumesi ve kategori cakismasi")


# ── uygulayici (spk_bulten_izleme) ────────────────────────────────────────────────────────
class SahteDB:
    def __init__(self, kurallar=None):
        self.kurallar = kurallar if kurallar is not None else {}
        self.yazilan = []
        self.islenmis = set()
        self.tespit = []

    def piyasa_tedbir_ticker_kurallari(self):
        return self.kurallar

    def piyasa_tedbir_otomatik_yaz(self, deger, kategori, tedbir_turu, kaynak_turu, kaynak_referans, kaynak_url,
                                   kaynak_tarihi, gerekce, ozet, kaynak_aciklama, bitis_tarihi=None):
        self.yazilan.append((deger, kategori, tedbir_turu, kaynak_turu, kaynak_referans, bitis_tarihi, kaynak_aciklama, ozet))
        self.kurallar[deger] = {"aktif": True, "tedbir_turu": tedbir_turu, "bitis_tarihi": bitis_tarihi, "kaldirilma_tarihi": None}
        return True

    def get_aktif_piyasa_tedbirleri(self):
        return [{"eslesme_turu": "TICKER", "deger": d, "kategori": "BIST", "tedbir_turu": v["tedbir_turu"],
                 "kaynak_aciklama": ""} for d, v in self.kurallar.items() if v["aktif"]]

    def spk_islenmis_bultenler(self):
        return set(self.islenmis)

    def spk_bulten_toplu_isaretle(self, nolar):
        self.islenmis |= set(nolar)
        return len(nolar)

    def spk_bulten_islendi_isaretle(self, no):
        self.islenmis.add(no)

    def piyasa_tedbir_tespit_durumlari(self, *a):
        return []

    def piyasa_tedbir_tespit_ekle(self, *a, **k):
        self.tespit.append(a)
        return True


DF = pd.DataFrame({"Ticker": sorted(BIST), "Kategori": "BIST", "Ad": sorted(BIST)})


def test_uygula_yazar_kuru_yazmaz():
    k = [x for x in kay(_yasak_metin()) if x["tur"] == "YASAK"] + [x for x in kay(SUC_METIN, "2026/77", date(2026, 10, 27))]
    db = SahteDB()
    o = S.hisse_kayitlari_uygula(k, DF, db, BUGUN, H.KAYNAK_GECMIS, kuru=True)
    ok(o["yazilan"] == 4 and not db.yazilan, "kuru: sayar ama VERITABANINA YAZMAZ")
    o = S.hisse_kayitlari_uygula(k, DF, db, BUGUN, H.KAYNAK_GECMIS)
    ok(o["yazilan"] == 4 and len(db.yazilan) == 4, "gercek: 2 yasak + 2 suc yazildi")
    yz = {y[0]: y for y in db.yazilan}
    ok(yz["TRALT"][2] == "ISLEM_YASAGI_SUPHESI" and yz["TRALT"][5] == date(2027, 2, 12), "yasak: tur ve bitis tarihi yazildi")
    ok(yz["ALKLC"][2] == "MANIPULASYON_SUPHESI" and yz["ALKLC"][5] is None, "suc: kalici")
    ok(yz["TRALT"][3] == "SPK_BULTEN_GECMIS", "kaynak_turu gecmis (e-posta yagdirmaz)")
    ok("Bülteni 2026/50" in yz["TRALT"][6] and "12.02.2027" in yz["TRALT"][6], "kullaniciya giden kaynak metni okunur")
    db.yazilan.clear()
    o = S.hisse_kayitlari_uygula(k, DF, db, BUGUN, H.KAYNAK_GECMIS)
    ok(o["yazilan"] == 0 and o["atlanan"] == 4 and not db.yazilan, "ikinci calisma IDEMPOTENT: hicbir sey yazilmaz")


def test_uygula_kurallar_okunamazsa_yazmaz():
    db = SahteDB(kurallar=None)
    db.kurallar = None
    o = S.hisse_kayitlari_uygula(kay(SUC_METIN), DF, db, BUGUN, H.KAYNAK_CANLI)
    ok(o["hata"] == 1 and not db.yazilan, "mevcut kurallar okunamazsa HICBIR sey yazilmaz")


def _liste_fn(yil):
    return {2026: [{"no": "2026/50", "tarih": date(2026, 8, 11), "url": "u50"},
                   {"no": "2026/77", "tarih": date(2026, 10, 27), "url": "u77"}]}.get(yil, [])


def _metin_fn(url):
    return {"u50": _yasak_metin(), "u77": SUC_METIN}.get(url)


def test_gecmis_dolgu_tamamlandi_isareti():
    db = SahteDB()
    o = S.gecmis_dolgu(db, DF, BUGUN, liste_fn=_liste_fn, metin_fn=_metin_fn, ilk_yil=2025, is_parcacigi=2)
    ok(o["tamam"] and S.GECMIS_ISARET in db.islenmis, "tum bultenler okundu -> tamamlandi isareti konur")
    ok({y[0] for y in db.yazilan} == {"TRALT", "GOZDE", "ALKLC", "NTHOL"}, "gecmis dolgu dort kurali yazdi")
    db2 = SahteDB()
    o2 = S.gecmis_dolgu(db2, DF, BUGUN, liste_fn=_liste_fn, metin_fn=lambda u: None if u == "u77" else _metin_fn(u),
                        ilk_yil=2025, is_parcacigi=2)
    ok(not o2["tamam"] and S.GECMIS_ISARET not in db2.islenmis, "okunamayan bulten varsa isaret KONMAZ (tekrar denenir)")
    ok({y[0] for y in db2.yazilan} == {"TRALT", "GOZDE"}, "okunanlar yine de uygulanir")
    db3 = SahteDB()
    S.gecmis_dolgu(db3, DF, BUGUN, liste_fn=_liste_fn, metin_fn=_metin_fn, ilk_yil=2025, kuru=True)
    ok(not db3.yazilan and S.GECMIS_ISARET not in db3.islenmis, "kuru: ne kural ne isaret yazar")


def test_calistir_ilk_calismada_gecmis_dolgu_sonra_degil():
    db = SahteDB()
    kw = dict(bugun=BUGUN, liste_fn=_liste_fn, metin_fn=_metin_fn, ai_fn=None, df_uni=DF, db_mod=db, maks_bulten=8)
    orijinal = S.bulten_listesi_tum_yil
    S.bulten_listesi_tum_yil = _liste_fn
    try:
        S.calistir(**kw)
        ok(S.GECMIS_ISARET in db.islenmis and len(db.yazilan) == 4, "ilk calisma: gecmis dolgu yapildi ve isaretlendi")
        n = len(db.yazilan)
        S.calistir(**kw)
        ok(len(db.yazilan) == n, "ikinci calisma: dolgu tekrarlanmaz, yeni yazim yok")
    finally:
        S.bulten_listesi_tum_yil = orijinal


def test_canli_akis_yeni_bulten_otomatik():
    db = SahteDB()
    db.islenmis.add(S.GECMIS_ISARET)
    db.kurallar = {}
    liste = [{"no": "2026/80", "tarih": date(2026, 11, 11), "url": "u50"}]
    S.calistir(bugun=BUGUN, liste_fn=lambda y: liste, metin_fn=_metin_fn, ai_fn=None, df_uni=DF, db_mod=db)
    ok({y[0] for y in db.yazilan} == {"TRALT", "GOZDE"}, "canli: 14 gun icindeki yeni bulten, onay penceresine dusmeden uygulanir")
    ok(all(y[3] == "SPK_BULTEN_OTO" for y in db.yazilan), "canli kaynak_turu SPK_BULTEN_OTO (bildirim e-postasi gider)")
    ok(not [t for t in db.tespit if t[5] in ("TRALT", "GOZDE")], "ayni hisseler ayrica bekleyen aday olarak YAZILMAZ")


def test_anahtar_kapali_eski_davranis():
    eski = S.HISSE_OTOMATIK
    S.HISSE_OTOMATIK = False
    try:
        db = SahteDB()
        db.kurallar = {}
        S.calistir(bugun=BUGUN, liste_fn=lambda y: [{"no": "2026/77", "tarih": date(2026, 11, 10), "url": "u77"}],
                   metin_fn=_metin_fn, ai_fn=None, df_uni=DF, db_mod=db)
        ok(not db.yazilan and S.GECMIS_ISARET not in db.islenmis, "SPK_HISSE_OTOMATIK=0: otomatik kural ve gecmis dolgu YOK")
    finally:
        S.HISSE_OTOMATIK = eski


# ── sayfalama ─────────────────────────────────────────────────────────────────────────────
class _Y:
    def __init__(self, html):
        self.text = html

    def raise_for_status(self):
        pass


def _html(nolar):
    return "<html><body>" + "".join(
        f'<a href="/data/x/{n.replace("/", "-")}.pdf">Bülten No : {n} Yayımlanma : 5 Ocak 2026</a>' for n in nolar) + "</body></html>"


def test_sayfalama_ve_url():
    cagrilar = []
    sayfalar = {1: ["2026/3", "2026/2"], 2: ["2026/1"], 3: []}

    def get(url, headers=None, timeout=None):
        cagrilar.append(url)
        s = int(url.split("?s=")[1]) if "?s=" in url else 1
        return _Y(_html(sayfalar.get(s, [])))
    l1 = S.bulten_listesi_cek(2026, get=get)
    ok([b["no"] for b in l1] == ["2026/3", "2026/2"] and "?s=" not in cagrilar[0], "1. sayfa: eski davranis (parametresiz URL)")
    tum = S.bulten_listesi_tum_yil(2026, get=get)
    ok([b["no"] for b in tum] == ["2026/3", "2026/2", "2026/1"], "tum yil: sayfalar birlestirilir")
    ok(any(u.endswith("?s=2") for u in cagrilar) and any(u.endswith("?s=3") for u in cagrilar), "?s=N ile sayfa istenir")
    ok("gecmis-yillara-ait-bultenler/2022-yili" in S._liste_url(2022), "2024 ve oncesi 'gecmis yillar' adresi")
    ok(S._liste_url(2026).endswith("/spk-bultenleri/2026-yili-spk-bultenleri"), "bu yil ana adres")


# ── kaynak kodu kontrolleri (db / e-posta / is akisi) ─────────────────────────────────────
def test_db_ve_diger_dosyalar():
    db = open("db.py", encoding="utf-8").read()
    ok("ADD COLUMN IF NOT EXISTS bitis_tarihi DATE" in db, "bitis_tarihi kolonu eklenir")
    ok("(bitis_tarihi IS NULL OR bitis_tarihi > CURRENT_DATE)" in db, "suresi dolan gecici kural aktif listeden duser")
    ok("bitis_tarihi=NULL" in db, "onay penceresinden onaylanan kural kalici olur (eski bitis temizlenir)")
    ok("'otomatik'" in db and "def piyasa_tedbir_otomatik_yaz" in db, "otomatik yazim denetim izi ('otomatik')")
    ok("ISLEM_YASAGI_SUPHESI" in open("piyasa_tedbir.py", encoding="utf-8").read(), "yeni tedbir turu etiketi")
    ok("SPK_BULTEN_GECMIS" in open("bildirim_eposta.py", encoding="utf-8").read(), "gecmis kurallar e-posta yagdirmaz")
    w = open(".github/workflows/spk_bulten_izleme.yml", encoding="utf-8").read()
    ok("gecmis:" in w and "--gecmis" in w, "workflow elle 'gecmis' tetikleme girdisi")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"test_spk_hisse_tedbir: {_n['ok']}/{_n['ok']} OK")
