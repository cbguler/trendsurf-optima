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
                         sell_date: str, fee_amount: float, tax_amount: float,
                         note: str = "") -> dict:
    """Bir pozisyondan (kısmi veya tam) satış yapar. Kalıcı bir satış kaydı
    oluşturur (portfolio_sales), açık pozisyonu günceller/kapatır.

    v2.0.7.58 - DUZELTME (Bahri'nin talebi): Komisyon/vergi artik YUZDEN
    HESAPLANMIYOR - aracı kurumun satış dekontunda gösterdiği GERÇEK TL
    tutarı doğrudan girilir (arayüzde kategori ortalamasına göre bir
    başlangıç önerisiyle doldurulur, kullanıcı dekonttaki gerçek tutarla
    değiştirebilir).

    Hesaplama:
      brut_kz    = (satis_fiyati - alis_fiyati) * miktar
      net_kz     = brut_kz - fee_amount - tax_amount

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
    komisyon     = round(float(fee_amount), 2)
    vergi        = round(float(tax_amount), 2)
    net_kz       = round(brut_kz - komisyon - vergi, 2)
    net_hasilat  = round(satis_degeri - komisyon - vergi, 2)
    # Kayit tutarliligi icin oransal yuzdeyi geriye hesaplayip saklıyoruz
    # (kaynak artik degil, sadece turev/bilgi amacli).
    _islem_hacmi = alis_degeri + satis_degeri
    fee_pct = round(komisyon / _islem_hacmi * 100.0, 4) if _islem_hacmi > 0 else 0.0
    tax_pct = round(vergi / brut_kz * 100.0, 4) if brut_kz > 0 else 0.0

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
                        fee_amount: float, tax_amount: float, note: str = "") -> dict:
    """v2.0.7.52 - Bahri'nin talebi: sadece silme yetmiyor, yanlış girilen
    bir satış kaydının miktar/fiyat/tarih/oran bilgileri DÜZELTİLEBİLMELİ.

    v2.0.7.57 - DUZELTME (Bahri'nin talebi): Komisyon/Vergi artik YUZDE
    olarak degil, aracı kurumun kestigi GERCEK TL TUTARI olarak dogrudan
    girilir (orn. "58" TL komisyon). Bir duzeltme yaparken kullanicinin
    elinde genelde hesap ekstresindeki GERCEK kesinti tutari olur, oran
    degil - bu yuzden dogrudan TL girisi daha dogru ve pratiktir.

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
    pos = conn.execute(
        "SELECT id, quantity FROM portfolio WHERE user_id=? AND ticker=? AND asset_type=?",
        (user_id, ticker, asset_type)
    ).fetchone()
    mevcut_pos_miktar = float(pos["quantity"]) if pos else 0.0

    if fark > 1e-9:
        # v2.0.7.55 - KRITIK DUZELTME (Bahri'nin bulgusu): miktar ARTIRILIYORSA
        # (daha fazla satildigini soyleyen bir duzeltme), elde bu farkı
        # karsilayacak kadar ACIK POZISYON olmasi SART - yoksa "10 sattim"
        # kaydini "11 sattim"a cevirmek, olmayan 1 birimi yoktan var eder.
        # Onceden bu durumda sadece UYARI verilip islem yine de kabul
        # ediliyordu - bu bir veri butunlugu ihlaliydi. Artik acikca
        # REDDEDILIYOR, hicbir sey degismiyor.
        if mevcut_pos_miktar < fark - 1e-9:
            conn.close()
            return {"basari": False, "hata":
                    f"Bu düzeltme, elinizdeki açık pozisyondan ({mevcut_pos_miktar:g} "
                    f"{unit_type}) daha fazla ek satış gösteriyor (+{fark:g} "
                    f"{unit_type} gerekiyor) - reddedildi. Miktarı azaltan bir "
                    f"düzeltme her zaman kabul edilir."}
        yeni_pos_miktar = mevcut_pos_miktar - fark
        if yeni_pos_miktar <= 1e-9:
            conn.execute("DELETE FROM portfolio WHERE id=?", (pos["id"],))
        else:
            conn.execute("UPDATE portfolio SET quantity=? WHERE id=?",
                         (yeni_pos_miktar, pos["id"]))
    elif fark < -1e-9:
        # Miktar AZALTILIYOR (daha az satildigini soyleyen bir duzeltme) -
        # fark her zaman kabul edilir, acik pozisyona geri eklenir.
        if pos:
            conn.execute("UPDATE portfolio SET quantity = quantity + ? WHERE id=?",
                         (-fark, pos["id"]))
        else:
            conn.execute(
                "INSERT INTO portfolio (user_id,asset_type,ticker,quantity,avg_cost,"
                "purchase_date,unit_type) VALUES (?,?,?,?,?,?,?)",
                (user_id, asset_type, ticker, -fark, buy_price, buy_date, unit_type)
            )

    alis_degeri  = sell_qty * buy_price
    satis_degeri = sell_qty * sell_price
    brut_kz      = satis_degeri - alis_degeri
    # v2.0.7.57 - Bahri'nin talebi: komisyon/vergi artik yuzdeden HESAPLANMIYOR,
    # aracı kurumun kestigi GERCEK TL tutari dogrudan kullaniliyor.
    komisyon     = round(float(fee_amount), 2)
    vergi        = round(float(tax_amount), 2)
    net_kz       = round(brut_kz - komisyon - vergi, 2)
    # Kayit tutarliligi icin orantili yuzdeyi geriye hesaplayip saklıyoruz
    # (baska bir yerde "Komisyon %" gosterilmek istenirse anlamli kalsin diye) -
    # ama artik hesaplamanin KAYNAGI degil, sadece bir turev bilgi.
    _islem_hacmi = alis_degeri + satis_degeri
    fee_pct = round(komisyon / _islem_hacmi * 100.0, 4) if _islem_hacmi > 0 else 0.0
    tax_pct = round(vergi / brut_kz * 100.0, 4) if brut_kz > 0 else 0.0

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
    # v2.0.7.54 - KRITIK DUZELTME (Bahri'nin bulgusu - tum sutunlar None
    # gorunuyordu): "rows" _CompatRow (dict alt sinifi) nesnelerinden
    # olusuyor. pd.DataFrame(rows, columns=cols) cagrisi, data bir dict
    # listesi oldugunda pandas'in ANAHTAR bazli sutun esleme davranisina
    # giriyor - "cols" Turkce goruntu isimleri (Kategori, Ticker, ...)
    # oldugu icin gercek SQL sutun adlariyla (asset_type, ticker, ...)
    # HICBIRI eslesmiyor, "id" haric hepsi NaN/None kaliyordu. Duzeltme:
    # her satiri ACIKCA pozisyonel bir listeye cevirip (SELECT'teki sirayla
    # birebir ayni) DataFrame'i tuple/list verisinden kurmak - dict
    # anahtar eslemesine hic girmez.
    veri = [[r[i] for i in range(len(cols))] for r in rows]
    return pd.DataFrame(veri, columns=cols)


def get_monthly_summary(user_id: int, df: pd.DataFrame = None) -> pd.DataFrame:
    """Aylık bazda gerçekleşmiş net K/Z özeti (en yeni ay en üstte).

    v2.0.7.62 - PERFORMANS DUZELTMESI (Bahri'nin bulgusu: "sistem
    agirlasti"): onceden her cagri kendi get_sales_history() sorgusunu
    ayrica calistiriyordu - Portfoyum sayfasinda AYNI veri 4 kez ayri
    ayri veritabanindan cekiliyordu. Artik cagiran taraf (app.py) veriyi
    BIR KEZ cekip "df" parametresiyle burada tekrar kullanabilir -
    verilmezse eskisi gibi kendi sorgusunu yapar (geriye donuk uyumlu).

    v2.0.7.99 - Bahri'nin talebi (20 Temmuz 2026): "İşlem Tutarı (₺)"
    (o aydaki tum satislarin TOPLAM TL tutari, Miktar x Satis Fiyati)
    "Toplam Net K/Z"'den HEMEN ONCE eklendi - banka dekontlarindaki
    tutarlarla aylik mutabakat yapilabilsin diye (bkz. Tum Islem
    Gecmisi'ndeki "Satis Tutari" sutunuyla ayni mantik/hesap)."""
    if df is None:
        df = get_sales_history(user_id)
    if df.empty:
        return pd.DataFrame(columns=["Ay", "İşlem Sayısı", "Ödenmiş Komisyon (₺)",
                                      "Ödenmiş Vergi (₺)", "İşlem Tutarı (₺)", "Toplam Net K/Z"])
    df = df.copy()
    df["Ay"] = pd.to_datetime(df["Satış Tarihi"], errors="coerce").dt.strftime("%Y-%m")
    df["_Satış Tutarı"] = df["Miktar"] * df["Satış Fiyatı"]
    ozet = (df.groupby("Ay")
              .agg(**{"İşlem Sayısı": ("Net K/Z", "count"),
                      "Ödenmiş Komisyon (₺)": ("Komisyon (₺)", "sum"),
                      "Ödenmiş Vergi (₺)": ("Vergi (₺)", "sum"),
                      "İşlem Tutarı (₺)": ("_Satış Tutarı", "sum"),
                      "Toplam Net K/Z": ("Net K/Z", "sum")})
              .reset_index()
              .sort_values("Ay", ascending=False))
    ozet["Ödenmiş Komisyon (₺)"] = ozet["Ödenmiş Komisyon (₺)"].round(2)
    ozet["Ödenmiş Vergi (₺)"] = ozet["Ödenmiş Vergi (₺)"].round(2)
    ozet["İşlem Tutarı (₺)"] = ozet["İşlem Tutarı (₺)"].round(2)
    ozet["Toplam Net K/Z"] = ozet["Toplam Net K/Z"].round(2)
    return ozet


def get_yearly_summary(user_id: int, df: pd.DataFrame = None) -> pd.DataFrame:
    """Yıllık bazda gerçekleşmiş net K/Z özeti (en yeni yıl en üstte).
    v2.0.7.62 - bkz. get_monthly_summary docstring (ayni performans notu).
    v2.0.7.99 - bkz. get_monthly_summary docstring (ayni "İşlem Tutarı
    (₺)" eklemesi, yıllık bazda)."""
    if df is None:
        df = get_sales_history(user_id)
    if df.empty:
        return pd.DataFrame(columns=["Yıl", "İşlem Sayısı", "Ödenmiş Komisyon (₺)",
                                      "Ödenmiş Vergi (₺)", "İşlem Tutarı (₺)", "Toplam Net K/Z"])
    df = df.copy()
    df["Yıl"] = pd.to_datetime(df["Satış Tarihi"], errors="coerce").dt.strftime("%Y")
    df["_Satış Tutarı"] = df["Miktar"] * df["Satış Fiyatı"]
    ozet = (df.groupby("Yıl")
              .agg(**{"İşlem Sayısı": ("Net K/Z", "count"),
                      "Ödenmiş Komisyon (₺)": ("Komisyon (₺)", "sum"),
                      "Ödenmiş Vergi (₺)": ("Vergi (₺)", "sum"),
                      "İşlem Tutarı (₺)": ("_Satış Tutarı", "sum"),
                      "Toplam Net K/Z": ("Net K/Z", "sum")})
              .reset_index()
              .sort_values("Yıl", ascending=False))
    ozet["Ödenmiş Komisyon (₺)"] = ozet["Ödenmiş Komisyon (₺)"].round(2)
    ozet["Ödenmiş Vergi (₺)"] = ozet["Ödenmiş Vergi (₺)"].round(2)
    ozet["İşlem Tutarı (₺)"] = ozet["İşlem Tutarı (₺)"].round(2)
    ozet["Toplam Net K/Z"] = ozet["Toplam Net K/Z"].round(2)
    return ozet


def get_realized_summary(user_id: int, start_date: str = None, end_date: str = None,
                          df: pd.DataFrame = None) -> dict:
    """Belirli bir tarih aralığındaki (veya tüm zamanların) gerçekleşmiş
    K/Z özetini döner: toplam brüt, toplam komisyon, toplam vergi, toplam net.
    v2.0.7.62 - "df" onceden cekilmis (filtresiz) tam gecmis verilir,
    tarih filtresi burada pandas ile uygulanir - ayri bir SQL sorgusu
    gerekmez."""
    if df is None:
        df = get_sales_history(user_id, start_date, end_date)
    else:
        if start_date:
            df = df[df["Satış Tarihi"] >= start_date]
        if end_date:
            df = df[df["Satış Tarihi"] <= end_date]
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


# ══════════════════════════════════════════════════════════════════
# v2.0.7.112 - SERMAYE / NAKİT TAKİBİ (Bahri'nin talebi, 30 Temmuz 2026)
# ══════════════════════════════════════════════════════════════════
# Bahri'nin tarifi: "başlangıç sermaye miktarının, ne kadar zamanda kaça
# geldiğinin, sattığımda ne kâr ettiğimin (bu kısım zaten portfolio_sales
# ile vardı) ve elimde güncel olarak finansal varlık veya nakit olarak ne
# miktarlar olduğunun kayıt altına alınması" isteniyor.
#
# Tasarım kararları (Bahri'nin onayıyla):
# 1. Sermaye TEK SEFERLİK sabit bir sayı DEĞİL - zaman içinde MEVDUAT/ÇEKİM
#    kayıtları eklenip çıkarılabilen bir HAREKET DEFTERİ (portfolio_sales'in
#    satış geçmişi tuttuğu mantığın aynısı).
# 2. Nakit bakiyesi NEGATİFE DÜŞEBİLİR - bilinçli olarak sınırlanmadı.
#    Bahri: "sermaye hayali değil, gerçek durumu göstersin" - yani alım
#    yaparken "yeterli nakit yok" diye engellenmiyor, sistem sadece
#    olduğu gibi (borçlu bile olsa) gösteriyor.
# 3. Nakit bakiyesi bir tablo SÜTUNU olarak SAKLANMIYOR - her seferinde
#    şu formülle TÜRETİLİYOR (portfolio_sales'teki net_pl mantığıyla aynı
#    "tek doğru kaynak" felsefesi):
#
#    Nakit = (Toplam Mevduat - Toplam Çekim)
#            - (açık pozisyonların toplam maliyeti + satılmış lotların
#               toplam maliyeti)      [= tüm zamanlarda alışa harcanan]
#            + (satışlardan elde edilen NET tutarların toplamı)
#               [= satış fiyatı x miktar - komisyon - vergi]
#
#    Böylece: hâlâ elde tutulan varlıkların maliyeti nakitten düşülmüş
#    olur (o para varlığa dönüşmüştür), satılanların net geliri nakde geri
#    eklenir - tıpkı gerçek bir yatırım hesabında olduğu gibi.

def add_capital_tx(user_id: int, tx_type: str, amount: float, tx_date: str,
                    note: str = "") -> dict:
    """Yeni bir sermaye hareketi (mevduat/çekim) kaydeder.
    tx_type: 'DEPOSIT' (para yatırma) veya 'WITHDRAWAL' (para çekme)."""
    from db import get_conn
    if tx_type not in ("DEPOSIT", "WITHDRAWAL"):
        return {"basari": False, "hata": "Geçersiz işlem tipi."}
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return {"basari": False, "hata": "Geçersiz tutar."}
    if amount <= 0:
        return {"basari": False, "hata": "Tutar 0'dan büyük olmalı."}
    conn = get_conn()
    conn.execute(
        "INSERT INTO portfolio_capital_tx (user_id, tx_type, amount, tx_date, note) "
        "VALUES (?,?,?,?,?)",
        (user_id, tx_type, amount, tx_date, note)
    )
    conn.commit(); conn.close()
    return {"basari": True}


def delete_capital_tx(user_id: int, tx_id: int) -> bool:
    from db import get_conn
    conn = get_conn()
    conn.execute(
        "DELETE FROM portfolio_capital_tx WHERE id=? AND user_id=?", (tx_id, user_id)
    )
    conn.commit(); conn.close()
    return True


def get_capital_tx_history(user_id: int) -> pd.DataFrame:
    """Kullanıcının tüm mevduat/çekim geçmişini döner (en yeni üstte)."""
    from db import get_conn
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, tx_type, amount, tx_date, note FROM portfolio_capital_tx "
        "WHERE user_id=? ORDER BY tx_date DESC, id DESC", (user_id,)
    ).fetchall()
    conn.close()
    cols = ["id", "Tip", "Tutar", "Tarih", "Not"]
    if not rows:
        return pd.DataFrame(columns=cols)
    veri = [[r[i] for i in range(len(cols))] for r in rows]
    return pd.DataFrame(veri, columns=cols)


