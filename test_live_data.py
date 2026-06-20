"""
test_live_data.py - TrendSurf Optima v1.6 yerel canli veri testi (revize)
========================================================================
borsapy 0.10+ icin: FX.current ve Crypto.current ikisi de dict donduruyor,
fiyat 'last' anahtarinda. Test bunu dogru cikariyor.
"""
import sys

try:
    import borsapy as bp
    print(f"borsapy yuklu - surum: {getattr(bp, '__version__', 'bilinmiyor')}")
except ImportError:
    print("HATA: borsapy yuklu degil. Cozum: pip install borsapy")
    sys.exit(1)


def _price_from(obj):
    try:
        v = obj.current
        if isinstance(v, dict):
            for k in ("last", "lastPrice", "price", "close", "sell"):
                if k in v and v[k] is not None:
                    return float(v[k])
            return None
        return float(v) if v is not None else None
    except Exception as e:
        return f"HATA: {type(e).__name__}: {str(e)[:80]}"


print()
print("=" * 60)
print("DOVIZ - canlidoviz.com / borsapy.FX")
print("=" * 60)
for ticker, code in [("USDTRY","USD"), ("EURTRY","EUR"),
                     ("JPYTRY","JPY"), ("CADTRY","CAD"),
                     ("DKKTRY","DKK"), ("CHFTRY","CHF"),
                     ("AUDTRY","AUD"), ("NOKTRY","NOK")]:
    r = _price_from(bp.FX(code))
    if isinstance(r, (int, float)):
        # JPY canlidoviz'de '100 yen basina' verildigi icin /100
        if ticker == "JPYTRY":
            r = r / 100.0
        print(f"  {ticker:8} -> {r:>14.6f} TL  (borsapy: '{code}')")
    else:
        print(f"  {ticker:8} -> {r}")

print()
print("=" * 60)
print("MADEN - canlidoviz.com / borsapy.FX (TRY-direkt gram)")
print("=" * 60)
for ticker, code in [("ALTIN_TRY","gram-altin"),
                     ("GUMUS_TRY","gram-gumus"),
                     ("PLATIN_TRY","gram-platin")]:
    r = _price_from(bp.FX(code))
    if isinstance(r, (int, float)):
        print(f"  {ticker:12} -> {r:>12.4f} TL/gram  (borsapy: '{code}')")
    else:
        print(f"  {ticker:12} -> {r}")

print()
print("=" * 60)
print("MADEN ek - Harem Altin (institution_rate)")
print("=" * 60)
try:
    inst = bp.FX("gram-altin").institution_rate("harem")
    print(f"  Harem buy={inst.get('buy')} sell={inst.get('sell')} spread={inst.get('spread')}")
except Exception as e:
    print(f"  HATA: {e}")

print()
print("=" * 60)
print("KRIPTO - BtcTurk / borsapy.Crypto (TRY-direkt)")
print("=" * 60)
for ticker in ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "LTC"]:
    r = _price_from(bp.Crypto(f"{ticker}TRY"))
    if isinstance(r, (int, float)):
        print(f"  {ticker:6} -> {r:>14.4f} TL  (borsapy: '{ticker}TRY')")
    else:
        print(f"  {ticker:6} -> {r}")

print()
print("=" * 60)
print("FX gecmis veri - JPYTRY 1 ay (capraz kur matematigi YOK)")
print("=" * 60)
try:
    h = bp.FX("JPY").history(period="1mo", interval="1d")
    print(f"  Satir: {len(h)}, sutunlar: {list(h.columns)}")
    if not h.empty:
        print("  Son 3 satir:")
        print(h.tail(3).to_string())
except Exception as e:
    print(f"  HATA: {e}")

print()
print("Test tamamlandi. Beklentiler:")
print("  - DOVIZ 8 ticker  -> en az 7 basari")
print("  - MADEN 3 ticker  -> hepsi basari")
print("  - Harem           -> sayi")
print("  - KRIPTO 9 ticker -> BTC+ETH+SOL+XRP kesin (BNB BtcTurk'te yok normal)")
print("  - FX gecmis veri  -> 20+ satir DataFrame")
