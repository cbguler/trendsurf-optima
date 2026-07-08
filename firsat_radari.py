# -*- coding: utf-8 -*-
"""
TrendSurf Optima - Firsat Radari (firsat_radari.py)
v2.0.5

AMAC
----
"BIST'teki TUM varliklarin performansini ayni anda degerlendirmek ve
firsatlar takip etmedigimiz hisselerdeyse kacirmamak" (Bahri, Temmuz 2026).

Uygulama tarafinda 772 hisseyi canli hesaplamak performansi oldurur.
Cozum: degerlendirme YUKU arka plana (GitHub Actions) alinir, SONUC
Supabase'e yazilir, uygulama tek sorguyla okur.

CALISMA SEKLI
-------------
- BIST     : Seans saatlerinde (hafta ici TRT 10:00-18:30 tampon dahil)
             772 hissenin TAMAMI batch indirilir, tam Optima Skoru
             (hacim trendi + Max Drawdown duzeltmesi + temel analiz
             bileseni dahil) worker.py ile BIREBIR ayni formulle hesaplanir.
             Temel analiz (P/B, P/E, temettu) YENIDEN CEKILMEZ - gece
             worker.py'nin CSV'ye yazdigi PB/PE/DY kolonlari kullanilir
             (yfinance'i gunduz 611 kez daha yormamak icin).
- DOVIZ/MADEN/KRIPTO: Sayilari az (12+4+19), 7/24 HER kosuda taranir.
- Sonuclar Supabase 'intraday_scores' tablosuna UPSERT edilir.
- RADAR   : Skoru esigi (varsayilan 75) asagidan yukari kesen veya bir
             onceki taramaya gore buyuk sicrama (varsayilan +10) yapan
             varliklar icin admin'e TEK toplu e-posta gonderilir.
             Ayni varlik icin ayni gun ayni tur alarm TEKRARLANMAZ
             (radar_alerts tablosu, ON CONFLICT DO NOTHING).

GEREKLI SUPABASE TABLOLARI (bir kez SQL Editor'de calistir):
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS intraday_scores (
    ticker      text PRIMARY KEY,
    kategori    text,
    skor        double precision,
    fiyat       double precision,
    rsi         double precision,
    ret1m       double precision,
    updated_at  timestamptz DEFAULT now()
);
ALTER TABLE intraday_scores ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS radar_alerts (
    ticker      text,
    tarih       date,
    tur         text,
    skor        double precision,
    created_at  timestamptz DEFAULT now(),
    PRIMARY KEY (ticker, tarih, tur)
);
ALTER TABLE radar_alerts ENABLE ROW LEVEL SECURITY;

ORTAM DEGISKENLERI (GitHub Actions secrets)
-------------------------------------------
SUPABASE_DB_URL  (zorunlu)
SMTP_USER, SMTP_PASS, SMTP_HOST, SMTP_PORT, ADMIN_EMAIL (radar maili icin)
RADAR_ESIK      (istege bagli, varsayilan 75)
RADAR_SICRAMA   (istege bagli, varsayilan 10)
"""

import os
import sys
import warnings
from datetime import datetime, timedelta

import pandas as pd

warnings.filterwarnings("ignore")

CSV_PATH      = "optimized_universe.csv"
RADAR_ESIK    = float(os.environ.get("RADAR_ESIK", "75"))
RADAR_SICRAMA = float(os.environ.get("RADAR_SICRAMA", "10"))


# ─── Zaman / seans yardimcilari ──────────────────────────────

def _trt_simdi() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Istanbul"))
    except Exception:
        return datetime.utcnow() + timedelta(hours=3)


def _bist_seans_acik(simdi: datetime) -> bool:
    """Hafta ici TRT 10:00-18:30 (kapanis sonrasi 30 dk tampon -
    son fiyatlarin/gunun tam degerlendirmesi bir kez daha yapilsin)."""
    if simdi.weekday() >= 5:
        return False
    dk = simdi.hour * 60 + simdi.minute
    return (10 * 60) <= dk <= (18 * 60 + 30)


