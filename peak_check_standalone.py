"""
TrendSurf Optima - Peak Check Standalone (GitHub Actions)
v2.0 Asama 4: Otomatik peak/threshold kontrol + uyari mail gonderim

Bu script GitHub Actions cron tarafindan her 15 dakikada bir calistirilir.
1) Universe yukler (CSV + live_data overlay + BIST canli refresh)
2) alert_settings.get_enabled_users() ile aktif kullanicilari alir
3) Her kullanici icin:
   - check_interval_min'e gore "su an kontrol zamani mi?" karar
   - Hafta sonu kontrolu (BIST/TEFAS/DOVIZ/MADEN sabit, kripto 7/24 aktif)
   - evaluate_user_alerts cagrir
   - alerts_pending varsa send_peak_alert ile mail gonder
   - mark_alert_sent cagrir (mail icinde otomatik)

Multi-user: Her kullanicinin uyarisi sadece KENDI e-postasina gider
(users.email kolonundan). Bahri'nin portfoy uyarisi Serdar'a gitmez.

Gerekli env degiskenleri (GitHub Secrets):
  SMTP_USER         - SMTP kullanici (Gmail adresi)
  SMTP_PASS         - Gmail App Password
  SUPABASE_DB_URL   - Postgres baglanti string'i (Supabase pooler)

Opsiyonel:
  PEAK_CHECK_FORCE  - "true" ise check_interval_min/hafta sonu kontrolleri
                      atlanir, tum aktif kullanicilar icin kontrol yapilir
                      (manual test icin)
"""
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta

import pandas as pd


# ----------------------------------------------------------------------------
# Env vars kontrol
# ----------------------------------------------------------------------------
if not os.environ.get("SMTP_USER") or not os.environ.get("SMTP_PASS"):
    print("HATA: SMTP_USER ve SMTP_PASS env degiskenleri eksik")
    sys.exit(1)

if not os.environ.get("SUPABASE_DB_URL"):
    print("HATA: SUPABASE_DB_URL env degiskeni eksik")
    sys.exit(1)

FORCE_MODE = os.environ.get("PEAK_CHECK_FORCE", "").lower() in ("true", "1", "yes")
if FORCE_MODE:
    print("[force] PEAK_CHECK_FORCE aktif - interval/weekend kontrolleri atlanacak")


# ----------------------------------------------------------------------------
# 1. Universe (CSV + live_data overlay + BIST canli refresh)
# ----------------------------------------------------------------------------
try:
    df_uni = pd.read_csv("optimized_universe.csv")
    print(f"[1/4] CSV yuklendi: {len(df_uni)} satir")
except FileNotFoundError:
    print("[1/4] UYARI: optimized_universe.csv yok - bos DataFrame ile devam")
    df_uni = pd.DataFrame()

