"""
TrendSurf Optima - Uyarı Ayarları Modülü (alert_settings.py)
v2.0: Kar Realizasyonu Uyarı Sistemi - kullanıcı bazlı tercih CRUD

Bu modül, alert_settings tablosundan kullanıcı tercihlerini okur/yazar.
db.py'deki get_conn() bağlantısını kullanır (Supabase PostgreSQL).

Pattern: email_settings ile aynı (load/save UPSERT mantığı).
"""
import sys
from db import get_conn


# Varsayılan değerler (kullanıcı henüz ayar kaydetmemişse veya DB'de kayıt yoksa)
DEFAULTS = {
    "threshold_pct":      3.0,
    "kar_only":           True,
    "check_interval_min": 30,
    "alert_mode":         "peak_break",          # peak_break | once | hourly
    "emir_formul":        "peak_minus_threshold", # peak_minus_threshold | current_price | info_only
    "enabled":            True,
}

# Seçenek listeleri (UI dropdown'larında kullanılacak)
THRESHOLD_OPTIONS  = [2.0, 3.0, 5.0]  # özel değer için ayrı slider
INTERVAL_OPTIONS   = [15, 30, 60]
ALERT_MODES        = {
    "peak_break": "Peak kırıldıkça (yeni peak sonrası tekrar uyar)",
    "once":       "Bir kez gönder ve sus",
    "hourly":     "Saatte bir tekrarla",
}
EMIR_FORMULS = {
    "peak_minus_threshold": "Peak × (1 − threshold) — örn peak 100, %3 -> tavsiye 97",
    "current_price":        "Şu anki fiyat (anlık satış emri)",
    "info_only":            "Sadece bilgi ver (tavsiye fiyat yok)",
}


def load_alert_settings(user_id: int) -> dict:
    """Kullanıcının alert ayarlarını DB'den çek.

    Eğer DB'de kayıt yoksa DEFAULTS döner (sistem default ayarlarla başlar).
    Hata olursa loglar ve DEFAULTS döner (sayfa açık kalsın, kullanıcı
    ayarları kendisi kaydeder).
    """
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT threshold_pct, kar_only, check_interval_min, "
            "       alert_mode, emir_formul, enabled "
            "FROM alert_settings WHERE user_id = %s",
            (user_id,)
        )
        row = cur.fetchone()
        cur.close()
        if row:
            return {
                "threshold_pct":      float(row[0]) if row[0] is not None else DEFAULTS["threshold_pct"],
                "kar_only":           bool(row[1])  if row[1] is not None else DEFAULTS["kar_only"],
                "check_interval_min": int(row[2])   if row[2] is not None else DEFAULTS["check_interval_min"],
                "alert_mode":         str(row[3])   if row[3]              else DEFAULTS["alert_mode"],
                "emir_formul":        str(row[4])   if row[4]              else DEFAULTS["emir_formul"],
                "enabled":            bool(row[5])  if row[5] is not None else DEFAULTS["enabled"],
            }
        # Kayıt yoksa default
        return dict(DEFAULTS)
    except Exception as e:
        sys.stderr.write(f"[alert_settings] load hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return dict(DEFAULTS)


def save_alert_settings(user_id: int, settings: dict) -> bool:
    """Kullanıcının alert ayarlarını DB'ye yaz (UPSERT).

    settings dict'inde eksik anahtarlar DEFAULTS'tan tamamlanır.
    """
    try:
        # Eksik anahtarları default ile doldur
        merged = dict(DEFAULTS)
        merged.update(settings)

        # Tip ve sınır validasyonu
        thr = float(merged["threshold_pct"])
        if thr < 0.5: thr = 0.5    # mantıklı alt sınır
        if thr > 20.0: thr = 20.0  # mantıklı üst sınır

        intv = int(merged["check_interval_min"])
        if intv not in (15, 30, 60):
            intv = 30  # geçersiz değer gelirse default

        mode = str(merged["alert_mode"])
        if mode not in ALERT_MODES:
            mode = "peak_break"

        formul = str(merged["emir_formul"])
        if formul not in EMIR_FORMULS:
            formul = "peak_minus_threshold"

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO alert_settings "
            "  (user_id, threshold_pct, kar_only, check_interval_min, "
            "   alert_mode, emir_formul, enabled, son_guncelleme) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, NOW()) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "  threshold_pct      = EXCLUDED.threshold_pct, "
            "  kar_only           = EXCLUDED.kar_only, "
            "  check_interval_min = EXCLUDED.check_interval_min, "
            "  alert_mode         = EXCLUDED.alert_mode, "
            "  emir_formul        = EXCLUDED.emir_formul, "
            "  enabled            = EXCLUDED.enabled, "
            "  son_guncelleme     = NOW()",
            (user_id, thr, bool(merged["kar_only"]), intv,
             mode, formul, bool(merged["enabled"]))
        )
        conn.commit()
        cur.close()
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


def get_enabled_users() -> list[int]:
    """Uyarı sistemi aktif olan tüm kullanıcıların user_id listesini döner.

    GitHub Actions workflow başlangıcında çağrılır - hangi kullanıcılar için
    peak check yapılacağını belirler.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM alert_settings WHERE enabled = TRUE"
        )
        rows = cur.fetchall()
        cur.close()
        return [int(r[0]) for r in rows]
    except Exception as e:
        sys.stderr.write(f"[alert_settings] get_enabled_users hatasi: {e}\n")
        sys.stderr.flush()
        return []