# ─── Skor formulleri (worker.py ile BIREBIR AYNI - senkron tutulmali) ──

def calc_rsi(s: pd.Series, p: int = 14) -> float:
    s = s.dropna()
    if len(s) < p + 1:
        return 50.0
    d = s.diff().dropna()
    g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    if l.iloc[-1] == 0:
        return 100.0
    rs = g.iloc[-1] / l.iloc[-1]
    return round(float(100 - 100 / (1 + rs)), 1)


def _bist_optima_score(rsi, ret1m, vol=30.0, has_fundamental=False,
                       pb=None, pe=None, dy=None):
    """worker.py._bist_optima_score kopyasi (v2.0.4.57)."""
    if 40 <= rsi <= 60: rsi_s = 25
    elif 35 <= rsi <= 65: rsi_s = 18
    elif 30 <= rsi < 35 or 65 < rsi <= 70: rsi_s = 10
    else: rsi_s = 0

    if ret1m >= 30: mom = 35
    elif ret1m >= 20: mom = 30
    elif ret1m >= 10: mom = 24
    elif ret1m >= 5: mom = 18
    elif ret1m >= 0: mom = 10
    elif ret1m >= -5: mom = 4
    else: mom = 0

    if vol < 20: vol_s = 15
    elif vol < 35: vol_s = 10
    elif vol < 55: vol_s = 5
    else: vol_s = 0

    fund_s = 0
    if has_fundamental:
        if pe and 0 < float(pe) < 12: fund_s += 10
        elif pe and 0 < float(pe) < 25: fund_s += 5
        if pb and 0 < float(pb) < 1.5: fund_s += 8
        elif pb and 0 < float(pb) < 3: fund_s += 4
        if dy and float(dy) > 0.08: fund_s += 7
        elif dy and float(dy) > 0.04: fund_s += 3
        return min(100, round(rsi_s + mom + vol_s + fund_s, 1))

    raw = rsi_s + mom + vol_s
    return min(100, round(raw * (100.0 / 75.0), 1))


# ─── BIST tam-evren taramasi ─────────────────────────────────

def tara_bist(tickers, fund_map):
    """worker.py.batch_bist ile ayni mantik: batch download + RSI/Ret1M/Vol
    + hacim trendi + Max DD duzeltmesi + (CSV'den gelen) temel analiz."""
    import yfinance as yf
    print(f"[radar] BIST tam tarama: {len(tickers)} hisse...")
    out = {}
    chunk_size = 200
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        syms = [f"{t}.IS" for t in chunk]
        try:
            raw = yf.download(syms, period="3mo", progress=False,
                              auto_adjust=True, group_by="ticker")
        except Exception as e:
            print(f"[radar] chunk {i//chunk_size+1} indirme hatasi: {e}")
            continue
        for t, sym in zip(chunk, syms):
            try:
                if len(syms) == 1:
                    sub = raw
                else:
                    sub = raw[sym] if sym in raw.columns.get_level_values(0) else pd.DataFrame()
                col = sub["Close"].dropna() if "Close" in sub.columns else pd.Series(dtype=float)
                if hasattr(col, "squeeze"):
                    col = col.squeeze()
                if col.empty or len(col) < 2:
                    continue
                p     = round(float(col.iloc[-1]), 4)
                rsi   = calc_rsi(col)
                ret1m = round((col.iloc[-1] / col.iloc[-22] - 1) * 100, 2) if len(col) >= 22 else 0.0
                rets  = col.pct_change().dropna()
                vol   = round(float(rets.std() * (252 ** 0.5) * 100), 1) if len(rets) > 10 else 30.0

                score_adj, dd_adj = 0, 0
                trend = "YUKSELIS" if ret1m >= 0 else "DUSUS"
                if "Volume" in sub.columns and len(sub) >= 20:
                    vs = sub["Volume"].fillna(0)
                    if hasattr(vs, "squeeze"):
                        vs = vs.squeeze()
                    if float(vs.sum()) > 0:
                        l5, l20 = float(vs.tail(5).mean()), float(vs.tail(20).mean())
                        if l20 > 0:
                            vr = l5 / l20
                            vt = "ARTIYOR" if vr >= 1.2 else "AZALIYOR" if vr <= 0.8 else "NORMAL"
                            if trend == "YUKSELIS" and vt == "ARTIYOR": score_adj = +5
                            elif trend == "YUKSELIS" and vt == "AZALIYOR": score_adj = -10
                            elif trend == "DUSUS" and vt == "ARTIYOR": score_adj = -3
                            elif trend == "DUSUS" and vt == "AZALIYOR": score_adj = +2
                win = col.tail(252) if len(col) >= 252 else col
                if len(win) >= 20:
                    cummax = win.cummax()
                    max_dd = float(((win - cummax) / cummax * 100).min())
                    if max_dd < -70: dd_adj = -7
                    elif max_dd < -50: dd_adj = -3

                pb, pe, dy = fund_map.get(t, (None, None, None))
                base = _bist_optima_score(rsi, ret1m, vol, True, pb, pe, dy)
                skor = max(0.0, min(100.0, round(base + score_adj + dd_adj, 1)))
                out[t] = {"kategori": "BIST", "skor": skor, "fiyat": p,
                          "rsi": rsi, "ret1m": ret1m}
            except Exception:
                continue
    print(f"[radar] BIST tarama sonucu: {len(out)} hisse degerlendirildi.")
    return out


