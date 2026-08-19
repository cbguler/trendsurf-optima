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
import datetime  # v2.0.7.160: ai_cagri_butcesi gunluk sayaci icin
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
    """db_url'i al. Sira: 1) env var, 2) Streamlit Secrets, 3) bos string.

    v2.0.2 - Onceki versiyon Streamlit Secrets'i ONCE deniyordu, GitHub Actions
    icin sorun: repo'ya kazara push edilmis .streamlit/secrets.toml [supabase]
    bolumu olmadan duruyor; dict().get("db_url") None doner, str(None)='None'
    (4 char string) truthy oldugu icin bu "gecersiz None" deger valid sanildi.
    Yeni sira: env var ONCE -> GitHub Actions her zaman dogru oradan okur.
    Streamlit Secrets sadece Streamlit Cloud'da fallback olarak kullanilir.

    Helper: _valid_url(s) -> "None" string'i ve bos degerleri filtreler.
    """
    def _valid_url(raw) -> str:
        if raw is None:
            return ""
        s = str(raw).strip()
        if not s or s.lower() in ("none", "null", "<none>"):
            return ""
        return s

    # 1) Environment variable ONCE (GitHub Actions, Docker, lokal env vb.)
    url = _valid_url(os.environ.get("SUPABASE_DB_URL", ""))
    if url:
        print(f"[db] _get_db_url: env SUPABASE_DB_URL OK (len={len(url)})", file=sys.stderr)
        return url

    # 2) Streamlit Secrets - bircok yol dene (Streamlit Cloud icin)
    try:
        import streamlit as st

        # Yol A: Modern indexing - st.secrets["supabase"]["db_url"]
        try:
            if "supabase" in st.secrets:
                sec_sup = st.secrets["supabase"]
                if "db_url" in sec_sup:
                    db_url = _valid_url(sec_sup["db_url"])
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
                raw = sup.get("db_url") if hasattr(sup, "get") else sup.get("db_url")
                db_url = _valid_url(raw)
                if db_url:
                    print(f"[db] _get_db_url: dict(secrets)[supabase][db_url] OK (len={len(db_url)})", file=sys.stderr)
                    return db_url
        except Exception as e:
            print(f"[db] secrets dict yol B fail: {type(e).__name__}: {e}", file=sys.stderr)

        # Yol C: Top-level SUPABASE_DB_URL
        try:
            db_url = _valid_url(st.secrets.get("SUPABASE_DB_URL", ""))
            if db_url:
                print(f"[db] _get_db_url: secrets[SUPABASE_DB_URL] OK (len={len(db_url)})", file=sys.stderr)
                return db_url
        except Exception as e:
            print(f"[db] secrets top-level yol C fail: {type(e).__name__}: {e}", file=sys.stderr)

    except Exception as e:
        print(f"[db] streamlit secrets erisilemez: {type(e).__name__}: {e}", file=sys.stderr)

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

    @property
    def rowcount(self) -> int:
        """v2.0.4.4: INSERT/UPDATE/DELETE sonrasi etkilenen satir sayisi.
        Atomik 'reservation' (INSERT ... ON CONFLICT DO NOTHING) mantiginda
        rowcount==1 -> bu cagri kazandi, rowcount==0 -> baskasi zaten almis."""
        try:
            return self._cur.rowcount
        except Exception:
            return -1

    def close(self):
        self._cur.close()


