"""
TrendSurf Optima - Standalone Email Sender (GitHub Actions)
v1.9.0: BIST live refresh + Supabase portfoy okuma + user_email filtre.

Onceki davranis (v1.7.1): portfolio=[] hardcoded -> e-postada Portfoy bolumu
                          her zaman bos cikiyordu.

Yeni davranis (v1.9.0):  Supabase'den ADMIN_EMAIL kullanicisinin portfoyu
                          okunur (db.py wrapper SUPABASE_DB_URL env var'i ile
                          PostgreSQL'e baglanir).
                          Ayrica BIST hisselerine de borsapy ile canli refresh.

Gerekli env degiskenleri (GitHub Secrets):
  EMAIL_ADDRESS     - alici e-posta
  SMTP_USER         - SMTP kullanici (Gmail adresi)
  SMTP_PASS         - Gmail App Password
  SUPABASE_DB_URL   - Postgres baglanti string'i (Supabase pooler)
  ADMIN_EMAIL       - Portfoyu okunacak kullanici e-postasi
Opsiyonel:
  REPORT_BUDGET     - default 20000
  REPORT_RISK       - default "Orta"
  REPORT_MAX_ASSETS - default 10
"""

import os
import sys
import pandas as pd

# ----------------------------------------------------------------------------
# SMTP konfigurasyonu
# ----------------------------------------------------------------------------
cfg = {
    "address":   os.environ.get("EMAIL_ADDRESS", ""),
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": os.environ.get("SMTP_USER", ""),
    "smtp_pass": os.environ.get("SMTP_PASS", ""),
}

if not cfg["smtp_user"] or not cfg["smtp_pass"]:
    print("HATA: SMTP_USER ve SMTP_PASS env degiskenleri eksik")
    sys.exit(1)

# Admin e-postasi (Supabase'de hangi kullanicinin portfoyu okunacak)
admin_email = os.environ.get("ADMIN_EMAIL", "").strip()
if not admin_email:
    print("UYARI: ADMIN_EMAIL env yok - portfoy bolumu bos kalacak")

# ----------------------------------------------------------------------------
# v1.9.8 - Saat kontrol mekanizmasi
#
# GitHub Actions cron her saat tetiklenir. Bu script DB'den kullanicinin
# kayitli gonderim saatlerini okur ve su anki TRT saati eslesirse mail gonderir,
# eslesmezse hemen cikar. Boylece kullanici saatleri (Supabase email_settings
# tablosundan) kalici ve cron'dan bagimsiz.
#
# Saat eslestirme: saatin "saat" kismi (HH) eslesirse yeterli, dakika gozardi
# edilir. Cron tam saat basinda calistigi icin (0 * * * *), dakika her zaman ~5.
# Boylece "09:00" ayarli saat icin UTC 06:00'da gelen cron mail gonderir.
# ----------------------------------------------------------------------------
def _ensure_send_log_table(conn):
    """v2.0.3: email_send_log tablosu yoksa olustur (idempotent).
    Duplicate guard icin gerekli."""
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_send_log (
                user_id INTEGER NOT NULL,
                send_date DATE NOT NULL,
                send_hour INTEGER NOT NULL,
                sent_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (user_id, send_date, send_hour)
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"[send_log] CREATE TABLE hatasi (yok sayilir): {e}")


def _already_sent_today(conn, user_id, send_date, send_hour):
    """v2.0.3: Bugun bu saatte bu user'a mail gonderildi mi?"""
    try:
        row = conn.execute(
            "SELECT 1 FROM email_send_log WHERE user_id=? AND send_date=? AND send_hour=?",
            (user_id, send_date, send_hour)
        ).fetchone()
        return row is not None
    except Exception as e:
        print(f"[send_log] SELECT hatasi (yok sayilir): {e}")
        return False


def _mark_sent_today(conn, user_id, send_date, send_hour):
    """v2.0.3: Mail basariyla gonderildikten sonra log'a kayit at."""
    try:
        conn.execute(
            "INSERT INTO email_send_log (user_id, send_date, send_hour) "
            "VALUES (?,?,?) ON CONFLICT DO NOTHING",
            (user_id, send_date, send_hour)
        )
        conn.commit()
        print(f"[send_log] kayit: user_id={user_id} tarih={send_date} saat={send_hour:02d}")
    except Exception as e:
        print(f"[send_log] INSERT hatasi: {e}")


