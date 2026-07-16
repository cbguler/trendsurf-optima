# TrendSurf Optima — Proje Notları

**BU DOSYA HER YENİ OTURUMA BAŞLARKEN İLK OKUNMASI GEREKEN DOSYADIR.**

Amaç: sohbet geçmişi dolup yeni bir oturuma geçildiğinde, daha önce
araştırılmış/denenmiş/karar verilmiş şeylerin unutulup sıfırdan tekrar
keşfedilmesini önlemek. Kod içindeki `v2.0.7.x` yorumları teknik detayı
verir ama "neden bu karar verildi, başka ne denendi" sorusuna hızlı cevap
vermez — bu dosya o boşluğu dolduruyor.

**Kural: Bu dosyada "REDDEDİLDİ" diye işaretlenmiş bir yaklaşım tekrar
önerilmeden önce, neden reddedildiğini burada kontrol et.**

---

## 1. Veri Kaynağı Mimarisi (kategori bazlı, öncelik sırasıyla)

### BIST (772 hisse)
1. yfinance toplu indirme (`batch_bist`) — fiyat + RSI/Ret1M/Vol AYNI
   çağrıdan gelir, biri başarısız olursa ikisi de başarısız olur (atomik).
2. Fırsat Radarı (`firsat_radari.py`) — BIST seans saatlerinde (10:00-18:30)
   **15 dakikada bir TÜM 772 hisseyi** tekrar tarar, Supabase
   `intraday_scores` tablosuna yazar. `load_universe()` bunu 45 dakika
   tazelik penceresinde otomatik üstüne yazar (overlay).
   → Bu yüzden "Canlı Fiyatları Yenile" gibi manuel butonlara **gerek yok**
   (v2.0.7.64'te kaldırıldı, zaten otomatik + kapsamı daha geniş).
3. Fiyatsız (Son_Fiyat<=0) hisselerin skoru HER ZAMAN 0 (v2.0.5.2).

### TEFAS (~1.347 fon)
- `tefas_client.py` — TEFAS Excel export. RSI HER ZAMAN gerçek getiri
  verisinden hesaplanır (`_rsi_from_rets`), asla sahte nötr değer kullanmaz.

### Kripto (186 parite)
- BtcTurk (`borsapy` → `bp.Crypto(...).history()`) — fiyat ve RSI/Ret1M/Vol
  AYNI çağrıdan gelir (BIST gibi atomik, bu yüzden bu kategoride de
  "fiyat var ama sahte nötr geçmiş" hatası OLUŞAMAZ).
- Evren otomatik genişler (`borsapy.crypto_pairs("TRY")`), BIST çakışması
  olan tickerlara "C" öneki eklenir (LINK→CLINK, TRA→CTRA, SKY→CSKY).

### Döviz (63 parite: 12 ana + 51 genişleme)
- **ÖNCELİK SIRASI (v2.0.7.74 itibarıyla):**
  1. yfinance (cross-rate veya doğrudan `=X`) — 12 ana döviz için genelde
     çalışır.
  2. **Harem/canlidoviz (`borsapy.FX(kod).institution_history("harem",...)`)**
     — 51 genişleme dövizinin **TAMAMI** için gerçek tarihsel serbest
     piyasa verisi. `canlidoviz.CURRENCY_IDS` (bkz. borsapy kaynak kodu)
     bu 51 dövizin hepsini numaralı kod olarak tanıyor.
  3. Truncgil (`finans.truncgil.com/v3/today.json`) — SADECE anlık fiyat,
     geçmiş veri YOK. Son çare, `_gecmis_veri_yok=True` ile işaretlenir.
- **TCMB KULLANILMIYOR — BİLİNÇLİ OLARAK REDDEDİLDİ (v2.0.7.74).**
  Sebep: Bahri'nin talebi — "yatırımcıların kullandığı fiyatlar daha çok
  serbest piyasa fiyatlarıdır". TCMB sadece 21 döviz kapsıyordu (Harem/
  canlidoviz 51'in tamamını kapsıyor), üstelik resmi/banka kuru veriyordu.
  `tcmb_client.py` dosyası hâlâ duruyor ama worker.py'nin DOVIZ döngüsünde
  ARTIK ÇAĞRILMIYOR. **Tekrar TCMB önerme — zaten denendi, terk edildi.**
- Sayfada "Fiyatlar serbest piyasa (Harem/Kapalıçarşı) kaynaklıdır"
  notu var (Bahri'nin talebiyle eklendi).

### Değerli Madenler (18: 4 ana + 9 Truncgil türü + 5 canlı overlay sikke)
- Bigpara (TL bazlı, doğrudan) — birincil, Gram Altın/Gümüş için.
- yfinance USD→TRY çevrimi — SADECE Platin/Paladyum'un teknik göstergesi
  (RSI/Ret/Vol) için, **Son_Fiyat'ı ASLA sentetik USD*kur ile doldurmaz**
  (Bahri'nin ilkesi: gerçek TL fiyatı yoksa sentetik gösterilmez).
- Ons Altın (USD) sadece bilgi amaçlı gösterilir, evrene/skora katılmaz.

---

## 2. KAP (Kamuyu Aydınlatma Platformu) Finansal Veri — v2.0.7.66/67

- **Gerçek çalışan adres:** `kap.org.tr/tr/sirket-finansal-bilgileri/{slug}`
  — JS gerektirmeyen, sunucu tarafında render edilmiş normal HTML sayfası,
  `pandas.read_html(io.StringIO(html), flavor="lxml")` ile parse edilir.
  **"api/financialReport/..." gibi JSON endpoint'ler HİÇ GERÇEK DEĞİLDİ**
  (önceki bir oturumda hiç doğrulanmadan varsayılmış, hiçbir zaman
  çalışmamış — tekrar JSON API aramaya kalkma, HTML tablo parse doğru yol).
- `pd.read_html()`'e HAM STRING vermek pandas'ın bunu dosya yolu sanmasına
  yol açar (`FileNotFoundError`) — **her zaman `io.StringIO(html)` ile
  sarmala.**
- **Slug kaynağı: `KAP_BIST.xlsx`** (Bahri'nin verdiği, repoda duran dosya).
  3. sütununda HER ŞİRKETİN gerçek KAP finansal-bilgiler URL'si var (771
  şirket). `kap_client.py`'nin `KAP_SLUG_MAP`'i artık bu dosyadan dinamik
  okunuyor — **elle yazılmış küçük bir liste YOK ARTIK.**
- **BİLİNÇLİ OLARAK OTOMATİK DEĞİL:** Yeni halka arz olan şirketler
  KAP_BIST.xlsx'e OTOMATİK eklenmez (Bahri'nin açık talebi — yeni IPO'ların
  sisteme kontrolsüz dahil olmasını istemiyor). Yeni şirket eklemek için
  `kap_liste_guncelle.py` betiği (KAP'ın `bist-sirketler` sayfasını tarar,
  TASLAK bir `KAP_BIST_guncel.xlsx` üretir) Bahri'ye rapor verir, o
  inceleyip onaylar, sonra elle KAP_BIST.xlsx günceller.
- Türkçe büyük sayı formatı (`45.269.483.033` gibi, nokta binlik ayıraç)
  için AYRI bir fonksiyon (`_safe_float_kap_tr`) kullanılıyor —
  `_safe_float` (yfinance için) ile KARIŞTIRILMAMALI, farklı formatlar.

---

## 3. Portföyüm Muhasebe Sistemi — v2.0.7.47'den itibaren

- `portfolio_ledger.py` — ayrı modül, satış geçmişi (`portfolio_sales`
  tablosu), komisyon/vergi ayarları (`portfolio_fee_settings`).
- **Komisyon/Vergi artık YÜZDE değil, DOĞRUDAN TL TUTARI** olarak giriliyor
  (v2.0.7.57/67 — Bahri'nin talebi: "aracı kurumun kestiği gerçek tutarı
  yazayım"). Kategori bazlı yüzde ayarları sadece bir BAŞLANGIÇ ÖNERİSİ
  hesaplamak için hâlâ var, ama girilen TL tutarı esas alınır.
- Miktar **azaltan** bir düzeltme her zaman kabul edilir (fark pozisyona
  geri eklenir). Miktar **artıran** bir düzeltme, elde yeterli açık
  pozisyon yoksa **REDDEDİLİR** (v2.0.7.55 — olmayan bir satışı var gibi
  göstermemek için).
- Toplam satırı denemesi: önce AYRI bir tabloya taşınmıştı (checkbox'ı
  kaldırmak için) ama bu görsel kopukluk yarattığı için **GERİ ALINDI**
  (v2.0.7.60) — tekrar aynı tabloya döndürüldü, TOPLAM satırındaki
  checkbox tıklanabilir ama "bu bir kayıt değil" diyip hiçbir şey yapmıyor.

---

## 4. Bilinen Teknik Tuzaklar (bir daha düşme)

- **`_CompatRow` (db.py) bir dict alt sınıfıdır.** `a, b, c = row` şeklinde
  tuple-unpacking yaparsan DEĞERLERİ değil ANAHTARLARI (sütun adlarını)
  açar — bu, "ValueError: could not convert string to float: 'quantity'"
  gibi gizemli hatalara yol açar (v2.0.7.53'te 3 fonksiyonda bulundu).
  Her zaman `row["sutun_adi"]` gibi açık anahtar erişimi kullan.
- **Streamlit `column_config` genişliği tam sayı (piksel) kabul eder**,
  sadece "small"/"medium"/"large" değil. Kesin değerler: small=75px,
  medium=200px, large=400px. Yüzdelik ince ayar istenirse bunları kullan.
- **`column_config`'in gerçek bir `alignment="left/center/right"`
  parametresi var** — CSS "text-align" hack'ine gerek yok, bu daha
  güvenilir ve daha az işlem gerektirir.
- **Türkçe sayı formatı HER YERDE zorunlu** (`fmt_tr()`/`fmt_tr_isaretli()`
  kullan, asla ham `f"{x:.2f}"` veya `f"{x:,.2f}"` yazma). Bu kural bir kez
  ihlal edilip ~50 yerde toplu düzeltme gerekmişti (v2.0.7.60) — yeni bir
  sayısal değer eklerken baştan `fmt_tr` kullan.
- **Emoji/dekoratif sembol YASAK** — ne kod/UI'da ne chat yanıtlarında.
- **Her zaman GitHub'dan taze klon ile başla, yerel sandbox'a güvenme.**
  Bir oturumda yerel çalışma klasöründe GERÇEK GITHUB'A HİÇ GÖNDERİLMEMİŞ
  bir düzeltme bulunmuştu (v2.0.7.68, get_signal fonksiyonu) — muhtemelen
  önceki bir oturumda yapılıp unutulmuş. `git log -S"arama_metni"` ile bir
  değişikliğin gerçekten commit edilip edilmediğini HER ZAMAN doğrula.

---

## 5. Denenip Reddedilen / Geri Alınan Yaklaşımlar

| Yaklaşım | Durum | Sebep |
|---|---|---|
| TCMB (Döviz veri kaynağı) | REDDEDİLDİ (v2.0.7.74) | Sadece 21 döviz kapsıyor, resmi/banka kuru. Harem/canlidoviz 51'in tamamını serbest piyasa fiyatıyla kapsıyor. |
| Manuel "Canlı Fiyatları Yenile" (BIST) | KALDIRILDI (v2.0.7.64) | Fırsat Radarı zaten otomatik + daha kapsamlı (772 vs 100 hisse). |
| KAP JSON API (`api/financialReport/...`) | HİÇ GERÇEK DEĞİLDİ (v2.0.7.66) | Doğrulanmadan varsayılmış, hiçbir zaman çalışan bir endpoint olmadı. Gerçek yol: HTML tablo parse. |
| Muhasebe Toplam satırını ayrı tabloya taşımak | GERİ ALINDI (v2.0.7.60) | Görsel kopukluk yarattı, checkbox sorunundan daha kötüydü. |
| VBA makrosu (KAP şirket listesi taraması) | Python'a çevrildi | `bist-sirketler` sayfası JS'e bağımlı olabilir, Python + requests daha güvenilir. |
| Excel'deki (Şirketler.xlsx) hyperlink'lerden URL çekmek | Mümkün değil | Bu spesifik KAP export'unda gizli hyperlink yok, düz metin. |

---

## 6. Versiyon Kilometre Taşları (özet)

- v2.0.4.x: Temel sistem (BIST/TEFAS/Kripto/Döviz/Maden, KAP entegrasyonu ilk hali)
- v2.0.7.30-45: UI iyileştirmeleri, kripto/döviz/maden genişletme (20→186, 12→63, 4→18)
- v2.0.7.47-67: Muhasebe sistemi (portfolio_ledger.py), Türkçe format düzeltmeleri (sistem geneli), KAP gerçek entegrasyonu
- v2.0.7.68-71: Sinyal mantığı düzeltmeleri, veri-yok tespiti (`_gecmis_veri_yok` bayrağı)
- v2.0.7.72-74: TCMB tarihsel deneme → Harem/canlidoviz'e geçiş (TCMB tamamen terk edildi)

**Yeni bir oturumda "acaba X daha önce denendi mi" sorusu varsa, önce bu
dosyayı ve `git log --oneline` çıktısını kontrol et.**
