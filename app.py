"""
TrendSurf Optima — Streamlit Terminali (app.py)
Çalıştırma: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(
    page_title="TrendSurf Optima",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Stil ─────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0d0f14; }
  [data-testid="stSidebar"] { background: #12151c; border-right: 1px solid #1e2330; }
  h1, h2, h3 { color: #e2e8f0; font-family: 'Courier New', monospace; }
  .stDataFrame { font-size: 13px; }
  div[data-testid="metric-container"] { background:#1a1f2e; border:1px solid #2a3042; border-radius:6px; padding:10px; }
</style>
""", unsafe_allow_html=True)

# ── Kullanıcı Yönetimi ────────────────────────────────────────
USER_DB = "users.csv"
SESSION_FILE = "login_session.txt"

def load_users():
    if os.path.exists(USER_DB):
        try:
            return pd.read_csv(USER_DB, encoding="utf-8")
        except:
            pass
    df = pd.DataFrame([{"username": "bahri", "password": "optima2026"}])
    df.to_csv(USER_DB, index=False, encoding="utf-8")
    return df

def check_session():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated and os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            saved = f.read().strip()
        if saved in load_users()["username"].values:
            st.session_state.authenticated = True
            st.session_state.username = saved

def save_session(u):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        f.write(u)

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    st.session_state.authenticated = False
    st.session_state.pop("username", None)

check_session()

# ── GİRİŞ EKRANI ─────────────────────────────────────────────
if not st.session_state.authenticated:
    st.title("TrendSurf Optima")
    st.caption("Finansal Varlık Takip ve Sinyal Terminali")
    st.divider()
    c1, c2 = st.columns([1, 2])
    with c1:
        u = st.text_input("Kullanici Adi")
        p = st.text_input("Sifre", type="password")
        rem = st.checkbox("Beni Hatirla")
        if st.button("Giris Yap", use_container_width=True):
            df_u = load_users()
            ok = df_u[(df_u["username"] == u) & (df_u["password"] == p)]
            if not ok.empty:
                st.session_state.authenticated = True
                st.session_state.username = u
                if rem:
                    save_session(u)
                st.rerun()
            else:
                st.error("Hatali kullanici adi veya sifre.")
    st.stop()

# ── ANA TERMİNAL ─────────────────────────────────────────────
CSV_PATH = "optimized_universe.csv"

# Sütun başlıkları
COL_TICKER   = "Ticker"
COL_AD       = "Ad"
COL_KAT      = "Kategori"
COL_FIYAT    = "Son_Fiyat"

# Sinyal renk haritası
SIG_COLORS = {
    "GUCLU AL":      "#00ff88",
    "KADEMELI AL":   "#00ccff",
    "TUT IZLE":      "#ffd700",
    "KADEMELI SAT":  "#ff8800",
    "NET SAT":       "#ff3333",
}

def sig_color(sig: str) -> str:
    for k, v in SIG_COLORS.items():
        if k in sig.upper().replace("İ","I").replace("Ç","C").replace("Ğ","G").replace("Ü","U").replace("Ş","S").replace("Ö","O"):
            return v
    return "#aaaaaa"

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    last_loss = loss.iloc[-1]
    if last_loss == 0:
        return 100.0 if gain.iloc[-1] > 0 else 50.0
    rs = gain.iloc[-1] / last_loss
    return round(100 - (100 / (1 + rs)), 2)

def score_to_signal(score: float, rsi: float, trend: str) -> str:
    if score >= 85:
        return "GUCLU AL" if (trend == "YUKSELIS" and 35 <= rsi <= 65) else "KADEMELI AL"
    elif score >= 65:
        return "KADEMELI AL" if (trend == "YUKSELIS" or 35 <= rsi <= 65) else "TUT IZLE"
    elif score >= 40:
        return "KADEMELI SAT" if (trend == "DUSUS" and rsi > 70) else "TUT IZLE"
    else:
        return "NET SAT"

@st.cache_data(ttl=600, show_spinner=False)
def load_universe() -> pd.DataFrame:
    """optimized_universe.csv'yi yükler ve temel sütunları garantiler."""
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame()
    df = pd.read_csv(CSV_PATH, encoding="utf-8", on_bad_lines="skip")
    # Zorunlu sütunları kontrol et
    for col in [COL_TICKER, COL_KAT, COL_FIYAT]:
        if col not in df.columns:
            return pd.DataFrame()
    if COL_AD not in df.columns:
        df[COL_AD] = df[COL_TICKER]
    df[COL_FIYAT] = pd.to_numeric(df[COL_FIYAT], errors="coerce").fillna(0.0)
    df = df[df[COL_TICKER].astype(str).str.len() > 0].copy()
    df = df.reset_index(drop=True)
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def get_hist_data(ticker: str, category: str, period: str = "1y") -> pd.DataFrame:
    """Geçmiş veriyi data_pipeline üzerinden çeker (önbellek 1 saat)."""
    try:
        from data_pipeline import DataPipeline
        dp = DataPipeline()
        return dp.get_historical_data(ticker, category, period)
    except Exception as e:
        return pd.DataFrame()

