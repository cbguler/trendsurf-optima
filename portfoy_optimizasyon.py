# -*- coding: utf-8 -*-
"""
portfoy_optimizasyon.py - Portföy/Bütçe Optimizasyonu'nun TEK, PAYLAŞILAN kaynağı.

app.py (Ana Sayfa), emailer.py ve emailer_standalone.py'nin ÜÇÜ de bu
modülü çağırır; bu yüzden aynı veri + aynı strateji = BİREBİR aynı tablo.
Streamlit'e bağımlı DEĞİLDİR.

v2.0.7.359 (3 Ekim 2026, Bahri'nin bulgusu - Ana Sayfa ile e-posta tablosu
varlık seçimi/lot/sıra bakımından farklı çıkıyordu):
  1) "Artan bakiye" lot dağıtımı (v2.0.7.21) SADECE app.py'de vardı, e-postada
     yoktu -> lot sayıları ve toplam tutar farklıydı. Artık burada, ortak.
  2) Nihai sıralama app.py'de kararsız (quicksort) bir sort ile yapılıyordu;
     eşit skorlu varlıkların sırası Ana Sayfa'da farklı çıkıyordu. Artık tek
     ve deterministik: (yuvarlanmış skor azalan, Ticker artan).
  3) Eski "kategori garantili" algoritma bütçeyi AŞIYORDU (30.000 TL bütçede
     38.940 TL öneriyordu: doldurma adımı varlık başına bütçe/max_assets
     kullanıyordu). İki strateji artık AYNI tahsis akışını paylaşıyor; tek fark
     "her kategoriye kaç slot düştüğü":
       a) "kuresel"            -> tüm havuzdan en yüksek skorlu max_assets varlık
       b) "kategori_guvenceli" -> uygun adayı olan HER kategoriye garantili slot,
                                  kalan slotlar en yüksek skorlulara
"""
import time
import pandas as pd

from scoring import optima_score as _optima_score_fn

STRATEJILER = ("kuresel", "kategori_guvenceli")

# Kullanıcıya gösterilen ad/açıklamalar TEK yerde (uygulama + e-posta aynı metni kullanır)
STRATEJI_ETIKET = {
    "kuresel": "En yüksek skorlular",
    "kategori_guvenceli": "Her kategoriden skorlular",
}
STRATEJI_SECENEK = {
    "kuresel": "En yüksek skorlular",
    "kategori_guvenceli": "Her kategoriden skorlular",
}
STRATEJI_ACIKLAMA = {
    "kuresel": ("Tüm kategoriler birlikte yarışır ve en yüksek Optima skorlu "
                "varlıklar seçilir. O an skorları daha düşük kalan bir kategori "
                "(örneğin BIST) sepete hiç girmeyebilir."),
    "kategori_guvenceli": ("Uygun adayı olan her kategoriden (TEFAS, BIST, Döviz, "
                           "Değerli Maden, Kripto) en yüksek skorlu varlıklar "
                           "seçilir; sepet kategoriler arasında dengelenir."),
}

MIN_SKOR = 60.0


def _skor_hesapla(row) -> float:
    """Önce varsa canlı Optima_Skor (Fırsat Radarı dahil), yoksa scoring.py
    formülüyle RSI/Ret1M/Vol'den taze hesaplar."""
    # v2.0.7.363 (Bahri'nin bulgusu - ILU): ESKIDEN `if v > 0` vardi; piyasa tedbiri
    # listesinin ACIKCA 0.0'a sifirladigi varliklar (117 fon + ILU + 3 hisse) "puan
    # yok" sayilip bayat RSI/getiriden YENIDEN puanlaniyor (ILU 0 -> 78,7) ve
    # sepete giriyordu. Artik NaN = eksik (hesapla), 0.0 = ACIK SIFIR (secilemez).
    for col in ["Optima_Skor", "optima_skor", "OptimaSkoru"]:
        if col in row.index and pd.notna(row[col]):
            return float(row[col])
    rsi = float(row.get("RSI", 50) or 50)
    ret1m = float(row.get("Ret1M", 0) or 0)
    vol = float(row.get("Vol", 30) or 30)
    return _optima_score_fn(rsi, ret1m, vol=vol, has_fundamental=False)


