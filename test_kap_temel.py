# -*- coding: utf-8 -*-
"""v2.0.7.381: KAP-oncelikli PD/DD + F/K (kap_temel.py), metin tabanli KAP tablo okuyucu, Yahoo para birimi
tutarliligi, detay tablosu etiketleri, temettu koruma. Calistir: python test_kap_temel.py
Ag KULLANILMAZ: KAP sayfalari sentetik HTML ile verilir (gercek sayfa yapisindan: THYAO/GARAN/KRDMD, 9 Ekim 2026)."""
import os
import sys
import tempfile

import pandas as pd

import kap_client as K
import kap_temel as T

_n = {"ok": 0}


def ok(kosul, mesaj):
    assert kosul, "BASARISIZ: " + mesaj
    _n["ok"] += 1


def yakin(a, b, tol=1e-6):
    return a is not None and abs(a - b) <= tol * max(1.0, abs(b))


# ── sentetik KAP sayfalari ───────────────────────────────────
def _tablo(basliklar, satirlar):
    h = "<thead><tr>" + "".join(f"<th>{b}</th>" for b in basliklar) + "</tr></thead>" if basliklar else ""
    g = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in s) + "</tr>" for s in satirlar)
    return f"<table>{h}<tbody>{g}</tbody></table>"


def fin_html(donemler, birimler, ozk, kar, etiket_ozk="Ana Ortaklığa Ait Özkaynaklar",
             etiket_kar="Dönem Kârının (Zararının) Dağılımı, Ana Ortaklık Payları", sermaye=None):
    """ozk/kar: donem sayisi kadar deger (metin, KAP formati) ya da ''."""
    bilanco = _tablo(["FİNANSAL DURUM TABLOSU"] + donemler,
                     [["Sunum Para Birimi"] + birimler, ["Toplam Varlıklar"] + ["9.999"] * len(donemler),
                      [etiket_ozk] + ozk] + ([["Ödenmiş Sermaye"] + [sermaye] * len(donemler)] if sermaye else []))
    gelir_baslik = _tablo(["KAR VEYA ZARAR VE DİĞER KAPSAMLI GELİR TABLOSU"] + donemler,
                          [["Sunum Para Birimi"] + birimler])
    kar_satiri = _tablo(None, [[etiket_kar] + kar])
    return f"<html><body>{bilanco}{gelir_baslik}{kar_satiri}{'x' * 600}</body></html>"


def genel_html(satirlar):
    return ("<html><body>" + _tablo(
        ["Borsa Kodu", "Toplam Pay Adedi", "Borsada İşlem Görmeyen Pay Adedi", "Fiili Dolaşımdaki Pay Oranı(%)"],
        [[k, a, "0,00", "50,00"] for k, a in satirlar]) + "x" * 600 + "</body></html>")


def test_metin_tablo_sondaki_sifir():
    """pandas.read_html '745.430'u 745.43 yapip 74543 okutuyordu; metin okuyucu bunu korumali."""
    html = _tablo(None, [["Hasılat", "504.398", "745.430", "955.472"]])
    t = K._kap_tablolar_metin(html)
    ok(len(t) == 1 and t[0].iloc[0, 2] == "745.430", "hucre metni oldugu gibi kalir")
    ok(T.tr_sayi("745.430") == 745430.0, "tr_sayi 745.430 -> 745430")
    ok(T.tr_sayi("119.470.352,22") == 119470352.22, "tr_sayi ondalikli")
    ok(T.tr_sayi("-") is None and T.tr_sayi("") is None and T.tr_sayi(None) is None, "bos degerler None")
    r = {}
    K._parse_kap_financials(K._kap_tablolar_metin(fin_html(["2025/12", "2026/06"], ["1000000TL", "1000000TL"],
                                                           ["900.000", "1.018.520"], ["100.000", "745.430"],
                                                           etiket_kar="Net Dönem Kârı (Zararı)")), r)
    ok(r.get("kap_net_income") == 745430 * 1e6, f"eski ayristirici da sondaki sifiri korur ({r.get('kap_net_income')})")
    ok(r.get("kap_equity") == 1018520 * 1e6, "ozkaynak 1.018.520 -> 1018520 (milyon TL)")


def test_seriler_sutun_basina_birim():
    """GARAN: 2025/12 sutunu 1000TL, 2026/06 sutunu 1000000TL - her sutunun kendi carpani."""
    t = K._kap_tablolar_metin(fin_html(["2025/12", "2026/06"], ["1000TL", "1000000TL"],
                                       ["500.000", "600"], ["100.000", "50"]))
    s = T.kap_seriler(t)
    oz = s[T._norm("Ana Ortaklığa Ait Özkaynaklar")]
    ok(oz["2025/12"] == (500000 * 1e3, "TL") and oz["2026/06"] == (600 * 1e6, "TL"), f"sutun basina carpan: {oz}")
    ok(T._en_guncel(s, T.OZKAYNAK_ETIKETLERI)[0] == "2026/06", "en guncel donem 2026/06")


