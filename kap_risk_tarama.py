# -*- coding: utf-8 -*-
"""
kap_risk_tarama.py - TrendSurf Optima
KAP'in TOPLU bildirim listesinden (tum sirketler) risk uretebilecek bildirimleri toplar, arsivler ve
hisse bazli guncel risk listesini `kap_risk_uyari` tablosuna yazar. app.py load_universe() bu tabloyu
okuyup etiket + skor dusurme uygular.

v2.0.7.373 (8 Ekim 2026, Bahri'nin bulgusu - ENERY). Bkz. kap_risk.py (siniflandirma ilkeleri).

VERI KAYNAGI (CANLI dogrulandi, 8 Ekim 2026; kimlik dogrulama GEREKTIRMEZ):
    POST https://www.kap.org.tr/tr/api/disclosure/members/byCriteria
         {"fromDate":"YYYY-MM-DD","toDate":"YYYY-MM-DD","memberTypes":["IGS"], ...}
  Tum sirketlerin o tarih araligindaki bildirimlerini TEK istekte JSON olarak verir (publishDate, kapTitle=
  gonderen, subject=bildirim turu, summary=kisa baslik, stockCodes=gonderen sirket kodu, relatedStocks=
  konu olan sirketler, disclosureIndex=bildirim no). SINIR: tek yanit EN FAZLA 2000 kayit - bu yuzden
  kisa pencerelerle cekilir, 2000'e ulasan pencere ikiye bolunur.
  Tam metin: https://www.kap.org.tr/tr/Bildirim/{disclosureIndex} sayfasi (metin sayfaya kacisli HTML
  olarak gomulu) - SADECE VBTS (asama + bitis tarihi) ve sermaye bildirimleri (tur) icin cekilir.
  Bu yontem, sirket basina yillik dosya cekmekten (770 istek, KAP'ta HTTP 429 hiz siniri) cok daha hafif.

Akis:
  1. Arsiv bossa son 130 gunu, doluysa son 4 gunu cek (hafta sonu + ust uste binme).
  2. Sadece risk uretebilecek bildirimleri (kap_risk.ilgili_mi) ve arsivde olmayanlari sec; gerekenlerin
     tam metnini cek; arsive yaz.
  3. Arsivin tamamindan riskleri SIFIRDAN hesapla ve `kap_risk_uyari`'yi tek islemde degistir.
  KAP erisilemezse (hata/429) hicbir sey silinmez: tablo bir onceki durumda kalir.

Kullanim:
    python kap_risk_tarama.py                       # veritabanina yazar
    python kap_risk_tarama.py --kuru --gun 40 --cikti x.json   # DB'ye yazmaz (test)
"""
import argparse
import datetime
import json
import os
import re
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kap_risk

KAP_LISTE_URL = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
KAP_DETAY_URL = "https://www.kap.org.tr/tr/Bildirim/{}"
KAP_UST_SINIR = 2000          # KAP tek yanitta en fazla bu kadar kayit doner
ARSIV_GUN = 130               # arsiv saklama (en uzun risk penceresi 120 gun)
ILK_YUKLEME_GUN = 130
ARTIMLI_GUN = 4
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Origin": "https://www.kap.org.tr",
    "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu",
}


class KapHata(Exception):
    """KAP erisilemedi / beklenmedik yanit - tarama iptal, DB DEGISMEZ."""


