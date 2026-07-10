-- ============================================================================
-- ipo_valuations.sql — TrendSurf Optima v2.0.6.4 (10 Temmuz 2026)
-- Halka Arz degerleme sonuclarinin (arz fiyati / iskonto / Graham / Carpan)
-- KALICI katmani. Supabase SQL Editor'de BIR KEZ calistirilir.
--
-- Neden: Zorla Yenile ile hesaplanan degerler yalnizca Streamlit Cloud
-- konteynerinin yerel dosyasina yaziliyordu; uygulama yeniden baslayinca
-- kayboluyordu. Bu tablo, bir kez dogru cikarilan degeri kalici yapar.
-- Yayinlanmis bir Fiyat Tespit Raporu'nun icerigi degismedigi icin kayitlar
-- bayatlamaz. UPSERT'te COALESCE kullanilir: null asla dolu degeri EZMEZ.
-- ============================================================================

CREATE TABLE IF NOT EXISTS ipo_valuations (
    disclosure_index   TEXT PRIMARY KEY,   -- KAP bildirim no (orn. '1624187')
    arz_fiyati         NUMERIC,            -- TL
    iskonto_orani      NUMERIC,            -- yuzde (orn. 20.00)
    tip                TEXT,               -- parser fiyat deseni tipi (A/E vb.)
    graham_degeri      NUMERIC,            -- TL (bagimsiz model)
    carpan_bazli_deger NUMERIC,            -- TL (bagimsiz model)
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Diger tablolarla (intraday_scores, radar_alerts) tutarli: RLS acik.
-- Uygulama/worker dogrudan DB baglantisiyla (tablo sahibi) eristigi icin
-- etkilenmez; anon/authenticated API rolleri icin tablo kapali kalir.
ALTER TABLE ipo_valuations ENABLE ROW LEVEL SECURITY;