def test_pay_adetleri():
    p = T.pay_adetleri(genel_html([("THYAO", "1.380.000.000,00")]))
    ok(p == {"THYAO": 1.38e9}, f"tek kodlu: {p}")
    p = T.pay_adetleri(genel_html([("KRDMB", "119.470.352,22"), ("KRDMA", "240.303.646,14"), ("KRDMD", "780.226.001,64")]))
    ok(set(p) == {"KRDMA", "KRDMB", "KRDMD"} and yakin(p["KRDMD"], 780226001.64), f"cok sinifli: {p}")
    ok(T.pay_adetleri("<html><body>bos</body></html>") == {}, "tablo yoksa bos sozluk")


# ── hesapla ──────────────────────────────────────────────────
def _thyao(kar_son="18.864", birim="1000000TL"):
    return fin_html(["2024/12", "2025/12", "2026/06"], [birim] * 3, ["679.887", "911.222", "1.018.517"],
                    ["113.378", "118.208", kar_son])


def test_thyao_ara_donem_yillik():
    r = T.hesapla("THYAO", 287.5, fin_html=_thyao(), genel_html=genel_html([("THYAO", "1.380.000.000,00")]))
    ok(yakin(r["piyasa_degeri"], 287.5 * 1.38e9), "piyasa degeri = fiyat x KAP pay adedi")
    ok(yakin(r["pb"], 287.5 * 1.38e9 / (1018517 * 1e6)), f"PD/DD 0,39 civari ({r['pb']})")
    ok(0.38 < r["pb"] < 0.40, "THYAO PD/DD ~0,39 (Yahoo'da 18,1 idi)")
    ok(r["donem"] == "2026/06" and r["pay_kaynak"] == "KAP genel", "donem ve pay kaynagi etiketli")
    ok(r["pe_tur"] == "YILLIK" and r["kar_donem"] == "2025/12", "ara donemde F/K son tam yil kariyla ve YILLIK etiketli")
    ok(yakin(r["pe"], 287.5 * 1.38e9 / (118208 * 1e6)), f"F/K = PD / 2025 net kar ({r['pe']})")


def test_yillik_donem_ttm():
    h = fin_html(["2024/12", "2025/12"], ["1000000TL"] * 2, ["679.887", "911.222"], ["113.378", "118.208"])
    r = T.hesapla("THYAO", 287.5, fin_html=h, genel_html=genel_html([("THYAO", "1.380.000.000,00")]))
    ok(r["pe_tur"] == "TTM" and r["kar_donem"] == "2025/12" and r["donem"] == "2025/12", "12. ay donemi = tam iz. 12A")


def test_ara_donem_zarar_ve_olmayan_yil():
    r = T.hesapla("THYAO", 100.0, fin_html=_thyao("-5.000"), genel_html=genel_html([("THYAO", "1.380.000.000,00")]))
    ok(r["pe"] is None and r["pe_durum"] == "zarar" and r["pb"] is not None, "ara donem zarar: F/K yok, PD/DD var")
    h = fin_html(["2026/06"], ["1000000TL"], ["1.018.517"], ["18.864"])
    r = T.hesapla("THYAO", 100.0, fin_html=h, genel_html=genel_html([("THYAO", "1.380.000.000,00")]))
    ok(r["pe"] is None and r["pb"] is not None and any("yillik net kar" in n for n in r["notlar"]),
       "onceki yil 12. ay yoksa F/K hesaplanmaz (yillandirma/tahmin yok)")
    h = fin_html(["2025/12"], ["1000000TL"], ["-5.000"], ["100"])
    r = T.hesapla("THYAO", 100.0, fin_html=h, genel_html=genel_html([("THYAO", "1.380.000.000,00")]))
    ok(r["pb"] is None, "negatif ozkaynakta PD/DD anlamsiz: None")


def test_cok_sinifli():
    h = fin_html(["2025/12"], ["1000TL"], ["108.343.586"], ["5.975.641"])
    g = genel_html([("KRDMB", "119.470.352,22"), ("KRDMA", "240.303.646,14"), ("KRDMD", "780.226.001,64")])
    fy = {"KRDMA": 39.18, "KRDMB": 72.15, "KRDMD": 43.20}
    r = T.hesapla("KRDMD", 43.20, fy, fin_html=h, genel_html=g)
    bek = (119470352.22 * 72.15 + 240303646.14 * 39.18 + 780226001.64 * 43.20)
    ok(yakin(r["piyasa_degeri"], bek), "her grup kendi fiyatiyla carpilip toplanir")
    r2 = T.hesapla("KRDMA", 39.18, fy, fin_html=h, genel_html=g)
    ok(yakin(r["pb"], r2["pb"]), "ayni sirketin tum siniflari ayni PD/DD'yi alir")
    r3 = T.hesapla("KRDMD", 43.20, {}, fin_html=h, genel_html=g)
    ok(any("fiyati olmayan" in n for n in r3["notlar"]), "diger sinif fiyati yoksa not dusulur")


