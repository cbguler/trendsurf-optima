# -*- coding: utf-8 -*-
"""
TrendSurf Optima - anlik bildirim e-postalarindan cikma baglantisi (abonelik.py)
v2.0.7.412 (11 Ekim 2026, Bahri'nin talebi): her mailin altinda "abonelikten cik" baglantisi.

Baglanti: <UYGULAMA>/?abonelik_iptal=<kullanici_id>.<imza>
  imza = HMAC-SHA256(anahtar, "bildirim-iptal:<kullanici_id>") ilk 32 hex karakter.
  anahtar = SHA256("bildirim-iptal-anahtari:" + SUPABASE_DB_URL). Yeni bir secret gerekmez: hem GitHub workflow'u
  (mail uretir) hem Streamlit uygulamasi (baglantiyi acar) bu degere zaten sahiptir; DB adresini bilmeyen biri
  baska bir kullanici icin gecerli baglanti uretemez.
Baglanti acmak tek basina abonelik iptal ETMEZ (e-posta tarayicilari baglantilari onceden acabilir): uygulama
bir onay dugmesi gosterir.
"""
import hashlib
import hmac
import os

UYGULAMA_URL = "https://trendsurf-optima.streamlit.app"


def anahtar_al(db_url: str = None) -> bytes:
    """db_url verilmezse SUPABASE_DB_URL ortam degiskeni, o da yoksa db modulunun cozumledigi adres."""
    u = db_url or os.environ.get("SUPABASE_DB_URL", "")
    if not u:
        try:
            import db
            u = db._get_db_url() or ""
        except Exception:
            u = ""
    if not u:
        raise RuntimeError("abonelik anahtari uretilemedi: veritabani adresi yok")
    return hashlib.sha256(("bildirim-iptal-anahtari:" + u).encode("utf-8")).digest()


def _imza(anahtar: bytes, user_id: int) -> str:
    return hmac.new(anahtar, f"bildirim-iptal:{int(user_id)}".encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def token_uret(user_id: int, anahtar: bytes) -> str:
    return f"{int(user_id)}.{_imza(anahtar, user_id)}"


def token_dogrula(token: str, anahtar: bytes):
    """Gecerliyse kullanici_id (int), degilse None."""
    try:
        uid_s, imza = str(token or "").split(".", 1)
        uid = int(uid_s)
        if uid <= 0:
            return None
    except Exception:
        return None
    return uid if hmac.compare_digest(imza, _imza(anahtar, uid)) else None


def baglanti_uret(user_id: int, anahtar: bytes, taban: str = UYGULAMA_URL) -> str:
    return f"{taban}/?abonelik_iptal={token_uret(user_id, anahtar)}"
