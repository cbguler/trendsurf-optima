"""
TrendSurf Optima — E-posta Rapor Modülü (emailer.py)
Kullanim : python emailer.py   (manuel test)
Otomatik : Windows Gorev Zamanlayici ile her gun 08:30 ve 11:30'da calistir
"""
import smtplib, json, os, base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
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

# ── Yardımcı ──────────────────────────────────────────────────────────────────

def _logo_b64():
    for p in ["logo.png", "Logo.png", "LOGO.PNG"]:
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


def _th(text, align="left"):
    return (f'<th style="padding:8px 12px;text-align:{align};background:#2c3e6b;'
            f'color:#fff;white-space:nowrap;font-size:11px;">{text}</th>')


def _td(val, align="left", bold=False, color=None, extra=""):
    style = f"padding:7px 12px;border-bottom:1px solid #e8edf5;text-align:{align};font-size:12px;"
    if bold:  style += "font-weight:700;"
    if color: style += f"color:{color};"
    if extra: style += extra
    return f'<td style="{style}">{val}</td>'


# ── Optimizasyon bölümü ───────────────────────────────────────────────────────

def _build_opt_section(df_uni: pd.DataFrame, budget: float,
                       risk: str, max_assets: int) -> str:
    """
    Portföy Optimizasyonu tablosu.
    Sütunlar: Kategori | Ticker | Ad | Skor | Fiyat | Lot | Tutar | Sinyal
    (RSI, 1A%, Kat.Pay% e-postadan çıkarıldı)
    """
    if budget <= 0 or df_uni.empty:
        return ""

    w = RISK_W.get(risk, RISK_W["Orta"])
    MIN_SKOR = 60.0

    cat_pools = {}
    for cat, weight in w.items():
        if weight <= 0:
            continue
        if cat == "TEFAS":
            df_c = df_uni[(df_uni["Kategori"] == cat) & (df_uni["Ret1M"] != 0)].copy()
        else:
            df_c = df_uni[(df_uni["Kategori"] == cat) & (df_uni["Son_Fiyat"] > 0)].copy()
        if df_c.empty:
            continue
        df_c["_skor"] = df_c.apply(_optima_score, axis=1)
        df_c = df_c[(df_c["Ret1M"] > 0) & (df_c["_skor"] >= MIN_SKOR)]
        df_c = df_c.sort_values("_skor", ascending=False)
        if not df_c.empty:
            cat_pools[cat] = df_c

    if not cat_pools:
        return ""

    n_cats      = len(cat_pools)
    max_per_cat = max(1, max_assets // n_cats)

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

    rows_html   = ""
    grand_total = 0.0
    row_count   = 0

    for cat, weight in adj_weights.items():
        sample  = cat_pools[cat].head(max_per_cat)
        cat_bud = budget * weight
        per     = cat_bud / len(sample)

        for _, row in sample.iterrows():
            price  = float(row["Son_Fiyat"]) if float(row.get("Son_Fiyat", 0)) > 0 else 1.0
            lot    = int(per / price) if price > 0 else 0
            gercek = round(lot * price, 2)
            skor   = float(row["_skor"])
            sc     = _sig_color(skor)
            sl     = _sig_lbl(skor)
            ad_str = str(row.get("Ad", row["Ticker"]))[:40]
            grand_total += gercek
            row_count   += 1

            rows_html += f"""<tr>
              {_td(f'<span style="font-size:10px;color:#6c7a9c">{cat}</span>')}
              {_td(f"<b>{row['Ticker']}</b>")}
              {_td(ad_str)}
              {_td(f"<b>{skor:.0f}</b>", "right")}
              {_td(f"{price:,.4f}", "right")}
              {_td(str(lot), "right", bold=True)}
              {_td(f"{gercek:,.2f} ₺", "right", bold=True)}
              {_td(f'<span style="background:{sc}20;color:{sc};padding:2px 7px;'
                   f'border-radius:6px;font-size:10px;font-weight:700;'
                   f'white-space:nowrap">{sl}</span>', "center")}
            </tr>"""

    if not rows_html:
        return ""

    return f"""
    <h2 style="color:#1b2a4a;margin:24px 0 10px 0;font-size:15px;
               border-left:4px solid #2c3e6b;padding-left:10px;">
      Portföy Optimizasyonu &mdash; {budget:,.0f} ₺ &nbsp;|&nbsp; Risk: {risk}
    </h2>
    <table style="width:100%;border-collapse:collapse;background:#fff;font-size:12px;">
      <thead><tr>
        {_th("Kategori")}{_th("Ticker")}{_th("Ad")}
        {_th("Skor","right")}{_th("Fiyat","right")}
        {_th("Lot","right")}{_th("Tutar","right")}{_th("Sinyal","center")}
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    <p style="font-size:11px;color:#9aa8c0;margin-top:6px;">
      Toplam: <b style="color:#1b2a4a">{grand_total:,.2f} ₺</b> &nbsp;|&nbsp;
      {row_count} varlık önerildi. Yatırım tavsiyesi değildir.
    </p>"""


# ── Portföy bölümü ────────────────────────────────────────────────────────────

def _build_portfolio_section(portfolio: list, df_uni: pd.DataFrame) -> str:
    """
    Portföy durumu tablosu — Optimizasyon tablosuyla aynı sütun yapısı.
    Sütunlar: Kategori | Ticker | Ad | Skor | Fiyat (Güncel) | Adet | Toplam | K/Z
    """
    rows_html = ""

    if not portfolio:
        return """
    <h2 style="color:#1b2a4a;margin:24px 0 10px 0;font-size:15px;
               border-left:4px solid #2c3e6b;padding-left:10px;">Portföy Durumu</h2>
    <p style="color:#9aa8c0;font-size:12px;font-style:italic;">
      Henüz portföye pozisyon eklenmemiş.
    </p>"""


    pf_total  = 0.0
    pf_pnl    = 0.0

    for pos in portfolio:
        tkr  = str(pos.get("ticker", "")).strip()
        adet = float(pos.get("quantity", pos.get("adet", 0)) or 0)
        mal  = float(pos.get("avg_cost", pos.get("maliyet", 0)) or 0)

        match   = df_uni[df_uni["Ticker"] == tkr]
        cur     = float(match["Son_Fiyat"].iloc[0]) if not match.empty else 0.0
        ad_name = str(match["Ad"].iloc[0])[:40] if (not match.empty and "Ad" in match.columns) else tkr
        cat     = str(match["Kategori"].iloc[0]) if not match.empty else str(pos.get("asset_type", "—"))

        # Optima skoru CSV'den al
        skor = 0.0
        if not match.empty:
            skor = _optima_score(match.iloc[0])
        sc = _sig_color(skor)
        sl = _sig_lbl(skor) if skor > 0 else "—"

        pnl_pct = round((cur / mal - 1) * 100, 2) if mal > 0 and cur > 0 else 0.0
        toplam  = round(cur * adet, 2)
        pnl_try = round((cur - mal) * adet, 2)
        pf_total += toplam
        pf_pnl   += pnl_try
        clr = "#00732f" if pnl_pct >= 0 else "#b71c1c"

        rows_html += f"""<tr>
          {_td(f'<span style="font-size:10px;color:#6c7a9c">{cat}</span>')}
          {_td(f"<b>{tkr}</b>")}
          {_td(ad_name)}
          {_td(f"<b>{skor:.0f}</b>" if skor > 0 else "—", "right")}
          {_td(f"{cur:,.4f}", "right")}
          {_td(f"{adet:,.4f}", "right")}
          {_td(f"{toplam:,.2f} ₺", "right", bold=True)}
          {_td(f'<span style="color:{clr};font-weight:700">{pnl_pct:+.2f}%</span><br>'
               f'<span style="color:{clr};font-size:10px">{pnl_try:+,.2f} ₺</span>', "right")}
        </tr>"""

    if not rows_html:
        return ""

    pf_color = "#00732f" if pf_pnl >= 0 else "#b71c1c"

    return f"""
    <h2 style="color:#1b2a4a;margin:24px 0 10px 0;font-size:15px;
               border-left:4px solid #2c3e6b;padding-left:10px;">Portföy Durumu</h2>
    <table style="width:100%;border-collapse:collapse;background:#fff;font-size:12px;">
      <thead><tr>
        {_th("Kategori")}{_th("Ticker")}{_th("Ad")}
        {_th("Skor","right")}{_th("Güncel Fiyat","right")}
        {_th("Adet","right")}{_th("Toplam","right")}{_th("K/Z","right")}
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    <p style="font-size:12px;margin-top:8px;color:#4a5a7a;">
      <b>Toplam Değer:</b> {pf_total:,.2f} ₺ &nbsp;|&nbsp;
      <b style="color:{pf_color}">Kar / Zarar: {pf_pnl:+,.2f} ₺</b>
    </p>"""


# ── Ana HTML ──────────────────────────────────────────────────────────────────

def build_html(df_uni: pd.DataFrame, portfolio: list,
               budget: float = 0, risk: str = "Orta",
               max_assets: int = 10) -> str:

    now      = datetime.now().strftime("%d.%m.%Y  %H:%M")
    logo_b64 = _logo_b64()

    # Logo: varsa küçük, beyaz zemine uygun; yoksa sade metin
    if logo_b64:
        logo_tag = (f'<img src="data:image/png;base64,{logo_b64}" '
                    f'style="height:32px;max-width:120px;display:block;" alt="TrendSurf Optima">')
    else:
        logo_tag = '<span style="font-size:18px;font-weight:800;color:#1b2a4a;letter-spacing:1px;">TrendSurf Optima</span>'

    opt_section = _build_opt_section(df_uni, budget, risk, max_assets)
    pf_section  = _build_portfolio_section(portfolio, df_uni)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>TrendSurf Optima Raporu</title>
</head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;">
<tr><td align="center" style="padding:20px 10px;">
<table width="{_EMAIL_WIDTH}" cellpadding="0" cellspacing="0"
       style="max-width:{_EMAIL_WIDTH}px;width:100%;background:#fff;
              border-radius:10px;overflow:hidden;
              box-shadow:0 2px 12px rgba(0,0,0,.10);">

  <!-- HEADER: sade, açık zemin -->
  <tr><td style="background:#f8faff;padding:18px 28px;
                 border-bottom:3px solid #2c3e6b;text-align:left;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td>{logo_tag}</td>
      <td style="text-align:right;vertical-align:middle;">
        <span style="font-size:12px;color:#6c7a9c;">Finansal Rapor</span><br>
        <span style="font-size:13px;font-weight:700;color:#1b2a4a;">{now}</span>
      </td>
    </tr></table>
  </td></tr>

  <!-- İÇERİK -->
  <tr><td style="padding:20px 28px;">
    {opt_section}
    {pf_section}
    <p style="color:#b0bac8;font-size:10px;margin-top:24px;
              border-top:1px solid #e8edf5;padding-top:12px;text-align:center;">
      Bu rapor <b>TrendSurf Optima</b> tarafından otomatik olarak oluşturulmuştur.
      Yatırım tavsiyesi değildir.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Gönderici ─────────────────────────────────────────────────────────────────

def send_report(df_uni: pd.DataFrame = None, portfolio: list = None,
                budget: float = 0, risk: str = "Orta", max_assets: int = 10):

    cfg = {}
    if os.path.exists(CFG_FILE):
        with open(CFG_FILE) as f:
            cfg = json.load(f)

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
        try:
            from db import get_conn
            conn = get_conn()
            rows = conn.execute(
                "SELECT ticker, quantity, avg_cost, asset_type, note "
                "FROM portfolio ORDER BY added_at DESC"
            ).fetchall()
            conn.close()
            portfolio = [dict(r) for r in rows]
        except Exception:
            portfolio = []

    html = build_html(df_uni, portfolio, budget, risk, max_assets)
    now  = datetime.now().strftime("%d.%m.%Y %H:%M")

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