def test_pay_adedi_yedegi_ve_yabanci_para():
    h = fin_html(["2025/12"], ["1000000TL"], ["900"], ["100"], sermaye="1.380")
    r = T.hesapla("THYAO", 10.0, fin_html=h, genel_html="x" * 600)
    ok(r["pay_kaynak"].startswith("KAP odenmis sermaye") and yakin(r["piyasa_degeri"], 10.0 * 1380 * 1e6),
       f"genel sayfa yoksa donem sonu odenmis sermaye (etiketli): {r['pay_kaynak']}")
    h = fin_html(["2025/12"], ["1000USD"], ["100.000"], ["10.000"])
    r = T.hesapla("THYAO", 50.0, kurlar={"USD": 50.0}, fin_html=h, genel_html=genel_html([("THYAO", "1.000.000,00")]))
    ok(yakin(r["pb"], (50.0 * 1e6 / 50.0) / (100000 * 1e3)), f"USD raporlayan: piyasa degeri USD'ye cevrilir ({r['pb']})")
    r = T.hesapla("THYAO", 50.0, kurlar={}, fin_html=h, genel_html=genel_html([("THYAO", "1.000.000,00")]))
    ok(r["pb"] is None and any("kuru yok" in n for n in r["notlar"]), "kur yoksa oran hesaplanmaz, kur uydurulmaz")


def test_veri_yok():
    ok(T.hesapla("THYAO", 0.0)["notlar"] == ["fiyat yok"], "fiyat yoksa hesap yok")
    r = T.hesapla("THYAO", 10.0, fin_html="<html>" + "x" * 600 + "</html>", genel_html="x" * 600)
    ok(r["pb"] is None and r["pe"] is None, "finansal tablo yoksa her sey None")


# ── birlestirme (KAP -> yfinance) ────────────────────────────
def _kap(pb=0.39, pe=3.36, tur="YILLIK", durum="hesaplandi"):
    return {"pb": pb, "pe": pe, "pe_tur": tur, "pe_durum": durum, "donem": "2026/06", "kar_donem": "2025/12", "notlar": []}


def test_birlestir_thyao():
    yf = {"_source": "yfinance", "pb_ratio": 18.1, "pe_ratio": None, "div_yield": 0.0, "financial_currency": "USD",
          "currency": "TRY", "equity": 15.884, "eps": -5.98}
    pb, pe, dy, m = T.oranlari_birlestir(_kap(), yf, 287.5, {"USD": 49.3})
    ok(pb == 0.39 and pe == 3.36 and dy == 0.0, f"THYAO: KAP degerleri kullanilir ({pb},{pe},{dy})")
    ok(m["kaynak"] == "KAP" and m["fk_tur"] == "YILLIK" and m["donem"] == "2026/06", "kaynak etiketleri")
    ok(m["fk_donem"] == "2025/12", "F/K donemi meta'da")
    from scoring import _temel_alt_skor
    ok(_temel_alt_skor(pb, pe, dy) == 18, "THYAO Temel Skor 18/25 (eskiden 0)")


def test_birlestir_yahoo_pe_ara_donem():
    yf = {"_source": "yfinance", "pb_ratio": 0.4, "pe_ratio": 32.4, "div_yield": 0.03, "financial_currency": "TRY",
          "currency": "TRY"}
    pb, pe, dy, m = T.oranlari_birlestir(_kap(0.42, 509.0), yf, 100.0, {})
    ok(pe == 32.4 and m["fk_tur"] == "yfinance", "ara donem: Yahoo iz. 12A (KAP PD/DD ile dogrulanmis) KAP yillik F/K'dan once gelir")
    yf2 = dict(yf, pb_ratio=55.0)
    pb, pe, dy, m = T.oranlari_birlestir(_kap(1.2, 13.7), yf2, 100.0, {})
    ok(pe == 13.7 and m["fk_tur"] == "YILLIK", "Yahoo tutarsizsa (PD/DD 55 vs 1,2) Yahoo F/K reddedilir, KAP yillik kalir")
    pb, pe, dy, m = T.oranlari_birlestir(_kap(1.2, 13.7, tur="TTM"), yf, 100.0, {})
    ok(pe == 13.7 and m["fk_tur"] == "TTM", "KAP 12 aylik (TTM) varsa Yahoo'ya hic bakilmaz")


