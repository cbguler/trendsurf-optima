"""bildirim_eposta.py testleri. Calistirma: python3 test_bildirim_eposta.py

Saf mantik testleri (govde/konu, olay toplayicilar, IPO siniflandirma tasimasi) agsiz calisir.
Veritabani testleri YEREL Postgres ister (varsayilan postgresql://postgres@127.0.0.1:54329/postgres, TEST_DB_URL ile
degistirilebilir); ulasilamazsa o bolum ATLANIR (SKIP yazar) - gercek Supabase'e ASLA baglanmaz. SMTP sahtedir.
"""
import os
import sys
import datetime

BASARISIZ = []


def kontrol(ad, kosul, ayrinti=""):
    print(("OK   " if kosul else "FAIL ") + ad + ((" -> " + str(ayrinti)) if (ayrinti and not kosul) else ""))
    if not kosul:
        BASARISIZ.append(ad)


import bildirim_eposta as be

# ---------------------------------------------------------------- saf mantik
o_risk = be.risk_olaylari.__name__ == "risk_olaylari"
kontrol("kod_goster fon on eki", be._kod_goster("F:ABC") == "Fon ABC" and be._kod_goster("ENERY") == "ENERY")

ev = be.xharz_olaylari([{"Ticker": "abcde", "Şirket": "ABC AŞ", "KAP_URL": "u"}, {"Ticker": ""}])
kontrol("xharz anahtar buyuk harf, bos ticker atlanir", len(ev) == 1 and ev[0]["anahtar"] == "XHARZ:ABCDE", ev)
kontrol("xharz bos liste -> None (kaynak sorunlu sayilir)", be.xharz_olaylari([]) is None and be.xharz_olaylari(None) is None)
kontrol("halkaarz None -> None", be.halkaarz_olaylari(None) is None)
ha = be.halkaarz_olaylari([{"disclosure_index": "123", "Sirket": "X AŞ", "Durum": "Onaylandı Talep Toplanıyor Yakında",
                            "Konu": "İzahname", "Detay_URL": "https://kap/123"}])
kontrol("halkaarz olayi", ha[0]["anahtar"] == "HA:123" and "X AŞ" in ha[0]["baslik"] and ha[0]["url"] == "https://kap/123", ha)

cagrilar = []
ham = [
    {"disclosureIndex": 11, "stockCodes": "AAA", "relatedStocks": "", "publishDate": "10.10.2026 10:00:00"},
    {"disclosureIndex": 12, "stockCodes": "BBB, BBB", "relatedStocks": "BBB", "publishDate": "10.10.2026 11:00:00"},
    {"disclosureIndex": 13, "stockCodes": "CCC", "relatedStocks": ""},
    {"stockCodes": "ZZZ"},
]


def detay(idx, kod):
    cagrilar.append(idx)
    if idx == 12:
        raise RuntimeError("kap hata")
    return {"brut_tl": 1.5, "ex_date": "20.10.2026"}


tm = be.temettu_olaylari(ham, detay_getir=detay, limit=5, bilinen={"TEMETTU:13"})
kontrol("temettu: indeksi olmayan kayit atlanir", [e["anahtar"] for e in tm] == ["TEMETTU:11", "TEMETTU:12", "TEMETTU:13"], tm)
kontrol("temettu: detay sadece yeni olaylar icin", cagrilar == [11, 12], cagrilar)
kontrol("temettu: detay ozete girer, hata ozeti bozmaz",
        "1,5000" in tm[0]["ozet"] and "20.10.2026" in tm[0]["ozet"] and "Kar Payı" in tm[1]["ozet"], tm)
kontrol("temettu: ham None -> None", be.temettu_olaylari(None) is None)
cagrilar.clear()
be.temettu_olaylari(ham, detay_getir=detay, limit=1)
kontrol("temettu: detay limiti", len(cagrilar) == 1, cagrilar)

html, txt = be.govde_olustur([
    {"tur": "risk", "anahtar": "k1", "baslik": "ENERY <b>", "ozet": "özet & test", "url": ""},
    {"tur": "temettu", "anahtar": "k2", "baslik": "AAA", "ozet": "", "url": "https://kap/1"},
])
kontrol("govde: HTML kacisli", "&lt;b&gt;" in html and "&amp;" in html and "<b>" not in html.split("ENERY")[1][:10], html[:300])
kontrol("govde: baglanti ve duz metin", "href='https://kap/1'" in html and "https://kap/1" in txt and "KAP uyarısı" in txt)
kontrol("govde: emoji yok", all(ord(ch) < 0x2600 or ch in "’" for ch in html + txt))
kontrol("konu satiri", be.konu_olustur([{"tur": "risk"}, {"tur": "risk"}, {"tur": "temettu"}]) ==
        "TrendSurf Optima - 2 kap uyarısı, 1 temettü", be.konu_olustur([{"tur": "risk"}, {"tur": "risk"}, {"tur": "temettu"}]))

