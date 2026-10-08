# -*- coding: utf-8 -*-
"""kap_risk.py + kap_risk_tarama.py (agsiz kisimlar) birim testleri. Calistir: python test_kap_risk.py
v2.0.7.373. Ornek metin/basliklar CANLI KAP verisinden (8 Ekim 2026) alinmistir."""
import datetime as dt
import sys

import pandas as pd

import kap_risk as K
import kap_risk_tarama as T

BUGUN = dt.date(2026, 10, 8)
_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def b(konu, ozet="", tarih=dt.datetime(2026, 10, 7, 18, 30), gk=(), ik=(), metin="", gonderen="X", i=1):
    return {"id": i, "tarih": tarih, "gonderen": gonderen, "konu": konu, "ozet": ozet,
            "gonderen_kodlar": list(gk), "ilgili_kodlar": list(ik), "metin": metin}


def kurallar(riskler, t):
    return {r["kural"] for r in riskler.get(t, [])}


VBTS_ACIK = ("Sermaye Piyasası Kurulu kararı uyarınca devreye alınan Volatilite Bazlı Tedbir Sistemi (VBTS) kapsamında "
             "CITAS.E, CATES.E ve SELEC.E payları 15/09/2026 tarihli işlemlerden (seans başından) 14/10/2026 tarihli "
             "işlemlere (seans sonuna) kadar açığa satışa ve kredili işlemlere konu edilemeyecektir. Not: VBTS kapsamında "
             "getirilen tedbirler ayrı değerlendirilir. According to the Volatility Based Measures System (VBMS), "
             "short selling in CATES.E shares will be prohibited from 15/09/2026 until 14/10/2026.")
VBTS_BRUT = ("Sermaye Piyasası Kurulu kararı uyarınca devreye alınan Volatilite Bazlı Tedbir Sistemi (VBTS) kapsamında "
             "AHSGY.E paylarında 19/09/2026 tarihli işlemlerden (seans başından) 18/10/2026 tarihli işlemlere (seans sonuna) "
             "kadar brüt takas uygulanacaktır. İlgili payda halihazırda uygulanmakta olan tedbirler de devam edecektir.")
OZ_VBTS = "Pay Piyasasında Volatilite Bazlı Tedbir Sistemi"


def test_vbts():
    r = K.riskleri_hesapla([b(K.K_VBTS, OZ_VBTS, dt.datetime(2026, 9, 14, 18, 28), ik=["CITAS", "CATES", "SELEC"], metin=VBTS_ACIK)], BUGUN)
    ok(set(r) == {"CITAS", "CATES", "SELEC"}, "toplu duyuruda 3 hisse")
    ok(kurallar(r, "CATES") == {"VBTS_ACIGA_SATIS"} and r["CATES"][0]["seviye"] == K.SEVIYE_ORTA, "CATES VBTS ORTA")
    ok(r["CATES"][0]["bitis"] == dt.date(2026, 10, 14), "bitis tarihi 14.10 (ingilizce cumle kural uretmez)")
    ok(K.riskleri_hesapla([b(K.K_VBTS, OZ_VBTS, dt.datetime(2026, 9, 14), ik=["CATES"], metin=VBTS_ACIK)], dt.date(2026, 10, 15)) == {},
       "suresi dolan VBTS kalkar")
    rb = K.riskleri_hesapla([b(K.K_VBTS, OZ_VBTS, dt.datetime(2026, 9, 18, 18, 30), ik=["AHSGY"], metin=VBTS_BRUT)], BUGUN)
    ok(kurallar(rb, "AHSGY") == {"VBTS_BRUT_TAKAS"} and rb["AHSGY"][0]["seviye"] == K.SEVIYE_AGIR, "brut takas AGIR")
    # metin alinamadiysa guvenli taraf: ilgili kodlara ORTA
    rf = K.riskleri_hesapla([b(K.K_VBTS, OZ_VBTS, dt.datetime(2026, 10, 6), ik=["DMRGD"], metin="")], BUGUN)
    ok(kurallar(rf, "DMRGD") == {"VBTS_ACIGA_SATIS"}, "metinsiz VBTS yine uyari uretir")
    # VBTS olmayan BISTECH duyurusu (temettu 'Hak Kullanimi') risk degil
    ok(K.ilgili_mi(b(K.K_VBTS, "Hak Kullanımı", ik=["KRVGD"])) is False, "Hak Kullanimi ilgisiz")
    ok(K.metin_gerekli_mi(b(K.K_VBTS, OZ_VBTS)) and not K.metin_gerekli_mi(b(K.K_SERMAYE[0], "Bedelsiz ...")), "metin sadece VBTS icin")


