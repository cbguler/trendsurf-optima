"""
TrendSurf Optima — E-posta Rapor Modülü (emailer.py)
"""
import smtplib, json, os, base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    _TR_TZ = ZoneInfo("Europe/Istanbul")
except Exception:
    _TR_TZ = None  # Python < 3.9 fallback (degerlerimiz hep 3.12+)


def _tr_now():
    """Turkiye saatiyle (TRT, UTC+3) anlik datetime.

    Onceki davranis: bare datetime.now() Ubuntu container'da UTC donuyordu,
    mail subject ve body'sinde UTC saati basiliyordu. v1.9.0'dan itibaren
    her zaman TRT.
    """
    if _TR_TZ is not None:
        return datetime.now(_TR_TZ)
    # Python <3.9 fallback (gercekte ortamimiz 3.12, asla buraya dusmemeli)
    from datetime import timezone, timedelta
    return datetime.now(timezone(timedelta(hours=3)))


import pandas as pd

CFG_FILE = "email_config.json"
CSV_PATH = "optimized_universe.csv"

_EMAIL_WIDTH = 900

RISK_W = {
    "Çok Düşük": {"TEFAS": .60, "DOVIZ": .20, "MADEN": .10, "BIST": .08, "KRIPTO": .02},
    "Düşük":     {"TEFAS": .45, "DOVIZ": .15, "MADEN": .15, "BIST": .20, "KRIPTO": .05},
    "Orta":      {"TEFAS": .30, "DOVIZ": .10, "MADEN": .15, "BIST": .35, "KRIPTO": .10},
    "Yüksek":    {"TEFAS": .15, "DOVIZ": .08, "MADEN": .12, "BIST": .45, "KRIPTO": .20},
    "Çok Yüksek":{"TEFAS": .05, "DOVIZ": .05, "MADEN": .10, "BIST": .50, "KRIPTO": .30},
}

# Sütun genişlikleri (px) — toplam ~860px (28px padding her iki taraf)
_COL_W = {
    "kat":    "65",   # Kategori
    "tkr":    "58",   # Ticker
    "ad":     "175",  # Ad (uzun isimler kırpılır)
    "skor":   "42",   # Skor
    "fiyat":  "72",   # Fiyat
    "lot":    "52",   # Lot / Adet
    "tutar":  "82",   # Tutar / Toplam
    "sinyal": "95",   # Sinyal / K/Z
}


def _format_birim(val) -> str:
    """Birim sutunu icin tutarli format (iki tabloda da ayni).

    - Tam sayi ise: integer + binlik ayraci (orn 1,000 / 276 / 2,020)
    - Ondalik varsa: en fazla 4 ondalik, trailing sifir yok (orn 5.06 / 0.4567)

    v1.9.2 sonrasi: Optimizasyon ve Portfoy tablolarinda ayni gorunum.
    """
    try:
        f = float(val)
    except (TypeError, ValueError):
        return str(val)
    if f == int(f):
        return f"{int(f):,}"
    s = f"{f:,.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


# ── Yardımcı ──────────────────────────────────────────────────────────────────

def _logo_b64():
    """Email banner (logo + metin) veya fallback logo dosyasini base64'e cevirir."""
    # Once email banner'i dene
    for p in ["logo_email_clean.png", "logo2.png", "logo.png", "Logo.png"]:
        if os.path.exists(p):
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return None


def _optima_score(row) -> float:
    for col in ["Optima_Skor", "optima_skor", "OptimaSkoru"]:
        if col in row.index and pd.notna(row[col]):
            v = float(row[col])
            if v > 0:
                return v
    rsi   = float(row.get("RSI",   50) or 50)
    ret1m = float(row.get("Ret1M",  0) or  0)
    vol   = float(row.get("Vol",   30) or 30)
    if   40 <= rsi <= 60: rs = 25
    elif 35 <= rsi <= 65: rs = 18
    elif 30 <= rsi < 35 or 65 < rsi <= 70: rs = 10
    else: rs = 0
    if   ret1m >= 30: ms = 35
    elif ret1m >= 20: ms = 30
    elif ret1m >= 10: ms = 24
    elif ret1m >=  5: ms = 18
    elif ret1m >=  0: ms = 10
    elif ret1m >= -5: ms =  4
    else:             ms =  0
    if   vol < 20: vs = 15
    elif vol < 35: vs = 10
    elif vol < 55: vs =  5
    else:          vs =  0
    return min(100, round((rs + ms + vs) * (100.0 / 75.0), 1))


