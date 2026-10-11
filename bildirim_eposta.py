"""
TrendSurf Optima - Anlik Bildirim E-postasi (bildirim_eposta.py)
v2.0.7.405 (11 Ekim 2026, Bahri'nin talebi): "Fon veya Hisse senedi uyari aldiginda, halka arz ve temettu
degisiklik oldugunda aninda e-posta gonderilsin" - alicilar: e-posta ayari (email_settings) yapmis TUM aboneler.

OLAY KAYNAKLARI (hepsi KAP'tan ya da onaylanmis SPK tedbir listesinden; bkz. PROJE_NOTLARI v405):
  risk      kap_risk_uyari       AGIR/ORTA seviyeli KAP risk uyarilari (hisse + fon; kap_risk_tarama.py yazar)
  tedbir    piyasa_tedbir_listesi  ONAYLANMIS aktif SPK/piyasa tedbirleri (yeni eklenen satir)
  halkaarz  KAP izahname bildirimleri (SPK onayina sunulan + onaylanan) - yeni bildirim = yeni halka arz / asama degisimi
  xharz     KAP Endeksler XHARZ uyeleri - yeni uye = borsada islem gormeye basladi
  temettu   KAP "Kar Payi Dagitimi" bildirimleri - yeni bildirim = yeni/degisen temettu karari

TEKRAR ONLEME:
  bildirim_eposta_olay       her olay bir kez kaydedilir (anahtar tekil)
  bildirim_eposta_gonderim   (kullanici, olay) basina bir kez rezerve edilir; SMTP basarisiz olursa rezervasyon
                             silinir ve olay RETRY_SAAT icinde sonraki calismada tekrar denenir
  ILK CALISMA: her tur icin ilk calismada mevcut olaylar SESSIZCE kaydedilir (__BASLANGIC__ isareti) - boylece
  kurulumda gecmis uyarilarin hepsi kullanicilara yagmaz. Bir kaynak o calismada cekilemezse (None) o tur ATLANIR
  ve baslangic isareti konmaz.

Tetikleme: kap_risk_tarama.yml, KAP taramasindan hemen sonra (cron-job.org ~15 dk) bu modulu calistirir.
Tum alicilar tek bir ozet e-posta alir (bir calismada birden cok olay varsa tek mail).
"""
import sys
import smtplib
import argparse
import datetime
import html as _html
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

RETRY_SAAT = 6
TEMETTU_GERI_GUN = 10
TEMETTU_DETAY_LIMIT = 15
TURLER = ("risk", "tedbir", "halkaarz", "xharz", "temettu")
TUR_BASLIK = {
    "risk": "KAP uyarısı",
    "tedbir": "Piyasa tedbiri",
    "halkaarz": "Halka arz",
    "xharz": "Borsada işlem görmeye başlayan halka arz",
    "temettu": "Temettü",
}
SEVIYE_ETIKET = {"AGIR": "Ağır", "ORTA": "Orta"}
UYGULAMA_URL = "https://trendsurf-optima.streamlit.app"


def _baslangic_anahtari(tur: str) -> str:
    return f"__BASLANGIC__:{tur}"


def _kod_goster(t: str) -> str:
    t = str(t or "")
    return f"Fon {t[2:]}" if t.startswith("F:") else t


def _demetler(rows) -> list:
    """db._CompatRow (dict alt sinifi) satirlarini duz demete cevirir - dogrudan acilim (for a, b in rows)
    anahtarlari verirdi."""
    return [tuple(r.values()) if hasattr(r, "values") else tuple(r) for r in rows]


def _tarih_anahtari(v) -> str:
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime("%Y%m%d%H%M") if isinstance(v, datetime.datetime) else v.strftime("%Y%m%d")
    return str(v or "")[:16].replace("-", "").replace(":", "").replace(" ", "").replace("T", "")


# ---------------------------------------------------------------------------
# Olay toplayicilar (her biri: liste ya da kaynak okunamadiysa None)
# ---------------------------------------------------------------------------
def risk_olaylari(conn):
    try:
        rows = conn.execute(
            "SELECT ticker, kural, seviye, ad, baslik, gonderim_tarihi, bitis_tarihi, ozet "
            "FROM kap_risk_uyari WHERE seviye IN ('AGIR','ORTA')").fetchall()
        rows = _demetler(rows)
    except Exception as e:
        print(f"[bildirim_eposta] risk okunamadi: {e}")
        return None
    sonuc = []
    for ticker, kural, seviye, ad, baslik, gtar, btar, ozet in rows:
        etiket = SEVIYE_ETIKET.get(seviye, seviye)
        sonuc.append({
            "tur": "risk",
            "anahtar": f"RISK:{ticker}:{kural}:{_tarih_anahtari(gtar)}",
            "baslik": f"{_kod_goster(ticker)} - {ad or kural} ({etiket} seviye)",
            "ozet": (ozet or baslik or "")[:400],
            "url": "",
        })
    return sonuc


