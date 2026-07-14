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

    # v2.0.7.53 - KRITIK DUZELTME (Bahri'nin bulgusu, ValueError): _CompatRow
    # bir dict alt sinifi - "a, b, c = row" seklinde tuple-unpacking
    # yapildiginda DEGERLER degil ANAHTARLAR (sutun isimleri) aciliyordu!
    # (dict'i dogrudan unpack etmek onun key'lerini gezer). Bu yuzden
    # "quantity" degiskenine 5.06 gibi bir sayi degil, DUZ "quantity"
    # STRING'i atanıyordu - float("quantity") da ValueError firlatiyordu.
    # Duzeltme: acik sekilde anahtarla eris.
    ticker      = row["ticker"]
    asset_type  = row["asset_type"]
    quantity    = float(row["quantity"])
    avg_cost    = float(row["avg_cost"])
    unit_type   = row["unit_type"]
    purchase_date = row["purchase_date"]

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


def delete_sale_record(user_id: int, sale_id: int, geri_ac: bool = False) -> dict:
    """v2.0.7.51 - Bir satış kaydını KALICI olarak siler (test/hatalı
    girişleri geri almak için - Bahri'nin talebi: test satışı yapmadan
    önce güvenli bir geri alma yolu olmalı).

    geri_ac=True verilirse, satılan miktar açık pozisyona geri eklenir
    (aynı ticker'da hâlâ açık bir pozisyon varsa miktarına eklenir, yoksa
    satıştaki alış fiyatı/tarihiyle yeni bir açık pozisyon oluşturulur) -
    böylece "yanlışlıkla sattım" durumunu tam olarak geri alabilirsiniz.
    geri_ac=False ise sadece muhasebe kaydı silinir, pozisyon değişmez
    (örn. test amaçlı deneme satışını temizlemek için)."""
    from db import get_conn
    conn = get_conn()
    row = conn.execute(
        "SELECT ticker, asset_type, unit_type, quantity, buy_price, buy_date "
        "FROM portfolio_sales WHERE id=? AND user_id=?",
        (sale_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"basari": False, "hata": "Satış kaydı bulunamadı."}
    ticker      = row["ticker"]
    asset_type  = row["asset_type"]
    unit_type   = row["unit_type"]
    quantity    = row["quantity"]
    buy_price   = row["buy_price"]
    buy_date    = row["buy_date"]

    if geri_ac:
        mevcut = conn.execute(
            "SELECT id, quantity FROM portfolio WHERE user_id=? AND ticker=? AND asset_type=?",
            (user_id, ticker, asset_type)
        ).fetchone()
        if mevcut:
            conn.execute(
                "UPDATE portfolio SET quantity = quantity + ? WHERE id=?",
                (float(quantity), mevcut[0])
            )
        else:
            conn.execute(
                "INSERT INTO portfolio (user_id,asset_type,ticker,quantity,avg_cost,"
                "purchase_date,unit_type) VALUES (?,?,?,?,?,?,?)",
                (user_id, asset_type, ticker, float(quantity), float(buy_price),
                 buy_date, unit_type)
            )

    conn.execute("DELETE FROM portfolio_sales WHERE id=? AND user_id=?", (sale_id, user_id))
    conn.commit(); conn.close()
    return {"basari": True, "hata": None}


def update_sale_record(user_id: int, sale_id: int, sell_qty: float, buy_price: float,
                        buy_date: str, sell_price: float, sell_date: str,
                        fee_pct: float, tax_pct: float, note: str = "") -> dict:
    """v2.0.7.52 - Bahri'nin talebi: sadece silme yetmiyor, yanlış girilen
    bir satış kaydının miktar/fiyat/tarih/oran bilgileri DÜZELTİLEBİLMELİ.

    Miktar değiştirilirse (eski kayıttaki miktardan farklıysa), açık
    pozisyon da FARKA göre otomatik ayarlanır - böylece "aslında 5 değil 6
    sattım" gibi bir düzeltme, elinizdeki güncel miktarla tutarlı kalır:
      - Düzeltilen miktar eskisinden BÜYÜKSE -> açık pozisyondan ek düşülür.
      - Düzeltilen miktar eskisinden KÜÇÜKSE -> açık pozisyona fark geri eklenir
        (pozisyon kapanmışsa yeniden açılır).
    Ticker/kategori DEĞİŞTİRİLEMEZ (yanlış varlığa taşıma değil, aynı
    kaydın rakamlarını düzeltme amaçlıdır).

    Döner: {"basari":bool, "hata":str|None, "uyari":str|None, ... yeni hesap değerleri}
    """
    from db import get_conn
    conn = get_conn()
    old = conn.execute(
        "SELECT ticker, asset_type, unit_type, quantity FROM portfolio_sales "
        "WHERE id=? AND user_id=?", (sale_id, user_id)
    ).fetchone()
    if not old:
        conn.close()
        return {"basari": False, "hata": "Satış kaydı bulunamadı."}
    ticker      = old["ticker"]
    asset_type  = old["asset_type"]
    unit_type   = old["unit_type"]
    eski_miktar = float(old["quantity"])

    if sell_qty <= 0:
        conn.close()
        return {"basari": False, "hata": "Miktar 0'dan büyük olmalı."}

    fark = sell_qty - eski_miktar  # pozitif: daha fazla satildi (pozisyondan ek dus)
    uyari = None
    if abs(fark) > 1e-9:
        pos = conn.execute(
            "SELECT id, quantity FROM portfolio WHERE user_id=? AND ticker=? AND asset_type=?",
            (user_id, ticker, asset_type)
        ).fetchone()
        if pos:
            yeni_pos_miktar = float(pos[1]) - fark
            if yeni_pos_miktar <= 1e-9:
                if yeni_pos_miktar < -1e-9:
                    uyari = ("Düzeltme, elinizdeki miktardan daha fazla satış "
                             "gösteriyor - pozisyon 0'a sabitlendi, lütfen kontrol edin.")
                conn.execute("DELETE FROM portfolio WHERE id=?", (pos[0],))
            else:
                conn.execute("UPDATE portfolio SET quantity=? WHERE id=?",
                             (yeni_pos_miktar, pos[0]))
        elif fark < 0:
            # Pozisyon tamamen kapanmisti, duzeltme daha AZ satildigini
            # gosteriyor -> farki yeni acik pozisyon olarak geri ac.
            conn.execute(
                "INSERT INTO portfolio (user_id,asset_type,ticker,quantity,avg_cost,"
                "purchase_date,unit_type) VALUES (?,?,?,?,?,?,?)",
                (user_id, asset_type, ticker, -fark, buy_price, buy_date, unit_type)
            )
        else:
            uyari = ("Açık pozisyon bulunamadı, düzeltme daha fazla satış "
                     "gösteriyor - pozisyon güncellenemedi, sadece kayıt düzeltildi.")

    alis_degeri  = sell_qty * buy_price
    satis_degeri = sell_qty * sell_price
    brut_kz      = satis_degeri - alis_degeri
    komisyon     = round((alis_degeri + satis_degeri) * fee_pct / 100.0, 2)
    vergi        = round(max(0.0, brut_kz) * tax_pct / 100.0, 2)
    net_kz       = round(brut_kz - komisyon - vergi, 2)

    conn.execute(
        "UPDATE portfolio_sales SET quantity=?, buy_price=?, buy_date=?, sell_price=?, "
        "sell_date=?, fee_pct=?, tax_pct=?, fee_amount=?, tax_amount=?, gross_pl=?, "
        "net_pl=?, note=? WHERE id=? AND user_id=?",
        (sell_qty, buy_price, buy_date, sell_price, sell_date, fee_pct, tax_pct,
         komisyon, vergi, round(brut_kz, 2), net_kz, note, sale_id, user_id)
    )
    conn.commit(); conn.close()
    return {"basari": True, "hata": None, "uyari": uyari, "net_kz": net_kz,
            "brut_kz": round(brut_kz, 2), "komisyon": komisyon, "vergi": vergi}


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
