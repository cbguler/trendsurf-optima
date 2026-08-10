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

## 0. TEMEL İLKE (her kategoriye uygulanır — asla ihlal etme)

**Bahri'nin çekirdek prensibi (birden fazla oturumda tekrarlanmış,
en son 18 Temmuz 2026'da DOVIZ için hatırlatıldı):** Bir ürünün/paritenin
**Türkiye'de kendi gerçek piyasası** varsa (arz-talep koşulları uluslararası
piyasadan FARKLI gelişebilir), o gerçek Türkiye fiyatı HER ZAMAN tercih
edilir — USD (veya başka bir yabancı para) fiyatını alıp bir kurla ÇARPARAK/
BÖLEREK **türetilmiş (sentetik) bir fiyat asla kullanılmaz**, gerçek
kaynak bulunamıyorsa "veri yok" durumu dürüstçe gösterilir.

Bu ilkenin şimdiye kadarki uygulamaları:
- **Değerli Madenler (en eski uygulama):** Ons Altın'ın USD fiyatını
  USDTRY ile çarpıp sentetik bir TL fiyatı üretmek YASAK
  (`_MADEN_SENTETIK_CEVRIM_YASAK` seti) — gerçek TL fiyatı yoksa (Bigpara/
  Truncgil/canlidoviz'den), varlık "veri yok" kalır.
- **Döviz (v2.0.7.81, 18 Temmuz 2026):** JPYTRY/AUDTRY/CADTRY/NZDTRY/
  NOKTRY/SEKTRY/DKKTRY/CNYTRY için worker.py'de USD üzerinden **çapraz kur
  hesabı** (`get_cross_rate_hist`/`CROSS_PAIRS`) vardı — bu, canlidoviz'in
  GERÇEK Harem/serbest piyasa fiyatından (Türkiye'nin kendi piyasası) ÖNCE
  deneniyordu, yani ilkenin TAM TERSİYDİ. **Tamamen kaldırıldı** — artık
  DOVIZ döngüsünde canlidoviz (gerçek Türkiye fiyatı) HER ZAMAN ilk denenir,
  yfinance doğrudan sorgu ikinci, Truncgil (anlık-sadece) son çaredir.

**Yeni bir kategori/varlık türü eklerken bu ilkeyi baştan uygula — "yabancı
fiyat × kur" türetmesini ilk tercih yapma, önce gerçek Türkiye kaynağı ara.**

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
- **GÜNCEL ÖNCELİK SIRASI (v2.0.7.81 itibarıyla, 18 Temmuz 2026'da
  BAŞTAN YAZILDI — aşağıdaki eski notlar sadece tarihsel bağlam için
  korunuyor, GÜNCEL DAVRANIŞ bu maddedir):**
  1. **canlidoviz (`bp.FX(kod).history()`)** — TÜM 63 döviz için HER ZAMAN
     ilk denenir (Bahri'nin §0'daki temel ilkesi: gerçek Türkiye/serbest
     piyasa fiyatı, USD üzerinden türetmeden önce gelir). Kod = ticker'ın
     "TRY" son eki çıkarılmış hali (`"ZARTRY"` → `"ZAR"`).
  2. yfinance doğrudan sorgu (`single_full`) — SADECE canlidoviz
     başarısız olursa.
  3. Truncgil (`finans.truncgil.com/v3/today.json`) — SADECE anlık fiyat,
     geçmiş veri YOK, son çare. `_gecmis_veri_yok=True` ile işaretlenir.
  **USD üzerinden çapraz kur hesabı (`get_cross_rate_hist`/`CROSS_PAIRS`,
  eskiden JPY/AUD/CAD/NZD/NOK/SEK/DKK/CNY için 1. sıradaydı) v2.0.7.81'de
  TAMAMEN KALDIRILDI — bkz. §0.**
- **Harem'in kendisi (`institution_history("harem",...)`) 17 Temmuz
  2026'dan beri 401 (erişilemez) — ama bu ARTIK ÖNEMLİ DEĞİL**, çünkü
  1. maddedeki `bp.FX(kod).history()` Harem'e ihtiyaç duymuyor (MADEN'in
  9 metalinde de kanıtlanan, auth gerektirmeyen düz canlidoviz metodu).
  `doviz.com`'un kurumsal arşiv API'si (`api.doviz.com/api/v12/assets/
  .../archive`) — hem borsapy'nin kendi token çekme mekanizması hem elle
  denenen 3 sayfa (www.doviz.com, altin.doviz.com, kur.doviz.com) token
  kazıma denemesi 401 aldı. **Harem'in kendisini tekrar test etmeden
  üzerine yeni bir özellik kurma** ama bu artık DOVIZ'i bloklamıyor.
- Detay sayfasının kendi geçmiş veri fonksiyonu (`get_fx_history()` /
  `_DOVIZ_TO_BP`, live_data.py) v2.0.7.80'de 51 genişleme döviziyle
  genişletildi (worker.py'nin `_DOVIZ_TRUNCGIL_KOD`'u ile birebir aynı
  kodlar) — **iki dosyada aynı sözlük elle senkron tutulmalı**, biri
  değişirse diğeri de güncellenmeli.
- **TCMB KULLANILMIYOR — BİLİNÇLİ OLARAK REDDEDİLDİ (v2.0.7.74).**
  Sebep: Bahri'nin talebi — "yatırımcıların kullandığı fiyatlar daha çok
  serbest piyasa fiyatlarıdır". TCMB sadece 21 döviz kapsıyordu (Harem/
  canlidoviz 51'in tamamını kapsıyor), üstelik resmi/banka kuru veriyordu.
  `tcmb_client.py` dosyası hâlâ duruyor ama worker.py'nin DOVIZ döngüsünde
  ARTIK ÇAĞRILMIYOR. **Tekrar TCMB önerme — zaten denendi, terk edildi.**
- Sayfada "Fiyatlar serbest piyasa (Harem/Kapalıçarşı) kaynaklıdır"
  notu var (Bahri'nin talebiyle eklendi) — Harem şu an erişilemez olsa da
  bu not güncel kalabilir (canlidoviz de serbest piyasa verisi).

### Değerli Madenler (17: 3 ana + 9 Truncgil türü + 5 canlı overlay sikke)
- **v2.0.7.76 (17 Temmuz 2026) - Paladyum TAMAMEN KALDIRILDI.** Sebep:
  RSI/Ret1M için hiçbir kaynakta (canlidoviz'de gram-paladyum slug'ı yok,
  Harem 401 ile kapalı) geçmiş veri bulunamıyordu, sonsuza dek 0 skor/boş
  RSI gösterecekti. Bahri'nin talebiyle worker.py/bigpara_client.py/
  firsat_radari.py'den tüm izleri silindi. **Tekrar eklemeyi önerme.**
- Bigpara/Truncgil (TL bazlı, doğrudan) — birincil, Gram Altın/Gümüş/
  Platin için.
- **canlidoviz (`bp.FX(slug).history()`) 9/9 doğrulandı çalışıyor**
  (17 Temmuz 2026 testi, bkz. `test_maden_kaynak.py`): gram-altin,
  ceyrek/yarim/tam/cumhuriyet/ata-altin, gram-gumus, ons-altin,
  gram-platin — bunların hepsi GERÇEK geçmiş veri döndürüyor, Harem'e
  hiç ihtiyaç yok. Bu, ALTIN_TRY/GUMUS_TRY/PLATIN_TRY + 5 sikkenin RSI/
  Ret1M/skor hesaplarının kaynağı.
- 9 Truncgil-türü sikke/ayar (Gram Has, 14/18 Ayar, Bilezik22, İkibuçuk,
  Beşli, Gremse, Reşat, Hamit) — HİÇBİR kaynakta geçmiş veri yok (Truncgil
  sadece anlık, canlidoviz'de slug yok, Harem 401). **KESİN KARAR (Bahri,
  18 Temmuz 2026): böyle kalsınlar — fiyat gösterilmeye devam eder, RSI/
  Skor boş kalır. Kaldırılmayacaklar (Paladyum'dan farklı olarak). Bu
  konu KAPANDI, tekrar sorma.**
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

- **TEFAS'ın resmi API'si dakikada SADECE 6 istek kabul eder** (bu, kütüphanenin
  kendi `pytefas/_ratelimit.py` docstring'inde açıkça yazıyor: "TEFAS API'si
  dakikada 6 istek sınırına sahiptir"). 18 Temmuz 2026'da Bahri'nin
  çalıştırdığı fizibilite testinde (`test_tefas_bulk_fizibilite.py`) fon
  başına ~400-430 saniye (bazen 13.250 saniye/3,7 saat!) gibi anormal
  süreler gözlendi — bunun sebebi bir hata/timeout DEĞİL, `pytefas`'ın rate
  limit'e her çarptığında `reset` süresi kadar otomatik BEKLEMESİ. **Sonuç:**
  1348 TEFAS fonunun TAMAMI için tek bir gece koşusunda geçmiş veri çekmek
  pratik değil (en iyi ihtimalle ~3,7 saat, muhtemelen çok daha fazla —
  kind-fallback/retry çarpanı yüzünden). **PARALEL ÇALIŞTIRMAK YARDIMCI
  OLMAZ** — rate limit IP/hesap bazlı olduğu için birden fazla worker aynı
  6/dakika kotasını paylaşıp durumu kötüleştirir. Bu yüzden TEFAS için
  BIST tarzı "tüm evreni geceden tam skorla önceden hesapla" yaklaşımı
  şu an TERK EDİLDİ (bkz. §5 Bekleyen İşler).
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
- **`bool(x)` Python'da NaN için de `True` döner — NaN "sıfır değil"
  sayıldığından ("truthy").** Bu, `_gecmis_veri_yok` bayrağını okuyan 4
  yerde (v2.0.7.71'de yazılmış, "KRITIK DUZELTME" olarak) `bool(row.get(
  "_gecmis_veri_yok", False))` deseniyle gizli bir hataya yol açmıştı:
  bu bayrak SADECE DOVIZ/MADEN satırlarında ayarlanır, TEFAS/BIST/KRIPTO'da
  hiç yoktur — `pd.DataFrame(all_rows)` birleştirince bu kategorilerde
  sütun NaN olur, `bool(NaN)==True` olduğundan TEFAS/BIST/KRIPTO'nun TÜM
  Detay sayfaları (Ana Sayfa, kategori sayfası, Portföyüm satış-analizi,
  `live_optima_score()`) yanlışlıkla "veri yok" sanılıp skoru 0'a
  sıfırlanıyordu. Liste tablosu ise pandas'ın vektörel `== True`
  karşılaştırmasını kullandığından (`NaN == True` HER ZAMAN `False`
  döner) bu hataya hiç düşmüyordu — sonuç: liste doğru skor gösterirken
  hemen altındaki Detay paneli 0,0 gösteriyordu (17 Temmuz 2026, Bahri'nin
  bulgusu, FZJ/TEFAS örneği; v2.0.7.77'de düzeltildi). **Bahri aynı gün
  örnekleme ile TÜM TEFAS varlıklarını kontrol etti, HEPSİNDE aynı sorunu
  doğruladı** — beklenen sonuç, çünkü `_gecmis_veri_yok` TEFAS'ın 1340
  satırının TAMAMINDA NaN (worker.py bu bayrağı hiç yazmıyor). **Kural: pandas
  satırından/DataFrame'den okunan, NaN olabilecek bir bayrak/işaret sütunu
  test edilirken ASLA `bool(x)` kullanma, HER ZAMAN `x == True` (ya da
  `x is True`) kullan.**
- **Eksik/None/NaN sayısal değer için `"—"` (tire) işareti YASAK (v2.0.7.76,
  Bahri'nin talebi — emoji/widget yasağıyla aynı ruhta).** `fmt_tr()` ve
  `fmt_tr_isaretli()` artık None/NaN için boş metin (`""`) döndürür, tire
  değil. Yeni bir yerde eksik veri göstermek gerekirse bu iki fonksiyonu
  kullan, elle `"—"` yazma.
- **Liste ile Detay arasında DD/hacim cezası farkı (17 Temmuz 2026, Bahri'nin
  bulgusu, GZL/TEFAS örneği — 60,0 liste / 53,0 Detay).** `enrich()` (Detay
  sayfası) skoru `base_score + hacim_trendi_duzeltmesi + Max_Drawdown_cezasi`
  olarak hesaplar; liste tablosu (`df_cat["Optima_Skor"]`) SADECE
  `optima_score(RSI,Ret1M,Vol)` — DD/hacim düzeltmesi hiç yok. BIST'te sorun
  yok çünkü worker.py TAM skoru (DD/hacim dahil) geceden hesaplayıp CSV'ye
  yazıyor, liste de onu kullanıyor (`df_cat["Optima_Skor"].notna().any()`
  kontrolü). **TEFAS/Kripto/Döviz/Maden'de worker.py bu ön-hesaplamayı hiç
  yapmıyor** — liste bu yüzden basit formüle düşüyor.
  **TEFAS'ın özel zorluğu:** günlük NAV geçmişi worker.py'de YOK, sadece
  kullanıcı bir fonun detayına tıklayınca `app.py`'nin `_load_tefas_cache`/
  `_save_tefas_cache` (pytefas `Crawler.fetch()`, fon başına TEK istek,
  toplu uç nokta yok) ile TEMBEL (lazy) doldurulan bir önbellek var — 1340
  fonun tamamı için değil. **KARAR (Bahri, 17 Temmuz): kalıcı çözüm
  isteniyor — worker.py BIST gibi TAM skoru geceden hesaplayacak şekilde
  genişletilecek, ama önce 1340 fonu toplu çekmenin ne kadar sürdüğü
  fizibilite testiyle doğrulanacak.** Test betiği hazırlandı
  (`test_tefas_bulk_fizibilite.py`, sıralı vs paralel/ThreadPoolExecutor
  zamanlama karşılaştırması) — Bahri'nin proje klasöründe çalıştırıp
  sonucu iletmesi bekleniyor. **Sonuç gelmeden worker.py'yi TEFAS için
  genişletme kararını uygulamaya kalkma — süre kabul edilemez çıkarsa
  (örn. GitHub Actions'ın pratik limitlerini aşarsa) farklı bir yaklaşım
  (örn. sadece portföydeki/en çok görüntülenen fonlar için önceden
  hesaplama, BIST'in `refresh_bist_selective` mantığına benzer) gerekebilir.**
  Kripto/Döviz/Maden için ise durum muhtemelen çok daha kolay: PROJE_NOTLARI
  §1'de belirtildiği gibi bu kategorilerin RSI/Ret1M'i ZATEN gerçek günlük
  geçmişten (aynı API çağrısından, atomik) geliyor — yani DD hesaplaması
  için EK bir ağ isteği gerekmeyebilir, sadece mevcut veriden bir hesaplama
  eklemek yeterli olabilir. Bu, TEFAS'tan bağımsız, daha ucuz bir kazanım
  olabilir — ayrıca değerlendirilebilir.
- **TEFAS Ret6M/Ret1Y için sahte %0,00 (v2.0.7.78, 17 Temmuz 2026, Bahri'nin
  bulgusu, DTH örneği).** "TEFAS Getiri ve Risk Analizi" panelinde 6 Ay ve
  1 Yıl getirisi "%0,00" gösteriyordu ama fonun mum grafiği o dönemde
  açıkça yükselmişti — `tefas_client.py`'nin `_pct()` fonksiyonu Excel'de
  boş/NaN olan hücreleri (fon o kadar eski değilse TEFAS'ın kendi 6 Ay/
  1 Yıl sütunu boş kalıyor) sessizce `0.0`'a çeviriyordu, "veri yok" ile
  "gerçekten %0 getiri" ayırt edilemiyordu — TAM OLARAK `_gecmis_veri_yok`
  ile çözülen sorunun aynısı, farklı bir veri yolunda. **Kapsam küçük değil:
  1348 fonun 201'i (1 Yıl) ve 61'i (6 Ay) etkileniyordu.** Daha kötüsü, bu
  sahte sıfır `_rsi_from_rets(ret1m,ret3m,ret1y)` ağırlıklı ortalamasına da
  giriyordu (ret1y ağırlığı %20) — RSI'yi yapay olarak aşağı çekiyordu (DTH:
  59,0 yerine gerçek değer 61,2). **Düzeltme:** `_pct()` artık `None` döner
  (0.0 değil); `_rsi_from_rets()` eksik dönemi ağırlıklı ortalamadan
  ÇIKARIR, kalan dönemlerin ağırlığını yeniden ölçekler (hiçbiri yoksa nötr
  50.0); `worker.py`'nin Kaydet bölümündeki Ret3M/Ret1Y için eski
  `.fillna(0.0)` kaldırıldı (gerçek NaN korunuyor, `fmt_tr` bunu otomatik
  boş gösteriyor). **Ret1M dokunulmadı** (optima_score()'un doğrudan
  girdisi olduğu için hâlâ 0.0'a düşüyor — ama bu sadece ~1348 fonun 12'sini
  etkiliyor, çok nadir). **Henüz dokunulmayan, düşük öncelikli bir yer var:**
  worker.py'nin "Minimal fallback" yolu (tefas_client.py hiç import
  edilemezse devreye giren yedek) hâlâ eski (sahte-sıfır) formülü kullanıyor
  — bu yol pratikte neredeyse hiç çalışmadığı için düzeltilmedi, ama ileride
  akla gelirse burası da not düşülsün.
- **"Skor Bileşimi" paneli üçe bölünmüş, birbirinden habersiz hesap
  (v2.0.7.79, 17 Temmuz 2026, Bahri'nin bulgusu, YAYLA örneği — Teknik
  Skor "40,7 / 70" gösteriyordu ama gerçek max 75; Temel Skor Master
  Skor'u hiç etkilemeyen ayrı bir formüldü).** Üç kopukluk: (1) ekrandaki
  "Teknik Skor" aslında `enrich()`'in `_d['score']`'u — 0-100'e normalize
  edilmiş (TEFAS/Kripto/Döviz/Maden'i BIST ile karşılaştırmak için
  tasarlanmış AYRI bir mantık) + DD/hacim düzeltmesi dahil bir değerdi,
  ama "/70" diye etiketleniyordu; gerçekte `optima_score()`'un kendi RSI+
  Momentum+Vol ağırlıkları toplamı 75'tir (70 değil). (2) Ekrandaki "Temel
  Skor", Master Skor'u belirleyen `optima_score()`'un İÇ temel-analiz
  hesabından TAMAMEN FARKLI, `kap_client.py`'deki `score_from_fundamentals()`
  (farklı F/K/PD/DD/Temettü eşikleri + net kâr bonusu, max 30) kullanıyordu
  — ekranda görünen sayı Master Skor'a hiç girmiyordu. (3) "Master Skor"
  genelde bu ikisinin toplamı değil, worker.py'nin geceden hesaplayıp
  CSV'ye yazdığı bağımsız bir değerdi. **Düzeltme:** `optima_score()`
  `_teknik_alt_skor()` (0-75) ve `_temel_alt_skor()` (0-25) yardımcılarına
  bölündü — dışarıya dönen davranış AYNI kaldı, ama artık "Skor Bileşimi"
  paneli (3 yerde: Ana Sayfa/Kategori Detay/Portföyüm) BU İKİ fonksiyonu
  DOĞRUDAN çağırıyor, `kap_client.score_from_fundamentals()` artık
  KULLANILMIYOR (kaldırılmadı, sadece çağrılmıyor). Etiketler "/75" ve
  "/25" olarak düzeltildi. **Bilinmesi gereken kalıntı:** Master Skor BIST
  için hâlâ genelde worker.py'nin ÖNCEDEN HESAPLANMIŞ (gece, DD/hacim
  düzeltmesi dahil) değeri olduğundan, Teknik+Temel toplamı Master Skor'u
  HÂLÂ tam tutturamayabilir (farklı an'ın verisi + düzeltme payı bu
  panelde ayrıca gösterilmiyor) — ama artık her iki alt bileşen kendi
  içinde doğru ve TEK kaynaktan, önceki gibi üç bağımsız/çelişkili sayı
  değil.
- **Türkçe sayı formatı HER YERDE zorunlu** (`fmt_tr()`/`fmt_tr_isaretli()`
  kullan, asla ham `f"{x:.2f}"` veya `f"{x:,.2f}"` yazma). Bu kural bir kez
  ihlal edilip ~50 yerde toplu düzeltme gerekmişti (v2.0.7.60) — yeni bir
  sayısal değer eklerken baştan `fmt_tr` kullan.
- **`kripto_parite_map.json` (BIST ile çakışan kriptoların gerçek BtcTurk
  kodu — CSKY→SKY gibi) worker.py tarafından her koşuda üretilir ama
  18 Temmuz 2026'ya kadar HİÇBİR ZAMAN git'e commit edilmiyordu**
  (GitHub Actions workflow'u sadece `optimized_universe.csv` ekliyordu).
  Sonuç: deploy edilen uygulama hep eski `{"CLINK":"LINKTRY"}` yedeğini
  kullanıyordu — CLINK dışındaki HER çakışma-yeniden-adlandırılmış kripto
  (örn. CSKY) için Detay sayfası var-olmayan bir parite ("CSKYTRY")
  sorguluyor, "geçmiş fiyat verisi yüklenemedi" veriyordu; worker.py'nin
  KENDİ atomik hesaplaması doğru eşlemeyi bildiği için liste skoru
  (80,0 gibi) GERÇEK ve doğruydu — bu yüzden liste/detay arasında bir
  celiski degil, "veri var ama detay sayfasi yanlis paritede ariyor"
  durumu vardı. **Düzeltme (v2.0.7.82):** hem `.github/workflows/
  update_data.yml` hem `guncelle_ve_push.bat`'a `git add -f
  kripto_parite_map.json` eklendi. **Genel ders: worker.py'nin ürettiği
  YARDIMCI dosyalar (CSV dışında) commit listesine bilerek eklenmezse,
  deploy edilen uygulama onları asla göremez — yeni bir yardımcı dosya
  eklerken bunu unutma.**
- **`yf.Ticker(...).info` yfinance'in EN YAVAŞ çağrılarından biri (genelde
  1-5+ saniye/hisse) ve ÖNBELLEKSİZ kullanılırsa (Streamlit her widget
  etkileşiminde TÜM sayfayı yeniden çalıştırdığından) HER checkbox
  tıklamasında/sayfa etkileşiminde TEKRAR TEKRAR çağrılır.** Bu,
  `dividend_engine.get_bist_dividend()`'de bulundu (v2.0.7.84, Bahri'nin
  bulgusu — Ana Sayfa Bütçe Optimizasyonu tablosunun açılması VE herhangi
  bir checkbox tıklaması yavaştı). **Önbelleklerken dikkat:** fiyat gibi
  sık değişen bir parametreyi `@st.cache_data`'nın önbellek anahtarına
  KATMA — her fiyat güncellemesinde önbellek isabetsiz olur, yavaş çağrı
  yine tekrarlanır. Pahalı/nadiren-değişen kısmı (örn. temettü oranı,
  sadece ticker'a göre) AYRI bir önbellekli fonksiyona taşı, fiyata bağlı
  ucuz hesabı dışarıda, önbellek dışında yap. Yeni bir yfinance `.info`
  çağrısı eklerken bu deseni tekrarlama — `kap_client.
  fetch_kap_fundamentals()` doğru yapılmış bir örnek (sadece ticker'a
  göre, 24 saat önbellekli).
- **GitHub Actions workflow'ları git push yapıyorsa, commit sonrası/push
  öncesi MUTLAKA `git pull` (merge) olmalı.** Aksi halde, workflow uzun
  sürdüğü (worker.py dakikalarca çalışabilir) VEYA Bahri workflow ile AYNI
  anda elle push yaptığı sürece, uzak dal ilerlemiş olabilir - push
  "non-fast-forward" ile reddedilir ve TÜM iş (o çalışmanın ürettiği HER
  ŞEY dahil) başarısız sayılıp atılır (v2.0.7.85, 18 Temmuz 2026, Bahri'nin
  bulgusu — Actions #70 çalışması, `kripto_parite_map.json` üretilmiş ama
  push edilemediği için kaybolmuştu). Bahri'nin kendi manuel push akışı
  zaten bu deseni kullanıyor (commit → pull → push) - workflow'lar da
  aynı deseni izlemeli.
- **Streamlit yeni bir elemanı (st.empty() dahil) eskisinin YERİNE
  koymaz — script bitene kadar önceki çalışmadan kalan elemanlar sayfada
  kalmaya devam eder.** v2.0.7.87'de bu yanlış varsayılıp "auth gate
  sonrası hemen st.empty() ile 'Yükleniyor...' yazarsam eski giriş formu
  kaybolur" denendi — olmadı, yeni mesaj eskinin ÜSTÜNE/YANINA eklendi,
  görüntü DAHA karışık hale geldi (Bahri'nin bulgusu, 18 Temmuz 2026,
  v2.0.7.88'de geri alındı). Streamlit'in element-degistirme/temizleme
  davranışı, ancak script TAMAMEN bittiğinde (ya da o pozisyona TEKRAR
  bir eleman yazıldığında) devreye girer - "erken bir yer tutucu
  koyarsam sonraki (yavaş) icerik gelene kadar eski goruntu gizlenir"
  varsayımı YANLIŞ. Bu tür bir "yükleniyor" ekranı gerekiyorsa, gerçek
  çözüm ya (a) yavaş işlemi gerçekten hızlandırmak ya da (b) TÜM sayfa
  içeriğini TEK bir `st.empty().container()` içine alıp o container'ı
  script başında bir kez temizlemek gibi çok daha kapsamlı bir yeniden
  yapılandırma - küçük/nokta atışı bir yama yeterli değil.
- **Dış API çağrısı (yfinance/.info, borsapy/canlidoviz/BtcTurk .history()
  vb.) EKLERKEN HER ZAMAN zaman aşımı koruması ekle — varsayılan olarak
  bu kütüphanelerin çoğu SINIRSIZ bekler.** 19 Temmuz 2026'da aynı gün
  içinde İKİ AYRI yerde bu tuzağa düşüldü (dividend_engine.py'nin
  yfinance çağrısı - v2.0.7.90; live_data.py'nin borsapy çağrıları -
  v2.0.7.91) — dış servis yavaş/rate-limit'e takılırsa TEK bir çağrı
  bile tüm sayfayı dakikalarca (bazen görünüşte süresiz) kilitleyebiliyor.
  Kalıcı desen: `_borsapy_zaman_asimili()` (live_data.py) tarzı bir
  `ThreadPoolExecutor(max_workers=1).submit(fn).result(timeout=N)`
  sarmalayıcısı kullan, zaman aşımında sessizce None/varsayılan dön -
  ASLA çıplak bir dış API çağrısı ekleme.
- **Emoji/dekoratif sembol YASAK** — ne kod/UI'da ne chat yanıtlarında.
- **Her zaman GitHub'dan taze klon ile başla, yerel sandbox'a güvenme.**
  Bir oturumda yerel çalışma klasöründe GERÇEK GITHUB'A HİÇ GÖNDERİLMEMİŞ
  bir düzeltme bulunmuştu (v2.0.7.68, get_signal fonksiyonu) — muhtemelen
  önceki bir oturumda yapılıp unutulmuş. `git log -S"arama_metni"` ile bir
  değişikliğin gerçekten commit edilip edilmediğini HER ZAMAN doğrula.

---

## 5. BEKLEYEN İŞLER / TODO (her oturum başında kontrol et)

- **[UYGULANDI] v2.0.7.130 (10 Ağustos 2026, Bahri'nin bulgusu): Getiri
  Kıyaslaması grafiğindeki "Portföyünüz: +1,95%" ile Portföy Varlıkları
  Tablosu'ndaki "+1,67%" arasındaki tutarsızlık düzeltildi.** Kök neden
  (Ana Sayfa'daki v2.0.7.105 "canlı vs dondurulmuş skor" sorunuyla AYNI
  sınıf): ana tablodaki "Güncel" fiyat `_ld_portfolio_prices()` ile CANLI
  çekiliyor, ama grafikteki "bugün" noktası `get_hist()`'in son
  değerinden geliyordu - TEFAS için bu pytefas/önbellekli GEÇMİŞ NAV'a
  dayanıyor (TEFAS NAV'ları günde bir kez, genelde gün sonunda
  yayınlanır, bir gün gecikebilir). İki ayrı veri hattı, aynı gün için
  farklı sayı veriyordu. **Düzeltme:** `_kiyaslama_gunluk_serileri()`'nde
  her ticker'ın günlük serisinin SON günü artık ana tabloyla BİREBİR AYNI
  canlı fiyat kaynağıyla (`_ld_portfolio_prices`, Son_Fiyat yedekli)
  eziliyor - geçmiş günler `get_hist()`'ten kalıyor (zaten doğru), sadece
  "bugün" artık iki gösterge arasında tutarlı. **DOĞRULANMADI** (canlı
  test gerekiyor) - push sonrası iki sayının artık eşleştiğinin kontrol
  edilmesi gerekir.

- **[UYGULANDI] v2.0.7.129 (10 Ağustos 2026, Bahri'nin talebi — "elle veri
  girişi asla kabul edilemez" itirazı üzerine ikinci revizyon).**
  (1) **Mevduat/Tahvil/Repo artık ÜÇÜ DE TCMB EVDS'ten tam otomatik**
  — araştırma sonucu bulunan seriler: `TP.MT210AGS.TRY.MT01` (mevduat,
  aylık), `TP.AOFOBAP` (BIST gecelik repo ağırlıklı ort. faizi, günlük),
  `TP.BISTTLREF.ORAN` (BIST TLREF gecelik referans faizi, günlük - EVDS'de
  tek bir "gösterge tahvil getirisi" serisi yok, DİBS verisi 2500+ tekil
  ISIN bazlı, TLREF piyasada yaygın kullanılan gerçek bir referans oranı
  olduğu için en yakın anlamlı otomatik alternatif olarak seçildi).
  `_evds_mevduat_faizi_cek()` → genel `_evds_seri_cek(seri_kodu)` +
  `_evds_referans_oranlari_cek()` (6 saat cache, 3'ü birden). **"Referans
  Oranları" manuel giriş expander'ı TAMAMEN kaldırıldı** —
  `portfolio_benchmark_rates` tablosu/`get_benchmark_rates`/
  `set_benchmark_rate` artık bu özellik tarafından kullanılmıyor (DB'de
  kalabilir, ileride başka bir amaçla kullanılabilir, silinmedi).
  (2) Grafik çizgi renkleri daha canlı/doygun (soft tonlar değil) +
  kalınlaştırıldı (Portföy 4px, diğerleri 2.75px — önceki 3px/1.75px'ten
  artırıldı). (3) **Açık soru (henüz uygulanmadı):** Bahri'ye pozisyon
  bazlı (her ticker ayrı çizgi) ikinci bir grafik eklenip eklenmeyeceği
  soruldu — 6 pozisyon + 6 karşılaştırma aracı birleşince 13 çizgi çok
  karışık olur, ayrı bir grafik önerildi, cevap bekleniyor.

- **[UYGULANDI, GÖRSEL TEST GEREKİYOR] v2.0.7.128 (10 Ağustos 2026,
  Bahri'nin talebi — Getiri Kıyaslaması'nın köklü yeniden tasarımı, 5
  madde).** (1) Bölüm artık Portföy Varlıkları Tablosu'nun HEMEN
  ALTINDA (Sermaye/Nakit ve Gerçekleşmiş K/Z'den ÖNCE). (2) EVDS mevduat
  oranı artık buton olmadan, sayfa açılınca OTOMATİK çekiliyor (başarısız
  olursa sessizce son kaydedilen/elle girilen değere düşer, hata caption
  olarak gösterilir). (3)(4) Eski nokta-karşılaştırma tablosu (sadece
  alış günü vs bugün) tamamen kaldırıldı — yerine tek bir **Plotly çizgi
  grafiği**: yatay eksen zaman (portföydeki EN ERKEN alışın tarihinden
  bugüne), her araç (Portföyünüz + BIST100 + Altın + Dolar/TL + Mevduat +
  Tahvil + Repo) için ayrı renkli GÜNLÜK kümülatif getiri çizgisi. (5)
  `template="plotly_white"`, temiz gridline'lar, üstte yatay lejant,
  hover'da birleşik tooltip — profesyonel görünüm hedeflendi.
  **Mimari:** yeni `_kiyaslama_gunluk_serileri()` fonksiyonu, portföyün
  KENDİ günlük değer/maliyet serisini oluştururken TSO'nun ZATEN sahip
  olduğu birleşik `get_hist()` altyapısını (TEFAS/BIST/DÖVİZ/MADEN/
  KRİPTO hepsini kapsar, detay sayfalarındaki AYNI fonksiyon) kullanıyor
  — ayrı bir veri yolu icat edilmedi. Altın karşılaştırması da bu arada
  düzeldi: eski kod sentetik `GC=F×USDTRY` çeviriyordu (MADEN için
  "hiçbir sentetik USD->TL çevrimi denenmez" kuralına aykırıydı) — artık
  `get_hist(..., "MADEN", ...)` ile gerçek TL verisi kullanılıyor.
  **DOĞRULANMADI:** çoklu pozisyon + çoklu ticker'lı gerçek bir portföyde
  grafiğin doğru render olduğu görsel olarak bu oturumda test edilemedi
  (canlıya erişim yok) — ilk kullanımda kontrol edilmesi gerekir.

- **[UYGULANDI, TEKRAR DENEME BEKLİYOR] v2.0.7.127 (10 Ağustos 2026,
  Bahri'nin bulgusu — "Mevduatı TCMB EVDS'ten Çek" ilk denemede genel
  bir "çekilemedi" mesajı verdi, gerçek sebep görünmüyordu).** İki
  düzeltme: (1) `_evds_mevduat_faizi_cek()` artık `(değer, hata_detayı)`
  tuple'ı dönüyor — başarısız olursa hangi aşamada (anahtar tanımsız /
  paket import hatası / API boş sonuç / başka bir istisna + tam mesajı)
  başarısız olduğu ekranda görünüyor, bir daha "genel" mesajla
  karşılaşılmayacak. (2) **Daha kritik bir hata bulundu:** fonksiyon
  `@st.cache_data(ttl=86400)` ile işaretliydi — yani bir kere
  "başarısız" sonucu önbelleğe düşünce, `EVDS_API_KEY` sonradan doğru
  eklense bile aynı gün tekrar "Çek" butonuna basmak hâlâ o ESKİ
  başarısız sonucu gösterip duracaktı (cache, fonksiyonun hiç argümanı
  olmadığı için tüm çağrılarda aynı anahtarı kullanıyordu). Cache
  kaldırıldı — buton zaten sadece tıklanınca çalışıyor, otomatik/sık
  çağrılmıyor, önbelleğe gerek yoktu. **Sıradaki adım:** Bahri'nin
  Streamlit Cloud secrets'a `EVDS_API_KEY`'i eklediğini doğrulaması ve
  butona tekrar basması — bu sefer gerçek hata (varsa) görünecek.

- **[UYGULANDI] v2.0.7.126 (10 Ağustos 2026, Bahri'nin talebi): Getiri
  Kıyaslaması'ndaki Mevduat referans oranı artık TCMB EVDS'den TEK
  TUŞLA otomatik çekilebiliyor.** Önceki oturumda hesap.com'un mevduat
  faizi grafiğinin JS ile sonradan yüklendiği (güvenilir şekilde
  scrape edilemediği) tespit edilmişti; kaynağının zaten TCMB olduğu da
  görülmüştü. Bahri kendi EVDS API anahtarını verince doğru seri
  bulundu: **`TP.MT210AGS.TRY.MT01`** ("1 Aya Kadar Vadeli TL Mevduat,
  Stok, %" — hesap.com'un gösterdiğiyle AYNI seri, resmi kaynaktan,
  aylık güncelleniyor). `fatihmete/evds` pip paketi kullanıldı (EVDS3'ün
  belgesiz gerçek taban adresini - `evds3.tcmb.gov.tr/igmevdsms-dis/` -
  ve auth header'ını doğru yönetiyor, kendi HTTP istemcimizi
  yazmaktan daha güvenilir).
  **GÜVENLİK (KRİTİK):** API anahtarı KODA YAZILMADI — bu repo public,
  commit edilen bir anahtar herkese açık olurdu (GitGuardian/SMTP
  sızıntısı hâlâ hatırlanıyor). Anahtar `EVDS_API_KEY` ortam
  değişkeninden (yoksa Streamlit secrets'tan) okunuyor — Supabase
  bağlantısıyla AYNI desen. **Bahri'nin yapması gereken:** gerçek anahtar
  değerini Streamlit Cloud'un "Secrets" ayarına `EVDS_API_KEY = "..."`
  olarak eklemesi (worker.py/GitHub Actions bu özelliği kullanmıyor,
  sadece canlı app.py'de "Mevduatı TCMB EVDS'ten Çek" butonuna basılınca
  çalışıyor — o yüzden GitHub Secrets'a değil, Streamlit Cloud
  secrets'ına eklenmeli). Tahvil/Repo için hâlâ güvenilir/ücretsiz bir
  API yok, elle girilmeye devam ediyor.

- **[UYGULANDI, GERÇEK VERİYLE TEST EDİLMEDİ] v2.0.7.125 (8 Ağustos
  2026, Bahri'nin talebi — büyük özellik): "Getiri Kıyaslaması" —
  Portföyüm sayfasına, portföyün gerçek getirisini (her pozisyonun
  KENDİ alış tarihinden bugüne, ağırlıklı) BIST100/Altın/Dolar/Mevduat/
  Tahvil/Repo ile kıyaslayan bir "Karşılaştır" butonu + sonuç tablosu
  eklendi.**
  - **BIST100/Altın/Dolar:** GERÇEK geçmiş piyasa verisi — yfinance
    üzerinden (`XU100.IS`, `GC=F`+`TRY=X` ons→gram dönüşümüyle altın,
    `TRY=X` dolar). Her pozisyonun kendi alış tarihi için ayrı ayrı
    çekiliyor, `st.cache_data(ttl=3600)` ile önbellekli, 8sn zaman
    aşımı korumalı (aynı desen worker.py/live_data.py).
  - **Mevduat/Tahvil/Repo:** canlı/güvenilir bir API YOK (TCMB "ortalama
    mevduat faizi" diye bir şey yayınlamıyor) — bu 3 oran yeni
    `benchmark_rates` tablosunda MANUEL saklanıyor, Bahri "Referans
    Oranları" bölümünden düzenleyip güncelleyebiliyor. **İlk kurulum
    varsayılan değerleri (7-8 Ağustos 2026'da araştırıldı, gerçek
    kaynaklardan):** Mevduat %38 (en yüksek TL mevduatların ~%46-47
    brüt oranının stopaj sonrası net ortalaması), Tahvil %37,97 (2
    yıllık gösterge tahvil, investing.com), Repo %37 (TCMB politika
    faizi, 23 Temmuz 2026 kararı). Bahri bu oranları zaman zaman
    güncellemezse zamanla eskir — arayüzde bu uyarı gösteriliyor.
  - Hesap basit faizle: `oran × gün_sayısı / 365`, her pozisyonun
    maliyetiyle ağırlıklı toplanıyor.
  - **Bu oturumda gerçek veriyle (canlıda buton tıklanarak) test
    EDİLMEDİ** — sadece kod yazıldı ve derleme/sözdizimi doğrulandı.
    İlk kullanımda: yfinance çağrılarının (özellikle `XU100.IS` ve
    `TRY=X`) beklendiği gibi geriye dönük veri döndürüp döndürmediğini,
    ve tabloların doğru göründüğünü kontrol et.

- **[KARAR - TEKRAR SORULMASIN] Değerli Madenler'de 9 sikke/gram altın
  türünün (Gram Has Altın, 14/18 Ayar, Bilezik22, İkibuçuk, Beşli,
  Gremse, Reşat, Hamit Altın) RSI/1A Getiri/Optima Skor boş/0 kalması
  (5 Ağustos 2026'da Bahri'ye tekrar teyit edildi).** Bu bir bug DEĞİL —
  v2.0.7.43'te zaten bilinçli alınmış bir karar: bu 9 ürünün hiçbirinin
  yfinance karşılığı yok (Türkiye'ye özgü fiziki ürünler), Bigpara/
  Truncgil'den sadece ANLIK fiyat geliyor, hiçbir kaynakta geçmiş fiyat
  serisi yok. RSI/Ret1M hesaplamak için geçmiş veri şart. Bahri'ye
  "Gram Altın'ın (ALTIN_TRY) RSI/Getiri'sini yaklaşık bir vekil olarak
  kullanabiliriz" önerisi sunuldu, **açıkça reddetti**: "sahte veri
  istemiyorum, boş kalsın." Bu tercih kalıcıdır — ileride bu konu tekrar
  gündeme gelirse (yeni bir oturumda fark edilip "bug" sanılabilir)
  kod DEĞİŞTİRİLMEDEN önce bu maddeye bakılsın.

- **[UYGULANDI] v2.0.7.124 (5 Ağustos 2026, gece 03:01 TRT çalışması —
  gerçek loglar görülebildi, iki ayrı iyileştirme).** (1) **MADEN kök
  neden bulundu ve düzeltildi:** `"TESHIS (MADEN:GUMUS_TRY):
  DataNotAvailableError: Unsupported asset: gumus"` — borsapy'nin resmi
  API'sinde değerli maden kodları `"gram-gumus"`/`"gram-platin"`
  (`"gram-altin"` ile aynı desende), ama `firsat_radari.py`'nin kendi
  `_MADEN_BP` haritasında sadece ALTIN doğru yazılmıştı, GÜMÜŞ/PLATİN'de
  "gram-" öneki hep eksikti (muhtemelen kopyala-yapıştır hatası —
  `live_data.py`'deki `_MADEN_TO_BP`'de bu 3 kod zaten doğruydu). Bu,
  MADEN kapsamının hep 1/3'te kalmasının nedeniydi; artık düzeltildi.
  (2) **Supabase bağlantı retry:** aynı gece bir çalışmada geçici bir
  Supabase bağlantı zaman aşımı TÜM işi başarısız göstermişti (sonraki
  çalışmalar hemen düzelmişti — tek seferlik bir altyapı kesintisiydi).
  Artık bağlantı 3 kez (aralarda 5sn, 10sn bekleyerek) deneniyor, sadece
  3. deneme de başarısız olursa iş başarısız sayılıyor — anlık kesintiler
  artık bütün 20 dakikalık döngüyü atlatmayacak.

- **[UYGULANDI, İZLEMEDE] v2.0.7.123 (4 Ağustos 2026 — "All jobs have
  failed", 3dk7sn, 14:34 TRT/BIST seansı açıkken).** E-postadaki commit
  (`d6eb5e6`) benim aynı gün attığım v2.0.7.122 idi ama o SADECE
  `app.py`'yi (Portföyüm) değiştiriyordu — `firsat_radari.py`'ye hiç
  dokunmamıştı, yani alakasız bir çakışma, asıl arıza başka yerde.
  **Bulunan gerçek boşluk:** v2.0.7.103/104'te DOVİZ/MADEN/KRİPTO, BIST,
  TEFAS taramaları kategori bazlı try/except'e alınmıştı — ama
  `main()`'in SONUNDAKİ 5 adım (`_onceki_skorlari_al`,
  `_radar_tetikleyicileri`, `_upsert`, `_dedupe_ve_kaydet`,
  `_radar_maili_gonder`) HİÇ korunmamıştı. Bunlardan biri (en olası
  aday: e-posta gönderimi/SMTP) patlarsa, veri toplama tamamen başarılı
  olsa bile TÜM iş çöküyordu. **Düzeltme:** bu 5 adımın her biri artık
  kendi try/except'i içinde — özellikle Supabase `_upsert` (en önemli
  adım, canlı uygulamanın veriyi görmesini sağlar) artık e-posta
  gönderimi patlasa bile tamamlanmış olacak. **Sıradaki adım:** bu tür
  bir arıza tekrarlanırsa artık log'da HANGİ adımın patladığı (tür +
  mesaj) görünecek — kesin teşhis o zaman netleşir.

- **[UYGULANDI] v2.0.7.122 (31 Temmuz 2026, Bahri'nin talebi): Portföy
  Varlıkları Tablosu'nun alt toplamına Toplam K/Z % eklendi.** Önemli
  tasarım notu: bu, satırlardaki K/Z %'lerin basit toplamı/ortalaması
  DEĞİL — o yanlış olurdu (küçük bir pozisyonun %50 değişimiyle büyük
  bir pozisyonun %1 değişimi eşit ağırlıkta sayılır, gerçek portföy
  getirisini çarpıtır). Doğrusu ve uygulanan: **Toplam K/Z (TL) / Toplam
  Maliyet (TL)** — yani ağırlıklı/gerçek portföy getirisi. Toplam K/Z %
  önceki K/Z% sütunuyla aynı boş slota (weight=1, "KZPCT") yerleştirildi.

- **[GERİ ALINDI] v2.0.7.121 (31 Temmuz 2026, Bahri'nin talebi):
  hizalama denemeleri durduruldu.** v2.0.7.118, 119 ve 120'de sırayla
  3 farklı yaklaşım denendi (oransal flex ağırlığı, sabit piksel
  genişlik, native `st.metric` kutuları) — hiçbiri Bahri'yi tatmin
  etmedi, sonuncusu (metric kutuları) "kayık olandan daha kötü"
  bulundu. **Orijinal (v2.0.7.117 ve öncesi) satır biçimine AYNEN geri
  dönüldü** — sadece gerçekten hatalı olan işaret kontrolü (`>=0`
  sıfırı da pozitif sayıyordu, artık `>0`) kalıcı olarak düzeltilmiş
  halde kaldı, hizalamaya BAŞKA DOKUNULMADI. **Ders/not:** Streamlit'in
  native `st.dataframe` bileşeninin iç piksel/dolgu değerleri dışarı
  açılmıyor — ayrı bir HTML satırını buna hizalamaya çalışmak yapısal
  olarak kırılgan ve bu ortamdan doğrulanamaz; bu konu bir daha
  gündeme gelirse doğrudan sütun hizalamasına dokunmadan önce Bahri'ye
  bu kısıtı hatırlat.

- **[UYGULANDI, MİMARİ DEĞİŞİKLİK] v2.0.7.120 (31 Temmuz 2026, Bahri'nin
  bulgusu — v2.0.7.118/119'daki İKİ hizalama denemesi de başarısız oldu,
  ikincisinde "TL" yazısı "T"ye kırpıldı).** Kök sorun: Streamlit'in
  native `st.dataframe` bileşeni iç piksel/dolgu değerlerini dışarı hiç
  açmıyor — ayrı bir HTML satırını buna görsel olarak hizalamaya çalışmak
  (önce oransal flex ağırlığı, sonra sabit piksel genişlik) yapısal olarak
  kırılgan ve tahmine dayalıydı, doğrulanamıyordu (bu ortamdan canlı
  render'a erişim yok). **Hizalama illüzyonundan TAMAMEN vazgeçildi** —
  "TOPLAM PORTFÖY DEĞERİ" satırı artık tablo sütunlarına hizalanmaya
  çalışmıyor; bunun yerine Streamlit'in kendi native `st.metric`
  kutularıyla (3 kutu: Toplam Portföy Değeri, Toplam K/Z, Varlık Sayısı)
  ayrı, net bir özet olarak gösteriliyor — uygulamanın başka yerinde
  (Ana Sayfa) zaten kullanılan aynı desen. Bu, YAPISAL olarak doğru
  render'ı garanti eder (tahmine dayalı değil, Streamlit'in kendi
  bileşeni). "+0,00 TL" işaret sorunu da bu arada kalıcı olarak çözüldü
  (yeni `_total_kz_pct` hesabıyla birlikte, `_total_kz` önce yuvarlanıp
  sonra kontrol ediliyor).

- **[UYGULANDI, GÖRSEL DOĞRULAMA GEREKİYOR] v2.0.7.119 (31 Temmuz 2026,
  Bahri'nin bulgusu — v2.0.7.118'in iki düzeltmesi de yeterli değildi).**
  (1) "TOPLAM K/Z +0,00 TL" sorunu — v2.0.7.118 sadece tablo SATIRLARINDAKİ
  işaret mantığını (`_fmt_tr_isaretli`) düzeltmişti; alttaki TOPLAM
  satırının KENDİ AYRI işaret hesabı (`_tcs = "+" if _total_kz>=0 else ""`)
  farklı bir kod parçasıydı ve gözden kaçmıştı — `>=0` sıfırı da pozitif
  sayıyordu. `>0` yapıldı (ve `_total_kz` önce yuvarlandı). **DİKKAT:**
  `fmt_tr()` negatif sayılar için KENDİ "-" işaretini zaten ekliyor - bu
  yüzden `_tcs` SADECE "+" için kullanılmalı, negatif için boş bırakılmalı
  (aksi halde "--123,45 TL" gibi çift eksi çıkar) - bu tuzağa düşülmedi
  ama ileride bu satır tekrar düzenlenirse dikkat edilmeli.
  (2) Hizalama — v2.0.7.118'deki ORANSAL flex ağırlığı tahmini (64/82,
  54/68 oranları) yeterli hassasiyette değildi. Artık footer, sütunların
  `column_config`'teki GERÇEK piksel genişlikleriyle BİREBİR aynı SABİT
  piksel genişlikleri kullanıyor (`flex:0 0 Wpx`, oransal değil). **Tek
  kesin bilinmeyen:** Streamlit'in otomatik seçim checkbox sütununun tam
  piksel genişliği `column_config`'te tanımlı değil, ~40px olarak
  TAHMİN edildi — gerçek değer farklıysa hizalama yine küçük bir kayma
  gösterebilir. **Bu oturumda görsel olarak doğrulanamadı** (canlı
  render'a erişim yok) — push sonrası Bahri'nin gözle kontrol etmesi
  gerekiyor; checkbox genişliği tahmini yanlışsa bana kaç piksel kaydığını
  söylemesi yeterli olur, kesin değeri buluruz.

- **[UYGULANDI] v2.0.7.118 (31 Temmuz 2026, Bahri'nin bulgusu — MTG
  örneği): iki küçük görsel/mantık düzeltmesi, Portföy Varlıkları
  Tablosu.** (1) K/Z % sütununda MTG gibi K/Z (TL) tam 0,00 görünen
  ama K/Z %'de "+0,00%" gösterilen satırlar vardı — kök neden: K/Z (TL)
  önceden 2 ondalığa yuvarlanıp saklanıyordu ama K/Z % HİÇ yuvarlanmadan
  (tam kayan nokta hassasiyetiyle) saklanıyordu; işaret kontrolü (`xf>0`)
  yuvarlanmamış mikroskobik bir kalıntıyı (ör. 0,00004) yakalayıp "+"
  basıyordu, ekranda "0,00" görünse de. Artık K/Z % de K/Z gibi 2
  ondalığa önceden yuvarlanıyor. (2) Alt "TOPLAM PORTFÖY DEĞERİ" satırının
  hizalaması v2.0.7.115'teki Miktar/Birim sütun daraltmasından sonra
  güncellenmemişti (footer'ın flex ağırlıkları eski piksel genişlikleriyle
  ayarlanmıştı) — Miktar/Birim ağırlıkları aynı oranla (64/82, 54/68)
  küçültülerek yeniden hizalandı.

- **[UYGULANDI] v2.0.7.117 (31 Temmuz 2026, Bahri'nin bulgusu — HTS
  örneği, v2.0.7.116'nın eklediği doğrulama sayesinde YAKALANDI):
  KESİN KÖK NEDEN bulundu — `portfolio`/`portfolio_sales`/
  `portfolio_fee_settings`/`portfolio_capital_tx` tablolarındaki tüm
  parasal sütunlar `REAL` (Postgres tek hassasiyetli float4, ~6-7
  anlamlı basamak) ile tanımlıydı.** 56,630841 gibi 8 anlamlı basamaklı
  bir değer REAL'de TAM saklanamıyor, en yakın temsil edilebilir değere
  yuvarlanıyor — v2.0.7.116'nın eklediği "yazdıktan sonra doğrula"
  kontrolü tam bu yüzden hata verdi (kaydedilen değer istenenle
  uyuşmuyordu). v2.0.7.115'te Alış/Güncel gösterimi 4→6 ondalığa
  çıkarılınca bu sorun daha görünür hale geldi. **Düzeltme:** tüm bu
  sütunlar `DOUBLE PRECISION`a (8 byte, Python'un native float'ıyla aynı,
  ~15-17 anlamlı basamak) yükseltildi — hem yeni `CREATE TABLE`
  tanımlarında hem de mevcut Supabase tablolarını yükselten `ALTER
  COLUMN ... TYPE DOUBLE PRECISION` migration'larıyla (idempotent,
  `_init_db_once()` sayesinde oturum başına 1 kez çalışır). **Bu, hem
  Düzelt formunu hem de tüm portföy/satış/sermaye verilerinin hassasiyetini
  kalıcı olarak düzeltir** — sadece HTS'in maliyetini değil, düşük
  fiyatlı TEFAS payları/kripto gibi çok ondalıklı her değeri etkiliyordu.

- **[TEŞHİS/SAĞLAMLAŞTIRMA, KESİN DOĞRULANMADI] v2.0.7.116 (31 Temmuz
  2026, Bahri'nin bulgusu — HTS örneği: Düzelt formuyla maliyeti
  56,630800'den 56,630841'e değiştirmeyi denedi, "Düzeltmeyi Kaydet"e
  bastı, tabloda hiçbir şey değişmedi, hiçbir hata da görünmedi).**
  Kodu inceledim, `parse_tr`/SQL parametre sırası doğru görünüyor -
  ama `update_portfolio_item()` (v2.0.7.114'te eklendi) UPDATE'i HİÇ
  try/except'siz çalıştırıyordu VE `rowcount` (kaç satırın etkilendiği)
  hiç kontrol edilmiyordu. Yani `WHERE id=? AND user_id=?` hiçbir
  satırla eşleşmese bile (rowcount=0) fonksiyon sessizce "başarılı"
  dönüyordu - hata da yok, değişiklik de yok. **Kesin kök neden bu
  oturumda doğrulanamadı** (canlı ortama erişim yok). **Uygulanan
  sağlamlaştırma:** artık (1) UPDATE try/except içinde - gerçek bir DB
  hatası artık ekranda görünür, (2) `rowcount==0` ise artık açık bir
  hata mesajı dönüyor ("hiçbir satırı etkilemedi"), (3) yazdıktan hemen
  sonra satır tekrar okunup `avg_cost`'un GERÇEKTEN değişip değişmediği
  doğrulanıyor, uyuşmazsa yine açık hata. **Sıradaki adım:** Bahri aynı
  düzeltmeyi tekrar denesin - bu sefer ya başarılı olacak ya da tam
  olarak NEDEN başarısız olduğunu söyleyen bir hata mesajı görecek.

- **[UYGULANDI] v2.0.7.115 (31 Temmuz 2026, Bahri'nin talebi): Portföy
  Varlıkları Tablosu görsel ince ayarları.** (1) Miktar sütunu artık 2
  ondalık basamak (önceden 4). (2) Alış ve Güncel sütunları artık 6
  ondalık basamak (önceden 4) — küçük birim fiyatlı varlıklarda (ör.
  kripto/TEFAS payları) hassasiyet artsın diye. (3) Miktar sütunu 82px'ten
  64px'e, Birim sütunu 68px'ten 54px'e daraltıldı. Not: bu değişiklik
  sadece salt-okunur TABLOYA uygulandı — Sat/Düzelt formlarındaki giriş
  alanlarının varsayılan ondalık hassasiyeti (4) değiştirilmedi, istenirse
  ayrıca güncellenebilir.

- **[UYGULANDI] v2.0.7.114 (31 Temmuz 2026, Bahri'nin talebi): Portföy
  Varlıkları Tablosu'nda bir satır seçilince "Sil"/"Sat"ın yanına
  üçüncü bir **"Düzelt"** seçeneği eklendi.** Yanlış girilmiş bir
  miktar/maliyet/tarih/birim türünü satmadan veya silmeden düzeltebilme
  ihtiyacı. Yeni `update_portfolio_item()` fonksiyonu (app.py, `add_/
  delete_portfolio_item`'ın hemen yanında) — Miktar, Maliyet, Alış
  Tarihi, Birim Türü güncellenebiliyor. **Ticker/kategori BİLİNÇLİ
  OLARAK değiştirilemez** — farklı bir varlığa dönüştürmek "düzeltme"
  değil ayrı bir işlemdir (gerekirse sil+yeniden ekle). Form, satış
  formuyla aynı görsel desende (`st.container(border=True)`, aynı buton
  yerleşimi).

- **[UYGULANDI] v2.0.7.113 (31 Temmuz 2026, Bahri'nin bulgusu — ILU fon
  örneği: TEFAS fonları "pay" birimiyle işlem görür, sistemde bu isimde
  bir birim seçeneği yoktu).** `_unit_opts` listesine "Pay" eklendi, ve
  `_default_unit_for()`'da TEFAS kategorisinin varsayılan birimi
  "Adet"ten "Pay"a çevrildi (BIST->Lot, MADEN gram bazlı->Gram ile aynı
  desende). Bahri'nin ayrıca belirttiği "ILU'da 1 milyon adetten az
  alınamıyor" bilgisi — bu TEFAS/aracı kurum tarafındaki bir alım-satım
  kısıtı, uygulama gerçek emir vermediği (sadece pozisyon kaydı tuttuğu)
  için bir minimum-miktar doğrulaması EKLENMEDİ; sadece bağlam olarak not
  edildi. İstenirse ileride "bu fon için minimum X pay" gibi bilgilendirici
  bir uyarı eklenebilir.

- **[UYGULANDI] v2.0.7.112 (30 Temmuz 2026, Bahri'nin talebi — büyük
  özellik): "Başlangıç sermaye miktarının, ne kadar zamanda kaça
  geldiğinin, sattığımda ne kâr ettiğimin ve elimde güncel olarak
  finansal varlık veya nakit olarak ne miktarlar olduğunun kayıt altına
  alınması."** Mevcut durumda satış geçmişi (`portfolio_sales`, tarih +
  net K/Z) zaten vardı (bkz. v2.0.7.111), ama **nakit/sermaye kavramı
  HİÇ yoktu** — bir varlık satıldığında para "hiçbir yere gitmiyordu".
  **Tasarım kararları (Bahri'nin onayıyla, iki soru soruldu):**
  1. Nakit bakiyesi **negatife düşebilir**, bilinçli olarak
     SINIRLANMADI — Bahri: "sermaye hayali değil, gerçek durumu
     göstersin", yetersiz nakitte alım engellenmiyor.
  2. Sermaye **tek seferlik sabit bir sayı DEĞİL** — zaman içinde
     mevduat/çekim eklenip çıkarılabilen bir **hareket defteri**
     (`portfolio_sales`'in satış geçmişi tuttuğu mantığın aynısı).

  **Uygulanan mimari:**
  - Yeni tablo: `portfolio_capital_tx` (id, user_id, tx_type
    DEPOSIT/WITHDRAWAL, amount, tx_date, note) — `db.py`'ye eklendi, RLS
    listesine de dahil edildi (Bölüm 0'daki kalıcı kural).
  - `portfolio_ledger.py`: `add_capital_tx`, `delete_capital_tx`,
    `get_capital_tx_history`, `get_net_capital`, `get_cash_balance`.
    Nakit bakiyesi bir SÜTUN olarak SAKLANMIYOR, her seferinde
    türetiliyor: `Nakit = Net Sermaye − (açık pozisyon maliyeti +
    satılmış lot maliyeti) + net satış geliri` — "tek doğru kaynak"
    felsefesi (worker.py/Optima_Skor ile aynı prensip).
  - `app.py`: yeni `_render_sermaye_nakit_ozeti()` fonksiyonu —
    `_render_gerceklesmis_kar_zarar()` ile AYNI desende (bkz. v2.0.7.111),
    hem boş hem dolu portföy durumunda çağrılıyor (sermaye/nakit açık
    pozisyonlara bağlı değil). 5 metrik gösteriyor: Net Yatırılan
    Sermaye, Nakit Bakiye, Güncel Varlık Değeri, Toplam Servet, Toplam
    Getiri (TL+%). Mevduat/çekim ekleme formu + geçmiş tablosu + silme
    de dahil.
  - **Not:** "ne kadar zamanda kaça geldiği" (elde tutma süresi) için
    ayrı bir "geçen gün/ay" kolonu EKLENMEDİ — Portföy Varlıkları
    Tablosu'ndaki "Tarih" (alış tarihi) sütunundan zaten çıkarılabiliyor.
    İstenirse ayrı bir "Elde Tutma Süresi" kolonu sonradan eklenebilir.
  - **Doğrulanmadı:** Bu özellik bu oturumda yazıldı ama Bahri tarafından
    henüz canlıda test edilmedi (mevduat ekleme, nakit hesabı doğruluğu).
    İlk kullanımda bir test mevduatı girip rakamların beklenen şekilde
    çıkıp çıkmadığını doğrulamak faydalı olur.

- **[UYGULANDI, İZLEMEDE] v2.0.7.110 (30 Temmuz 2026, Bahri'nin bulgusu —
  IZMDC/BIGTK örnekleri: BIST evreninin %85'i F/K'siz, %71'i PD/DD'siz,
  %98'i temettü verimsizdi — hepsi NaN, negatif/zararda olduğu için
  değil).** Kök neden `worker.py`'nin `fetch_bist_fundamentals_parallel()`
  fonksiyonu — 772 hisse için yfinance'in `.info` endpoint'ini (Yahoo'nun
  en ağır/hız-sınırına en yatkın endpoint'i) 25 eş zamanlı worker ile ANINDA
  çağırıyordu. **Kesin kök neden (hız sınırı mı, Yahoo'nun küçük BIST
  hisseleri için veri eksikliği mi) bu ortamdan gerçek Yahoo API'sine
  erişim olmadığından doğrulanamadı** — bu yüzden bu bir KESİN düzeltme
  değil, **düşük riskli bir iyileştirme** olarak uygulandı: (1) eş
  zamanlılık 25'ten 8'e düşürüldü, (2) ilk geçişte başarısız olan hisseler
  15sn beklenip 4 worker ile TEKRAR deneniyor, (3) her çağrıya 15sn zaman
  aşımı eklendi (tek bir asılı çağrı artık 45dk'lık iş zaman aşımını riske
  atmıyor), (4) gereksiz bir yan etki de düzeltildi: eskiden bu fonksiyon
  `fetch_kap_fundamentals()` (yfinance+KAP birlikte) çağırıp KAP kısmını
  hiç KULLANMIYORDU (sadece pb/pe/dy okunuyordu, ikisi de yfinance
  kaynaklı) — artık doğrudan `_fetch_yfinance()` çağrılıyor, hem gereksiz
  KAP isteği kalkıyor hem de retry'nin `st.cache_data`'nın 24 saatlik
  önbelleğine takılıp AYNI başarısız sonucu tekrar dönmesi önleniyor.
  **Sıradaki adım:** bir sonraki gece çalışmasının logunda "İlk geçiş: X/772
  ... (Y başarısız)" ve "SONUÇ (tekrar deneme sonrası): Z/772" satırlarını
  karşılaştırıp gerçek iyileşme oranını gör.

- **[ARAŞTIRMA BEKLİYOR, AYRI OTURUM] KAP'tan tam F/K + PD/DD hesaplama
  (Bahri'nin talebi, 30 Temmuz 2026).** Bahri'nin uzun süredir tercihi:
  Temel Skor'u belirleyen F/K, PD/DD, Temettü Verimi'nin yfinance yerine
  KAP'tan (`KAP_BIST.xlsx` zaten repoda, `kap_client.py`'nin
  `KAP_SLUG_MAP`'i buradan geliyor — bkz. Bölüm 2) hesaplanması. Şu an
  sadece EK bilanço kalemleri (Dönen/Duran Varlık, Net Kâr, Özkaynak vb.)
  KAP'tan çekiliyor, görüntüleme amaçlı — asıl 3 rasyo hâlâ yfinance
  kaynaklı (`kap_client.py`'nin kendi docstring'i: "yfinance (birincil) +
  KAP (ikincil)"). Bu oturumda BIGTK'nin gerçek KAP sayfası canlı
  incelendi: Net Kâr ve Özkaynak var, ama **hisse sayısı YOK** — "Ödenmiş
  Sermaye" tek başına güvenilir değil (2013'ten beri nominal hisse değeri
  şirketten şirkete değişebiliyor, bu yüzden Ödenmiş Sermaye'den hisse
  sayısı çıkarmak yanlış sonuç verebilir). F/K=Fiyat/(NetKâr/HisseSayısı)
  ve PD/DD=Fiyat/(Özkaynak/HisseSayısı) hesaplamak için güvenilir bir hisse
  sayısı kaynağı (MKK? BIST'in kendi sitesi? KAP'ın başka bir sekmesi?)
  bulunmalı — bu araştırma AYRI bir oturumda ele alınacak, bu oturumda
  yapılmadı.

- **[UYGULANDI] v2.0.7.109 (30 Temmuz 2026, Bahri'nin talebi — BULGS
  örneği).** v2.0.7.108'de tek bir renk (skorun işaretine göre) hem
  hacim yazısına hem skor rakamına uygulanmıştı. Bahri: "Hacim ARTIYOR
  yazısı yeşil olmalı (ham yön), skor kendi işaretiyle (-3 ise kırmızı)
  ayrı boyansın" — haklı, ikisi farklı şeyi anlatıyor (biri ham hacim
  yönü, biri o yönün BU TRENDDEKİ etkisi). **Uygulandı:** artık İKİ AYRI
  renk değişkeni — `_vol_clr` (hacim yazısı, yön bazlı: ARTIYOR=yeşil/
  AZALIYOR=kırmızı, v2.0.7.108 öncesi orijinal haline döndü) ve `_adj_clr`
  (skor rakamı, işaret bazlı: pozitif=yeşil/negatif=kırmızı, v2.0.7.108'de
  eklenen mantık). Örn. BULGS (DÜŞÜŞ + hacim ARTIYOR = panik satış onayı,
  -3 skor): şimdi "ARTIYOR" yeşil, "(-3 skor)" kırmızı — ikisi de kendi
  anlamıyla tutarlı.

- **[UYGULANDI] v2.0.7.108 (30 Temmuz 2026, Bahri'nin bulgusu — AKSEN
  örneği: "Hacim: AZALIYOR (+2 skor)" kırmızı yazıyla gösteriliyordu,
  ama skor +2 pozitifti — neden kırmızı?).** Kök neden: rozetin rengi
  HAM hacim yönüne göre belirleniyordu (`ARTIYOR`→yeşil, `AZALIYOR`→
  kırmızı), skorun işaretine göre DEĞİL. Ama skor mantığı (`app.py`
  ~satır 1196-1203) şöyle: DÜŞÜŞ trendinde azalan hacim aslında OLUMLU
  bir işaret (+2, "düşüş bitiyor olabilir" — satıcılar tükeniyor), ve
  DÜŞÜŞ trendinde artan hacim OLUMSUZ (-3, "panik satış onayı"). Yani 4
  kombinasyondan 2'sinde (DÜŞÜŞ+ARTIYOR ve DÜŞÜŞ+AZALIYOR) renk skorun
  işaretiyle ÇELİŞİYORDU. **Düzeltme:** renk artık ham hacim yönüne değil
  `score_adj`'ın işaretine göre: pozitif→yeşil, negatif→kırmızı, sıfır→
  gri (3 blokta da). Skorlama formülünün kendisi DEĞİŞMEDİ, sadece renk
  artık anlamıyla tutarlı.

- **[UYGULANDI] v2.0.7.107 (30 Temmuz 2026, Bahri'nin talebi — ATATP
  örneği).** v2.0.7.105'ten sonra Teknik+Temel toplamı Master Skor ile
  hep tutarlıydı AMA hacim/DD ayarı (-10/-3/+2/+5, Max DD -3/-7) hâlâ
  görünmez bir katman olarak sadece Master Skor'a yansıyordu (Teknik+
  Temel'e değil) — örn. ATATP'de Teknik 43,0 + Temel 17,0 = 60,0 ama
  Master Skor 65,0 (fark = üstteki rozetteki "Hacim: ARTIYOR +5 skor").
  Bahri'nin sorusu üzerine ("hacimin +5 puanı teknik skora eklenmez
  mi?") — haklı, hacim/DD zaten teknik bir gösterge. **Uygulandı:**
  hacim/DD ayarı artık Teknik Skor'un İÇİNE katlanıyor (3 blokta da).
  CSV-precomp yolunda ayar ayrı saklanmadığından `(Master Skor - Teknik
  - Temel)` farkı olarak geri türetiliyor — bu fark matematiksel olarak
  worker.py/radar'ın uyguladığı hacim/DD ayarına birebir eşit (ATATP ile
  doğrulandı: 65-43-17=+5, tutarlı). Artık Teknik+Temel HER ZAMAN Master
  Skor'a tam eşit — hiçbir gizli/açıklanamayan fark kalmadı. Etiket de
  "Teknik Skor (RSI + Momentum + Vol + Hacim/DD)" olarak güncellendi.
  **Küçük kozmetik not:** "/75" tavanı olduğu gibi bırakıldı ama artık
  yumuşak bir referans (hacim/DD dahil olduğundan teorik üst sınır 80,
  alt sınır -17 olabilir) — Bahri isterse bu da ayrıca netleştirilebilir.

- **[UYGULANDI, İZLEMEDE] v2.0.7.106 (30 Temmuz 2026, Bahri'nin bulgusu —
  "sistem çok yavaşladı", reboot'tan BAĞIMSIZ, sürekli bir sorun).**
  Kök neden `live_data.py`'de bulundu: `_fetch_live_kripto()` (uygulamanın
  ana canlı fiyat katmanı, 5 dk cache) ~186 kripto parite için **sıralı**
  (paralel değil) `bp.Crypto(...).current` çağrısı yapıyordu — ve bu
  çağrının altındaki `_safe_current()`'ın birincil yolu (`.current`/
  `.info`/`.fast_info` erişimi) **hiç zaman aşımı korumalı değildi**
  (sadece yedek `history()` yolunda vardı). BtcTurk/borsapy tarafında bir
  yavaşlama olduğunda (bkz. `firsat_radari.py` v2.0.7.103/104'teki AYNI
  aile sorun) her 5 dakikada bir (cache süresi dolunca) sayfayı yükleyen
  kullanıcı, 186 sıralı çağrının potansiyel olarak dakikalarca sürebilen
  toplamını bekliyordu. **Uygulanan düzeltme:** (1) `_safe_current()`'ın
  birincil yolu artık 8sn zaman aşımı korumalı (`_borsapy_zaman_asimili`
  ile). (2) `_fetch_live_kripto()` artık `_fetch_live_bist()` ile aynı
  desende `ThreadPoolExecutor` (20 worker) ile eş zamanlı çalışıyor. (3)
  Tutarlılık için `_fetch_live_fx_maden()`'deki DÖVİZ döngüsü de aynı
  şekilde paralelleştirildi (küçük risk ama aynı aile). **Bilinen, DOKUNULMAMIŞ
  küçük kalıntı:** `get_harem_buy_prices()` içindeki 3 metal için olan
  döngü hâlâ sıralı/korumasız — sadece 3 kalem olduğu için düşük risk,
  kapsam dışı bırakıldı. **Sıradaki adım:** birkaç gün gözlemleyip
  yavaşlığın tekrarlanıp tekrarlanmadığını izle; borsapy/BtcTurk tarafında
  gerçek bir hız sınırı/API sorunu varsa (firsat_radari teşhisiyle
  birleşince bu ihtimal güçleniyor) bu düzeltme etkiyi ORTADAN kaldırmaz
  ama sıralıdan paralele geçtiği için TOPLAM bekleme süresini ciddi
  şekilde azaltır (~186×8sn yerine ~8-16sn tavan).

- **[UYGULANDI] v2.0.7.105 (29 Temmuz 2026, Bahri'nin bulgusu — AKSEN
  örneği: BIST Detay sayfasında "Skor Bileşimi" panelinde Teknik Skor
  54,0/75 + Temel Skor 9,0/25 = 63,0 gösteriyordu ama Master Skor 68,0
  yazıyordu, 5 puanlık açıklanamayan fark).** Kök neden: Teknik/Temel
  CANLI hesaplanıyordu (sayfa açılırken `enrich()`'in anlık RSI/Ret1M/Vol
  + tam o an KAP'tan çekilen PB/PE/DY ile), ama Master Skor
  `optimized_universe.csv`'deki `Optima_Skor` kolonundan geliyordu — bu
  da `worker.py`'nin GECE hesapladığı, hacim/DD ayarı zaten gömülü,
  dondurulmuş bir değer. İki farklı andan/kaynaktan gelen sayılar aynı
  panelde "bunlar toplanır" izlenimiyle yan yana duruyordu.
  Bahri'nin tercihi: Teknik/Temel de CSV'nin dondurulmuş RSI/Ret1M/Vol/
  PB/PE/DY değerlerinden hesaplansın (canlı değil) — böylece CSV'de
  Optima_Skor varken üç sayı da (Teknik, Temel, Master) HER ZAMAN aynı
  anın/kaynağın ürünü olur. **Uygulandı:** yeni `_csv_alan()` yardımcı
  fonksiyonu (app.py, `_temel_alt_skor`'un hemen üstünde) + bu mantığın
  bulunduğu **3 ayrı Detay bloğu** güncellendi (Ana Sayfa, Portföyüm,
  genel Kategori Detay — BIST/TEFAS/Döviz/Maden/Kripto hepsi aynı
  fonksiyonu paylaşıyor). CSV'de Optima_Skor YOKSA (henüz precompute
  edilmediyse) davranış değişmedi — hâlâ tamamen canlı hesaplanıyor.
  **Bilinen kalıcı durum (kasıtlı, düzeltme değil):** hacim/DD ayarı
  (-10/-3/+2/+5, Max DD -3/-7) sadece Master Skor'a (worker.py'nin gece
  hesabına) gömülü olarak yansır; Teknik+Temel toplamı bu yüzden Master
  Skor'dan o ayar kadar farklı KALABİLİR — bu artık çelişki değil, ayrı
  bir katman (üstteki "Hacim: ... (X skor)" rozeti bunu zaten ayrıca
  gösteriyor). Bahri bu ek katmanı panelde ayrıca satır olarak istemedi,
  şimdilik sadece rozette kalıyor.

- **[KISMEN DOĞRULANDI, İZLEMEDE] v2.0.7.103/104 (25 ve 27 Temmuz 2026,
  Bahri'nin bulgusu — iki farklı "Fırsat Radari" olayı).**
  25 Temmuz'da SADECE KRİPTO için sağlık uyarısı gelmişti (DOVİZ/MADEN/
  BIST sağlam). 27 Temmuz 14:35 TRT'de (BIST seansı AÇIKKEN) ise "All
  jobs have failed" ile TÜM çalışma 3dk45sn'de çökmüştü. Bu iki olayın
  neden farklı göründüğünü açıklayan tutarlı hipotez: `borsapy` importu
  zaten try/except içindeydi (patlarsa sadece o kategori boş dönüyordu),
  ama `yfinance` importu HİÇ korumasızdı — BIST seansı kapalıyken
  `tara_bist()` hiç çağrılmadığı için sorun görünmüyordu (25 Temmuz'daki
  olay), seans açıkken çağrılınca (27 Temmuz) sarmalanmamış bir hata
  `main()`'in tamamını coturuyordu (DOVİZ/MADEN/KRİPTO/TEFAS dahil —
  Python'da yakalanmayan hata cagiran fonksiyonun TAMAMINI durdurur).
  **NOT: Bu hipotez mantıken tutarlı ama gerçek hata metniyle henüz
  doğrulanmadı** (GitHub Actions logu bu oturumda da görülemedi).
  **Uygulanan değişiklik (v2.0.7.104):** (1) `tara_bist()` içindeki
  `import yfinance` artık `borsapy` ile aynı desende try/except'e alındı
  — patlarsa sadece BIST bu koşuda atlanır, hata tipi+mesajı loglanır.
  (2) `main()`'deki 3 kategori çağrısı (`tara_fx_maden_kripto`,
  `tara_bist`, `degerlendir_tefas`) artık HER BİRİ kendi try/except'i
  içinde — bundan böyle hiçbir kategorideki beklenmeyen hata diğerlerini
  ya da Supabase yazımını/radar alarmını etkilemeyecek (savunma
  katmanı, ileride benzer bir hata sınıfı tekrar çıkarsa bile). **Sıradaki
  adım:** birkaç gün gözlemleyip hem "All jobs have failed" hem de
  kategoriye özel sağlık uyarılarının tekrarlanıp tekrarlanmadığını
  izle; tekrarlanırsa artık her kategori kendi hata tipini/mesajını
  loglayacağı için kök neden netleşecek.

- **[TEŞHİS BEKLİYOR] v2.0.7.103 (25 Temmuz 2026, Bahri'nin bulgusu —
  bir "Firsat Radari" çalışması "All jobs have failed" ile ~2dk 3sn'de
  bitti; ardından saglik kontrolü sadece KRIPTO için "1.9 saattir
  Supabase'e yazmıyor" uyarısı verdi, DOVİZ/MADEN/BIST etkilenmedi.**
  GitHub Actions'ın gerçek çalışma logu bu oturumda görülemedi (GitHub
  API'ye kimlik doğrulamasız erişim rate-limit'e takıldı, Bahri log
  metnini paylaşmadı). Semptom deseni (sadece KRIPTO, DOVİZ/MADEN sağlam)
  tüm betiğin çökmesini değil, `tara_fx_maden_kripto()` içindeki
  `bp.Crypto(...)` (BtcTurk) çağrılarına özgü bir sorunu işaret ediyor —
  muhtemel neden: `firsat_radari.yml`'deki `pip install` satırı hiçbir
  paketi sabitlemiyor (`websockets` hariç), bu yüzden `borsapy` her
  çalışmada en güncel sürümü çekiyor ve API'de bir değişiklik/hız
  sınırı (`bp.RateLimitError` sınıfı zaten mevcut) devreye girmiş
  olabilir — ama bu SADECE bir hipotez, doğrulanmadı. **Uygulanan
  değişiklik (kesin düzeltme DEĞİL, sadece teşhis):** `_bp_zaman_asimili()`
  artık ilk 5 ham hatayı (tür + mesaj) `etiket` parametresiyle
  (`MADEN:ALTIN_TRY`, `KRIPTO:BTC` gibi) logluyor — eskiden TÜM hatalar
  (RateLimitError dahil) sessizce yutulup `None` dönüyordu, hiçbir iz
  kalmıyordu. Ayrıca sonuç satırı artık kategori bazlı kırılım veriyor
  (`MADEN X/3, DOVIZ X/12, KRIPTO X/186`). **Sıradaki adım:** bir sonraki
  "Firsat Radari" çalışmasının GitHub Actions logunda bu yeni satırlar
  görülüp gerçek hata netleşmeden kalıcı bir düzeltme (versiyon
  sabitleme, throttling, vb.) yapılmamalı — körlemesine "muhtemelen
  budur" fixi uygulama.

- **[DOĞRULAMA BEKLİYOR] v2.0.7.102 (24 Temmuz 2026, Bahri'nin bulgusu —
  v2.0.7.101'den sonra art arda "Cancelled"/"No jobs were run"/"Internal
  server error" e-postaları).** İncelemede iki çalışma da (biri "Firsat
  Radari calistir" adımının ORTASINDA "The operation was canceled" ile
  kesilmiş — benim eklediğim Playwright adımlarına hiç sıra gelmeden;
  diğeri "Internal server error" ile) GitHub Actions'ın kendi altyapı
  sorununa işaret ediyordu, koddaki bir hataya değil. Yine de v2.0.7.101
  her çalışmayı ~20-90sn uzattığı ve bu workflow zaten çok sık (15-20
  dk'da bir) tetiklendiği için, bu ek yük üst üste binme riskini dolaylı
  artırmış olabilir. **Risk azaltma:** Playwright uyandırma adımları
  artık HER çalışmada değil, ~3 saatte bir (UTC saat % 3 == 0) çalışacak
  şekilde sınırlandı — uyku eşiği saatler mertebesinde olduğu için
  fazlasıyla yeterli, gereksiz yükü ~3'te 2 oranında azaltıyor. Bahri'nin
  önümüzdeki günlerde bu tür hata e-postalarının sıklığının azalıp
  azalmadığını gözlemlemesi gerekiyor.

- **[DOĞRULAMA BEKLİYOR, GARANTİSİZ DENEME] v2.0.7.101 (Streamlit Cloud
  uyku sorunu, 22 Temmuz 2026, Bahri'nin talebi).** Geçmiş bir oturumda
  (v2.0.5.2) bu soruna karşı zaten bir "keep-alive" denenmişti — curl
  ile yönlendirme zincirini takip edip uygulamayı ziyaret ediyordu.
  Güncel araştırma (Temmuz 2026) bunun ARTIK İŞE YARAMADIĞINI gösterdi:
  Streamlit'in güncel mimarisinde gerçek bir tarayıcı JavaScript
  çalıştırıp WebSocket bağlantısı (`/_stcore/stream`) kurmadan uygulama
  hiç başlamıyor; curl sadece statik bir HTML kabuğu alıyor (HTTP 200
  dönse bile uygulama gerçekte uyanmıyor) — bu, Bahri'nin hâlâ uyku
  ekranı görmesinin muhtemel açıklaması. **Denenen çözüm:**
  `firsat_radari.yml`'deki curl adımı, Playwright ile GERÇEK bir
  headless Chromium tarayıcısı açıp "Yes, get this app back up!"
  butonunu arayıp (varsa) tıklayan bir Python betiğiyle (`wake_app.py`)
  değiştirildi. Bu, Fırsat Radarı zaten 15-20 dakikada bir çalıştığı
  için aynı sıklıkta devreye girer. **ÖNEMLİ SINIRLAMA: Bu resmi/garantili
  bir çözüm DEĞİL** — topluluk kaynaklı bir workaround, Streamlit
  altyapısı değişirse bozulabilir. Playwright'ın kendi API kullanımı
  (yöntem isimleri) doğrulandı ama CANLI uygulamaya karşı uçtan uca test
  EDİLEMEDİ (sandbox ağ kısıtlaması, streamlit.app'e erişim yok) — Bahri
  push sonrası birkaç gün boyunca uygulamanın gerçekten uyku ekranına
  düşüp düşmediğini gözlemlemeli. Eğer bu da işe yaramazsa, kalan seçenek
  ücretli bir Streamlit katmanına geçmek (ayrıca araştırılmadı, Bahri
  istemedi/gündeme gelmedi).

- **[DOĞRULAMA BEKLİYOR] v2.0.7.100 (KRİTİK GÜVENLİK — RLS etkin olmayan
  tablolar, 22 Temmuz 2026, Bahri'nin bulgusu — Supabase güvenlik
  uyarısı e-postası: "Table publicly accessible... Row-Level Security
  is not enabled").** Kod taraması: `db.py`'deki 6 tablonun (`users`,
  `portfolio`, `sessions`, `password_resets`, `portfolio_sales`,
  `portfolio_fee_settings`) HİÇBİRİNDE RLS'i etkinleştiren kod yoktu —
  oysa `firsat_radari.py`/`worker.py`'deki 3 tablo (`intraday_scores`,
  `radar_alerts`, `bist_universe_dynamic`) bunu zaten yapıyordu. En
  güçlü şüpheli: `portfolio_sales`/`portfolio_fee_settings`, 16
  Temmuz'da (muhasebe sistemiyle, v2.0.7.47) eklenmişti — 1-2 Temmuz'daki
  (Session XII) manuel RLS taramasından SONRA, o taramaya hiç dahil
  olmadan. `emailer_standalone.py`'deki `email_send_log` de aynı
  şekilde eksikti. **Düzeltme:** Bu 7 tablonun hepsine `ALTER TABLE ...
  ENABLE ROW LEVEL SECURITY` eklendi — mevcut 3 tablodaki AYNI desen
  (politika/CREATE POLICY YOK, sadece RLS açık — uygulama Supabase'e
  DOĞRUDAN Postgres bağlantısıyla, RLS'i doğal olarak atlayan bir rolle
  bağlandığı için bu app'in kendi erişimini etkilemiyor, sadece genel
  PostgREST API'sinden gelen yetkisiz erişimi kapatıyor). `init_db()`
  uygulama her açıldığında zaten çalıştığı için, kod deploy olup
  uygulama bir kez yeniden başlayınca OTOMATİK uygulanır — manuel
  Supabase panel işlemi gerekmez. **Bahri'nin doğrulaması gereken:**
  push+reboot sonrası birkaç gün içinde Supabase'in bu uyarıyı e-posta
  ile tekrar göndermediğini, ve/veya Supabase Dashboard → Advisors
  sekmesinde bu uyarının kaybolduğunu kontrol etmeli.

- **[TAMAMLANDI, DOĞRULANDI] v2.0.7.99 (Portföyüm muhasebe tablosu
  düzenlemeleri, 20 Temmuz 2026, Bahri'nin talebi).** v2.0.7.98'in
  Alış/Satış Tutarı eklemesi "Tüm İşlem Geçmişi" tablosunu genişletip
  yatay scroll'a yol açmıştı. Üç düzeltme: (1) "Kategori" sütunu
  tamamen kaldırıldı; (2) "Ticker" sütunu "Portföy Varlıkları
  Tablosu"yla BİREBİR AYNI piksel genişliğine (79px) çekildi; (3)
  "Komisyon (₺)" başlığı "Kom. (₺)" olarak kısaltılıp daraltıldı (sütun
  ADI/verisi değişmedi, sadece `column_config`'in ilk pozisyonel
  argümanıyla görüntü etiketi değiştirildi — "Skor"→"Optima Skor"
  deseninin aynısı). Ayrıca Aylık Özet ve Yıllık Özet tablolarına,
  "Toplam Net K/Z"'den HEMEN ÖNCE, "İşlem Tutarı (₺)" sütunu eklendi
  (`portfolio_ledger.py`'nin `get_monthly_summary()`/`get_yearly_summary()`
  fonksiyonlarında, Miktar×Satış Fiyatı toplamı) — banka dekontlarıyla
  aylık/yıllık bazda da mutabakat yapılabilsin diye. Gerçek verilerle
  (3.256,43 TL) doğrulandı.

- **[TAMAMLANDI, DOĞRULANDI] v2.0.7.98 (Portföyüm işlem geçmişinde
  Alış/Satış Tutarı eksikliği, 20 Temmuz 2026, Bahri'nin bulgusu —
  gerçek bir ING altın satışı sonrası).** "Tüm İşlem Geçmişi" tablosu
  sadece birim fiyatları (Alış/Satış Fiyatı) ve Net K/Z gösteriyordu,
  GERÇEK İŞLEM TUTARI (Miktar × birim fiyat) hiç yoktu — banka
  dekontuyla (örn. "TL Karşılığı: 3.256,43 TL") doğrudan mutabakat
  yapılamıyordu. "Alış Tutarı" ve "Satış Tutarı" sütunları eklendi
  (ilgili fiyat sütununun hemen sağına), TOPLAM satırına da toplamları
  eklendi. Bahri'nin gerçek rakamlarıyla (0,55 gr, 5.470,00/5.920,78
  TL) doğrulandı — Satış Tutarı tam 3.256,43 TL çıkıyor, ING dekontuyla
  birebir eşleşiyor.

- **[TAMAMLANDI] v2.0.7.97 (20 Temmuz 2026, Bahri'nin bulgusu — Actions
  logları/ekran görüntüleri).** İki ayrı ama muhtemelen ilişkili sorun:
  1. **"Veri Güncelle" #78 çöktü** ("divergent branches... fatal: Need
     to specify how to reconcile", exit 128). v2.0.7.85'teki `git pull`
     düzeltmesi YETERSİZ kalmıştı — dallar gerçekten ayrışınca, runner
     ortamında `pull.rebase` config'i hiç ayarlanmadığı için git
     birleştirme stratejisini SORUYOR, reddediyordu. Üç workflow'un
     (`update_data.yml`, `health_check.yml`, `update_tefas_evening.yml`)
     push öncesi `git pull --no-edit --no-rebase origin main` kullanması
     sağlandı — ilk ikisinde eksikti/yetersizdi, health_check ve TEFAS
     akşam workflow'larında ise pull'un KENDİSİ hiç yoktu.
  2. **Fırsat Radarı'nda bir çalışma 2 saat 30 dakika, ardından birkaçı
     14-15 dakika sürmüş** (normali ~2 dakika) — tam olay penceresi
     (03:30-05:45 TRT) "Veri Akışı Uyarısı" e-postasındaki 2,9 saatlik
     gecikmeyle örtüşüyor. Kök neden: `firsat_radari.py`'nin KENDİ
     `bp.FX(...)/bp.Crypto(...).history()` çağrılarının (MADEN/DOVIZ/
     KRIPTO taraması, 188 kriptoya kadar) HİÇBİRİNDE zaman aşımı
     koruması yoktu — `live_data.py`'de v2.0.7.91'de yapılan AYNI
     düzeltme bu AYRI script'e hiç yansımamıştı. Şimdi 8 saniyelik
     zaman aşımı eklendi (aynı `ThreadPoolExecutor` deseni, dosyaya
     özel kopyalanmış — worker.py/live_data.py'yi import etmek yan
     etkili olabileceği için).
  **Doğrulama bekliyor:** Bahri push'tan sonra birkaç gün Actions
  geçmişini izleyip hem "Veri Güncelle"nin artık divergent-branch
  hatası vermediğini hem Fırsat Radarı çalışmalarının ~2 dakika
  civarında kaldığını teyit etmeli.

- **[TAMAMLANDI, DOĞRULANDI] v2.0.7.96 (Fırsat Radarı yanlış varlık adı,
  20 Temmuz 2026, Bahri'nin bulgusu — e-posta uyarıları).** Sabah 01:47
  alarmında KRIPTO/APT (Aptos) için "AK PORTFÖY ORTA VADELİ BORÇLANMA
  ARAÇLAR" (bir TEFAS fon adı) gösterilmişti. Kök neden:
  `firsat_radari.py`'nin `ad_map`'i SADECE Ticker'a göre kuruluyordu
  (`dict(zip(Ticker, Ad))`) — ama tickerlar kategoriler ARASINDA
  benzersiz değil (TEFAS'ta da "APT" kodlu bir fon varmış/olmuş).
  `dict(zip(...))` tekrarlanan anahtarlarda sessizce SON değeri kullanır
  — hangi kategori df_uni'de sonra geliyorsa o kazanıyordu. **Düzeltme:**
  `ad_map` artık `(Kategori, Ticker)` ikilisiyle anahtarlanıyor, çakışma
  artık mümkün değil. Simüle edilen çakışma senaryosuyla doğrulandı.
  **Not:** Şu anki CSV'de bu çakışma görünmüyor (APT sadece KRIPTO'da) —
  yani TEFAS fon listesi zamanla değişip o gün geçici olarak çakışmış
  olabilir. Bu, ayrıca genel bir ders: **tickerlar kategoriler arasında
  benzersiz olduğu VARSAYILMAMALI**, benzer bir hata başka bir yerde
  (örn. BIST-Kripto çakışmaları zaten "C" öneki ile çözülmüştü, ama
  TEFAS-Kripto çakışması hiç düşünülmemişti) tekrar çıkabilir.
- **[TAMAMLANDI, DOĞRULANDI] v2.0.7.94→95 (Kategori diversifikasyon
  garantisi TAMAMEN kaldırıldı, 19 Temmuz 2026, Bahri'nin bulgusu:
  ILU/ZARTRY, sonra PEPE/ETHFI/ALLO örnekleri).** Max Varlık Sayısı
  kategori sayısından (5) azken (v2.0.7.65'ten beri), sistem kategorileri
  KENDİ HAVUZ ORTALAMASINA göre sıralayıp en iyi N kategoriye 1'er slot
  veriyordu — bu, TEK BAŞINA en yüksek skorlu bir varlığın (TEFAS/ILU
  78,7) sırf kendi kategorisinin GENEL ORTALAMASI düşük diye elenip,
  objektif olarak DAHA DÜŞÜK skorlu başka bir varlığın (DOVIZ/ZARTRY
  66,7) seçilmesine yol açıyordu. **v2.0.7.94'te bu SADECE max_assets <
  5 durumuna düzeltilmişti** — ama max_assets=5 olunca (5<5 YANLIŞ
  olduğu için) ESKİ "her kategoriye en az 1 slot" mantığına geri
  dönülüyordu, Kripto'nun 3 tane 80,0 puanlı varlığından sadece 1'i
  (PEPE) gösterilebiliyor, ETHFI/ALLO (ikisi de 80,0) sırf "kategori
  payı" kuralı yüzünden elenip yerlerine DAHA DÜŞÜK puanlı BIST/Döviz
  varlıkları zorla ekleniyordu. **Bahri'nin kesin kararı:** "her zaman
  en iyi skor kazansın, kategori çeşitlendirme garantisi TAMAMEN
  kalksın" — max_assets ile kategori sayısı karşılaştırması TAMAMEN
  KALDIRILDI, artık HER DURUMDA (Max Varlık Sayısı ne olursa olsun) tüm
  havuzlardan objektif olarak en yüksek Optima_Skor'lu max_assets varlık
  doğrudan seçiliyor. Eski "eşit bölüşüm + kalite bazlı slot transferi"
  mantığı (v2.0.7.65 ve öncesi, `cat_quality`/`cats_by_qual`/`n_cats`
  değişkenleri dahil) TAMAMEN KALDIRILDI — artık gereksiz. Gerçek
  verilerle (PEPE/ETHFI/ALLO 80,0 + ILU 78,7 + ISGYO 70,0, Max=5) elle
  doğrulandı — ZARTRY (66,7) haklı olarak 6. sırada kalıp dışarıda
  kalıyor.

- **[ÇÖZÜLDÜ] v2.0.7.92 (Bütçe Optimizasyonu askıda kalma sorunu, 19 Temmuz
  2026) — KÖK NEDEN DOĞRULANDI.** v2.0.7.90/91 (yfinance/borsapy zaman
  aşımı) sorunun sadece bir kısmıydı; asıl neden Ana Sayfa'daki bütçe
  dağıtım (round-robin lot ekleme) döngüsünün HİÇBİR üst sınırının
  olmamasıydı — geçici teşhis satırları eklenip sorun tekrarlanınca,
  tabloda **PEPE (Kripto) 0,0001 TL fiyatla 8.185.865 birim** olarak
  önerilmiş görüldü — aşırı düşük fiyatlı bir varlık (IDR gibi bir döviz
  değil, meme-coin bir kripto para) kalan bütçeyi tüketmek için
  milyonlarca iterasyon gerektiriyordu, bu da döngüyü etkin olarak
  süresiz askıda bırakıyordu. **100.000 iterasyon / 5 saniye güvenlik
  freni işe yaradı, tablo başarıyla geldi.** Geçici teşhis satırları
  (`st.caption("[TEŞHİS]: ...")`) v2.0.7.93'te kaldırıldı — güvenlik
  freni mekanizmasının kendisi KALICI olarak kaldı.
- **[TAMAMLANDI] v2.0.7.93 (19 Temmuz 2026, Bahri'nin talebi).** (1)
  v2.0.7.92'nin geçici teşhis satırları temizlendi. (2) Ana Sayfa'nın
  Bütçe Optimizasyonu tablosunun altına KALICI bir açıklama eklendi:
  istenen `max_assets` sayısından daha az varlık önerildiğinde (örn.
  bir kategori uygun fiyatlı/sinyalli varlık bulamadığında), abonelerin
  "neden 10 istedim 8 geldi" sorusuna sohbette birine ihtiyaç duymadan
  kendi başlarına cevap bulabilmesi için hangi kategori(ler)in boş
  kaldığı açıkça yazılır.

- **[DOĞRULAMA BEKLİYOR] v2.0.7.91 (KAPSAMLI zaman aşımı koruması —
  muhtemel asıl kök neden, 19 Temmuz 2026).** Bahri'nin ikinci log
  dosyasında ("boş etiket" uyarısının tekrarlanma zamanları arasında
  TAM 5 dakikalık boşluklar — autorefresh aralığıyla birebir örtüşüyor)
  bulduğu kanıt, her script çalışmasının neredeyse tüm 5 dakikayı
  doldurduğunu gösterdi. Kök neden: `live_data.py`'deki `bp.FX(...)`/
  `bp.Crypto(...).history()` çağrılarının (canlidoviz/BtcTurk, 266
  varlığı etkileyen ANA canlı overlay) **HİÇBİRİNDE** zaman aşımı
  koruması yoktu — v2.0.7.90'daki BIST temettü düzeltmesi (~10 varlığı
  etkiliyordu) bu sorunun sadece küçük bir parçasıydı. Paylaşılan
  `_borsapy_zaman_asimili()` yardımcısı eklendi, 6 çağrı yeri (MADEN
  özet, iki adet FX/anlık-fiyat yedek yolu, Döviz/Maden/Kripto detay
  sayfası geçmiş verisi) 10 saniyelik zaman aşımıyla sarmalandı. **Bahri
  push'tan ve reboot'tan sonra sayfa yüklemesinin makul sürede (birkaç
  dakikayı geçmeden) tamamlandığını ve "sürekli çalışıyor" görüntüsünün
  bitip bitmediğini doğrulamalı.**
- **[DOĞRULAMA BEKLİYOR] v2.0.7.90 (BIST temettü zaman aşımı).** Yukarıdaki
  v2.0.7.91 ile aynı kökten, dar kapsamlı ilk düzeltme — hâlâ geçerli,
  ayrıca doğrulanmasına gerek yok (v2.0.7.91'in bir parçası sayılabilir).

- **[TAMAMLANDI] v2.0.7.89 — Streamlit `use_container_width` deprecation
  düzeltmesi (19 Temmuz 2026, Bahri'nin bulgusu: "sisteme giremiyorum",
  logları inceleyince gerçek çökme YOKTU — Streamlit'in kendi deprecation
  uyarılarıydı; asıl yavaşlık container'ın 29+ saattir kesintisiz açık
  olmasından kaynaklanıyordu, reboot çözdü).** Loglarda "`use_container_
  width` will be removed after 2025-12-31" uyarısı görüldü — bu tarih
  ZATEN GEÇMİŞ (bugün 19 Temmuz 2026). 27 kullanım `width='stretch'`
  olarak düzeltildi (Streamlit'in kendi önerdiği birebir karşılık).
  **Kalan, düşük öncelikli, DOKUNULMAYAN uyarılar:**
  - `st.radio("", ..., label_visibility="collapsed")` gibi boş etiket
    kullanımları ("may be disallowed in the future" — kesin tarih yok,
    henüz acil değil).
  - `components.html(...)` → `st.iframe` önerisi — **DİKKAT: bunu kör
    kör değiştirme**, `components.html` ham HTML/JS içeriği render eder,
    `st.iframe` ise muhtemelen bir URL (`src`) bekler — API'ler birebir
    aynı olmayabilir, önce Streamlit'in güncel dokümantasyonu
    doğrulanmadan değiştirilirse splash ekranı (`_splash_html`) bozulabilir.

- **[TAMAMLANDI, DOĞRULANDI] El kitapları güncellemesi (18 Temmuz 2026,
  25 Temmuz'da GitHub'dan tekrar doğrulandı — gerçekten yayında).**
  Abone ve Yönetici El Kitabı'nda (Word) birikmiş güncel-olmayan bilgiler
  bulundu ve düzeltildi: döviz/maden/kripto sayıları (63/17/188), Paladyum
  kaldırılması, alarm eşiği (85/+15), Yönetici kitabındaki veri kaynağı
  tablosunun ÇOK ESKİ olan Döviz (TCMB/EVDS — asla doğru değildi artık)
  ve Maden/Kripto (sentetik USD×kur yedek — artık yasak) satırları, "⚠/✓/
  ⓘ" gibi emoji/dekoratif sembollerin TAMAMEN temizlenmesi (kalıcı emoji
  yasağı kurala Word dosyaları da dahil), ve Yönetici kitabına bugünkü
  oturumun (v2.0.7.76-88) özet bir versiyon geçmişi eklenmesi. Bahri henüz
  push etmedi — dosyalar hazır, bekliyor.

- **[BAŞARISIZ, GERİ ALINDI] v2.0.7.87 (giriş ekranı kalıntısı UX
  düzeltmesi) — v2.0.7.88 ile geri alındı, 18 Temmuz 2026.** Bahri'nin
  bulgusu: giriş yapıp bütçe girdikten sonra bile ana alanda eski Giriş/
  Kayıt ekranı görüntüsü kalıyordu. Denenen çözüm: auth gate sonrası
  hemen `st.empty()` ile "Yükleniyor..." yer tutucusu eklemek. **BU
  YANLIŞ VARSAYIMA DAYANIYORDU VE İŞE YARAMADI** — bkz. §4'teki
  "Streamlit yeni elemani eskinin YERINE koymaz" notu. Sonuç: "Yükleniyor"
  mesajı eski giriş formunun ÜSTÜNE eklendi, ikisi birlikte görünüp durum
  daha karışık hale geldi ("daha beter oldu" - Bahri). Kod tamamen geri
  alındı (v2.0.7.88). **Kök sorun (yükleme süresinin kendisi) hâlâ
  çözülmedi** — bkz. hemen altındaki "İlk açılış yavaşlığı" maddesi,
  gerçek çözüm o mimari ödünleşimi ele almaktan geçiyor, kozmetik bir
  yama ile olmuyor.

- **[DOĞRULAMA BEKLİYOR] v2.0.7.86 (Kripto/Döviz/Maden Liste=Detay skor
  tutarlılığı).** CSKY örneği (Liste 70,7 / Detay 60,7, Hacim cezası -10)
  ile keşfedildi — TEFAS'ta bulunanla AYNI hata (BIST-tarzı DD/hacim dahil
  TAM skorun sadece BIST için önceden hesaplanması), ama Kripto/Döviz/Maden
  için TEFAS'ın rate-limit engeli YOK (worker.py zaten gerekli geçmiş
  veriyi çekiyordu, sadece DD/hacim'i skora katmıyordu). Düzeltildi:
  worker.py'nin KRIPTO ve DOVIZ döngüleri artık `Optima_Skor`'u (DD+hacim
  dahil) doğrudan CSV'ye yazıyor; MADEN için ise bu hesap `live_data.py`'nin
  canlı overlay'inde yapılıyor (MADEN'in gerçek geçmiş verisi zaten SADECE
  orada çekiliyor, worker.py'de değil). Bahri push'tan ve worker.py'nin
  bir kez daha çalışmasından sonra birkaç Kripto/Döviz/Maden varlığında
  Liste=Detay skorunun eşleştiğini doğrulamalı. **TEFAS hâlâ kapsam
  dışı** (rate-limit engeli hâlâ geçerli, ayrı bir konu).

- **[KOD PUSH EDİLDİ, KULLANICI DOĞRULAMASI BEKLİYOR] v2.0.7.84 (performans
  - get_bist_dividend önbellekleme).** Kod GitHub'da doğrulandı (18 Temmuz).
  Bahri'nin Ana Sayfa'da bütçe girip Bütçe Optimizasyonu tablosunun açılma
  hızının ve checkbox tıklamasının gerçekten hızlandığını onaylaması
  bekleniyor.
- **[ÇÖZÜLMEDİ/MİMARİ ÖDÜNLEŞİM] "İlk açılış" yavaşlığı.** `load_universe()`
  zaten 10 dakika önbellekli — ama önbellek her dolduğunda Döviz/Maden/
  Kripto'nun canlı fiyat overlay'i (266 varlık için canlidoviz/BtcTurk
  gerçek zamanlı çağrısı) yeniden ödenen bir maliyet. Bu, "daha taze veri"
  ile "daha hızlı açılış" arasında BİLİNÇLİ bir tasarım tercihi - kesin
  bir hata değil. Ayrıca Streamlit Cloud'un ücretsiz katmanı uzun süre
  kullanılmayan uygulamaları uyutabilir (platform kaynaklı, kodla
  çözülemez). Bahri bunu hâlâ sorun olarak görürse: (a) önbellek süresini
  uzatmak (10dk→30dk, tazelik/hız takası) (b) overlay'i sadece belirli
  kategorilerde/varlıklarda çalıştırmak gibi seçenekler değerlendirilebilir.
- **[DOĞRULAMA BEKLİYOR] v2.0.7.85 push'u (workflow git pull-before-push).**
  18 Temmuz 2026'da GitHub Actions "update_data" manuel çalıştırması
  (#70), Bahri AYNI ANDA elle push yaptığı için "non-fast-forward"
  hatasıyla tamamen BAŞARISIZ oldu — worker.py'nin ürettiği
  `kripto_parite_map.json` dahil TÜM veri kayboldu (commit edildi ama
  push edilemedi, iş başarısız sayılınca atıldı). Workflow'a commit
  sonrası/push öncesi `git pull --no-edit` eklendi (Bahri'nin kendi
  manuel push akışındaki AYNI desen). **Push'tan sonra "update_data"
  workflow'unu TEKRAR manuel çalıştır** ve bu sefer başarıyla bitip
  bitmediğini doğrula — bitmeden CSKY (v2.0.7.82) düzelmeyecek.
- **[DOĞRULAMA BEKLİYOR] v2.0.7.83 (alarm eşiği 85/+15).** Bahri'nin
  günlük e-posta sayısının makul bir seviyeye düşüp düşmediğini
  onaylaması bekleniyor.
- **[DOĞRULAMA BEKLİYOR] v2.0.7.80/81 push'u (Döviz düzeltmeleri).**
  Bahri push'u yaptıktan ve worker.py bir kez daha çalıştıktan sonra:
  ZARTRY'nin Detay sayfasındaki grafik/MA/DD tablosunun artık dolu
  geldiğini, ana 12 dövizin (özellikle eskiden çapraz-kur kullanan JPY/
  AUD/CAD/NZD/NOK/SEK/DKK/CNY) hâlâ doğru çalıştığını doğrula.
- **[ERTELENDİ/BEKLEMEDE] TEFAS Liste/Detay skor farkı (DD/hacim cezası,
  GZL örneği).** Kalıcı çözüm (worker.py'nin TEFAS için de BIST gibi tam
  skoru geceden hesaplaması) TEFAS'ın kendi API'sinin **dakikada 6 istek**
  sınırı yüzünden 1348 fonun tamamı için pratik değil (en iyi ihtimalle
  ~3,7 saat, muhtemelen çok daha fazla — bkz. §4'teki rate-limit notu).
  Bahri bu konudan bir süre yorulduğunu belirtti ("bu işten vazgeçelim"),
  sonra "bugünlük bırakalım" ile yumuşattı. **Şu anki durum: HİÇBİR
  KOD DEĞİŞİKLİĞİ YAPILMADI, TEFAS'ta liste skorunda basit (DD'siz) hesap
  kullanılmaya devam ediyor.** Bahri kendisi tekrar gündeme getirmeden
  bu konuyu proaktif olarak açma — yorulduğu bir konuydu.
- **[SORULDU] Genel uygulama yavaşlığı.** Bahri "hâlâ devam ediyor" dedi
  ama nerede (açılış/sayfa geçişi/detay tıklama) hiç netleşmedi. Bir
  sonraki oturumda bunu sorup somut bir yer/sayfa öğrenilmeli, körlemesine
  performans avına çıkma.
- **[DÜŞÜK ÖNCELİK] ~19 adet bağımsız `"—"` kullanımı** (radar tablosu,
  admin paneli, portföy metrikleri gibi `fmt_tr()`'den GEÇMEYEN sabit
  metinler) hâlâ temizlenmedi — sadece merkezi `fmt_tr`/`fmt_tr_isaretli`
  düzeltildi (v2.0.7.76). Bahri isterse ayrı bir taramada hepsi bulunup
  düzeltilebilir.
- **[DÜŞÜK ÖNCELİK] worker.py'nin TEFAS "Minimal fallback" yolu**
  (tefas_client.py import edilemezse devreye giren, nadiren çalışan yedek)
  hâlâ eski sahte-sıfır RSI formülünü kullanıyor (bkz. §4'teki "TEFAS
  Ret6M/Ret1Y için sahte %0,00" notu) — bu yol pratikte neredeyse hiç
  tetiklenmediği için düzeltilmedi.

---

## 6. Denenip Reddedilen / Geri Alınan Yaklaşımlar

| Yaklaşım | Durum | Sebep |
|---|---|---|
| TCMB (Döviz veri kaynağı) | REDDEDİLDİ (v2.0.7.74) | Sadece 21 döviz kapsıyor, resmi/banka kuru. Harem/canlidoviz 51'in tamamını serbest piyasa fiyatıyla kapsıyor. |
| Manuel "Canlı Fiyatları Yenile" (BIST) | KALDIRILDI (v2.0.7.64) | Fırsat Radarı zaten otomatik + daha kapsamlı (772 vs 100 hisse). |
| KAP JSON API (`api/financialReport/...`) | HİÇ GERÇEK DEĞİLDİ (v2.0.7.66) | Doğrulanmadan varsayılmış, hiçbir zaman çalışan bir endpoint olmadı. Gerçek yol: HTML tablo parse. |
| Muhasebe Toplam satırını ayrı tabloya taşımak | GERİ ALINDI (v2.0.7.60) | Görsel kopukluk yarattı, checkbox sorunundan daha kötüydü. |
| VBA makrosu (KAP şirket listesi taraması) | Python'a çevrildi | `bist-sirketler` sayfası JS'e bağımlı olabilir, Python + requests daha güvenilir. |
| Excel'deki (Şirketler.xlsx) hyperlink'lerden URL çekmek | Mümkün değil | Bu spesifik KAP export'unda gizli hyperlink yok, düz metin. |
| Paladyum (Değerli Madenler) | KALDIRILDI (v2.0.7.76) | RSI/Ret1M için hiçbir kaynakta (canlidoviz'de slug yok, Harem 401) geçmiş veri yok, sonsuza dek 0 skor gösterecekti. |
| Harem/doviz.com kurumsal arşivi (yeni tür eklemek için) | ERİŞİLEMEZ (17 Tem 2026) | Token çıkarma mekanizması (hem borsapy'ninki hem elle deneme) 401 alıyor - site token'ı artık HTML'e gömmüyor. Tekrar denemeden önce güncel durumu test et. |

---

## 7. Versiyon Kilometre Taşları (özet)

- v2.0.4.x: Temel sistem (BIST/TEFAS/Kripto/Döviz/Maden, KAP entegrasyonu ilk hali)
- v2.0.7.30-45: UI iyileştirmeleri, kripto/döviz/maden genişletme (20→186, 12→63, 4→18)
- v2.0.7.47-67: Muhasebe sistemi (portfolio_ledger.py), Türkçe format düzeltmeleri (sistem geneli), KAP gerçek entegrasyonu
- v2.0.7.68-71: Sinyal mantığı düzeltmeleri, veri-yok tespiti (`_gecmis_veri_yok` bayrağı)
- v2.0.7.72-74: TCMB tarihsel deneme → Harem/canlidoviz'e geçiş (TCMB tamamen terk edildi)
- v2.0.7.76-77 (17 Temmuz 2026, Oturum XVIII): Paladyum kaldırıldı; Harem/
  doviz.com arşiv API'sinin 401 ile kapandığı keşfedildi (bkz. Döviz/Maden
  bölümü); MADEN `_gecmis_veri_yok` bayrak temizleme hatası (ALTIN/GUMUS/
  PLATIN skor sıfırlanması) düzeltildi; eksik veri için `"—"` yerine boş
  gösterim; **`bool(NaN)==True` hatası** (TEFAS/BIST/KRIPTO Detay
  sayfalarının hepsini etkileyen, 4 konumda tekrarlanan) düzeltildi.
- v2.0.7.78 (17 Temmuz 2026, Oturum XVIII): TEFAS Ret6M/Ret1Y için sahte
  %0,00 düzeltildi (DTH örneği, `_pct()`/`_rsi_from_rets()`/worker.py Kaydet
  bölümü) — RSI hesabı artık eksik dönemi doğru dışlıyor. Liste/Detay
  arasındaki DD/hacim cezası farkı (GZL örneği) için kalıcı çözüm kararı
  alındı (worker.py'nin TEFAS için de tam skoru geceden hesaplaması) ama
  fizibilite testi sonucu bekleniyor.
- v2.0.7.79 (17 Temmuz 2026, Oturum XVIII): "Skor Bileşimi" paneli
  (YAYLA örneği) tek kaynağa bağlandı — `_teknik_alt_skor()`/
  `_temel_alt_skor()` yardımcıları eklendi, `kap_client.
  score_from_fundamentals()` artık kullanılmıyor, etiketler /75+/25
  olarak düzeltildi.
- v2.0.7.80 (18 Temmuz 2026, Oturum XVIII): Döviz Detay sayfası
  (ZARTRY örneği) — `_DOVIZ_TO_BP` 51 genişleme döviziyle genişletildi
  (worker.py'nin zaten çalışan `_DOVIZ_TRUNCGIL_KOD` yoluyla aynı
  kodlar), "geçmiş fiyat verisi yüklenemedi" hatası ve boş MA/DD
  tablosu düzeltildi.
- v2.0.7.81 (18 Temmuz 2026, Oturum XVIII): Döviz'de USD-çapraz-kur
  hesabı (JPY/AUD/CAD/NZD/NOK/SEK/DKK/CNY) tamamen kaldırıldı — Bahri'nin
  temel ilkesine (bkz. dosya başı §0) aykırıydı. canlidoviz artık TÜM 63
  döviz için birincil kaynak.
- v2.0.7.82 (18 Temmuz 2026, Oturum XVIII): `kripto_parite_map.json`
  artık git'e commit ediliyor (CSKY örneği) — BIST ile çakışan kriptoların
  Detay sayfası düzeldi.
- v2.0.7.83 (18 Temmuz 2026, Oturum XVIII): Fırsat Radarı alarm eşikleri
  75/+10'dan 85/+15'e yükseltildi (Bahri'nin talebi) — kripto evreninin
  19'dan 186'ya genişlemesiyle günlük ~48 e-postaya çıkan alarm seli
  için.
- v2.0.7.84 (18 Temmuz 2026, Oturum XVIII): `get_bist_dividend()`
  önbelleklendi (24 saat, sadece ticker'a göre) — Ana Sayfa Bütçe
  Optimizasyonu tablosunun açılması ve checkbox tıklamalarındaki ciddi
  yavaşlığın kök nedeniydi (Bahri'nin bulgusu).
- v2.0.7.85 (18 Temmuz 2026, Oturum XVIII): GitHub Actions
  "update_data" workflow'una commit sonrası/push öncesi `git pull`
  eklendi — Actions #70 çalışmasının "non-fast-forward" ile tamamen
  başarısız olup `kripto_parite_map.json` dahil ürettiği her şeyi
  kaybetmesinin kalıcı çözümü.
- v2.0.7.86 (18 Temmuz 2026, Oturum XVIII): Kripto/Döviz/Maden'de Liste
  skoru artık BIST gibi DD/hacim cezası dahil (CSKY örneği) — worker.py
  (Kripto/Döviz) ve live_data.py (Maden) canlı overlay'i güncellendi.
  TEFAS hâlâ rate-limit engeli yüzünden kapsam dışı.
- v2.0.7.87 (18 Temmuz 2026, Oturum XVIII): Giriş sonrası ana alanda eski
  Giriş/Kayıt ekranı görüntüsü kalması için "Yükleniyor..." yer tutucusu
  denendi — **BAŞARISIZ, v2.0.7.88 ile GERİ ALINDI** (Streamlit'in
  element-degistirme modeli yanlış anlaşılmıştı, bkz. §4).

**Yeni bir oturumda "acaba X daha önce denendi mi" sorusu varsa, önce bu
dosyayı ve `git log --oneline` çıktısını kontrol et.**