def tedbir_olaylari(conn):
    try:
        rows = conn.execute(
            "SELECT eslesme_turu, deger, kategori, tedbir_turu, kaynak_aciklama, eklenme_tarihi "
            "FROM piyasa_tedbir_listesi WHERE aktif = TRUE").fetchall()
        rows = _demetler(rows)
    except Exception as e:
        print(f"[bildirim_eposta] tedbir okunamadi: {e}")
        return None
    sonuc = []
    for esl, deger, kat, tur_, aciklama, tar in rows:
        sonuc.append({
            "tur": "tedbir",
            "anahtar": f"TEDBIR:{esl}:{deger}:{_tarih_anahtari(tar)}",
            "baslik": f"{deger} - {tur_}" + (f" ({kat})" if kat else ""),
            "ozet": (aciklama or "")[:400],
            "url": "",
        })
    return sonuc


def halkaarz_olaylari(izahname_satirlari):
    """izahname_satirlari: upcoming_ipo_client.izahname_listesi_hafif() ciktisi (ya da None)."""
    if izahname_satirlari is None:
        return None
    sonuc = []
    for s in izahname_satirlari:
        sonuc.append({
            "tur": "halkaarz",
            "anahtar": f"HA:{s['disclosure_index']}",
            "baslik": f"{s.get('Sirket') or s.get('Kod') or 'Şirket'} - {s.get('Durum', '')}",
            "ozet": (s.get("Konu") or "")[:300],
            "url": s.get("Detay_URL", ""),
        })
    return sonuc


def xharz_olaylari(xharz_satirlari):
    """xharz_satirlari: halka_arz_client._fetch_from_kap_rsc() ciktisi (ya da bos/None)."""
    if not xharz_satirlari:
        return None
    sonuc = []
    for r in xharz_satirlari:
        t = str(r.get("Ticker") or "").upper()
        if not t:
            continue
        sonuc.append({
            "tur": "xharz",
            "anahtar": f"XHARZ:{t}",
            "baslik": f"{t} - {r.get('Şirket', '')} XHARZ (Halka Arz Endeksi) listesine girdi",
            "ozet": "Şirket borsada işlem görmeye başlamış olarak KAP Halka Arz Endeksi üyeleri arasında görünüyor.",
            "url": r.get("KAP_URL", "") or "",
        })
    return sonuc


def temettu_olaylari(ham_kayitlar, detay_getir=None, limit=TEMETTU_DETAY_LIMIT, bilinen=None):
    """ham_kayitlar: temettu_client._kar_payi_ham_kayitlar() ciktisi (ya da None).
    detay_getir(idx, ticker) -> {"brut_tl","ex_date",...}: sadece `bilinen` anahtar kumesinde OLMAYAN
    (yani gercekten yeni) olaylar icin ve en fazla `limit` kez cagrilir."""
    if ham_kayitlar is None:
        return None
    import re
    bilinen = bilinen or set()
    sonuc, detay_sayac = [], 0
    for rec in ham_kayitlar:
        idx = rec.get("disclosureIndex")
        if not idx:
            continue
        kodlar = [c.strip().upper() for c in re.split(r"[,\s]+", f"{rec.get('stockCodes') or ''},{rec.get('relatedStocks') or ''}")
                  if 2 <= len(c.strip()) <= 8]
        kodlar = list(dict.fromkeys(kodlar))
        kod = kodlar[0] if kodlar else ""
        anahtar = f"TEMETTU:{idx}"
        ozet = (rec.get("summary") or rec.get("title") or "Kar Payı Dağıtım İşlemlerine İlişkin Bildirim")
        if detay_getir and kod and anahtar not in bilinen and detay_sayac < limit:
            detay_sayac += 1
            try:
                d = detay_getir(idx, kod) or {}
                parca = []
                if d.get("brut_tl"):
                    parca.append(f"Hisse başı brüt {d['brut_tl']:.4f} TL".replace(".", ","))
                if d.get("ex_date"):
                    parca.append(f"Ödeme/ex tarihi {d['ex_date']}")
                if parca:
                    ozet = " | ".join(parca)
            except Exception as e:
                print(f"[bildirim_eposta] temettu detayi alinamadi ({kod}/{idx}): {e}")
        sonuc.append({
            "tur": "temettu",
            "anahtar": anahtar,
            "baslik": f"{kod or 'Şirket'} - Kar payı dağıtımı bildirimi" + (f" ({rec.get('publishDate')})" if rec.get("publishDate") else ""),
            "ozet": str(ozet)[:300],
            "url": f"https://www.kap.org.tr/tr/Bildirim/{idx}",
        })
    return sonuc


