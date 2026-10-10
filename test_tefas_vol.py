"""v2.0.7.391: TEFAS Vol artik gercek gunluk NAV getirilerinden (risk sinifi tahmini yalniz yedek).
Calistir: python3 test_tefas_vol.py"""
import sys, types, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


import tefas_client as tc


def _seri(getiriler, bitis=None, ilk=1.0):
    """Gunluk getiri listesinden is gunu indeksli fiyat serisi."""
    f = [ilk]
    for r in getiriler:
        f.append(f[-1] * (1 + r))
    idx = pd.bdate_range(end=bitis or pd.Timestamp.now().normalize(), periods=len(f))
    return pd.Series(f, index=idx)


def test_formul_elle_hesapla():
    r = [0.01, -0.01] * 20                       # 40 getiri, std ~0.01
    s = _seri(r)
    v = tc.gercek_volatilite(s)
    beklenen = round(float(s.pct_change().dropna().std()) * np.sqrt(252) * 100, 1)
    ok(v == beklenen, f"std x sqrt(252) x 100 ({v})")
    ok(15.5 < v < 16.5, "yaklasik %16 (0,01 x 15,87 x 100)")
    ok(tc.gercek_volatilite(_seri([0.001] * 40)) < 0.1, "sabit buyume -> neredeyse sifir volatilite")


def test_yetersiz_veri_none():
    ok(tc.gercek_volatilite(_seri([0.01, -0.01] * 14)) is None, "28 getiri < 30 -> None (risk sinifi tahmini kalir)")
    ok(tc.gercek_volatilite(_seri([0.01, -0.01] * 15)) is not None, "30 getiri yeterli")
    ok(tc.gercek_volatilite(None) is None and tc.gercek_volatilite(pd.Series(dtype=float)) is None, "bos/None guvenli")


def test_sifir_nan_fiyat_dayanikli():
    s = _seri([0.01, -0.01] * 20)
    s.iloc[10] = 0.0                              # TEFAS sifir yayinlamis bir gun
    s.iloc[20] = np.nan
    v = tc.gercek_volatilite(s)
    ok(v is not None and np.isfinite(v), "0 / NaN fiyat sonsuz getiri uretmez, sonuc sonlu")
    ok(v < 100, "0 fiyatli gun yapay dev volatilite uretmez")


def test_fiyat_hatasi_yer_tutucu_serisi_guvenilmez():
    r = [0.01, -0.01] * 20
    s = _seri(r)
    ok(tc.gercek_volatilite(s) is not None, "temiz seri hesaplanir")
    # TEFAS yer tutucu: 55,47 -> 0,01 -> 48,55 (canli FTM vakasi)
    bozuk = s.copy()
    bozuk.iloc[15] = bozuk.iloc[15] * 0.0002
    ok(tc.gercek_volatilite(bozuk) is None, "tek gunluk -%99,98 / +%485.000 hareket -> None (risk sinifi tahmini kalir)")
    # 0 fiyatli gun atlanir ama komsu fiyatlar arasi +%6000 sicrama da hata sayilir (canli KSP vakasi: 1,0 -> 0,0 -> 63,3)
    ksp = _seri([0.001] * 40)
    ksp.iloc[10] = 0.0
    ksp.iloc[11:] = ksp.iloc[11:] * 63
    ok(tc.gercek_volatilite(ksp) is None, "0 / yer tutucu sonrasi dev sicrama -> None")
    # %49 sinirinin altindaki gercek buyuk hareket kabul edilir; %51 hata sayilir
    ok(tc.gercek_volatilite(_seri([0.01, -0.01] * 18 + [0.49] + [0.0] * 3)) is not None, "+%49 gunluk getiri gercek sayilir")
    ok(tc.gercek_volatilite(_seri([0.01, -0.01] * 18 + [0.51] + [0.0] * 3)) is None, "+%51 gunluk getiri hata sayilir")


def _sahte_pytefas(seriler_by_kind):
    class Crawler:
        def __init__(self, *a, **k): pass
        def fetch(self, start=None, end=None, kind=None, fund_code=None):
            satirlar = seriler_by_kind.get(kind, {})
            rows = []
            for kod, s in satirlar.items():
                for t, p in s.items():
                    rows.append({"fund_code": kod, "date": t, "price": p})
            return pd.DataFrame(rows)
    m = types.ModuleType("pytefas")
    m.Crawler = Crawler
    sys.modules["pytefas"] = m


