"""
TrendSurf Optima — Standalone Email Sender (GitHub Actions)
"""
import os, sys, pandas as pd

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

try:
    df_uni = pd.read_csv("optimized_universe.csv")
    print(f"Veri yuklendi: {len(df_uni)} varlik")
except FileNotFoundError:
    print("optimized_universe.csv bulunamadi — bos DataFrame ile devam")
    df_uni = pd.DataFrame()

from emailer import send_report
result = send_report(df_uni=df_uni, portfolio=[], cfg=cfg)
print("Sonuc:", result)
