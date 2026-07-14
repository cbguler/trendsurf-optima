"""
portfolio_ledger.py — TrendSurf Optima
v2.0.7.47 - Portföyüm sayfasına gerçek bir muhasebe katmanı (Bahri'nin
talebi): satış işlemleri kalıcı olarak kaydedilir, komisyon+vergi düşülmüş
NET gerçekleşmiş kâr/zarar hesaplanır, tarih aralığına göre ve aylık/yıllık
özet raporlanabilir.

ÖNEMLİ - VERGİ/KOMİSYON ORANLARI HAKKINDA:
Aşağıdaki varsayılan oranlar GENEL VE YAKLAŞIK tahminlerdir, kesin bir mali
müşavirlik/vergi danışmanlığı değildir. Türkiye'de stopaj/komisyon oranları
varlık türüne, işlem tarihine, aracı kuruma ve mevzuat değişikliklerine göre
değişir. Kullanıcı bu oranları kendi durumuna göre DÜZENLEMELİDİR - sistem
sadece bir başlangıç noktası/hesap makinesi sunar, resmi beyan yerine
geçmez.
"""
from datetime import datetime, date
import pandas as pd

# v2.0.7.47 - Kategori bazlı VARSAYILAN (öneri) oranlar - genel piyasa
# pratiğine dayanan kaba tahminlerdir, kesin değildir. Kullanıcı Portföyüm
# sayfasındaki "Komisyon/Vergi Ayarları" bölümünden değiştirebilir.
VARSAYILAN_ORANLAR = {
    "BIST":   {"fee_pct": 0.15, "tax_pct": 0.0},
    "TEFAS":  {"fee_pct": 0.0,  "tax_pct": 0.0},
    "KRIPTO": {"fee_pct": 0.10, "tax_pct": 0.0},
    "DOVIZ":  {"fee_pct": 0.0,  "tax_pct": 0.0},
    "MADEN":  {"fee_pct": 0.10, "tax_pct": 0.0},
}


def get_fee_settings(user_id: int) -> dict:
    """Kullanıcının kategori bazlı komisyon/vergi oranlarını döner.
    Hiç ayarlanmamışsa VARSAYILAN_ORANLAR ile otomatik doldurulur."""
    from db import get_conn
    conn = get_conn()
    rows = conn.execute(
        "SELECT asset_type, fee_pct, tax_pct FROM portfolio_fee_settings WHERE user_id=?",
        (user_id,)
    ).fetchall()
    conn.close()
    mevcut = {r[0]: {"fee_pct": float(r[1]), "tax_pct": float(r[2])} for r in rows}
    sonuc = {}
    eksikler = []
    for cat, varsayilan in VARSAYILAN_ORANLAR.items():
        if cat in mevcut:
            sonuc[cat] = mevcut[cat]
        else:
            sonuc[cat] = dict(varsayilan)
            eksikler.append(cat)
    if eksikler:
        _seed_fee_settings(user_id, eksikler)
    return sonuc


def _seed_fee_settings(user_id: int, kategoriler: list):
    """İlk kullanımda eksik kategorileri varsayılan oranlarla veritabanına yazar."""
    from db import get_conn
    conn = get_conn()
    for cat in kategoriler:
        v = VARSAYILAN_ORANLAR.get(cat, {"fee_pct": 0.0, "tax_pct": 0.0})
        try:
            conn.execute(
                "INSERT INTO portfolio_fee_settings (user_id, asset_type, fee_pct, tax_pct) "
                "VALUES (?,?,?,?)",
                (user_id, cat, v["fee_pct"], v["tax_pct"])
            )
        except Exception:
            pass
    conn.commit(); conn.close()


