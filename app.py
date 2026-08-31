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
/* v2.0.7.146 (Bahri'nin bulgusu, ikinci kez bildirdi - "sayfaların
   üstlerindeki devasa boşluk her sayfada var"): Streamlit'in KENDİ
   varsayılan .block-container üst dolgusu (araç çubuğuyla çakışmasın
   diye tasarımda bırakılan, genellikle ~6rem gibi geniş bir değer)
   şimdiye kadar hiç küçültülmemişti - sadece MOBİL breakpoint'te
   (aşağıdaki @media satırı) küçültülüyordu, masaüstü/geniş görünümde
   Streamlit'in varsayılanı aynen kalıyordu. Bu CSS global olduğu için
   (her sayfa aynı stili paylaşıyor) "her sayfada var" şikayeti tam
   olarak buradan kaynaklanıyordu. Not: sadece st.set_page_config'teki
   Streamlit sürüm varsayılanına bağlı olarak bu deger degisebilir; asil
   test canli ortamda yapilmali.*/
.block-container{padding-top:2rem!important;}
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
/* v2.0.7.149 (Bahri'nin talebi, 18 Ağustos 2026): "Sidebar'daki
   aralıkları da azaltmamız gerekiyor" - Streamlit'in varsayılan
   element-container üst/alt boşlukları sidebar'da (dar bir alanda çok
   sayıda kontrol olduğu için) gereksiz büyük görünüyordu. */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:0.35rem!important;}
[data-testid="stSidebar"] .element-container{margin-bottom:0!important;}
[data-testid="stSidebar"] hr{margin:0.6rem 0!important;}
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
# v2.0.7.160 (Bahri'nin talebi, 19 Agustos 2026): "Haberler" sayfasi
# eklendi. Menude EN ALTA konuldu - tek istisna El Kitabi, cunku sidebar
# onu PAGES[:-1] + [el_kitabi_etiketi] seklinde kuruyor (yani PAGES'in
# SON elemani HER ZAMAN "Yardim" olmak zorunda, yoksa navigasyon bozulur).
PAGES = ["Ana Sayfa","Portföyüm","BIST","TEFAS","Döviz","Değerli Madenler","Kriptolar","Halka Arz","Temettü","Makro Göstergeler","SonDakika Haberleri","Abonelik","Yardım"]
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

        # v2.0.7.138 (Bahri'nin bulgusu, 11 Ağustos 2026 — "TUPRS'a baktım,
        # başka hisseler de var mıdır?" sorusu üzerine tarama): bu uç nokta
        # da (e-posta tetikleyicisi) kendi ayrı CSV yükünü yapıyordu ve
        # load_universe()'in Fırsat Radarı overlay'ini (Supabase
        # intraday_scores, 20 dk taze) HİÇ uygulamıyordu - Temettü/Halka
        # Arz'da bulunanla AYNI hata. Artık burada da uygulanıyor.
        try:
            from db import get_intraday_overlay
            _rd_map = get_intraday_overlay(45)
            if _rd_map:
                _mask_rd = _df_uni["Ticker"].astype(str).isin(_rd_map.keys())
                if _mask_rd.any():
                    if "Optima_Skor" not in _df_uni.columns:
                        _df_uni["Optima_Skor"] = pd.NA
                    _df_uni.loc[_mask_rd, "Optima_Skor"] = _df_uni.loc[_mask_rd, "Ticker"].astype(str).map(
                        lambda t: _rd_map[t]["skor"])
                    _mask_bist_rd = _mask_rd & (_df_uni["Kategori"] == "BIST")
                    if _mask_bist_rd.any():
                        for _col, _key in (("Son_Fiyat","fiyat"),("RSI","rsi"),("Ret1M","ret1m")):
                            _df_uni.loc[_mask_bist_rd, _col] = _df_uni.loc[_mask_bist_rd, "Ticker"].astype(str).map(
                                lambda t, _k=_key: _rd_map[t][_k])
        except Exception as _rd_err_trig:
            print(f"[radar-overlay][trigger] atlandi: {_rd_err_trig}")

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
        st.write(f"OK: Email gonderildi ({fmt_tr(_dt,1)}s)")
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
                if st.button("Şifremi Güncelle", width='stretch', key="btn_rp"):
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

                submitted = st.form_submit_button("Giris Yap", width='stretch')

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
            if st.button("Kayit Ol", key="btn_register", width='stretch'):
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
            if st.button("Sıfırlama Bağlantısı Gönder", width='stretch', key="btn_reset"):
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

# v2.0.7.88 - GERI ALINDI (Bahri'nin bulgusu): v2.0.7.87'de eklenen
# st.empty()+"Yukleniyor..." yer tutucusu beklenen isi yapmadi - Streamlit
# yeni elemani ESKI elemanlarin YERINE koymuyor, yanina/ustune EKLIYOR;
# script bitene kadar onceki calismadan kalan (giris formu gibi) elemanlar
# sayfada kalmaya devam ediyor. Sonuc, sorunu cozmek yerine ustune bir
# mesaj daha eklemek oldu (daha karisik gorunum). Asil cozum yukleme
# suresinin KISALTILMASI (bkz. "Ilk acilis yavasligi" - mimari odunlesim,
# PROJE_NOTLARI.md) - kozmetik bir yama ile duzeltilemez.

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


@st.cache_data(ttl=300,show_spinner=False)  # v1.9.4: 60s -> 600s (kullanici beklemesi 1dk yerine 10dk'da bir)
# v2.0.7.219 (Bahri'nin bulgusu, 31 Ağustos 2026 — TEFAS workflow'unu
# elle çalıştırıp CSV'nin başarıyla güncellendiğini doğruladı, ama
# uygulamada tarayıcı yenilemesiyle yeni değer görünmedi - sadece TAM
# REBOOT sonrası göründü): 600sn (10 dk) -> 300sn (5 dk). Kök neden
# kod hatası DEĞİLDİ - bu, `st.cache_data`'nın SUNUCU TARAFI, TÜM
# kullanıcılar arası PAYLAŞIMLI önbelleği - tarayıcı yenilemesi bunu
# TEMİZLEMEZ, sadece TTL süresi dolunca (ya da uygulama yeniden
# başlayınca) yeni veri okunur.
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

# v2.0.7.132 (Bahri'nin bulgusu, TUPRS 83,0 vs 68,0 celiskisi): skor
# hesaplama mantigi (_teknik_alt_skor, _temel_alt_skor, optima_score,
# get_signal) paylasilan scoring.py modulune tasindi - artik hem app.py
# hem temettu_client.py AYNI, TEK kaynagi kullaniyor (temettu_client.py
# app.py'yi guvenle import edemezdi, bu yuzden CSV'den donmus deger
# kopyaliyordu - bkz. scoring.py'nin modul docstring'i).
from scoring import _teknik_alt_skor, _temel_alt_skor, optima_score, get_signal, optima_score_breakdown


def _render_skor_pasta_grafigi(d, row, key_prefix="det"):
    """v2.0.7.144 (Bahri'nin talebi, 18 Ağustos 2026): "Optima Skor'u
    oluşturan unsurları pasta grafik olarak görebilmek istiyorum, her
    varlık sayfasının en başındaki devasa boşluğa oturtabiliriz" -
    scoring.optima_score_breakdown() ile TUTARLI (aynı RSI/Ret1M/Vol/
    PB/PE/DY girdilerinden, aynı bileşenler - toplamı gösterilen Optima
    Skor'a eşittir, ayrı bir hesaplama yolu YOK).

    Üç ayrı Detay bloğunda (Ana Sayfa, Portföyüm, Kategori sayfaları)
    ORTAK kullanılıyor - tek kaynak, üç kopya yok.

    d: enrich()'in döndürdüğü dict (rsi/ret1m/vol içerir)
    row: PB/PE/DY (varsa) içeren pandas Series (df_uni satırı)."""
    try:
        _pb, _pe, _dy = row.get("PB"), row.get("PE"), row.get("DY")
        _has_fund = any(
            v is not None and str(v) != "nan" and float(v or 0) > 0
            for v in (_pb, _pe, _dy)
        )
        _parcalar = optima_score_breakdown(
            float(d.get("rsi", 50)), float(d.get("ret1m", 0)),
            vol=float(d.get("vol", 30)), has_fundamental=_has_fund,
            pb=_pb, pe=_pe, dy=_dy)
        _parcalar = {k: v for k, v in _parcalar.items() if v > 0}
        if not _parcalar:
            st.caption("Skor bileşimi için yeterli veri yok.")
            return
        import plotly.graph_objects as go
        _renkler_pasta = {
            "RSI Bölgesi": "#1d4ed8", "Momentum": "#15803d", "Volatilite": "#b45309",
            "F/K": "#7e22ce", "PD/DD": "#a21caf", "Temettü Verimi": "#0e7490",
        }
        fig = go.Figure(data=[go.Pie(
            labels=list(_parcalar.keys()), values=list(_parcalar.values()),
            marker=dict(colors=[_renkler_pasta.get(k, "#6b7280") for k in _parcalar.keys()],
                       line=dict(color="white", width=2)),
            hole=0.45, textinfo="label+percent", textposition="outside",
            hovertemplate="<b>%{label}</b>: %{value:.1f} puan<extra></extra>",
        )])
        fig.update_layout(
            height=300, margin=dict(l=10, r=10, t=35, b=10),
            showlegend=False,
            title=dict(text="Optima Skor Bileşimi", font=dict(size=13, color="#1b2a4a"), x=0.5),
            paper_bgcolor="white",
            annotations=[dict(text=f"<b>{fmt_tr(sum(_parcalar.values()),1)}</b>",
                              x=0.5, y=0.5, font=dict(size=20, color="#1b2a4a"),
                              showarrow=False)],
        )
        st.plotly_chart(fig, use_container_width=True, key=f"pasta_{key_prefix}_{row.get('Ticker','')}")
    except Exception as _pasta_err:
        st.caption(f"Skor bileşimi grafiği yüklenemedi: {_pasta_err}")



def _csv_alan(row, kolon):
    """CSV satirindan (worker.py'nin dondurulmus/toplu snapshot'i) bir
    sayisal alani guvenle okur - kolon yoksa veya NaN ise None doner.
    v2.0.7.105'te eklendi: bkz. asagidaki 3 Detay blogundaki ayni not."""
    try:
        v = row.get(kolon)
        if v is None:
            return None
        v = float(v)
        return None if v != v else v  # NaN kontrolu
    except Exception:
        return None

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
    # v2.0.7.69 - KRITIK DUZELTME (Bahri'nin bulgusu): worker.py bu
    # satirin RSI/Ret1M/Vol'unun SAHTE NOTR degerler oldugunu (gercek
    # gecmis veri bulunamadigi icin) acikca isaretlemisse, asagidaki
    # hesaplamalara hic girmeden dogrudan 0 dondur - Son_Fiyat<=0 ile
    # AYNI mantik (bkz. kategori sayfasindaki ayni yorum).
    # v2.0.7.77 - KRITIK DUZELTME (Bahri'nin bulgusu, FZJ/TEFAS ornegi):
    # bool(x) Python'da NaN icin de True doner ("NaN sifir degil" mantigi
    # yuzunden) - ama bu bayrak SADECE DOVIZ/MADEN satirlarinda ayarlanir,
    # TEFAS/BIST/KRIPTO'da hic yok, yani df birlestirilince NaN olur.
    # bool(NaN)==True oldugu icin TEFAS/BIST/KRIPTO'nun HEPSI yanlislikla
    # "veri yok" sanilip skoru sifirlaniyordu - liste tablosu ise "== True"
    # kullandigindan (NaN==True daima False) bu hataya hic dusmuyordu, bu
    # yuzden liste dogru/detay yanlis gibi bir celiski olusuyordu. Asagidaki
    # "== True" karsilastirmasi liste ile AYNI (dogru) mantigi kullanir.
    if row.get("_gecmis_veri_yok") == True:
        return 0.0
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


@st.cache_data(show_spinner=False, ttl=600)
def _clickable_table_turkce_format(df_show: pd.DataFrame, kolon_ondalik_items: tuple):
    """v2.0.7.63 - PERFORMANS (Bahri'nin bulgusu: "sistem agirlasti",
    eski sayfali gorunume DONMEK ISTEMIYOR): Turkce format donusumu
    (.apply ile hucre hucre string islemi) BIST(772)/TEFAS(1339) gibi
    buyuk, sayfasiz listelerde her Streamlit yeniden calismasinda
    (her tiklamada) TEKRAR TEKRAR yapiliyordu - asil yavaslama kaynagi
    muhtemelen buydu. Alttaki veri zaten load_universe() ile 10 dk
    onbelleklendigi icin, bu donusumu de AYNI onbellege alip sadece
    veri GERCEKTEN degistiginde yeniden hesaplamak mantikli - ayni
    tabloya tekrar tekrar tiklamak artik hicbir bicimlendirme maliyeti
    getirmez (cache hit)."""
    df_show = df_show.copy()
    _turkce_cevrilen = []
    for c, dec in kolon_ondalik_items:
        if c in df_show.columns:
            df_show[c] = df_show[c].apply(lambda v: fmt_tr(v, dec))
            _turkce_cevrilen.append(c)
    return df_show, _turkce_cevrilen


def clickable_table(df_show, key, sel_ticker="", col_cfg=None):
    """on_select ile satır seçimi — checkbox Streamlit'in kendi davranışı.

    v2.0.4.29: col_cfg parametresi eklendi. Öncesinde bu fonksiyon dışarıdan
    sütun ayarı (genişlik, başlık, format) kabul etmiyordu - çağıran kod
    özenle bir col_cfg sözlüğü hazırlasa bile sessizce yok sayılıyordu.
    Şimdi disaridan verilen col_cfg, otomatik tespit edilenin üzerine yazar.

    v2.0.7.31: "Sinyal" sutunu varsa otomatik renklendirilir (bkz.
    _sinyal_renk_stil). Ana Sayfa, BIST, TEFAS - hepsi bu fonksiyonu
    kullandigi icin tek yerden tum tablolara yayilir.

    v2.0.7.60 - KRITIK, SISTEM GENELI DUZELTME (Bahri'nin bulgusu:
    "Turkce sayi formati sorunu her sayfada karsima cikiyor"): Bu fonksiyon
    Ana Sayfa/BIST/TEFAS/Doviz/Maden/Kripto TARAFINDAN PAYLASILIYOR - NumberColumn
    format="%.4f" gibi INGILIZCE format string'leri kullaniyordu, bu yuzden
    TEK bir yerdeki hata butun bu sayfalara ayni anda yayiliyordu. Simdi
    numerik sutunlar Turkce bicimli metne cevriliyor (Portfoyum'deki
    duzeltmeyle AYNI desen) - boylece Ana Sayfa/BIST/TEFAS/Doviz/Maden/
    Kripto'nun HEPSI TEK SEFERDE duzelir.

    v2.0.7.63 - Turkce donusumu artik _clickable_table_turkce_format()
    icinde ONBELLEKLI yapiliyor (bkz. o fonksiyonun docstring'i).
    """
    # v2.0.7.60 - kolon adina gore ondalik hassasiyeti (eski NumberColumn
    # format spec'leriyle AYNI hassasiyet, sadece artik Turkce virgul).
    _kolon_ondalik = {
        "Son Fiyat": 4, "Fiyat": 4, "Emir Fiyati": 4, "Emir Fiyatı": 4,
        "1A Getiri%": 2, "1A Getiri %": 2, "1A%": 2, "Ret1M": 2,
        "Optima Skor": 1, "Optima Skoru": 1, "Skor": 1,
        "RSI": 1,
        "Tutar (₺)": 2, "Tutar": 2,
    }
    df_show, _turkce_cevrilen = _clickable_table_turkce_format(
        df_show, tuple(_kolon_ondalik.items()))

    auto_cfg = {}
    for c in df_show.columns:
        if c in _turkce_cevrilen:
            # v2.0.7.61 - CSS hack yerine GERCEK alignment parametresi
            # (Streamlit'in kendi TextColumn ozelligi, daha guvenilir).
            auto_cfg[c] = st.column_config.TextColumn(alignment="right")
    if col_cfg:
        auto_cfg.update(col_cfg)

    try:
        df_render = df_show.style
        if "Sinyal" in df_show.columns:
            df_render = df_render.map(_sinyal_renk_stil, subset=["Sinyal"])
    except AttributeError:
        df_render = df_show.style
        if "Sinyal" in df_show.columns:
            df_render = df_render.applymap(_sinyal_renk_stil, subset=["Sinyal"])

    evt = st.dataframe(
        df_render,
        width='stretch',
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
            # v2.0.7.60 - Turkce format: fmt parametresindeki ondalik
            # basamak sayisini koru, virgul ayiraciyla goster.
            _ondalik = int(fmt.split(".")[1][0]) if "." in fmt else 2
            return fmt_tr(float(v), _ondalik)
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
        dd_str = f"<span style='color:{dd_clr}'><b>{fmt_tr(max_dd,1)}%</b></span>{adj_note}"
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
        df_p_g = df_p.copy()
        for _c, _dec in [("Alış",4),("Güncel",4),("Toplam",2),("K/Z (₺)",2)]:
            df_p_g[_c] = df_p_g[_c].apply(lambda v: fmt_tr(v, _dec))
        df_p_g["K/Z %"] = df_p_g["K/Z %"].apply(lambda v: fmt_tr_isaretli(v,2,yuzde=True))
        st.dataframe(df_p_g, width='stretch', hide_index=True)
        c1, c2 = st.columns(2)
        c1.metric("Toplam Değer", f"{fmt_tr(df_p['Toplam'].sum())} ₺")
        c2.metric("Toplam K/Z", fmt_tr_isaretli(df_p['K/Z (₺)'].sum())+" ₺")

def fmt_tr(val, decimals=2):
    """Float -> Türkçe format: 1.234,56
    v2.0.7.76 (Bahri'nin talebi): eskiden eksik/None deger icin "—"
    isareti gosteriliyordu - artik hicbir isaret yok, hucre BOS kalir
    (emoji/widget yok kuraliyla ayni ruhta: sistemde gereksiz gorsel
    isaretleyici olmasin)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    sign = "-" if val < 0 else ""
    s = f"{abs(val):,.{decimals}f}"          # "1,234.56"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return sign + s

def fmt_tr_isaretli(val, decimals=2, yuzde=False):
    """v2.0.7.60 - Türkçe format + acik +/- isareti (eskiden "%+.2f" gibi
    Ingilizce format spec'leri kullanilan onlarca yerde tek noktadan
    tekrar kullanilir: 1A Getiri%, K/Z, MACD degisimi vb."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    try:
        val = float(val)
    except (TypeError, ValueError):
        return str(val)
    taban = fmt_tr(abs(val), decimals)
    isaret = "+" if val > 0 else ("-" if val < 0 else "")
    return f"{isaret}{taban}{'%' if yuzde else ''}"

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


def update_portfolio_item(item_id: int, adet: float, maliyet: float,
                           purchase_date: str = "", unit_type: str = "Adet",
                           note: str = None) -> dict:
    """v2.0.7.114 (Bahri'nin talebi): açık bir pozisyonun giriş bilgilerini
    (miktar, maliyet, alış tarihi, birim türü, not) sonradan düzeltebilmek
    için - ör. yanlış girilmiş bir maliyeti ya da tarihi elden düzeltmek.
    Ticker/asset_type KASITLI OLARAK degistirilemez (varlığın kendisini
    değiştirmek "düzeltme" değil, sil+yeniden-ekle olmalı - farklı bir
    işlem)."""
    from db import get_conn
    user_id = (_cur_user or {}).get("id")
    if not user_id:
        return {"basari": False, "hata": "Oturum bulunamadı."}
    try:
        adet = float(adet); maliyet = float(maliyet)
    except (TypeError, ValueError):
        return {"basari": False, "hata": "Geçersiz miktar/maliyet."}
    if adet <= 0:
        return {"basari": False, "hata": "Miktar 0'dan büyük olmalı."}
    if maliyet <= 0:
        return {"basari": False, "hata": "Maliyet 0'dan büyük olmalı."}
    conn = get_conn()
    try:
        if note is None:
            _cur = conn.execute(
                "UPDATE portfolio SET quantity=?, avg_cost=?, purchase_date=?, unit_type=? "
                "WHERE id=? AND user_id=?",
                (adet, maliyet, purchase_date, unit_type, item_id, user_id)
            )
        else:
            _cur = conn.execute(
                "UPDATE portfolio SET quantity=?, avg_cost=?, purchase_date=?, unit_type=?, note=? "
                "WHERE id=? AND user_id=?",
                (adet, maliyet, purchase_date, unit_type, note, item_id, user_id)
            )
        # v2.0.7.116 - KRITIK DUZELTME (Bahri'nin bulgusu, HTS ornegi, 31
        # Temmuz 2026: Duzelt formuyla maliyeti degistirdi, kaydet dedi,
        # tabloda hic degismedi - hicbir hata da gorunmedi). Eskiden bu
        # fonksiyon UPDATE'i hicbir try/except OLMADAN calistiriyordu -
        # bir hata olsaydi Streamlit'in kirmizi traceback kutusu cikardi,
        # AMA rowcount==0 (yani "WHERE id=? AND user_id=?" hicbir satirla
        # eslesmedi - ornegin item_id/user_id uyumsuzlugu) durumunda
        # HATASIZ ama ETKISIZ bir UPDATE calisiyordu - hic satir
        # degismedi, hic hata da firlamadi, "basari: True" donuyordu.
        # Artik rowcount kontrol ediliyor + yazdiktan hemen sonra satir
        # tekrar okunup GERCEKTEN degisip degismedigi dogrulaniyor.
        if _cur.rowcount == 0:
            conn.rollback(); conn.close()
            return {"basari": False,
                    "hata": "Güncelleme hiçbir satırı etkilemedi (kayıt bulunamadı ya da "
                            "size ait değil) - hiçbir değer değiştirilmedi."}
        conn.commit()
        _dogrula = conn.execute(
            "SELECT quantity, avg_cost FROM portfolio WHERE id=? AND user_id=?",
            (item_id, user_id)
        ).fetchone()
        conn.close()
        if _dogrula is None or round(float(_dogrula["avg_cost"]), 6) != round(maliyet, 6):
            return {"basari": False,
                    "hata": "Kayıt güncellendi ama doğrulama okuması beklenen değeri "
                            "göstermiyor - lütfen sayfayı yenileyip tekrar kontrol edin."}
        return {"basari": True}
    except Exception as e:
        try:
            conn.rollback(); conn.close()
        except Exception:
            pass
        return {"basari": False, "hata": f"Veritabanı hatası: {type(e).__name__}: {e}"}


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
# ══════════════════════════════════════════════════════════════
# BEKLENTİ MODU — GLOBAL uygulama (v2.0.7.149, Bahri'nin bulgusu)
# ══════════════════════════════════════════════════════════════
# Kontroller sidebar'da (yukarıda) - burada SADECE session_state okunup
# df_uni'ye TEK SEFERDE, TÜM sayfa yönlendirmesinden ÖNCE uygulanıyor.
# Böylece Ana Sayfa/Döviz/BIST/TEFAS/Maden/Kripto/Portföyüm/Temettü/
# Halka Arz HEPSİ aynı ayarlanmış Optima_Skor'u görür.
#
# v2.0.7.152 (Bahri'nin talebi, 18 Ağustos 2026 - iki yönlü genişletme):
# (1) Tekil tarihli referans olaylar KALDIRILDI ("13 sene önceki bir
# olayı bugüne örnek göstermek anlamsız" - Bahri haklı, TEK bir olay
# istatistik değil, anekdottur). Açıklamalar artık ÇOK SAYIDA olayı
# kapsayan akademik ÇALIŞMALARA (panel/olay çalışması, onlarca yıl,
# yüzlerce olay) atıfta bulunuyor - istatistiksel ifade, tarih değil.
# (2) SADECE 3 kalıp yeterli değildi - araştırma genişletildi, İKİ yeni
# kalıp eklendi: Kredi notu değişikliği ve Kripto-özel şok (KRIPTO
# kategorisi önceden HİÇ kapsanmıyordu).
#
# Kaynaklar (hepsi çok-olaylı akademik çalışmalar, tek anekdot değil):
# - Jeopolitik: Caldara-Iacoviello Jeopolitik Risk Endeksi (1900-günümüz)
# - Kredi notu: gelişen piyasa panel çalışması, 1990-2016 günlük veri
# - Kripto: çok sayıda kripto parada halving olay çalışması (2014-2023)
# v2.0.7.162 (Bahri'nin talebi, 19 Ağustos 2026 — "anahtar kelime
# ön-filtresi ve kalıplara daha sonra ekleme yapılabilir hale getirilebilir
# mi, kalıpların netleşmesi halinde hangi varlıkların skorları hangi
# oranda etkilenecek tabloda görmek isterim"): 6 kalıp ARTIK KODA GÖMÜLÜ
# DEĞİL — db.get_kaliplar() ile Supabase'den okunuyor. Yeni kalıp/kelime/
# etki puanı eklemek Admin Paneli > "Kalıp Yönetimi" bölümünden yapılır,
# KOD DEĞİŞİKLİĞİ/DEPLOY GEREKMEZ. Puan tablosu da aynı yerde görünür
# hale geldi (Bahri'nin istediği "hangi kategori hangi oranda etkilenecek"
# tablosu).
# SADECE aktif=True kalıplar yüklenir - pasif kalıp hem ön-filtrede hem AI
# doğrulamasında hem skor uygulamasında görünmez (kalıcı silme değil,
# admin panelinden geri açılabilir).
@st.cache_data(ttl=300, show_spinner=False)
def _kalip_verilerini_yukle():
    """5 dakikada bir tazelenir - Admin Paneli'nde bir kalıp
    değiştirildiğinde de cache açıkça temizlenir (bkz. admin.py), yani
    değişiklik en geç 5 dakikada, çoğu zaman ANINDA yansır."""
    from db import get_kaliplar
    try:
        _kaliplar = get_kaliplar(sadece_aktif=True)
    except Exception:
        _kaliplar = []
    _tablosu, _isim, _aciklama = {}, {}, {}
    for _k in _kaliplar:
        _kk = _k["kalip_key"]
        _tablosu[_kk] = _k["etkiler"]
        _isim[_kk] = _k["ad"]
        _aciklama[_kk] = _k["aciklama"] or ""
    return _tablosu, _isim, _aciklama

_KALIP_TABLOSU, _KALIP_ISIM, _KALIP_ACIKLAMA = _kalip_verilerini_yukle()
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

    st.markdown("**Bütçe (TL)**")
    # v2.0.7.197 (Bahri'nin talebi, 25 Ağustos 2026 — "uygulama ilk
    # açıldığında 25.000 TL bütçe default olarak girilmiş olsun"):
    # eskiden varsayılan 0'dı (kutucuk boş açılıyordu) - bu da hem
    # kullanıcı için "önce bir şey yazmam lazım" sürtünmesi yaratıyordu
    # hem de v2.0.7.196'da düzelttiğimiz "bütçe boşsa sayfa
    # st.stop() ile duruyor" sorununu YENİDEN tetikleyebiliyordu. Artık
    # ilk açılışta 25.000 TL varsayılan - _DEFAULT_BUTCE sabitinden
    # okunuyor, tek yerden değiştirilebilir.
    _DEFAULT_BUTCE = 25000
    butce_str = st.text_input(
        "Butce",
        value=str(int(st.session_state.get("butce_val", _DEFAULT_BUTCE))),
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
        budget = int(st.session_state.get("butce_val", _DEFAULT_BUTCE))
    if budget > 0:
        st.caption(f"Seçilen: {budget:,} TL".replace(",", "."))
        # Deger hala varsayilanla AYNIYSA (kullanici degistirmemis
        # olabilir) hatirlatma notu goster - "ilk acilis" takibi yerine
        # bu daha saglam: herhangi bir yeniden calisma (rerun) notu
        # erken kaybetmez, kullanici GERCEKTEN farkli bir deger
        # yazana kadar goruntude kalir.
        if budget == _DEFAULT_BUTCE:
            st.caption("Bu bir varsayılan değerdir, dilediğiniz gibi değiştirebilirsiniz.")
    risk=st.select_slider("Risk Toleransı",
                           options=["Çok Düşük","Düşük","Orta","Yüksek","Çok Yüksek"],value="Orta")
    max_assets=st.slider("Max Varlık Sayısı",min_value=2,max_value=30,value=10,step=1,
                          help="Portföyde kaç farklı varlık olacağını belirler")

    # v2.0.7.158 (Bahri'nin talebi, 19 Ağustos 2026 — "artık bunlara gerek
    # kalmadı ki"): Sidebar'daki "Beklenti Modu" bölümü (ana anahtar + 6
    # kalıbın elle işaretlenmesi + şiddet kaydırıcıları) TAMAMEN KALDIRILDI.
    # Sebep: v2.0.7.154-157 ile kurulan otomatik akış (haber_izleme.py son
    # dakika haberi yakalar → 6 kalıptan birine eşler → kategori/yön/şiddet
    # hesaplar → kullanıcıya doğal bir cümleyle sunar → SADECE onaylanırsa
    # uygulanır) elle işaretlemeyi gereksiz kıldı.
    # DİKKAT — 6 KALIP v2.0.7.162'den beri KOD DEĞİL, VERİTABANI (bkz.
    # yukarıdaki `_kalip_verilerini_yukle`). `_KALIP_TABLOSU`/`_KALIP_ISIM`/
    # `_KALIP_ACIKLAMA` artık db.get_kaliplar()'ın CACHE'LENMİŞ sonucudur -
    # bunları elle koda geri yazmaya kalkma, tek doğruluk kaynağı
    # `haber_kaliplari`/`haber_kalip_kelime`/`haber_kalip_etki` tabloları.
    # Ayarlamanın kendisi df_uni yüklendikten HEMEN SONRA, TÜM sayfa
    # yönlendirmesinden ÖNCE uygulanır (v2.0.7.149'da kurulan mimari aynen
    # korunuyor) - böylece Ana Sayfa/Döviz/BIST/TEFAS/Maden/Kripto/Portföyüm
    # HEPSİ AYNI ayarlanmış skoru görür.
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
        if st.button("Ayarları Kaydet", key="ecfg_save", width='stretch'):
            save_email_cfg({"address":e_addr,"smtp_host":"smtp.gmail.com","smtp_port":587,
                             "smtp_user":ecfg.get("smtp_user",""),
                             "smtp_pass":ecfg.get("smtp_pass",""),
                             "times":[e_t1,e_t2],
                             "tcmb_key":ecfg.get("tcmb_key","")},
                            user_id=_uid_for_cfg)
            st.success("Kaydedildi! (Saatler Supabase'de kalıcı)")
        if st.button("Şimdi Gönder", key="send_now", width='stretch'):
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
                             width='stretch'):
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
                         width='stretch'):
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
                            "Alış":        fmt_tr(a['alish_fiyat'],4),
                            "Peak":        fmt_tr(a['peak_price'],4),
                            "Şu Anki":     fmt_tr(a['current_price'],4),
                            "Düşüş (%)":   fmt_tr(a['drop_pct'],2),
                            "Tavsiye":     fmt_tr(a['tavsiye_fiyat'],4) if a['tavsiye_fiyat'] > 0 else "—",
                            "Miktar":      fmt_tr(a['miktar'],4),
                            "Toplam (TL)": fmt_tr(a['toplam_deger'],2),
                        })
                    if _alert_rows:
                        st.dataframe(_alert_rows, width='stretch',
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
                                 width='stretch'):
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
                        f"{t} -> {fmt_tr(p,4)} ({s})"
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
                             width='stretch'):
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
                        st.caption(f"**Son yüklenme:** {fmt_tr(_toplam,2)} sn")
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
                if st.button("Olcumleri Sifirla", key="diag_reset", width='stretch'):
                    _ld_reset_timings()
                    st.rerun()
                st.caption(
                    "İlk yükleme cache miss = 30-60 sn beklenir. "
                    "Sonraki açılışlar 5 dk içinde hızlı (cache hit, ~0s). "
                    "Streamlit Cloud Logs'a `[timing]` satırları da basar."
                )
            except Exception as _e:
                st.caption(f"Tanilama yuklenemedi: {_e}")

        if st.button("Admin Paneli", width='stretch'):
            st.session_state["page_override"] = "admin"
            st.rerun()
    if st.button("Cikis Yap", width='stretch'):
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

