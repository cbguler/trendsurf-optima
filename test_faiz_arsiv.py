# -*- coding: utf-8 -*-
"""v2.0.7.407: faiz_arsiv.py testleri. Calistir: python3 test_faiz_arsiv.py
Ag YOK (kaynaklar sahte). Veritabani bolumu yerel Postgres ister (TEST_DB_URL, varsayilan 127.0.0.1:54329);
ulasilamazsa SKIP. Gercek Supabase'e baglanmaz."""
import datetime
import os
import pickle
import sys

import pandas as pd

import faiz_arsiv as fa

_n = {"ok": 0}


def ok(k, m):
    assert k, "BASARISIZ: " + m
    _n["ok"] += 1


# ---- ayiklayicilar
ok(fa.mevduat_ayikla('<td class="Table_td__xlSfc">% <!-- -->44,00</td><td class="Table_td__xlSfc">% <!-- -->46,25</td>') == 46.25,
   "mevduat: en yuksek oran")
ok(fa.mevduat_ayikla("<html></html>") is None and fa.mevduat_ayikla("") is None, "mevduat: oran yoksa None")
HTML = ('<tr><td><a href="x" class="name">TR 2 Yıllık Tahvil Faizi</a></td><td class="text-bold">39,59</td>'
        '<td class="text-bold color-down"> %-0,40 </td></tr><tr><td><a class="name">TR 5 Yıllık Tahvil Faizi</a></td>'
        '<td class="text-bold">38,46</td></tr>')
ok(fa.tahvil2y_ayikla(HTML) == 39.59, "tahvil2y: 2 yillik deger (5 yilliga kaymaz)")
ok(fa.tahvil2y_ayikla("<tr><td>TR 5 Yıllık Tahvil Faizi</td></tr>") is None, "tahvil2y: yoksa None")
ok(fa.tahvil2y_ayikla("TR 2 Yıllık Tahvil Faizi</a>\n </td>\n <td class=\"x\">1.039,50</td>") == 1039.5, "tahvil2y: binlik ayrac")
ok(not fa._makul(0) and not fa._makul(250) and fa._makul(39.6), "makul aralik")

# ---- EVDS DataFrame -> kayit
df = pd.DataFrame({"Tarih": ["01-10-2026", "02-10-2026", "03-10-2026", "04-10-2026"],
                   "TP_AOFOBAP": [39.5, None, 39.7, 900.0]})
ok(fa.evds_df_kayitlar(df, "TP.AOFOBAP") == [(datetime.date(2026, 10, 1), 39.5), (datetime.date(2026, 10, 3), 39.7)],
   "evds: bos ve makul olmayan satirlar atilir, gun-ay-yil okunur")
ok(fa.evds_df_kayitlar(pd.DataFrame(), "TP.AOFOBAP") == [] and fa.evds_df_kayitlar(None, "X") == [], "evds: bos df")


class SahteEvds:
    def __init__(self, key): self.key = key

    def get_data(self, seriler, startdate, enddate):
        assert seriler == ["TP.AOFOBAP"]
        return df


k, h = fa.repo_gecmis_cek(30, evds_factory=SahteEvds)
ok(len(k) == 2 and h is None, "repo_gecmis_cek: sahte EVDS")
os.environ.pop("EVDS_API_KEY", None)
k, h = fa.repo_gecmis_cek(30)
ok(k == [] and "EVDS_API_KEY" in h, "repo: anahtar yoksa acik hata")

