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