# ---------------------------------------------------------------------------
# Veritabani: olay kaydi, baslangic, alicilar, rezervasyon
# ---------------------------------------------------------------------------
def kaydet_ve_yeni_olaylar(conn, tur: str, adaylar):
    """adaylar None ise (kaynak okunamadi) -> ([], False). Ilk calismada sessizce kaydeder -> ([], True).
    Aksi halde veritabaninda olmayan olaylari kaydeder ve dondurur."""
    if adaylar is None:
        return [], False
    mevcut = {r[0] for r in conn.execute(
        "SELECT anahtar FROM bildirim_eposta_olay WHERE tur=?", (tur,)).fetchall()}
    ilk = _baslangic_anahtari(tur) not in mevcut
    yeni = [a for a in adaylar if a["anahtar"] not in mevcut]
    if ilk:
        for a in yeni:
            conn.execute(
                "INSERT INTO bildirim_eposta_olay (anahtar, tur, baslik, ozet, url, ilk_tohum) "
                "VALUES (?,?,?,?,?,TRUE) ON CONFLICT DO NOTHING",
                (a["anahtar"], tur, a["baslik"], a["ozet"], a["url"]))
        conn.execute(
            "INSERT INTO bildirim_eposta_olay (anahtar, tur, baslik, ozet, url, ilk_tohum) "
            "VALUES (?,?,?,?,?,TRUE) ON CONFLICT DO NOTHING",
            (_baslangic_anahtari(tur), tur, "baslangic", "", ""))
        conn.commit()
        print(f"[bildirim_eposta] {tur}: ilk calisma - {len(yeni)} mevcut olay sessizce kaydedildi (mail yok).")
        return [], True
    kesin = []
    for a in yeni:
        cur = conn.execute(
            "INSERT INTO bildirim_eposta_olay (anahtar, tur, baslik, ozet, url, ilk_tohum) "
            "VALUES (?,?,?,?,?,FALSE) ON CONFLICT DO NOTHING",
            (a["anahtar"], tur, a["baslik"], a["ozet"], a["url"]))
        if cur.rowcount == 1:
            kesin.append(a)
    conn.commit()
    if kesin:
        print(f"[bildirim_eposta] {tur}: {len(kesin)} YENI olay.")
    return kesin, True


def alicilari_oku(conn):
    """email_settings kaydi olan, aktif kullanicilar -> [(user_id, email)]."""
    try:
        rows = conn.execute(
            "SELECT u.id, u.email FROM email_settings es JOIN users u ON u.id = es.user_id "
            "WHERE u.email IS NOT NULL AND u.email <> '' "
            "AND COALESCE(u.is_active::text, '1') IN ('1','true','t')").fetchall()
        rows = _demetler(rows)
    except Exception as e:
        print(f"[bildirim_eposta] alici listesi okunamadi: {e}")
        return []
    gorulen, sonuc = set(), []
    for uid, em in rows:
        if uid in gorulen:
            continue
        gorulen.add(uid)
        sonuc.append((uid, str(em).strip()))
    return sonuc


def bekleyen_olaylar(conn, user_id: int, retry_saat: int = RETRY_SAAT):
    """Son `retry_saat` saatte kaydedilmis, tohum olmayan ve bu kullaniciya HENUZ rezerve edilmemis olaylar."""
    rows = conn.execute(
        "SELECT o.anahtar, o.tur, o.baslik, o.ozet, o.url FROM bildirim_eposta_olay o "
        "WHERE o.ilk_tohum = FALSE AND o.olay_zamani > NOW() - (? * INTERVAL '1 hour') "
        "AND NOT EXISTS (SELECT 1 FROM bildirim_eposta_gonderim g "
        "WHERE g.user_id = ? AND g.olay_anahtari = o.anahtar) ORDER BY o.olay_zamani, o.anahtar",
        (retry_saat, user_id)).fetchall()
    rows = _demetler(rows)
    return [{"anahtar": a, "tur": t, "baslik": b, "ozet": oz, "url": u} for a, t, b, oz, u in rows]


