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
        # v2.0.7.325 (17 Eylul 2026, Bahri'nin push SONRASI ikinci logunun
        # ANALIZI sirasinda bulundu - GERCEK, KESIN, %100 TEKRARLANAN KOK
        # NEDEN): v2.0.7.324 (haber_islendi_mi ve 9 fonksiyona eksik
        # close() eklenmesi) DOGRU bir duzeltmeydi ama YETERSIZDI - push
        # sonrasi ikinci logda hata AYNI SIKLIKTA (~1-1,4 saniyede bir,
        # calismanin TAMAMI boyunca, %100 basarisizlikla) devam etti.
        # ASIL SORUN cok daha temeldeydi ve get_conn()'un PRE-PING
        # mantiginin KENDISINDEYDI:
        #   1) get_conn() onbellekteki baglantinin canli olup olmadigini
        #      kontrol etmek icin bir "SELECT 1" calistiriyordu (bkz.
        #      asagidaki pre-ping) - psycopg2'de autocommit=False
        #      OLDUGU icin bu SELECT, KENDISI bir transaction BASLATIYORDU.
        #   2) Pre-ping "basarili" olur olmaz, get_conn() hemen
        #      `_CompatConn(_toplu_baglanti_onbellek)` cagiriyordu - yani
        #      BU __init__ calisiyordu, ve BURASI HER ZAMAN
        #      `self._conn.autocommit = False` diye bir atama YAPIYORDU.
        #   3) psycopg2'de, AKTIF BIR TRANSACTION VARKEN `autocommit`
        #      OZELLIGINE DEGER ATAMAK YASAKTIR - `ProgrammingError`
        #      FIRLATIR (tam olarak logda gorulen istisna turu!). Pre-
        #      ping'in kendi SELECT 1'i transaction'i HENUZ AC IK
        #      BIRAKTIGI icin, bu __init__ HER SEFERINDE bu hatayi
        #      TETIKLIYORDU - baglanti gercekten canli/olu olmasindan
        #      BAGIMSIZ OLARAK, %100 tekrarlanabilir sekilde. Bu, get_conn()
        #      icindeki AYNI try/except tarafindan yakalanip yanlislikla
        #      "onbellekteki baglanti canli degil" olarak loglaniyordu -
        #      gercekte baglanti CANLIYDI, sadece bu satir onu KENDI
        #      KENDINE gecersiz kiliyordu.
        # COZUM: psycopg2 baglantilari zaten VARSAYILAN OLARAK
        # autocommit=False geliyor - bu satir hicbir zaman gerekli
        # DEGILDI (yeni acilan baglantilarda no-op, yeniden kullanilan
        # baglantilarda ZARARLI). Satir tamamen KALDIRILDI.
        self._conn = pg_conn

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
        # v2.0.7.310 (15 Eylul 2026, O&M4): TOPLU MOD aktifse (bkz.
        # toplu_mod_ac()) bu, PAYLASILAN toplu-calisma baglantisidir -
        # her db.py fonksiyonu kendi isini bitirince .close() cagiriyor
        # (tek kullanimlik baglanti VARSAYIMIYLA yazilmislar) - eger bu
        # PAYLASILAN baglantiyi burada GERCEKTEN kapatirsak, TOPLU
        # MOD'un butun amaci (tek calismada TEK baglanti) bosa cikar.
        #
        # v2.0.7.320 (16 Eylul 2026, Bahri'nin CANLI kanitiyla - Session
        # pooler'a gecildikten SONRA BILE ayni "onbellekteki baglanti
        # canli degil (ProgrammingError)" hatasi ~100 kez tekrarlandi -
        # yani sorun pooler TURU degilmis): KOK NEDEN BULUNDU - close()
        # burada eskiden TAMAMEN HICBIR SEY yapmiyordu (sadece "return").
        # db.py fonksiyonlarinin COGU (orn. get_kaliplar()) SELECT-only
        # birden fazla sorgu calistirip ASLA commit() cagirmiyor (yazma
        # islemi olmadigi icin gereksiz sayiliyordu) - sadece .close()
        # cagiriyorlar. Toplu modda o .close() hicbir sey yapmayinca,
        # o SORGULARIN ACTIGI TRANSACTION AC IK KALIYORDU. RSS kaynaklarini
        # cekerken gecen saniyeler/onlarca saniye boyunca bu acik islem
        # ASILI kaliyor - Supabase'in pooler'i (Transaction VEYA Session,
        # ikisinde de ayni hata gorulduğu icin ikisi de etkileniyor)
        # muhtemelen bir "idle in transaction" zaman asimiyla bunu
        # SESSIZCE olduruyor - bir sonraki sorgu (pre-ping dahil) da
        # tam bu yuzden ProgrammingError ile pathliyor.
        # COZUM: TCP baglantiyi KAPATMIYORUZ (toplu modun amaci hala
        # bu) ama ACIK KALAN TRANSACTION'I commit() ile SONLANDIRIYORUZ -
        # boylece db.py fonksiyonu isini bitirip .close() dedigi AN
        # transaction temizleniyor, sonraki cagriya kadar ACIK ASILI
        # KALMIYOR.
        global _toplu_baglanti_onbellek
        if _TOPLU_MOD["aktif"] and self._conn is _toplu_baglanti_onbellek:
            try:
                self._conn.commit()
            except Exception:
                pass
            return
        try:
            self._conn.close()
        except Exception:
            pass


# ============================================================================
# v2.0.7.310: TOPLU MOD - SADECE tek seferlik, dogrusal calisan BATCH
# script'ler (haber_izleme.py, kap_bildirim_izleme.py) icin, BILEREK
# app.py'nin (Streamlit, uzun omurlu, cok sayida ayri rerun) senaryosuna
# HICBIR SEKILDE dokunmuyor - varsayilan KAPALI, hicbir mevcut davranis
# degismez. v2.0.7.142'nin havuzlama COKMELERINDEN (bkz. _CompatConn
# ustundeki not) KOKTEN FARKLI bir senaryo: (1) BIR TEK baglanti (havuz
# YOK - "havuz tukenmesi" cokme turu bu yuzden BURADA IMKANSIZ), (2)
# SADECE tek, kisa (dakikalar suren) bir script calismasi icinde -
# Supabase pooler'inin saatlerce/gunlerce IDLE bir baglantiyi sessizce
# dusurmesi senaryosu (2. cokme turu) bu kisa sure icinde COK DUSUK
# ihtimal, AMA yine de "sunucu tarafinda dusurulmus baglanti" ihtimaline
# karsi HER get_conn() cagrisinda PRE-PING (SELECT 1) ile kontrol
# ediliyor - dusmusse SESSIZCE yeni baglanti aciliyor, hicbir hata
# disariya sizmiyor. Bu, gecmis notun aciqca istedigi "pre-ping / retry-
# on-execute" tasarimidir.
_TOPLU_MOD = {"aktif": False}
_toplu_baglanti_onbellek = None


def toplu_mod_ac():
    """SADECE haber_izleme.py/kap_bildirim_izleme.py gibi tek seferlik,
    calisip biten batch script'lerin main()/calistir() basinda cagirmasi
    icin. app.py BUNU ASLA CAGIRMAMALI - Streamlit'in uzun omurlu, cok
    sayida ayri rerun yaptigi baglamda bu KESINLIKLE test edilmedi ve
    v2.0.7.142'nin ele aldigi TAM O riskli senaryoyu yeniden getirebilir."""
    global _toplu_baglanti_onbellek
    _TOPLU_MOD["aktif"] = True
    _toplu_baglanti_onbellek = None
    print("[db] Toplu mod ACIK - bu calisma boyunca TEK baglanti yeniden kullanilacak.",
          file=sys.stderr)


def toplu_mod_kapat():
    """Toplu modu kapatir VE varsa gercekten bekleyen paylasilan
    baglantiyi kapatir. Batch script'in main()'inin SONUNDA (try/finally
    icinde, hata olsa bile calisacak sekilde) cagrilmali."""
    global _toplu_baglanti_onbellek
    _TOPLU_MOD["aktif"] = False
    if _toplu_baglanti_onbellek is not None:
        try:
            _toplu_baglanti_onbellek.close()
        except Exception:
            pass
        _toplu_baglanti_onbellek = None
    print("[db] Toplu mod KAPALI - paylasilan baglanti kapatildi.", file=sys.stderr)


