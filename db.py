"""
TrendSurf Optima - Veritabani Modulu (db.py)
v1.8.0: PostgreSQL/Supabase backend, SQLite-uyumlu interface

Onceki davranis: trendsurf.db (SQLite, Streamlit Cloud diskinde, restart'ta wipe)
Yeni davranis:   Supabase PostgreSQL (kalici, Streamlit Cloud + GitHub Actions
                 erisebilir). API ayni: get_conn().execute(sql, params).fetchone()

Yapilan donusumler (otomatik, caller kod degismez):
  ? placeholder            -> %s
  datetime('now')          -> CURRENT_TIMESTAMP
  AUTOINCREMENT            -> (kaldirilir, SERIAL kullanilir)
  INTEGER (is_active, ...) -> BOOLEAN (PostgreSQL'de native)
  sqlite3.IntegrityError   -> db.IntegrityError (psycopg2 IntegrityError alias)

Kurulum: Streamlit Secrets'ta su tanimli olmali:
  [supabase]
  db_url = "postgresql://postgres.<proj>:<pass>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require"
"""

import os
import re
from typing import Any, Optional

# ============================================================================
# psycopg2 import (Supabase PostgreSQL erisimi icin)
# ============================================================================
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import IntegrityError as _PgIntegrityError
    PSYCOPG2_OK = True
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    _PgIntegrityError = Exception
    PSYCOPG2_OK = False


# Disariya export: from db import IntegrityError
IntegrityError = _PgIntegrityError


# ============================================================================
# Connection string (Streamlit Secrets veya env)
# ============================================================================
def _get_db_url() -> str:
    """Streamlit Secrets'tan db_url'i al, yoksa env, yoksa hata."""
    # Streamlit Secrets
    try:
        import streamlit as st
        sup = st.secrets.get("supabase", {})
        if sup and sup.get("db_url"):
            return sup["db_url"]
    except Exception:
        pass
    # Environment variable (GitHub Actions vb.)
    url = os.environ.get("SUPABASE_DB_URL", "")
    if url:
        return url
    return ""


# ============================================================================
# SQLite -> PostgreSQL syntax cevirici
# ============================================================================
_DATETIME_NOW_RX = re.compile(r"datetime\(\s*['\"]now['\"]\s*\)", re.IGNORECASE)


def _translate_sql(sql: str) -> str:
    """SQLite SQL'i PostgreSQL'e cevir.

    Yapilan donusumler:
      ?              -> %s   (placeholder)
      datetime('now')-> CURRENT_TIMESTAMP
      AUTOINCREMENT  -> (silinir, SERIAL kullanildi)
      INTEGER NOT NULL DEFAULT 0 / 1 (is_active, is_admin) -> as-is (PostgreSQL kabul eder)
    """
    # ? -> %s (ama string literal icinde olmasin diye dikkatli)
    # Basit yaklasim: tum ? karakterlerini %s yap. Olas i risk: TEXT icinde ? gecerse
    # bozulur. Bizim kodumuzda boyle bir kullanim yok.
    sql = sql.replace("?", "%s")
    # datetime('now')
    sql = _DATETIME_NOW_RX.sub("CURRENT_TIMESTAMP", sql)
    # AUTOINCREMENT - SERIAL kullaniyoruz, AUTOINCREMENT yoksay
    sql = re.sub(r"\bAUTOINCREMENT\b", "", sql, flags=re.IGNORECASE)
    return sql