# ============================================================================
# Compat Connection
# ============================================================================
class _CompatConn:
    """sqlite3.Connection arayuzu, PostgreSQL backend.

    v2.0.7.142 (Bahri'nin bulgusu, 11 Agustos 2026 - KRITIK GERI ALMA):
    v2.0.7.137'de eklenen baglanti havuzu (psycopg2.pool) art arda IKI
    FARKLI cokme turune yol acti: (1) havuz tukenmesi (bazi cagiran
    kodlar istisna durumunda .close()'a ulasmayip baglantiyi sizdiriyordu)
    - v2.0.7.140'ta guvenlik agiyla kismen ele alindi, sonra (2) havuzdan
    gelen bir baglanti "acik" gorunse bile (pg_conn.closed==0) Supabase
    pooler'i sunucu tarafinda sessizce dusurmus olabiliyordu - bu da
    GERCEK SORGU calistirilirken (baglanti alinirken degil) cokmeye yol
    aciyordu, guvenlik agi bunu YAKALAYAMIYORDU.

    Iki farkli cokme turu art arda gelince, havuzlamanin getirdigi
    performans kazanci GUVENILIRLIK riskine deymiyordu. Havuzlama
    TAMAMEN KALDIRILDI - proje tarihinin tamaminda (bugune kadar)
    KANITLANMIS sekilde calisan basit yonteme (her cagrida sifirdan yeni
    baglanti) GERI DONULDU. Performans "3-4 kez _get_db_url" bulgusu
    gercekti ama cozumu bu degildi - ileride (istenirse) cok daha
    dikkatli test edilerek, ozellikle "sunucu tarafinda dusurulmus
    baglanti" senaryosuna karsi saglam (pre-ping / retry-on-execute)
    bir tasarimla yeniden ele alinabilir."""
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
# Public API: get_conn  -  v2.0.7.142: basit, guvenilir (havuz KALDIRILDI)
# ============================================================================
def get_conn() -> _CompatConn:
    """Supabase PostgreSQL baglantisi dondurur - basit, kanitlanmis
    guvenilir yontem (havuzlama v2.0.7.142'de KALDIRILDI, bkz.
    _CompatConn'un modul ustu notu - iki ayri cokme turune yol acmisti)."""
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
    try:
        pg_conn = psycopg2.connect(url, connect_timeout=10)
    except psycopg2.OperationalError as e:
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
        quantity      DOUBLE PRECISION    NOT NULL DEFAULT 0,
        avg_cost      DOUBLE PRECISION    NOT NULL DEFAULT 0,
        note          TEXT,
        added_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        purchase_date TEXT    DEFAULT '',
        unit_type     TEXT    DEFAULT 'Adet'
    )""")

    # v2.0.7.156 (Bahri'nin talebi, 18 Ağustos 2026 — KRİTİK tasarım
    # düzeltmesi): "hemen otomatik uygula" YANLIŞ anlaşılmıştı/yanlış
    # seçilmişti - Bahri'nin gerçekte istediği: sistem tespit eder,
    # KULLANICIYA gösterir (haber + AI gerekçesi + hangi kategoriye ne
    # kadar puan etkisi olacağı), kullanıcı UYGUN BULURSA onaylar, ANCAK
    # o zaman Optima Skor'a uygulanır. `kullanici_iptal` (uygulandıktan
    # SONRA geri alma) yerine `onay_durumu` (uygulanmadan ÖNCE onay
    # bekleme: 'bekliyor'/'onaylandi'/'reddedildi') - v2.0.7.154'ün
    # "otomatik uygula" mantığı TAMAMEN kaldırıldı.
    c.execute("""
    CREATE TABLE IF NOT EXISTS beklenti_otomatik_tespit (
        id                SERIAL PRIMARY KEY,
        kalip_key         TEXT NOT NULL,
        siddet            TEXT NOT NULL,
        haber_basligi     TEXT,
        haber_url         TEXT,
        haber_kaynak      TEXT,
        ai_gerekce        TEXT,
        tespit_zamani     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        gecerlilik_bitis  TIMESTAMP NOT NULL,
        onay_durumu       TEXT NOT NULL DEFAULT 'bekliyor',
        onay_zamani       TIMESTAMP
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS haber_islenmis (
        haber_url    TEXT PRIMARY KEY,
        islenme_zamani TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")

    # v2.0.7.160 (Bahri'nin talebi, 19 Ağustos 2026 — "durumun stabil
    # olduğunu nasıl görebilirim diye düşünürken haber sayfası fikri
    # oluştu"): Haber AKIŞI artık saklanıyor. Önceden haber_izleme.py
    # anahtar kelime filtresine takılmayan başlığı ATIYORDU (sadece
    # haber_islenmis'e URL yazıp geçiyordu) - yani "hiçbir şey olmuyor"
    # bilgisi hiçbir yerde görünmüyordu. Bu tablo o boşluğu dolduruyor.
    # eslesen_kalip NULL ise: haber tarandı, hiçbir kalıba uymadı (yani
    # piyasa açısından sakin bir haber). NULL değilse: ön-filtreye takıldı,
    # Haberler sayfasında üstte işaretli gösterilir.
    # baslik_tr NULL ise ya kaynak zaten Türkçedir (AA/Investing TR/
    # BloombergHT) ya da çeviri bütçesi dolmuştur - iki durumda da
    # orijinal başlık gösterilir.
    # SAKLAMA SÜRESİ 7 GÜN (haber_akisi_temizle ile) - sınırsız büyümesin.
    c.execute("""
    CREATE TABLE IF NOT EXISTS haber_akisi (
        haber_url      TEXT PRIMARY KEY,
        kaynak         TEXT NOT NULL,
        baslik         TEXT NOT NULL,
        baslik_tr      TEXT,
        eslesen_kalip  TEXT,
        yayin_zamani   TIMESTAMP,
        eklenme_zamani TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")

    # v2.0.7.160: Gemini ücretsiz katman günlük istek limiti BELİRSİZ
    # (üçüncü taraf kaynaklar 20/50/250/500/1500 gibi çelişkili rakamlar
    # veriyor, Aralık 2025'te bir kez düşürüldüğü bildirildi). Bu yüzden
    # kotanın cömert olduğu VARSAYILMIYOR: günlük çağrı sayısı burada
    # tutuluyor, bütçe dolunca çeviri durur (haberler orijinal başlıkla
    # görünmeye devam eder), tespit/doğrulama akışı etkilenmez.
    c.execute("""
    CREATE TABLE IF NOT EXISTS ai_cagri_butcesi (
        tarih      TEXT PRIMARY KEY,
        cagri_sayisi INTEGER NOT NULL DEFAULT 0
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

    # v2.0.7.47 - Muhasebe sistemi (Bahri'nin talebi): satis islemleri
    # KALICI olarak kaydedilir - "portfolio" tablosundaki gibi silinince
    # yok olmaz. Gercek kar/zarar (net, komisyon+vergi dusulmus) burada
    # hesaplanip saklanir.
    c.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_sales (
        id           SERIAL  PRIMARY KEY,
        user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        asset_type   TEXT    NOT NULL,
        ticker       TEXT    NOT NULL,
        unit_type    TEXT    DEFAULT 'Adet',
        quantity     DOUBLE PRECISION    NOT NULL,
        buy_price    DOUBLE PRECISION    NOT NULL,
        buy_date     TEXT    DEFAULT '',
        sell_price   DOUBLE PRECISION    NOT NULL,
        sell_date    TEXT    NOT NULL,
        fee_pct      DOUBLE PRECISION    NOT NULL DEFAULT 0,
        tax_pct      DOUBLE PRECISION    NOT NULL DEFAULT 0,
        fee_amount   DOUBLE PRECISION    NOT NULL DEFAULT 0,
        tax_amount   DOUBLE PRECISION    NOT NULL DEFAULT 0,
        gross_pl     DOUBLE PRECISION    NOT NULL DEFAULT 0,
        net_pl       DOUBLE PRECISION    NOT NULL DEFAULT 0,
        note         TEXT    DEFAULT '',
        created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")

    # v2.0.7.47 - Kategori bazli komisyon/vergi oranlari (kullanici
    # duzenleyebilir, ilk kullanimda makul varsayilanlarla doldurulur).
    c.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_fee_settings (
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        asset_type  TEXT    NOT NULL,
        fee_pct     DOUBLE PRECISION    NOT NULL DEFAULT 0,
        tax_pct     DOUBLE PRECISION    NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, asset_type)
    )""")

    # v2.0.7.112 - Sermaye/Nakit takibi (Bahri'nin talebi): "başlangıç
    # sermayesi tek seferlik sabit bir tutar degil, dinamiktir - zaman
    # icinde ekleme/cikarma yapabilmeliyim" karari geregi, sabit bir
    # "baslangic_sermaye" alani yerine bir MEVDUAT/CEKIM HAREKET
    # defteri tutuluyor (portfolio_sales'in satis gecmisi tuttugu
    # mantigin ayni). Nakit bakiyesi bundan + alis/satis islemlerinden
    # TÜRETİLİR (bkz. portfolio_ledger.get_cash_balance) - negatife
    # düşebilir, bilinçli olarak SINIRLANDIRILMADI (Bahri: "sermaye
    # hayali değil, gerçek durumu göstersin").
    c.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_capital_tx (
        id         SERIAL  PRIMARY KEY,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        tx_type    TEXT    NOT NULL,
        amount     DOUBLE PRECISION    NOT NULL,
        tx_date    TEXT    NOT NULL,
        note       TEXT    DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")

    # v2.0.7.125 - Kiyaslama ozelligi (Bahri'nin talebi): "portfoyumun
    # getirisini TSO'da olan/olmayan baska yatirim araclariyla kiyasla"
    # butonu icin - mevduat/tahvil/repo gibi araclarin canli/guvenilir
    # bir API'si olmadigindan (TCMB "ortalama mevduat faizi" diye bir
    # sey yayinlamiyor), bu 3 oran Bahri tarafindan MANUEL girilip
    # guncellenir. BIST100/Altin/Dolar icin ise yfinance'ten GERCEK
    # gecmis veri cekiliyor (bkz. app.py _karsilastirma_gecmis_fiyat).
    c.execute("""
    CREATE TABLE IF NOT EXISTS benchmark_rates (
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        rate_name   TEXT    NOT NULL,
        annual_rate DOUBLE PRECISION NOT NULL,
        updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, rate_name)
    )""")

    # v2.0.7.117 - KRITIK VERI DUZELTMESI (Bahri'nin bulgusu, HTS ornegi,
    # 31 Temmuz 2026: Duzelt formuyla maliyeti 56,630841 yapmaya calisti,
    # UPDATE hatasiz calisti ama yazdiktan hemen sonra okundugunda deger
    # UYUSMUYORDU). Kok neden: yukaridaki tablolar parasal alanlari
    # `REAL` (Postgres tek hassasiyetli float4, ~6-7 anlamli basamak) ile
    # tanimliyordu. 56,630841 gibi 8 anlamli basamakli bir deger REAL'de
    # TAM olarak saklanamiyor - en yakin temsil edilebilir degere
    # yuvarlaniyor (ornegin 56,63084 gibi). v2.0.7.115'te Alis/Guncel
    # gosterimi 4 ondalitktan 6 ondaliga cikarilinca bu sorun daha da
    # belirginlesti. CREATE TABLE'lar artik DOUBLE PRECISION (8 byte,
    # Python'un native float'iyla ayni, ~15-17 anlamli basamak) kullaniyor
    # - ama bu SADECE YENI kurulan tablolar icin gecerli. Bahri'nin
    # Supabase'inde tablolar ZATEN REAL ile olusturulmus oldugundan,
    # asagidaki ALTER COLUMN'lar mevcut tablolari da yukseltir (idempotent
    # - DOUBLE PRECISION'a zaten yukseltilmisse hata vermez, sadece atlanir
    # gibi davranir cunku ALTER COLUMN TYPE ayni tipe de guvenle uygulanir).
    for _tablo, _kolon in (
        ("portfolio", "quantity"), ("portfolio", "avg_cost"),
        ("portfolio_sales", "quantity"), ("portfolio_sales", "buy_price"),
        ("portfolio_sales", "sell_price"), ("portfolio_sales", "fee_pct"),
        ("portfolio_sales", "tax_pct"), ("portfolio_sales", "fee_amount"),
        ("portfolio_sales", "tax_amount"), ("portfolio_sales", "gross_pl"),
        ("portfolio_sales", "net_pl"),
        ("portfolio_fee_settings", "fee_pct"), ("portfolio_fee_settings", "tax_pct"),
        ("portfolio_capital_tx", "amount"),
    ):
        try:
            c.execute(f"ALTER TABLE {_tablo} ALTER COLUMN {_kolon} TYPE DOUBLE PRECISION")
        except Exception as _e:
            print(f"[db] REAL->DOUBLE PRECISION yukseltme atlandi ({_tablo}.{_kolon}): {_e}")

    # v2.0.7.156: beklenti_otomatik_tespit tablosu v2.0.7.154'te
    # (eski "kullanici_iptal" semasiyla) zaten olusturulmus olabilir -
    # bu ALTER'lar idempotent, tabloyu yeni ("onay_durumu") semaya
    # guvenle yukseltir. Eski kayitlar varsa (hicbiri Bahri tarafindan
    # gercekten onaylanmamisti - "kullanici_iptal" mantigi hicbir zaman
    # canliya cikmadi) onay_durumu='bekliyor' varsayilanina duser.
    try:
        c.execute("ALTER TABLE beklenti_otomatik_tespit ADD COLUMN IF NOT EXISTS onay_durumu TEXT NOT NULL DEFAULT 'bekliyor'")
        c.execute("ALTER TABLE beklenti_otomatik_tespit ADD COLUMN IF NOT EXISTS onay_zamani TIMESTAMP")
    except Exception as _e:
        print(f"[db] beklenti_otomatik_tespit sema yukseltme atlandi: {_e}")

    # Idempotent index'ler
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_email      ON users(LOWER(email))")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token   ON sessions(token)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user   ON portfolio(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_sales_user ON portfolio_sales(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_capital_tx_user ON portfolio_capital_tx(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_rates_user ON benchmark_rates(user_id)")

    # v2.0.7.100 - KRITIK GUVENLIK DUZELTMESI (Bahri'nin bulgusu, 22 Temmuz
    # 2026: Supabase "CRITICAL: Table publicly accessible - Row-Level
    # Security is not enabled" uyarisi). Bu 6 tabloda (users, portfolio,
    # sessions, password_resets, portfolio_sales, portfolio_fee_settings)
    # RLS'i etkinlestiren HICBIR satir yoktu - oysa firsat_radari.py/
    # worker.py'deki 3 tablo (intraday_scores, radar_alerts,
    # bist_universe_dynamic) bunu zaten yapiyordu. portfolio_sales/
    # portfolio_fee_settings ozellikle supheliydi: ikisi de 16 Temmuz'da
    # (muhasebe sistemiyle, v2.0.7.47) eklenmisti - 1-2 Temmuz'daki
    # (Session XII) manuel RLS taramasindan SONRA, o taramaya hic dahil
    # olmadan. ALTIN TASI: uygulama Supabase'e DOGRUDAN Postgres
    # baglantisiyla (psycopg2 tarzi, servis/sahip rolu ile) baglaniyor -
    # bu rol RLS'i dogal olarak ATLAR (BYPASSRLS), yani asagidaki RLS
    # ac,ma app'in KENDI erisimini ETKILEMEZ - SADECE Supabase'in genel
    # PostgREST API'sinden (herkesin proje URL'siyle erisebildigi katman)
    # gelen YETKISIZ erisimi kapatir. Politika (CREATE POLICY) eklenmedi -
    # zaten calisan 3 tablodaki AYNI ("sadece RLS'i ac, politika yok")
    # deseni izleniyor; RLS + politika yoksa PostgREST katmani o tabloya
    # SIFIR erisim verir, bu tam istenen davranis.
    # v2.0.7.112 - yeni portfolio_capital_tx da bu listeye eklendi (ayni
    # gerekce - kullanici finansal verisi tasiyan her yeni tablo icin
    # kalici kural, bkz. Bolum 0).
    for _rls_tablo in ("users", "portfolio", "sessions", "password_resets",
                       "portfolio_sales", "portfolio_fee_settings",
                       "portfolio_capital_tx", "benchmark_rates"):
        try:
            c.execute(f"ALTER TABLE {_rls_tablo} ENABLE ROW LEVEL SECURITY")
        except Exception as _e:
            print(f"[db] RLS etkinlestirme atlandi ({_rls_tablo}): {_e}")

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


def get_intraday_overlay(freshness_minutes: int = 45) -> dict:
    """v2.0.7.134 (Bahri'nin bulgusu, 11 Agustos 2026 - TUPRS 63,0 vs
    76,0): app.py'nin load_universe()'i, CSV'nin (worker.py, gunde 1-2
    kez) USTUNE Firsat Radari'nin (firsat_radari.py, 20 dakikada bir)
    Supabase intraday_scores tablosuna yazdigi TAZE veriyi bindiriyordu
    ("Firsat Radari overlay") - bu overlay mantigi SADECE app.py icinde
    inline yaziliydi. Bu fonksiyon o overlay mantiginin TEK, PAYLASILAN
    kaynagi - hem app.py hem temettu_client.py/halka_arz_client.py/
    emailer.py buradan cagirir. {ticker: {"kategori":, "skor":, "fiyat":,
    "rsi":, "ret1m":}} doner. Tablo yoksa/baglanti sorunu varsa sessizce
    bos dict doner (cagiran taraf CSV'yle devam eder, hata firlatmaz)."""
    try:
        rows = get_conn().execute(
            "SELECT ticker, kategori, skor, fiyat, rsi, ret1m FROM intraday_scores "
            f"WHERE updated_at > now() - interval '{int(freshness_minutes)} minutes'"
        ).fetchall()
    except Exception:
        return {}
    if not rows:
        return {}

    def _rv(r, k, i):
        return r[k] if isinstance(r, dict) else r[i]

    sonuc = {}
    for r in rows:
        sonuc[str(_rv(r, "ticker", 0))] = {
            "kategori": _rv(r, "kategori", 1), "skor": _rv(r, "skor", 2),
            "fiyat": _rv(r, "fiyat", 3), "rsi": _rv(r, "rsi", 4),
            "ret1m": _rv(r, "ret1m", 5),
        }
    return sonuc


# ══════════════════════════════════════════════════════════════
# Beklenti Modu — Otomatik Haber Tespiti (v2.0.7.154)
# ══════════════════════════════════════════════════════════════

def haber_islendi_mi(url: str) -> bool:
    """haber_izleme.py'nin AYNI haberi tekrar tekrar islememesi icin -
    her calismada once bu kontrol edilir."""
    try:
        row = get_conn().execute(
            "SELECT 1 FROM haber_islenmis WHERE haber_url=?", (url,)
        ).fetchone()
        return row is not None
    except Exception:
        return False


def haber_islendi_isaretle(url: str):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO haber_islenmis (haber_url) VALUES (?) "
            "ON CONFLICT (haber_url) DO NOTHING", (url,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] haber_islendi_isaretle hata: {e}", file=sys.stderr)


def haber_akisi_ekle(haber_url: str, kaynak: str, baslik: str,
                     baslik_tr: str = None, eslesen_kalip: str = None,
                     yayin_zamani=None):
    """v2.0.7.160: Taranan HER haberi akisa yazar - eslesen_kalip None ise
    'tarandi, sakin' demektir. Ayni URL tekrar gelirse hicbir sey yapmaz."""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO haber_akisi (haber_url, kaynak, baslik, baslik_tr, "
            "eslesen_kalip, yayin_zamani) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT (haber_url) DO NOTHING",
            (haber_url, kaynak, baslik, baslik_tr, eslesen_kalip, yayin_zamani))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] haber_akisi_ekle hata: {e}", file=sys.stderr)


def haber_akisi_ceviri_yaz(haber_url: str, baslik_tr: str):
    """v2.0.7.160: Toplu ceviri sonrasi Turkce basligi geriye yazar."""
    try:
        conn = get_conn()
        conn.execute("UPDATE haber_akisi SET baslik_tr=? WHERE haber_url=?",
                     (baslik_tr, haber_url))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] haber_akisi_ceviri_yaz hata: {e}", file=sys.stderr)


def get_haber_akisi(saat: int = 48, limit: int = 300) -> list:
    """v2.0.7.160: Haberler sayfasi icin - EN YENI EN USTTE. eslesen_kalip
    dolu olanlar sayfada ayrica ustte gosterilir, bu fonksiyon ikisini de
    ayni listede tek sorguda doner."""
    try:
        rows = get_conn().execute(
            "SELECT haber_url, kaynak, baslik, baslik_tr, eslesen_kalip, "
            "COALESCE(yayin_zamani, eklenme_zamani) AS zaman "
            "FROM haber_akisi "
            f"WHERE COALESCE(yayin_zamani, eklenme_zamani) > now() - interval '{int(saat)} hours' "
            "ORDER BY zaman DESC LIMIT ?", (int(limit),)
        ).fetchall()
    except Exception as e:
        print(f"[db] get_haber_akisi hata: {e}", file=sys.stderr)
        return []
    sonuc = []
    for r in rows:
        def _hv(k, i):
            return r[k] if isinstance(r, dict) else r[i]
        sonuc.append({
            "haber_url": _hv("haber_url", 0), "kaynak": _hv("kaynak", 1),
            "baslik": _hv("baslik", 2), "baslik_tr": _hv("baslik_tr", 3),
            "eslesen_kalip": _hv("eslesen_kalip", 4), "zaman": _hv("zaman", 5),
        })
    return sonuc


def haber_akisi_temizle(gun: int = 7):
    """v2.0.7.160: 7 gunden eski haberleri siler - tablo sinirsiz buyumesin.
    haber_izleme.py her turun sonunda cagirir."""
    try:
        conn = get_conn()
        conn.execute("DELETE FROM haber_akisi WHERE eklenme_zamani < "
                     f"now() - interval '{int(gun)} days'")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] haber_akisi_temizle hata: {e}", file=sys.stderr)


