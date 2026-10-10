# -*- coding: utf-8 -*-
"""v2.0.7.399: FON tarafinda KAP otomasyonu (kap_risk fon kurallari, tarama normallestirme, TEFAS isaretleme,
uyari katmani). Metinler CANLI KAP fon bildirimlerinden (9-10 Ekim 2026). Ag/veritabani KULLANILMAZ."""
import datetime as dt
import sys

import pandas as pd

import kap_risk as K
import kap_risk_tarama as T
import uyari_katmani as U

BUGUN = dt.date(2026, 10, 10)
_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def fb(konu, ozet="", metin="", kod="BTE", tarih=dt.datetime(2026, 10, 7, 12, 0), i=1):
    return {"id": i, "tarih": tarih, "gonderen": "X PORTFOY", "konu": konu, "ozet": ozet,
            "gonderen_kodlar": [K.fon_anahtari(kod)], "ilgili_kodlar": [], "metin": metin}


KARSILIK = ("Adil Varlık Kiralama A.Ş. (İhraççı) tarafından ihraç edilen TRFADLVE2612 ISIN kodlu kıymete ait 06.10.2026 "
            "tarihli itfa ve kupon ödemeleri işleminin, ödeme tutarının aktarılmaması nedeniyle gerçekleştirilemediği, "
            "İhraççı tarafından aynı tarihli Kamuyu Aydınlatma Platformu'nda duyurusu ile kamuya açıklanmıştır. Fon "
            "portföyünde bulunan aşağıdaki kıymetler ile ilgili olarak ... %100 oranında karşılık ayrılmasına karar verilmiştir.")
YAN_HESAP = ("Fon portföyünde bulunan, Türk İlaç ve Serum Sanayi Anonim Şirketi tarafından ihraç edilen TRFTRLC92612 ISIN "
             "kodlu özel sektör borçlanma aracına ilişkin olarak, 16.07.2026 tarihinde gerçekleşmesi gereken itfa ve kupon "
             "ödemelerinin yerine getirilememesi nedeniyle ... %100 oranında karşılık ayrıldığı hususu 17.07.2026 tarihinde "
             "kamuya açıklanmıştır. ... fon nezdinde yan hesap (side pocket) oluşturulmasına karar verilmiştir.")
TASFIYE = ("09.10.2026 Tarih 45259 Sayılı Yönetm Kurulu Kararı ile; Kurucusu ve yöneticisi olduğumuz ... Gayrimenkul Yatırım "
           "Fonu (Fon), ... Fon'un Kurulca belirlenen asgari değere ulaşamaması sebebiyle tasfiye edilecek olup;")
EK_ONLY = "Tasarruf Sahiplerine Duyuru metni bildirim Ek'inde sunulmuştur."
UCRET = ("TASARRUF SAHİPLERİNE DUYURU ... yönetim ücreti değişikliğinin iptali ... yönetim ücretinde herhangi bir değişiklik "
         "yapılmayacak olup mevcut yönetim ücreti uygulanmaya devam edilecektir.")
KENTSEL = ("Fon portföyünde yer alan taşınmazın ... riskli yapı olarak tespit edildiği ve mevcut yapının yıkımına karar "
           "verildiği bildirilmiştir. ... kentsel dönüşüm sürecine dahil edilmesine ... karar verilmiştir.")


def test_siniflandirma_gercek_metinler():
    r = K.riskleri_hesapla([fb("Genel Açıklama", "Karşılık Ayrılması Hk.", KARSILIK, "BTE", i=1)], BUGUN)
    ok(set(r) == {"F:BTE"} and r["F:BTE"][0]["kural"] == "FON_KARSILIK" and r["F:BTE"][0]["seviye"] == K.SEVIYE_ORTA,
       "karsilik ayrilmasi (temerrut) = ORTA")
    r = K.riskleri_hesapla([fb("Genel Açıklama", "Yan Hesap Oluşturulmasına İlişkin Açıklama", YAN_HESAP, "MP4", i=2)], BUGUN)
    ok(r["F:MP4"][0]["kural"] == "FON_YAN_HESAP" and r["F:MP4"][0]["seviye"] == K.SEVIYE_ORTA,
       "yan hesap (karsilik de gecse) yan hesap olarak siniflanir")
    r = K.riskleri_hesapla([fb("Fon Tasfiye Duyurusu", "IY2- İkinci GYF Tasfiye Duyurusu", TASFIYE, "IY2", i=3)], BUGUN)
    ok(r["F:IY2"][0]["kural"] == "FON_TASFIYE" and r["F:IY2"][0]["seviye"] == K.SEVIYE_AGIR, "tasfiye = AGIR")
    ok(K.etiket(K.SEVIYE_AGIR) == "KAP UYARISI" and K.etiket(K.SEVIYE_ORTA) == "KAP DİKKAT", "etiketler hisselerle ayni")