def test_yanlis_pozitifler():
    ban = b("SPK İşlem Yasağı Nedeniyle Pay Duyurusu", "SPK İşlem Yasağı Nedeniyle Pay Duyurusu", ik=["THYAO", "AKBNK"], gonderen="MERKEZİ KAYIT KURULUŞU A.Ş.")
    ok(K.ilgili_mi(ban) is False and K.riskleri_hesapla([ban], BUGUN) == {}, "kisi bazli SPK islem yasagi hisse riski DEGIL")
    ok(K.riskleri_hesapla([b("Temerrüt İşlemi", "x", ik=["AKBNK"])], BUGUN) == {}, "piyasa temerrut islemi risk degil")
    ok(K.riskleri_hesapla([b("Borsa İstanbul A.Ş. Duyurusu", "Gözetim tedbiri", ik=["AEFES"])], BUGUN) == {}, "yatirimci bazli gozetim risk degil")
    # sirket-gonderimli kural: bildirim baska sirketin koduna yazilmaz (konu sirketi olan ilgili_kodlar yok sayilir)
    r = K.riskleri_hesapla([b(K.K_GERI_ALIM, "x", gk=["ENERY"], ik=["BASKA"])], BUGUN)
    ok(set(r) == {"ENERY"}, "sirket bildirimi sadece gonderen sirkete yazilir")
    ok(K.riskleri_hesapla([b(K.K_GENEL, "Yenilenebilir Enerji Yatırımı Hakkında", gk=["SARKY"])], BUGUN) == {}, "siradan ozel durum risk degil")


def test_geri_alim_bilgi():
    r = K.riskleri_hesapla([b(K.K_GERI_ALIM, "07.10.2026 Tarihli Pay Geri Alım İşlemleri hk.", dt.datetime(2026, 10, 7, 18, 30, 47), gk=["ENERY"])], BUGUN)
    ok(kurallar(r, "ENERY") == {"GERI_ALIM"} and r["ENERY"][0]["seviye"] == K.SEVIYE_BILGI, "ENERY geri alim = BILGI")
    ok(K.en_siddetli(r["ENERY"]) == K.SEVIYE_BILGI and K.etiket(K.SEVIYE_BILGI) == "", "BILGI etiket/skor vermez")
    ok(K.riskleri_hesapla([b(K.K_GERI_ALIM, "x", dt.datetime(2026, 10, 7), gk=["ENERY"])], dt.date(2026, 10, 30)) == {}, "14 gun sonra kalkar")


def test_sira_kapatma():
    kap = b(K.K_SIRA, "Pay Sırasının İşleme Kapatılması", dt.datetime(2026, 10, 5, 9), ik=["XXXX"], i=1)
    ac = b(K.K_SIRA, "Pay Sırasının İşleme Açılması", dt.datetime(2026, 10, 6, 9), ik=["XXXX"], i=2)
    ok(kurallar(K.riskleri_hesapla([kap], BUGUN), "XXXX") == {"SIRA_KAPALI"}, "kapatma -> AGIR")
    ok(K.riskleri_hesapla([kap, ac], BUGUN) == {} and K.riskleri_hesapla([ac, kap], BUGUN) == {}, "sonra acilmissa uyari yok (liste sirasi onemsiz)")
    kap2 = b(K.K_SIRA, "Pay Sırasının İşleme Kapatılması", dt.datetime(2026, 10, 7, 9), ik=["XXXX"], i=3)
    ok(kurallar(K.riskleri_hesapla([ac, kap2, kap], BUGUN), "XXXX") == {"SIRA_KAPALI"}, "acmadan SONRA yeniden kapatma -> AGIR")


