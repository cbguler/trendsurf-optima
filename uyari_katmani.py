# -*- coding: utf-8 -*-
"""
uyari_katmani.py - piyasa tedbiri / KAP riski / SINIRLI VERI katmaninin TEK kaynagi.

v2.0.7.380 (9 Ekim 2026): E-posta uc ayri yoldan gonderiliyordu (uygulamadaki buton -> load_universe,
tetikleyici uc nokta app.py, zamanlanmis emailer_standalone.py) ve bu katmani ya hic ya da yalniz skor
sifirlama olarak uyguluyordu; etiketi ise _sig_lbl(skor) hesapliyordu. Sonuc: uygulamada "KAP UYARISI"/
"KAP DIKKAT"/"ISLEME KAPALI" gorunen bir hisse e-postada AL olabilirdi. Bu modul load_universe'ten
BIREBIR tasinan mantigi (davranis degismedi) ve etiket secimini (get_signal_row) tek yerde toplar;
app.py, emailer.py, emailer_standalone.py hepsi buradan kullanir. streamlit'e BAGIMLI DEGIL.
"""
import pandas as pd

from scoring import get_signal, sinyal_sinirla
from piyasa_tedbir import SINYAL_KAPALI, SINYAL_TEDBIR, SINYAL_KISITLI
from kap_risk import SINYAL_KAP_AGIR, SINYAL_KAP_ORTA

TEDBIR_SINIF = {SINYAL_KAPALI: "sig-kapali", SINYAL_TEDBIR: "sig-tedbir", SINYAL_KISITLI: "sig-kisitli",
                SINYAL_KAP_AGIR: "sig-kap-agir", SINYAL_KAP_ORTA: "sig-kap-orta"}

SINYAL_RENK = {"sig-g": "#00732f", "sig-k": "#1a7a3a", "sig-t": "#8a5e00", "sig-s": "#c0451b", "sig-n": "#b71c1c",
               "sig-kapali": "#3b4350", "sig-tedbir": "#6a1b8a", "sig-kisitli": "#1f4e79",
               "sig-kap-agir": "#8e1b10", "sig-kap-orta": "#9a5b00"}


def tedbir_deger(row) -> str:
    """Satirdaki Piyasa_Tedbiri etiketi ('' = tedbir yok). row: Series/dict/None."""
    try:
        v = row.get("Piyasa_Tedbiri") if row is not None else None
    except Exception:
        return ""
    return v if isinstance(v, str) and v in TEDBIR_SINIF else ""


def veri_sinirli_mi(row) -> bool:
    """Satirda Veri_Sinirli bayragi (uyari_katmanini_uygula) var mi. row: Series/dict/None."""
    try:
        return bool(row.get("Veri_Sinirli")) if row is not None else False
    except Exception:
        return False


GENC_FON_SKOR_CARPANI = 0.5   # v2.0.7.392 (Bahri'nin karari): genc fonun Optima Skoru yariya iner


def genc_fon_mu(row) -> bool:
    """TEFAS satirinda Genc_Fon == True (CSV'den gelen deger bool ya da 'True' metni olabilir). Bilinmiyor/bos = False."""
    try:
        if str(row.get("Kategori")) != "TEFAS":
            return False
        v = row.get("Genc_Fon")
    except Exception:
        return False
    return v is True or str(v).strip().lower() == "true"


def veri_sinirli_aciklama(row) -> str:
    if genc_fon_mu(row):
        return ("Genç fon: yaklaşık bir yıldan kısa fiyat geçmişi var. Getiri, RSI ve volatilite kısa bir geçmişe "
                "dayandığı için Optima Skor düşük güvenilirliktedir; skor yarıya indirilmiştir ve AL sinyali "
                "üretilmez, en fazla TUT İZLE verilir.")
    try:
        g = int(float(row.get("Gecmis_Gun")))
    except Exception:
        return ""
    return (f"Yeni halka arz / kısa geçmiş: {g} işlem günü fiyat geçmişi var (260'tan az, yaklaşık bir yıl). "
            f"Optima Skor kısa bir teknik geçmişe dayanır; bu nedenle AL sinyali üretilmez, en fazla TUT İZLE verilir.")


