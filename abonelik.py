# -*- coding: utf-8 -*-
"""
TrendSurf Optima - anlik bildirim e-postalarindan cikma baglantisi (abonelik.py)
v2.0.7.412 (11 Ekim 2026, Bahri'nin talebi; anahtar v417'de veritabanina tasindi): her mailin altinda "abonelikten cik" baglantisi.

Baglanti: <UYGULAMA>/?abonelik_iptal=<kullanici_id>.<imza>
  imza = HMAC-SHA256(anahtar, "bildirim-iptal:<kullanici_id>") ilk 32 hex karakter.
  anahtar = SHA256("bildirim-iptal-anahtari-v2:" + <uygulama_anahtar tablosundaki rastgele deger>) (v417; v412'deki
  SUPABASE_DB_URL'den turetme iki tarafta farkli metin cikinca "gecersiz baglanti" verdi). Hem GitHub workflow'u (mail
  uretir) hem Streamlit uygulamasi (baglantiyi acar) ayni veritabanini okur; tablo RLS'lidir, disaridan okunamaz.
Baglanti acmak tek basina abonelik iptal ETMEZ (e-posta tarayicilari baglantilari onceden acabilir): uygulama
bir onay dugmesi gosterir.
"""
import hashlib
import hmac
import os

# DOGRU adres TIRESIZ: trendsurfoptima.streamlit.app (v2.0.7.332/170 notlari). Tireli "trendsurf-optima" ESKI adrestir ve
# Streamlit "You do not have access to this app or it does not exist" sayfasini gosterir (v405'te yanlis yazilmisti).
UYGULAMA_URL = "https://trendsurfoptima.streamlit.app"


ANAHTAR_AD = "abonelik-imza"


def anahtar_al(db_url: str = None) -> bytes:
    """Imza anahtari. v2.0.7.417: veritabanindaki 'uygulama_anahtar' satirindan (GitHub workflow'u ve Streamlit
    uygulamasi ayni veritabanini okur; v412'de SUPABASE_DB_URL metninden turetilen anahtar iki tarafta farkli
    cikti ve baglanti 'gecersiz' dedi). Satir yoksa rastgele uretilip yazilir. db_url verilirse (yalniz testler /
    eski bicim) anahtar o metinden turetilir. Veritabanina ulasilamazsa RuntimeError (cagiran mailde baglanti koymaz)."""
    if db_url:
        return hashlib.sha256(("bildirim-iptal-anahtari:" + db_url).encode("utf-8")).digest()
    import db
    deger = db.uygulama_anahtari_al(ANAHTAR_AD)
    if not deger:
        raise RuntimeError("abonelik anahtari alinamadi: veritabanina ulasilamadi")
    return hashlib.sha256(("bildirim-iptal-anahtari-v2:" + deger).encode("utf-8")).digest()


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
