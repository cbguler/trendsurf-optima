# -*- coding: utf-8 -*-
"""
spk_bulten_izleme.py - SPK Kurul Bultenlerini otomatik tarar; fonlarin/hisselerin
islem kapatma, tasfiye, piyasa dolandiriciligi suc duyurusu gibi KARARLARINI tespit edip
Admin onayina sunar (piyasa_tedbir_tespit tablosu). ONAYLANMADAN HICBIR SEY UYGULANMAZ.

v2.0.7.366 (4 Ekim 2026, Bahri'nin talebi - "resmi kaynaklari devreye sok, pop-up onay
penceresi ile onaylayayim"). Tasarim gercek bultenlerden (2026/39-68) cikarildi:

  * Fon krizi (2026/60, /61): "...kurucusu olduğu ve katılma payları TEFAS'ta işlem gören
    tüm yatırım fonlarının ... işleme kapatılmasına" + "aşağıda ünvanlarına yer verilen
    yatırım fonlarının ... tasfiye ettirilmesine" + tam fon unvanlari listesi.
  * Hisse (2026/59, /65, /66): "<Sirket AŞ> (TICKER) hakkında yapılan inceleme sonucunda ...
    suç duyurusu" - ticker parantez icinde.
  * Gonullu tasfiye izinleri ("tasfiye edilmelerine izin verilmesi") rutin ve cok.
  * KALDIRMA ifadeleri SARTLI olabiliyor (2026/67: "işleme açılabileceği") - bu KESIN
    karar DEGIL; duz regex "fonlar acildi" diye yanlis okurdu. Bu yuzden kaldirma sadece
    mevcut aktif kurala baglanir ve sartli dil korumasindan gecer.

Katmanlar (hepsi sirayla; bir aday kuyruga girmek icin TUMUNDEN gecmeli):
  1. Deterministik cikarici (regex + EVREN ESLEMESI) - gercek bultenlerde sinandi.
  2. (Opsiyonel) Yapay zeka ikinci gorus - SADECE anahtar kelime pencerelerini okur, ciktisi
     bultende AYNEN gecen bir alinti ve evrende dogrulanabilir bir varlik adi gerektirir.
  3. Evren dogrulamasi: aday evrende en az 1 varlik etkilemeli, zaten aktif kurallarla
     kapsanmis olmamali, ayni tespit bekliyor/yakin zamanda reddedilmis olmamali.
  4. Insan onayi (app.py'deki pop-up).

Kullanim:  python spk_bulten_izleme.py [--kuru] [--yil 2026] [--bugun YYYY-MM-DD]
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from piyasa_tedbir import (GENIS_ETKI_ESIGI, TEDBIR_ETIKET, esleyen_maske, etki_ozeti,  # noqa: E402
                           kapsanan_maske, sirket_anahtari, sirket_degeri, tr_harf_norm, tr_norm)

LISTE_URL = "https://spk.gov.tr/spk-bultenleri/{yil}-yili-spk-bultenleri"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
AYLAR = {"OCAK": 1, "SUBAT": 2, "MART": 3, "NISAN": 4, "MAYIS": 5, "HAZIRAN": 6, "TEMMUZ": 7,
         "AGUSTOS": 8, "EYLUL": 9, "EKIM": 10, "KASIM": 11, "ARALIK": 12}

ILK_CALISMA_GUN = int(os.environ.get("SPK_ILK_CALISMA_GUN", "14") or 14)   # bundan eski bultenler analiz EDILMEDEN "islendi" sayilir
MAKS_BULTEN = int(os.environ.get("SPK_MAKS_BULTEN", "8") or 8)             # bir calismada en fazla
GUNLUK_AI_BUTCESI = 120                                                    # haber_izleme.py ile PAYLASILAN gunluk limit
AI_MAKS_KARAKTER = 9000
SIRKET_ORANI_ESIGI = 0.8        # sirketin evrendeki fonlarinin >=%80'i listedeyse sirket-seviyesi kural
SIRKET_MIN_FON = 3
MAKS_FON_ADAYI = 25             # bir bultende en fazla bu kadar tekil-fon adayi
REDDEDILEN_SKIP_GUN = 30

# --- tetikleyiciler (tr_harf_norm uzerinde) -------------------------------------------------
KAPATMA_RX = re.compile(r"ISLEME KAPAT(?:ILMASINA|ILDI|ILMISTIR)")
TASFIYE_ZORUNLU_RX = re.compile(r"TASFIYE ETTIRILMESINE|TASFIYESINE KARAR VERILMISTIR")
TASFIYE_IZNI_RX = re.compile(r"TASFIYE EDILME(?:LERINE|SINE) IZIN VERILMESI")
HISSE_RX = re.compile(r"\(([A-Z0-9]{3,6})\) HAKKINDA YAPILAN INCELEME SONUCUNDA")
KALDIRMA_RX = re.compile(r"ISLEME ACILMASINA KARAR|ISLEME ACILMISTIR|ISLEM YASAGININ KALDIRILMASINA|"
                         r"TEDBIR(?:IN|LERIN) KALDIRILMASINA|KAPATILMASI KARARININ KALDIRILMASINA")
SARTLI_RX = re.compile(r"ACILABILE|ACILABILIR|OLABILIR|MUMKUN|BELIRLENECEK|BELIRLENMESI|TARAFINDAN BELIRLE")
AI_PENCERE_RX = re.compile(r"KALDIRIL|ISLEME ACIL|ISLEME KAPAT|TASFIYE ETTIRIL|ISLEM GORMESININ|"
                           r"GECICI OLARAK DURDUR|TEDBIRIN|SUC DUYURU")
BOLUM_SONU_RX = re.compile(r"\d{1,2}\. KURUL KARAR ORGANI|(?<=[A-Z\.] )[B-Z]\. [A-Z]{4,}")


def log(msg):
    print(f"[spk-bulten] {msg}", flush=True)


# ════════════════════════════════════════════════════════════════════════════════════════
# 1) Bulten listesi + PDF metni
# ════════════════════════════════════════════════════════════════════════════════════════
_BULTEN_RX = re.compile(r"BULTEN NO\s*:\s*(\d{4}/\d+)\s*YAYIMLANMA\s*:\s*(\d{1,2})\s+([A-Z]+)\s+(\d{4})")


def bulten_listesi_cek(yil: int, get=None, deneme: int = 3) -> list:
    """[{'no': '2026/68', 'tarih': date, 'url': ...}, ...] YENIDEN ESKIYE."""
    import requests
    from bs4 import BeautifulSoup
    get = get or requests.get
    r, son_hata = None, None
    for n in range(1, deneme + 1):
        try:
            r = get(LISTE_URL.format(yil=yil), headers=HEADERS, timeout=30)
            r.raise_for_status()
            break
        except Exception as e:
            son_hata = e
            r = None
            if n < deneme:
                time.sleep(3 * n)
    if r is None:
        raise RuntimeError(f"SPK bulten listesi alinamadi ({yil}): {son_hata}")
    sonuc, gorulen = [], set()
    for a in BeautifulSoup(r.text, "html.parser").find_all("a", href=True):
        m = _BULTEN_RX.search(tr_norm(a.get_text(" ", strip=True)))
        if not m or m.group(1) in gorulen:
            continue
        ay = AYLAR.get(m.group(3))
        if not ay:
            continue
        href = a["href"]
        if href.startswith("/"):
            href = "https://spk.gov.tr" + href
        gorulen.add(m.group(1))
        sonuc.append({"no": m.group(1), "tarih": date(int(m.group(4)), ay, int(m.group(2))), "url": href})
    sonuc.sort(key=lambda b: b["tarih"], reverse=True)
    return sonuc


def pdf_metni_cek(url: str, get=None) -> str:
    import io
    import pdfplumber
    import requests
    get = get or requests.get
    r = get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    with pdfplumber.open(io.BytesIO(r.content)) as p:
        return "\n".join((pg.extract_text() or "") for pg in p.pages)


# ════════════════════════════════════════════════════════════════════════════════════════
# 2) Evren (dogrulama icin)
# ════════════════════════════════════════════════════════════════════════════════════════
def evren_hazirla(df: pd.DataFrame) -> dict:
    tefas = df[df["Kategori"] == "TEFAS"]
    sirket_fon = {}
    for ad in tefas["Ad"]:
        k = sirket_anahtari(ad)
        if k:
            sirket_fon.setdefault(k, []).append(str(ad))
    fon_adlari = {}
    for ad in tefas["Ad"]:
        nad = tr_norm(ad)
        if len(nad) >= 15:
            fon_adlari[nad] = str(ad)
    bist = set(df[df["Kategori"] == "BIST"]["Ticker"].astype(str).str.upper())
    return {"df": df, "sirket_fon": sirket_fon, "fon_adlari": fon_adlari, "bist": bist}


def _hizala(metin: str):
    """(duz, norm): bosluklar teke inmis metin ve AYNI UZUNLUKTA normallestirilmis hali."""
    duz = re.sub(r"\s+", " ", metin or "")
    n = tr_harf_norm(duz)
    if len(n) != len(duz):                 # savunma: hizalama bozulursa normallestirilmis metinle devam
        n = tr_norm(duz)
        duz = n
    return duz, n


def _kelime_var(metin_norm: str, anahtar: str) -> bool:
    return re.search(r"(?<![A-Z0-9])" + re.escape(anahtar) + r"(?![A-Z0-9])", metin_norm) is not None


def _alinti(duz: str, bas: int, son: int, azami: int = 260) -> str:
    """Bultenden kisa alinti; KELIME ORTASINDAN baslamaz/bitmez."""
    bas0 = max(0, bas)
    s = duz[bas0:son]
    if bas0 > 0 and duz[bas0 - 1] != " " and " " in s:
        s = s[s.index(" ") + 1:]
    if son < len(duz) and duz[son:son + 1] != " " and " " in s:
        s = s.rsplit(" ", 1)[0]
    s = s.strip()
    if len(s) > azami:
        s = s[-azami:]
        s = "..." + (s[s.index(" ") + 1:] if " " in s else s)
    return s


# ════════════════════════════════════════════════════════════════════════════════════════
# 3) Deterministik cikarici
# ════════════════════════════════════════════════════════════════════════════════════════
def _fon_adaylari(eslesen_adlar, tedbir, alinti, evren, kaynak="deterministik"):
    """Eslesen fon unvanlarini aday kurala cevirir: sirketin fonlarinin cogu listedeyse
    SIRKET-seviyesi, degilse tek tek (en fazla MAKS_FON_ADAYI)."""
    adaylar, tekil = [], []
    gruplar = {}
    for ad in eslesen_adlar:
        k = sirket_anahtari(ad)
        gruplar.setdefault(k, []).append(ad)
    for k, adlar in gruplar.items():
        evrendeki = evren["sirket_fon"].get(k, []) if k else []
        if k and len(adlar) >= SIRKET_MIN_FON and len(adlar) >= SIRKET_ORANI_ESIGI * len(evrendeki):
            adaylar.append({"eslesme_turu": "SIRKET_ADI", "deger": sirket_degeri(adlar[0], k), "kategori": "TEFAS",
                            "tedbir_turu": tedbir, "alinti": alinti, "kaynak": kaynak,
                            "gerekce": f"{k.title()} fonlarinin {len(adlar)}/{len(evrendeki)}'si bultende listelenmis"})
        else:
            tekil.extend(adlar)
    for ad in tekil[:MAKS_FON_ADAYI]:
        adaylar.append({"eslesme_turu": "SIRKET_ADI", "deger": str(ad).upper(), "kategori": "TEFAS",
                        "tedbir_turu": tedbir, "alinti": alinti, "kaynak": kaynak,
                        "gerekce": "Fon unvani bultende aynen listelenmis"})
    return adaylar


def _bolum_penceresi(n: str, bas: int, azami: int) -> str:
    """Tetikleyiciden sonraki metin; bir sonraki karar/bolum basligina kadar."""
    parca = n[bas:bas + azami]
    m = BOLUM_SONU_RX.search(parca, 200)
    return parca[:m.start()] if m else parca


def kapatma_tasfiye_adaylari(duz: str, n: str, evren: dict) -> list:
    adaylar = []
    # (a) "<Sirket listesi> kurucusu olduğu ... tüm fonların ... işleme kapatılmasına"
    for m in KAPATMA_RX.finditer(n):
        bas = max(0, m.start() - 1200)
        onceki = n[bas:m.start()]
        idx = max((onceki.rfind(x) for x in ("KAPSAMINDA", "UYARINCA", "DUYURU:")), default=-1)
        segment = onceki[idx:] if idx >= 0 else onceki[-600:]
        if "KURUCUSU" not in segment:
            continue
        alinti = _alinti(duz, m.start() - 160, m.end())
        for k, adlar in evren["sirket_fon"].items():
            if _kelime_var(segment, k):
                adaylar.append({"eslesme_turu": "SIRKET_ADI", "deger": sirket_degeri(adlar[0], k), "kategori": "TEFAS",
                                "tedbir_turu": "ISLEME_KAPATMA", "alinti": alinti, "kaynak": "deterministik",
                                "gerekce": f"{k.title()} kurucusu olduğu fonlar TEFAS'ta alım-satıma kapatıldı"})
    # (b) zorunlu tasfiye: "aşağıda ünvanlarına yer verilen fonların ... tasfiye ettirilmesine" + liste
    for m in TASFIYE_ZORUNLU_RX.finditer(n):
        pencere = _bolum_penceresi(n, m.end(), 15000)
        bulunan = [orj for nad, orj in evren["fon_adlari"].items() if nad in pencere]
        adaylar += _fon_adaylari(bulunan, "TASFIYE", _alinti(duz, m.start() - 140, m.end()), evren)
    # (c) gonullu tasfiye izni (tablolar iki sutunlu olabilir; tam unvan eslesmesi bulunanlari yakalar)
    for m in TASFIYE_IZNI_RX.finditer(n):
        pencere = n[m.end():m.end() + 6000]
        bulunan = [orj for nad, orj in evren["fon_adlari"].items() if nad in pencere]
        adaylar += _fon_adaylari(bulunan, "TASFIYE_IZNI", _alinti(duz, m.start() - 100, m.end()), evren)
    return adaylar


def hisse_adaylari(duz: str, n: str, evren: dict) -> list:
    adaylar, gorulen = [], set()
    for m in HISSE_RX.finditer(n):
        ticker = duz[m.start(1):m.end(1)]
        if ticker != ticker.upper() or not re.fullmatch(r"[A-Z0-9]{3,6}", ticker):
            continue                                   # "(Fon)", "(Vanet)" gibi sahte yakalamalari ele
        if ticker not in evren["bist"] or ticker in gorulen:
            continue
        gorulen.add(ticker)
        yakin = n[m.end():m.end() + 900]
        tur = ("MANIPULASYON_SUPHESI" if ("PIYASA DOLANDIRICILIGI" in yakin or "PAY PIYASASINDA" in yakin or "107/1" in yakin)
               else "SUC_DUYURUSU")
        adaylar.append({"eslesme_turu": "TICKER", "deger": ticker, "kategori": "BIST", "tedbir_turu": tur,
                        "alinti": _alinti(duz, m.start() - 90, m.end() + 110), "kaynak": "deterministik",
                        "gerekce": f"{ticker} hakkında suç duyurusu kararı"})
    return adaylar


def kaldirma_adaylari(duz: str, n: str, evren: dict, aktif_kurallar: list) -> list:
    """Kesin kaldirma kararlari -> MEVCUT aktif kurala bagli (baska hicbir sey kaldirilamaz)."""
    adaylar = []
    for m in KALDIRMA_RX.finditer(n):
        pencere = n[max(0, m.start() - 700):m.end() + 300]
        if SARTLI_RX.search(n[max(0, m.start() - 200):m.end() + 200]):
            continue                                   # "açılabileceği" gibi sartli dil = KESIN karar degil
        for k in aktif_kurallar:
            anahtar = tr_norm(k["deger"])
            if len(anahtar) >= 4 and _kelime_var(pencere, anahtar):
                adaylar.append({"eslesme_turu": k["eslesme_turu"], "deger": k["deger"], "kategori": k.get("kategori"),
                                "tedbir_turu": "KALDIRMA", "alinti": _alinti(duz, m.start() - 160, m.end() + 80),
                                "kaynak": "deterministik", "gerekce": "Bülten tedbirin kaldırıldığını bildiriyor"})
    return adaylar


# ════════════════════════════════════════════════════════════════════════════════════════
# 4) Yapay zeka ikinci gorus (opsiyonel)
# ════════════════════════════════════════════════════════════════════════════════════════
AI_PROMPT = """Aşağıda SPK (Sermaye Piyasası Kurulu) bülteninden alınmış alıntılar var.
GÖREV: Bu alıntılarda geçen KESİN KARARLARI çıkar:
 - EKLE: bir fon şirketinin/fonun/hissenin işleme KAPATILMASI, zorunlu TASFİYESİ veya hakkında
   piyasa dolandırıcılığı / suç duyurusu kararı verilmesi.
 - KALDIR: daha önce getirilmiş böyle bir tedbirin KALDIRILMASI / varlığın işleme AÇILMASI KARARI.
