"""
data_health_check.py — TrendSurf Optima
Her varlik kategorisinin (BIST/TEFAS/DOVIZ/MADEN/KRIPTO) veri akisini
izler; bir kategori beklenenden uzun sure degismiyorsa (donmussa) admin'e
otomatik e-posta uyarisi gonderir.

Neden gerekli: Temmuz 2026'daki gram altin olayinda, bir kategorinin
gunlerce yanlis/donuk deger gosterdigi TESADUFEN fark edildi. Bu script,
bir dahaki sefere böyle bir sorunu saatler icinde (gunler degil) otomatik
yakalamak icin var.

Yontem: Her kategori icin, o kategorideki TUM Son_Fiyat degerlerinin
toplamini bir "imza" olarak kullanir (tek bir ticker'a bagli kalmadan,
yanlislikla var olmayan bir ticker adi kullanma riski olmadan). Imza son
kontrolden beri degismediyse ve bu degismeme suresi kategori icin
belirlenen esigi asiyorsa, uyari e-postasi gonderilir.

Kategori esikleri (mevcut mimariye gore, TrendSurf_Optima_Yonetici_El_Kitabi'nda
belgelenen guncelleme sikliklarini yansitir):
  - BIST:   sadece seans saatlerinde (hafta ici 10:00-18:00 TRT) kontrol
            edilir, 30 dk esik (Portfoyum/Ana Sayfa'daki canli yenilemenin
            calistigini dogrular)
  - DOVIZ:  7/24 kontrol, 30 dk esik (canli veri katmani var)
  - KRIPTO: 7/24 kontrol, 30 dk esik (canli veri katmani var)
  - TEFAS:  30 saat esik (gunde 1 kez - gece + aksam - guncelleniyor)
  - MADEN:  30 saat esik (henuz canli degil, worker.py gunluk guncelliyor -
            canli kaynak eklendiginde bu esik siklastirilmali)

Calistirma: python data_health_check.py
Gerekli ortam degiskenleri (GitHub Actions Secrets):
  SMTP_USER, SMTP_PASS, SMTP_HOST, SMTP_PORT, ADMIN_EMAIL
  (Bu isimler mevcut e-posta gonderen workflow'unuzdakiyle AYNI OLMALI -
  farkliysa, asagidaki env okuma satirlarini kendi isimlerinizle degistirin.)
"""
import os
import json
import sys
from datetime import datetime, timezone, timedelta

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "optimized_universe.csv")
STATE_PATH = os.path.join(BASE_DIR, "health_state.json")

TRT = timezone(timedelta(hours=3))

KATEGORI_AYARLARI = {
    "BIST":   {"esik_saat": 0.5, "sadece_seans": True},
    "DOVIZ":  {"esik_saat": 0.5, "sadece_seans": False},
    "KRIPTO": {"esik_saat": 0.5, "sadece_seans": False},
    "TEFAS":  {"esik_saat": 30,  "sadece_seans": False},
    "MADEN":  {"esik_saat": 30,  "sadece_seans": False},
}


def _bist_seans_acik(simdi: datetime) -> bool:
    if simdi.weekday() >= 5:
        return False
    return simdi.time() >= datetime.strptime("10:00", "%H:%M").time() and \
           simdi.time() <= datetime.strptime("18:00", "%H:%M").time()


def _imza_hesapla(df: pd.DataFrame, kategori: str):
    """Bir kategorideki tum fiyatlarin toplamini 'imza' olarak kullan.
    Tek bir ticker'a bagli kalmaz - yanlis/degismis ticker adi riski yok."""
    alt = df[df["Kategori"] == kategori]
    if alt.empty:
        return None, 0
    toplam = round(pd.to_numeric(alt["Son_Fiyat"], errors="coerce").fillna(0).sum(), 6)
    return toplam, len(alt)