def save_fee_settings(user_id: int, asset_type: str, fee_pct: float, tax_pct: float) -> bool:
    """Kullanıcının bir kategori için komisyon/vergi oranını günceller (upsert)."""
    from db import get_conn
    conn = get_conn()
    _var = conn.execute(
        "SELECT 1 FROM portfolio_fee_settings WHERE user_id=? AND asset_type=?",
        (user_id, asset_type)
    ).fetchone()
    if _var:
        conn.execute(
            "UPDATE portfolio_fee_settings SET fee_pct=?, tax_pct=? "
            "WHERE user_id=? AND asset_type=?",
            (fee_pct, tax_pct, user_id, asset_type)
        )
    else:
        conn.execute(
            "INSERT INTO portfolio_fee_settings (user_id, asset_type, fee_pct, tax_pct) "
            "VALUES (?,?,?,?)",
            (user_id, asset_type, fee_pct, tax_pct)
        )
    conn.commit(); conn.close()
    return True


def sell_portfolio_item(user_id: int, item_id: int, sell_qty: float, sell_price: float,
                         sell_date: str, fee_pct: float, tax_pct: float,
                         note: str = "") -> dict:
    """Bir pozisyondan (kısmi veya tam) satış yapar. Kalıcı bir satış kaydı
    oluşturur (portfolio_sales), açık pozisyonu günceller/kapatır.

    Hesaplama:
      brut_kz    = (satis_fiyati - alis_fiyati) * miktar
      komisyon   = (alis_degeri + satis_degeri) * fee_pct/100  (gidiş-dönüş)
      vergi      = max(0, brut_kz) * tax_pct/100  (sadece kârdan, zarar
                   vergilendirilmez - Türk vergi mevzuatının genel mantığı,
                   kesin oran/istisna için mali müşavire danışılmalıdır)
      net_kz     = brut_kz - komisyon - vergi

    Döner: {"basari":bool, "hata":str|None, "brut_kz":float, "net_kz":float,
            "komisyon":float, "vergi":float, "net_hasilat":float}
    """
    from db import get_conn
    conn = get_conn()
    row = conn.execute(
        "SELECT ticker, asset_type, quantity, avg_cost, unit_type, purchase_date "
        "FROM portfolio WHERE id=? AND user_id=?",
        (item_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"basari": False, "hata": "Pozisyon bulunamadı."}

    ticker, asset_type, quantity, avg_cost, unit_type, purchase_date = row
    quantity = float(quantity); avg_cost = float(avg_cost)

    if sell_qty <= 0:
        conn.close()
        return {"basari": False, "hata": "Satış miktarı 0'dan büyük olmalı."}
    if sell_qty > quantity + 1e-9:
        conn.close()
        return {"basari": False, "hata": f"Elinizde sadece {quantity:g} {unit_type} var."}

    alis_degeri  = sell_qty * avg_cost
    satis_degeri = sell_qty * sell_price
    brut_kz      = satis_degeri - alis_degeri
    komisyon     = round((alis_degeri + satis_degeri) * fee_pct / 100.0, 2)
    vergi        = round(max(0.0, brut_kz) * tax_pct / 100.0, 2)
    net_kz       = round(brut_kz - komisyon - vergi, 2)
    net_hasilat  = round(satis_degeri - komisyon - vergi, 2)

    try:
        conn.execute(
            "INSERT INTO portfolio_sales "
            "(user_id, asset_type, ticker, unit_type, quantity, buy_price, buy_date, "
            " sell_price, sell_date, fee_pct, tax_pct, fee_amount, tax_amount, "
            " gross_pl, net_pl, note) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, asset_type, ticker, unit_type, sell_qty, avg_cost, purchase_date,
             sell_price, sell_date, fee_pct, tax_pct, komisyon, vergi,
             round(brut_kz, 2), net_kz, note)
        )
        kalan = round(quantity - sell_qty, 8)
        if kalan <= 1e-9:
            conn.execute("DELETE FROM portfolio WHERE id=? AND user_id=?", (item_id, user_id))
        else:
            conn.execute(
                "UPDATE portfolio SET quantity=? WHERE id=? AND user_id=?",
                (kalan, item_id, user_id)
            )
        conn.commit()
    except Exception as e:
        conn.rollback(); conn.close()
        return {"basari": False, "hata": f"Kayıt hatası: {e}"}
    conn.close()
    return {"basari": True, "hata": None, "brut_kz": round(brut_kz, 2), "net_kz": net_kz,
            "komisyon": komisyon, "vergi": vergi, "net_hasilat": net_hasilat}


