"""
TrendSurf Optima - Uyari Ayarlari Modulu (alert_settings.py)
v2.0: Kar Realizasyonu Uyari Sistemi - kullanici bazli tercih CRUD

Bu modul, alert_settings tablosundan kullanici tercihlerini okur/yazar.
db.py'deki _CompatConn arayuzunu kullanir (conn.execute, ? placeholder).

Pattern: email_settings ile birebir ayni (load/save UPSERT mantigi).
"""
import sys
from db import get_conn


# Varsayilan degerler (kullanici henuz ayar kaydetmemisse veya DB'de kayit yoksa)
DEFAULTS = {
    "threshold_pct":      3.0,
    "kar_only":           True,
    "check_interval_min": 30,
    "alert_mode":         "peak_break",
    "emir_formul":        "peak_minus_threshold",
    "enabled":            True,
}

# Secenek listeleri (UI dropdown'larinda kullanilacak)
THRESHOLD_OPTIONS  = [2.0, 3.0, 5.0]
INTERVAL_OPTIONS   = [15, 30, 60]
ALERT_MODES = {
    "peak_break": "Peak kirildikca (yeni peak sonrasi tekrar uyar)",
    "once":       "Bir kez gonder ve sus",
    "hourly":     "Saatte bir tekrarla",
}
EMIR_FORMULS = {
    "peak_minus_threshold": "Peak x (1 - threshold) - orn peak 100, %3 olur tavsiye 97",
    "current_price":        "Su anki fiyat (anlik satis emri)",
    "info_only":            "Sadece bilgi ver (tavsiye fiyat yok)",
}


def load_alert_settings(user_id: int) -> dict:
    """Kullanicinin alert ayarlarini DB'den cek.

    DB'de kayit yoksa DEFAULTS doner. Hata olursa loglar ve DEFAULTS doner
    (sayfa acik kalsin, kullanici ayarlari kendisi kaydeder).
    db.py'deki _CompatConn arayuzunu kullanir: conn.execute(sql, params).fetchone()
    """
    try:
        conn = get_conn()
        row = conn.execute(
            "SELECT threshold_pct, kar_only, check_interval_min, "
            "       alert_mode, emir_formul, enabled "
            "FROM alert_settings WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if row:
            return {
                "threshold_pct":      float(row[0]) if row[0] is not None else DEFAULTS["threshold_pct"],
                "kar_only":           bool(row[1])  if row[1] is not None else DEFAULTS["kar_only"],
                "check_interval_min": int(row[2])   if row[2] is not None else DEFAULTS["check_interval_min"],
                "alert_mode":         str(row[3])   if row[3]              else DEFAULTS["alert_mode"],
                "emir_formul":        str(row[4])   if row[4]              else DEFAULTS["emir_formul"],
                "enabled":            bool(row[5])  if row[5] is not None else DEFAULTS["enabled"],
            }
        return dict(DEFAULTS)
    except Exception as e:
        sys.stderr.write(f"[alert_settings] load hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return dict(DEFAULTS)


def save_alert_settings(user_id: int, settings: dict) -> bool:
    """Kullanicinin alert ayarlarini DB'ye yaz (UPSERT).

    settings dict'inde eksik anahtarlar DEFAULTS'tan tamamlanir.
    db.py'deki _CompatConn arayuzunu kullanir: conn.execute(sql, params) + conn.commit().
    """
    try:
        merged = dict(DEFAULTS)
        merged.update(settings)

        thr = float(merged["threshold_pct"])
        if thr < 0.5: thr = 0.5
        if thr > 20.0: thr = 20.0

        intv = int(merged["check_interval_min"])
        if intv not in (15, 30, 60):
            intv = 30

        mode = str(merged["alert_mode"])
        if mode not in ALERT_MODES:
            mode = "peak_break"

        formul = str(merged["emir_formul"])
        if formul not in EMIR_FORMULS:
            formul = "peak_minus_threshold"

        conn = get_conn()
        conn.execute(
            """INSERT INTO alert_settings
                 (user_id, threshold_pct, kar_only, check_interval_min,
                  alert_mode, emir_formul, enabled, son_guncelleme)
               VALUES (?, ?, ?, ?, ?, ?, ?, NOW())
               ON CONFLICT (user_id) DO UPDATE SET
                 threshold_pct      = EXCLUDED.threshold_pct,
                 kar_only           = EXCLUDED.kar_only,
                 check_interval_min = EXCLUDED.check_interval_min,
                 alert_mode         = EXCLUDED.alert_mode,
                 emir_formul        = EXCLUDED.emir_formul,
                 enabled            = EXCLUDED.enabled,
                 son_guncelleme     = NOW()""",
            (user_id, thr, bool(merged["kar_only"]), intv,
             mode, formul, bool(merged["enabled"]))
        )
        try:
            conn.commit()
        except Exception:
            pass

        sys.stderr.write(
            f"[alert_settings] kaydedildi user={user_id} "
            f"thr={thr}% kar_only={merged['kar_only']} "
            f"interval={intv}min mode={mode} formul={formul} "
            f"enabled={merged['enabled']}\n"
        )
        sys.stderr.flush()
        return True
    except Exception as e:
        sys.stderr.write(f"[alert_settings] save hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return False


def get_enabled_users() -> list:
    """Uyari sistemi aktif olan tum kullanicilarin user_id listesini doner.

    GitHub Actions workflow baslangicinda cagrilir.
    """
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT user_id FROM alert_settings WHERE enabled = TRUE"
        ).fetchall()
        return [int(r[0]) for r in rows]
    except Exception as e:
        sys.stderr.write(f"[alert_settings] get_enabled_users hatasi: {e}\n")
        sys.stderr.flush()
        return []
