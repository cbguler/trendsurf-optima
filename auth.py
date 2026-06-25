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

# ── Kayit ────────────────────────────────────────────────────────────────────
def register_user(email: str, password: str, full_name: str) -> dict:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (email, password, full_name) VALUES (?, ?, ?)",
            (email.strip().lower(), hash_password(password), full_name.strip())
        )
        conn.commit()
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