# ============================================================================
# Public API: get_conn  -  v2.0.7.142: basit, guvenilir (havuz KALDIRILDI)
# ============================================================================
def get_conn() -> _CompatConn:
    """Supabase PostgreSQL baglantisi dondurur - basit, kanitlanmis
    guvenilir yontem (havuzlama v2.0.7.142'de KALDIRILDI, bkz.
    _CompatConn'un modul ustu notu - iki ayri cokme turune yol acmisti).

    v2.0.7.310: Toplu mod ACIKSA (bkz. toplu_mod_ac()), her cagrida SIFIRDAN
    yeni baglanti acmak yerine, ONCE onbellekteki paylasilan baglantinin
    HALA CANLI olup olmadigi PRE-PING (SELECT 1) ile kontrol edilir - canliysa
    O DONER (yeni baglanti YOK), degilse (sunucu tarafinda dusurulmus olabilir)
    SESSIZCE yeni bir tane acilip onbelleklenir. Toplu mod KAPALIYSA (varsayilan,
    app.py dahil TUM diger her yer) davranis v2.0.7.142'den beri AYNEN korunur -
    her cagrida sifirdan yeni baglanti."""
    global _toplu_baglanti_onbellek
    if not PSYCOPG2_OK:
        raise RuntimeError(
            "psycopg2-binary yuklu degil. requirements.txt'e ekleyin: psycopg2-binary>=2.9"
        )

    if _TOPLU_MOD["aktif"] and _toplu_baglanti_onbellek is not None:
        try:
            _pre_ping_cur = _toplu_baglanti_onbellek.cursor()
            _pre_ping_cur.execute("SELECT 1")
            _pre_ping_cur.close()
            # v2.0.7.325: pre-ping'in kendi actigi transaction'i (autocommit
            # False oldugundan SELECT 1 bile bir transaction baslatir)
            # burada kapatiyoruz - _CompatConn.__init__ artik autocommit
            # atamasi yapmasa da, baglantiyi "temiz" (transaction'siz)
            # teslim etmek ileride benzer bir sorunu onceden onler.
            _toplu_baglanti_onbellek.rollback()
            return _CompatConn(_toplu_baglanti_onbellek)
        except Exception as e:
            # v2.0.7.323 (17 Eylul 2026, Bahri'nin paylastigi loglarin
            # ANALIZI sirasinda bulundu): Bu satir zaman damgasi
            # ICERMIYORDU ve sys.stderr'e yaziyordu, oysa
            # haber_izleme.py'deki "Baslangic"/"ZAMANLAMA" satirlari
            # duz print() ile stdout'a yaziyor - GitHub Actions gibi bir
            # TTY olmayan ortamda Python stdout'u VARSAYILAN OLARAK
            # BLOK-TAMPONLU (stderr ise tamponsuz/satir-tamponlu), yani
            # bu iki akis BIRLESTIRILMIS logda GERCEK KRONOLOJIK sirayla
            # GORUNMEYEBILIR - stderr mesajlari erken "gorunse" bile
            # ASLINDA cok daha SONRA (orn. 295 haberin taranmasi sirasinda)
            # olusmus olabilirler. Bu, v2.0.7.320'nin (toplu mod
            # close()/commit() duzeltmesi) gercekten ise yarayip
            # yaramadigini SADECE log SIRASINA bakarak guvenilir bicimde
            # degerlendirmeyi IMKANSIZ kiliyordu. Zaman damgasi + flush=True
            # eklenerek bir sonraki calismada KESIN, guvenilir bir zaman
            # cizelgesi elde edilecek.
            import datetime as _dt_reconnect
            print(f"[db] {_dt_reconnect.datetime.now().isoformat()} Toplu mod: "
                  f"onbellekteki baglanti canli degil ({type(e).__name__}), "
                  f"yenisi aciliyor.", file=sys.stderr, flush=True)
            try:
                _toplu_baglanti_onbellek.close()
            except Exception:
                pass
            _toplu_baglanti_onbellek = None

    url = _get_db_url()
    if not url:
        raise RuntimeError(
            "Supabase db_url ayarlanmamis. Streamlit Cloud Secrets'ta tanimlayin:\n"
            "  [supabase]\n"
            "  db_url = \"postgresql://...\"\n"
            "Veya GitHub Actions icin env: SUPABASE_DB_URL"
        )
    try:
        # v2.0.7.326 (17 Eylul 2026, Bahri'nin bulgusu - v2.0.7.325
        # push'undan HEMEN SONRA GitHub Actions'ta "Beklenti Modu Haber
        # Izleme" calismalari normalin (~12-20 dk) cok uzerine cikti -
        # biri 20 dk'lik workflow zaman asimina tam denk gelip kesildi,
        # digeri 31+ dk'dir "In progress" (asili) durumda): v2.0.7.325
        # onbellekteki baglantinin YANLIŞLIKLA HER SEFERINDE yeniden
        # acilmasina yol acan hatayi duzeltti - ama bu, ISTENMEYEN bir
        # yan etkiyi de ORTAYA CIKARDI: baglanti artik GERCEKTEN uzun
        # sure (dakikalarca) tek parca halinde yeniden kullanilabiliyor.
        # Bu baglantida ne connect_timeout (sadece ILK baglanti kurma
        # asamasini kapsar) ne de bir statement/soket zaman asimi
        # TANIMLIYDI - Supabase'in pooler'i (ya da araya giren herhangi
        # bir ag bileseni) bu uzun-omurlu baglantiyi SESSIZCE (TCP
        # FIN/RST gondermeden) dusurursen, sonraki sorgu (pre-ping'in
        # kendi SELECT 1'i dahil) TCP'nin isletim sistemi seviyesindeki
        # varsayilan (COK UZUN, onlarca dakikaya varabilen) yeniden-
        # deneme suresi dolana kadar SONSUZA KADAR ASILI KALIR - tam
        # olarak gozlemlenen 20-31+ dakikalik "takilma" ile ortusuyor.
        # COZUM: TCP keepalive (olu baglantiyi ~30 saniye icinde tespit
        # eder) + PostgreSQL statement_timeout (herhangi bir sorgu 30
        # saniyeden uzun surerse ACIK bir hata firlatir, sessizce asili
        # KALMAZ) eklendi. Boylece "olu ama henuz fark edilmemis"
        # baglantilar ARTIK saniyeler icinde (dakikalar/onlarca dakika
        # yerine) tespit edilip mevcut reconnect mantigina duser.
        pg_conn = psycopg2.connect(
            url, connect_timeout=10,
            keepalives=1, keepalives_idle=15,
            keepalives_interval=5, keepalives_count=3,
            options="-c statement_timeout=30000",
        )
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

    if _TOPLU_MOD["aktif"]:
        _toplu_baglanti_onbellek = pg_conn

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
        expires_at  TIMESTAMP,
        phone_number TEXT
    )""")
    # v2.0.7.214 (Bahri'nin talebi, 29 Ağustos 2026 — "Abonelik
    # Ayarları'na profil bilgileri, iletişim bilgileri, şifre
    # değişikliği eklensin"): mevcut tabloya sütunu ekle (idempotent) -
    # canlıdaki tablo zaten var.
    try:
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number TEXT")
    except Exception as e:
        print(f"[db] users phone_number migration hatasi: {e}", file=sys.stderr)

    # v2.0.7.353 (3 Ekim 2026, Bahri'nin talebi - "kullanıcı hangi
    # portföy tarzını tercih ederse emaillerde ve Ana Sayfa portföy
    # bütçesinde AYNI FORMÜL kullanılmalı"): portfoy_optimizasyon.py'nin
    # desteklediği iki stratejiden ('kuresel' | 'kategori_guvenceli')
    # hangisinin kullanılacağı - hem canlı uygulama hem zamanlanmış
    # e-posta BU SÜTUNU okuyacak, tek kaynak.
    try:
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                  "portfoy_dagilim_stratejisi TEXT NOT NULL DEFAULT 'kuresel'")
    except Exception as e:
        print(f"[db] users portfoy_dagilim_stratejisi migration hatasi: {e}", file=sys.stderr)

    # v2.0.7.355 (3 Ekim 2026, Bahri'nin bulgusu - e-posta 20.000 TL/Orta/10
    # (ortam değişkeni varsayılanları) kullanırken, uygulama 25.000 TL/Orta/10
    # (app.py'nin KENDİ varsayılanı) kullanıyordu - İKİSİ DE "varsayılan"
    # olduğu için hiç fark edilmeden sapmışlardı): Bütçe/Risk/Max Varlık da
    # artık stratejiyle AYNI şekilde kalıcı, kullanıcı bazlı bir tercih -
    # hem Ana Sayfa hem e-posta BURADAN okuyacak.
    try:
        # v2.0.7.356 (3 Ekim 2026, Bahri'nin bulgusu - "e-postalar hep
        # 20.000 TL gösteriyor, uygulama 25.000 TL varsayılan kullanıyor,
        # bunlar AYNI olmalı"): varsayılan 25000'den 20000'e düzeltildi -
        # e-postanın GERÇEK, tutarlı tarihçesi 20.000 TL idi.
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                  "portfoy_butce NUMERIC NOT NULL DEFAULT 20000")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                  "portfoy_risk TEXT NOT NULL DEFAULT 'Orta'")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                  "portfoy_max_varlik INTEGER NOT NULL DEFAULT 10")
    except Exception as e:
        print(f"[db] users portfoy_butce/risk/max_varlik migration hatasi: {e}", file=sys.stderr)

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
    # v2.0.7.246 (2 Eylul 2026, Bahri'nin bulgusu - "pop-up'lar tercih
    # yapmama ragmen yine de uzun sureyle ekranda kaliyorlar", genel
    # yavasligin UCUNCU bir kaynagi): app.py'deki `load_portfolio()`
    # fonksiyonu HER TEK cagrisinda (yani Portfoyum sayfasi her acildiginda/
    # yenilendiginde) bu IKI ALTER TABLE komutunu (try/except icinde,
    # "zaten var" hatasini yutarak) YENIDEN calistiriyordu - CREATE TABLE
    # zaten bu sutunlari icerdigi icin (yukarida) bu satirlar SADECE eski,
    # sutunlarin YENI eklendigi donemden kalma bir migration'in kalintisiydi,
    # gercekte HICBIR ISLEV GORMUYORDU ama HER SEFERINDE Supabase'e 2 fazla
    # round-trip yaptiriyordu. Idempotent (IF NOT EXISTS) hali BURAYA (init_db,
    # sadece oturum basina 1 kez calisir) tasindi, load_portfolio()'daki
    # tekrarlayan try/except versiyonlari KALDIRILDI (asagida bkz).
    c.execute("ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS purchase_date TEXT DEFAULT ''")
    c.execute("ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS unit_type TEXT DEFAULT 'Adet'")

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
    # v2.0.7.203 (Bahri'nin talebi, 26 Ağustos 2026 — "her abone kendi
    # tespitlerini görsün/onaylasın, Optima Skor kişiye özel olsun"):
    # KRİTİK MİMARİ DEĞİŞİKLİK. `beklenti_otomatik_tespit` (yukarıda)
    # ARTIK SADECE PAYLAŞIMLI/OBJEKTİF tespit kaydını tutuyor (hangi
    # haber, hangi kalıp, ne zaman tespit edildi) - `onay_durumu`
    # sütunu ARTIK KULLANICI KARARI İÇİN KULLANILMIYOR (geriye dönük
    # uyumluluk için siliniyor değil, sadece yeni kodda yazılmıyor).
    # Her kullanıcının KENDİ kararı (onayladı/reddetti) bu YENİ ayrı
    # tabloda tutuluyor - UNIQUE(kullanici_id, tespit_id) ile bir
    # kullanıcı aynı tespite sadece TEK bir karar verebilir (fikrini
    # değiştirirse UPSERT ile güncellenir).
    c.execute("""
    CREATE TABLE IF NOT EXISTS kullanici_tespit_karari (
        id            SERIAL PRIMARY KEY,
        kullanici_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        tespit_id     INTEGER NOT NULL REFERENCES beklenti_otomatik_tespit(id) ON DELETE CASCADE,
        karar         TEXT NOT NULL,
        karar_zamani  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(kullanici_id, tespit_id)
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
        eklenme_zamani TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        ozet           TEXT,
        ozet_tr        TEXT
    )""")
    # v2.0.7.179 (Bahri'nin talebi, 21 Ağustos 2026 — "başlıkları
    # çevirebiliyorsak kısa özeti de çevirebiliriz"): `ozet`/`ozet_tr`
    # sütunları CREATE TABLE'a eklendi (yeni kurulumlar için), ama
    # canlıdaki tablo ZATEN VAR ve bu sütunları içermiyor - CREATE TABLE
    # IF NOT EXISTS var olan bir tabloyu DEĞİŞTİRMEZ. Bu yüzden mevcut
    # tabloya ALTER TABLE ile idempotent (defalarca çalıştırılsa da
    # güvenli) şekilde ekleniyor.
    try:
        c.execute("ALTER TABLE haber_akisi ADD COLUMN IF NOT EXISTS ozet TEXT")
        c.execute("ALTER TABLE haber_akisi ADD COLUMN IF NOT EXISTS ozet_tr TEXT")
    except Exception as e:
        print(f"[db] haber_akisi ozet sutunu migration hatasi: {e}", file=sys.stderr)

    # v2.0.7.302 (15 Eylul 2026, O&M4, Bahri'nin talebi - "KAP, TEFAS,
    # TCMB ve diger kaynaklarimizin bildirimlerini de degerlendirelim"):
    # PORTFOYDEKI HER TICKER icin ayri KAP bildirim takibi. Bu, YUKARIDAKI
    # beklenti_otomatik_tespit'ten (macro Beklenti Modu kaliplari, bir
    # skor formulune uygulanan) BILEREK AYRI bir tablo - kap bildirimleri
    # bir skoru DEGISTIRMEZ, sadece OKUNACAK bilgidir (VBTS tedbiri,
    # sermaye artirimi, temettu karari vb.) - onay/red is akisi GEREKMEZ,
    # kullaniciya gosterilir, o okur/kapatir. UNIQUE kisitlamasi ayni
    # bildirimin farkli calistirmalarda TEKRAR eklenmesini (dogal olarak,
    # ON CONFLICT DO NOTHING ile) engeller.
    c.execute("""
    CREATE TABLE IF NOT EXISTS kap_bildirim_takip (
        id              SERIAL PRIMARY KEY,
        ticker          TEXT NOT NULL,
        kap_baslik      TEXT NOT NULL,
        gonderen        TEXT,
        gonderim_tarihi TIMESTAMP NOT NULL,
        icerik_ozet     TEXT,
        onemli_mi       BOOLEAN NOT NULL DEFAULT TRUE,
        tespit_tarihi   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(ticker, gonderim_tarihi, kap_baslik)
    )""")

    # v2.0.7.373 (8 Ekim 2026, Bahri'nin bulgusu - ENERY): TUM BIST evreni icin KAP bildirimlerinden
    # cikarilan HISSE BAZLI risk uyarilari. YUKARIDAKI kap_bildirim_takip'ten (sadece portfoy, sadece
    # bilgi) BILEREK AYRI: bu tablo load_universe()'te etiket + skor dusurme icin kullanilir.
    # kap_risk_tarama.py her taramada riskleri bildirim arsivinden (kap_risk_bildirim) SIFIRDAN hesaplayip
    # kap_risk_hepsini_yaz() ile bu tabloyu TAMAMEN degistirir (durum tutulmaz; suresi dolan/kalkan uyari silinir).
    c.execute("""
    CREATE TABLE IF NOT EXISTS kap_risk_uyari (
        id              SERIAL PRIMARY KEY,
        ticker          TEXT NOT NULL,
        kural           TEXT NOT NULL,
        seviye          TEXT NOT NULL,
        ad              TEXT,
        baslik          TEXT,
        gonderim_tarihi TIMESTAMP,
        bitis_tarihi    DATE NOT NULL,
        ozet            TEXT,
        tespit_tarihi   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(ticker, kural)
    )""")
    # Bildirim ARSIVI: kap_risk_tarama.py KAP'in toplu bildirim listesinden SADECE risk uretebilecek
    # turleri (VBTS, sira kapatma, denetim, sermaye...) buraya saklar (disclosure_index = KAP bildirim no,
    # tekrar eklenmez). Risk listesi her taramada bu arsivden SIFIRDAN hesaplanir (kap_risk.py).
    c.execute("""
    CREATE TABLE IF NOT EXISTS kap_risk_bildirim (
        disclosure_index BIGINT PRIMARY KEY,
        yayin_tarihi     TIMESTAMP NOT NULL,
        gonderen         TEXT,
        konu             TEXT NOT NULL,
        ozet             TEXT,
        gonderen_kodlar  TEXT,
        ilgili_kodlar    TEXT,
        metin            TEXT,
        eklenme_tarihi   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")

    # v2.0.7.342 (3 Ekim 2026, Bahri'nin talebi - "KAP, TEFAS, BIST, TCMB,
    # Cumhurbaskanligi/Bakanlar Kurulu, Resmi Gazete'nin fon krizi ile
    # ilgili bildirimlerinin otomatik izlenip ilgili varliklarin skoruna
    # yansitilmasi"): OTOMATIK PIYASA TEDBIRI IZLEME - spk_tedbir_fonlari.py
    # STATIK dosyasinin yerini alacak, veritabani tabanli, ONAY KAPILI
    # sistem. YUKARIDAKI kap_bildirim_takip'ten BILEREK AYRI: o SADECE
    # OKUNUR bilgi, bu AKTIF OLARAK Optima_Skor'u SIFIRLAR (load_universe()
    # icinde) - bu yuzden onay/red is akisi GEREKLI (beklenti_otomatik_
    # tespit'teki PRENSIP ayni, ama o KATEGORI-GENELI puan etkisi icin,
    # bu TEK TEK TICKER/SIRKET icin). Tek, PAYLASIMLI onay (per-kullanici
    # DEGIL) - cunku bu bir SPK/Resmi Gazete kararinin GERCEKTEN olup
    # olmadigi objektif bir OLGU, kisiye gore degisen bir yorum degil.
    #
    # piyasa_tedbir_tespit: AI'nin tespit ettigi, HENUZ onaylanmamis
    # adaylar (SPK bulteni/Resmi Gazete/KAP taramasindan).
    c.execute("""
    CREATE TABLE IF NOT EXISTS piyasa_tedbir_tespit (
        id                  SERIAL PRIMARY KEY,
        kaynak_turu         TEXT NOT NULL,
        kaynak_referans     TEXT,
        kaynak_url          TEXT,
        kaynak_tarihi       DATE,
        tespit_zamani       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        eslesme_turu        TEXT NOT NULL,
        deger               TEXT NOT NULL,
        kategori            TEXT,
        tedbir_turu         TEXT NOT NULL,
        ai_gerekce          TEXT,
        ai_ozet             TEXT,
        onay_durumu         TEXT NOT NULL DEFAULT 'bekliyor',
        onay_zamani         TIMESTAMP,
        onaylayan_kullanici_id INTEGER REFERENCES users(id),
        ek_veri             TEXT
    )""")
    # v2.0.7.370: KISMI_KALDIRMA tespitlerinin yapisal verisi (JSON: acilan/kalacak fonlar).
    # Mevcut (canli) tablo icin ALTER; yeni kurulumda CREATE zaten icerir.
    c.execute("ALTER TABLE piyasa_tedbir_tespit ADD COLUMN IF NOT EXISTS ek_veri TEXT")
    # piyasa_tedbir_listesi: ONAYLANMIS, AKTIF kurallar - load_universe()
    # HER YUKLEMEDE bunu okur. eslesme_turu='TICKER' -> deger TAM ticker
    # (orn. KTLEV), kategori ZORUNLU. eslesme_turu='SIRKET_ADI' -> deger
    # fon adinda aranacak alt-dize (orn. "PUSULA PORTFÖY") - bu, spk_
    # tedbir_fonlari.py'nin orijinal sirket-adi eslestirmesiyle AYNI
    # mantik: sirketin YENI eklenen fonlarini da otomatik yakalar, tek
    # tek ticker eklemeyi gerektirmez.
    c.execute("""
    CREATE TABLE IF NOT EXISTS piyasa_tedbir_listesi (
        id                SERIAL PRIMARY KEY,
        eslesme_turu      TEXT NOT NULL,
        deger             TEXT NOT NULL,
        kategori          TEXT,
        tedbir_turu       TEXT NOT NULL,
        kaynak_aciklama   TEXT,
        tespit_id         INTEGER REFERENCES piyasa_tedbir_tespit(id),
        eklenme_tarihi    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        aktif             BOOLEAN NOT NULL DEFAULT TRUE,
        kaldirilma_tarihi TIMESTAMP,
        UNIQUE(eslesme_turu, deger)
    )""")
    # spk_bulten_islenmis: hangi SPK bulten numaralarinin ZATEN tarandigi
    # (tekrar indirip AI'ye tekrar sormamak icin) - haber_islenmis ile
    # AYNI desen.
    c.execute("""
    CREATE TABLE IF NOT EXISTS spk_bulten_islenmis (
        bulten_no      TEXT PRIMARY KEY,
        islenme_zamani TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    _piyasa_tedbir_tohumla(conn)
    _piyasa_tedbir_ek_kurallar(conn)

    # v2.0.7.350 (3 Ekim 2026, Bahri'nin talebi - "95 günden geriye
    # gidilemiyor, en az 365 gün görebilmem lazım, dışarıda bir buffer
    # kursak çözüm olur mu?"): EVET - pytefas'ın GERÇEK TARİHSEL ARALIK
    # sorgusu (1y/5y) TEFAS API'sinde çok yavaş/güvenilmez çıktı (CANLI
    # ÖLÇÜLDÜ: "3 Ay" 1,78 sn, "5 Yıl" 38+ sn'de HİÇ TAMAMLANMADI). Ama
    # "TEFAS Aksam Guncelle" HER GÜN, TÜM 1348 fon için GÜNCEL fiyatı
    # ZATEN GÜVENİLİR ŞEKİLDE çekiyor (bulk endpoint). Bu tablo, HER GÜN
    # o günün fiyatını KALICI olarak biriktiren bir arşiv - zamanla
    # (bugünden itibaren) pytefas'ın büyük-aralık sorgusuna HİÇ ihtiyaç
    # duymadan GERÇEK, GÜVENİLİR bir tarihçe birikecek.
    c.execute("""
    CREATE TABLE IF NOT EXISTS tefas_fiyat_gecmisi (
        ticker TEXT NOT NULL,
        tarih  DATE NOT NULL,
        fiyat  NUMERIC NOT NULL,
        PRIMARY KEY (ticker, tarih)
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

    # v2.0.7.162 (Bahri'nin talebi, 19 Ağustos 2026 — "anahtar kelime
    # ön-filtresi ve kalıplara daha sonra ekleme yapılabilir hale
    # getirilebilir mi"): Beklenti Modu'nun 6 kalıbı ARTIK KODA GÖMÜLÜ
    # DEĞİL, bu üç tabloda yaşıyor. app.py ve haber_izleme.py ikisi de
    # BAŞLANGIÇTA buradan okur - kod değişikliği/deploy GEREKMEDEN yeni
    # kalıp eklenebilir, kelime eklenebilir/çıkarılabilir, etki puanı
    # değiştirilebilir. Yönetim arayüzü: Admin Paneli.
    # DİKKAT — kalip_key SİLİNİRSE kelime ve etki satırları CASCADE ile
    # otomatik silinir (aşağıdaki FOREIGN KEY ... ON DELETE CASCADE).
    c.execute("""
    CREATE TABLE IF NOT EXISTS haber_kaliplari (
        kalip_key   TEXT PRIMARY KEY,
        ad          TEXT NOT NULL,
        aciklama    TEXT,
        aktif       BOOLEAN NOT NULL DEFAULT TRUE,
        olusturma_zamani TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        istatistiksel_dayanak BOOLEAN NOT NULL DEFAULT FALSE
    )""")
    # v2.0.7.194 (Bahri'nin talebi, 25 Ağustos 2026 — "her haberin
    # optima skoruna etki etmesi söz konusu olamaz"): mevcut tabloya
    # sütunu ekle (idempotent) - canlıdaki tablo zaten var.
    try:
        c.execute("ALTER TABLE haber_kaliplari ADD COLUMN IF NOT EXISTS "
                  "istatistiksel_dayanak BOOLEAN NOT NULL DEFAULT FALSE")
    except Exception as e:
        print(f"[db] haber_kaliplari istatistiksel_dayanak migration hatasi: {e}", file=sys.stderr)
    c.execute("""
    CREATE TABLE IF NOT EXISTS haber_kalip_kelime (
        id        SERIAL PRIMARY KEY,
        kalip_key TEXT NOT NULL REFERENCES haber_kaliplari(kalip_key) ON DELETE CASCADE,
        dil       TEXT NOT NULL,
        kelime    TEXT NOT NULL
    )""")
    # kategori: MADEN / DOVIZ / BIST / KRIPTO. puan POZİTİFSE o kategorinin
    # Optima Skoru ARTAR, NEGATİFSE AZALIR - yön ayrıca saklanmaz, işaretten
    # okunur (tek doğruluk kaynağı - iki yerde tutulup birbirinden
    # sapma riski olmasın diye).
    c.execute("""
    CREATE TABLE IF NOT EXISTS haber_kalip_etki (
        id        SERIAL PRIMARY KEY,
        kalip_key TEXT NOT NULL REFERENCES haber_kaliplari(kalip_key) ON DELETE CASCADE,
        kategori  TEXT NOT NULL,
        puan      NUMERIC NOT NULL
    )""")
    _kaliplar_tohumla(conn)

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

    # v2.0.7.313 (16 Eylul 2026, Bahri'nin talebi - "portfoyumun getirisi
    # ENAG enflasyonunun altinda mi ustunde mi"): ENAG'in KENDI sitesi
    # bot erisimini ENGELLIYOR (robots.txt) ve resmi bir API'si YOK -
    # arastirilan ucuncu taraf kaynaklarda da (hesapkurdu.com, oranoranti.
    # com.tr) canli/yapisal ENAG verisi BULUNAMADI. Bahri'nin kendisi
    # BUNU bilerek onayladi: "elle veri girisi asla kabul edilemez"
    # kuralinin (v2.0.7.129, mevduat/tahvil/repo icin) TEK istisnasi -
    # ENAG ayda SADECE 1 kez guncellendigi icin (gunluk bir oran degil)
    # elle giris burada mevduat/tahvil/repo'daki gibi "guncel olmayan
    # veri" riski tasimiyor. TUIK TUFE ICIN ISE (ayni ozellik kapsaminda)
    # OTOMATIK EVDS entegrasyonu YAPILDI (bkz. app.py
    # _tufe_endeks_serisi_cek) - ENAG SADECE bunun mumkun olmadigi
    # durumda, bilerek sinirli bir istisna.
    c.execute("""
    CREATE TABLE IF NOT EXISTS enag_aylik_enflasyon (
        yil_ay            TEXT PRIMARY KEY,
        aylik_oran        DOUBLE PRECISION NOT NULL,
        guncelleme_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")

    # v2.0.7.254 (5 Eylul 2026, Bahri'nin talebi - Admin Paneli'nde
    # abonelerin uygulama kullanim istatistiklerini gormek): her SAYFA
    # DEGISIKLIGINDE (her tiklamada DEGIL - bkz. app.py'deki kayit
    # noktasi, bugunku "her renderda gereksiz baglanti" derslerinden
    # kacinmak icin bilerek SADECE sayfa GERCEKTEN degistiginde yaziyor)
    # bir satir eklenir. Sure/oturum hesaplamasi bu HAM ziyaret
    # zaman damgalarindan (admin.py'de) turetilir - ayri bir "sure"
    # sutunu YOK, cunku bir sayfada ne kadar kalindigi ancak BIR SONRAKI
    # sayfaya gecildiginde belli olur.
    c.execute("""
    CREATE TABLE IF NOT EXISTS sayfa_ziyaretleri (
        id            SERIAL    PRIMARY KEY,
        user_id       INTEGER   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        sayfa         TEXT      NOT NULL,
        giris_zamani  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sayfa_ziyaretleri_user "
              "ON sayfa_ziyaretleri(user_id, giris_zamani)")

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

    # v2.0.7.238 (1 Eylül 2026, Supabase güvenlik uyarısı e-postası -
    # Bahri'nin bulgusu): Yukarıdaki liste SADECE 22 Temmuz'daki (v2.0.7.100)
    # 8 tabloyu kapsıyordu. AMA 25 Ağustos'ta AYRICA 7 "haber izleme"
    # tablosunda (beklenti_otomatik_tespit, kullanici_tespit_karari,
    # haber_islenmis, haber_akisi, ai_cagri_butcesi, haber_kaliplari,
    # haber_kalip_kelime, haber_kalip_etki) AYNI uyarı çıkmıştı - o zaman
    # SADECE Supabase SQL editöründe ELLE düzeltilmiş, bu koda HİÇ
    # işlenmemişti (KALICI KURAL o zaman yazılmıştı ama uygulanmamıştı).
    # Ayrıca `ipo_valuations` (upcoming_ipo_client.py, v2.0.6.4) de bu
    # tabloyu bu dosyada hiç OLUŞTURMADIĞI için (dışarıda, elle
    # oluşturulmuş) HİÇBİR sweep'e hiç girmemişti - 1 Eylül 2026'daki
    # Supabase uyarısının en olası kaynağı bu tablo. Yukarıdaki listeye
    # eklenerek artık HER uygulama başlangıcında (init_db her çalıştığında)
    # bu tablolarda da RLS'in açık kaldığı garanti ediliyor - bir daha
    # "manuel düzelttim ama koda işlemeyi unuttum" riski kalmıyor.
    for _rls_tablo in ("beklenti_otomatik_tespit", "kullanici_tespit_karari",
                       "haber_islenmis", "haber_akisi", "ai_cagri_butcesi",
                       "haber_kaliplari", "haber_kalip_kelime", "haber_kalip_etki",
                       "ipo_valuations", "sayfa_ziyaretleri"):
        try:
            c.execute(f"ALTER TABLE {_rls_tablo} ENABLE ROW LEVEL SECURITY")
        except Exception as _e:
            print(f"[db] RLS etkinlestirme atlandi ({_rls_tablo}): {_e}")

    # v2.0.7.333 (22 Eylul 2026, Supabase güvenlik uyarısı e-postası -
    # Bahri'nin bulgusu): "KALICI KURAL: kullanici finansal verisi tasiyan
    # HER YENI tablo icin RLS listesine eklenmeli" kurali BIR KEZ DAHA
    # ihlal edilmisti - bu dosyadaki TUM CREATE TABLE'lar (19 tablo) ile
    # yukaridaki iki liste (17 tablo) karsilastirildi, TAM OLARAK 2 tablo
    # HICBIR listede yoktu: `enag_aylik_enflasyon` (ENAG Enflasyon Izleme,
    # v2.0.7.2xx civari eklendi) ve `kap_bildirim_takip` (KAP Bildirim
    # Izleme, v2.0.6.x civari eklendi) - ikisi de olusturulduklari gunden
    # beri bu sweep'in DISINDA kalmis, PostgREST uzerinden herkese acik
    # kalmis olabilir. digger dosyalardaki (firsat_radari.py,
    # emailer_standalone.py, worker.py) tablolarin HEPSI kendi RLS
    # satirlarini zaten iceriyordu, TEK sorun bu dosyanin kendi ic
    # tutarliligindaydi.
    for _rls_tablo in ("enag_aylik_enflasyon", "kap_bildirim_takip"):
        try:
            c.execute(f"ALTER TABLE {_rls_tablo} ENABLE ROW LEVEL SECURITY")
        except Exception as _e:
            print(f"[db] RLS etkinlestirme atlandi ({_rls_tablo}): {_e}")

    # v2.0.7.342: yeni tablolar olusturulurken AYNI ANDA RLS'e eklendi -
    # v2.0.7.333'teki guvenlik acigi (yeni tablo olusturulup bu listeye
    # eklenmeyi UNUTMA) burada TEKRARLANMAMASI icin.
    for _rls_tablo in ("piyasa_tedbir_tespit", "piyasa_tedbir_listesi",
                       "spk_bulten_islenmis", "tefas_fiyat_gecmisi",
                       "kap_risk_uyari", "kap_risk_bildirim"):
        try:
            c.execute(f"ALTER TABLE {_rls_tablo} ENABLE ROW LEVEL SECURITY")
        except Exception as _e:
            print(f"[db] RLS etkinlestirme atlandi ({_rls_tablo}): {_e}")

    # v2.0.7.342/350: Supabase'in 30 Ekim 2026'dan itibaren YENI tablolara
    # artik otomatik Data API (PostgREST) izni vermeyecegi bildirilmisti
    # (public.trendsurf-optima / Menu Muhendisi ile AYNI Supabase hesabi) -
    # bu YENI tablolara ACIKCA grant veriliyor, ileride PostgREST
    # uzerinden "erisilemiyor" sorunu yasanmasin diye.
    for _grant_tablo in ("piyasa_tedbir_tespit", "piyasa_tedbir_listesi",
                         "spk_bulten_islenmis", "tefas_fiyat_gecmisi",
                         "kap_risk_uyari", "kap_risk_bildirim"):
        try:
            c.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON public.{_grant_tablo} "
                      f"TO anon, authenticated, service_role")
        except Exception as _e:
            print(f"[db] grant atlandi ({_grant_tablo}): {_e}")

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
        conn = get_conn()
        rows = conn.execute(
            "SELECT ticker, kategori, skor, fiyat, rsi, ret1m FROM intraday_scores "
            f"WHERE updated_at > now() - interval '{int(freshness_minutes)} minutes'"
        ).fetchall()
        conn.close()
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
    her calismada once bu kontrol edilir.

    v2.0.7.324 (17 Eylul 2026, Bahri'nin paylastigi zaman damgali logun
    ANALIZI sirasinda bulundu - KESIN KOK NEDEN): Bu fonksiyon `get_conn()`
    ile aldigi baglantiyi HICBIR ZAMAN `.close()` ETMIYORDU (sonucu direkt
    zincirleme cagriyla donduruyordu, baglanti nesnesi hic degiskene
    atanmiyordu). Toplu modda `close()` cagrilmayinca v2.0.7.320'nin
    oraya ekledigi commit() de HIC CALISMIYORDU - yani bu fonksiyonun
    actigi SELECT islemi PAYLASILAN baglanti uzerinde surekli ACIK/
    COMMIT EDILMEMIS kaliyordu. Bu fonksiyon TARANAN HER TEK HABER icin
    ayri ayri cagriliyor (bir turda ~300 kez) - dongu adimlari arasinda
    gecen sure (~1-1,2 sn, ZAMAN DAMGALI logda dogrulandi) Supabase'in
    "idle in transaction" zaman asimini asiyor, bir sonraki cagrida
    ProgrammingError ile baglanti yeniden aciliyordu - PRATIKTE HER
    CAGRIDA. Duzeltme: baglanti artik degiskene atanip acikca
    kapatiliyor (toplu modda bu artik commit() cagirir, gercek TCP
    baglanti KAPANMAZ - bkz. _CompatConn.close())."""
    try:
        conn = get_conn()
        row = conn.execute(
            "SELECT 1 FROM haber_islenmis WHERE haber_url=?", (url,)
        ).fetchone()
        conn.close()
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


def get_cevrilmemis_haberler(kaynaklar: list, limit: int = 40) -> list:
    """v2.0.7.161: Ceviri artik SADECE o turda gelen haberlerle sinirli degil -
    veritabanindaki HENUZ CEVRILMEMIS Ingilizce basliklari doner.

    Sebep: v2.0.7.160'ta ceviri bellekteki kuyruktan besleniyordu. O turda
    Gemini cagrisi herhangi bir sebeple basarisiz olursa (kota, ag, API
    hatasi) o haberler SONSUZA KADAR Ingilizce kaliyordu - bir daha hic
    denenmiyordu. Bu fonksiyonla sistem kendini onariyor: sorun cozulunce
    birikmis basliklar sonraki turlarda otomatik cevriliyor.

    v2.0.7.179 (Bahri'nin talebi - "başlığı çevirebiliyorsak özeti de
    çevirebiliriz"): artik `ozet` de donuyor - ceviri fonksiyonlari HEM
    basligi HEM ozeti birlikte cevirebilsin diye."""
    if not kaynaklar:
        return []
    try:
        isaretler = ",".join(["?"] * len(kaynaklar))
        conn = get_conn()
        rows = conn.execute(
            "SELECT haber_url, baslik, ozet FROM haber_akisi "
            "WHERE baslik_tr IS NULL "
            f"AND kaynak IN ({isaretler}) "
            "ORDER BY eklenme_zamani DESC LIMIT ?",
            (*kaynaklar, int(limit))).fetchall()
        conn.close()
    except Exception as e:
        print(f"[db] get_cevrilmemis_haberler hata: {e}", file=sys.stderr)
        return []
    def _cv(r, k, i):
        return r[k] if isinstance(r, dict) else r[i]
    return [(_cv(r, "haber_url", 0), _cv(r, "baslik", 1), _cv(r, "ozet", 2) or "")
            for r in rows]


# ══════════════════════════════════════════════════════════════
# v2.0.7.162: TOHUM VERİSİ - haber_kaliplari tablosu BOŞSA (ilk kurulum)
# önceden koda gömülü olan 6 kalıp BİREBİR AYNI değerlerle buraya
# aktarılır. DEĞERLER app.py/haber_izleme.py'nin eski hardcoded
# hallerinden PROGRAMATİK OLARAK çekildi (elle yeniden yazılmadı) -
# transkripsiyon hatası riski yok.
# ══════════════════════════════════════════════════════════════
_SEED_TABLOSU = {'jeopolitik': {'MADEN': 8, 'DOVIZ': 6, 'BIST': -6}, 'petrol': {'MADEN': 3, 'DOVIZ': 5, 'BIST': -3}, 'fed': {'MADEN': -5, 'DOVIZ': 6, 'BIST': -5}, 'kredi_notu': {'DOVIZ': 5, 'BIST': -7}, 'kripto_olay': {'KRIPTO': -8}, 'tcmb_kredibilite': {'DOVIZ': 10, 'MADEN': 4, 'BIST': -3}}
_SEED_ISIM = {'jeopolitik': 'Jeopolitik gerilim/çatışma', 'petrol': 'Petrol arz şoku (Ortadoğu/OPEC)', 'fed': 'Merkez bankası (Fed/ECB/TCMB) şahin sürprizi', 'kredi_notu': "Kredi notu düşürülmesi (S&P/Moody's/Fitch)", 'kripto_olay': 'Kripto düzenleme/halving şoku', 'tcmb_kredibilite': 'TCMB para politikası kredibilite kaybı (beklenmedik gevşeme)'}
_SEED_ACIKLAMA = {'jeopolitik': "İstatistiksel dayanak: Jeopolitik Risk Endeksi (Caldara-Iacoviello, 1900'den günümüze, yüzlerce olay) literatüründe, yükselen jeopolitik risk dönemlerinde altının istatistiksel olarak anlamlı güvenli liman talebi gördüğü, gelişen piyasa para birimlerinin (TL dahil) baskı altında kaldığı ve borsaların kısa vadeli satış baskısı yaşadığı tutarlı şekilde gözlemlenmiştir.", 'petrol': 'İstatistiksel dayanak: petrol arzını kesintiye uğratan olaylarda (saldırı, ambargo, üretim kesintisi), petrol fiyatlarının kısa vadede çift haneli yüzdelerle sıçradığı tarihte tekrar tekrar gözlemlenmiştir. Türkiye net petrol ithalatçısı olduğu için bu şoklar enflasyon baskısı yaratma ve TL üzerinde değer kaybı baskısı oluşturma eğilimindedir.', 'fed': 'İstatistiksel dayanak: merkez bankalarının piyasa beklentisinin ötesinde sıkılaştırıcı (şahin) kararları/sinyalleri, akademik olay çalışması (event study) literatüründe dolar güçlenmesi, gelişen piyasa para birimlerinde (TL dahil) istatistiksel olarak anlamlı değer kaybı ve risk iştahının azalmasıyla ilişkilendirilmiştir.', 'kredi_notu': 'İstatistiksel dayanak: 1990-2016 dönemini kapsayan, çok sayıda gelişen piyasayı içeren günlük veriye dayalı akademik panel çalışması, egemen kredi notu düşürülmelerinin hem borsa getirilerini hem ülke para biriminin dolar değerini istatistiksel olarak anlamlı şekilde olumsuz etkilediğini, bu etkinin özellikle S&P ve Fitch düşürmelerinde belirgin olduğunu ve düşürmelerin etkisinin not artırımlarına kıyasla daha güçlü (asimetrik) olduğunu göstermektedir.', 'kripto_olay': "İstatistiksel dayanak: çok sayıda kripto parada (2014-2023, halving yaşayan tüm kripto varlıklar) yapılan akademik olay çalışması, olay penceresinde ORTALAMA anormal getirinin istatistiksel olarak anlamlı şekilde NEGATİF (~-%7,6) olduğunu bulmuştur - popüler 'halving = yükseliş' anlatısının aksine, bu KISA VADELİ tepkidir. Uzun vadeli (6-12 ay sonrası) 'boğa piyasası' anlatısı ayrı bir konudur ve çok daha küçük örneklem boyutuna (Bitcoin için sadece 4 halving döngüsü) dayandığından güvenilirliği literatürde açıkça tartışmalıdır - bu yüzden burada sadece kısa vadeli, istatistiksel olarak daha sağlam bulgu kullanılmıştır.", 'tcmb_kredibilite': "İstatistiksel dayanak: TCMB'nin piyasa beklentisinin tersine hareket ettiği (ör. enflasyon yükselirken faiz indirmesi gibi) dönemlerde, Türkiye kendi para politikası kredibilitesini kaybetme riskiyle karşı karşıya kalır - bu, global faiz/risk ortamından BAĞIMSIZ, yerli bir mekanizmadır. Belgelenmiş örnek:  2021 Eylül-Kasım döneminde TCMB, enflasyon %20'ye yaklaşırken piyasa beklentisinin aksine toplam 400 baz puan faiz indirdi; TL o yıl doları karşısında %44 değer kaybederek gelişen piyasalar arasında en kötü performans gösteren para birimi oldu (Arjantin pesosu %18,1, Şili pesosu %16,5 kayıpla onu takip etti - TL'nin kaybı ikinciden yaklaşık 2,5 kat fazlaydı)."}
_SEED_KELIMELER = {'jeopolitik': {'tr': ['savaş', 'çatışma', 'saldırı', 'gerilim', 'işgal', 'füze', 'ordu', 'askeri operasyon', 'ateşkes', 'bombalama'], 'en': ['war', 'conflict', 'attack', 'invasion', 'missile', 'military', 'ceasefire', 'airstrike', 'troops', 'strike on']}, 'petrol': {'tr': ['petrol', 'opec', 'hürmüz', 'ambargo', 'üretim kesintisi', 'boru hattı', 'rafineri', 'tanker'], 'en': ['oil', 'strait of hormuz', 'pipeline', 'refinery', 'crude']}, 'fed': {'tr': ['faiz kararı', 'avrupa merkez bankası'], 'en': ['fed', 'fomc', 'ecb', 'federal reserve', 'interest rate decision', 'rate hike', 'rate cut', 'powell', 'lagarde']}, 'kredi_notu': {'tr': ['kredi notu', 'not indirimi'], 'en': ["moody's", 's&p', 'fitch', 'credit rating', 'sovereign rating', 'downgrade']}, 'kripto_olay': {'tr': ['kripto düzenleme', 'borsa çöktü'], 'en': ['halving', 'bitcoin hack', 'crypto regulation', 'exchange collapse', 'sec lawsuit']}, 'tcmb_kredibilite': {'tr': ['tcmb', 'ppk', 'para politikası kurulu', 'faiz indirimi', 'merkez bankası bağımsızlığı'], 'en': []}}


def _kaliplar_tohumla(conn):
    """init_db() cagirir - haber_kaliplari BOSSA tohum veriyi yazar.
    Zaten doluysa HICBIR SEY yapmaz (Bahri'nin admin panelinden yaptigi
    duzenlemelerin uzerine YAZILMAZ)."""
    try:
        mevcut = conn.execute("SELECT COUNT(*) AS n FROM haber_kaliplari").fetchone()
        if mevcut and int(mevcut["n"] if isinstance(mevcut, dict) else mevcut[0]) > 0:
            return  # zaten tohumlanmis (veya admin tarafindan duzenlenmis)
        for kalip_key, ad in _SEED_ISIM.items():
            conn.execute(
                "INSERT INTO haber_kaliplari (kalip_key, ad, aciklama, aktif) "
                "VALUES (?,?,?,TRUE) ON CONFLICT (kalip_key) DO NOTHING",
                (kalip_key, ad, _SEED_ACIKLAMA.get(kalip_key, "")))
            for dil, kelimeler in _SEED_KELIMELER.get(kalip_key, {}).items():
                for kelime in kelimeler:
                    conn.execute(
                        "INSERT INTO haber_kalip_kelime (kalip_key, dil, kelime) "
                        "VALUES (?,?,?)", (kalip_key, dil, kelime))
            for kategori, puan in _SEED_TABLOSU.get(kalip_key, {}).items():
                conn.execute(
                    "INSERT INTO haber_kalip_etki (kalip_key, kategori, puan) "
                    "VALUES (?,?,?)", (kalip_key, kategori, puan))
        conn.commit()
        print("[db] haber_kaliplari tohumlandi (6 varsayilan kalip).", file=sys.stderr)
    except Exception as e:
        print(f"[db] _kaliplar_tohumla hata: {e}", file=sys.stderr)
        try:
            conn.rollback()
        except Exception:
            pass



def _piyasa_tedbir_tohumla(conn):
    """init_db() cagirir - piyasa_tedbir_listesi BOSSA, bu sohbette
    (2-20 Eylul 2026 arasi, v2.0.7.322/331) ELLE arastirilip dogrulanmis
    SPK fon krizi kararlarini tohumlar - bunlar zaten bir kez Bahri'ye
    sunulup onaylanmis OLGULARDI (spk_tedbir_fonlari.py statik dosyasinda
    yasiyordu), bu yuzden tekrar Admin Panel onayindan GECMEDEN dogrudan
    AKTIF olarak eklenir. Zaten doluysa HICBIR SEY yapmaz."""
    try:
        mevcut = conn.execute("SELECT COUNT(*) AS n FROM piyasa_tedbir_listesi").fetchone()
        if mevcut and int(mevcut["n"] if isinstance(mevcut, dict) else mevcut[0]) > 0:
            return
        # v2.0.7.322 (17 Eylul 2026, SPK 2026/60 sayili Bulten): Tera/
        # Pusula/Hedef/Atlas/A1 Capital/Pardus/Bulls Portfoy'un TUM
        # TEFAS fonlari alim-satima kapatildi.
        _sirketler = [
            "TERA PORTFÖY", "PUSULA PORTFÖY", "HEDEF PORTFÖY", "ATLAS PORTFÖY",
            "A1 CAPİTAL PORTFÖY", "A1 PORTFÖY", "PARDUS PORTFÖY", "BULLS PORTFÖY",
        ]
        for sirket in _sirketler:
            conn.execute(
                "INSERT INTO piyasa_tedbir_listesi "
                "(eslesme_turu, deger, kategori, tedbir_turu, kaynak_aciklama) "
                "VALUES ('SIRKET_ADI', ?, 'TEFAS', 'ISLEM_DURDURMA_TASFIYE', "
                "'SPK 17.09.2026 - 2026/60 sayili Bulten') "
                "ON CONFLICT (eslesme_turu, deger) DO NOTHING", (sirket,))
        # v2.0.7.331 (16 Eylul 2026, SPK 2026/59 sayili Bulten): piyasa
        # dolandiriciligi tespit edilen 3 hisse.
        for ticker in ("KTLEV", "GUNDG", "DSTKF"):
            conn.execute(
                "INSERT INTO piyasa_tedbir_listesi "
                "(eslesme_turu, deger, kategori, tedbir_turu, kaynak_aciklama) "
                "VALUES ('TICKER', ?, 'BIST', 'MANIPULASYON_SUPHESI', "
                "'SPK 16.09.2026 - 2026/59 sayili Bulten') "
                "ON CONFLICT (eslesme_turu, deger) DO NOTHING", (ticker,))
        conn.commit()
        print("[db] piyasa_tedbir_listesi tohumlandi (7 sirket + 3 hisse, "
              "spk_tedbir_fonlari.py'den tasindi).", file=sys.stderr)
    except Exception as e:
        print(f"[db] _piyasa_tedbir_tohumla hata: {e}", file=sys.stderr)
        try:
            conn.rollback()
        except Exception:
            pass


def _piyasa_tedbir_ek_kurallar(conn):
    """v2.0.7.351 (3 Ekim 2026, Bahri'nin bulgusu - ILU'yu ING Bank'ta
    almaya calistiginde "minimum 1 milyon TL" sarti bildirilmisti, bunu
    daha once iletmesine ragmen fon hala sistemde oneriliyordu): bu,
    `_piyasa_tedbir_tohumla()`'nin AKSINE - tablo BOS OLMASA BILE HER
    init_db() cagrisinda calisir (ON CONFLICT DO NOTHING ile idempotent) -
    boylece BURAYA eklenecek YENI, tek tek dogrulanmis kisitlamalar bir
    sonraki deploy'da otomatik aktif olur, tabloyu bosaltip yeniden
    tohumlamaya gerek kalmaz. Bu, SPK/resmi bir karar DEGIL - ING Bank'in
    KENDI aracilik/dagitim kisitlamasi (TEFAS'in genel verisinde yer
    almaz, sadece Bahri'nin bildirdigi icin biliniyor)."""
    try:
        conn.execute(
            "INSERT INTO piyasa_tedbir_listesi "
            "(eslesme_turu, deger, kategori, tedbir_turu, kaynak_aciklama) "
            "VALUES ('TICKER', 'ILU', 'TEFAS', 'YUKSEK_MINIMUM_TUTAR', "
            "'Bahri''nin bildirdigi - ING Bank minimum 1.000.000 TL yatirim sarti kosuyor') "
            "ON CONFLICT (eslesme_turu, deger) DO NOTHING")
        conn.commit()
    except Exception as e:
        print(f"[db] _piyasa_tedbir_ek_kurallar hata: {e}", file=sys.stderr)
        try:
            conn.rollback()
        except Exception:
            pass


def haber_akisi_ekle(haber_url: str, kaynak: str, baslik: str,
                     baslik_tr: str = None, eslesen_kalip: str = None,
                     yayin_zamani=None, ozet: str = None):
    """v2.0.7.160: Taranan HER haberi akisa yazar - eslesen_kalip None ise
    'tarandi, sakin' demektir. Ayni URL tekrar gelirse hicbir sey yapmaz.
    v2.0.7.179: `ozet` (RSS'in kendi kisa ozeti) da saklanir - Haberler
    sayfasinda baslik ile birlikte gosterilecek."""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO haber_akisi (haber_url, kaynak, baslik, baslik_tr, "
            "eslesen_kalip, yayin_zamani, ozet) VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT (haber_url) DO NOTHING",
            (haber_url, kaynak, baslik, baslik_tr, eslesen_kalip, yayin_zamani, ozet))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] haber_akisi_ekle hata: {e}", file=sys.stderr)


def haber_akisi_ceviri_yaz(haber_url: str, baslik_tr: str = None, ozet_tr: str = None):
    """v2.0.7.160: Toplu ceviri sonrasi Turkce basligi geriye yazar.
    v2.0.7.179: artik ozet_tr da yazabiliyor - biri None ise o alan
    DOKUNULMADAN kalir (COALESCE ile), boylece sadece baslik cevrilip
    ozet cevrilemediyse (ya da tam tersi) diger alan bozulmaz."""
    try:
        conn = get_conn()
        conn.execute(
            "UPDATE haber_akisi SET "
            "baslik_tr = COALESCE(?, baslik_tr), "
            "ozet_tr = COALESCE(?, ozet_tr) "
            "WHERE haber_url=?",
            (baslik_tr, ozet_tr, haber_url))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] haber_akisi_ceviri_yaz hata: {e}", file=sys.stderr)


def get_haber_akisi(saat: int = 48, limit: int = 300) -> list:
    """v2.0.7.160: Haberler sayfasi icin - EN YENI EN USTTE. eslesen_kalip
    dolu olanlar sayfada ayrica ustte gosterilir, bu fonksiyon ikisini de
    ayni listede tek sorguda doner.
    v2.0.7.179: ozet/ozet_tr de donuyor - Haberler sayfasi artik basligin
    altinda kisa (cevrilmis) ozeti de gosterebiliyor."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT haber_url, kaynak, baslik, baslik_tr, eslesen_kalip, "
            "COALESCE(yayin_zamani, eklenme_zamani) AS zaman, ozet, ozet_tr "
            "FROM haber_akisi "
            f"WHERE COALESCE(yayin_zamani, eklenme_zamani) > now() - interval '{int(saat)} hours' "
            "ORDER BY zaman DESC LIMIT ?", (int(limit),)
        ).fetchall()
        conn.close()
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
            "ozet": _hv("ozet", 6), "ozet_tr": _hv("ozet_tr", 7),
        })
    return sonuc


def kap_bildirim_ekle(ticker: str, kap_baslik: str, gonderen: str,
                       gonderim_tarihi, icerik_ozet: str, onemli_mi: bool = True) -> bool:
    """kap_bildirim_izleme.py her yeni bildirim icin bunu cagirir. UNIQUE
    kisitlamasi (ticker, gonderim_tarihi, kap_baslik) sayesinde ayni
    bildirim tekrar tekrar eklenmez - ON CONFLICT DO NOTHING ile
    sessizce atlanir, hata FIRLATMAZ."""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO kap_bildirim_takip "
            "(ticker, kap_baslik, gonderen, gonderim_tarihi, icerik_ozet, onemli_mi) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT (ticker, gonderim_tarihi, kap_baslik) DO NOTHING",
            (ticker.upper(), kap_baslik, gonderen, gonderim_tarihi, icerik_ozet, bool(onemli_mi)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] kap_bildirim_ekle hata: {e}", file=sys.stderr)
        return False


def get_tum_portfoy_tickerlari() -> list:
    """kap_bildirim_izleme.py bunu cagirir - TUM kullanicilarin
    portfoyundeki BENZERSIZ ticker'lari doner (hangi kullanicida
    oldugu onemli degil, checker HERKESIN elindeki her seyi kontrol
    eder - goruntuleme asamasinda kullaniciya gore filtrelenir, bkz.
    get_yeni_kap_bildirimleri). KAP sadece BIST/TEFAS uyeleri icin
    anlamli oldugundan asset_type bu ikisiyle sinirlandirildi."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM portfolio "
            "WHERE UPPER(asset_type) IN ('BIST','TEFAS')"
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[db] get_tum_portfoy_tickerlari hata: {e}", file=sys.stderr)
        return []
    return [(r["ticker"] if isinstance(r, dict) else r[0]) for r in rows]


def get_yeni_kap_bildirimleri(kullanici_id, saat: int = 72) -> list:
    """app.py bunu cagirir - SADECE bu kullanicinin PORTFOYUNDE OLAN
    ticker'lar icin, son `saat` icinde tespit edilmis bildirimleri
    doner. Onay/red YOK (bkz. tablo yorumu) - bu salt-okunur bir
    bilgilendirme listesidir."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT k.ticker, k.kap_baslik, k.gonderen, k.gonderim_tarihi, "
            "k.icerik_ozet, k.onemli_mi "
            "FROM kap_bildirim_takip k "
            "WHERE k.tespit_tarihi > now() - interval '%s hours' "
            "AND k.ticker IN (SELECT DISTINCT ticker FROM portfolio WHERE user_id = ?) "
            "ORDER BY k.gonderim_tarihi DESC" % int(saat),
            (kullanici_id,)
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[db] get_yeni_kap_bildirimleri hata: {e}", file=sys.stderr)
        return []
    sonuc = []
    for r in rows:
        def _kv(k, i):
            return r[k] if isinstance(r, dict) else r[i]
        sonuc.append({
            "ticker": _kv("ticker", 0), "kap_baslik": _kv("kap_baslik", 1),
            "gonderen": _kv("gonderen", 2), "gonderim_tarihi": _kv("gonderim_tarihi", 3),
            "icerik_ozet": _kv("icerik_ozet", 4), "onemli_mi": _kv("onemli_mi", 5),
        })
    return sonuc


def kap_bildirim_temizle(gun: int = 14):
    """14 gunden eski KAP bildirim kayitlarini siler - tablo sinirsiz
    buyumesin (haber_akisi_temizle ile ayni mantik)."""
    try:
        conn = get_conn()
        conn.execute(
            "DELETE FROM kap_bildirim_takip WHERE tespit_tarihi < now() - interval '%s days'"
            % int(gun))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] kap_bildirim_temizle hata: {e}", file=sys.stderr)


def kap_risk_hepsini_yaz(riskler_tickera: dict) -> bool:
    """kap_risk_tarama.py: TUM guncel risk listesini TEK islemde YAZAR (eski satirlarin hepsini
    degistirir; kalkan/suresi dolan uyari silinir). riskler_tickera: kap_risk.riskleri_hesapla() ciktisi.
    Hata olursa hicbir sey degismez (rollback)."""
    try:
        conn = get_conn()
        conn.execute("DELETE FROM kap_risk_uyari")
        for ticker, riskler in (riskler_tickera or {}).items():
            for r in riskler:
                conn.execute(
                    "INSERT INTO kap_risk_uyari "
                    "(ticker, kural, seviye, ad, baslik, gonderim_tarihi, bitis_tarihi, ozet) "
                    "VALUES (?,?,?,?,?,?,?,?) ON CONFLICT (ticker, kural) DO NOTHING",
                    (ticker.upper(), r["kural"], r["seviye"], r.get("ad"), r.get("baslik"),
                     r.get("tarih"), r["bitis"], r.get("ozet")))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] kap_risk_hepsini_yaz hata: {e}", file=sys.stderr)
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return False


def kap_risk_bildirim_idleri(gun: int = 140) -> set:
    """Arsivde zaten olan KAP bildirim numaralari (tekrar indirmemek icin)."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT disclosure_index FROM kap_risk_bildirim "
            "WHERE yayin_tarihi > now() - interval '%s days'" % int(gun)).fetchall()
        conn.close()
    except Exception as e:
        print(f"[db] kap_risk_bildirim_idleri hata: {e}", file=sys.stderr)
        return set()
    return {int(r["disclosure_index"] if isinstance(r, dict) else r[0]) for r in rows}


def kap_risk_bildirim_ekle(b: dict) -> bool:
    """Bir bildirimi arsive ekler (ayni numara zaten varsa sessizce atlanir)."""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO kap_risk_bildirim (disclosure_index, yayin_tarihi, gonderen, konu, ozet, "
            "gonderen_kodlar, ilgili_kodlar, metin) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT (disclosure_index) DO NOTHING",
            (int(b["id"]), b["tarih"], b.get("gonderen"), b["konu"], b.get("ozet"),
             ",".join(b.get("gonderen_kodlar") or []), ",".join(b.get("ilgili_kodlar") or []),
             b.get("metin") or ""))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] kap_risk_bildirim_ekle hata ({b.get('id')}): {e}", file=sys.stderr)
        return False


