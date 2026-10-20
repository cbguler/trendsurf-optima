# -*- coding: utf-8 -*-
"""
msci_izleme.py - MSCI'in KENDI "Index Announcements" listesini tarar; Turkiye ile ilgili duyurulari
arsivler (msci_duyuru tablosu), Admin'e e-posta atar ve uygulamadaki "MSCI DUYURUSU" seridine
(piyasa_rejimi.py) aktarir.

v2.0.7.429 (20 Ekim 2026, Bahri'nin talebi - "MSCI'in Turkiye'ye iliskin kararlarini da gunluk takip
etmek gerekiyor"). Birincil kaynak: MSCI'in herkese acik duyuru servisi
  https://app2.msci.com/webapp/index_ann/Announcement?doc_type=ANNOUNCEMENT&lang=en&prod_type=STANDARD&visibility=public&format=html
(sunucu tarafinda uretilen HTML; tarih + baslik + DocGet?pub_key=... baglantisi; pub_key duyuru basina
SABIT - iki ayri cekimde ayni). Her duyurunun tam metni DocGet ile alinabilir. Haber sitelerinden
(ikincil kaynak) OKUNMAZ.

Ilgili sayma kurali (YORUM YOK - yalniz eslesme):
  1. Baslikta TURKEY / TURKIYE / TURKISH gecerse ya da baslik 'TR: <SIRKET>' ise (MSCI sirket duyurulari ulke koduyla baslar).
  2. Baslik piyasa siniflandirmasi / yeniden siniflandirma / istisare / serbest dolasim / endeks
     degerlendirmesi konulu ise duyurunun TAM METNI indirilir; metinde Turkey/Turkiye/Turkish geciyorsa.
     Seride gosterilen "alinti", o metindeki Turkiye gecen ilk cumledir (AYNEN, yorumlanmadan).

Calisma: ilk calistirmada (tablo bos) listedeki her sey "bildirildi" sayilarak kaydedilir (baz cizgisi:
e-posta yagmuru olmasin); sonraki her calismada yalniz YENI pub_key'ler islenir. Liste "en son" duyurulari
verir (yaklasik 20); calismalar arasi 20'den fazla duyuru gelirse eskiler kacabilir - bu yuzden her 3 saatte
bir calisir.

Kullanim:  python msci_izleme.py [--kuru]
Cikis kodu: 0 = tamam; 1 = liste cekilemedi/cozulemedi (MSCI sayfa bicimi degismis olabilir).
"""
import argparse
import html as _html
import os
import re
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = "https://app2.msci.com/webapp/index_ann/"
LISTE_URL = (BASE + "Announcement?doc_type=ANNOUNCEMENT&lang=en&prod_type=STANDARD"
             "&visibility=public&format=html")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
AYLAR = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
         "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}

TURKIYE_RE = re.compile(r"T[UÜ]RK(?:EY|IYE|İYE|ISH)", re.IGNORECASE)
# Basligi bunlardan birini iceren duyurunun TAM METNINE bakilir (Turkiye adi basliktan gecmese de
# yillik siniflandirma / endeks degerlendirmesi metinlerinde Turkiye anilabilir).
METIN_KONULARI_RE = re.compile(
    r"MARKET CLASSIFICATION|RECLASSIF|CONSULTATION|FREE FLOAT|FOREIGN INCLUSION|INDEX REVIEW|"
    r"NUMBER OF SHARES|STANDALONE|FRONTIER|EMERGING MARKET", re.IGNORECASE)


def _tr_upper_norm(s):
    return (s or "").replace("İ", "I").replace("ı", "i")


TR_SIRKET_RE = re.compile(r"^\s*TR\s*:")   # MSCI sirket duyurulari "<ULKE KODU>: <SIRKET>" basligiyla gelir


def baslikta_turkiye_mi(baslik):
    return bool(TURKIYE_RE.search(_tr_upper_norm(baslik)) or "TÜRKİYE" in (baslik or "").upper()
                or TR_SIRKET_RE.search(baslik or ""))


