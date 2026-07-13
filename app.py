"""TrendSurf Optima — Terminal v5 | streamlit run app.py"""
import streamlit as st, pandas as pd, numpy as np, os, json, base64, time
import streamlit.components.v1 as components

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
/* v2.0.1 - Stale (script running) opacity'yi GIZLE
   Streamlit rerun sirasinda UI elemanlarini soluklastiriyordu (~50% opacity).
   Autorefresh her 5 dakikada tetiklendigi icin kullanici bu bulanikligi
   gormeye basliyordu. Bu CSS opacity'yi sabit 1.0'a kilitliyor, fade-out
   efekti kayboluyor. Streamlit'in stale gostergesi gorsel ama hicbir
   fonksiyonel anlam tasimiyor (data yeniden cekiliyor olsa bile UI gorunur).
   Selektorler: hem element-container hem stApp ve block-container icin tum
   olasi stale variantlarini hedefliyor. */
[data-stale="true"],[data-test-stale="true"],
.element-container[data-stale="true"],
.stApp[data-test-script-state="running"] [data-stale="true"],
.stApp[data-test-script-state="running"] .element-container,
[data-testid="stAppViewContainer"][data-stale="true"],
[data-testid="stSidebar"][data-stale="true"]{
    opacity:1!important;
    filter:none!important;
    transition:none!important;
}
.stApp,[data-testid="stAppViewContainer"],.main,.block-container{background:#f0f4f8!important;}
/* v2.0.4.38: Mobilde sidebar kapaliyken acma oku (>>) sayfayla birlikte
   kayip yukari gitmeden gorunmez oluyordu - tablonun altindaysaniz sidebar'i
   acmak icin en tepeye scroll etmek gerekiyordu. Sabit (fixed) konuma
   alindi, artik her zaman erisilebilir. */
[data-testid="collapsedControl"]{
    position:fixed!important; top:8px!important; left:8px!important;
    z-index:999999!important; background:#ffffffcc!important;
    border-radius:8px!important;
}
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
PAGES = ["Ana Sayfa","Portföyüm","BIST","TEFAS","Döviz","Değerli Madenler","Kriptolar","Halka Arz","Temettü","Makro Göstergeler","Yardım"]
CAT   = {"BIST":"BIST","TEFAS":"TEFAS","Döviz":"DOVIZ","Değerli Madenler":"MADEN","Kriptolar":"KRIPTO"}
SIG_COLORS = {"sig-g":"#00732f","sig-k":"#1a7a3a","sig-t":"#8a5e00","sig-s":"#c0451b","sig-n":"#b71c1c"}

def _bist_seans_acik() -> bool:
    """BIST seans saatleri icinde miyiz? (Hafta ici 10:00-18:00 TRT)

    v2.0.4.50: BIST fiyatlarini otomatik canli yenilemeyi sadece bu
    pencerede tetiklemek icin - hafta sonu/mesai disi zaten piyasa
    kapali oldugundan CSV degeri (son kapanis) esasen dogru, gereksiz
    API cagrisi/gecikme yaratmamak icin canli yenileme atlanir.
    """
    import datetime as _dt
    try:
        _simdi = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=3)))  # TRT = UTC+3
    except Exception:
        _simdi = _dt.datetime.now()
    if _simdi.weekday() >= 5:  # 5=Cumartesi, 6=Pazar
        return False
    return _dt.time(10, 0) <= _simdi.time() <= _dt.time(18, 0)

# ── Canli veri katmani (borsapy) - v1.6+ ─────────────────────────────────────
from live_data import (
    filter_universe as _ld_filter_universe,
    rename_existing_maden as _ld_rename_maden,
    extend_maden_universe as _ld_extend_maden,
    refresh_fx_maden_kripto as _ld_refresh_overlay,
    refresh_bist as _ld_refresh_bist,
    refresh_bist_selective as _ld_refresh_bist_sel,  # v1.9.7
    portfolio_value_prices as _ld_portfolio_prices,
    get_fx_history as _ld_fx_history,
    get_maden_history as _ld_maden_history,
    get_kripto_history as _ld_kripto_history,
    BORSAPY_OK as _LIVE_BORSAPY_OK,
    status_summary as _ld_status,
)

# v1.9.7 - Otomatik sayfa yenileme (streamlit-autorefresh paketi)
try:
    from streamlit_autorefresh import st_autorefresh as _st_autorefresh
    _AUTOREFRESH_OK = True
except ImportError:
    _AUTOREFRESH_OK = False
    def _st_autorefresh(*args, **kwargs):
        """Fallback (paket yoksa no-op)."""
        return 0

# v1.9.9 - Beni Hatirla: tarayici cookie persistence
# v1.9.9.1 - streamlit-cookies-controller paketi async timing sorunlari yaratti
# Bunun yerine localStorage tabanli JavaScript yontemi kullaniyoruz (daha guvenilir).
# (streamlit_cookies_controller import'u kaldirildi - artik gerek yok)
_COOKIE_OK = True  # localStorage her zaman erisilebilir

# v1.9.9.3.1 - components.v1.html icin module-level import (scope sorunu engellenir)
# Asagidaki render_auth_gate ve logout button'da kullaniliyor.
import streamlit.components.v1 as _stc_v1
import extra_streamlit_components as stx

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
# v2.0 - Kar Realizasyonu Uyari Sistemi (alert_settings + peak_tracker tablolari Supabase'de)
from alert_settings import (
    load_alert_settings, save_alert_settings,
    DEFAULTS as ALERT_DEFAULTS,
    ALERT_MODES, EMIR_FORMULS,
)
# v2.0 asama 3a - Peak Tracker (peak/threshold mantigi)
from peak_tracker import (
    evaluate_user_alerts, get_user_peaks, reset_peaks_for_user,
)
# v2.0 asama 3b - Peak Alert Emailer (uyari maillerini gonderir)
from peak_alert_emailer import send_peak_alert


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
                                extend_maden_universe, refresh_fx_maden_kripto,
                                refresh_bist)

        # Universe CSV'yi yukle (worker.py her gun guncelliyor)
        _csv = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "optimized_universe.csv")
        _df_uni = pd.read_csv(_csv)

        # Live data pipeline (mevcut Streamlit ile ayni - tutarli sonuc)
        _df_uni = filter_universe(_df_uni)
        _df_uni = rename_existing_maden(_df_uni)
        _df_uni = extend_maden_universe(_df_uni)
        _df_uni = refresh_fx_maden_kripto(_df_uni)
        _df_uni = refresh_bist(_df_uni)

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

        # Admin user'in portfoyu (Secrets'tan email ile)
        _admin_email = st.secrets.get("admin", {}).get("email", "")

        # send_report portfolio=None + user_email -> sadece o kullanicinin portfoyu
        send_report(_df_uni, portfolio=None, cfg=_cfg,
                    budget=_budget, risk=_risk, max_assets=_max_assets,
                    user_email=_admin_email)

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

