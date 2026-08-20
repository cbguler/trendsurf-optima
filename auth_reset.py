"""
Şifre sıfırlama fonksiyonları — auth.py'e entegre edilecek ek kod
"""

def generate_reset_token(email: str) -> dict:
    """
    Şifre sıfırlama token'ı üretir, DB'ye kaydeder ve e-posta gönderir.
    Token 1 saat geçerlidir.
    """
    import secrets
    from datetime import datetime, timedelta
    from db import get_conn

    conn = get_conn()
    
    # Kullanıcı var mı kontrol et
    user = conn.execute(
        "SELECT id, email, full_name FROM users WHERE email=?",
        (email.strip().lower(),)
    ).fetchone()
    
    if not user:
        conn.close()
        # Güvenlik: kullanıcı yoksa da başarılı mesaj ver
        return {"ok": True, "msg": "E-posta adresinize sıfırlama bağlantısı gönderildi."}

    # Reset token tablosu yoksa oluştur
    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            token      TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            used       INTEGER NOT NULL DEFAULT 0
        )
    """)
    
    # Eski token'ları temizle
    conn.execute("DELETE FROM password_resets WHERE user_id=?", (user["id"],))
    
    token   = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(hours=1)).isoformat()
    conn.execute(
        "INSERT INTO password_resets (token, user_id, expires_at) VALUES (?,?,?)",
        (token, user["id"], expires)
    )
    conn.commit()
    conn.close()

    # E-posta gönder
    _send_reset_email(user["email"], user["full_name"], token)
    
    return {"ok": True, "msg": "E-posta adresinize sıfırlama bağlantısı gönderildi."}


def _send_reset_email(to_email: str, full_name: str, token: str):
    """Şifre sıfırlama e-postası gönderir.

    v2.0.7.170 (Bahri'nin bulgusu, 20 Ağustos 2026 — "şifremi unuttuğum
    için giremiyorum, sıfırlama bağlantısı bir türlü gelmiyor"): KÖK
    NEDEN BULUNDU - bu fonksiyon SADECE yerel `email_config.json`
    dosyasına bakıyordu. O dosya `.gitignore`'da ("Hassas konfigürasyon")
    - yani Streamlit Cloud'a HİÇ YÜKLENMİYOR, orada asla var olmuyor.
    Dosya yoksa fonksiyon SESSİZCE hiçbir şey yapmadan geri dönüyordu -
    ama çağıran kod (app.py) buna rağmen HER ZAMAN "E-posta adresinize
    sıfırlama bağlantısı gönderildi." başarı mesajı gösteriyordu (bu
    kısım BİLEREK böyle - "kullanıcı yoksa da başarılı mesaj ver"
    güvenlik prensibiyle aynı, hesabın var olup olmadığını e-posta
    enumerasyonuyla sızdırmamak için - buna DOKUNULMADI). Sonuç: bu
    özellik Streamlit Cloud'da MUHTEMELEN HİÇ ÇALIŞMAMIŞTI, sessizce.

    ÇÖZÜM: `emailer.py`'nin ZATEN ÇALIŞAN (Bahri'nin planlı e-posta
    raporları bu şekilde geliyor) tam olarak aynı deseni buraya
    taşındı - önce yerel dosya, YOKSA `st.secrets["email"]` fallback.
    Streamlit Cloud'da bu secrets zaten yapılandırılmış (emailer.py
    onu kullanıyor) - yani bu düzeltme YENİ bir secrets girişi
    GEREKTİRMİYOR, sadece auth_reset.py'nin ONA BAKMASINI sağlıyor."""
    import smtplib, json, os
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    cfg = {}
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email_config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    # v2.0.7.170: emailer.py ile AYNI fallback - yerel dosya yoksa/boşsa
    # Streamlit Cloud'un kendi Secrets mekanizmasına düş (Cloud reboots
    # sonrası da kalıcı, git'e asla yazılmaz).
    if not cfg.get("smtp_user"):
        try:
            import streamlit as st
            _s = st.secrets.get("email", {})
            if _s.get("smtp_user"):
                cfg = dict(_s)
        except Exception:
            pass

    smtp_host = cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(cfg.get("smtp_port", 587))
    smtp_user = cfg.get("smtp_user", "")
    smtp_pass = cfg.get("smtp_pass", "")

    if not smtp_user:
        print("[auth_reset] SMTP ayarları bulunamadı (ne email_config.json "
              "ne de st.secrets['email']) - sıfırlama e-postası GÖNDERİLEMEDİ.")
        return

    # v2.0.7.171 (Bahri'nin bulgusu, 20 Ağustos 2026 — "e-posta geldi
    # ama linke tıklayınca localhost çıktı, giremedim"): KÖK NEDEN -
    # `APP_URL` Streamlit Cloud Secrets'ta HİÇ TANIMLI DEĞİLDİ, kod bu
    # yüzden "http://localhost:8501" varsayılanına düşüyordu - Bahri'nin
    # kendi cihazında ASLA çalışmayan bir adres (yerel geliştirme
    # sunucusu, sadece geliştiricinin kendi bilgisayarında anlamlı).
    # BU BİR KOD HATASI DEĞİL - eksik bir Secrets girişi. Ama varsayılan
    # değer DAHA GÜVENLİ hale getirildi: localhost yerine, secret
    # eksik/yanlış olsa bile en azından GERÇEKTEN VAR OLAN bir adrese
    # düşsün diye bilinen Streamlit Cloud adresi varsayılan yapıldı
    # (auth.py'deki v2.0.7.170 düzeltmesiyle AYNI desen).
    # KALICI ÇÖZÜM (Bahri'nin yapması gereken, kod dışı bir adım):
    # Streamlit Cloud > Manage app > Settings > Secrets'a
    # `APP_URL = "https://<güncel-adresin>.streamlit.app"` satırını
    # ekle - subdomain'i her değiştirdiğinde bu satırı da güncelle.
    _VARSAYILAN_APP_URL = "https://trendsurf-optima.streamlit.app"
    try:
        import streamlit as st
        base_url = st.secrets.get("APP_URL", _VARSAYILAN_APP_URL)
    except Exception:
        base_url = _VARSAYILAN_APP_URL

    reset_url = f"{base_url}?reset_token={token}"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px;">
      <div style="background:#2c3e6b;padding:20px;border-radius:10px 10px 0 0;text-align:center;">
        <h2 style="color:#fff;margin:0;">TrendSurf Optima</h2>
        <p style="color:#8ca3cc;margin:5px 0 0;">Şifre Sıfırlama</p>
      </div>
      <div style="background:#fff;padding:24px;border:1px solid #e0e8f5;border-radius:0 0 10px 10px;">
        <p style="color:#1b2a4a;">Merhaba <b>{full_name}</b>,</p>
        <p style="color:#4a5a7a;">Şifre sıfırlama talebiniz alındı. Aşağıdaki butona tıklayarak yeni şifrenizi belirleyebilirsiniz.</p>
        <div style="text-align:center;margin:24px 0;">
          <a href="{reset_url}"
             style="background:#2c3e6b;color:#fff;padding:12px 32px;border-radius:6px;
                    text-decoration:none;font-weight:700;font-size:15px;">
            Şifremi Sıfırla
          </a>
        </div>
        <p style="color:#9aa8c0;font-size:12px;">Bu bağlantı 1 saat geçerlidir. Talebi siz yapmadıysanız bu e-postayı görmezden gelebilirsiniz.</p>
      </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "TrendSurf Optima — Şifre Sıfırlama"
    msg["From"]    = smtp_user
    msg["To"]      = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.ehlo(); s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, to_email, msg.as_string())
    except Exception as e:
        print(f"Reset e-posta hatası: {e}")


