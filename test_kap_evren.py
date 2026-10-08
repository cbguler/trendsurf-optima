# -*- coding: utf-8 -*-
"""kap_evren.py + worker._kap_listesinden_evreni_tamamla testleri. Calistir: python test_kap_evren.py
v2.0.7.374. HTML ornegi KAP'in canli bist-sirketler sayfasinin (8 Ekim 2026) yapisindan alinmistir.
Ag/veritabani KULLANILMAZ (sahte nesnelerle)."""
import sys

import kap_evren as E

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def satir(slug, kodlar, ad):
    return ('<tr class="border-b hover:bg-light-danger"><td class="pl-4 py-1 text-sm">'
            f'<a href="/tr/sirket-bilgileri/ozet/{slug}"><div>{kodlar}</div></a></td>'
            '<td class="pl-4 py-4 text-sm font-normal no-underline hover:underline">'
            f'<a href="/tr/sirket-bilgileri/ozet/{slug}">{ad}</a></td>'
            '<td class="pl-4 py-4 text-sm font-normal">ANKARA</td></tr>')


HTML = "<table>" + "".join([
    satir("6275-citlekci-magazacilik-gida-a-s", "CITAS", "ÇİTLEKÇİ MAĞAZACILIK GIDA A.Ş."),
    satir("1-garanti", "GARAN, TGB", "TÜRKİYE GARANTİ BANKASI A.Ş."),
    satir("2-akbank", "AKBNK", "AKBANK T.A.Ş."),
    satir("3-bos", "", "KODSUZ"),
    satir("4-amp", "ABC", "A&amp;B SANAYİ A.Ş."),
]) + "</table>"


def test_ayristir():
    k = E.kap_bist_listesini_ayristir(HTML)
    ok(len(k) == 4, "kodsuz satir atlanir, 4 kayit")
    ok(k[0] == {"kodlar": ["CITAS"], "ad": "ÇİTLEKÇİ MAĞAZACILIK GIDA A.Ş.",
                "slug": "6275-citlekci-magazacilik-gida-a-s"}, "CITAS kaydi")
    ok(k[1]["kodlar"] == ["GARAN", "TGB"], "birden cok kod ayrilir")
    ok(k[3]["ad"] == "A&B SANAYİ A.Ş.", "HTML varliklari cozulur")
    ok(E.kap_bist_listesini_ayristir("") == [] and E.kap_bist_listesini_ayristir(None) == [], "bos girdi")
    ok(E.kap_bist_listesini_ayristir("<html>yapi degisti</html>") == [], "yapi degisirse bos (cagiran saglik kontrolu yapar)")


def test_eksik_adaylar():
    k = E.kap_bist_listesini_ayristir(HTML)
    a, c = E.eksik_adaylar(k, {"GARAN", "akbnk"}, ())
    ok([x["ticker"] for x in a] == ["ABC", "CITAS", "TGB"], "evrende olmayanlar (kucuk/buyuk harf duyarsiz), sirali")
    ok(c == [], "cakisma yok")
    ok(a[1]["ad"].startswith("ÇİTLEKÇİ") and a[1]["slug"].startswith("6275"), "ad ve slug tasinir")
    a, c = E.eksik_adaylar(k, set(), {"CITAS", "ABC"})
    ok([x["ticker"] for x in a] == ["AKBNK", "GARAN", "TGB"], "baska kategoriyle cakisanlar aday olmaz")
    ok(c == ["ABC", "CITAS"], "cakisanlar ayrica raporlanir")
    a, c = E.eksik_adaylar(k, {"GARAN", "TGB", "AKBNK", "ABC", "CITAS"}, ())
    ok(a == [] and c == [], "hepsi evrende -> bos")
    ayni = k + k
    a, _ = E.eksik_adaylar(ayni, set(), ())
    ok(len([x for x in a if x["ticker"] == "CITAS"]) == 1, "tekrarlayan kayit tek aday")
    bozuk = [{"kodlar": ["X", "TOOLONGTICKER", "A-B"], "ad": "z", "slug": "z"}]
    a, _ = E.eksik_adaylar(bozuk, set(), ())
    ok([x["ticker"] for x in a] == [], "gecersiz kod (1 harf, 8+ harf, tireli) elenir")


