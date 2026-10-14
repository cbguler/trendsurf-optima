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


def genc_fon_mu(row) -> bool:
    """TEFAS satirinda Genc_Fon == True (CSV'den gelen deger bool ya da 'True' metni olabilir). Bilinmiyor/bos = False."""
    try:
        if str(row.get("Kategori")) != "TEFAS":
            return False
        v = row.get("Genc_Fon")
    except Exception:
        return False
    return v is True or str(v).strip().lower() == "true"


def yas_kademesi_satir(row):
    """v2.0.7.415: satirin yas kademesi - 0 (1 yildan genc), 1 (1-2 yil), 2 (2-3 yil), 3 (3 yil+) ya da None (bilinmiyor
    / kapsam disi). TEFAS: worker'in arsivden yazdigi 'Yas_Kademe' (yoksa eski 'Genc_Fon'=True -> 0). BIST/KRIPTO:
    'Gecmis_Gun'dan (BIST islem gunu, KRIPTO takvim gunu; esikler scoring.YAS_ESIKLERI)."""
    from scoring import yas_kademesi
    try:
        kat = str(row.get("Kategori"))
        if kat == "TEFAS":
            v = row.get("Yas_Kademe")
            try:
                k = int(float(v))
                if 0 <= k <= 3:
                    return k
            except (TypeError, ValueError):
                pass
            return 0 if genc_fon_mu(row) else None
        return yas_kademesi(kat, row.get("Gecmis_Gun"))
    except Exception:
        return None


def yas_kesinti_mi(row) -> bool:
    """Yas kademesi 1 veya 2 (1-3 yillik varlik): skor eksildi ama AL siniri/SINIRLI VERI seridi yok."""
    try:
        return int(float(row.get("Yas_Kademe"))) in (1, 2)
    except (TypeError, ValueError):
        return False


def _yuzde(k) -> int:
    from scoring import yas_carpani
    return int(round((1.0 - yas_carpani(k)) * 100))


def veri_sinirli_aciklama(row) -> str:
    """Kademe 0 (1 yildan genc) aciklamasi."""
    pct = _yuzde(0)
    if str(row.get("Kategori")) == "TEFAS" or genc_fon_mu(row):
        return ("Genç fon: yaklaşık bir yıldan kısa fiyat geçmişi var. Getiri, RSI ve volatilite kısa bir geçmişe "
                f"dayandığı için Optima Skor düşük güvenilirliktedir; skor %{pct} düşürülmüştür ve AL sinyali "
                "üretilmez, en fazla TUT İZLE verilir.")
    try:
        g = int(float(row.get("Gecmis_Gun")))
    except Exception:
        return ""
    if str(row.get("Kategori")) == "KRIPTO":
        return (f"Genç kripto varlık: BtcTurk'te {g} günlük fiyat geçmişi var (365 günden az, yaklaşık bir yıl). "
                f"Optima Skor kısa bir teknik geçmişe dayandığı için %{pct} düşürülmüştür; AL sinyali üretilmez, "
                "en fazla TUT İZLE verilir.")
    return (f"Yeni halka arz / kısa geçmiş: {g} işlem günü fiyat geçmişi var (260'tan az, yaklaşık bir yıl). "
            f"Optima Skor kısa bir teknik geçmişe dayandığı için %{pct} düşürülmüştür; AL sinyali üretilmez, "
            "en fazla TUT İZLE verilir.")


def yas_kesinti_aciklama(row) -> str:
    """Kademe 1-2 (1-3 yillik varlik) aciklamasi."""
    try:
        k = int(float(row.get("Yas_Kademe")))
    except (TypeError, ValueError):
        return ""
    if k not in (1, 2):
        return ""
    return (f"Görece genç varlık: fiyat geçmişi {k} ile {k + 1} yıl arasında. Kısa geçmiş skorun güvenilirliğini "
            f"azalttığı için Optima Skor %{_yuzde(k)} düşürülmüştür (1 yıl altı %{_yuzde(0)}, 1-2 yıl %{_yuzde(1)}, "
            f"2-3 yıl %{_yuzde(2)}, 3 yıl ve üzeri kesinti yok). Sinyal etiketi bu düşük skora göre verilir.")


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

    # v2.0.7.415 (14 Ekim 2026, Bahri'nin karari): YAS KADEMESI (BIST + KRIPTO + TEFAS, tek kural).
    # Kademe 0 (1 yildan genc): skor x0,70 + SINIRLI VERI bayragi (uyari seridi + AL sinyali siniri);
    # kademe 1 (1-2 yil): x0,80; kademe 2 (2-3 yil): x0,90; kademe 3 / bilinmeyen: dokunulmaz.
    # (378: BIST 260 gun siniri yalniz sinyali sinirliyordu; 392: genc fon x0,5. Ikisi bu kuralda birlesti.)
    # Yas bilgisi worker'dan gelir (Gecmis_Gun: BIST islem gunu / KRIPTO takvim gunu; Yas_Kademe: TEFAS arsivi).
    # TEFAS'in CSV'de skoru yoktur (sayfa hesaplar); burada ayni formulle (RSI, Ret1M, Vol) hesaplanip carpilir ki
    # liste/detay/Ana Sayfa/e-posta ayni sayiyi gorsun. Tedbirli/KAP UYARISI skoru zaten 0'dir (0 x k = 0).
    df["Veri_Sinirli"] = False
    df["Yas_Kesinti"] = 0
    try:
        from scoring import yas_carpani as _yc, optima_score as _os
        if "Gecmis_Gun" in df.columns:
            df["Gecmis_Gun"] = pd.to_numeric(df["Gecmis_Gun"], errors="coerce")
        else:
            df["Gecmis_Gun"] = pd.NA
        _fiyat_var = pd.to_numeric(df["Son_Fiyat"], errors="coerce").fillna(0) > 0
        _kd = pd.Series([yas_kademesi_satir(r) for r in df.to_dict("records")], index=df.index, dtype=object)
        _kd = _kd.where(_fiyat_var, None)
        df["Yas_Kademe"] = pd.to_numeric(_kd, errors="coerce")
        _k0 = df["Yas_Kademe"] == 0
        df["Veri_Sinirli"] = _k0.fillna(False).astype(bool)
        _kes = df["Yas_Kademe"].isin([0, 1, 2])
        if _kes.any():
            if "Optima_Skor" not in df.columns:
                df["Optima_Skor"] = pd.NA
            _sk = pd.to_numeric(df["Optima_Skor"], errors="coerce")
            _eksik = _kes & _sk.isna() & (df["Kategori"].astype(str) == "TEFAS")
            if _eksik.any():
                _sk[_eksik] = [
                    _os(float(r.get("RSI", 50) or 50), float(r.get("Ret1M", 0) or 0), vol=float(r.get("Vol", 30) or 30))
                    for r in df.loc[_eksik].to_dict("records")]
            _carp = df["Yas_Kademe"].map(lambda k: _yc(k) if pd.notna(k) else 1.0).astype(float)
            _sk = (_sk * _carp.where(_kes, 1.0)).round(1)
            df["Optima_Skor"] = _sk
            df["Yas_Kesinti"] = df["Yas_Kademe"].map(lambda k: _yuzde(k) if pd.notna(k) and int(k) in (0, 1, 2) else 0).astype(int)
            _dag = {int(k): int((df["Yas_Kademe"] == k).sum()) for k in (0, 1, 2)}
            print(f"[yas-kademe] skor kesintisi uygulandi (kademe 0/1/2 satir sayisi): {_dag}.")
    except Exception as _yk_err:
        print(f"[yas-kademe] atlandi: {_yk_err}")
    return df