MAKS_GETIRI_YASI_GUN = 10


def _tefas_tazelik_suz(df_c: pd.DataFrame):
    """TEFAS fonlarinin getiri/RSI'si (Getiri_Tarihi kolonu) son 10 gun icinde GERCEK
    fiyatlardan hesaplanmamissa o fon onerilmez. Kolon hic yoksa dogrulanamaz ->
    TEFAS tamamen disarida (bayat Excel verisiyle sessizce oneri vermemek icin).
    Dondurur: (suzulmus df, kullaniciya gosterilecek uyari | None)."""
    if df_c.empty:
        return df_c, None
    if "Getiri_Tarihi" not in df_c.columns:
        return df_c.iloc[0:0], ("TEFAS: getiri/RSI verisinin güncelliği doğrulanamadı "
                                "('Getiri_Tarihi' yok) - TEFAS fonları öneri dışı bırakıldı. "
                                "'TEFAS Aksam Guncelle' iş akışı çalışınca düzelir.")
    t = pd.to_datetime(df_c["Getiri_Tarihi"], errors="coerce")
    taze = t >= (pd.Timestamp.now().normalize() - pd.Timedelta(days=MAKS_GETIRI_YASI_GUN))
    n_bayat = int((~taze).sum())
    if n_bayat == 0:
        return df_c, None
    uyari = None
    if n_bayat / len(df_c) > 0.25:      # kucuk oranda (yeni fon vb.) sessizce elenir
        uyari = (f"TEFAS: {n_bayat} fonun getiri/RSI verisi güncel değil (son {MAKS_GETIRI_YASI_GUN} "
                 "günde gerçek fiyatlardan hesaplanmamış) - bu fonlar öneri dışı bırakıldı.")
    return df_c[taze], uyari


def _fiyat(row) -> float:
    p = float(row.get("Son_Fiyat", 0) or 0)
    return p if p > 0 else 1.0