def get_sales_history(user_id: int, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Kullanıcının gerçekleşmiş (satılmış) tüm işlemlerini döner, isteğe
    bağlı tarih aralığı filtresiyle (sell_date bazlı, YYYY-MM-DD)."""
    from db import get_conn
    conn = get_conn()
    q = ("SELECT id, asset_type, ticker, unit_type, quantity, buy_price, buy_date, "
         "sell_price, sell_date, fee_pct, tax_pct, fee_amount, tax_amount, "
         "gross_pl, net_pl, note FROM portfolio_sales WHERE user_id=?")
    params = [user_id]
    if start_date:
        q += " AND sell_date >= ?"; params.append(start_date)
    if end_date:
        q += " AND sell_date <= ?"; params.append(end_date)
    q += " ORDER BY sell_date DESC"
    rows = conn.execute(q, tuple(params)).fetchall()
    conn.close()
    cols = ["id", "Kategori", "Ticker", "Birim", "Miktar", "Alış Fiyatı", "Alış Tarihi",
            "Satış Fiyatı", "Satış Tarihi", "Komisyon %", "Vergi %", "Komisyon (₺)",
            "Vergi (₺)", "Brüt K/Z", "Net K/Z", "Not"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


def get_monthly_summary(user_id: int) -> pd.DataFrame:
    """Aylık bazda gerçekleşmiş net K/Z özeti (en yeni ay en üstte)."""
    df = get_sales_history(user_id)
    if df.empty:
        return pd.DataFrame(columns=["Ay", "İşlem Sayısı", "Toplam Net K/Z"])
    df = df.copy()
    df["Ay"] = pd.to_datetime(df["Satış Tarihi"], errors="coerce").dt.strftime("%Y-%m")
    ozet = (df.groupby("Ay")
              .agg(**{"İşlem Sayısı": ("Net K/Z", "count"),
                      "Toplam Net K/Z": ("Net K/Z", "sum")})
              .reset_index()
              .sort_values("Ay", ascending=False))
    ozet["Toplam Net K/Z"] = ozet["Toplam Net K/Z"].round(2)
    return ozet


def get_yearly_summary(user_id: int) -> pd.DataFrame:
    """Yıllık bazda gerçekleşmiş net K/Z özeti (en yeni yıl en üstte)."""
    df = get_sales_history(user_id)
    if df.empty:
        return pd.DataFrame(columns=["Yıl", "İşlem Sayısı", "Toplam Net K/Z"])
    df = df.copy()
    df["Yıl"] = pd.to_datetime(df["Satış Tarihi"], errors="coerce").dt.strftime("%Y")
    ozet = (df.groupby("Yıl")
              .agg(**{"İşlem Sayısı": ("Net K/Z", "count"),
                      "Toplam Net K/Z": ("Net K/Z", "sum")})
              .reset_index()
              .sort_values("Yıl", ascending=False))
    ozet["Toplam Net K/Z"] = ozet["Toplam Net K/Z"].round(2)
    return ozet


def get_realized_summary(user_id: int, start_date: str = None, end_date: str = None) -> dict:
    """Belirli bir tarih aralığındaki (veya tüm zamanların) gerçekleşmiş
    K/Z özetini döner: toplam brüt, toplam komisyon, toplam vergi, toplam net."""
    df = get_sales_history(user_id, start_date, end_date)
    if df.empty:
        return {"islem_sayisi": 0, "brut_kz": 0.0, "komisyon": 0.0,
                "vergi": 0.0, "net_kz": 0.0}
    return {
        "islem_sayisi": len(df),
        "brut_kz":  round(float(df["Brüt K/Z"].sum()), 2),
        "komisyon": round(float(df["Komisyon (₺)"].sum()), 2),
        "vergi":    round(float(df["Vergi (₺)"].sum()), 2),
        "net_kz":   round(float(df["Net K/Z"].sum()), 2),
    }