# ─── DOVIZ / MADEN / KRIPTO taramasi (7/24) ──────────────────

def tara_fx_maden_kripto(df_uni):
    """Az sayida varlik: her kosuda gecmis veriden RSI/Ret1M/Vol + skor.
    Kaynaklar canli katmanla ayni: MADEN/DOVIZ -> borsapy, KRIPTO -> BtcTurk."""
    out = {}
    try:
        import borsapy as bp
    except Exception as e:
        print(f"[radar] borsapy yok, FX/MADEN/KRIPTO atlandi: {e}")
        return out

    _MADEN_BP = {"ALTIN_TRY": "gram-altin", "GUMUS_TRY": "gumus",
                 "PLATIN_TRY": "platin", "PALADYUM_TRY": "paladyum"}
    _DOVIZ_BP = {"USDTRY": "USD", "EURTRY": "EUR", "GBPTRY": "GBP",
                 "JPYTRY": "JPY", "CHFTRY": "CHF", "AUDTRY": "AUD",
                 "CADTRY": "CAD", "NZDTRY": "NZD", "NOKTRY": "NOK",
                 "SEKTRY": "SEK", "DKKTRY": "DKK", "CNYTRY": "CNY"}

    def _skorla(t, kategori, close):
        if close is None or len(close) < 2:
            return
        p     = round(float(close.iloc[-1]), 6)
        rsi   = calc_rsi(close)
        ret1m = round((close.iloc[-1] / close.iloc[-22] - 1) * 100, 2) if len(close) >= 22 else 0.0
        rets  = close.pct_change().dropna()
        vol   = round(float(rets.std() * (252 ** 0.5) * 100), 1) if len(rets) > 10 else 30.0
        skor  = _bist_optima_score(rsi, ret1m, vol)  # has_fundamental=False
        out[t] = {"kategori": kategori, "skor": skor, "fiyat": p,
                  "rsi": rsi, "ret1m": ret1m}

    def _close_from(h):
        if h is None or h.empty:
            return None
        for c in ("Close", "close", "PRICE", "price"):
            if c in h.columns:
                return h[c].dropna()
        return None

    for t, code in _MADEN_BP.items():
        try:
            _skorla(t, "MADEN", _close_from(bp.FX(code).history(period="3mo", interval="1d")))
        except Exception:
            continue
    for t, code in _DOVIZ_BP.items():
        try:
            _skorla(t, "DOVIZ", _close_from(bp.FX(code).history(period="3mo", interval="1d")))
        except Exception:
            continue

    kripto_list = (df_uni[df_uni["Kategori"] == "KRIPTO"]["Ticker"]
                   .dropna().astype(str).tolist()) if df_uni is not None else []
    for t in kripto_list:
        try:
            code = "LINK" if t == "CLINK" else t
            _skorla(t, "KRIPTO", _close_from(bp.Crypto(f"{code}TRY").history(period="3mo", interval="1d")))
        except Exception:
            continue

    print(f"[radar] FX/MADEN/KRIPTO: {len(out)} varlik degerlendirildi.")
    return out


