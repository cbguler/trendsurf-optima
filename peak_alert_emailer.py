"""
TrendSurf Optima - Peak Alert Emailer Modulu (peak_alert_emailer.py)
v2.0 Asama 3b: Kar Realizasyonu Uyari Sistemi - mail gonderim

Bu modul peak_tracker.evaluate_user_alerts'in dondurdugu alerts_pending
listesini kullanicinin KENDI e-posta adresine (users.email) HTML mail
olarak gonderir.

Onemli: Bahri'nin kararina gore uyari maili kullanicinin kendi adresine
gider (Serdar'a Bahri'nin portfoy uyarisi gitmez). Multi-user mantigi.

SMTP config: Streamlit Secrets'tan ([email] bolumu).
Mail formatı emailer.py'den BAGIMSIZ - kendi HTML template'i.
"""
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from db import get_conn


def _get_user_email(user_id: int) -> str:
    """users tablosundan kullanicinin login email'ini cek."""
    try:
        conn = get_conn()
        row = conn.execute(
            "SELECT email FROM users WHERE id=?",
            (user_id,)
        ).fetchone()
        if row and row[0]:
            return str(row[0])
        return ""
    except Exception as e:
        sys.stderr.write(f"[peak_alert_emailer] email cek hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return ""


def _get_smtp_config() -> dict:
    """Streamlit Secrets'tan SMTP config."""
    try:
        import streamlit as _st
        _s = _st.secrets.get("email", {})
        return {
            "smtp_host": _s.get("smtp_host", "smtp.gmail.com"),
            "smtp_port": int(_s.get("smtp_port", 587)),
            "smtp_user": _s.get("smtp_user", ""),
            "smtp_pass": _s.get("smtp_pass", ""),
        }
    except Exception as e:
        sys.stderr.write(f"[peak_alert_emailer] smtp config hatasi: {e}\n")
        sys.stderr.flush()
        return {"smtp_host": "smtp.gmail.com", "smtp_port": 587,
                "smtp_user": "", "smtp_pass": ""}


def _tr_now() -> datetime:
    """Turkiye saati (TRT, UTC+3)."""
    return datetime.now(timezone(timedelta(hours=3)))


def _fmt_tr_num(v: float, dec: int = 4) -> str:
    """Turk sayi formati: 1.234,5670"""
    if v is None:
        return "—"
    try:
        s = f"{float(v):,.{dec}f}"
        # ABD formati -> TR formati: 1,234.56 -> 1.234,56
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


def _fmt_tr_pct(v: float) -> str:
    """%2,34 formati."""
    if v is None:
        return "—"
    try:
        s = f"{float(v):.2f}"
        return f"%{s.replace('.', ',')}"
    except (TypeError, ValueError):
        return "—"


def _build_alert_html(user_email: str, alerts_pending: list,
                      settings: dict) -> str:
    """Uyari mailinin HTML govdesini olustur.

    Tek bir mail icinde tum uyariyan tickerlar tablo halinde yer alir.
    """
    now_str = _tr_now().strftime("%d.%m.%Y %H:%M")
    threshold_str = _fmt_tr_pct(settings.get("threshold_pct", 3.0))

    mode_label = {
        "peak_break": "Peak kırıldıkça",
        "once":       "Bir kez gönder ve sus",
        "hourly":     "Saatte bir tekrarla",
    }.get(settings.get("alert_mode", "peak_break"), "Peak kırıldıkça")

    formul_label = {
        "peak_minus_threshold": "Peak x (1 - threshold)",
        "current_price":        "Şu anki fiyat",
        "info_only":            "Sadece bilgi (tavsiye fiyat yok)",
    }.get(settings.get("emir_formul", "peak_minus_threshold"),
          "Peak x (1 - threshold)")

    # Tablo satirlari
    rows_html = ""
    for a in alerts_pending:
        ticker      = a.get("ticker", "")
        kategori    = a.get("asset_type", "")
        alish       = _fmt_tr_num(a.get("alish_fiyat"), 4)
        peak        = _fmt_tr_num(a.get("peak_price"), 4)
        current     = _fmt_tr_num(a.get("current_price"), 4)
        drop_pct    = _fmt_tr_pct(a.get("drop_pct"))
        tavsi       = _fmt_tr_num(a.get("tavsiye_fiyat"), 4)
        miktar      = _fmt_tr_num(a.get("miktar"), 4)
        unit        = a.get("unit_type", "")
        toplam      = _fmt_tr_num(a.get("toplam_deger"), 2)
        tavsi_disp  = tavsi if a.get("tavsiye_fiyat", 0) > 0 else "—"

        rows_html += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
            <td style="padding:10px 12px;font-weight:700;color:#1b2a4a;">{ticker}</td>
            <td style="padding:10px 12px;color:#6c7a9c;font-size:12px;">{kategori}</td>
            <td style="padding:10px 12px;text-align:right;">{alish}</td>
            <td style="padding:10px 12px;text-align:right;font-weight:700;color:#0d9488;">{peak}</td>
            <td style="padding:10px 12px;text-align:right;font-weight:700;">{current}</td>
            <td style="padding:10px 12px;text-align:right;color:#dc2626;font-weight:700;">{drop_pct}</td>
            <td style="padding:10px 12px;text-align:right;color:#2563eb;font-weight:700;">{tavsi_disp}</td>
            <td style="padding:10px 12px;text-align:right;color:#6c7a9c;">{miktar} {unit}</td>
            <td style="padding:10px 12px;text-align:right;font-weight:700;">{toplam} TL</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrendSurf Optima - Kar Realizasyonu Uyarısı</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <div style="max-width:900px;margin:24px auto;background:#ffffff;border-radius:12px;
                box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">

        <div style="background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);
                    padding:24px 30px;color:#fff;">
            <div style="font-size:22px;font-weight:800;letter-spacing:0.5px;">
                TrendSurf Optima
            </div>
            <div style="font-size:14px;opacity:0.9;margin-top:4px;">
                Kar Realizasyonu Uyarısı
            </div>
        </div>

        <div style="padding:24px 30px;">
            <p style="margin:0 0 14px;font-size:15px;color:#1b2a4a;line-height:1.5;">
                Sayın yatırımcı, portföyünüzdeki aşağıdaki <strong>{len(alerts_pending)} varlık</strong>
                için peak fiyatından <strong>{threshold_str}</strong> veya daha fazla düşüş tespit edildi.
                Kâr realizasyonu için satış emri vermeyi değerlendirebilirsiniz.
            </p>

            <div style="margin:18px 0;padding:14px 16px;background:#fef3c7;
                        border-left:4px solid #f59e0b;border-radius:6px;font-size:13px;color:#78350f;">
                <strong>Önemli:</strong> Bu sistem otomatik bir uyarıdır.
                Nihai satış kararı tamamen size aittir. Tavsiye edilen emir fiyatı,
                seçtiğiniz formüle göre hesaplanır ({formul_label}); piyasa koşullarına
                göre değişebilir.
            </div>

            <div style="overflow-x:auto;margin-top:20px;">
                <table style="width:100%;border-collapse:collapse;font-size:13px;
                              background:#fff;border:1px solid #e5e7eb;border-radius:8px;
                              overflow:hidden;">
                    <thead>
                        <tr style="background:#f9fafb;color:#374151;text-align:left;
                                   font-size:12px;text-transform:uppercase;letter-spacing:0.5px;">
                            <th style="padding:12px;font-weight:700;">Ticker</th>
                            <th style="padding:12px;font-weight:700;">Kategori</th>
                            <th style="padding:12px;font-weight:700;text-align:right;">Alış</th>
                            <th style="padding:12px;font-weight:700;text-align:right;">Peak</th>
                            <th style="padding:12px;font-weight:700;text-align:right;">Şu Anki</th>
                            <th style="padding:12px;font-weight:700;text-align:right;">Düşüş</th>
                            <th style="padding:12px;font-weight:700;text-align:right;">Tavsiye</th>
                            <th style="padding:12px;font-weight:700;text-align:right;">Miktar</th>
                            <th style="padding:12px;font-weight:700;text-align:right;">Toplam</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}
                    </tbody>
                </table>
            </div>

            <div style="margin-top:24px;padding:14px 16px;background:#eff6ff;
                        border-radius:6px;font-size:13px;color:#1e3a8a;">
                <strong>Uyarı modu:</strong> {mode_label}<br>
                <strong>Alıcı:</strong> {user_email}<br>
                <strong>Mailin oluşturulma zamanı:</strong> {now_str} (TRT)
            </div>
        </div>

        <div style="padding:18px 30px;background:#f9fafb;border-top:1px solid #e5e7eb;
                    font-size:12px;color:#6c7a9c;text-align:center;line-height:1.6;">
            Bu mail TrendSurf Optima Kar Realizasyonu Uyarı Sistemi tarafından
            otomatik olarak gönderildi.<br>
            Sadece <strong>sizin portföyünüzdeki</strong> varlıklar takip edilir;
            uyarı ayarlarınızı uygulamadan değiştirebilirsiniz.<br>
            <span style="opacity:0.7;">Bahri Güler</span>
        </div>
    </div>