def _slotlari_belirle(cat_pools: dict, max_assets: int, strateji: str) -> dict:
    """Her kategoriye kaç varlık düşeceğini döndürür (strateji farkı SADECE burada)."""
    slots = {c: 0 for c in cat_pools}
    if strateji == "kategori_guvenceli":
        kats = list(cat_pools.keys())
        if len(kats) > max_assets:
            # Kategori sayısı varlık sayısından fazla: en iyi adayı en yüksek
            # skorlu max_assets kategori birer slot alır.
            kats = sorted(kats, key=lambda c: (-float(cat_pools[c]["_skor"].iloc[0]), c))[:max_assets]
            for c in kats:
                slots[c] = 1
            return slots
        taban = max(1, max_assets // len(kats))
        for c in kats:
            slots[c] = min(taban, len(cat_pools[c]))
        kalan = max_assets - sum(slots.values())
        if kalan > 0:
            artan = pd.concat(
                [cat_pools[c].iloc[slots[c]:].assign(_Kategori=c) for c in kats],
                ignore_index=True)
            if not artan.empty:
                artan = artan.sort_values(["_skor", "Ticker"], ascending=[False, True], kind="mergesort")
                for _, r in artan.head(kalan).iterrows():
                    slots[r["_Kategori"]] += 1
        return slots

    # "kuresel": saf küresel en iyi N
    tum = pd.concat([df.assign(_Kategori=c) for c, df in cat_pools.items()], ignore_index=True)
    tum = tum.sort_values(["_skor", "Ticker"], ascending=[False, True], kind="mergesort")
    for c, grp in tum.head(max_assets).groupby("_Kategori"):
        slots[c] = len(grp)
    return slots


def optimize_portfolio(df_uni: pd.DataFrame, budget: float, risk_weights: dict,
                       max_assets: int, strateji: str = "kuresel",
                       watchlist_mode: bool = False) -> dict:
    """Döndürür:
      secilenler      : nihai (artan bakiye dağıtılmış, sıralı) varlık listesi
      elenen          : slot alamayan kategoriler (kendi havuzunda aday olsa bile)
      karsilanamayan  : payını karşılayacak hiçbir varlık bulunamayan kategoriler
      havuz_sayilari  : {kategori: uygun aday sayısı (skor>=60 ve Ret1M>0)}
      strateji        : fiilen kullanılan strateji
      kalan_butce     : dağıtılamayan bakiye
    """
    if strateji not in STRATEJILER:
        strateji = "kuresel"
    sonuc = {"secilenler": [], "elenen": [], "karsilanamayan": [],
             "havuz_sayilari": {}, "strateji": strateji, "kalan_butce": float(budget or 0),
             "uyarilar": []}
    if df_uni is None or df_uni.empty:
        return sonuc

    cat_pools = {}
    for cat, weight in risk_weights.items():
        if weight <= 0:
            continue
        if cat == "TEFAS":
            df_c = df_uni[(df_uni["Kategori"] == cat) & (df_uni["Ret1M"] != 0)].copy()
            df_c, _uyari = _tefas_tazelik_suz(df_c)
            if _uyari:
                sonuc["uyarilar"].append(_uyari)
        else:
            df_c = df_uni[(df_uni["Kategori"] == cat) & (df_uni["Son_Fiyat"] > 0)].copy()
            # v2.0.7.378: 260 islem gunu altindaki (SINIRLI VERI) hisse icin AL sinyali uretilmedigi
            # icin otomatik portfoy onerisine de ALINMAZ (izleme listesi modunda kullanicinin secimi korunur).
            if not watchlist_mode and "Veri_Sinirli" in df_c.columns:
                df_c = df_c[~df_c["Veri_Sinirli"].fillna(False).astype(bool)]
        if df_c.empty:
            sonuc["havuz_sayilari"][cat] = 0
            continue
        df_c["_skor"] = df_c.apply(_skor_hesapla, axis=1)
        df_c = (df_c[(df_c["Ret1M"] > 0) & (df_c["_skor"] >= MIN_SKOR)]
                .sort_values(["_skor", "Ticker"], ascending=[False, True], kind="mergesort"))
        sonuc["havuz_sayilari"][cat] = int(len(df_c))
        if not df_c.empty:
            cat_pools[cat] = df_c

    if not cat_pools:
        sonuc["elenen"] = [c for c, w in risk_weights.items() if w > 0]
        return sonuc

    def _satir(cat, row, price, lot, gercek):
        return {
            "cat": cat, "ticker": row["Ticker"], "ad": str(row.get("Ad", row["Ticker"])),
            "skor": float(row["_skor"]), "fiyat": price, "lot": lot, "gercek": gercek,
            "rsi": float(row.get("RSI", 50)), "ret1m": float(row.get("Ret1M", 0)),
            "gercek_fiyat_var": float(row.get("Son_Fiyat", 0) or 0) > 0,
        }

    def _sirala(rows):
        # Görünen skor (1 ondalık) eşitse Ticker alfabetik - HER yerde aynı sıra
        return sorted(rows, key=lambda r: (-round(r["skor"], 1), r["ticker"]))

    slots = _slotlari_belirle(cat_pools, max_assets, strateji)

    # Watchlist (bütçe yok): sadece seçim, tutar/lot yok
    if watchlist_mode:
        rows = []
        for cat, n in slots.items():
            for _, row in cat_pools[cat].head(n).iterrows():
                rows.append(_satir(cat, row, _fiyat(row), 0, 0.0))
        sonuc["secilenler"] = _sirala(rows)
        sonuc["elenen"] = [c for c, w in risk_weights.items() if w > 0 and slots.get(c, 0) <= 0]
        sonuc["kalan_butce"] = 0.0
        return sonuc

    # Kalite ağırlıklı kategori bütçeleri
    adj, toplam_adj = {}, 0.0
    for cat, weight in risk_weights.items():
        n = slots.get(cat, 0)
        if cat not in cat_pools or n <= 0:
            continue
        kalite = float(cat_pools[cat]["_skor"].head(n).mean()) / 100.0
        adj[cat] = weight * kalite
        toplam_adj += adj[cat]
    if toplam_adj > 0:
        adj = {c: a / toplam_adj for c, a in adj.items()}

    rows, karsilanamayan = [], []
    for cat, agirlik in adj.items():
        sample = cat_pools[cat].head(slots[cat])
        cat_bud = budget * agirlik
        aktif = list(sample.iterrows())
        per = 0.0
        # Payını karşılayamayan varlık elenir, kalan bütçe kalanlara dağılır
        while aktif:
            pay = cat_bud / len(aktif)
            elenecek = [i for i, (_, r) in enumerate(aktif) if _fiyat(r) > pay]
            if not elenecek:
                per = pay
                break
            aktif = [x for i, x in enumerate(aktif) if i not in elenecek]
        else:
            per = 0.0
        if not aktif:
            karsilanamayan.append(cat)
            continue
        for _, row in aktif:
            price = _fiyat(row)
            lot = int(per / price) if price > 0 else int(per)
            gercek_var = float(row.get("Son_Fiyat", 0) or 0) > 0
            gercek = round(lot * price, 2) if gercek_var else per
            rows.append(_satir(cat, row, price, lot, gercek))

    # Artan bakiye: kalan bütçe, skoru en yüksek varlıklardan başlayarak
    # birer lot daha eklenerek dağıtılır (v2.0.7.21'den taşındı; güvenlik
    # freni: en fazla 100.000 iterasyon / 5 saniye - bkz. v2.0.7.92).
    rows = _sirala(rows)
    kalan = round(budget - sum(r["gercek"] for r in rows), 2)
    adaylar = [r for r in rows if r["gercek_fiyat_var"]]
    t0, iterasyon, ilerleme, fren = time.time(), 0, True, False
    while kalan > 0.01 and ilerleme and adaylar:
        ilerleme = False
        for r in adaylar:
            if 0 < r["fiyat"] <= kalan:
                r["lot"] += 1
                r["gercek"] = round(r["gercek"] + r["fiyat"], 2)
                kalan = round(kalan - r["fiyat"], 2)
                ilerleme = True
            iterasyon += 1
            if iterasyon >= 100_000 or time.time() - t0 > 5.0:
                fren = True
                break
        if fren:
            break

    sonuc["secilenler"] = rows
    sonuc["karsilanamayan"] = karsilanamayan
    sonuc["elenen"] = [c for c, w in risk_weights.items() if w > 0 and c not in adj]
    sonuc["kalan_butce"] = max(kalan, 0.0)
    return sonuc


def elenen_notu(sonuc: dict) -> str:
    """Slot alamayan kategoriler için DOĞRU açıklama - uygulama ve e-posta AYNI
    metni kullanır. Ayrım: (1) hiç uygun adayı olmayan kategoriler, (2) adayı
    olduğu halde diğer kategorilere göre daha düşük skorlu kalanlar."""
    elenen = sonuc.get("elenen") or []
    if not elenen:
        return ""
    havuz = sonuc.get("havuz_sayilari", {})
    adaysiz = [c for c in elenen if havuz.get(c, 0) == 0]
    yarisi_kaybeden = [c for c in elenen if havuz.get(c, 0) > 0]
    parcalar = []
    if adaysiz:
        parcalar.append("uygun aday bulunamadı (skor ≥ 60 ve pozitif 1 aylık getiri şartını "
                        f"sağlayan varlık yok): {', '.join(adaysiz)}")
    if yarisi_kaybeden:
        parcalar.append("adayları var ancak şu an diğer kategorilerin adaylarından daha düşük "
                        f"skorlu kaldı: {', '.join(yarisi_kaybeden)}")
    return "Bütçe diğer kategorilere dağıtıldı - " + "; ".join(parcalar) + "."


def havuz_ozeti(sonuc: dict) -> str:
    """Örn. 'TEFAS 166 · KRIPTO 72 · DOVIZ 9 · BIST 1 · MADEN 0' (uygun aday sayıları)."""
    h = sonuc.get("havuz_sayilari", {})
    return " · ".join(f"{c} {n}" for c, n in sorted(h.items(), key=lambda x: (-x[1], x[0])))