def test_birlestir_yahoo_fk_ic_tutarlilik():
    # ORZAX: halka arz 2026, KAP'ta yalniz 2026/06 var (yillik kar yok); Yahoo EPS 12,57 x 338,5M pay = 4,25 milyar,
    # Yahoo net kari 1,16 milyar -> oran 3,68: EPS ile net kar tutarsiz -> Yahoo F/K (5,85) alinmaz
    orz_kap = {"pb": 7.03, "pe": None, "pe_tur": None, "pe_durum": "yok", "donem": "2026/06", "kar_donem": "2026/06",
               "pay_adedi": 338.5e6, "notlar": []}
    orz_yf = {"_source": "yfinance", "pb_ratio": 7.03, "pe_ratio": 5.85, "eps": 12.57, "net_income": 1.1575e9,
              "div_yield": 0.0, "financial_currency": None, "currency": "TRY"}
    pb, pe, dy, m = T.oranlari_birlestir(orz_kap, orz_yf, 73.5, {})
    ok(pb == 7.03 and pe is None, f"ORZAX: tutarsiz Yahoo F/K alinmaz, F/K bos ({pe})")
    ok(m.get("fk_not") and "tutarsiz" in m["uyari"], f"kullaniciya neden F/K yok yazilir: {m['uyari']}")
    # tutarli TL raporlayan (GARAN benzeri oran ~0,99): Yahoo F/K kabul
    gar_kap = dict(orz_kap, pb=1.3, pay_adedi=4.2e9)
    gar_yf = dict(orz_yf, pb_ratio=1.3, pe_ratio=4.54, eps=28.45, net_income=1.204e11)
    pb, pe, dy, m = T.oranlari_birlestir(gar_kap, gar_yf, 129.0, {})
    ok(pe == 4.54 and m["fk_tur"] == "yfinance" and not m.get("fk_not"), "tutarli Yahoo F/K kabul edilir")
    # kanit yoksa (EPS veya net kar yok / zarar) reddetmek icin neden yok -> onceki davranis
    ok(T.yahoo_fk_tutarli_mi({"eps": 5.0}, 1e9) is None, "net kar yoksa None")
    ok(T.yahoo_fk_tutarli_mi({"eps": -1.0, "net_income": -1e9}, 1e9) is None, "zararda None")
    ok(T.yahoo_fk_tutarli_mi(orz_yf, None) is None, "pay adedi yoksa None")
    pb, pe, dy, m = T.oranlari_birlestir(gar_kap, {k: v for k, v in gar_yf.items() if k != "net_income"}, 129.0, {})
    ok(pe == 4.54, "net kar bilgisi yoksa mevcut dogrulama (PD/DD) gecerli sayilir")
    # tutarsiz Yahoo ama KAP son tam yil kari varsa KAP yillik F/K kullanilir
    kap_y = dict(orz_kap, pe=21.5, pe_tur="YILLIK", pe_durum="hesaplandi", kar_donem="2025/12")
    pb, pe, dy, m = T.oranlari_birlestir(kap_y, orz_yf, 73.5, {})
    ok(pe == 21.5 and m["fk_tur"] == "YILLIK" and not m.get("fk_not"), "tutarsiz Yahoo -> KAP yillik F/K")


def test_birlestir_yedek_yahoo():
    yf = {"_source": "yfinance", "pb_ratio": 2.0, "pe_ratio": 10.0, "div_yield": 0.05, "financial_currency": "TRY",
          "currency": "TRY"}
    pb, pe, dy, m = T.oranlari_birlestir({"notlar": ["KAP finansal sayfasi alinamadi"]}, yf, 10.0, {})
    ok((pb, pe, dy) == (2.0, 10.0, 0.05) and m["kaynak"] == "yfinance", "KAP yoksa tutarli Yahoo yedek")
    yf = {"_source": "yfinance", "pb_ratio": 230.0, "pe_ratio": 21.4, "financial_currency": "EUR", "currency": "TRY",
          "equity": 47.0, "eps": 504.0}
    pb, pe, dy, m = T.oranlari_birlestir({}, yf, 10795.0, {"EUR": 55.5})
    ok(pb is not None and 4.0 < pb < 4.3 and m["kaynak"] == "yfinance (kurla)", f"DOCO: EUR defter degeri kurla cevrilir ({pb})")
    ok(pe is None, "rapor para birimi farkliysa hisse basi kar para birimi dogrulanamaz: F/K alinmaz")
    pb, pe, dy, m = T.oranlari_birlestir({}, yf, 10795.0, {})
    ok(pb is None and pe is None, "kur yoksa Yahoo'nun 230'u asla kullanilmaz")


