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
                remember = st.checkbox("Beni Hatirla (90 gün)", key="li_remember", value=True)

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
                            _tok_safe = res["token"].replace("'","").replace('"','')
                            _em_safe = email.replace("'","").replace('"','')
                            _stc_v1.html(f"""
                            <script>
                            try {{
                              window.parent.localStorage.setItem('tso_auth_token', '{_tok_safe}');
                              window.parent.sessionStorage.setItem('tso_logged_in', '1');
                              var d = new Date();
                              d.setTime(d.getTime() + 90*24*60*60*1000);
                              window.parent.document.cookie = "ts_rem_email=" +
                                  encodeURIComponent('{_em_safe}') +
                                  ";expires=" + d.toUTCString() +
                                  ";path=/;SameSite=Lax";
                              console.log('[tso] auth+email saved to browser');
                            }} catch(e) {{ console.log('[tso] save err:', e); }}
                            </script>
                            """, height=0)
                            print(f"[auth] Beni Hatirla aktif: 90 gun localStorage + email cookie")
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
                # v2.0.3: Volume varsa ekle
                _cols = ["Open","High","Low","Close"]
                if "Volume" in _h.columns:
                    _cols.append("Volume")
                return _h[_cols].dropna(subset=["Open","High","Low","Close"])
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
            # v2.0.3: Volume varsa ekle (hacim subplot icin)
            cols = ["Open", "High", "Low", "Close"]
            if "Volume" in h.columns:
                cols.append("Volume")
            return h[cols].dropna(subset=["Open","High","Low","Close"])
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
    # v1.9.7.1 - Canli veri indikatoru (her autorefresh'te timestamp guncellenir)
    # v1.9.7.4 - Saat damgasi TRT (Europe/Istanbul), UTC yerine
    import datetime as _dt_now
    try:
        from zoneinfo import ZoneInfo as _ZI_sb
        _now_str = _dt_now.datetime.now(_ZI_sb("Europe/Istanbul")).strftime("%H:%M:%S")
    except Exception:
        # ZoneInfo yoksa: UTC+3 manuel ofset
        _now_str = (_dt_now.datetime.utcnow() + _dt_now.timedelta(hours=3)).strftime("%H:%M:%S")
    st.markdown(
        '<style>'
        '@keyframes tso_pulse { 0%,100% {opacity:1;} 50% {opacity:0.35;} }'
        '.tso-live-dot { display:inline-block; width:8px; height:8px; '
        '  border-radius:50%; background:#22c55e; margin-right:6px; '
        '  animation: tso_pulse 2s ease-in-out infinite; '
        '  box-shadow: 0 0 6px #22c55e88;}'
        '.tso-live-box { background:#f0f7f0; border:1px solid #c5e1c5; '
        '  border-radius:6px; padding:6px 10px; margin:6px 0 4px 0; '
        '  font-size:11px; color:#1b2a4a; }'
        '</style>'
        f'<div class="tso-live-box">'
        f'<span class="tso-live-dot"></span>'
        f'<b>Canlı veri</b> &nbsp;•&nbsp; '
        f'<span style="color:#4a5a7a">{_now_str}</span>'
        f'</div>',
        unsafe_allow_html=True
    )
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
            # help= parametresi Streamlit'in button rendering'ini farklilastiriyor
            # (silik/okunmaz hale getiriyor); aciklamayi caption olarak yaziyoruz.
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
        # v1.9.9.2 - localStorage + sessionStorage + email cookie temizle
        # components.v1.html ile script gercekten calisir (st.markdown calismaz)
        _stc_v1.html("""
        <script>
        try {
          window.parent.localStorage.removeItem('tso_auth_token');
          window.parent.sessionStorage.removeItem('tso_logged_in');
          window.parent.document.cookie =
              "ts_rem_email=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
          console.log('[tso] auth cleared from browser');
        } catch(e) { console.log('[tso] clear err:', e); }
        </script>
        """, height=0)
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
                    Optima Skor: <b>{d['score']}/100</b> &nbsp;|&nbsp;
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
                        # v2.0.3.4: Portfoyum/kategori sayfalariyla ayni formul
                        # (teknik+temel primli optima_score + hacim/DD ayari)
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
        _pf_rows.append({
            "Ticker":       _tkr,
            "Tarih":        _tg,
            "Miktar":       _adet,
            "Birim":        _unit,
            "Alış":         _alis,
            "Güncel":       _guncel,
            "Toplam":       _toplam,
            "K/Z %":        _kz_pct,
            "Skor":         _skor,
            "Sinyal":       _sig_lbl,
            "_id":          pos["id"],
        })

    import pandas as _pd2
    df_pf = _pd2.DataFrame(_pf_rows)
    df_show = df_pf.drop(columns=["_id"])

    # st.dataframe — Daraltilmis sutunlar + Sinyal eklendi
    _event = st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
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
            "K/Z %":  st.column_config.NumberColumn(
                format="%+.2f%%", width="small", help="Kâr/Zarar yüzdesi"),
            "Skor":   st.column_config.NumberColumn(
                format="%.1f", width="small", help="Optima Skoru (0-100)"),
            "Sinyal": st.column_config.TextColumn(
                width="medium",
                help="Hızlı tahmin (RSI + Ret1M + Vol). Detaylı sinyal için satıra tıklayın."),
        }
    )

    # Toplam satırı
    _total_val = df_pf["Toplam"].sum()
    _total_kz  = (df_pf["Toplam"] - df_pf["Miktar"]*df_pf["Alış"]).sum()
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
        Trend: <b>{_d["trend"]}</b> | Optima Skor: <b>{_d["score"]}/100</b> | MACD: <b>{_d["macd"]:.4f}</b>{_vol_html}{_dd_html}
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
        Optima Skor: <b>{d['score']}/100</b> &nbsp;|&nbsp;
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
            # v2.0.3: Temel analiz primi + hacim duzeltmesi
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
    try:
        from upcoming_ipo_client import fetch_upcoming_ipos
        with st.spinner("KAP izahname bildirimleri yükleniyor..."):
            df_upcoming = fetch_upcoming_ipos()
    except Exception as _uip_ex:
        df_upcoming = pd.DataFrame()
        st.info(
            f"Yaklaşan halka arz verisi şu an yüklenemedi. "
            f"(Teknik not: {_uip_ex})"
        )

    if not df_upcoming.empty:
        _cols_show = [c for c in ["Tarih","Kod","Sirket","Konu","Durum","Fiyat_Tespit_URL"]
                      if c in df_upcoming.columns]
        st.dataframe(
            df_upcoming[_cols_show],
            use_container_width=True, hide_index=True,
            column_config={
                "Fiyat_Tespit_URL": st.column_config.LinkColumn(
                    "Fiyat Tespit Raporu",
                    display_text="KAP'ta Aç",
                    help="Resmi KAP bildirimi - arz fiyatının belirlendiği rapor (varsa)",
                ),
            } if "Fiyat_Tespit_URL" in df_upcoming.columns else None,
        )
        st.caption(
            "Not: Şirket bazlı getiri tahmini sunulmaz — bu bilgilendirme "
            "amaçlıdır, yatırım tavsiyesi değildir. \"Fiyat Tespit Raporu\" "
            "sütunundaki link, KAP'ın resmi belgesine götürür (henüz "
            "yayınlanmamışsa boş görünür). Detaylı bilgi için "
            "[KAP Bildirim Sorgulama](https://www.kap.org.tr/tr/bildirim-sorgu) "
            "sayfasını ziyaret edebilirsiniz."
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

**Veri Akisi:** `worker.py` -> `optimized_universe.csv` -> `app.py` -> kullanici

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
- kap_client.py -> kap.org.tr sirket sayfalari
- yfinance info (P/E, beta, dividendYield)

**Halka Arz / Tetemttu:**
- KAP RSC endpoint (Next.js) -> endeks uyeleri
- Yedek: Endeksler.xlsx
""")

        with st.expander("3. GitHub ve Deployment", expanded=False):
            st.markdown("""
**GitHub Repo:** `github.com/cbguler/trendsurf-optima` (private)

**Streamlit Cloud:**
`https://trendsurf-optima-mxqgu6qvkmqbkmaorwmquj.streamlit.app`

**Streamlit Cloud Secrets** (App Settings -> Secrets):
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

**Yeni Abone Onaylama:** Admin Paneli -> Bekleyen Kullanicilar -> Onayla

**Sifre Sifirlama:**
- `python auth_reset.py` (lokal)
- Veya Giris ekrani -> Sifremi Unuttum

**SQLite Veritabani:** `trendsurf.db`
- Tablolar: `users`, `sessions`, `portfolio`, `reset_tokens`
- Streamlit Cloud'da Reboot yaparsan sifirlanir — Reboot yerine F5 kullan
""")

        with st.expander("5. E-posta Sistemi", expanded=False):
            st.markdown("""
**Gonderim Zamanlayici:**
- Windows Task Scheduler: `emailler.py` — 08:30 ve 11:30
- Manuel: Sol menu -> E-posta Ayarlari -> Simdi Gonder

**Gmail App Password Yenileme:**
1. `myaccount.google.com/apppasswords` adresine git
2. Yeni App Password olustur (TrendSurf)
3. Streamlit Cloud Secrets -> EMAIL_PASS guncelle
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
| Uygulama acilamiyor | Streamlit gizlilik | share.streamlit.io -> Settings -> Public |
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
- Giris ekraninda **Sifremi Unuttum** sekmesi -> e-posta adresinizi girin
- Sifirlama baglantisi e-postaniza gelir
""")

        with st.expander("Ana Sayfa — Portfoy Optimizasyonu", expanded=False):
            st.markdown("""
Ana Sayfa, butce ve risk tercihine gore en iyi yatirim firsatlarini listeler.

**Sol Panelden Ayarlar:**
- **Portfoy Butcesi (TL):** Yatirim dusundugunuz toplam tutar
- **Risk Toleransi:** Cok Dusuk -> Cok Yuksek (5 seviye)
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

**Fiyat Girisi:** Ondalik ayirici virgul -> `6.480,00`

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