_beklenti_ayarlar = {}

# v2.0.7.156 (Bahri'nin talebi, 18 Ağustos 2026 — KRİTİK tasarım
# düzeltmesi, "hemen otomatik uygula" YANLIŞ anlaşılmıştı): Otomatik
# tespitler ARTIK ASLA kendiliğinden uygulanmaz. Akış: haber_izleme.py
# tespit eder → burada "bekliyor" olarak okunur → TÜM sayfalarda görünen
# bir bildirimle kullanıcıya gösterilir (haber + AI gerekçesi + hangi
# kategoriye ne kadar puan etkisi olacağı) → kullanıcı Ana Sayfa'da
# Onayla/Reddet der → SADECE onaylananlar Optima Skor'a uygulanır.
# v2.0.7.158 GÜNCELLEMESİ: buradaki eski "anahtara bağlıdır" cümlesi
# geçersiz - sidebar'daki Beklenti Modu anahtarı tamamen kaldırıldı,
# artık ONAY/RED kararının kendisi tek kontroldür.
try:
    from db import get_bekleyen_tespitler as _gbt_raw

    # v2.0.7.168 (Bahri'nin bulgusu, 20 Ağustos 2026 — "uygulama yeniden
    # çok ağırlaştı"): KÖK NEDEN bulundu - bu çağrı ÖNBELLEKSİZDİ, yani
    # sayfa fark etmeksizin HER rerun'da (her tıklama, her widget
    # etkileşimi, uygulamanın HERHANGİ bir yerinde) Supabase'e YENİ bir
    # bağlantı açılıyordu (bağlantı havuzu YOK - v2.0.7.142'de denenmiş,
    # iki farklı çöküşe yol açmıştı, bu yüzden havuza DÖNÜLMEDİ). 20
    # saniyelik kısa ömürlü önbellek ekleyerek: haber_izleme.py zaten
    # 2 saatte bir çalıştığı için 20 saniyelik gecikme hiçbir şeyi
    # geciktirmiyor, ama art arda tıklamalarda (ör. bir sayı kutusuna
    # yazarken her tuşta rerun tetiklenmesi) gereksiz onlarca bağlantı
    # açılması engelleniyor.
    # v2.0.7.203 (Bahri'nin talebi — "Optima Skor kişiye özel olsun"):
    # kullanici_id artık PARAMETRE - st.cache_data zaten argüman
    # DEĞERİNE göre ayrı önbellek tutuyor, bu yüzden bu tek değişiklik
    # otomatik olarak KULLANICI BAZLI önbellekleme de sağlıyor (bir
    # kullanıcının önbelleği başka bir kullanıcıya asla karışmaz).
    @st.cache_data(ttl=20, show_spinner=False)
    def _bekleyen_tespitler_onbellekli(_kid):
        return _gbt_raw(_kid)

    _bekleyen_tespitler = (
        _bekleyen_tespitler_onbellekli(_cur_user["id"]) if _cur_user else [])
except Exception:
    _bekleyen_tespitler = []

if _bekleyen_tespitler:
    st.warning(
        f"**{len(_bekleyen_tespitler)} adet otomatik tespit edilen olay onayınızı bekliyor** "
        f"— incelemek için Ana Sayfa'daki 'Onay Bekleyen Otomatik Tespitler' "
        f"bölümüne gidin. Hiçbiri siz onaylamadan Optima Skor'a uygulanmaz."
    )

# v2.0.7.159 (Bahri'nin talebi, 19 Ağustos 2026 — "bir mesaj kutusunun
# çıkmasını tercih ederim, mobildeki uygulamayı da düşünmek lazım"):
# Onay bekleyen tespitler artık sadece Ana Sayfa'daki listede değil,
# HANGİ SAYFADA OLURSA OLSUN bir MODAL KUTU (st.dialog) ile önüne çıkar.
# Sebep: son dakika haberi zaman hassasiyetli - kullanıcı Portföyüm'deyken
# de görmeli, Ana Sayfa'ya gitmesini beklememeliyiz.
# ÜÇ TEKNİK KISIT (Streamlit'in kendi davranışı, tasarım bunlara göre):
#  1. st.dialog Streamlit 1.37.0'da genel kullanıma açıldı - requirements.txt
#     bu yüzden >=1.37.0'a yükseltildi. Yine de `hasattr` ile korunuyor:
#     eski bir sürüme düşülürse modal atlanır, Ana Sayfa listesi çalışmaya
#     devam eder (çökme YOK).
#  2. Bir script çalışmasında SADECE TEK dialog açılabilir - bu yüzden
#     bekleyen tespitler sırayla gösterilir (en yenisi ilk), başlıkta
#     "1 / N" sayacı var. Onayla/Reddet sonrası rerun ile bir sonraki açılır.
#  3. Uygulamada 5 dakikada bir sessiz autorefresh var - önlem alınmazsa
#     modal kullanıcı okurken tekrar tekrar önüne düşer. Bu yüzden
#     "Daha sonra bak" düğmesi oturum boyunca modalı susturur
#     (`tespit_modal_ertelendi`); üstteki uyarı şeridi kalmaya devam eder.
_MODAL_ERTELE_KEY = "tespit_modal_ertelendi"

if (_bekleyen_tespitler and hasattr(st, "dialog")
        and not st.session_state.get(_MODAL_ERTELE_KEY)):

    def _tespit_puan_onizleme(_kalip_key_o, _siddet_o):
        """Tespit ONAYLANIRSA hangi kategoriye kaç puan gideceğini önceden
        hesaplar - aşağıdaki asıl uygulama bloğuyla AYNI çarpanları kullanır
        (şiddet x risk toleransı). İki yer birbirinden ayrışırsa kullanıcıya
        gösterilen sayı ile gerçekte uygulanan sayı tutmaz - değiştirirken
        ikisini birlikte güncelle."""
        _sc_o = {"Düşük": 0.5, "Orta": 1.0, "Yüksek": 1.5}.get(_siddet_o, 1.0)
        _rc_o = {"Çok Düşük": 0.4, "Düşük": 0.7, "Orta": 1.0,
                 "Yüksek": 1.3, "Çok Yüksek": 1.6}.get(risk, 1.0)
        # DİKKAT: çarpım sırası asıl blokla BİREBİR aynı olmalı - önce
        # (şiddet x risk) çarpanı, SONRA puan ile çarpım. Ters sırada
        # (puan x şiddet) x risk yazılırsa kayan nokta aritmetiği yüzünden
        # 90 kombinasyonun 16'sında bit düzeyinde farklı sonuç çıkar.
        _carpan_o = _sc_o * _rc_o
        _ad_o = {"MADEN": "Değerli Maden", "DOVIZ": "Döviz",
                 "BIST": "BIST", "KRIPTO": "Kripto"}
        return [(_ad_o.get(_k_o, _k_o), _p_o * _carpan_o)
                for _k_o, _p_o in _KALIP_TABLOSU.get(_kalip_key_o, {}).items()]

    # v2.0.7.215 (Bahri'nin talebi, 29 Ağustos 2026 — "ikinci kaynağı
    # sadece 'Ayrıca...' yazısında değil, ana cümlenin başında ve
    # Kaynak listesinde numaralı olarak görmek istiyorum"): AI'nın
    # ürettiği cümle SADECE birincil kaynakla üretiliyor (teyit,
    # AI çağrısından SONRA, ayrı bir veritabanı sorgusuyla tespit
    # ediliyor) - bu yüzden AI'ya tekrar sormak yerine, cümledeki
    # "{kaynak} kaynağından alınan habere göre" ifadesini basit bir
    # metin ikamesiyle "{kaynak}'den alınan ve {teyit_kaynak}
    # kaynağından da tespit edilen habere göre" haline getiriyoruz.
    # ÖNEMLİ: Bu iki yardımcı fonksiyon, @st.dialog dekoratörlü
    # _tespit_onay_modali'DEN AYRI, sıradan (dekoratörsüz) fonksiyonlar
    # olarak BİLEREK burada, dekoratörden ÖNCE tanımlanıyor - dekoratör
    # yanlışlıkla bu fonksiyonlardan birine değil, doğrudan
    # _tespit_onay_modali'ye uygulanmalı.
    def _turkce_liste_birlestir(ogeler):
        """v2.0.7.217: ['A'] -> 'A', ['A','B'] -> 'A ve B',
        ['A','B','C'] -> 'A, B ve C' - dogal Turkce liste birlestirme."""
        if not ogeler:
            return ""
        if len(ogeler) == 1:
            return ogeler[0]
        return ", ".join(ogeler[:-1]) + " ve " + ogeler[-1]

    def _cok_kaynakli_cumle_olustur(ai_gerekce, haber_kaynak, teyit_listesi):
        """v2.0.7.217 (Bahri'nin sorusu — "üç, dört, beş, altı kaynak
        olması halinde pop-up bunları da gösterebilecek mi?"): ARTIK
        TEK BİR teyit_kaynak DEĞİL, `teyit_listesi` (sözlük listesi)
        alıyor - kaç tane teyit eden kaynak varsa hepsi doğal bir
        Türkçe listede ("X, Y ve Z kaynaklarından da teyit edilen")
        cümleye ekleniyor."""
        if not ai_gerekce or not teyit_listesi or not haber_kaynak:
            return ai_gerekce
        eski_ifade = f"{haber_kaynak} kaynağından alınan habere göre"
        if eski_ifade not in ai_gerekce:
            return ai_gerekce  # beklenen kalıpta değilse dokunma - guvenli geri donus
        _teyit_isimleri = [t.get("kaynak", "") for t in teyit_listesi if t.get("kaynak")]
        if not _teyit_isimleri:
            return ai_gerekce
        _isim_metni = _turkce_liste_birlestir(_teyit_isimleri)
        # v2.0.7.216: "tespit edilen" -> "teyit edilen" (Bahri'nin
        # talebi - anlamsal olarak daha doğru kelime).
        _kaynak_ek = "kaynağından" if len(_teyit_isimleri) == 1 else "kaynaklarından"
        yeni_ifade = (f"{haber_kaynak}'den alınan ve {_isim_metni} "
                      f"{_kaynak_ek} da teyit edilen habere göre")
        return ai_gerekce.replace(eski_ifade, yeni_ifade, 1)

    def _kaynak_bolumu_goster(satir):
        """Hem modal hem Ana Sayfa listesi icin AYNI numarali kaynak
        gosterimi.

        v2.0.7.217 (Bahri'nin sorusu — "üç, dört, beş, altı kaynak
        olması halinde pop-up bunları da gösterebilecek mi?"): ARTIK
        SINIRSIZ SAYIDA teyit eden kaynak destekleniyor - eskiden
        `teyit_kaynak` tekil bir alandı (en fazla 1 teyit
        gösterilebiliyordu, `db.py`'deki eşleştirme mantığı da ilk
        eşleşmede duruyordu). Şimdi `teyit_listesi` bir DİZİ - kaç
        tane bağımsız kaynak aynı olayı doğruladıysa hepsi 2, 3, 4...
        şeklinde numaralanarak gösteriliyor.

        v2.0.7.216: teyit eden bir kaynağın `haber_url`'i boşsa link
        yerine düz metin olarak gösteriliyor - kaynak GENE DE
        listeden tamamen gizlenmiyor."""
        if not satir.get("haber_url"):
            return
        _tum_maddeler = [f"[{satir.get('haber_kaynak','')} — {satir.get('haber_basligi','')}]({satir.get('haber_url')})"]
        for _t in satir.get("teyit_listesi") or []:
            if _t.get("url"):
                _tum_maddeler.append(f"[{_t.get('kaynak','')} — {_t.get('baslik','')}]({_t.get('url')})")
            else:
                # url yoksa duz metin olarak goster - kaynak GENE DE
                # gorunur kalsin, tamamen gizlenmesin (v2.0.7.216).
                _tum_maddeler.append(f"{_t.get('kaynak','')} — {_t.get('baslik','')}")
        if len(_tum_maddeler) == 1:
            st.caption(f"Kaynak: {_tum_maddeler[0]}")
        else:
            _numarali = "  \n".join(f"{i+1}- {m}" for i, m in enumerate(_tum_maddeler))
            st.caption(f"Kaynaklar: {_numarali}")

    @st.dialog("Otomatik tespit")
    def _tespit_onay_modali():
        _tm = _bekleyen_tespitler[0]
        _tkm = _tm["kalip_key"]
        _sdm = _tm.get("siddet", "Orta")
        if len(_bekleyen_tespitler) > 1:
            st.caption(f"1 / {len(_bekleyen_tespitler)} bekleyen tespit")
        _cumle_m = _tm.get("ai_gerekce", "") or (
            f"{_KALIP_ISIM.get(_tkm, _tkm)} kalıbı tespit edildi.")
        _cumle_m = _cok_kaynakli_cumle_olustur(
            _cumle_m, _tm.get("haber_kaynak"), _tm.get("teyit_listesi"))
        st.markdown(f"{_cumle_m} **Onaylıyor musunuz?**")

        _onizleme = _tespit_puan_onizleme(_tkm, _sdm)
        if _onizleme:
            st.caption("Onaylarsanız uygulanacak")
            for _kat_ad_m, _puan_m in _onizleme:
                _pc1, _pc2 = st.columns([3, 1])
                _pc1.markdown(_kat_ad_m)
                _pc2.markdown(f"**{_puan_m:+.1f}**")

        # v2.0.7.195 (Bahri'nin talebi, 25 Ağustos 2026 — "Kalıp/Şiddet/
        # Geçerlilik yazısının daha çok görünürlüğünü sağla"): sade,
        # gri bir st.caption yerine, şiddete göre renklenen (Yüksek=
        # kırmızı, Orta=turuncu, Düşük=gri), daha büyük/kalın bir rozet.
        _siddet_renk = {"Yüksek": "#b91c1c", "Orta": "#b45309", "Düşük": "#6b7280"}.get(_sdm, "#6b7280")
        st.markdown(
            f"""<div style="background:#f3f4f6;border-left:4px solid {_siddet_renk};
                 border-radius:6px;padding:10px 14px;margin:6px 0;font-size:15px;">
                 <b>Kalıp:</b> {_KALIP_ISIM.get(_tkm, _tkm)} &nbsp;·&nbsp;
                 <b>Şiddet:</b> <span style="color:{_siddet_renk};font-weight:700;">{_sdm}</span>
                 &nbsp;·&nbsp; <b>Geçerlilik:</b> 48 saat</div>""",
            unsafe_allow_html=True)
        _kaynak_bolumu_goster(_tm)
        # v2.0.7.215: Eski "Ayrıca ... teyit edildi" satırı KALDIRILDI -
        # bu bilgi artık ana cümlenin başında ve yukarıdaki numaralı
        # Kaynak listesinde zaten gösteriliyor (bkz. yukarıdaki yorumlar).

        _mc1, _mc2 = st.columns(2)
        with _mc1:
            if st.button("Onayla", key="modal_tespit_onay",
                         use_container_width=True):
                try:
                    from db import tespit_onayla
                    # v2.0.7.192 (Bahri'nin bulgusu, 25 Ağustos 2026 —
                    # "onay butonunu tıklıyorum ama hiçbir buton
                    # çalışmıyor"): KESİN KÖK NEDEN - `tespit_onayla`
                    # HATA FIRLATMIYOR, veritabanı yazması başarısız
                    # olsa bile SADECE `False` döndürüyor (arka planda
                    # print ediyor, kullanıcıya hiç yansımıyor). Buradaki
                    # eski kod bu dönüş değerini HİÇ KONTROL ETMİYORDU -
                    # "except" bloğu hiçbir zaman tetiklenmiyordu (çünkü
                    # exception hiç fırlamıyordu), kod her zaman "else"
                    # dalına düşüp SESSİZCE cache temizleyip rerun
                    # ediyordu. Gerçek bir yazma hatası olduğunda,
                    # veritabanındaki satır GÜNCELLENMEMİŞ haliyle
                    # kalıyordu - rerun sonrası AYNI tespit AYNI pop-up'ta
                    # tekrar görünüyordu, hiçbir hata mesajı olmadan -
                    # tam da Bahri'nin tarif ettiği "hiçbir şey olmuyor"
                    # deneyimi.
                    _basarili = tespit_onayla(_cur_user["id"] if _cur_user else None, _tm["id"])
                except Exception as _me1:
                    st.error(f"Onaylanamadı: {_me1}")
                else:
                    if _basarili:
                        # v2.0.7.193 (Bahri'nin bulgusu, 25 Ağustos 2026 —
                        # "onay butonu çok geç çalıştı"): `st.cache_data.
                        # clear()` (GENEL temizleme) yerine SADECE bu iki
                        # küçük tespit önbelleğini temizliyoruz. Eski kod
                        # UYGULAMADAKİ HER önbellekli fonksiyonu (tüm evren
                        # CSV'si, BIST/TEFAS verileri, her şey) tek seferde
                        # siliyordu - onay sonrası rerun bu yüzden HER ŞEYİ
                        # sıfırdan yeniden hesaplamak zorunda kalıyor,
                        # "çok geç çalıştı" hissi buradan geliyordu.
                        try:
                            _bekleyen_tespitler_onbellekli.clear()
                            _onaylanmis_tespitler_onbellekli.clear()
                        except Exception:
                            st.cache_data.clear()  # guvenli yedek - fonksiyonlar hic tanimlanmamissa
                        st.rerun()
                    else:
                        st.error(
                            "Onaylanamadı - veritabanı yazması başarısız "
                            "oldu (sunucu loglarına bakılmalı). Tekrar "
                            "deneyin, sürerse Bahri'ye bildirin.")
        with _mc2:
            if st.button("Reddet", key="modal_tespit_red",
                         use_container_width=True):
                try:
                    from db import tespit_reddet
                    _basarili = tespit_reddet(_cur_user["id"] if _cur_user else None, _tm["id"])
                except Exception as _me2:
                    st.error(f"Reddedilemedi: {_me2}")
                else:
                    if _basarili:
                        try:
                            _bekleyen_tespitler_onbellekli.clear()
                            _onaylanmis_tespitler_onbellekli.clear()
                        except Exception:
                            st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(
                            "Reddedilemedi - veritabanı yazması başarısız "
                            "oldu (sunucu loglarına bakılmalı). Tekrar "
                            "deneyin, sürerse Bahri'ye bildirin.")

        if st.button("Daha sonra bak", key="modal_tespit_ertele",
                     use_container_width=True):
            st.session_state[_MODAL_ERTELE_KEY] = True
            st.rerun()
        st.caption(
            "Kutuyu kapatırsanız sayfa yenilendiğinde tekrar açılır. "
            "Bu oturumda bir daha çıkmasın isterseniz 'Daha sonra bak' "
            "düğmesini kullanın - tespit silinmez, Ana Sayfa'daki listede "
            "durmaya devam eder.")

    _tespit_onay_modali()

# v2.0.7.158 (Bahri'nin kararı, 19 Ağustos 2026): Bu blok ESKİDEN
# `if st.session_state.get("beklenti_aktif"):` içindeydi - yani sidebar'daki
# ana anahtar KAPALIYKEN, kullanıcı bir tespiti onaylasa bile Optima Skor'a
# HİÇ uygulanmıyordu (sessiz işlevsizlik). Sidebar bölümü kaldırıldığı için
# bu kapı da kaldırıldı: ONAYLANAN TESPİTLER ARTIK HER ZAMAN UYGULANIR.
# Kullanıcının kontrolü artık anahtarda değil, ONAY/RED kararının kendisinde.
# Uygulanmayı durdurmanın iki yolu var: (1) tespiti en baştan Reddet,
# (2) hiçbir şey yapma - onaylanan tespitler 48 saat sonra `gecerlilik_bitis`
# ile kendiliğinden düşer (bkz. db.tespit_ekle, gecerlilik_saat=48).
try:
    from db import get_onaylanmis_tespitler as _got_raw

    # v2.0.7.168: yukarıdaki _bekleyen_tespitler_onbellekli ile AYNI
    # sebep/çözüm - bu çağrı da ÖNBELLEKSİZDİ, her rerun'da yeni bir
    # Supabase bağlantısı açıyordu. 20 saniyelik önbellek eklendi.
    # v2.0.7.203 (Bahri'nin talebi — "Optima Skor kişiye özel olsun"):
    # kullanici_id artık PARAMETRE - önbellek de otomatik olarak
    # kullanıcı bazlı ayrışıyor (bkz. yukarıdaki _bekleyen_tespitler_
    # onbellekli'deki AYNI açıklama).
    @st.cache_data(ttl=20, show_spinner=False)
    def _onaylanmis_tespitler_onbellekli(_kid):
        return _got_raw(_kid)

    _onaylanmis_tespitler = (
        _onaylanmis_tespitler_onbellekli(_cur_user["id"]) if _cur_user else [])
except Exception:
    _onaylanmis_tespitler = []

# Aynı kalıp için birden fazla onaylı tespit varsa (ör. iki ayrı haber aynı
# "Fed şahin sürprizi" kalıbına düştüyse) puan İKİ KEZ eklenmez - YÜKSEK olan
# şiddet kazanır, kalıp tek kez sayılır.
_siddet_sira = {"Düşük": 0, "Orta": 1, "Yüksek": 2}
for _tespit in _onaylanmis_tespitler:
    _tk = _tespit["kalip_key"]
    _ts = _tespit.get("siddet", "Orta")
    if _tk not in _KALIP_TABLOSU:
        continue  # eski/tanimsiz bir kalip - guvenli sekilde atla
    _mevcut = _beklenti_ayarlar.get(_tk)
    if _mevcut is None or _siddet_sira.get(_ts, 1) > _siddet_sira.get(_mevcut, 1):
        _beklenti_ayarlar[_tk] = _ts