def test_sermaye_uyarisi():
    k = dict(_kap(), notlar=["sermaye 2026/06 doneminden sonra degismis: 1,400,000,000 -> 3,780,000,000 pay"])
    m = T.oranlari_birlestir(k, {}, 10.0, {})[3]
    ok(m["uyari"] and m["uyari"].startswith("Sermaye 2026/06") and "bedelli" in m["uyari"], f"sermaye degisimi uyarisi: {m['uyari']}")
    ok(T.oranlari_birlestir(_kap(), {}, 10.0, {})[3]["uyari"] is None, "sermaye degismediyse uyari yok")
    h = fin_html(["2025/12"], ["1000TL"], ["8.893.812"], ["1.000"], sermaye="1.400.000")
    r = T.hesapla("THYAO", 13.5, fin_html=h, genel_html=genel_html([("THYAO", "3.780.000.000,00")]))
    ok(any(n.startswith("sermaye ") for n in r["notlar"]), "hesapla: odenmis sermaye ile pay adedi %10'dan fazla ayriysa not")
    r = T.hesapla("THYAO", 13.5, fin_html=h, genel_html=genel_html([("THYAO", "1.400.000.000,00")]))
    ok(not any(n.startswith("sermaye ") for n in r["notlar"]), "ayniysa not yok")
    ok("| Not: X" in K.kaynak_notu({}, {"uyari": "X"}), "kaynak notuna eklenir")


def test_yf_ok_bayragi():
    ok(T.oranlari_birlestir(_kap(), {}, 10.0, {})[3]["yf_ok"] is False, "Yahoo bos -> yf_ok False")
    ok(T.oranlari_birlestir(_kap(), {"_source": "yfinance_error"}, 10.0, {})[3]["yf_ok"] is False, "Yahoo hata -> False")
    ok(T.oranlari_birlestir(_kap(), {"_source": "yfinance", "div_yield": 0.0}, 10.0, {})[3]["yf_ok"] is True, "Yahoo yanit verdi -> True")


# ── worker: temettu koruma ───────────────────────────────────
def test_temettu_koruma():
    import worker
    import datetime as dt
    with tempfile.TemporaryDirectory() as d:
        csv = os.path.join(d, "u.csv")
        pd.DataFrame([{"Ticker": "AAA", "Kategori": "BIST", "PB": 1.0, "PE": 5.0, "DY": 0.06, "Temel_Tarihi": "2026-10-08"},
                      {"Ticker": "BBB", "Kategori": "BIST", "PB": 1.0, "PE": 5.0, "DY": 0.06, "Temel_Tarihi": "2026-10-08"}]
                     ).to_csv(csv, index=False)
        bugun = dt.date(2026, 10, 9)
        taze = {"AAA": (0.4, 3.0, None), "BBB": (0.4, 3.0, None)}
        s, _t = worker._temel_veri_birlestir(taze, ["AAA", "BBB"], csv_path=csv, bugun=bugun, log=lambda *a: None,
                                             tohum_yolu=os.path.join(d, "yok.json"), dy_koru={"AAA"})
        ok(s["AAA"] == (0.4, 3.0, 0.06), "Yahoo bu gece yanit vermeyen hissede temettu onceki degerden korunur")
        ok(s["BBB"] == (0.4, 3.0, None), "Yahoo yanit verip temettu yoksa bos kalir (korunmaz)")
        s, _t = worker._temel_veri_birlestir(taze, ["AAA"], csv_path=csv, bugun=dt.date(2026, 12, 31), log=lambda *a: None,
                                             tohum_yolu=os.path.join(d, "yok.json"), dy_koru={"AAA"})
        ok(s["AAA"][2] is None, "30 gunden eski temettu korunmaz")


# ── worker.build() icindeki temel veri blogu (sahte KAP katmaniyla) ─
def test_worker_blogu():
    import textwrap
    import worker
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker.py"), encoding="utf-8").read().split("\n")
    a = next(i for i, l in enumerate(src) if l.startswith('    _bist_priced = [r["Ticker"]'))
    b = next(i for i, l in enumerate(src) if i > a and "# ── 3. Kripto" in l)
    blok = textwrap.dedent("\n".join(src[a:b]))
    rows = [{"Ticker": t, "Kategori": "BIST", "Son_Fiyat": p, "RSI": 55.0, "Ret1M": 3.0, "Vol": 30.0,
             "_score_adj": 0, "_dd_adj": 0} for t, p in [("THYAO", 287.5), ("GARAN", 150.0), ("ZZZZZ", 0.0)]]

    def sahte(tk, fy, kur):
        return ({"THYAO": (0.39, 3.36, 0.0), "GARAN": (1.1, 4.5, None)},
                {"THYAO": {"kaynak": "KAP", "donem": "2026/06", "fk_tur": "YILLIK", "fk_donem": "2025/12",
                           "uyari": "Sermaye degismis", "yf_ok": True},
                 "GARAN": {"kaynak": "yfinance", "donem": None, "fk_tur": "yfinance", "fk_donem": None, "uyari": None,
                           "yf_ok": True}})
    g = dict(vars(worker), all_rows=rows, fetch_bist_temel_kap_oncelikli=sahte, _temel_icin_kurlar=lambda: {},
             _temel_veri_birlestir=lambda t, k, **kw: (t, {x: "2026-10-09" for x in t}))
    exec(compile(blok, "blok", "exec"), g)
    th, ga, zz = rows
    ok((th["PB"], th["PE"], th["DY"]) == (0.39, 3.36, 0.0) and th["Temel_Kaynak"] == "KAP" and th["Temel_Donem"] == "2026/06",
       "THYAO satiri KAP degerleri + kaynak/donem")
    ok(th["Temel_FK_Tur"] == "YILLIK" and th["Temel_FK_Donem"] == "2025/12" and th["Temel_Uyari"] == "Sermaye degismis", "F/K ve uyari alanlari")
    from scoring import optima_score
    ok(th["Optima_Skor"] == optima_score(55.0, 3.0, 30.0, True, 0.39, 3.36, 0.0), "THYAO Optima skoru KAP girdileriyle hesaplanir")
    ok(th["Optima_Skor"] - optima_score(55.0, 3.0, 30.0, True, None, None, None) == 18, "temel puan katkisi tam 18 (eskiden 0)")
    ok(ga["Temel_Kaynak"] == "yfinance", "yedek kaynak etiketi")
    ok(zz["Optima_Skor"] == 0.0 and zz["Temel_Kaynak"] is None, "fiyati olmayan satir 0 ve kaynaksiz")