def metin_konusu_mu(baslik):
    return bool(METIN_KONULARI_RE.search(baslik or ""))


def liste_ayikla(html_metni):
    """Duyuru listesi HTML'inden [{tarih (date), baslik, pub_key, url}] (sayfadaki sirayla).
    Yapi: <td>15 Oct 2026</td><td><a href="DocGet?pub_key=XXX&lang=en&format=html">BASLIK</a></td>"""
    out = []
    kalip = re.compile(
        r"<td[^>]*>\s*(\d{1,2})\s+([A-Za-z]{3})\w*\s+(\d{4})\s*</td>\s*"
        r"<td[^>]*>\s*<a[^>]+href=\"([^\"]*pub_key=([^&\"]+)[^\"]*)\"[^>]*>(.*?)</a>",
        re.IGNORECASE | re.DOTALL)
    for g, ay, y, href, key, baslik in kalip.findall(html_metni or ""):
        ay_no = AYLAR.get(ay.upper())
        if not ay_no:
            continue
        try:
            tarih = date(int(y), ay_no, int(g))
        except ValueError:
            continue
        baslik = _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", baslik))).strip()
        href = _html.unescape(href)
        url = href if href.startswith("http") else BASE + href
        out.append({"tarih": tarih, "baslik": baslik, "pub_key": key, "url": url})
    return out


def metni_temizle(html_metni):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html_metni or "", flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</tr>|</li>", ". ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return _html.unescape(re.sub(r"\s+", " ", s)).strip()


def turkiye_alintisi(metin, baslik=None):
    """Metindeki Turkiye/Turkish gecen ILK cumle (AYNEN, en fazla 400 karakter) ya da None.
    `baslik` verilirse metnin basligin SON tekrarindan sonraki kismi taranir (sayfa ustbilgisi
    - 'STANDARD ANNOUNCEMENTS - <tarih>' - ve basligin kendisi alinti sayilmasin)."""
    if baslik:
        i = (metin or "").upper().rfind(baslik.upper())
        if i >= 0:
            metin = metin[i + len(baslik):].strip()
    for cumle in re.split(r"(?<=[.!?])\s+", metin or ""):
        if TURKIYE_RE.search(_tr_upper_norm(cumle)):
            c = cumle.strip()
            return c if len(c) <= 400 else c[:397] + "..."
    return None


def degerlendir(duyuru, metin_getir):
    """(ilgili, neden, alinti). metin_getir(url) -> temiz metin (yalniz gerektiginde cagrilir)."""
    b = duyuru["baslik"]
    if baslikta_turkiye_mi(b):
        alinti = None
        try:
            alinti = turkiye_alintisi(metin_getir(duyuru["url"]), b)
        except Exception as e:
            print(f"[msci] metin alinamadi ({b[:60]}): {type(e).__name__}: {str(e)[:120]}")
        return True, ("baslikta TR: (Turkiye sirket duyurusu)" if TR_SIRKET_RE.search(b) else "baslikta Turkiye geciyor"), alinti
    if metin_konusu_mu(b):
        try:
            alinti = turkiye_alintisi(metin_getir(duyuru["url"]), b)
        except Exception as e:
            print(f"[msci] metin alinamadi ({b[:60]}): {type(e).__name__}: {str(e)[:120]}")
            return False, "metin alinamadi", None
        if alinti:
            return True, "metinde Turkiye geciyor", alinti
    return False, None, None


def _http_get(url, timeout=30):
    import requests
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def _metin_getir(url):
    return metni_temizle(_http_get(url))