_beklenti_log = []
_beklenti_kategori_ayar = {"MADEN": 0.0, "DOVIZ": 0.0, "BIST": 0.0, "KRIPTO": 0.0}
if _beklenti_ayarlar:
    _siddet_carpan = {"Düşük": 0.5, "Orta": 1.0, "Yüksek": 1.5}
    _risk_carpan = {"Çok Düşük": 0.4, "Düşük": 0.7, "Orta": 1.0,
                    "Yüksek": 1.3, "Çok Yüksek": 1.6}.get(risk, 1.0)
    for _kalip_key, _siddet in _beklenti_ayarlar.items():
        _carpan = _siddet_carpan.get(_siddet, 1.0) * _risk_carpan
        for _kat, _puan in _KALIP_TABLOSU.get(_kalip_key, {}).items():
            _beklenti_kategori_ayar[_kat] += _puan * _carpan
        # v2.0.7.158: kaynak etiketi ("manuel"/"onaylanmış otomatik") artık
        # tek türden olduğu için satırdan çıkarıldı - hepsi onaylanmış
        # otomatik tespit.
        _beklenti_log.append(f"{_KALIP_ISIM[_kalip_key]} ({_siddet} şiddet)")

    # v2.0.7.150 (Bahri'nin bulgusu, 18 Ağustos 2026 — "Ort. Optima Skor
    # yine de eskide kalmış"): KÖK NEDEN bulundu - birçok Döviz/Maden/
    # BIST varlığının Optima_Skor'u henüz NaN'dı (hiç hesaplanmamış).
    # NaN + puan = NaN (Python/pandas'ta NaN aritmetiği hep NaN verir) -
    # yani ayarlama bu varlıklar için SESSİZCE hiç uygulanmıyordu, sonra
    # sayfa kendi "eksik skoru doldur" mantığıyla bunları HAM (ayarlanmamış)
    # formülle dolduruyordu. En üstte gösterilen (zaten skoru olan) birkaç
    # varlık doğru ayarlanmış görünürken, geri kalanların ÇOĞU ayarlamayı
    # hiç almıyor, ortalama da bu yüzden eski kalıyordu. Düzeltme:
    # ayarlama uygulanmadan ÖNCE, etkilenen kategorilerdeki TÜM eksik
    # (NaN) Optima_Skor'lar önce scoring.py ile tam olarak hesaplanıp
    # dolduruluyor - böylece ayarlama HİÇBİR varlığı atlamadan uygulanır.
    _etkilenen_kategoriler = [k for k, v in _beklenti_kategori_ayar.items() if v != 0]
    for _kat_doldur in _etkilenen_kategoriler:
        _mask_eksik = (df_uni["Kategori"] == _kat_doldur) & (df_uni["Optima_Skor"].isna())
        if _mask_eksik.any():
            df_uni.loc[_mask_eksik, "Optima_Skor"] = df_uni.loc[_mask_eksik].apply(
                lambda r: optima_score(
                    float(r.get("RSI", 50) or 50), float(r.get("Ret1M", 0) or 0),
                    vol=float(r.get("Vol", 30) or 30),
                    has_fundamental=any(
                        v is not None and str(v) != "nan" and float(v or 0) > 0
                        for v in (r.get("PB"), r.get("PE"), r.get("DY"))),
                    pb=r.get("PB"), pe=r.get("PE"), dy=r.get("DY")),
                axis=1)

    for _kat, _ayar in _beklenti_kategori_ayar.items():
        if _ayar != 0:
            _mask_bk = df_uni["Kategori"] == _kat
            df_uni.loc[_mask_bk, "Optima_Skor"] = (
                df_uni.loc[_mask_bk, "Optima_Skor"] + _ayar).clip(0, 100)

    # v2.0.7.149: TÜM sayfalarda görünen kısa bir üst şerit - kullanıcı
    # hangi sayfada olursa olsun ayarlamanın aktif olduğunu ve HANGİ
    # kategorilerin ne kadar etkilendiğini bilsin, sadece Ana Sayfa'da
    # değil.
    st.info(
        f"**Onayladığınız tespitler uygulanıyor** — {', '.join(_beklenti_log)} (Risk: {risk}). "
        f"Değerli Maden **{_beklenti_kategori_ayar['MADEN']:+.1f}**, "
        f"Döviz **{_beklenti_kategori_ayar['DOVIZ']:+.1f}**, "
        f"BIST **{_beklenti_kategori_ayar['BIST']:+.1f}**, "
        f"Kripto **{_beklenti_kategori_ayar['KRIPTO']:+.1f}** puan ayarlandı — "
        f"tahmin değildir, onayladığınız tespitlere dayalıdır."
    )

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

def _render_gerceklesmis_kar_zarar(_cur_user):
    """v2.0.7.111 - Bahri'nin bulgusu (30 Temmuz 2026): portfoy tamamen
    bosaldiginda (tum pozisyonlar satildiginda) bu bolum eskiden HIC
    gorunmuyordu, cunku birazdan gorulecek 'Henuz pozisyon yok' mesajinin
    hemen ardindan gelen st.stop() TUM sayfa calismasini durduruyordu -
    bu bolume (portfolio_sales tablosundan gelen satis gecmisi/gerceklesen
    kar-zarar) hic sira gelmiyordu. Bu bolum ACIK POZISYONLARA bagli
    DEGIL (sadece _cur_user'a bagli) - fonksiyona cikarildi, hem bos hem
    dolu portfoy durumunda cagrilabilsin diye."""
    # ══════════════════════════════════════════════════════════
    # v2.0.7.49 - GERÇEKLEŞMİŞ KÂR/ZARAR (Bahri'nin talebi): gerçek bir
    # muhasebe katmanı - satış geçmişi, komisyon/vergi düşülmüş net K/Z,
    # tarih aralığı + aylık/yıllık özet raporu.
    # DUZELTME (v2.0.7.49): Bu blok yanlislikla "elif page in CAT:"
    # (BIST/TEFAS/Doviz/Maden/Kripto ortak blogu) icine eklenmisti - bu
    # yuzden TUM kategori sayfalarinda goruyordu. Dogru yere (yalnizca
    # Portfoyum sayfasinin sonuna) tasindi. Ayrica emoji/widget KESINLIKLE
    # kullanilmiyor - proje kuralinin ihlaliydi, duzeltildi.
    # ══════════════════════════════════════════════════════════
    st.divider()
    st.subheader("Gerçekleşmiş Kâr/Zarar (Muhasebe)")
    from portfolio_ledger import (get_fee_settings, save_fee_settings,
                                   get_sales_history, get_monthly_summary,
                                   get_yearly_summary, get_realized_summary)

    with st.expander("Komisyon / Vergi Ayarları (kategori bazlı)"):
        st.caption(
            "Aşağıdaki oranlar genel/yaklaşık başlangıç değerleridir, kesin "
            "mali müşavirlik veya vergi danışmanlığı yerine geçmez. Kendi "
            "aracı kurumunuzun/borsanızın komisyon oranına ve güncel "
            "mevzuata göre düzenleyin.")
        _fee_ayarlari = get_fee_settings(_cur_user["id"])
        for _cat_key, _cat_lbl in [("BIST","BIST"),("TEFAS","TEFAS"),
                                     ("KRIPTO","Kripto"),("DOVIZ","Döviz"),
                                     ("MADEN","Değerli Maden")]:
            _fc1, _fc2, _fc3 = st.columns([1, 1, 1])
            _mevcut = _fee_ayarlari.get(_cat_key, {"fee_pct":0.0,"tax_pct":0.0})
            with _fc1:
                st.markdown(f"**{_cat_lbl}**")
            with _fc2:
                _yeni_fee = parse_tr(st.text_input(
                    "Komisyon %", value=fmt_tr(float(_mevcut["fee_pct"]), 2),
                    key=f"fee_ayar_{_cat_key}"))
            with _fc3:
                _yeni_tax = parse_tr(st.text_input(
                    "Vergi %", value=fmt_tr(float(_mevcut["tax_pct"]), 2),
                    key=f"tax_ayar_{_cat_key}"))
            if _yeni_fee != _mevcut["fee_pct"] or _yeni_tax != _mevcut["tax_pct"]:
                save_fee_settings(_cur_user["id"], _cat_key, _yeni_fee, _yeni_tax)

    _pl_tum = get_sales_history(_cur_user["id"])
    if _pl_tum.empty:
        st.caption("Henüz gerçekleşmiş (satılmış) bir işlem yok. Bir varlığı "
                   "yukarıdaki tablodan seçip Sat butonuyla satış kaydı "
                   "oluşturduğunuzda burada raporlanır.")
    else:
        # v2.0.7.58 - Yardimci Turkce format fonksiyonlari erken tanimlandi
        # (Aylik/Yillik ozet + Tum Islem Gecmisi, hepsi bunlari kullanir).
        def _tr_sayi(x, ondalik=2):
            try:
                return (f"{float(x):,.{ondalik}f}"
                        .replace(",", "X").replace(".", ",").replace("X", "."))
            except (TypeError, ValueError):
                return str(x)

        def _pl_netkz_renk(v):
            # v2.0.7.61 - CSS "text-align" hack'i kaldirildi - artik
            # column_config'in GERCEK alignment="right" parametresi
            # kullaniliyor, sadece renk burada kaliyor.
            try:
                sayi = float(str(v).replace(".", "").replace(",", "."))
            except (TypeError, ValueError):
                return ""
            if sayi > 0:
                return "color: #1b8a4a; font-weight: 600;"
            elif sayi < 0:
                return "color: #c0392b; font-weight: 600;"
            return ""

        st.markdown("**Tarih Aralığına Göre Özet**")
        dr1, dr2 = st.columns(2)
        import datetime as _dt_pl
        with dr1:
            _pl_bas = st.date_input("Başlangıç", key="pl_bas_tarih",
                                     value=_dt_pl.date.today() - _dt_pl.timedelta(days=30),
                                     format="DD.MM.YYYY")
        with dr2:
            _pl_bit = st.date_input("Bitiş", key="pl_bit_tarih", value=_dt_pl.date.today(),
                                     format="DD.MM.YYYY")
        # v2.0.7.62 - PERFORMANS: asagidaki 3 cagri artik AYRI sorgu
        # yapmiyor, yukarida zaten cekilmis "_pl_tum" DataFrame'ini
        # tekrar kullaniyor - Portfoyum sayfasi basina 4 yerine 1
        # veritabani sorgusu (Bahri'nin "sistem agirlasti" bulgusu).
        _ozet = get_realized_summary(_cur_user["id"],
                                      _pl_bas.strftime("%Y-%m-%d"),
                                      _pl_bit.strftime("%Y-%m-%d"),
                                      df=_pl_tum)
        o1, o2, o3, o4, o5 = st.columns(5)
        o1.metric("İşlem Sayısı", _ozet["islem_sayisi"])
        o2.metric("Brüt K/Z", f"{fmt_tr(_ozet['brut_kz'])} ₺")
        o3.metric("Komisyon", f"-{fmt_tr(_ozet['komisyon'])} ₺")
        o4.metric("Vergi", f"-{fmt_tr(_ozet['vergi'])} ₺")
        o5.metric("Net K/Z", f"{fmt_tr(_ozet['net_kz'])} ₺")

        # v2.0.7.58 - Aylik/Yillik ozet tablolarina Turkce sayi formati
        # uygulandi (onceki halde "68.35" gibi ingilizce noktali gorunuyordu).
        def _ozet_tablo_gostergisi(df_ozet):
            df_g = df_ozet.copy()
            for _c in ["Ödenmiş Komisyon (₺)", "Ödenmiş Vergi (₺)",
                       "İşlem Tutarı (₺)", "Toplam Net K/Z"]:
                if _c in df_g.columns:
                    df_g[_c] = df_g[_c].apply(lambda v: fmt_tr(v))
            if "Toplam Net K/Z" in df_g.columns:
                return df_g.style.map(_pl_netkz_renk, subset=["Toplam Net K/Z"])
            return df_g

        st.markdown("**Aylık Özet**")
        st.dataframe(_ozet_tablo_gostergisi(get_monthly_summary(_cur_user["id"], df=_pl_tum)),
                     width='stretch', hide_index=True)

        st.markdown("**Yıllık Özet**")
        st.dataframe(_ozet_tablo_gostergisi(get_yearly_summary(_cur_user["id"], df=_pl_tum)),
                     width='stretch', hide_index=True)

        st.markdown("**Tüm İşlem Geçmişi**")
        from portfolio_ledger import delete_sale_record, update_sale_record

        # v2.0.7.55 - Bahri'nin bulguları: (1) tarihler Turkce (GG.AA.YYYY)
        # olmali, (2) sayilar Turkce ondalik (virgul) formatinda olmali,
        # (3) Net K/Z pozitif/negatife gore yesil/kirmizi renklensin ve
        # genis rakamlar (100 bin+) icin sutun genisletilsin, (4) Miktar/
        # Komisyon/Vergi sutunlari daraltilsin.
        # v2.0.7.99 - Bahri'nin talebi (20 Temmuz 2026): Alış/Satış Tutarı
        # eklenince tablo genisleyip yatay scroll olusmustu. "Kategori"
        # sutunu (zaten Ticker'dan cikarilabilecek, az bilgi tasiyan bir
        # sutun) tamamen kaldirildi - yer acmak icin.
        _pl_gosterim = _pl_tum.drop(
            columns=["id", "Kategori", "Birim", "Komisyon %", "Vergi %", "Brüt K/Z", "Not"]).copy()

        # v2.0.7.98 - KRITIK EKSIKLIK DUZELTMESI (Bahri'nin bulgusu, 20
        # Temmuz 2026: gerçek bir altın satışı sonrası - ING dekontunda
        # "TL Karşılığı: 3.256,43 TL" yazarken, uygulamada sadece birim
        # fiyat (Satış Fiyatı) ve Net K/Z görünüyordu, GERÇEK SATIŞ TUTARI
        # (Miktar × Satış Fiyatı) hiçbir yerde gösterilmiyordu - banka
        # dekontuyla doğrudan karşılaştırma/mutabakat yapılamıyordu). Aynı
        # eksiklik Alış Tutarı için de geçerliydi. Artık ikisi de
        # (Miktar × ilgili birim fiyat) hesaplanıp tabloya ekleniyor,
        # ilgili fiyat sütununun hemen sağına yerleştiriliyor.
        _pl_gosterim.insert(
            _pl_gosterim.columns.get_loc("Alış Fiyatı") + 1, "Alış Tutarı",
            (_pl_tum["Miktar"] * _pl_tum["Alış Fiyatı"]).round(2))
        _pl_gosterim.insert(
            _pl_gosterim.columns.get_loc("Satış Fiyatı") + 1, "Satış Tutarı",
            (_pl_tum["Miktar"] * _pl_tum["Satış Fiyatı"]).round(2))

        for _dcol in ["Alış Tarihi", "Satış Tarihi"]:
            _pl_gosterim[_dcol] = pd.to_datetime(
                _pl_gosterim[_dcol], errors="coerce").dt.strftime("%d.%m.%Y")
        for _ncol in ["Miktar", "Alış Fiyatı", "Alış Tutarı", "Satış Fiyatı",
                      "Satış Tutarı", "Komisyon (₺)", "Vergi (₺)"]:
            _pl_gosterim[_ncol] = _pl_gosterim[_ncol].apply(_tr_sayi)
        _pl_gosterim["Net K/Z"] = _pl_gosterim["Net K/Z"].apply(lambda v: _tr_sayi(v))

        # v2.0.7.60 - DUZELTME (Bahri'nin bulgusu: ayri tablo denemesi -
        # kendi basligi ve satir araligiyla - "korkunc" gorundu, tabloyla
        # devam ediyormus gibi algilanmiyordu). TOPLAM satiri tekrar AYNI
        # tabloya donduruldu (v2.0.7.56'daki gibi) - tek baslik, sifir
        # bosluk, mukemmel hizalama. Bedel: o satirda da bir isaret kutusu
        # gorunur ama tiklaninca "bu bir kayit degil" diye uyarilip yok
        # sayilir - bu, iki ayri tablonun yarattigi gorsel kopukluktan
        # daha az rahatsiz edici.
        _pl_satir_sayisi = len(_pl_gosterim)
        _pl_toplam_netkz = float(_pl_tum["Net K/Z"].sum())
        _pl_toplam_alis  = float((_pl_tum["Miktar"] * _pl_tum["Alış Fiyatı"]).sum())
        _pl_toplam_satis = float((_pl_tum["Miktar"] * _pl_tum["Satış Fiyatı"]).sum())
        _pl_toplam_satir = {c: "" for c in _pl_gosterim.columns}
        _pl_toplam_satir["Ticker"] = "TOPLAM"
        _pl_toplam_satir["Alış Tutarı"] = _tr_sayi(_pl_toplam_alis)
        _pl_toplam_satir["Satış Tutarı"] = _tr_sayi(_pl_toplam_satis)
        _pl_toplam_satir["Net K/Z"] = _tr_sayi(_pl_toplam_netkz)
        _pl_gosterim = pd.concat(
            [_pl_gosterim, pd.DataFrame([_pl_toplam_satir])], ignore_index=True)

        def _pl_toplam_satir_kalin(row):
            if row.name == _pl_satir_sayisi:
                return ["font-weight: 700; border-top: 2px solid #1b2a4a;"] * len(row)
            return [""] * len(row)

        _pl_styled = (_pl_gosterim.style
                      .map(_pl_netkz_renk, subset=["Net K/Z"])
                      .apply(_pl_toplam_satir_kalin, axis=1))

        # v2.0.7.56 - Bahri'nin talebi: Kategori/Ticker/fiyat/tarih
        # sutunlari da daraltildi (yanal scroll azaltmak icin) - Miktar/
        # Komisyon/Vergi zaten kucuktu, digerleri de artik kucuk; Net K/Z
        # tek genis sutun (buyuk rakamlar icin, orn. 100.000+).
        # v2.0.7.99 - Bahri'nin talebi: Alış/Satış Tutarı eklenince yatay
        # scroll olustu - "Kategori" kaldirildi (yukarida), "Ticker"
        # Portfoy Varliklari Tablosu'yla AYNI piksel genisligine (79px)
        # cekildi, "Komisyon (₺)" basligi "Kom. (₺)" olarak kisaltilip
        # daha da daraltildi (sutun ADI degismedi - column_config'in ilk
        # pozisyonel argumanindan SADECE goruntu etiketi degistirildi,
        # tipki asagidaki Portfoy Varliklari Tablosu'ndaki "Skor" ->
        # "Optima Skor" deseninin aynisi).
        _pl_col_config = {
            "Ticker":        st.column_config.Column(width=79),
            "Miktar":        st.column_config.Column(width="small", alignment="right"),
            "Alış Fiyatı":   st.column_config.Column(width="small", alignment="right"),
            "Alış Tutarı":   st.column_config.Column(width="small", alignment="right"),
            "Alış Tarihi":   st.column_config.Column(width="small"),
            "Satış Fiyatı":  st.column_config.Column(width="small", alignment="right"),
            "Satış Tutarı":  st.column_config.Column(width="small", alignment="right"),
            "Satış Tarihi":  st.column_config.Column(width="small"),
            "Komisyon (₺)":  st.column_config.Column("Kom. (₺)", width=60, alignment="right"),
            "Vergi (₺)":     st.column_config.Column(width="small", alignment="right"),
            "Net K/Z":       st.column_config.Column(width="small", alignment="right"),
        }
        _pl_event = st.dataframe(
            _pl_styled, width='stretch', hide_index=True,
            column_config=_pl_col_config,
            on_select="rerun", selection_mode="single-row", key="pl_gecmis_tablo")
        _pl_sel = _pl_event.selection.rows if hasattr(_pl_event, "selection") else []
        if _pl_sel and _pl_sel[0] >= _pl_satir_sayisi:
            st.caption("TOPLAM satırı bir işlem kaydı değildir, düzenlenemez/silinemez.")
            _pl_sel = []
        if _pl_sel:
            _pl_si = _pl_sel[0]
            _pl_row = _pl_tum.iloc[_pl_si]
            _pl_sel_id = int(_pl_row["id"])
            _pl_sel_tkr = _pl_row["Ticker"]

            _pdz1, _pdz2 = st.columns([1, 1])
            if _pdz1.button(f"Düzelt: {_pl_sel_tkr}", type="primary", key="pl_duzelt_ac"):
                st.session_state["pl_duzelt_form_id"] = _pl_sel_id
            with _pdz2:
                st.caption(
                    "Bu kaydı silebilirsiniz (örn. bir test satışını geri almak "
                    "için). 'Pozisyonu geri aç' işaretlenirse satılan miktar "
                    "açık pozisyona geri eklenir; işaretlenmezse sadece "
                    "muhasebe kaydı silinir, pozisyon değişmez.")
            _pl_geri_ac = st.checkbox("Pozisyonu geri aç (miktarı portföye geri ekle)",
                                       key="pl_geri_ac")
            if st.button(f"Kaydı Sil: {_pl_sel_tkr}", type="secondary", key="pl_kayit_sil"):
                _pl_sonuc = delete_sale_record(_cur_user["id"], _pl_sel_id, _pl_geri_ac)
                if _pl_sonuc["basari"]:
                    st.success("Satış kaydı silindi.")
                    st.rerun()
                else:
                    st.error(_pl_sonuc["hata"])

            # v2.0.7.52 - Duzeltme formu (Bahri'nin talebi: silmek yetmez,
            # yanlis girilen bir kaydin miktar/fiyat/tarih/oranlari
            # duzeltilebilmeli).
            if st.session_state.get("pl_duzelt_form_id") == _pl_sel_id:
                with st.container(border=True):
                    st.markdown(f"**{_pl_sel_tkr} — Kayıt Düzeltme**")
                    dz1, dz2, dz3 = st.columns(3)
                    with dz1:
                        _dz_miktar = parse_tr(st.text_input(
                            "Miktar", value=fmt_tr(float(_pl_row["Miktar"]), 4),
                            key="dz_miktar"))
                    with dz2:
                        _dz_alis = parse_tr(st.text_input(
                            "Alış Fiyatı", value=fmt_tr(float(_pl_row["Alış Fiyatı"]), 4),
                            key="dz_alis"))
                    with dz3:
                        _dz_satis = parse_tr(st.text_input(
                            "Satış Fiyatı", value=fmt_tr(float(_pl_row["Satış Fiyatı"]), 4),
                            key="dz_satis"))
                    dz4, dz5, dz6 = st.columns(3)
                    import datetime as _dt_dz
                    with dz4:
                        try:
                            _dz_alis_tarih_val = _dt_dz.datetime.strptime(
                                str(_pl_row["Alış Tarihi"]), "%Y-%m-%d").date()
                        except Exception:
                            _dz_alis_tarih_val = _dt_dz.date.today()
                        _dz_alis_tarih = st.date_input(
                            "Alış Tarihi", value=_dz_alis_tarih_val,
                            key="dz_alis_tarih", format="DD.MM.YYYY")
                    with dz5:
                        try:
                            _dz_satis_tarih_val = _dt_dz.datetime.strptime(
                                str(_pl_row["Satış Tarihi"]), "%Y-%m-%d").date()
                        except Exception:
                            _dz_satis_tarih_val = _dt_dz.date.today()
                        _dz_satis_tarih = st.date_input(
                            "Satış Tarihi", value=_dz_satis_tarih_val,
                            key="dz_satis_tarih", format="DD.MM.YYYY")
                    with dz6:
                        st.caption("")
                    dz7, dz8 = st.columns(2)
                    with dz7:
                        _dz_komisyon = parse_tr(st.text_input(
                            "Komisyon (₺) — aracı kurumun kestiği gerçek tutar",
                            value=fmt_tr(float(_pl_row["Komisyon (₺)"]), 2),
                            key="dz_komisyon"))
                    with dz8:
                        _dz_vergi = parse_tr(st.text_input(
                            "Vergi (₺) — aracı kurumun kestiği gerçek tutar",
                            value=fmt_tr(float(_pl_row["Vergi (₺)"]), 2),
                            key="dz_vergi"))

                    dzb1, dzb2 = st.columns([1, 1])
                    if dzb1.button("Düzeltmeyi Kaydet", type="primary", key="pl_duzelt_kaydet"):
                        _dz_sonuc = update_sale_record(
                            _cur_user["id"], _pl_sel_id, _dz_miktar, _dz_alis,
                            _dz_alis_tarih.strftime("%Y-%m-%d"), _dz_satis,
                            _dz_satis_tarih.strftime("%Y-%m-%d"),
                            _dz_komisyon, _dz_vergi)
                        if _dz_sonuc["basari"]:
                            st.session_state.pop("pl_duzelt_form_id", None)
                            if _dz_sonuc.get("uyari"):
                                st.warning(_dz_sonuc["uyari"])
                            st.success(f"Kayıt düzeltildi — Net K/Z: {fmt_tr(_dz_sonuc['net_kz'])} ₺")
                            st.rerun()
                        else:
                            st.error(_dz_sonuc["hata"])
                    if dzb2.button("Vazgeç", key="pl_duzelt_vazgec"):
                        st.session_state.pop("pl_duzelt_form_id", None)
                        st.rerun()