# ── onbellek, kota, zaman butcesi, devre kesici ──────────────
def _ham(tarih="2026-10-09", genel_ok=True):
    return {"tarih": tarih, "yok": None, "genel_ok": genel_ok, "para": "TL", "donem": "2026/06", "ozkaynak": 1000.0,
            "kar": ["2025/12", 100.0, "TL", "x"], "paylar": {"AAA": 10.0}, "notlar": []}


def test_yenilenecekler():
    import datetime as dt
    bugun = dt.date(2026, 10, 20)
    onb = {"T1": _ham("2026-10-19"), "T2": _ham("2026-10-01"), "T3": _ham("2026-10-10"), "T4": _ham("2026-10-19", genel_ok=False)}
    sonuc = T.yenilenecekler(["T1", "T2", "T3", "T4", "T5"], onb, bugun, yas_gun=7, kota=10)
    ok(sonuc == ["T5", "T4", "T2", "T3"], f"oncelik: kayitsiz > genel_ok=False > en eski; taze (T1) yok: {sonuc}")
    ok(T.yenilenecekler(["T1", "T2", "T3", "T4", "T5"], onb, bugun, kota=2) == ["T5", "T4"], "kota uygulanir")
    ok(T.yenilenecekler(["T1"], onb, bugun) == [], "taze kayit yenilenmez")
    onb["T6"] = {"tarih": "bozuk"}
    ok(T.yenilenecekler(["T6"], onb, bugun) == ["T6"], "tarihi okunamayan kayit eski sayilir")


def test_onbellek_dosyasi():
    with tempfile.TemporaryDirectory() as d:
        y = os.path.join(d, "o.json")
        ok(T.onbellek_yukle(y) == {}, "dosya yoksa bos")
        T.onbellek_kaydet(y, {"AAA": _ham()})
        ok(T.onbellek_yukle(y)["AAA"]["ozkaynak"] == 1000.0, "yaz/oku turu")
        open(y, "w").write("bozuk{")
        ok(T.onbellek_yukle(y) == {}, "bozuk dosya sessizce bos sayilir")


def test_ham_ve_hesapla_ham_ayni_sonuc():
    h = fin_html(["2024/12", "2025/12", "2026/06"], ["1000000TL"] * 3, ["679.887", "911.222", "1.018.517"],
                 ["113.378", "118.208", "18.864"], sermaye="1.380")
    g = genel_html([("THYAO", "1.380.000.000,00")])
    ham = T.ham_cek("THYAO", h, g, bugun="2026-10-09")
    ok(ham["tarih"] == "2026-10-09" and ham["donem"] == "2026/06" and ham["paylar"] == {"THYAO": 1.38e9}, f"ham kayit: {ham}")
    ok(ham["onceki_yil_kar"][0] == "2025/12" and ham["kar"][0] == "2026/06", "ara donemde onceki yil 12. ay kari saklanir")
    import json
    ham2 = json.loads(json.dumps(ham))          # onbellek gidis-donusu
    a = T.hesapla_ham("THYAO", 287.5, ham=ham2)
    b = T.hesapla("THYAO", 287.5, fin_html=h, genel_html=g)
    ok(a["pb"] == b["pb"] and a["pe"] == b["pe"] and a["pe_tur"] == "YILLIK", "onbellekten hesap = dogrudan hesap")
    ok(a["kap_tarihi"] == "2026-10-09", "ham verinin tarihi sonuca tasinir")
    ok(T.hesapla_ham("THYAO", 287.5, ham=None)["pb"] is None, "ham yoksa hesap yok (hata vermez)")
    ok(T.ham_cek("THYAO", fin_html="<html>" + "x" * 600 + "</html>", genel_html="x" * 600)["yok"], "tablo yoksa 'yok' notu (onbellege de yazilir)")
    ok(T.ham_cek("THYAO", fin_html=h, genel_html="<html>" + "x" * 600 + "</html>")["paylar"] == {}, "genel sayfada tablo yoksa bos paylar")