def rezerve_et(conn, user_id: int, olaylar) -> list:
    """Atomik rezervasyon: sadece bu calismanin kazandigi olaylari dondurur."""
    kazanilan = []
    for o in olaylar:
        cur = conn.execute(
            "INSERT INTO bildirim_eposta_gonderim (user_id, olay_anahtari) VALUES (?,?) ON CONFLICT DO NOTHING",
            (user_id, o["anahtar"]))
        if cur.rowcount == 1:
            kazanilan.append(o)
    conn.commit()
    return kazanilan


def rezervasyonu_birak(conn, user_id: int, olaylar):
    for o in olaylar:
        conn.execute("DELETE FROM bildirim_eposta_gonderim WHERE user_id=? AND olay_anahtari=?",
                     (user_id, o["anahtar"]))
    conn.commit()


# ---------------------------------------------------------------------------
# E-posta
# ---------------------------------------------------------------------------
def konu_olustur(olaylar) -> str:
    sayac = {}
    for o in olaylar:
        sayac[o["tur"]] = sayac.get(o["tur"], 0) + 1
    parca = [f"{n} {TUR_BASLIK[t].lower()}" for t, n in sayac.items() if t in TUR_BASLIK]
    return "TrendSurf Optima - " + ", ".join(parca)


def govde_olustur(olaylar):
    """(html, duz_metin)"""
    gruplar = {}
    for o in olaylar:
        gruplar.setdefault(o["tur"], []).append(o)
    html_parca, txt_parca = [], []
    for tur in TURLER:
        lst = gruplar.get(tur)
        if not lst:
            continue
        html_parca.append(f"<h3 style='margin:18px 0 6px;font-size:15px;color:#1a3a5c;'>{_html.escape(TUR_BASLIK[tur])}</h3><ul style='margin:0;padding-left:18px;'>")
        txt_parca.append(f"\n{TUR_BASLIK[tur]}")
        for o in lst:
            b = _html.escape(o["baslik"])
            if o.get("url"):
                b = f"<a href='{_html.escape(o['url'])}' style='color:#1a5fb4;'>{b}</a>"
            oz = f"<br><span style='color:#555;font-size:13px;'>{_html.escape(o['ozet'])}</span>" if o.get("ozet") else ""
            html_parca.append(f"<li style='margin-bottom:8px;'>{b}{oz}</li>")
            txt_parca.append(f"- {o['baslik']}" + (f"\n  {o['ozet']}" if o.get("ozet") else "") + (f"\n  {o['url']}" if o.get("url") else ""))
        html_parca.append("</ul>")
    html = (
        "<html><body style='font-family:Arial,Helvetica,sans-serif;color:#222;max-width:640px;margin:auto;'>"
        "<h2 style='color:#0d2a47;margin-bottom:4px;'>TrendSurf Optima</h2>"
        "<div style='color:#555;font-size:13px;'>Yeni bildirimler</div>"
        + "".join(html_parca) +
        f"<p style='margin-top:22px;font-size:12px;color:#777;'>Kaynak: KAP (Kamuyu Aydınlatma Platformu) ve onaylanmış SPK tedbir listesi. "
        f"Bu e-posta yatırım tavsiyesi değildir. Detaylar: <a href='{UYGULAMA_URL}'>{UYGULAMA_URL}</a></p>"
        "</body></html>")
    txt = "TrendSurf Optima - Yeni bildirimler\n" + "\n".join(txt_parca) + \
          "\n\nKaynak: KAP ve onaylanmış SPK tedbir listesi. Yatırım tavsiyesi değildir.\n"
    return html, txt