# ---- birikim
gun = pd.date_range("2026-08-01", "2026-08-11")  # 11 gun, ilk 0
sabit = fa.birikim_serisi([(datetime.date(2026, 8, 1), 36.5)], gun)[0]
ok(abs(sabit.iloc[0]) < 1e-12 and abs(sabit.iloc[-1] - 36.5 / 365 * 10) < 1e-9, "sabit oran: eski formul (oran x gun / 365)")
# oran 5. gunden itibaren degisir: ilk 4 gun %36.5, sonra %73
kayit = [(datetime.date(2026, 8, 1), 36.5), (datetime.date(2026, 8, 5), 73.0)]
ser, ilk, sabit_gun = fa.birikim_serisi(kayit, gun)
beklenen = (36.5 * 4 + 73.0 * 6) / 365   # 8/1->8/5: 4 gun %36.5; 8/5->8/11: 6 gun %73
ok(abs(ser.iloc[-1] - beklenen) < 1e-9, f"oran degisince birikim gunluk oranla: {ser.iloc[-1]} vs {beklenen}")
ok(ilk == datetime.date(2026, 8, 1) and sabit_gun == 0, "ilk kayit/sabit gun sayisi")
# gecmis cizgi, yeni oran gelince DEGISMEZ
ser2, _, _ = fa.birikim_serisi(kayit + [(datetime.date(2026, 8, 11), 90.0)], gun)
ok(abs(ser2.iloc[8] - ser.iloc[8]) < 1e-12, "sonradan gelen oran gecmis birikimi degistirmez")
# arsiv ilk kaydi gunlerin ortasinda baslarsa onceki gunler ilk oranla (sabit_gun sayilir)
ser3, ilk3, sg = fa.birikim_serisi([(datetime.date(2026, 8, 6), 36.5)], gun)
ok(sg == 5 and ilk3 == datetime.date(2026, 8, 6) and abs(ser3.iloc[-1] - 36.5 / 365 * 10) < 1e-9, "arsiv oncesi gunler ilk oranla, sayilir")
# hafta sonu bosluklari (repo): son bilinen oran tasinir
ser4, _, _ = fa.birikim_serisi([(datetime.date(2026, 8, 1), 36.5), (datetime.date(2026, 8, 4), 36.5)], gun)
ok(abs(ser4.iloc[-1] - 36.5 / 365 * 10) < 1e-9, "bosluklarda son bilinen oran")
ser.attrs["kaynak_notu"] = "x"
ok(pickle.loads(pickle.dumps(ser)).attrs.get("kaynak_notu") == "x", "attrs onbellekleme (pickle) ile korunur")

# ---- calistir (sahte db)
class SahteDb:
    def __init__(self):
        self.yazilan, self.son = {}, {}

    def faiz_arsiv_son_guncelleme(self, seri): return self.son.get(seri)

    def faiz_arsiv_kayit_sayisi(self, seri): return len(self.yazilan.get(seri, []))

    def faiz_arsiv_yaz(self, seri, kayitlar, kaynak=""):
        self.yazilan.setdefault(seri, []).extend(kayitlar)
        self.son[seri] = NOW
        return len(kayitlar)


NOW = datetime.datetime(2026, 10, 11, 12, 0, tzinfo=datetime.timezone.utc)
db = SahteDb()
repo_cagri = []
def repo_fn(gun):
    repo_cagri.append(gun)
    return [(datetime.date(2026, 10, 9), 39.4), (datetime.date(2026, 10, 10), 39.5)], None
s1 = fa.calistir(db, lambda: (44.0, None), lambda: (39.59, None), repo_fn, simdi=NOW)
ok(s1["mevduat"].startswith("yazildi") and s1["tahvil2y"].startswith("yazildi") and s1["repo"].startswith("yazildi 2"), f"ilk calisma yazar {s1}")
ok(repo_cagri == [fa.REPO_ILK_GUN], "repo ilk calismada uzun gecmis")
s2 = fa.calistir(db, lambda: (44.0, None), lambda: (39.59, None), repo_fn, simdi=NOW + datetime.timedelta(hours=1))
ok(set(s2.values()) == {"atlandi"}, "6 saatten taze ise hicbir kaynak cagrilmaz")
cag = []
s3 = fa.calistir(db, lambda: cag.append("m") or (45.0, None), lambda: (None, "doviz 403"), lambda g: ([], "evds hata"),
                 simdi=NOW + datetime.timedelta(hours=7))
ok(s3["mevduat"].startswith("yazildi") and s3["tahvil2y"] == "HATA: doviz 403" and s3["repo"] == "HATA: evds hata",
   f"bir kaynagin hatasi digerlerini engellemez {s3}")
ok(len(db.yazilan["mevduat"]) == 2 and len(db.yazilan["tahvil2y"]) == 1, "hata olan seriye yazilmaz")
db.yazilan["repo"] = [(datetime.date(2026, 10, 1), 1.0)] * 40
db.son["repo"] = None
repo_cagri.clear()
fa.calistir(db, lambda: (44.0, None), lambda: (39.59, None), repo_fn, simdi=NOW + datetime.timedelta(hours=20))
ok(repo_cagri == [fa.REPO_NORMAL_GUN], "yeterli repo kaydi varsa kisa pencere")