def test_worker_onbellek_kota_devre_kesici():
    import worker
    import datetime as dt
    cagri = []
    orj_h, orj_f, orj_b = T.ham_cek, worker.fetch_bist_fundamentals_parallel, worker.KAP_TEMEL_ZAMAN_BUTCESI_SN
    worker.fetch_bist_fundamentals_parallel = lambda tk, **kw: {}
    bugun = dt.date(2026, 10, 9)
    fy = {"AAA": 2.0, "BBB": 2.0}
    try:
        with tempfile.TemporaryDirectory() as d:
            y = os.path.join(d, "o.json")
            T.ham_cek = lambda t, *a, **k: (cagri.append(t) or _ham(k.get("bugun") or "2026-10-09"))
            s, m = worker.fetch_bist_temel_kap_oncelikli(["AAA", "BBB"], fy, {}, log=lambda *a: None, onbellek_yolu=y, bugun=bugun)
            ok(sorted(cagri) == ["AAA", "BBB"], "onbellek bos: iki hisse de KAP'tan cekilir")
            ok(set(T.onbellek_yukle(y)) == {"AAA", "BBB"}, "onbellek dosyaya yazildi")
            cagri.clear()
            s, m = worker.fetch_bist_temel_kap_oncelikli(["AAA", "BBB"], fy, {}, log=lambda *a: None, onbellek_yolu=y, bugun=bugun)
            ok(cagri == [], "taze onbellek: KAP'a HIC gidilmez")
            ok(m["AAA"]["kaynak"] == "KAP" and abs(s["AAA"][0] - (2.0 * 10.0) / 1000.0) < 1e-12, "PD/DD onbellekten guncel fiyatla hesaplanir")
            s2, _ = worker.fetch_bist_temel_kap_oncelikli(["AAA", "BBB"], {"AAA": 4.0, "BBB": 2.0}, {}, log=lambda *a: None, onbellek_yolu=y, bugun=bugun)
            ok(abs(s2["AAA"][0] - 0.04) < 1e-12, "fiyat degisince KAP'a gitmeden PD/DD degisir")
            # zaman butcesi: yeni hisse + sure dolmus
            cagri.clear()
            worker.KAP_TEMEL_ZAMAN_BUTCESI_SN = -1
            s, m = worker.fetch_bist_temel_kap_oncelikli(["AAA", "CCC"], {"AAA": 2.0, "CCC": 2.0}, {}, log=lambda *a: None, onbellek_yolu=y, bugun=bugun)
            ok(cagri == [] and m["CCC"]["kaynak"] == "" and m["AAA"]["kaynak"] == "KAP", "butce doldu: yeni hisse yarina kalir, onbellekli hisse etkilenmez")
            worker.KAP_TEMEL_ZAMAN_BUTCESI_SN = orj_b
            # ham_cek hata (None): eski kayit korunur
            y2 = os.path.join(d, "o2.json")
            T.onbellek_kaydet(y2, {"AAA": _ham("2026-09-01")})
            T.ham_cek = lambda t, *a, **k: None
            s, m = worker.fetch_bist_temel_kap_oncelikli(["AAA"], {"AAA": 2.0}, {}, log=lambda *a: None, onbellek_yolu=y2, bugun=bugun)
            ok(m["AAA"]["kaynak"] == "KAP" and T.onbellek_yukle(y2)["AAA"]["tarih"] == "2026-09-01", "KAP basarisizsa eski onbellek kaydi korunur ve kullanilir")
            # devre kesici: art arda hata sayaci
            def bozuk(t, *a, **k):
                cagri.append(t)
                with T._ist_kilit:
                    T._ist["ardisik"] += 100
                return None
            T.ham_cek = bozuk
            cagri.clear()
            y3 = os.path.join(d, "o3.json")
            worker.fetch_bist_temel_kap_oncelikli(["A1", "A2", "A3", "A4"], {}, {}, max_workers=1, log=lambda *a: None, onbellek_yolu=y3, bugun=bugun)
            ok(len(cagri) == 1, f"art arda hata esigi asilinca KAP adimi kesilir (cagri: {len(cagri)})")
    finally:
        T.ham_cek, worker.fetch_bist_fundamentals_parallel, worker.KAP_TEMEL_ZAMAN_BUTCESI_SN = orj_h, orj_f, orj_b
        T.istatistik_sifirla()