# ============================================================================
# Compat Row - sqlite3.Row gibi davranan dict
# ============================================================================
class _CompatRow(dict):
    """sqlite3.Row uyumlu: hem dict hem index erisimi."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

    def keys(self):
        return list(super().keys())


# ============================================================================
# Compat Cursor
# ============================================================================
class _CompatCursor:
    def __init__(self, pg_cur):
        self._cur = pg_cur

    def fetchone(self) -> Optional[_CompatRow]:
        row = self._cur.fetchone()
        if row is None:
            return None
        return _CompatRow(row)

    def fetchall(self) -> list:
        return [_CompatRow(r) for r in self._cur.fetchall()]

    def close(self):
        self._cur.close()


# ============================================================================
# Compat Connection
# ============================================================================
class _CompatConn:
    """sqlite3.Connection arayuzu, PostgreSQL backend.

    execute(sql, params) calls return a cursor with fetchone/fetchall.
    commit(), close() also supported.
    """
    def __init__(self, pg_conn):
        self._conn = pg_conn
        self._conn.autocommit = False

    def execute(self, sql: str, params=None) -> _CompatCursor:
        sql_pg = _translate_sql(sql)
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(sql_pg, params or ())
        except Exception:
            # PostgreSQL: basarisiz statement transaction'i zehirler.
            # Sonraki execute'lerin calismasi icin rollback sart.
            try:
                self._conn.rollback()
            except Exception:
                pass
            raise
        return _CompatCursor(cur)

    def cursor(self):
        return _CompatCursor(self._conn.cursor(cursor_factory=RealDictCursor))

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


# ============================================================================
# Public API: get_conn
# ============================================================================
def get_conn() -> _CompatConn:
    """Supabase PostgreSQL baglantisi don."""
    if not PSYCOPG2_OK:
        raise RuntimeError(
            "psycopg2-binary yuklu degil. requirements.txt'e ekleyin: psycopg2-binary>=2.9"
        )
    url = _get_db_url()
    if not url:
        raise RuntimeError(
            "Supabase db_url ayarlanmamis. Streamlit Secrets'ta tanimlayin:\n"
            "[supabase]\ndb_url = \"postgresql://...\""
        )
    pg_conn = psycopg2.connect(url)
    return _CompatConn(pg_conn)


# ============================================================================
# init_db - PostgreSQL tablolarini olustur
# ============================================================================
def init_db():
    """Tablolari olustur (yoksa). PostgreSQL syntax."""
    conn = get_conn()
    c = conn._conn.cursor()

    # users tablosu
    # Not: is_active ve is_admin INTEGER (0/1) - mevcut SQL (=1, =0) ile uyumlu kalsin
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id          SERIAL  PRIMARY KEY,
        email       TEXT    UNIQUE NOT NULL,
        password    TEXT    NOT NULL,
        full_name   TEXT    NOT NULL,
        plan        TEXT    NOT NULL DEFAULT 'free',
        is_active   INTEGER NOT NULL DEFAULT 0,
        is_admin    INTEGER NOT NULL DEFAULT 0,
        created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at  TIMESTAMP
    )""")

    # portfolio tablosu (ek sutunlar dahil)
    c.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        id            SERIAL  PRIMARY KEY,
        user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        asset_type    TEXT    NOT NULL,
        ticker        TEXT    NOT NULL,
        quantity      REAL    NOT NULL DEFAULT 0,
        avg_cost      REAL    NOT NULL DEFAULT 0,
        note          TEXT,
        added_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        purchase_date TEXT    DEFAULT '',
        unit_type     TEXT    DEFAULT 'Adet'
    )""")

    # sessions tablosu
    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token       TEXT      PRIMARY KEY,
        user_id     INTEGER   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at  TIMESTAMP NOT NULL
    )""")

    # password_resets tablosu (auth_reset.py icin)
    c.execute("""
    CREATE TABLE IF NOT EXISTS password_resets (
        token      TEXT      PRIMARY KEY,
        user_id    INTEGER   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        expires_at TIMESTAMP NOT NULL,
        used       INTEGER   NOT NULL DEFAULT 0
    )""")

    # Idempotent index'ler (e-posta lookup, session token lookup hizli olsun)
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_email      ON users(LOWER(email))")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token   ON sessions(token)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user   ON portfolio(user_id)")

    conn.commit()
    conn.close()

    # Streamlit Secrets'tan admin otomatik olustur
    _ensure_admin_from_secrets()

    print("Veritabani hazir: Supabase PostgreSQL")


# ============================================================================
# Auto-seed admin (Cloud reboot'tan sonra her seferinde calistirilir)
# ============================================================================
def _ensure_admin_from_secrets():
    """Secrets'ta [admin] tanimliysa, kullaniciyi olustur (yoksa) ve aktif/admin yap.

    auth.py'nin hash_password'unu kullanir (bcrypt). Boylece verify_password
    eslesir. Onceki sha256 hack'i kaldirildi.
    """
    try:
        import streamlit as st
        asec = st.secrets.get("admin", {})
        email = asec.get("email", "").strip().lower()
        password = asec.get("password", "")
        name = asec.get("name", "Admin")
        if not email or not password:
            return

        from auth import hash_password

        conn = get_conn()
        existing = conn.execute(
            "SELECT id FROM users WHERE email=?", (email,)
        ).fetchone()

        if not existing:
            conn.execute("""
                INSERT INTO users (email, password, full_name, plan, is_active, is_admin)
                VALUES (?, ?, ?, 'premium', 1, 1)
            """, (email, hash_password(password), name))
        else:
            # Mevcut admin'i premium + aktif yap
            conn.execute("""
                UPDATE users SET is_active=1, is_admin=1, plan='premium'
                WHERE email=?
            """, (email,))
        conn.commit()
        conn.close()
    except Exception:
        # Secrets yok veya gecici hata - sessizce gec
        pass


if __name__ == "__main__":
    init_db()