def _render_sermaye_nakit_ozeti(_cur_user, portfolio, guncel_varlik_degeri):
    """v2.0.7.112 (Bahri'nin talebi, 30 Temmuz 2026): "başlangıç sermaye
    miktarının, ne kadar zamanda kaça geldiğinin, sattığımda ne kâr
    ettiğimin ve elimde güncel olarak finansal varlık veya nakit olarak
    ne miktarlar olduğunun" görülebilmesi. Bu fonksiyon, Gerçekleşmiş
    Kâr/Zarar bölümüyle AYNI mantıkla (bkz. _render_gerceklesmis_kar_zarar),
    hem portföy boşken hem doluyken çağrılır - sermaye/nakit takibi açık
    pozisyonlara bağlı değil, sadece kullanıcının kendisine bağlı.

    Tasarım (Bahri'nin onayıyla): sermaye tek seferlik sabit bir sayı
    DEĞİL - zaman içinde mevduat/çekim eklenip çıkarılabilen bir hareket
    defteri. Nakit bakiyesi negatife düşebilir (bilinçli - "sermaye
    hayali değil, gerçek durumu göstersin")."""
    from portfolio_ledger import (get_capital_tx_history, add_capital_tx,
                                   delete_capital_tx, get_sales_history,
                                   get_cash_balance)
    import datetime as _dt_cap

    st.divider()
    st.subheader("Sermaye ve Nakit Durumu")

    with st.expander("Sermaye Hareketi Ekle (Para Yatırma / Çekme)"):
        sc1, sc2, sc3 = st.columns([1, 1, 1])
        with sc1:
            _tx_secim = st.selectbox(
                "İşlem Tipi", ["Para Yatırma", "Para Çekme"], key="cap_tx_tip")
        with sc2:
            _tx_tutar_str = st.text_input(
                "Tutar (TL)", key="cap_tx_tutar", placeholder="Örn: 50.000")
        with sc3:
            _tx_tarih = st.date_input(
                "Tarih", key="cap_tx_tarih", format="DD.MM.YYYY")
        _tx_not = st.text_input(
            "Not (isteğe bağlı)", key="cap_tx_not",
            placeholder="Örn: Maaştan aktarım, ilk sermaye")
        if st.button("Kaydet", key="cap_tx_ekle_btn"):
            try:
                _tx_tutar = parse_tr(_tx_tutar_str) if _tx_tutar_str.strip() else 0.0
            except Exception:
                _tx_tutar = 0.0
            _tip = "DEPOSIT" if _tx_secim == "Para Yatırma" else "WITHDRAWAL"
            _sonuc = add_capital_tx(
                _cur_user["id"], _tip, _tx_tutar,
                _tx_tarih.strftime("%Y-%m-%d"), _tx_not)
            if _sonuc["basari"]:
                st.success("Sermaye hareketi kaydedildi.")
                st.rerun()
            else:
                st.error(_sonuc["hata"])

    _cap_df = get_capital_tx_history(_cur_user["id"])
    _sales_df_ozet = get_sales_history(_cur_user["id"])
    _hesap = get_cash_balance(
        _cur_user["id"], portfolio_rows=portfolio,
        sales_df=_sales_df_ozet, capital_df=_cap_df)

    _toplam_servet = _hesap["nakit_bakiye"] + guncel_varlik_degeri
    _toplam_getiri_tl = _toplam_servet - _hesap["net_sermaye"]
    try:
        _toplam_getiri_pct = ((_toplam_servet / _hesap["net_sermaye"] - 1) * 100
                               if _hesap["net_sermaye"] else 0.0)
    except Exception:
        _toplam_getiri_pct = 0.0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Net Yatırılan Sermaye", f"{fmt_tr(_hesap['net_sermaye'])} ₺")
    m2.metric("Nakit Bakiye", f"{fmt_tr(_hesap['nakit_bakiye'])} ₺")
    m3.metric("Güncel Varlık Değeri", f"{fmt_tr(guncel_varlik_degeri)} ₺")
    m4.metric("Toplam Servet (Nakit+Varlık)", f"{fmt_tr(_toplam_servet)} ₺")
    m5.metric("Toplam Getiri",
              f"{'+' if _toplam_getiri_tl >= 0 else ''}{fmt_tr(_toplam_getiri_tl)} ₺",
              delta=f"{'+' if _toplam_getiri_pct >= 0 else ''}{fmt_tr(_toplam_getiri_pct)}%")

    if _hesap["nakit_bakiye"] < 0:
        st.caption(
            "Nakit bakiyeniz negatif — yatırdığınız sermayeden daha fazlasını "
            "varlığa yatırmışsınız görünüyor (ör. kâr üstüne tekrar yatırım, "
            "ya da henüz kaydedilmemiş bir mevduat olabilir). Bu bilinçli "
            "olarak engellenmiyor, gerçek durumu yansıtması için.")

    if _cap_df.empty:
        st.caption("Henüz bir sermaye hareketi (mevduat/çekim) kaydı yok. "
                   "Yukarıdaki bölümden ekleyebilirsin.")
    else:
        with st.expander("Sermaye Hareketi Geçmişi", expanded=False):
            _cap_show = _cap_df.copy()
            _cap_show["Tip"] = _cap_show["Tip"].map(
                {"DEPOSIT": "Para Yatırma", "WITHDRAWAL": "Para Çekme"})
            _cap_show["Tutar"] = _cap_show["Tutar"].apply(lambda v: fmt_tr(v, 2))
            _cap_show["Tarih"] = _cap_show["Tarih"].apply(
                lambda v: _dt_cap.datetime.strptime(v, "%Y-%m-%d").strftime("%d.%m.%Y")
                if v and len(str(v)) == 10 else v)
            st.dataframe(_cap_show.drop(columns=["id"]), width='stretch', hide_index=True)

            _sil_id = st.selectbox(
                "Silinecek işlem (id)", _cap_df["id"].tolist(), key="cap_tx_sil_id")
            if st.button("Seçili İşlemi Sil", key="cap_tx_sil_btn"):
                delete_capital_tx(_cur_user["id"], int(_sil_id))
                st.success("Sermaye hareketi silindi.")
                st.rerun()


@st.cache_data(ttl=3600, show_spinner=False)
def _benchmark_close_series(df):
    """v2.0.7.128 - yfinance'in degisen kolon bicimlerinden (MultiIndex ya
    da tekli) tek boyutlu bir Close Serisi cikarir. None donerse cagiran
    taraf o kiyaslamayi atlar."""
    if df is None or len(df) == 0:
        return None
    try:
        if isinstance(df.columns, pd.MultiIndex):
            for col in df.columns:
                if str(col[0]).lower() == "close":
                    return df[col]
            return None
        if "Close" in df.columns:
            return df["Close"]
        if "close" in df.columns:
            return df["close"]
        return df.iloc[:, 0]
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def _kiyaslama_ticker_serileri_cek(portfolio):
    """v2.0.7.132 (Bahri'nin bulgusu, 10 Ağustos 2026 — "sistem çok
    ağırlaşmış" şikayeti üzerine performans düzeltmesi): Bu, portföydeki
    her benzersiz ticker için geçmiş fiyat serisini (+ son güne canlı
    fiyat eziyor) çeken PAHALI kısımdı - hem `_kiyaslama_gunluk_serileri`
    (ana grafik) hem `_render_pozisyon_karsilastirma` (pozisyon grafiği)
    bunu AYRI AYRI, ÖNBELLEKSİZ yapıyordu - yani Portföyüm sayfası her
    açıldığında AYNI geçmiş veri 2 KEZ çekiliyordu, hiçbiri
    önbelleklenmiyordu (her widget etkileşiminde - Streamlit'in tam
    script yeniden çalıştırma modeli yüzünden - ikisi de baştan
    çalışıyordu). Artık TEK, PAYLAŞILAN, 5 DAKİKA önbellekli bu
    fonksiyon - iki grafik de aynı sonucu (aynı Streamlit oturumunda)
    tekrar tekrar çekmeden kullanıyor.

    Döner: (_ticker_seri: {ticker: pd.Series}, _gun_araligi: DatetimeIndex,
    _baslangic: date) - ya da hiçbir geçerli alış tarihi yoksa
    (None, None, None)."""
    import datetime as _dt_ks

    _tarihler = []
    for _p in portfolio:
        _t = _p.get("purchase_date", "")
        if _t and len(str(_t)) == 10:
            try:
                _tarihler.append(_dt_ks.date.fromisoformat(_t))
            except Exception:
                pass
    if not _tarihler:
        return None, None, None
    _baslangic = min(_tarihler)
    _bugun = _dt_ks.date.today()
    if _baslangic >= _bugun:
        return None, None, None

    _gun_farki = (_bugun - _baslangic).days
    if _gun_farki <= 35: _period = "1mo"
    elif _gun_farki <= 95: _period = "3mo"
    elif _gun_farki <= 190: _period = "6mo"
    elif _gun_farki <= 370: _period = "1y"
    elif _gun_farki <= 1100: _period = "3y"
    else: _period = "5y"

    _gun_araligi = pd.date_range(_baslangic, _bugun, freq="D")

    def _seri_hazirla(_close_serisi):
        _s = _close_serisi.astype(float).copy()
        _idx = pd.to_datetime(_s.index)
        if getattr(_idx, "tz", None) is not None:
            _idx = _idx.tz_localize(None)
        _s.index = _idx
        _s = _s[~_s.index.duplicated(keep="last")].sort_index()
        _s = _s.reindex(_gun_araligi, method="ffill")
        return _s.bfill()

    _ticker_seri = {}
    _benzersiz_tickerlar = []
    for _p in portfolio:
        _tkr = _p.get("ticker")
        _kat = _p.get("asset_type") or "BIST"
        if not _tkr or _tkr in _ticker_seri:
            continue
        _benzersiz_tickerlar.append(_tkr)
        try:
            _h = get_hist(_tkr, "", _kat, _period)
        except Exception:
            _h = None
        if _h is not None and not _h.empty and "Close" in _h.columns:
            _ticker_seri[_tkr] = _seri_hazirla(_h["Close"])

    try:
        _canli_fiyatlar = _ld_portfolio_prices(df_uni, _benzersiz_tickerlar)
    except Exception:
        _canli_fiyatlar = {}
    for _tkr in _benzersiz_tickerlar:
        if _tkr not in _ticker_seri:
            continue
        _canli = _canli_fiyatlar.get(_tkr, 0.0)
        if not _canli or _canli <= 0:
            _match_u = df_uni[df_uni["Ticker"] == _tkr]
            if not _match_u.empty:
                try:
                    _canli = float(_match_u["Son_Fiyat"].iloc[0])
                except Exception:
                    _canli = 0.0
        if _canli and _canli > 0:
            _ticker_seri[_tkr].iloc[-1] = _canli

    return _ticker_seri, _gun_araligi, _baslangic


@st.cache_data(ttl=300, show_spinner=False)
def _kiyaslama_gunluk_serileri(portfolio):
    """v2.0.7.128 (Bahri'nin talebi, 10 Ağustos 2026 — köklü yeniden
    tasarım): Portföyün VE her kıyaslama aracının GÜNLÜK kümülatif getiri
    serisini hesaplar (başlangıç = portföydeki EN ERKEN alış tarihi,
    bitiş = bugün). Grafik çizimi için {seri_adı: pd.Series} döner.

    Portföy serisi için TSO'nun ZATEN sahip olduğu birleşik `get_hist()`
    kullanılıyor. Altın için de (eski sentetik GC=F×USDTRY yerine)
    `get_hist(..., "MADEN", ...)` kullanılıyor - MADEN için "hiçbir
    sentetik USD->TL çevrimi denenmez" kuralıyla tutarlı.

    v2.0.7.132 - PERFORMANS: ticker-seri çekme kısmı artık paylaşılan,
    önbellekli `_kiyaslama_ticker_serileri_cek()`'ten geliyor (bkz. o
    fonksiyonun notu) - hem bu fonksiyon hem `_render_pozisyon_karsilastirma`
    tekrar tekrar aynı veriyi çekmiyor. Ayrıca BU fonksiyonun kendisi de
    5 dakika önbellekli - Portföyüm sayfası her rerun olduğunda (herhangi
    bir widget etkileşiminde) baştan hesaplanmıyor."""
    import datetime as _dt_ks

    _ticker_seri, _gun_araligi, _baslangic = _kiyaslama_ticker_serileri_cek(portfolio)
    if _ticker_seri is None:
        return None

    def _seri_hazirla(_close_serisi):
        _s = _close_serisi.astype(float).copy()
        _idx = pd.to_datetime(_s.index)
        if getattr(_idx, "tz", None) is not None:
            _idx = _idx.tz_localize(None)
        _s.index = _idx
        _s = _s[~_s.index.duplicated(keep="last")].sort_index()
        _s = _s.reindex(_gun_araligi, method="ffill")
        return _s.bfill()

    _gun_farki = (_dt_ks.date.today() - _baslangic).days
    if _gun_farki <= 35: _period = "1mo"
    elif _gun_farki <= 95: _period = "3mo"
    elif _gun_farki <= 190: _period = "6mo"
    elif _gun_farki <= 370: _period = "1y"
    elif _gun_farki <= 1100: _period = "3y"
    else: _period = "5y"

    _portfoy_deger = pd.Series(0.0, index=_gun_araligi)
    _portfoy_maliyet = pd.Series(0.0, index=_gun_araligi)
    for _p in portfolio:
        _tkr = _p.get("ticker")
        _t = _p.get("purchase_date", "")
        if not _t or _tkr not in _ticker_seri:
            continue
        try:
            _alis_tarihi = pd.Timestamp(_dt_ks.date.fromisoformat(_t))
        except Exception:
            continue
        _adet = float(_p.get("quantity", 0) or 0)
        _maliyet_birim = float(_p.get("avg_cost", 0) or 0)
        if _adet <= 0 or _maliyet_birim <= 0:
            continue
        _s = _ticker_seri[_tkr]
        _aktif = _gun_araligi >= _alis_tarihi
        _portfoy_deger.loc[_aktif] += _adet * _s.loc[_aktif]
        _portfoy_maliyet.loc[_aktif] += _adet * _maliyet_birim

    _gecerli_maliyet = _portfoy_maliyet.replace(0, np.nan)
    _portfoy_getiri = ((_portfoy_deger / _gecerli_maliyet) - 1) * 100
    _portfoy_getiri = _portfoy_getiri.fillna(0.0)
    _sonuc = {"Portföyünüz": _portfoy_getiri}

    # 2) BIST 100 endeksi (yfinance, TSO evreninde olmayan tek dış varlık)
    # v2.0.7.169 (Bahri'nin bulgusu, 20 Ağustos 2026 — "BIST100'ün
    # buradan çıktığını görüyorum, bir süre bekleyince geri geliyor"):
    # KÖK NEDEN: yfinance geçici bir ağ/rate-limit hatası verdiğinde
    # eski kod `except Exception: pass` ile BIST 100'ü SESSİZCE
    # düşürüyordu. Bu fonksiyon 5 dakika önbellekli olduğu için, tam o
    # anda oluşan bir hata "BIST 100 yok" durumunu TAM 5 DAKİKA
    # boyunca dondurup önbelleğe kaydediyordu - "bir süre bekleyince
    # geri gelmesi" bu yüzdendi (önbellek süresi dolup yeni bir deneme
    # başarılı olana kadar). Çözüm: 2 KEZ daha dene (kısa bekleme ile)
    # önce pes et - yfinance'ın bilinen geçici flakiness'ini tolere
    # etmek için (live_data.py'deki borsapy retry desenleriyle tutarlı).
    # v2.0.7.175 (Bahri'nin bulgusu, 21 Ağustos 2026 — "BIST100'ün
    # grafikte olmaması yine devam eden bir sorun"): v2.0.7.169'daki
    # RETRY MANTIĞINDA BİR HATA VARDI - `break` satırı, exception
    # FIRLAMADIĞI her durumda ÇALIŞIYORDU, `_bs` GERÇEKTEN BOŞ/YETERSİZ
    # gelse bile. yfinance'ın EN YAYGIN başarısızlık şekli tam olarak bu:
    # hata FIRLATMADAN boş bir DataFrame döndürmek (rate-limit'te sık
    # görülür). Yani eski kod, İLK denemede "boş ama hatasız" bir sonuç
    # aldığında HİÇ YENİDEN DENEMİYORDU - retry'nin kendisi işlevsizdi.
    # ÇÖZÜM: `break` artık SADECE gerçekten `_sonuc["BIST 100"]`
    # ATANDIĞINDA çalışıyor - boş/yetersiz veri de artık normal başarısız
    # bir deneme sayılıp yeniden deneniyor.
    for _bist100_deneme in range(3):
        try:
            import yfinance as yf
            _bb = yf.download("XU100.IS", start=_baslangic.isoformat(), progress=False)
            _bs = _benchmark_close_series(_bb)
            if _bs is not None and len(_bs) > 1:
                _bs = _seri_hazirla(_bs)
                if float(_bs.iloc[0]) > 0:
                    _sonuc["BIST 100"] = (_bs / float(_bs.iloc[0]) - 1) * 100
                    break  # GERÇEKTEN basarili - veri atandi, artik dur
            # Buraya dustuyse: exception YOK ama veri bos/yetersizdi -
            # bu da basarisizlik sayilir, asagidaki ayni bekleme/retry
            # bloguna duser (exception blogundakiyle AYNI davranis).
            if _bist100_deneme < 2:
                import time as _time_b100
                _time_b100.sleep(1.5)
        except Exception:
            if _bist100_deneme < 2:
                import time as _time_b100
                _time_b100.sleep(1.5)
                continue
            # 3 denemenin hepsi basarisiz - BIST 100 bu turda YOK,
            # ama en azindan sebepsiz yere ilk hatada pes edilmedi.

    # 3) Altın ve Dolar/TL - TSO'nun kendi kategori verisiyle (sentetik yok)
    for _ad, _tkr, _kat in (("Altın", "ALTIN_TRY", "MADEN"), ("Dolar/TL", "USDTRY", "DOVIZ")):
        try:
            _h = get_hist(_tkr, "", _kat, _period)
        except Exception:
            _h = None
        if _h is not None and not _h.empty and "Close" in _h.columns:
            _s = _seri_hazirla(_h["Close"])
            if float(_s.iloc[0]) > 0:
                _sonuc[_ad] = (_s / float(_s.iloc[0]) - 1) * 100

    # 4) Mevduat / Tahvil / Repo - TCMB EVDS'ten tam otomatik, basit
    # faizle (oran x gun/365) dogrusal birikim.
    _evds_oranlar = _evds_referans_oranlari_cek()
    _gun_sayilari = np.array([(d.date() - _baslangic).days for d in _gun_araligi], dtype=float)
    for _ad, _key in (("Vadeli Mevduat", "mevduat"), ("Devlet Tahvili", "tahvil"), ("Repo", "repo")):
        _oran, _hata = _evds_oranlar.get(_key, (None, "bilinmeyen seri"))
        if _oran and _oran > 0:
            _sonuc[_ad] = pd.Series(_oran / 365 * _gun_sayilari, index=_gun_araligi)

    return _sonuc


def _evds_seri_cek(seri_kodu, gun_geriye=120):
    """v2.0.7.129 (Bahri'nin talebi, 10 Ağustos 2026): "elle veri girişi
    asla kabul edilemez" - v2.0.7.126'daki mevduat-özel fonksiyon
    genelleştirildi, artık TCMB EVDS'deki HERHANGİ bir seriyi çekebiliyor.
    Araştırma sonucu bulunan 3 seri:
      - Mevduat: TP.MT210AGS.TRY.MT01 ("1 Aya Kadar Vadeli TL Mevduat,
        Stok, %", aylık)
      - Repo:    TP.AOFOBAP ("Borsa İstanbul Gecelik Repo Ağırlıklı
        Ortalama Faiz Oranı", günlük)
      - Tahvil:  TP.BISTTLREF.ORAN ("BIST TLREF - TL Gecelik Referans
        Faiz Oranı", günlük) - EVDS'de tek bir "gösterge tahvil getirisi"
        serisi yok (DİBS verisi 2500+ tekil ISIN bazlı, tek bir gösterge
        değil), TLREF piyasada yaygın kullanılan gerçek bir referans oranı
        olduğu için en yakın anlamlı otomatik alternatif.

    GÜVENLİK: API anahtarı ASLA kod içine yazılmaz (bu repo public) - önce
    EVDS_API_KEY ortam değişkeninden, sonra Streamlit secrets'tan okunur.

    (değer, hata_detayı) tuple'ı döner - değer None ise hata_detayı NEDEN
    başarısız olduğunu açıkça söyler."""
    try:
        _key = os.environ.get("EVDS_API_KEY", "")
        if not _key:
            try:
                _key = st.secrets.get("EVDS_API_KEY", "")
            except Exception:
                _key = ""
        if not _key:
            return None, "EVDS_API_KEY tanımlı değil (ne ortam değişkeninde ne Streamlit secrets'ta bulundu)"
        try:
            from evds import evdsAPI
        except Exception as e:
            return None, f"'evds' paketi import edilemedi: {type(e).__name__}: {e}"
        import datetime as _dt_evds
        e = evdsAPI(_key)
        bugun = _dt_evds.date.today()
        onceki = bugun - _dt_evds.timedelta(days=gun_geriye)
        df = e.get_data([seri_kodu],
                         startdate=onceki.strftime("%d-%m-%Y"),
                         enddate=bugun.strftime("%d-%m-%Y"))
        if df is None or df.empty:
            return None, f"EVDS'ten boş sonuç döndü ({seri_kodu})"
        _kolon = seri_kodu.replace(".", "_")
        if _kolon not in df.columns:
            _kolon = df.columns[-1]
        _son = df[_kolon].dropna()
        if _son.empty:
            return None, f"EVDS serisinde geçerli veri yok ({seri_kodu})"
        return round(float(_son.iloc[-1]), 2), None
    except Exception as _dis_hata:
        return None, f"{type(_dis_hata).__name__}: {_dis_hata}"


def _en_yuksek_vadeli_mevduat_cek():
    """v2.0.7.131 (Bahri'nin talebi, 10 Ağustos 2026): "Banka mevduatı,
    bankaların vadeli mevduata verdikleri EN YÜKSEK faiz gözetilerek
    hesaplanmalı" - TCMB EVDS'deki TP.MT210AGS.TRY.MT01 bir AĞIRLIKLI
    ORTALAMA, en yüksek değil, o yüzden bu amaca uymuyordu.

    Araştırma: hesap.com'un "en çok kazandıran mevduat" bölümü Cloudflare
    bot korumasıyla engelleniyordu (doğrudan test edildi - 403 + "Just a
    moment" sayfası). hesapkurdu.com/mevduat ise ENGELSİZ ve sunucu
    tarafında render ediliyor (Next.js SSR) - oranlar
    '<td class="Table_td__xlSfc">% 46,00</td>' bicimindeki HTML'de
    doğrudan mevcut, JS calistirmaya gerek yok.

    Sayfadaki TÜM bankaların oranlarını çeker, EN YÜKSEĞİNİ döner -
    (değer, hata_detayı) tuple'ı."""
    try:
        import requests, re as _re_evm
        _headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36"),
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        _r = requests.get("https://www.hesapkurdu.com/mevduat",
                          headers=_headers, timeout=15)
        if _r.status_code != 200:
            return None, f"hesapkurdu.com HTTP {_r.status_code}"
        _oranlar = _re_evm.findall(
            r'Table_td__xlSfc">%\s*<!-- -->\s*([\d]+,[\d]+)</td>', _r.text)
        if not _oranlar:
            return None, "hesapkurdu.com sayfa yapısı değişmiş olabilir (oran bulunamadı)"
        _en_yuksek = max(float(o.replace(",", ".")) for o in _oranlar)
        return round(_en_yuksek, 2), None
    except Exception as _e:
        return None, f"{type(_e).__name__}: {_e}"


@st.cache_data(ttl=21600, show_spinner=False)
def _evds_referans_oranlari_cek():
    """v2.0.7.131 - Mevduat (en yüksek, hesapkurdu.com) + Tahvil/Repo
    (TCMB EVDS) TEK seferde çekilir (6 saat cache - bu oranlar günde en
    fazla 1 kez güncelleniyor, sık sorgulamaya gerek yok).
    {"mevduat": (deger,hata), "tahvil": (...), "repo": (...)} döner."""
    return {
        "mevduat": _en_yuksek_vadeli_mevduat_cek(),
        "tahvil": _evds_seri_cek("TP.BISTTLREF.ORAN", gun_geriye=10),
        "repo": _evds_seri_cek("TP.AOFOBAP", gun_geriye=10),
    }


def _render_karsilastirma(_cur_user, portfolio):
    """v2.0.7.129 (Bahri'nin talebi, 10 Ağustos 2026 — ikinci köklü
    revizyon): (1) Mevduat/Tahvil/Repo artık ÜÇÜ DE TCMB EVDS'ten tam
    otomatik çekiliyor (araştırma: TP.MT210AGS.TRY.MT01, TP.AOFOBAP,
    TP.BISTTLREF.ORAN) - "elle veri girişi asla kabul edilemez" talebi
    üzerine manuel giriş bölümü TAMAMEN kaldırıldı. (2) Grafik çizgi
    renkleri daha belirgin/canlı (soft tonlar değil) ve kalınlaştırıldı.
    (3) Portföyünüzdeki ilk alışın tarihinden bugüne, günlük kümülatif
    getiri - her araç ayrı renkli çizgi (Plotly)."""
    st.subheader("Getiri Kıyaslaması")
    st.caption(
        "Portföyünüzdeki ilk alışın tarihinden bugüne, günlük kümülatif "
        "getiri - TSO'da olan/olmayan diğer araçlarla karşılaştırmalı."
    )

    if not portfolio:
        st.info("Karşılaştırma için açık pozisyon yok.")
        return

    with st.spinner("Geçmiş piyasa verileri hesaplanıyor (BIST100/Altın/Dolar/Mevduat/Tahvil/Repo/portföy varlıkları)..."):
        _seriler = _kiyaslama_gunluk_serileri(portfolio)

    if not _seriler:
        st.info("Karşılaştırma için geçerli alış tarihi olan pozisyon bulunamadı.")
        return

    if "BIST 100" not in _seriler:
        st.caption(
            "⚠ BIST 100 karşılaştırması şu an yüklenemedi (Yahoo Finance "
            "tarafında geçici bir sorun olabilir) - sayfayı birkaç dakika "
            "sonra yenilemeyi deneyin."
        )

    import plotly.graph_objects as go
    # v2.0.7.167 (Bahri'nin talebi, 20 Ağustos 2026 — "grafik çok
    # anlaşılmaz bir hal aldı barları kaldır"): v2.0.7.166'da eklenen
    # günlük değişim barları GERİ ALINDI - 7 varlığın barları üst üste
    # binince (yarı saydam da olsa) çizgi grafiği okunaksız hale
    # getirdi. Sadece kümülatif çizgilere geri dönüldü (v2.0.7.143'teki
    # hal). Günlük hareketi görmek isterse ayrı, daha sade bir çözüm
    # (ör. tek seçili varlık için ayrı bir bar grafiği) ileride
    # düşünülebilir - burada TÜMÜNÜ AYNI ANDA basmak yanlış çıktı.
    _renkler = {
        "Portföyünüz": "#1d4ed8", "BIST 100": "#111827", "Altın": "#b45309",
        "Dolar/TL": "#15803d", "Vadeli Mevduat": "#a21caf",
        "Devlet Tahvili": "#4338ca", "Repo": "#b91c1c",
    }
    # v2.0.7.169 (Bahri'nin bulgusu, 20 Ağustos 2026 — "çizgi ve etiket
    # renkleri ile çizgi kalınlıkları ayırt edici değil, anlaşılır hale
    # getir"): RENK TEK BAŞINA yeterli değildi - her çizgi kendine özgü
    # bir DESEN de alıyor (düz/kesikli/noktalı/nokta-çizgi). Bu özellikle
    # Devlet Tahvili/Repo gibi DEĞERLERİ neredeyse aynı çıkıp üst üste
    # binen çizgilerin birbirini TAMAMEN gizlemesini önlüyor.
    _desenler = {
        "Portföyünüz": "solid", "BIST 100": "dash", "Altın": "solid",
        "Dolar/TL": "dot", "Vadeli Mevduat": "dashdot",
        "Devlet Tahvili": "longdash", "Repo": "longdashdot",
    }
    fig = go.Figure()
    for _ad, _seri in _seriler.items():
        fig.add_trace(go.Scatter(
            x=_seri.index, y=_seri.values, mode="lines", name=_ad,
            line=dict(width=4 if _ad == "Portföyünüz" else 2.75,
                      color=_renkler.get(_ad, "#374151"),
                      dash=_desenler.get(_ad, "solid")),
            hovertemplate="<b>" + _ad + "</b>: %{y:.2f}%<extra></extra>",
        ))
        # v2.0.7.169: çizginin sağ ucuna doğrudan etiket - hover'a gerek
        # kalmadan hangi çizginin hangi varlık olduğu görülüyor.
        fig.add_annotation(
            x=_seri.index[-1], y=float(_seri.iloc[-1]),
            text=f" {_ad}", showarrow=False, xanchor="left",
            font=dict(size=11, color=_renkler.get(_ad, "#374151")),
        )
    fig.add_hline(y=0, line_width=1, line_color="rgba(120,120,120,0.4)")
    fig.update_layout(
        template="plotly_white", height=440,
        # v2.0.7.169: sağ uçtaki etiketlerin sığması için sağ kenar
        # boşluğu artırıldı (10 -> 90).
        margin=dict(l=10, r=90, t=10, b=10),
        # v2.0.7.143 (Bahri'nin talebi): imleci bir CIZGININ uzerine
        # goturunce SADECE o serinin adi/degeri gorunsun - "x unified"
        # (butun serileri tek kutuda listeler) yerine "closest" (imlecin
        # en yakin oldugu TEK cizgiyi gosterir).
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis=dict(title="Kümülatif Getiri", ticksuffix="%",
                   gridcolor="rgba(120,120,120,0.15)", zeroline=False),
        xaxis=dict(gridcolor="rgba(120,120,120,0.08)"),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=13),
    )
    st.plotly_chart(fig, use_container_width=True)

    _ozet = " · ".join(
        f"{_ad}: {fmt_tr_isaretli(float(_seri.iloc[-1]), 2, yuzde=True)}"
        for _ad, _seri in _seriler.items()
    )
    st.caption(f"Bugün itibarıyla — {_ozet}")
    st.caption(
        "Vadeli Mevduat, hesapkurdu.com'daki bankaların 32 gün vadeli "
        "tekliflerinden EN YÜKSEK orana göre; Tahvil/Repo, TCMB EVDS'ten "
        "(sırasıyla BIST TLREF gecelik referans faiz oranı, BIST gecelik "
        "repo ağırlıklı ortalama faiz oranı) çekilen güncel oranlarla basit "
        "faizle (oran × gün/365) hesaplanır - gerçek bir işlemin (stopaj, "
        "minimum vade vb.) tam yerine geçmez. Kısa dönemli getiriler "
        "piyasa koşullarına bağlıdır, tek bir dönemden genel bir sonuç "
        "çıkarmak yanıltıcı olabilir."
    )