def _uyari_maili_gonder(uyarilar: list):
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # v2.0.5.5: Secrets tanimli-ama-BOS olabiliyor (SMTP_PORT='' ->
        # int('') patliyordu, mail sessizce basarisiz oluyordu).
        smtp_user = os.environ.get("SMTP_USER") or None
        smtp_pass = os.environ.get("SMTP_PASS") or None
        smtp_host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
        smtp_port = int(os.environ.get("SMTP_PORT") or "587")
        admin_email = os.environ.get("ADMIN_EMAIL") or None

        if not (smtp_user and smtp_pass and admin_email):
            print("[health-check] SMTP/ADMIN_EMAIL secrets eksik, mail gonderilemedi "
                  "(uyarilar yine de asagida yazdirildi).")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "TrendSurf Optima — Veri Akisi Uyarisi"
        msg["From"] = smtp_user
        msg["To"] = admin_email

        _simdi = datetime.now(TRT).strftime("%d.%m.%Y %H:%M TRT")
        _madde_html = "".join(f"<li>{u}</li>" for u in uyarilar)
        html = f"""
        <div style="font-family:Segoe UI,Arial,sans-serif;max-width:520px;margin:auto;">
          <h2 style="color:#b71c1c;margin-bottom:4px;">Veri Akışı Uyarısı</h2>
          <p>TrendSurf Optima'da aşağıdaki kategori(ler) beklenenden uzun süredir güncellenmiyor:</p>
          <ul>{_madde_html}</ul>
          <p style="color:#5a6a78;font-size:13px;">Kontrol zamanı: {_simdi}</p>
          <p style="color:#5a6a78;font-size:13px;">
            Bu, ilgili veri kaynağının donmuş/bozulmuş olabileceğine işaret eder.
            GitHub Actions loglarını ve Manage app loglarını kontrol edin.
          </p>
        </div>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print("[health-check] Uyari maili gonderildi.")
    except Exception as e:
        print(f"[health-check] Uyari maili gonderilemedi: {type(e).__name__}: {e}")


def main():
    simdi = datetime.now(TRT)
    print(f"[health-check] Baslatiliyor - {simdi.isoformat()}")

    if not os.path.exists(CSV_PATH):
        print(f"[health-check] HATA: {CSV_PATH} bulunamadi.")
        sys.exit(1)

    df = pd.read_csv(CSV_PATH, on_bad_lines="skip")

    state = {}
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    uyarilar = []

    for kategori, ayar in KATEGORI_AYARLARI.items():
        if ayar["sadece_seans"] and not _bist_seans_acik(simdi):
            print(f"[health-check] {kategori}: seans disi, kontrol atlandi.")
            continue

        imza, adet = _imza_hesapla(df, kategori)
        if imza is None:
            uyarilar.append(f"<b>{kategori}</b>: kategori CSV'de hiç bulunamadı (0 satır)")
            print(f"[health-check] {kategori}: BULUNAMADI")
            continue

        onceki = state.get(kategori, {})
        if onceki.get("imza") == imza:
            son_degisim = onceki.get("son_degisim_ts")
            if son_degisim:
                gecen_saat = (simdi - datetime.fromisoformat(son_degisim)).total_seconds() / 3600
                esik = ayar["esik_saat"]
                if gecen_saat > esik:
                    uyarilar.append(
                        f"<b>{kategori}</b>: {gecen_saat:.1f} saattir hiç değişmiyor "
                        f"(eşik: {esik:.1f} saat, {adet} varlık)"
                    )
                    print(f"[health-check] {kategori}: UYARI - {gecen_saat:.1f}sa degismiyor "
                          f"(esik {esik}sa)")
                else:
                    print(f"[health-check] {kategori}: OK (henuz {gecen_saat:.1f}sa, esik {esik}sa)")
            else:
                # State'te imza var ama zaman damgasi yok (eski format) - simdiden basla
                state[kategori] = {"imza": imza, "son_degisim_ts": simdi.isoformat()}
        else:
            state[kategori] = {"imza": imza, "son_degisim_ts": simdi.isoformat()}
            print(f"[health-check] {kategori}: degismis, OK (yeni imza kaydedildi)")

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    if uyarilar:
        print(f"\n[health-check] {len(uyarilar)} uyari bulundu:")
        for u in uyarilar:
            print(f"  - {u}")
        _uyari_maili_gonder(uyarilar)
    else:
        print("\n[health-check] Tum kategoriler saglikli.")


if __name__ == "__main__":
    main()