def kap_risk_bildirimleri_oku(gun: int = 140) -> list:
    """Arsivdeki bildirimler (kap_risk.riskleri_hesapla girdisi)."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT disclosure_index, yayin_tarihi, gonderen, konu, ozet, gonderen_kodlar, ilgili_kodlar, metin "
            "FROM kap_risk_bildirim WHERE yayin_tarihi > now() - interval '%s days' "
            "ORDER BY yayin_tarihi DESC" % int(gun)).fetchall()
        conn.close()
    except Exception as e:
        print(f"[db] kap_risk_bildirimleri_oku hata: {e}", file=sys.stderr)
        return []
    out = []
    for r in rows:
        def _v(k, i):
            return r[k] if isinstance(r, dict) else r[i]
        out.append({"id": int(_v("disclosure_index", 0)), "tarih": _v("yayin_tarihi", 1),
                    "gonderen": _v("gonderen", 2), "konu": _v("konu", 3), "ozet": _v("ozet", 4),
                    "gonderen_kodlar": [k for k in (_v("gonderen_kodlar", 5) or "").split(",") if k],
                    "ilgili_kodlar": [k for k in (_v("ilgili_kodlar", 6) or "").split(",") if k],
                    "metin": _v("metin", 7) or ""})
    return out


def kap_risk_bildirim_temizle(gun: int = 140):
    """Gecerlilik penceresinden (en uzunu 120 gun) eski arsiv kayitlarini siler."""
    try:
        conn = get_conn()
        conn.execute("DELETE FROM kap_risk_bildirim WHERE yayin_tarihi < now() - interval '%s days'" % int(gun))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] kap_risk_bildirim_temizle hata: {e}", file=sys.stderr)


def get_aktif_kap_riskleri() -> dict:
    """app.py load_universe(): {TICKER: [ {kural, seviye, ad, baslik, tarih, bitis, ozet}, ... ]}
    SADECE suresi dolmamis olanlar. Hata/tablo yoksa {} (uygulama calismaya devam eder)."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT ticker, kural, seviye, ad, baslik, gonderim_tarihi, bitis_tarihi, ozet "
            "FROM kap_risk_uyari WHERE bitis_tarihi >= CURRENT_DATE "
            "ORDER BY ticker, gonderim_tarihi DESC").fetchall()
        conn.close()
    except Exception as e:
        print(f"[db] get_aktif_kap_riskleri hata: {e}", file=sys.stderr)
        return {}
    sonuc = {}
    for r in rows:
        def _v(k, i):
            return r[k] if isinstance(r, dict) else r[i]
        sonuc.setdefault(str(_v("ticker", 0)).upper(), []).append({
            "kural": _v("kural", 1), "seviye": _v("seviye", 2), "ad": _v("ad", 3),
            "baslik": _v("baslik", 4), "tarih": _v("gonderim_tarihi", 5),
            "bitis": _v("bitis_tarihi", 6), "ozet": _v("ozet", 7)})
    # siddet sirasi (AGIR > ORTA > BILGI), icinde yeni -> eski
    _s = {"AGIR": 0, "ORTA": 1, "BILGI": 2}
    for lst in sonuc.values():
        lst.sort(key=lambda x: _s.get(x["seviye"], 9))
    return sonuc