def get_signal_row(row, score, rsi, trend):
    """get_signal() ile ayni donus (etiket, css sinifi); tedbirli varlikta tedbir etiketi,
    sinirli veride AL etiketleri TUT IZLE'ye indirilir."""
    t = tedbir_deger(row)
    if t:
        return t, TEDBIR_SINIF[t]
    lbl, cls = get_signal(score, rsi, trend)
    return sinyal_sinirla(lbl, cls, veri_sinirli_mi(row))


def uyari_katmanini_uygula(df):
    """Tedbir/KAP/SINIRLI VERI katmani (load_universe'ten tasindi). Sutunlar: Piyasa_Tedbiri,
    Tedbir_Aciklama, KAP_Bilgi, Veri_Sinirli (+Optima_Skor degisir: tedbirde 0, KAP UYARISI 0, KAP DIKKAT x0.5).
    ZATEN uygulanmis bir df'e (bu sutunlarin ucu de varsa) ikinci kez uygulanmaz - KAP carpani cift islenmesin.
    Her adim kendi icinde korunur; hata verirse ilgili adim atlanir, df doner."""
    if df is None:
        return df
    if {"Tedbir_Aciklama", "Veri_Sinirli", "KAP_Bilgi"} <= set(df.columns):
        return df
    _aktif_tedbirler = []
    try:
        from db import get_aktif_piyasa_tedbirleri
        _aktif_tedbirler = get_aktif_piyasa_tedbirleri()
        _sirket_adlari = [t["deger"] for t in _aktif_tedbirler if t["eslesme_turu"] == "SIRKET_ADI"]
        _tickerlar = {t["deger"] for t in _aktif_tedbirler if t["eslesme_turu"] == "TICKER"}
        if _sirket_adlari:
            _sirket_maskesi = (df["Kategori"] == "TEFAS") & df["Ad"].apply(
                lambda ad, _sl=_sirket_adlari: any(s in str(ad).upper() for s in _sl))
            if _sirket_maskesi.any():
                df.loc[_sirket_maskesi, "Optima_Skor"] = 0.0
                print(f"[piyasa-tedbir] {_sirket_maskesi.sum()} fon sirket-adi "
                      f"tedbiri kapsaminda - Optima Skor 0'a sabitlendi.")
        if _tickerlar:
            _ticker_maskesi = df["Ticker"].astype(str).str.upper().isin(_tickerlar)
            if _ticker_maskesi.any():
                df.loc[_ticker_maskesi, "Optima_Skor"] = 0.0
                print(f"[piyasa-tedbir] {_ticker_maskesi.sum()} varlik ticker "
                      f"tedbiri kapsaminda - Optima Skor 0'a sabitlendi.")
    except Exception as _pt_err:
        print(f"[piyasa-tedbir] atlandi: {_pt_err}")

    # v2.0.7.371: tedbirli varliklara sinyal etiketi (tedbirin TURUNE gore) + NAV'i sifir fonlar.
    # get_signal_row() bu iki kolonu okur; boylece tablo/detay/birlesik sinyal HEP AYNI olur.
    df["Piyasa_Tedbiri"] = ""
    df["Tedbir_Aciklama"] = ""
    try:
        from piyasa_tedbir import tedbir_isaretle, tedbir_aciklamasi, SINYAL_KAPALI as _SK
        _iz = tedbir_isaretle(df, locals().get("_aktif_tedbirler") or [])
        df["Piyasa_Tedbiri"] = _iz["Piyasa_Tedbiri"]
        df["Tedbir_Aciklama"] = _iz["Tedbir_Aciklama"]
        # TEFAS'ta fiyati 0'a dusen fon (NAV_Durumu=SIFIR): kural eslesmese bile islem kapali say
        if "NAV_Durumu" in df.columns:
            _nav0 = (df["Kategori"] == "TEFAS") & (df["NAV_Durumu"].astype(str).str.upper() == "SIFIR") \
                    & (df["Piyasa_Tedbiri"] == "")
            if _nav0.any():
                df.loc[_nav0, "Piyasa_Tedbiri"] = _SK
                df.loc[_nav0, "Tedbir_Aciklama"] = (
                    "TEFAS bu fonun fiyatını 0,0000 yayınlıyor (fon fiilen değersiz/kapalı). "
                    "Son sıfır olmayan fiyat gösterilmez; alım/satım sinyali üretilmez.")
        _tum = df["Piyasa_Tedbiri"] != ""
        if _tum.any():
            if "Optima_Skor" not in df.columns:
                df["Optima_Skor"] = pd.NA
            df.loc[_tum, "Optima_Skor"] = 0.0
    except Exception as _ts_err:
        print(f"[piyasa-tedbir] sinyal etiketi atlandi: {_ts_err}")

    # v2.0.7.373 (8 Ekim 2026, Bahri'nin bulgusu - ENERY): KAP bildirimlerinden cikarilan HISSE
    # BAZLI risk uyarilari (kap_risk_tarama.py -> kap_risk_uyari tablosu). AGIR -> sinyal "KAP UYARISI"
    # + Optima Skor 0; ORTA -> "KAP DIKKAT" + skor x0.5; BILGI (geri alim, bedelsiz...) -> sadece detay
    # seridinde bilgi. SPK tedbiri/islem kapali zaten etiketliyse onun etiketi KORUNUR (daha siki).
    df["KAP_Bilgi"] = ""
    try:
        from kap_risk import (kap_isaretle, SINYAL_KAP_AGIR, SINYAL_KAP_ORTA,
                              SEVIYE_AGIR, SEVIYE_ORTA)
        from db import get_aktif_kap_riskleri
        _kr = get_aktif_kap_riskleri()
        if _kr:
            _kap = kap_isaretle(df, _kr)
            df["KAP_Bilgi"] = _kap["KAP_Bilgi"]
            _kap_var = _kap["KAP_Seviye"] != ""
            if _kap_var.any():
                if "Optima_Skor" not in df.columns:
                    df["Optima_Skor"] = pd.NA
                _etiketsiz = _kap_var & (df["Piyasa_Tedbiri"] == "")
                for _sev, _sin, _not in (
                        (SEVIYE_AGIR, SINYAL_KAP_AGIR, "Optima Skor 0'a sabitlenmiştir; alım/satım sinyali üretilmez."),
                        (SEVIYE_ORTA, SINYAL_KAP_ORTA, "Optima Skor yarıya indirilmiştir; dikkatli olun.")):
                    _m = _etiketsiz & (_kap["KAP_Seviye"] == _sev)
                    if _m.any():
                        df.loc[_m, "Piyasa_Tedbiri"] = _sin
                        df.loc[_m, "Tedbir_Aciklama"] = (
                            "KAP bildirimi: " + _kap.loc[_m, "KAP_Aciklama"] + ". " + _not)
                        if _sev == SEVIYE_AGIR:
                            # v2.0.7.399: TEFAS'ta CSV skoru bos (sayfa hesaplar) -> NaN x 0 = NaN olurdu; acikca 0
                            df.loc[_m, "Optima_Skor"] = 0.0
                        else:
                            _sk = pd.to_numeric(df.loc[_m, "Optima_Skor"], errors="coerce")
                            # v2.0.7.399: bos skorlu TEFAS fonu icin once ayni formulle skoru uret, sonra x0,5
                            _eksik = _sk.isna() & (df.loc[_m, "Kategori"].astype(str).str.upper() == "TEFAS") \
                                     & (pd.to_numeric(df.loc[_m, "Son_Fiyat"], errors="coerce").fillna(0) > 0)
                            if _eksik.any():
                                from scoring import optima_score as _os_kap
                                _sk[_eksik] = [
                                    _os_kap(float(r.get("RSI", 50) or 50), float(r.get("Ret1M", 0) or 0),
                                            vol=float(r.get("Vol", 30) or 30))
                                    for r in df.loc[_m].loc[_eksik].to_dict("records")]
                            df.loc[_m, "Optima_Skor"] = (_sk * 0.5).round(1)
                print(f"[kap-risk] {int(_kap_var.sum())} hisse KAP risk uyarisi kapsaminda "
                      f"({int((_kap['KAP_Seviye'] == SEVIYE_AGIR).sum())} agir).")
    except Exception as _kr_err:
        print(f"[kap-risk] atlandi: {_kr_err}")

    # v2.0.7.378 (9 Ekim 2026, Bahri'nin karari): BIST hissesi 260 islem gununden az fiyat gecmisine sahipse
    # SINIRLI VERI bayragi (uyari seridi + AL sinyali siniri). Gecmis_Gun worker'dan gelir; yoksa/bilinmiyorsa
    # bayrak YOK. Skor degistirilmez.
    df["Veri_Sinirli"] = False
    try:
        from scoring import sinirli_veri_mi as _svm
        if "Gecmis_Gun" in df.columns:
            df["Gecmis_Gun"] = pd.to_numeric(df["Gecmis_Gun"], errors="coerce")
            df["Veri_Sinirli"] = [
                _svm(k, p, g) for k, p, g in zip(df["Kategori"], df["Son_Fiyat"], df["Gecmis_Gun"])]
        else:
            df["Gecmis_Gun"] = pd.NA
    except Exception as _vs_err:
        print(f"[veri-sinirli] atlandi: {_vs_err}")

    # v2.0.7.392 (Bahri'nin karari, 10 Ekim 2026): ~1 yildan genc TEFAS fonu icin (2) uyari seridi + AL siniri
    # (SINIRLI VERI bayragi) VE (3) Optima Skoru yariya iner. TEFAS'in CSV'de skoru yoktur (sayfa hesaplar); burada
    # ayni formulle (RSI, Ret1M, Vol) hesaplanip carpilir ki liste/detay/Ana Sayfa/e-posta ayni sayiyi gorsun.
    # Tedbirli fon zaten 0'dir (0 x 0,5 = 0). Genc_Fon bos/bilinmiyorsa HICBIR sey yapilmaz.
    try:
        if "Genc_Fon" in df.columns:
            _gf = pd.Series([genc_fon_mu(r) for r in df.to_dict("records")], index=df.index)
            _gf &= pd.to_numeric(df["Son_Fiyat"], errors="coerce").fillna(0) > 0
            if _gf.any():
                from scoring import optima_score as _os
                df.loc[_gf, "Veri_Sinirli"] = True
                if "Optima_Skor" not in df.columns:
                    df["Optima_Skor"] = pd.NA
                _sk = pd.to_numeric(df["Optima_Skor"], errors="coerce")
                _eksik = _gf & _sk.isna()
                if _eksik.any():
                    _sk[_eksik] = [
                        _os(float(r.get("RSI", 50) or 50), float(r.get("Ret1M", 0) or 0),
                            vol=float(r.get("Vol", 30) or 30))
                        for r in df.loc[_eksik].to_dict("records")]
                _sk[_gf] = (_sk[_gf] * GENC_FON_SKOR_CARPANI).round(1)
                df["Optima_Skor"] = _sk
                print(f"[genc-fon] {int(_gf.sum())} genc TEFAS fonu: SINIRLI VERI + skor x{GENC_FON_SKOR_CARPANI}.")
    except Exception as _gf_err:
        print(f"[genc-fon] atlandi: {_gf_err}")
    return df