# ─── Supabase yazma + radar alarmi ───────────────────────────

def _onceki_skorlari_al(conn):
    try:
        rows = conn.execute("SELECT ticker, skor FROM intraday_scores").fetchall()
        onceki = {}
        for r in rows:
            if isinstance(r, dict):
                onceki[r["ticker"]] = float(r["skor"] or 0)
            else:
                onceki[r[0]] = float(r[1] or 0)
        return onceki
    except Exception as e:
        print(f"[radar] onceki skorlar okunamadi (ilk kosu olabilir): {e}")
        return {}


def _upsert(conn, sonuc):
    n = 0
    for t, v in sonuc.items():
        try:
            conn.execute(
                "INSERT INTO intraday_scores (ticker, kategori, skor, fiyat, rsi, ret1m, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, now()) "
                "ON CONFLICT (ticker) DO UPDATE SET "
                "kategori=EXCLUDED.kategori, skor=EXCLUDED.skor, fiyat=EXCLUDED.fiyat, "
                "rsi=EXCLUDED.rsi, ret1m=EXCLUDED.ret1m, updated_at=now()",
                # v2.0.5.4: float() zorunlu - pandas/numpy'den gelen np.float64
                # tipleri db katmaninda SQL'e "np.float64(...)" metni olarak
                # gomuluyor ve PostgreSQL 'schema "np" does not exist' veriyordu.
                (str(t), str(v["kategori"]), float(v["skor"]), float(v["fiyat"]),
                 float(v["rsi"]), float(v["ret1m"])))
            n += 1
        except Exception as e:
            print(f"[radar] upsert hatasi ({t}): {e}")
    try:
        conn.commit()
    except Exception:
        pass
    print(f"[radar] Supabase intraday_scores: {n} satir guncellendi.")


def _radar_tetikleyicileri(sonuc, onceki, ad_map):
    """Esik kesisi ve sicrama alarmlari."""
    tetik = []
    for t, v in sonuc.items():
        eski = onceki.get(t)
        yeni = v["skor"]
        if yeni >= RADAR_ESIK and (eski is None or eski < RADAR_ESIK):
            tetik.append((t, "esik", yeni, eski, v))
        elif eski is not None and (yeni - eski) >= RADAR_SICRAMA:
            tetik.append((t, "sicrama", yeni, eski, v))
    return tetik