</body>
</html>"""
    return html


def send_peak_alert(user_id: int, alerts_pending: list,
                    settings: dict) -> dict:
    """Bekleyen uyarilari kullanicinin email'ine HTML mail olarak gonder.

    Args:
        user_id: Kullanici ID
        alerts_pending: peak_tracker.evaluate_user_alerts'in dondurdugu liste
        settings: alert_settings.load_alert_settings'in dondurdugu dict

    Returns:
      {"sent": bool, "to": str, "count": int, "reason": str (hata varsa)}

    Mail basarili gonderildikten sonra her ticker icin
    peak_tracker.mark_alert_sent cagrilir (flag set edilir).
    """
    if not alerts_pending:
        return {"sent": False, "reason": "alerts_pending bos", "count": 0}

    user_email = _get_user_email(user_id)
    if not user_email:
        return {"sent": False, "reason": f"kullanici email bulunamadi (user_id={user_id})",
                "count": 0}

    cfg = _get_smtp_config()
    if not cfg.get("smtp_user") or not cfg.get("smtp_pass"):
        return {"sent": False, "reason": "SMTP config eksik (Secrets'ta email bolumu)",
                "count": 0}

    try:
        html = _build_alert_html(user_email, alerts_pending, settings)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"TrendSurf Optima - Kar Realizasyonu Uyarisi "
            f"({len(alerts_pending)} varlik)"
        )
        msg["From"] = cfg["smtp_user"]
        msg["To"]   = user_email
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as s:
            s.ehlo()
            s.starttls()
            s.login(cfg["smtp_user"], cfg["smtp_pass"])
            s.sendmail(cfg["smtp_user"], user_email, msg.as_string())

        # Mail gonderildi - her ticker icin flag set
        from peak_tracker import mark_alert_sent
        marked = 0
        for a in alerts_pending:
            if mark_alert_sent(user_id, a["ticker"], a["current_price"]):
                marked += 1

        sys.stderr.write(
            f"[peak_alert_emailer] mail gonderildi user={user_id} "
            f"to={user_email} count={len(alerts_pending)} marked={marked}\n"
        )
        sys.stderr.flush()

        return {
            "sent": True, "to": user_email,
            "count": len(alerts_pending), "marked": marked
        }

    except Exception as e:
        sys.stderr.write(f"[peak_alert_emailer] gonderim hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return {"sent": False, "reason": str(e), "count": 0}