def _sig_color(score: float) -> str:
    if score >= 80: return "#00732f"
    if score >= 60: return "#1a7a3a"
    if score >= 40: return "#8a5e00"
    return "#b71c1c"


def _sig_lbl(score: float) -> str:
    if score >= 80: return "GÜÇLÜ AL"
    if score >= 60: return "KADEMELİ AL"
    if score >= 40: return "TUT İZLE"
    return "SAT"


def _th(text, align="left", width=None):
    w = f"width:{width}px;" if width else ""
    return (f'<th style="{w}padding:6px 8px;text-align:{align};background:#2c3e6b;white-space:nowrap;'
            f'color:#fff;white-space:nowrap;font-size:11px;">{text}</th>')


def _td(val, align="left", bold=False, color=None, extra="", nowrap=False):
    style = (f"padding:6px 8px;border-bottom:1px solid #e8edf5;"
             f"text-align:{align};font-size:11px;vertical-align:middle;"
             + ("white-space:nowrap;" if nowrap else ""))
    if bold:  style += "font-weight:700;"
    if color: style += f"color:{color};"
    if extra: style += extra
    return f'<td style="{style}">{val}</td>'


def _col_group():
    """<colgroup> ile sütun genişliklerini sabitler."""
    w = _COL_W
    return (f'<colgroup>'
            f'<col style="width:{w["kat"]}px"><col style="width:{w["tkr"]}px">'
            f'<col style="width:{w["ad"]}px"><col style="width:{w["skor"]}px">'
            f'<col style="width:{w["fiyat"]}px"><col style="width:{w["lot"]}px">'
            f'<col style="width:{w["tutar"]}px"><col style="width:{w["sinyal"]}px">'
            f'</colgroup>')


# ── Optimizasyon bölümü ───────────────────────────────────────────────────────

