"""
TrendSurf Optima — Ilk Admin Olusturma
Bir kez calistirin: python create_admin.py
"""
from db import init_db, get_conn
from auth import hash_password

ADMIN_EMAIL    = "bahriguler@gmail.com"
ADMIN_PASSWORD = "optima2026"        # <-- degistirin
ADMIN_NAME     = "Bahri Guler"

init_db()
conn = get_conn()
conn.execute("""
    INSERT OR REPLACE INTO users (email, password, full_name, plan, is_active, is_admin)
    VALUES (?, ?, ?, 'premium', 1, 1)
""", (ADMIN_EMAIL, hash_password(ADMIN_PASSWORD), ADMIN_NAME))
conn.commit()
conn.close()
print(f"Admin olusturuldu: {ADMIN_EMAIL}")