def _logo_splash_html():
    """v2.0.3.5-3.7: Giris aninda 2 kez oynayan hareketli logo, sonra statik
    logoya doner. %25 buyutulmus (188px) + mix-blend-mode:multiply ile
    (beyazlatilmis) arka plan sidebar rengiyle (#d0e4ff) gorsel olarak kayboluyor.

    NOT (2 Temmuz 2026): Bu fonksiyon Halka Arz modulu eklenirken yanlislikla
    eski bir app.py kopyasi uzerinden calisilmasi sonucu bir ara kayboldu,
    bugun tekrar eklendi. Video assets/logo_animated.mp4 dosyasindan CALISMA
    ZAMANINDA okunur (koda gomulu degil, ayri dosya olarak kalir).
    """
    video_path = None
    for p in ["assets/logo_animated.mp4", "logo_animated.mp4"]:
        if os.path.exists(p):
            video_path = p
            break
    if not video_path:
        return None

    try:
        with open(video_path, "rb") as f:
            vid_b64 = base64.b64encode(f.read()).decode()
    except Exception:
        return None

    img_tag = ""
    for p in ["logo.png","Logo.png","LOGO.PNG"]:
        if os.path.exists(p):
            with open(p,"rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            img_tag = f'<img id="logoImgStatic" src="data:image/png;base64,{img_b64}" style="width:150px;display:none;">'
            break

    return f"""
    <style>html,body{{margin:0;padding:0;background:#d0e4ff;}}</style>
    <div style="text-align:center;padding:6px 0 2px 0;background:#d0e4ff;">
      <video id="logoVidSplash" width="188" autoplay muted playsinline
             style="display:block;margin:0 auto;mix-blend-mode:multiply;">
        <source src="data:video/mp4;base64,{vid_b64}" type="video/mp4">
      </video>
      {img_tag}
    </div>
    <script>
      const vid = document.getElementById('logoVidSplash');
      const img = document.getElementById('logoImgStatic');
      let playCount = 0;
      if (vid) {{
        vid.addEventListener('ended', function() {{
          playCount++;
          if (playCount < 2) {{
            vid.currentTime = 0;
            vid.play();
          }} else {{
            vid.style.display = 'none';
            if (img) {{ img.style.display = 'block'; }}
          }}
        }});
      }}
    </script>
    """

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
            # v1.9.9.4 - st.form ile sarma: browser autofill (Edge password manager)
            # form submit ile DOM'daki gercek values'i Streamlit'e iletir; React state
            # senkronize degilse bile email/sifre dogru yakalanir.
            # Onceki sorun: autofill DOM'da values'i guncelliyordu ama Streamlit
            # text_input state'i sifir kaliyordu, "Lutfen tum alanlari doldurun" uyarisi.

            # Email autofill: ts_rem_email cookie'sinden email'i URL query'sine koy
            _remembered_email = st.query_params.get("_re", "")
            _stc_v1.html("""
            <script>
            (function() {
                try {
                  var loc = window.parent.location;
                  if (loc.search.indexOf('_re=') !== -1) return;  // zaten eklenmis
                  // Cookie'den email oku
                  var v = "; " + window.parent.document.cookie;
                  var p = v.split("; ts_rem_email=");
                  if (p.length === 2) {
                    var em = decodeURIComponent(p.pop().split(";")[0]);
                    if (em) {
                      var u = new URL(loc.href);
                      u.searchParams.set("_re", em);
                      loc.href = u.toString();
                    }
                  }
                } catch(e) { console.log('tso email autofill err:', e); }
            })();
            </script>
            """, height=0)

            with st.form("login_form_v1994", clear_on_submit=False):
                email = st.text_input("E-posta", key="li_email",
                                      placeholder="ornek@gmail.com",
                                      value=_remembered_email)
                pwd   = st.text_input("Sifre", type="password", key="li_pass",
                                      placeholder="Sifreniz")
                remember = st.checkbox("Beni Hatirla (90 gün)", key="li_remember", value=False)

                # v1.9.9.3 - Browser password manager entegrasyonu (fallback)
                # Streamlit 1.32+ text_input autocomplete parametresi var (yukarida);
                # eski sürümlerde calismadigi icin yedek MutationObserver script'i:
                _stc_v1.html("""
                <script>
                (function() {
                  function applyAutofill() {
                    try {
                      var doc = window.parent.document;
                      var inputs = doc.querySelectorAll('input[aria-label]');
                      inputs.forEach(function(inp) {
                        var lbl = (inp.getAttribute('aria-label') || '').toLowerCase();
                        if (lbl.indexOf('posta') !== -1 || lbl.indexOf('mail') !== -1) {
                          if (inp.getAttribute('autocomplete') !== 'username') {
                            inp.setAttribute('autocomplete', 'username');
                            inp.setAttribute('name', 'username');
                          }
                        }
                      });
                      var passes = doc.querySelectorAll('input[type="password"]');
                      passes.forEach(function(inp) {
                        if (inp.getAttribute('autocomplete') !== 'current-password') {
                          inp.setAttribute('autocomplete', 'current-password');
                          inp.setAttribute('name', 'password');
                        }
                      });
                    } catch(e) { console.log('[tso] autofill attr err:', e); }
                  }
                  applyAutofill();
                  var iv = setInterval(applyAutofill, 800);
                  setTimeout(function() { clearInterval(iv); }, 30000);
                })();
                </script>
                """, height=0)

                submitted = st.form_submit_button("Giris Yap", use_container_width=True)

            if submitted:
                if email and pwd:
                    # v1.9.9 - remember=True ise 90 gunluk DB token uretilir
                    res = login_user(email, pwd, remember=remember)
                    if res["ok"]:
                        st.session_state["auth_token"] = res["token"]
                        # v1.9.9.2 - Hem localStorage hem email cookie yaz (components.v1.html ile)
                        # Email cookie 90 gun, localStorage token 90 gun (DB token suresi ile ayni)
                        if remember:
                            # v2.0.7.36 - CookieManager ile GERCEK tarayici
                            # cerezi yazilir (90 gun) - herhangi bir cihaz/
                            # tarayicida calisir, URL/bookmark bagimliligi yok.
                            from datetime import datetime, timedelta
                            _expire = datetime.now() + timedelta(days=90)
                            cookie_manager.set(
                                "tso_auth", res["token"],
                                expires_at=_expire, key="set_tso_auth",
                                same_site="lax",
                            )
                            print("[auth] Beni Hatirla aktif: tso_auth cerezi CookieManager ile yazildi")
                        else:
                            # v2.0.7.2 -> v2.0.7.41: Beni Hatirla ISARETSIZ:
                            # eski bir tso_auth cerezi kalmissa temizle.
                            # v2.0.7.41 - KRITIK DUZELTME: extra-streamlit-
                            # components'in CookieManager.delete() metodu,
                            # cerez o an tarayicida/kutuphanenin kendi ic
                            # sozlugunde HENUZ HIC YOKSA "del self.cookies
                            # [cookie]" ile KeyError firlatiyor (kutuphanenin
                            # kendi hatasi) - Bahri'nin ekran goruntusunde
                            # gorulen "KeyError" cokmesi tam olarak bu.
                            # Cerez zaten yoksa silmeye calismanin bir
                            # anlami da yok - try/except ile sessizce
                            # atlanir.
                            try:
                                cookie_manager.delete("tso_auth", key="del_tso_auth_login")
                            except KeyError:
                                pass
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
# v2.0.7.36 - Beni Hatirla GERCEK COZUM: onceki st.query_params tabanli
# yontem calisan ama kirilgan bir gecici cozumdu - token tarayici adres
# cubugunda tasindigi icin SADECE o tam URL (bookmarkli) tekrar acilirsa
# calisiyordu; farkli bir cihazda/tarayicida (Serdar'in bilgisayari gibi)
# normal giris deneyimi saglamiyordu. KESIN COZUM: extra-streamlit-
# components paketinin CookieManager'i - bu, Streamlit'in RESMI cift-
# yonlu bilesen protokolunu (window.parent.postMessage) kullanir, navigasyon
# GEREKTIRMEZ, bu yuzden daha once tum JS/URL denemelerini kirip gecen
# sandboxed iframe navigasyon kisitina hic takilmaz. Artik GERCEK bir
# tarayici cerezi (tso_auth) yazilip okunuyor - herhangi bir cihazda normal
# "giris yap + Beni Hatirla isaretle" deneyimi calisir, URL'ye veya
# bookmark'a bagimlilik yok.
cookie_manager = stx.CookieManager(key="tso_cookie_mgr")

if "auth_token" not in st.session_state:
    _tso_cookies = cookie_manager.get_all(key="tso_cookies_get_all")
    _tso_token_cookie = (_tso_cookies or {}).get("tso_auth")
    if _tso_token_cookie:
        st.session_state["auth_token"] = _tso_token_cookie
        print("[auth] tso_auth cerezinden (CookieManager) oturum geri yuklendi")

# v1.9.9.3 - Beni Hatirla yapilanmasi:
#   Daha onceki localStorage + cookie yontemleri Streamlit Cloud iframe sandboxing
#   nedeniyle calismadi. Bunun yerine browser password manager'i (Edge/Chrome) ile
#   entegre calisan basit bir yontem: input alanlarina autocomplete attribute ekle.
#
#   Browser autofill her iki alani (username + password) tek tikla doldurur.
#   DB tarafindaki 90 gunluk token uretilmeye devam ediyor (gelecekteki kullanim icin).
#
# Ana JavaScript trick'i: Streamlit DOM'undaki email input'una autocomplete="username"
# ve sifre input'una autocomplete="current-password" attribute'larini ekle.
# MutationObserver ile Streamlit re-render'larinda attribute'lar korunur.

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

# v2.0.7.9 - "Yeni Abonelik Basvurusu" mailindeki dogrudan link icin:
# ?go=admin URL parametresi, ADMIN kullanicisini otomatik Admin Paneli'ne
# yonlendirir. Sadece is_admin=True icin calisir (baskasi bu linki elde
# ederse hicbir sey olmaz - normal sayfaya duser). Beni Hatirla (tso_auth
# cerezi) ile birlikte kullanildiginda mobilden tek tikla onay ekranina inilir.
if st.query_params.get("go") == "admin" and _cur_user.get("is_admin"):
    st.session_state["page_override"] = "admin"
    del st.query_params["go"]

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


@st.cache_data(ttl=600,show_spinner=False)  # v1.9.4: 60s -> 600s (kullanici beklemesi 1dk yerine 10dk'da bir)
def load_universe():
    import time as _t
    _t0 = _t.perf_counter()
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
    # v2.0.5: Firsat Radari overlay - GitHub Actions'in gun ici tam-evren
    # taramasi (firsat_radari.py) Supabase intraday_scores tablosuna yazar.
    # 45 dk'dan taze kayit varsa Optima_Skor (tum kategoriler) ve BIST icin
    # Son_Fiyat/RSI/Ret1M CSV'nin (gece verisi) uzerine bindirilir. Boylece
    # 772 hissenin TAMAMI en fazla ~30 dk tazelikte degerlendirilmis olur -
    # "firsat takip etmedigim hissedeyse kacirmayayim" ilkesi. DOVIZ/MADEN/
    # KRIPTO fiyatlari asagidaki 5-10 dk'lik canli katman tarafindan zaten
    # daha taze yazilacagi icin burada sadece skorlari alinir.
    try:
        from db import get_conn
        _rd_rows = get_conn().execute(
            "SELECT ticker, kategori, skor, fiyat, rsi, ret1m FROM intraday_scores "
            "WHERE updated_at > now() - interval '45 minutes'").fetchall()
        if _rd_rows:
            def _rv(r, k, i):
                return r[k] if isinstance(r, dict) else r[i]
            _rd_map = {}
            for _r in _rd_rows:
                _rd_map[str(_rv(_r, "ticker", 0))] = {
                    "kategori": _rv(_r, "kategori", 1),
                    "skor":  _rv(_r, "skor", 2),  "fiyat": _rv(_r, "fiyat", 3),
                    "rsi":   _rv(_r, "rsi", 4),   "ret1m": _rv(_r, "ret1m", 5)}
            _mask_rd = df["Ticker"].astype(str).isin(_rd_map.keys())
            if _mask_rd.any():
                if "Optima_Skor" not in df.columns:
                    df["Optima_Skor"] = pd.NA
                df.loc[_mask_rd, "Optima_Skor"] = df.loc[_mask_rd, "Ticker"].astype(str).map(
                    lambda t: _rd_map[t]["skor"])
                _mask_bist = _mask_rd & (df["Kategori"] == "BIST")
                if _mask_bist.any():
                    for _col, _key in (("Son_Fiyat","fiyat"),("RSI","rsi"),("Ret1M","ret1m")):
                        df.loc[_mask_bist, _col] = df.loc[_mask_bist, "Ticker"].astype(str).map(
                            lambda t, _k=_key: _rd_map[t][_k])
    except Exception as _rd_err:
        # Tablo henuz yoksa / baglanti sorunuysa sessizce CSV ile devam
        print(f"[radar-overlay] atlandi: {_rd_err}")
    # v1.6: USD bazli emtialari evrenden cikar (Brent/WTI/Dogalgaz/tarim emtialari)
    df = _ld_filter_universe(df)
    # v1.6.1: Mevcut MADEN adlarini netlestir (ALTIN_TRY -> "Gram Altin")
    df = _ld_rename_maden(df)
    # v1.6.1: Yeni MADEN sikkelerini ekle (Ceyrek/Yarim/Tam/Cumhuriyet/Ata/Ons-TL)
    df = _ld_extend_maden(df)
    # v1.6: DOVIZ + MADEN + KRIPTO icin canli fiyat uzerine yaz (borsapy)
    df = _ld_refresh_overlay(df)
    # v1.9.5.2 ACIL: refresh_bist tamamen kaldirildi (770 ticker 380+ sn aliyordu)
    # BIST fiyatlari CSV'den (worker.py her gun guncelliyor, 1 gun gecikmeli)
    # v1.9.6'da: portfoydeki + top N BIST icin selective canli refresh yapilacak
    # NOT: BIST sayfasinda "Canli Yenile" butonu manuel tetikleme icin uygun olur
    # v1.9.3 - profilleme: cache miss durumunda toplam yukleme suresi
    try:
        from live_data import _TIMINGS as _LD_TIMINGS
        _LD_TIMINGS["load_universe_TOPLAM"] = _t.perf_counter() - _t0
        # refresh_bist artik cagrilmiyor - eski timing varsa sil
        _LD_TIMINGS.pop("refresh_bist", None)
        print(f"[timing] load_universe (cache MISS, ilk yukleme): "
              f"{_LD_TIMINGS['load_universe_TOPLAM']:.3f}s")
    except Exception:
        pass
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


class _HistEmptyError(Exception):
    """get_hist() basarisiz/bos sonuc verdiginde kullanilir - boylece
    st.cache_data BU sonucu ONBELLEKLEMEZ (sadece basarili veri cache'lenir),
    gecici bir yfinance/kaynak aksakligi 5 dakika boyunca donup kalmaz."""
    pass

@st.cache_data(ttl=300, show_spinner=False)  # v2.0.4.x: BIST yfinance cagrisi onbelleksizdi
                                              # - her rerun'da (her 5dk'lik autorefresh dahil)
                                              # tekrar canli cekiliyordu. 300s = mevcut
                                              # "5 dakikalik pencere" canli veri formuluyle
                                              # birebir ayni tazelik, DOVIZ/MADEN/KRIPTO icin
                                              # zaten var olan 900s onbellekle celismez (300<900).
                                              # v2.0.4.x+1: basarisiz sonuclar _HistEmptyError
                                              # firlatir - Streamlit exception'i cache'lemez,
                                              # yani gecici aksaklik her cagrida yeniden denenir.
def _get_hist_cached(ticker, yf_symbol, category, period="1y"):
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
        raise _HistEmptyError()

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
        raise _HistEmptyError()

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
        raise _HistEmptyError()

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
                # v2.0.3: Volume varsa ekle
                _cols = ["Open","High","Low","Close"]
                if "Volume" in _h.columns:
                    _cols.append("Volume")
                return _h[_cols].dropna(subset=["Open","High","Low","Close"])
        except Exception:
            pass
        raise _HistEmptyError()

    # BIST - simdilik yfinance (v1.7'de borsapy.Ticker'a gecilecek)
    from data_pipeline import _format_yf_symbol
    sym = _format_yf_symbol(ticker, category)
    if yf_symbol and yf_symbol.strip() and "=F" in str(yf_symbol):
        sym = yf_symbol.strip()

    try:
        import yfinance as yf
        h = yf.Ticker(sym).history(period=period, auto_adjust=True)
        if not h.empty and len(h) >= 5:
            # v2.0.3: Volume varsa ekle (hacim subplot icin)
            cols = ["Open", "High", "Low", "Close"]
            if "Volume" in h.columns:
                cols.append("Volume")
            return h[cols].dropna(subset=["Open","High","Low","Close"])
    except Exception:
        pass
    raise _HistEmptyError()


def get_hist(ticker, yf_symbol, category, period="1y"):
    """Ince, onbelleksiz sarmalayici: basarili sonucu _get_hist_cached'ten
    (5 dk onbellekli) dondurur; basarisizlik durumunda (istisna) bos
    DataFrame dondurur - bu sayede gecici bir veri kaynagi aksakligi
    onbellege takilip 5 dakika donup kalmaz, her cagrida yeniden denenir."""
    try:
        return _get_hist_cached(ticker, yf_symbol, category, period)
    except _HistEmptyError:
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

    v2.0.3: Hacim trendi analizi (BIST/KRIPTO icin).
    Hacim azalirken fiyat yukseliyorsa zayif onay -> skor cezasi.
    Hacim artiyor + fiyat yukseliyorsa saglikli yukselis -> skor primi.
    """
    t=str(row["Ticker"]); cat=str(row["Kategori"]); yfs=str(row.get("YF_Symbol",""))
    # CSV verileri — skorun TEK kaynağı (ham)
    csv_rsi   = float(row.get("RSI",50))
    csv_ret1m = float(row.get("Ret1M",0))
    csv_vol   = float(row.get("Vol",30) or 30)
    base_score = optima_score(csv_rsi, csv_ret1m, csv_vol)

    hist=get_hist(t,yfs,cat,period)
    trend,ret3m,macd_v,macd_s="YUKSELIS" if csv_ret1m>=0 else "DUSUS",0.0,0.0,0.0
    live_rsi, live_vol = csv_rsi, csv_vol

    # v2.0.3: Hacim trendi
    vol_trend = "YOK"   # YOK / ARTIYOR / AZALIYOR / NORMAL
    vol_ratio = 0.0     # son5gun_ort / son20gun_ort
    score_adj = 0       # skor duzeltmesi (+/- puan)

    # v2.0.3.2: 52H, MA50, Max Drawdown
    week52_high = None
    week52_low = None
    week52_pct = None      # su anki fiyat 52H Yuksek'e yakinlik yuzdesi (0-100)
    ma50_val = None
    max_dd = None          # son 1Y maksimum drawdown yuzdesi (negatif sayi)
    dd_adj = 0             # Max DD icin skor cezasi

    if not hist.empty:
        pr=hist["Close"].dropna() if "Close" in hist.columns else hist.iloc[:,0].dropna()
        live_rsi=calc_rsi(pr); last=float(pr.iloc[-1])
        ma20=float(pr.rolling(20).mean().iloc[-1]) if len(pr)>=20 else last
        trend="YUKSELIS" if last>=ma20 else "DUSUS"
        ret3m=round((last/float(pr.iloc[-66])-1)*100,2) if len(pr)>=66 else 0.0
        live_vol=round(float(pr.pct_change().std()*np.sqrt(252)*100),1) if len(pr)>5 else csv_vol
        macd_v,macd_s=calc_macd(pr)

        # v2.0.3.2: MA50
        if len(pr)>=50:
            ma50_val = float(pr.rolling(50).mean().iloc[-1])

        # v2.0.3.2: 52H Yuksek / Dusuk (son 252 gun, yoksa tum data)
        win = pr.tail(252) if len(pr) >= 252 else pr
        if len(win) >= 20:
            week52_high = float(win.max())
            week52_low  = float(win.min())
            _spread = week52_high - week52_low
            if _spread > 0:
                # Su anki fiyatin 52H aralıgındaki konumu (0=dip, 100=tepe)
                week52_pct = round((last - week52_low) / _spread * 100, 1)

        # v2.0.3.2: Maksimum Drawdown (son 252 gun)
        if len(win) >= 20:
            cummax = win.cummax()
            dd_series = (win - cummax) / cummax * 100
            max_dd = round(float(dd_series.min()), 1)
            # Skor cezasi (Cevap B = B2)
            if max_dd < -70:
                dd_adj = -7
            elif max_dd < -50:
                dd_adj = -3
            else:
                dd_adj = 0

        # v2.0.3: Hacim trendi analizi
        if "Volume" in hist.columns and len(hist) >= 20:
            vol_series = hist["Volume"].fillna(0)
            if vol_series.sum() > 0:
                last5_avg = float(vol_series.tail(5).mean())
                last20_avg = float(vol_series.tail(20).mean())
                if last20_avg > 0:
                    vol_ratio = last5_avg / last20_avg
                    if vol_ratio >= 1.2:
                        vol_trend = "ARTIYOR"
                    elif vol_ratio <= 0.8:
                        vol_trend = "AZALIYOR"
                    else:
                        vol_trend = "NORMAL"

                    # v2.0.3.1: Skor duzeltmesi (hacim + trend kombinasyonu) - agresif
                    if trend == "YUKSELIS" and vol_trend == "ARTIYOR":
                        score_adj = +5   # Saglikli yukselis - guclu onay
                    elif trend == "YUKSELIS" and vol_trend == "AZALIYOR":
                        score_adj = -10  # Supheli yukselis (hacim zayif)
                    elif trend == "DUSUS" and vol_trend == "ARTIYOR":
                        score_adj = -3   # Panik satis onayi
                    elif trend == "DUSUS" and vol_trend == "AZALIYOR":
                        score_adj = +2   # Dusus bitiyor olabilir

    # v2.0.3.2: Toplam skor duzeltmesi (hacim + Max DD)
    total_adj = score_adj + dd_adj
    final_score = max(0, min(100, round(base_score + total_adj, 1)))

    return dict(hist=hist,rsi=csv_rsi,trend=trend,ret1m=csv_ret1m,ret3m=ret3m,
                vol=csv_vol,score=final_score,base_score=base_score,
                score_adj=score_adj,dd_adj=dd_adj,total_adj=total_adj,
                vol_trend=vol_trend,vol_ratio=vol_ratio,
                week52_high=week52_high,week52_low=week52_low,week52_pct=week52_pct,
                ma20=float(hist["Close"].rolling(20).mean().iloc[-1]) if (not hist.empty and "Close" in hist.columns and len(hist)>=20) else None,
                ma50=ma50_val,max_dd=max_dd,
                macd=macd_v,macd_sig=macd_s,
                live_rsi=live_rsi,live_vol=live_vol)

def live_optima_score(row, period="1mo"):
    """v2.0.4.x+2: enrich()'in ayni canli hesabini (hacim/DD dahil) tek
    bir satir icin guvenli sekilde dondurur. SADECE o an ekranda gorunen
    (sayfalanmis/kucuk) satir kumelerine uygulanmali - tum evrene degil,
    yoksa performans sorunu geri doner. get_hist() zaten 5 dk onbellekli
    oldugundan tekrar gorunumler hizli olur. Basarisizlikta CSV'deki
    onceden hesaplanmis Optima_Skor'a (veya ham optima_score()'a) duser."""
    try:
        d = enrich(row, period)
        return float(d["score"])
    except Exception:
        pass
    _fallback = row.get("Optima_Skor")
    if _fallback is not None and _fallback == _fallback:
        return float(_fallback)
    try:
        return float(optima_score(float(row.get("RSI", 50)), float(row.get("Ret1M", 0)),
                                   vol=float(row.get("Vol", 30) or 30)))
    except Exception:
        return 0.0

def _sinyal_renk_stil(v):
    """v2.0.7.31/32 - Sinyal metnine gore renk dondurur (Bahri'nin talebi):
    GUCLU AL koyu yesil, KADEMELI AL acik yesil, TUT IZLE sari,
    KADEMELI SAT turuncu, NET SAT kirmizi. Sadece YAZI RENGI + kalin -
    v2.0.7.32'de arkaplan/hucre dolgusu kaldirildi (Bahri: 'sadece
    yazinin rengi degissin, hucre komple degismesin'). clickable_table()
    ve Portfoyum tablosunda ortak kullanilir."""
    v = str(v).upper()
    if "GÜÇLÜ AL" in v or "GUCLU AL" in v:
        return "color: #1b8a4a; font-weight: 700;"
    elif "KADEMELİ AL" in v or "KADEMELI AL" in v:
        return "color: #66bb6a; font-weight: 700;"
    elif "TUT" in v:
        return "color: #b8860b; font-weight: 700;"
    elif "KADEMELİ SAT" in v or "KADEMELI SAT" in v:
        return "color: #e67e22; font-weight: 700;"
    elif "NET SAT" in v:
        return "color: #e74c3c; font-weight: 700;"
    return ""


def clickable_table(df_show, key, sel_ticker="", col_cfg=None):
    """on_select ile satır seçimi — checkbox Streamlit'in kendi davranışı.

    v2.0.4.29: col_cfg parametresi eklendi. Öncesinde bu fonksiyon dışarıdan
    sütun ayarı (genişlik, başlık, format) kabul etmiyordu - çağıran kod
    özenle bir col_cfg sözlüğü hazırlasa bile sessizce yok sayılıyordu.
    Şimdi disaridan verilen col_cfg, otomatik tespit edilenin üzerine yazar.

    v2.0.7.31: "Sinyal" sutunu varsa otomatik renklendirilir (bkz.
    _sinyal_renk_stil). Ana Sayfa, BIST, TEFAS - hepsi bu fonksiyonu
    kullandigi icin tek yerden tum tablolara yayilir.
    """
    auto_cfg = {}
    for c in df_show.columns:
        if c in ("Son Fiyat","Fiyat","Emir Fiyati"):
            auto_cfg[c] = st.column_config.NumberColumn(format="%.4f")
        elif c in ("1A Getiri%","1A%","Ret1M"):
            auto_cfg[c] = st.column_config.NumberColumn(format="%.2f")
        elif c in ("Optima Skor","Skor"):
            auto_cfg[c] = st.column_config.NumberColumn(format="%.1f")
        elif c == "RSI":
            auto_cfg[c] = st.column_config.NumberColumn(format="%.1f")
    if col_cfg:
        auto_cfg.update(col_cfg)

    df_render = df_show
    if "Sinyal" in df_show.columns:
        try:
            df_render = df_show.style.map(_sinyal_renk_stil, subset=["Sinyal"])
        except AttributeError:
            df_render = df_show.style.applymap(_sinyal_renk_stil, subset=["Sinyal"])

    evt = st.dataframe(
        df_render,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config=auto_cfg,
        key=key,
    )
    if evt and hasattr(evt, "selection") and evt.selection.rows:
        idx = evt.selection.rows[0]
        if idx < len(df_show):
            return str(df_show.iloc[idx]["Ticker"])
    return sel_ticker


def candle_fig(hist, ticker):
    """v2.0.3: Mum grafigi + opsiyonel hacim subplot.

    Volume kolonu varsa (BIST/KRIPTO) altta tek-renk hacim cubuklari gosterilir.
    DOVIZ/MADEN/TEFAS'ta Volume yok -> eski tek-panel davranis korunur.
    """
    if not HAS_PLOTLY or hist.empty: return None
    has_ohlc = all(c in hist.columns for c in ["Open","High","Low","Close"])
    use_candle = has_ohlc and len(hist) >= 5 and (hist["High"] - hist["Low"]).sum() > 0

    # v2.0.3: Hacim var mi? (sadece anlamliysa subplot olusturalim)
    has_volume = (use_candle and "Volume" in hist.columns
                  and hist["Volume"].fillna(0).sum() > 0)

    if has_volume:
        from plotly.subplots import make_subplots
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.75, 0.25], vertical_spacing=0.03)
    else:
        fig = go.Figure()

    if use_candle:
        candle_trace = go.Candlestick(
            x=hist.index, open=hist.Open, high=hist.High,
            low=hist.Low, close=hist.Close, name=ticker,
            increasing_line_color="#00732f", decreasing_line_color="#b71c1c",
            increasing_fillcolor="#e8f9ee", decreasing_fillcolor="#fde8e8")
        if has_volume:
            fig.add_trace(candle_trace, row=1, col=1)
        else:
            fig.add_trace(candle_trace)

        if len(hist) >= 20:
            ma20_trace = go.Scatter(x=hist.index, y=hist.Close.rolling(20).mean(),
                name="MA20", line=dict(color="#1b2a4a", width=1.5, dash="dot"))
            if has_volume:
                fig.add_trace(ma20_trace, row=1, col=1)
            else:
                fig.add_trace(ma20_trace)
        if len(hist) >= 50:
            ma50_trace = go.Scatter(x=hist.index, y=hist.Close.rolling(50).mean(),
                name="MA50", line=dict(color="#f4a300", width=1.5, dash="dash"))
            if has_volume:
                fig.add_trace(ma50_trace, row=1, col=1)
            else:
                fig.add_trace(ma50_trace)

        # v2.0.3.1: Hacim cubuklari (mum rengiyle - mavi yukselen/lacivert dusen)
        if has_volume:
            # Her gun icin yon: close >= open -> yukselen (mavi), aksi -> dusen (lacivert)
            _up_color   = "#3b7dd8"   # mavi - yukselen gun
            _down_color = "#1b2a4a"   # lacivert - dusen gun
            _bar_colors = [
                _up_color if (c >= o) else _down_color
                for c, o in zip(hist["Close"], hist["Open"])
            ]
            fig.add_trace(go.Bar(
                x=hist.index, y=hist["Volume"],
                name="Hacim",
                marker=dict(color=_bar_colors),
                opacity=0.75,
                showlegend=False
            ), row=2, col=1)
    else:
        col = "Close" if "Close" in hist.columns else hist.columns[0]
        if hist[col].nunique() < 2:
            return None
        line_trace = go.Scatter(x=hist.index, y=hist[col], name=ticker,
            line=dict(color="#1b2a4a", width=2),
            fill="tozeroy", fillcolor="rgba(27,42,74,.07)")
        fig.add_trace(line_trace)

    # Y ekseni — fiyat aralığını otomatik ayarla (normalize 0-100 görünümünü engelle)
    close_col = hist["Close"] if "Close" in hist.columns else hist.iloc[:, 0]
    y_min = float(close_col.min()) * 0.995
    y_max = float(close_col.max()) * 1.005

    if has_volume:
        # 2 satirli subplot duzeni
        fig.update_layout(
            height=480, paper_bgcolor="#fff", plot_bgcolor="#fafbff",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=0, r=0, t=30, b=0))
        fig.update_xaxes(showgrid=True, gridcolor="#eef0f7",
                         rangeslider=dict(visible=False), row=1, col=1)
        fig.update_xaxes(showgrid=True, gridcolor="#eef0f7", row=2, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="#eef0f7",
                         range=[y_min, y_max], autorange=False, row=1, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="#eef0f7",
                         title_text="Hacim", title_font=dict(size=10, color="#6c7a9c"),
                         row=2, col=1)
    else:
        # Tek panel duzeni (DOVIZ/MADEN/TEFAS)
        fig.update_layout(height=380, paper_bgcolor="#fff", plot_bgcolor="#fafbff",
            xaxis=dict(showgrid=True, gridcolor="#eef0f7", rangeslider=dict(visible=False)),
            yaxis=dict(showgrid=True, gridcolor="#eef0f7",
                       range=[y_min, y_max], autorange=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=0, r=0, t=30, b=0))
    return fig


def render_teknik_gostergeler(d, son_fiyat):
    """v2.0.3.2: Detay panelinde Teknik Gostergeler tablosu (expander icinde).

    d: enrich() ciktisi (dict)
    son_fiyat: float - mevcut fiyat (52H yakinliği icin)

    Expander varsayilan kapali; kullanici "Goster"e tiklarsa acilir.
    Sutunlar: Gosterge | Deger
    """
    def _fmt(v, fmt="{:.4f}"):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        try:
            return fmt.format(float(v))
        except Exception:
            return "—"

    # 52H yakinlik etiketi
    w52h_str = _fmt(d.get("week52_high"))
    w52l_str = _fmt(d.get("week52_low"))
    w52_pct = d.get("week52_pct")
    if w52_pct is not None and d.get("week52_high"):
        if w52_pct >= 90:
            w52_note = f"<span style='color:#27ae60;font-size:11px'>(tepeye %{w52_pct:.0f} yakin)</span>"
        elif w52_pct <= 10:
            w52_note = f"<span style='color:#e74c3c;font-size:11px'>(dipe %{100-w52_pct:.0f} yakin)</span>"
        else:
            w52_note = f"<span style='color:#6c7a9c;font-size:11px'>(araliktaki konum: %{w52_pct:.0f})</span>"
        w52h_full = f"{w52h_str} ₺ {w52_note}"
    else:
        w52h_full = f"{w52h_str} ₺" if w52h_str != "—" else "—"

    # Max DD - renkli
    max_dd = d.get("max_dd")
    if max_dd is not None:
        dd_clr = "#e74c3c" if max_dd < -50 else "#f39c12" if max_dd < -30 else "#27ae60"
        dd_adj = d.get("dd_adj", 0)
        adj_note = f" <span style='color:{dd_clr};font-size:11px'>({dd_adj:+d} skor)</span>" if dd_adj != 0 else ""
        dd_str = f"<span style='color:{dd_clr}'><b>{max_dd:.1f}%</b></span>{adj_note}"
    else:
        dd_str = "—"

    # MA20/MA50 - MA20'ye gore trend
    ma20_val = d.get("ma20")
    ma50_val = d.get("ma50")
    if ma20_val is not None:
        ma20_clr = "#27ae60" if son_fiyat >= ma20_val else "#e74c3c"
        ma20_str = f"<span style='color:{ma20_clr}'><b>{_fmt(ma20_val)} ₺</b></span>"
    else:
        ma20_str = "—"
    if ma50_val is not None:
        ma50_clr = "#27ae60" if son_fiyat >= ma50_val else "#e74c3c"
        ma50_str = f"<span style='color:{ma50_clr}'><b>{_fmt(ma50_val)} ₺</b></span>"
    else:
        ma50_str = "—"

    rows = [
        ("MA20 (Trend Cizgisi)",     ma20_str),
        ("MA50",                      ma50_str),
        ("52H Yüksek",                w52h_full),
        ("52H Düşük",                 f"{w52l_str} ₺" if w52l_str != "—" else "—"),
        ("Max Drawdown (1Y)",         dd_str),
        ("MACD",                      _fmt(d.get("macd"), "{:.4f}")),
    ]

    table_html = '<table class="kap-table" style="margin-top:6px">'
    for k, v in rows:
        table_html += f"<tr><td style='width:45%'>{k}</td><td>{v}</td></tr>"
    table_html += '</table>'

    with st.expander("Teknik Göstergeleri Göster", expanded=False):
        st.markdown(table_html, unsafe_allow_html=True)
        st.caption(
            "MA: Hareketli Ortalama (fiyat MA'nın üzerinde = yukseliş trendi). "
            "52H: Son 1 yılın en yüksek ve en düşük noktaları. "
            "Max Drawdown: Tepe noktasından en derin dip noktasına düşüş yüzdesi. "
            "MACD: Momentum göstergesi."
        )



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
    """Float -> Türkçe format: 1.234,56"""
    if val is None: return "—"
    sign = "-" if val < 0 else ""
    s = f"{abs(val):,.{decimals}f}"          # "1,234.56"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return sign + s

def parse_tr(s):
    """Türkçe format string -> float: '1.234,56' -> 1234.56"""
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

def load_email_cfg(user_id=None):
    """E-posta ayarlarini yukle.

    v1.9.8: Kullanici saatleri (times) Supabase'den gelir, SMTP credentials
    Streamlit Secrets'tan. Saat ayarlari kalici (logout sonrasi kaybolmaz).

    Args:
        user_id: Kullanici ID'si. Verilmezse default saatler kullanilir.
    """
    # 1) Önce secrets.toml (Streamlit Cloud)
    cfg = {"address":"", "smtp_host":"smtp.gmail.com", "smtp_port":587,
           "smtp_user":"", "smtp_pass":"", "times":["08:30","11:30"], "tcmb_key":""}
    try:
        s = st.secrets
        _es = dict(s.get("email", {}) or {})
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
            cfg = {
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

    # 2) Lokal email_config.json (Secrets yoksa)
    if not cfg["smtp_user"]:
        if os.path.exists(EMAIL_CFG_FILE):
            try:
                with open(EMAIL_CFG_FILE) as f:
                    cfg.update(json.load(f))
            except Exception:
                pass

    # 3) v1.9.8 - Kullanici saatleri Supabase'den (kalici)
    if user_id:
        try:
            from db import get_conn as _gc_es
            _conn_es = _gc_es()
            _row_es = _conn_es.execute(
                "SELECT gonderim_saati_1, gonderim_saati_2 FROM email_settings WHERE user_id=?",
                (user_id,)
            ).fetchone()
            if _row_es:
                cfg["times"] = [str(_row_es[0]), str(_row_es[1])]
        except Exception as _es_err:
            print(f"[db] email_settings okuma hatasi (default kullanilacak): {_es_err}")

    return cfg

def save_email_cfg(cfg, user_id=None):
    """E-posta ayarlarini kaydet.

    v1.9.8: Saatler Supabase'e, SMTP credentials lokal dosyaya.
    """
    # Saatleri Supabase'e (kalici)
    if user_id and cfg.get("times"):
        try:
            from db import get_conn as _gc_es
            _conn_es = _gc_es()
            _t1 = str(cfg["times"][0]) if len(cfg["times"]) > 0 else "09:00"
            _t2 = str(cfg["times"][-1]) if len(cfg["times"]) > 1 else "12:00"
            # UPSERT - postgres syntax
            _conn_es.execute(
                """INSERT INTO email_settings (user_id, gonderim_saati_1, gonderim_saati_2, son_guncelleme)
                   VALUES (?, ?, ?, NOW())
                   ON CONFLICT (user_id) DO UPDATE SET
                     gonderim_saati_1 = EXCLUDED.gonderim_saati_1,
                     gonderim_saati_2 = EXCLUDED.gonderim_saati_2,
                     son_guncelleme = NOW()""",
                (user_id, _t1, _t2)
            )
            try:
                _conn_es.commit()
            except Exception:
                pass
            print(f"[db] email_settings kaydedildi: user={user_id} t1={_t1} t2={_t2}")
        except Exception as _es_err:
            print(f"[db] email_settings yazma hatasi: {_es_err}")
            # Yedek: lokal dosyaya da yaz (eski davranis)
            try:
                with open(EMAIL_CFG_FILE,"w") as f: json.dump(cfg,f)
            except Exception:
                pass
    else:
        # user_id yoksa eski davranis (lokal dosya)
        with open(EMAIL_CFG_FILE,"w") as f: json.dump(cfg,f)

# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    # v2.0.3.5: Sadece login aninda 2 kez oynayan hareketli logo, sonra statik logo
    if not st.session_state.get("logo_splash_played", False):
        st.session_state["logo_splash_played"] = True
        _splash_html = _logo_splash_html()
        if _splash_html:
            components.html(_splash_html, height=150)
        else:
            st.markdown(_logo_html(), unsafe_allow_html=True)
    else:
        st.markdown(_logo_html(), unsafe_allow_html=True)
    plan_badge = {"free":"Ucretsiz","pro":"Pro","premium":"Premium"}
    st.markdown(
        f"<small style='color:#8ca3cc'>"
        f"<b>{_cur_user['full_name']}</b><br>"
        f"{plan_badge.get(_cur_user['plan'], _cur_user['plan'])}"
        f"</small>",
        unsafe_allow_html=True
    )
    st.divider()

    _yardim_etiket = "Admin El Kitabı" if _cur_user.get("is_admin") else "Kullanıcı El Kitabı"
    _pages_display = PAGES[:-1] + [_yardim_etiket]
    _page_secim = st.radio("", _pages_display, label_visibility="collapsed")
    page = "Yardım" if _page_secim == _yardim_etiket else _page_secim
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
        # v1.9.8 - Saatler artik Supabase'den (kalici, logout sonrasi kaybolmaz)
        _uid_for_cfg = _cur_user.get("id") if _cur_user else None
        ecfg=load_email_cfg(user_id=_uid_for_cfg)
        e_addr=st.text_input("Alıcı E-posta",value=ecfg.get("address",""))
        e_t1=st.text_input("1. Gönderim (HH:MM)",value=ecfg.get("times",["09:00"])[0])
        e_t2=st.text_input("2. Gönderim (HH:MM)",value=ecfg.get("times",["09:00","12:00"])[-1])
        st.markdown('<style>[data-testid="stSidebar"] button{color:#ffffff!important;font-weight:700!important;opacity:1!important;}</style>', unsafe_allow_html=True)
        if st.button("Ayarları Kaydet", key="ecfg_save", use_container_width=True):
            save_email_cfg({"address":e_addr,"smtp_host":"smtp.gmail.com","smtp_port":587,
                             "smtp_user":ecfg.get("smtp_user",""),
                             "smtp_pass":ecfg.get("smtp_pass",""),
                             "times":[e_t1,e_t2],
                             "tcmb_key":ecfg.get("tcmb_key","")},
                            user_id=_uid_for_cfg)
            st.success("Kaydedildi! (Saatler Supabase'de kalıcı)")
        if st.button("Şimdi Gönder", key="send_now", use_container_width=True):
            try:
                # Streamlit Cloud için: Secrets'dan cfg oku, email_config.json'a yaz
                import json as _ej
                # v1.9.8: user_id ile Supabase'den saatleri de al
                _ecfg = load_email_cfg(user_id=_uid_for_cfg)
                if _ecfg.get("smtp_user") and _ecfg.get("smtp_pass"):
                    with open("email_config.json", "w", encoding="utf-8") as _ef:
                        _ej.dump(_ecfg, _ef)
                from emailer import send_report
                df_uni2=load_universe()
                pf=load_portfolio()
                # v1.9.7.3: butce 0 ise emailer Watchlist (Top 10) modunda calisir
                # Kullaniciya bilgilendirme:
                if budget <= 0:
                    st.info("Bütçe girilmedi — İzleme Listesi (Top 10) modunda gönderiliyor.")
                send_report(df_uni2,pf,budget,risk,max_assets,cfg=_ecfg)
                st.success("E-posta gönderildi!")
            except Exception as ex:
                st.error(f"Hata: {ex}")

    # v2.0 - Kar Realizasyonu Uyarı Sistemi (Uyarı Ayarları)
    # E-posta Ayarları'na paralel mantik: DB-tabanli, kullanici bazli, kalici.
    # GitHub Actions workflow (peak_check.yml) bu ayarlari okuyup her kullanici
    # icin uygun frekansta fiyat takibi yapar ve uyari maillerini kullanicinin
    # KENDI e-posta adresine gonderir.
    with st.expander("Uyarı Ayarları"):
        _uid_for_alert = _cur_user.get("id") if _cur_user else None
        if _uid_for_alert is None:
            st.warning("Kullanıcı bilgisi alınamadı.")
        else:
            _acfg = load_alert_settings(_uid_for_alert)

            # Sistem aktif/pasif
            a_enabled = st.checkbox(
                "Uyarı sistemi aktif",
                value=_acfg["enabled"],
                key="alert_enabled",
                help="Kapalıyken hiçbir uyarı maili gönderilmez. Açıkken "
                     "portföyünüzdeki varlıklar takip edilir."
            )

            # Threshold (düşüş eşiği) - hazır seçenekler + özel
            _thr_choices = ["%2 (agresif)", "%3 (önerilen)", "%5 (rahat)", "Özel..."]
            _cur_thr = float(_acfg["threshold_pct"])
            if abs(_cur_thr - 2.0) < 0.01:   _thr_idx = 0
            elif abs(_cur_thr - 3.0) < 0.01: _thr_idx = 1
            elif abs(_cur_thr - 5.0) < 0.01: _thr_idx = 2
            else:                            _thr_idx = 3

            a_thr_pick = st.radio(
                "Düşüş eşiği (peak'ten %)",
                _thr_choices,
                index=_thr_idx,
                key="alert_thr_pick",
                help="Peak fiyatına göre bu yüzde kadar düşüş olursa uyarı tetiklenir."
            )
            if a_thr_pick == "Özel...":
                a_thr = st.slider("Özel eşik (%)", 0.5, 10.0, _cur_thr, 0.5,
                                  key="alert_thr_custom")
            elif a_thr_pick == "%2 (agresif)":
                a_thr = 2.0
            elif a_thr_pick == "%5 (rahat)":
                a_thr = 5.0
            else:
                a_thr = 3.0

            # Kar koşulu
            a_kar_only = st.checkbox(
                "Sadece kârdayken uyar",
                value=_acfg["kar_only"],
                key="alert_kar_only",
                help="İşaretliyse: uyarı yalnızca güncel fiyat alış fiyatının üstündeyken "
                     "gelir (kar realizasyonu). İşaretsizse: zararda olsa bile peak "
                     "sonrası düşüşlerde uyarı gelir (stop-loss mantığı)."
            )

            # Kontrol sıklığı
            _intv_labels = {15: "15 dk", 30: "30 dk", 60: "60 dk (saatlik)"}
            _intv_keys   = list(_intv_labels.keys())
            _cur_intv    = int(_acfg["check_interval_min"])
            _intv_idx    = _intv_keys.index(_cur_intv) if _cur_intv in _intv_keys else 1
            a_intv_lbl = st.radio(
                "Kontrol sıklığı",
                [_intv_labels[k] for k in _intv_keys],
                index=_intv_idx,
                key="alert_intv",
                help="Sistemin fiyatları ne sıklıkta kontrol edeceği. "
                     "Daha sık = daha hızlı uyarı, daha çok mail."
            )
            a_intv = _intv_keys[[_intv_labels[k] for k in _intv_keys].index(a_intv_lbl)]

            # Uyarı modu (tekrar mantığı)
            _mode_keys   = list(ALERT_MODES.keys())
            _mode_labels = [ALERT_MODES[k] for k in _mode_keys]
            _cur_mode    = _acfg["alert_mode"]
            _mode_idx    = _mode_keys.index(_cur_mode) if _cur_mode in _mode_keys else 0
            a_mode_lbl = st.selectbox(
                "Uyarı tekrar mantığı",
                _mode_labels,
                index=_mode_idx,
                key="alert_mode_sel",
            )
            a_mode = _mode_keys[_mode_labels.index(a_mode_lbl)]

            # Tavsiye emir fiyatı formülü
            _fml_keys   = list(EMIR_FORMULS.keys())
            _fml_labels = [EMIR_FORMULS[k] for k in _fml_keys]
            _cur_fml    = _acfg["emir_formul"]
            _fml_idx    = _fml_keys.index(_cur_fml) if _cur_fml in _fml_keys else 0
            a_fml_lbl = st.selectbox(
                "Tavsiye emir fiyatı",
                _fml_labels,
                index=_fml_idx,
                key="alert_fml_sel",
            )
            a_fml = _fml_keys[_fml_labels.index(a_fml_lbl)]

            # Kaydet butonu
            with st.container(border=True):
                st.caption("**Uyarı Ayarlarını Kaydet** — yukarıdaki eşik, kâr koşulu, "
                           "kontrol sıklığı, uyarı modu ve emir fiyatı formülü "
                           "ayarlarınızı kalıcı olarak kaydeder (Supabase).")
                if st.button("Uyarı Ayarlarını Kaydet", key="alert_save",
                             use_container_width=True):
                    ok = save_alert_settings(_uid_for_alert, {
                        "threshold_pct":      float(a_thr),
                        "kar_only":           bool(a_kar_only),
                        "check_interval_min": int(a_intv),
                        "alert_mode":         a_mode,
                        "emir_formul":        a_fml,
                        "enabled":            bool(a_enabled),
                    })
                    if ok:
                        st.success("Uyarı ayarları kaydedildi. (Supabase'de kalıcı)")
                    else:
                        st.error("Kaydetme hatası — loglara bakın.")

            st.divider()

            # v2.0 asama 3a.2 - Manuel Test (autorefresh-safe)
            # streamlit-autorefresh her 60 sn sayfayi yeniliyor. Buton state
            # Streamlit'te sadece basildigi turda True doner, sonraki rerunlarda
            # False. Bu yuzden sonuc render'i buton bloku DISINDA olmali,
            # session_state'den okuyarak. Aksi halde kullanici sonucu goremez.
            st.caption("**Manuel Test** — Portföyünüzdeki varlıkların peak değerlerini "
                       "güncelleyip threshold kontrolü yapar. Mail gönderilmez.")
            if st.button("Şimdi Kontrol Et (Test)", key="alert_test_run",
                         use_container_width=True):
                with st.spinner("Peak kontrol ediliyor..."):
                    try:
                        df_uni_test = load_universe()
                        _alert_res = evaluate_user_alerts(_uid_for_alert, df_uni_test)
                        # Sonucu session_state'e koy, render buton DISINDA olacak
                        from datetime import datetime as _dt_alert
                        st.session_state["alert_test_result"] = _alert_res
                        st.session_state["alert_test_ts"] = _dt_alert.now()
                    except Exception as _ate:
                        st.session_state["alert_test_error"] = str(_ate)
                        st.session_state["alert_test_result"] = None

            # Sonuc render'i (buton bloku DISINDA, session_state'den)
            # autorefresh sayfayi yenilese bile bu blok her rerun'da calisir
            # ve son sonucu gosterir.
            _last_err = st.session_state.get("alert_test_error")
            _last_res = st.session_state.get("alert_test_result")
            _last_ts  = st.session_state.get("alert_test_ts")
            if _last_err:
                st.error(f"Test sirasinda hata: {_last_err}")
            elif _last_res is not None and _last_ts is not None:
                st.caption(f"Son kontrol: {_last_ts.strftime('%H:%M:%S')}")
                st.success(
                    f"Kontrol tamamlandı: "
                    f"{len(_last_res['updated_peaks'])} peak güncellendi, "
                    f"{len(_last_res['alerts_pending'])} uyarı bekliyor, "
                    f"{len(_last_res['skipped'])} varlık atlandı."
                )

                # Uyari bekleyen tickerlari tablo halinde goster
                if _last_res["alerts_pending"]:
                    st.markdown("**Uyarı Bekleyen Varlıklar:**")
                    _alert_rows = []
                    for a in _last_res["alerts_pending"]:
                        _alert_rows.append({
                            "Ticker":      a["ticker"],
                            "Kategori":    a["asset_type"],
                            "Alış":        f"{a['alish_fiyat']:.4f}",
                            "Peak":        f"{a['peak_price']:.4f}",
                            "Şu Anki":     f"{a['current_price']:.4f}",
                            "Düşüş (%)":   f"{a['drop_pct']:.2f}",
                            "Tavsiye":     f"{a['tavsiye_fiyat']:.4f}" if a['tavsiye_fiyat'] > 0 else "—",
                            "Miktar":      f"{a['miktar']:.4f}",
                            "Toplam (TL)": f"{a['toplam_deger']:,.2f}",
                        })
                    if _alert_rows:
                        st.dataframe(_alert_rows, use_container_width=True,
                                     hide_index=True)

                    # v2.0 asama 3b - Mail gonder butonu
                    # Sadece alerts_pending doluyken gorunur. Mail basariyla
                    # gonderildikten sonra her ticker icin mark_alert_sent
                    # cagrilir, ayni peak icin tekrar mail gelmez.
                    st.caption(
                        f"**Bekleyen Uyarıları Mail Gönder** — Yukarıdaki "
                        f"{len(_last_res['alerts_pending'])} uyarıyı e-posta "
                        f"adresinize gönderir. Gönderim sonrası her ticker için "
                        f"'alert sent' flag'i set edilir, aynı peak için tekrar "
                        f"mail gelmez (uyarı modunuza göre)."
                    )
                    if st.button("Bekleyen Uyarıları Mail Gönder",
                                 key="alert_send_email",
                                 use_container_width=True):
                        with st.spinner("Mail gönderiliyor..."):
                            _alert_settings = load_alert_settings(_uid_for_alert)
                            _mail_res = send_peak_alert(
                                _uid_for_alert,
                                _last_res["alerts_pending"],
                                _alert_settings
                            )
                        if _mail_res.get("sent"):
                            st.success(
                                f"Mail gönderildi: {_mail_res.get('to')} adresine "
                                f"{_mail_res.get('count')} uyarı "
                                f"({_mail_res.get('marked', 0)} ticker için "
                                f"alert flag set edildi)."
                            )
                            # Mail gonderildikten sonra test sonucunu temizle
                            # (eski uyari bekliyor gibi gosterilmesin)
                            st.session_state.pop("alert_test_result", None)
                            st.session_state.pop("alert_test_ts", None)
                        else:
                            st.error(
                                f"Mail gönderilemedi: "
                                f"{_mail_res.get('reason', 'bilinmeyen hata')}"
                            )
                else:
                    st.caption("Şu an uyarı tetikleyen varlık yok.")

                # Yeni peak yapan tickerlar
                if _last_res["updated_peaks"]:
                    _peak_msgs = [
                        f"{t} -> {p:.4f} ({s})"
                        for t, p, s in _last_res["updated_peaks"]
                    ]
                    st.caption("Peak güncellemeleri: " + ", ".join(_peak_msgs))

                # Atlananlar
                if _last_res["skipped"]:
                    _skip_msgs = [f"{t}: {r}" for t, r in _last_res["skipped"]]
                    st.caption("Atlananlar: " + ", ".join(_skip_msgs))

            # Peak'leri Sifirla butonu
            # v2.0.7.13 - "Simdi Kontrol Et" butonuyle karisiyordu (Bahri geri
            # bildirimi): sadece divider() yeterli ayrim yaratmiyordu. Gorunur
            # SINIRLI KUTU (border=True) icine alindi - artik hangi metnin
            # hangi butona ait oldugu goz onunde acikca ayrisir.
            st.divider()
            with st.container(border=True):
                st.caption("**Tüm Peak'leri Sıfırla** — DB'deki tüm peak kayıtlarınızı "
                           "siler. Bir sonraki kontrolde mevcut fiyatlardan yeni "
                           "peak başlatılır.")
                if st.button("Tüm Peak'leri Sıfırla", key="alert_peak_reset",
                             use_container_width=True):
                    ok = reset_peaks_for_user(_uid_for_alert)
                    if ok:
                        # Test sonucunu da temizle - eski peak kayitlari gosterilmesin
                        st.session_state.pop("alert_test_result", None)
                        st.session_state.pop("alert_test_ts", None)
                        st.session_state.pop("alert_test_error", None)
                        st.success("Peak kayıtları sıfırlandı.")
                    else:
                        st.error("Sıfırlama hatası — loglara bakın.")

            # Bilgilendirme
            st.caption(
                "Uyarı mailleri **sizin e-posta adresinize** gönderilir "
                "(E-Posta Ayarları'ndaki alıcı). Yalnızca **portföyünüzdeki** "
                "varlıklar takip edilir. Sistem hafta sonu sadece kripto varlıkları "
                "için aktif çalışır (BIST/TEFAS/döviz piyasaları kapalı)."
            )

    st.divider()
    if _cur_user.get("is_admin"):
        # v1.9.3 - Sistem Tanilama paneli (yavaslik teshisi icin)
        with st.expander("Sistem Tanılama"):
            st.markdown("""<style>
            [data-testid="stSidebar"] [data-testid="stExpander"] summary p,
            [data-testid="stSidebar"] [data-testid="stExpander"] label p,
            [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stCaptionContainer"] {
                color:#1b2a4a!important;font-weight:600!important;
            }
            </style>""", unsafe_allow_html=True)
            try:
                from live_data import get_timings as _ld_get_timings, reset_timings as _ld_reset_timings
                _tdict = _ld_get_timings()
                if _tdict:
                    # Sayfa yuklemesi: cache hit ise tum degerler eski, cache miss ise yeni
                    _toplam = _tdict.get("load_universe_TOPLAM", 0.0)
                    if _toplam > 0:
                        st.caption(f"**Son yüklenme:** {_toplam:.2f} sn")
                    st.caption("**Parça parça (saniye):**")
                    _order = ["extend_maden_universe", "refresh_fx_maden_kripto", "refresh_bist"]
                    _shown = set()
                    for k in _order:
                        if k in _tdict:
                            v = _tdict[k]
                            _shown.add(k)
                            _color = "#00732f" if v < 1 else ("#a06000" if v < 5 else "#b71c1c")
                            st.markdown(
                                f"<small><code>{k}</code>: "
                                f"<b style='color:{_color}'>{v:.3f}s</b></small>",
                                unsafe_allow_html=True)
                    # Sirada olmayan ek olculmus seyler varsa goster
                    for k, v in _tdict.items():
                        if k in _shown or k == "load_universe_TOPLAM":
                            continue
                        st.markdown(f"<small><code>{k}</code>: {v:.3f}s</small>",
                                    unsafe_allow_html=True)
                else:
                    st.caption("Henüz ölçüm yok — bir sayfa açın.")
                if st.button("Olcumleri Sifirla", key="diag_reset", use_container_width=True):
                    _ld_reset_timings()
                    st.rerun()
                st.caption(
                    "İlk yükleme cache miss = 30-60 sn beklenir. "
                    "Sonraki açılışlar 5 dk içinde hızlı (cache hit, ~0s). "
                    "Streamlit Cloud Logs'a `[timing]` satırları da basar."
                )
            except Exception as _e:
                st.caption(f"Tanilama yuklenemedi: {_e}")

        if st.button("Admin Paneli", use_container_width=True):
            st.session_state["page_override"] = "admin"
            st.rerun()
    if st.button("Cikis Yap", use_container_width=True):
        # v2.0.7.36 -> v2.0.7.41 - CookieManager ile gercek cerez silme.
        # KeyError korumasi: cerez hic yoksa kutuphane kendi ic sozlugunde
        # bulamayip KeyError firlatiyor - bkz. login blogundaki not.
        try:
            cookie_manager.delete("tso_auth", key="del_tso_auth_logout")
        except KeyError:
            pass
        logout()
        st.rerun()

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

# v1.9.7 - Otomatik veri yenileme (her 60 saniyede sessiz re-run)
# Cache hit oldugunda kullanici fark etmez, cache miss oldugunda yeni veri gelir.
# Boylece kullanici hicbir buton tiklamadan portfoyundeki fiyatlari guncel gorur.
if _AUTOREFRESH_OK:
    # v2.0.1 - Autorefresh interval 60sn -> 5dk
    # Sebep: Her 60sn'de tum sayfa rerun ediliyor, bu da Streamlit'in stale
    # opacity efektine yol acip kisa bulanikliga sebep oluyordu. 5dk daha
    # makul: canli veri (BIST/kripto) zaten dakika hassasiyetinde degil,
    # autorefresh esas amaci sidebar timestamp + manuel calismayan widget'lar
    # icin gerekli minimum yenileme.
    _st_autorefresh(interval=300_000, key="trendsurf_auto_refresh", limit=None)

# v1.9.7.5 - Selective BIST refresh ACIL DEVRE DISI
# Sebep: app sayfa render'inda selective refresh bazen takiliyor, sayfalar bos kaliyor
# EUKYO/diger BIST tickerlari CSV verisinden gelir (worker.py her gun gunceller)
# v1.9.8'de daha guvenli bir strateji ile (kisa timeout + async pattern) tekrar acilacak
_portfolio_bist_tickers = []  # placeholder, kullanilmiyor
# Asagidaki blok comment'lendi - timeout korumasi yetersiz kaldi:
# try:
#     ... selective BIST refresh kodu ...
# except Exception:
#     pass

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
    # v2.0.7.42 - "Döviz+Maden" birlesik karti ayri iki karta bolundu
    # (Bahri'nin bulgusu: birlesik etiket, Doviz'in sayiya dahil oldugunu
    # gizliyor, sanki eksikmis gibi goruniyordu - matematiksel olarak
    # eksik degildi, sadece etiket yaniltici sekilde tek kategori gibi
    # okunuyordu).
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("Toplam Varlık",f"{len(df_uni):,}")
    c2.metric("TEFAS",f"{cats.get('TEFAS',0):,}")
    c3.metric("BIST",f"{cats.get('BIST',0):,}")
    c4.metric("Kripto",f"{cats.get('KRIPTO',0):,}")
    c5.metric("Döviz",f"{cats.get('DOVIZ',0):,}")
    c6.metric("Maden",f"{cats.get('MADEN',0):,}")

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
    # v2.0.4.50: Optimizasyona girmeden once, BIST adaylarinin fiyatini
    # seans saatlerinde canli yenile. Hangi hisselerin sonunda secilecegini
    # henuz bilmiyoruz (skor/butce hesabi asagida yapiliyor), o yuzden
    # cok genis bir ust-kume (1A getirisine gore ilk 40 BIST hissesi)
    # canli yenileniyor - secilecek olanlari neredeyse her zaman kapsar,
    # 40 ticker de refresh_bist_selective icin hizli (birkac saniye).
    if _bist_seans_acik() and w.get("BIST", 0) > 0:
        _bist_aday = (df_uni[(df_uni["Kategori"] == "BIST") & (df_uni["Son_Fiyat"] > 0)]
                      .sort_values("Ret1M", ascending=False).head(40))
        if not _bist_aday.empty:
            df_uni = _ld_refresh_bist_sel(df_uni, _bist_aday["Ticker"].tolist())

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
        # v2.0.4.57: BIST icin worker.py'nin ONCEDEN hesapladigi TAM skoru
        # (temel analiz + hacim/dususu cezasi dahil) kullan - boylece bu
        # sayfa, Portfoyum ve Detay sayfasiyla AYNI sayiyi gosterir. Diger
        # kategoriler icin (henuz precompute edilmedi) eski basit hesaba
        # devam edilir.
        if "Optima_Skor" in df_c.columns and df_c["Optima_Skor"].notna().any():
            df_c["Optima_Skor"] = pd.to_numeric(df_c["Optima_Skor"], errors="coerce")
            _eksik = df_c["Optima_Skor"].isna()
            if _eksik.any():
                df_c.loc[_eksik, "Optima_Skor"] = df_c.loc[_eksik].apply(
                    lambda r: optima_score(float(r.get("RSI",50)),float(r.get("Ret1M",0)),
                                           vol=float(r.get("Vol",30) or 30)), axis=1)
        else:
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
    karsilanamayan_kategoriler = []
    for cat, weight in adj_weights.items():
        df_c = cat_pools[cat]
        mpc  = max_per_cat_map.get(cat, 1)
        sample = df_c.head(min(mpc, len(df_c)))
        cat_bud = budget * weight

        # v2.0.4.34: Esit bolusumde bir varligin payi kendi birim fiyatindan
        # dusuk cikarsa (lot=0), o varlik oncesinde hala "onerilen" listede
        # 0 birim/0 TL ile goruniyordu - bu hem yaniltici hem de kategoriye
        # ayrilan butcenin bir kismini fiilen harcanmadan birakiyordu.
        # Simdi asama asama: payini karsilayamayan varliklar kategori
        # havuzundan cikarilip kalan butce, kalan varliklara yeniden esit
        # dagitiliyor (feasibility/water-filling) - stabil hale gelene
        # kadar (herkes kendi payini karsilayana kadar) tekrarlaniyor.
        aktif = list(sample.iterrows())
        per = 0.0
        while aktif:
            pay = cat_bud / len(aktif)
            karsilayamayan = [
                i for i, (_, row) in enumerate(aktif)
                if (float(row["Son_Fiyat"]) if float(row.get("Son_Fiyat", 0)) > 0 else 1.0) > pay
            ]
            if not karsilayamayan:
                per = pay
                break
            aktif = [item for i, item in enumerate(aktif) if i not in karsilayamayan]
        else:
            per = 0.0

        if not aktif:
            karsilanamayan_kategoriler.append(cat)
            continue

        for _, row in aktif:
            # v2.0.5.1: Skorun tek kaynagi Firsat Radari destekli Optima_Skor
            # (load_universe overlay) - tablo/Top5/Detay ile birebir ayni.
            _rs = row.get("Optima_Skor")
            skor = float(_rs) if (_rs is not None and _rs == _rs) else live_optima_score(row)
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
                "Birim":lot,
                "Tutar (₺)":gercek,
                "_gercek_fiyat": float(row.get("Son_Fiyat",0)) > 0,
            })

    # Elenen kategorileri bildir
    elenen = [c for c in w if w.get(c,0) > 0 and c not in adj_weights]
    if elenen:
        st.info(f"Şu kategorilerde yeterli AL sinyalli varlik bulunamadigi icin "
                f"bütçe diğer kategorilere dağıtıldı: {', '.join(elenen)}")
    if karsilanamayan_kategoriler:
        st.info(f"Şu kategorilerde ayrılan bütçe, havuzdaki hiçbir varlığın "
                f"birim fiyatını karşılamadığı için o kategoriye hiç alım "
                f"önerilemedi: {', '.join(karsilanamayan_kategoriler)}. "
                f"Bütçeyi artırmak veya Max Varlık Sayısı'nı azaltmak bu durumu çözebilir.")

    # v2.0.7.21 - BUTCE KULLANIM VERIMLILIGI (Bahri'nin talebi): Lot tam
    # sayiya yuvarlandigi icin her varlikta Tutar'dan az kalan bir
    # artik olusuyordu ve bu artik toplamda kullanilmadan kaliyordu (orn.
    # 20.000 TL butcede Gercek Tutar toplami 19.831 TL'de kaliyordu). Mantik:
    # kullanicinin elinde YATIRIMA AYRILACAK gercek bir tutar var - onemli
    # olan bu paranin GERCEKTE ne kadari karsiliginda varlik alinabildigi,
    # teorik hedef degil. Bu yuzden tum kategorilerin secimleri belirlendik-
    # ten SONRA, kalan (harcanmamis) butce, Optima Skoru en yuksek secili
    # varliklardan baslayarak sirayla birer LOT daha eklenerek (round-robin,
    # kalan butce hicbir secili varligin fiyatini karsilayamayana kadar
    # tekrarlanir) dagitilir. Sadece MEVCUT secili varliklara ek lot eklenir
    # - Max Varlik Sayisi kisitini bozmaz, yeni varlik eklemez.
    if opt_rows:
        _kalan_butce = budget - sum(r["Tutar (₺)"] for r in opt_rows)
        _skor_sirali = sorted(
            [r for r in opt_rows if r.get("_gercek_fiyat")],
            key=lambda r: -r["Optima Skoru"])
        _ilerleme = True
        while _kalan_butce > 0.01 and _ilerleme and _skor_sirali:
            _ilerleme = False
            for r in _skor_sirali:
                _fiyat = r["Emir Fiyatı"]
                if _fiyat > 0 and _fiyat <= _kalan_butce:
                    r["Birim"] += 1
                    r["Tutar (₺)"] = round(r["Tutar (₺)"] + _fiyat, 2)
                    _kalan_butce = round(_kalan_butce - _fiyat, 2)
                    _ilerleme = True

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
        # v2.0.4.29: "Kategori Payı %" kaldırıldı (Kategori Dağılımı pasta
        # grafiğinde zaten gösteriliyor, tabloda tekrar oluyordu). "Gelir
        # Türü/Oranı/Yıllık Gelir" sütunları da tablodan çıkarıldı - üstteki
        # özet metrikler (Tahmini Yıllık Pasif Gelir vb.) zaten aynı veriyi
        # gösteriyor, df_opt_gelir'den hesaplanmaları bundan etkilenmiyor.
        base_cols = ["Kategori","Ticker","Ad","Optima Skoru","Sinyal","RSI","1A Getiri %",
                     "Emir Fiyatı","Birim","Tutar (₺)"]
        col_order = base_cols
        df_opt = df_opt[[c for c in col_order if c in df_opt.columns]]

        st.caption("Tutar = Lot x Emir Fiyatı. Kategori içi eşit bölüşümden artan bakiye, "
                   "Optima Skoru en yüksek varlıklara ek lot olarak dağıtılarak bütçenin mümkün "
                   "olduğunca tamamı kullanılır. "
                   "Pasif gelir tahmini üstteki özet metriklerde gösterilir — BIST (temettü) ve "
                   "Kripto (staking APY) GERÇEK verilere dayanır; TEFAS, Döviz ve Değerli Maden "
                   "için ise gerçek/sabit bir gelir kaynağı olmadığından tutarlı bir yöntemle "
                   "1 aylık getiri bileşik olarak yıllıklandırılır — bu SPEKÜLATİF bir trend "
                   "projeksiyonudur, gerçek gelir garantisi değildir. Yatırım tavsiyesi değildir.")

        # v2.0.4.40: Deneme - Ana Sayfa'yi da Portfoyum/kategori sayfalarinda
        # zaten basariyla kullanilan native st.dataframe (clickable_table)
        # formatina cevirdik. Bu format mobilde dagilmiyor (tek parca bir
        # bilesen, st.columns() gibi dikey istiflenmiyor) ve satirin
        # HERHANGI bir yerine tiklamak secim yapiyor (checkbox'a tiklamak
        # zorunlu degil - checkbox sadece gorsel bir isaret). Risk: bu
        # bilesen metin kaydirma (word-wrap) desteklemedigi icin dar
        # sutunlarda eskisi gibi sikisma/kesilme olabilir - bunu canlida
        # birlikte degerlendirecegiz.
        col_cfg_ana = {
            "Kategori": st.column_config.TextColumn("Kategori", width="small"),
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Optima Skoru": st.column_config.NumberColumn("Optima Skoru", format="%.1f", width="small"),
            "Sinyal": st.column_config.TextColumn("Sinyal", width="small"),
            "RSI": st.column_config.NumberColumn("RSI", format="%.1f", width="small"),
            "1A Getiri %": st.column_config.NumberColumn("1A Getiri %", format="%.2f", width="small"),
            "Emir Fiyatı": st.column_config.NumberColumn("Emir Fiyatı", format="%.4f", width="small"),
            "Birim": st.column_config.NumberColumn("Birim", format="%d", width="small"),
            "Tutar (₺)": st.column_config.NumberColumn("Tutar (₺)", format="%.2f", width="small"),
        }
        st.markdown("""
        <style>
        @media (min-width: 769px) {
            .block-container { padding-left: 1rem !important; padding-right: 1rem !important;
                                max-width: 100% !important; }
        }
        </style>
        """, unsafe_allow_html=True)
        sel_ana = st.session_state.get("sel_Ana Sayfa", "")
        df_opt_show = df_opt.drop(columns=["Ad"], errors="ignore").reset_index(drop=True)
        _yeni_secim = clickable_table(df_opt_show, key="anasayfa_df", sel_ticker=sel_ana, col_cfg=col_cfg_ana)

        # v2.0.7.24 - Siralama degistirildi (Bahri'nin talebi): Bütçe
        # Kullanımı once, Toplam Tutar en sona (en saga) alindi - boylece
        # tablonun en sagindaki "Tutar (₺)" sutununun devami gibi hizalaniyor.
        # "Tutar" etiketi "Toplam Tutar" olarak degistirildi.
        _toplam_gercek = df_opt["Tutar (₺)"].sum()
        st.markdown(
            f"<div style='border-top:2px solid #2c3e6b;padding:8px 4px;"
            f"display:flex;justify-content:space-between;'>"
            f"<b style='font-size:13px;color:#6c7a9c;'>TOPLAM</b>"
            f"<span style='font-size:14px;'>"
            f"Bütçe Kullanımı: <b style='color:#1b2a4a;'>"
            f"{(_toplam_gercek/budget*100 if budget>0 else 0):.1f}%</b>"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;Toplam Tutar: <b style='color:#1b2a4a;'>{_toplam_gercek:,.2f} ₺</b>"
            f"</span></div>",
            unsafe_allow_html=True
        )

        if _yeni_secim and _yeni_secim != sel_ana:
            st.session_state["sel_Ana Sayfa"] = _yeni_secim
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
                    # v2.0.4.x: Tabloyla AYNI sayiyi goster - worker.py'nin
                    # onceden hesapladigi (hacim/DD dahil) skor varsa onu kullan.
                    # Canli hacim okumasi asagida sadece bilgi notu olarak kalir.
                    # v2.0.5.1: Skorun TEK kaynagi Firsat Radari (load_universe
                    # overlay'i sel_row'a yansimis durumda). Detay basligi da ayni
                    # sayiyi gosterir -> tablo = detay birebir esit. Radar yoksa
                    # (tablo bos / 45dk'dan eski) canli enrich() skoruna duser.
                    _rd_ana = sel_row_ana.get("Optima_Skor")
                    disp_score_ana = float(_rd_ana) if (_rd_ana is not None and _rd_ana == _rd_ana) else d["score"]
                    # v2.0.7.34 - ayni tutarlilik kurali (bkz. genel Detay
                    # sayfasindaki not): fiyatsiz varligin skoru daima 0.
                    if float(sel_row_ana.get("Son_Fiyat", 0) or 0) <= 0:
                        disp_score_ana = 0.0
                    sig_lbl, sig_cls = get_signal(disp_score_ana, d["rsi"], d["trend"])

                r1,r2,r3,r4,r5 = st.columns(5)
                r1.metric("Son Fiyat",    f"{float(sel_row_ana['Son_Fiyat']):,.4f}")
                r2.metric("Optima Skor",  f"{disp_score_ana:.1f}")
                r3.metric("RSI (14)",     f"{d['rsi']:.1f}")
                r4.metric("1A Getiri %",  f"{d['ret1m']:+.2f}%")
                r5.metric("Yillik Vol %", f"{d['vol']:.1f}%")

                sig_color = SIG_COLORS.get(sig_cls, "#666")

                # v2.0.3: Hacim trendi bilgisi (varsa)
                _vol_html_ana = ""
                if d.get("vol_trend", "YOK") != "YOK":
                    _vt = d["vol_trend"]
                    _vr = d.get("vol_ratio", 0.0)
                    _adj = d.get("score_adj", 0)
                    _vol_clr = {"ARTIYOR":"#27ae60","AZALIYOR":"#e74c3c","NORMAL":"#7f8c8d"}.get(_vt,"#7f8c8d")
                    _adj_str = f" <b style='color:{_vol_clr}'>({_adj:+d} skor)</b>" if _adj != 0 else ""
                    _vol_html_ana = (
                        f' | Hacim: <b style="color:{_vol_clr}">{_vt}</b> '
                        f'<small>(5g/20g = {_vr:.2f})</small>{_adj_str}'
                    )

                # v2.0.3.2: Max DD cezasi bilgisi
                _dd_html_ana = ""
                if d.get("dd_adj", 0) != 0:
                    _dd_val = d.get("max_dd")
                    _dd_clr = "#e74c3c"
                    _dd_html_ana = (
                        f' | Max DD: <b style="color:{_dd_clr}">{_dd_val:.1f}%</b> '
                        f'<b style="color:{_dd_clr}">({d["dd_adj"]:+d} skor)</b>'
                    )

                st.markdown(f"""
                <div class="ts-card" style="border-left:5px solid {sig_color};padding:12px 18px;">
                  <span class="ts-sig {sig_cls}">{sig_lbl}</span>
                  <span style="color:#6c7a9c;font-size:12px;margin-left:14px">
                    Trend: <b>{d['trend']}</b> &nbsp;|&nbsp;
                    Optima Skor: <b>{disp_score_ana}/100</b> &nbsp;|&nbsp;
                    MACD: <b>{d['macd']:.4f}</b>{_vol_html_ana}{_dd_html_ana}
                  </span>
                </div>""", unsafe_allow_html=True)

                # v2.0.3.2: Teknik Gostergeler expander
                render_teknik_gostergeler(d, float(sel_row_ana["Son_Fiyat"]))

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
                        # v2.0.4.57: Onceden hesaplanmis (worker.py, gece)
                        # Optima_Skor varsa ONU kullan - boylece bu sayfa,
                        # Ana Sayfa/BIST listesi/Portfoyum ile AYNI sayiyi
                        # gosterir. Yoksa (henuz precompute edilmediyse)
                        # eskisi gibi canli hesapla.
                        _precomp = sel_row_ana.get("Optima_Skor")
                        if _precomp is not None and _precomp == _precomp:
                            combined = float(_precomp)
                        else:
                            tech_with_fund = optima_score(d["rsi"], d["ret1m"], d["vol"], True, pb, pe, dy)
                            combined = max(0, min(100, round(tech_with_fund + d.get("total_adj", d.get("score_adj", 0)), 1)))
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
                            <small style='color:#6c7a9c'>Teknik Skor (RSI + Momentum + Vol)</small><br>
                            <b style='font-size:20px;color:#1b2a4a'>{d['score']:.1f} / 70</b><br><br>
                            <small style='color:#6c7a9c'>Temel Skor (F/K + PD/DD + Temettu + Kar)</small><br>
                            <b style='font-size:20px;color:#1b2a4a'>{fund_skor:.1f} / 30</b><br>
                            <hr style='border-color:#e0e8f4;margin:10px 0'>
                            <small style='color:#6c7a9c'>Master Skor</small><br>
                            <b style='font-size:30px;color:{clr}'>{combined}</b> <small>/100</small><br><br>
                            <span class="ts-sig {final_cls}">{final_lbl}</span>
                            </div>""", unsafe_allow_html=True)
                    except Exception as e:
                        st.warning(f"Temel analiz yuklenemedi: {e}")

        # v2.0.4.26: Gercek 3D pasta grafigi (once Plotly Pie + pull ile sahte
        # "3D-effect" deniyordu - aslinda duz/2D bir donut'tu, sadece dilimler
        # disari cekilmisti). Kullanicinin verdigi referans gorsele (parlak,
        # kalin kesitli, gercekten hacimli 3D pasta dilimleri) uygun olmasi
        # icin Plotly'nin native 3D pasta grafigi olmadigindan ozel bir SVG
        # ile elips govde + kenar/govde yuzeyleri (extrusion) cizilerek
        # gercek 3D dilim gorunumu elde edildi. Her dilim: ust yuz (aciklik
        # rengi), on/dis govde (koyu ton) ve iki radyal yan govde (orta ton)
        # olarak ayri path'lerle cizilir; arkadan one dogru z-sirasiyla
        # (sin(orta_aci) kucukten buyuge) cizilerek dogru ortusme saglanir.
        cat_sum=df_opt.groupby("Kategori")["Tutar (₺)"].sum().reset_index()
        n=len(cat_sum)
        colors=["#1b2a4a","#3b9eff","#00d4aa","#f4a300","#e74c3c",
                "#9b59b6","#2ecc71","#e67e22","#1abc9c","#e91e63"][:n]

        import math
        def _3d_pasta_ton(hex_renk, faktor):
            hex_renk = hex_renk.lstrip("#")
            r, g, b = int(hex_renk[0:2],16), int(hex_renk[2:4],16), int(hex_renk[4:6],16)
            if faktor >= 0:
                r, g, b = r+(255-r)*faktor, g+(255-g)*faktor, b+(255-b)*faktor
            else:
                r, g, b = r*(1+faktor), g*(1+faktor), b*(1+faktor)
            r, g, b = max(0,min(255,int(r))), max(0,min(255,int(g))), max(0,min(255,int(b)))
            return f"#{r:02x}{g:02x}{b:02x}"

        def _3d_pasta_nokta(cx, cy, rx, ry, aci_derece):
            a = math.radians(aci_derece)
            return cx + rx*math.cos(a), cy + ry*math.sin(a)

        def _3d_pasta_svg(etiketler, degerler, renkler, genislik=700, yukseklik=410):
            toplam = sum(degerler)
            cx0, cy0 = genislik*0.42, yukseklik*0.44
            rx, ry = genislik*0.235, yukseklik*0.265
            derinlik = ry*0.34
            # v2.0.4.43: Ayrik/patlatilmis dilim denemesinden (birkac
            # revizyon) vazgecildi - kullanici defalarca test etti, dilimin
            # ic kesit yuzeyi hicbir kalinlik degerinde dogru/dolu
            # gorunmedi ("vazo" hissi). Bitisik (explode'suz) tasarima geri
            # donuldu: tum dilimler ayni merkezi paylasiyor, aralarinda
            # bosluk/kesit yuzeyi hic olmadigi icin bu sorun yapisal olarak
            # ortaya cikamaz. Bu versiyon daha once kullanici tarafindan
            # onaylanmisti.

            acilar, basla = [], -90.0
            for v in degerler:
                bit = basla + (v/toplam)*360.0
                acilar.append((basla, bit))
                basla = bit

            dilimler = []
            for i, ((a0, a1), renk) in enumerate(zip(acilar, renkler)):
                orta = (a0+a1)/2.0
                dilimler.append(dict(i=i, a0=a0, a1=a1, orta=orta, renk=renk))

            sirali = sorted(dilimler, key=lambda w: math.sin(math.radians(w["orta"])))

            parcalar = [f'<svg viewBox="0 0 {genislik} {yukseklik}" width="100%" '
                        f'xmlns="http://www.w3.org/2000/svg" style="font-family:Segoe UI,Arial,sans-serif;">']
            parcalar.append(f'<text x="14" y="26" font-size="15" font-weight="700" fill="#1b2a4a">Kategori Dağılımı</text>')

            for w in sirali:
                a0, a1, renk = w["a0"], w["a1"], w["renk"]
                buyuk_yay = 1 if (a1-a0) > 180 else 0
                ust_renk = _3d_pasta_ton(renk, 0.14)
                govde_renk = _3d_pasta_ton(renk, -0.34)

                p0 = _3d_pasta_nokta(cx0, cy0, rx, ry, a0)
                p1 = _3d_pasta_nokta(cx0, cy0, rx, ry, a1)
                p0a = (p0[0], p0[1]+derinlik)
                p1a = (p1[0], p1[1]+derinlik)

                govde_yolu = (f"M {p0[0]:.2f},{p0[1]:.2f} "
                              f"A {rx},{ry} 0 {buyuk_yay} 1 {p1[0]:.2f},{p1[1]:.2f} "
                              f"L {p1a[0]:.2f},{p1a[1]:.2f} "
                              f"A {rx},{ry} 0 {buyuk_yay} 0 {p0a[0]:.2f},{p0a[1]:.2f} Z")
                parcalar.append(f'<path d="{govde_yolu}" fill="{govde_renk}"/>')

                ust_yolu = (f"M {cx0:.2f},{cy0:.2f} L {p0[0]:.2f},{p0[1]:.2f} "
                            f"A {rx},{ry} 0 {buyuk_yay} 1 {p1[0]:.2f},{p1[1]:.2f} Z")
                parcalar.append(f'<path d="{ust_yolu}" fill="{ust_renk}" stroke="#ffffff" stroke-width="1.5">'
                                 f'<title>{etiketler[w["i"]]}: %{degerler[w["i"]]/toplam*100:.1f}</title></path>')


            for w in dilimler:
                rad = math.radians(w["orta"])
                # v2.0.4.31: On/alt (front-facing, sin(orta)>0) dilimlerin

                # etiketleri pastanin govdesiyle cakisiyordu, cunku o
                # bolgede govde derinlik kadar daha asagiya taşiyor ama
                # eski formul sabit bir miktar YUKARI cekiyordu (tam ters
                # yönde). Şimdi on tarafa dogru orantili ek boşluk ekleniyor.
                lx = cx0 + math.cos(rad)*(rx*1.30)
                ly = cy0 + math.sin(rad)*(ry*1.30) + derinlik*max(0.0, math.sin(rad))*1.3
                yuzde = degerler[w["i"]]/toplam*100
                hiza = "start" if math.cos(rad) >= 0 else "end"
                parcalar.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="12.5" fill="#1b2a4a" '
                                 f'text-anchor="{hiza}" font-weight="600">{_html_esc(etiketler[w["i"]])}</text>')
                parcalar.append(f'<text x="{lx:.1f}" y="{ly+15:.1f}" font-size="11.5" fill="#5a6a8a" '
                                 f'text-anchor="{hiza}">%{yuzde:.1f}</text>')

            parcalar.append("</svg>")
            return "".join(parcalar)

        import html as _html_mod
        _html_esc = _html_mod.escape
        st.markdown(_3d_pasta_svg(cat_sum["Kategori"].tolist(),
                                    cat_sum["Tutar (₺)"].tolist(),
                                    colors), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# PORTFÖYÜM
# ══════════════════════════════════════════════════════════════
elif page=="Portföyüm":
    st.title("Portföyüm")
    portfolio = load_portfolio()

    # ── v1.9.11 - Birim Türü için akıllı default (UX iyileştirmesi) ──────────
    # Kullanici yeni varlik eklerken Birim Türünü kategoriden mantikli bir
    # baslangic degeriyle gosterir. Kullanici yine de manuel degistirebilir.
    def _default_unit_for(ticker: str, kategori: str) -> str:
        k = (kategori or "").upper()
        t = (ticker or "").upper()
        if k == "BIST":
            return "Lot"
        if k == "MADEN":
            # Gram-bazli kiymetli madenler
            if t in {"ALTIN_TRY", "GUMUS_TRY", "PLATIN_TRY"}:
                return "Gram"
            # Sikkeler ve diger madenler (Bakir, Paladyum vb.) -> Adet
            return "Adet"
        # TEFAS, KRIPTO, DOVIZ ve digerleri -> Adet
        return "Adet"

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
            sel_label = st.selectbox("Varlık", labels, index=None,
                                     placeholder="Varlık ara veya seç...",
                                     key="pf_varlik_sel")
            if sel_label is None:
                st.caption("Eklemek istediğiniz varlığı yukarıdan seçin.")
            else:
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
                    # v1.9.11 - Otomatik Birim Turu (UX)
                    # Default kategoriye gore (BIST->Lot, MADEN gram->Gram, vs).
                    # Key ticker'a baglandigi icin yeni varlik secildikce dropdown
                    # uygun default'a doner. Kullanici manuel de degistirebilir.
                    _unit_opts = ["Adet","Gram","Lot","Ons","Varil","Ton","kg","m²","Diğer"]
                    _def_unit  = _default_unit_for(pt, pt_cat)
                    _def_idx   = _unit_opts.index(_def_unit) if _def_unit in _unit_opts else 0
                    unit_type = st.selectbox("Birim Türü", _unit_opts,
                                              index=_def_idx,
                                              key=f"pf_unit_{pt}")
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

    # v2.0.4.50: Portfoydeki BIST hisselerini seans saatlerinde canli
    # yenile. refresh_bist_selective() zaten yazilmis ama hic
    # cagrilmiyordu - kucuk ticker sayisinda (portfoy tipik olarak
    # birkac hisse) hizli ve guvenli (1-50 ticker = 1-5sn).
    if _bist_seans_acik():
        _pf_bist_tickers = [
            t for t in _pf_tickers
            if not df_uni.loc[df_uni["Ticker"] == t, "Kategori"].empty
            and df_uni.loc[df_uni["Ticker"] == t, "Kategori"].iloc[0] == "BIST"
        ]
        if _pf_bist_tickers:
            df_uni = _ld_refresh_bist_sel(df_uni, _pf_bist_tickers)

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
            # v2.0.5.1: Skorun tek kaynagi Firsat Radari destekli Optima_Skor
            # (load_universe overlay) - tablo/Top5/Detay ile birebir ayni.
            _rs_pf = _row.get("Optima_Skor")
            _skor = float(_rs_pf) if (_rs_pf is not None and not _pd.isna(_rs_pf)) else live_optima_score(_row)
        else:
            _skor = 0.0
        _toplam = _adet * _guncel
        _kz_pct = ((_guncel/_alis-1)*100) if _alis>0 else 0.0

        # v2.0.3: Sinyal etiketi (hizli yontem - CSV verisi, yfinance cagrisi yok)
        # Trend tahmini: Ret1M >= 0 ise YUKSELIS, degilse DUSUS
        # (Detay panelinde MA20'ye gore daha hassas hesaplaniyor)
        if not _match.empty:
            _rsi_v = _sf(_row.get("RSI"), 50.0)
            _ret1m_v = _sf(_row.get("Ret1M"), 0.0)
            _trend_v = "YUKSELIS" if _ret1m_v >= 0 else "DUSUS"
            _sig_lbl, _ = get_signal(_skor, _rsi_v, _trend_v)
        else:
            _sig_lbl = "—"

        _id_map[_tkr + "_" + str(pos["id"])] = pos["id"]
        _kz_tl = _toplam - (_adet * _alis)
        _pf_rows.append({
            "Ticker":       _tkr,
            "Tarih":        _tg,
            "Miktar":       _adet,
            "Birim":        _unit,
            "Alış":         _alis,
            "Güncel":       _guncel,
            "Toplam":       _toplam,
            "K/Z":          round(_kz_tl, 2),
            "K/Z %":        _kz_pct,
            "Skor":         _skor,
            "Sinyal":       _sig_lbl,
            "_id":          pos["id"],
        })

    import pandas as _pd2
    df_pf = _pd2.DataFrame(_pf_rows)
    df_show = df_pf.drop(columns=["_id"])

    # v2.0.7.30 - K/Z ve K/Z % sutunlarina pozitif/negatif renk kodlamasi
    # (Bahri'nin talebi): pozitif yesil, negatif kirmizi. st.dataframe bir
    # pandas Styler kabul eder, column_config ile birlikte calisir.
    def _kz_renk(v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return ""
        if v > 0:
            return "color: #1b8a4a; font-weight: 600;"
        elif v < 0:
            return "color: #c0392b; font-weight: 600;"
        return ""

    # v2.0.7.31 - Sinyal renklendirmesi icin ortak _sinyal_renk_stil()
    # fonksiyonu kullanilir (bkz. clickable_table yakinindaki tanim) -
    # Ana Sayfa/BIST/TEFAS ile tutarli olsun diye kod tekrari yapilmadi.
    try:
        df_show_styled = df_show.style.map(_kz_renk, subset=["K/Z", "K/Z %"]) \
                                       .map(_sinyal_renk_stil, subset=["Sinyal"])
    except AttributeError:
        # eski pandas surumlerinde .map yok, .applymap kullan
        df_show_styled = df_show.style.applymap(_kz_renk, subset=["K/Z", "K/Z %"]) \
                                       .applymap(_sinyal_renk_stil, subset=["Sinyal"])

    # st.dataframe — Daraltilmis sutunlar + Sinyal eklendi
    _event = st.dataframe(
        df_show_styled,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            "Ticker": st.column_config.TextColumn(width="small"),
            "Tarih":  st.column_config.TextColumn(width="small"),
            "Miktar": st.column_config.NumberColumn(
                format="%.4f", width="small"),
            "Birim":  st.column_config.TextColumn(width="small"),
            "Alış":   st.column_config.NumberColumn(
                format="%.4f", width="small", help="Alış fiyatı (TL)"),
            "Güncel": st.column_config.NumberColumn(
                format="%.4f", width="small", help="Güncel piyasa fiyatı (TL)"),
            "Toplam": st.column_config.NumberColumn(
                format="%.2f", width="small", help="Pozisyon toplam değeri (TL)"),
            "K/Z":    st.column_config.NumberColumn(
                format="%+.2f", width="small", help="Kâr/Zarar (TL) — Toplam − Alış maliyeti"),
            "K/Z %":  st.column_config.NumberColumn(
                format="%+.2f%%", width="small", help="Kâr/Zarar yüzdesi"),
            "Skor":   st.column_config.NumberColumn(
                "Optima Skor",
                format="%.1f", help="Optima Skoru (0-100)"),
            "Sinyal": st.column_config.TextColumn(
                width="medium",
                help="Hızlı tahmin (RSI + Ret1M + Vol). Detaylı sinyal için satıra tıklayın."),
        }
    )

    # Toplam satırı — v2.0.7.28 (Bahri'nin talebi): Onceki versiyonda
    # "TOPLAM PORTFOY DEGERI" etiketi AYNI satirda soldan yer kapladigi
    # icin butun rakam satiri saga kayiyor, sutun agirliklari dogru olsa
    # bile hizalama tutmuyordu. Cozum: etiket AYRI bir ust satira alindi,
    # rakam satiri artik tablonun sol kenariyla AYNI noktadan basliyor -
    # boylece sutun agirliklari gercekten karsilik gelen sutunlarin
    # ALTINA denk geliyor (native dataframe oldugu icin yine de piksel
    # piksel garanti degil, ama onceki halden cok daha yakin).
    _total_val = df_pf["Toplam"].sum()
    _total_kz  = (df_pf["Toplam"] - df_pf["Miktar"]*df_pf["Alış"]).sum()
    _tcc = "#27ae60" if _total_kz>=0 else "#e74c3c"
    _tcs = "+" if _total_kz>=0 else ""
    # Sutun sirasi/agirliklari tablodaki fiili genisliklerle (ekran
    # goruntusunden olculdu) uyumlu: checkbox kucuk, veri sutunlari esit,
    # Optima Skor biraz genis, Sinyal en genis.
    _footer_kolonlar = [
        ("", 0.45),     # checkbox sutunu spaceri
        ("Ticker", 1), ("Tarih", 1), ("Miktar", 1), ("Birim", 1),
        ("Alış", 1), ("Güncel", 1),
        ("TOPLAM", 1), ("KZ", 1),
        ("", 1), ("", 1.2), ("", 1.9),
    ]
    _footer_html = ""
    for _etiket, _w in _footer_kolonlar:
        if _etiket == "TOPLAM":
            _icerik = f"<b style='font-size:15px;color:#1b2a4a;white-space:nowrap;'>{fmt_tr(_total_val)} TL</b>"
        elif _etiket == "KZ":
            _icerik = f"<b style='font-size:15px;color:{_tcc};white-space:nowrap;'>{_tcs}{fmt_tr(_total_kz)} TL</b>"
        else:
            _icerik = ""
        _footer_html += f"<div style='flex:{_w};text-align:right;padding:0 4px;white-space:nowrap;'>{_icerik}</div>"
    st.markdown(
        f"<div style='border-top:2px solid #2c3e6b;padding-top:6px;margin-top:2px;'>"
        f"<b style='font-size:13px;color:#6c7a9c;'>TOPLAM PORTFÖY DEĞERİ</b>"
        f"</div>"
        f"<div style='display:flex;flex-wrap:nowrap;padding:2px 4px 8px 4px;'>"
        f"{_footer_html}</div>",
        unsafe_allow_html=True
    )

    # Seçili satır(lar) — Coklu ise toplu Sil, tekli ise Sil + Analiz
    _sel = _event.selection.rows if hasattr(_event,"selection") else []
    if len(_sel) > 1:
        _sel_tickers = [_pf_rows[i]["Ticker"] for i in _sel]
        _sel_ids     = [_pf_rows[i]["_id"] for i in _sel]
        st.info(f"{len(_sel)} varlık seçildi: " + ", ".join(_sel_tickers))
        if st.button(f"Seçilen {len(_sel)} Varlığı Sil", type="secondary",
                     key="pf_sil_coklu"):
            for _sid in _sel_ids:
                delete_portfolio_item(_sid)
            st.rerun()
    elif _sel:
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
                # v2.0.4.x: Tabloyla AYNI sayiyi goster (bkz. Ana Sayfa Detay notu)
                # v2.0.5.1: Skorun TEK kaynagi Firsat Radari (bkz. Ana Sayfa notu).
                _rd_pf = _sr.get("Optima_Skor")
                disp_score_pf = float(_rd_pf) if (_rd_pf is not None and _rd_pf == _rd_pf) else _d["score"]
                # v2.0.7.34 - ayni tutarlilik kurali: fiyatsiz varligin skoru daima 0.
                if float(_sr.get("Son_Fiyat", 0) or 0) <= 0:
                    disp_score_pf = 0.0
                _sig_lbl, _sig_cls = get_signal(disp_score_pf,_d["rsi"],_d["trend"])
            _m1,_m2,_m3,_m4,_m5 = st.columns(5)
            _m1.metric("Son Fiyat",   f"{float(_sr['Son_Fiyat']):,.4f}")
            _m2.metric("Optima Skor", f"{disp_score_pf:.1f}")
            _m3.metric("RSI (14)",    f"{_d['rsi']:.1f}")
            _m4.metric("1A Getiri %", f"{_d['ret1m']:+.2f}%")
            _m5.metric("Yıllık Vol %",f"{_d['vol']:.1f}%")
            _sc = SIG_COLORS.get(_sig_cls,"#666")

            # v2.0.3: Hacim trendi bilgisi (varsa)
            _vol_html = ""
            if _d.get("vol_trend","YOK") != "YOK":
                _vt = _d["vol_trend"]
                _vr = _d.get("vol_ratio", 0.0)
                _adj = _d.get("score_adj", 0)
                _vol_clr = {"ARTIYOR":"#27ae60","AZALIYOR":"#e74c3c","NORMAL":"#7f8c8d"}.get(_vt,"#7f8c8d")
                _adj_str = f" <b style='color:{_vol_clr}'>({_adj:+d} skor)</b>" if _adj != 0 else ""
                _vol_html = (
                    f' | Hacim: <b style="color:{_vol_clr}">{_vt}</b> '
                    f'<small>(5g/20g = {_vr:.2f})</small>{_adj_str}'
                )

            # v2.0.3.2: Max DD cezasi bilgisi (kullaniciya hatirlat)
            _dd_html = ""
            if _d.get("dd_adj", 0) != 0:
                _dd_val = _d.get("max_dd")
                _dd_clr = "#e74c3c"
                _dd_html = (
                    f' | Max DD: <b style="color:{_dd_clr}">{_dd_val:.1f}%</b> '
                    f'<b style="color:{_dd_clr}">({_d["dd_adj"]:+d} skor)</b>'
                )

            st.markdown(f'''<div class="ts-card" style="border-left:5px solid {_sc};padding:12px 18px;">
      <span class="ts-sig {_sig_cls}">{_sig_lbl}</span>
      <span style="color:#6c7a9c;font-size:12px;margin-left:14px">
        Trend: <b>{_d["trend"]}</b> | Optima Skor: <b>{disp_score_pf}/100</b> | MACD: <b>{_d["macd"]:.4f}</b>{_vol_html}{_dd_html}
      </span></div>''', unsafe_allow_html=True)

            # v2.0.3.2: Teknik Gostergeler expander
            render_teknik_gostergeler(_d, float(_sr["Son_Fiyat"]))

            if not _d["hist"].empty:
                _fig = candle_fig(_d["hist"],_sel_tkr)
                if _fig: st.plotly_chart(_fig, use_container_width=True)
            else:
                st.info(f"{_sel_tkr} için geçmiş fiyat verisi yüklenemedi.")

            # v2.0.3.1: BIST varligi icin Temel Analiz blogu (kategori sayfasiyla ayni mantik)
            _sel_cat = str(_sr["Kategori"])
            if _sel_cat == "BIST":
                st.divider()
                st.subheader("Temel Analiz")
                try:
                    from kap_client import (fetch_kap_fundamentals, fundamentals_to_display,
                                            score_from_fundamentals, get_kap_url)
                    _kap_url = get_kap_url(_sel_tkr)

                    with st.spinner("Temel veriler yükleniyor (yfinance + KAP)..."):
                        _raw  = fetch_kap_fundamentals(_sel_tkr)
                        _disp = fundamentals_to_display(_raw)
                        _fund_skor = score_from_fundamentals(_raw, float(_sr["Son_Fiyat"]))

                    _pb = _raw.get("pb_ratio"); _pe = _raw.get("pe_ratio"); _dy = _raw.get("div_yield")
                    _precomp2 = _sr.get("Optima_Skor")
                    if _precomp2 is not None and _precomp2 == _precomp2:
                        _combined = float(_precomp2)
                    else:
                        _tech_with_fund = optima_score(_d["rsi"], _d["ret1m"], _d["vol"], True, _pb, _pe, _dy)
                        _combined = max(0, min(100, round(_tech_with_fund + _d.get("total_adj", _d.get("score_adj", 0)), 1)))
                    _final_lbl, _final_cls = get_signal(_combined, _d["rsi"], _d["trend"])

                    # Kaynak bilgisi
                    _src_note = "yfinance"
                    if _raw.get("_kap_available"):
                        _src_note += " + KAP"
                    elif _raw.get("_kap_note"):
                        _src_note += f" | KAP: {_raw['_kap_note']}"
                    st.caption(f"Kaynak: {_src_note}")

                    if _kap_url:
                        st.caption(f"[KAP Finansal Bilgiler Sayfası]({_kap_url})")

                    _ka, _kb = st.columns([2, 1])
                    with _ka:
                        _rows_html = "".join(
                            f"<tr><td>{k}</td><td><b>{v}</b></td></tr>"
                            for k, v in _disp.items()
                        )
                        st.markdown(
                            f'<table class="kap-table">{_rows_html}</table>',
                            unsafe_allow_html=True
                        )
                    with _kb:
                        _clr = SIG_COLORS.get(_final_cls, "#666")
                        st.markdown(f"""
                        <div class="ts-card">
                        <b style='font-size:14px'>Skor Bileşimi</b><br><br>
                        <small style='color:#6c7a9c'>Teknik Skor (RSI + Momentum + Vol)</small><br>
                        <b style='font-size:20px;color:#1b2a4a'>{_d['score']:.1f} / 70</b><br><br>
                        <small style='color:#6c7a9c'>Temel Skor (F/K + PD/DD + Temettü + Kâr)</small><br>
                        <b style='font-size:20px;color:#1b2a4a'>{_fund_skor:.1f} / 30</b><br>
                        <hr style='border-color:#e0e8f4;margin:10px 0'>
                        <small style='color:#6c7a9c'>Master Skor</small><br>
                        <b style='font-size:30px;color:{_clr}'>{_combined}</b> <small>/100</small><br><br>
                        <span class="ts-sig {_final_cls}">{_final_lbl}</span>
                        </div>
                        """, unsafe_allow_html=True)

                except Exception as e:
                    st.warning(f"Temel analiz yüklenemedi: {e}")
                    st.info("Kontrol: `pip install yfinance` kurulu mu?")

    st.caption("Analiz için tablodaki varlığın solundaki kutucuğu işaretleyin.")



# ══════ KATEGORİ SAYFALARI ══════
elif page in CAT:
    cat_code=CAT[page]
    st.title(page)
    if df_uni.empty: st.error("`python worker.py` çalıştırın."); st.stop()

    # v2.0.7.45 - Ons Altın (USD) - Bahri'nin talebi: SADECE bilgi amaçlı,
    # TL'ymiş gibi gizlenmeden USD olarak gösterilir. Evrene/skorlamaya/
    # bütçe dağıtımına KATILMAZ (bkz. bigpara_client.fetch_truncgil_ons_usd
    # docstring) - bu yüzden ayrı bir metrik olarak, kategori tablosunun
    # dışında gösteriliyor.
    if cat_code == "MADEN":
        @st.cache_data(ttl=1800, show_spinner=False)
        def _ons_usd_cached():
            try:
                from bigpara_client import fetch_truncgil_ons_usd
                return fetch_truncgil_ons_usd()
            except Exception:
                return 0.0
        _ons_usd = _ons_usd_cached()
        if _ons_usd > 0:
            st.caption(f"ℹ️ Ons Altın (USD, bilgi amaçlı — TL fiyatlara dahil değildir): **${_ons_usd:,.2f}**")

    df_cat=df_uni[df_uni["Kategori"]==cat_code].copy()
    if df_cat.empty: st.warning(f"{page} verisi bulunamadı."); st.stop()

    # v2.0.4.50: BIST icin manuel canli yenileme butonu. Tum 772 hisseyi
    # otomatik/her sayfa yuklemesinde canli cekmek gecmiste denendi ve
    # cok yavas cikti (bkz. live_data.py notlari, 380+ saniye) - o yuzden
    # burada SADECE kullanici acikca isterse, makul bir ust sinirla (ilk
    # 100 hisse, fiyati zaten olanlar) calisiyor.
    if cat_code == "BIST" and _bist_seans_acik():
        if st.button("Canlı Fiyatları Yenile (ilk 100 hisse)", key="btn_bist_canli_yenile"):
            _hedef = df_cat[df_cat["Son_Fiyat"] > 0].head(100)["Ticker"].tolist()
            with st.spinner(f"{len(_hedef)} hisse için canlı fiyat çekiliyor..."):
                _t_baslangic = __import__("time").time()
                df_uni = _ld_refresh_bist_sel(df_uni, _hedef)
                _sure = __import__("time").time() - _t_baslangic
            st.caption(f"Tamamlandı ({_sure:.1f} sn) — {len(_hedef)} hisse yenilendi.")
            df_cat = df_uni[df_uni["Kategori"] == cat_code].copy()
    elif cat_code == "BIST":
        st.caption("Canlı yenileme sadece BIST seans saatlerinde (hafta içi 10:00-18:00) kullanılabilir.")

    # Optima Skoru hesapla (BIST icin oncelikle worker.py'nin onceden
    # hesapladigi tam skor kullanilir - bkz. v2.0.4.57 notu, Ana Sayfa'daki
    # ayni mantik)
    if "Optima_Skor" in df_cat.columns and df_cat["Optima_Skor"].notna().any():
        df_cat["Optima_Skor"] = pd.to_numeric(df_cat["Optima_Skor"], errors="coerce")
        _eksik_c = df_cat["Optima_Skor"].isna()
        if _eksik_c.any():
            df_cat.loc[_eksik_c, "Optima_Skor"] = df_cat.loc[_eksik_c].apply(
                lambda r: optima_score(float(r.get("RSI",50)),float(r.get("Ret1M",0)),
                                       vol=float(r.get("Vol",30) or 30)), axis=1)
    else:
        df_cat["Optima_Skor"]=df_cat.apply(
            lambda r: optima_score(float(r.get("RSI",50)),float(r.get("Ret1M",0)),
                                   vol=float(r.get("Vol",30) or 30)),axis=1)

    # Fiyatlılar üste, fiyatsızlar alta — skor sıralı
    # v2.0.5.2: Islem gormeyen (fiyatsiz) varligin skoru HER kosulda 0 -
    # notr varsayilanlar (RSI=50/Ret1M=0/Vol=30) 45 puan uretiyordu, "veri
    # yok" durumu vasat skor gibi gorunuyordu. CSV eski olsa bile burada
    # sifirlanir (worker.py'ye de ayni kural eklendi).
    df_cat.loc[df_cat["Son_Fiyat"] <= 0, "Optima_Skor"] = 0.0
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
    # v2.0.5.1: Top 5 dogrudan radar destekli Optima_Skor'dan (load_universe
    # overlay). Onceki "ilk 15 adayi canli hesapla" yontemi kaldirildi -
    # Firsat Radari zaten TUM evreni ayni formulle taradigindan gereksiz,
    # ayrica buyuk tabloyla ayni kaynagi kullanmak siralama tutarliligini
    # garanti eder.
    top5 = degerli.nlargest(5, "Optima_Skor")
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
    # v2.0.7.46 - Arama kutusu artik TUM kategorilerde (once sadece BIST/
    # TEFAS icin vardi - Bahri'nin talebi: Doviz 63'e, Kripto 186'ya
    # cikinca onlarda da arama gerekli hale geldi). Mantik zaten kategoriden
    # bagimsizdi, sadece kisitlama kaldirildi.
    srch=st.text_input("Ara",placeholder="Ticker veya ad...",key=f"srch_{page}")
    if srch.strip():
        mask=(df_cat["Ticker"].str.contains(srch.strip().upper(),na=False)|
              df_cat["Ad"].str.contains(srch.strip(),case=False,na=False))
        df_cat=df_cat[mask]

    # v2.0.5.1: Sayfalama KALDIRILDI - 772 varligin tamami tek listede.
    # st.dataframe satirlari sanallastirarak cizdigi icin 772 satir hizli
    # render edilir (kaydirma ile gezilir). Skor kaynagi artik Firsat
    # Radari (load_universe'te overlay, 15 dk'da bir tam-evren, worker
    # formulunun birebir aynisi) oldugu icin sayfa-ici canli hesap
    # (live_optima_score, 50 satir) da kaldirildi - hem 772 satirda
    # yapilamazdi hem de kuresel siralamayi bozuyordu (skor sayfa icinde
    # azalirken sonraki sayfada artiyordu). Tek kaynak = tutarli siralama.
    sel_now = st.session_state.get(f"sel_{page}", "")

    df_page_show = df_cat[["Ticker","Ad","Son_Fiyat","RSI","Ret1M","Optima_Skor"]].copy()
    df_page_show.columns = ["Ticker","Ad","Son Fiyat","RSI","1A Getiri%","Optima Skor"]
    df_page_show["Ad"] = df_page_show["Ad"].astype(str).str[:50]
    st.caption(f"{len(df_cat)} varlik - Optima Skoruna gore sirali")
    new_sel = clickable_table(df_page_show, key=f"cat_{page}_full", sel_ticker=sel_now)
    if new_sel and new_sel != sel_now:
        st.session_state[f"sel_{page}"] = new_sel
        st.rerun()

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
        # v2.0.4.x: Tabloyla AYNI sayiyi goster (bkz. Ana Sayfa Detay notu)
        # v2.0.5.1: Skorun TEK kaynagi Firsat Radari (bkz. Ana Sayfa notu).
        _rd_cat = sel_row.get("Optima_Skor")
        disp_score_cat = float(_rd_cat) if (_rd_cat is not None and _rd_cat == _rd_cat) else d["score"]
        # v2.0.7.34 - TUTARLILIK DUZELTMESI (Bahri'nin 12 Temmuz bulgusu):
        # sel_row, DUZELTILMEMIS df_uni'den okunuyor - "Tum Varliklar"
        # listesindeki "fiyatsiz varligin skoru HER ZAMAN 0'dir" kurali
        # (bkz. df_cat.loc[Son_Fiyat<=0, Optima_Skor]=0.0) buraya hic
        # yansimiyordu. Sonuc: CLINK/ICP gibi fiyati 0 olan varliklar,
        # enrich()'in kendi (genelde notr varsayilanlardan tureyen)
        # skoruyla KADEMELI AL/NET SAT gibi anlamli gorunen ama aslinda
        # veri yoklugundan kaynaklanan celiskili sinyaller uretiyordu.
        # Ayni kural burada da uygulanir.
        if float(sel_row.get("Son_Fiyat", 0) or 0) <= 0:
            disp_score_cat = 0.0
        sig_lbl,sig_cls=get_signal(disp_score_cat,d["rsi"],d["trend"])

    r1,r2,r3,r4,r5=st.columns(5)
    r1.metric("Son Fiyat",f"{float(sel_row['Son_Fiyat']):,.4f}")
    r2.metric("Optima Skor",f"{disp_score_cat:.1f}")
    r3.metric("RSI (14)",f"{d['rsi']:.1f}")
    r4.metric("1A Getiri %",f"{d['ret1m']:+.2f}%")
    r5.metric("Yıllık Vol %",f"{d['vol']:.1f}%")

    sig_color=SIG_COLORS.get(sig_cls,"#666")

    # v2.0.3: Hacim trendi bilgisi (varsa)
    vol_html = ""
    if d.get("vol_trend","YOK") != "YOK":
        _vt = d["vol_trend"]
        _vr = d.get("vol_ratio", 0.0)
        _adj = d.get("score_adj", 0)
        _vol_clr = {"ARTIYOR":"#27ae60","AZALIYOR":"#e74c3c","NORMAL":"#7f8c8d"}.get(_vt,"#7f8c8d")
        _adj_str = f" <b style='color:{_vol_clr}'>({_adj:+d} skor)</b>" if _adj != 0 else ""
        vol_html = (
            f' &nbsp;|&nbsp; Hacim: <b style="color:{_vol_clr}">{_vt}</b> '
            f'<small>(5g/20g = {_vr:.2f})</small>{_adj_str}'
        )

    # v2.0.3.2: Max DD cezasi bilgisi
    dd_html = ""
    if d.get("dd_adj", 0) != 0:
        _dd_val = d.get("max_dd")
        dd_html = (
            f' &nbsp;|&nbsp; Max DD: <b style="color:#e74c3c">{_dd_val:.1f}%</b> '
            f'<b style="color:#e74c3c">({d["dd_adj"]:+d} skor)</b>'
        )

    st.markdown(f"""
    <div class="ts-card" style="border-left:5px solid {sig_color};padding:12px 18px;">
      <span class="ts-sig {sig_cls}">{sig_lbl}</span>
      <span style="color:#6c7a9c;font-size:12px;margin-left:14px">
        Trend: <b>{d['trend']}</b> &nbsp;|&nbsp;
        Optima Skor: <b>{disp_score_cat}/100</b> &nbsp;|&nbsp;
        MACD: <b>{d['macd']:.4f}</b>{vol_html}{dd_html}
      </span>
    </div>""",unsafe_allow_html=True)

    # v2.0.3.2: Teknik Gostergeler expander
    render_teknik_gostergeler(d, float(sel_row["Son_Fiyat"]))

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
            # v2.0.4.57: Onceden hesaplanmis skoru tercih et (bkz. yukaridaki
            # diger iki detay bloguyla ayni mantik)
            _precomp3 = sel_row.get("Optima_Skor")
            if _precomp3 is not None and _precomp3 == _precomp3:
                combined = float(_precomp3)
            else:
                _tech_with_fund = optima_score(d["rsi"], d["ret1m"], d["vol"], True, pb, pe, dy)
                combined = max(0, min(100, round(_tech_with_fund + d.get("total_adj", d.get("score_adj", 0)), 1)))
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
                clr = SIG_COLORS.get(final_cls, "#666")
                st.markdown(f"""
                <div class="ts-card">
                <b style='font-size:14px'>Skor Bileşimi</b><br><br>
                <small style='color:#6c7a9c'>Teknik Skor (RSI + Momentum + Vol)</small><br>
                <b style='font-size:20px;color:#1b2a4a'>{d['score']:.1f} / 70</b><br><br>
                <small style='color:#6c7a9c'>Temel Skor (F/K + PD/DD + Temettü + Kâr)</small><br>
                <b style='font-size:20px;color:#1b2a4a'>{fund_skor:.1f} / 30</b><br>
                <hr style='border-color:#e0e8f4;margin:10px 0'>
                <small style='color:#6c7a9c'>Master Skor</small><br>
                <b style='font-size:30px;color:{clr}'>{combined}</b> <small>/100</small><br><br>
                <span class="ts-sig {final_cls}">{final_lbl}</span>
                </div>
                """, unsafe_allow_html=True)

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

    # ── v2.0.4: Yaklaşan Halka Arzlar (henüz borsada işlem görmeyen, ──────────
    # ── izahname sürecindeki şirketler) — KAP izahname bildirimlerinden ──────
    st.subheader("Yaklaşan Halka Arzlar")
    st.caption(
        "Kaynak: KAP (Kamuyu Aydınlatma Platformu) — İzahname bildirimleri, "
        "iki aşama: SPK Onayına Sunulan (başvuru) ve SPK Tarafından Onaylanan "
        "(talep toplama sürecinde/yakında). Sadece henüz BIST evreninde olmayan "
        "(yeni) şirketler gösterilir; mevcut şirketlerin sermaye artırımı "
        "izahnameleri hariç tutulur."
    )
    _col_baslik, _col_buton = st.columns([5, 1])
    with _col_buton:
        _zorla_yenile = st.button("Zorla Yenile", help="12 saatlik önbelleği atlayıp KAP'tan taze veri çeker (yavaş olabilir)")
    try:
        from upcoming_ipo_client import fetch_upcoming_ipos
        with st.spinner("KAP izahname bildirimleri yükleniyor..."):
            df_upcoming = fetch_upcoming_ipos(force_refresh=_zorla_yenile)
    except Exception as _uip_ex:
        df_upcoming = pd.DataFrame()
        st.info(
            f"Yaklaşan halka arz verisi şu an yüklenemedi. "
            f"(Teknik not: {_uip_ex})"
        )

    if not df_upcoming.empty:
        # v2.0.4.10: st.dataframe metin sarma (word-wrap) desteklemediginden
        # (uzun Durum/Kod metinleri "..." ile kesiliyordu, Tarih'te gereksiz
        # saat bilgisi vardi, alt not dusuk kontrastli gorunuyordu) tablo
        # ozel stillendirilmis bir HTML tabloya cevrildi - boylece hucre
        # icinde tam metin sarma, okunur kontrast ve Arz Fiyati'nin bagimsiz
        # degerlere (Graham/Carpan) gore nerede durdugunu gosteren bir
        # "Referans Araligi" sutunu eklenebildi.
        import html as _html

        def _fmt_num(v, suffix=""):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return "—"
            return f"{v:,.2f}{suffix}".replace(",", "X").replace(".", ",").replace("X", ".")

        def _arz_renk(arz, graham, carpan):
            """Arz Fiyati'nin bagimsiz Graham/Carpan degerlerine gore nerede
            durdugunu renkle gosterir (yesil: altinda/iskontolu, sari: aralik
            icinde, kirmizi: ustunde/pahali). Tavsiye degildir - sadece
            karsilastirmadir. Not: Referans Araligi ayri bir sutun olarak
            gosterilmiyor cunku zaten Graham Degeri ve Carpan Bazli Deger
            sutunlari yan yana - okuyucu iki sayiyi dogrudan karsilastirabilir,
            ayri bir sutun gereksiz tekrar oluyordu."""
            degerler = [v for v in (graham, carpan) if v is not None and not pd.isna(v)]
            if not degerler or arz is None or (isinstance(arz, float) and pd.isna(arz)):
                return ""
            alt, ust = min(degerler), max(degerler)
            if arz < alt:
                return "background-color:#e6f4ea;"  # yesilimsi - referansin altinda
            elif arz > ust:
                return "background-color:#fdeaea;"  # kirmizimsi - referansin ustunde
            else:
                return "background-color:#fff8e1;"  # sarimsi - aralik icinde

        _basliklar = [
            ("Tarih", "9%"), ("Kod", "7%"), ("Şirket", "18%"), ("Durum", "15%"),
            ("Arz Fiyatı (TL)", "10%"), ("İskonto (%)", "8%"),
            ("Graham Değeri (TL)", "12%"), ("Çarpan Bazlı Değer (TL)", "12%"),
            ("Rapor", "9%"),
        ]
        _tooltips = [
            "", "", "", "",
            "Fiyat Tespit Raporu'ndan otomatik çıkarılmıştır (bulunamazsa boş kalır)",
            "Halka arz iskontosu — Fiyat Tespit Raporu'ndan otomatik çıkarılmıştır",
            "Bağımsız, muhafazakar taban değer — √(22.5 × Hisse Başı Kâr × Hisse Başı Özkaynak). Arz Fiyatı hücresinin rengi bu değerle Çarpan Bazlı Değer'in alt-üst sınırına göre belirlenir.",
            "Bağımsız değer — Şirket EBITDA'sı × sektör medyan çarpanı, net borç düşülüp hisse sayısına bölünmüştür",
            "Fiyat Tespit Raporu — Resmi KAP bildirimi (varsa)",
        ]

        _rows_html = []
        for _, r in df_upcoming.iterrows():
            tarih_gosterim = str(r.get("Tarih", "") or "").split(" ")[0]
            kod = _html.escape(str(r.get("Kod", "") or ""))
            sirket = _html.escape(str(r.get("Sirket", "") or ""))
            durum = _html.escape(str(r.get("Durum", "") or ""))
            arz = r.get("Arz_Fiyati")
            iskonto = r.get("Iskonto_Orani")
            graham = r.get("Graham_Degeri")
            carpan = r.get("Carpan_Bazli_Deger")
            url = r.get("Fiyat_Tespit_URL", "") or ""
            arz_bg = _arz_renk(arz, graham, carpan)
            link_html = (f'<a href="{_html.escape(url)}" target="_blank">KAP\'ta Aç</a>'
                         if url else "—")
            _rows_html.append(f"""
            <tr>
                <td>{_html.escape(tarih_gosterim)}</td>
                <td>{kod}</td>
                <td>{sirket}</td>
                <td>{durum}</td>
                <td style="{arz_bg}">{_fmt_num(arz)}</td>
                <td>{_fmt_num(iskonto, "%")}</td>
                <td>{_fmt_num(graham)}</td>
                <td>{_fmt_num(carpan)}</td>
                <td>{link_html}</td>
            </tr>""")

        _thead = "".join(
            f'<th style="width:{w};" title="{_html.escape(tip)}">{_html.escape(baslik)}</th>'
            for (baslik, w), tip in zip(_basliklar, _tooltips)
        )

        st.markdown(f"""
        <style>
        @media (min-width: 769px) {{
            .block-container {{ padding-left: 2rem !important; padding-right: 2rem !important;
                                 max-width: 100% !important; }}
        }}
        .ha-tablo-wrap {{ overflow-x: auto; }}
        table.ha-tablo {{ width: 100%; min-width: 820px; border-collapse: collapse; table-layout: fixed;
                           font-size: 14.5px; }}
        table.ha-tablo th {{ background-color: #0d2b4e; color: #ffffff; text-align: left;
                              padding: 10px 12px; font-weight: 600; white-space: normal;
                              font-size: 13.5px; line-height: 1.3; }}
        table.ha-tablo td {{ padding: 10px 12px; border-bottom: 1px solid #e3e7ec;
                              white-space: normal; word-wrap: break-word;
                              vertical-align: top; color: #1a1a1a; line-height: 1.4; }}
        table.ha-tablo td:first-child {{ white-space: nowrap; }}
        table.ha-tablo tr:nth-child(even) {{ background-color: #f7f9fb; }}
        </style>
        <div class="ha-tablo-wrap">
        <table class="ha-tablo">
        <thead><tr>{_thead}</tr></thead>
        <tbody>{"".join(_rows_html)}</tbody>
        </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            "<div style='color:#333333; font-size:14px; line-height:1.5; margin-top:10px;'>"
            "<b>Nasıl okunur:</b> Arz Fiyatı hücresindeki renk, o fiyatın "
            "<b>Graham Değeri</b> ile <b>Çarpan Bazlı Değer</b>'in alt-üst "
            "sınırına göre nerede durduğunu gösterir — "
            "<span style='background-color:#e6f4ea;'>yeşil</span>: Arz Fiyatı "
            "her ikisinin de altında (iki bağımsız modele göre görece "
            "iskontolu), <span style='background-color:#fff8e1;'>sarı</span>: "
            "ikisinin arasında, <span style='background-color:#fdeaea;'>kırmızı</span>: "
            "ikisinin de üstünde (görece pahalı). Bu bir alım tavsiyesi ya da "
            "\"bu fiyatın altından al\" önerisi değildir — sadece TrendSurf "
            "Optima'nın kendi bağımsız modellerinin aracı kurumun arz "
            "fiyatıyla karşılaştırmasıdır; iki model de kendi varsayımlarına "
            "bağlıdır ve gerçek değeri garanti etmez."
            "<br><br>"
            "Diğer notlar: Şirket bazlı getiri tahmini sunulmaz. Arz Fiyatı / "
            "İskonto sütunları Fiyat Tespit Raporu PDF'inden otomatik olarak "
            "çıkarılır; bazı raporlarda format farkı nedeniyle boş kalabilir. "
            "İskonto oranı yalnızca aracı kurumun hesapladığı değere göre "
            "uygulanan indirim yüzdesidir — arz sonrası fiyat performansını "
            "göstermez. \"Fiyat Tespit Raporu\" sütunundaki link, KAP'ın resmi "
            "belgesine götürür (henüz yayınlanmamışsa boş görünür). Detaylı "
            "bilgi için <a href='https://www.kap.org.tr/tr/bildirim-sorgu' "
            "target='_blank'>KAP Bildirim Sorgulama</a> sayfasını ziyaret "
            "edebilirsiniz."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Şu anda takip edilen yeni halka arz başvurusu bulunmuyor.")

    st.divider()

    # ── Mevcut: XHARZ Endeks Üyeleri (borsada işlem gören, son 2 yıl) ────────
    st.subheader("XHARZ Endeks Üyeleri")
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
            "Çözüm: borsaistanbul.com -> Endeksler -> Excel olarak indir -> "
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
    # v2.0.4.25: Halka Arz sayfasindaki gibi st.dataframe (dinamik sutun
    # genislikleri -> yatay scroll) sabit genislikli HTML tabloya cevrildi.
    # Ayrica Ex-Date'e 14 gun veya daha az kalan satirlar renkle vurgulaniyor
    # (temettu hakkindan faydalanmak icin o tarihten once alinmis olmasi
    # gerektigi icin bu "aksiyon alinabilir" bir sinyal - Halka Arz'daki
    # Arz Fiyati renklendirmesiyle ayni mantik: bagimsiz bir sinyali goze
    # carpacak sekilde one cikarmak).
    import html as _html
    from datetime import datetime as _dt, timedelta as _td

    def _fmt_num(v, suffix="", ondalik=2):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        return f"{v:,.{ondalik}f}{suffix}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _exdate_renk(ex_date_str):
        """Ex-Date'e 14 gun veya daha az varsa turuncumsu vurgu (yakinda
        temettu hakki dusuyor - hisseyi elde tutmak/almak icin son gunler).
        Tarih gecmisse renklendirme yapilmaz (zaten gecmis kayittir)."""
        if not ex_date_str:
            return ""
        try:
            d = _dt.strptime(str(ex_date_str), "%d.%m.%Y")
            bugun = _dt.now()
            if bugun <= d <= bugun + _td(days=14):
                return "background-color:#fff3e0;"
        except Exception:
            pass
        return ""

    _kolonlar = []  # (anahtar, baslik, genislik, tooltip, hizalama)
    if "Ticker" in df_show.columns:
        _kolonlar.append(("Ticker", "Ticker", "6%", "", "nowrap"))
    if "Şirket" in df_show.columns:
        _kolonlar.append(("Şirket", "Şirket", "15%", "", ""))
    if "Son_Fiyat" in df_show.columns:
        _kolonlar.append(("Son_Fiyat", "Fiyat (₺)", "8%", "Son kapanış fiyatı", ""))
    if "div_per_share" in df_show.columns:
        _kolonlar.append(("div_per_share", "Temettü/Hisse (₺)", "10%",
                           "Hisse başına ödenen/duyurulan brüt temettü tutarı (yfinance)", ""))
    if "div_yield" in df_show.columns:
        _kolonlar.append(("div_yield", "Temettü Verimi %", "9%",
                           "Temettü/Hisse ÷ Fiyat × 100", ""))
    if "ex_date" in df_show.columns:
        _kolonlar.append(("ex_date", "Ex-Date", "9%",
                           "Haklardan düşme tarihi — temettüyü almak için bu tarihten önce hisseye sahip olunmalı", "nowrap"))
    if "Durum" in df_show.columns:
        _kolonlar.append(("Durum", "Durum", "11%",
                           "Yaklaşıyor: ex-date bugün veya ileride. Geçti: ex-date geçmişte kalmış (referans amaçlı gösterilir).", "nowrap"))
    if "frequency" in df_show.columns:
        _kolonlar.append(("frequency", "Sıklık", "6%", "Temettü ödeme sıklığı", ""))
    if "Ret1M" in df_show.columns:
        _kolonlar.append(("Ret1M", "1A Getiri %", "8%", "Son 1 aylık fiyat getirisi", ""))
    if "Optima_Skor" in df_show.columns:
        _kolonlar.append(("Optima_Skor", "Optima Skor", "8%",
                           "TrendSurf Optima bileşik puanı (0-100)", ""))
    if "Toplam_Getiri" in df_show.columns:
        _kolonlar.append(("Toplam_Getiri", "Tahmini Toplam Getiri %", "8%",
                           "1 Aylık Momentum + Temettü Verimi (gösterge, yatırım tavsiyesi değildir)", ""))
    if "KAP_URL" in df_show.columns:
        _kolonlar.append(("KAP_URL", "KAP", "9%", "Kamuyu Aydınlatma Platformu şirket sayfası", ""))

    _thead = "".join(
        f'<th style="width:{w};" title="{_html.escape(tip)}">{_html.escape(baslik)}</th>'
        for (_, baslik, w, tip, _hiz) in _kolonlar
    )

    _rows_html = []
    for _, r in df_show.iterrows():
        ex_date_val = r.get("ex_date") if "ex_date" in df_show.columns else None
        exdate_bg = _exdate_renk(ex_date_val)
        _tds = []
        for anahtar, _baslik, _w, _tip, hiz in _kolonlar:
            v = r.get(anahtar)
            if anahtar in ("Ticker", "Şirket", "frequency"):
                deger = _html.escape(str(v)) if v is not None and not (isinstance(v, float) and pd.isna(v)) else "—"
            elif anahtar == "ex_date":
                _bos = v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "" or str(v).lower() == "nan"
                deger = "—" if _bos else _html.escape(str(v))
            elif anahtar == "Durum":
                _durum_stil = {"Yaklaşıyor": ("#c8e6c9", "#1b5e20"),
                               "Geçti":      ("#e0e0e0", "#616161")}.get(str(v))
                _durum_txt = _html.escape(str(v)).upper() if v is not None else "—"
                if _durum_stil:
                    _bgc, _fgc = _durum_stil
                    deger = (f'<span style="background:{_bgc};color:{_fgc};'
                             f'padding:4px 9px;border-radius:12px;font-size:12px;'
                             f'font-weight:700;letter-spacing:0.2px;'
                             f'display:inline-block;white-space:nowrap;">'
                             f'{_durum_txt}</span>')
                else:
                    deger = _durum_txt
            elif anahtar == "div_per_share":
                deger = _fmt_num(v, ondalik=4)
            elif anahtar == "div_yield":
                deger = _fmt_num(v, suffix="%")
            elif anahtar == "Ret1M":
                deger = _fmt_num(v, suffix="%")
            elif anahtar == "Optima_Skor":
                deger = _fmt_num(v, ondalik=1)
            elif anahtar == "Toplam_Getiri":
                deger = _fmt_num(v, suffix="%")
            elif anahtar == "KAP_URL":
                _bos = v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "" or str(v).lower() == "nan"
                deger = ("—" if _bos else f'<a href="{_html.escape(str(v))}" target="_blank">Görüntüle</a>')
            else:
                deger = _fmt_num(v)
            nowrap = "white-space:nowrap;" if hiz == "nowrap" else ""
            bg = exdate_bg if anahtar == "ex_date" else ""
            stil = f' style="{bg}{nowrap}"' if (bg or nowrap) else ""
            _tds.append(f"<td{stil}>{deger}</td>")
        _rows_html.append(f"<tr>{''.join(_tds)}</tr>")

    st.markdown(f"""
    <style>
    @media (min-width: 769px) {{
        .block-container {{ padding-left: 2rem !important; padding-right: 2rem !important;
                             max-width: 100% !important; }}
    }}
    .tm-tablo-wrap {{ overflow-x: auto; }}
    table.tm-tablo {{ width: 100%; min-width: 900px; border-collapse: collapse; table-layout: fixed;
                       font-size: 14.5px; }}
    table.tm-tablo th {{ background-color: #0d2b4e; color: #ffffff; text-align: left;
                          padding: 10px 12px; font-weight: 600; white-space: normal;
                          font-size: 13.5px; line-height: 1.3; }}
    table.tm-tablo td {{ padding: 10px 12px; border-bottom: 1px solid #e3e7ec;
                          white-space: normal; word-wrap: break-word;
                          vertical-align: top; color: #1a1a1a; line-height: 1.4; }}
    table.tm-tablo tr:nth-child(even) {{ background-color: #f7f9fb; }}
    </style>
    <div class="tm-tablo-wrap">
    <table class="tm-tablo">
    <thead><tr>{_thead}</tr></thead>
    <tbody>{"".join(_rows_html)}</tbody>
    </table>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<div style='color:#333333; font-size:14px; line-height:1.6; margin-top:10px;'>"
        "<b>Bu tablo nedir:</b> BIST Temettü Endeksi (XTMTU) üyesi şirketlerin temettü "
        "getirisini ve kısa vadeli fiyat momentumunu bir arada gösterir — düzenli nakit "
        "temettü dağıtan şirketleri karşılaştırmak için kullanılır."
        "<br><br>"
        "<b>Nasıl okunur:</b> "
        "<span style='background-color:#fff3e0;'>Turuncu</span> vurgulu Ex-Date hücreleri, "
        "haklardan düşme tarihine 14 gün veya daha az kaldığını gösterir — temettüyü almak "
        "için hisseye bu tarihten <i>önceki</i> günün kapanışında sahip olunması gerekir; "
        "ex-date'te veya sonrasında alım o dönemin temettüsünü kaçırır. "
        "<b>Temettü Verimi %</b>, Temettü/Hisse ÷ Fiyat oranıdır — sırf fiyat artışından değil, "
        "düzenli nakit dağıtımından elde edilen getiriyi ölçer. "
        "<b>Tahmini Toplam Getiri %</b> = 1 Aylık Momentum + Temettü Verimi; kaba bir gösterge "
        "olup kesin bir öngörü değildir, çünkü 1 aylık kısa vadeli hareketi yıllık bir oranla topluyor."
        "<br><br>"
        "<b>Nasıl kullanılır — üç yöntem:</b>"
        "<br>"
        "<b>1. Temettü geliri hesabı:</b> Portföy Bütçesi × Temettü Verimi % = o hisseye "
        "yatırılırsa yıllık beklenen brüt nakit temettü tutarı (stopaj bu hesaba dahil değildir, "
        "ayrıca düşülmelidir)."
        "<br>"
        "<b>2. Ex-date takvimi:</b> Yaklaşan (turuncu vurgulu) ve yüksek verimli satırları "
        "filtreleyerek, o ayki temettü hakkını kaçırmadan almak istenen hisselerin bir listesini "
        "çıkarmak için kullanılabilir."
        "<br>"
        "<b>3. Kalite filtresi:</b> Sadece en yüksek Temettü Verimi %'ne bakmak yanıltıcı "
        "olabilir — bazen düşen fiyat verimi yapay olarak şişirir. Optima Skor ve 1A Getiri "
        "sütunlarıyla birlikte değerlendirip, \"yüksek verim + pozitif/nötr momentum + makul "
        "Optima Skor\" kombinasyonunu arayan bir eleme yapılabilir."
        "<br><br>"
        "Buradaki hiçbir sayı yatırım tavsiyesi değildir — geçmiş/duyurulmuş verilerin "
        "matematiksel bir özetidir."
        "</div>", unsafe_allow_html=True
    )

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
        },
        {
            "baslik": "Yaş Grupları Bazında Yatırımcı Sayıları",
            "aciklama": "Demografik dağılım — yaş grubu ve cinsiyet bazında yatırımcı profili.",
            "url": "https://www.vap.org.tr/yas-gruplari-bazinda-yatirimci-sayilari",
        },
        {
            "baslik": "Yerli / Yabancı Pay Senedi Analizi",
            "aciklama": "Yerli ve yabancı yatırımcıların pay senedi portföy dağılımı.",
            "url": "https://www.vap.org.tr/yerli-yabanci-pay-senedi-analizi",
        },
        {
            "baslik": "Yabancı Yatırımcı Sayıları (İlk 10 Ülke)",
            "aciklama": "Ülke bazında yabancı yatırımcı sayıları ve portföy değerleri.",
            "url": "https://www.vap.org.tr/pay-senedi-yabanci-yatirimci-sayilari-ilk-10-ulke",
        },
        {
            "baslik": "BIST Endeksleri Bazında Portföy Değerleri",
            "aciklama": "9 farklı BIST endeksi için yatırımcı sayısı ve portföy değeri.",
            "url": "https://www.vap.org.tr/bist-endeksleri-bazinda-portfoy-degerleri",
        },
        {
            "baslik": "Dönemsel Finansal Oranlar",
            "aciklama": "BIST şirketlerinin F/K, PD/DD, temettü verimi gibi finansal oranları.",
            "url": "https://www.vap.org.tr/donemsel-finansal-oranlar",
        },
        {
            "baslik": "REKS — Risk İştahı Endeksi",
            "aciklama": "Türkiye sermaye piyasası risk iştahı endeksi ve tarihsel trendi.",
            "url": "https://www.vap.org.tr/reks",
        },
        {
            "baslik": "MKK Aylık Piyasa Bülteni",
            "aciklama": "Yatırımcı ve piyasa verilerinin aylık özet raporu (PDF).",
            "url": "https://www.mkk.com.tr/veri-hizmetleri/mkk-aylik-piyasa-bulteni",
        },
    ]

    _makro_cols = st.columns(2)
    for _mi, _link in enumerate(VAP_LINKS):
        with _makro_cols[_mi % 2]:
            st.markdown(
                f'''<a href="{_link['url']}" target="_blank" style="text-decoration:none;">
                <div style="background:#fff;border:1.5px solid #c8d6e8;border-radius:10px;
                            padding:16px 18px;margin-bottom:14px;cursor:pointer;">
                    <div style="font-size:14px;font-weight:700;color:#1b2a4a;
                                margin-bottom:6px;">{_link['baslik']}</div>
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

    # v2.0.4.45: Yardim sayfasi tamamen el kitaplarina cevrildi. Icerik,
    # ayri .md dosyalarindan okunuyor (app.py'yi sismemesi icin) - bu
    # dosyalar TrendSurf_Optima klasorunde app.py ile ayni dizinde
    # bulunmali: el_kitabi_abone.md / el_kitabi_admin.md. Ayrica orijinal
    # Word (.docx) dosyalarini indirebilmek icin bir buton da ekleniyor.
    import os as _os_yk

    if is_admin:
        _md_dosya = "el_kitabi_admin.md"
        _docx_dosya = "TrendSurf_Optima_Yonetici_El_Kitabi.docx"
        _baslik = "Admin El Kitabı"
        _altbaslik = "TrendSurf Optima — Sistem Mimarisi ve İşletim Kılavuzu (GİZLİ — yalnızca yönetici)"
    else:
        _md_dosya = "el_kitabi_abone.md"
        _docx_dosya = "TrendSurf_Optima_Abone_El_Kitabi.docx"
        _baslik = "Kullanıcı El Kitabı"
        _altbaslik = "TrendSurf Optima — Nasıl Kullanılır, Değerler Ne Anlama Gelir"

    st.title(_baslik)
    st.caption(_altbaslik)

    _md_yol = _os_yk.path.join(_os_yk.path.dirname(__file__), _md_dosya)
    _docx_yol = _os_yk.path.join(_os_yk.path.dirname(__file__), _docx_dosya)

    if _os_yk.path.exists(_docx_yol):
        with open(_docx_yol, "rb") as _f:
            st.download_button(
                "📄 Word (.docx) olarak indir",
                data=_f.read(),
                file_name=_docx_dosya,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    st.divider()

    if _os_yk.path.exists(_md_yol):
        with open(_md_yol, "r", encoding="utf-8") as _f:
            _icerik = _f.read()
        st.markdown(_icerik, unsafe_allow_html=True)
    else:
        st.warning(f"El kitabı içerik dosyası bulunamadı: {_md_dosya}. Bu dosyanın app.py ile aynı klasörde olduğundan emin olun.")
