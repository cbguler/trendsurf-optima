"""
TrendSurf Optima - Veritabani Modulu (db.py)
v1.9.9.3: Defansif _get_db_url + verbose error mesajlari + diagnostic logging

Onceki davranis: trendsurf.db (SQLite, Streamlit Cloud diskinde, restart'ta wipe)
Yeni davranis:   Supabase PostgreSQL (kalici, Streamlit Cloud + GitHub Actions
                 erisebilir). API ayni: get_conn().execute(sql, params).fetchone()

v1.9.9.3 degisikligi: Streamlit 1.58+ secrets API'sinde davranis degisikligi
nedeniyle _get_db_url() multiple format/access pattern destekler. Hata olusursa
verbose error mesaji + logs'a diagnostic print.

Kurulum: Streamlit Secrets'ta su tanimli olmali:
  [supabase]
  db_url = "postgresql://postgres.<proj>:<pass>@aws-0-<region>.pooler.supabase.com:6543/postgres"
"""

import os
import re
import sys
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
# Connection string (Streamlit Secrets veya env) - v1.9.9.3 DEFANSIF
# ============================================================================
def _get_db_url() -> str:
    """Streamlit Secrets'tan db_url'i al, yoksa env, yoksa bos string.

    v1.9.9.3 - Streamlit 1.58+ secrets API'sindeki davranis degisikligini
    kompanse etmek icin multiple access pattern destekler. Hatalari logla.
    """
    # 1) Streamlit Secrets - bircok yol dene
    try:
        import streamlit as st

        # Yol A: Modern indexing - st.secrets["supabase"]["db_url"]
        try:
            if "supabase" in st.secrets:
                sec_sup = st.secrets["supabase"]
                if "db_url" in sec_sup:
                    db_url = str(sec_sup["db_url"]).strip()
                    if db_url:
                        print(f"[db] _get_db_url: secrets[supabase][db_url] OK (len={len(db_url)})", file=sys.stderr)
                        return db_url
        except Exception as e:
            print(f"[db] secrets indexing yol A fail: {type(e).__name__}: {e}", file=sys.stderr)

        # Yol B: dict(secrets) yontemi
        try:
            sec = dict(st.secrets)
            sup = sec.get("supabase", {})
            if isinstance(sup, dict) or hasattr(sup, "get"):
                db_url = (sup.get("db_url") if hasattr(sup, "get") else sup["db_url"])
                db_url = str(db_url).strip()
                if db_url:
                    print(f"[db] _get_db_url: dict(secrets)[supabase][db_url] OK (len={len(db_url)})", file=sys.stderr)
                    return db_url
        except Exception as e:
            print(f"[db] secrets dict yol B fail: {type(e).__name__}: {e}", file=sys.stderr)

        # Yol C: Top-level SUPABASE_DB_URL
        try:
            db_url = str(st.secrets.get("SUPABASE_DB_URL", "")).strip()
            if db_url:
                print(f"[db] _get_db_url: secrets[SUPABASE_DB_URL] OK (len={len(db_url)})", file=sys.stderr)
                return db_url
        except Exception as e:
            print(f"[db] secrets top-level yol C fail: {type(e).__name__}: {e}", file=sys.stderr)

    except Exception as e:
        print(f"[db] streamlit secrets erisilemez: {type(e).__name__}: {e}", file=sys.stderr)

    # 2) Environment variable (GitHub Actions vb.)
    url = os.environ.get("SUPABASE_DB_URL", "").strip()
    if url:
        print(f"[db] _get_db_url: env SUPABASE_DB_URL OK (len={len(url)})", file=sys.stderr)
        return url

    print("[db] _get_db_url: HIC BIR YOL CALISMADI, bos string donduruluyor", file=sys.stderr)
    return ""


# ============================================================================
# SQLite -> PostgreSQL syntax cevirici
# ============================================================================
_DATETIME_NOW_RX = re.compile(r"datetime\(\s*['\"]now['\"]\s*\)", re.IGNORECASE)