def _render_pozisyon_karsilastirma(_cur_user, portfolio):
    """v2.0.7.131 (Bahri'nin talebi, 10 Ağustos 2026): "Portföyümdeki
    varlıkların getirilerini kıyaslayan ikinci bir grafik oluşturalım,
    eğer beğenmezsem kaldırırız" - DENEME özellik. Ana Getiri
    Kıyaslaması'ndan TAMAMEN BAĞIMSIZ, kendi kendine yeten - beğenilmezse
    bu tek fonksiyonu ve çağrı satırını silmek yeterli, başka hiçbir
    yere dokunmaya gerek yok.

    Portföydeki HER POZİSYONUN (dış kıyaslama araçları OLMADAN, sadece
    kendi varlıklar birbirine göre) kendi alış tarihinden bugüne kümülatif
    getirisini ayrı bir çizgi olarak gösterir. Aynı ticker farklı
    tarihlerde birden fazla kez alınmışsa (ör. MTG iki kez), her pozisyon
    kendi çizgisini alır ("MTG", "MTG #2" gibi etiketlenir) - tek bir
    tarihe zorlamak yanıltıcı olurdu.

    v2.0.7.132 - PERFORMANS (Bahri'nin bulgusu, "sistem çok ağırlaşmış"):
    ticker geçmiş verisi artık `_kiyaslama_gunluk_serileri`nin de
    kullandığı PAYLAŞILAN, 5 dakika önbellekli
    `_kiyaslama_ticker_serileri_cek()`'ten geliyor - eskiden bu fonksiyon
    KENDİ ayrı, önbelleksiz kopyasını çekiyordu (Portföyüm sayfasında iki
    grafik = aynı veri 2 kez, hiç önbelleksiz, her widget etkileşiminde
    tekrar tekrar)."""
    if not portfolio:
        return

    import datetime as _dt_pk
    _ticker_seri_pk, _gun_araligi_pk, _baslangic_pk = _kiyaslama_ticker_serileri_cek(portfolio)
    if _ticker_seri_pk is None:
        return

    st.divider()
    st.subheader("Pozisyon Bazlı Getiri Karşılaştırması")
    st.caption(
        "Deneme — portföyünüzdeki her varlığın kendi alış tarihinden "
        "bugüne ayrı getirisi (dış araçlar olmadan, sadece kendi "
        "varlıklarınız birbirine göre)."
    )

    _pozisyon_serileri = {}
    _etiket_sayaci = {}
    for _p in portfolio:
        _tkr = _p.get("ticker")
        _t = _p.get("purchase_date", "")
        if not _t or _tkr not in _ticker_seri_pk:
            continue
        try:
            _alis_tarihi_pk = pd.Timestamp(_dt_pk.date.fromisoformat(_t))
        except Exception:
            continue
        _s = _ticker_seri_pk[_tkr]
        _aktif_pk = _gun_araligi_pk >= _alis_tarihi_pk
        if not _aktif_pk.any():
            continue
        _s_aktif = _s.loc[_aktif_pk]
        if _s_aktif.empty or float(_s_aktif.iloc[0]) <= 0:
            continue
        _getiri_pk = (_s_aktif / float(_s_aktif.iloc[0]) - 1) * 100
        _etiket_sayaci[_tkr] = _etiket_sayaci.get(_tkr, 0) + 1
        _etiket = _tkr if _etiket_sayaci[_tkr] == 1 else f"{_tkr} #{_etiket_sayaci[_tkr]}"
        _pozisyon_serileri[_etiket] = _getiri_pk

    if not _pozisyon_serileri:
        st.info("Pozisyon bazlı karşılaştırma için geçerli veri bulunamadı.")
        return

    import plotly.graph_objects as go
    # v2.0.7.143 (Bahri'nin bulgusu: renkler cok yakindi, asla pastel
    # kullanilmamali) - eski "Bold + Set2" karisimi Set2'nin PASTEL
    # tonlari yuzunden sorunluydu, tamamen kaldirildi. Elle secilmis,
    # renk carkinda maksimum ayrilmis, koyu/doygun (pastel DEGIL) bir
    # liste - kac pozisyon olursa olsun donguyle kullanilir.
    _renk_paleti_pk = [
        "#1d4ed8",  # mavi
        "#b91c1c",  # kirmizi
        "#15803d",  # yesil
        "#b45309",  # amber/turuncu
        "#7e22ce",  # mor
        "#0e7490",  # koyu camgobegi
        "#a21caf",  # macenta
        "#4d7c0f",  # zeytin/koyu sari-yesil
        "#be123c",  # gul/koyu kirmizi
        "#111827",  # neredeyse siyah
    ]
    # v2.0.7.172 (Bahri'nin talebi, 20 Ağustos 2026 — "ikinci grafiği de
    # önceki grafiğe benzer yöntemle daha anlaşılır hale getir"): Ana
    # Getiri Kıyaslaması'nda (v2.0.7.169) kullanılan AYNI iki teknik
    # burada da uygulandı: (1) her çizgi renge EK OLARAK kendine özgü
    # bir DESEN alıyor - pozisyon sayısı SABİT DEĞİL (portföye göre
    # değişir) olduğu için desen döngüsü renk döngüsünden BAĞIMSIZ
    # uzunlukta (6 desen x 10 renk = 60 farklı kombinasyon, aynı
    # kombinasyon 60 pozisyondan önce tekrarlanmaz - gerçekçi bir
    # portföy için fazlasıyla yeterli). (2) Her çizginin SAĞ UCUNA
    # doğrudan etiket ekleniyor - hover'a gerek kalmadan hangi çizginin
    # hangi pozisyon olduğu görülüyor.
    _desen_paleti_pk = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
    fig2 = go.Figure()
    for _i, (_etiket, _seri) in enumerate(_pozisyon_serileri.items()):
        _renk_pk = _renk_paleti_pk[_i % len(_renk_paleti_pk)]
        fig2.add_trace(go.Scatter(
            x=_seri.index, y=_seri.values, mode="lines", name=_etiket,
            line=dict(width=2.75, color=_renk_pk,
                      dash=_desen_paleti_pk[_i % len(_desen_paleti_pk)]),
            hovertemplate="<b>" + _etiket + "</b>: %{y:.2f}%<extra></extra>",
        ))
        fig2.add_annotation(
            x=_seri.index[-1], y=float(_seri.iloc[-1]),
            text=f" {_etiket}", showarrow=False, xanchor="left",
            font=dict(size=11, color=_renk_pk),
        )
    fig2.add_hline(y=0, line_width=1, line_color="rgba(120,120,120,0.4)")
    fig2.update_layout(
        template="plotly_white", height=420,
        # v2.0.7.172: sağ uçtaki etiketlerin sığması için sağ kenar
        # boşluğu artırıldı (10 -> 90) - Ana Getiri Kıyaslaması'yla tutarlı.
        margin=dict(l=10, r=90, t=10, b=10),
        # v2.0.7.143 (Bahri'nin talebi): imleci bir CIZGININ uzerine
        # goturunce SADECE o serinin adi/degeri gorunsun.
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis=dict(title="Kümülatif Getiri", ticksuffix="%",
                   gridcolor="rgba(120,120,120,0.15)", zeroline=False),
        xaxis=dict(gridcolor="rgba(120,120,120,0.08)"),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=13),
    )
    st.plotly_chart(fig2, use_container_width=True)