def ai_cagri_sayisi_bugun() -> int:
    """v2.0.7.160: Bugun kac Gemini cagrisi yapildi? Butce kontrolu icin."""
    try:
        bugun = datetime.date.today().isoformat()
        row = get_conn().execute(
            "SELECT cagri_sayisi FROM ai_cagri_butcesi WHERE tarih=?",
            (bugun,)).fetchone()
        if not row:
            return 0
        return int(row["cagri_sayisi"] if isinstance(row, dict) else row[0])
    except Exception as e:
        print(f"[db] ai_cagri_sayisi_bugun hata: {e}", file=sys.stderr)
        return 0  # okunamadiysa engelleme - cagri yapilsin


def ai_cagri_kaydet(adet: int = 1):
    """v2.0.7.160: Yapilan Gemini cagrisini gunluk sayaca ekler."""
    try:
        bugun = datetime.date.today().isoformat()
        conn = get_conn()
        conn.execute(
            "INSERT INTO ai_cagri_butcesi (tarih, cagri_sayisi) VALUES (?,?) "
            "ON CONFLICT (tarih) DO UPDATE SET "
            "cagri_sayisi = ai_cagri_butcesi.cagri_sayisi + ?",
            (bugun, int(adet), int(adet)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] ai_cagri_kaydet hata: {e}", file=sys.stderr)


def otomatik_tespit_ekle(kalip_key: str, siddet: str, haber_basligi: str,
                          haber_url: str, haber_kaynak: str, ai_gerekce: str,
                          gecerlilik_saat: int = 48):
    """haber_izleme.py, AI dogrulamasi basarili olunca bunu cagirir -
    tespit varsayilan olarak 'bekliyor' durumunda eklenir, HENUZ
    UYGULANMAZ (bkz. v2.0.7.156 - onay bekleme modeline gecis).
    gecerlilik_saat: kullanici onaylamazsa bu tespitin kac saat sonra
    otomatik "suresi dolmus" sayilacagi (bekleyenler listesinden
    kaybolur) - olay etkileri kalici degildir, sonsuza kadar onay
    beklememelidir."""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO beklenti_otomatik_tespit "
            "(kalip_key, siddet, haber_basligi, haber_url, haber_kaynak, "
            "ai_gerekce, gecerlilik_bitis) "
            "VALUES (?,?,?,?,?,?, now() + interval '%s hours')" % int(gecerlilik_saat),
            (kalip_key, siddet, haber_basligi, haber_url, haber_kaynak, ai_gerekce))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] otomatik_tespit_ekle hata: {e}", file=sys.stderr)
        return False


