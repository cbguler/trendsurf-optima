"""v2.0.7.427: radar trendi (fiyat-MA20) + tablo sinyali + log tamponu testleri (agsiz, veritabansiz).
Calistir: python test_radar_trend.py"""
import sys
import types
import warnings

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

import firsat_radari as fr
import uyari_katmani as uk
from scoring import get_signal

_n = {"ok": 0}


def ok(kosul, mesaj):
    if not kosul:
        print("BASARISIZ:", mesaj)
        sys.exit(1)
    _n["ok"] += 1


# --- _ma20_trendi ---
yuk = pd.Series(np.linspace(10, 20, 30))
dus = pd.Series(np.linspace(20, 10, 30))
ok(fr._ma20_trendi(yuk) == "YUKSELIS", "yukselen seri YUKSELIS")
ok(fr._ma20_trendi(dus) == "DUSUS", "dusen seri DUSUS")
ok(fr._ma20_trendi(pd.Series([1.0] * 30)) == "YUKSELIS", "esitlikte (fiyat == MA20) YUKSELIS (app.enrich ile ayni >=)")
ok(fr._ma20_trendi(pd.Series(range(10))) is None, "20 gunden kisa seri: None")
ok(fr._ma20_trendi(None) is None, "None guvenli")
# BALAT benzeri: son 20 gunun ortalamasi altinda baslayip toparlanan seri (fiyat MA20 ustunde, 1A getiri negatif)
balat = pd.Series([70.0] * 6 + [62, 60, 58, 55, 52, 50, 48, 45, 47, 50, 52, 55, 56, 58, 57, 59, 60.5, 61, 60.5, 60.5, 60.5])
ret1m = (balat.iloc[-1] / balat.iloc[-22] - 1) * 100
ok(ret1m < 0 and fr._ma20_trendi(balat) == "YUKSELIS", f"BALAT senaryosu: 1A getiri<0 ({ret1m:.1f}) ama fiyat MA20 ustunde")

# --- tablo_trendi ve sinyal: BALAT celismesi ---
satir = pd.Series({"Trend": "YUKSELIS"})
ok(uk.tablo_trendi(satir, -6.47) == "YUKSELIS", "radar trendi varsa 1A isaretini ezer")
ok(uk.tablo_trendi(pd.Series({"Trend": "DUSUS"}), 5.0) == "DUSUS", "radar DUSUS ise pozitif 1A'yi ezer")
ok(uk.tablo_trendi(pd.Series({"Trend": ""}), -1.0) == "DUSUS", "bos Trend: eski yontem (negatif -> DUSUS)")
ok(uk.tablo_trendi(pd.Series({"Trend": ""}), 1.0) == "YUKSELIS", "bos Trend: eski yontem (pozitif -> YUKSELIS)")
ok(uk.tablo_trendi(None, 0.0) == "YUKSELIS", "satir yok: eski yontem")
ok(uk.tablo_trendi(pd.Series({"Ticker": "X"}), -2.0) == "DUSUS", "Trend kolonu hic yok: eski yontem")
ok(uk.tablo_trendi(pd.Series({"Trend": "BILINMEZ"}), 3.0) == "YUKSELIS", "gecersiz deger yok sayilir")
eski = get_signal(16.0, 64.8, "DUSUS")[0]
yeni = get_signal(16.0, 64.8, uk.tablo_trendi(satir, -6.47))[0]
ok(eski == "NET SAT" and yeni == "TUT İZLE", f"BALAT: eski tablo {eski} -> yeni {yeni} (detayla ayni)")

# --- _trend_yaz: sahte baglanti ---
class Conn:
    def __init__(self, alter_hata=False, update_hata=False):
        self.sql, self.params, self.commits = [], [], 0
        self.alter_hata, self.update_hata = alter_hata, update_hata

    def execute(self, sql, params=None):
        if "ALTER TABLE" in sql and self.alter_hata:
            raise RuntimeError("alter yok")
        if sql.startswith("UPDATE") and self.update_hata:
            raise RuntimeError("update yok")
        self.sql.append(sql)
        self.params.append(params)

    def commit(self):
        self.commits += 1


