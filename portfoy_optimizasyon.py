# -*- coding: utf-8 -*-
"""
portfoy_optimizasyon.py - Portföy/Bütçe Optimizasyonu seçim mantığının TEK,
PAYLAŞILAN kaynağı.

v2.0.7.353 (3 Ekim 2026, Bahri'nin talebi - "kullanıcı hangi portföy
tarzını tercih ederse emaillerde ve Ana Sayfa portföy bütçesinde AYNI
FORMÜL kullanılmalı"): Bu dosya KURULMADAN ÖNCE, AYNI seçim mantığının
ÜÇ AYRI KOPYASI vardı (app.py'nin Ana Sayfa'sı, emailer.py, emailer_
standalone.py) - bunlardan biri (emailer.py) uzun süre app.py'nin
BİLEREK kaldırdığı eski bir algoritmayı kullanmaya devam etmiş ve
e-posta ile Ana Sayfa'nın FARKLI sonuçlar vermesine yol açmıştı
(v2.0.7.349'da bulunup düzeltildi). Bir dahaki sefere BÖYLE bir sapma
YAŞANMASIN diye, seçim mantığı artık TEK yerde yaşıyor - app.py,
emailer.py ve emailer_standalone.py'nin ÜÇÜ de buradan import ediyor.

İKİ STRATEJİ destekleniyor (kullanıcı tercihi, bkz. db.py'deki
get_portfoy_stratejisi/set_portfoy_stratejisi):
  - "kuresel": kategoriler arası çeşitlendirme garantisi YOK, tüm
    havuzdan en yüksek skorlu max_assets varlık doğrudan seçilir
    (Bahri'nin önceki açık kararı - bkz. v2.0.7.94/338 notları).
  - "kategori_guvenceli": her kategoriye (en az 1 aday varsa) garantili
    bir slot ayrılır, bütçe kategori KALİTESİNE göre ağırlıklı
    dağıtılır (eski emailer.py'nin orijinal mantığı - daha çeşitlendirilmiş
    bir sepet isteyen kullanıcılar için).

Bu modül Streamlit'e BAĞIMLI DEĞİLDİR (scoring.py ile AYNI prensip) -
hem app.py hem emailer.py/emailer_standalone.py güvenle import edebilir.
"""
import pandas as pd

from scoring import optima_score as _optima_score_fn


def _skor_hesapla(row) -> float:
    """scoring.py'nin TEK kaynağını kullanır - önce varsa canlı
    Optima_Skor'u (Fırsat Radarı dahil), yoksa RSI/Ret1M/Vol'den taze
    hesaplar."""
    for col in ["Optima_Skor", "optima_skor", "OptimaSkoru"]:
        if col in row.index and pd.notna(row[col]):
            v = float(row[col])
            if v > 0:
                return v
    rsi   = float(row.get("RSI",   50) or 50)
    ret1m = float(row.get("Ret1M",  0) or  0)
    vol   = float(row.get("Vol",   30) or 30)
    return _optima_score_fn(rsi, ret1m, vol=vol, has_fundamental=False)