try:
    from live_data import (
        filter_universe,
        rename_existing_maden,
        extend_maden_universe,
        refresh_fx_maden_kripto,
        refresh_bist_selective,
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
        # v2.0.2 optimizasyon: BIST icin refresh_bist (770 hisse, 17 dk!)
        # cagrisini KALDIRDIK. Asagidaki "BIST selective refresh" bolumunde
        # sadece aktif kullanicilarin portfoyundeki BIST hisseleri canli
        # yenilenecek (genellikle 5-15 hisse, 1-3 saniye).
        print(f"[2/4] live_data: {n0} -> filter -> {n1} -> extend -> {n2} -> overlay (borsapy aktif, BIST selective sonra)")
    else:
        print(f"[2/4] UYARI: borsapy yok, sadece filter+rename uygulandi ({n1} satir)")
except ImportError as e:
    print(f"[2/4] HATA: live_data import edilemedi ({e}) - CSV'yi oldugu gibi kullaniyoruz")
    refresh_bist_selective = None
except Exception as e:
    print(f"[2/4] HATA: live_data hatasi (yok sayilir): {type(e).__name__}: {e}")
    traceback.print_exc()
    refresh_bist_selective = None

if df_uni.empty:
    print("[done] df_uni bos - kontrol yapilamiyor, cikiliyor")
    sys.exit(0)


# ----------------------------------------------------------------------------
# 2. Aktif kullanicilar
# ----------------------------------------------------------------------------
try:
    from alert_settings import get_enabled_users, load_alert_settings
    user_ids = get_enabled_users()
    print(f"[3/4] Aktif kullanici sayisi: {len(user_ids)}")
except Exception as e:
    print(f"[3/4] HATA: get_enabled_users hatasi: {e}")
    traceback.print_exc()
    sys.exit(1)

if not user_ids:
    print("[done] Aktif kullanici yok - cikiliyor")
    sys.exit(0)


# ----------------------------------------------------------------------------
# 2.5. BIST SELECTIVE REFRESH (v2.0.2 optimizasyon)
# ----------------------------------------------------------------------------
# Eski mantik: refresh_bist tum 770 BIST hisselerini cekiyordu -> 17 dakika!
# Yeni mantik: Sadece aktif kullanicilarin portfoyundeki BIST hisselerini
# canli refresh et. Genellikle 5-15 ticker -> 1-3 saniye.
#
# Buradan onceki [2/4] adiminda refresh_bist_selective import edildi
# (basarisizsa None set edildi).
if refresh_bist_selective is not None and not df_uni.empty:
    try:
        from db import get_conn
        conn = get_conn()
        placeholders = ",".join("?" * len(user_ids))
        rows = conn.execute(
            f"SELECT DISTINCT ticker FROM portfolio WHERE user_id IN ({placeholders})",
            user_ids
        ).fetchall()
        # Tum portfoy ticker'lari (kategori farketmez)
        all_portfolio_tickers = {str(r[0]).strip() for r in rows if r and r[0]}

        # Sadece BIST kategorisinde olanlarla kesisim
        bist_in_uni = set(
            df_uni[df_uni["Kategori"] == "BIST"]["Ticker"].dropna().astype(str)
        )
        user_bist_tickers = sorted(all_portfolio_tickers & bist_in_uni)

        if user_bist_tickers:
            print(f"[2.5/4] BIST selective refresh: {len(user_bist_tickers)} ticker -> {user_bist_tickers[:8]}{'...' if len(user_bist_tickers) > 8 else ''}")
            df_uni = refresh_bist_selective(df_uni, user_bist_tickers)
        else:
            print(f"[2.5/4] BIST selective refresh: kullanici portfoylerinde BIST ticker yok, atlandi")
    except Exception as e:
        print(f"[2.5/4] HATA: BIST selective refresh basarisiz (yok sayilir): {type(e).__name__}: {e}")
        traceback.print_exc()


# ----------------------------------------------------------------------------
# 3. Saat ve hafta sonu kontrolu (her kullanici icin)
# ----------------------------------------------------------------------------
def _should_check_now(check_interval_min: int, now_utc: datetime) -> bool:
    """check_interval_min'e gore su an kontrol zamani mi?

    Cron her 15 dk calisir (UTC dakikalari 0/15/30/45 civarinda).
    GitHub Actions gecikme ~5-10 dk olabilir, tolerans gerekli.

    interval=15 -> her tetiklemede calis
    interval=30 -> dakika 0-9 veya 30-39 araliginda
    interval=60 -> dakika 0-9 araliginda
    """
    if FORCE_MODE:
        return True
    m = now_utc.minute
    if check_interval_min == 15:
        return True
    if check_interval_min == 30:
        return (m % 30) < 10
    if check_interval_min == 60:
        return m < 10
    # bilinmeyen deger - guvenli secim: calistir
    return True


def _is_weekend(now_utc: datetime) -> bool:
    """TRT haftasi pazartesi=0, pazar=6. Cumartesi/pazar -> weekend."""
    # TRT = UTC + 3
    now_trt = now_utc + timedelta(hours=3)
    return now_trt.weekday() >= 5  # 5=Saturday, 6=Sunday


now_utc = datetime.now(timezone.utc)
is_weekend = _is_weekend(now_utc)
print(f"[time] UTC: {now_utc.strftime('%Y-%m-%d %H:%M')} | "
      f"TRT: {(now_utc + timedelta(hours=3)).strftime('%H:%M')} | "
      f"weekend: {is_weekend}")


# ----------------------------------------------------------------------------
# 4. Her kullanici icin evaluate + mail
# ----------------------------------------------------------------------------
from peak_tracker import evaluate_user_alerts
from peak_alert_emailer import send_peak_alert

total_evaluated = 0
total_alerts    = 0
total_mailed    = 0
total_skipped_interval  = 0
total_skipped_weekend   = 0

for uid in user_ids:
    try:
        settings = load_alert_settings(uid)
        interval = int(settings.get("check_interval_min", 30))

        # Saat kontrolu
        if not _should_check_now(interval, now_utc):
            total_skipped_interval += 1
            print(f"[user={uid}] atlandi (interval={interval}min, su an UTC dakika={now_utc.minute})")
            continue

        # Hafta sonu: tum kullanicilar icin evaluate calistir;
        # ancak hafta sonuysa sadece KRIPTO uyarilari mail edilir
        # (BIST/TEFAS/DOVIZ/MADEN piyasalari kapali, peak hareketi olmaz).
        result = evaluate_user_alerts(uid, df_uni)
        total_evaluated += 1

        alerts_pending = result.get("alerts_pending", [])

        # Hafta sonu filtre (sadece kripto)
        if is_weekend and not FORCE_MODE:
            before = len(alerts_pending)
            alerts_pending = [a for a in alerts_pending if a.get("asset_type") == "KRIPTO"]
            if before > 0 and not alerts_pending:
                total_skipped_weekend += 1
                print(f"[user={uid}] hafta sonu - kripto disi {before} uyari atlandi")

        total_alerts += len(alerts_pending)

        if alerts_pending:
            mail_res = send_peak_alert(uid, alerts_pending, settings)
            if mail_res.get("sent"):
                total_mailed += 1
                print(f"[user={uid}] mail gonderildi: {mail_res.get('to')} - "
                      f"{mail_res.get('count')} uyari, "
                      f"{mail_res.get('marked', 0)} ticker flag set edildi")
            else:
                print(f"[user={uid}] mail gonderilemedi: {mail_res.get('reason')}")
        else:
            print(f"[user={uid}] uyari yok (evaluate OK, "
                  f"updated_peaks={len(result.get('updated_peaks', []))}, "
                  f"skipped={len(result.get('skipped', []))})")

    except Exception as e:
        print(f"[user={uid}] HATA: {type(e).__name__}: {e}")
        traceback.print_exc()


# ----------------------------------------------------------------------------
# Ozet
# ----------------------------------------------------------------------------
print(f"\n[done] Ozet:")
print(f"  Toplam aktif kullanici: {len(user_ids)}")
print(f"  Saat kontrolu nedeniyle atlandi: {total_skipped_interval}")
print(f"  Evaluate yapildi: {total_evaluated}")
print(f"  Toplam uyari: {total_alerts}")
print(f"  Mail gonderilen kullanici: {total_mailed}")
print(f"  Hafta sonu filtresi: {total_skipped_weekend}")