def get_bekleyen_tespitler() -> list:
    """v2.0.7.156 (Bahri'nin talebi, KRİTİK tasarım düzeltmesi): app.py
    bunu her sayfa yuklemesinde cagirir - suresi gecmemis VE HENUZ
    ONAY/RED VERİLMEMİŞ tespitleri doner. Bunlar Optima Skor'a HENUZ
    UYGULANMAMIŞTIR - sadece kullanıcıya "onaylar mısınız?" diye
    gösterilecek adaylardır."""
    try:
        rows = get_conn().execute(
            "SELECT id, kalip_key, siddet, haber_basligi, haber_url, "
            "haber_kaynak, ai_gerekce, tespit_zamani FROM beklenti_otomatik_tespit "
            "WHERE gecerlilik_bitis > now() AND onay_durumu = 'bekliyor' "
            "ORDER BY tespit_zamani DESC"
        ).fetchall()
    except Exception:
        return []
    return _tespit_satirlarini_donustur(rows)


def get_onaylanmis_tespitler() -> list:
    """v2.0.7.156: kullanıcının AÇIKÇA onayladığı, hâlâ geçerlilik
    süresi dolmamış tespitler - SADECE BUNLAR Optima Skor'a uygulanır."""
    try:
        rows = get_conn().execute(
            "SELECT id, kalip_key, siddet, haber_basligi, haber_url, "
            "haber_kaynak, ai_gerekce, tespit_zamani FROM beklenti_otomatik_tespit "
            "WHERE gecerlilik_bitis > now() AND onay_durumu = 'onaylandi' "
            "ORDER BY tespit_zamani DESC"
        ).fetchall()
    except Exception:
        return []
    return _tespit_satirlarini_donustur(rows)