def test_rutin_ve_belirsiz_bildirimler_risk_degil():
    for konu, ozet, metin in (("Genel Açıklama", "Tasarruf Sahiplerine Duyuru", EK_ONLY),
                              ("Genel Açıklama", "Tasarruf Sahiplerine Duyuru", UCRET),
                              ("Özel Durum Açıklaması (Genel)", "Kentsel Dönüşüm Kararı Hk.", KENTSEL),
                              ("Genel Açıklama", "Fonun 30.09.2026 Tarihli Pay Fiyatı Açıklaması", ""),
                              ("Fon Gider Bilgileri", "Fon Gider Bilgileri", ""),
                              ("Portföy Dağılım Raporu", "Portföy Dağılım Raporu", ""),
                              ("Kredi Kullanımı", "Kredi Kullanımı", "")):
        b = fb(konu, ozet, metin, "ZZL")
        ok(K.riskleri_hesapla([b], BUGUN) == {}, f"risk degil: {konu} / {ozet[:30]}")
        ok(not K.ilgili_mi(b) or K.metin_gerekli_mi(b) or konu == K.K_FON_TASFIYE, f"saklama karari tutarli: {ozet[:30]}")


def test_karsilik_olumsuzlamasi_risk_degil():
    for metin in ("Fon portföyündeki kıymet için karşılık ayrılmasına gerek bulunmamaktadır.",
                  "Söz konusu kıymet için herhangi bir karşılık ayrılmayacaktır.",
                  "Karşılık ayrılmamıştır; ödeme gerçekleşmiştir."):
        ok(K.riskleri_hesapla([fb("Genel Açıklama", "Karşılık Ayrılması Hk.", metin, "XYZ")], BUGUN) == {},
           f"olumsuzlama risk degil: {metin[:40]}")
    ok("F:BTE" in K.riskleri_hesapla([fb("Genel Açıklama", "Karşılık Ayrılması Hk.", KARSILIK, "BTE")], BUGUN),
       "gercek karsilik metni hala yakalanir")


def test_ilgili_mi_ve_metin_gerekli_mi():
    ok(K.ilgili_mi(fb("Genel Açıklama", "Karşılık Ayrılması Hk.")) and K.metin_gerekli_mi(fb("Genel Açıklama", "Karşılık Ayrılması Hk.")),
       "karsilik basligi saklanir ve metni cekilir")
    ok(K.ilgili_mi(fb("Genel Açıklama", "Yan Hesap Oluşturulmasına İlişkin Açıklama")), "yan hesap saklanir")
    t = fb("Fon Tasfiye Duyurusu", "X Tasfiye Duyurusu")
    ok(K.ilgili_mi(t) and not K.metin_gerekli_mi(t), "tasfiye duyurusu konudan siniflanir (metin gerekmez)")
    ok(not K.ilgili_mi(fb("Portföy Dağılım Raporu", "Karşılık")), "rutin rapor konusu baslikta anahtar kelime olsa da alinmaz")
    ok(not K.ilgili_mi(fb("Genel Açıklama", "Fon Fiyatı Hk")), "fiyat aciklamasi alinmaz")
    # hisse bildirimleri etkilenmez
    hisse = {"id": 9, "tarih": dt.datetime(2026, 10, 7), "gonderen": "X", "konu": K.K_GERI_ALIM, "ozet": "x",
             "gonderen_kodlar": ["ENERY"], "ilgili_kodlar": [], "metin": ""}
    ok(K.ilgili_mi(hisse) and K.siniflandir(hisse)[0][1] == "GERI_ALIM", "hisse yolu degismedi")


def test_pencere_ve_birlestirme():
    r = K.riskleri_hesapla([fb("Genel Açıklama", "Karşılık Ayrılması Hk.", KARSILIK, "BTE", dt.datetime(2026, 10, 7))], dt.date(2026, 12, 7))
    ok(r == {}, "karsilik 60 gun sonra kalkar (7 Ekim + 60 = 6 Aralik; 7 Aralik'ta yok)")
    r = K.riskleri_hesapla([fb("Genel Açıklama", "Karşılık Ayrılması Hk.", KARSILIK, "BTE", dt.datetime(2026, 10, 7))], dt.date(2026, 12, 6))
    ok("F:BTE" in r, "60. gun (6 Aralik) hala gecerli")
    r = K.riskleri_hesapla([fb("Fon Tasfiye Duyurusu", "T", "", "IY2", dt.datetime(2026, 10, 9))], dt.date(2027, 3, 1))
    ok("F:IY2" in r, "tasfiye 180 gun gecerli")
    r = K.riskleri_hesapla([fb("Genel Açıklama", "Karşılık Ayrılması Hk.", KARSILIK, "BTE", i=1),
                            fb("Genel Açıklama", "Yan Hesap Oluşturulmasına İlişkin Açıklama", YAN_HESAP, "BTE", i=2)], BUGUN)
    ok({x["kural"] for x in r["F:BTE"]} == {"FON_KARSILIK", "FON_YAN_HESAP"}, "ayni fonda iki kural birlikte")