# ── detay tablosu ────────────────────────────────────────────
def test_detay_tablosu():
    raw = {"pe_ratio": None, "pb_ratio": None, "forward_pe": None, "_para_uyumsuz": "USD", "revenue": 5e10,
           "net_income": 2e9, "eps": -5.98, "equity": 15.9, "market_cap": 3.9e11, "_kap_available": True,
           "kap_equity": 1.018e12, "kap_donemler": {"kap_equity": "2026/06"}}
    temel = {"pb": 0.39, "pe": 3.36, "dy": 0.0, "kaynak": "KAP", "donem": "2026/06", "fk_tur": "YILLIK",
             "fk_donem": "2025/12"}
    d = K.fundamentals_to_display(raw, temel)
    ok("PD/DD Oranı (KAP, 2026/06)" in d and d["PD/DD Oranı (KAP, 2026/06)"] == "0.39", f"PD/DD satiri KAP etiketli: {list(d)}")
    ok("F/K Oranı (KAP, 2025/12 yıllık net kâr)" in d, "F/K satiri yillik ve donem etiketli")
    ok("PD/DD Oranı" not in d and "F/K Oranı (İz. 12A)" not in d, "Yahoo'nun ayni adli satirlari kalkar")
    ok(any(k.startswith("Ciro (Yıllık, yfinance, USD)") and v.endswith("$") for k, v in d.items()),
       "Yahoo tutar satirlari para birimiyle etiketlenir (USD)")
    ok(list(d).index("PD/DD Oranı (KAP, 2026/06)") < list(d).index("Net Kâr (yfinance, USD)"), "satir sirasi korunur")
    d2 = K.fundamentals_to_display({"pe_ratio": 9.0, "pb_ratio": 1.1, "revenue": 1e9, "_kap_available": False})
    ok("PD/DD Oranı" in d2 and "F/K Oranı (İz. 12A)" in d2, "temel verilmezse eski gorunum aynen kalir")
    n = K.kaynak_notu(raw, temel)
    ok(n.startswith("KAP (PD/DD ve F/K, 2026/06 bilançosu)") and "USD" in n, f"kaynak notu: {n}")
    ok(K.kaynak_notu({"_kap_available": False, "_kap_note": "x"}, None).startswith("yfinance"), "temel yoksa eski not")
    t = K.temel_satiri({"PB": 0.39, "PE": float("nan"), "DY": 0.0, "Temel_Kaynak": "KAP", "Temel_Donem": "2026/06"})
    ok(t["pb"] == 0.39 and t["pe"] is None and t["kaynak"] == "KAP", "temel_satiri NaN'i None yapar")


def test_piyasa_degeri_kap():
    # ORZAX: Yahoo marketCap 18,11 milyar (246,4M pay) - KAP pay adediyla 24,9 milyar; tabloda KAP degeri gorunur
    kap = {"pb": 7.03, "pe": None, "pe_tur": None, "pe_durum": "yok", "donem": "2026/06", "kar_donem": "2026/06",
           "pay_adedi": 338.5e6, "piyasa_degeri": 24.88e9, "notlar": []}
    pb, pe, dy, m = T.oranlari_birlestir(kap, {"_source": "yfinance", "pb_ratio": 7.03}, 73.5, {})
    ok(m["piyasa_degeri"] == 24.88e9, "KAP kaynakli PD/DD'de piyasa degeri meta'ya yazilir")
    pb, pe, dy, m = T.oranlari_birlestir({}, {"_source": "yfinance", "pb_ratio": 2.0, "financial_currency": "TRY"}, 10.0, {})
    ok(m["piyasa_degeri"] is None, "KAP yoksa piyasa degeri bos (Yahoo'nunki yazilmaz)")
    raw = {"market_cap": 18.11e9, "pe_ratio": None, "pb_ratio": None, "revenue": 5e9, "_kap_available": True}
    temel = K.temel_satiri({"PB": 7.03, "PE": float("nan"), "DY": 0.0, "Temel_Kaynak": "KAP", "Temel_Donem": "2026/06",
                            "Temel_PD": 24.88e9})
    ok(temel["pd"] == 24.88e9, "temel_satiri Temel_PD'yi okur")
    d = K.fundamentals_to_display(raw, temel)
    ok("Piyasa Değeri" not in d and "Piyasa Değeri (KAP pay adedi × fiyat)" in d, f"etiket KAP'li: {list(d)[:3]}")
    ok(d["Piyasa Değeri (KAP pay adedi × fiyat)"].startswith("24.88"), f"deger KAP'tan: {d['Piyasa Değeri (KAP pay adedi × fiyat)']}")
    ok(list(d)[0].startswith("Piyasa Değeri"), "satir sirasi korunur")
    d2 = K.fundamentals_to_display(raw, K.temel_satiri({"PB": 7.03, "Temel_Kaynak": "onceki derleme"}))
    ok("Piyasa Değeri" in d2, "Temel_PD yoksa Yahoo satiri aynen kalir")


if __name__ == "__main__":
    for ad, f in list(globals().items()):
        if ad.startswith("test_"):
            f()
    print(f"kap_temel testleri TAMAM ({_n['ok']} kontrol)")
    sys.exit(0)
