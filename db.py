"""
TrendSurf Optima — Veritabani Modulu (db.py)
Kurulum: python db.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trendsurf.db")

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        email       TEXT    UNIQUE NOT NULL,
        password    TEXT    NOT NULL,
        full_name   TEXT    NOT NULL,
        plan        TEXT    NOT NULL DEFAULT 'free',
        is_active   INTEGER NOT NULL DEFAULT 0,
        is_admin    INTEGER NOT NULL DEFAULT 0,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        expires_at  TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        asset_type  TEXT    NOT NULL,
        ticker      TEXT    NOT NULL,
        quantity    REAL    NOT NULL DEFAULT 0,
        avg_cost    REAL    NOT NULL DEFAULT 0,
        note        TEXT,
        added_at    TEXT    NOT NULL DEFAULT (datetime('now'))
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token       TEXT    PRIMARY KEY,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        expires_at  TEXT    NOT NULL
    )""")

    conn.commit()
    conn.close()

    # Streamlit Cloud: Secrets'tan admin otomatik oluştur
    _ensure_admin_from_secrets()

    print(f"Veritabani hazir: {DB_PATH}")


def _ensure_admin_from_secrets():
    """
    Streamlit Secrets'ta ADMIN_EMAIL ve ADMIN_PASS tanımlıysa
    ve veritabanında admin yoksa otomatik oluşturur.
    """
    try:
        import streamlit as st
        email = st.secrets.get("ADMIN_EMAIL", "")
        password = st.secrets.get("ADMIN_PASS", "")
        name = st.secrets.get("ADMIN_NAME", "Admin")
        if not email or not password:
            return

        conn = get_conn()
        existing = conn.execute(
            "SELECT id FROM users WHERE email=?", (email,)
        ).fetchone()

        if not existing:
            from auth import hash_password
            conn.execute("""
                INSERT INTO users (email, password, full_name, plan, is_active, is_admin)
                VALUES (?, ?, ?, 'premium', 1, 1)
            """, (email, hash_password(password), name))
            conn.commit()
            print(f"[Secrets] Admin olusturuldu: {email}")
        else:
            # Mevcut admin'i aktif ve premium yap
            conn.execute("""
                UPDATE users SET is_active=1, is_admin=1, plan='premium'
                WHERE email=?
            """, (email,))
            conn.commit()
        conn.close()

    except Exception as e:
        # Secrets yoksa veya hata olursa sessizce geç
        pass


if __name__ == "__main__":
    init_db()
