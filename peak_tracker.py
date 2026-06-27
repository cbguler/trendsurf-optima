"""
TrendSurf Optima - Peak Tracker Modulu (peak_tracker.py)
v2.0 Asama 3a: Kar Realizasyonu Uyari Sistemi - peak/threshold mantigi

Bu modul iki ana islev yapar:
1) Her ticker icin maximum gorulen fiyati (peak) takip eder
2) Peak'ten threshold kadar dusus oldugunda uyari tetikleyecek tickerlari listeler

Mail GONDERMEZ - sadece "uyari bekleyen" listesi doner (Asama 3b mail isini yapar).

db.py'deki _CompatConn arayuzunu kullanir: conn.execute(sql, ?), conn.commit().
"""
import sys
from datetime import datetime, timedelta
from db import get_conn
from alert_settings import load_alert_settings


def _calc_tavsiye_fiyat(peak: float, current: float,
                         threshold_pct: float, formul: str) -> float:
    """Uyari mailinde gosterilecek tavsiye satis emir fiyati.

    formul:
      - peak_minus_threshold: peak x (1 - threshold/100)
      - current_price: anlik fiyat
      - info_only: 0 (mailde 'tavsiye yok' yazilir)
    """
    if formul == "peak_minus_threshold":
        return round(peak * (1.0 - threshold_pct / 100.0), 4)
    if formul == "current_price":
        return round(current, 4)
    return 0.0  # info_only