def enrich_row(row) -> dict:
    """Tek varlık için RSI, trend ve sinyal hesaplar (geçmiş veri yoksa varsayılan)."""
    ticker = str(row[COL_TICKER])
    cat    = str(row[COL_KAT])
    price  = float(row[COL_FIYAT])

    hist = get_hist_data(ticker, cat, "1y")

    if not hist.empty and "Close" in hist.columns and len(hist) > 15:
        rsi   = calculate_rsi(hist["Close"])
        last  = hist["Close"].iloc[-1]
        ma20  = hist["Close"].rolling(20).mean().iloc[-1]
        trend = "YUKSELIS" if last >= ma20 else "DUSUS"
        ret_1m = round((hist["Close"].iloc[-1] / hist["Close"].iloc[-22] - 1) * 100, 2) if len(hist) >= 22 else 0.0
    else:
        rsi, trend, ret_1m = 50.0, "YUKSELIS", 0.0

    # Temel skor (basit yaklaşım — sinyaller.py ile entegre edilebilir)
    base = 60.0
    if trend == "YUKSELIS":
        base += 10
    if 35 <= rsi <= 65:
        base += 10
    if ret_1m > 5:
        base += 10
    elif ret_1m < -5:
        base -= 10

    signal = score_to_signal(base, rsi, trend)

    return {
        "RSI": rsi,
        "Trend": trend,
        "1A_Getiri%": ret_1m,
        "Skor": round(base, 1),
        "Sinyal": signal,
    }

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**Kullanici:** {st.session_state.username}")
    if st.button("Cikis Yap", use_container_width=True):
        clear_session()
        st.rerun()

    st.divider()
    st.subheader("Butce Optimizasyonu")
    budget = st.number_input(
        "Toplam Butce (TRY)",
        min_value=0.0, value=0.0, step=10000.0,
        help="0 girince tam evren tablosu gorunur"
    )
    risk_level = st.select_slider(
        "Risk Toleransi",
        options=["Cok Dusuk", "Dusuk", "Orta", "Yuksek", "Cok Yuksek"],
        value="Orta"
    )
    max_per_asset = st.slider("Varlik Basi Maks %", 5, 50, 25, step=5)

    st.divider()
    st.caption("Veri kaynagi: worker.py\nGrafik: yfinance / TEFAS API")

# ── VERİ YÜKLEMESİ ───────────────────────────────────────────
st.title("TrendSurf Optima Terminali")

df_uni = load_universe()

if df_uni.empty:
    st.error(
        f"'{CSV_PATH}' bulunamadi veya bozuk.\n\n"
        "Lutfen once terminalde calistirin:  `python worker.py`"
    )
    st.stop()

# ── KATEGORİ TABLARİ ─────────────────────────────────────────
categories = ["Tum Evren"] + sorted(df_uni[COL_KAT].unique().tolist())
tabs = st.tabs(categories)