def test_tarama_normallestirme():
    x = {"disclosureIndex": 1678397, "publishDate": "09.10.2026 11:46:01", "fundCode": "iy2",
         "kapTitle": " İSRA GAYRİMENKUL ", "subject": "Fon Tasfiye Duyurusu", "summary": " IY2-  İkinci GYF\nTasfiye Duyurusu "}
    b = T.normallestir_fon(x)
    ok(b["gonderen_kodlar"] == ["F:IY2"] and b["konu"] == "Fon Tasfiye Duyurusu" and b["id"] == 1678397, "alanlar")
    ok(b["ozet"] == "IY2- İkinci GYF Tasfiye Duyurusu" and b["ilgili_kodlar"] == [], "ozet bosluklari teke iner")
    ok(T.normallestir_fon(dict(x, fundCode=None))["gonderen_kodlar"] == [], "fon kodu yoksa kod yok (toplama atlar)")


class _SahteIst:
    n_istek = 0
    n429 = 0

    def __init__(self, gunler, metinler=None):
        self.gunler, self.metinler, self.cagrilar = gunler, metinler or {}, []

    def istek(self, yontem, url, deneme=4, **kw):
        self.cagrilar.append((yontem, url))
        import json as _j

        class R:
            pass
        r = R()
        if "funds/byCriteria" in url:
            r.text = ""
            r.json = lambda g=kw["json"]["fromDate"]: self.gunler.get(g, [])
        else:
            bno = int(url.rsplit("/", 1)[1])
            r.text = '"text-block-value">' + self.metinler.get(bno, "") + "</div>"
            r.json = lambda: {}
        return r


def test_tarama_toplama_akisi():
    gun = lambda g, i, konu, ozet, kod: {"disclosureIndex": i, "publishDate": f"{g[8:]}.10.2026 12:00:00", "fundCode": kod,
                                         "kapTitle": "X", "subject": konu, "summary": ozet}
    gunler = {
        "2026-10-10": [gun("2026-10-10", 11, "Genel Açıklama", "Karşılık Ayrılması Hk.", "BTE"),
                       gun("2026-10-10", 12, "Fon Gider Bilgileri", "Fon Gider Bilgileri", "ABC"),
                       gun("2026-10-10", 13, "Genel Açıklama", "Tasarruf Sahiplerine Duyuru", "ZZL")],
        "2026-10-09": [gun("2026-10-09", 14, "Fon Tasfiye Duyurusu", "IY2- Tasfiye", "IY2"),
                       gun("2026-10-09", 11, "Genel Açıklama", "Karşılık Ayrılması Hk.", "BTE")],     # ayni no: tekrar eklenmez
    }
    ist = _SahteIst(gunler, {11: KARSILIK})
    mevcut = set()
    yeni = T.fon_bildirimlerini_topla(ist, 2, dt.date(2026, 10, 10), mevcut)
    ok(sorted(b["id"] for b in yeni) == [11, 14], "yalniz ilgili 2 bildirim (rutin ve belirsiz atlandi, kopya yok)")
    ok(sum(1 for c in ist.cagrilar if "funds/byCriteria" in c[1]) == 2, "gun basina bir liste istegi")
    ok(sum(1 for c in ist.cagrilar if "/Bildirim/" in c[1]) == 1, "yalniz karsilik bildiriminin metni cekildi (tasfiye metinsiz)")
    ok("%100" in [b for b in yeni if b["id"] == 11][0]["metin"], "metin bildirime eklendi")
    r = K.riskleri_hesapla(yeni, dt.date(2026, 10, 10))
    ok(set(r) == {"F:BTE", "F:IY2"}, "riskler iki fon icin")
    ok(T.fon_bildirimlerini_topla(ist, 2, dt.date(2026, 10, 10), mevcut) == [], "ikinci tur: arsivdekiler tekrar alinmaz")