def spk_bulten_islendi_mi(bulten_no: str) -> bool:
    """spk_bulten_izleme.py'nin AYNI bulteni tekrar indirip AI'ye tekrar
    sormamasi icin - haber_islendi_mi ile AYNI desen."""
    try:
        conn = get_conn()
        row = conn.execute(
            "SELECT 1 FROM spk_bulten_islenmis WHERE bulten_no=?", (bulten_no,)
        ).fetchone()
        conn.close()
        return row is not None
    except Exception:
        return False


def spk_bulten_islendi_isaretle(bulten_no: str):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO spk_bulten_islenmis (bulten_no) VALUES (?) "
            "ON CONFLICT (bulten_no) DO NOTHING", (bulten_no,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] spk_bulten_islendi_isaretle hata: {e}", file=sys.stderr)


def spk_islenmis_bultenler() -> set:
    """v2.0.7.367: islenmis TUM bulten numaralari TEK sorguda (spk_bulten_islendi_mi bulten basina
    ayri baglanti aciyordu: 30 bulten ~35 sn). Hata olursa BOS kume - bu durumda tarayici
    bultenleri yeniden analiz eder ama tespit tekrarlari bekleyen/reddedilen kontroluyle engellenir."""
    try:
        conn = get_conn()
        rows = conn.execute("SELECT bulten_no FROM spk_bulten_islenmis").fetchall()
        conn.close()
        return {r[0] for r in rows}
    except Exception as e:
        print(f"[db] spk_islenmis_bultenler hata: {e}", file=sys.stderr)
        return set()


