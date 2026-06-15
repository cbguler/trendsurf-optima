
# TrendSurf Optima - Gereksiz dosya temizleme scripti
# Çalıştır: python temizle.py

import os, glob

# Silinecek dosya kalıpları
patterns = [
    "__p1", "__p2", "__p3",  # Base64 parça dosyaları
    "_pages.py", "_p.txt", "_p1.txt", "_p2.txt",  # Geçici dosyalar
    "fix_*.py",   # Tüm fix scripti
    "check_*.py", # Test scriptleri
    "fix_t.py", "uygula_duzeltme.py", "duzelt.py",
    "kucult_logo.py", "test_bigpara_spread.py",
    "guncelle_log.txt",
]

deleted = []
for pattern in patterns:
    for f in glob.glob(pattern):
        try:
            os.remove(f)
            deleted.append(f)
        except Exception as e:
            print(f"Silinemedi {f}: {e}")

# Versiyonlu kopyalar
for f in glob.glob("app_v*.py") + glob.glob("emailer_v*.py"):
    try:
        os.remove(f)
        deleted.append(f)
    except Exception as e:
        print(f"Silinemedi {f}: {e}")

print(f"Silinen {len(deleted)} dosya:")
for d in sorted(deleted):
    print(f"  - {d}")
print("\nTemizlik tamamlandı!")
