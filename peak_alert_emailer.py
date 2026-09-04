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
    """SMTP config. Onceligi:
       1) Env vars (SMTP_USER, SMTP_PASS) - GitHub Actions standalone modu
       2) Streamlit Secrets [email] - Streamlit Cloud modu
    """
    import os
    # 1) Env vars
    env_user = os.environ.get("SMTP_USER", "").strip()
    env_pass = os.environ.get("SMTP_PASS", "").strip()
    if env_user and env_pass:
        return {
            "smtp_host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
            "smtp_user": env_user,
            "smtp_pass": env_pass,
        }
    # 2) Streamlit Secrets (Cloud modu)
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
                      settings: dict, test_mode: bool = False) -> str:
    """Uyari mailinin HTML govdesini olustur.

    Tek bir mail icinde tum uyariyan tickerlar tablo halinde yer alir.
    test_mode=True ise govdeye acikca gorunur bir "ORNEK/TEST" seridi
    eklenir (v2.0.7.243) - konu satirindaki "(TEST)" on ekiyle birlikte,
    gercek bir uyariyla KARISTIRILMAMASI icin cift guvence.
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

    # v2.0.7.241 (2 Eylül 2026, Bahri'nin bulgusu — mobilde 9 sütunlu tablo
    # okunamayacak kadar küçülüyordu, ekran görüntüsü ekte): YATAY TABLO
    # YERİNE DİKEY "KART" TASARIMINA GEÇİLDİ. Kök neden: e-posta
    # istemcileri (özellikle mobil Gmail uygulaması) geniş tabloları
    # `overflow-x:auto` ile yatay kaydırmak yerine EKRANA SIĞDIRMAK için
    # tüm hücreleri küçültüyor - 9 sütun mobilde okunaksız hale geliyordu.
    # Her varlık artık kendi kutusunda, etiket-değer çiftleri ALT ALTA
    # (2 sütunlu basit tablolar) gösteriliyor - bu düzen HERHANGİ bir
    # ekran genişliğinde (mobil/masaüstü) otomatik okunaklı kalıyor,
    # medya sorgusu (@media) veya flexbox/grid GEREKTİRMİYOR (bunlar
    # Outlook gibi istemcilerde güvenilir değil - sadece <table>
    # kullanılıyor, e-posta uyumluluğu için en güvenli yöntem).
    cards_html = ""
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

        cards_html += f"""
        <div style="border:1px solid #e5e7eb;border-radius:10px;margin-bottom:16px;overflow:hidden;">
            <table role="presentation" style="width:100%;border-collapse:collapse;background:#f9fafb;">
                <tr>
                    <td style="padding:14px 16px;font-size:19px;font-weight:800;color:#1b2a4a;">{ticker}</td>
                    <td style="padding:14px 16px;text-align:right;font-size:13px;color:#6c7a9c;
                               text-transform:uppercase;letter-spacing:0.5px;">{kategori}</td>
                </tr>
            </table>
            <table role="presentation" style="width:100%;border-collapse:collapse;font-size:15px;">
                <tr>
                    <td style="padding:10px 16px;color:#6c7a9c;border-top:1px solid #f1f2f4;">Alış</td>
                    <td style="padding:10px 16px;text-align:right;font-weight:700;border-top:1px solid #f1f2f4;">{alish}</td>
                </tr>
                <tr>
                    <td style="padding:10px 16px;color:#6c7a9c;border-top:1px solid #f1f2f4;">Peak</td>
                    <td style="padding:10px 16px;text-align:right;font-weight:700;color:#0d9488;border-top:1px solid #f1f2f4;">{peak}</td>
                </tr>
                <tr>
                    <td style="padding:10px 16px;color:#6c7a9c;border-top:1px solid #f1f2f4;">Şu Anki</td>
                    <td style="padding:10px 16px;text-align:right;font-weight:700;border-top:1px solid #f1f2f4;">{current}</td>
                </tr>
                <tr>
                    <td style="padding:10px 16px;color:#6c7a9c;border-top:1px solid #f1f2f4;">Düşüş</td>
                    <td style="padding:10px 16px;text-align:right;font-weight:800;font-size:17px;
                               color:#dc2626;border-top:1px solid #f1f2f4;">{drop_pct}</td>
                </tr>
                <tr>
                    <td style="padding:10px 16px;color:#6c7a9c;border-top:1px solid #f1f2f4;">Tavsiye Fiyat</td>
                    <td style="padding:10px 16px;text-align:right;font-weight:700;color:#2563eb;border-top:1px solid #f1f2f4;">{tavsi_disp}</td>
                </tr>
                <tr>
                    <td style="padding:10px 16px;color:#6c7a9c;border-top:1px solid #f1f2f4;">Miktar</td>
                    <td style="padding:10px 16px;text-align:right;color:#374151;border-top:1px solid #f1f2f4;">{miktar} {unit}</td>
                </tr>
                <tr>
                    <td style="padding:12px 16px;font-weight:800;color:#1b2a4a;border-top:2px solid #e5e7eb;">Toplam</td>
                    <td style="padding:12px 16px;text-align:right;font-weight:800;font-size:16px;
                               color:#1b2a4a;border-top:2px solid #e5e7eb;">{toplam} TL</td>
                </tr>
            </table>
        </div>
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
            {"" if not test_mode else '''
            <div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;
                        padding:12px 16px;margin-bottom:18px;font-size:14px;
                        font-weight:700;color:#92400e;text-align:center;">
                ÖRNEK / TEST E-POSTASI - gerçek bir uyarı değildir, sadece
                tasarımı önizlemek için gönderildi.
            </div>
            '''}
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

            <div style="margin-top:20px;">
                {cards_html}
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
                    settings: dict, test_mode: bool = False) -> dict:
    """Bekleyen uyarilari kullanicinin email'ine HTML mail olarak gonder.

    Args:
        user_id: Kullanici ID
        alerts_pending: peak_tracker.evaluate_user_alerts'in dondurdugu liste
        settings: alert_settings.load_alert_settings'in dondurdugu dict
        test_mode: v2.0.7.243 (2 Eylul 2026, Bahri'nin talebi - "Bir ornek
            posta gonder de gorelim") - True ise konu satirina "(TEST)"
            eklenir VE mark_alert_sent HIC cagrilmaz (ornek/uydurma
            ticker'lar gercek peaks tablosuna YAZILMAZ - gercek uyari
            durumunu bozmamak icin).

    Returns:
      {"sent": bool, "to": str, "count": int, "reason": str (hata varsa)}

    Mail basarili gonderildikten sonra (test_mode=False ise) her ticker
    icin peak_tracker.mark_alert_sent cagrilir (flag set edilir).
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
        html = _build_alert_html(user_email, alerts_pending, settings, test_mode=test_mode)

        msg = MIMEMultipart("alternative")
        _konu_on_eki = "(TEST) " if test_mode else ""
        msg["Subject"] = (
            f"{_konu_on_eki}TrendSurf Optima - Kar Realizasyonu Uyarisi "
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

        # Mail gonderildi - her ticker icin flag set (test_mode'da ATLANIR -
        # ornek/uydurma ticker'lar gercek peaks tablosuna yazilmamali)
        marked = 0
        if not test_mode:
            from peak_tracker import mark_alert_sent
            for a in alerts_pending:
                if mark_alert_sent(user_id, a["ticker"], a["current_price"]):
                    marked += 1

        sys.stderr.write(
            f"[peak_alert_emailer] mail gonderildi user={user_id} "
            f"to={user_email} count={len(alerts_pending)} marked={marked} "
            f"test_mode={test_mode}\n"
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