def spk_bulten_toplu_isaretle(bulten_nolari) -> int:
    """v2.0.7.367: bir baglantida cok bulteni 'islendi' isaretle (idempotent)."""
    nolar = [str(n) for n in (bulten_nolari or [])]
    if not nolar:
        return 0
    try:
        conn = get_conn()
        for n in nolar:
            conn.execute("INSERT INTO spk_bulten_islenmis (bulten_no) VALUES (?) "
                         "ON CONFLICT (bulten_no) DO NOTHING", (n,))
        conn.commit()
        conn.close()
        return len(nolar)
    except Exception as e:
        print(f"[db] spk_bulten_toplu_isaretle hata: {e}", file=sys.stderr)
        return 0


def piyasa_tedbir_tespit_ekle(kaynak_turu: str, kaynak_referans: str, kaynak_url: str,
                              kaynak_tarihi, eslesme_turu: str, deger: str,
                              kategori: str, tedbir_turu: str,
                              ai_gerekce: str, ai_ozet: str, ek_veri: str = None) -> bool:
    """v2.0.7.342: spk_bulten_izleme.py (ve gelecekte Resmi Gazete/KAP
    taramaları) AI tespiti basarili olunca bunu cagirir - 'bekliyor'
    durumunda eklenir, HENUZ piyasa_tedbir_listesi'ne YANSIMAZ, Admin
    Panel'de onay bekler."""
    try:
        conn = get_conn()
        if ek_veri is not None:
            # Tarayici (GitHub Actions) uygulamadan ONCE calisabilir; kolon henuz yoksa olustur (idempotent).
            conn.execute("ALTER TABLE piyasa_tedbir_tespit ADD COLUMN IF NOT EXISTS ek_veri TEXT")
            conn.execute(
                "INSERT INTO piyasa_tedbir_tespit "
                "(kaynak_turu, kaynak_referans, kaynak_url, kaynak_tarihi, "
                "eslesme_turu, deger, kategori, tedbir_turu, ai_gerekce, ai_ozet, ek_veri) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (kaynak_turu, kaynak_referans, kaynak_url, kaynak_tarihi,
                 eslesme_turu, deger, kategori, tedbir_turu, ai_gerekce, ai_ozet, ek_veri))
        else:
            conn.execute(
                "INSERT INTO piyasa_tedbir_tespit "
                "(kaynak_turu, kaynak_referans, kaynak_url, kaynak_tarihi, "
                "eslesme_turu, deger, kategori, tedbir_turu, ai_gerekce, ai_ozet) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (kaynak_turu, kaynak_referans, kaynak_url, kaynak_tarihi,
                 eslesme_turu, deger, kategori, tedbir_turu, ai_gerekce, ai_ozet))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] piyasa_tedbir_tespit_ekle hata: {e}", file=sys.stderr)
        return False


def get_bekleyen_piyasa_tedbirleri() -> list:
    """Admin Panel'in onay kuyrugunda gosterecegi, henuz karar verilmemis
    tespitler. Tek, PAYLASIMLI liste (kullaniciya ozel DEGIL - bkz.
    piyasa_tedbir_tespit tablosunun yorumu: bu objektif bir SPK/Resmi
    Gazete olgusu, kisiye gore degisen bir yorum degil)."""
    try:
        conn = get_conn()
        try:
            rows = conn.execute(
                "SELECT id, kaynak_turu, kaynak_referans, kaynak_url, kaynak_tarihi, "
                "tespit_zamani, eslesme_turu, deger, kategori, tedbir_turu, "
                "ai_gerekce, ai_ozet, ek_veri "
                "FROM piyasa_tedbir_tespit WHERE onay_durumu='bekliyor' "
                "ORDER BY tespit_zamani DESC"
            ).fetchall()
        except Exception:
            # v2.0.7.370: ek_veri kolonu henuz yoksa (init_db calismadan) eski sorgu - kuyruk bos gorunmesin
            try:
                conn.rollback()
            except Exception:
                pass
            rows = conn.execute(
                "SELECT id, kaynak_turu, kaynak_referans, kaynak_url, kaynak_tarihi, "
                "tespit_zamani, eslesme_turu, deger, kategori, tedbir_turu, "
                "ai_gerekce, ai_ozet "
                "FROM piyasa_tedbir_tespit WHERE onay_durumu='bekliyor' "
                "ORDER BY tespit_zamani DESC"
            ).fetchall()
        conn.close()
        # v2.0.7.366: `_CompatRow` bir dict alt sinifi - zip(cols, r) / a,b,c = r
        # DEGERLERI degil ANAHTARLARI dondurur (gercek PostgreSQL'le test edilirken
        # bulundu: onay kuyrugu 'id':'id','deger':'deger' gosteriyordu). Sozluk olarak al.
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[db] get_bekleyen_piyasa_tedbirleri hata: {e}", file=sys.stderr)
        return []