def test_diger_kurallar():
    r = K.riskleri_hesapla([b(K.K_DENETIM_OLUMSUZ, "x", dt.datetime(2026, 9, 1), gk=["ATEKS"])], BUGUN)
    ok(kurallar(r, "ATEKS") == {"DENETIM_OLUMSUZ"} and r["ATEKS"][0]["seviye"] == K.SEVIYE_AGIR, "olumsuz denetim AGIR")
    r = K.riskleri_hesapla([b(K.K_FIN_GEC, "x", dt.datetime(2026, 9, 20), ik=["ARASE"], gonderen="KAMUYU AYDINLATMA PLATFORMU")], BUGUN)
    ok(kurallar(r, "ARASE") == {"FIN_TABLO_GEC"}, "gec finansal tablo ORTA")
    r = K.riskleri_hesapla([b(K.K_PAZAR[0], "Payların Yakın İzleme Pazarına Alınması", ik=["XYZ"])], BUGUN)
    ok(kurallar(r, "XYZ") == {"YAKIN_IZLEME"} and r["XYZ"][0]["seviye"] == K.SEVIYE_ORTA, "yakin izleme ORTA")
    r = K.riskleri_hesapla([b(K.K_PAZAR[0], "Pazar Değişikliği", ik=["TERA"])], BUGUN)
    ok(kurallar(r, "TERA") == {"PAZAR_DEGISIKLIGI"} and r["TERA"][0]["seviye"] == K.SEVIYE_BILGI, "yonu belirsiz pazar degisikligi BILGI")
    r = K.riskleri_hesapla([b(K.K_UYARI, "x", ik=["CASA"], tarih=dt.datetime(2026, 8, 1))], BUGUN)
    ok(kurallar(r, "CASA") == {"SIRKET_UYARI"}, "sirket uyarisi (90 gun)")


def test_sermaye():
    ok(K._sermaye_turu("Bedelsiz Pay Alma Hakkı Kullanım Tarihi Hk.") == "SERMAYE_BEDELSIZ", "'Bedelsiz Pay Alma Hakki' bedelli DEGIL")
    ok(K._sermaye_turu("Bedelli Sermaye Artırımı Hak Kullanım Tarihi") == "SERMAYE_BEDELLI", "bedelli")
    ok(K._sermaye_turu("Tahsisli Sermaye Artırımı Başvurusu") == "SERMAYE_BEDELLI", "tahsisli (sulandirici) ORTA grubunda")
    ok(K._sermaye_turu("Tahsisli Sermaye Artırımı Sürecinden Vazgeçilmesi Hakkında") == "SERMAYE_DIGER", "vazgecme risk degil")
    ok(K._sermaye_turu("25.09.2026 Tescil Tarihli Sermaye Artırımı Bildirimidir.") == "SERMAYE_DIGER", "turu belirsiz = BILGI")
    ok(K._sermaye_turu("Sermaye Azaltımı Hakkında") == "SERMAYE_AZALTIM", "azaltim")
    ok(K._sermaye_turu("Geri Alınan Payların İptali Nedeniyle Sermaye Azaltımı") == "SERMAYE_DIGER", "geri alinan pay iptali risk degil")
    r = K.riskleri_hesapla([b(K.K_SERMAYE[0], "Bedelli Sermaye Artırımı", dt.datetime(2026, 10, 2), gk=["ABC"])], BUGUN)
    ok(r["ABC"][0]["seviye"] == K.SEVIYE_ORTA, "bedelli = ORTA")


def test_konkordato():
    ok(K._kendi_konkordato_mu("Konkordato Talebi Kapsamında Geçici Mühlet ve İhtiyati Tedbir Kararları Hakkında"), "USAK: kendi (AGIR)")
    ok(not K._kendi_konkordato_mu("Konkordato 58. Taksit Ödemesi"), "EMNIS: surmekte olan plan taksiti ORTA, AGIR degil")
    ok(not K._kendi_konkordato_mu("Fon Kullanıcısı İnfinia Advanced Elektronik A.Ş. Hakkında Konkordato Geçici Mühlet Kararı"), "HDFVK: baskasi (ORTA)")
    r = K.riskleri_hesapla([b(K.K_GENEL, "Konkordato Talebi Kapsamında Geçici Mühlet Hakkında", gk=["USAK"])], BUGUN)
    ok(r["USAK"][0]["seviye"] == K.SEVIYE_AGIR and r["USAK"][0]["kural"] == "KONKORDATO_IFLAS", "kendi konkordato AGIR")
    r = K.riskleri_hesapla([b(K.K_GENEL, "Fon Kullanıcısı X A.Ş. Hakkında Konkordato Kararı", gk=["HDFVK"])], BUGUN)
    ok(r["HDFVK"][0]["seviye"] == K.SEVIYE_ORTA, "baskasinin konkordatosu ORTA")
    r = K.riskleri_hesapla([b("Konkordato Talebi", "x", gk=["ABC"])], BUGUN)
    ok(kurallar(r, "ABC") == {"KONKORDATO_IFLAS"}, "baslikta konkordato AGIR")