# IPO siniflandirma tasimasi: ayni kural iki yerde (fetch_upcoming_ipos + hafif liste)
import upcoming_ipo_client as u
cat = u.KAP_CATEGORIES[1]
rec_yeni = {"disclosureBasic": {"stockCode": "INFO", "summary": "Örnek Teknoloji A.Ş. Pay Halka Arz Başvurusu Hk.",
                                "disclosureIndex": 999, "publishDate": "10.10.2026 09:00:00", "title": "İzahname",
                                "companyTitle": "INFO YATIRIM", "relatedStocks": "ORNEK"}}
rec_sa = {"disclosureBasic": {"stockCode": "XXX", "summary": "Bedelli sermaye artırımı izahnamesi", "disclosureIndex": 1}}
sat = u._izahname_satiri(rec_yeni, cat)
kontrol("izahname_satiri: yeni halka arz", sat is not None and sat["Sirket"].startswith("Örnek Teknoloji") and sat["_related_kod"] == "ORNEK"
        and sat["Durum"] == cat["durum_label"], sat)
kontrol("izahname_satiri: sermaye artirimi elenir", u._izahname_satiri(rec_sa, cat) is None)

html_kaynak = "SENTINEL"
orijinal_fetch, orijinal_ext = u._fetch_kap_html, u._extract_disclosure_json
u._fetch_kap_html = lambda params: html_kaynak
u._extract_disclosure_json = lambda h: [rec_yeni, rec_sa]
liste = u.izahname_listesi_hafif()
kontrol("izahname_listesi_hafif: iki kategori, indeks eklenir", liste is not None and len(liste) == 2 and liste[0]["disclosure_index"] == "999", liste)
u._fetch_kap_html = lambda params: None
kontrol("izahname_listesi_hafif: hicbiri cekilemezse None", u.izahname_listesi_hafif() is None)
u._fetch_kap_html, u._extract_disclosure_json = orijinal_fetch, orijinal_ext

# ---------------------------------------------------------------- veritabani
DB_URL = os.environ.get("TEST_DB_URL", "postgresql://postgres@127.0.0.1:54329/postgres")
try:
    import psycopg2
    ana = psycopg2.connect(DB_URL, connect_timeout=3)
    ana.autocommit = True
    cur = ana.cursor()
    cur.execute("DROP DATABASE IF EXISTS bildirim_test")
    cur.execute("CREATE DATABASE bildirim_test")
    ana.close()
    DB_OK = True
except Exception as e:
    print(f"SKIP veritabani testleri (yerel Postgres yok: {e})")
    DB_OK = False