def _translate_sql(sql: str) -> str:
    """SQLite SQL'i PostgreSQL'e cevir."""
    sql = sql.replace("?", "%s")
    sql = _DATETIME_NOW_RX.sub("CURRENT_TIMESTAMP", sql)
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
    """sqlite3.Connection arayuzu, PostgreSQL backend."""
    def __init__(self, pg_conn):
        self._conn = pg_conn
        self._conn.autocommit = False

    def execute(self, sql: str, params=None) -> _CompatCursor:
        sql_pg = _translate_sql(sql)
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(sql_pg, params or ())
        except Exception:
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
# Public API: get_conn  -  v1.9.9.3 VERBOSE
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
            "Supabase db_url ayarlanmamis. Streamlit Cloud Secrets'ta tanimlayin:\n"
            "  [supabase]\n"
            "  db_url = \"postgresql://...\"\n"
            "Veya GitHub Actions icin env: SUPABASE_DB_URL"
        )
    # v1.9.9.3 - connect_timeout + verbose error handling
    try:
        pg_conn = psycopg2.connect(url, connect_timeout=10)
    except psycopg2.OperationalError as e:
        # Host/port/credentials/SSL hatalari
        err_msg = str(e)[:300] if e else "bilinmeyen hata"
        print(f"[db] psycopg2 OperationalError: {err_msg}", file=sys.stderr)
        raise RuntimeError(
            f"Supabase baglantisi acilamadi (OperationalError): {err_msg}\n"
            f"Cozumler:\n"
            f"  1) Supabase Dashboard'ta projenin aktif oldugunu dogrulayin\n"
            f"  2) Connection string'in dogru oldugunu kontrol edin (Settings > Database)\n"
            f"  3) URL'de password'unun URL-encoded oldugundan emin olun (?, @, $, !)"
        ) from e
    except Exception as e:
        err_msg = str(e)[:300] if e else "bilinmeyen"
        print(f"[db] psycopg2.connect hatasi: {type(e).__name__}: {err_msg}", file=sys.stderr)
        raise RuntimeError(
            f"Supabase baglantisi acilamadi ({type(e).__name__}): {err_msg}"
        ) from e
    return _CompatConn(pg_conn)


# ============================================================================
# init_db - PostgreSQL tablolarini olustur
# ============================================================================
def init_db():
    """Tablolari olustur (yoksa). PostgreSQL syntax."""
    print("[db] init_db basliyor...", file=sys.stderr)
    conn = get_conn()
    print("[db] get_conn OK, tablolari olusturuyorum...", file=sys.stderr)
    c = conn._conn.cursor()

    # users tablosu
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

    # Idempotent index'ler
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_email      ON users(LOWER(email))")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token   ON sessions(token)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user   ON portfolio(user_id)")

    conn.commit()
    conn.close()

    # Streamlit Secrets'tan admin otomatik olustur
    _ensure_admin_from_secrets()

    print("[db] Veritabani hazir: Supabase PostgreSQL", file=sys.stderr)


# ============================================================================
# Auto-seed admin
# ============================================================================
def _ensure_admin_from_secrets():
    """Secrets'ta [admin] tanimliysa, kullaniciyi olustur (yoksa) ve aktif/admin yap."""
    try:
        import streamlit as st
        asec = st.secrets.get("admin", {})
        # Streamlit 1.58+ Section object'i destek
        try:
            asec_d = dict(asec)
        except Exception:
            asec_d = asec or {}
        email = str(asec_d.get("email", "")).strip().lower() if hasattr(asec_d, "get") else ""
        password = str(asec_d.get("password", "")) if hasattr(asec_d, "get") else ""
        name = str(asec_d.get("name", "Admin")) if hasattr(asec_d, "get") else "Admin"
        if not email or not password:
            print("[db] admin secrets bos, auto-seed atlandi", file=sys.stderr)
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
            print(f"[db] Admin auto-seed: {email} olusturuldu", file=sys.stderr)
        else:
            conn.execute("""
                UPDATE users SET is_active=1, is_admin=1, plan='premium'
                WHERE email=?
            """, (email,))
            print(f"[db] Admin auto-seed: {email} aktif/admin yapildi", file=sys.stderr)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] _ensure_admin_from_secrets hata (sessiz devam): {type(e).__name__}: {e}", file=sys.stderr)


if __name__ == "__main__":
    init_db()