def test_tarama_yardimcilari():
    x = {"publishDate": "07.10.2026 18:30:47", "kapTitle": "ENERYA ENERJİ A.Ş.", "subject": "Payların Geri Alınmasına İlişkin Bildirim",
         "summary": " 07.10.2026 Tarihli  Pay Alım İşlemleri hk.", "stockCodes": "ENERY", "relatedStocks": None, "disclosureIndex": 1676000}
    n = T.normallestir(x)
    ok(n["gonderen_kodlar"] == ["ENERY"] and n["ilgili_kodlar"] == [] and n["tarih"] == dt.datetime(2026, 10, 7, 18, 30, 47), "kayit normallestirme")
    ok(n["ozet"] == "07.10.2026 Tarihli Pay Alım İşlemleri hk.", "ozet bosluklari")
    ok(K.kodlari_ayir("OZATD, SKP, TERA, TRA") == ["OZATD", "SKP", "TERA", "TRA"], "kod listesi")
    sayfa = ('...<div class=\\"text-block-value\\"\\u003e\\u003cdiv\\u003eSermaye Piyasası Kurulu kararı uyarınca devreye alınan '
             'Volatilite Bazlı Tedbir Sistemi (VBTS) kapsamında DMRGD.E payları 28/09/2026 tarihli işlemlerden (seans başından) '
             '27/10/2026 tarihli işlemlere (seans sonuna) kadar açığa satışa ve kredili işlemlere konu edilemeyecektir.\\u003c/div\\u003e...')
    m = T.detay_metni(sayfa)
    r = K.riskleri_hesapla([b(K.K_VBTS, OZ_VBTS, dt.datetime(2026, 9, 25), ik=["DMRGD"], metin=m)], BUGUN)
    ok(r["DMRGD"][0]["bitis"] == dt.date(2026, 10, 27), "kacisli sayfa metninden VBTS bitis tarihi")


def test_isaretle():
    df = pd.DataFrame({"Ticker": ["CATES", "ENERY", "THYAO", "ATEKS", "XYZ"],
                       "Kategori": ["BIST", "BIST", "BIST", "BIST", "TEFAS"]})
    rk = {"CATES": [{"kural": "VBTS_ACIGA_SATIS", "seviye": "ORTA", "ad": "VBTS", "tarih": dt.datetime(2026, 9, 14)}],
          "ENERY": [{"kural": "GERI_ALIM", "seviye": "BILGI", "ad": "Pay geri alımı", "tarih": dt.datetime(2026, 10, 7)}],
          "ATEKS": [{"kural": "DENETIM_OLUMSUZ", "seviye": "AGIR", "ad": "Denetim", "tarih": dt.datetime(2026, 9, 1)},
                    {"kural": "GERI_ALIM", "seviye": "BILGI", "ad": "Geri alım", "tarih": dt.datetime(2026, 9, 5)}],
          "XYZ": [{"kural": "SIRA_KAPALI", "seviye": "AGIR", "ad": "x", "tarih": dt.datetime(2026, 9, 1)}]}
    o = K.kap_isaretle(df, rk)
    ok(list(o["KAP_Seviye"]) == ["ORTA", "", "", "AGIR", ""], "seviyeler (TEFAS satiri etkilenmez, BILGI seviye vermez)")
    ok(list(o["KAP_Carpan"]) == [0.5, 1.0, 1.0, 0.0, 1.0], "skor carpanlari")
    ok(o.loc[1, "KAP_Bilgi"] != "" and o.loc[1, "KAP_Aciklama"] == "", "ENERY: bilgi var, etiket yok")
    ok("Denetim" in o.loc[3, "KAP_Aciklama"] and "Geri alım" in o.loc[3, "KAP_Bilgi"], "ATEKS aciklama ve bilgi ayri")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"kap_risk testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