def smtp_gonder(to: str, konu: str, html: str, txt: str) -> bool:
    """Gercek gonderim (peak_alert_emailer ile ayni SMTP ayarlari: env SMTP_USER/SMTP_PASS)."""
    from peak_alert_emailer import _get_smtp_config
    cfg = _get_smtp_config()
    if not cfg.get("smtp_user") or not cfg.get("smtp_pass"):
        print("[bildirim_eposta] SMTP ayari eksik (SMTP_USER/SMTP_PASS) - gonderilemedi.")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = konu
    msg["From"] = cfg["smtp_user"]
    msg["To"] = to
    msg.attach(MIMEText(txt, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=30) as s:
        s.ehlo()
        s.starttls()
        s.login(cfg["smtp_user"], cfg["smtp_pass"])
        s.sendmail(cfg["smtp_user"], to, msg.as_string())
    return True


# ---------------------------------------------------------------------------
# Ana akis
# ---------------------------------------------------------------------------
def kaynaklari_topla(conn, turler):
    """Her tur icin {tur: adaylar|None}. Agir ag cagrilari sadece istenen turler icin yapilir."""
    sonuc = {}
    if "risk" in turler:
        sonuc["risk"] = risk_olaylari(conn)
    if "tedbir" in turler:
        sonuc["tedbir"] = tedbir_olaylari(conn)
    if "halkaarz" in turler:
        try:
            import upcoming_ipo_client as _u
            sonuc["halkaarz"] = halkaarz_olaylari(_u.izahname_listesi_hafif())
        except Exception as e:
            print(f"[bildirim_eposta] halka arz kaynagi hatasi: {e}")
            sonuc["halkaarz"] = None
    if "xharz" in turler:
        try:
            import halka_arz_client as _h
            sonuc["xharz"] = xharz_olaylari(_h._fetch_from_kap_rsc())
        except Exception as e:
            print(f"[bildirim_eposta] XHARZ kaynagi hatasi: {e}")
            sonuc["xharz"] = None
    if "temettu" in turler:
        try:
            import temettu_client as _t
            ham = _t._kar_payi_ham_kayitlar(TEMETTU_GERI_GUN)
            bilinen = {r[0] for r in conn.execute(
                "SELECT anahtar FROM bildirim_eposta_olay WHERE tur='temettu'").fetchall()}
            detay_cache = {}
            sonuc["temettu"] = temettu_olaylari(
                ham, detay_getir=lambda idx, kod: _t._kar_payi_detay_getir(idx, kod, detay_cache),
                bilinen=bilinen)
        except Exception as e:
            print(f"[bildirim_eposta] temettu kaynagi hatasi: {e}")
            sonuc["temettu"] = None
    return sonuc


def calistir(conn, turler=TURLER, gonderici=smtp_gonder, kaynaklar=None, kuru=False) -> dict:
    """Donus: {"yeni": n, "gonderilen": mail sayisi, "basarisiz": n}. `kaynaklar` verilirse (test) ag/DB kaynagi
    okunmaz; `kuru` True ise olaylar kaydedilmez/gonderilmez, sadece sayilir."""
    kaynaklar = kaynaklari_topla(conn, turler) if kaynaklar is None else kaynaklar
    toplam_yeni = 0
    for tur in turler:
        if tur not in kaynaklar:
            continue
        if kuru:
            print(f"[bildirim_eposta] (kuru) {tur}: {0 if kaynaklar[tur] is None else len(kaynaklar[tur])} aday")
            continue
        yeni, _ = kaydet_ve_yeni_olaylar(conn, tur, kaynaklar[tur])
        toplam_yeni += len(yeni)
    sonuc = {"yeni": toplam_yeni, "gonderilen": 0, "basarisiz": 0}
    if kuru:
        return sonuc
    for uid, email in alicilari_oku(conn):
        bekleyen = bekleyen_olaylar(conn, uid)
        if not bekleyen:
            continue
        kazanilan = rezerve_et(conn, uid, bekleyen)
        if not kazanilan:
            continue
        html, txt = govde_olustur(kazanilan)
        try:
            ok = gonderici(email, konu_olustur(kazanilan), html, txt)
        except Exception as e:
            print(f"[bildirim_eposta] gonderim hatasi (user={uid}): {e}")
            ok = False
        if ok:
            sonuc["gonderilen"] += 1
            print(f"[bildirim_eposta] user={uid}: {len(kazanilan)} olay gonderildi.")
        else:
            rezervasyonu_birak(conn, uid, kazanilan)
            sonuc["basarisiz"] += 1
    return sonuc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tur", default=",".join(TURLER), help="virgulle: " + ",".join(TURLER))
    ap.add_argument("--kuru", action="store_true", help="kaydetme/gonderme yok, sadece say")
    a = ap.parse_args(argv)
    turler = tuple(t for t in a.tur.split(",") if t in TURLER)
    import db
    db.toplu_mod_ac()
    try:
        db.init_db()
        conn = db.get_conn()
        sonuc = calistir(conn, turler, kuru=a.kuru)
        print(f"[bildirim_eposta] Bitti: {sonuc}")
        return 0
    except Exception as e:
        print(f"[bildirim_eposta] HATA: {e}")
        return 1
    finally:
        db.toplu_mod_kapat()


if __name__ == "__main__":
    sys.exit(main())
