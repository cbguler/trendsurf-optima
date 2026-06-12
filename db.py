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

    # Kullanicilar
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

    # Portfoy
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

    # Oturumlar
    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token       TEXT    PRIMARY KEY,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        expires_at  TEXT    NOT NULL
    )""")

    conn.commit()
    conn.close()
    print(f"Veritabani hazir: {DB_PATH}")

if __name__ == "__main__":
    init_db()
