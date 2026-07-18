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
- **Emoji/dekoratif sembol YASAK** — ne kod/UI'da ne chat yanıtlarında.
- **Her zaman GitHub'dan taze klon ile başla, yerel sandbox'a güvenme.**
  Bir oturumda yerel çalışma klasöründe GERÇEK GITHUB'A HİÇ GÖNDERİLMEMİŞ
  bir düzeltme bulunmuştu (v2.0.7.68, get_signal fonksiyonu) — muhtemelen
  önceki bir oturumda yapılıp unutulmuş. `git log -S"arama_metni"` ile bir
  değişikliğin gerçekten commit edilip edilmediğini HER ZAMAN doğrula.

---

## 5. BEKLEYEN İŞLER / TODO (her oturum başında kontrol et)

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
