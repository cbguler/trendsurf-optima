"""
TrendSurf Optima - Peak Tracker Modulu (peak_tracker.py)
v2.0 Asama 3a.3: Kar Realizasyonu Uyari Sistemi - peak/threshold (BATCH)

v2.0 asama 3a.3 - Performans optimizasyonu:
Onceki versiyon (3a.1/3a.2): 14 ticker icin 14 SELECT + 14 INSERT/UPDATE
= 28 ayri DB call. Supabase free tier pooler'da bu 32-77 saniye aldi,
streamlit-autorefresh (60 sn) ile cakisti, session_state yazimi
gerceklesmedi -> UI sonuc gostermedi.

3a.3 cozumu:
- 1 SELECT'le tum peak kayitlari tek sorguda
- 1 batch UPSERT'le tum guncellemeler tek sorguda (PostgreSQL ON CONFLICT WHERE)
Beklenen: 28 call -> 2 call, 30+ sn -> 2-5 sn.

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
    """Kullanicinin portfoy satirlarini DB'den cek (1 SELECT).

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


def _load_user_peaks_map(user_id: int) -> dict:
    """Kullanicinin tum peak kayitlarini TEK SELECT'le cek.

    Returns: {ticker: {peak_price, peak_time, last_alert_price, last_alert_time, ...}}

    Eski 14 ayri _get_peak_record cagrisi yerine 1 SELECT.
    """
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT ticker, peak_price, peak_time, last_alert_price, "
            "       last_alert_time, alert_sent_for_current_peak "
            "FROM peak_tracker WHERE user_id=?",
            (user_id,)
        ).fetchall()
        out = {}
        for r in rows:
            out[str(r[0])] = {
                "peak_price":                    float(r[1]) if r[1] is not None else None,
                "peak_time":                     r[2],
                "last_alert_price":              float(r[3]) if r[3] is not None else None,
                "last_alert_time":               r[4],
                "alert_sent_for_current_peak":   bool(r[5]) if r[5] is not None else False,
            }
        return out
    except Exception as e:
        sys.stderr.write(f"[peak_tracker] peaks map hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return {}


def _consolidate_portfolio_lots(portfolio: list) -> list:
    """Ayni tickera ait birden fazla lotu (alim kaydi) TEK pozisyonda birlestirir.

    KESIN KOK NEDEN BULUNDU VE DUZELTILDI (v2.0.7.224, 1 Eylul 2026,
    Bahri'nin bulgusu): Portfoyde ayni hisseden (ornek: MTG) birden fazla
    lot varsa, konsolidasyon yapilmadan evaluate_user_alerts() ayni
    ticker'i TEK bir batch UPSERT komutunun icine birden fazla kez
    ekliyordu. PostgreSQL bunu reddediyor:
        "ON CONFLICT DO UPDATE command cannot affect row a second time"
    Sonuc: o hissenin peak_price'i veritabaninda HIC GUNCELLENMIYORDU -
    kayitli "zirve" donuk/eski kaliyor, gercek dusus yuzdesi yanlis
    hesaplaniyor, uyari hic tetiklenmiyordu.

    Cozum: ayni ticker'in tum lotlari, per-ticker degerlendirmeden ONCE,
    miktar toplanarak + maliyet miktar-agirlikli ortalama alinarak TEK
    pozisyona indirgenir. asset_type/unit_type ilk lottan alinir (ayni
    ticker icin bunlarin degismedigi varsayilir).
    """
    consolidated = {}
    for pos in portfolio:
        t = pos["ticker"]
        if t not in consolidated:
            consolidated[t] = {
                "ticker":          t,
                "asset_type":      pos["asset_type"],
                "unit_type":       pos["unit_type"],
                "quantity":        0.0,
                "_maliyet_toplam": 0.0,  # agirlikli ortalama payi
            }
        c = consolidated[t]
        q = pos["quantity"]
        c["quantity"]        += q
        c["_maliyet_toplam"] += q * pos["avg_cost"]

    out = []
    for c in consolidated.values():
        qty = c["quantity"]
        avg_cost = (c["_maliyet_toplam"] / qty) if qty else 0.0
        out.append({
            "ticker":     c["ticker"],
            "asset_type": c["asset_type"],
            "quantity":   qty,
            "avg_cost":   avg_cost,
            "unit_type":  c["unit_type"],
        })
    return out


def _batch_upsert_peaks(user_id: int, upserts: list) -> bool:
    """Toplu peak UPSERT - tek query'de tum guncellemeler.

    upserts: [(ticker, current_price), ...]
    PostgreSQL ON CONFLICT ... WHERE: sadece yeni peak (current > existing) update yapar.
    Yoksa INSERT yapar (yeni record).

    Bu fonksiyon eski update_peak_for_user'in toplu versiyonudur.
    14 ayri call yerine TEK call.
    """
    if not upserts:
        return True
    # Savunma amacli ek tekillestirme (v2.0.7.224): ana cozum
    # _consolidate_portfolio_lots() olsa da, beklenmedik bir cagri yolundan
    # ayni ticker iki kez gelirse burada da PostgreSQL'in "cannot affect
    # row a second time" hatasi vermesini onlemek icin en yuksek fiyati
    # tutan tek kayda indirgenir.
    dedup = {}
    for ticker, current in upserts:
        t = str(ticker)
        if t not in dedup or current > dedup[t]:
            dedup[t] = current
    upserts = list(dedup.items())
    try:
        # Dinamik placeholder string'i build et: "(?, ?, ?, NOW(), FALSE), ..."
        placeholders = ",".join(["(?, ?, ?, NOW(), FALSE)"] * len(upserts))
        sql = (
            "INSERT INTO peak_tracker "
            "  (user_id, ticker, peak_price, peak_time, alert_sent_for_current_peak) "
            f"VALUES {placeholders} "
            "ON CONFLICT (user_id, ticker) DO UPDATE SET "
            "  peak_price = EXCLUDED.peak_price, "
            "  peak_time = NOW(), "
            "  alert_sent_for_current_peak = FALSE "
            "WHERE peak_tracker.peak_price < EXCLUDED.peak_price"
        )
        params = []
        for ticker, current in upserts:
            params.extend([user_id, str(ticker), float(current)])
        conn = get_conn()
        conn.execute(sql, tuple(params))
        try: conn.commit()
        except Exception: pass
        return True
    except Exception as e:
        sys.stderr.write(f"[peak_tracker] batch_upsert hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return False


def _should_trigger_alert(peak_rec: dict, current_price: float,
                          avg_cost: float, settings: dict) -> bool:
    """Bu ticker icin uyari tetiklenmeli mi karari.

    Sirayla:
    1) Dusus thresholdu asti mi?
    2) kar_only ise mevcut > alish mi?
    3) alert_mode bu uyariya izin veriyor mu?
    """
    if peak_rec is None or peak_rec.get("peak_price") is None:
        return False
    peak = peak_rec["peak_price"]
    if peak <= 0:
        return False

    # 1) Dusus yuzdesi
    drop_pct = (peak - current_price) / peak * 100.0
    if drop_pct < settings["threshold_pct"]:
        return False

    # 2) Kar kosulu
    if settings["kar_only"] and current_price <= avg_cost:
        return False

    # 3) Alert mode mantigi
    mode = settings["alert_mode"]
    if mode == "peak_break":
        return not peak_rec.get("alert_sent_for_current_peak", False)
    if mode == "once":
        return peak_rec.get("last_alert_time") is None
    if mode == "hourly":
        last_t = peak_rec.get("last_alert_time")
        if last_t is None:
            return True
        try:
            if isinstance(last_t, str):
                last_t = datetime.fromisoformat(last_t.replace("Z", "+00:00"))
            now_n  = datetime.utcnow()
            last_n = last_t.replace(tzinfo=None) if last_t.tzinfo else last_t
            return (now_n - last_n) >= timedelta(hours=1)
        except Exception:
            return True

    return False


def evaluate_user_alerts(user_id: int, df_uni) -> dict:
    """Kullanicinin portfoyundeki tum varliklar icin peak update + threshold kontrol.

    BATCH versiyon (v2.0 asama 3a.3): 2 DB call (1 SELECT + 1 UPSERT).

    df_uni: pandas DataFrame, 'Ticker' ve 'Son_Fiyat' sutunlari olmali.

    Returns:
      {
        "updated_peaks":  [(ticker, current_price, status)],
        "alerts_pending": [dict - uyari bekleyen tickerlar],
        "skipped":        [(ticker, reason)],
      }
    """
    result = {"updated_peaks": [], "alerts_pending": [], "skipped": []}

    try:
        import time as _t
        _t_start = _t.perf_counter()

        # Kullanici ayarlari (1 SELECT - cache'siz; alert_settings.load icinde)
        settings = load_alert_settings(user_id)
        if not settings.get("enabled", True):
            result["skipped"].append(("(tum portfoy)", "uyari sistemi pasif"))
            return result

        # Portfoy (1 SELECT)
        portfolio = _load_user_portfolio(user_id)
        if not portfolio:
            result["skipped"].append(("(tum portfoy)", "portfoy bos"))
            return result

        # v2.0.7.224: Ayni tickera ait birden fazla lot varsa (ör. MTG'nin
        # 2 alim kaydi), tek pozisyona konsolide et - aksi halde asagidaki
        # per-ticker donguyu ayni ticker'i upserts listesine iki kez ekler
        # ve PostgreSQL batch UPSERT'i reddeder (bkz. _consolidate_portfolio_lots).
        portfolio = _consolidate_portfolio_lots(portfolio)

        # Universe -> ticker:fiyat dict (memory, hizli)
        price_map = {}
        if df_uni is not None and not df_uni.empty:
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

        # Mevcut peak'leri TEK SELECT'le cek
        peak_map = _load_user_peaks_map(user_id)

        # Her ticker icin karar ver (Python tarafinda, DB call YOK)
        upserts = []  # batch UPSERT icin
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

            existing = peak_map.get(ticker)
            effective_peak_rec = existing

            if existing is None:
                # Yeni record olusturulacak
                upserts.append((ticker, current))
                result["updated_peaks"].append((ticker, current, "new_record"))
                # Yeni record icin peak_rec olustur (threshold kontrolu icin)
                effective_peak_rec = {
                    "peak_price": current,
                    "alert_sent_for_current_peak": False,
                    "last_alert_time": None,
                }
            elif current > existing["peak_price"]:
                # Yeni peak (mevcut peak kirilacak)
                upserts.append((ticker, current))
                result["updated_peaks"].append((ticker, current, "new_peak"))
                # Yeni peak icin peak_rec guncellenir (flag reset)
                effective_peak_rec = {
                    **existing,
                    "peak_price": current,
                    "alert_sent_for_current_peak": False,
                }
            # else: current <= peak, no change

            # Threshold kontrolu - mevcut/yeni peak'e gore
            if _should_trigger_alert(effective_peak_rec, current, avg_cost, settings):
                peak  = effective_peak_rec["peak_price"]
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
                    "peak_time":     effective_peak_rec.get("peak_time"),
                    "current_price": current,
                    "drop_pct":      drop,
                    "tavsiye_fiyat": tavsi,
                    "toplam_deger":  current * quantity,
                })

        # Batch UPSERT - tek query (varsa)
        if upserts:
            _batch_upsert_peaks(user_id, upserts)

        _t_total = _t.perf_counter() - _t_start
        sys.stderr.write(
            f"[peak_tracker] evaluate user={user_id} "
            f"updated={len(result['updated_peaks'])} "
            f"pending={len(result['alerts_pending'])} "
            f"skipped={len(result['skipped'])} "
            f"sure={_t_total:.2f}s\n"
        )
        sys.stderr.flush()
        return result
    except Exception as e:
        sys.stderr.write(f"[peak_tracker] evaluate hatasi (user={user_id}): {e}\n")
        sys.stderr.flush()
        return result


def mark_alert_sent(user_id: int, ticker: str, current_price: float) -> bool:
    """Uyari maili basariyla gonderildikten sonra cagrilir."""
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
    """Kullanicinin tum peak kayitlarini doner (UI Uyarilar sayfasi icin)."""
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
    """Manuel peak sifirlama."""
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
