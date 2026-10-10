"""v2.0.7.388: MADEN icin capraz fiyat YOK - worker maden blogunda yfinance (ons USD serisi) kullanilmaz.
Bahri'nin kurali: 'uygulamamizda asla ve asla capraz fiyat kullanilmama kurali' (Turkiye piyasasi degeri
baska ulkelerde farkli olabilir)."""
import re, sys, warnings
warnings.filterwarnings("ignore")

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def _maden_blogu():
    src = open("worker.py", encoding="utf-8").read()
    a = src.index('print(f"\\n[4/4] {len(MADEN)} maden')
    b = src.index("# Döviz — her parite ayrı çek")
    return src[a:b]


def _kod(blok):
    """Yorum satirlarini at (yorumlarda yasakli kelimeler gecebilir)."""
    return "\n".join(l for l in blok.splitlines() if not l.strip().startswith("#"))


def test_maden_blogunda_yfinance_yok():
    k = _kod(_maden_blogu())
    ok("yf.download" not in k and "yf.Ticker" not in k, "maden blogunda yf.download / yf.Ticker yok")
    ok("single_full" not in k, "maden blogunda tek tek yfinance (single_full) yok")
    ok("31.1035" not in k, "ons -> gram sentetik cevrimi yok")
    ok("* usdtry_rate" not in k and "*usdtry_rate" not in k, "USD x kur cevrimi yok")
    ok("ONS_TO_GRAM" not in k, "ons yardimcisi yok")
    # blokta kalan tek yfinance cagrisi USDTRY=X kuru (Bigpara'nin kripto yolu icin; maden fiyatina girmez)
    ok(re.findall(r'_yf2\.download\("([^"]+)"', k) in ([], ["USDTRY=X"]), "yfinance yalniz USDTRY=X kuru icin")


def test_fiyat_yalniz_turkiye_kaynagi_veya_onceki_csv():
    k = _maden_blogu()
    ok("bp_maden.get(t" in k, "birincil fiyat Bigpara/Truncgil'den")
    ok("Kademe 3: Son CSV" in k, "yedek: onceki CSV fiyati")
    blok3 = k[k.index("Kademe 3: Son CSV"):k.index('all_rows.append({"Ticker": t, "Ad": MADEN_ADLAR')]
    kod3 = _kod(blok3)
    ok('p     = float(_row["Son_Fiyat"]' in kod3, "Kademe 3 fiyati tasir")
    ok('_row["RSI"]' not in kod3 and '_row["Ret1M"]' not in kod3 and "_gecmis_veri_var = not" not in kod3,
       "Kademe 3 eski RSI/Ret1M/Vol'u TASIMAZ (eski degerler yfinance ons serisindendi)")


def test_teknik_gosterge_varsayilanlari_veri_yok_isaretli():
    k = _maden_blogu()
    ok("p, rsi, ret, vol_v = 0.0, 50.0, 0.0, 25.0" in k, "RSI/Ret1M/Vol notr varsayilan")
    ok("_gecmis_veri_var = False" in k, "baslangicta 'gecmis veri yok'")
    # v389: True'ya cekme YALNIZ kendi Truncgil TL arsivinden hesaplanan ozet varsa (t in _arsiv_ozetleri)
    kod = _kod(k)
    ok(len(re.findall(r"_gecmis_veri_var\s*=\s*True", kod)) == 1, "'gecmis veri var' tek yerde True'ya cekilir")
    ok(re.search(r"if t in _arsiv_ozetleri:\s*\n\s*_oz = _arsiv_ozetleri\[t\]\s*\n(?:.*\n){1}\s*_gecmis_veri_var = True", kod),
       "True yalniz arsiv ozeti olan satirda")
    ok("maden_arsiv" in kod and "yf." not in kod.split("maden_arsiv")[1].split("for t, yf_s in MADEN")[0],
       "arsiv adimi yfinance kullanmaz")
    ok('"_gecmis_veri_yok": not _gecmis_veri_var' in k, "satir 'veri yok' bayragiyla yazilir (arsiv ozeti yoksa; uygulama Turkiye gecmisiyle tazeler)")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"maden_fiyat testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