def _tespit_satirlarini_donustur(rows) -> list:
    sonuc = []
    for r in rows:
        def _rv(k, i):
            return r[k] if isinstance(r, dict) else r[i]
        sonuc.append({
            "id": _rv("id", 0), "kalip_key": _rv("kalip_key", 1),
            "siddet": _rv("siddet", 2), "haber_basligi": _rv("haber_basligi", 3),
            "haber_url": _rv("haber_url", 4), "haber_kaynak": _rv("haber_kaynak", 5),
            "ai_gerekce": _rv("ai_gerekce", 6), "tespit_zamani": _rv("tespit_zamani", 7),
        })
    return sonuc


def tespit_onayla(tespit_id: int):
    """Kullanıcı (Ana Sayfa'daki "Onayla" butonu) bir tespiti uygun
    bulursa - BUNDAN SONRA Optima Skor'a uygulanır."""
    try:
        conn = get_conn()
        conn.execute(
            "UPDATE beklenti_otomatik_tespit SET onay_durumu='onaylandi', "
            "onay_zamani=now() WHERE id=?", (tespit_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] tespit_onayla hata: {e}", file=sys.stderr)
        return False


def tespit_reddet(tespit_id: int):
    """Kullanıcı bir tespiti uygun bulmazsa - bir daha gösterilmez,
    Optima Skor'a HİÇ uygulanmaz."""
    try:
        conn = get_conn()
        conn.execute(
            "UPDATE beklenti_otomatik_tespit SET onay_durumu='reddedildi', "
            "onay_zamani=now() WHERE id=?", (tespit_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] tespit_reddet hata: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    init_db()
