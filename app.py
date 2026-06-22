"""TrendSurf Optima — Terminal v5 | streamlit run app.py"""
import streamlit as st, pandas as pd, numpy as np, os, json, base64, time

try:
    import plotly.graph_objects as go, plotly.express as px
    HAS_PLOTLY = True
except: HAS_PLOTLY = False

st.set_page_config(page_title="TrendSurf Optima", page_icon="favicon.png", layout="wide",
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
[data-testid="stSidebar"] .stButton>button,[data-testid="stSidebar"] .stButton button,[data-testid="stSidebar"] button[kind="secondary"],[data-testid="stSidebar"] button[kind="primary"],[data-testid="stSidebar"] [data-testid="stExpander"] .stButton>button,[data-testid="stSidebar"] [data-testid="stExpander"] .stButton button{color:#ffffff!important;font-weight:700!important;opacity:1!important;}
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

    [data-testid="stTextInput"] {width:100%!important;}
    </style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SABITLER & YARDIMCILAR
# ══════════════════════════════════════════════════════════════
CSV_PATH, PORTFOLIO_FILE = "optimized_universe.csv", "portfolio.json"
EMAIL_CFG_FILE = "email_config.json"
PAGES = ["Ana Sayfa","Portföyüm","BIST","TEFAS","Döviz","Madenler","Kriptolar","Halka Arz","Temettü","Makro Göstergeler","Yardım"]
CAT   = {"BIST":"BIST","TEFAS":"TEFAS","Döviz":"DOVIZ","Madenler":"MADEN","Kriptolar":"KRIPTO"}
SIG_COLORS = {"sig-g":"#00732f","sig-k":"#1a7a3a","sig-t":"#8a5e00","sig-s":"#c0451b","sig-n":"#b71c1c"}

# ── Canli veri katmani (borsapy) - v1.6+ ─────────────────────────────────────
from live_data import (
    filter_universe as _ld_filter_universe,
    rename_existing_maden as _ld_rename_maden,
    extend_maden_universe as _ld_extend_maden,
    refresh_fx_maden_kripto as _ld_refresh_overlay,
    portfolio_value_prices as _ld_portfolio_prices,
    get_fx_history as _ld_fx_history,
    get_maden_history as _ld_maden_history,
    get_kripto_history as _ld_kripto_history,
    BORSAPY_OK as _LIVE_BORSAPY_OK,
    status_summary as _ld_status,
)

# ── Yeni Auth sistemi (SQLite) ───────────────────────────────────────────────
from db import init_db


# v1.8.2 - init_db'yi session basina 1 kez calistir (PostgreSQL roundtrip'leri pahali)
@st.cache_resource(show_spinner=False)
def _init_db_once():
    init_db()
    return True

_init_db_once()  # Tablolari olustur ve Secrets'tan admin'i seed et (db.py icinde, 1 kez)
from auth import get_current_user, login_user, register_user, logout
from admin import render_admin_panel


# ════════════════════════════════════════════════════════════════════════════
# HTTP TRIGGER ENDPOINT (v1.8 - Asama 2)
# URL: https://trendsurf-optima.streamlit.app/?trigger=email&token=<SECRET>
# cron-job.org bu URL'i hafta ici 09:00 ve 12:00 TRT'de hit eder.
# st.stop() ile normal app yuklenmeden tamamlanir.
# ════════════════════════════════════════════════════════════════════════════
_qp = st.query_params
if _qp.get("trigger") == "email":
    # 1) Token validasyonu
    _expected = ""
    try:
        _expected = st.secrets["trigger"]["token"]
    except Exception:
        pass
    _provided = _qp.get("token", "")

    if not _expected:
        st.write("ERROR: `trigger.token` Streamlit Secrets'ta tanimli degil.")
        st.write("Secrets'a ekle: [trigger]\\ntoken = \"...\"")
        st.stop()

    if _provided != _expected:
        st.write("403 Forbidden: Invalid token")
        st.stop()

    # 2) Email gonderimi
    import time as _t
    _t0 = _t.time()
    try:
        from emailer import send_report
        from live_data import (filter_universe, rename_existing_maden,
                                extend_maden_universe, refresh_fx_maden_kripto)

        # Universe CSV'yi yukle (worker.py her gun guncelliyor)
        _csv = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "optimized_universe.csv")
        _df_uni = pd.read_csv(_csv)

        # Live data pipeline (mevcut Streamlit ile ayni - tutarli sonuc)
        _df_uni = filter_universe(_df_uni)
        _df_uni = rename_existing_maden(_df_uni)
        _df_uni = extend_maden_universe(_df_uni)
        _df_uni = refresh_fx_maden_kripto(_df_uni)

        # Email config (Secrets'tan)
        _cfg = {
            "address":   st.secrets["email"]["address"],
            "smtp_host": st.secrets["email"]["smtp_host"],
            "smtp_port": int(st.secrets["email"]["smtp_port"]),
            "smtp_user": st.secrets["email"]["smtp_user"],
            "smtp_pass": st.secrets["email"]["smtp_pass"],
        }

        # Optimizasyon parametreleri (Secrets'ta [trigger]'dan veya default)
        _trig = st.secrets.get("trigger", {})
        _budget     = int(_trig.get("budget", 20000))
        _risk       = str(_trig.get("risk", "Orta"))
        _max_assets = int(_trig.get("max_assets", 10))

        # send_report portfolio=None -> DB'den otomatik okur (Supabase, kalici)
        send_report(_df_uni, portfolio=None, cfg=_cfg,
                    budget=_budget, risk=_risk, max_assets=_max_assets)

        _dt = _t.time() - _t0
        st.write(f"OK: Email gonderildi ({_dt:.1f}s)")
        st.write(f"Alici: {_cfg['address']}")
        st.write(f"Universe: {len(_df_uni)} satir | Butce: {_budget} TL | "
                 f"Risk: {_risk} | Max varlik: {_max_assets}")
    except Exception as _e:
        import traceback
        st.write(f"ERROR: {type(_e).__name__}: {_e}")
        st.code(traceback.format_exc(), language=None)

    st.stop()


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
    .stTextInput > div > div > input {max-width:380px!important;}
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
    _sp1, col_logo, col_form, _sp2 = st.columns([0.8, 0.7, 0.65, 0.8])

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
            # Beni Hatırla: cookie'dan email oku
            _remembered = st.query_params.get("_re", "")
            st.markdown("""
            <script>
            (function() {
                function getCookie(n){var v="; "+document.cookie,p=v.split("; "+n+"=");if(p.length===2)return decodeURIComponent(p.pop().split(";")[0]);return "";}
                var em=getCookie("ts_rem_email");
                if(em && !window.location.search.includes("_re=")){
                    var u=new URL(window.location);
                    u.searchParams.set("_re",em);
                    window.history.replaceState({},"",u);
                    location.reload();
                }
            })();
            </script>
            """, unsafe_allow_html=True)
            email = st.text_input("E-posta", key="li_email", placeholder="ornek@gmail.com", value=_remembered)
            pwd   = st.text_input("Sifre", type="password", key="li_pass", placeholder="Sifreniz")
            remember = st.checkbox("Beni Hatirla", key="li_remember")
            if st.button("Giris Yap", key="btn_login", use_container_width=True):
                if email and pwd:
                    res = login_user(email, pwd)
                    if res["ok"]:
                        st.session_state["auth_token"] = res["token"]
                        if remember:
                            st.session_state["remember_token"] = res["token"]
                            # Email cookie - 30 gün
                            import urllib.parse as _up
                            _enc = _up.quote(email)
                            _exp = "expires=Thu, 31 Dec 2026 23:59:59 GMT"
                            st.markdown(
                                f'<script>document.cookie="ts_rem_email={_enc};{_exp};path=/;SameSite=Lax";</script>',
                                unsafe_allow_html=True
                            )
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
                    if res["ok"]:
                        # Sadece admin e-postası veya ilk kullanıcıysa otomatik onayla
                        try:
                            _admin_email = st.secrets.get("admin",{}).get("email","")
                            from db import get_conn as _gc2
                            _cc2 = _gc2()
                            _user_count = _cc2.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                            _is_admin_email = email_r.lower() == _admin_email.lower()
                            if _is_admin_email or _user_count <= 1:
                                # auth.py kolonlari: is_active (aktif/onayli), is_admin, plan
                                for _s2 in [
                                    "UPDATE users SET is_active=1 WHERE email=?",
                                    "UPDATE users SET is_admin=1 WHERE email=?",
                                    "UPDATE users SET plan='premium' WHERE email=?",
                                ]:
                                    try: _cc2.execute(_s2,(email_r,)); _cc2.commit()
                                    except: pass
                                st.success("Kaydiniz tamamlandi. Giris Yap sekmesinden girebilirsiniz.")
                            else:
                                st.info("Kaydiniz alindi. Admin onayi bekleniyor.")
                            _cc2.close()
                        except:
                            st.success(res["msg"])
                    else: st.error(res["msg"])

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
# is_admin override: role=="admin" veya Secrets email eşleşmesi
if _cur_user:
    try:
        _asec2 = st.secrets.get("admin", {})
        _is_adm = (
            _cur_user.get("role") == "admin" or
            _cur_user.get("is_admin") == True or
            _cur_user.get("is_admin") == 1 or
            (_asec2.get("email") and
             _cur_user.get("email","").lower() == _asec2["email"].lower())
        )
        _cur_user["is_admin"] = _is_adm
        if _is_adm:
            _cur_user["plan"] = "premium"
    except Exception:
        pass
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


@st.cache_data(ttl=60,show_spinner=False)  # v1.8.2: 300s -> 60s (fiyat tazelemesi daha sik)
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
    # v1.6: USD bazli emtialari evrenden cikar (Brent/WTI/Dogalgaz/tarim emtialari)
    df = _ld_filter_universe(df)
    # v1.6.1: Mevcut MADEN adlarini netlestir (ALTIN_TRY -> "Gram Altin")
    df = _ld_rename_maden(df)
    # v1.6.1: Yeni MADEN sikkelerini ekle (Ceyrek/Yarim/Tam/Cumhuriyet/Ata/Ons-TL)
    df = _ld_extend_maden(df)
    # v1.6: DOVIZ + MADEN + KRIPTO icin canli fiyat uzerine yaz (borsapy)
    df = _ld_refresh_overlay(df)
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

    # v1.6: DOVIZ - borsapy direkt TRY cifti (capraz kur matematigi yok)
    if category == "DOVIZ":
        hist = _ld_fx_history(ticker, period)
        if hist is not None and not hist.empty and len(hist) >= 5:
            return hist
        # Yedek: yfinance USDTRY=X formati
        try:
            import yfinance as yf
            from data_pipeline import _format_yf_symbol
            _sym = _format_yf_symbol(ticker, category)
            _h = yf.Ticker(_sym).history(period=period, auto_adjust=True)
            if not _h.empty and len(_h) >= 5:
                return _h[["Open","High","Low","Close"]].dropna()
        except Exception:
            pass
        return pd.DataFrame()

    # v1.6: MADEN - sadece TRY-direkt gram bazli (canlidoviz.com gercek zamanli)
    if category == "MADEN":
        hist = _ld_maden_history(ticker, period)
        if hist is not None and not hist.empty and len(hist) >= 5:
            return hist
        # Yedek: yfinance (eski yontem, USD x USDTRY turetilmis)
        try:
            import yfinance as yf
            from data_pipeline import _format_yf_symbol
            _sym = _format_yf_symbol(ticker, category)
            if yf_symbol and yf_symbol.strip() and "=F" in str(yf_symbol):
                _sym = yf_symbol.strip()
            _h = yf.Ticker(_sym).history(period=period, auto_adjust=True)
            if not _h.empty and len(_h) >= 5:
                return _h[["Open","High","Low","Close"]].dropna()
        except Exception:
            pass
        return pd.DataFrame()

    # v1.6: KRIPTO - borsapy direkt TRY cifti (BtcTurk gercek zamanli)
    if category == "KRIPTO":
        hist = _ld_kripto_history(ticker, period)
        if hist is not None and not hist.empty and len(hist) >= 5:
            return hist
        # Yedek: yfinance BTC-USD turetilmis
        try:
            import yfinance as yf
            from data_pipeline import _format_yf_symbol
            _sym = _format_yf_symbol(ticker, category)
            _h = yf.Ticker(_sym).history(period=period, auto_adjust=True)
            if not _h.empty and len(_h) >= 5:
                return _h[["Open","High","Low","Close"]].dropna()
        except Exception:
            pass
        return pd.DataFrame()

    # BIST - simdilik yfinance (v1.7'de borsapy.Ticker'a gecilecek)
    from data_pipeline import _format_yf_symbol
    sym = _format_yf_symbol(ticker, category)
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

def fmt_tr(val, decimals=2):
    """Float → Türkçe format: 1.234,56"""
    if val is None: return "—"
    sign = "-" if val < 0 else ""
    s = f"{abs(val):,.{decimals}f}"          # "1,234.56"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return sign + s

def parse_tr(s):
    """Türkçe format string → float: '1.234,56' → 1234.56"""
    try:
        return float(str(s).replace(".", "").replace(",", "."))
    except Exception:
        return 0.0


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
    # purchase_date sütunu yoksa ekle (migration)
    try:
        conn.execute("ALTER TABLE portfolio ADD COLUMN purchase_date TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE portfolio ADD COLUMN unit_type TEXT DEFAULT 'Adet'")
        conn.commit()
    except Exception:
        pass
    rows = conn.execute(
        "SELECT id, asset_type, ticker, quantity, avg_cost, note, added_at, "
        "COALESCE(purchase_date,'') as purchase_date, "
        "COALESCE(unit_type,'Adet') as unit_type "
        "FROM portfolio WHERE user_id=? ORDER BY purchase_date ASC, added_at ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_portfolio_item(ticker: str, adet: float, maliyet: float,
                        asset_type: str = "BIST", note: str = "",
                        purchase_date: str = "", unit_type: str = "Adet") -> bool:
    from db import get_conn
    user_id = (_cur_user or {}).get("id")
    if not user_id: return False
    conn = get_conn()
    for _col in ["purchase_date TEXT DEFAULT ''", "unit_type TEXT DEFAULT 'Adet'"]:
        try:
            conn.execute(f"ALTER TABLE portfolio ADD COLUMN {_col}")
            conn.commit()
        except Exception:
            pass
    conn.execute(
        "INSERT INTO portfolio (user_id,asset_type,ticker,quantity,avg_cost,note,purchase_date,unit_type) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (user_id, asset_type, ticker.strip().upper(), adet, maliyet, note, purchase_date, unit_type)
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
        # [email] nested section (toml: [email] smtp_user=...)
        _es = dict(s.get("email", {}) or {})
        # Üst seviye veya [email] altındaki anahtarları kontrol et
        email_user = (s.get("EMAIL_USER") or s.get("SMTP_USER")
                      or s.get("smtp_user")
                      or _es.get("smtp_user") or "")
        email_pass = (s.get("EMAIL_PASS") or s.get("SMTP_PASS")
                      or s.get("smtp_pass")
                      or _es.get("smtp_pass") or "")
        email_addr = (s.get("EMAIL_ADDRESS") or s.get("address")
                      or s.get("ADMIN_EMAIL")
                      or _es.get("address") or "")
        smtp_host  = (s.get("SMTP_HOST") or _es.get("smtp_host","smtp.gmail.com"))
        smtp_port  = int(s.get("SMTP_PORT") or _es.get("smtp_port", 587))
        if email_user and email_pass:
            return {
                "address":   email_addr or email_user,
                "smtp_host": smtp_host,
                "smtp_port": smtp_port,
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
        [data-testid="stSidebar"] [data-testid="stExpander"] label p,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stCaptionContainer"] {
            color:#1b2a4a!important;font-weight:600!important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] .stButton button p,
        [data-testid="stSidebar"] [data-testid="stExpander"] .stButton>button p {
            color:#ffffff!important;font-weight:700!important;
        }
        </style>""", unsafe_allow_html=True)
        ecfg=load_email_cfg()
        e_addr=st.text_input("Alıcı E-posta",value=ecfg.get("address",""))
        e_t1=st.text_input("1. Gönderim (HH:MM)",value=ecfg.get("times",["08:30"])[0])
        e_t2=st.text_input("2. Gönderim (HH:MM)",value=ecfg.get("times",["08:30","11:30"])[-1])
        st.markdown('<style>[data-testid="stSidebar"] button{color:#ffffff!important;font-weight:700!important;opacity:1!important;}</style>', unsafe_allow_html=True)
        if st.button("Ayarları Kaydet", key="ecfg_save", use_container_width=True):
            save_email_cfg({"address":e_addr,"smtp_host":"smtp.gmail.com","smtp_port":587,
                             "smtp_user":ecfg.get("smtp_user",""),
                             "smtp_pass":ecfg.get("smtp_pass",""),
                             "times":[e_t1,e_t2],
                             "tcmb_key":ecfg.get("tcmb_key","")})
            st.success("Kaydedildi!")
        if st.button("Şimdi Gönder", key="send_now", use_container_width=True):
            try:
                # Streamlit Cloud için: Secrets'dan cfg oku, email_config.json'a yaz
                import json as _ej
                _ecfg = load_email_cfg()
                if _ecfg.get("smtp_user") and _ecfg.get("smtp_pass"):
                    with open("email_config.json", "w", encoding="utf-8") as _ef:
                        _ej.dump(_ecfg, _ef)
                from emailer import send_report
                df_uni2=load_universe()
                pf=load_portfolio()
                send_report(df_uni2,pf,budget,risk,max_assets,cfg=_ecfg)
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
    portfolio = load_portfolio()

    # ── Yeni Pozisyon Ekle ──────────────────────────────────────
    with st.expander("Yeni Pozisyon Ekle", expanded=not portfolio):
        if df_uni.empty:
            st.warning("`python worker.py` ile veriyi önce oluşturun.")
        else:
            df_uni_copy = df_uni.copy()
            df_uni_copy["_label"] = df_uni_copy["Ticker"] + " — " + df_uni_copy["Ad"].astype(str).str[:50]
            labels       = df_uni_copy["_label"].tolist()
            tickers_list = df_uni_copy["Ticker"].tolist()
            cats_list    = df_uni_copy["Kategori"].tolist()
            sel_label = st.selectbox("Varlık", labels, key="pf_varlik_sel")
            idx_sel   = labels.index(sel_label)
            pt        = tickers_list[idx_sel]
            pt_cat    = cats_list[idx_sel]
            _pm       = df_uni[df_uni["Ticker"] == pt]
            auto_price = float(_pm["Son_Fiyat"].iloc[0]) if not _pm.empty and float(_pm["Son_Fiyat"].iloc[0]) > 0 else 0.0
            f_c1, f_c2, f_c3, f_c4 = st.columns([1.2, 0.9, 0.8, 1.2])
            with f_c1:
                import datetime as _dt
                satin_tarih = st.date_input("Satın Alma Tarihi", value=_dt.date.today(),
                                            key="pf_tarih", format="DD.MM.YYYY")
            with f_c2:
                pa_str = st.text_input("Birim (miktar)", value="1", key="pf_adet",
                                       placeholder="Örn: 5,06")
                try:    pa = parse_tr(pa_str)
                except: pa = 0.0
            with f_c3:
                unit_type = st.selectbox("Birim Türü",
                    ["Adet","Gram","Lot","Ons","Varil","Ton","kg","m²","Diğer"], key="pf_unit")
            with f_c4:
                _ph = fmt_tr(auto_price,4) if auto_price>0 else "Örn: 6.277,08"
                pm_str = st.text_input("Alış Fiyatı (birim, TL)", value="",
                                       key="pf_maliyet", placeholder=_ph)
                try:    pm = parse_tr(pm_str) if pm_str.strip() else auto_price
                except: pm = auto_price
            if auto_price>0 and pa>0:
                st.caption(f"Güncel piyasa fiyatı: {fmt_tr(auto_price,4)} TL"
                           f"  |  Tahmini toplam: {fmt_tr(pa*auto_price)} TL")
            pf_note = st.text_input("Not (isteğe bağlı)", key="pf_not",
                                    placeholder="Örn: İlk alım, uzun vadeli")
            if st.button("EKLE", use_container_width=True, key="pf_ekle"):
                if pa > 0:
                    add_portfolio_item(pt, pa, pm, asset_type=pt_cat, note=pf_note,
                                       purchase_date=satin_tarih.strftime("%Y-%m-%d"),
                                       unit_type=unit_type)
                    st.success(f"{pt} eklendi — {fmt_tr(pa,4)} {unit_type} @ {fmt_tr(pm,4)} TL")
                    st.rerun()
                else:
                    st.warning("Birim 0'dan büyük olmalı.")

    if not portfolio:
        st.info("Henüz pozisyon yok. Yukarıdan ekleyebilirsin.")
        st.stop()

    import datetime as _dt, pandas as _pd

    # ── Portföy Varlıkları Tablosu ───────────────────────────────
    st.divider()
    st.subheader("Portföy Varlıkları Tablosu")

    # v1.6.1: Portfoy degerleme icin Harem alis fiyati (kullanicinin satinca alacagi)
    # Sadece 4 ana metal (gram-altin/gumus/platin, ons-altin TL) icin Harem-spesifik;
    # diger varliklarda Son_Fiyat (canlidoviz mid / yfinance last) kullanilir.
    _pf_tickers = [pos["ticker"] for pos in portfolio]
    _satis_fiyatlari = _ld_portfolio_prices(df_uni, _pf_tickers)

    # Tablo verisi
    _pf_rows = []
    _id_map  = {}
    for pos in portfolio:
        _tkr  = pos["ticker"]
        _adet = float(pos["quantity"])
        _alis = float(pos["avg_cost"])
        _unit = pos.get("unit_type","Adet") or "Adet"
        _traw = pos.get("purchase_date","")
        _tg   = (_dt.datetime.strptime(_traw,"%Y-%m-%d").strftime("%d.%m.%Y")
                 if _traw and len(_traw)==10 else _traw or "—")
        _match  = df_uni[df_uni["Ticker"]==_tkr]
        # Once Harem alis (varsa), yoksa Son_Fiyat'a duser
        _guncel = _satis_fiyatlari.get(_tkr, 0.0)
        if _guncel <= 0 and not _match.empty:
            _try = float(_match["Son_Fiyat"].iloc[0])
            _guncel = _try if _try > 0 else 0.0
        if not _match.empty:
            _row = _match.iloc[0]
            def _sf(v,d):
                try: fv=float(v); return d if _pd.isna(fv) else fv
                except: return d
            _skor = optima_score(_sf(_row.get("RSI"),50.0),
                                  _sf(_row.get("Ret1M"),0.0),
                                  _sf(_row.get("Vol_1Y"),30.0))
        else:
            _skor = 0.0
        _toplam = _adet * _guncel
        _kz_pct = ((_guncel/_alis-1)*100) if _alis>0 else 0.0
        _id_map[_tkr + "_" + str(pos["id"])] = pos["id"]
        _pf_rows.append({
            "Ticker":       _tkr,
            "Tarih":        _tg,
            "Miktar":       _adet,
            "Birim":        _unit,
            "Alış (TL)":    _alis,
            "Güncel (TL)":  _guncel,
            "Toplam (TL)":  _toplam,
            "K/Z (%)":      _kz_pct,
            "Optima Skor":  _skor,
            "_id":          pos["id"],
        })

    import pandas as _pd2
    df_pf = _pd2.DataFrame(_pf_rows)
    df_show = df_pf.drop(columns=["_id"])

    # st.dataframe — BIST formatıyla aynı
    _event = st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Miktar":      st.column_config.NumberColumn(format="%.4f"),
            "Alış (TL)":  st.column_config.NumberColumn(format="%.4f"),
            "Güncel (TL)":st.column_config.NumberColumn(format="%.4f"),
            "Toplam (TL)":st.column_config.NumberColumn(format="%.2f"),
            "K/Z (%)":    st.column_config.NumberColumn(format="%+.2f%%"),
            "Optima Skor":st.column_config.NumberColumn(format="%.1f"),
        }
    )

    # Toplam satırı
    _total_val = df_pf["Toplam (TL)"].sum()
    _total_kz  = (df_pf["Toplam (TL)"] - df_pf["Miktar"]*df_pf["Alış (TL)"]).sum()
    _tcc = "#27ae60" if _total_kz>=0 else "#e74c3c"
    _tcs = "+" if _total_kz>=0 else ""
    st.markdown(
        f"<div style='border-top:2px solid #2c3e6b;padding:8px 4px;"
        f"display:flex;justify-content:space-between;'>"
        f"<b style='font-size:13px;color:#6c7a9c;'>TOPLAM PORTFÖY DEĞERİ</b>"
        f"<b style='font-size:17px;color:#1b2a4a;'>{fmt_tr(_total_val)} TL"
        f"&nbsp;<span style='font-size:13px;color:{_tcc};'>"
        f"{_tcs}{fmt_tr(_total_kz)} TL</span></b></div>",
        unsafe_allow_html=True
    )

    # Seçili satır — Sil + Analiz
    _sel = _event.selection.rows if hasattr(_event,"selection") else []
    if _sel:
        _si  = _sel[0]
        _row_data = _pf_rows[_si]
        _sel_tkr  = _row_data["Ticker"]
        _sel_id   = _row_data["_id"]
        _ca, _cb  = st.columns([1, 5])
        if _ca.button(f"Sil: {_sel_tkr}", type="secondary", key="pf_sil"):
            delete_portfolio_item(_sel_id)
            st.rerun()

        # Analiz
        _sm = df_uni[df_uni["Ticker"]==_sel_tkr]
        if not _sm.empty:
            _sr = _sm.iloc[0]
            st.divider()
            st.subheader(f"Detay: {_sel_tkr} — {str(_sr['Ad'])[:60]}")
            _pm2 = {"1 Ay":"1mo","3 Ay":"3mo","6 Ay":"6mo","1 Yıl":"1y","5 Yıl":"5y"}
            _pl  = st.radio("Periyot", list(_pm2.keys()), horizontal=True, key="pf_per")
            with st.spinner("Yükleniyor..."):
                _d = enrich(_sr, _pm2[_pl])
                _sig_lbl, _sig_cls = get_signal(_d["score"],_d["rsi"],_d["trend"])
            _m1,_m2,_m3,_m4,_m5 = st.columns(5)
            _m1.metric("Son Fiyat",   f"{float(_sr['Son_Fiyat']):,.4f}")
            _m2.metric("Optima Skor", f"{_d['score']:.1f}")
            _m3.metric("RSI (14)",    f"{_d['rsi']:.1f}")
            _m4.metric("1A Getiri %", f"{_d['ret1m']:+.2f}%")
            _m5.metric("Yıllık Vol %",f"{_d['vol']:.1f}%")
            _sc = SIG_COLORS.get(_sig_cls,"#666")
            st.markdown(f'''<div class="ts-card" style="border-left:5px solid {_sc};padding:12px 18px;">
      <span class="ts-sig {_sig_cls}">{_sig_lbl}</span>
      <span style="color:#6c7a9c;font-size:12px;margin-left:14px">
        Trend: <b>{_d["trend"]}</b> | Optima Skor: <b>{_d["score"]}/100</b> | MACD: <b>{_d["macd"]:.4f}</b>
      </span></div>''', unsafe_allow_html=True)
            if not _d["hist"].empty:
                _fig = candle_fig(_d["hist"],_sel_tkr)
                if _fig: st.plotly_chart(_fig, use_container_width=True)
            else:
                st.info(f"{_sel_tkr} için geçmiş fiyat verisi yüklenemedi.")

    st.caption("Analiz için tablodaki varlığın solundaki kutucuğu işaretleyin.")



# ══════ KATEGORİ SAYFALARI ══════
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
        st.info("Analiz için tablodaki varlığın solundaki kutucuğu işaretleyin.")
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


elif page=="Makro Göstergeler":
    st.title("Makro Göstergeler")
    st.caption("MKK Veri Analiz Platformu (VAP) — Türkiye sermaye piyasası yatırımcı ve saklama istatistikleri. Haftalık güncellenir.")

    st.subheader("VAP — Veri Analiz Platformu")
    st.markdown(
        "MKK (Merkezi Kayıt Kuruluşu) tarafından yönetilen VAP, Türkiye sermaye piyasasına ait "
        "yatırımcı sayıları, saklama değerleri, yerli/yabancı analizleri ve endeks bazlı verileri "
        "haftalık olarak yayınlamaktadır. Aşağıdaki bağlantılardan ilgili sayfaya doğrudan ulaşabilirsiniz."
    )

    VAP_LINKS = [
        {
            "baslik": "Genel Bakış",
            "aciklama": "Toplam yatırımcı, bakiyeli hesap sayısı ve saklanan menkul kıymet değeri.",
            "url": "https://www.vap.org.tr/",
            "ikon": "📊",
        },
        {
            "baslik": "Yaş Grupları Bazında Yatırımcı Sayıları",
            "aciklama": "Demografik dağılım — yaş grubu ve cinsiyet bazında yatırımcı profili.",
            "url": "https://www.vap.org.tr/yas-gruplari-bazinda-yatirimci-sayilari",
            "ikon": "👥",
        },
        {
            "baslik": "Yerli / Yabancı Pay Senedi Analizi",
            "aciklama": "Yerli ve yabancı yatırımcıların pay senedi portföy dağılımı.",
            "url": "https://www.vap.org.tr/yerli-yabanci-pay-senedi-analizi",
            "ikon": "🌍",
        },
        {
            "baslik": "Yabancı Yatırımcı Sayıları (İlk 10 Ülke)",
            "aciklama": "Ülke bazında yabancı yatırımcı sayıları ve portföy değerleri.",
            "url": "https://www.vap.org.tr/pay-senedi-yabanci-yatirimci-sayilari-ilk-10-ulke",
            "ikon": "🗺️",
        },
        {
            "baslik": "BIST Endeksleri Bazında Portföy Değerleri",
            "aciklama": "9 farklı BIST endeksi için yatırımcı sayısı ve portföy değeri.",
            "url": "https://www.vap.org.tr/bist-endeksleri-bazinda-portfoy-degerleri",
            "ikon": "📈",
        },
        {
            "baslik": "Dönemsel Finansal Oranlar",
            "aciklama": "BIST şirketlerinin F/K, PD/DD, temettü verimi gibi finansal oranları.",
            "url": "https://www.vap.org.tr/donemsel-finansal-oranlar",
            "ikon": "🔢",
        },
        {
            "baslik": "REKS — Risk İştahı Endeksi",
            "aciklama": "Türkiye sermaye piyasası risk iştahı endeksi ve tarihsel trendi.",
            "url": "https://www.vap.org.tr/reks",
            "ikon": "⚡",
        },
        {
            "baslik": "MKK Aylık Piyasa Bülteni",
            "aciklama": "Yatırımcı ve piyasa verilerinin aylık özet raporu (PDF).",
            "url": "https://www.mkk.com.tr/veri-hizmetleri/mkk-aylik-piyasa-bulteni",
            "ikon": "📄",
        },
    ]

    _makro_cols = st.columns(2)
    for _mi, _link in enumerate(VAP_LINKS):
        with _makro_cols[_mi % 2]:
            st.markdown(
                f'''<a href="{_link['url']}" target="_blank" style="text-decoration:none;">
                <div style="background:#fff;border:1.5px solid #c8d6e8;border-radius:10px;
                            padding:16px 18px;margin-bottom:14px;cursor:pointer;">
                    <div style="font-size:22px;margin-bottom:6px;">{_link['ikon']}</div>
                    <div style="font-size:14px;font-weight:700;color:#1b2a4a;
                                margin-bottom:4px;">{_link['baslik']}</div>
                    <div style="font-size:12px;color:#6c7a9c;">{_link['aciklama']}</div>
                </div></a>''',
                unsafe_allow_html=True
            )

    st.divider()
    st.subheader("Güncel Piyasa Verileri (MKK)")
    st.markdown("_Güncel veriler için yukarıdaki VAP bağlantılarını kullanın._")

    _mkk_cols = st.columns(5)
    _mkk_data = [
        ("Saklanan MK Değeri", "35,14 Trilyon ₺"),
        ("Toplam Yatırımcı",   "38,57 Milyon"),
        ("Toplam Hesap",       "92,60 Milyon"),
        ("Bakiyeli Yatırımcı", "10,64 Milyon"),
        ("Bakiyeli Hesap",     "15,45 Milyon"),
    ]
    for _col, (_lbl, _val) in zip(_mkk_cols, _mkk_data):
        with _col:
            st.metric(_lbl, _val)
    st.caption("Kaynak: vap.org.tr | MKK Merkezi Kayıt Kuruluşu. Veriler haftalık güncellenmektedir.")

elif page=="Yardım":
    is_admin = _cur_user.get("is_admin", False)

    if is_admin:
        st.title("Admin El Kitabi")
        st.caption("TrendSurf Optima — Sistem Yonetici Dokumantasyonu")

        with st.expander("1. Sistem Mimarisi", expanded=False):
            st.markdown("""
**Dosya Yapisi** — `C:/Users/bahri/Desktop/TrendSurf_Optima/`

| Dosya | Aciklama |
|-------|----------|
| `app.py` | Ana Streamlit uygulamasi |
| `worker.py` | Veri cekme ve evren olusturma motoru |
| `db.py` | SQLite veritabani baglantisi |
| `auth.py` | Kullanici kimlik dogrulama |
| `auth_reset.py` | Sifre sifirlama |
| `admin.py` | Admin panel fonksiyonlari |
| `emailer.py` | E-posta rapor sistemi |
| `bigpara_client.py` | Bigpara altin/gumus TL fiyat yedek kaynak |
| `halka_arz_client.py` | KAP XHARZ endeks verileri |
| `temettu_client.py` | KAP XTMTU + yfinance temettü verileri |
| `tefas_client.py` | TEFAS fon verileri |
| `kap_client.py` | KAP temel analiz verileri |
| `tcmb_client.py` | TCMB doviz kuru yedek kaynak |
| `signals.py` | Sinyal hesaplama motoru |
| `optimized_universe.csv` | Worker ciktisi — tum varliklar |
| `KAP_BIST.xlsx` | BIST hisse sembol/slug esleme (771 hisse) |
| `Endeksler.xlsx` | Endeks uye listeleri (fallback) |

**Veri Akisi:** `worker.py` → `optimized_universe.csv` → `app.py` → kullanici

**Varlik Sayilari:** BIST 610 | TEFAS 1347 | Kripto 19 | Maden 12 | Doviz 12
""")

        with st.expander("2. Veri Kaynaklari ve Yedek Mekanizmalari", expanded=False):
            st.markdown("""
**BIST Fiyatlari:**
- Birincil: yfinance (.IS suffix)
- Yedek: optimized_universe.csv son bilinen fiyat

**TEFAS Fon Verileri:**
- Birincil: TEFAS Next.js API (`www.tefas.gov.tr/api/funds/`)
- Yedek: pytefas kutuphanesi

**Maden Fiyatlari (TL bazli):**
- Birincil: Bigpara HTML scraping (gram altin, gumus)
- Yedek: yfinance (GC=F) x USDTRY

**Doviz Kurlari:**
- Birincil: yfinance (=X suffix)
- Yedek: TCMB XML API — 11/12 kur
- Son yedek: EVDS API (TCMB_KEY gerekli: 5F0yYjCHDf)

**Kripto:**
- Birincil: yfinance (BTC-USD vb.)
- Yedek: Bigpara kripto fiyatlari

**Temel Analiz (BIST):**
- kap_client.py → kap.org.tr sirket sayfalari
- yfinance info (P/E, beta, dividendYield)

**Halka Arz / Tetemttu:**
- KAP RSC endpoint (Next.js) → endeks uyeleri
- Yedek: Endeksler.xlsx
""")

        with st.expander("3. GitHub ve Deployment", expanded=False):
            st.markdown("""
**GitHub Repo:** `github.com/cbguler/trendsurf-optima` (private)

**Streamlit Cloud:**
`https://trendsurf-optima-mxqgu6qvkmqbkmaorwmquj.streamlit.app`

**Streamlit Cloud Secrets** (App Settings → Secrets):
```
EMAIL_USER    = "bahriguler@gmail.com"
EMAIL_PASS    = "xxxx xxxx xxxx xxxx"
EMAIL_ADDRESS = "bahriguler@gmail.com"
ADMIN_EMAIL   = "bahriguler@gmail.com"
ADMIN_PASS    = "..."
ADMIN_NAME    = "Bahri"
TCMB_KEY      = "5F0yYjCHDf"
```

**CSV Manuel Guncelleme:**
```
cd C:/Users/bahri/Desktop/TrendSurf_Optima
python worker.py
git add -f optimized_universe.csv
git commit -m "veri guncelleme"
git push origin main
```

**Task Scheduler:** Her sabah 08:00 — `guncelle_ve_push.bat`
""")

        with st.expander("4. Kullanici Yonetimi", expanded=False):
            st.markdown("""
**Kullanici Tipleri:**

| Tip | Aciklama |
|-----|----------|
| `free` | Sinirli erisim |
| `pro` | Temel ozellikler |
| `premium` | Tum ozellikler |
| `admin` | Sistem yoneticisi |

**Yeni Abone Onaylama:** Admin Paneli → Bekleyen Kullanicilar → Onayla

**Sifre Sifirlama:**
- `python auth_reset.py` (lokal)
- Veya Giris ekrani → Sifremi Unuttum

**SQLite Veritabani:** `trendsurf.db`
- Tablolar: `users`, `sessions`, `portfolio`, `reset_tokens`
- Streamlit Cloud'da Reboot yaparsan sifirlanir — Reboot yerine F5 kullan
""")

        with st.expander("5. E-posta Sistemi", expanded=False):
            st.markdown("""
**Gonderim Zamanlayici:**
- Windows Task Scheduler: `emailler.py` — 08:30 ve 11:30
- Manuel: Sol menu → E-posta Ayarlari → Simdi Gonder

**Gmail App Password Yenileme:**
1. `myaccount.google.com/apppasswords` adresine git
2. Yeni App Password olustur (TrendSurf)
3. Streamlit Cloud Secrets → EMAIL_PASS guncelle
4. `email_config.json` dosyasini da guncelle

**email_config.json yapisi:**
```json
{
  "address": "bahriguler@gmail.com",
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "bahriguler@gmail.com",
  "smtp_pass": "uygulama sifresi",
  "times": ["08:30", "11:30"],
  "tcmb_key": "5F0yYjCHDf"
}
```
""")

        with st.expander("6. Sik Karsilasilan Sorunlar", expanded=False):
            st.markdown("""
| Sorun | Neden | Cozum |
|-------|-------|-------|
| BIST 97 hisse geliyor | GitHub Actions yfinance kisiti | worker.py lokalde calistir, push et |
| Altin fiyati yanlis | yfinance ons/gram karisikligi | Bigpara birincil — otomatik duzelmeli |
| Turkce karakter bozuk | KAP API encoding | latin-1 UTF-8 fix_encoding'de cozuldu |
| E-posta gitmiyor | Streamlit Secrets eksik | EMAIL_USER/EMAIL_PASS ekle |
| Uygulama acilamiyor | Streamlit gizlilik | share.streamlit.io → Settings → Public |
| Veritabani sifirlanmis | Streamlit Cloud reboot | Beklenen davranis — F5 kullan |
| CSV push edilemiyor | gitignore sorunu | `git add -f optimized_universe.csv` |
""")

    else:
        st.title("Yardim — Kullanim Kilavuzu")
        st.caption("TrendSurf Optima — Finansal Varlik Takip ve Sinyal Terminali")

        with st.expander("Baslangic — Kayit ve Giris", expanded=True):
            st.markdown("""
**Hesap Olusturma:**
1. Giris ekraninda **Kayit Ol** sekmesine tiklayin
2. Ad Soyad, e-posta ve sifrenizi girin (en az 8 karakter)
3. Hesabiniz admin onayindan sonra aktif olur

**Giris Yapma:**
- E-posta ve sifrenizle giris yapin
- **Beni Hatirla** kutusunu isaretlerseniz otomatik giris aktif olur

**Sifremi Unuttum:**
- Giris ekraninda **Sifremi Unuttum** sekmesi → e-posta adresinizi girin
- Sifirlama baglantisi e-postaniza gelir
""")

        with st.expander("Ana Sayfa — Portfoy Optimizasyonu", expanded=False):
            st.markdown("""
Ana Sayfa, butce ve risk tercihine gore en iyi yatirim firsatlarini listeler.

**Sol Panelden Ayarlar:**
- **Portfoy Butcesi (TL):** Yatirim dusundugunuz toplam tutar
- **Risk Toleransi:** Cok Dusuk → Cok Yuksek (5 seviye)
- **Max Varlik Sayisi:** Portfoyde kac farkli varlik olsun (5-20)

**Oneri Tablosu Sutunlari:**

| Sutun | Aciklama |
|-------|----------|
| Kategori | BIST, TEFAS, Doviz, Maden, Kripto |
| Optima Skoru | 0-100 bileşik puan |
| Sinyal | Guclu Al / Kademeli Al / Tut Izle / Sat |
| RSI | Goreceli guc endeksi (30 alti asiri satim, 70 uzeri asiri alim) |
| 1A Getiri % | Son 1 aylik getiri |
| Lot | Butcenize gore onerilen alim adedi |

**Optima Skoru:** RSI Zonu (25%) + Momentum (35%) + Volatilite (15%) + Temel Analiz (25%)

> Bu sistem yatirim tavsiyesi vermez. Kararlar tamamen size aittir.
""")

        with st.expander("Portfoyum — Pozisyon Takibi", expanded=False):
            st.markdown("""
**Yeni Pozisyon Ekleme:**
1. **Yeni Pozisyon Ekle** bolumunu acin
2. Listeden varlik secin
3. Adet, Alis Maliyeti (TL) ve isterseniz Not girin
4. **Pozisyon Ekle** butonuna tiklayin

**Fiyat Girisi:** Ondalik ayirici virgul → `6.480,00`

**Portfoy Tablosu:**
- Guncel Fiyat: Bigpara / yfinance anlık veri
- Toplam Deger: Adet × Guncel Fiyat  
- K/Z: (Guncel - Alis) / Alis × 100

**E-posta Raporu (Sol Menu):**
1. Alici e-posta adresinizi girin
2. Gonderim saatlerini belirleyin
3. **Ayarlari Kaydet** ile saatleri kaydedin
4. **Simdi Gonder** ile anlik rapor alin
""")

        with st.expander("BIST — Turk Hisse Senetleri", expanded=False):
            st.markdown("""
~610 Borsa Istanbul hissesini Optima Skoru'na gore listeler.

**Filtreleme:** Ticker/sirket adi ara, sinyal turune gore filtrele, RSI araligini sec

**KAP Linki:** Her hissenin **Goruntule** linki KAP sirket sayfasina acar

**Sayfalama:** Tabloda 50 hisse gosterilir, altta sayfa secimi yapabilirsiniz
""")

        with st.expander("TEFAS — Yatirim Fonlari", expanded=False):
            st.markdown("""
~1347 yatirim fonunu listeler.

**Fon Turu Filtresi:** Hisse Senedi Yogun, Karma, Tahvil, Altin, Para Piyasasi vb.

**Getiri Karsilastirmasi:** 1A, 3A, 6A ve 1Y getirilerini yan yana gorun

**TEFAS Linki:** Her fonun linki TEFAS detay sayfasina acar
""")

        with st.expander("Doviz, Madenler, Kriptolar", expanded=False):
            st.markdown("""
**Doviz:** 12 TRY bazli kur — Kaynak: yfinance, yedek: TCMB XML

**Madenler:** 12 emtia (Altin, Gumus, Platin, Petrol vb.)
- Altin ve Gumus: Bigpara (gercek TL/gram Turkiye fiyati)
- Diger: yfinance × USDTRY

**Kriptolar:** 19 kripto para — BTC, ETH, BNB, SOL vb.
- Kaynak: yfinance (USD) × USDTRY

Her sayfada Optima Skoru, RSI, 1A Getiri ve guncel fiyat gosterilir.
""")

        with st.expander("Halka Arz ve Temettu", expanded=False):
            st.markdown("""
**Halka Arz (XHARZ):**
- BIST Halka Arz Endeksi uyeleri — KAP'tan gunluk cekiliyor
- Her sirketin KAP sayfasina **Goruntule** linki ile ulasabilirsiniz

**Temettu (XTMTU):**
- BIST Temettu Endeksi uyeleri + yfinance temettu verileri
- Temettu/Hisse, Verim (%), Ex-Date, Siklik
- Ex-Date'e gore sirali (yakin tarih uste)

**CSV Indir:** Her sayfada tabloyu Excel olarak indirebilirsiniz
""")

        with st.expander("Makro Gostergeler", expanded=False):
            st.markdown("""
MKK Veri Analiz Platformu (vap.org.tr) baglantilari ve ozet veriler.

**Kart Baglantilari:**
- Genel Bakis, Yas Gruplari, Yerli/Yabanci Analizi
- BIST Endeks Bazli Portfoy, Finansal Oranlar
- REKS Risk Istahi Endeksi, MKK Aylik Bulteni

Her karta tiklayin — VAP sayfasi yeni sekmede acilir.
""")

        with st.expander("Sik Sorulan Sorular", expanded=False):
            st.markdown("""
**Veriler ne siklikla guncellenir?**
Her gun sabah 08:00'de otomatik guncellenir. TEFAS/Halka Arz 4 saatlik onbellekten gelir.

**Optima Skoru ne anlama gelir?**
0-100 arasi bileşik puan. 80+ Guclu Al, 60-80 Kademeli Al, 40-60 Tut Izle, 40- Sat.

**Portfoy verileri kayboldu?**
Portfoy veritabaninda saklanir. Cikis yapip tekrar giris yapin.

**Uygulama yavash aciliyor?**
Uzun sure kullanilmayinca uyku moduna giriyor. Ilk acilista 1-2 dakika normaldir.
""")
            if not _ex:
                try:
                    register_user(_asec["email"], _asec["password"], "Admin")
                except Exception:
                    pass