def optimize_portfolio(df_uni: pd.DataFrame, budget: float, risk_weights: dict,
                        max_assets: int, strateji: str = "kuresel",
                        watchlist_mode: bool = False) -> dict:
    """Portföy/Bütçe Optimizasyonu'nun seçim mantığı - app.py VE
    emailer.py/emailer_standalone.py'nin HEPSİ bunu çağırır.

    Döndürür: {
        "secilenler": [{"cat","ticker","ad","skor","fiyat","lot","gercek","rsi","ret1m"}, ...],
        "elenen": [kategori, ...],  # kendi havuzunda aday olsa bile secime giremeyen (SADECE "kuresel"da anlamli)
        "karsilanamayan": [kategori, ...],  # payini karsilayacak hicbir varlik bulunamayan
    }
    """
    MIN_SKOR = 60.0
    bos_sonuc = {"secilenler": [], "elenen": [], "karsilanamayan": []}
    if df_uni is None or df_uni.empty:
        return bos_sonuc

    cat_pools = {}
    for cat, weight in risk_weights.items():
        if weight <= 0:
            continue
        if cat == "TEFAS":
            df_c = df_uni[(df_uni["Kategori"] == cat) & (df_uni["Ret1M"] != 0)].copy()
        else:
            df_c = df_uni[(df_uni["Kategori"] == cat) & (df_uni["Son_Fiyat"] > 0)].copy()
        if df_c.empty:
            continue
        df_c["_skor"] = df_c.apply(_skor_hesapla, axis=1)
        df_c = (df_c[(df_c["Ret1M"] > 0) & (df_c["_skor"] >= MIN_SKOR)]
                .sort_values(["_skor", "Ticker"], ascending=[False, True], kind="mergesort"))
        if not df_c.empty:
            cat_pools[cat] = df_c

    if not cat_pools:
        return bos_sonuc

    def _satir_ekle(cat, row, price, lot, gercek, skor):
        return {
            "cat": cat, "ticker": row["Ticker"], "ad": str(row.get("Ad", row["Ticker"])),
            "skor": skor, "fiyat": price, "lot": lot, "gercek": gercek,
            "rsi": float(row.get("RSI", 50)), "ret1m": float(row.get("Ret1M", 0)),
            "gercek_fiyat_var": float(row.get("Son_Fiyat", 0)) > 0,
        }

    if watchlist_mode:
        _tum_havuz = pd.concat(
            [df.assign(_Kategori=c) for c, df in cat_pools.items()], ignore_index=True
        ).sort_values(["_skor", "Ticker"], ascending=[False, True], kind="mergesort")
        secilenler = []
        for _, row in _tum_havuz.head(max_assets).iterrows():
            price = float(row.get("Son_Fiyat", 0)) if float(row.get("Son_Fiyat", 0)) > 0 else 1.0
            secilenler.append(_satir_ekle(row["_Kategori"], row, price, 0, 0.0, float(row["_skor"])))
        elenen = [c for c in risk_weights if risk_weights.get(c, 0) > 0 and c not in cat_pools]
        return {"secilenler": secilenler, "elenen": elenen, "karsilanamayan": []}

    if strateji == "kategori_guvenceli":
        # Eski emailer.py mantığı: her kategoriye (en az 1 aday varsa)
        # garantili bir slot - max_assets kategori sayısına esit bolunur.
        n_cats = len(cat_pools)
        max_per_cat = max(1, max_assets // n_cats)
        adj_weights = {}
        total_adj = 0.0
        for cat, weight in risk_weights.items():
            if cat not in cat_pools:
                continue
            quality = float(cat_pools[cat]["_skor"].head(max_per_cat).mean()) / 100.0
            adj = weight * quality
            adj_weights[cat] = adj
            total_adj += adj
        if total_adj > 0:
            adj_weights = {c: a / total_adj for c, a in adj_weights.items()}

        secilenler = []
        for cat, weight in adj_weights.items():
            sample = cat_pools[cat].head(max_per_cat)
            cat_bud = budget * weight
            per = cat_bud / len(sample) if len(sample) else 0.0
            for _, row in sample.iterrows():
                price = float(row["Son_Fiyat"]) if float(row.get("Son_Fiyat", 0)) > 0 else 1.0
                lot = int(per / price) if price > 0 else 0
                gercek = round(lot * price, 2)
                secilenler.append(_satir_ekle(cat, row, price, lot, gercek, float(row["_skor"])))

        if len(secilenler) < max_assets:
            already = {(s["cat"], s["ticker"]) for s in secilenler}
            for cat in cat_pools:
                for _, row in cat_pools[cat].iterrows():
                    if len(secilenler) >= max_assets:
                        break
                    if (cat, row["Ticker"]) in already:
                        continue
                    price = float(row.get("Son_Fiyat", 0)) if float(row.get("Son_Fiyat", 0)) > 0 else 1.0
                    per = budget / max_assets
                    lot = int(per / price) if price > 0 else 0
                    gercek = round(lot * price, 2)
                    secilenler.append(_satir_ekle(cat, row, price, lot, gercek, float(row["_skor"])))

        elenen = [c for c in risk_weights if risk_weights.get(c, 0) > 0 and c not in cat_pools]
        return {"secilenler": secilenler, "elenen": elenen, "karsilanamayan": []}

    # strateji == "kuresel" (varsayılan): saf küresel en-iyi-N, kategori
    # çeşitlendirme garantisi YOK (Bahri'nin açık kararı).
    _tum_havuz = pd.concat(
        [df.assign(_Kategori=c) for c, df in cat_pools.items()], ignore_index=True
    ).sort_values(["_skor", "Ticker"], ascending=[False, True], kind="mergesort")
    _secilenler_havuz = _tum_havuz.head(max_assets)
    slots = {c: 0 for c in cat_pools}
    for _cat, _grp in _secilenler_havuz.groupby("_Kategori"):
        slots[_cat] = len(_grp)

    adj_weights = {}
    total_adj = 0.0
    for cat, weight in risk_weights.items():
        if cat not in cat_pools:
            continue
        mpc = slots.get(cat, 0)
        if mpc <= 0:
            continue
        quality = float(cat_pools[cat]["_skor"].head(mpc).mean()) / 100.0
        adj = weight * quality
        adj_weights[cat] = adj
        total_adj += adj
    if total_adj > 0:
        adj_weights = {c: a / total_adj for c, a in adj_weights.items()}

    secilenler = []
    karsilanamayan = []
    for cat, weight in adj_weights.items():
        df_c = cat_pools[cat]
        mpc = slots.get(cat, 0)
        sample = df_c.head(min(mpc, len(df_c)))
        cat_bud = budget * weight
        aktif = list(sample.iterrows())
        per = 0.0
        while aktif:
            pay = cat_bud / len(aktif)
            karsilayamayan = [
                i for i, (_, row) in enumerate(aktif)
                if (float(row["Son_Fiyat"]) if float(row.get("Son_Fiyat", 0)) > 0 else 1.0) > pay
            ]
            if not karsilayamayan:
                per = pay
                break
            aktif = [item for i, item in enumerate(aktif) if i not in karsilayamayan]
        else:
            per = 0.0
        if not aktif:
            karsilanamayan.append(cat)
            continue
        for _, row in aktif:
            price = float(row["Son_Fiyat"]) if float(row.get("Son_Fiyat", 0)) > 0 else 1.0
            lot = int(per / price) if price > 0 else int(per)
            gercek = round(lot * price, 2) if float(row.get("Son_Fiyat", 0)) > 0 else per
            secilenler.append(_satir_ekle(cat, row, price, lot, gercek, float(row["_skor"])))

    elenen = [c for c in risk_weights if risk_weights.get(c, 0) > 0 and c not in adj_weights]
    return {"secilenler": secilenler, "elenen": elenen, "karsilanamayan": karsilanamayan}
