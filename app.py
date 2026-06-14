"""TrendSurf Optima — Terminal v5 | streamlit run app.py"""
import streamlit as st, pandas as pd, numpy as np, os, json, base64, time

try:
    import plotly.graph_objects as go, plotly.express as px
    HAS_PLOTLY = True
except: HAS_PLOTLY = False

st.set_page_config(page_title="TrendSurf Optima", layout="wide",
                   initial_sidebar_state="expanded")

# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""<style>
.stApp,[data-testid="stAppViewContainer"],.main,.block-container{background:#f0f4f8!important;}
[data-testid="stSidebar"]{background:#d0e4ff!important;border-right:1px solid #e0eeff!important;}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small{color:#1b2a4a!important;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#2c3e6b!important;}
[data-testid="stSidebar"] .stSlider [data-testid="stMarkdownContainer"] p{color:#1b2a4a!important;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3{color:#1b2a4a!important;}
[data-testid="stSidebar"] hr{border-color:#e0eeff!important;}
[data-testid="stSidebar"] input{background:#e0eeff!important;color:#1b2a4a!important;border:1px solid #d0e4ff!important;}
[data-testid="stSidebar"] .stButton>button,[data-testid="stSidebar"] .stButton button,[data-testid="stSidebar"] button[kind="secondary"],[data-testid="stSidebar"] button[kind="primary"]{color:#ffffff!important;font-weight:700!important;}
[data-testid="stSidebar"] img{filter:brightness(1.15)!important;}
/* Ana içerik koyu metin */
.main p,.main span,.main div,.main label,.block-container p,
.block-container span,.block-container label{color:#1b2a4a!important;}
h1,h2,h3,h4{color:#1b2a4a!important;font-weight:700!important;}
h1{font-size:26px!important;} h2{font-size:20px!important;} h3{font-size:16px!important;}
/* Metrik kartları */
[data-testid="metric-container"]{background:#fff!important;border:1px solid #c8d6e8!important;
  border-radius:10px!important;padding:14px 18px!important;box-shadow:0 2px 8px rgba(27,42,74,.10)!important;}
[data-testid="stMetricLabel"]>div,[data-testid="stMetricLabel"] p{color:#4a5a7a!important;font-size:12px!important;font-weight:600!important;}
[data-testid="stMetricValue"]>div,[data-testid="stMetricValue"]{color:#1b2a4a!important;font-size:22px!important;font-weight:800!important;}
/* Tablolar */
[data-testid="stDataFrame"]{background:#fff!important;border-radius:8px!important;}
[data-testid="stDataFrame"] th{background:#eef2fa!important;color:#1b2a4a!important;font-weight:700!important;}
[data-testid="stDataFrame"] td{color:#1b2a4a!important;background:#fff!important;}
/* Butonlar — tüm butonlarda yazı beyaz */
.stButton>button{background:#1b2a4a!important;color:#fff!important;border:none!important;border-radius:6px!important;font-weight:700!important;}
.stButton>button p,.stButton>button span,.stButton>button div{color:#fff!important;}
.stButton>button:hover{background:#2c3e6b!important;color:#fff!important;}
div[data-testid="stButton"]>button{color:#fff!important;}
div[data-testid="stButton"]>button p{color:#fff!important;}
/* Ana içerik radio */
section.main [data-testid="stRadio"] label,
section.main [data-testid="stRadio"] label p,
section.main [data-testid="stRadio"] label span,
.block-container [data-testid="stRadio"] label,
.block-container [data-testid="stRadio"] label p{color:#1b2a4a!important;font-size:14px!important;font-weight:600!important;}
/* Sidebar radio */
[data-testid="stSidebar"] [data-testid="stRadio"] label,
[data-testid="stSidebar"] [data-testid="stRadio"] label p,
[data-testid="stSidebar"] [data-testid="stRadio"] label span{color:#1b2a4a!important;font-size:14px!important;}
/* Select / input */
[data-testid="stSelectbox"] label,[data-testid="stSelectbox"] p{color:#1b2a4a!important;font-weight:600!important;}
.stSelectbox>div>div{background:#fff!important;color:#1b2a4a!important;}
[data-testid="stNumberInput"] label,[data-testid="stNumberInput"] p{color:#1b2a4a!important;font-weight:600!important;}
.stNumberInput input{color:#1b2a4a!important;background:#fff!important;}
[data-testid="stSlider"] label,[data-testid="stSlider"] p{color:#1b2a4a!important;font-weight:600!important;}
[data-testid="stSidebar"] [data-testid="stNumberInput"] label,[data-testid="stSidebar"] [data-testid="stNumberInput"] p{color:#1b2a4a!important;}
[data-testid="stSidebar"] [data-testid="stSlider"] label,[data-testid="stSidebar"] [data-testid="stSlider"] p,[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stMarkdownContainer"] p,[data-testid="stSidebar"] .stSlider p,[data-testid="stSidebar"] .stSlider span{color:#1b2a4a!important;font-weight:600!important;}
[data-testid="stSidebar"] [data-testid="stSlider"] div[data-testid="stTickBarMin"],[data-testid="stSidebar"] [data-testid="stSlider"] div[data-testid="stTickBarMax"]{color:#2c3e6b!important;}
[data-testid="stSidebar"] [role="slider"]{background:#5b8dee!important;}
.stCaption,[data-testid="stCaptionContainer"] p{color:#5a6a8a!important;}
[data-testid="stSidebar"] .stCaption,[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p{color:#2c3e6b!important;}
[data-testid="stAlert"] p{color:#1b2a4a!important;}
[data-testid="stExpander"] summary p{color:#1b2a4a!important;font-weight:600!important;}
/* Özel bileşenler */
.ts-card{background:#fff;border:1px solid #c8d6e8;border-radius:10px;padding:18px 22px;
  margin-bottom:12px;box-shadow:0 2px 8px rgba(27,42,74,.08);}
.ts-sig{display:inline-block;padding:5px 16px;border-radius:16px;font-weight:700;font-size:14px;}
.sig-g{background:#e8f9ee!important;color:#00732f!important;border:2px solid #00732f!important;}
.sig-k{background:#e3f4e8!important;color:#1a7a3a!important;border:1px solid #1a7a3a!important;}
.sig-t{background:#fef9e6!important;color:#8a5e00!important;border:1px solid #c8890a!important;}
.sig-s{background:#fef0eb!important;color:#c0451b!important;border:1px solid #c0451b!important;}
.sig-n{background:#fde8e8!important;color:#b71c1c!important;border:2px solid #b71c1c!important;}
.top5-row{background:#fff;border:1px solid #c8d6e8;border-radius:8px;padding:8px 14px;margin:3px 0;
  display:flex;align-items:center;gap:10px;cursor:pointer;}
.top5-ticker{font-weight:700;color:#1b2a4a!important;font-size:14px;min-width:70px;}
.pos{color:#006d28!important;font-weight:700;} .neg{color:#b71c1c!important;font-weight:700;}
.kap-table{width:100%;border-collapse:collapse;}
.kap-table td{padding:7px 12px;border-bottom:1px solid #e0e8f4;font-size:13px;color:#1b2a4a!important;}
.kap-table td:first-child{color:#4a5a7a!important;font-weight:600;width:45%;}
/* Mobil responsive */
@media(max-width:768px){
  .block-container{padding:0.5rem 0.5rem!important;}
  h1{font-size:20px!important;} h2{font-size:16px!important;}
  [data-testid="metric-container"]{padding:8px 10px!important;}
  [data-testid="stMetricValue"]>div{font-size:16px!important;}
}
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SABITLER & YARDIMCILAR
# ══════════════════════════════════════════════════════════════
CSV_PATH, PORTFOLIO_FILE = "optimized_universe.csv", "portfolio.json"
EMAIL_CFG_FILE = "email_config.json"
PAGES = ["Ana Sayfa","Portföyüm","BIST","TEFAS","Döviz","Madenler","Kriptolar","Halka Arz","Temettü"]
CAT   = {"BIST":"BIST","TEFAS":"TEFAS","Döviz":"DOVIZ","Madenler":"MADEN","Kriptolar":"KRIPTO"}
SIG_COLORS = {"sig-g":"#00732f","sig-k":"#1a7a3a","sig-t":"#8a5e00","sig-s":"#c0451b","sig-n":"#b71c1c"}

# ── Yeni Auth sistemi (SQLite) ───────────────────────────────────────────────
from db import init_db
from auth import get_current_user, login_user, register_user, logout
from admin import render_admin_panel
init_db()

def _logo_html():
    for p in ["logo.png","Logo.png","LOGO.PNG"]:
        if os.path.exists(p):
            with open(p,"rb") as f:
                b64=base64.b64encode(f.read()).decode()
            return f'<div style="text-align:center;padding:6px 0 2px 0;"><img src="data:image/png;base64,{b64}" style="width:150px;"></div>'
    return '<div style="font-size:16px;font-weight:800;color:#fff;padding:8px 0;">TrendSurf Optima</div>'

SVG_LOGO = '<div style="font-size:15px;font-weight:800;color:#fff;">TrendSurf Optima</div>'

# ══════════════════════════════════════════════════════════════
# GIRIS / KAYIT EKRANI
# ══════════════════════════════════════════════════════════════
def render_auth_gate():
    # Giriş sayfasına özel CSS — input görünürlüğü
    st.markdown("""<style>
    [data-testid="stTextInput"] input {
        background:#ffffff!important;color:#1b2a4a!important;
        border:1.5px solid #c8d6e8!important;border-radius:6px!important;
        font-size:15px!important;padding:10px 14px!important;
    }
    [data-testid="stTextInput"] label p {
        color:#1b2a4a!important;font-weight:600!important;font-size:14px!important;
    }
    [data-testid="stTabs"] button p { color:#1b2a4a!important;font-weight:600!important; }
    [data-testid="stCheckbox"] label p { color:#1b2a4a!important; }
    </style>""", unsafe_allow_html=True)

    # Şifre sıfırlama token'ı URL'de varsa önce onu göster
    _reset_token = st.query_params.get("reset_token", "")
    if _reset_token:
        _,col,_ = st.columns([1,1.2,1])
        with col:
            st.subheader("Yeni Şifre Belirle")
            from auth_reset import verify_reset_token, reset_password
            _verify = verify_reset_token(_reset_token)
            if not _verify["ok"]:
                st.error(_verify["msg"])
            else:
                st.info(f"Hesap: {_verify['email']}")
                _np1 = st.text_input("Yeni Şifre", type="password", key="rp_new1", placeholder="En az 8 karakter")
                _np2 = st.text_input("Yeni Şifre (Tekrar)", type="password", key="rp_new2")
                if st.button("Şifremi Güncelle", use_container_width=True, key="btn_rp"):
                    if not _np1 or not _np2:
                        st.warning("Lütfen her iki alanı doldurun.")
                    elif _np1 != _np2:
                        st.error("Şifreler eşleşmiyor.")
                    else:
                        _res = reset_password(_reset_token, _np1)
                        if _res["ok"]:
                            st.success(_res["msg"])
                            st.query_params.clear()
                        else:
                            st.error(_res["msg"])
        st.stop()

    # ── Giriş ekranı: sol logo, sağ form ────────────────────
    col_logo, col_form = st.columns([1, 1.4])

    with col_logo:
        st.markdown("<div style='padding-top:40px'>", unsafe_allow_html=True)
        try: st.image("logo.png", width=200)
        except: st.markdown("## TrendSurf Optima")
        st.markdown(
            "<p style='color:#6c7a9c;font-size:13px;margin-top:8px'>"
            "Finansal Varlık Takip<br>ve Sinyal Terminali</p>",
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_form:
        st.markdown("<div style='padding-top:30px'>", unsafe_allow_html=True)
        tab_login, tab_register, tab_reset = st.tabs(["Giris Yap", "Kayit Ol", "Sifremi Unuttum"])

        with tab_login:
            email = st.text_input("E-posta", key="li_email", placeholder="ornek@gmail.com")
            pwd   = st.text_input("Sifre", type="password", key="li_pass", placeholder="Sifreniz")
            remember = st.checkbox("Beni Hatirla", key="li_remember")
            if st.button("Giris Yap", key="btn_login", use_container_width=True):
                if email and pwd:
                    res = login_user(email, pwd)
                    if res["ok"]:
                        st.session_state["auth_token"] = res["token"]
                        if remember:
                            st.session_state["remember_token"] = res["token"]
                        st.rerun()
                    else:
                        st.error(res["msg"])
                else:
                    st.warning("Lutfen tum alanlari doldurun.")

        with tab_register:
            full_name = st.text_input("Ad Soyad",   key="reg_name",   placeholder="Adiniz Soyadiniz")
            email_r   = st.text_input("E-posta",    key="reg_email",  placeholder="ornek@gmail.com")
            pass_r    = st.text_input("Sifre",      key="reg_pass",   type="password", placeholder="En az 8 karakter")
            pass_r2   = st.text_input("Sifre (Tekrar)", key="reg_pass2", type="password", placeholder="Sifreyi tekrar girin")
            if st.button("Kayit Ol", key="btn_register", use_container_width=True):
                if not all([full_name, email_r, pass_r, pass_r2]):
                    st.warning("Lutfen tum alanlari doldurun.")
                elif pass_r != pass_r2:
                    st.error("Sifreler eslesmiyor.")
                elif len(pass_r) < 8:
                    st.error("Sifre en az 8 karakter olmali.")
                else:
                    res = register_user(email_r, pass_r, full_name)
                    if res["ok"]: st.success(res["msg"])
                    else:         st.error(res["msg"])

        with tab_reset:
            st.markdown("E-posta adresinizi girin, şifre sıfırlama bağlantısı göndereceğiz.")
            reset_email = st.text_input("E-posta", key="rst_email", placeholder="ornek@gmail.com")
            if st.button("Sıfırlama Bağlantısı Gönder", use_container_width=True, key="btn_reset"):
                if not reset_email:
                    st.warning("Lütfen e-posta adresinizi girin.")
                else:
                    try:
                        from auth_reset import generate_reset_token
                        res = generate_reset_token(reset_email)
                        if res["ok"]:
                            st.success(res["msg"])
                        else:
                            st.error(res["msg"])
                    except Exception as _re:
                        st.error(f"Hata: {_re}")
        st.markdown("</div>", unsafe_allow_html=True)

# Beni Hatirla: onceki token ile otomatik giris
if "auth_token" not in st.session_state and "remember_token" in st.session_state:
    st.session_state["auth_token"] = st.session_state["remember_token"]

_cur_user = get_current_user()
if _cur_user is None:
    render_auth_gate()
    st.stop()

# ══════════════════════════════════════════════════════════════
# VERİ
# ══════════════════════════════════════════════════════════════
import json as _json

_TEFAS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tefas_cache")

def _load_tefas_cache(ticker: str, period: str) -> pd.DataFrame:
    """Yerel JSON cache'ten fon geçmişi oku."""
    fpath = os.path.join(_TEFAS_CACHE_DIR, f"{ticker}_{period}.json")
    if not os.path.exists(fpath):
        return pd.DataFrame()
    try:
        import time
        if time.time() - os.path.getmtime(fpath) > 86400:
            return pd.DataFrame()
        with open(fpath, "r") as f:
            data = _json.load(f)
        df = pd.DataFrame(data)
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()

def _save_tefas_cache(ticker: str, period: str, hist: pd.DataFrame):
    """Fon geçmişini yerel JSON cache'e yaz."""
    try:
        os.makedirs(_TEFAS_CACHE_DIR, exist_ok=True)
        fpath = os.path.join(_TEFAS_CACHE_DIR, f"{ticker}_{period}.json")
        data = hist[["Open","High","Low","Close"]].copy()
        data.index = data.index.strftime("%Y-%m-%d")
        data.to_json(fpath, orient="index")
    except Exception:
        pass


@st.cache_data(ttl=1800,show_spinner=False)
def load_universe():
    if not os.path.exists(CSV_PATH): return pd.DataFrame()
    df=pd.read_csv(CSV_PATH,on_bad_lines="skip")
    if not all(c in df.columns for c in ["Ticker","Kategori","Son_Fiyat"]): return pd.DataFrame()
    if "Ad" not in df.columns: df["Ad"]=df["Ticker"]
    if "YF_Symbol" not in df.columns: df["YF_Symbol"]=""
    if "RSI" not in df.columns: df["RSI"]=50.0
    if "Ret1M" not in df.columns: df["Ret1M"]=0.0
    df["Son_Fiyat"]=pd.to_numeric(df["Son_Fiyat"],errors="coerce").fillna(0)
    df["RSI"]=pd.to_numeric(df["RSI"],errors="coerce").fillna(50)
    df["Ret1M"]=pd.to_numeric(df["Ret1M"],errors="coerce").fillna(0)
    return df.reset_index(drop=True)

@st.cache_data(ttl=3600,show_spinner=False)
def _guess_tefas_kind(ticker: str, df_uni=None) -> str:
    """
    CSV'de TEFAS_Kind yoksa Excel dosyalarından fon türünü bul.
    Bulamazsa YAT döner.
    """
    # 1. CSV'den bak
    if df_uni is not None and "TEFAS_Kind" in df_uni.columns:
        match = df_uni[df_uni["Ticker"] == ticker]
        if not match.empty:
            k = str(match["TEFAS_Kind"].iloc[0]).strip()
            if k and k not in ("", "nan", "0"):
                return k

    # 2. Excel dosyalarından ara
    import glob
    kind_map = {"Menkul_Kiymet": "YAT", "Emeklilik": "EMK", "Borsa_Yatirim": "BYF"}
    for fpath in sorted(glob.glob("*.xlsx")):
        if "KAP" in fpath.upper():
            continue
        kind = "YAT"
        for key, val in kind_map.items():
            if key in fpath:
                kind = val
                break
        try:
            import pandas as pd
            df_xl = pd.read_excel(fpath, header=4, usecols=["Fon Kodu"])
            codes = df_xl["Fon Kodu"].dropna().astype(str).str.upper().str.strip().tolist()
            if ticker.upper() in codes:
                return kind
        except Exception:
            continue
    return "YAT"


@st.cache_data(ttl=86400, show_spinner="Fon verisi yukleniyor...")
def _fetch_tefas_hist_cached(ticker: str, kind: str, period: str) -> pd.DataFrame:
    """pytefas ile geçmiş veri — 1 saat cache."""
    try:
        from pytefas import Crawler
        from datetime import datetime, timedelta
        period_days = {"1mo": 35, "3mo": 95, "6mo": 190,
                       "1y": 370, "3y": 1100, "5y": 1830}
        days = period_days.get(period, 370)
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end   = datetime.now().strftime("%Y-%m-%d")
        c = Crawler()
        for try_kind in [kind] + [k for k in ["YAT","EMK","BYF"] if k != kind]:
            df = c.fetch(start=start, end=end, kind=try_kind, fund_code=ticker)
            if df.empty:
                continue
            # Sütun normalize
            col_price = next((c2 for c2 in df.columns
                              if c2.lower() in ("price","fiyat")), None)
            col_date  = next((c2 for c2 in df.columns
                              if c2.lower() in ("date","tarih")), None)
            if not col_price or not col_date:
                continue
            df = df.rename(columns={col_price: "Close", col_date: "date"})
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).set_index("date").sort_index()
            df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
            df = df.dropna(subset=["Close"])
            if len(df) < 5:
                continue
            df["Open"]  = df["Close"].shift(1).fillna(df["Close"])
            df["High"]  = df[["Open","Close"]].max(axis=1)
            df["Low"]   = df[["Open","Close"]].min(axis=1)
            return df[["Open","High","Low","Close"]]
    except Exception:
        pass
    return pd.DataFrame()


def get_hist(ticker, yf_symbol, category, period="1y"):
    # TEFAS — önce yerel JSON cache, sonra pytefas, son çare sentetik
    if category == "TEFAS":
        # 1. Yerel cache dene (worker.py tarafından oluşturulur)
        try:
            cache_hist = _load_tefas_cache(ticker, period)
            if cache_hist is not None and not cache_hist.empty and len(cache_hist) >= 5:
                return cache_hist
        except Exception:
            pass
        # 2. pytefas ile gerçek veri (cache'li, yavaş ama doğru)
        try:
            df_u = load_universe()
            kind = _guess_tefas_kind(ticker, df_u)
            hist = _fetch_tefas_hist_cached(ticker, kind, period)
            if hist is not None and not hist.empty and len(hist) >= 5:
                # Başarılı veriyi cache'e yaz (sonraki açılışta hızlı)
                _save_tefas_cache(ticker, period, hist)
                return hist
        except Exception:
            pass
        # 3. Sentetik fallback
        try:
            from tefas_client import _synthetic_from_excel
            hist = _synthetic_from_excel(ticker, period)
            if hist is not None and not hist.empty:
                return hist
        except Exception:
            pass
        return pd.DataFrame()

    # Döviz/Maden/Kripto/BIST için doğru sembol
    from data_pipeline import _format_yf_symbol
    # _format_yf_symbol her zaman doğru sembolü üretir
    sym = _format_yf_symbol(ticker, category)
    # Maden futures için CSV'deki =F sembolü varsa onu kullan
    if yf_symbol and yf_symbol.strip() and "=F" in str(yf_symbol):
        sym = yf_symbol.strip()

    try:
        import yfinance as yf
        h = yf.Ticker(sym).history(period=period, auto_adjust=True)
        if not h.empty and len(h) >= 5:
            return h[["Open", "High", "Low", "Close"]].dropna()
    except Exception:
        pass
    return pd.DataFrame()

def calc_rsi(s,p=14):
    s=s.dropna()
    if len(s)<p+1: return 50.0
    d=s.diff(); g=d.where(d>0,0.0).rolling(p).mean()
    l=(-d.where(d<0,0.0)).rolling(p).mean()
    ll=l.iloc[-1]
    if ll==0: return 100.0
    return round(100-(100/(1+g.iloc[-1]/ll)),1)

def calc_macd(s):
    if len(s)<26: return 0.0,0.0
    m=s.ewm(span=12).mean()-s.ewm(span=26).mean()
    return round(float(m.iloc[-1]),4),round(float(m.ewm(span=9).mean().iloc[-1]),4)

def optima_score(rsi,ret1m,vol=30.0,has_fundamental=False,pb=None,pe=None,dy=None):
    """
    Optima Skoru (0-100): teknik + temel faktörler.
    Ağırlıklar: RSI Zonu 25%, Momentum 35%, Volatilite 15%, Temel 25%.
    """
    # RSI Zonu (0-25)
    if 40<=rsi<=60: rsi_s=25
    elif 35<=rsi<=65: rsi_s=18
    elif 30<=rsi<35 or 65<rsi<=70: rsi_s=10
    else: rsi_s=0

    # Momentum / Getiri (0-35)
    if ret1m>=30: mom=35
    elif ret1m>=20: mom=30
    elif ret1m>=10: mom=24
    elif ret1m>=5: mom=18
    elif ret1m>=0: mom=10
    elif ret1m>=-5: mom=4
    else: mom=0

    # Volatilite cezası (0-15; düşük vol = yüksek puan)
    if vol<20: vol_s=15
    elif vol<35: vol_s=10
    elif vol<55: vol_s=5
    else: vol_s=0

    # Temel analiz (0-25) — yfinance'den gelen F/K ve PD/DD
    fund_s=0
    if has_fundamental:
        if pe and 0<float(pe)<12: fund_s+=10
        elif pe and 0<float(pe)<25: fund_s+=5
        if pb and 0<float(pb)<1.5: fund_s+=8
        elif pb and 0<float(pb)<3: fund_s+=4
        if dy and float(dy)>0.08: fund_s+=7
        elif dy and float(dy)>0.04: fund_s+=3
        return min(100, round(rsi_s+mom+vol_s+fund_s, 1))

    # Temel analiz verisi YOKSA: 75 üzerinden hesaplanan skoru 100'e normalize et
    # Böylece TEFAS/Kripto/Döviz/Maden varlıkları BIST ile adil karşılaştırılır
    raw = rsi_s + mom + vol_s          # max 75
    return min(100, round(raw * (100.0 / 75.0), 1))

def get_signal(score,rsi,trend):
    if score>=80: lbl,cls=("GÜÇLÜ AL","sig-g") if trend=="YUKSELIS" and 35<=rsi<=65 else ("KADEMELİ AL","sig-k")
    elif score>=60: lbl,cls=("KADEMELİ AL","sig-k") if (trend=="YUKSELIS" or 35<=rsi<=65) else ("TUT İZLE","sig-t")
    elif score>=40: lbl,cls=("KADEMELİ SAT","sig-s") if trend=="DUSUS" and rsi>70 else ("TUT İZLE","sig-t")
    else: lbl,cls=("NET SAT","sig-n")
    return lbl,cls

def enrich(row,period="1y"):
    """
    Varlık analizi.
    TUTARLILIK KURALI: Optima Skoru ve sinyal HER ZAMAN CSV'deki
    (worker.py'nin yazdığı) RSI / Ret1M / Vol değerlerinden hesaplanır —
    optimizasyon tablosuyla birebir aynı.
    Grafik ve güncel teknik görünüm (MA20 trendi, MACD) histten gelir.
    """
    t=str(row["Ticker"]); cat=str(row["Kategori"]); yfs=str(row.get("YF_Symbol",""))
    # CSV verileri — skorun TEK kaynağı
    csv_rsi   = float(row.get("RSI",50))
    csv_ret1m = float(row.get("Ret1M",0))
    csv_vol   = float(row.get("Vol",30) or 30)
    score     = optima_score(csv_rsi, csv_ret1m, csv_vol)

    hist=get_hist(t,yfs,cat,period)
    trend,ret3m,macd_v,macd_s="YUKSELIS" if csv_ret1m>=0 else "DUSUS",0.0,0.0,0.0
    live_rsi, live_vol = csv_rsi, csv_vol
    if not hist.empty:
        pr=hist["Close"].dropna() if "Close" in hist.columns else hist.iloc[:,0].dropna()
        live_rsi=calc_rsi(pr); last=float(pr.iloc[-1])
        ma20=float(pr.rolling(20).mean().iloc[-1]) if len(pr)>=20 else last
        trend="YUKSELIS" if last>=ma20 else "DUSUS"
        ret3m=round((last/float(pr.iloc[-66])-1)*100,2) if len(pr)>=66 else 0.0
        live_vol=round(float(pr.pct_change().std()*np.sqrt(252)*100),1) if len(pr)>5 else csv_vol
        macd_v,macd_s=calc_macd(pr)
    return dict(hist=hist,rsi=csv_rsi,trend=trend,ret1m=csv_ret1m,ret3m=ret3m,
                vol=csv_vol,score=score,macd=macd_v,macd_sig=macd_s,
                live_rsi=live_rsi,live_vol=live_vol)

def clickable_table(df_show, key, sel_ticker=""):
    """on_select ile satır seçimi — checkbox Streamlit'in kendi davranışı."""
    col_cfg = {}
    for c in df_show.columns:
        if c in ("Son Fiyat","Fiyat","Emir Fiyati"):
            col_cfg[c] = st.column_config.NumberColumn(format="%.4f")
        elif c in ("1A Getiri%","1A%","Ret1M"):
            col_cfg[c] = st.column_config.NumberColumn(format="%.2f")
        elif c in ("Optima Skor","Skor"):
            col_cfg[c] = st.column_config.NumberColumn(format="%.1f")
        elif c == "RSI":
            col_cfg[c] = st.column_config.NumberColumn(format="%.1f")

    evt = st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config=col_cfg,
        key=key,
    )
    if evt and hasattr(evt, "selection") and evt.selection.rows:
        idx = evt.selection.rows[0]
        if idx < len(df_show):
            return str(df_show.iloc[idx]["Ticker"])
    return sel_ticker


def candle_fig(hist, ticker):
    if not HAS_PLOTLY or hist.empty: return None
    has_ohlc = all(c in hist.columns for c in ["Open","High","Low","Close"])
    use_candle = has_ohlc and len(hist) >= 5 and (hist["High"] - hist["Low"]).sum() > 0
    fig = go.Figure()
    if use_candle:
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist.Open, high=hist.High,
            low=hist.Low, close=hist.Close, name=ticker,
            increasing_line_color="#00732f", decreasing_line_color="#b71c1c",
            increasing_fillcolor="#e8f9ee", decreasing_fillcolor="#fde8e8"))
        if len(hist) >= 20:
            fig.add_trace(go.Scatter(x=hist.index, y=hist.Close.rolling(20).mean(),
                name="MA20", line=dict(color="#1b2a4a", width=1.5, dash="dot")))
        if len(hist) >= 50:
            fig.add_trace(go.Scatter(x=hist.index, y=hist.Close.rolling(50).mean(),
                name="MA50", line=dict(color="#f4a300", width=1.5, dash="dash")))
    else:
        col = "Close" if "Close" in hist.columns else hist.columns[0]
        if hist[col].nunique() < 2:
            return None
        fig.add_trace(go.Scatter(x=hist.index, y=hist[col], name=ticker,
            line=dict(color="#1b2a4a", width=2),
            fill="tozeroy", fillcolor="rgba(27,42,74,.07)"))
    # Y ekseni — fiyat aralığını otomatik ayarla (normalize 0-100 görünümünü engelle)
    close_col = hist["Close"] if "Close" in hist.columns else hist.iloc[:, 0]
    y_min = float(close_col.min()) * 0.995
    y_max = float(close_col.max()) * 1.005
    fig.update_layout(height=380, paper_bgcolor="#fff", plot_bgcolor="#fafbff",
        xaxis=dict(showgrid=True, gridcolor="#eef0f7", rangeslider=dict(visible=False)),
        yaxis=dict(showgrid=True, gridcolor="#eef0f7",
                   range=[y_min, y_max], autorange=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=30, b=0))
    return fig



def _simple_portfolio(portfolio, df_uni):
    """Gelir hesabı yapılamadığında sade portföy tablosu."""
    rows = []
    for pos in portfolio:
        tkr = pos["ticker"]
        match = df_uni[df_uni["Ticker"] == tkr]
        cur = float(match["Son_Fiyat"].iloc[0]) if not match.empty else 0.0
        mal = float(pos["maliyet"]); ad = float(pos["adet"])
        rows.append({
            "Ticker": tkr, "Adet": ad, "Alış": mal, "Güncel": cur,
            "K/Z %": round((cur/mal-1)*100, 2) if mal > 0 else 0.0,
            "K/Z (₺)": round((cur-mal)*ad, 2),
            "Toplam": round(cur*ad, 2),
        })
    if rows:
        df_p = pd.DataFrame(rows)
        st.dataframe(df_p, use_container_width=True, hide_index=True)
        c1, c2 = st.columns(2)
        c1.metric("Toplam Değer", f"{df_p['Toplam'].sum():,.2f} ₺")
        c2.metric("Toplam K/Z", f"{df_p['K/Z (₺)'].sum():+,.2f} ₺")

def load_portfolio(user_id: int = None) -> list:
    """
    Kullanıcıya özel portföyü SQLite'tan çeker.
    Eski portfolio.json varsa ilk çalıştırmada migrate eder.
    """
    from db import get_conn
    if user_id is None:
        user_id = (_cur_user or {}).get("id")
    if not user_id:
        return []

    # Eski JSON'dan tek seferlik migration
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE) as f:
                old_data = json.load(f)
            if old_data:
                conn = get_conn()
                existing = conn.execute(
                    "SELECT COUNT(*) FROM portfolio WHERE user_id=?", (user_id,)
                ).fetchone()[0]
                if existing == 0:
                    df_u = load_universe()
                    for pos in old_data:
                        t = str(pos.get("ticker","")).strip()
                        if not t: continue
                        cat = "BIST"
                        if not df_u.empty:
                            m = df_u[df_u["Ticker"]==t]
                            if not m.empty:
                                cat = str(m["Kategori"].iloc[0])
                        conn.execute(
                            "INSERT INTO portfolio (user_id,asset_type,ticker,quantity,avg_cost) "
                            "VALUES (?,?,?,?,?)",
                            (user_id, cat, t,
                             float(pos.get("adet",0)),
                             float(pos.get("maliyet",0)))
                        )
                    conn.commit()
                conn.close()
            os.rename(PORTFOLIO_FILE, PORTFOLIO_FILE + ".migrated")
        except Exception:
            pass

    conn = get_conn()
    rows = conn.execute(
        "SELECT id, asset_type, ticker, quantity, avg_cost, note, added_at "
        "FROM portfolio WHERE user_id=? ORDER BY added_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_portfolio_item(ticker: str, adet: float, maliyet: float,
                        asset_type: str = "BIST", note: str = "") -> bool:
    from db import get_conn
    user_id = (_cur_user or {}).get("id")
    if not user_id: return False
    conn = get_conn()
    conn.execute(
        "INSERT INTO portfolio (user_id,asset_type,ticker,quantity,avg_cost,note) "
        "VALUES (?,?,?,?,?,?)",
        (user_id, asset_type, ticker.strip().upper(), adet, maliyet, note)
    )
    conn.commit(); conn.close()
    return True


def delete_portfolio_item(item_id: int) -> bool:
    from db import get_conn
    user_id = (_cur_user or {}).get("id")
    if not user_id: return False
    conn = get_conn()
    conn.execute(
        "DELETE FROM portfolio WHERE id=? AND user_id=?", (item_id, user_id)
    )
    conn.commit(); conn.close()
    return True


def clear_portfolio() -> bool:
    from db import get_conn
    user_id = (_cur_user or {}).get("id")
    if not user_id: return False
    conn = get_conn()
    conn.execute("DELETE FROM portfolio WHERE user_id=?", (user_id,))
    conn.commit(); conn.close()
    return True


def save_portfolio(p):
    """Geriye dönük uyumluluk — artık kullanılmıyor."""
    pass

def load_email_cfg():
    # 1) Önce secrets.toml (Streamlit Cloud)
    try:
        s = st.secrets
        # GitHub Secrets key adlarından herhangi biri varsa kullan
        email_user = (s.get("EMAIL_USER") or s.get("SMTP_USER")
                      or s.get("smtp_user") or "")
        email_pass = (s.get("EMAIL_PASS") or s.get("SMTP_PASS")
                      or s.get("smtp_pass") or "")
        email_addr = (s.get("EMAIL_ADDRESS") or s.get("address")
                      or s.get("ADMIN_EMAIL") or "")
        if email_user and email_pass:
            return {
                "address":   email_addr,
                "smtp_host": s.get("SMTP_HOST", "smtp.gmail.com"),
                "smtp_port": int(s.get("SMTP_PORT", 587)),
                "smtp_user": email_user,
                "smtp_pass": email_pass,
                "times":     list(s.get("REPORT_TIMES", ["08:30","11:30"])),
                "tcmb_key":  s.get("TCMB_KEY", ""),
            }
    except Exception:
        pass
    # 2) Lokal email_config.json
    if os.path.exists(EMAIL_CFG_FILE):
        with open(EMAIL_CFG_FILE) as f: return json.load(f)
    return {"address":"","smtp_host":"smtp.gmail.com","smtp_port":587,
            "smtp_user":"","smtp_pass":"","times":["08:30","11:30"]}

def save_email_cfg(cfg):
    with open(EMAIL_CFG_FILE,"w") as f: json.dump(cfg,f)

# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(_logo_html(),unsafe_allow_html=True)
    plan_badge = {"free":"Ucretsiz","pro":"Pro","premium":"Premium"}
    st.markdown(
        f"<small style='color:#8ca3cc'>"
        f"<b>{_cur_user['full_name']}</b><br>"
        f"{plan_badge.get(_cur_user['plan'], _cur_user['plan'])}"
        f"</small>",
        unsafe_allow_html=True
    )
    st.divider()
    page=st.radio("",PAGES,label_visibility="collapsed")
    st.divider()

    st.markdown("**Portföy Bütçesi (TL)**")
    butce_str = st.text_input(
        "Butce",
        value="" if st.session_state.get("butce_val", 0) == 0 else str(int(st.session_state.get("butce_val", 0))),
        label_visibility="collapsed",
        placeholder="Tutar girin, örnek: 100000",
        key="butce_input"
    )
    try:
        budget = int(butce_str.replace(".", "").replace(",", "").replace(" ", ""))
        if budget < 0:
            budget = 0
        st.session_state["butce_val"] = budget
    except ValueError:
        budget = int(st.session_state.get("butce_val", 0))
    if budget > 0:
        st.caption(f"Secilen: {budget:,} TL".replace(",", "."))
    risk=st.select_slider("Risk Toleransı",
                           options=["Çok Düşük","Düşük","Orta","Yüksek","Çok Yüksek"],value="Orta")
    max_assets=st.slider("Max Varlık Sayısı",min_value=5,max_value=30,value=10,step=1,
                          help="Portföyde kaç farklı varlık olacağını belirler")
    st.divider()

    # E-posta ayarları
    with st.expander("E-posta Ayarları"):
        st.markdown("""<style>
        [data-testid="stSidebar"] [data-testid="stExpander"] summary p,
        [data-testid="stSidebar"] [data-testid="stExpander"] p,
        [data-testid="stSidebar"] [data-testid="stExpander"] label p {
            color:#1b2a4a!important;font-weight:600!important;
        }
        </style>""", unsafe_allow_html=True)
        ecfg=load_email_cfg()
        e_addr=st.text_input("Alıcı E-posta",value=ecfg.get("address",""))
        e_t1=st.text_input("1. Gönderim (HH:MM)",value=ecfg.get("times",["08:30"])[0])
        e_t2=st.text_input("2. Gönderim (HH:MM)",value=ecfg.get("times",["08:30","11:30"])[-1])
        if st.button("Ayarları Kaydet", key="ecfg_save", use_container_width=True):
            save_email_cfg({"address":e_addr,"smtp_host":"smtp.gmail.com","smtp_port":587,
                             "smtp_user":ecfg.get("smtp_user",""),
                             "smtp_pass":ecfg.get("smtp_pass",""),
                             "times":[e_t1,e_t2],
                             "tcmb_key":ecfg.get("tcmb_key","")})
            st.success("Kaydedildi!")
        if st.button("Şimdi Gönder", key="send_now", use_container_width=True):
            try:
                from emailer import send_report
                df_uni2=load_universe()
                pf=load_portfolio()
                send_report(df_uni2,pf,budget,risk,max_assets)
                st.success("E-posta gönderildi!")
            except Exception as ex:
                st.error(f"Hata: {ex}")
    st.divider()
    if _cur_user.get("is_admin"):
        if st.button("Admin Paneli", use_container_width=True):
            st.session_state["page_override"] = "admin"
            st.rerun()
    if st.button("Cikis Yap", use_container_width=True):
        logout(); st.rerun()

# Admin panel override
if st.session_state.get("page_override") == "admin":
    render_admin_panel()
    if st.button("Panele Don"):
        st.session_state.pop("page_override", None)
        st.rerun()
    st.stop()


# ══════════════════════════════════════════════════════════════
# VERİ YÜKLE
# ══════════════════════════════════════════════════════════════
df_uni=load_universe()

# session_state: seçili ticker
for pg in PAGES:
    if f"sel_{pg}" not in st.session_state:
        st.session_state[f"sel_{pg}"]=None

RISK_W={
    "Çok Düşük":{"TEFAS":.60,"DOVIZ":.20,"MADEN":.10,"BIST":.08,"KRIPTO":.02},
    "Düşük":    {"TEFAS":.45,"DOVIZ":.15,"MADEN":.15,"BIST":.20,"KRIPTO":.05},
    "Orta":     {"TEFAS":.30,"DOVIZ":.10,"MADEN":.15,"BIST":.35,"KRIPTO":.10},
    "Yüksek":   {"TEFAS":.15,"DOVIZ":.08,"MADEN":.12,"BIST":.45,"KRIPTO":.20},
    "Çok Yüksek":{"TEFAS":.05,"DOVIZ":.05,"MADEN":.10,"BIST":.50,"KRIPTO":.30},
}

# ══════════════════════════════════════════════════════════════
# ANA SAYFA
# ══════════════════════════════════════════════════════════════
if page=="Ana Sayfa":
    st.title("Portföy Optimizasyonu")
    if df_uni.empty:
        st.error("`python worker.py` ile veriyi oluşturun."); st.stop()

    cats=df_uni["Kategori"].value_counts()
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Toplam Varlık",f"{len(df_uni):,}")
    c2.metric("TEFAS",f"{cats.get('TEFAS',0):,}")
    c3.metric("BIST",f"{cats.get('BIST',0):,}")
    c4.metric("Kripto",f"{cats.get('KRIPTO',0):,}")
    c5.metric("Döviz+Maden",f"{cats.get('DOVIZ',0)+cats.get('MADEN',0):,}")

    if budget<=0:
        st.info("Sol panelden **Portföy Bütçesi** girerek optimize edilmiş öneri listesini görün.")
        st.stop()

    w=RISK_W[risk]
    st.subheader(f"Önerilen Dağılım — {budget:,.0f} ₺  |  Risk: {risk}  |  Max: {max_assets} varlık")
    st.caption(
        "**Optima Skoru** = RSI Zonu (25%) + Momentum/Getiri (35%) + Volatilite (15%) + Temel Analiz (25%). "
        "Her kategori içinde en yüksek Optima Skoruna sahip varlıklar seçilir. "
        "**Yatırım tavsiyesi değildir.**"
    )

    # ── Optimizasyon v2: Min skor eşiği + kalite bazlı ağırlık ──
    MIN_SKOR = 60.0   # Sadece "KADEMELİ AL" ve üstü sinyaller önerilir

    # 1. Adım: Her kategorideki uygun varlıkları skorla ve filtrele
    cat_pools = {}
    for cat, weight in w.items():
        if weight <= 0:
            continue
        if cat == "TEFAS":
            df_c = df_uni[df_uni["Kategori"] == cat].copy()
            if "Ret1M" in df_c.columns:
                df_c = df_c[df_c["Ret1M"] != 0].copy()
        else:
            df_c = df_uni[(df_uni["Kategori"]==cat)&(df_uni["Son_Fiyat"]>0)].copy()
        if df_c.empty:
            continue
        df_c["Optima_Skor"] = df_c.apply(
            lambda r: optima_score(float(r.get("RSI",50)),float(r.get("Ret1M",0)),
                                   vol=float(r.get("Vol",30) or 30)), axis=1)
        # Filtre 1: Negatif getirili varlıklar elenir
        df_c = df_c[df_c["Ret1M"] > 0].copy()
        # Filtre 2: Skor eşiği — 60 altı = "TUT İZLE" veya daha kötü
        df_c = df_c[df_c["Optima_Skor"] >= MIN_SKOR].sort_values("Optima_Skor", ascending=False)
        if not df_c.empty:
            cat_pools[cat] = df_c

    # 2. Adım: Slot dağıtımı — garantili max_assets varlık
    # Strateji:
    #   a) Her kategoriye başlangıç slotu ver (eşit bölme)
    #   b) Bir kategori kendi slotunu dolduramıyorsa (az varlık),
    #      boş kalan slotlar en yüksek skorlu diğer kategorilere aktarılır
    #   c) Bu döngü max_assets dolana veya aktarılacak slot kalmayana kadar sürer
    cat_quality  = {c: float(df["Optima_Skor"].mean()) for c, df in cat_pools.items()}
    cats_by_qual = sorted(cat_quality, key=cat_quality.get, reverse=True)
    n_cats       = len(cat_pools)

    slots     = {c: max(1, max_assets // n_cats) for c in cat_pools}
    # Toplam slotu max_assets'e tamamla (bölme artığı)
    deficit   = max_assets - sum(slots.values())
    for cat in cats_by_qual:
        if deficit <= 0: break
        slots[cat] += 1
        deficit    -= 1

    # Kapasitesi az olan kategorilerin slotlarını yeniden dağıt
    changed = True
    while changed:
        changed   = False
        overflow  = 0
        for cat in list(slots):
            cap = len(cat_pools[cat])
            if slots[cat] > cap:
                overflow    += slots[cat] - cap
                slots[cat]   = cap
                changed      = True
        # Taşan slotları yüksek skorlu kategorilere ver (kapasiteleri varsa)
        for cat in cats_by_qual:
            if overflow <= 0: break
            cap   = len(cat_pools[cat])
            room  = cap - slots[cat]
            if room > 0:
                give        = min(room, overflow)
                slots[cat] += give
                overflow   -= give

    max_per_cat_map = slots

    # Kalite bazlı ağırlık — kategori ortalama skoruna göre düzelt
    adj_weights = {}
    total_adj = 0.0
    for cat, weight in w.items():
        if cat not in cat_pools:
            continue
        mpc = max_per_cat_map.get(cat, 1)
        top_scores = cat_pools[cat]["Optima_Skor"].head(mpc)
        quality = float(top_scores.mean()) / 100.0
        adj = weight * quality
        adj_weights[cat] = adj
        total_adj += adj
    if total_adj > 0:
        adj_weights = {c: a/total_adj for c, a in adj_weights.items()}

    opt_rows=[]
    for cat, weight in adj_weights.items():
        df_c = cat_pools[cat]
        mpc  = max_per_cat_map.get(cat, 1)
        sample = df_c.head(min(mpc, len(df_c)))
        cat_bud = budget * weight
        per = cat_bud / len(sample)
        for _, row in sample.iterrows():
            skor = float(row["Optima_Skor"])
            rsi_v = float(row.get("RSI",50))
            trend_v = "YUKSELIS" if float(row.get("Ret1M",0)) >= 0 else "DUSUS"
            sig_lbl, _ = get_signal(skor, rsi_v, trend_v)
            price = float(row["Son_Fiyat"]) if float(row.get("Son_Fiyat",0)) > 0 else 1.0
            lot = int(per/price) if price > 0 else int(per)
            gercek = round(lot*price,2) if float(row.get("Son_Fiyat",0)) > 0 else per
            opt_rows.append({
                "Kategori":cat,
                "Ticker":row["Ticker"],
                "Ad":str(row["Ad"])[:50],
                "Optima Skoru":skor,
                "Sinyal":sig_lbl,
                "RSI":rsi_v,
                "1A Getiri %":float(row.get("Ret1M",0)),
                "Emir Fiyatı":price,
                "Kategori Payı %":round(weight*100,1),
                "Lot / Adet":lot,
                "Gerçek Tutar (₺)":gercek,
                "Hedef Tutar (₺)":round(per,2),
            })

    # Elenen kategorileri bildir
    elenen = [c for c in w if w.get(c,0) > 0 and c not in adj_weights]
    if elenen:
        st.info(f"Şu kategorilerde yeterli AL sinyalli varlik bulunamadigi icin "
                f"bütçe diğer kategorilere dağıtıldı: {', '.join(elenen)}")

    if opt_rows:
        df_opt=pd.DataFrame(opt_rows)
        # Optima Skoru'na göre azalan sırala
        df_opt=df_opt.sort_values("Optima Skoru", ascending=False).reset_index(drop=True)

        # Gelir projeksiyonu sütunlarını ana tabloya ekle
        try:
            from dividend_engine import calc_optimization_income
            with st.spinner("Pasif gelir hesaplanıyor..."):
                df_opt_gelir = calc_optimization_income(df_opt, df_uni, budget)
            if not df_opt_gelir.empty and "Yıllık Gelir (₺)" in df_opt_gelir.columns:
                toplam_gelir = df_opt_gelir["Yıllık Gelir (₺)"].sum()
                # Gelir sütunlarını Ticker üzerinden birleştir
                gelir_merge = df_opt_gelir[
                    [c for c in ["Ticker","Gelir Türü","Gelir Oranı (%)","Yıllık Gelir (₺)"]
                     if c in df_opt_gelir.columns]
                ]
                df_opt = df_opt.merge(gelir_merge, on="Ticker", how="left")
                # Özet metrikler
                if toplam_gelir > 0:
                    pg1, pg2, pg3 = st.columns(3)
                    pg1.metric("Tahmini Yıllık Pasif Gelir", f"{toplam_gelir:,.2f} ₺")
                    pg2.metric("Aylık Gelir (~)", f"{toplam_gelir/12:,.2f} ₺")
                    pg3.metric("Bütçeye Oranı",
                               f"{toplam_gelir/budget*100:.2f}%" if budget > 0 else "—")
        except Exception as e:
            st.caption(f"Gelir projeksiyonu: {e}")

        # Birleşik tablo — sütun sırası
        base_cols = ["Kategori","Ticker","Ad","Optima Skoru","Sinyal","RSI","1A Getiri %",
                     "Emir Fiyatı","Kategori Payı %","Lot / Adet","Gerçek Tutar (₺)","Hedef Tutar (₺)"]
        extra_cols = [c for c in ["Gelir Türü","Gelir Oranı (%)","Yıllık Gelir (₺)"]
                      if c in df_opt.columns]
        col_order = base_cols + extra_cols
        df_opt = df_opt[[c for c in col_order if c in df_opt.columns]]

        col_cfg = {
            "Optima Skoru": st.column_config.NumberColumn("Optima Skoru", format="%.1f",
                help="0-100 arası bileşik skor"),
            "RSI":          st.column_config.NumberColumn(format="%.1f"),
            "1A Getiri %":  st.column_config.NumberColumn(format="%.2f"),
            "Emir Fiyatı":  st.column_config.NumberColumn(format="%.4f",
                help="Güncel piyasa fiyatı — limit emir için referans alın"),
            "Gerçek Tutar (₺)": st.column_config.NumberColumn(format="%.2f",
                help="Lot x Fiyat — tam alım tutarı"),
            "Hedef Tutar (₺)":  st.column_config.NumberColumn(format="%.2f",
                help="Kategoriye ayrılan bütçe payı"),
        }
        if "Gelir Oranı (%)" in df_opt.columns:
            col_cfg["Gelir Oranı (%)"]  = st.column_config.NumberColumn(format="%.2f")
        if "Yıllık Gelir (₺)" in df_opt.columns:
            col_cfg["Yıllık Gelir (₺)"] = st.column_config.NumberColumn(format="%.2f")

        st.caption("Gerçek Tutar = Lot x Emir Fiyatı. Lot tam sayıya yuvarlandığından Hedef Tutar'dan küçük olabilir. "
                   "Pasif gelir tahmini: BIST temettü | Kripto staking APY | TEFAS 1A getirisi x 12. Yatırım tavsiyesi değildir.")

        # Tıklanabilir tablo
        df_opt_show = df_opt.copy()
        sel_ana = st.session_state.get("sel_Ana Sayfa", "")
        new_sel = clickable_table(df_opt_show, key="anasayfa", sel_ticker=sel_ana)
        if new_sel and new_sel != sel_ana:
            st.session_state["sel_Ana Sayfa"] = new_sel
            st.rerun()

        # ── Tıklanan varlığın analizi ──────────────────────────
        sel_ana = st.session_state.get("sel_Ana Sayfa")
        if sel_ana:
            sel_row_ana = df_uni[df_uni["Ticker"] == sel_ana]
            if not sel_row_ana.empty:
                sel_row_ana = sel_row_ana.iloc[0]
                cat_ana = str(sel_row_ana["Kategori"])
                st.divider()
                st.subheader(f"Detay: {sel_ana}  —  {str(sel_row_ana['Ad'])[:60]}")

                period_map = {"1 Ay":"1mo","3 Ay":"3mo","6 Ay":"6mo","1 Yil":"1y","5 Yil":"5y"}
                p_lbl = st.radio("Periyot", list(period_map.keys()),
                                 horizontal=True, key="per_ana")
                period_val = period_map[p_lbl]

                with st.spinner("Analiz yukleniyor..."):
                    d = enrich(sel_row_ana, period_val)
                    sig_lbl, sig_cls = get_signal(d["score"], d["rsi"], d["trend"])

                r1,r2,r3,r4,r5 = st.columns(5)
                r1.metric("Son Fiyat",    f"{float(sel_row_ana['Son_Fiyat']):,.4f}")
                r2.metric("Optima Skor",  f"{d['score']:.1f}")
                r3.metric("RSI (14)",     f"{d['rsi']:.1f}")
                r4.metric("1A Getiri %",  f"{d['ret1m']:+.2f}%")
                r5.metric("Yillik Vol %", f"{d['vol']:.1f}%")

                sig_color = SIG_COLORS.get(sig_cls, "#666")
                st.markdown(f"""
                <div class="ts-card" style="border-left:5px solid {sig_color};padding:12px 18px;">
                  <span class="ts-sig {sig_cls}">{sig_lbl}</span>
                  <span style="color:#6c7a9c;font-size:12px;margin-left:14px">
                    Trend: <b>{d['trend']}</b> &nbsp;|&nbsp;
                    Optima Skor: <b>{d['score']}/100</b> &nbsp;|&nbsp;
                    MACD: <b>{d['macd']:.4f}</b>
                  </span>
                </div>""", unsafe_allow_html=True)

                if not d["hist"].empty:
                    fig = candle_fig(d["hist"], sel_ana)
                    if fig: st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"{sel_ana} icin gecmis fiyat verisi yuklenemedi.")

                # BIST ise temel analiz
                if cat_ana == "BIST":
                    st.divider()
                    st.subheader("Temel Analiz")
                    try:
                        from kap_client import (fetch_kap_fundamentals,
                                                fundamentals_to_display,
                                                score_from_fundamentals, get_kap_url)
                        kap_url = get_kap_url(sel_ana)
                        with st.spinner("Temel veriler yukleniyor..."):
                            raw  = fetch_kap_fundamentals(sel_ana)
                            disp = fundamentals_to_display(raw)
                            fund_skor = score_from_fundamentals(
                                raw, float(sel_row_ana["Son_Fiyat"]))
                        pb = raw.get("pb_ratio"); pe = raw.get("pe_ratio")
                        dy = raw.get("div_yield")
                        # Master Skor: ana Optima Skoru (%70) + temel skor (%30)
                        # Ana skor tabloda gösterilen skorla AYNI — tutarlılık korunur
                        combined = min(100, round(d["score"] * 0.70 + fund_skor, 1))
                        final_lbl, final_cls = get_signal(combined, d["rsi"], d["trend"])
                        src_note = "yfinance"
                        if raw.get("_kap_available"): src_note += " + KAP"
                        elif raw.get("_kap_note"):    src_note += f" | KAP: {raw['_kap_note']}"
                        st.caption(f"Kaynak: {src_note}")
                        if kap_url: st.caption(f"[KAP Finansal Bilgiler Sayfasi]({kap_url})")
                        ka, kb = st.columns([2, 1])
                        with ka:
                            rows_html = "".join(
                                f"<tr><td>{k}</td><td><b>{v}</b></td></tr>"
                                for k, v in disp.items())
                            st.markdown(f'<table class="kap-table">{rows_html}</table>',
                                        unsafe_allow_html=True)
                        with kb:
                            clr = SIG_COLORS.get(final_cls, "#666")
                            st.markdown(f"""
                            <div class="ts-card">
                            <b>Skor Bilesimi</b><br><br>
                            <small style='color:#6c7a9c'>Optima Skoru (tabloyla ayni)</small><br>
                            <b style='font-size:20px;color:#1b2a4a'>{d['score']:.1f} / 100</b><br><br>
                            <small style='color:#6c7a9c'>Temel Skor</small><br>
                            <b style='font-size:20px;color:#1b2a4a'>{fund_skor:.1f} / 30</b><br>
                            <hr style='border-color:#e0e8f4;margin:10px 0'>
                            <small style='color:#6c7a9c'>Master Skor</small><br>
                            <b style='font-size:30px;color:{clr}'>{combined}</b> <small>/100</small><br><br>
                            <span class="ts-sig {final_cls}">{final_lbl}</span>
                            </div>""", unsafe_allow_html=True)
                    except Exception as e:
                        st.warning(f"Temel analiz yuklenemedi: {e}")

        # 3D-effect pasta grafiği
        if HAS_PLOTLY:
            cat_sum=df_opt.groupby("Kategori")["Hedef Tutar (₺)"].sum().reset_index()
            n=len(cat_sum)
            pull=[0.07]*n  # 3D etkisi için tüm dilimler dışarı çekilir
            colors=["#1b2a4a","#3b9eff","#00d4aa","#f4a300","#e74c3c",
                    "#9b59b6","#2ecc71","#e67e22","#1abc9c","#e91e63"][:n]
            fig_pie=go.Figure(go.Pie(
                labels=cat_sum["Kategori"],values=cat_sum["Hedef Tutar (₺)"],
                pull=pull,hole=0.25,
                marker=dict(colors=colors,line=dict(color="#ffffff",width=2)),
                textinfo="label+percent",textfont=dict(size=13),
                hovertemplate="<b>%{label}</b><br>%{value:,.2f} ₺<br>%{percent}<extra></extra>"
            ))
            fig_pie.update_layout(
                title=dict(text="Kategori Dağılımı",font=dict(size=15,color="#1b2a4a")),
                height=360,paper_bgcolor="#fff",
                legend=dict(orientation="v",font=dict(color="#1b2a4a")),
                margin=dict(l=0,r=0,t=50,b=0)
            )
            st.plotly_chart(fig_pie,use_container_width=True)

# ══════════════════════════════════════════════════════════════
# PORTFÖYÜM
# ══════════════════════════════════════════════════════════════
elif page=="Portföyüm":
    st.title("Portföyüm")

    # ── Veri yükle ──────────────────────────────────────────────
    portfolio = load_portfolio()

    # ── Yeni Pozisyon Ekle ──────────────────────────────────────
    with st.expander("Yeni Pozisyon Ekle", expanded=not portfolio):
        if df_uni.empty:
            st.warning("`python worker.py` ile veriyi önce oluşturun.")
        else:
            df_uni_copy = df_uni.copy()
            df_uni_copy["_label"] = (
                df_uni_copy["Ticker"] + " — " +
                df_uni_copy["Ad"].astype(str).str[:50]
            )
            labels  = df_uni_copy["_label"].tolist()
            tickers_list = df_uni_copy["Ticker"].tolist()
            cats_list    = df_uni_copy["Kategori"].tolist()

            p_c1, p_c2, p_c3 = st.columns(3)
            with p_c1:
                sel_label = st.selectbox("Varlık", labels, key="pf_varlik_sel")
                idx_sel   = labels.index(sel_label)
                pt        = tickers_list[idx_sel]
                pt_cat    = cats_list[idx_sel]
            with p_c2:
                pa_str = st.text_input("Adet / Lot", value="1", key="pf_adet",
                                       placeholder="Örn: 5,06")
                try:
                    pa = float(pa_str.replace(".", "").replace(",", "."))
                except Exception:
                    pa = 0.0
            with p_c3:
                pm_str = st.text_input("Alış Maliyeti (birim, TL)", value="0", key="pf_maliyet",
                                       placeholder="Örn: 6.480,00")
                try:
                    pm = float(pm_str.replace(".", "").replace(",", "."))
                except Exception:
                    pm = 0.0
            p_c4, p_c5 = st.columns(2)
            with p_c4:
                pm_kurum_str = st.text_input(
                    "Kurumun Güncel Alış Fiyatı (TL) — K/Z için",
                    value="0", key="pf_kurum_alis",
                    placeholder="Örn: 6.027,19",
                    help="Varlığı bugün satsanız kurumun size ödeyeceği fiyat"
                )
                try:
                    pm_kurum = float(pm_kurum_str.replace(".", "").replace(",", "."))
                except Exception:
                    pm_kurum = 0.0
            with p_c5:
                pf_note = st.text_input("Not (isteğe bağlı)", key="pf_not",
                                        placeholder="Örn: ING Bank, uzun vadeli")
            if st.button("EKLE", use_container_width=True, key="pf_ekle"):
                if pa > 0:
                    note_full = pf_note
                    if pm_kurum > 0:
                        note_full = f"kurum_alis:{pm_kurum:.4f}" + (f"|{pf_note}" if pf_note else "")
                    add_portfolio_item(pt, pa, pm, asset_type=pt_cat, note=note_full)
                    st.success(f"{pt} portföye eklendi.")
                    st.rerun()
                else:
                    st.warning("Adet 0'dan büyük olmalı.")

    if not portfolio:
        st.info("Henüz pozisyon yok. Yukarıdan ekleyebilirsin.")
        st.stop()

    # ── Özet ve gelir hesabı ────────────────────────────────────
    # dividend_engine için eski format (ticker/adet/maliyet)
    pf_legacy = [
        {"ticker": r["ticker"], "adet": r["quantity"], "maliyet": r["avg_cost"]}
        for r in portfolio
    ]

    try:
        from dividend_engine import calc_portfolio_income, portfolio_income_summary
        with st.spinner("Temettü ve gelir hesaplanıyor..."):
            df_income = calc_portfolio_income(pf_legacy, df_uni)
        if not df_income.empty:
            summary = portfolio_income_summary(df_income)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Toplam Değer",
                      f"{summary.get('toplam_deger',0):,.2f} ₺")
            m2.metric("Yıllık Temettü + Staking",
                      f"{summary.get('yillik_gelir_try',0):,.2f} ₺")
            m3.metric("Ort. Pasif Gelir %",
                      f"{summary.get('ortalama_gelir_pct',0):.2f}%")
            m4.metric("En Yüksek Gelirli",
                      summary.get("max_gelir_varlik","—"))

            if summary.get("temettu_try",0)+summary.get("staking_try",0) > 0:
                st.divider()
                st.subheader("Gelir Kaynakları")
                g1, g2, g3 = st.columns(3)
                g1.metric("Temettü (BIST)",
                          f"{summary.get('temettu_try',0):,.2f} ₺/yıl")
                g2.metric("Staking (Kripto)",
                          f"{summary.get('staking_try',0):,.2f} $/yıl")
                g3.metric("Fon Getirisi (TEFAS)",
                          f"{summary.get('fon_getiri_try',0):,.2f} ₺/yıl")

            st.divider()
            st.subheader("Pozisyon Detayı")
            st.dataframe(
                df_income,
                use_container_width=True, hide_index=True,
                column_config={
                    "Güncel Fiyat":       st.column_config.NumberColumn(format="%.4f"),
                    "Toplam Değer (₺)":   st.column_config.NumberColumn(format="%.2f"),
                    "Yıllık Gelir/Birim": st.column_config.NumberColumn(format="%.4f"),
                    "Yıllık Gelir (₺)":   st.column_config.NumberColumn(format="%.2f"),
                    "Gelir Oranı (%)":    st.column_config.NumberColumn(format="%.2f"),
                    "K/Z (%)":            st.column_config.NumberColumn(format="%.2f"),
                    "Toplam Getiri (%)":  st.column_config.NumberColumn(format="%.2f"),
                }
            )
            st.caption(
                "Toplam Getiri = K/Z (%) + Pasif Gelir Oranı (%). "
                "BIST: temettü | Kripto: staking APY | TEFAS: fon getirisi."
            )
        else:
            _simple_portfolio(pf_legacy, df_uni)
    except Exception as e:
        st.warning(f"Gelir hesabı: {e}")
        _simple_portfolio(pf_legacy, df_uni)

    # ── Pozisyon Yönetimi ────────────────────────────────────────
    st.divider()
    st.subheader("Pozisyon Yönetimi")

    # Tek tek silme
    for pos in portfolio:
        col_t, col_q, col_c, col_btn = st.columns([3, 2, 2, 1])
        col_t.markdown(
            f"**{pos['ticker']}** "
            f"<span style='color:#6c7a9c;font-size:12px'>{pos['asset_type']}</span>",
            unsafe_allow_html=True
        )
        col_q.markdown(
            f"<span style='color:#1b2a4a'>{pos['quantity']:,.4f} adet</span>",
            unsafe_allow_html=True
        )
        col_c.markdown(
            f"<span style='color:#1b2a4a'>Alış: {pos['avg_cost']:,.4f} TL</span>",
            unsafe_allow_html=True
        )
        if col_btn.button("Sil", key=f"del_{pos['id']}"):
            delete_portfolio_item(pos["id"])
            st.rerun()

    st.divider()
    if st.button("Tümünü Sil", use_container_width=True, key="pf_clear"):
        clear_portfolio()
        st.rerun()

# ══════════════════════════════════════════════════════════════
# KATEGORİ SAYFALARI (tıklanabilir tablo)
# ══════════════════════════════════════════════════════════════
elif page in CAT:
    cat_code=CAT[page]
    st.title(page)
    if df_uni.empty: st.error("`python worker.py` çalıştırın."); st.stop()

    df_cat=df_uni[df_uni["Kategori"]==cat_code].copy()
    if df_cat.empty: st.warning(f"{page} verisi bulunamadı."); st.stop()

    # Optima Skoru hesapla
    df_cat["Optima_Skor"]=df_cat.apply(
        lambda r: optima_score(float(r.get("RSI",50)),float(r.get("Ret1M",0)),
                               vol=float(r.get("Vol",30) or 30)),axis=1)

    # Fiyatlılar üste, fiyatsızlar alta — skor sıralı
    df_cat["_fiyatli"] = (df_cat["Son_Fiyat"] > 0).astype(int)
    df_cat = df_cat.sort_values(["_fiyatli","Optima_Skor"], ascending=[False,False])
    df_cat = df_cat.drop(columns=["_fiyatli"])

    # Özet metrikler
    m1,m2,m3,m4=st.columns(4)
    fiyatli=df_cat[df_cat["Son_Fiyat"]>0]
    # TEFAS için Ret1M>0 olan varlıklar da değerlendirilebilir
    degerli = fiyatli if cat_code != "TEFAS" else df_cat[df_cat["Ret1M"] != 0]
    if degerli.empty:
        degerli = df_cat
    m1.metric("Toplam Varlık",len(df_cat))
    m2.metric("Fiyatı Olan" if cat_code != "TEFAS" else "Getiri Verisi",
              len(fiyatli) if cat_code != "TEFAS" else len(degerli))
    ret_mean = degerli["Ret1M"].mean() if not degerli.empty else 0.0
    m3.metric("Ort. 1A Getiri %",f"{ret_mean:.2f}%")
    m4.metric("Ort. Optima Skor",f"{degerli['Optima_Skor'].mean():.1f}" if not degerli.empty else "N/A")

    # ── TOP 5 ────────────────────────────────────────────────
    st.divider()
    st.subheader("En Yüksek Optima Skoru — Top 5")
    top5=degerli.nlargest(5,"Optima_Skor")
    # Top5 dataframe olarak göster — tıklanabilir
    top5_show = top5[["Ticker","Ad","Son_Fiyat","RSI","Ret1M","Optima_Skor"]].copy()
    top5_show.columns = ["Ticker","Ad","Son Fiyat","RSI","1A Getiri%","Optima Skor"]
    top5_show["Ad"] = top5_show["Ad"].astype(str).str[:40]
    new_sel_top5 = clickable_table(top5_show, key=f"top5_{page}",
                                   sel_ticker=st.session_state.get(f"sel_{page}",""))
    if new_sel_top5 and new_sel_top5 != st.session_state.get(f"sel_{page}"):
        st.session_state[f"sel_{page}"] = new_sel_top5
        st.rerun()

    # ── Tüm Varlıklar Tablosu (tıklanabilir) ─────────────────
    st.divider()
    st.subheader("Tüm Varlıklar")
    if cat_code in ["BIST","TEFAS"]:
        srch=st.text_input("Ara",placeholder="Ticker veya ad...")
        if srch.strip():
            mask=(df_cat["Ticker"].str.contains(srch.strip().upper(),na=False)|
                  df_cat["Ad"].str.contains(srch.strip(),case=False,na=False))
            df_cat=df_cat[mask]

    # Sayfalama
    page_size = 50
    pg_key = f"tbl_pg_{page}"
    if pg_key not in st.session_state:
        st.session_state[pg_key] = 0
    cur_pg  = st.session_state[pg_key]
    df_page = df_cat.iloc[cur_pg*page_size:(cur_pg+1)*page_size]
    sel_now = st.session_state.get(f"sel_{page}", "")

    # Tıklanabilir tablo
    df_page_show = df_page[["Ticker","Ad","Son_Fiyat","RSI","Ret1M","Optima_Skor"]].copy()
    df_page_show.columns = ["Ticker","Ad","Son Fiyat","RSI","1A Getiri%","Optima Skor"]
    df_page_show["Ad"] = df_page_show["Ad"].astype(str).str[:50]
    new_sel = clickable_table(df_page_show, key=f"cat_{page}_{cur_pg}", sel_ticker=sel_now)
    if new_sel and new_sel != sel_now:
        st.session_state[f"sel_{page}"] = new_sel
        st.rerun()

    # Sayfa navigasyonu
    total_pages = max(1, -(-len(df_cat) // page_size))
    if total_pages > 1:
        nav1, nav2, nav3 = st.columns([1,2,1])
        with nav1:
            if cur_pg > 0 and st.button("Onceki", key=f"pg_prev_{page}"):
                st.session_state[pg_key] = cur_pg - 1; st.rerun()
        with nav2:
            st.caption(f"Sayfa {cur_pg+1} / {total_pages}  ({len(df_cat)} varlik)")
        with nav3:
            if cur_pg < total_pages-1 and st.button("Sonraki", key=f"pg_next_{page}"):
                st.session_state[pg_key] = cur_pg + 1; st.rerun()

    # ── DETAY ANALİZ ─────────────────────────────────────────
    sel=st.session_state.get(f"sel_{page}")
    if not sel:
        st.info("Tablodan bir satıra tıklayarak analizi açın.")
        st.stop()

    all_tickers=df_uni[df_uni["Kategori"]==cat_code]["Ticker"].tolist()
    if sel not in all_tickers:
        st.session_state[f"sel_{page}"]=all_tickers[0] if all_tickers else None
        st.rerun()

    sel_row=df_uni[df_uni["Ticker"]==sel].iloc[0]
    st.divider()
    st.subheader(f"Detay: {sel}  —  {str(sel_row['Ad'])[:60]}")

    period_map={"1 Ay":"1mo","3 Ay":"3mo","6 Ay":"6mo","1 Yıl":"1y","5 Yıl":"5y"}
    p_lbl=st.radio("Periyot",list(period_map.keys()),horizontal=True,key=f"per_{page}")
    period_val=period_map[p_lbl]

    with st.spinner("Analiz yükleniyor..."):
        d=enrich(sel_row,period_val)
        sig_lbl,sig_cls=get_signal(d["score"],d["rsi"],d["trend"])

    r1,r2,r3,r4,r5=st.columns(5)
    r1.metric("Son Fiyat",f"{float(sel_row['Son_Fiyat']):,.4f}")
    r2.metric("Optima Skor",f"{d['score']:.1f}")
    r3.metric("RSI (14)",f"{d['rsi']:.1f}")
    r4.metric("1A Getiri %",f"{d['ret1m']:+.2f}%")
    r5.metric("Yıllık Vol %",f"{d['vol']:.1f}%")

    sig_color=SIG_COLORS.get(sig_cls,"#666")
    st.markdown(f"""
    <div class="ts-card" style="border-left:5px solid {sig_color};padding:12px 18px;">
      <span class="ts-sig {sig_cls}">{sig_lbl}</span>
      <span style="color:#6c7a9c;font-size:12px;margin-left:14px">
        Trend: <b>{d['trend']}</b> &nbsp;|&nbsp;
        Optima Skor: <b>{d['score']}/100</b> &nbsp;|&nbsp;
        MACD: <b>{d['macd']:.4f}</b>
      </span>
    </div>""",unsafe_allow_html=True)

    # Mum grafiği
    if not d["hist"].empty:
        fig=candle_fig(d["hist"],sel)
        if fig: st.plotly_chart(fig,use_container_width=True)
    else:
        st.warning(f"{sel} için geçmiş fiyat verisi yüklenemedi.")

    # BIST Temel Analiz
    if cat_code=="BIST":
        st.divider()
        st.subheader("Temel Analiz")
        try:
            from kap_client import (fetch_kap_fundamentals, fundamentals_to_display,
                                    score_from_fundamentals, get_kap_url)
            kap_url = get_kap_url(sel)

            with st.spinner("Temel veriler yükleniyor (yfinance + KAP)..."):
                raw  = fetch_kap_fundamentals(sel)
                disp = fundamentals_to_display(raw)
                fund_skor = score_from_fundamentals(raw, float(sel_row["Son_Fiyat"]))

            pb = raw.get("pb_ratio"); pe = raw.get("pe_ratio"); dy = raw.get("div_yield")
            combined = min(100, round(
                optima_score(d["rsi"], d["ret1m"], d["vol"], True, pb, pe, dy), 1))
            final_lbl, final_cls = get_signal(combined, d["rsi"], d["trend"])

            # Kaynak bilgisi
            src_note = "yfinance"
            if raw.get("_kap_available"):
                src_note += " + KAP"
            elif raw.get("_kap_note"):
                src_note += f" | KAP: {raw['_kap_note']}"
            st.caption(f"Kaynak: {src_note}")

            if kap_url:
                st.caption(f"[KAP Finansal Bilgiler Sayfası]({kap_url})")

            ka, kb = st.columns([2, 1])
            with ka:
                rows_html = "".join(
                    f"<tr><td>{k}</td><td><b>{v}</b></td></tr>"
                    for k, v in disp.items()
                )
                st.markdown(
                    f'<table class="kap-table">{rows_html}</table>',
                    unsafe_allow_html=True
                )
            with kb:
                st.markdown('<div class="ts-card">', unsafe_allow_html=True)
                st.markdown("**Skor Bileşimi**")
                clr = SIG_COLORS.get(final_cls, "#666")
                st.markdown(f"""
                <small style='color:#6c7a9c'>Teknik Skor (RSI + Momentum + Vol)</small><br>
                <b style='font-size:20px;color:#1b2a4a'>{d['score']:.1f} / 70</b><br><br>
                <small style='color:#6c7a9c'>Temel Skor (F/K + PD/DD + Temettü + Kâr)</small><br>
                <b style='font-size:20px;color:#1b2a4a'>{fund_skor:.1f} / 30</b><br>
                <hr style='border-color:#e0e8f4;margin:10px 0'>
                <small style='color:#6c7a9c'>Master Skor</small><br>
                <b style='font-size:30px;color:{clr}'>{combined}</b> <small>/100</small><br><br>
                <span class="ts-sig {final_cls}">{final_lbl}</span>
                """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.warning(f"Temel analiz yüklenemedi: {e}")
            st.info("Kontrol: `pip install yfinance` kurulu mu?")

    # TEFAS Getiri ve Risk Analizi (API verisinden)
    if cat_code=="TEFAS":
        st.divider(); st.subheader("TEFAS Getiri ve Risk Analizi")
        risk_val = int(sel_row.get("Risk_Deger",4))
        risk_labels={1:"Çok Düşük",2:"Düşük",3:"Orta Altı",4:"Orta",
                     5:"Orta Üstü",6:"Yüksek",7:"Çok Yüksek"}


        # Excel'den gelen getiri metrikleri — her zaman göster
        ret1m_x = float(sel_row.get("Ret1M", 0) or 0)
        ret3m_x = float(sel_row.get("Ret3M", 0) or 0)
        ret6m_x = float(sel_row.get("Ret6M", 0) or 0) if "Ret6M" in sel_row.index else 0.0
        ret1y_x = float(sel_row.get("Ret1Y", 0) or 0) if "Ret1Y" in sel_row.index else 0.0
        ret3y_x = float(sel_row.get("Ret3Y", 0) or 0) if "Ret3Y" in sel_row.index else 0.0
        ret5y_x = float(sel_row.get("Ret5Y", 0) or 0) if "Ret5Y" in sel_row.index else 0.0

        ta,tb,tc,td = st.columns(4)
        ta.metric("1 Ay",  f"{ret1m_x:+.2f}%")
        tb.metric("3 Ay",  f"{ret3m_x:+.2f}%")
        tc.metric("6 Ay",  f"{ret6m_x:+.2f}%")
        td.metric("1 Yil", f"{ret1y_x:+.2f}%")

        if ret3y_x != 0 or ret5y_x != 0:
            te,tf,tg = st.columns(3)
            te.metric("3 Yil", f"{ret3y_x:+.2f}%")
            tf.metric("5 Yil", f"{ret5y_x:+.2f}%")
            tg.metric("Risk Puani", f"{risk_val}/7 — {risk_labels.get(risk_val,'')}")
        else:
            st.metric("Risk Puani", f"{risk_val}/7 — {risk_labels.get(risk_val,'')}")

        if not d["hist"].empty:
            pr = d["hist"]["Close"].dropna() if "Close" in d["hist"].columns else d["hist"].iloc[:,0].dropna()
            if len(pr) > 20 and pr.pct_change().dropna().std() > 0:
                rets=pr.pct_change().dropna(); rf=0.42/252; ex=rets-rf
                sharpe=round(float(ex.mean()/ex.std()*np.sqrt(252)),3)
                maxdd=round(float(((pr-pr.cummax())/pr.cummax()).min()*100),2)
                s1,s2=st.columns(2)
                s1.metric("Tahmini Sharpe",f"{sharpe:.3f}",
                          help="Getiri noktalarindan uretilen sentetik seriden hesaplanmistir.")
                s2.metric("Tahmini Max Drawdown",f"{maxdd:.2f}%",
                          help="Getiri noktalarindan uretilen sentetik seriden hesaplanmistir.")
        st.caption("Kaynak: TEFAS Excel (TEFAS.gov.tr)")
# ══════════════════════════════════════════════════════════════
# HALKA ARZ
# ══════════════════════════════════════════════════════════════
elif page=="Halka Arz":
    from datetime import datetime
    st.title("Halka Arz Takip")
    st.caption("BIST Halka Arz Endeksi (XHARZ) üyeleri — Borsa İstanbul Endeksler.xlsx kaynağından. Her 4 saatte bir güncellenir.")

    # ── Kontroller ──────────────────────────────────────────
    ha_col1, ha_col2 = st.columns([4, 1])
    with ha_col1:
        ha_ara = st.text_input("Ara (ticker veya şirket adı)", placeholder="GUNDG, Güldoğdu...", key="ha_ara")
    with ha_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        ha_refresh = st.button("Yenile", key="ha_refresh", use_container_width=True)

    # ── Veri yükle ──────────────────────────────────────────
    try:
        from halka_arz_client import fetch_ipo_list, get_ipo_summary
        with st.spinner("XHARZ üye listesi yükleniyor..."):
            df_ipo = fetch_ipo_list(force_refresh=ha_refresh)
        ha_error = None
    except Exception as _ha_ex:
        df_ipo = pd.DataFrame()
        ha_error = str(_ha_ex)

    if ha_error:
        st.error(f"Hata: {ha_error}")
        st.stop()

    if df_ipo.empty:
        st.warning(
            "Veri yüklenemedi. Olası nedenler:\n"
            "- `Endeksler.xlsx` klasörde yok\n"
            "- Borsa İstanbul'a bağlanılamıyor\n\n"
            "Çözüm: borsaistanbul.com → Endeksler → Excel olarak indir → "
            "klasöre `Endeksler.xlsx` adıyla kaydet."
        )
        st.stop()

    # ── Özet metrikler ──────────────────────────────────────
    n_fiyatli = len(df_ipo[df_ipo.get("Son_Fiyat", pd.Series([0]*len(df_ipo))).fillna(0) > 0]) if "Son_Fiyat" in df_ipo.columns else 0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("XHARZ Üye Sayısı", len(df_ipo))
    m2.metric("Fiyat Verisi Olan", n_fiyatli)
    if "Optima_Skor" in df_ipo.columns:
        ort_skor = df_ipo[df_ipo["Optima_Skor"] > 0]["Optima_Skor"].mean()
        m3.metric("Ort. Optima Skor", f"{ort_skor:.1f}" if not pd.isna(ort_skor) else "—")
    if "Ret1M" in df_ipo.columns:
        ort_ret = df_ipo[df_ipo["Ret1M"] != 0]["Ret1M"].mean()
        m4.metric("Ort. 1A Getiri", f"{ort_ret:+.2f}%" if not pd.isna(ort_ret) else "—")

    # ── Filtre ──────────────────────────────────────────────
    df_show = df_ipo.copy()
    if ha_ara:
        mask = (
            df_show["Ticker"].str.upper().str.contains(ha_ara.upper(), na=False) |
            df_show["Şirket"].str.upper().str.contains(ha_ara.upper(), na=False)
        )
        df_show = df_show[mask]

    # Optima Skoru varsa sırala
    if "Optima_Skor" in df_show.columns:
        df_show = df_show.sort_values("Optima_Skor", ascending=False)

    st.caption(f"{len(df_show)} üye gösteriliyor")

    if df_show.empty:
        st.info("Arama sonucu bulunamadı.")
        st.stop()

    # ── Tablo ───────────────────────────────────────────────
    display_cols = []
    col_cfg = {}

    display_cols.append("Ticker")
    display_cols.append("Şirket")

    if "Son_Fiyat" in df_show.columns:
        display_cols.append("Son_Fiyat")
        col_cfg["Son_Fiyat"] = st.column_config.NumberColumn("Fiyat (₺)", format="%.4f")

    if "RSI" in df_show.columns:
        display_cols.append("RSI")
        col_cfg["RSI"] = st.column_config.NumberColumn("RSI", format="%.1f")

    if "Ret1M" in df_show.columns:
        display_cols.append("Ret1M")
        col_cfg["Ret1M"] = st.column_config.NumberColumn("1A Getiri %", format="%.2f")

    if "Optima_Skor" in df_show.columns:
        display_cols.append("Optima_Skor")
        col_cfg["Optima_Skor"] = st.column_config.NumberColumn("Optima Skor", format="%.1f")

    display_cols.append("KAP_URL")
    col_cfg["KAP_URL"] = st.column_config.LinkColumn("KAP", display_text="Görüntüle")

    tablo_df = df_show[[c for c in display_cols if c in df_show.columns]].reset_index(drop=True)
    st.dataframe(tablo_df, use_container_width=True, hide_index=True, column_config=col_cfg)

    # ── CSV indir ────────────────────────────────────────────
    csv_bytes = df_show.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "CSV İndir",
        data=csv_bytes,
        file_name=f"xharz_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# ══════════════════════════════════════════════════════════════
# TEMETTÜ
# ══════════════════════════════════════════════════════════════
elif page=="Temettü":
    from datetime import datetime
    st.title("Temettü Takip")
    st.caption("BIST Temettü Endeksi (XTMTU) üyeleri — KAP verisi. Temettü bilgisi yfinance'den çekilir. Her 4 saatte bir güncellenir.")

    # ── Kontroller ───────────────────────────────────────────
    tm_col1, tm_col2 = st.columns([4, 1])
    with tm_col1:
        tm_ara = st.text_input("Ara (ticker veya şirket adı)", key="tm_ara",
                               placeholder="THYAO, Türk Hava...")
    with tm_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        tm_refresh = st.button("Yenile", key="tm_refresh", use_container_width=True)

    # ── Veri yükle ───────────────────────────────────────────
    try:
        from temettu_client import fetch_temettu_list
        with st.spinner("XTMTU verileri yükleniyor..."):
            df_tm = fetch_temettu_list(force_refresh=tm_refresh)
        tm_error = None
    except Exception as _tm_ex:
        df_tm = pd.DataFrame()
        tm_error = str(_tm_ex)

    if tm_error:
        st.error(f"Hata: {tm_error}")
        st.stop()

    if df_tm.empty:
        st.warning("XTMTU verisi çekilemedi. İnternet bağlantısını kontrol edin.")
        st.stop()

    # ── Özet metrikler ───────────────────────────────────────
    n_temettu   = len(df_tm[df_tm.get("div_yield", pd.Series([0]*len(df_tm))).fillna(0) > 0]) if "div_yield" in df_tm.columns else 0
    ort_verim   = df_tm[df_tm["div_yield"] > 0]["div_yield"].mean() if "div_yield" in df_tm.columns else 0
    maks_verim  = df_tm["div_yield"].max() if "div_yield" in df_tm.columns else 0
    ex_yakinda  = 0
    if "ex_date" in df_tm.columns:
        try:
            from datetime import datetime, timedelta
            bugun = datetime.now()
            for ed in df_tm["ex_date"]:
                try:
                    d = datetime.strptime(str(ed), "%d.%m.%Y")
                    if bugun <= d <= bugun + timedelta(days=30):
                        ex_yakinda += 1
                except Exception:
                    pass
        except Exception:
            pass

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("XTMTU Üye Sayısı",   len(df_tm))
    m2.metric("Temettü Verisi Olan", n_temettu)
    m3.metric("Ort. Temettü Verimi", f"%{ort_verim:.2f}" if ort_verim else "—")
    m4.metric("30 Gün İçinde Ex-Date", ex_yakinda)

    # ── Filtre ───────────────────────────────────────────────
    df_show = df_tm.copy()
    if tm_ara:
        mask = (
            df_show["Ticker"].str.upper().str.contains(tm_ara.upper(), na=False) |
            df_show["Şirket"].str.upper().str.contains(tm_ara.upper(), na=False)
        )
        df_show = df_show[mask]

    st.caption(f"{len(df_show)} şirket gösteriliyor — Ex-date'e göre sıralı (yakın tarih üste), ardından temettü verimine göre")

    if df_show.empty:
        st.info("Arama sonucu bulunamadı.")
        st.stop()

    # ── Tablo ────────────────────────────────────────────────
    col_cfg = {}
    display_cols = ["Ticker", "Şirket"]

    if "Son_Fiyat" in df_show.columns:
        display_cols.append("Son_Fiyat")
        col_cfg["Son_Fiyat"] = st.column_config.NumberColumn("Fiyat (₺)", format="%.2f")

    if "div_per_share" in df_show.columns:
        display_cols.append("div_per_share")
        col_cfg["div_per_share"] = st.column_config.NumberColumn("Temettü/Hisse (₺)", format="%.4f")

    if "div_yield" in df_show.columns:
        display_cols.append("div_yield")
        col_cfg["div_yield"] = st.column_config.NumberColumn("Temettü Verimi %", format="%.2f")

    if "ex_date" in df_show.columns:
        display_cols.append("ex_date")
        col_cfg["ex_date"] = st.column_config.TextColumn("Ex-Date")

    if "frequency" in df_show.columns:
        display_cols.append("frequency")
        col_cfg["frequency"] = st.column_config.TextColumn("Sıklık")

    if "Ret1M" in df_show.columns:
        display_cols.append("Ret1M")
        col_cfg["Ret1M"] = st.column_config.NumberColumn("1A Getiri %", format="%.2f")

    if "Optima_Skor" in df_show.columns:
        display_cols.append("Optima_Skor")
        col_cfg["Optima_Skor"] = st.column_config.NumberColumn("Optima Skor", format="%.1f")

    if "Toplam_Getiri" in df_show.columns:
        display_cols.append("Toplam_Getiri")
        col_cfg["Toplam_Getiri"] = st.column_config.NumberColumn(
            "Tahmini Toplam Getiri %",
            format="%.2f",
            help="1A Getiri % + Temettü Verimi % (gösterge, yatırım tavsiyesi değildir)"
        )

    if "KAP_URL" in df_show.columns:
        display_cols.append("KAP_URL")
        col_cfg["KAP_URL"] = st.column_config.LinkColumn("KAP", display_text="Görüntüle")

    tablo_df = df_show[[c for c in display_cols if c in df_show.columns]].reset_index(drop=True)

    st.dataframe(tablo_df, use_container_width=True, hide_index=True, column_config=col_cfg)

    st.caption("Tahmini Toplam Getiri = 1 Aylık Momentum + Temettü Verimi. Yatırım tavsiyesi değildir.")

    # ── CSV indir ────────────────────────────────────────────
    csv_bytes = df_show.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "CSV İndir",
        data=csv_bytes,
        file_name=f"xtmtu_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