def _check_user_send_time():
    """DB'den kullanicinin gonderim saatlerini oku + duplicate guard.

    v2.0.3: Yedekli cron tetiklemeleriyle (her saat 4 kez) duplicate mail
    riskini onlemek icin email_send_log tablosunu kullanir.

    Returns:
        dict | None: None = gonderme. dict = {user_id, today_date, now_hour, _bypass}
                     _bypass=True ise ALWAYS_SEND modu (duplicate guard atlanir).
    """
    # ALWAYS_SEND env'i set ise bypass (test ve manuel trigger icin)
    if os.environ.get("ALWAYS_SEND", "").lower() in ("1", "true", "yes"):
        print("[time-check] ALWAYS_SEND aktif - saat ve duplicate kontrol atlandi")
        return {"user_id": None, "today_date": None, "now_hour": None, "_bypass": True}

    if not admin_email:
        print("[time-check] admin_email yok - mail atlandi")
        return None

    try:
        import datetime as dt
        try:
            from zoneinfo import ZoneInfo
            now_tr = dt.datetime.now(ZoneInfo("Europe/Istanbul"))
        except Exception:
            now_tr = dt.datetime.utcnow() + dt.timedelta(hours=3)
        now_hour = now_tr.hour
        today_date = now_tr.date()

        # DB'den kullanicinin saatlerini al
        from db import get_conn
        conn = get_conn()

        # v2.0.3: Bootstrap - email_send_log tablosu yoksa olustur
        _ensure_send_log_table(conn)

        # Once admin_email ile user_id al
        row_u = conn.execute(
            "SELECT id FROM users WHERE LOWER(email)=LOWER(?)",
            (admin_email,)
        ).fetchone()
        if not row_u:
            print(f"[time-check] users tablosunda '{admin_email}' yok - mail atlandi")
            return None
        user_id = row_u[0]
        # email_settings'ten saatleri al
        row_es = conn.execute(
            "SELECT gonderim_saati_1, gonderim_saati_2 FROM email_settings WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if not row_es:
            saatler = ["09:00", "12:00"]
            print(f"[time-check] email_settings'te kayit yok, default kullanildi: {saatler}")
        else:
            saatler = [str(row_es[0]), str(row_es[1])]
            print(f"[time-check] user_id={user_id} saatleri: {saatler}")

        # Su anki saat (HH) saatlerden birine esit mi?
        target_hours = set()
        for s in saatler:
            try:
                hh = int(str(s).split(":")[0])
                target_hours.add(hh)
            except Exception:
                continue
        print(f"[time-check] TRT saat={now_hour:02d}:{now_tr.minute:02d}, hedef saatler={sorted(target_hours)}")

        if now_hour not in target_hours:
            print(f"[time-check] eslesme yok -> sessizce cikis")
            return None

        # v2.0.3: Duplicate guard - bugun bu saatte zaten gonderdik mi?
        if _already_sent_today(conn, user_id, today_date, now_hour):
            print(f"[duplicate-guard] user_id={user_id} icin bugun ({today_date}) saat {now_hour:02d}'de zaten mail gonderildi -> atlandi")
            return None

        print(f"[time-check] EŞLEŞME -> mail gonderiliyor (ilk defa bugun bu saatte)")
        return {"user_id": user_id, "today_date": today_date, "now_hour": now_hour, "_bypass": False}

    except Exception as e:
        print(f"[time-check] HATA (default ile devam et): {e}")
        # Hata durumunda guvenli secim: gonderme
        return None

# v2.0.3 - Saat kontrolu + duplicate guard
_send_ctx = _check_user_send_time()
if _send_ctx is None:
    print("[done] Bu saatte gonderim yok (veya bugun zaten gonderildi) - cikiliyor")
    sys.exit(0)

# ----------------------------------------------------------------------------
# 1. CSV'den taban veri evrenini oku
# ----------------------------------------------------------------------------
try:
    df_uni = pd.read_csv("optimized_universe.csv")
    print(f"[1/5] CSV yuklendi: {len(df_uni)} satir")
except FileNotFoundError:
    print("[1/5] UYARI: optimized_universe.csv yok - bos DataFrame ile devam")
    df_uni = pd.DataFrame()

# ----------------------------------------------------------------------------
# 2. Streamlit Cloud ile birebir veri pipeline'i (live_data.py)
#    Hata olursa sessizce devam; e-posta yine de gonderilir
# ----------------------------------------------------------------------------
try:
    from live_data import (
        filter_universe,
        rename_existing_maden,
        extend_maden_universe,
        refresh_fx_maden_kripto,
        refresh_bist,
        BORSAPY_OK,
    )
    n0 = len(df_uni)

    df_uni = filter_universe(df_uni)
    df_uni = rename_existing_maden(df_uni)
    n1 = len(df_uni)

    if BORSAPY_OK:
        df_uni = extend_maden_universe(df_uni)
        n2 = len(df_uni)
        df_uni = refresh_fx_maden_kripto(df_uni)
        df_uni = refresh_bist(df_uni)
        print(f"[2/5] live_data: {n0} -> filter -> {n1} -> extend -> {n2} -> overlay+BIST (borsapy aktif)")
    else:
        print(f"[2/5] UYARI: borsapy yok, sadece filter+rename uygulandi ({n1} satir, CSV verisi kalir)")

except ImportError as e:
    print(f"[2/5] HATA: live_data import edilemedi ({e}) - CSV'yi oldugu gibi kullaniyoruz")
except Exception as e:
    print(f"[2/5] HATA: live_data hatasi (yok sayilir): {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# ----------------------------------------------------------------------------
# 3. Veri saglik kontrolu
# ----------------------------------------------------------------------------
if df_uni.empty:
    print("[3/5] KRITIK: df_uni bos - e-posta icerigi bos olacak ama yine de gonderiyoruz")
else:
    print(f"[3/5] Veri hazir: {len(df_uni)} satir")
    if "Kategori" in df_uni.columns:
        for cat in ["BIST", "TEFAS", "DOVIZ", "MADEN", "KRIPTO"]:
            n = (df_uni["Kategori"] == cat).sum()
            print(f"        {cat:6}: {n} satir")

# ----------------------------------------------------------------------------
# 4. Rapor parametrelerini env'den al (default: 20000 TL, Orta risk, 10 varlik)
# ----------------------------------------------------------------------------
try:
    budget = float(os.environ.get("REPORT_BUDGET", "20000"))
    if budget <= 0:
        budget = 20000.0
except (TypeError, ValueError):
    budget = 20000.0

risk = os.environ.get("REPORT_RISK", "Orta")
if risk not in ("Çok Düşük", "Düşük", "Orta", "Yüksek", "Çok Yüksek"):
    risk = "Orta"

try:
    max_assets = int(os.environ.get("REPORT_MAX_ASSETS", "10"))
    if max_assets <= 0:
        max_assets = 10
except (TypeError, ValueError):
    max_assets = 10

print(f"[4/5] Rapor parametreleri: butce={budget:.0f} TL, risk={risk}, "
      f"max_varlik={max_assets}, admin_email={admin_email or '<bos>'}")

# ----------------------------------------------------------------------------
# 5. E-posta gonder (mevcut emailer.send_report kullanir)
#    portfolio=None + user_email -> Supabase'den o kullanicinin portfoyu cekilir
# ----------------------------------------------------------------------------
from emailer import send_report
result = send_report(
    df_uni=df_uni,
    portfolio=None,           # None -> user_email ile DB'den oku
    budget=budget,
    risk=risk,
    max_assets=max_assets,
    cfg=cfg,
    user_email=admin_email,   # None/bos ise portfoy bos kalir
)
print(f"[5/5] Sonuc: {result}")

# v2.0.3 - Mail basariyla gonderildikten sonra duplicate guard'a kayit at
if _send_ctx and not _send_ctx.get("_bypass"):
    try:
        from db import get_conn
        _conn_log = get_conn()
        _mark_sent_today(
            _conn_log,
            _send_ctx["user_id"],
            _send_ctx["today_date"],
            _send_ctx["now_hour"],
        )
    except Exception as e:
        print(f"[send_log] mark_sent hata (yok sayilir): {e}")