sonuc = {"A": {"trend": "YUKSELIS"}, "B": {"trend": "DUSUS"}, "C": {"trend": None}, "D": {}}
c = Conn()
ok(fr._trend_yaz(c, sonuc) == 2, "yalniz gecerli trend yazilir (2)")
ok(any("ADD COLUMN IF NOT EXISTS trend" in s for s in c.sql), "kolon otomatik eklenir")
upd = [p for s, p in zip(c.sql, c.params) if s.startswith("UPDATE")][0]
ok(upd == ("A", "YUKSELIS", "B", "DUSUS"), f"parametreler: {upd}")
ok(fr._trend_yaz(Conn(alter_hata=True), sonuc) == 0, "kolon eklenemezse hata firlatmaz, 0 doner")
c2 = Conn(update_hata=True)
ok(fr._trend_yaz(c2, sonuc) == 0, "UPDATE hatasi firlatmaz")
ok(fr._trend_yaz(Conn(), {"A": {"trend": None}}) == 0, "yazilacak yoksa 0")

# --- ana upsert trend'den bagimsiz: kaynakta ayri adim ve kendi korumasi ---
src = open("firsat_radari.py", encoding="utf-8").read()
i = src.index("_upsert(conn, sonuc)\n    except")
ok("_trend_yaz(conn, sonuc)" in src[i:i + 400], "_trend_yaz, ana upsert'ten SONRA ayri cagriliyor")
ok('"trend": _ma20_trendi(col)' in src and '"trend": _ma20_trendi(close)' in src, "BIST ve FX/MADEN/KRIPTO taramalari trend yazar")
ok("INSERT INTO intraday_scores (ticker, kategori, skor, fiyat, rsi, ret1m, updated_at)" in src, "ana upsert degismedi")

# --- db.get_intraday_trend: baglanti/kolon hatasinda {} ---
import db
_orj = db.get_conn
db.get_conn = lambda: (_ for _ in ()).throw(RuntimeError("baglanti yok"))
ok(db.get_intraday_trend(96) == {}, "baglanti hatasinda sessizce {}")
db.get_conn = _orj

# --- app.py: tablo noktalari + overlay + log tamponu ---
app = open("app.py", encoding="utf-8").read()
ok("_tablo_trendi(r, float(r.get(\"Ret1M\", 0) or 0))" in app, "kategori tablosu tablo_trendi kullanir")
ok("trend_v = _tablo_trendi(_vr.iloc[0] if not _vr.empty else None, _s[\"ret1m\"])" in app, "Ana Sayfa tablosu tablo_trendi kullanir")
ok("stdout.reconfigure(line_buffering=True)" in app, "stdout satir tamponu acik")

# overlay parcasini calistir: sahte db.get_intraday_trend ile Trend kolonu, kategori maskesiyle
bas = app.index("    try:\n        from db import get_intraday_trend")
bit = app.index('print(f"[radar-trend] atlandi: {_tr_err}")', bas) + len('print(f"[radar-trend] atlandi: {_tr_err}")')
parca = "\n".join(l[4:] if l.startswith("    ") else l for l in app[bas:bit].splitlines())
df = pd.DataFrame({"Ticker": ["BALAT", "FIL", "FIL", "XYZ"], "Kategori": ["BIST", "KRIPTO", "TEFAS", "BIST"]})
sahte = types.SimpleNamespace(get_intraday_trend=lambda h: {"BALAT": ("BIST", "YUKSELIS"), "FIL": ("KRIPTO", "DUSUS")})
sys.modules["db"] = sahte
exec(parca, {"df": df, "pd": pd})
ok(list(df["Trend"]) == ["YUKSELIS", "DUSUS", "", ""],
   f"Trend yalniz KATEGORISI eslesen satira yazilir (FIL/TEFAS ve XYZ bos): {list(df['Trend'])}")
sys.modules["db"] = db

print(f"{_n['ok']} kontrol gecti")
print("TUM TESTLER GECTI")