def piyasa_tedbir_onayla(tespit_id: int, kullanici_id: int) -> bool:
    """Admin bir tespiti onaylar: piyasa_tedbir_listesi'ne AKTIF bir
    kural olarak eklenir (load_universe() bir sonraki yuklemede okur) VE
    tespit 'onaylandi' olarak isaretlenir. Tek sorguda, ayni baglanti
    uzerinde yapilir ki biri basarili biri basarisiz olup tutarsiz kalma
    riski olmasin."""
    try:
        conn = get_conn()
        try:
            tespit = conn.execute(
                "SELECT eslesme_turu, deger, kategori, tedbir_turu, kaynak_turu, "
                "kaynak_referans, ek_veri FROM piyasa_tedbir_tespit WHERE id=? AND onay_durumu='bekliyor'",
                (tespit_id,)
            ).fetchone()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            tespit = conn.execute(
                "SELECT eslesme_turu, deger, kategori, tedbir_turu, kaynak_turu, "
                "kaynak_referans FROM piyasa_tedbir_tespit WHERE id=? AND onay_durumu='bekliyor'",
                (tespit_id,)
            ).fetchone()
        if not tespit:
            conn.close()
            return False
        eslesme_turu, deger, kategori, tedbir_turu, kaynak_turu, kaynak_referans = (
            tespit["eslesme_turu"], tespit["deger"], tespit["kategori"],
            tespit["tedbir_turu"], tespit["kaynak_turu"], tespit["kaynak_referans"])
        kaynak_aciklama = f"{kaynak_turu} {kaynak_referans or ''}".strip()
        if str(tedbir_turu).upper() == "KISMI_KALDIRMA":
            # v2.0.7.370 (CVL/BAG arastirmasi): SPK sirketin fonlarindan YALNIZCA BAZILARINI aciyor. TEK
            # islemde (atomik): sirket kurali pasife alinir + KAPALI KALACAK her fon icin TEKIL kural
            # yazilir (tasfiyedeki fonlar yanlislikla yeniden skorlanmasin). Gecersiz veri = HICBIR sey degismez.
            import json as _json
            try:
                ek = _json.loads(tespit["ek_veri"] or "{}")
                kalacak = [str(x).strip() for x in ek.get("kalacak", [])]
                if not isinstance(ek.get("kalacak"), list) or any(len(x) < 15 for x in kalacak):
                    raise ValueError("kalacak listesi gecersiz")
            except Exception as ve:
                print(f"[db] piyasa_tedbir_onayla KISMI_KALDIRMA ek_veri gecersiz, ISLEM YAPILMADI: {ve}", file=sys.stderr)
                conn.close()
                return False
            eski = conn.execute(
                "SELECT tedbir_turu FROM piyasa_tedbir_listesi WHERE eslesme_turu=? AND deger=? AND aktif=TRUE",
                (eslesme_turu, deger)).fetchone()
            if not eski:
                conn.close()
                return False                      # kaldirilacak AKTIF sirket kurali yok
            for ad in kalacak:
                conn.execute(
                    "INSERT INTO piyasa_tedbir_listesi "
                    "(eslesme_turu, deger, kategori, tedbir_turu, kaynak_aciklama, tespit_id) "
                    "VALUES ('SIRKET_ADI',?,?,?,?,?) "
                    "ON CONFLICT (eslesme_turu, deger) DO UPDATE SET "
                    "aktif=TRUE, kaldirilma_tarihi=NULL, tedbir_turu=EXCLUDED.tedbir_turu, "
                    "kaynak_aciklama=EXCLUDED.kaynak_aciklama, tespit_id=EXCLUDED.tespit_id",
                    (ad, kategori or "TEFAS", eski["tedbir_turu"],
                     f"KISMI KALDIRMA (kapali kaliyor) - {kaynak_aciklama}", tespit_id))
            conn.execute(
                "UPDATE piyasa_tedbir_listesi SET aktif=FALSE, kaldirilma_tarihi=now(), "
                "kaynak_aciklama=? WHERE eslesme_turu=? AND deger=?",
                (f"KISMI KALDIRILDI - {kaynak_aciklama}", eslesme_turu, deger))
            conn.execute(
                "UPDATE piyasa_tedbir_tespit SET onay_durumu='onaylandi', "
                "onay_zamani=now(), onaylayan_kullanici_id=? WHERE id=?",
                (kullanici_id, tespit_id))
            conn.commit()
            conn.close()
            return True
        if str(tedbir_turu).upper() == "KALDIRMA":
            # v2.0.7.366: tedbirin KALDIRILMASI - kural silinmez, pasife alinir (gecmis korunur)
            conn.execute(
                "UPDATE piyasa_tedbir_listesi SET aktif=FALSE, kaldirilma_tarihi=now(), "
                "kaynak_aciklama=? WHERE eslesme_turu=? AND deger=?",
                (f"KALDIRILDI - {kaynak_aciklama}", eslesme_turu, deger))
            conn.execute(
                "UPDATE piyasa_tedbir_tespit SET onay_durumu='onaylandi', "
                "onay_zamani=now(), onaylayan_kullanici_id=? WHERE id=?",
                (kullanici_id, tespit_id))
            conn.commit()
            conn.close()
            return True
        conn.execute(
            "INSERT INTO piyasa_tedbir_listesi "
            "(eslesme_turu, deger, kategori, tedbir_turu, kaynak_aciklama, tespit_id) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT (eslesme_turu, deger) DO UPDATE SET "
            "aktif=TRUE, kaldirilma_tarihi=NULL, tedbir_turu=EXCLUDED.tedbir_turu, "
            "kaynak_aciklama=EXCLUDED.kaynak_aciklama, tespit_id=EXCLUDED.tespit_id",
            (eslesme_turu, deger, kategori, tedbir_turu, kaynak_aciklama, tespit_id))
        conn.execute(
            "UPDATE piyasa_tedbir_tespit SET onay_durumu='onaylandi', "
            "onay_zamani=now(), onaylayan_kullanici_id=? WHERE id=?",
            (kullanici_id, tespit_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] piyasa_tedbir_onayla hata: {e}", file=sys.stderr)
        return False


def piyasa_tedbir_reddet(tespit_id: int, kullanici_id: int) -> bool:
    try:
        conn = get_conn()
        conn.execute(
            "UPDATE piyasa_tedbir_tespit SET onay_durumu='reddedildi', "
            "onay_zamani=now(), onaylayan_kullanici_id=? "
            "WHERE id=? AND onay_durumu='bekliyor'",
            (kullanici_id, tespit_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] piyasa_tedbir_reddet hata: {e}", file=sys.stderr)
        return False


def piyasa_tedbir_tespit_durumlari(eslesme_turu: str, deger: str, tedbir_turu: str) -> list:
    """v2.0.7.366: tarayicinin AYNI tespiti tekrar kuyruga atmamasi icin - ayni (tur, deger,
    tedbir) icin mevcut kayitlarin [(onay_durumu, tespit_zamani), ...] listesi."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT onay_durumu, tespit_zamani FROM piyasa_tedbir_tespit "
            "WHERE eslesme_turu=? AND deger=? AND tedbir_turu=?",
            (eslesme_turu, deger, tedbir_turu)).fetchall()
        conn.close()
        return [(r[0], r[1]) for r in rows]
    except Exception as e:
        print(f"[db] piyasa_tedbir_tespit_durumlari hata: {e}", file=sys.stderr)
        return []


def get_aktif_piyasa_tedbirleri() -> list:
    """app.py'nin load_universe()'i HER YUKLEMEDE bunu okur - onaylanmis
    ve hala aktif olan tum kurallar. Kucuk bir liste (onlarca satir)
    oldugu icin 5 dk'lik Streamlit cache'i (load_universe'in kendi
    cache'i) yeterli, ayrica bir cache katmani eklenmedi."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT eslesme_turu, deger, kategori, tedbir_turu, kaynak_aciklama "
            "FROM piyasa_tedbir_listesi WHERE aktif=TRUE"
        ).fetchall()
        conn.close()
        # v2.0.7.371: tedbir_turu + kaynak_aciklama da donuyor (sinyal etiketi tedbir TURUNE gore)
        return [{"eslesme_turu": r[0], "deger": r[1], "kategori": r[2],
                 "tedbir_turu": r[3], "kaynak_aciklama": r[4]} for r in rows]
    except Exception as e:
        print(f"[db] get_aktif_piyasa_tedbirleri hata: {e}", file=sys.stderr)
        return []


def tefas_fiyat_gecmisi_df_ekle(df, izinli_tickerlar=None, sayfa_boyutu: int = 5000) -> int:
    """v2.0.7.359 (3 Ekim 2026, Bahri'nin bulgusu - "TEFAS Gecmis Derin Doldur
    1,5 saat calisip hata verdi"): ESKI yontem her (fon x gun) icin AYRI bir
    INSERT gonderiyordu - Supabase'e her gidis-gelis ~130 ms oldugundan TEK bir
    gunun ~2000 satiri bile ~4,5 DAKIKA surdu (logda `_get_db_url` satirinin
    ~4,5 dakikada bir tekrarlanmasindan olculdu), 1 yillik bir parca (250+ gun)
    ise SAATLER surerdi. Artik psycopg2'nin execute_values'u ile binlerce satir
    TEK sorguda gonderiliyor (1 milyon satir icin birkac yuz sorgu, dakikalar).

    df: sutunlar [ticker, tarih, fiyat]. izinli_tickerlar verilirse yalnizca
    bunlar yazilir (evrende olmayan ~700 fonu arsive tasimamak icin).
    Idempotent (ON CONFLICT DO UPDATE). Dondurulen: yazilan satir sayisi."""
    import pandas as _pd
    if df is None or len(df) == 0:
        return 0
    try:
        from psycopg2.extras import execute_values
        d = df[["ticker", "tarih", "fiyat"]].copy()
        d["ticker"] = d["ticker"].astype(str)
        if izinli_tickerlar is not None:
            d = d[d["ticker"].isin(set(map(str, izinli_tickerlar)))]
        d["tarih"] = _pd.to_datetime(d["tarih"], errors="coerce").dt.strftime("%Y-%m-%d")
        d["fiyat"] = _pd.to_numeric(d["fiyat"], errors="coerce")
        d = d.dropna(subset=["ticker", "tarih", "fiyat"])
        d = d[d["fiyat"] > 0]
        # ON CONFLICT DO UPDATE ayni sorguda ayni satiri iki kez etkileyemez
        d = d.drop_duplicates(subset=["ticker", "tarih"], keep="last")
        satirlar = list(d.itertuples(index=False, name=None))
        if not satirlar:
            return 0

        conn = get_conn()
        pg = conn._conn
        yazilan = 0
        try:
            cur = pg.cursor()
            for i in range(0, len(satirlar), sayfa_boyutu):
                sayfa = satirlar[i:i + sayfa_boyutu]
                execute_values(
                    cur,
                    "INSERT INTO tefas_fiyat_gecmisi (ticker, tarih, fiyat) VALUES %s "
                    "ON CONFLICT (ticker, tarih) DO UPDATE SET fiyat=EXCLUDED.fiyat",
                    sayfa, page_size=len(sayfa))
                yazilan += len(sayfa)
                if (i // sayfa_boyutu) % 10 == 9:
                    pg.commit()
            pg.commit()
            cur.close()
        except Exception:
            try:
                pg.rollback()
            except Exception:
                pass
            raise
        finally:
            conn.close()
        return yazilan
    except Exception as e:
        print(f"[db] tefas_fiyat_gecmisi_df_ekle hata: {type(e).__name__}: {e}", file=sys.stderr)
        return 0


def tefas_fiyat_gecmisi_toplu_ekle(fiyat_map: dict, tarih=None) -> int:
    """Geriye uyumluluk sarmalayicisi: {ticker: fiyat} + tek tarih -> toplu yazim."""
    import pandas as _pd
    if not fiyat_map:
        return 0
    if tarih is None:
        from datetime import datetime, timezone, timedelta
        tarih = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d")
    df = _pd.DataFrame({"ticker": list(fiyat_map.keys()),
                        "tarih": tarih,
                        "fiyat": list(fiyat_map.values())})
    return tefas_fiyat_gecmisi_df_ekle(df)


_TEFAS_ARSIV_FIYAT_SQL = (
    "SELECT DISTINCT ON (ticker) ticker, fiyat FROM tefas_fiyat_gecmisi "
    "WHERE tarih BETWEEN CAST(? AS DATE) - ? AND CAST(? AS DATE) + ? "
    "ORDER BY ticker, ABS(tarih - CAST(? AS DATE)), tarih DESC")


def tefas_arsiv_fiyatlari(hedef_tarih: str, tolerans_gun: int = 10):
    """v2.0.7.363: kalici arsivden, her fon icin hedef tarihe EN YAKIN (+-tolerans
    gun icindeki) fiyat -> {ticker: fiyat}. 6 ay/1-3-5 yillik getirileri bayat
    Excel yerine GERCEK fiyatlardan hesaplamak icin. Veritabanina ulasilamazsa
    None doner (cagiran mevcut degerleri korur; bos dict = arsivde o tarihte
    veri yok)."""
    try:
        conn = get_conn()
        rows = conn.execute(
            _TEFAS_ARSIV_FIYAT_SQL,
            (hedef_tarih, int(tolerans_gun), hedef_tarih, int(tolerans_gun), hedef_tarih)
        ).fetchall()
        conn.close()
        return {str(r[0]): float(r[1]) for r in rows if r[1] is not None and float(r[1]) > 0}
    except Exception as e:
        print(f"[db] tefas_arsiv_fiyatlari hata ({hedef_tarih}): {type(e).__name__}: {e}", file=sys.stderr)
        return None


def tefas_fiyat_gecmisi_oku(ticker: str, gun: int = 1825) -> list:
    """v2.0.7.350: Bir fonun kendi arşivimizdeki (pytefas'a HİÇ gitmeden)
    birikmiş gerçek gecmisini okur - [(tarih, fiyat), ...] (tarihe göre
    artan). `gun`: kaç gün geriye bakılacağı (varsayılan ~5 yıl, yani
    arşivde ne kadar varsa hepsi döner)."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT tarih, fiyat FROM tefas_fiyat_gecmisi WHERE ticker=? "
            "AND tarih >= CURRENT_DATE - ? ORDER BY tarih ASC",
            (str(ticker), int(gun))
        ).fetchall()
        conn.close()
        return [(r[0], float(r[1])) for r in rows]
    except Exception as e:
        print(f"[db] tefas_fiyat_gecmisi_oku hata: {e}", file=sys.stderr)
        return []


def get_portfoy_stratejisi(user_id: int) -> str:
    """v2.0.7.353: kullanıcının Bütçe Optimizasyonu için seçtiği
    dağılım stratejisi ('kuresel' | 'kategori_guvenceli') - hem
    app.py'nin Ana Sayfa'sı hem zamanlanmış e-posta scripti BUNU okur,
    böylece ikisi HER ZAMAN aynı sonucu üretir."""
    try:
        conn = get_conn()
        row = conn.execute(
            "SELECT portfoy_dagilim_stratejisi FROM users WHERE id=?", (user_id,)
        ).fetchone()
        conn.close()
        if row and row[0] in ("kuresel", "kategori_guvenceli"):
            return row[0]
        return "kuresel"
    except Exception as e:
        print(f"[db] get_portfoy_stratejisi hata: {e}", file=sys.stderr)
        return "kuresel"


def set_portfoy_stratejisi(user_id: int, strateji: str) -> bool:
    if strateji not in ("kuresel", "kategori_guvenceli"):
        return False
    try:
        conn = get_conn()
        conn.execute(
            "UPDATE users SET portfoy_dagilim_stratejisi=? WHERE id=?",
            (strateji, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] set_portfoy_stratejisi hata: {e}", file=sys.stderr)
        return False


def get_portfoy_ayarlari(user_id: int) -> dict:
    """v2.0.7.355: kullanıcının kaydettiği bütçe/risk/max varlık/strateji -
    Ana Sayfa VE zamanlanmış e-posta scripti AYNI DEĞERLERİ okur."""
    _varsayilan = {"butce": 20000.0, "risk": "Orta", "max_varlik": 10,
                   "strateji": "kuresel"}
    try:
        conn = get_conn()
        row = conn.execute(
            "SELECT portfoy_butce, portfoy_risk, portfoy_max_varlik, "
            "portfoy_dagilim_stratejisi FROM users WHERE id=?", (user_id,)
        ).fetchone()
        conn.close()
        if not row:
            return _varsayilan
        return {
            "butce": float(row[0]) if row[0] else _varsayilan["butce"],
            "risk": row[1] if row[1] in ("Çok Düşük","Düşük","Orta","Yüksek","Çok Yüksek") else _varsayilan["risk"],
            "max_varlik": int(row[2]) if row[2] else _varsayilan["max_varlik"],
            "strateji": row[3] if row[3] in ("kuresel", "kategori_guvenceli") else _varsayilan["strateji"],
        }
    except Exception as e:
        print(f"[db] get_portfoy_ayarlari hata: {e}", file=sys.stderr)
        return _varsayilan


def get_portfoy_ayarlari_by_email(email: str) -> dict:
    """v2.0.7.359: e-posta adresinden kayitli portfoy ayarlari (tetikleyici
    yolu icin - kullanici oturumu yokken)."""
    try:
        conn = get_conn()
        row = conn.execute("SELECT id FROM users WHERE LOWER(email)=LOWER(?)", (email,)).fetchone()
        conn.close()
        if row:
            return get_portfoy_ayarlari(row[0])
    except Exception as e:
        print(f"[db] get_portfoy_ayarlari_by_email hata: {e}", file=sys.stderr)
    return {"butce": 20000.0, "risk": "Orta", "max_varlik": 10, "strateji": "kuresel"}


def set_portfoy_ayarlari(user_id: int, butce: float = None, risk: str = None,
                         max_varlik: int = None) -> bool:
    _alanlar, _degerler = [], []
    if butce is not None and butce > 0:
        _alanlar.append("portfoy_butce=?"); _degerler.append(float(butce))
    if risk is not None and risk in ("Çok Düşük","Düşük","Orta","Yüksek","Çok Yüksek"):
        _alanlar.append("portfoy_risk=?"); _degerler.append(risk)
    if max_varlik is not None and max_varlik > 0:
        _alanlar.append("portfoy_max_varlik=?"); _degerler.append(int(max_varlik))
    if not _alanlar:
        return False
    try:
        conn = get_conn()
        _degerler.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(_alanlar)} WHERE id=?", tuple(_degerler))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] set_portfoy_ayarlari hata: {e}", file=sys.stderr)
        return False


def enag_oran_kaydet(yil_ay: str, aylik_oran: float) -> bool:
    """v2.0.7.313: ENAG'in bir ayina ait aylik enflasyon oranini
    kaydeder/gunceller (upsert). yil_ay formati 'YYYY-MM' (orn. '2026-08').
    TUM kullanicilar icin ORTAK/GLOBAL tek bir tablo - ENAG orani herkes
    icin ayni, kullaniciya ozel degil (benchmark_rates'ten farkli olarak)."""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO enag_aylik_enflasyon (yil_ay, aylik_oran, guncelleme_tarihi) "
            "VALUES (?, ?, now()) "
            "ON CONFLICT (yil_ay) DO UPDATE SET "
            "aylik_oran = EXCLUDED.aylik_oran, guncelleme_tarihi = now()",
            (yil_ay, float(aylik_oran)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] enag_oran_kaydet hata: {e}", file=sys.stderr)
        return False


def enag_oranlari_getir() -> dict:
    """v2.0.7.313: Kayitli TUM ENAG aylik oranlarini {yil_ay: oran} sozlugu
    olarak doner - app.py bunu kumulatif enflasyon serisi olusturmak icin
    kullanir (bkz. _enag_kumulatif_seri)."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT yil_ay, aylik_oran FROM enag_aylik_enflasyon"
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[db] enag_oranlari_getir hata: {e}", file=sys.stderr)
        return {}
    sonuc = {}
    for r in rows:
        yil_ay = r["yil_ay"] if isinstance(r, dict) else r[0]
        oran = r["aylik_oran"] if isinstance(r, dict) else r[1]
        sonuc[yil_ay] = float(oran)
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


def haber_akisi_ve_islenmis_sifirla(gun: int = 2) -> dict:
    """v2.0.7.163 (Bahri'nin bulgusu, 19 Ağustos 2026 — "Maradona haberi
    yine filtreye takılan haberler arasına giriyor"): KÖK NEDEN'in
    kalıcı çözümü. `eslesen_kalip` ve `baslik_tr` bir haberin AKIŞA
    YAZILDIĞI ANDA hesaplanıp donuyor — filtre/çeviri mantığı sonradan
    düzelse bile ESKİ satırlar YENİDEN DEĞERLENDİRİLMEZ, çünkü URL zaten
    `haber_islenmis`te "görüldü" işaretli olduğu için RSS döngüsü bir
    daha o habere hiç uğramaz.

    Bu fonksiyon Admin Paneli'nden ELLE tetiklenir: son `gun` gün
    içindeki hem `haber_akisi` hem `haber_islenmis` satırlarını siler -
    böylece bir SONRAKİ haber_izleme.py turunda, RSS kaynağında HÂLÂ
    mevcut olan URL'ler "yeni" sayılıp GÜNCEL kod (kelime sınırı filtresi
    + güncel Admin Paneli kalıpları) ile YENİDEN işlenir/çevrilir.

    SINIRLAMA (Admin Paneli'nde kullanıcıya AÇIKÇA gösterilmeli): her
    kaynaktan sadece en yeni ~30 haber RSS'te tutulur. Bu pencerenin
    DIŞINA çıkmış (kaynağın artık listelemediği) eski haberler GERİ
    GELMEZ - o satırlar yalnızca 7 günlük doğal temizlikle
    (`haber_akisi_temizle`) kaybolur, YENİDEN İŞLENMEZ.

    Döner: {"akis_silinen": N, "islenmis_silinen": N} - N okunamazsa
    None (hata değil, sadece rowcount driver'dan gelmemiş olabilir)."""
    sonuc = {"akis_silinen": None, "islenmis_silinen": None}
    try:
        conn = get_conn()
        c1 = conn.execute(
            "DELETE FROM haber_akisi WHERE eklenme_zamani > "
            f"now() - interval '{int(gun)} days'")
        sonuc["akis_silinen"] = c1.rowcount if c1.rowcount is not None and c1.rowcount >= 0 else None
        c2 = conn.execute(
            "DELETE FROM haber_islenmis WHERE islenme_zamani > "
            f"now() - interval '{int(gun)} days'")
        sonuc["islenmis_silinen"] = c2.rowcount if c2.rowcount is not None and c2.rowcount >= 0 else None
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] haber_akisi_ve_islenmis_sifirla hata: {e}", file=sys.stderr)
    return sonuc


def ai_cagri_sayisi_bugun() -> int:
    """v2.0.7.160: Bugun kac Gemini cagrisi yapildi? Butce kontrolu icin."""
    try:
        bugun = datetime.date.today().isoformat()
        conn = get_conn()
        row = conn.execute(
            "SELECT cagri_sayisi FROM ai_cagri_butcesi WHERE tarih=?",
            (bugun,)).fetchone()
        conn.close()
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


# ══════════════════════════════════════════════════════════════
# v2.0.7.162: KALIP YÖNETİMİ (okuma + CRUD) - Admin Paneli'nden çağrılır.
# ══════════════════════════════════════════════════════════════

def get_kaliplar(sadece_aktif: bool = False) -> list:
    """Tum kaliplari, her birinin kelimeleri VE etki puanlariyla BIRLIKTE
    doner - Admin Paneli'ndeki tablo ve haber_izleme.py/app.py'nin
    baslangic yuklemesi bunu kullanir. Tek sorguda N+1 sorgu sorunundan
    kacinmak icin 3 ayri sorgu yapip Python tarafinda birlestiriyoruz -
    3 sorgu, kalip basina 1 sorgu yerine 3 sabit sorgu (kalip sayisi
    artsa da sorgu sayisi artmaz)."""
    try:
        conn = get_conn()
        where = "WHERE aktif = TRUE" if sadece_aktif else ""
        kaliplar = conn.execute(
            f"SELECT kalip_key, ad, aciklama, aktif, istatistiksel_dayanak "
            f"FROM haber_kaliplari "
            f"{where} ORDER BY olusturma_zamani").fetchall()
        kelimeler = conn.execute(
            "SELECT kalip_key, dil, kelime FROM haber_kalip_kelime "
            "ORDER BY id").fetchall()
        etkiler = conn.execute(
            "SELECT kalip_key, kategori, puan FROM haber_kalip_etki "
            "ORDER BY id").fetchall()
        conn.close()
    except Exception as e:
        print(f"[db] get_kaliplar hata: {e}", file=sys.stderr)
        return []

    def _v(row, key, idx):
        return row[key] if isinstance(row, dict) else row[idx]

    sonuc = {}
    for r in kaliplar:
        kk = _v(r, "kalip_key", 0)
        sonuc[kk] = {
            "kalip_key": kk, "ad": _v(r, "ad", 1),
            "aciklama": _v(r, "aciklama", 2), "aktif": bool(_v(r, "aktif", 3)),
            # v2.0.7.194 (Bahri'nin talebi - "her haberin optima skoruna
            # etki etmesi söz konusu olamaz"): kalıbın gerçek akademik/
            # tarihsel dayanağı olup olmadığı - "Tümünü Onayla (kriterleri
            # karşılayanlar)" toplu onay özelliği bu bayrağı kontrol eder.
            "istatistiksel_dayanak": bool(_v(r, "istatistiksel_dayanak", 4)),
            "kelimeler": {"tr": [], "en": []}, "etkiler": {},
        }
    for r in kelimeler:
        kk = _v(r, "kalip_key", 0)
        if kk in sonuc:
            sonuc[kk]["kelimeler"].setdefault(_v(r, "dil", 1), []).append(_v(r, "kelime", 2))
    for r in etkiler:
        kk = _v(r, "kalip_key", 0)
        if kk in sonuc:
            sonuc[kk]["etkiler"][_v(r, "kategori", 1)] = float(_v(r, "puan", 2))
    return list(sonuc.values())


def kalip_istatistiksel_dayanak_ayarla(kalip_key: str, deger: bool) -> bool:
    """v2.0.7.194 (Bahri'nin talebi, 25 Ağustos 2026): Admin Paneli'nden
    bir kalıbın gerçek akademik/tarihsel dayanağı olup olmadığını
    işaretlemek için. Sadece bu bayrak TRUE olan kalıpların tespitleri
    "Tümünü Onayla (kriterleri karşılayanlar)" ile toplu onaylanabilir."""
    try:
        conn = get_conn()
        conn.execute(
            "UPDATE haber_kaliplari SET istatistiksel_dayanak=? WHERE kalip_key=?",
            (bool(deger), kalip_key))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] kalip_istatistiksel_dayanak_ayarla hata: {e}", file=sys.stderr)
        return False


def coklu_kaynak_teyidi(kalip_key: str, kendi_haber_kaynak: str, saat: int = 24) -> bool:
    """v2.0.7.194 (Bahri'nin talebi — "birden fazla haber kaynağında
    aynı haber olduğu teyid edilmeli"): Aynı kalıp için, KENDİSİNDEN
    FARKLI bir haber_kaynak'a (ör. AA Ekonomi/BBC/Al Jazeera - aynı
    kaynağın farklı bir URL'i DEĞİL, gerçekten FARKLI bir kaynak) sahip
    başka bir tespit, son `saat` saat içinde var mı diye kontrol eder.

    NOT: Bu kaba bir vekildir (proxy) - "aynı OLAYIN farklı kaynaklarca
    haber yapılması" ile "aynı kalıba uyan FARKLI bir olayın aynı gün
    olması" arasında ayrım yapmaz (ikisi de bu sorguda "teyit edilmiş"
    görünür). Daha kesin bir eşleştirme (başlık benzerliği/aynı olay
    tespiti) ileride eklenebilir - şimdilik "aynı kalıpta yakın zamanda
    birden fazla FARKLI kaynaktan tetikleme" makul bir ilk yaklaşım."""
    try:
        conn = get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as adet FROM beklenti_otomatik_tespit "
            "WHERE kalip_key=? AND haber_kaynak != ? "
            "AND tespit_zamani > now() - interval '%s hours'" % int(saat),
            (kalip_key, kendi_haber_kaynak)).fetchone()
        conn.close()
        adet = (row["adet"] if isinstance(row, dict) else row[0]) if row else 0
        return int(adet or 0) > 0
    except Exception as e:
        print(f"[db] coklu_kaynak_teyidi hata: {e}", file=sys.stderr)
        return False


def kalip_ekle(kalip_key: str, ad: str, aciklama: str = "") -> bool:
    """Yeni kalip olusturur (henuz kelime/etki icermez - ayrica eklenmeli).
    kalip_key benzersiz olmali - zaten varsa False doner, coker degil."""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO haber_kaliplari (kalip_key, ad, aciklama, aktif) "
            "VALUES (?,?,?,TRUE)", (kalip_key, ad, aciklama))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] kalip_ekle hata (muhtemelen kalip_key zaten var): {e}", file=sys.stderr)
        return False


def kalip_aktif_durum_degistir(kalip_key: str, aktif: bool):
    """Kalibi PASIFE alir/aktif eder - SILMEZ. Pasif kaliplar hem
    on-filtrede hem AI dogrulamasinda ATLANIR ama kelime/etki gecmisi
    kaybolmaz - yanlislikla kapatilirsa geri acilabilir."""
    try:
        conn = get_conn()
        conn.execute("UPDATE haber_kaliplari SET aktif=? WHERE kalip_key=?",
                     (aktif, kalip_key))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] kalip_aktif_durum_degistir hata: {e}", file=sys.stderr)


