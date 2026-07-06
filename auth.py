"""
TrendSurf Optima — Kimlik Dogrulama Modulu (auth.py)
"""
import sqlite3, secrets, hashlib
from datetime import datetime, timedelta
import streamlit as st
from db import get_conn, init_db, IntegrityError

# ── Sifre Hash ───────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"sha256:{salt}:{h}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ImportError:
        if hashed.startswith("sha256:"):
            _, salt, h = hashed.split(":", 2)
            return hashlib.sha256((salt + password).encode()).hexdigest() == h
        return password == hashed

# ── Yeni Kayit Bildirimi (Admin'e E-posta) ───────────────────────────────────
def _notify_admin_yeni_kayit(email: str, full_name: str):
    """Yeni bir abonelik basvurusu oldugunda admin'e bilgilendirme maili
    gonderir. Mevcut [email] Secrets (smtp_user/smtp_pass/smtp_host/smtp_port)
    ve ADMIN_EMAIL kullanilir - gunluk rapor sisteminde zaten kullanilan
    ayarlarin aynisi, yeni bir secret eklemeye gerek yok.

    Onemli: Bu fonksiyon HICBIR ZAMAN kayit islemini engellemez. SMTP
    ayarlari eksikse veya gonderim basarisiz olursa sessizce gecilir -
    kullanici yine de basariyla kayit olur, admin sadece bildirimi
    kacirmis olur (onay panelinden yine de gorebilir).
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        _email_cfg = st.secrets.get("email", {})
        smtp_user = _email_cfg.get("smtp_user")
        smtp_pass = _email_cfg.get("smtp_pass")
        smtp_host = _email_cfg.get("smtp_host", "smtp.gmail.com")
        smtp_port = int(_email_cfg.get("smtp_port", 587))
        admin_email = st.secrets.get("ADMIN_EMAIL")

        if not (smtp_user and smtp_pass and admin_email):
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "TrendSurf Optima — Yeni Abonelik Başvurusu"
        msg["From"] = smtp_user
        msg["To"] = admin_email

        _simdi = datetime.now().strftime("%d.%m.%Y %H:%M")
        _html = f"""
        <div style="font-family:Segoe UI,Arial,sans-serif;max-width:480px;margin:auto;">
          <h2 style="color:#0d2b4e;margin-bottom:4px;">Yeni Abonelik Başvurusu</h2>
          <p style="color:#333;">TrendSurf Optima'ya yeni bir kayıt başvurusu geldi:</p>
          <table style="border-collapse:collapse;width:100%;font-size:14px;">
            <tr><td style="padding:6px 0;color:#5a6a78;width:110px;">Ad Soyad</td>
                <td style="padding:6px 0;"><b>{full_name}</b></td></tr>
            <tr><td style="padding:6px 0;color:#5a6a78;">E-posta</td>
                <td style="padding:6px 0;"><b>{email}</b></td></tr>
            <tr><td style="padding:6px 0;color:#5a6a78;">Tarih</td>
                <td style="padding:6px 0;">{_simdi}</td></tr>
          </table>
          <p style="margin-top:16px;color:#333;">Onaylamak için Admin Paneli →
          Bekleyen Kullanıcılar bölümüne gidin.</p>
        </div>
        """
        msg.attach(MIMEText(_html, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception:
        pass  # bildirim basarisiz olsa da kayit islemini asla etkileme

# ── Kayit ────────────────────────────────────────────────────────────────────
def register_user(email: str, password: str, full_name: str) -> dict:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (email, password, full_name) VALUES (?, ?, ?)",
            (email.strip().lower(), hash_password(password), full_name.strip())
        )
        conn.commit()
        _notify_admin_yeni_kayit(email.strip().lower(), full_name.strip())
        return {"ok": True, "msg": "Kaydiniz alindi. Admin onayi bekleniyor."}
    except IntegrityError:
        return {"ok": False, "msg": "Bu e-posta adresi zaten kayitli."}
    finally:
        conn.close()

# ── Giris ────────────────────────────────────────────────────────────────────
def login_user(email: str, password: str, remember: bool = False) -> dict:
    """Kullaniciyi dogrula ve oturum acmasini sagla.

    v1.9.9: remember=True ise token 90 gun, False ise 7 gun yasar.
            Beni Hatirla checkbox isaretliyse 90 gunluk token uretilir,
            tarayici cookie'sine yazilir (login persistence).

    Args:
        email: Kullanici e-postasi
        password: Kullanici sifresi (plain)
        remember: True = 90 gun, False = 7 gun (default)
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    conn.close()

    if not row:
        return {"ok": False, "msg": "E-posta veya sifre hatali."}
    if not verify_password(password, row["password"]):
        return {"ok": False, "msg": "E-posta veya sifre hatali."}
    if not row["is_active"]:
        return {"ok": False, "msg": "Hesabiniz henuz onaylanmadi. Lutfen bekleyin."}

    token = secrets.token_urlsafe(32)
    # v1.9.9 - Beni Hatirla: 90 gun, Aksi halde: 7 gun
    _days = 90 if remember else 7
    expires = (datetime.now() + timedelta(days=_days)).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, row["id"], expires)
    )
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "token": token,
        "user": {
            "id":        row["id"],
            "email":     row["email"],
            "full_name": row["full_name"],
            "plan":      row["plan"],
            "is_admin":  row["is_admin"],
        }
    }

# ── Mevcut Kullanici ─────────────────────────────────────────────────────────
def get_current_user():
    if "auth_token" not in st.session_state:
        return None
    token = st.session_state["auth_token"]
    conn = get_conn()
    row = conn.execute("""
        SELECT u.* FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ? AND s.expires_at > datetime('now')
    """, (token,)).fetchone()
    conn.close()
    if not row:
        st.session_state.pop("auth_token", None)
        return None
    return dict(row)

def logout():
    token = st.session_state.pop("auth_token", None)
    st.session_state.pop("logo_splash_played", None)  # v2.0.3.5: sonraki girişte splash tekrar oynasın
    if token:
        conn = get_conn()
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()

# ── Plan Yetki Kontrolu ──────────────────────────────────────────────────────
PLAN_LEVELS = {"free": 0, "pro": 1, "premium": 2}

def has_plan(min_plan: str) -> bool:
    user = get_current_user()
    if not user:
        return False
    return PLAN_LEVELS.get(user["plan"], 0) >= PLAN_LEVELS.get(min_plan, 0)
