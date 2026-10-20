"""v2.0.7.422: BIST canli fiyat yenilemesinde zaman asimi testleri (agsiz, sahte borsapy).

Calistir: python test_canli_fiyat_zaman_asimi.py
"""
import sys
import time
import types

import pandas as pd

import live_data as ld

_sayac = {"ok": 0}


def ok(kosul, mesaj):
    if not kosul:
        print("BASARISIZ:", mesaj)
        sys.exit(1)
    _sayac["ok"] += 1


# --- 1) _borsapy_zaman_asimili: zaman asimi cagirani GERCEKTEN serbest birakir ---
t0 = time.perf_counter()
r = ld._borsapy_zaman_asimili(lambda: (time.sleep(3), 1)[1], timeout=0.5)
gecen = time.perf_counter() - t0
ok(r is None, "zaman asimi None donmeli")
ok(gecen < 1.5, f"cagiran takilan isi beklememeli (gecen {gecen:.2f}s)")

ok(ld._borsapy_zaman_asimili(lambda: 42, timeout=1) == 42, "hizli is sonucunu dondurmeli")


def _hata():
    raise ValueError("x")


ok(ld._borsapy_zaman_asimili(_hata, timeout=1) is None, "hata None donmeli")

# --- 2) _fetch_live_bist sinirli mod: takilanlar beklenmez, gelenler doner ---
TAKILAN = {"HANG1", "HANG2", "HANG3"}


class _FI:
    def __init__(self, t):
        self.t = t

    @property
    def last_price(self):
        if self.t in TAKILAN:
            time.sleep(6)           # borsapy'nin takilmasini taklit eder
        return 10.0 + len(self.t)


class _Ticker:
    def __init__(self, t):
        self.fast_info = _FI(t)

    def history(self, **kw):
        return pd.DataFrame()


ld.BORSAPY_OK = True
ld.bp = types.SimpleNamespace(Ticker=_Ticker)

anahtar = ("AAA", "BBBB", "CCCCC", "HANG1", "HANG2", "HANG3")
ld._fetch_live_bist.clear()
t0 = time.perf_counter()
fiyat = ld._fetch_live_bist(anahtar, 1)
gecen = time.perf_counter() - t0
ok(gecen < 3.0, f"sinirli mod 1 sn'lik sinirda donmeli (gecen {gecen:.2f}s)")
ok(set(fiyat) == {"AAA", "BBBB", "CCCCC"}, f"yalniz gelenler donmeli: {sorted(fiyat)}")
ok(fiyat["AAA"] == 13.0, "fiyat degeri dogru olmali")

# Sinirsiz mod (None) hizli tickerlarda eski davranisi korur
ld._fetch_live_bist.clear()
fiyat2 = ld._fetch_live_bist(("AAA", "BBBB"), None)
ok(set(fiyat2) == {"AAA", "BBBB"}, "sinirsiz mod hizli tickerlari getirmeli")

# --- 3) refresh_bist_selective sinirli modu kullanir, takilan ticker CSV fiyatiyla kalir ---
df = pd.DataFrame({
    "Ticker": ["AAA", "HANG1"], "Kategori": ["BIST", "BIST"], "Son_Fiyat": [1.0, 2.0]})
ld._SECILI_CANLI_TOPLAM_SN = 1
ld._fetch_live_bist.clear()
t0 = time.perf_counter()
out = ld.refresh_bist_selective(df, ["AAA", "HANG1"])
gecen = time.perf_counter() - t0
ok(gecen < 3.0, f"refresh_bist_selective takilan tickeri beklememeli (gecen {gecen:.2f}s)")
ok(float(out.loc[out.Ticker == "AAA", "Son_Fiyat"].iloc[0]) == 13.0, "gelen ticker guncellenmeli")
ok(float(out.loc[out.Ticker == "HANG1", "Son_Fiyat"].iloc[0]) == 2.0, "takilan ticker CSV fiyatinda kalmali")

print(f"{_sayac['ok']} kontrol gecti")
print("TUM TESTLER GECTI")