def get_net_capital(user_id: int, df: pd.DataFrame = None) -> float:
    """Net yatırılan sermaye = toplam mevduat - toplam çekim."""
    if df is None:
        df = get_capital_tx_history(user_id)
    if df.empty:
        return 0.0
    yatirilan = float(df.loc[df["Tip"] == "DEPOSIT", "Tutar"].sum())
    cekilen = float(df.loc[df["Tip"] == "WITHDRAWAL", "Tutar"].sum())
    return round(yatirilan - cekilen, 2)


def get_cash_balance(user_id: int, portfolio_rows: list = None,
                      sales_df: pd.DataFrame = None,
                      capital_df: pd.DataFrame = None) -> dict:
    """Güncel nakit bakiyesini ve bileşenlerini döner. bkz. yukarıdaki
    modül-üstü not - formül: net sermaye - toplam alış maliyeti (açık +
    satılmış) + toplam net satış geliri. `portfolio_rows` verilmezse
    (app.py'nin `portfolio` listesi, dict'ler: quantity, avg_cost)
    açık pozisyon maliyeti 0 sayılır - çağıran taraf mutlaka vermeli."""
    if capital_df is None:
        capital_df = get_capital_tx_history(user_id)
    if sales_df is None:
        sales_df = get_sales_history(user_id)

    net_sermaye = get_net_capital(user_id, df=capital_df)

    acik_pozisyon_maliyeti = 0.0
    if portfolio_rows:
        acik_pozisyon_maliyeti = sum(
            float(p.get("quantity", 0)) * float(p.get("avg_cost", 0))
            for p in portfolio_rows
        )

    satilmis_lot_maliyeti = 0.0
    net_satis_geliri = 0.0
    if not sales_df.empty:
        satilmis_lot_maliyeti = float((sales_df["Miktar"] * sales_df["Alış Fiyatı"]).sum())
        net_satis_geliri = float(
            (sales_df["Satış Fiyatı"] * sales_df["Miktar"]
             - sales_df["Komisyon (₺)"] - sales_df["Vergi (₺)"]).sum()
        )

    toplam_alis_maliyeti = acik_pozisyon_maliyeti + satilmis_lot_maliyeti
    nakit = net_sermaye - toplam_alis_maliyeti + net_satis_geliri

    return {
        "net_sermaye": round(net_sermaye, 2),
        "acik_pozisyon_maliyeti": round(acik_pozisyon_maliyeti, 2),
        "satilmis_lot_maliyeti": round(satilmis_lot_maliyeti, 2),
        "net_satis_geliri": round(net_satis_geliri, 2),
        "nakit_bakiye": round(nakit, 2),
    }