# ---- uygulama/workflow/db baglantilari
SRC = open("app.py", encoding="utf-8").read()
ok("faiz_arsiv_oku" in SRC and "birikim_serisi" in SRC, "app.py arsivi okur")
ok("TP.BISTTLREF.ORAN" not in SRC.split("def _evds_referans_oranlari_cek")[1].split("def ")[0], "TLREF 'Devlet Tahvili' kaynagi kalkti")
W = open(".github/workflows/kap_risk_tarama.yml", encoding="utf-8").read()
ok("python faiz_arsiv.py" in W and "EVDS_API_KEY" in W and "evds" in W, "workflow adimi")
DB = open("db.py", encoding="utf-8").read()
ok('"faiz_arsiv"' in DB and "CREATE TABLE IF NOT EXISTS faiz_arsiv" in DB, "db.py tablo + RLS")

# ---- gercek Postgres
DB_URL = os.environ.get("TEST_DB_URL", "postgresql://postgres@127.0.0.1:54329/postgres")
try:
    import psycopg2
    ana = psycopg2.connect(DB_URL, connect_timeout=3)
    ana.autocommit = True
    c = ana.cursor()
    c.execute("DROP DATABASE IF EXISTS faiz_test")
    c.execute("CREATE DATABASE faiz_test")
    ana.close()
    PG = True
except Exception as e:
    print(f"SKIP veritabani testleri ({e})")
    PG = False
if PG:
    os.environ["SUPABASE_DB_URL"] = DB_URL.rsplit("/", 1)[0] + "/faiz_test"
    import db as dbm
    c0 = dbm.get_conn()
    c0.execute("CREATE TABLE IF NOT EXISTS ipo_valuations (disclosure_index BIGINT PRIMARY KEY)")
    c0.commit()
    dbm.init_db()
    ok(dbm.faiz_arsiv_oku() == {}, "bos arsiv -> {}")
    ok(dbm.faiz_arsiv_son_guncelleme("mevduat") is None and dbm.faiz_arsiv_kayit_sayisi("mevduat") == 0, "bos: son guncelleme None, sayi 0")
    ok(dbm.faiz_arsiv_yaz("mevduat", [(datetime.date(2026, 8, 1), 44.0), (datetime.date(2026, 9, 1), 45.0)], "t") == 2, "yaz")
    ok(dbm.faiz_arsiv_yaz("mevduat", [(datetime.date(2026, 9, 1), 46.0)], "t") == 1, "ayni gun upsert")
    o = dbm.faiz_arsiv_oku()
    ok(o["mevduat"] == [(datetime.date(2026, 8, 1), 44.0), (datetime.date(2026, 9, 1), 46.0)], f"okuma/upsert {o}")
    o2 = dbm.faiz_arsiv_oku(datetime.date(2026, 8, 15))
    ok(o2["mevduat"][0] == (datetime.date(2026, 8, 1), 44.0), "baslangictan onceki son kayit dahil (o gunun gecerli orani)")
    o3 = dbm.faiz_arsiv_oku(datetime.date(2026, 7, 1))
    ok(o3["mevduat"][0][0] == datetime.date(2026, 8, 1), "baslangictan once kayit yoksa ilk kayit")
    son = dbm.faiz_arsiv_son_guncelleme("mevduat")
    ok(son is not None and son.tzinfo is not None, "son guncelleme tz-aware")
    ok("tahvil2y" not in o and dbm.faiz_arsiv_kayit_sayisi("mevduat") == 2, "baska seri karismaz")
    # uctan uca: gercek db ile calistir (sahte kaynaklar)
    s = fa.calistir(dbm, lambda: (47.0, None), lambda: (39.6, None),
                    lambda g: ([(datetime.date(2026, 10, 9), 39.4)], None))
    ok(s["tahvil2y"].startswith("yazildi") and dbm.faiz_arsiv_kayit_sayisi("repo") == 1, "uctan uca yazma")
    s = fa.calistir(dbm, lambda: (47.0, None), lambda: (39.6, None), lambda g: ([], "x"))
    ok(set(s.values()) == {"atlandi"}, "uctan uca: hemen tekrar -> atlandi")
    rls = dbm.get_conn().execute("SELECT relrowsecurity FROM pg_class WHERE relname='faiz_arsiv'").fetchone()
    ok(rls and rls[0], "veritabaninda RLS acik")

print(f"test_faiz_arsiv: {_n['ok']}/{_n['ok']} OK")