if DB_OK:
    test_url = DB_URL.rsplit("/", 1)[0] + "/bildirim_test"
    os.environ["SUPABASE_DB_URL"] = test_url
    import db
    _c0 = db.get_conn()
    # prod'da elle olusturulan, init_db'nin RLS dongusunun bekledigi tablo (yoksa donguyu bozar)
    _c0.execute("CREATE TABLE IF NOT EXISTS ipo_valuations (disclosure_index BIGINT PRIMARY KEY)")
    _c0.commit()
    db.init_db()
    conn = db.get_conn()
    conn.execute("CREATE TABLE IF NOT EXISTS email_settings (user_id INTEGER PRIMARY KEY, "
                 "gonderim_saati_1 TEXT, gonderim_saati_2 TEXT, son_guncelleme TIMESTAMP)")
    for uid, em, aktif in ((101, "a@x.com", 1), (102, "b@x.com", 1), (103, "pasif@x.com", 0), (104, "ayarsiz@x.com", 1)):
        conn.execute("INSERT INTO users (id, email, password, full_name, plan, is_active) VALUES (?,?,?,?,?,?) "
                     "ON CONFLICT (id) DO NOTHING", (uid, em, "x", "T", "free", aktif))
    for uid in (101, 102, 103):
        conn.execute("INSERT INTO email_settings (user_id, gonderim_saati_1, gonderim_saati_2) VALUES (?,?,?)",
                     (uid, "09:00", "12:00"))
    conn.commit()

    alicilar = be.alicilari_oku(conn)
    kontrol("alicilar: email_settings olan + aktif", sorted(a[1] for a in alicilar) == ["a@x.com", "b@x.com"], alicilar)

    gonderilen = []
    basarisiz_adresler = set()


    def sahte(to, konu, h, t):
        if to in basarisiz_adresler:
            raise RuntimeError("smtp kapali")
        gonderilen.append((to, konu, t))
        return True


    # risk + tedbir tablolarini hazirla (ilk calisma: sessiz)
    conn.execute("INSERT INTO kap_risk_uyari (ticker, kural, seviye, ad, baslik, gonderim_tarihi, bitis_tarihi, ozet) "
                 "VALUES ('ENERY','VBTS','ORTA','VBTS tedbiri','b','2026-10-01 10:00',DATE '2026-12-01','o')")
    conn.execute("INSERT INTO kap_risk_uyari (ticker, kural, seviye, ad, baslik, gonderim_tarihi, bitis_tarihi, ozet) "
                 "VALUES ('F:ABC','FON_TASFIYE','BILGI','x','b','2026-10-01 10:00',DATE '2026-12-01','o')")
    conn.commit()
    s1 = be.calistir(conn, turler=("risk", "tedbir"), gonderici=sahte)
    kontrol("ilk calisma: mevcut uyarilar mail OLMADAN kaydedilir", s1["gonderilen"] == 0 and not gonderilen and s1["yeni"] == 0, (s1, gonderilen))
    kontrol("ilk calisma: baslangic isareti konur", conn.execute(
        "SELECT COUNT(*) FROM bildirim_eposta_olay WHERE anahtar LIKE ?", ("__BASLANGIC__%",)).fetchone()[0] == 2)
    kontrol("BILGI seviyesi olay sayilmaz", conn.execute(
        "SELECT COUNT(*) FROM bildirim_eposta_olay WHERE anahtar LIKE ?", ("RISK:F:ABC%",)).fetchone()[0] == 0)

    s2 = be.calistir(conn, turler=("risk", "tedbir"), gonderici=sahte)
    kontrol("degisiklik yoksa mail yok", s2["gonderilen"] == 0 and not gonderilen, (s2, gonderilen))

    # yeni fon uyarisi gelir
    conn.execute("INSERT INTO kap_risk_uyari (ticker, kural, seviye, ad, baslik, gonderim_tarihi, bitis_tarihi, ozet) "
                 "VALUES ('F:MD2','FON_YAN_HESAP','ORTA','Fon yan hesap','b','2026-10-11 09:00',DATE '2026-12-01','Yan hesap ozeti')")
    conn.commit()
    s3 = be.calistir(conn, turler=("risk", "tedbir"), gonderici=sahte)
    kontrol("yeni fon uyarisi: iki aboneye birer mail", s3["gonderilen"] == 2 and sorted(g[0] for g in gonderilen) == ["a@x.com", "b@x.com"], (s3, gonderilen))
    kontrol("mail icerigi fon kodunu icerir", all("Fon MD2" in g[2] for g in gonderilen))
    gonderilen.clear()
    s4 = be.calistir(conn, turler=("risk", "tedbir"), gonderici=sahte)
    kontrol("ayni olay ikinci kez gonderilmez", s4["gonderilen"] == 0 and not gonderilen, (s4, gonderilen))

    # SMTP hatasi: rezervasyon birakilir, sonraki calismada tekrar denenir
    conn.execute("INSERT INTO kap_risk_uyari (ticker, kural, seviye, ad, baslik, gonderim_tarihi, bitis_tarihi, ozet) "
                 "VALUES ('ABCDE','KONKORDATO','AGIR','Konkordato','b','2026-10-11 10:00',DATE '2026-12-01','o')")
    conn.commit()
    basarisiz_adresler.add("b@x.com")
    s5 = be.calistir(conn, turler=("risk",), gonderici=sahte)
    kontrol("SMTP hatasi: biri gider biri basarisiz", s5["gonderilen"] == 1 and s5["basarisiz"] == 1 and [g[0] for g in gonderilen] == ["a@x.com"], (s5, gonderilen))
    basarisiz_adresler.clear()
    gonderilen.clear()
    s6 = be.calistir(conn, turler=("risk",), gonderici=sahte)
    kontrol("basarisiz olan sonraki calismada tekrar denenir, digeri tekrar almaz",
            s6["gonderilen"] == 1 and [g[0] for g in gonderilen] == ["b@x.com"], (s6, gonderilen))

    # birden cok tur tek mailde ozetlenir
    gonderilen.clear()
    kaynaklar = {
        "halkaarz": be.halkaarz_olaylari([{"disclosure_index": "5", "Sirket": "Y AŞ", "Durum": "Onaylandı", "Konu": "k", "Detay_URL": "u"}]),
        "temettu": be.temettu_olaylari([{"disclosureIndex": 77, "stockCodes": "TTT", "publishDate": "11.10.2026"}]),
        "xharz": be.xharz_olaylari([{"Ticker": "NEWCO", "Şirket": "New Co"}]),
    }
    be.calistir(conn, turler=("halkaarz", "temettu", "xharz"), gonderici=sahte, kaynaklar=kaynaklar)  # ilk: sessiz
    kaynaklar2 = {
        "halkaarz": be.halkaarz_olaylari([{"disclosure_index": "5", "Sirket": "Y AŞ", "Durum": "Onaylandı", "Konu": "k", "Detay_URL": "u"},
                                          {"disclosure_index": "6", "Sirket": "Z AŞ", "Durum": "Başvuru", "Konu": "k", "Detay_URL": "u2"}]),
        "temettu": be.temettu_olaylari([{"disclosureIndex": 77, "stockCodes": "TTT"}, {"disclosureIndex": 78, "stockCodes": "UUU"}]),
        "xharz": be.xharz_olaylari([{"Ticker": "NEWCO", "Şirket": "New Co"}, {"Ticker": "SECOND", "Şirket": "Second"}]),
    }
    s7 = be.calistir(conn, turler=("halkaarz", "temettu", "xharz"), gonderici=sahte, kaynaklar=kaynaklar2)
    kontrol("uc tur: kullanici basina TEK mail", s7["yeni"] == 3 and len(gonderilen) == 2, (s7, len(gonderilen)))
    kontrol("tek mailde uc tur birden", all(("Z AŞ" in g[2] and "UUU" in g[2] and "SECOND" in g[2]) for g in gonderilen))

    # kaynak okunamadiysa (None) tur atlanir ve baslangic isareti KONMAZ
    gonderilen.clear()
    be.calistir(conn, turler=("tedbir",), gonderici=sahte, kaynaklar={"tedbir": None})
    kontrol("kaynak None: tur sessizce atlanir", not gonderilen)
    conn.execute("DELETE FROM bildirim_eposta_olay WHERE tur='tedbir'")
    conn.commit()
    be.calistir(conn, turler=("tedbir",), gonderici=sahte, kaynaklar={"tedbir": None})
    kontrol("kaynak None: baslangic isareti konmaz",
            conn.execute("SELECT COUNT(*) FROM bildirim_eposta_olay WHERE tur='tedbir'").fetchone()[0] == 0)

    # eski olaylar (retry penceresi disinda) gonderilmez
    gonderilen.clear()
    conn.execute("INSERT INTO bildirim_eposta_olay (anahtar, tur, baslik, ozet, url, ilk_tohum, olay_zamani) "
                 "VALUES ('RISK:ESKI:K:1','risk','eski','','',FALSE, NOW() - INTERVAL '30 hours')")
    conn.commit()
    s8 = be.calistir(conn, turler=("risk",), gonderici=sahte)
    kontrol("retry penceresi disindaki olay gonderilmez", s8["gonderilen"] == 0 and not gonderilen, (s8, gonderilen))

    # kuru mod
    s9 = be.calistir(conn, turler=("risk",), gonderici=sahte, kuru=True)
    kontrol("kuru mod: kayit/gonderim yok", s9["gonderilen"] == 0)

    # DDL: RLS listesi
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "db.py"), encoding="utf-8").read()
    kontrol("db.py: yeni tablolar RLS listesinde", '"bildirim_eposta_olay"' in src and '"bildirim_eposta_gonderim"' in src)
    rls = conn.execute("SELECT relname, relrowsecurity FROM pg_class WHERE relname IN "
                       "('bildirim_eposta_olay','bildirim_eposta_gonderim')").fetchall()
    kontrol("veritabaninda RLS acik", len(rls) == 2 and all(r[1] for r in rls), rls)
    conn.close()

# v410: temettu_client.py bs4 ister; workflow bunu kurmali (409 logunda "No module named 'bs4'" goruldu)
_yml = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".github/workflows/kap_risk_tarama.yml"), encoding="utf-8").read()
kontrol("workflow: beautifulsoup4 kurulur (temettu ayrintisi icin)", "beautifulsoup4" in _yml)

print()
if BASARISIZ:
    print(f"{len(BASARISIZ)} BASARISIZ:", BASARISIZ)
    sys.exit(1)
print("TUM TESTLER GECTI")
