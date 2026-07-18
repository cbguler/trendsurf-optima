"""
dividend_engine.py — Temettü ve Pasif Gelir Hesaplama Motoru
TrendSurf Optima için tüm varlık sınıflarından beklenen geliri hesaplar.

Gelir türleri:
  BIST    → Temettü (yfinance dividendRate / dividendYield) — GERÇEK veri
  KRIPTO  → Staking / Proof-of-Stake getirisi (sabit oran tablosu) — GERÇEK veri
  TEFAS   → Fon getirisi (1A getiri × 12 bileşik = yıllıklandırma) — SPEKÜLATİF (trend)
  DÖVİZ   → Fiyat trendi (1A getiri × 12 bileşik = yıllıklandırma) — SPEKÜLATİF (trend)
  MADEN   → Fiyat trendi (1A getiri × 12 bileşik = yıllıklandırma) — SPEKÜLATİF (trend)

v2.0.7.23 - TEFAS/DÖVİZ/MADEN artık AYNI trend-bazlı yıllıklandırma yöntemini
kullanıyor (Bahri'nin talebi: "sadece TEFAS için olacaksa taraftar değilim").
Sadece BIST ve KRIPTO gerçek/sabit oranlı veriye dayanır; diğer üçü kısa
vadeli fiyat momentumunun basit bir projeksiyonudur, yatırım tavsiyesi değildir.
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional

# ─── SABİT TABLO: Kripto Staking APY ───────────────────────
# Kaynak: Ortalama piyasa değerleri (Haziran 2026 itibarıyla)
# Güncelleme: stakingrewards.com referanslı
KRIPTO_STAKING_APY = {
    "ETH":   0.035,   # %3.5  Ethereum 2.0 staking
    "SOL":   0.070,   # %7.0  Solana validator staking
    "DOT":   0.110,   # %11.0 Polkadot nominasyon
    "ADA":   0.040,   # %4.0  Cardano delegation
    "ATOM":  0.150,   # %15.0 Cosmos staking
    "NEAR":  0.090,   # %9.0  NEAR Protocol
    "TRX":   0.045,   # %4.5  TRON SR staking
    "BNB":   0.025,   # %2.5  BSC validator
    "MATIC": 0.040,   # %4.0  Polygon staking
    "POL":   0.040,   # %4.0  Polygon (yeni ad)
    "INJ":   0.120,   # %12.0 Injective staking
    "AVAX":  0.080,   # %8.0  Avalanche validation
    "OP":    0.000,   # %0.0  Optimism (staking yok)
    "ARB":   0.000,   # %0.0  Arbitrum (staking yok)
    "LTC":   0.000,   # %0.0  PoW — staking yok
    "DOGE":  0.000,   # %0.0  PoW — staking yok
    "XRP":   0.000,   # %0.0  PoS değil
    "BTC":   0.000,   # %0.0  PoW — staking yok
    "ICP":   0.060,   # %6.0  Internet Computer governance
    "SUI":   0.030,   # %3.0  Sui staking
    "TON":   0.035,   # %3.5  TON staking
    "LINK":  0.000,   # %0.0  LINK (staking yok)
}

# Türkiye'de BIST temettü verisi için ortalama getiri beklentisi
TCMB_POLITIKA_FAIZI = 0.46   # %46 (Haziran 2026 yaklaşık)
TL_FAIZ_REFERANS    = 0.42   # %42 mevduat referansı


@st.cache_data(ttl=86400, show_spinner=False)
@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_bist_dividend_raw(ticker: str) -> dict:
    """yfinance .info cagrisinin PAHALI/YAVAS kismini onbellekler.
    v2.0.7.84: current_price BURADA YOK, cunku fiyat surekli degisir -
    onbellek anahtarina fiyat eklenirse her fiyat guncellemesinde
    onbellek ISABETSIZ olur ve yavas .info cagrisi yine tekrar tekrar
    yapilir. Fiyata bagli hesap (temettu verimi) get_bist_dividend()'de,
    bu ONBELLEKSIZ (ama anlik/ucretsiz) fonksiyonun DISINDA yapilir."""
    raw = {"div_rate": None, "div_yield_yf": None, "ex_date": None,
           "frequency": None, "_error": None}
    try:
        import yfinance as yf
        info = yf.Ticker(f"{ticker}.IS").info
        raw["div_rate"]      = info.get("dividendRate")
        raw["div_yield_yf"]  = info.get("dividendYield")
        raw["ex_date"]       = info.get("exDividendDate")
        raw["frequency"]     = info.get("dividendFrequency")
    except Exception as e:
        raw["_error"] = str(e)[:40]
    return raw


def get_bist_dividend(ticker: str, current_price: float) -> dict:
    """
    yfinance'den BIST hissesi için temettü verilerini çeker.
    Returns: {div_per_share, div_yield, ex_date, frequency, annual_div}

    v2.0.7.84 - KRITIK PERFORMANS DUZELTMESI (Bahri'nin bulgusu: Ana
    Sayfa Butce Optimizasyonu tablosunun acilmasi VE herhangi bir
    checkbox tiklamasi cok yavas). Kok neden: yf.Ticker(...).info
    yfinance'in EN YAVAS cagrilarindan biri (genelde 1-5+ saniye/hisse),
    ve bu fonksiyon HICBIR ONBELLEK kullanmiyordu. Streamlit HER widget
    etkilesiminde (checkbox tiklama dahil) TUM sayfayi yeniden calistirdigi
    icin, bu yavas cagri HER tiklamada BIST sonuclarindaki her hisse icin
    TEKRAR TEKRAR yapiliyordu. Temettu verisi (yillik/ceyreklik odeme)
    gercekte cok NADIR degisir (ceyrekte bir, yilda bir) - 24 saatlik
    onbellek guvenli ve dogru, performans farkini dramatik sekilde
    (saniyelerden ~0'a) dusurur. Pahali .info cagrisi _fetch_bist_
    dividend_raw()'a tasindi (sadece ticker'a gore onbellekli); burada
    sadece HIZLI/anlik fiyata-bagli verim hesabi yapilir.
    """
    result = {
        "div_per_share":  0.0,
        "div_yield":      0.0,
        "ex_date":        None,
        "frequency":      None,
        "annual_div":     0.0,
        "source":         "—",
    }
    raw = _fetch_bist_dividend_raw(ticker)
    if raw.get("_error"):
        result["source"] = f"hata: {raw['_error']}"
        return result

    div_rate  = raw.get("div_rate")     # Yıllık temettü / hisse (₺)
    div_yield = raw.get("div_yield_yf") # Yıllık getiri oranı
    ex_date   = raw.get("ex_date")
    freq      = raw.get("frequency")    # 1=yıllık, 4=çeyreklik

    # Temizle ve hesapla
    if div_rate and float(div_rate) > 0:
        result["div_per_share"] = round(float(div_rate), 4)
        result["annual_div"]    = round(float(div_rate), 4)
        result["source"] = "yfinance"

    if div_yield and 0 < float(div_yield) <= 0.5:
        result["div_yield"] = round(float(div_yield) * 100, 2)
    elif result["div_per_share"] > 0 and current_price > 0:
        result["div_yield"] = round(result["div_per_share"] / current_price * 100, 2)

    if ex_date:
        import datetime
        try:
            result["ex_date"] = datetime.datetime.fromtimestamp(ex_date).strftime("%d.%m.%Y")
        except: pass

    result["frequency"] = {1: "Yıllık", 2: "Yarıyıllık", 4: "Çeyreklik"}.get(freq, "Yıllık")

    return result


def get_kripto_staking(ticker: str, current_price_usd: float) -> dict:
    """
    Kripto için staking/pasif gelir bilgilerini döner.
    Returns: {apy, daily_rate, source}
    """
    apy = KRIPTO_STAKING_APY.get(ticker.upper(), 0.0)
    return {
        "apy":       round(apy * 100, 1),    # %
        "daily_rate": round(apy / 365, 6),
        "stakeable":  apy > 0,
        "source":    "StakingRewards.com referanslı sabit tablo",
    }


def calc_portfolio_income(portfolio: list, df_universe: pd.DataFrame) -> pd.DataFrame:
    """
    Kullanıcının portföyündeki her pozisyon için beklenen yıllık geliri hesaplar.

    portfolio: [{"ticker": "THYAO", "adet": 100, "maliyet": 300}, ...]
    df_universe: optimized_universe.csv DataFrame'i

    Returns: DataFrame with columns:
      Ticker, Kategori, Adet, Güncel Fiyat, Toplam Değer,
      Gelir Türü, Yıllık Gelir/Birim, Yıllık Gelir (₺/$),
      Gelir Oranı (%), K/Z %, Toplam Getiri %
    """
    rows = []

    for pos in portfolio:
        ticker  = str(pos.get("ticker", "")).upper()
        adet    = float(pos.get("adet", 0))
        maliyet = float(pos.get("maliyet", 0))

        # Evren tablosundan fiyat ve kategori al
        match = df_universe[df_universe["Ticker"] == ticker]
        if match.empty:
            continue

        row      = match.iloc[0]
        cat      = str(row.get("Kategori", ""))
        cur_price = float(row.get("Son_Fiyat", 0))
        toplam   = round(cur_price * adet, 2)
        kz_pct   = round((cur_price / maliyet - 1) * 100, 2) if maliyet > 0 else 0.0

        gelir_turu  = "—"
        yillik_birim = 0.0
        yillik_try  = 0.0
        gelir_oran  = 0.0

        if cat == "BIST":
            # Temettü
            div_info = get_bist_dividend(ticker, cur_price)
            yillik_birim = div_info["div_per_share"]
            yillik_try   = round(yillik_birim * adet, 2)
            gelir_oran   = div_info["div_yield"]
            gelir_turu   = f"Temettü ({div_info['frequency']})"

        elif cat == "KRIPTO":
            # Staking
            stk = get_kripto_staking(ticker, cur_price)
            if stk["stakeable"]:
                gelir_oran   = stk["apy"]
                yillik_try   = round(toplam * stk["apy"] / 100, 2)
                yillik_birim = round(cur_price * stk["apy"] / 100, 4)
                gelir_turu   = f"Staking (%{stk['apy']:.1f} APY)"
            else:
                gelir_turu = "Staking yok (PoW)"

        elif cat == "TEFAS":
            # Fon getirisi — 1M return'ü annualize et
            ret1m = float(row.get("Ret1M", 0))
            if ret1m > 0:
                annualized  = round(((1 + ret1m/100)**12 - 1) * 100, 2)
                gelir_oran  = annualized
                yillik_try  = round(toplam * annualized / 100, 2)
                gelir_turu  = f"Fon getirisi (~%{annualized:.1f} yıllık)"
            else:
                gelir_turu = "Fon getirisi (veri yok)"

        elif cat in ("DOVIZ", "MADEN"):
            # v2.0.7.23 - TUTARLILIK: Bu fonksiyon (gercek portfoy geliri)
            # su an app.py'den cagrilmiyor ama tutarlilik icin ayni kural
            # burada da uygulaniyor - TEFAS'takiyle ayni trend-bazli
            # yillıklandirma, sadece BIST/KRIPTO'daki gercek sabit oranli
            # veriler ozel kalir.
            ret1m = float(row.get("Ret1M", 0))
            if ret1m > 0:
                gelir_oran = round(((1 + ret1m/100)**12 - 1) * 100, 2)
                yillik_try = round(toplam * gelir_oran / 100, 2)
                kat_lbl = "Döviz" if cat == "DOVIZ" else "Değerli Maden"
                gelir_turu = f"{kat_lbl} Fiyat Trendi (spekülatif)"
            else:
                kat_lbl = "Döviz" if cat == "DOVIZ" else "Değerli Maden"
                gelir_turu = f"{kat_lbl} (getiri verisi yok)"

        toplam_getiri = round(kz_pct + gelir_oran, 2)

        rows.append({
            "Ticker":             ticker,
            "Kategori":           cat,
            "Adet":               adet,
            "Güncel Fiyat":       cur_price,
            "Toplam Değer (₺)":   toplam,
            "Gelir Türü":         gelir_turu,
            "Yıllık Gelir/Birim": yillik_birim,
            "Yıllık Gelir (₺)":   yillik_try,
            "Gelir Oranı (%)":    gelir_oran,
            "K/Z (%)":            kz_pct,
            "Toplam Getiri (%)":  toplam_getiri,
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def calc_optimization_income(df_opt: pd.DataFrame, df_universe: pd.DataFrame,
                              budget: float) -> pd.DataFrame:
    """
    Optimizasyon tablosuna beklenen gelir sütunlarını ekler.
    df_opt: Ana sayfa önerilen dağılım tablosu
    Returns: Gelir sütunları eklenmiş df_opt
    """
    if df_opt.empty:
        return df_opt

    df_out = df_opt.copy()
    yillik_gelir_list = []
    gelir_oran_list   = []
    gelir_tur_list    = []

    for _, row in df_out.iterrows():
        ticker   = str(row.get("Ticker", ""))
        cat      = str(row.get("Kategori", ""))
        # v2.0.7.23 - IKI SUTUN ADI HATASI DUZELTILDI (Bahri'nin 11 Temmuz
        # bulgusu): (1) "Hedef Tutar (₺)" sutunu kaldirildi, "Tutar (₺)"
        # kullanilmali. (2) "Lot / Adet" sutunu app.py'de HICBIR ZAMAN bu
        # isimle var olmadi - gercek adi "Birim". Bu ikinci hata yuzunden
        # BIST temettu geliri (asagida lot*div_per_share) HER ZAMAN 0
        # cikiyordu (row.get varsayilan deger donuyordu) - yani onceki
        # "Tahmini Yillik Pasif Gelir" neredeyse tamamen TEFAS'in spekulatif
        # yillıklandirmasindan geliyordu, gercek temettu hic katkida
        # bulunmuyordu.
        tutar    = float(row.get("Tutar (₺)", 0))
        cur_p    = float(row.get("Emir Fiyatı", 0))
        lot      = int(row.get("Birim", 0))

        gelir = 0.0; oran = 0.0; tur = "—"

        if cat == "BIST" and cur_p > 0:
            d = get_bist_dividend(ticker, cur_p)
            gelir = round(d["div_per_share"] * lot, 2)
            oran  = d["div_yield"]
            tur   = "Temettü"

        elif cat == "KRIPTO":
            stk = get_kripto_staking(ticker, cur_p)
            if stk["stakeable"]:
                gelir = round(tutar * stk["apy"] / 100, 2)
                oran  = stk["apy"]
                tur   = f"Staking %{stk['apy']:.1f}"

        elif cat == "TEFAS":
            match = df_universe[df_universe["Ticker"] == ticker]
            if not match.empty:
                ret1m = float(match.iloc[0].get("Ret1M", 0))
                if ret1m > 0:
                    ann  = round(((1 + ret1m/100)**12 - 1) * 100, 2)
                    gelir = round(tutar * ann / 100, 2)
                    oran  = ann
                    tur   = "Fon Getirisi (trend, spekülatif)"

        elif cat in ("DOVIZ", "MADEN"):
            # v2.0.7.23 - TUTARLILIK (Bahri'nin talebi): "pasif gelir tahmini"
            # sadece TEFAS'a ozel bir yontem olmamali - gercek sabit oranli
            # bir gelir kaynagi olmayan TUM kategorilerde AYNI trend-bazli
            # yillıklandirma (1A getiri -> bileşik yıllık) tutarli sekilde
            # uygulanir. Boylece metodoloji BIST/KRIPTO (gercek veri) disinda
            # her yerde ayni mantikla calisir, TEFAS ozel bir durum olmaktan
            # cikar.
            match = df_universe[df_universe["Ticker"] == ticker]
            if not match.empty:
                ret1m = float(match.iloc[0].get("Ret1M", 0))
                if ret1m > 0:
                    ann  = round(((1 + ret1m/100)**12 - 1) * 100, 2)
                    gelir = round(tutar * ann / 100, 2)
                    oran  = ann
                    kat_lbl = "Döviz" if cat == "DOVIZ" else "Değerli Maden"
                    tur   = f"{kat_lbl} Fiyat Trendi (spekülatif)"

        yillik_gelir_list.append(gelir)
        gelir_oran_list.append(oran)
        gelir_tur_list.append(tur)

    df_out["Gelir Türü"]        = gelir_tur_list
    df_out["Gelir Oranı (%)"]   = gelir_oran_list
    df_out["Yıllık Gelir (₺)"]  = yillik_gelir_list

    return df_out


def portfolio_income_summary(df_income: pd.DataFrame) -> dict:
    """
    Toplam gelir özeti döner.
    """
    if df_income.empty:
        return {}
    return {
        "toplam_deger":       df_income["Toplam Değer (₺)"].sum(),
        "yillik_gelir_try":   df_income["Yıllık Gelir (₺)"].sum(),
        "ortalama_gelir_pct": df_income["Gelir Oranı (%)"].mean(),
        "max_gelir_varlik":   df_income.loc[df_income["Yıllık Gelir (₺)"].idxmax(), "Ticker"]
                              if not df_income.empty else "—",
        "temettu_try":        df_income[df_income["Kategori"]=="BIST"]["Yıllık Gelir (₺)"].sum(),
        "staking_try":        df_income[df_income["Kategori"]=="KRIPTO"]["Yıllık Gelir (₺)"].sum(),
        "fon_getiri_try":     df_income[df_income["Kategori"]=="TEFAS"]["Yıllık Gelir (₺)"].sum(),
    }