def test_kap_isaretle_tefas():
    df = pd.DataFrame({"Ticker": ["BTE", "BTE", "IY2", "ABC"], "Kategori": ["TEFAS", "BIST", "TEFAS", "TEFAS"]})
    rk = {"F:BTE": [{"kural": "FON_KARSILIK", "seviye": "ORTA", "ad": "Karsilik", "tarih": dt.datetime(2026, 10, 7)}],
          "F:IY2": [{"kural": "FON_TASFIYE", "seviye": "AGIR", "ad": "Tasfiye", "tarih": dt.datetime(2026, 10, 9)}],
          "ABC": [{"kural": "DENETIM_OLUMSUZ", "seviye": "AGIR", "ad": "x", "tarih": dt.datetime(2026, 9, 1)}]}
    o = K.kap_isaretle(df, rk)
    ok(list(o["KAP_Seviye"]) == ["ORTA", "", "AGIR", ""], "TEFAS BTE ORTA; ayni kodlu BIST hissesi ETKILENMEZ; IY2 AGIR; hisse anahtari fona uygulanmaz")
    ok(list(o["KAP_Carpan"]) == [0.5, 1.0, 0.0, 1.0], "carpanlar")


def _sahte_db(riskler):
    import db
    orj = (getattr(db, "get_aktif_piyasa_tedbirleri", None), getattr(db, "get_aktif_kap_riskleri", None))
    db.get_aktif_piyasa_tedbirleri = lambda: []
    db.get_aktif_kap_riskleri = lambda: riskler
    return db, orj


def test_uyari_katmani_tefas_fon():
    df = pd.DataFrame([
        # TEFAS'ta CSV skoru BOS (sayfa hesaplar)
        {"Ticker": "BTE", "Ad": "F1", "Kategori": "TEFAS", "Son_Fiyat": 1.0, "RSI": 55.0, "Ret1M": 4.0, "Vol": 8.0,
         "Optima_Skor": None, "Gecmis_Gun": None},
        {"Ticker": "IY2", "Ad": "F2", "Kategori": "TEFAS", "Son_Fiyat": 1.0, "RSI": 55.0, "Ret1M": 4.0, "Vol": 8.0,
         "Optima_Skor": None, "Gecmis_Gun": None},
        {"Ticker": "OKF", "Ad": "F3", "Kategori": "TEFAS", "Son_Fiyat": 1.0, "RSI": 55.0, "Ret1M": 4.0, "Vol": 8.0,
         "Optima_Skor": None, "Gecmis_Gun": None},
        {"Ticker": "BTEH", "Ad": "H", "Kategori": "BIST", "Son_Fiyat": 10.0, "RSI": 50.0, "Ret1M": 5.0, "Vol": 30.0,
         "Optima_Skor": 80.0, "Gecmis_Gun": 500.0},
    ])
    from scoring import optima_score
    ham = optima_score(55.0, 4.0, vol=8.0)
    riskler = {
        "F:BTE": [{"kural": "FON_KARSILIK", "seviye": "ORTA", "ad": "Karşılık", "tarih": dt.datetime(2026, 10, 7)}],
        "F:IY2": [{"kural": "FON_TASFIYE", "seviye": "AGIR", "ad": "Fon tasfiye kararı", "tarih": dt.datetime(2026, 10, 9)}],
    }
    db, orj = _sahte_db(riskler)
    try:
        d = U.uyari_katmanini_uygula(df).set_index("Ticker")
    finally:
        db.get_aktif_piyasa_tedbirleri, db.get_aktif_kap_riskleri = orj
    ok(d.loc["BTE", "Piyasa_Tedbiri"] == "KAP DİKKAT" and "KAP bildirimi" in d.loc["BTE", "Tedbir_Aciklama"], "ORTA: etiket + aciklama")
    ok(abs(float(d.loc["BTE", "Optima_Skor"]) - round(ham * 0.5, 1)) < 0.051, "ORTA: bos TEFAS skoru uretilip x0,5 (NaN kalmaz)")
    ok(d.loc["IY2", "Piyasa_Tedbiri"] == "KAP UYARISI" and float(d.loc["IY2", "Optima_Skor"]) == 0.0, "AGIR: skor acikca 0 (NaN degil)")
    ok(d.loc["OKF", "Piyasa_Tedbiri"] == "" and pd.isna(d.loc["OKF", "Optima_Skor"]), "riski olmayan fon degismez")
    ok(d.loc["BTEH", "Piyasa_Tedbiri"] == "" and float(d.loc["BTEH", "Optima_Skor"]) == 80.0, "ayni onekli BIST hissesi etkilenmez")


def test_workflow_ve_cli():
    w = open(".github/workflows/kap_risk_tarama.yml", encoding="utf-8").read()
    ok("fon_gun" in w and "--fon-gun" in w, "workflow elle geriye yukleme girdisi (fon_gun)")
    import argparse
    src = open("kap_risk_tarama.py", encoding="utf-8").read()
    ok('"--fon-gun"' in src and "FON_ILK_YUKLEME_GUN" in src, "CLI secenegi")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"test_fon_kap: {_n['ok']}/{_n['ok']} OK")
    sys.exit(0)
