"""v2.0.7.387: maden fiyat secimi ve worker.build() icinde `yf` tanimi (sessizce yutulan NameError)."""
import ast, sys, warnings
warnings.filterwarnings("ignore")
import worker as W

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def test_turkiye_fiyati_ezilmez():
    # Bigpara/Truncgil'den gelen TL fiyat (ALTIN_TRY 6644,78) USD x kur cevrimiyle ezilmemeli
    p = W._maden_tl_fiyat(6644.78, 4220.0, True, 49.3174, False)
    ok(p == 6644.78, f"TL fiyat korunur ({p})")
    ok(W._maden_tl_fiyat(96.37, 61.1, True, 49.3174, False) == 96.37, "gumus TL fiyati korunur")


def test_tl_fiyat_yoksa_yedek():
    p = W._maden_tl_fiyat(0.0, 4220.0, True, 49.3174, False)
    ok(abs(p - round(4220.0 * 49.3174 / 31.1035, 4)) < 1e-9, f"ons -> gram yedek cevrim ({p})")
    ok(W._maden_tl_fiyat(0.0, 10.0, False, 40.0, False) == 400.0, "ons olmayan: USD x kur")


def test_sentetik_yasak_ve_veri_yok():
    ok(W._maden_tl_fiyat(0.0, 2000.0, True, 49.0, True) == 0.0, "sentetik cevrim yasaksa (Platin vb.) cevrilmez")
    ok(W._maden_tl_fiyat(2680.54, 2000.0, True, 49.0, True) == 2680.54, "yasakli varlikta TL fiyat aynen")
    ok(W._maden_tl_fiyat(0.0, 0.0, True, 49.0, False) == 0.0, "USD fiyat yoksa 0")
    ok(W._maden_tl_fiyat(0.0, 4220.0, True, 0.0, False) == 0.0, "kur yoksa cevrilmez (kur uydurulmaz)")


def test_build_icinde_yf_tanimli():
    """build() icinde `yf.` kullanan her yerden ONCE `import yfinance as yf` olmali (aksi halde NameError)."""
    src = open("worker.py", encoding="utf-8").read()
    tree = ast.parse(src)
    build = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build")
    imp = [m.lineno for m in ast.walk(build) if isinstance(m, ast.Import)
           and any(a.name == "yfinance" and a.asname == "yf" for a in m.names)]
    kullanim = [m.lineno for m in ast.walk(build) if isinstance(m, ast.Attribute)
                and isinstance(m.value, ast.Name) and m.value.id == "yf"]
    ok(kullanim, "build() icinde yf kullanimi var (test anlamli)")
    ok(imp and min(imp) < min(kullanim), f"yf import (satir {imp}) kullanimdan (satir {kullanim}) once")
    # bos `except:` yok: hatalar sessizce yutulmasin (maden toplu download blogu)
    blok = src[src.index("maden_syms = [yf_s"):src.index("# USDTRY kuru")]
    ok(not any(l.strip() == "except:" for l in blok.splitlines()), "maden toplu download blogunda bos except yok")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"maden_fiyat testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