def kalip_sil(kalip_key: str):
    """Kalibi VE ona bagli TUM kelime/etki satirlarini siler (CASCADE).
    GERI ALINAMAZ - Admin Paneli'nde onay istenmeli."""
    try:
        conn = get_conn()
        conn.execute("DELETE FROM haber_kaliplari WHERE kalip_key=?", (kalip_key,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] kalip_sil hata: {e}", file=sys.stderr)


def kalip_kelime_ekle(kalip_key: str, dil: str, kelime: str):
    """dil: 'tr' veya 'en'. Turkce kelimeler haberde COKUL/hal EKLERIYLE
    de eslesir (ornek: 'savas' -> 'savasi','savasta'), Ingilizce SADECE
    coguluyla eslesir - bkz. haber_izleme.py _DERLENMIS_KALIPLAR notu."""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO haber_kalip_kelime (kalip_key, dil, kelime) VALUES (?,?,?)",
            (kalip_key, dil, kelime.strip().lower()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] kalip_kelime_ekle hata: {e}", file=sys.stderr)


def kalip_kelime_sil(kalip_key: str, dil: str, kelime: str):
    try:
        conn = get_conn()
        conn.execute(
            "DELETE FROM haber_kalip_kelime WHERE kalip_key=? AND dil=? AND kelime=?",
            (kalip_key, dil, kelime))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] kalip_kelime_sil hata: {e}", file=sys.stderr)


def kalip_etki_kaydet(kalip_key: str, kategori: str, puan: float):
    """UPSERT - kategori icin etki zaten varsa GUNCELLER, yoksa EKLER.
    kategori: MADEN / DOVIZ / BIST / KRIPTO. puan=0 verilirse satir SILINIR
    (0 puan 'etkisiz' demektir, saklamanin anlami yok)."""
    try:
        conn = get_conn()
        if float(puan) == 0:
            conn.execute(
                "DELETE FROM haber_kalip_etki WHERE kalip_key=? AND kategori=?",
                (kalip_key, kategori))
        else:
            _var = conn.execute(
                "SELECT id FROM haber_kalip_etki WHERE kalip_key=? AND kategori=?",
                (kalip_key, kategori)).fetchone()
            if _var:
                conn.execute(
                    "UPDATE haber_kalip_etki SET puan=? WHERE kalip_key=? AND kategori=?",
                    (puan, kalip_key, kategori))
            else:
                conn.execute(
                    "INSERT INTO haber_kalip_etki (kalip_key, kategori, puan) VALUES (?,?,?)",
                    (kalip_key, kategori, puan))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] kalip_etki_kaydet hata: {e}", file=sys.stderr)


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


