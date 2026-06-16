"""
TrendSurf Optima — Standalone Email Sender (GitHub Actions)
"""
import os, sys, json, pandas as pd

# Çevre değişkenlerinden config oluştur
cfg = {
    "address":   os.environ.get("EMAIL_ADDRESS", ""),
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": os.environ.get("SMTP_USER", ""),
    "smtp_pass": os.environ.get("SMTP_PASS", ""),
}

if not cfg["smtp_user"] or not cfg["smtp_pass"]:
    print("HATA: EMAIL_ADDRESS, SMTP_USER, SMTP_PASS env değişkenleri eksik")
    sys.exit(1)

# Veri yükle
try:
    df_uni = pd.read_csv("optimized_universe.csv")
    print(f"Veri yüklendi: {len(df_uni)} varlık")
except FileNotFoundError:
    print("optimized_universe.csv bulunamadı")
    df_uni = pd.DataFrame()

# Gönder (portfolyo GitHub Actions'ta yok — boş bırakılır)
from emailer import send_report
result = send_report(df_uni=df_uni, portfolio_rows=[], cfg=cfg)
print("E-posta gönderildi:", result)