KESİN KURALLAR:
 - Olasılık/şart ifadelerini ("açılabilir", "belirlenecek", "mümkün") KESİN KARAR SAYMA; kesin_karar=false yaz.
 - Rutin başvuru/izin/izahname/halka arz metinlerini YOKSAY.
 - "alinti" alanı metinde AYNEN geçen, en fazla 200 karakterlik bir ifade olmalı.
 - Bir hisse için ticker'ı (BÜYÜK HARF, 3-6 karakter) ver; fon şirketi için şirketin adını ver.
SADECE şu JSON'u döndür:
{{"kararlar":[{{"islem":"EKLE|KALDIR","varlik_turu":"FON_SIRKETI|FON|HISSE","ad":"...","ticker":null,
"tedbir":"ISLEME_KAPATMA|TASFIYE|MANIPULASYON_SUPHESI|KALDIRMA","kesin_karar":true,
"alinti":"...","gerekce":"tek cümle"}}]}}
Karar yoksa {{"kararlar":[]}} döndür.

ALINTILAR:
{metin}
"""


def _ai_pencereleri(duz: str, n: str) -> str:
    parcalar = []
    for m in AI_PENCERE_RX.finditer(n):
        a, b = max(0, m.start() - 900), min(len(duz), m.end() + 900)
        if parcalar and a <= parcalar[-1][1]:
            parcalar[-1] = (parcalar[-1][0], b)
        else:
            parcalar.append((a, b))
    metin = "\n---\n".join(duz[a:b] for a, b in parcalar)
    return metin[:AI_MAKS_KARAKTER]


def ai_cagir_gercek(prompt: str, db_mod=None):
    """Gemini, olmazsa Groq (haber_izleme.py ile AYNI uc noktalar/modeller/anahtar adlari ve
    PAYLASILAN gunluk butce). Dondurur: JSON dict | None (anahtar yok/butce bitti/hata)."""
    import requests
    if db_mod is not None and db_mod.ai_cagri_sayisi_bugun() >= GUNLUK_AI_BUTCESI:
        log("Gunluk AI butcesi doldu - AI ikinci gorus atlandi.")
        return None
    gk, qk = os.environ.get("GEMINI_API_KEY", ""), os.environ.get("GROQ_API_KEY", "")
    if not gk and not qk:
        log("GEMINI_API_KEY/GROQ_API_KEY yok - AI ikinci gorus atlandi (deterministik cikarici calisti).")
        return None
    if gk:
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
            for deneme in (1, 2):
                resp = requests.post(url, headers={"Content-Type": "application/json", "x-goog-api-key": gk},
                                     json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=45)
                if resp.status_code == 429 and deneme == 1:
                    time.sleep(65)
                    continue
                resp.raise_for_status()
                break
            metin = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            metin = metin.replace("```json", "").replace("```", "").strip()
            if db_mod is not None:
                db_mod.ai_cagri_kaydet(1)
            return json.loads(metin)
        except Exception as e:
            log(f"Gemini AI hatasi: {type(e).__name__}: {str(e)[:120]}")
    if qk:
        try:
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                 headers={"Authorization": f"Bearer {qk}", "Content-Type": "application/json"},
                                 json={"model": "openai/gpt-oss-120b", "messages": [{"role": "user", "content": prompt}],
                                       "response_format": {"type": "json_object"}, "temperature": 0.2,
                                       "max_completion_tokens": 2000}, timeout=45)
            resp.raise_for_status()
            if db_mod is not None:
                db_mod.ai_cagri_kaydet(1)
            return json.loads(resp.json()["choices"][0]["message"]["content"].strip())
        except Exception as e:
            log(f"Groq AI hatasi: {type(e).__name__}: {str(e)[:120]}")
    return None


def ai_adaylari(duz: str, n: str, evren: dict, aktif_kurallar: list, ai_fn) -> list:
    """AI ciktisini KATI dogrular: kesin_karar + metinde aynen gecen alinti + evrende
    dogrulanabilir varlik. Dogrulanamayan HICBIR sey aday olmaz."""
    pencere = _ai_pencereleri(duz, n)
    if not pencere or ai_fn is None:
        return []
    veri = ai_fn(AI_PROMPT.format(metin=pencere))
    if not isinstance(veri, dict):
        return []
    pencere_n = tr_norm(pencere)
    adaylar = []
    for k in (veri.get("kararlar") or []):
        try:
            if not k.get("kesin_karar"):
                continue
            alinti = str(k.get("alinti") or "").strip()
            if len(alinti) < 12 or tr_norm(alinti) not in pencere_n:
                continue                                    # uydurma/yaklasik alinti -> RED
            islem, vtur = str(k.get("islem")).upper(), str(k.get("varlik_turu")).upper()
            ad, ticker = str(k.get("ad") or ""), str(k.get("ticker") or "").upper().strip()
            gerekce = str(k.get("gerekce") or "")[:240]
            if islem == "KALDIR":
                if SARTLI_RX.search(tr_norm(alinti)):
                    continue
                aday = None
                for r in aktif_kurallar:
                    anahtar = tr_norm(r["deger"])
                    if (len(anahtar) >= 4 and (_kelime_var(tr_norm(ad), anahtar) or _kelime_var(anahtar, tr_norm(ad))
                                               or (ticker and ticker == anahtar))):
                        aday = {"eslesme_turu": r["eslesme_turu"], "deger": r["deger"], "kategori": r.get("kategori"),
                                "tedbir_turu": "KALDIRMA", "alinti": alinti, "kaynak": "ai", "gerekce": gerekce}
                        break
                if aday:
                    adaylar.append(aday)
            elif islem == "EKLE":
                tedbir = str(k.get("tedbir") or "").upper()
                if tedbir not in ("ISLEME_KAPATMA", "TASFIYE", "MANIPULASYON_SUPHESI"):
                    tedbir = "SUC_DUYURUSU"
                if vtur == "HISSE":
                    if ticker in evren["bist"] and re.search(r"(?<![A-Z0-9])" + re.escape(ticker) + r"(?![A-Z0-9])", pencere_n):
                        adaylar.append({"eslesme_turu": "TICKER", "deger": ticker, "kategori": "BIST", "tedbir_turu": tedbir,
                                        "alinti": alinti, "kaynak": "ai", "gerekce": gerekce})
                elif vtur == "FON_SIRKETI":
                    nad = tr_norm(ad)
                    for anahtar, adlar in evren["sirket_fon"].items():
                        if _kelime_var(nad, anahtar) and _kelime_var(pencere_n, anahtar):
                            adaylar.append({"eslesme_turu": "SIRKET_ADI", "deger": sirket_degeri(adlar[0], anahtar),
                                            "kategori": "TEFAS", "tedbir_turu": tedbir, "alinti": alinti,
                                            "kaynak": "ai", "gerekce": gerekce})
                elif vtur == "FON":
                    orj = evren["fon_adlari"].get(tr_norm(ad))
                    if orj:
                        adaylar.append({"eslesme_turu": "SIRKET_ADI", "deger": str(orj).upper(), "kategori": "TEFAS",
                                        "tedbir_turu": tedbir, "alinti": alinti, "kaynak": "ai", "gerekce": gerekce})
        except Exception as e:                              # tek bir bozuk kayit digerlerini engellemesin
            log(f"AI karar kaydi atlandi ({type(e).__name__}: {e})")
    return adaylar


# ════════════════════════════════════════════════════════════════════════════════════════
# 5) Dogrulama + kayit
# ════════════════════════════════════════════════════════════════════════════════════════
def adaylari_suz(adaylar: list, evren: dict, aktif: list, durum_fn, bugun: date) -> list:
    """Evren dogrulamasi, kapsanma, tekrar ve bekleyen/reddedilen kontrolu. Dondurur: kuyruga girecekler."""
    df = evren["df"]
    kapsanan = kapsanan_maske(df, aktif)
    birlestirilmis = {}
    for a in adaylar:                                       # ayni (tur, deger, tedbir): iki kaynak = teyit
        anahtar = (a["eslesme_turu"], a["deger"], a["tedbir_turu"])
        if anahtar in birlestirilmis:
            if birlestirilmis[anahtar]["kaynak"] != a["kaynak"]:
                birlestirilmis[anahtar]["kaynak"] = "deterministik+ai"
            continue
        birlestirilmis[anahtar] = dict(a)
    sonuc = []
    # En genis etkili aday ONCE: sirket-seviyesi kural kabul edilince, ayni bultende onun
    # zaten kapsadigi tekil-fon adaylari (orn. 25 tekil TASFIYE) elenir - onay penceresi
    # gurultulu olmasin.
    sirali = sorted(birlestirilmis.items(),
                    key=lambda kv: -int(esleyen_maske(df, kv[0][0], kv[0][1]).sum()))
    for (tur, deger, tedbir), a in sirali:
        maske = esleyen_maske(df, tur, deger)
        n_etkilenen = int(maske.sum())
        if tedbir == "KALDIRMA":
            if not any(r["eslesme_turu"] == tur and r["deger"] == deger for r in aktif):
                continue                                    # kaldirilacak aktif kural yok
        else:
            if n_etkilenen == 0:
                continue                                    # evrende hicbir varliga denk gelmiyor
            if bool(maske[~kapsanan].sum() == 0):
                continue                                    # zaten aktif kurallarla kapsanmis
        mevcut = durum_fn(tur, deger, tedbir) or []
        engel = False
        for durum, zaman in mevcut:
            gun = (bugun - (zaman.date() if hasattr(zaman, "date") else zaman)).days if zaman else 0
            if durum == "bekliyor" or (durum in ("reddedildi", "onaylandi") and gun <= REDDEDILEN_SKIP_GUN):
                engel = True
        if engel:
            continue
        a["n_etkilenen"] = n_etkilenen
        a["etki"] = etki_ozeti(df, tur, deger)
        sonuc.append(a)
        if tedbir != "KALDIRMA":
            kapsanan = kapsanan | maske                    # sonraki adaylar bunu da "zaten kapsanmis" sayar
    return sonuc


def _tespit_metinleri(a: dict) -> tuple:
    etiket = TEDBIR_ETIKET.get(a["tedbir_turu"], a["tedbir_turu"])
    kaynak = {"deterministik": "otomatik tarama", "ai": "yapay zekâ", "deterministik+ai": "otomatik tarama + yapay zekâ (teyitli)"}.get(a["kaynak"], a["kaynak"])
    gerekce = f"{etiket}. {a['gerekce']}. [{kaynak}] Bültenden: \"{a['alinti']}\""
    e = a["etki"]
    ornek = ", ".join(t for t, _ in e["ornekler"])
    if a["tedbir_turu"] == "KALDIRMA":
        ozet = f"Kural kaldırılırsa {a['n_etkilenen']} varlığın skoru yeniden hesaplanır (örn. {ornek})."
        if a["eslesme_turu"] == "SIRKET_ADI" and a["n_etkilenen"] > 1:
            # CVL/BAG arastirmasindan (4 Ekim 2026): SPK sirketin fonlarindan YALNIZCA BAZILARINI yeniden
            # acabilir (ornegin A1 Capital: 7 fon acilabilir, 4 fon tasfiyede). Sirket kurali hepsini kapsar.
            ozet += (" DİKKAT: Bu şirket kuralı TASFİYEDEKİ fonları da kapsar; onaylarsanız onlar da yeniden "
                     "skorlanır. Bülten yalnızca bazı fonların açıldığını söylüyorsa ONAYLAMAYIN, reddedip bildirin.")
    else:
        ozet = f"Etkilenen varlık: {a['n_etkilenen']} (örn. {ornek}). Onaylanırsa Optima Skor 0'a sabitlenir."
        if e["genis"]:
            ozet += f" DİKKAT: ETKİ ÇOK GENİŞ (>{GENIS_ETKI_ESIGI} varlık) - onaylamadan önce bülteni kontrol edin."
    return gerekce[:900], ozet[:500]


def bulten_adaylari(metin: str, evren: dict, aktif: list, ai_fn=None) -> list:
    duz, n = _hizala(metin)
    adaylar = (kapatma_tasfiye_adaylari(duz, n, evren) + hisse_adaylari(duz, n, evren)
               + kaldirma_adaylari(duz, n, evren, aktif))
    try:
        adaylar += ai_adaylari(duz, n, evren, aktif, ai_fn)
    except Exception as e:
        log(f"AI ikinci gorus atlandi ({type(e).__name__}: {e})")
    return adaylar


# ════════════════════════════════════════════════════════════════════════════════════════
# 6) Ana akis
# ════════════════════════════════════════════════════════════════════════════════════════
def calistir(yil=None, kuru=False, bugun=None, ilk_gun=ILK_CALISMA_GUN, maks_bulten=MAKS_BULTEN,
             liste_fn=None, metin_fn=None, ai_fn="varsayilan", df_uni=None, db_mod=None) -> dict:
    bugun = bugun or datetime.now(timezone(timedelta(hours=3))).date()
    yil = yil or bugun.year
    if db_mod is None:
        import db as db_mod
    if df_uni is None:
        df_uni = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "optimized_universe.csv"),
                             on_bad_lines="skip")
    liste_fn = liste_fn or bulten_listesi_cek
    metin_fn = metin_fn or pdf_metni_cek
    if ai_fn == "varsayilan":
        ai_fn = lambda prompt: ai_cagir_gercek(prompt, db_mod)      # noqa: E731

    liste = list(liste_fn(yil))
    if bugun.month == 1 and bugun.day <= 14:                         # yil basi: onceki yilin son bultenleri
        try:
            liste += list(liste_fn(yil - 1))
        except Exception as e:
            log(f"Onceki yil listesi alinamadi: {e}")
    liste.sort(key=lambda b: b["tarih"], reverse=True)
    log(f"{len(liste)} bulten listede (en yeni: {liste[0]['no'] if liste else '-'}).")

    aktif = db_mod.get_aktif_piyasa_tedbirleri()
    evren = evren_hazirla(df_uni)
    islenecek, baz = [], 0
    for b in liste:
        if db_mod.spk_bulten_islendi_mi(b["no"]):
            continue
        if (bugun - b["tarih"]).days > ilk_gun:
            baz += 1
            if not kuru:
                db_mod.spk_bulten_islendi_isaretle(b["no"])          # eski bulten: analiz edilmeden "islendi"
            continue
        islenecek.append(b)
    if baz:
        log(f"{baz} eski bulten (>{ilk_gun} gun) analiz edilmeden 'islendi' sayildi (baz cizgisi).")
    islenecek = islenecek[:maks_bulten][::-1]                        # eskiden yeniye

    ozet = {"bulten": 0, "aday": 0, "yeni_tespit": [], "hata": 0}
    for b in islenecek:
        try:
            metin = metin_fn(b["url"])
            if not metin or len(metin) < 150:
                log(f"{b['no']}: metin cikarilamadi (taranmis PDF olabilir) - sonraki calismada tekrar denenecek.")
                ozet["hata"] += 1
                continue
            adaylar = bulten_adaylari(metin, evren, aktif, ai_fn)
            yeni = adaylari_suz(adaylar, evren, aktif, getattr(db_mod, "piyasa_tedbir_tespit_durumlari"), bugun)
            log(f"{b['no']} ({b['tarih']}): {len(adaylar)} ham aday -> {len(yeni)} yeni tespit.")
            tum_yazildi = True
            for a in yeni:
                gerekce, ozet_m = _tespit_metinleri(a)
                log(f"   + {a['eslesme_turu']}:{a['deger']} [{a['tedbir_turu']}] ({a['kaynak']}) - {a['n_etkilenen']} varlik")
                if kuru:
                    continue
                if not db_mod.piyasa_tedbir_tespit_ekle("SPK_BULTEN", b["no"], b["url"], b["tarih"], a["eslesme_turu"],
                                                        a["deger"], a.get("kategori"), a["tedbir_turu"], gerekce, ozet_m):
                    tum_yazildi = False
            if not kuru and tum_yazildi:
                db_mod.spk_bulten_islendi_isaretle(b["no"])
            elif not kuru:
                log(f"{b['no']}: bazi tespitler yazilamadi - bulten 'islendi' sayilmadi, tekrar denenecek.")
                ozet["hata"] += 1
            ozet["bulten"] += 1
            ozet["aday"] += len(adaylar)
            ozet["yeni_tespit"] += [(b["no"], a["eslesme_turu"], a["deger"], a["tedbir_turu"]) for a in yeni]
        except Exception as e:
            ozet["hata"] += 1
            log(f"{b['no']}: HATA {type(e).__name__}: {str(e)[:160]}")
    log(f"BITTI: {ozet['bulten']} bulten islendi, {len(ozet['yeni_tespit'])} yeni tespit, {ozet['hata']} hata.")
    return ozet


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true", help="veritabanina YAZMAZ, sadece ne bulacagini gosterir")
    ap.add_argument("--yil", type=int)
    ap.add_argument("--bugun", help="YYYY-MM-DD (test)")
    a = ap.parse_args()
    try:
        s = calistir(yil=a.yil, kuru=a.kuru, bugun=date.fromisoformat(a.bugun) if a.bugun else None)
    except Exception as e:
        log(f"KRITIK HATA: {type(e).__name__}: {e}")
        sys.exit(1)
    sys.exit(1 if (s["hata"] and not s["bulten"] and not a.kuru) else 0)
