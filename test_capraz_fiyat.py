"""v2.0.7.390: capraz fiyat (USD x kur) politikasi - Bahri: 'kur cevrimi politikamiza aykiri, kesinlikle kalkmali'.
Bigpara kripto yolu (USD fiyat x USDTRY) silindi; kripto yalniz BtcTurk TL paritesi."""
import inspect, re, sys, warnings
warnings.filterwarnings("ignore")

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def _kod(path):
    src = open(path, encoding="utf-8").read()
    src = re.sub(r'""".*?"""', "", src, flags=re.S)
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))


def test_bigpara_kripto_ve_kur_cevrimi_yok():
    import bigpara_client as bc
    for ad in ("_fetch_kripto_bigpara", "KRIPTO_PAGES", "enrich_worker_kripto", "fetch_truncgil_usdtry"):
        ok(not hasattr(bc, ad), f"bigpara_client.{ad} silindi")
    ok("usdtry" not in inspect.signature(bc.fetch_all_bigpara).parameters, "fetch_all_bigpara kur parametresi almaz")
    ok("usdtry" not in inspect.signature(bc.enrich_worker_maden).parameters, "enrich_worker_maden kur parametresi almaz")
    k = _kod("bigpara_client.py")
    ok("usdtry" not in k.lower(), "bigpara_client kodunda usdtry gecmez")
    ok(not re.search(r"\*\s*usd|usd\w*\s*\*", k, re.I), "bigpara_client'ta USD carpimi yok")
    ok("yfinance" not in k and "yf." not in k, "bigpara_client yfinance kullanmaz")


def test_fetch_all_bigpara_kripto_anahtari_uretmez():
    import bigpara_client as bc
    # ag erisimi yok / her sey basarisiz: cache'i de devre disi birak
    bc._read_cache = lambda: None
    bc._write_cache = lambda d: None
    bc.fetch_truncgil_maden = lambda: {"ALTIN_TRY": 6644.78, "GUMUS_TRY": 96.37, "PLATIN_TRY": 2680.54}
    sonuc = bc.fetch_all_bigpara(force_refresh=True)
    ok(set(sonuc) == {"ALTIN_TRY", "GUMUS_TRY", "PLATIN_TRY"}, "yalniz maden anahtarlari doner (BTC/ETH vb. yok)")
    ok(sonuc["ALTIN_TRY"] == 6644.78, "maden fiyati dogrudan Truncgil TL")


def test_worker_usdtry_cekmez_ve_cagri_imzasi():
    k = _kod("worker.py")
    ok("fetch_all_bigpara(usdtry" not in k, "worker fetch_all_bigpara'ya kur gecmez")
    ok("usdtry_rate" not in k, "worker'da usdtry_rate yok")
    ok("_yf2" not in k, "worker'da kur almak icin ayri yfinance cekimi (_yf2) yok (USDTRY=X yalniz DOVIZ listesinde dogrudan TL parite olarak kalir)")


def test_projede_usd_carpimli_fiyat_cevrimi_yok():
    """Fiyat modulleri: '* usdtry' / 'usdtry *' / ons->gram sabiti yok."""
    for dosya in ("worker.py", "live_data.py", "bigpara_client.py", "maden_arsiv.py", "data_pipeline.py"):
        k = _kod(dosya)
        ok(not re.search(r"\*\s*usdtry|usdtry\w*\s*\*", k, re.I), f"{dosya}: USDTRY carpimi yok")
        ok("31.1035" not in k, f"{dosya}: ons->gram sabiti yok")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"capraz_fiyat testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