def _load_user_portfolio(user_id: int) -> list:
    """Kullanicinin portfoy satirlarini DB'den cek.

    Returns: [{ticker, asset_type, quantity, avg_cost, unit_type}, ...]
    """
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT ticker, asset_type, quantity, avg_cost, "
            "       COALESCE(unit_type,'Adet') as unit_type "
            "FROM portfolio WHERE user_id=?",
            (user_id,)
        ).fetchall()
        return [
            {
                "ticker":     str(r[0]),
                "asset_type": str(r[1]),
                "quantity":   float(r[2]),
                "avg_cost":   float(r[3]),
                "unit_type":  str(r[4]) if r[4] else "Adet",
            }
            for r in rows
        ]
    except Exception as e:
        sys.stderr.write(f"[peak_tracker] portfolio okuma hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return []


def _get_peak_record(user_id: int, ticker: str) -> dict:
    """peak_tracker tablosundan tek satirlik kaydi cek. Yoksa None doner."""
    try:
        conn = get_conn()
        row = conn.execute(
            "SELECT peak_price, peak_time, last_alert_price, last_alert_time, "
            "       alert_sent_for_current_peak "
            "FROM peak_tracker WHERE user_id=? AND ticker=?",
            (user_id, ticker)
        ).fetchone()
        if not row:
            return None
        return {
            "peak_price":                    float(row[0]) if row[0] is not None else None,
            "peak_time":                     row[1],
            "last_alert_price":              float(row[2]) if row[2] is not None else None,
            "last_alert_time":               row[3],
            "alert_sent_for_current_peak":   bool(row[4]) if row[4] is not None else False,
        }
    except Exception as e:
        sys.stderr.write(f"[peak_tracker] peak okuma hatasi ({ticker}): {e}\n")
        sys.stderr.flush()
        return None


def update_peak_for_user(user_id: int, ticker: str, current_price: float) -> str:
    """Tek bir ticker icin peak'i guncelle/olustur.

    Returns:
      "new_record"    -> ilk kez kaydedildi (current = peak)
      "new_peak"      -> mevcut peak'i kirdi, peak guncellendi, alert flag reset
      "no_change"     -> peak'in altinda, hicbir sey yapilmadi
      "error"         -> hata olustu (loglara bakin)
    """
    try:
        if current_price is None or current_price <= 0:
            return "error"

        existing = _get_peak_record(user_id, ticker)
        conn = get_conn()

        if existing is None:
            # Ilk kayit: current = peak, alert_sent_for_current_peak = FALSE
            conn.execute(
                "INSERT INTO peak_tracker "
                "  (user_id, ticker, peak_price, peak_time, "
                "   alert_sent_for_current_peak) "
                "VALUES (?, ?, ?, NOW(), FALSE)",
                (user_id, ticker, float(current_price))
            )
            try: conn.commit()
            except Exception: pass
            return "new_record"

        # Mevcut peak ile karsilastir
        if current_price > existing["peak_price"]:
            # Yeni peak: kaydi guncelle, alert flag'i reset et
            conn.execute(
                "UPDATE peak_tracker SET "
                "  peak_price = ?, peak_time = NOW(), "
                "  alert_sent_for_current_peak = FALSE "
                "WHERE user_id=? AND ticker=?",
                (float(current_price), user_id, ticker)
            )
            try: conn.commit()
            except Exception: pass
            return "new_peak"

        # Peak'in altinda veya esit - hicbir sey yapma
        return "no_change"
    except Exception as e:
        sys.stderr.write(f"[peak_tracker] update_peak hatasi ({ticker}): {e}\n")
        sys.stderr.flush()
        return "error"


def _should_trigger_alert(peak_rec: dict, current_price: float,
                          avg_cost: float, settings: dict) -> bool:
    """Bu ticker icin uyari tetiklenmeli mi karari.

    Sirayla:
    1) Dusus thresholdu asti mi?
    2) kar_only ise mevcut > alish mi?
    3) alert_mode bu uyariya izin veriyor mu?
    """
    if peak_rec is None or peak_rec["peak_price"] is None:
        return False

    peak  = peak_rec["peak_price"]
    if peak <= 0:
        return False

    # 1) Dusus yuzdesi
    drop_pct = (peak - current_price) / peak * 100.0
    if drop_pct < settings["threshold_pct"]:
        return False  # threshold asilmamis

    # 2) Kar kosulu
    if settings["kar_only"] and current_price <= avg_cost:
        return False  # zararda iken uyarmiyor

    # 3) Alert mode mantigi
    mode = settings["alert_mode"]
    if mode == "peak_break":
        # Yeni peak gelirse flag reset olur, tekrar tetikleyebilir
        return not peak_rec["alert_sent_for_current_peak"]
    if mode == "once":
        # Hic uyari gonderilmemisse tetikle, sonra hic tekrarlama
        return peak_rec["last_alert_time"] is None
    if mode == "hourly":
        # Son uyaridan beri 1 saat gectiyse tetikle
        last_t = peak_rec["last_alert_time"]
        if last_t is None:
            return True
        try:
            # last_t TIMESTAMPTZ - psycopg2 datetime objesi olarak doner
            if isinstance(last_t, str):
                last_t = datetime.fromisoformat(last_t.replace("Z", "+00:00"))
            # tz-naive karsilastirma icin both naive yap
            now_n  = datetime.utcnow()
            last_n = last_t.replace(tzinfo=None) if last_t.tzinfo else last_t
            return (now_n - last_n) >= timedelta(hours=1)
        except Exception:
            return True  # parse hatasi olursa varsayilan tetikle

    return False


def evaluate_user_alerts(user_id: int, df_uni) -> dict:
    """Kullanicinin portfoyundeki tum varliklar icin peak update + threshold kontrol.

    df_uni: pandas DataFrame, 'Ticker' ve 'Son_Fiyat' sutunlari olmali.
    (NOT: Sutun adi 'Son_Fiyat' alt cizgi ile - UI'da gosterimde 'Son Fiyat'
    olarak rename edilir ama DataFrame'in ic adi 'Son_Fiyat'.)

    Returns:
      {
        "updated_peaks":  [list of (ticker, peak, status)],
        "alerts_pending": [list of dict - uyari bekleyen tickerlar],
        "skipped":        [list of (ticker, reason)],
      }
    """
    result = {"updated_peaks": [], "alerts_pending": [], "skipped": []}

    try:
        # Kullanicinin ayarlari
        settings = load_alert_settings(user_id)
        if not settings.get("enabled", True):
            result["skipped"].append(("(tum portfoy)", "uyari sistemi pasif"))
            return result

        # Portfoy
        portfolio = _load_user_portfolio(user_id)
        if not portfolio:
            result["skipped"].append(("(tum portfoy)", "portfoy bos"))
            return result

        # Universe -> ticker:fiyat dict (hizli lookup)
        # Sutun adi 'Son_Fiyat' (alt cizgi), 'Son Fiyat' (bosluk) DEGIL.
        price_map = {}
        if df_uni is not None and not df_uni.empty:
            # Hem 'Son_Fiyat' hem 'Son Fiyat' destegi (UI'da rename'li tablo da
            # bu fonksiyona gelebilir)
            price_col = None
            for cand in ("Son_Fiyat", "Son Fiyat", "Fiyat"):
                if cand in df_uni.columns:
                    price_col = cand
                    break
            if price_col:
                for _, row in df_uni.iterrows():
                    t = str(row.get("Ticker", ""))
                    p = row.get(price_col)
                    if t and p is not None:
                        try:
                            pf = float(p)
                            if pf > 0:
                                price_map[t] = pf
                        except (TypeError, ValueError):
                            pass

        # Her ticker icin
        for pos in portfolio:
            ticker     = pos["ticker"]
            asset_type = pos["asset_type"]
            quantity   = pos["quantity"]
            avg_cost   = pos["avg_cost"]
            unit_type  = pos["unit_type"]

            current = price_map.get(ticker)
            if current is None or current <= 0:
                result["skipped"].append((ticker, "canli fiyat yok"))
                continue

            # 1) Peak'i guncelle
            status = update_peak_for_user(user_id, ticker, current)
            if status in ("new_peak", "new_record"):
                result["updated_peaks"].append((ticker, current, status))

            # 2) Threshold kontrol
            peak_rec = _get_peak_record(user_id, ticker)
            if peak_rec and _should_trigger_alert(peak_rec, current, avg_cost, settings):
                peak  = peak_rec["peak_price"]
                drop  = (peak - current) / peak * 100.0
                tavsi = _calc_tavsiye_fiyat(peak, current,
                                             settings["threshold_pct"],
                                             settings["emir_formul"])
                result["alerts_pending"].append({
                    "ticker":        ticker,
                    "asset_type":    asset_type,
                    "alish_fiyat":   avg_cost,
                    "miktar":        quantity,
                    "unit_type":     unit_type,
                    "peak_price":    peak,
                    "peak_time":     peak_rec["peak_time"],
                    "current_price": current,
                    "drop_pct":      drop,
                    "tavsiye_fiyat": tavsi,
                    "toplam_deger":  current * quantity,
                })

        sys.stderr.write(
            f"[peak_tracker] evaluate user={user_id} "
            f"updated={len(result['updated_peaks'])} "
            f"pending={len(result['alerts_pending'])} "
            f"skipped={len(result['skipped'])}\n"
        )
        sys.stderr.flush()
        return result
    except Exception as e:
        sys.stderr.write(f"[peak_tracker] evaluate hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return result


def mark_alert_sent(user_id: int, ticker: str, current_price: float) -> bool:
    """Uyari maili basariyla gonderildikten sonra cagrilir.

    last_alert_price, last_alert_time guncellenir; alert_sent_for_current_peak = TRUE.
    """
    try:
        conn = get_conn()
        conn.execute(
            "UPDATE peak_tracker SET "
            "  last_alert_price = ?, last_alert_time = NOW(), "
            "  alert_sent_for_current_peak = TRUE "
            "WHERE user_id=? AND ticker=?",
            (float(current_price), user_id, ticker)
        )
        try: conn.commit()
        except Exception: pass
        return True
    except Exception as e:
        sys.stderr.write(f"[peak_tracker] mark_alert_sent hatasi ({ticker}): {e}\n")
        sys.stderr.flush()
        return False


def get_user_peaks(user_id: int) -> list:
    """Kullanicinin tum peak kayitlarini doner (UI Uyarilar sayfasi icin).

    Returns: [{ticker, peak_price, peak_time, last_alert_price, last_alert_time, ...}]
    """
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT ticker, peak_price, peak_time, last_alert_price, "
            "       last_alert_time, alert_sent_for_current_peak "
            "FROM peak_tracker WHERE user_id=? ORDER BY ticker ASC",
            (user_id,)
        ).fetchall()
        return [
            {
                "ticker":                       str(r[0]),
                "peak_price":                   float(r[1]) if r[1] is not None else None,
                "peak_time":                    r[2],
                "last_alert_price":             float(r[3]) if r[3] is not None else None,
                "last_alert_time":              r[4],
                "alert_sent_for_current_peak":  bool(r[5]) if r[5] is not None else False,
            }
            for r in rows
        ]
    except Exception as e:
        sys.stderr.write(f"[peak_tracker] get_user_peaks hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return []


def reset_peaks_for_user(user_id: int, ticker: str = None) -> bool:
    """Manuel peak sifirlama.

    ticker None ise tum portfoy icin peak silinir, aksi halde sadece o ticker.
    Bir sonraki evaluate_user_alerts cagrisinda yeni peak (current fiyattan) olusur.
    """
    try:
        conn = get_conn()
        if ticker:
            conn.execute(
                "DELETE FROM peak_tracker WHERE user_id=? AND ticker=?",
                (user_id, ticker)
            )
        else:
            conn.execute(
                "DELETE FROM peak_tracker WHERE user_id=?",
                (user_id,)
            )
        try: conn.commit()
        except Exception: pass
        sys.stderr.write(
            f"[peak_tracker] reset user={user_id} "
            f"ticker={ticker if ticker else 'ALL'}\n"
        )
        sys.stderr.flush()
        return True
    except Exception as e:
        sys.stderr.write(f"[peak_tracker] reset hatasi: {e}\n")
        sys.stderr.flush()
        return False
