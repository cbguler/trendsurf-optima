"""
TrendSurf Optima - Standalone Email Sender (GitHub Actions)
v1.7.0: live_data.py entegrasyonu

Onceki davranis:  optimized_universe.csv'yi okuyup oldugu gibi gonderirdi.
                  Worker.py PC'de calismadigi gunlerde icerik 1+ hafta eski olurdu.

Yeni davranis:    CSV'yi tabani okur, live_data.py uzerinden Streamlit Cloud
                  ile birebir ayni pipeline'i uygular:
                    1. USD bazli emtialari filtrele (Brent/WTI/Bugday vb.)
                    2. Gram Altin/Gumus/Platin adlarini netlestir
                    3. 6 yeni sikke ekle (Ceyrek/Yarim/Tam/Cumhuriyet/Ata/Ons-TL)
                    4. DOVIZ + MADEN + KRIPTO icin borsapy canli fiyat overlay
                  Boylece e-posta icerigi Streamlit ile birebir.

BIST ve TEFAS hala CSV'den gelir (worker.py sorumlulugu).
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

# ----------------------------------------------------------------------------
# 1. CSV'den taban veri evrenini oku
# ----------------------------------------------------------------------------
try:
    df_uni = pd.read_csv("optimized_universe.csv")
    print(f"[1/4] CSV yuklendi: {len(df_uni)} satir")
except FileNotFoundError:
    print("[1/4] UYARI: optimized_universe.csv yok - bos DataFrame ile devam")
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
        print(f"[2/4] live_data: {n0} -> filter -> {n1} -> extend -> {n2} -> overlay (borsapy aktif)")
    else:
        print(f"[2/4] UYARI: borsapy yok, sadece filter+rename uygulandi ({n1} satir, CSV verisi kalir)")

except ImportError as e:
    print(f"[2/4] HATA: live_data import edilemedi ({e}) - CSV'yi oldugu gibi kullaniyoruz")
except Exception as e:
    print(f"[2/4] HATA: live_data hatasi (yok sayilir): {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# ----------------------------------------------------------------------------
# 3. Veri saglik kontrolu
# ----------------------------------------------------------------------------
if df_uni.empty:
    print("[3/4] KRITIK: df_uni bos - e-posta icerigi bos olacak ama yine de gonderiyoruz")
else:
    print(f"[3/4] Veri hazir: {len(df_uni)} satir")
    if "Kategori" in df_uni.columns:
        for cat in ["BIST", "TEFAS", "DOVIZ", "MADEN", "KRIPTO"]:
            n = (df_uni["Kategori"] == cat).sum()
            print(f"        {cat:6}: {n} satir")

# ----------------------------------------------------------------------------
# 4. E-posta gonder (mevcut emailer.send_report kullanir)
#    portfolio=[] cunku GitHub Actions SQLite'a erisemez (Streamlit Cloud'da)
# ----------------------------------------------------------------------------
from emailer import send_report
result = send_report(df_uni=df_uni, portfolio=[], cfg=cfg)
print(f"[4/4] Sonuc: {result}")