for tab, cat in zip(tabs, categories):
    with tab:
        if cat == "Tum Evren":
            df_view = df_uni.copy()
        else:
            df_view = df_uni[df_uni[COL_KAT] == cat].copy()

        st.caption(f"{len(df_view)} varlik")

        # Büyük tablolar için detay hesaplamayı isteğe bağlı yap
        if len(df_view) > 200:
            st.info(
                f"Bu kategoride {len(df_view)} varlik var. "
                "RSI/Sinyal hesaplamasi yavas olabilir. "
                "Asagidan bir varlik secin."
            )
            show_detail = False
        else:
            show_detail = st.checkbox("RSI/Sinyal hesapla (yavas)", key=f"detail_{cat}", value=False)

        # Ham tablo (her zaman göster)
        display_cols = [COL_TICKER, COL_AD, COL_KAT, COL_FIYAT]
        existing = [c for c in display_cols if c in df_view.columns]
        st.dataframe(
            df_view[existing].rename(columns={
                COL_TICKER: "Ticker",
                COL_AD: "Ad",
                COL_KAT: "Kategori",
                COL_FIYAT: "Son Fiyat",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Seçili varlık detayı
        st.divider()
        st.subheader("Varlik Detay & Grafik")
        tickers_in_tab = df_view[COL_TICKER].tolist()
        selected = st.selectbox(
            "Varlik sec",
            options=tickers_in_tab,
            key=f"sel_{cat}",
            index=0 if tickers_in_tab else None,
        )

        if selected:
            sel_row = df_view[df_view[COL_TICKER] == selected].iloc[0]
            sel_cat = str(sel_row[COL_KAT])

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Ticker", selected)
            col_m2.metric("Son Fiyat", f"{sel_row[COL_FIYAT]:,.4f}")

            with st.spinner("Gecmis veri ve sinyaller hesaplaniyor..."):
                hist = get_hist_data(selected, sel_cat, "1y")
                enriched = enrich_row(sel_row)

            col_m3.metric("RSI (14)", enriched["RSI"])
            col_m4.metric("1A Getiri %", f"{enriched['1A_Getiri%']:+.2f}%")

            sig = enriched["Sinyal"]
            clr = sig_color(sig)
            st.markdown(
                f"<div style='background:#1a1f2e;border-left:4px solid {clr};"
                f"padding:12px 18px;border-radius:4px;margin:8px 0;'>"
                f"<span style='color:{clr};font-size:20px;font-weight:700;font-family:monospace'>"
                f"{sig}</span>"
                f"&nbsp;&nbsp;<span style='color:#888;font-size:13px'>"
                f"Trend: {enriched['Trend']} | Skor: {enriched['Skor']}</span></div>",
                unsafe_allow_html=True,
            )

            if not hist.empty and "Close" in hist.columns:
                st.line_chart(hist["Close"], use_container_width=True, height=280)
            else:
                st.warning("Bu varlik icin gecmis fiyat serisi yuklenemedi.")

# ── BUTCE OPTİMİZASYONU ──────────────────────────────────────
if budget > 0:
    st.divider()
    st.subheader(f"Butce Dagilimi — {budget:,.0f} TRY | Risk: {risk_level}")

    # Sadece fiyati olan ve AL sinyali (heuristik) beklenen varlıkları filtrele
    df_opt = df_uni[df_uni[COL_FIYAT] > 0].copy()

    # Risk seviyesine göre kategori ağırlıkları
    risk_weights = {
        "Cok Dusuk": {"TEFAS": 0.60, "DOVIZ": 0.20, "MADEN": 0.10, "BIST": 0.08, "KRIPTO": 0.02},
        "Dusuk":     {"TEFAS": 0.45, "DOVIZ": 0.20, "MADEN": 0.15, "BIST": 0.15, "KRIPTO": 0.05},
        "Orta":      {"TEFAS": 0.30, "DOVIZ": 0.15, "MADEN": 0.15, "BIST": 0.30, "KRIPTO": 0.10},
        "Yuksek":    {"TEFAS": 0.15, "DOVIZ": 0.10, "MADEN": 0.10, "BIST": 0.45, "KRIPTO": 0.20},
        "Cok Yuksek":{"TEFAS": 0.05, "DOVIZ": 0.05, "MADEN": 0.10, "BIST": 0.50, "KRIPTO": 0.30},
    }
    weights = risk_weights.get(risk_level, risk_weights["Orta"])

    opt_rows = []
    for cat_name, cat_weight in weights.items():
        df_cat = df_opt[df_opt[COL_KAT] == cat_name]
        if df_cat.empty:
            continue

        cat_budget = budget * cat_weight
        n = max(1, min(len(df_cat), int(max_per_asset * len(df_cat) / 100) + 1))
        # İlk N varlığı eşit dağıt (LP yerine basit eşit ağırlık — sinyallerle iyileştirilebilir)
        sample = df_cat.head(n)
        per_asset = cat_budget / len(sample)

        for _, row in sample.iterrows():
            price = float(row[COL_FIYAT])
            lot = int(per_asset / price) if price > 0 else 0
            opt_rows.append({
                "Kategori": cat_name,
                "Ticker": row[COL_TICKER],
                "Son Fiyat": price,
                "Hedef Tutar (TRY)": round(per_asset, 2),
                "Tahmini Lot/Adet": lot,
                "Kategori Payi %": round(cat_weight * 100, 1),
            })

    if opt_rows:
        df_result = pd.DataFrame(opt_rows)
        st.dataframe(df_result, use_container_width=True, hide_index=True)

        toplam = df_result["Hedef Tutar (TRY)"].sum()
        st.caption(f"Toplam tahsis: {toplam:,.2f} TRY / {budget:,.2f} TRY")
    else:
        st.warning("Fiyati olan varlik bulunamadi. Lutfen once worker.py calistirin.")