def get_bekleyen_tespitler(kullanici_id) -> list:
    """v2.0.7.156 (Bahri'nin talebi, KRİTİK tasarım düzeltmesi): app.py
    bunu her sayfa yuklemesinde cagirir - suresi gecmemis VE HENUZ
    ONAY/RED VERİLMEMİŞ tespitleri doner. Bunlar Optima Skor'a HENUZ
    UYGULANMAMIŞTIR - sadece kullanıcıya "onaylar mısınız?" diye
    gösterilecek adaylardır.

    v2.0.7.199/200: Çoklu kaynak teyidi (aynı kalıp, farklı kaynak,
    24 saat içinde + başlık benzerliği) - bkz. PROJE_NOTLARI.md.

    v2.0.7.203 (Bahri'nin talebi, 26 Ağustos 2026 — "her abone kendi
    tespitlerini görsün/onaylasın, Optima Skor kişiye özel olsun"):
    KRİTİK MİMARİ DEĞİŞİKLİK - artık `kullanici_id` ZORUNLU parametre.

    v2.0.7.209 (Bahri'nin bulgusu, 29 Ağustos 2026 — "kullanıcının
    onayına sunulacak pop-up'ın en az iki kaynaktan doğrulanmış olması
    VE yüksek şiddette olması kuralıydı, gelen pop-up'larda bu
    kuralların uygulanmadığını görüyorum"): İKİ GERÇEK EKSİKLİK
    BULUNDU VE DÜZELTİLDİ:
    (1) "Yüksek şiddet" kuralı ASLA pop-up gösterimine bir ŞART olarak
        eklenmemişti - sadece AYRI bir özellik olan toplu onayın
        ("Tümünü Onayla") 3 kriterinden biriydi. Bahri'nin ORİJİNAL
        isteği ("çok yüksek risk taşıyan... olsun, diğerlerini pop-up
        yapma") aslında POP-UP'IN KENDİSİ için bir şarttı - bu şimdi
        SQL'e `AND t1.siddet = 'Yüksek'` olarak eklendi.
    (2) Çoklu kaynak teyidi ARKA PLANDA doğru çalışıyordu ama ARAYÜZDE
        HİÇ GÖRÜNMÜYORDU - modal/liste sadece tespitin KENDİ tek
        kaynağını gösteriyordu, teyit eden İKİNCİ kaynak tamamen
        görünmezdi. Bu, Bahri'ye "teyit hiç yapılmamış" izlenimi
        veriyordu (yanlış, ama şeffaflık eksikliği yüzünden GÖRÜNÜŞTE
        doğru). Artık her tespit sözlüğü `teyit_kaynak` ve
        `teyit_baslik` alanlarını da içeriyor - app.py bunu
        gösterebilir."""
    import difflib

    def _baslik_benzer_mi(b1, b2, esik=0.35):
        if not b1 or not b2:
            return False
        oran = difflib.SequenceMatcher(None, b1.lower(), b2.lower()).ratio()
        return oran >= esik

    if not kullanici_id:
        return []

    try:
        # v2.0.7.287 (10 Eylul 2026, Bahri'nin talebi - "sistem, aynı
        # olay için gelen her haberi ayrı bir bekleyen kayıt olarak
        # görmesin, reddedilen haber 24 saat gecmeden tekrar gundeme
        # gelmesin"): YENI KURAL - eger bu kullanici, AYNI kalip_key
        # icin son 24 saatte bir tespiti REDDETMISSE, o kalibin YENI
        # bir haberle tekrar gelen versiyonu da (FARKLI bir tespit_id
        # olsa bile) ARTIK POP-UP OLARAK GOSTERILMIYOR - "NOT EXISTS"
        # kontrolu ONCEDEN SADECE AYNI tespit_id icin karar var mi diye
        # bakiyordu (farkli id = farkli haber makalesi oldugu icin bu
        # kontrolden GECIYORDU, red kalici olmuyordu). Artik AYRICA
        # "ayni kalip_key + reddedildi + son 24 saat" de eleniyor.
        conn = get_conn()
        rows = conn.execute(
            "SELECT t1.id, t1.kalip_key, t1.siddet, t1.haber_basligi, "
            "t1.haber_url, t1.haber_kaynak, t1.ai_gerekce, t1.tespit_zamani "
            "FROM beklenti_otomatik_tespit t1 "
            "WHERE t1.gecerlilik_bitis > now() "
            "AND t1.siddet = 'Yüksek' "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM kullanici_tespit_karari k "
            "  WHERE k.tespit_id = t1.id AND k.kullanici_id = ?"
            ") "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM kullanici_tespit_karari k2 "
            "  JOIN beklenti_otomatik_tespit t2 ON t2.id = k2.tespit_id "
            "  WHERE k2.kullanici_id = ? AND t2.kalip_key = t1.kalip_key "
            "  AND k2.karar = 'reddedildi' "
            "  AND k2.karar_zamani > now() - interval '24 hours'"
            ")",
            (kullanici_id, kullanici_id)
        ).fetchall()
        if not rows:
            conn.close()
            return []

        def _v(r, k, i):
            return r[k] if isinstance(r, dict) else r[i]

        # Ayni kalipteki TUM son-24-saat tespitleri (paylasimli havuzdan,
        # kullanicidan BAGIMSIZ) tek seferde cek - her aday icin ayri
        # sorgu atmamak icin (performans).
        # v2.0.7.215 (Bahri'nin talebi - Kaynak bolumunde teyit eden
        # ikinci kaynagin da tiklanabilir bir link olmasi): haber_url
        # da sorguya eklendi.
        # v2.0.7.324: ayni baglanti (conn) yeniden kullaniliyor - ikinci
        # bir get_conn() cagirip ayri bir baglanti acmaya gerek yok.
        tum_yakin = conn.execute(
            "SELECT id, kalip_key, haber_basligi, haber_kaynak, haber_url "
            "FROM beklenti_otomatik_tespit "
            "WHERE tespit_zamani > now() - interval '24 hours'"
        ).fetchall()
        conn.close()

        onaylanan_id_listesi = []
        # v2.0.7.209/215: teyit eden kaynagin bilgisini (kaynak, baslik,
        # url) de sakla - hem ana cumlede hem Kaynak listesinde
        # goruntulemek icin.
        # v2.0.7.217 (Bahri'nin sorusu, 29 Ağustos 2026 — "üç, dört,
        # beş, altı kaynak olması halinde pop-up bunları da
        # gösterebilecek mi?"): KESİN KÖK NEDEN - eski kod ilk eşleşen
        # teyidi bulur bulmaz `break` ile aramayı durduruyordu, bu
        # yüzden 5-6 kaynak aynı haberi doğrulasa bile SADECE İLKİ
        # yakalanıyordu. Artık `teyit_bilgisi[_id]` tekil bir sözlük
        # DEĞİL, bir LİSTE - eşleşen HER FARKLI kaynak (aynı kaynaktan
        # birden fazla makale varsa bile o kaynak sadece BİR KEZ
        # sayılır) listeye ekleniyor, `break` KALDIRILDI.
        teyit_bilgisi = {}
        for r in rows:
            _id = _v(r, "id", 0)
            _kalip = _v(r, "kalip_key", 1)
            _baslik = _v(r, "haber_basligi", 3)
            _kaynak = _v(r, "haber_kaynak", 5)
            _bu_tespitin_teyitleri = []
            _teyit_eden_kaynaklar = {_kaynak}  # kendi kaynagi + eklenen her teyit kaynagi buraya girer (tekrar onlemek icin)
            for r2 in tum_yakin:
                _id2 = _v(r2, "id", 0)
                if _id2 == _id:
                    continue
                if _v(r2, "kalip_key", 1) != _kalip:
                    continue
                _kaynak2 = _v(r2, "haber_kaynak", 3)
                if _kaynak2 in _teyit_eden_kaynaklar:
                    continue  # ayni kaynak (birincil VEYA zaten eklenmis bir teyit) - tekrar sayilmaz
                _baslik2 = _v(r2, "haber_basligi", 2)
                if _baslik_benzer_mi(_baslik, _baslik2):
                    _bu_tespitin_teyitleri.append({
                        "kaynak": _kaynak2, "baslik": _baslik2,
                        "url": _v(r2, "haber_url", 4),
                    })
                    _teyit_eden_kaynaklar.add(_kaynak2)
                    # NOT: break YOK - taramaya devam, BASKA teyit
                    # eden kaynaklar da varsa hepsini toplasin.
            if _bu_tespitin_teyitleri:
                onaylanan_id_listesi.append(_id)
                teyit_bilgisi[_id] = _bu_tespitin_teyitleri

        onaylanan_satirlar = [r for r in rows if _v(r, "id", 0) in onaylanan_id_listesi]
        # v2.0.7.200: Python tarafinda filtreleme SQL'in ORDER BY'ini
        # kaybettirdi - en yeni once sirasi burada geri saglaniyor.
        onaylanan_satirlar.sort(key=lambda r: _v(r, "tespit_zamani", 6), reverse=True)

        # v2.0.7.287 (10 Eylul 2026, Bahri'nin talebi - "aynı olay için
        # gelen her haberi ayrı bir bekleyen kayıt olarak görmesin"):
        # AYNI kalip_key'e ait BIRDEN FAZLA onaylanmis tespit varsa
        # (orn. 20 farkli haber kaynagi ayni jeopolitik olayi
        # bildiriyorsa), bunlarin HEPSI ayri ayri pop-up olarak
        # gosterilmek YERINE, kalip_key'e gore GRUPLANIP tek bir
        # TEMSILCI (en yuksek siddetli, esitlikte en yeni) SECILIYOR -
        # digerlerinin kaynak/baslik bilgisi bu TEK temsilcinin teyit
        # listesine EKLENIYOR (bilgi kaybi yok, sadece pop-up sayisi
        # azaliyor).
        _siddet_sirasi_grup = {"Düşük": 0, "Orta": 1, "Yüksek": 2}
        _kalip_gruplari = {}
        for r in onaylanan_satirlar:
            _kalip_gruplari.setdefault(_v(r, "kalip_key", 1), []).append(r)

        _temsilciler = []
        _ekstra_teyit = {}  # temsilci_id -> [{"kaynak":..,"baslik":..,"url":..}, ...]
        for _kalip, _grup in _kalip_gruplari.items():
            _grup_sirali = sorted(
                _grup,
                key=lambda r: (_siddet_sirasi_grup.get(_v(r, "siddet", 2), 1), _v(r, "tespit_zamani", 6)),
                reverse=True)
            _temsilci = _grup_sirali[0]
            _temsilciler.append(_temsilci)
            _temsilci_id = _v(_temsilci, "id", 0)
            _ekstra_teyit[_temsilci_id] = []
            for _diger in _grup_sirali[1:]:
                _ekstra_teyit[_temsilci_id].append({
                    "kaynak": _v(_diger, "haber_kaynak", 5),
                    "baslik": _v(_diger, "haber_basligi", 3),
                    "url": _v(_diger, "haber_url", 4),
                })
        _temsilciler.sort(key=lambda r: _v(r, "tespit_zamani", 6), reverse=True)
        onaylanan_satirlar = _temsilciler
    except Exception:
        return []
    _sonuc_listesi = _tespit_satirlarini_donustur(onaylanan_satirlar)
    # v2.0.7.217: artik TEK bir teyit degil, BIRDEN FAZLA teyit eden
    # kaynak listesi ekleniyor - "teyit_listesi" alani (bos liste =
    # teyit yok, ki bu duruma zaten hic ulasilmaz cunku teyitsiz
    # tespitler yukarida zaten elenmisti).
    for _d in _sonuc_listesi:
        _birlesik_teyit = list(teyit_bilgisi.get(_d.get("id"), []))
        _mevcut_kaynaklar = {_t["kaynak"] for _t in _birlesik_teyit} | {_d.get("haber_kaynak")}
        for _ek in _ekstra_teyit.get(_d.get("id"), []):
            if _ek["kaynak"] not in _mevcut_kaynaklar:
                _birlesik_teyit.append(_ek)
                _mevcut_kaynaklar.add(_ek["kaynak"])
        _d["teyit_listesi"] = _birlesik_teyit
    return _sonuc_listesi


def get_onaylanmis_tespitler(kullanici_id) -> list:
    """v2.0.7.156: kullanıcının AÇIKÇA onayladığı, hâlâ geçerlilik
    süresi dolmamış tespitler - SADECE BUNLAR Optima Skor'a uygulanır.

    v2.0.7.203 (Bahri'nin talebi — "Optima Skor kişiye özel olsun"):
    ARTIK `kullanici_id` ZORUNLU - SADECE BU KULLANICININ
    `kullanici_tespit_karari` tablosundaki 'onaylandi' kararları
    sayılıyor. AYNI habere Kullanıcı A onay verip Kullanıcı B
    vermemiş olabilir - bu durumda Optima Skor ikisi için FARKLI
    görünür (Kullanıcı A'nınki habere göre ayarlanmış, B'ninki
    varsayılan kalır)."""
    if not kullanici_id:
        return []
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT t.id, t.kalip_key, t.siddet, t.haber_basligi, t.haber_url, "
            "t.haber_kaynak, t.ai_gerekce, t.tespit_zamani "
            "FROM beklenti_otomatik_tespit t "
            "JOIN kullanici_tespit_karari k ON k.tespit_id = t.id "
            "WHERE k.kullanici_id = ? AND k.karar = 'onaylandi' "
            "AND t.gecerlilik_bitis > now() "
            "ORDER BY t.tespit_zamani DESC",
            (kullanici_id,)
        ).fetchall()
        conn.close()
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


def tespit_onayla(kullanici_id, tespit_id: int):
    """Kullanıcı (Ana Sayfa'daki "Onayla" butonu) bir tespiti uygun
    bulursa - BUNDAN SONRA SADECE O KULLANICININ Optima Skor'una
    uygulanır.

    v2.0.7.203 (Bahri'nin talebi — kişiye özel skor): ARTIK
    `kullanici_id` ZORUNLU parametre - karar, paylaşımlı tabloya
    DEĞİL, o kullanıcıya özel `kullanici_tespit_karari` satırına
    yazılıyor (UPSERT - fikrini değiştirirse güncellenir)."""
    if not kullanici_id:
        return False
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO kullanici_tespit_karari (kullanici_id, tespit_id, karar, karar_zamani) "
            "VALUES (?, ?, 'onaylandi', now()) "
            "ON CONFLICT (kullanici_id, tespit_id) DO UPDATE SET karar='onaylandi', karar_zamani=now()",
            (kullanici_id, tespit_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] tespit_onayla hata: {e}", file=sys.stderr)
        return False


def tespit_reddet(kullanici_id, tespit_id: int):
    """Kullanıcı bir tespiti uygun bulmazsa - SADECE O KULLANICIYA bir
    daha gösterilmez, SADECE O KULLANICININ Optima Skor'una uygulanmaz
    (diğer kullanıcılar bu tespiti hâlâ görüp kendi kararlarını
    verebilir).

    v2.0.7.203 (Bahri'nin talebi — kişiye özel skor): ARTIK
    `kullanici_id` ZORUNLU parametre."""
    if not kullanici_id:
        return False
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO kullanici_tespit_karari (kullanici_id, tespit_id, karar, karar_zamani) "
            "VALUES (?, ?, 'reddedildi', now()) "
            "ON CONFLICT (kullanici_id, tespit_id) DO UPDATE SET karar='reddedildi', karar_zamani=now()",
            (kullanici_id, tespit_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] tespit_reddet hata: {e}", file=sys.stderr)
        return False


def tespit_karar_toplu(kullanici_id, tespit_id_listesi, karar: str) -> int:
    """v2.0.7.286 (10 Eylul 2026, Bahri'nin bulgusu - "Tumunu Reddet
    cok uzun suruyor"): TEK BIR baglanti/sorguyla, BIRDEN FAZLA
    tespit_id icin ayni karari ('onaylandi'/'reddedildi') yazar.
    ONCEKI YONTEM ("Tumunu Reddet"/"Tumunu Onayla" dugmeleri) her
    tespit icin AYRI bir `tespit_reddet()`/`tespit_onayla()` cagrisi
    yapiyordu - HER cagri KENDI Supabase baglantisini aciyor/kapatiyordu
    (klasik N+1 sorunu) - dusinlerce bekleyen tespit varsa (Bahri'nin
    bildirdigi durum), bu ONLARCA ayri ag gidis-gelisi anlamina
    geliyordu. Artik TEK bir INSERT ifadesiyle, TEK bir baglantiyla
    TUMU birden yaziliyor. Basariyla islenen kayit sayisini dondurur."""
    if not kullanici_id or not tespit_id_listesi:
        return 0
    try:
        conn = get_conn()
        # Her tespit_id icin (kullanici_id, tespit_id, karar, now())
        # dortlusunu tek bir VALUES listesinde birlestiriyoruz.
        _degerler_sablonu = ", ".join(["(?, ?, ?, now())"] * len(tespit_id_listesi))
        _parametreler = []
        for _tid in tespit_id_listesi:
            _parametreler.extend([kullanici_id, _tid, karar])
        conn.execute(
            f"INSERT INTO kullanici_tespit_karari (kullanici_id, tespit_id, karar, karar_zamani) "
            f"VALUES {_degerler_sablonu} "
            f"ON CONFLICT (kullanici_id, tespit_id) DO UPDATE SET karar=EXCLUDED.karar, karar_zamani=now()",
            tuple(_parametreler))
        conn.commit()
        conn.close()
        return len(tespit_id_listesi)
    except Exception as e:
        print(f"[db] tespit_karar_toplu hata: {e}", file=sys.stderr)
        return 0


# ── v2.0.7.254: Kullanici Aktivite/Sayfa Ziyaret Takibi (Admin Paneli) ───────
def sayfa_ziyareti_kaydet(kullanici_id, sayfa: str) -> bool:
    """Bir SAYFA DEGISIKLIGINI kaydeder - app.py TARAFINDAN SADECE sayfa
    GERCEKTEN degistiginde cagrilir (her tiklamada/rerun'da DEGIL) - bu
    yuzden yazma sikligi dogal olarak dusuk kalir, bugunku "her renderda
    gereksiz Supabase baglantisi" derslerine aykiri bir yavaslik
    kaynagi YARATMAZ. Hata durumunda SESSIZCE False doner - istatistik
    kaydinin basarisiz olmasi kullanicinin asil islemini ASLA
    engellememeli."""
    if not kullanici_id or not sayfa:
        return False
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO sayfa_ziyaretleri (user_id, sayfa, giris_zamani) "
            "VALUES (?, ?, now())",
            (kullanici_id, sayfa))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] sayfa_ziyareti_kaydet hata: {e}", file=sys.stderr)
        return False


def kullanici_ziyaret_gecmisi(kullanici_id, limit: int = 500) -> list:
    """Bir kullanicinin en SON `limit` sayfa ziyaretini, EN YENIDEN EN
    ESKIYE dogru sirali dondurur. admin.py bunu oturum/sure hesaplamak
    icin kullanir - HAM veri, hesaplama admin.py tarafinda yapilir."""
    if not kullanici_id:
        return []
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT sayfa, giris_zamani FROM sayfa_ziyaretleri "
            "WHERE user_id = ? ORDER BY giris_zamani DESC LIMIT ?",
            (kullanici_id, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[db] kullanici_ziyaret_gecmisi hata: {e}", file=sys.stderr)
        return []


def tum_onaylanan_etkileri_sifirla(kullanici_id) -> int:
    """v2.0.7.201 (Bahri'nin talebi, 26 Ağustos 2026 — Admin Panel'e
    "Varsayılan Skor" düğmesi).

    v2.0.7.203 (Bahri'nin talebi — kişiye özel skor): ARTIK
    `kullanici_id` ZORUNLU - SADECE BU KULLANICININ onayladığı
    kararlar siliniyor (`kullanici_tespit_karari`'dan) - diğer
    kullanıcıların kendi onayları HİÇ ETKİLENMİYOR. Silinen kararlar
    o tespiti "henüz karar verilmemiş" durumuna döndürür - kullanıcı
    isterse pop-up'ta tekrar görüp yeniden karar verebilir. Paylaşımlı
    `beklenti_otomatik_tespit` kaydı HİÇ DEĞİŞMİYOR/SİLİNMİYOR - sadece
    bu kullanıcının o kayıtlara verdiği karar kaldırılıyor.
    Etkilenen satır sayısını döner (0 = zaten etkin bir şey yoktu)."""
    if not kullanici_id:
        return -1
    try:
        conn = get_conn()
        cur = conn.execute(
            "DELETE FROM kullanici_tespit_karari "
            "WHERE kullanici_id=? AND karar='onaylandi'",
            (kullanici_id,))
        etkilenen = cur.rowcount if hasattr(cur, "rowcount") else None
        conn.commit()
        conn.close()
        return int(etkilenen or 0)
    except Exception as e:
        print(f"[db] tum_onaylanan_etkileri_sifirla hata: {e}", file=sys.stderr)
        return -1


if __name__ == "__main__":
    init_db()