def verify_reset_token(token: str) -> dict:
    """Token geçerli mi kontrol et."""
    from datetime import datetime
    from db import get_conn

    conn = get_conn()
    row = conn.execute("""
        SELECT r.user_id, r.expires_at, r.used, u.email
        FROM password_resets r
        JOIN users u ON u.id = r.user_id
        WHERE r.token=?
    """, (token,)).fetchone()
    conn.close()

    if not row:
        return {"ok": False, "msg": "Geçersiz veya süresi dolmuş bağlantı."}
    if row["used"]:
        return {"ok": False, "msg": "Bu bağlantı daha önce kullanılmış."}
    if datetime.fromisoformat(row["expires_at"]) < datetime.now():
        return {"ok": False, "msg": "Bağlantının süresi dolmuş. Yeni talep oluşturun."}

    return {"ok": True, "user_id": row["user_id"], "email": row["email"]}


def reset_password(token: str, new_password: str) -> dict:
    """Token ile şifreyi sıfırla."""
    from db import get_conn
    from auth import hash_password

    verify = verify_reset_token(token)
    if not verify["ok"]:
        return verify

    if len(new_password) < 8:
        return {"ok": False, "msg": "Şifre en az 8 karakter olmalı."}

    conn = get_conn()
    conn.execute(
        "UPDATE users SET password=? WHERE id=?",
        (hash_password(new_password), verify["user_id"])
    )
    conn.execute(
        "UPDATE password_resets SET used=1 WHERE token=?", (token,)
    )
    conn.commit()
    conn.close()

    return {"ok": True, "msg": "Şifreniz başarıyla güncellendi. Giriş yapabilirsiniz."}
