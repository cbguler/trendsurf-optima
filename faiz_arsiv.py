"""
TrendSurf Optima - Faiz Arsivi (faiz_arsiv.py)
v2.0.7.407 (11 Ekim 2026, Bahri'nin talebi): Portfoyum > Getiri Kiyaslamasi'ndaki Vadeli Mevduat / Devlet Tahvili /
Repo cizgilerinin DUZENLI guncellenmesi.

ESKI DURUM: uc oran da sayfa her acildiginda (6 saat onbellekli) yalniz BUGUNKU deger olarak cekiliyor ve butun
doneme sabit uygulaniyordu (oran x gun / 365) - oran degisince gecmis cizgi de geriye donuk degisiyordu. Ayrica
"Devlet Tahvili" aslinda gecelik TLREF idi (Repo ile ayni, bkz. PROJE_NOTLARI v2.0.7.169 acik madde).

YENI: bu betik her calistiginda her serinin gunluk degerini `faiz_arsiv` tablosuna yazar; uygulama gunluk oran
yolundan birikimi hesaplar (faiz_arsiv.birikim_serisi). Kaynaklar:
  mevduat   hesapkurdu.com/mevduat, 32 gun vadeli tekliflerin EN YUKSEK orani (Bahri'nin 10 Agustos 2026 karari)
  tahvil2y  doviz.com/tahvil, "TR 2 Yillik Tahvil Faizi" (Turkiye gosterge tahvili; TCMB EVDS'te tek bir gosterge
            tahvil serisi yok - bkz. v2.0.7.129 notu)
  repo      TCMB EVDS TP.AOFOBAP (BIST gecelik repo agirlikli ortalama faiz), GUNLUK GECMIS (EVDS_API_KEY gerekir)
mevduat ve tahvil2y icin kaynaklar yalniz GUNCEL deger verir (gecmis uc noktasi bulunamadi/erisilemedi), bu yuzden
gecmis arsivde ancak bu betigin ilk calistigi gunden itibaren birikir; bundan onceki gunler icin ilk kayitli oran
sabit varsayilir ve grafik altinda bu AYRICA yazilir (tahmin, olculmus gecmis degil).

Tetikleme: kap_risk_tarama.yml'deki adim (cron-job.org ~15 dk); kaynak basina 6 saatte bir gercek istek atilir,
digerlerinde yalniz arsiv tarihine bakilir (hafif).
"""
import re
import sys
import os
import datetime