def _dedupe_ve_kaydet(conn, tetik):
    """Ayni gun ayni varlik+tur icin tekrar mail atma (atomik ON CONFLICT)."""
    bugun = _trt_simdi().strftime("%Y-%m-%d")
    yeni = []
    for t, tur, yeni_skor, eski_skor, v in tetik:
        try:
            cur = conn.execute(
                "INSERT INTO radar_alerts (ticker, tarih, tur, skor) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (t, bugun, tur, yeni_skor))
            eklendi = getattr(cur, "rowcount", 1)
            if eklendi and eklendi > 0:
                yeni.append((t, tur, yeni_skor, eski_skor, v))
        except Exception as e:
            print(f"[radar] alert kaydi hatasi ({t}): {e}")
    try:
        conn.commit()
    except Exception:
        pass
    return yeni


def _radar_maili_gonder(yeni_alarmlar, ad_map):
    if not yeni_alarmlar:
        return
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        smtp_user = os.environ.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASS")
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        admin     = os.environ.get("ADMIN_EMAIL")
        if not (smtp_user and smtp_pass and admin):
            print("[radar] SMTP/ADMIN_EMAIL secrets eksik, mail atlanadi. "
                  f"{len(yeni_alarmlar)} alarm sadece loglandi.")
            return

        satirlar = []
        for t, tur, yeni_s, eski_s, v in yeni_alarmlar:
            ad = ad_map.get(t, t)
            eski_txt = f"{eski_s:.1f}" if eski_s is not None else "-"
            tur_txt = ("esik ustu (" + str(int(RADAR_ESIK)) + "+)" if tur == "esik"
                       else f"sicrama (+{RADAR_SICRAMA:.0f}+)")
            satirlar.append(
                f"<tr><td>{t}</td><td>{ad[:40]}</td><td>{v['kategori']}</td>"
                f"<td>{eski_txt} -> <b>{yeni_s:.1f}</b></td>"
                f"<td>{v['fiyat']}</td><td>{tur_txt}</td></tr>")

        html = f"""
        <html><body>
        <h3>TrendSurf Optima - Firsat Radari</h3>
        <p>{_trt_simdi().strftime('%d.%m.%Y %H:%M')} taramasinda
        {len(yeni_alarmlar)} varlik radar kriterlerini tetikledi:</p>
        <table border="1" cellpadding="6" cellspacing="0">
        <tr><th>Ticker</th><th>Ad</th><th>Kategori</th><th>Optima Skor</th>
        <th>Fiyat</th><th>Tetik</th></tr>
        {''.join(satirlar)}
        </table>
        <p style="color:#888;font-size:12px">Bu bir yatirim tavsiyesi degildir.
        Skorlar gecmis/duyurulmus verilerin matematiksel ozetidir.</p>
        </body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Firsat Radari: {len(yeni_alarmlar)} yeni sinyal"
        msg["From"] = smtp_user
        msg["To"] = admin
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [admin], msg.as_string())
        print(f"[radar] Radar maili gonderildi: {len(yeni_alarmlar)} sinyal.")
    except Exception as e:
        print(f"[radar] Mail gonderilemedi: {e}")


# ─── TEFAS aksam degerlendirmesi (gunde 1) ───────────────────

def degerlendir_tefas(df_uni, simdi):
    """v2.0.5.3: TEFAS fonlari gunde BIR kez NAV aciklar - gun ici tarama
    anlamsizdir. Bunun yerine, aksam NAV guncellemesinden (TRT 20:00/20:30,
    update_tefas_evening.yml) SONRAKI kosuda, CSV'deki guncel skorlar okunur
    ve BIST/Doviz ile ayni esik/sicrama kurallarindan gecirilir. Yeni veri
    CEKILMEZ (CSV zaten taze) - sadece karsilastirilir; maliyet saniyeler.

    Pencere TRT 20:40-21:40: 15 dk'lik radar araligiyla bu pencereye en az
    bir kosu kesin duser; radar_alerts'in gun bazli dedupe'u sayesinde
    pencereye iki kosu dussa bile ayni alarm iki kez gitmez."""
    dk = simdi.hour * 60 + simdi.minute
    # v2.0.5.3a: Manuel test icin pencere disi zorlama - workflow'u elle
    # tetiklerken RADAR_TEFAS_ZORLA=1 ortam degiskeni verilirse pencere
    # kontrolu atlanir (normal cron kosularinda tanimsiz oldugundan etkisiz).
    _zorla = os.environ.get("RADAR_TEFAS_ZORLA", "") == "1"
    if not _zorla and not ((20 * 60 + 40) <= dk <= (21 * 60 + 40)):
        return {}

    out = {}
    df_t = df_uni[df_uni["Kategori"] == "TEFAS"]
    for _, r in df_t.iterrows():
        try:
            fiyat = float(r.get("Son_Fiyat", 0) or 0)
            if fiyat <= 0:
                continue
            rsi   = float(r.get("RSI", 50) or 50)
            ret1m = float(r.get("Ret1M", 0) or 0)
            vol   = float(r.get("Vol", 30) or 30)
            # v2.0.5.4: CSV'de Optima_Skor TEFAS icin BOS geliyor (worker.py
            # o kolonu sadece BIST icin dolduruyor; uygulama TEFAS skorunu
            # ekranda anlik hesapliyor). Radar da ayni formulle kendisi
            # hesaplar: skor varsa kullan, yoksa RSI/Ret1M/Vol'den uret.
            try:
                skor = float(r["Optima_Skor"])
            except Exception:
                skor = float("nan")
            if skor != skor:  # NaN -> ayni formulle hesapla
                skor = float(_bist_optima_score(rsi, ret1m, vol))
            out[str(r["Ticker"])] = {
                "kategori": "TEFAS", "skor": round(skor, 1), "fiyat": fiyat,
                "rsi": rsi, "ret1m": ret1m}
        except Exception:
            continue
    print(f"[radar] TEFAS aksam degerlendirmesi: {len(out)} fon (CSV'den).")
    return out


# ─── Ana akis ────────────────────────────────────────────────

def main():
    simdi = _trt_simdi()
    print(f"[radar] Baslangic: {simdi.strftime('%d.%m.%Y %H:%M TRT')}")

    # Evren + gece temel verileri CSV'den (repo checkout icinde)
    try:
        df_uni = pd.read_csv(CSV_PATH, on_bad_lines="skip")
    except Exception as e:
        print(f"[radar] KRITIK: {CSV_PATH} okunamadi: {e}")
        sys.exit(1)

    ad_map = dict(zip(df_uni["Ticker"].astype(str), df_uni["Ad"].astype(str)))

    # Gece worker'inin yazdigi temel analiz kolonlari (varsa)
    fund_map = {}
    if all(c in df_uni.columns for c in ("PB", "PE", "DY")):
        for _, r in df_uni[df_uni["Kategori"] == "BIST"].iterrows():
            def _f(x):
                try:
                    fx = float(x)
                    return None if fx != fx else fx
                except Exception:
                    return None
            fund_map[str(r["Ticker"])] = (_f(r["PB"]), _f(r["PE"]), _f(r["DY"]))
        print(f"[radar] Temel analiz CSV'den yuklendi: {sum(1 for v in fund_map.values() if any(v))} hisse.")
    else:
        print("[radar] CSV'de PB/PE/DY kolonlari yok - skorlar temel analizsiz "
              "hesaplanacak (worker.py guncellemesi push edilince duzelir).")

    sonuc = {}

    # 1) DOVIZ / MADEN / KRIPTO - 7/24
    sonuc.update(tara_fx_maden_kripto(df_uni))

    # 2) BIST - sadece seans saatleri
    if _bist_seans_acik(simdi):
        bist_tickers = (df_uni[(df_uni["Kategori"] == "BIST")]["Ticker"]
                        .dropna().astype(str).tolist())
        sonuc.update(tara_bist(bist_tickers, fund_map))
    else:
        print("[radar] BIST seansi kapali - BIST taramasi atlandi.")

    # 3) TEFAS - gunde 1 (aksam NAV guncellemesi sonrasi pencere)
    sonuc.update(degerlendir_tefas(df_uni, simdi))

    if not sonuc:
        print("[radar] Degerlendirilecek sonuc yok, cikiliyor.")
        return

    # 4) Supabase'e yaz + radar
    try:
        from db import get_conn
        conn = get_conn()
    except Exception as e:
        print(f"[radar] KRITIK: Supabase baglantisi kurulamadi: {e}")
        sys.exit(1)

    onceki = _onceki_skorlari_al(conn)
    tetik  = _radar_tetikleyicileri(sonuc, onceki, ad_map)
    _upsert(conn, sonuc)
    yeni   = _dedupe_ve_kaydet(conn, tetik)
    _radar_maili_gonder(yeni, ad_map)

    print(f"[radar] Bitti: {len(sonuc)} varlik tarandi, "
          f"{len(tetik)} tetik, {len(yeni)} yeni alarm.")


if __name__ == "__main__":
    main()