def _build_opt_section(df_uni: pd.DataFrame, budget: float,
                       risk: str, max_assets: int) -> str:
    if budget <= 0 or df_uni.empty:
        return ""

    w = RISK_W.get(risk, RISK_W["Orta"])
    MIN_SKOR = 60.0

    # Her kategori için havuz oluştur
    cat_pools = {}
    skipped_cats = []  # Agirligi >0 ama AL sinyali bulunmayan kategoriler
    for cat, weight in w.items():
        if weight <= 0:
            continue
        if cat == "TEFAS":
            df_c = df_uni[(df_uni["Kategori"] == cat) & (df_uni["Ret1M"] != 0)].copy()
        else:
            df_c = df_uni[(df_uni["Kategori"] == cat) & (df_uni["Son_Fiyat"] > 0)].copy()
        if df_c.empty:
            skipped_cats.append(cat)
            continue
        df_c["_skor"] = df_c.apply(_optima_score, axis=1)
        df_c = df_c[(df_c["Ret1M"] > 0) & (df_c["_skor"] >= MIN_SKOR)]
        df_c = df_c.sort_values("_skor", ascending=False)
        if not df_c.empty:
            cat_pools[cat] = df_c
        else:
            skipped_cats.append(cat)

    if not cat_pools:
        return ""

    n_cats      = len(cat_pools)
    max_per_cat = max(1, max_assets // n_cats)

    # Kalite ağırlıklı bütçe dağılımı
    adj_weights = {}
    total_adj   = 0.0
    for cat, weight in w.items():
        if cat not in cat_pools:
            continue
        quality = float(cat_pools[cat]["_skor"].head(max_per_cat).mean()) / 100.0
        adj = weight * quality
        adj_weights[cat] = adj
        total_adj += adj
    if total_adj > 0:
        adj_weights = {c: a / total_adj for c, a in adj_weights.items()}

    # Seçilen varlıkları topla
    selected = []
    for cat, weight in adj_weights.items():
        sample  = cat_pools[cat].head(max_per_cat)
        cat_bud = budget * weight
        per     = cat_bud / len(sample)
        for _, row in sample.iterrows():
            price  = float(row["Son_Fiyat"]) if float(row.get("Son_Fiyat", 0)) > 0 else 1.0
            lot    = int(per / price) if price > 0 else 0
            gercek = round(lot * price, 2)
            skor   = float(row["_skor"])
            selected.append({
                "cat": cat, "row": row, "price": price,
                "lot": lot, "gercek": gercek, "skor": skor
            })

    # max_assets'e tam ulaşmak için eksik yerleri doldur
    if len(selected) < max_assets:
        already = {(s["cat"], s["row"]["Ticker"]) for s in selected}
        for cat in cat_pools:
            for _, row in cat_pools[cat].iterrows():
                if len(selected) >= max_assets:
                    break
                if (cat, row["Ticker"]) in already:
                    continue
                price  = float(row.get("Son_Fiyat", 0)) if float(row.get("Son_Fiyat", 0)) > 0 else 1.0
                skor   = float(row["_skor"])
                per    = budget / max_assets
                lot    = int(per / price) if price > 0 else 0
                gercek = round(lot * price, 2)
                selected.append({"cat": cat, "row": row, "price": price,
                                  "lot": lot, "gercek": gercek, "skor": skor})

    # Skora göre azalan sırala — en iyi varlık her zaman en üstte
    selected.sort(key=lambda x: x["skor"], reverse=True)

    rows_html   = ""
    grand_total = 0.0

    for s in selected:
        row    = s["row"]
        cat    = s["cat"]
        price  = s["price"]
        lot    = s["lot"]
        gercek = s["gercek"]
        skor   = s["skor"]
        sc     = _sig_color(skor)
        sl     = _sig_lbl(skor)
        ad_str = str(row.get("Ad", row["Ticker"]))[:38]
        grand_total += gercek

        rows_html += f"""<tr>
          {_td(f'<span style="font-size:10px;color:#6c7a9c">{cat}</span>')}
          {_td(f"<b>{row['Ticker']}</b>", nowrap=True)}
          {_td(ad_str)}
          {_td(f"<b>{skor:.0f}</b>", "right")}
          {_td(f"{price:,.4f}", "right", nowrap=True)}
          {_td(_format_birim(lot), "right", bold=True, nowrap=True)}
          {_td(f"{gercek:,.2f}&nbsp;₺", "right", bold=True, nowrap=True)}
          {_td(f'<span style="background:{sc}20;color:{sc};padding:2px 6px;'
               f'border-radius:5px;font-size:10px;font-weight:700;'
               f'white-space:nowrap">{_email_sig(sl)}</span>', "center")}
        </tr>"""

    if not rows_html:
        return ""

    # v1.8 - Butce dagildi banner'i (Streamlit Ana Sayfa ile ayni davranis)
    banner_html = ""
    if skipped_cats:
        banner_html = f"""
    <div style="background:#fff8e1;border-left:4px solid #f0a830;
                padding:10px 12px;margin:10px 0 0 0;font-size:11px;color:#5a4a1a;
                border-radius:4px;">
      <b>Bütçe Dağılımı Notu:</b> Şu kategorilerde yeterli AL sinyalli varlık
      bulunamadığı için bütçe diğer kategorilere dağıtıldı:
      <b>{', '.join(skipped_cats)}</b>
    </div>"""

    return f"""
    <h2 style="color:#1b2a4a;margin:24px 0 10px 0;font-size:15px;
               border-left:4px solid #2c3e6b;padding-left:10px;">
      Portföy Optimizasyonu &mdash; {budget:,.0f}&nbsp;₺ &nbsp;|&nbsp; Risk: {risk}
    </h2>{banner_html}
    <div style="overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%;">
<table style="width:100%;border-collapse:collapse;background:#fff;
                  font-size:12px;table-layout:fixed;min-width:560px;">
      {_col_group()}
      <thead><tr>
        {_th("Kategori", "left",   _COL_W["kat"])}
        {_th("Ticker",   "left",   _COL_W["tkr"])}
        {_th("Ad",       "left",   _COL_W["ad"])}
        {_th("Skor",     "right",  _COL_W["skor"])}
        {_th("Fiyat",    "right",  _COL_W["fiyat"])}
        {_th("Birim",    "right",  _COL_W["lot"])}
        {_th("Toplam",   "right",  _COL_W["tutar"])}
        {_th("Sinyal",   "center", _COL_W["sinyal"])}
      </tr></thead>
      <tbody>{rows_html}</tbody>
      <tfoot>
        <tr style="background:#f4f6fb;border-top:2px solid #1b2a4a;">
          <td colspan="6" style="padding:8px 10px;font-size:11px;
              color:#1b2a4a;font-weight:700;text-align:right;">Genel Toplam:</td>
          <td style="padding:8px 10px;font-size:12px;color:#1b2a4a;
              font-weight:700;text-align:right;white-space:nowrap;">
              {grand_total:,.2f}&nbsp;₺</td>
          <td style="padding:8px 10px;font-size:10px;color:#9aa8c0;
              text-align:center;">{len(selected)} varlık</td>
        </tr>
      </tfoot>
    </table>
</div>
    <p style="font-size:10px;color:#9aa8c0;margin-top:6px;font-style:italic;">
      Yatırım tavsiyesi değildir.
    </p>"""


# ── Portföy bölümü ────────────────────────────────────────────────────────────

def _build_portfolio_section(portfolio: list, df_uni: pd.DataFrame) -> str:
    if not portfolio:
        return """
    <h2 style="color:#1b2a4a;margin:24px 0 10px 0;font-size:15px;
               border-left:4px solid #2c3e6b;padding-left:10px;
               page-break-before:always;">Portföy Durumu</h2>
    <p style="color:#9aa8c0;font-size:12px;font-style:italic;">
      Henüz portföye pozisyon eklenmemiş.
    </p>"""

    rows_html = ""
    pf_total  = 0.0
    pf_pnl    = 0.0

    for pos in portfolio:
        tkr  = str(pos.get("ticker", "")).strip()
        adet = float(pos.get("quantity", pos.get("adet", 0)) or 0)
        mal  = float(pos.get("avg_cost", pos.get("maliyet", 0)) or 0)

        match   = df_uni[df_uni["Ticker"] == tkr]
        cur     = float(match["Son_Fiyat"].iloc[0]) if not match.empty else 0.0
        ad_name = str(match["Ad"].iloc[0])[:38] if (not match.empty and "Ad" in match.columns) else tkr
        cat     = str(match["Kategori"].iloc[0]) if not match.empty else str(pos.get("asset_type", "—"))

        skor = 0.0
        if not match.empty:
            skor = _optima_score(match.iloc[0])
        sc  = _sig_color(skor)
        sl  = _sig_lbl(skor) if skor > 0 else "—"

        pnl_pct = round((cur / mal - 1) * 100, 2) if mal > 0 and cur > 0 else 0.0
        toplam  = round(cur * adet, 2)
        pnl_try = round((cur - mal) * adet, 2)
        pf_total += toplam
        pf_pnl   += pnl_try
        clr = "#00732f" if pnl_pct >= 0 else "#b71c1c"

        # K/Z bilgisini Toplam sutununun icinde kucuk alt-satir olarak goster
        # (Boylelikle K/Z ayri sutun gerektirmez, son sutun Sinyal olur)
        toplam_cell = (
            f'<b>{toplam:,.2f}&nbsp;₺</b><br>'
            f'<span style="color:{clr};font-size:10px;font-weight:700;">'
            f'{pnl_pct:+.2f}%&nbsp;&nbsp;{pnl_try:+,.2f}&nbsp;₺</span>'
        )

        rows_html += f"""<tr>
          {_td(f'<span style="font-size:10px;color:#6c7a9c">{cat}</span>')}
          {_td(f"<b>{tkr}</b>", nowrap=True)}
          {_td(ad_name)}
          {_td(f"<b>{skor:.0f}</b>" if skor > 0 else "—", "right")}
          {_td(f"{cur:,.4f}", "right", nowrap=True)}
          {_td(_format_birim(adet), "right", bold=True, nowrap=True)}
          {_td(toplam_cell, "right", nowrap=True)}
          {_td(f'<span style="background:{sc}20;color:{sc};padding:2px 6px;'
               f'border-radius:5px;font-size:10px;font-weight:700;'
               f'white-space:nowrap">{_email_sig(sl) if skor > 0 else "—"}</span>',
               "center")}
        </tr>"""

    if not rows_html:
        return ""

    pf_color = "#00732f" if pf_pnl >= 0 else "#b71c1c"

    # Genel Toplam icin K/Z'yi de tek satirda goster (Toplam sutununda)
    pf_total_cell = (
        f'<b>{pf_total:,.2f}&nbsp;₺</b><br>'
        f'<span style="color:{pf_color};font-size:10px;font-weight:700;">'
        f'K/Z: {pf_pnl:+,.2f}&nbsp;₺</span>'
    )

    return f"""
    <h2 style="color:#1b2a4a;margin:24px 0 10px 0;font-size:15px;
               border-left:4px solid #2c3e6b;padding-left:10px;
               page-break-before:always;">Portföy Durumu</h2>
    <div style="overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%;">
<table style="width:100%;border-collapse:collapse;background:#fff;
                  font-size:12px;table-layout:fixed;min-width:560px;">
      {_col_group()}
      <thead><tr>
        {_th("Kategori",  "left",   _COL_W["kat"])}
        {_th("Ticker",    "left",   _COL_W["tkr"])}
        {_th("Ad",        "left",   _COL_W["ad"])}
        {_th("Skor",      "right",  _COL_W["skor"])}
        {_th("Fiyat",     "right",  _COL_W["fiyat"])}
        {_th("Birim",     "right",  _COL_W["lot"])}
        {_th("Toplam",    "right",  _COL_W["tutar"])}
        {_th("Sinyal",    "center", _COL_W["sinyal"])}
      </tr></thead>
      <tbody>{rows_html}</tbody>
      <tfoot>
        <tr style="background:#f4f6fb;border-top:2px solid #1b2a4a;">
          <td colspan="6" style="padding:8px 10px;font-size:11px;
              color:#1b2a4a;font-weight:700;text-align:right;">Genel Toplam:</td>
          <td style="padding:8px 10px;text-align:right;white-space:nowrap;
              font-size:12px;color:#1b2a4a;">{pf_total_cell}</td>
          <td style="padding:8px 10px;"></td>
        </tr>
      </tfoot>
    </table>
</div>"""


# ── Ana HTML ──────────────────────────────────────────────────────────────────

def build_html(df_uni: pd.DataFrame, portfolio: list,
               budget: float = 0, risk: str = "Orta",
               max_assets: int = 10) -> str:

    now      = _tr_now().strftime("%d.%m.%Y  %H:%M")
    logo_b64 = _logo_b64()

    if logo_b64:
        logo_tag = (
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'width="220" height="198" '
            f'style="display:block;width:220px;height:198px;border:0;max-width:100%;" '
            f'alt="TrendSurf Optima">'
        )
    else:
        logo_tag = (
            '<span style="font-size:22px;font-weight:900;color:#1b2a4a;">TREND</span>'
            '<span style="font-size:22px;font-weight:900;color:#2ecc71;">SURF</span>'
        )

    opt_section = _build_opt_section(df_uni, budget, risk, max_assets)
    pf_section  = _build_portfolio_section(portfolio, df_uni)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>TrendSurf Optima Raporu</title>
</head>
<body style="margin:0;padding:0;background:#f0f4f8;
             font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#f0f4f8;">
<tr><td align="center" style="padding:20px 10px;">
<table width="{_EMAIL_WIDTH}" cellpadding="0" cellspacing="0"
       style="max-width:{_EMAIL_WIDTH}px;width:100%;background:#fff;
              border-radius:10px;overflow:hidden;
              box-shadow:0 2px 12px rgba(0,0,0,.10);">

  <!-- HEADER -->
  <tr><td style="background:#ffffff;padding:10px 24px;
                 border-bottom:3px solid #2c3e6b;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:middle;width:240px;">{logo_tag}</td>
      <td style="text-align:right;vertical-align:middle;">
        <span style="font-size:11px;color:#6c7a9c;">Finansal Rapor</span><br>
        <span style="font-size:13px;font-weight:700;color:#1b2a4a;">{now}</span>
      </td>
    </tr></table>
  </td></tr>

  <!-- İÇERİK -->
  <tr><td style="padding:20px 28px;">
    {opt_section}
    {pf_section}
    <p style="color:#b0bac8;font-size:10px;margin-top:24px;
              border-top:1px solid #e8edf5;padding-top:12px;
              text-align:center;">
      Bu rapor Bahri Güler'in geliştirdiği, <b>TrendSurf Optima</b> tarafından
      otomatik olarak oluşturulmuştur. Yatırım tavsiyesi değildir.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Gönderici ─────────────────────────────────────────────────────────────────

def _email_sig(sig: str) -> str:
    """Email için sinyal kısaltması."""
    return {"GÜÇLÜ AL": "GÜ.AL", "KADEMELİ AL": "KAD.AL",
            "TUT İZLE": "TUT", "SAT": "SAT", "NET SAT": "N.SAT"}.get(sig, sig)


def send_report(df_uni: pd.DataFrame = None, portfolio: list = None,
                budget: float = 0, risk: str = "Orta", max_assets: int = 10,
                cfg: dict = None, user_email: str = None):
    """E-posta raporu gonder.

    Args:
        user_email: Eger portfolio=None ise, sadece bu kullanicinin portfoyunu
                    DB'den oku. Bos birakirsa hicbir kullanicinin portfoyu cekilmez.
                    Onceki davranis: tum kullanicilarin portfoyu okunuyordu (yanlis).
    """

    if cfg is None:
        cfg = {}
        if os.path.exists(CFG_FILE):
            with open(CFG_FILE) as f:
                cfg = json.load(f)
        # Streamlit Secrets fallback (Cloud reboots sonrası kalıcılık)
        if not cfg:
            try:
                import streamlit as _st
                _s = _st.secrets.get("email", {})
                if _s.get("smtp_user"):
                    cfg = dict(_s)
            except Exception:
                pass

    to_addr   = cfg.get("address",   "")
    smtp_host = cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(cfg.get("smtp_port", 587))
    smtp_user = cfg.get("smtp_user", "")
    smtp_pass = cfg.get("smtp_pass", "")

    if not to_addr or not smtp_user:
        raise ValueError("E-posta ayarlari eksik. app.py sidebar'dan ayarlayin.")

    if df_uni is None:
        df_uni = pd.read_csv(CSV_PATH) if os.path.exists(CSV_PATH) else pd.DataFrame()

    if portfolio is None:
        # Sadece user_email verildiyse o kullanicinin portfoyunu cek.
        # Aksi halde bos kalsin - tum kullanicilari karistirmak yanlis olur.
        if user_email:
            try:
                from db import get_conn
                conn = get_conn()
                rows = conn.execute(
                    "SELECT p.ticker, p.quantity, p.avg_cost, p.asset_type, p.note "
                    "FROM portfolio p JOIN users u ON p.user_id = u.id "
                    "WHERE LOWER(u.email) = LOWER(?) "
                    "ORDER BY p.added_at DESC",
                    (user_email,)
                ).fetchall()
                conn.close()
                portfolio = [dict(r) for r in rows]
            except Exception as _e:
                print(f"[emailer] Portfoy DB okuma hatasi: {_e}")
                portfolio = []
        else:
            portfolio = []

    html = build_html(df_uni, portfolio, budget, risk, max_assets)
    now  = _tr_now().strftime("%d.%m.%Y %H:%M")

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"TrendSurf Optima — Finansal Rapor {now}"
    msg["From"]    = smtp_user
    msg["To"]      = to_addr
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as s:
        s.ehlo()
        s.starttls()
        s.login(smtp_user, smtp_pass)
        s.sendmail(smtp_user, to_addr, msg.as_string())

    print(f"[{now}] E-posta gonderildi -> {to_addr}")


if __name__ == "__main__":
    send_report()