EVDS_REPO_SERISI = "TP.AOFOBAP"
YENILEME_SAAT = 6
REPO_ILK_GUN = 400
REPO_NORMAL_GUN = 45
SERILER = ("mevduat", "tahvil2y", "repo")
ORAN_ARALIGI = (0.0, 200.0)   # yuzde; bunun disindaki deger kaynak hatasi sayilir

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,*/*",
}


def _tr_float(s: str) -> float:
    return float(str(s).strip().replace(".", "").replace(",", "."))


def _makul(oran) -> bool:
    return oran is not None and ORAN_ARALIGI[0] < float(oran) < ORAN_ARALIGI[1]


# ---------------------------------------------------------------- kaynaklar
def mevduat_ayikla(html: str):
    """hesapkurdu.com/mevduat HTML'inden tum oranlarin EN YUKSEGI (yuzde) ya da None."""
    oranlar = re.findall(r'Table_td__xlSfc">%\s*<!-- -->\s*([\d]+,[\d]+)</td>', html or "")
    if not oranlar:
        return None
    return max(_tr_float(o) for o in oranlar)


def mevduat_cek():
    """(oran, hata). app.py'deki eski _en_yuksek_vadeli_mevduat_cek ile ayni kaynak/ayiklama."""
    try:
        import requests
        r = requests.get("https://www.hesapkurdu.com/mevduat", headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            return None, f"hesapkurdu.com HTTP {r.status_code}"
        oran = mevduat_ayikla(r.text)
        if oran is None:
            return None, "hesapkurdu.com sayfa yapisi degismis olabilir (oran bulunamadi)"
        if not _makul(oran):
            return None, f"hesapkurdu.com makul olmayan oran: {oran}"
        return round(oran, 2), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def tahvil2y_ayikla(html: str):
    """doviz.com/tahvil HTML'inden 'TR 2 Yillik Tahvil Faizi' degeri (yuzde) ya da None."""
    m = re.search(r'TR\s*2\s*Y[ıi]ll[ıi]k\s*Tahvil\s*Faizi\s*</a>\s*</td>\s*<td[^>]*>\s*([\d.]+,[\d]+)\s*</td>',
                  html or "", re.I | re.S)
    return _tr_float(m.group(1)) if m else None


def tahvil2y_cek():
    """(oran, hata)."""
    try:
        import requests
        r = requests.get("https://www.doviz.com/tahvil", headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            return None, f"doviz.com HTTP {r.status_code}"
        oran = tahvil2y_ayikla(r.text)
        if oran is None:
            return None, "doviz.com sayfa yapisi degismis olabilir (TR 2 Yillik Tahvil Faizi bulunamadi)"
        if not _makul(oran):
            return None, f"doviz.com makul olmayan oran: {oran}"
        return round(oran, 2), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def evds_df_kayitlar(df, seri_kodu: str):
    """EVDS get_data DataFrame'i -> [(date, oran)] (bos/gecersiz satirlar atilir, tarihe gore sirali)."""
    if df is None or len(df) == 0 or "Tarih" not in df.columns:
        return []
    import pandas as pd
    kolon = seri_kodu.replace(".", "_")
    if kolon not in df.columns:
        kolon = df.columns[-1]
    sonuc = []
    for t, v in zip(df["Tarih"], df[kolon]):
        try:
            d = pd.to_datetime(t, dayfirst=True).date()
            if v is None or pd.isna(v):
                continue
            f = float(v)
        except Exception:
            continue
        if _makul(f):
            sonuc.append((d, round(f, 2)))
    return sorted(sonuc)


def repo_gecmis_cek(gun: int, evds_factory=None):
    """([(date, oran)], hata). EVDS_API_KEY ortam degiskeni gerekir; evds_factory test icin."""
    try:
        key = os.environ.get("EVDS_API_KEY", "").strip()
        if evds_factory is None:
            if not key:
                return [], "EVDS_API_KEY tanimli degil (GitHub Secrets'a eklenmeli)"
            from evds import evdsAPI
            evds_factory = evdsAPI
        e = evds_factory(key)
        bugun = datetime.date.today()
        df = e.get_data([EVDS_REPO_SERISI],
                        startdate=(bugun - datetime.timedelta(days=gun)).strftime("%d-%m-%Y"),
                        enddate=bugun.strftime("%d-%m-%Y"))
        kayit = evds_df_kayitlar(df, EVDS_REPO_SERISI)
        if not kayit:
            return [], f"EVDS'ten gecerli veri gelmedi ({EVDS_REPO_SERISI})"
        return kayit, None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------- birikim (uygulama kullanir)
def birikim_serisi(kayitlar, gun_araligi):
    """kayitlar: [(date, yillik oran %)]. gun_araligi: DatetimeIndex (gunluk).
    Her gun icin O GUNUN orani (kayit olmayan gunde son bilinen; ilk kayittan onceki gunlerde ILK kayit) kullanilir
    ve birikim basit faizle toplanir: kumulatif(t) = toplam(oran_gun / 365), ilk gun 0.
    Donus: (pd.Series % kumulatif getiri, ilk_kayit_tarihi, ilk_kayittan_onceki_gun_sayisi)"""
    import pandas as pd
    s = pd.Series({pd.Timestamp(d): float(o) for d, o in kayitlar}).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    gunluk = s.reindex(pd.DatetimeIndex(gun_araligi), method="ffill").bfill()
    gunluk.index = pd.DatetimeIndex(gun_araligi)
    ilk = s.index[0]
    sabit_gun = int((pd.DatetimeIndex(gun_araligi) < ilk).sum())
    # ilk gun 0: birikim, bir onceki gunun oranindan o gune kadar gecen sureyi sayar
    gun_farki = pd.Series(pd.DatetimeIndex(gun_araligi)).diff().dt.days.fillna(0).values
    artim = (gunluk.shift(1).bfill().values * gun_farki) / 365.0
    kumulatif = pd.Series(artim, index=gunluk.index).cumsum()
    return kumulatif, ilk.date(), sabit_gun


# ---------------------------------------------------------------- calistirma
def _bugun_trt() -> datetime.date:
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date()


def calistir(db_mod, mevduat_fn=mevduat_cek, tahvil_fn=tahvil2y_cek, repo_fn=repo_gecmis_cek, simdi=None) -> dict:
    """Her seri icin: son guncelleme YENILEME_SAAT'ten yeniyse atla; degilse kaynaktan cek ve arsive yaz.
    Donus: {seri: 'yazildi N' | 'atlandi' | 'HATA: ...'}"""
    simdi = simdi or datetime.datetime.now(datetime.timezone.utc)
    bugun = _bugun_trt()
    sonuc = {}

    def _taze(seri):
        son = db_mod.faiz_arsiv_son_guncelleme(seri)
        return son is not None and (simdi - son) < datetime.timedelta(hours=YENILEME_SAAT)

    for seri, fn in (("mevduat", mevduat_fn), ("tahvil2y", tahvil_fn)):
        if _taze(seri):
            sonuc[seri] = "atlandi"
            continue
        oran, hata = fn()
        if oran is None:
            sonuc[seri] = f"HATA: {hata}"
            continue
        db_mod.faiz_arsiv_yaz(seri, [(bugun, oran)], "hesapkurdu.com" if seri == "mevduat" else "doviz.com")
        sonuc[seri] = f"yazildi 1 ({oran})"

    if _taze("repo"):
        sonuc["repo"] = "atlandi"
    else:
        gun = REPO_ILK_GUN if db_mod.faiz_arsiv_kayit_sayisi("repo") < 30 else REPO_NORMAL_GUN
        kayit, hata = repo_fn(gun)
        if not kayit:
            sonuc["repo"] = f"HATA: {hata}"
        else:
            db_mod.faiz_arsiv_yaz("repo", kayit, "TCMB EVDS TP.AOFOBAP")
            sonuc["repo"] = f"yazildi {len(kayit)} (son {kayit[-1][1]})"
    return sonuc


def main() -> int:
    import db
    db.toplu_mod_ac()
    try:
        db.init_db()
        sonuc = calistir(db)
        for k, v in sonuc.items():
            print(f"[faiz_arsiv] {k}: {v}")
        return 0
    except Exception as e:
        print(f"[faiz_arsiv] HATA: {e}")
        return 1
    finally:
        db.toplu_mod_kapat()


if __name__ == "__main__":
    sys.exit(main())