def _eposta_gonder(satirlar):
    """Admin'e ozet e-posta. Basarisizsa False (satirlar 'bildirildi' isaretlenmez, sonraki calismada tekrar)."""
    smtp_user = os.environ.get("SMTP_USER") or None
    smtp_pass = os.environ.get("SMTP_PASS") or None
    smtp_host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    smtp_port = int(os.environ.get("SMTP_PORT") or "587")
    admin = os.environ.get("ADMIN_EMAIL") or None
    if not (smtp_user and smtp_pass and admin):
        print("[msci] SMTP/ADMIN_EMAIL secrets eksik: e-posta atlandi (duyuru uygulamada gorunur).")
        return True   # tekrar tekrar denemenin anlami yok; duyuru zaten seritte
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    govde = []
    for d in satirlar:
        al = f"<blockquote>{_html.escape(d['alinti'])}</blockquote>" if d.get("alinti") else ""
        govde.append(f"<p><b>{_html.escape(d['baslik'])}</b><br>{d['tarih']} - "
                     f"<a href=\"{_html.escape(d['url'])}\">MSCI duyurusunun metni</a> "
                     f"({_html.escape(d.get('neden') or '')}){al}</p>")
    html = (f"<html><body><h3>TrendSurf Optima - MSCI Turkiye duyurusu</h3>{''.join(govde)}"
            "<p style=\"color:#888;font-size:12px\">Baslik ve alinti MSCI'in kendi duyurusundan aynen alinmistir. "
            "Uygulamada Ana Sayfa / BIST / TEFAS ust kisminda 'MSCI DUYURUSU' seridi olarak gorunur; "
            "Optima bu duyuruyu henuz ozetlememistir - Piyasa Rejimi seridinin guncellenmesi icin Claude'a bildirin.</p>"
            "</body></html>")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"MSCI Turkiye: {len(satirlar)} yeni duyuru"
    msg["From"] = smtp_user
    msg["To"] = admin
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"[msci] e-posta gonderildi: {len(satirlar)} duyuru.")
        return True
    except Exception as e:
        print(f"[msci] e-posta gonderilemedi: {type(e).__name__}: {str(e)[:160]}")
        return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true", help="veritabanina yazmaz, sadece loglar")
    args = ap.parse_args(argv)
    print(f"[msci] Baslangic: {datetime.now():%d.%m.%Y %H:%M}")
    try:
        liste = liste_ayikla(_http_get(LISTE_URL))
    except Exception as e:
        print(f"[msci] HATA: duyuru listesi cekilemedi: {type(e).__name__}: {str(e)[:200]}")
        return 1
    if not liste:
        print("[msci] HATA: duyuru listesi cozulemedi (0 satir) - MSCI sayfa bicimi degismis olabilir.")
        return 1
    print(f"[msci] Listede {len(liste)} duyuru (en yeni: {liste[0]['tarih']} - {liste[0]['baslik'][:70]}).")

    if args.kuru:
        for d in liste:
            ilgili, neden, alinti = degerlendir(d, _metin_getir)
            print(f"[msci][kuru] {d['tarih']} ilgili={ilgili} ({neden}) | {d['baslik'][:90]}")
            if alinti:
                print(f"[msci][kuru]    alinti: {alinti[:200]}")
        return 0

    import db
    db.msci_tablosu_hazirla()
    bilinen = db.msci_bilinen_anahtarlar()
    ilk_calisma = len(bilinen) == 0
    yeni = [d for d in liste if d["pub_key"] not in bilinen]
    if ilk_calisma:
        print("[msci] Ilk calisma: mevcut duyurular baz cizgisi olarak kaydedilir (e-posta gonderilmez).")
    print(f"[msci] Yeni duyuru: {len(yeni)}")
    for d in yeni:
        ilgili, neden, alinti = degerlendir(d, _metin_getir)
        db.msci_duyuru_ekle(d["pub_key"], d["tarih"], d["baslik"], d["url"], ilgili, neden, alinti,
                            bildirildi=(ilk_calisma or not ilgili))
        print(f"[msci] {'ILGILI' if ilgili else 'ilgisiz'} {d['tarih']} | {d['baslik'][:90]}")

    bekleyen = db.msci_bildirilmeyenler()
    if bekleyen:
        if _eposta_gonder(bekleyen):
            for d in bekleyen:
                db.msci_bildirildi_isaretle(d["pub_key"])
    print("[msci] Bitti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