def test_toplu_guncelleme_gercek_vol_ve_kaynak_etiketi():
    import db
    db.tefas_arsiv_fiyatlari = lambda *a, **k: None    # arsive ulasilamadi: uzun vade bos, test DB'ye gitmez
    rng = np.random.default_rng(11)
    oynak = _seri(list(rng.normal(0, 0.02, 70)))       # 71 nokta, belirgin oynak
    kisa = _seri(list(rng.normal(0, 0.02, 20)))        # 21 nokta: RSI var, volatilite icin yetersiz
    _sahte_pytefas({"YAT": {"AAA": oynak, "BBB": kisa}, "EMK": {}, "BYF": {}})
    df_t = pd.DataFrame([
        {"Ticker": "AAA", "TEFAS_Kind": "YAT", "Son_Fiyat": float(oynak.iloc[-1]), "Ret1M": 0.0, "Ret3M": None,
         "RSI": 50.0, "Vol": 25.0},
        {"Ticker": "BBB", "TEFAS_Kind": "YAT", "Son_Fiyat": float(kisa.iloc[-1]), "Ret1M": 0.0, "Ret3M": None,
         "RSI": 50.0, "Vol": 18.0},
        {"Ticker": "CCC", "TEFAS_Kind": "YAT", "Son_Fiyat": 1.0, "Ret1M": 0.0, "Ret3M": None,
         "RSI": 50.0, "Vol": 12.0},                    # TEFAS'tan hic gelmedi
    ])
    out, _, ozet = tc.gercek_getiri_rsi_guncelle(df_t, log=lambda m: None)
    a = out[out.Ticker == "AAA"].iloc[0]
    b = out[out.Ticker == "BBB"].iloc[0]
    c = out[out.Ticker == "CCC"].iloc[0]
    ok(a["Vol_Kaynak"] == "GERCEK" and a["Vol"] == tc.gercek_volatilite(oynak), "yeterli veri -> gercek volatilite + GERCEK etiketi")
    ok(a["Vol"] != 25.0, "risk sinifi tahmini (25) ezildi")
    ok(b["Vol_Kaynak"] == "RISK_SINIFI" and b["Vol"] == 18.0, "yetersiz veri -> risk sinifi tahmini korunur, etiketli")
    ok(c["Vol_Kaynak"] == "RISK_SINIFI" and c["Vol"] == 12.0, "TEFAS'tan gelmeyen fon -> risk sinifi tahmini korunur")
    ok(0 <= b["RSI"] <= 100, "RSI akisi bozulmadi (kisa seride de hesaplanir)")
    ok(ozet["guncellenen"] >= 1, "getiri guncellemesi yine calisiyor")


def test_skora_etkisi_belgelenmis():
    from scoring import _teknik_alt_skor, optima_score
    # risk sinifi 5 (tahmin 25) ama gercekte durgun bir fon (yillik %6): Volatilite bileseni 10 -> 15 ham puan
    ok(_teknik_alt_skor(50, 3.0, 6.0) - _teknik_alt_skor(50, 3.0, 25.0) == 5, "tahmin 25 -> gercek 6: ham +5 puan")
    # risk sinifi 2 (tahmin 7) ama gercekte oynak (yillik %60): 15 -> 0 ham puan
    ok(_teknik_alt_skor(50, 3.0, 60.0) - _teknik_alt_skor(50, 3.0, 7.0) == -15, "tahmin 7 -> gercek 60: ham -15 puan")
    ok(optima_score(50, 3.0, vol=6.0) > optima_score(50, 3.0, vol=25.0), "Optima Skoru yonu dogru")


def test_worker_yedek_yolu_vol_kolonlarini_tasir():
    src = open("worker.py", encoding="utf-8").read()
    ok('"Getiri_Tarihi", "Vol", "Vol_Kaynak"]' in src, "gercek getiri hesaplanamazsa onceki CSV'nin Vol/Vol_Kaynak degerleri korunur")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"tefas_vol testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
