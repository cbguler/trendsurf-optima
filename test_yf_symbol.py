"""v2.0.7.393: YF_Symbol etiketi - KRIPTO ve MADEN satirlarinda bos (fiyat TL kaynaklidir; Yahoo/USD sembolu
yaniltici). DOVIZ ve BIST dokunulmadi (worker DOVIZ icin single_full(yf_s) kullaniyor)."""
import re, sys, warnings
warnings.filterwarnings("ignore")

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def _satirlar():
    return open("worker.py", encoding="utf-8").read().splitlines()


def _satir_blogu(kategori):
    """'"Kategori": "<kategori>"' gecen sozluk blogunu (ilk 4 satir) dondurur."""
    s = _satirlar()
    out = []
    for i, l in enumerate(s):
        if f'"Kategori": "{kategori}"' in l and "Son_Fiyat" in l:
            out.append("\n".join(s[i:i + 5]))
    return out


def test_kripto_ve_maden_yf_symbol_bos():
    for kat in ("KRIPTO", "MADEN"):
        bl = _satir_blogu(kat)
        ok(len(bl) == 1, f"{kat}: tek satir-olusturma blogu bulundu ({len(bl)})")
        ok('"YF_Symbol": ""' in bl[0], f"{kat}: YF_Symbol bos yaziliyor")
        ok('"YF_Symbol": yf_s' not in bl[0], f"{kat}: eski yf_s atamasi yok")


def test_doviz_dokunulmadi():
    bl = _satir_blogu("DOVIZ")
    ok(len(bl) == 1 and '"YF_Symbol": yf_s' in bl[0], "DOVIZ: YF_Symbol ayni kaldi")
    ok("single_full(yf_s, t)" in open("worker.py", encoding="utf-8").read(), "DOVIZ yfinance yedegi duruyor")


def test_grafik_yolu_kolona_bagli_degil():
    src = open("app.py", encoding="utf-8").read()
    for kat in ("MADEN", "KRIPTO"):
        i = src.index(f'if category == "{kat}":')
        j = src.index("raise _HistEmptyError()", i)
        ok("yfs" not in src[i:j] and "YF_Symbol" not in src[i:j], f"app.get_hist {kat} dali kolonu okumaz")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"test_yf_symbol: {_n['ok']}/{_n['ok']} OK")