class Istemci:
    """KAP'a nazik HTTP istemcisi: istekler arasi bekleme, 429/5xx'te geri cekilme."""

    def __init__(self, bekle: float = 1.0):
        self.bekle = float(bekle)
        self.s = requests.Session()
        self.s.headers.update(_HEADERS)
        self.son = 0.0
        self.n429 = 0
        self.n_istek = 0

    def _bekle(self):
        fark = time.time() - self.son
        if fark < self.bekle:
            time.sleep(self.bekle - fark)
        self.son = time.time()

    def istek(self, yontem: str, url: str, deneme: int = 4, **kw) -> requests.Response:
        son = ""
        for i in range(1, deneme + 1):
            self._bekle()
            self.n_istek += 1
            try:
                r = self.s.request(yontem, url, timeout=90, **kw)
            except Exception as e:
                son = f"ag hatasi: {e}"
                time.sleep(4 * i)
                continue
            if r.status_code == 200:
                return r
            son = f"HTTP {r.status_code}"
            if r.status_code in (429, 502, 503, 504):
                self.n429 += 1
                try:
                    ra = float(r.headers.get("Retry-After", ""))
                except ValueError:
                    ra = 0.0
                bekleme = min(max(ra, 20.0 * i), 120.0)
                print(f"[kap_risk_tarama] {son} - {bekleme:.0f} sn bekleniyor")
                time.sleep(bekleme)
                continue
            break
        raise KapHata(f"{url}: {son}")


def _tarihi_coz(s: str) -> datetime.datetime:
    return datetime.datetime.strptime(s.strip(), "%d.%m.%Y %H:%M:%S")


def normallestir(x: dict) -> dict:
    """KAP liste kaydi -> kap_risk bildirim sozlugu."""
    return {
        "id": int(x["disclosureIndex"]),
        "tarih": _tarihi_coz(x["publishDate"]),
        "gonderen": (x.get("kapTitle") or "").strip(),
        "konu": (x.get("subject") or "").strip(),
        "ozet": re.sub(r"\s+", " ", (x.get("summary") or "")).strip(),
        "gonderen_kodlar": kap_risk.kodlari_ayir(x.get("stockCodes")),
        "ilgili_kodlar": kap_risk.kodlari_ayir(x.get("relatedStocks")),
        "metin": "",
    }