def test_saglik_kontrolu():
    class R:
        def __init__(self, kod, metin=""):
            self.status_code, self.text = kod, metin

    import requests
    import time
    orj_get, orj_sleep = requests.get, time.sleep
    time.sleep = lambda s: None
    try:
        requests.get = lambda *a, **k: R(200, "<html>kisa</html>")
        try:
            E.kap_bist_listesini_cek(deneme=2)
            ok(False, "kisa sayfa hata vermeli")
        except E.KapListeHata as e:
            ok("beklenenden kisa" in str(e), "yapi degisikligi acik hata")
        requests.get = lambda *a, **k: R(429)
        try:
            E.kap_bist_listesini_cek(deneme=2)
            ok(False, "HTTP 429 hata vermeli")
        except E.KapListeHata as e:
            ok("HTTP 429" in str(e), "HTTP hatasi acik hata")
        buyuk = "".join(satir(f"{i}-s", f"T{i:04d}", f"SIRKET {i}") for i in range(E.MIN_BEKLENEN_SATIR + 5))
        requests.get = lambda *a, **k: R(200, buyuk)
        ok(len(E.kap_bist_listesini_cek(deneme=1)) == E.MIN_BEKLENEN_SATIR + 5, "yeterli satir -> liste doner")
    finally:
        requests.get, time.sleep = orj_get, orj_sleep


class SahteConn:
    def __init__(self):
        self.sorgular, self.kapandi = [], False

    def execute(self, sql, params=()):
        self.sorgular.append((sql, params))
        return self

    def fetchall(self):
        return []

    def commit(self):
        pass

    def close(self):
        self.kapandi = True


def test_worker_entegrasyon():
    import worker
    import db
    sahte = SahteConn()
    orj = (E.kap_bist_listesini_cek, worker._fiyati_olanlar, db.get_conn, worker._kripto_evren_al)
    kap = E.kap_bist_listesini_ayristir(HTML)
    try:
        E.kap_bist_listesini_cek = lambda *a, **k: kap
        db.get_conn = lambda *a, **k: sahte
        worker._kripto_evren_al = lambda: [("ABC", "ABC-USD")]
        worker._KAP_AD_HARITASI.clear()
        # fiyat kontrolu: CITAS fiyatli, TGB fiyatsiz
        worker._fiyati_olanlar = lambda t: {x for x in t if x == "CITAS"}
        eklenen = worker._kap_listesinden_evreni_tamamla(["GARAN", "AKBNK"])
        ok(eklenen == ["CITAS"], "sadece fiyati olan ve cakismayan eklenir (ABC kripto ile cakisti, TGB fiyatsiz)")
        ins = [s for s in sahte.sorgular if "INSERT INTO bist_universe_dynamic" in s[0]]
        ok(len(ins) == 1 and ins[0][1] == ("CITAS", "ÇİTLEKÇİ MAĞAZACILIK GIDA A.Ş.", "KAP_BIST_auto"),
           "dinamik tabloya KAP unvani ve source=KAP_BIST_auto ile yazilir")
        ok(worker._KAP_AD_HARITASI.get("CITAS", "").startswith("ÇİTLEKÇİ"), "isim haritasi doldu")
        # KAP erisilemezse worker durmaz, hicbir sey eklenmez
        def patla(*a, **k):
            raise E.KapListeHata("test")
        E.kap_bist_listesini_cek = patla
        sahte.sorgular.clear()
        ok(worker._kap_listesinden_evreni_tamamla(["GARAN"]) == [] and not sahte.sorgular,
           "KAP hatasinda sessizce [] ve veritabani dokunulmaz")
        # fiyat kontrolu basarisizsa (bos set) hicbir sey eklenmez
        E.kap_bist_listesini_cek = lambda *a, **k: kap
        worker._fiyati_olanlar = lambda t: set()
        ok(worker._kap_listesinden_evreni_tamamla(["GARAN"]) == [] and not sahte.sorgular, "fiyat yoksa ekleme yok")
        # evren zaten tam
        worker._fiyati_olanlar = lambda t: set(t)
        ok(worker._kap_listesinden_evreni_tamamla(["GARAN", "TGB", "AKBNK", "CITAS", "ABC"]) == [],
           "eksik yoksa bos")
    finally:
        E.kap_bist_listesini_cek, worker._fiyati_olanlar, db.get_conn, worker._kripto_evren_al = orj
        worker._KAP_AD_HARITASI.clear()


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"kap_evren testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