if page=="Ana Sayfa":
    import time as _t_ana
    _t_ana_basla = _t_ana.perf_counter()
    st.title("Bütçe Optimizasyonu")
    if df_uni.empty:
        st.error("`python worker.py` ile veriyi oluşturun."); st.stop()

    cats=df_uni["Kategori"].value_counts()
    # v2.0.7.42 - "Döviz+Maden" birlesik karti ayri iki karta bolundu
    # (Bahri'nin bulgusu: birlesik etiket, Doviz'in sayiya dahil oldugunu
    # gizliyor, sanki eksikmis gibi goruniyordu - matematiksel olarak
    # eksik degildi, sadece etiket yaniltici sekilde tek kategori gibi
    # okunuyordu).
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("Toplam Varlık",fmt_tr(len(df_uni),0))
    c2.metric("TEFAS",fmt_tr(cats.get('TEFAS',0),0))
    c3.metric("BIST",fmt_tr(cats.get('BIST',0),0))
    c4.metric("Kripto",fmt_tr(cats.get('KRIPTO',0),0))
    c5.metric("Döviz",fmt_tr(cats.get('DOVIZ',0),0))
    c6.metric("Maden",fmt_tr(cats.get('MADEN',0),0))


    # v2.0.7.196 (Bahri'nin bulgusu, 25 Ağustos 2026 — "sayfanın
    # devamı yok burada bitiyor zaten"): KRİTİK YERLEŞİM HATASI
    # BULUNDU VE DÜZELTİLDİ. Bu blok (Onay Bekleyen Otomatik
    # Tespitler + Onaylanan Tespitler) ESKİDEN aşağıda, "if
    # budget<=0: st.stop()" kontrolünden SONRA duruyordu - bütçe
    # girilmemişse (Bahri'nin durumu tam buydu) `st.stop()` TÜM
    # SAYFAYI orada durduruyordu, bu blok DAHİL hiçbir şey
    # çalışmıyordu. Tespit onay/red işlemi bütçe girilip
    # girilmemesinden TAMAMEN BAĞIMSIZ olması gerektiği için, blok
    # bütçe kontrolünden ÖNCEYE taşındı - artık bütçe girilmese bile
    # her zaman görünür.
    if _bekleyen_tespitler:
        st.divider()
        st.markdown("**Onay Bekleyen Otomatik Tespitler**")
        st.caption(
            "Bunlar HENÜZ Optima Skor'a uygulanmadı - sadece onayladığınız "
            "tespitler uygulanır."
        )

        # v2.0.7.194 (Bahri'nin talebi, 25 Ağustos 2026 — "her
        # haberin optima skoruna etki etmesi söz konusu olamaz,
        # bazı kriterler belirlemeliyiz"): TOPLU ONAY - ama SADECE
        # ÜÇ KRİTERİ DE karşılayan tespitler onaylanır, geri kalanı
        # OTOMATİK REDDEDİLİR (skor etkilemez, listeden çıkar).
        # Kriterler: (1) Şiddet="Yüksek", (2) aynı kalıpta FARKLI
        # bir kaynaktan son 24 saatte başka bir tespit var (çoklu
        # kaynak teyidi), (3) kalıbın "istatistiksel_dayanak"
        # bayrağı işaretli (Admin Panel > Kalıp Yönetimi'nden
        # ayarlanır - gerçek akademik/tarihsel dayanağı olan
        # kalıplar: jeopolitik, petrol, fed, kredi_notu,
        # tcmb_kredibilite).
        try:
            from db import get_kaliplar as _gk_toplu, coklu_kaynak_teyidi as _ckt
            _kalip_dayanak_haritasi = {
                k["kalip_key"]: k.get("istatistiksel_dayanak", False)
                for k in _gk_toplu()
            }
        except Exception:
            _kalip_dayanak_haritasi = {}

        def _tespit_kriterleri_karsiliyor_mu(_t):
            if (_t.get("siddet") or "").strip() != "Yüksek":
                return False
            if not _kalip_dayanak_haritasi.get(_t.get("kalip_key"), False):
                return False
            try:
                if not _ckt(_t.get("kalip_key"), _t.get("haber_kaynak", ""), saat=24):
                    return False
            except Exception:
                return False
            return True

        if st.button("Tümünü Onayla (kriterleri karşılayanlar)",
                     key="tumunu_onayla_kriterli"):
            from db import tespit_onayla as _to_toplu, tespit_reddet as _tr_toplu
            _onaylanan_sayisi, _reddedilen_sayisi = 0, 0
            for _t_toplu in _bekleyen_tespitler:
                if _tespit_kriterleri_karsiliyor_mu(_t_toplu):
                    if _to_toplu(_cur_user["id"] if _cur_user else None, _t_toplu["id"]):
                        _onaylanan_sayisi += 1
                else:
                    if _tr_toplu(_cur_user["id"] if _cur_user else None, _t_toplu["id"]):
                        _reddedilen_sayisi += 1
            try:
                _bekleyen_tespitler_onbellekli.clear()
                _onaylanmis_tespitler_onbellekli.clear()
            except Exception:
                st.cache_data.clear()
            st.success(
                f"{_onaylanan_sayisi} tespit kriterleri karşıladığı için "
                f"onaylandı, {_reddedilen_sayisi} tespit kriterleri "
                f"karşılamadığı için otomatik reddedildi.")
            st.rerun()
        st.caption(
            "Kriterler: Şiddet=Yüksek + son 24 saatte farklı bir "
            "kaynaktan teyit + kalıbın istatistiksel dayanağı olması "
            "(Admin Panel'den ayarlanır). Karşılamayanlar otomatik "
            "reddedilir, skoru etkilemez.")

        for _tespit in _bekleyen_tespitler:
            _tk2 = _tespit["kalip_key"]
            _kalip_adi_gosterim = _KALIP_ISIM.get(_tk2, _tk2)
            with st.container(border=True):
                # v2.0.7.157 (Bahri'nin talebi): AI'nin ürettiği doğal
                # cümle ("[Kaynak]'a göre, ... bu durumda ... Optima
                # Skorlarını artırmamız/azaltmamız gerekir") artık
                # ANA MESAJ olarak, teknik bir "AI gerekçesi:" etiketi
                # ARKASINDA gizlenmeden, doğrudan gösteriliyor.
                _dogal_cumle = _tespit.get('ai_gerekce', '') or (
                    f"{_kalip_adi_gosterim} kalıbı tespit edildi.")
                # v2.0.7.215: modal dialogdaki AYNI cok-kaynakli cumle
                # donusumu - tutarlilik icin (bkz. o yorum).
                _dogal_cumle = _cok_kaynakli_cumle_olustur(
                    _dogal_cumle, _tespit.get('haber_kaynak'), _tespit.get('teyit_listesi'))
                st.markdown(f"{_dogal_cumle} **Onaylıyor musunuz?**")
                # v2.0.7.195: modal dialogdaki AYNI rozet stili -
                # tutarlılık için (bkz. o yorum).
                _sdt2 = _tespit.get('siddet', 'Orta')
                _sr2 = {"Yüksek": "#b91c1c", "Orta": "#b45309", "Düşük": "#6b7280"}.get(_sdt2, "#6b7280")
                st.markdown(
                    f"""<div style="background:#f3f4f6;border-left:4px solid {_sr2};
                         border-radius:6px;padding:8px 12px;margin:4px 0;font-size:14px;">
                         <b>Kalıp:</b> {_kalip_adi_gosterim} &nbsp;·&nbsp;
                         <b>Önerilen şiddet:</b> <span style="color:{_sr2};font-weight:700;">{_sdt2}</span></div>""",
                    unsafe_allow_html=True)
                # v2.0.7.215: modal dialogdaki AYNI numarali kaynak
                # gosterimi - tutarlilik icin (bkz. o yorum).
                _kaynak_bolumu_goster(_tespit)
                _oc1, _oc2, _oc3 = st.columns([1, 1, 4])
                with _oc1:
                    if st.button("Onayla", key=f"tespit_onay_{_tespit['id']}"):
                        try:
                            from db import tespit_onayla
                            _basarili_ah = tespit_onayla(_cur_user["id"] if _cur_user else None, _tespit["id"])
                        except Exception as _onay_err:
                            st.error(f"Onaylanamadı: {_onay_err}")
                        else:
                            if _basarili_ah:
                                # v2.0.7.193: GENEL st.cache_data.clear()
                                # yerine SADECE bu iki kucuk tespit
                                # onbellegi temizleniyor - modal
                                # dialogdaki v2.0.7.193 duzeltmesiyle
                                # AYNI sebep/cozum (bkz. o yorum).
                                try:
                                    _bekleyen_tespitler_onbellekli.clear()
                                    _onaylanmis_tespitler_onbellekli.clear()
                                except Exception:
                                    st.cache_data.clear()
                                st.success("Onaylandı, Optima Skor'a uygulanacak.")
                                st.rerun()
                            else:
                                st.error(
                                    "Onaylanamadı - veritabanı yazması "
                                    "başarısız oldu. Tekrar deneyin.")
                with _oc2:
                    if st.button("Reddet", key=f"tespit_red_{_tespit['id']}"):
                        try:
                            from db import tespit_reddet
                            _basarili_rh = tespit_reddet(_cur_user["id"] if _cur_user else None, _tespit["id"])
                        except Exception as _red_err:
                            st.error(f"Reddedilemedi: {_red_err}")
                        else:
                            if _basarili_rh:
                                try:
                                    _bekleyen_tespitler_onbellekli.clear()
                                    _onaylanmis_tespitler_onbellekli.clear()
                                except Exception:
                                    st.cache_data.clear()
                                st.info("Reddedildi, bir daha gösterilmeyecek.")
                                st.rerun()
                            else:
                                st.error(
                                    "Reddedilemedi - veritabanı yazması "
                                    "başarısız oldu. Tekrar deneyin.")

    if _beklenti_ayarlar:
        st.divider()
        # v2.0.7.158: manuel işaretleme kaldırıldığı için kaynak ayrımı
        # (elle/otomatik) da anlamsızlaştı - buradaki her satır artık
        # kullanıcının ONAYLADIĞI bir otomatik tespittir.
        st.markdown("**Onayladığınız Tespitler ve Gerekçeleri**")
        for _kalip_key, _siddet in _beklenti_ayarlar.items():
            st.markdown(
                f"**{_KALIP_ISIM[_kalip_key]}** ({_siddet} şiddet): "
                f"{_KALIP_ACIKLAMA[_kalip_key]}"
            )
        st.caption(
            "Yukarıdaki yön ve büyüklük ilişkileri, tek bir olaya değil, "
            "onlarca yıl ve çok sayıda olayı kapsayan akademik panel/olay "
            "çalışmalarına (event study) dayanır — ama gelecekteki her "
            "olay öncekilerle birebir aynı büyüklükte gerçekleşmez, bu "
            "istatistiksel bir eğilimdir, kesin bir tahmin değildir. "
            "Otomatik tespitler SİZ ONAYLAMADAN asla uygulanmaz. "
            "Yatırım tavsiyesi değildir."
        )

    if budget<=0:
        st.info("Sol panelden **Bütçe** girerek optimize edilmiş öneri listesini görün.")
        st.stop()

    w=RISK_W[risk]
    st.subheader(f"Önerilen Dağılım — {fmt_tr(budget,0)} ₺  |  Risk: {risk}  |  Max: {max_assets} varlık")
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
            _t_bist0 = _t_ana.perf_counter()
            df_uni = _ld_refresh_bist_sel(df_uni, _bist_aday["Ticker"].tolist())
            print(f"[timing][AnaSayfa] BIST canli yenileme (40 ticker): "
                  f"{_t_ana.perf_counter() - _t_bist0:.3f}s")

    cat_pools = {}
    _t_pool0 = _t_ana.perf_counter()
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
    print(f"[timing][AnaSayfa] Kategori havuzu skorlama (tum kategoriler): "
          f"{_t_ana.perf_counter() - _t_pool0:.3f}s")

    # 2. Adım: Slot dağıtımı — TÜM havuzdan en yüksek skorlu max_assets varlık
    #
    # v2.0.7.95 - KRITIK DUZELTME (Bahri'nin talebi, 19 Temmuz 2026, PEPE/
    # ETHFI/ALLO/ILU ornegi): v2.0.7.94'te bu mantik SADECE max_assets <
    # kategori_sayisi (5) iken uygulanmisti - max_assets=4 iken 3 tane
    # Kripto (80,0) + ILU (78,7) dogru seciliyordu, ama max_assets=5 olunca
    # (5 < 5 YANLIS oldugu icin) ESKI "her kategoriye en az 1 slot" mantigina
    # GERI DONULUYORDU - Kripto'nun 2 tane 80,0 puanli varligi (ETHFI, ALLO)
    # sirf "her kategoriye pay" kurali yuzunden elenip, yerlerine DAHA DUSUK
    # puanli BIST/Doviz varliklari (ISGYO 70,0, ZARTRY 66,7) zorla ekleniyordu.
    # Bahri'nin acik karari: "her zaman en iyi skor kazansin, kategori
    # cesitlendirme garantisi TAMAMEN kalksin" - artik max_assets'in
    # kategori sayisiyla karsilastirilmasi YOK, HER DURUMDA (Max Varlik
    # Sayisi ne olursa olsun) tum havuzlardan objektif olarak en yuksek
    # Optima_Skor'lu max_assets varlik dogrudan secilir. Eski "esit
    # bolusum + kalite bazli acik/dolu slot transferi" mantigi (v2.0.7.65
    # ve oncesi) TAMAMEN KALDIRILDI - artik gereksiz, cunku secim zaten
    # gercek havuzdan yapildigindan bir kategorinin kapasitesini asma
    # riski hic olusmaz.
    _tum_havuz = pd.concat(
        [df.assign(_Kategori=c) for c, df in cat_pools.items()],
        ignore_index=True
    ).sort_values("Optima_Skor", ascending=False)
    _secilenler = _tum_havuz.head(max_assets)
    slots = {c: 0 for c in cat_pools}
    for _cat, _grp in _secilenler.groupby("_Kategori"):
        slots[_cat] = len(_grp)

    max_per_cat_map = slots

    # Kalite bazlı ağırlık — kategori ortalama skoruna göre düzelt
    adj_weights = {}
    total_adj = 0.0
    for cat, weight in w.items():
        if cat not in cat_pools:
            continue
        mpc = max_per_cat_map.get(cat, 1)
        # v2.0.7.94 - GUVENLIK (global-secim mantigindan sonra bazi
        # kategoriler mpc=0 alabilir - bos bir Optima_Skor serisinin
        # .mean()'i NaN doner, bu NaN total_adj'a sizip TUM agirliklari
        # bozardi. mpc<=0 olan kategoriyi tamamen atla.
        if mpc <= 0:
            continue
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
    print(f"[timing][AnaSayfa] Sayfa basindan oneri listesi hazir olana kadar TOPLAM: "
          f"{_t_ana.perf_counter() - _t_ana_basla:.3f}s")

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
    #
    # v2.0.7.92 - KRITIK GUVENLIK FRENI (Bahri'nin bulgusu, 19 Temmuz 2026):
    # Bu donguye eskiden hicbir ust sinir yoktu. Secili varliklardan biri
    # asiri dusuk fiyatliysa (orn. bazi genisleme dovizleri - IDR gibi -
    # 1 birimi bir kurusun cok altinda olabilir), kalan butceyi o fiyata
    # bolup tuketmek MILYONLARCA iterasyon gerektirebilir - hata vermeden,
    # sessizce, etkin olarak SURESIZ calisir. Artik hem TOPLAM ITERASYON
    # SAYISI (100.000) hem DUVAR SAATI SURESI (5 saniye) icin sert bir
    # tavan var - ikisinden biri asilirsa dongu GUVENLI sekilde durur,
    # o ana kadar dagitilmis olan kismi sonuc kullanilir (hic cokme/askida
    # kalma olmaz).
    if opt_rows:
        import time as _time_guard
        _dongu_baslangic = _time_guard.time()
        _iterasyon_sayaci = 0
        _MAKS_ITERASYON = 100_000
        _MAKS_SURE_SN = 5.0
        _kalan_butce = budget - sum(r["Tutar (₺)"] for r in opt_rows)
        _skor_sirali = sorted(
            [r for r in opt_rows if r.get("_gercek_fiyat")],
            key=lambda r: -r["Optima Skoru"])
        _ilerleme = True
        _guvenlik_frenine_takildi = False
        while _kalan_butce > 0.01 and _ilerleme and _skor_sirali:
            _ilerleme = False
            for r in _skor_sirali:
                _fiyat = r["Emir Fiyatı"]
                if _fiyat > 0 and _fiyat <= _kalan_butce:
                    r["Birim"] += 1
                    r["Tutar (₺)"] = round(r["Tutar (₺)"] + _fiyat, 2)
                    _kalan_butce = round(_kalan_butce - _fiyat, 2)
                    _ilerleme = True
                _iterasyon_sayaci += 1
                if (_iterasyon_sayaci >= _MAKS_ITERASYON or
                        _time_guard.time() - _dongu_baslangic > _MAKS_SURE_SN):
                    _guvenlik_frenine_takildi = True
                    break
            if _guvenlik_frenine_takildi:
                break

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
                    pg1.metric("Tahmini Yıllık Pasif Gelir", f"{fmt_tr(toplam_gelir)} ₺")
                    pg2.metric("Aylık Gelir (~)", f"{fmt_tr(toplam_gelir/12)} ₺")
                    pg3.metric("Bütçeye Oranı",
                               f"{fmt_tr(toplam_gelir/budget*100)}%" if budget > 0 else "—")
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
        # v2.0.7.60 - KRITIK DUZELTME (Bahri'nin bulgusu): bu sozluk
        # clickable_table()'a col_cfg olarak veriliyor ve auto_cfg.update()
        # ile onun Turkce TextColumn ayarlarinin USTUNE yaziyordu - bu
        # yuzden clickable_table'i duzeltmis olmama ragmen Ana Sayfa hala
        # Ingilizce NumberColumn format="%.1f" gibi spec'ler gosteriyordu.
        # Artik Turkce'ye cevrilen sutunlarda format belirtilmiyor (sadece
        # genislik), TextColumn kullaniliyor - deger zaten clickable_table
        # icinde Turkce metne cevrilmis oluyor.
        col_cfg_ana = {
            "Kategori": st.column_config.TextColumn("Kategori", width="small"),
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Optima Skoru": st.column_config.TextColumn("Optima Skoru", width="small", alignment="right"),
            "Sinyal": st.column_config.TextColumn("Sinyal", width="small"),
            "RSI": st.column_config.TextColumn("RSI", width="small", alignment="right"),
            "1A Getiri %": st.column_config.TextColumn("1A Getiri %", width="small", alignment="right"),
            "Emir Fiyatı": st.column_config.TextColumn("Emir Fiyatı", width="small", alignment="right"),
            "Birim": st.column_config.NumberColumn("Birim", format="%d", width="small"),
            "Tutar (₺)": st.column_config.TextColumn("Tutar (₺)", width="small", alignment="right"),
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
            f"{fmt_tr((_toplam_gercek/budget*100 if budget>0 else 0),1)}%</b>"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;Toplam Tutar: <b style='color:#1b2a4a;'>{fmt_tr(_toplam_gercek)} ₺</b>"
            f"</span></div>",
            unsafe_allow_html=True
        )

        # v2.0.7.93 - KALICI ACIKLAMA, SADECE EKSIK OLDUGUNDA (Bahri'nin
        # talebi, 19 Temmuz 2026: "sadece bu durum bir daha gerceklesirse
        # not ciksin istemistim" - basari durumunda HICBIR SEY gosterme,
        # onceki surumde yanlislikla her zaman gosteriyordum). Bir kategori
        # uygun fiyatli/sinyalli varlik bulamadiginda, istenen "Max Varlik
        # Sayisi"ndan daha az varlik onerilir - abonelerin sohbette
        # aciklayacak biri olmadan "neden 10 istedim 8 geldi" sorusuna
        # kendi basina cevap bulabilmesi icin SADECE bu durumda bir not
        # gosterilir.
        _teslim_edilen = len(df_opt)
        if _teslim_edilen < max_assets:
            _eksik_kategoriler = sorted(set(elenen) | set(karsilanamayan_kategoriler))
            _kategori_metni = (f" ({', '.join(_eksik_kategoriler)} kategorisinde/lerinde "
                               f"uygun fiyatlı/sinyalli varlık bulunamadığı için)"
                               if _eksik_kategoriler else "")
            st.caption(
                f"İstenen varlık sayısı **{max_assets}**, önerilen **{_teslim_edilen}**"
                f"{_kategori_metni}. Sistem, boş kalan slotları uygun olmayan bir "
                f"varlıkla zorla doldurmaz — bütçeyi artırmak veya Max Varlık "
                f"Sayısı'nı azaltmak bu durumu çözebilir."
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
                    # v2.0.7.71 - KRITIK DUZELTME (Bahri'nin bulgusu, BGNTRY
                    # ornegi): v2.0.7.69'daki "_gecmis_veri_yok" duzeltmesi
                    # SADECE liste/tablo gorunumunun yerel kopyasina (df_cat)
                    # uygulanmisti - sel_row_ana ise DUZELTILMEMIS df_uni'den
                    # okundugu icin bu Detay sayfasi hala eski (yanlis
                    # yuksek) skoru gosteriyordu. Ayni Son_Fiyat kontrolu
                    # gibi burada da acikca tekrarlaniyor.
                    # v2.0.7.77 - bkz. live_optima_score()'daki ayni not:
                    # bool(NaN)==True oldugu icin TEFAS/BIST/KRIPTO burada
                    # yanlislikla hep 0 gosteriyordu - "== True" ile duzeltildi.
                    if sel_row_ana.get("_gecmis_veri_yok") == True:
                        disp_score_ana = 0.0
                    sig_lbl, sig_cls = get_signal(disp_score_ana, d["rsi"], d["trend"])

                r1,r2,r3,r4,r5 = st.columns(5)
                r1.metric("Son Fiyat",    fmt_tr(float(sel_row_ana['Son_Fiyat']),4))
                r2.metric("Optima Skor",  fmt_tr(disp_score_ana,1))
                r3.metric("RSI (14)",     fmt_tr(d['rsi'],1))
                r4.metric("1A Getiri %",  fmt_tr_isaretli(d['ret1m'],2,yuzde=True))
                r5.metric("Yillik Vol %", fmt_tr(d['vol'],1)+"%")

                    # v2.0.7.153 (Bahri'nin talebi, 18 Agustos 2026): tekil varlik
                    # skor bilesimi grafigi simdilik kaldirildi (fonksiyon tanimi
                    # duruyor, farkli bir grafik sekliyle - 3D SVG - istenirse
                    # kolayca geri eklenebilir).

                sig_color = SIG_COLORS.get(sig_cls, "#666")

                # v2.0.3: Hacim trendi bilgisi (varsa)
                _vol_html_ana = ""
                if d.get("vol_trend", "YOK") != "YOK":
                    _vt = d["vol_trend"]
                    _vr = d.get("vol_ratio", 0.0)
                    _adj = d.get("score_adj", 0)
                    # v2.0.7.109 (Bahri'nin talebi, BULGS ornegi, 30 Temmuz
                    # 2026): v2.0.7.108'de TEK renk (skor isaretine gore) hem
                    # hacim yazisina hem skora uygulanmisti. Bahri "hacim
                    # ARTIYOR yazisi yesil olmali (yon oldugu gibi kalsin),
                    # skor kendi isaretiyle (-3 ise kirmizi) ayri boyansin"
                    # dedi - haklı, ikisi farkli seyi anlatiyor (biri ham
                    # hacim yonu, biri o yonun O TREND baglamindaki etkisi).
                    # Artik IKI AYRI renk: hacim yazisi yon bazli (ARTIYOR=
                    # yesil/AZALIYOR=kirmizi, oldugu gibi), skor kendi
                    # isaretine gore (pozitif=yesil/negatif=kirmizi).
                    _vol_clr = {"ARTIYOR": "#27ae60", "AZALIYOR": "#e74c3c", "NORMAL": "#7f8c8d"}.get(_vt, "#7f8c8d")
                    _adj_clr = "#27ae60" if _adj > 0 else ("#e74c3c" if _adj < 0 else "#7f8c8d")
                    _adj_str = f" <b style='color:{_adj_clr}'>({_adj:+d} skor)</b>" if _adj != 0 else ""
                    _vol_html_ana = (
                        f' | Hacim: <b style="color:{_vol_clr}">{_vt}</b> '
                        f'<small>(5g/20g = {fmt_tr(_vr,2)})</small>{_adj_str}'
                    )

                # v2.0.3.2: Max DD cezasi bilgisi
                _dd_html_ana = ""
                if d.get("dd_adj", 0) != 0:
                    _dd_val = d.get("max_dd")
                    _dd_clr = "#e74c3c"
                    _dd_html_ana = (
                        f' | Max DD: <b style="color:{_dd_clr}">{fmt_tr(_dd_val,1)}%</b> '
                        f'<b style="color:{_dd_clr}">({d["dd_adj"]:+d} skor)</b>'
                    )

                st.markdown(f"""
                <div class="ts-card" style="border-left:5px solid {sig_color};padding:12px 18px;">
                  <span class="ts-sig {sig_cls}">{sig_lbl}</span>
                  <span style="color:#6c7a9c;font-size:12px;margin-left:14px">
                    Trend: <b>{d['trend']}</b> &nbsp;|&nbsp;
                    Optima Skor: <b>{disp_score_ana}/100</b> &nbsp;|&nbsp;
                    MACD: <b>{fmt_tr(d['macd'],4)}</b>{_vol_html_ana}{_dd_html_ana}
                  </span>
                </div>""", unsafe_allow_html=True)

                # v2.0.3.2: Teknik Gostergeler expander
                render_teknik_gostergeler(d, float(sel_row_ana["Son_Fiyat"]))

                if not d["hist"].empty:
                    fig = candle_fig(d["hist"], sel_ana)
                    if fig: st.plotly_chart(fig, width='stretch')
                else:
                    st.warning(f"{sel_ana} icin gecmis fiyat verisi yuklenemedi.")

                # BIST ise temel analiz
                if cat_ana == "BIST":
                    st.divider()
                    st.subheader("Temel Analiz")
                    try:
                        from kap_client import (fetch_kap_fundamentals,
                                                fundamentals_to_display,
                                                get_kap_url)
                        kap_url = get_kap_url(sel_ana)
                        with st.spinner("Temel veriler yukleniyor..."):
                            raw  = fetch_kap_fundamentals(sel_ana)
                            disp = fundamentals_to_display(raw)
                        pb = raw.get("pb_ratio"); pe = raw.get("pe_ratio")
                        dy = raw.get("div_yield")
                        # v2.0.7.79 (Bahri'nin talebi, YAYLA ornegi): Skor
                        # Bilesimi paneli artik Master Skor'u BELIRLEYEN
                        # AYNI fonksiyonlari kullanir - eskiden ekranda
                        # gorunen "Teknik Skor" _d['score'] (0-100'e
                        # normalize edilmis, DD/hacim dahil) idi ama "/70"
                        # etiketliydi; "Temel Skor" da Master Skor'u hic
                        # etkilemeyen ayri bir formuldu (kap_client.
                        # score_from_fundamentals). Ikisi de artik tek
                        # kaynaktan (_teknik_alt_skor/_temel_alt_skor).
                        #
                        # v2.0.7.105 - KRITIK DUZELTME (Bahri'nin bulgusu,
                        # AKSEN ornegi, 29 Temmuz 2026): Teknik/Temel skorlar
                        # CANLI (bu sayfa acilirken enrich()'in dondurdugu
                        # anlik RSI/Ret1M/Vol + tam simdi KAP'tan cekilen
                        # PB/PE/DY) ile hesaplaniyordu, ama Master Skor
                        # asagida CSV'deki (worker.py'nin GECE hesapladigi,
                        # hacim/DD ayari zaten gomulu) Optima_Skor'u
                        # kullaniyordu. Iki farkli anda, iki farkli
                        # kaynaktan hesaplanan sayilar yan yana konunca
                        # "54+9=63 ama Master Skor 68" gibi aciklanamayan
                        # farklar ortaya cikiyordu (54+9 CANLI, 68 GECEDEN
                        # DONDURULMUS). Artik: CSV'de Optima_Skor varsa
                        # Teknik/Temel de AYNI CSV satirinin dondurulmus
                        # RSI/Ret1M/Vol/PB/PE/DY degerlerinden hesaplanir -
                        # boylece uc sayi da HER ZAMAN ayni anin/kaynagin
                        # urunu olur. (Hacim/DD ayari GECE'den Optima_Skor'a
                        # gomulu oldugu icin Teknik+Temel toplami, Master
                        # Skor'dan o ayar kadar farkli GORUNEBILIR - bu artik
                        # celiskili degil, sadece ayri bir katman.)
                        _precomp = sel_row_ana.get("Optima_Skor")
                        if _precomp is not None and _precomp == _precomp:
                            combined = float(_precomp)
                            _csv_rsi  = _csv_alan(sel_row_ana, "RSI")
                            _csv_ret1m = _csv_alan(sel_row_ana, "Ret1M")
                            _csv_vol  = _csv_alan(sel_row_ana, "Vol")
                            _csv_pb   = _csv_alan(sel_row_ana, "PB")
                            _csv_pe   = _csv_alan(sel_row_ana, "PE")
                            _csv_dy   = _csv_alan(sel_row_ana, "DY")
                            teknik_skor = _teknik_alt_skor(
                                _csv_rsi if _csv_rsi is not None else 50.0,
                                _csv_ret1m if _csv_ret1m is not None else 0.0,
                                _csv_vol if _csv_vol is not None else 30.0)
                            fund_skor = _temel_alt_skor(_csv_pb, _csv_pe, _csv_dy)
                            # v2.0.7.107 (Bahri'nin talebi): hacim/DD ayari
                            # artik Teknik Skor'un icine katlaniyor - ayri,
                            # gorunmez bir katman olarak kalmiyor. Ayarin
                            # kendisi CSV'deayri saklanmadigindan, artik
                            # (Master Skor - Teknik - Temel) FARKI olarak
                            # geri turetiliyor - bu fark matematiksel olarak
                            # TAM OLARAK worker.py'nin uyguladigi hacim/DD
                            # ayarina esittir (bkz. ATATP dogrulamasi,
                            # 30 Temmuz 2026: 43+17=60, Master=65,
                            # fark=+5 = "Hacim: ARTIYOR (+5 skor)" rozetiyle
                            # birebir tutuyordu).
                            teknik_skor = teknik_skor + (combined - teknik_skor - fund_skor)
                        else:
                            teknik_skor = _teknik_alt_skor(d["rsi"], d["ret1m"], d["vol"])
                            fund_skor = _temel_alt_skor(pb, pe, dy)
                            tech_with_fund = optima_score(d["rsi"], d["ret1m"], d["vol"], True, pb, pe, dy)
                            _total_adj = d.get("total_adj", d.get("score_adj", 0))
                            teknik_skor = teknik_skor + _total_adj
                            combined = max(0, min(100, round(tech_with_fund + _total_adj, 1)))
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
                            <small style='color:#6c7a9c'>Teknik Skor (RSI + Momentum + Vol + Hacim/DD)</small><br>
                            <b style='font-size:20px;color:#1b2a4a'>{fmt_tr(teknik_skor,1)} / 75</b><br><br>
                            <small style='color:#6c7a9c'>Temel Skor (F/K + PD/DD + Temettu)</small><br>
                            <b style='font-size:20px;color:#1b2a4a'>{fmt_tr(fund_skor,1)} / 25</b><br>
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

        def _3d_pasta_svg(etiketler, degerler, renkler, baslik="Kategori Dağılımı", genislik=700, yukseklik=410, baslangic_aci=-90.0):
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

            acilar, basla = [], baslangic_aci
            for v in degerler:
                bit = basla + (v/toplam)*360.0
                acilar.append((basla, bit))
                basla = bit
            # v2.0.7.145 (Bahri'nin bulgusu, 18 Ağustos 2026): tek bir
            # kategori %100 olduğunda (ör. portföy tamamen TEFAS), bu
            # dilimin başlangıç açısı (-90°) ile bitiş açısı (270°) AYNI
            # NOKTAYA denk geliyordu (270° = -90°+360° aynı koordinat).
            # SVG standardına göre bir yayın başlangıç/bitiş noktaları
            # aynıysa o yay TAMAMEN ATLANIR (görünmez olur) - sadece
            # <text> etiketleri (başlık, "TEFAS", "%100,0") kalıyordu,
            # dilimin kendisi hiç çizilmiyordu. Düzeltme: herhangi bir
            # dilimin açısal genişliği 359,99°'yi geçemez - matematiksel
            # olarak görünmez fark ama SVG'nin "aynı nokta" kenar durumunu
            # kesin olarak önler.
            acilar = [(a0, min(a1, a0 + 359.99)) for (a0, a1) in acilar]

            dilimler = []
            for i, ((a0, a1), renk) in enumerate(zip(acilar, renkler)):
                orta = (a0+a1)/2.0
                dilimler.append(dict(i=i, a0=a0, a1=a1, orta=orta, renk=renk))

            sirali = sorted(dilimler, key=lambda w: math.sin(math.radians(w["orta"])))

            parcalar = [f'<svg viewBox="0 0 {genislik} {yukseklik}" width="100%" '
                        f'xmlns="http://www.w3.org/2000/svg" style="font-family:Segoe UI,Arial,sans-serif;">']
            parcalar.append(f'<text x="{genislik/2:.1f}" y="26" font-size="15" font-weight="700" fill="#1b2a4a" text-anchor="middle">{_html_esc(baslik)}</text>')

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
                                 f'<title>{etiketler[w["i"]]}: %{fmt_tr(degerler[w["i"]]/toplam*100,1)}</title></path>')


            # v2.0.7.147 (Bahri'nin bulgusu, 18 Ağustos 2026 — Optima Skor
            # Bileşimi'nde 6 dilim olunca komşu küçük dilimlerin etiketleri
            # üst üste biniyordu, ör. "Temettü Verimi %0,0" ile "PD/DD
            # %6,0"): sabit yarıçaplı etiket yerleşimi, açısal olarak
            # birbirine YAKIN dilimlerde (özellikle küçük/komşu dilimler)
            # çakışmaya açıktı - Kategori Dağılımı'nda nadiren sorun
            # olmuyordu çünkü orada genelde 2-3, az sayıda ve büyük dilim
            # var. Bu artık DEĞERLERDEN BAĞIMSIZ, sağlam bir sistem: açıya
            # göre sıralanmış etiketler arasında 28°'den DAR açısal boşluk
            # varsa "sıkışık" sayılır ve bu etiket bir sonraki (daha uzak)
            # yarıçap kademesine itilir - kademeler dönüşümlü olarak
            # yakın/uzak arasında geçiş yapar, kaç dilim/hangi değerler
            # olursa olsun otomatik uyum sağlar. Uzak kademedeki etiketler
            # için dilime geri bağlayan ince bir çizgi eklendi, hangi
            # dilime ait olduğu belirsiz kalmasın diye.
            _sirali_acilar = sorted(dilimler, key=lambda w: w["orta"] % 360)
            _esik_derece = 28.0
            _kademe_haritasi, _son_aci_kademe, _kademe_simdi = {}, None, 0
            for w in _sirali_acilar:
                _bu_aci = w["orta"] % 360
                if _son_aci_kademe is not None and (_bu_aci - _son_aci_kademe) % 360 < _esik_derece:
                    _kademe_simdi = (_kademe_simdi + 1) % 2
                else:
                    _kademe_simdi = 0
                _kademe_haritasi[w["i"]] = _kademe_simdi
                _son_aci_kademe = _bu_aci

            for w in dilimler:
                rad = math.radians(w["orta"])
                # v2.0.4.31: On/alt (front-facing, sin(orta)>0) dilimlerin

                # etiketleri pastanin govdesiyle cakisiyordu, cunku o
                # bolgede govde derinlik kadar daha asagiya taşiyor ama
                # eski formul sabit bir miktar YUKARI cekiyordu (tam ters
                # yönde). Şimdi on tarafa dogru orantili ek boşluk ekleniyor.
                _kademe_bu = _kademe_haritasi.get(w["i"], 0)
                _yaricap_carpani = 1.30 + _kademe_bu * 0.26
                lx = cx0 + math.cos(rad)*(rx*_yaricap_carpani)
                ly = cy0 + math.sin(rad)*(ry*_yaricap_carpani) + derinlik*max(0.0, math.sin(rad))*1.3
                yuzde = degerler[w["i"]]/toplam*100
                hiza = "start" if math.cos(rad) >= 0 else "end"
                if _kademe_bu > 0:
                    _bag_x0 = cx0 + math.cos(rad)*(rx*1.02)
                    _bag_y0 = cy0 + math.sin(rad)*(ry*1.02) + derinlik*max(0.0, math.sin(rad))*1.3
                    parcalar.append(f'<line x1="{_bag_x0:.1f}" y1="{_bag_y0:.1f}" x2="{lx:.1f}" y2="{ly-4:.1f}" '
                                     f'stroke="#b7c3d9" stroke-width="1"/>')
                parcalar.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="12.5" fill="#1b2a4a" '
                                 f'text-anchor="{hiza}" font-weight="600">{_html_esc(etiketler[w["i"]])}</text>')
                parcalar.append(f'<text x="{lx:.1f}" y="{ly+15:.1f}" font-size="11.5" fill="#5a6a8a" '
                                 f'text-anchor="{hiza}">%{fmt_tr(yuzde,1)}</text>')

            parcalar.append("</svg>")
            return "".join(parcalar)

        import html as _html_mod
        _html_esc = _html_mod.escape

        # v2.0.7.146 (Bahri'nin talebi, 18 Ağustos 2026): "Optima skor
        # bileşimi pasta grafiğini herhangi bir varlığa tıklanmadan,
        # Kategori Dağılımı ile yan yana görmek istiyorum" - önerilen
        # SEPETTEKİ TÜM varlıkların skor bileşimini (Tutar'a göre
        # ağırlıklı ortalama), Kategori Dağılımı ile AYNI 3D SVG
        # tarzında, yan yana gösteriyor. Tek bir varlığa tıklamaya HİÇ
        # gerek yok - "neden bu sepeti önerdik" sorusunun toplu cevabı.
        _agirlikli_bilesim = {}
        _toplam_agirlik_bilesim = 0.0
        for _, _or in df_opt.iterrows():
            _tkr_o = _or.get("Ticker")
            _agirlik_o = float(_or.get("Tutar (₺)", 0) or 0)
            if _agirlik_o <= 0:
                continue
            _match_o = df_uni[df_uni["Ticker"] == _tkr_o]
            if _match_o.empty:
                continue
            _row_o = _match_o.iloc[0]
            _pb_o, _pe_o, _dy_o = _row_o.get("PB"), _row_o.get("PE"), _row_o.get("DY")
            _has_fund_o = any(
                v is not None and str(v) != "nan" and float(v or 0) > 0
                for v in (_pb_o, _pe_o, _dy_o))
            _parcalar_o = optima_score_breakdown(
                float(_or.get("RSI", 50) or 50), float(_or.get("1A Getiri %", 0) or 0),
                vol=float(_row_o.get("Vol", 30) or 30), has_fundamental=_has_fund_o,
                pb=_pb_o, pe=_pe_o, dy=_dy_o)
            _toplam_agirlik_bilesim += _agirlik_o
            for _k_o, _v_o in _parcalar_o.items():
                _agirlikli_bilesim[_k_o] = _agirlikli_bilesim.get(_k_o, 0.0) + _v_o * _agirlik_o

        _kg_col, _sk_col = st.columns(2)
        with _kg_col:
            st.markdown(_3d_pasta_svg(cat_sum["Kategori"].tolist(),
                                        cat_sum["Tutar (₺)"].tolist(),
                                        colors, baslik="Kategori Dağılımı"), unsafe_allow_html=True)
        with _sk_col:
            # v2.0.7.147 (Bahri'nin bulgusu): sıfıra yuvarlanan bileşenler
            # (ör. "Temettü Verimi %0,0") sıfır genişlikte bir dilim
            # yaratıp komşusuyla aynı noktada çakışıyordu (tek varlık
            # pasta grafiğindeki %100 hatasıyla AYNI kök sınıf) - artık
            # 0'a yuvarlanan bileşenler grafiğe hiç dahil edilmiyor.
            _bilesim_ham = {k: v / _toplam_agirlik_bilesim for k, v in _agirlikli_bilesim.items()} \
                if _toplam_agirlik_bilesim > 0 else {}
            _bilesim_ham = {k: v for k, v in _bilesim_ham.items() if round(v, 1) > 0}
            if _bilesim_ham:
                _bilesim_etiket = list(_bilesim_ham.keys())
                _bilesim_deger = [round(v, 1) for v in _bilesim_ham.values()]
                _bilesim_renk_harita = {
                    "RSI Bölgesi": "#1d4ed8", "Momentum": "#15803d", "Volatilite": "#b45309",
                    "F/K": "#7e22ce", "PD/DD": "#a21caf", "Temettü Verimi": "#0e7490",
                }
                _bilesim_renkler = [_bilesim_renk_harita.get(k, "#6b7280") for k in _bilesim_etiket]
                st.markdown(_3d_pasta_svg(_bilesim_etiket, _bilesim_deger, _bilesim_renkler,
                                            baslik="Bütçe Sepetinin Optima Skor Bileşimi",
                                            baslangic_aci=-180.0),
                           unsafe_allow_html=True)
            else:
                st.caption("Skor bileşimi için yeterli veri yok.")

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
            # Sikkeler ve diger madenler (Bakir vb.) -> Adet
            return "Adet"
        # v2.0.7.113 (Bahri'nin bulgusu, ILU fon ornegi, 31 Temmuz 2026):
        # TEFAS fonlari "Adet" degil "Pay" birimiyle islem gorur (TEFAS'ta
        # katilma payi denir). Onceden "Adet" varsayilandi - yanlisti.
        if k == "TEFAS":
            return "Pay"
        # KRIPTO, DOVIZ ve digerleri -> Adet
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
                    _unit_opts = ["Adet","Pay","Gram","Lot","Ons","Varil","Ton","kg","m²","Diğer"]
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
                if st.button("EKLE", width='stretch', key="pf_ekle"):
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
        _render_sermaye_nakit_ozeti(_cur_user, portfolio, 0.0)
        _render_gerceklesmis_kar_zarar(_cur_user)
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
        _kz_pct = round(((_guncel/_alis-1)*100) if _alis>0 else 0.0, 2)

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
            "_asset_type":  pos.get("asset_type","BIST") or "BIST",
            "_purchase_date_raw": _traw,
        })

    import pandas as _pd2
    df_pf = _pd2.DataFrame(_pf_rows)
    df_show = df_pf.drop(columns=["_id", "_asset_type", "_purchase_date_raw"])

    # v2.0.7.58 - KRITIK DUZELTME (Bahri'nin bulgusu): bu tablo NumberColumn
    # format="%.4f" gibi INGILIZCE (nokta ondalik) format string'leri
    # kullaniyordu - K/Z/Sinyal renklendirmesi eklenmisti ama sayilarin
    # kendisi hic Turkce'ye cevrilmemisti. Artik tum sayisal sutunlar
    # Turkce bicimli METIN olarak gosteriliyor (once eski _fmt_tr_isaretli
    # ile +/- isareti korunuyor - K/Z ve K/Z % onceden "%+.2f" kullaniyordu).
    def _fmt_tr_isaretli(x, ondalik=2, yuzde=False):
        try:
            xf = float(x)
        except (TypeError, ValueError):
            return str(x)
        taban = fmt_tr(abs(xf), ondalik)
        isaret = "+" if xf > 0 else ("-" if xf < 0 else "")
        return f"{isaret}{taban}{'%' if yuzde else ''}"

    df_show["Miktar"] = df_show["Miktar"].apply(lambda v: fmt_tr(v, 2))
    df_show["Alış"]   = df_show["Alış"].apply(lambda v: fmt_tr(v, 6))
    df_show["Güncel"] = df_show["Güncel"].apply(lambda v: fmt_tr(v, 6))
    df_show["Toplam"] = df_show["Toplam"].apply(lambda v: fmt_tr(v, 2))
    df_show["K/Z"]    = df_show["K/Z"].apply(lambda v: _fmt_tr_isaretli(v, 2))
    df_show["K/Z %"]  = df_show["K/Z %"].apply(lambda v: _fmt_tr_isaretli(v, 2, yuzde=True))
    df_show["Skor"]   = df_show["Skor"].apply(lambda v: fmt_tr(v, 1))

    # v2.0.7.30 - K/Z ve K/Z % sutunlarina pozitif/negatif renk kodlamasi
    # (Bahri'nin talebi): pozitif yesil, negatif kirmizi. st.dataframe bir
    # pandas Styler kabul eder, column_config ile birlikte calisir.
    def _kz_renk(v):
        # v2.0.7.58 - Deger artik Turkce bicimli STRING ("+1.234,56" gibi) -
        # renk tespiti icin virgul/nokta cevrilip float'a donduruluyor.
        try:
            temiz = str(v).replace(".", "").replace(",", ".").replace("%", "").replace("+", "")
            vv = float(temiz)
        except (TypeError, ValueError):
            return "text-align: right;"
        if vv > 0:
            return "color: #1b8a4a; font-weight: 600; text-align: right;"
        elif vv < 0:
            return "color: #c0392b; font-weight: 600; text-align: right;"
        return "text-align: right;"

    def _sayi_saga_yasla(v):
        return "text-align: right;"

    # v2.0.7.31 - Sinyal renklendirmesi icin ortak _sinyal_renk_stil()
    # fonksiyonu kullanilir (bkz. clickable_table yakinindaki tanim) -
    # Ana Sayfa/BIST/TEFAS ile tutarli olsun diye kod tekrari yapilmadi.
    try:
        df_show_styled = df_show.style.map(_kz_renk, subset=["K/Z", "K/Z %"]) \
                                       .map(_sinyal_renk_stil, subset=["Sinyal"]) \
                                       .map(_sayi_saga_yasla, subset=["Miktar", "Alış", "Güncel", "Toplam", "Skor"])
    except AttributeError:
        # eski pandas surumlerinde .map yok, .applymap kullan
        df_show_styled = df_show.style.applymap(_kz_renk, subset=["K/Z", "K/Z %"]) \
                                       .applymap(_sinyal_renk_stil, subset=["Sinyal"]) \
                                       .applymap(_sayi_saga_yasla, subset=["Miktar", "Alış", "Güncel", "Toplam", "Skor"])

    # st.dataframe — Daraltilmis sutunlar + Sinyal eklendi
    _event = st.dataframe(
        df_show_styled,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            # v2.0.7.61 - Bahri'nin talebi: artik KESIN PIKSEL genislikleri
            # kullaniliyor (Streamlit'in "small"=75px/"medium"=200px/
            # "large"=400px varsayilanlarindan yuzdelik hesaplandi):
            # Ticker +%5, Miktar +%10, Birim -%10, Sinyal -%40. Ayrica
            # CSS hack'i yerine GERCEK alignment parametresi kullanildi
            # (daha guvenilir, Styler CSS destegine bagimli degil).
            "Ticker": st.column_config.TextColumn(width=79),
            "Tarih":  st.column_config.TextColumn(width="small"),
            "Miktar": st.column_config.TextColumn(width=64, alignment="right"),
            "Birim":  st.column_config.TextColumn(width=54),
            "Alış":   st.column_config.TextColumn(width="small", alignment="right", help="Alış fiyatı (TL)"),
            "Güncel": st.column_config.TextColumn(width="small", alignment="right", help="Güncel piyasa fiyatı (TL)"),
            "Toplam": st.column_config.TextColumn(width="small", alignment="right", help="Pozisyon toplam değeri (TL)"),
            "K/Z":    st.column_config.TextColumn(width="small", alignment="right", help="Kâr/Zarar (TL) — Toplam − Alış maliyeti"),
            "K/Z %":  st.column_config.TextColumn(width="small", alignment="right", help="Kâr/Zarar yüzdesi"),
            "Skor":   st.column_config.TextColumn(
                "Optima Skor", width="small", alignment="right", help="Optima Skoru (0-100)"),
            "Sinyal": st.column_config.TextColumn(
                width=120,
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
    # v2.0.7.61 - DUZELTME (Bahri'nin talebi): etiket tekrar ayni satira,
    # rakamlarla YAN YANA getirildi. Onceki (v2.0.7.28) endise - etiketin
    # sutun hizalamasini bozmasi - ilk uc BOS sutunu (checkbox spaceri +
    # Ticker + Tarih, toplam agirlik 2.45) TEK bir sola-yasli etiket
    # kutusuna birlestirerek cozuldu - geri kalan sutunlarin (Miktar,
    # Birim, Alis, Guncel, Toplam, KZ) hizalamasi/agirligi DEGISMEDI.
    _total_val = df_pf["Toplam"].sum()
    _total_kz  = round((df_pf["Toplam"] - df_pf["Miktar"]*df_pf["Alış"]).sum(), 2)
    # v2.0.7.122 (Bahri'nin talebi, 31 Temmuz 2026): Toplam K/Z %'yi de
    # footer'a ekliyoruz. DIKKAT: bu, satirlardaki K/Z %'lerin BASIT
    # ORTALAMASI ya da TOPLAMI DEGIL - o yanlis olurdu (kucuk bir pozisyonun
    # %50 degisimi ile buyuk bir pozisyonun %1 degisimi esit agirlikta
    # sayilmis olur, portfoyun gercek getirisini carpitir). Dogrusu:
    # Toplam K/Z (TL) / Toplam MALIYET (TL) - yani AGIRLIKLI/gercek
    # portfoy getirisi.
    _total_maliyet = (df_pf["Miktar"] * df_pf["Alış"]).sum()
    _total_kz_pct = round((_total_kz / _total_maliyet * 100), 2) if _total_maliyet else 0.0
    _tcc = "#27ae60" if _total_kz >= 0 else "#e74c3c"
    _tcs = "+" if _total_kz > 0 else ""
    _tcs_pct = "+" if _total_kz_pct > 0 else ""
    _footer_kolonlar = [
        ("ETIKET", 2.45),  # checkbox spaceri + Ticker + Tarih birlesik
        ("Miktar", 1), ("Birim", 1),
        ("Alış", 1), ("Güncel", 1),
        ("TOPLAM", 1), ("KZ", 1),
        ("KZPCT", 1), ("", 1.2), ("", 1.9),
    ]
    _footer_html = ""
    for _etiket, _w in _footer_kolonlar:
        if _etiket == "ETIKET":
            _icerik = "<b style='font-size:13px;color:#6c7a9c;white-space:nowrap;'>TOPLAM PORTFÖY DEĞERİ</b>"
        elif _etiket == "TOPLAM":
            _icerik = f"<b style='font-size:15px;color:#1b2a4a;white-space:nowrap;'>{fmt_tr(_total_val)} TL</b>"
        elif _etiket == "KZ":
            _icerik = f"<b style='font-size:15px;color:{_tcc};white-space:nowrap;'>{_tcs}{fmt_tr(_total_kz)} TL</b>"
        elif _etiket == "KZPCT":
            _icerik = f"<b style='font-size:15px;color:{_tcc};white-space:nowrap;'>{_tcs_pct}{fmt_tr(_total_kz_pct)}%</b>"
        else:
            _icerik = ""
        _hiza = "left" if _etiket == "ETIKET" else "right"
        _footer_html += f"<div style='flex:{_w};text-align:{_hiza};padding:0 4px;white-space:nowrap;'>{_icerik}</div>"
    st.markdown(
        f"<div style='border-top:2px solid #2c3e6b;padding-top:6px;margin-top:6px;'></div>"
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
        _ca, _cb, _cd, _cc  = st.columns([1, 1, 1, 3])
        if _ca.button(f"Sil: {_sel_tkr}", type="secondary", key="pf_sil"):
            delete_portfolio_item(_sel_id)
            st.rerun()
        if _cb.button(f"Sat: {_sel_tkr}", type="primary", key="pf_sat_ac"):
            st.session_state["pf_satis_form_id"] = _sel_id
        if _cd.button(f"Düzelt: {_sel_tkr}", type="secondary", key="pf_duzelt_ac"):
            st.session_state["pf_giris_duzelt_id"] = _sel_id

        # v2.0.7.114 (Bahri'nin talebi): açık pozisyonun giriş bilgilerini
        # (miktar, maliyet, alış tarihi, birim türü) düzeltme formu.
        # Ticker/kategori KASITLI değiştirilemez - farklı bir varlığa
        # dönüştürmek "düzeltme" değil, ayrı bir işlemdir (sil+ekle).
        if st.session_state.get("pf_giris_duzelt_id") == _sel_id:
            with st.container(border=True):
                st.markdown(f"**{_sel_tkr} — Giriş Bilgilerini Düzelt**")
                import datetime as _dt_duz
                _raw_tarih = _row_data.get("_purchase_date_raw", "")
                try:
                    _duz_tarih_def = (_dt_duz.datetime.strptime(_raw_tarih, "%Y-%m-%d").date()
                                       if _raw_tarih and len(_raw_tarih) == 10
                                       else _dt_duz.date.today())
                except Exception:
                    _duz_tarih_def = _dt_duz.date.today()

                dz1, dz2, dz3, dz4 = st.columns(4)
                with dz1:
                    _duz_miktar_str = st.text_input(
                        "Miktar", value=fmt_tr(_row_data["Miktar"], 4),
                        key="pf_duzelt_miktar")
                with dz2:
                    _duz_maliyet_str = st.text_input(
                        "Maliyet (birim, TL)", value=fmt_tr(_row_data["Alış"], 4),
                        key="pf_duzelt_maliyet")
                with dz3:
                    _duz_tarih = st.date_input(
                        "Alış Tarihi", value=_duz_tarih_def,
                        key="pf_duzelt_tarih", format="DD.MM.YYYY")
                with dz4:
                    _duz_unit_opts = ["Adet","Pay","Gram","Lot","Ons","Varil","Ton","kg","m²","Diğer"]
                    _duz_unit_def = _row_data.get("Birim", "Adet") or "Adet"
                    _duz_unit_idx = (_duz_unit_opts.index(_duz_unit_def)
                                     if _duz_unit_def in _duz_unit_opts else 0)
                    _duz_unit = st.selectbox(
                        "Birim Türü", _duz_unit_opts, index=_duz_unit_idx,
                        key="pf_duzelt_birim")

                dzb1, dzb2 = st.columns([1, 1])
                if dzb1.button("Düzeltmeyi Kaydet", type="primary", key="pf_duzelt_kaydet"):
                    _duz_miktar = parse_tr(_duz_miktar_str)
                    _duz_maliyet = parse_tr(_duz_maliyet_str)
                    _sonuc = update_portfolio_item(
                        _sel_id, _duz_miktar, _duz_maliyet,
                        _duz_tarih.strftime("%Y-%m-%d"), _duz_unit)
                    if _sonuc["basari"]:
                        st.session_state.pop("pf_giris_duzelt_id", None)
                        st.success(f"{_sel_tkr} giriş bilgileri güncellendi.")
                        st.rerun()
                    else:
                        st.error(_sonuc["hata"])
                if dzb2.button("Vazgeç", key="pf_duzelt_vazgec2"):
                    st.session_state.pop("pf_giris_duzelt_id", None)
                    st.rerun()

        # v2.0.7.47 - Satış formu (Bahri'nin talebi: gerçek muhasebe -
        # satış kalıcı bir kayıt olarak tutulur, komisyon+vergi düşülmüş
        # NET gerçekleşmiş K/Z hesaplanır).
        if st.session_state.get("pf_satis_form_id") == _sel_id:
            from portfolio_ledger import get_fee_settings, sell_portfolio_item
            _pf_oranlar = get_fee_settings(_cur_user["id"])
            _pf_asset_type = _row_data.get("_asset_type", "BIST")
            _oran = _pf_oranlar.get(_pf_asset_type, {"fee_pct": 0.0, "tax_pct": 0.0})

            with st.container(border=True):
                st.markdown(f"**{_sel_tkr} — Satış Formu** (elinizde: {fmt_tr(_row_data['Miktar'],4)} {_row_data['Birim']})")
                import datetime as _dt_pf
                fs1, fs2, fs3 = st.columns(3)
                with fs1:
                    _satis_miktar_str = st.text_input(
                        "Satış Miktarı", value=fmt_tr(_row_data["Miktar"], 4),
                        key="pf_satis_miktar")
                    _satis_miktar = parse_tr(_satis_miktar_str)
                with fs2:
                    _satis_fiyat_str = st.text_input(
                        "Satış Fiyatı (birim, TL)", value=fmt_tr(_row_data["Güncel"], 4),
                        key="pf_satis_fiyat")
                    _satis_fiyat = parse_tr(_satis_fiyat_str)
                with fs3:
                    _satis_tarih = st.date_input(
                        "Satış Tarihi", value=_dt_pf.date.today(), key="pf_satis_tarih",
                        format="DD.MM.YYYY")
                fs4, fs5 = st.columns(2)
                # v2.0.7.58 - Bahri'nin talebi: Satis dekontu geldiginde
                # gercek TL tutari elde olur, oran degil - bu yuzden
                # Komisyon/Vergi artik dogrudan TL olarak girilir. Kategori
                # varsayilan yuzdesi sadece bir BASLANGIC ONERISI hesaplamak
                # icin kullanilir (onizleme oncesi tahmini tutar), kullanici
                # dekonttaki gercek tutarla degistirir.
                _tahmini_alis_deger = float(_row_data["Miktar"]) * _row_data["Alış"]
                _tahmini_satis_deger = float(_row_data["Miktar"]) * _row_data["Güncel"]
                _tahmini_brut = _tahmini_satis_deger - _tahmini_alis_deger
                _oneri_komisyon_tl = round(
                    (_tahmini_alis_deger + _tahmini_satis_deger) * _oran["fee_pct"] / 100.0, 2)
                _oneri_vergi_tl = round(max(0.0, _tahmini_brut) * _oran["tax_pct"] / 100.0, 2)
                with fs4:
                    _satis_komisyon_str = st.text_input(
                        "Komisyon (₺)", value=fmt_tr(_oneri_komisyon_tl, 2),
                        key="pf_satis_komisyon",
                        help="Aracı kurumun satış dekontunda gösterdiği gerçek komisyon tutarı. "
                             "Kategori ortalamasına göre bir başlangıç önerisiyle dolduruldu, "
                             "dekonttaki gerçek tutarla değiştirebilirsiniz.")
                    _satis_komisyon = parse_tr(_satis_komisyon_str)
                with fs5:
                    _satis_vergi_str = st.text_input(
                        "Vergi (₺)", value=fmt_tr(_oneri_vergi_tl, 2),
                        key="pf_satis_vergi",
                        help="Aracı kurumun kestiği gerçek vergi/stopaj tutarı. Genel bir "
                             "tahminle dolduruldu, mali müşavirinize danışıp düzeltebilirsiniz.")
                    _satis_vergi = parse_tr(_satis_vergi_str)

                # Önizleme
                _alis_deger = _satis_miktar * _row_data["Alış"]
                _satis_deger = _satis_miktar * _satis_fiyat
                _brut = _satis_deger - _alis_deger
                _kom_tl = _satis_komisyon
                _verg_tl = _satis_vergi
                _net = round(_brut - _kom_tl - _verg_tl, 2)
                _net_renk = "#1b8a4a" if _net >= 0 else "#c0392b"
                st.markdown(
                    f"Brüt K/Z: **{fmt_tr(_brut)} ₺**  |  Komisyon: **-{fmt_tr(_kom_tl)} ₺**  |  "
                    f"Vergi: **-{fmt_tr(_verg_tl)} ₺**  |  "
                    f"<span style='color:{_net_renk};font-weight:700;'>Net K/Z: {fmt_tr(_net)} ₺</span>",
                    unsafe_allow_html=True)

                fb1, fb2 = st.columns([1, 1])
                if fb1.button("Satışı Onayla ve Kaydet", type="primary", key="pf_satis_onay"):
                    _sonuc = sell_portfolio_item(
                        _cur_user["id"], _sel_id, _satis_miktar, _satis_fiyat,
                        _satis_tarih.strftime("%Y-%m-%d"), _satis_komisyon, _satis_vergi)
                    if _sonuc["basari"]:
                        st.session_state.pop("pf_satis_form_id", None)
                        st.success(f"Satış kaydedildi — Net K/Z: {fmt_tr(_sonuc['net_kz'])} ₺")
                        st.rerun()
                    else:
                        st.error(_sonuc["hata"])
                if fb2.button("Vazgeç", key="pf_satis_vazgec"):
                    st.session_state.pop("pf_satis_form_id", None)
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
                # v2.0.7.71 - bkz. Ana Sayfa/Kategori Detay'daki ayni not:
                # _sr de DUZELTILMEMIS df_uni'den okunuyor.
                # v2.0.7.77 - bkz. live_optima_score()'daki ayni not:
                # bool(NaN)==True oldugu icin TEFAS/BIST/KRIPTO burada
                # yanlislikla hep 0 gosteriyordu - "== True" ile duzeltildi.
                if _sr.get("_gecmis_veri_yok") == True:
                    disp_score_pf = 0.0
                _sig_lbl, _sig_cls = get_signal(disp_score_pf,_d["rsi"],_d["trend"])
            _m1,_m2,_m3,_m4,_m5 = st.columns(5)
            _m1.metric("Son Fiyat",   fmt_tr(float(_sr['Son_Fiyat']),4))
            _m2.metric("Optima Skor", fmt_tr(disp_score_pf,1))
            _m3.metric("RSI (14)",    fmt_tr(_d['rsi'],1))
            _m4.metric("1A Getiri %", fmt_tr_isaretli(_d['ret1m'],2,yuzde=True))
            _m5.metric("Yıllık Vol %",fmt_tr(_d['vol'],1)+"%")

                # v2.0.7.153 (Bahri'nin talebi, 18 Agustos 2026): tekil varlik
                # skor bilesimi grafigi simdilik kaldirildi (fonksiyon tanimi
                # duruyor, farkli bir grafik sekliyle - 3D SVG - istenirse
                # kolayca geri eklenebilir).

            _sc = SIG_COLORS.get(_sig_cls,"#666")

            # v2.0.3: Hacim trendi bilgisi (varsa)
            _vol_html = ""
            if _d.get("vol_trend","YOK") != "YOK":
                _vt = _d["vol_trend"]
                _vr = _d.get("vol_ratio", 0.0)
                _adj = _d.get("score_adj", 0)
                # v2.0.7.109 - bkz. Ana Sayfa blogundaki ayni not.
                _vol_clr = {"ARTIYOR": "#27ae60", "AZALIYOR": "#e74c3c", "NORMAL": "#7f8c8d"}.get(_vt, "#7f8c8d")
                _adj_clr = "#27ae60" if _adj > 0 else ("#e74c3c" if _adj < 0 else "#7f8c8d")
                _adj_str = f" <b style='color:{_adj_clr}'>({_adj:+d} skor)</b>" if _adj != 0 else ""
                _vol_html = (
                    f' | Hacim: <b style="color:{_vol_clr}">{_vt}</b> '
                    f'<small>(5g/20g = {fmt_tr(_vr,2)})</small>{_adj_str}'
                )

            # v2.0.3.2: Max DD cezasi bilgisi (kullaniciya hatirlat)
            _dd_html = ""
            if _d.get("dd_adj", 0) != 0:
                _dd_val = _d.get("max_dd")
                _dd_clr = "#e74c3c"
                _dd_html = (
                    f' | Max DD: <b style="color:{_dd_clr}">{fmt_tr(_dd_val,1)}%</b> '
                    f'<b style="color:{_dd_clr}">({_d["dd_adj"]:+d} skor)</b>'
                )

            st.markdown(f'''<div class="ts-card" style="border-left:5px solid {_sc};padding:12px 18px;">
      <span class="ts-sig {_sig_cls}">{_sig_lbl}</span>
      <span style="color:#6c7a9c;font-size:12px;margin-left:14px">
        Trend: <b>{_d["trend"]}</b> | Optima Skor: <b>{disp_score_pf}/100</b> | MACD: <b>{fmt_tr(_d["macd"],4)}</b>{_vol_html}{_dd_html}
      </span></div>''', unsafe_allow_html=True)

            # v2.0.3.2: Teknik Gostergeler expander
            render_teknik_gostergeler(_d, float(_sr["Son_Fiyat"]))

            if not _d["hist"].empty:
                _fig = candle_fig(_d["hist"],_sel_tkr)
                if _fig: st.plotly_chart(_fig, width='stretch')
            else:
                st.info(f"{_sel_tkr} için geçmiş fiyat verisi yüklenemedi.")

            # v2.0.3.1: BIST varligi icin Temel Analiz blogu (kategori sayfasiyla ayni mantik)
            _sel_cat = str(_sr["Kategori"])
            if _sel_cat == "BIST":
                st.divider()
                st.subheader("Temel Analiz")
                try:
                    from kap_client import (fetch_kap_fundamentals,
                                            fundamentals_to_display, get_kap_url)
                    _kap_url = get_kap_url(_sel_tkr)

                    with st.spinner("Temel veriler yükleniyor (yfinance + KAP)..."):
                        _raw  = fetch_kap_fundamentals(_sel_tkr)
                        _disp = fundamentals_to_display(_raw)

                    _pb = _raw.get("pb_ratio"); _pe = _raw.get("pe_ratio"); _dy = _raw.get("div_yield")
                    # v2.0.7.79 (Bahri'nin talebi, YAYLA ornegi) - bkz.
                    # yukaridaki Ana Sayfa blogundaki ayni not: Skor
                    # Bilesimi artik Master Skor'u belirleyen AYNI
                    # fonksiyonlari kullanir.
                    #
                    # v2.0.7.105 - bkz. Ana Sayfa Detay blogundaki ayni
                    # KRITIK DUZELTME notu (Bahri'nin bulgusu, AKSEN ornegi):
                    # CSV'de Optima_Skor varsa Teknik/Temel de AYNI CSV
                    # satirinin dondurulmus degerlerinden hesaplanir.
                    _precomp2 = _sr.get("Optima_Skor")
                    if _precomp2 is not None and _precomp2 == _precomp2:
                        _combined = float(_precomp2)
                        _csv_rsi2   = _csv_alan(_sr, "RSI")
                        _csv_ret1m2 = _csv_alan(_sr, "Ret1M")
                        _csv_vol2   = _csv_alan(_sr, "Vol")
                        _csv_pb2    = _csv_alan(_sr, "PB")
                        _csv_pe2    = _csv_alan(_sr, "PE")
                        _csv_dy2    = _csv_alan(_sr, "DY")
                        _teknik_skor = _teknik_alt_skor(
                            _csv_rsi2 if _csv_rsi2 is not None else 50.0,
                            _csv_ret1m2 if _csv_ret1m2 is not None else 0.0,
                            _csv_vol2 if _csv_vol2 is not None else 30.0)
                        _fund_skor = _temel_alt_skor(_csv_pb2, _csv_pe2, _csv_dy2)
                        # v2.0.7.107 (Bahri'nin talebi) - bkz. Ana Sayfa
                        # blogundaki ayni not: hacim/DD ayari artik Teknik
                        # Skor'a katlaniyor (fark = Master - Teknik - Temel).
                        _teknik_skor = _teknik_skor + (_combined - _teknik_skor - _fund_skor)
                    else:
                        _teknik_skor = _teknik_alt_skor(_d["rsi"], _d["ret1m"], _d["vol"])
                        _fund_skor = _temel_alt_skor(_pb, _pe, _dy)
                        _tech_with_fund = optima_score(_d["rsi"], _d["ret1m"], _d["vol"], True, _pb, _pe, _dy)
                        _total_adj2 = _d.get("total_adj", _d.get("score_adj", 0))
                        _teknik_skor = _teknik_skor + _total_adj2
                        _combined = max(0, min(100, round(_tech_with_fund + _total_adj2, 1)))
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
                        <small style='color:#6c7a9c'>Teknik Skor (RSI + Momentum + Vol + Hacim/DD)</small><br>
                        <b style='font-size:20px;color:#1b2a4a'>{fmt_tr(_teknik_skor,1)} / 75</b><br><br>
                        <small style='color:#6c7a9c'>Temel Skor (F/K + PD/DD + Temettü)</small><br>
                        <b style='font-size:20px;color:#1b2a4a'>{fmt_tr(_fund_skor,1)} / 25</b><br>
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

    st.divider()
    _render_karsilastirma(_cur_user, portfolio)
    _render_pozisyon_karsilastirma(_cur_user, portfolio)
    _render_sermaye_nakit_ozeti(_cur_user, portfolio, float(df_pf["Toplam"].sum()))
    _render_gerceklesmis_kar_zarar(_cur_user)




# ══════ KATEGORİ SAYFALARI ══════
elif page in CAT:
    cat_code=CAT[page]
    st.title(page)
    if df_uni.empty: st.error("`python worker.py` çalıştırın."); st.stop()

    # v2.0.7.74 - Bahri'nin talebi: Doviz fiyatlarinin SERBEST PIYASA
    # (Harem/Kapalicarsi kaynakli) oldugu acikca belirtiliyor - TCMB
    # (resmi/banka kuru) kullanimi tamamen birakildi, cunku yatirimcilarin
    # gercekte kullandigi fiyatlar serbest piyasa fiyatlaridir.
    if cat_code == "DOVIZ":
        st.caption("Fiyatlar Serbest Piyasa kaynaklıdır - TCMB resmi kuru değildir.")

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
            st.caption(f"Ons Altın (USD, bilgi amaçlı — TL fiyatlara dahil değildir): **${fmt_tr(_ons_usd)}**")

    df_cat=df_uni[df_uni["Kategori"]==cat_code].copy()
    if df_cat.empty: st.warning(f"{page} verisi bulunamadı."); st.stop()

    # v2.0.7.64 - KALDIRILDI (Bahri'nin talebi, 15 Temmuz): v2.0.4.50'den
    # (6 Temmuz) beri duran manuel "Canli Fiyatlari Yenile (ilk 100
    # hisse)" butonu gereksiz bulunup kaldirildi. Sebep: Firsat Radari
    # (firsat_radari.py) zaten BIST seans saatlerinde 15 dk'da bir TUM
    # 772 hisseyi tariyor, Supabase intraday_scores'a yaziyor, ve
    # load_universe() bunu 45 dk tazelik penceresinde otomatik yansitiyor
    # (bkz. yukaridaki "Firsat Radari overlay" notu) - yani bu buton hem
    # gereksizdi hem de kapsadigi 100 hisse otomatik sistemin kapsadigi
    # 772'den azdi.

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
    # v2.0.7.69 - KRITIK DUZELTME (Bahri'nin bulgusu: Doviz'de ilk ~50
    # varlik "gecmis fiyat verisi yuklenemedi" diyor ama Optima Skoru
    # digerlerinden YUKSEKTI): yukaridaki satir sadece Son_Fiyat<=0 olan
    # varliklari yakaliyordu. Ama bu Doviz/Maden varliklarinin fiyati VAR
    # (Truncgil/Bigpara'dan) - sadece RSI/Ret1M/Vol SAHTE NOTR degerler
    # (50/0/dusuk-vol). RSI=50 tam da "en iyi RSI bolgesi" oldugu ve sahte
    # vol dusuk oldugu icin, veri OLMAYAN bir varlik veri OLAN bir
    # varliktan daha yuksek skor aliyordu. worker.py artik bu durumu acikca
    # "_gecmis_veri_yok" ile isaretliyor - burada da skor sifirlanir.
    if "_gecmis_veri_yok" in df_cat.columns:
        df_cat.loc[df_cat["_gecmis_veri_yok"] == True, "Optima_Skor"] = 0.0
        # v2.0.7.76 (Bahri'nin talebi): gercek gecmis verisi olmayan
        # satirlarda RSI/Ret1M artik sahte notr (50/0) gostermiyor - hucre
        # BOS kalir (fmt_tr artik None/NaN icin "" donduruyor). Boylece
        # "RSI hep 50 gorunuyor, kafa karistirici" durumu ortadan kalkar.
        for _col in ("RSI", "Ret1M"):
            if _col in df_cat.columns:
                df_cat.loc[df_cat["_gecmis_veri_yok"] == True, _col] = None
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
    m3.metric("Ort. 1A Getiri %",f"{fmt_tr(ret_mean,2)}%")
    m4.metric("Ort. Optima Skor",fmt_tr(degerli['Optima_Skor'].mean(),1) if not degerli.empty else "N/A")

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
        # v2.0.7.71 - KRITIK DUZELTME (Bahri'nin bulgusu, BGNTRY ornegi):
        # v2.0.7.69'daki "_gecmis_veri_yok" duzeltmesi SADECE liste/tablo
        # gorunumunun yerel kopyasina (df_cat) uygulanmisti - sel_row ise
        # DUZELTILMEMIS df_uni'den okundugu icin bu Detay sayfasi hala
        # eski (yanlis yuksek, orn. 66.7) skoru gosteriyordu. Ayni
        # Son_Fiyat kontrolu gibi burada da acikca tekrarlaniyor.
        # v2.0.7.77 - KRITIK DUZELTME (Bahri'nin bulgusu, FZJ/TEFAS ornegi:
        # liste tablosunda Optima Skor 66,7 ama hemen altindaki Detay
        # panelinde 0,0 gorunuyordu). bool(NaN)==True oldugu icin (Python'da
        # NaN "sifir degil" sayildigindan) bu bayragin hic ayarlanmadigi
        # TEFAS/BIST/KRIPTO kategorilerinde skor yanlislikla hep 0'a
        # sifirlaniyordu - liste tablosu "== True" kullandigi icin (NaN==True
        # daima False) bu hataya dusmuyordu. Asagidaki karsilastirma artik
        # liste ile birebir ayni (dogru) mantigi kullanir.
        if sel_row.get("_gecmis_veri_yok") == True:
            disp_score_cat = 0.0
        sig_lbl,sig_cls=get_signal(disp_score_cat,d["rsi"],d["trend"])

    r1,r2,r3,r4,r5=st.columns(5)
    r1.metric("Son Fiyat",fmt_tr(float(sel_row['Son_Fiyat']),4))
    r2.metric("Optima Skor",fmt_tr(disp_score_cat,1))
    r3.metric("RSI (14)",fmt_tr(d['rsi'],1))
    r4.metric("1A Getiri %",fmt_tr_isaretli(d['ret1m'],2,yuzde=True))
    r5.metric("Yıllık Vol %",fmt_tr(d['vol'],1)+"%")

        # v2.0.7.153 (Bahri'nin talebi, 18 Agustos 2026): tekil varlik
        # skor bilesimi grafigi simdilik kaldirildi (fonksiyon tanimi
        # duruyor, farkli bir grafik sekliyle - 3D SVG - istenirse
        # kolayca geri eklenebilir).

    sig_color=SIG_COLORS.get(sig_cls,"#666")

    # v2.0.3: Hacim trendi bilgisi (varsa)
    vol_html = ""
    if d.get("vol_trend","YOK") != "YOK":
        _vt = d["vol_trend"]
        _vr = d.get("vol_ratio", 0.0)
        _adj = d.get("score_adj", 0)
        # v2.0.7.109 - bkz. Ana Sayfa blogundaki ayni not.
        _vol_clr = {"ARTIYOR": "#27ae60", "AZALIYOR": "#e74c3c", "NORMAL": "#7f8c8d"}.get(_vt, "#7f8c8d")
        _adj_clr = "#27ae60" if _adj > 0 else ("#e74c3c" if _adj < 0 else "#7f8c8d")
        _adj_str = f" <b style='color:{_adj_clr}'>({_adj:+d} skor)</b>" if _adj != 0 else ""
        vol_html = (
            f' &nbsp;|&nbsp; Hacim: <b style="color:{_vol_clr}">{_vt}</b> '
            f'<small>(5g/20g = {fmt_tr(_vr,2)})</small>{_adj_str}'
        )

    # v2.0.3.2: Max DD cezasi bilgisi
    dd_html = ""
    if d.get("dd_adj", 0) != 0:
        _dd_val = d.get("max_dd")
        dd_html = (
            f' &nbsp;|&nbsp; Max DD: <b style="color:#e74c3c">{fmt_tr(_dd_val,1)}%</b> '
            f'<b style="color:#e74c3c">({d["dd_adj"]:+d} skor)</b>'
        )

    st.markdown(f"""
    <div class="ts-card" style="border-left:5px solid {sig_color};padding:12px 18px;">
      <span class="ts-sig {sig_cls}">{sig_lbl}</span>
      <span style="color:#6c7a9c;font-size:12px;margin-left:14px">
        Trend: <b>{d['trend']}</b> &nbsp;|&nbsp;
        Optima Skor: <b>{disp_score_cat}/100</b> &nbsp;|&nbsp;
        MACD: <b>{fmt_tr(d['macd'],4)}</b>{vol_html}{dd_html}
      </span>
    </div>""",unsafe_allow_html=True)

    # v2.0.3.2: Teknik Gostergeler expander
    render_teknik_gostergeler(d, float(sel_row["Son_Fiyat"]))

    # Mum grafiği
    if not d["hist"].empty:
        fig=candle_fig(d["hist"],sel)
        if fig: st.plotly_chart(fig,width='stretch')
    else:
        st.warning(f"{sel} için geçmiş fiyat verisi yüklenemedi.")

    # BIST Temel Analiz
    if cat_code=="BIST":
        st.divider()
        st.subheader("Temel Analiz")
        try:
            from kap_client import (fetch_kap_fundamentals, fundamentals_to_display,
                                    get_kap_url)
            kap_url = get_kap_url(sel)

            with st.spinner("Temel veriler yükleniyor (yfinance + KAP)..."):
                raw  = fetch_kap_fundamentals(sel)
                disp = fundamentals_to_display(raw)

            pb = raw.get("pb_ratio"); pe = raw.get("pe_ratio"); dy = raw.get("div_yield")
            # v2.0.7.79 (Bahri'nin talebi, YAYLA ornegi) - bkz. yukaridaki
            # diger iki detay blogundaki ayni not.
            #
            # v2.0.7.105 - bkz. Ana Sayfa Detay blogundaki ayni KRITIK
            # DUZELTME notu (Bahri'nin bulgusu, AKSEN ornegi, 29 Temmuz
            # 2026): CSV'de Optima_Skor varsa Teknik/Temel de AYNI CSV
            # satirinin dondurulmus degerlerinden hesaplanir - boylece
            # ekranda yan yana gorunen 3 sayi (Teknik, Temel, Master) HER
            # ZAMAN ayni anin/kaynagin urunu olur.
            _precomp3 = sel_row.get("Optima_Skor")
            if _precomp3 is not None and _precomp3 == _precomp3:
                combined = float(_precomp3)
                _csv_rsi3   = _csv_alan(sel_row, "RSI")
                _csv_ret1m3 = _csv_alan(sel_row, "Ret1M")
                _csv_vol3   = _csv_alan(sel_row, "Vol")
                _csv_pb3    = _csv_alan(sel_row, "PB")
                _csv_pe3    = _csv_alan(sel_row, "PE")
                _csv_dy3    = _csv_alan(sel_row, "DY")
                teknik_skor = _teknik_alt_skor(
                    _csv_rsi3 if _csv_rsi3 is not None else 50.0,
                    _csv_ret1m3 if _csv_ret1m3 is not None else 0.0,
                    _csv_vol3 if _csv_vol3 is not None else 30.0)
                fund_skor = _temel_alt_skor(_csv_pb3, _csv_pe3, _csv_dy3)
                # v2.0.7.107 (Bahri'nin talebi) - bkz. Ana Sayfa blogundaki
                # ayni not: hacim/DD ayari artik Teknik Skor'a katlaniyor.
                teknik_skor = teknik_skor + (combined - teknik_skor - fund_skor)
            else:
                teknik_skor = _teknik_alt_skor(d["rsi"], d["ret1m"], d["vol"])
                fund_skor = _temel_alt_skor(pb, pe, dy)
                _tech_with_fund = optima_score(d["rsi"], d["ret1m"], d["vol"], True, pb, pe, dy)
                _total_adj3 = d.get("total_adj", d.get("score_adj", 0))
                teknik_skor = teknik_skor + _total_adj3
                combined = max(0, min(100, round(_tech_with_fund + _total_adj3, 1)))
            final_lbl, final_cls = get_signal(combined, d["rsi"], d["trend"])

            # Kaynak bilgisi
            # v2.0.7.50 - DUZELTME (Bahri'nin bulgusu): "_kap_note" alani
            # zaten TAM bir cumleydi ("Veri kaynağı: yfinance"), ama buraya
            # "KAP: " oneki eklenerek yapistiriliyordu - sonuc "Kaynak:
            # yfinance | KAP: Veri kaynağı: yfinance" gibi anlamsiz,
            # tekrarli bir metin oluyordu. Artik acik ve tek seferlik.
            src_note = "yfinance"
            if raw.get("_kap_available"):
                src_note += " + KAP"
            st.caption(f"Kaynak: {src_note}")
            if not raw.get("_kap_available"):
                st.caption("Bu hisse için KAP bilanço verisi bulunamadı, sadece yfinance kullanıldı.")

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
                <small style='color:#6c7a9c'>Teknik Skor (RSI + Momentum + Vol + Hacim/DD)</small><br>
                <b style='font-size:20px;color:#1b2a4a'>{fmt_tr(teknik_skor,1)} / 75</b><br><br>
                <small style='color:#6c7a9c'>Temel Skor (F/K + PD/DD + Temettü)</small><br>
                <b style='font-size:20px;color:#1b2a4a'>{fmt_tr(fund_skor,1)} / 25</b><br>
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

        # v2.0.7.70 - DUZELTME (Bahri'nin bulgusu: rakamlar hizali degil):
        # onceki halde satirlar FARKLI sutun sayisi kullaniyordu (4, sonra
        # 3, sonra 2) - Streamlit her st.columns() cagrisinda esit genislik
        # ureten AYRI bir izgara olusturur, bu yuzden farkli satirlarin
        # sutun sinirlari alt alta gelmiyordu. Artik TUM satirlar sabit
        # 4 sutunlu tek bir izgarada - kullanilmayan hucreler bos birakilir,
        # boylece butun degerler dikey olarak hizali gorunur.
        ta,tb,tc,td = st.columns(4)
        ta.metric("1 Ay",  fmt_tr_isaretli(ret1m_x,2,yuzde=True))
        tb.metric("3 Ay",  fmt_tr_isaretli(ret3m_x,2,yuzde=True))
        tc.metric("6 Ay",  fmt_tr_isaretli(ret6m_x,2,yuzde=True))
        td.metric("1 Yil", fmt_tr_isaretli(ret1y_x,2,yuzde=True))

        te,tf,tg,th = st.columns(4)
        if ret3y_x != 0 or ret5y_x != 0:
            te.metric("3 Yil", fmt_tr_isaretli(ret3y_x,2,yuzde=True))
            tf.metric("5 Yil", fmt_tr_isaretli(ret5y_x,2,yuzde=True))
            tg.metric("Risk Puani", f"{risk_val}/7 — {risk_labels.get(risk_val,'')}")
        else:
            te.metric("Risk Puani", f"{risk_val}/7 — {risk_labels.get(risk_val,'')}")

        if not d["hist"].empty:
            pr = d["hist"]["Close"].dropna() if "Close" in d["hist"].columns else d["hist"].iloc[:,0].dropna()
            if len(pr) > 20 and pr.pct_change().dropna().std() > 0:
                rets=pr.pct_change().dropna(); rf=0.42/252; ex=rets-rf
                sharpe=round(float(ex.mean()/ex.std()*np.sqrt(252)),3)
                maxdd=round(float(((pr-pr.cummax())/pr.cummax()).min()*100),2)
                s1,s2,s3,s4=st.columns(4)
                s1.metric("Tahmini Sharpe",fmt_tr(sharpe,3),
                          help="Getiri noktalarindan uretilen sentetik seriden hesaplanmistir.")
                s2.metric("Tahmini Max Drawdown",f"{fmt_tr(maxdd,2)}%",
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
        ha_refresh = st.button("Yenile", key="ha_refresh", width='stretch')

    # ── Veri yükle ──────────────────────────────────────────
    try:
        from halka_arz_client import fetch_ipo_list, get_ipo_summary
        with st.spinner("XHARZ üye listesi yükleniyor..."):
            df_ipo = fetch_ipo_list(force_refresh=ha_refresh, df_uni_hazir=df_uni)
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
        m3.metric("Ort. Optima Skor", fmt_tr(ort_skor,1) if not pd.isna(ort_skor) else "—")
    if "Ret1M" in df_ipo.columns:
        ort_ret = df_ipo[df_ipo["Ret1M"] != 0]["Ret1M"].mean()
        m4.metric("Ort. 1A Getiri", fmt_tr_isaretli(ort_ret,2,yuzde=True) if not pd.isna(ort_ret) else "—")

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
    # v2.0.7.60 - Bahri'nin bulgusu: bu tablo da Ingilizce NumberColumn
    # format kullaniyordu, sistem geneli Turkce format taramasinda bulundu.
    if "Son_Fiyat" in tablo_df.columns:
        tablo_df["Son_Fiyat"] = tablo_df["Son_Fiyat"].apply(lambda v: fmt_tr(v,4))
        col_cfg["Son_Fiyat"] = st.column_config.TextColumn("Fiyat (₺)")
    if "RSI" in tablo_df.columns:
        tablo_df["RSI"] = tablo_df["RSI"].apply(lambda v: fmt_tr(v,1))
        col_cfg["RSI"] = st.column_config.TextColumn("RSI")
    if "Ret1M" in tablo_df.columns:
        tablo_df["Ret1M"] = tablo_df["Ret1M"].apply(lambda v: fmt_tr(v,2))
        col_cfg["Ret1M"] = st.column_config.TextColumn("1A Getiri %")
    if "Optima_Skor" in tablo_df.columns:
        tablo_df["Optima_Skor"] = tablo_df["Optima_Skor"].apply(lambda v: fmt_tr(v,1))
        col_cfg["Optima_Skor"] = st.column_config.TextColumn("Optima Skor")
    st.dataframe(tablo_df, width='stretch', hide_index=True, column_config=col_cfg)

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
        tm_refresh = st.button("Yenile", key="tm_refresh", width='stretch')

    # ── Veri yükle ───────────────────────────────────────────
    try:
        from temettu_client import fetch_temettu_list
        with st.spinner("XTMTU verileri yükleniyor..."):
            df_tm = fetch_temettu_list(force_refresh=tm_refresh, df_uni_hazir=df_uni)
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
    m3.metric("Ort. Temettü Verimi", f"%{fmt_tr(ort_verim,2)}" if ort_verim else "—")
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
        "<b>1. Temettü geliri hesabı:</b> Bütçe × Temettü Verimi % = o hisseye "
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

elif page=="SonDakika Haberleri":
    # v2.0.7.160 (Bahri'nin talebi, 19 Ağustos 2026 — "durumun stabil
    # olduğunu nasıl görebilirim diye düşünürken haber sayfası fikri
    # oluşmaya başladı"): Beklenti Modu'nun izlediği haber akışının
    # kendisi. AMAÇ: "hiçbir şey olmuyor" bilgisini görünür kılmak —
    # sistem sessizse bunun sebebi sistemin çalışmaması değil, gerçekten
    # sakin olması. Bahri'nin kararı: TÜM akış gösterilir, ama ön-filtreye
    # takılan (piyasa etkisi olası) haberler AYRICA ÜSTTE işaretli durur.
    st.title("SonDakika Haberleri")
    st.caption("Beklenti Modu'nun 10 dakikada bir taradığı kaynaklar — en yeni haber en üstte")

    try:
        from db import get_haber_akisi

        # v2.0.7.168: bu sayfadayken yapılan HER etkileşim (scroll'a bağlı
        # rerun, başka bir widget tıklaması vb.) öncesinde önbelleksiz
        # olarak 300 satıra kadar sorgu atılıyordu. 20 saniyelik önbellek
        # eklendi - haber akışı zaten en hızlı 2 saatte bir tazeleniyor,
        # 20 saniyelik gecikme hiçbir bilgiyi geciktirmiyor.
        @st.cache_data(ttl=20, show_spinner=False)
        def _haber_akisi_onbellekli():
            return get_haber_akisi(saat=48, limit=300)

        _akis = _haber_akisi_onbellekli()
    except Exception as _hak_err:
        _akis = []
        st.error(f"Haber akışı okunamadı: {_hak_err}")

    if not _akis:
        st.info(
            "Henüz haber akışı birikmemiş. Haber izleme betiği GitHub "
            "Actions'ta 10 dakikada bir çalışıyor — ilk tur tamamlandıktan "
            "sonra buraya haberler düşmeye başlar."
        )
    else:
        _ilgili = [h for h in _akis if h.get("eslesen_kalip")]
        _digerleri = [h for h in _akis if not h.get("eslesen_kalip")]

        # ── Durum özeti: Bahri'nin asıl sorusuna doğrudan cevap ──────
        _c1, _c2, _c3 = st.columns(3)
        _c1.metric("Son 48 saatte taranan", len(_akis))
        _c2.metric("Filtreye takılan", len(_ilgili))
        _c3.metric("Onay bekleyen tespit", len(_bekleyen_tespitler))
        if not _ilgili:
            st.success(
                "Son 48 saatte hiçbir haber izlenen 6 kalıbın anahtar "
                "kelimelerine takılmadı."
            )
        st.divider()

        def _haber_satiri(_h, _isaretli=False):
            _bas = _h.get("baslik_tr") or _h.get("baslik") or ""
            _zaman = _h.get("zaman")
            try:
                _zaman_str = _zaman.strftime("%d.%m.%Y %H:%M")
            except Exception:
                _zaman_str = str(_zaman or "")
            _kalip_etiket = ""
            if _isaretli and _h.get("eslesen_kalip"):
                _kalip_adlari = [_KALIP_ISIM.get(_k.strip(), _k.strip())
                                 for _k in str(_h["eslesen_kalip"]).split(",") if _k.strip()]
                _kalip_etiket = " · Kalıp: " + ", ".join(_kalip_adlari)
            if _h.get("haber_url"):
                st.markdown(f"[{_bas}]({_h['haber_url']})")
            else:
                st.markdown(_bas)
            # v2.0.7.179 (Bahri'nin talebi, 21 Ağustos 2026 — "başlığı
            # çevirebiliyorsak özeti de çevirebiliriz"): başlığın hemen
            # altında, RSS kaynağının kendi kısa özeti (çevrilmişse
            # Türkçesi, değilse orijinali) gösteriliyor - HABERİN TAMAMI
            # DEĞİL, sadece kaynağın verdiği 1-3 cümlelik özet (telif
            # açısından kaynağa link vermeye devam ediyoruz, tam metni
            # ASLA kazımıyoruz/göstermiyoruz - bkz. PROJE_NOTLARI.md).
            _ozet_goster = _h.get("ozet_tr") or _h.get("ozet") or ""
            if _ozet_goster:
                st.caption(_ozet_goster)
            _cev_not = ""
            if _h.get("baslik_tr"):
                _cev_not = " · Türkçeye çevrildi"
            st.caption(f"{_h.get('kaynak','')} · {_zaman_str}{_kalip_etiket}{_cev_not}")

        if _ilgili:
            st.subheader("Anahtar kelime filtresine takılan haberler")
            st.caption(
                "Bu bölüm bir DEĞERLENDİRME DEĞİL, sadece kaba bir eleme. "
                "Buradaki haberlerin çoğunun piyasayla ilgisi olmayabilir — "
                "listede olmak yalnızca haberin metninde kalıbın anahtar "
                "kelimelerinden biri geçtiği anlamına gelir. Gerçek "
                "değerlendirmeyi AI doğrulaması yapar; Optima Skor'a etki "
                "etmesi için oradan da geçip SİZİN onayınızı alması gerekir."
            )
            for _h in _ilgili:
                with st.container(border=True):
                    _haber_satiri(_h, _isaretli=True)
            st.divider()

        st.subheader("Tüm akış")
        for _h in _digerleri:
            _haber_satiri(_h)

        st.divider()
        st.caption(
            "Kaynaklar: BBC World, Investing.com TR, "
            "BloombergHT, Dünya Gazetesi, Sözcü Ekonomi, Euronews Türkçe, "
            "Halk TV, NPR Business, PBS NewsHour (ABD), Handelsblatt "
            "Finanzen (Almanya), Sky News, BBC Business, Sky News Business "
            "(İngiltere), ABC News Australia (Avustralya), Euronews "
            "(pan-Avrupa), ANSA (İtalya), Meduza (Rusya), Kathimerini "
            "(Yunanistan), El País (İspanya), Kyodo News (Japonya), "
            "Ouest-France (Fransa). Türkçe olmayan kaynaklar (İngilizce, "
            "Almanca, İtalyanca, Rusça, Yunanca, İspanyolca, Japonca, "
            "Fransızca) Türkçeye çevrilir; diğerleri zaten Türkçe yayın "
            "yapar. Çeviri günlük bir AI bütçesine tabidir — bütçe "
            "dolarsa başlık orijinal dilinde kalır, haber izleme durmaz. "
            "Akış 7 gün saklanır."
        )

# ══════════════════════════════════════════════════════════════
# ABONELİK
# ══════════════════════════════════════════════════════════════
# v2.0.7.206 (Bahri'nin talebi, 27 Ağustos 2026 — "diğer aboneler
# artık kendi optima skorlarını son dakika haberlerine göre nasıl
# oluşturabilecekler? ... ayrı bir 'abonelik' menüsü oluştursak mı"):
# v2.0.7.203'te tespit onayı/Optima Skor kişiye özel hale getirilmişti
# ama "Varsayılan Skor" sıfırlama düğmesi SADECE Admin Panel'de
# (admin.py) vardı - admin OLMAYAN aboneler kendi onaylarını
# yönetebilecekleri bir arayüze hiç sahip değildi. Bu sayfa TÜM
# kullanıcılara (admin dahil) açık - herkes SADECE KENDİ onaylarını
# görür/yönetir, admin.py'deki gibi başka bir kullanıcının onayına
# dokunulamaz.
elif page=="Abonelik":
    st.title("Abonelik")
    st.caption(f"{_cur_user['full_name']} — {plan_badge.get(_cur_user['plan'], _cur_user['plan'])}")

    # v2.0.7.214 (Bahri'nin talebi, 29 Ağustos 2026 — "Abonelik
    # Ayarları'na profil bilgileri, iletişim bilgileri, şifre
    # değişikliği eklensin, kalıp ayarları eskisi gibi admin panelinde
    # kalsın"): Kalıp Yönetimi/Haber Akışı Bakımı BİLEREK buraya
    # taşınmadı - admin.py'de kalmaya devam ediyor. Bu sayfaya sadece
    # HER kullanıcının (admin dahil) kendi hesabına yönelik ayarlar
    # eklendi.
    st.divider()
    st.markdown("**Profil Bilgileri**")
    from auth import kullanici_profil_guncelle, kullanici_sifre_degistir
    with st.form("abonelik_profil_form"):
        _yeni_ad = st.text_input("Ad Soyad", value=_cur_user.get("full_name", ""))
        _yeni_tel = st.text_input("Telefon (opsiyonel)", value=_cur_user.get("phone_number") or "",
                                   placeholder="ör. 0555 123 45 67")
        _profil_kaydet = st.form_submit_button("Profili Kaydet")
    if _profil_kaydet:
        if not _yeni_ad.strip():
            st.error("Ad Soyad boş bırakılamaz.")
        elif kullanici_profil_guncelle(_cur_user["id"], _yeni_ad, _yeni_tel):
            st.cache_data.clear()
            st.success("Profil bilgileri güncellendi.")
        else:
            st.error("Güncellenemedi - sunucu hatası (loglara bakılmalı).")

    st.divider()
    st.markdown("**İletişim Bilgileri**")
    st.text_input("E-posta", value=_cur_user.get("email", ""), disabled=True,
                   help="E-posta adresi güvenlik nedeniyle bu sayfadan değiştirilemez.")
    st.caption(
        "E-posta adresiniz giriş kimliğinizdir ve buradan değiştirilemez "
        "- değiştirmeniz gerekiyorsa admin ile iletişime geçin."
    )

    st.divider()
    st.markdown("**Şifre Değiştir**")
    with st.form("abonelik_sifre_form"):
        _eski_sifre = st.text_input("Mevcut Şifre", type="password")
        _yeni_sifre = st.text_input("Yeni Şifre (en az 6 karakter)", type="password")
        _yeni_sifre_tekrar = st.text_input("Yeni Şifre (tekrar)", type="password")
        _sifre_kaydet = st.form_submit_button("Şifreyi Değiştir")
    if _sifre_kaydet:
        if not _eski_sifre or not _yeni_sifre:
            st.error("Tüm alanları doldurun.")
        elif _yeni_sifre != _yeni_sifre_tekrar:
            st.error("Yeni şifreler eşleşmiyor.")
        else:
            _basarili_sifre, _mesaj_sifre = kullanici_sifre_degistir(
                _cur_user["id"], _eski_sifre, _yeni_sifre)
            if _basarili_sifre:
                st.success(_mesaj_sifre)
            else:
                st.error(_mesaj_sifre)

    st.divider()
    st.markdown("**Otomatik Haber Tespiti ve Optima Skor**")
    st.caption(
        "TrendSurf Optima, önemli haberleri tespit edip size onay için "
        "sunar (bkz. Ana Sayfa'daki pop-up ve 'Onay Bekleyen Otomatik "
        "Tespitler' bölümü). Bu tamamen KİŞİSELDİR: bir haberi "
        "onaylamanız SADECE SİZİN Optima Skorunuzu etkiler - diğer "
        "abonelerin skorunu değiştirmez, onlar da aynı haberi kendi "
        "başlarına görüp kendi kararlarını vermek zorundadır."
    )

    try:
        from db import get_onaylanmis_tespitler as _got_abonelik, tum_onaylanan_etkileri_sifirla as _tos_abonelik
        _benim_onaylarim = _got_abonelik(_cur_user["id"]) if _cur_user else []
    except Exception:
        _benim_onaylarim = []

    _ac1, _ac2 = st.columns(2)
    _ac1.metric("Şu an aktif onayınız", len(_benim_onaylarim))

    if _benim_onaylarim:
        with st.expander(f"Aktif onaylarınızın listesi ({len(_benim_onaylarim)})"):
            for _t in _benim_onaylarim:
                st.caption(f"- {_t.get('kalip_key', '')}: {_t.get('haber_basligi', '')}")

    st.divider()
    if st.button("Varsayılan Skor", key="abonelik_varsayilan_skor_btn"):
        _etkilenen_ab = _tos_abonelik(_cur_user["id"] if _cur_user else None)
        if _etkilenen_ab < 0:
            st.error("Sıfırlanamadı - veritabanı hatası (sunucu loglarına bakılmalı).")
        elif _etkilenen_ab == 0:
            st.info("Zaten aktif bir onayınız yoktu - değişiklik yapılmadı.")
        else:
            st.cache_data.clear()
            st.success(
                f"{_etkilenen_ab} onayınız kaldırıldı - Optima Skorunuz "
                f"artık varsayılan (haber etkisi olmayan) haline döndü. "
                f"Bu SADECE sizin skorunuzu etkiledi, diğer abonelerin "
                f"onayları değişmedi.")
    st.caption(
        "Varsayılan Skor: şu an aktif (onayladığınız, süresi dolmamış) "
        "tüm haber tespiti etkilerinizi HEMEN kapatır - geçmiş kayıtlar "
        "silinmez, sadece SİZİN için etkileri durdurulur."
    )

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
                "Word (.docx) olarak indir",
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