def liste_cek(ist: Istemci, bas: datetime.date, bit: datetime.date) -> list:
    """[bas, bit] araligindaki TUM bildirimler. 2000'e ulasirsa pencere ikiye bolunur."""
    govde = {"fromDate": bas.isoformat(), "toDate": bit.isoformat(), "memberTypes": ["IGS"],
             "mkkMemberOidList": [], "inactiveMkkMemberOidList": [], "disclosureClass": "",
             "subjectList": [], "isLate": "", "term": "", "year": "", "fromSrc": False,
             "srcCategory": "", "discIndex": []}
    r = ist.istek("POST", KAP_LISTE_URL, json=govde,
                  headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        veri = r.json()
    except Exception as e:
        raise KapHata(f"liste JSON degil: {e}")
    if not isinstance(veri, list):
        raise KapHata(f"beklenmeyen liste yaniti: {str(veri)[:120]}")
    if len(veri) >= KAP_UST_SINIR:
        if bas == bit:
            print(f"[kap_risk_tarama] UYARI: {bas} tek gunde {len(veri)} kayit (tavan) - bazi bildirimler eksik olabilir.")
        else:
            orta = bas + (bit - bas) // 2
            return liste_cek(ist, bas, orta) + liste_cek(ist, orta + datetime.timedelta(days=1), bit)
    return veri


def detay_metni(html: str) -> str:
    """/tr/Bildirim/{no} sayfasindan bildirim metni. Metin sayfaya kacisli HTML (\\u003c ...) gomulu."""
    t = (html or "").replace("\\u003c", "<").replace("\\u003e", ">").replace('\\"', '"') \
        .replace("\\n", " ").replace("\\u0026", "&")
    i = t.find("text-block-value")
    if i < 0:
        i = t.find("Özet Bilgi")
    if i < 0:
        return ""
    return kap_risk.temiz_metin(t[max(0, i - 100): i + 14000], 5000)


def metin_cek(ist: Istemci, bno: int) -> str:
    r = ist.istek("GET", KAP_DETAY_URL.format(bno), deneme=3)
    return detay_metni(r.text)


def bildirimleri_topla(ist: Istemci, gun: int, bugun: datetime.date, mevcut: set) -> list:
    """Son `gun` gunun listesi -> arsivde olmayan, ilgili bildirimler (gerekenlerin metniyle)."""
    # 4 gunluk pencereler (hafta ici ~230 bildirim/gun -> ~900); 2000'e ulasan otomatik bolunur
    yeni = []
    bit = bugun
    baslangic = bugun - datetime.timedelta(days=gun)
    toplam = 0
    while bit >= baslangic:
        bas = max(baslangic, bit - datetime.timedelta(days=3))
        for x in liste_cek(ist, bas, bit):
            toplam += 1
            try:
                b = normallestir(x)
            except Exception:
                continue
            if b["id"] in mevcut or not kap_risk.ilgili_mi(b):
                continue
            yeni.append(b)
            mevcut.add(b["id"])
        bit = bas - datetime.timedelta(days=1)
    print(f"[kap_risk_tarama] liste: {toplam} bildirim tarandi, {len(yeni)} yeni ilgili bildirim.")
    for b in yeni:
        if kap_risk.metin_gerekli_mi(b):
            try:
                b["metin"] = metin_cek(ist, b["id"])
            except KapHata as e:
                print(f"[kap_risk_tarama] {b['id']} metni alinamadi ({e}); basliktan siniflandirilacak.")
    return yeni


def calistir(args) -> int:
    bugun = datetime.date.today()
    yaz = not args.kuru
    ist = Istemci(args.bekle)
    arsiv = []
    mevcut = set()
    if yaz:
        import db
        db.toplu_mod_ac()
        db.init_db()
    try:
        if yaz:
            mevcut = db.kap_risk_bildirim_idleri(ARSIV_GUN + 10)
            arsiv = db.kap_risk_bildirimleri_oku(ARSIV_GUN)
        gun = args.gun or (ARTIMLI_GUN if mevcut else ILK_YUKLEME_GUN)
        print(f"[kap_risk_tarama] arsiv: {len(mevcut)} bildirim; son {gun} gun cekilecek.")
        yeni = bildirimleri_topla(ist, gun, bugun, mevcut)
        if yaz:
            for b in yeni:
                db.kap_risk_bildirim_ekle(b)
            db.kap_risk_bildirim_temizle(ARSIV_GUN + 10)
        tum = arsiv + yeni
        riskler = kap_risk.riskleri_hesapla(tum, bugun)
        sayac = {"AGIR": 0, "ORTA": 0, "BILGI": 0}
        for t, lst in sorted(riskler.items()):
            for r in lst:
                sayac[r["seviye"]] += 1
            if any(r["seviye"] != "BILGI" for r in lst):
                print(f"[kap_risk_tarama] {t}: " + ", ".join(f"{r['seviye']}:{r['kural']}(->{r['bitis']})" for r in lst))
        if yaz:
            if not db.kap_risk_hepsini_yaz(riskler):
                print("[kap_risk_tarama] HATA: risk tablosu yazilamadi.")
                return 1
        if args.cikti:
            with open(args.cikti, "w", encoding="utf-8") as f:
                json.dump({"tarih": bugun.isoformat(), "bildirim_sayisi": len(tum),
                           "riskler": {t: [dict(r, tarih=r["tarih"].isoformat(), bitis=r["bitis"].isoformat())
                                           for r in lst] for t, lst in riskler.items()}},
                          f, ensure_ascii=False, indent=1)
        print(f"[kap_risk_tarama] Bitti. arsiv+yeni={len(tum)} bildirim | {len(riskler)} hisse | "
              f"AGIR={sayac['AGIR']} ORTA={sayac['ORTA']} BILGI={sayac['BILGI']} | "
              f"istek={ist.n_istek} 429/5xx={ist.n429}")
        return 0
    except KapHata as e:
        print(f"[kap_risk_tarama] KAP'a ULASILAMADI: {e} - risk tablosu DEGISMEDI.")
        return 1
    finally:
        if yaz:
            db.toplu_mod_kapat()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true", help="DB'ye yazma/okuma yapma")
    ap.add_argument("--cikti", default="", help="sonucu JSON dosyasina yaz")
    ap.add_argument("--gun", type=int, default=0, help="kac gun geriye cekilecek (0 = otomatik)")
    ap.add_argument("--bekle", type=float, default=1.0, help="istekler arasi bekleme (sn)")
    return calistir(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
