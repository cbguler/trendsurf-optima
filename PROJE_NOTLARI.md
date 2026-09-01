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

- **[UYGULANDI, CANLI TEST EDİLMEDİ] v2.0.7.164 (19 Ağustos 2026,
  Bahri Actions logunu paylaştı — kesin teşhis): GEMINI 429 "TOO MANY
  REQUESTS" - RETRY-WITH-BACKOFF EKLENDİ, KESİN RAKAM HÂLÂ BİLİNMİYOR.**
  - **Log kanıtı:** `[haber_izleme] Toplu ceviri hatasi: HTTPError: 429
    Client Error: Too Many Requests` + `Bugunku toplam AI cagrisi: 20/120`.
    Yani: (1) 429 GERÇEK, tahmin değil - bu turun ÇEVİRİSİ gerçekten
    reddedildi. (2) Bugünkü kümülatif çağrı sadece 20 - kendi koyduğumuz
    120 günlük bütçenin çok altında. (3) Bu turdaki TEK Gemini isteği
    (çeviri) BİLE 429 aldı - yani sorun bizim günlük bütçemiz değil,
    Google'ın kendi tarafındaki bir kısıt.
  - **19 Ağustos'ta 5 farklı üçüncü taraf kaynak tarandı, HEPSİ
    BİRBİRİNDEN FARKLI dakikalık/günlük rakam verdi** (dakikalık 5/10/15,
    günlük 25/50/100/250/1500 gibi). Bu dağınıklık zaten kod içinde
    belgeleniyordu (v2.0.7.160). Kesin rakam KODA GÖMÜLMEDİ - bunun
    yerine dayanıklılık eklendi: **KESİN RAKAM Google AI Studio /
    Google Cloud Console'un kendi kota sayfasından görülmeli**
    (aistudio.google.com/apikey veya Cloud Console > APIs & Services >
    Quotas) - bu proje için GERÇEK, üçüncü taraf tahmini olmayan rakam
    orada. **Bahri isterse bu sayfaya birlikte bakılabilir.**
  - **Eklenen dayanıklılık (`_gemini_istek_gonder` sarmalayıcı, HER İKİ
    Gemini çağrı noktasında kullanılıyor - `_ai_dogrula` ve
    `_toplu_ceviri`):** 429 alınırsa 65 saniye (dakikalık pencerenin
    resetlenmesi için 60 sn + güvenlik payı) beklenip BİR KEZ DAHA
    denenir. **GÜVENLİK SINIRI:** bir turda bekleyip tekrar deneyip YİNE
    429 alınırsa, o turun GERİ KALANINDA bir daha BEKLENMEZ (hemen
    başarısız olunur) - yoksa çok sayıda eşleşmeli bir turda TÜM 10
    dakikalık workflow zaman aşımı retry beklemelerinde tükenebilirdi.
    Bayrak (`_ardisik_429_goruldu`) her turun başında sıfırlanır.
    İzole test edildi (sahte 429 senaryosu): ilk çağrı 1 kez bekleyip
    tekrar deniyor, ikinci çağrıda hiç beklemeden hemen başarısız oluyor
    - doğrulandı.
  - **429 DIŞINDAKİ hatalarda YENİDEN DENENMEZ** (400/401/500 vb. -
    bunlar beklemekle düzelmez, ör. geçersiz anahtar).
  - **AYRI, DAHA KÜÇÜK BİR ŞÜPHE - Actions ekran görüntüsünden
    gözlemlendi:** workflow'un çalışma sıklığı yapılandırılan "10
    dakikada bir" DEĞİL, gözlemlenen aralık ~25-40 dakika. Bu,
    `haber_izleme.yml`'in kendi yorumunda zaten belgelenen "GitHub'ın
    best-effort cron'u" sorununun CANLI KANITI. Kalıcı çözüm hâlâ
    kurulmadı (cron-job.org + workflow_dispatch, `firsat_radari`'de
    zaten kullanılan yöntem) - bu bir GitHub Secrets/harici servis
    kurulumu, git push ile yapılamaz, Bahri karar verip kurmalı.


  Bahri'nin bulgusu — "değişen bir şey olmadı, haberler yine ingilizce,
  maradona haberi yine filtreye takılan haberler arasına giriyor"):
  MARADONA BULGUSUNUN KESİN KÖK NEDENİ + "HABER AKIŞI BAKIMI" ARACI.**
  - **DOĞRULAMA:** GitHub'dan taze klonla kontrol edildi - v2.0.7.161
    VE v2.0.7.162 GERÇEKTEN CANLIDA (commit `1924c0c`, 19 Ağustos
    14:40'ta push edilmiş). Yani "kod düzeltmesi çalışmıyor" DEĞİL.
  - **GERÇEK KÖK NEDEN (test edilerek doğrulandı):** `haber_akisi`
    tablosu sadece `baslik` saklıyor, `ozet` SAKLAMIYOR. Maradona
    haberinin SADECE başlığıyla test edildi - yeni (düzeltilmiş) kod
    ile bile HİÇBİR kalıba eşleşmiyor (boş liste döndü). Bu şu demek:
    o satır, hatanın giderildiği ANDAN ÖNCE yazılmış eski bir kayıt -
    `eslesen_kalip` ve `baslik_tr` bir haber AKIŞA YAZILDIĞI ANDA
    hesaplanıp DONUYOR, filtre/çeviri mantığı sonradan düzelse bile
    ESKİ satırlar KENDİLİĞİNDEN yeniden değerlendirilmiyor - çünkü o
    haberin URL'si zaten `haber_islenmis`te "görüldü" işaretli, RSS
    döngüsü bir daha ona hiç uğramıyor.
  - **ÇEVİRİ İÇİN AYRI BİR ŞÜPHE VAR, HENÜZ DOĞRULANAMADI:**
    `haber_izleme.yml`'in KENDİ YORUMU (18 Ağustos'tan beri orada duruyor)
    GitHub'ın varsayılan `schedule: cron` tetikleyicisinin "best-effort"
    olduğunu ve gecikme/atlama yaşayabileceğini, `firsat_radari.yml`/
    `send_email.yml` geçmişinde bu sorunun zaten yaşandığını, güvenilir
    tetikleme için cron-job.org (harici, ücretsiz) kurulması GEREKTİĞİNİ
    söylüyor - **ama bu HİÇBİR ZAMAN GERÇEKTEN KURULMADI**, sadece yorum
    olarak kaldı. Workflow'un push'tan bu yana HİÇ ÇALIŞMAMIŞ olma
    ihtimali güçlü bir şüphe - kesin cevap Actions sekmesinde.
    **BAHRI'DEN BEKLENEN:** Actions > "Beklenti Modu Haber Izleme" >
    son çalışma zamanı + logundaki "CEVIRI ATLANDI"/"Toplu ceviri
    hatasi"/"N baslik cevrildi" satırlarından hangisi bastığı.
  - **YENİ ARAÇ - Admin Paneli > "Haber Akışı Bakımı":** son N gün
    (varsayılan 2) `haber_akisi` VE `haber_islenmis` satırlarını siler -
    böylece RSS'te hâlâ mevcut olan URL'ler bir sonraki turda "yeni"
    sayılıp GÜNCEL kod ile yeniden işlenir/çevrilir. **SINIRLAMA açıkça
    UI'da yazılı:** her kaynaktan sadece ~30 haber RSS'te tutulur, bu
    pencerenin dışına çıkmış eski haberler GERİ GELMEZ (7 günlük doğal
    temizlikle kaybolurlar, yeniden işlenmezler).
  - **KALICI ÇÖZÜM (Bahri karar vermeli, kod dışı bir adım):**
    haber_izleme.yml için de firsat_radari'de zaten kullanılan
    cron-job.org + workflow_dispatch yöntemi kurulmalı - bu bir GitHub
    Secrets/harici servis kurulumu, git push ile yapılamaz. Bahri
    isterse adım adım yardım edilebilir.


  (19 Ağustos 2026, Bahri'nin talebi — "anahtar kelime ön-filtresi ve
  kalıplara daha sonra ekleme yapılabilir hale getirilebilir mi ...
  kalıpların netleşmesi halinde hangi varlıkların Optima Skorları hangi
  oranda etkilenecek tabloda görmek isterdim"): KALIPLAR KODDAN
  VERİTABANINA TAŞINDI + ADMIN PANELİNDEN YÖNETİLEBİLİR HALE GETİRİLDİ.**
  - **Üç yeni tablo:** `haber_kaliplari` (ad/açıklama/aktif), `haber_kalip_kelime`
    (TR/EN kelime listeleri, kalıp silinince CASCADE ile silinir),
    `haber_kalip_etki` (kategori başına puan — MADEN/DOVIZ/BIST/KRIPTO).
    Yön (artış/azalış) AYRI SAKLANMIYOR, puanın işaretinden türetiliyor
    (tek doğruluk kaynağı — iki yerde tutup sapma riski yok).
  - **Tohumlama programatik yapıldı:** eski koda gömülü 6 kalıbın
    (kelimeler + puanlar + açıklamalar) TAMAMI Python `exec()` ile
    KAYNAK DOSYALARDAN çekilip veritabanına yazıldı — elle yeniden
    yazılmadı, transkripsiyon hatası riski yok. `init_db()` her
    çalıştığında kontrol eder, tablo BOŞSA tohumlar, DOLUYSA hiçbir şey
    yapmaz (admin'in yaptığı düzenlemelerin üzerine yazmaz).
  - **haber_izleme.py:** `_kaliplari_yukle()` her turun başında
    `db.get_kaliplar(sadece_aktif=True)` çağırıp kelime listelerini
    kelime-sınırlı regex'e derliyor (v2.0.7.161'deki "warning" düzeltmesi
    AYNEN korunuyor). DB okunamazsa boş sözlüklerle devam eder — o tur
    hiçbir haberi tespit etmez ama akışa yazmaya devam eder (güvenli
    taraf: "hiçbir şey tespit etme", "her şeyi tespit et" değil).
  - **app.py:** `_KALIP_TABLOSU`/`_KALIP_ISIM`/`_KALIP_ACIKLAMA` artık
    `st.cache_data(ttl=300)` ile veritabanından yükleniyor — Admin
    Panelinde bir değişiklik yapılınca `st.cache_data.clear()` çağrılıyor,
    yani değişiklik ANINDA yansır, 5 dakika beklemeye gerek yok.
  - **admin.py — "Kalıp Yönetimi" bölümü eklendi:**
    - **Bahri'nin istediği etki tablosu:** her kalıp satır, her kategori
      sütun, hücrede işaretli puan (`+8.0`, `-6.0`, boşsa `—`).
    - Her kalıp için: aktif/pasif anahtarı, kelime ekleme/çıkarma
      (TR/EN ayrı), kategori başına puan girişi, "Bu Kalıbı Kalıcı Olarak
      Sil" (iki adımlı onay — "Evet, Sil" / "Vazgeç").
    - "Yeni Kalıp Ekle" — anahtar/ad/açıklama girip oluşturur, sonra aynı
      ekrandan kelime ve puan eklenir. **Kelimesiz veya etkisiz bir kalıp
      hiçbir şeyi tetiklemez** (regex boşsa derlenmez, etki boşsa skor
      değişmez) — UI bunu açıkça belirtiyor.
  - **DÜZELTILEN BİR HATA (kendi kendine yakalandı, canlıya gitmeden):**
    admin.py'ye Kalıp Yönetimi bölümünü eklerken yapılan bir `str_replace`
    yanlışlıkla mevcut kullanıcı "Sil" düğmesinin kodunu SİLDİ (eşleşen
    metnin içine dahil edilip yeni metinde korunmadı). Derleme hatası
    vermediği için (geçerli Python'du, sadece işlevsellik eksikti) fark
    edilmesi ZOR bir hataydı — `grep -n '.button('` ile TÜM düğme
    çağrılarını tek tek sayarak yakalandı ve geri eklendi. **DERS: kod
    kaldıran bir str_replace'ten sonra, değişen dosyadaki TÜM
    etkileşim noktalarını (düğme/fonksiyon/tablo referansı) tek tek
    sayıp orijinaliyle karşılaştırmadan "tamamlandı" denemez.**
  - **AÇIK KALAN İKİ MADDE:**
    1. Bu turun tamamı gerçek Supabase bağlantısı olmadan (sandbox'ta
       ağ/kimlik bilgisi yok) test edildi — SQL sözdizimi ve mantık
       sahte veriyle doğrulandı ama GERÇEK Postgres'e karşı ÇALIŞTIRILMADI.
       İlk push sonrası Streamlit Cloud loglarında `init_db basliyor` ve
       ardından hata OLMADIĞI teyit edilmeli.
    2. v2.0.7.161'de açık bırakılan "çeviri neden hiç çalışmadı" sorusu
       HÂLÂ AÇIK — Bahri'den Actions log çıktısı bekleniyor.


  Bahri'nin bulgusu — "Maradona'nın doktoru ile ilgili haberi neden
  piyasa etkisi olası haberlerin içine aldın?"): ÖN-FİLTRE ALT-DİZE
  HATASI + ÇEVİRİ DAYANIKLILIĞI.**
  - **KÖK NEDEN (kesin, yeniden üretildi):** `_on_filtre_eslesen_kaliplar`
    anahtar kelimeyi düz alt-dize olarak arıyordu (`if kelime in metin`).
    "war" kelimesi, Maradona haberinin özetindeki **"crucial WARning
    signs"** ifadesinin içinde geçtiği için haber "Jeopolitik gerilim"
    kalıbına takıldı. Aynı tuzağın doğrulanmış diğer örnekleri:
    "attack"→"heart attack" (bu kelime bazlı, aşağıya bak),
    "fed"→"conFEDeration"/"FedEx", "oil"→"turmOIL", "crude"→"crudely".
  - **ÇÖZÜM:** kelime sınırı (`\b`) ile regex eşleştirme. Türkçe ve
    İngilizce AYRI ele alınıyor çünkü Türkçe sondan eklemeli:
    Türkçe `\bkelime\w*` (savaş → savaşı/savaşta yakalanır),
    İngilizce `\bkelimes?\b` (sadece çoğul). **LİSTEYE KELİME EKLERKEN
    DOĞRU DİL ANAHTARINA EKLE** (`_ANAHTAR_KELIMELER[kalip]["tr"/"en"]`).
    Regex'ler modül seviyesinde BİR KEZ derleniyor (`_DERLENMIS_KALIPLAR`).
  - **Test sonucu:** 7 yanlış eşleşme senaryosunun 6'sı temizlendi,
    10 doğru eşleşme senaryosunun 10'u korundu (Türkçe çekimli haller
    dahil). **"heart attack" hâlâ takılıyor** — orada "attack" gerçekten
    ayrı bir kelime, alt-dize hatası DEĞİL. Bunu kelime listesiyle
    çözmeye çalışma (kara liste yaklaşımı sonsuz kuyruk olur); AI
    doğrulama katmanının elemesi gerekir, zaten görevi bu.
  - **ÇEVİRİ ARTIK VERİTABANI TABANLI VE KENDİNİ ONARIYOR:** v2.0.7.160'ta
    çeviri bellekteki `ceviri_kuyrugu`ndan besleniyordu — o turda Gemini
    çağrısı herhangi bir sebeple başarısız olursa o haberler SONSUZA
    KADAR İngilizce kalıyordu, bir daha hiç denenmiyordu. Artık
    `get_cevrilmemis_haberler()` ile `baslik_tr IS NULL` olan İngilizce
    kaynak satırları okunuyor; kök neden çözülünce birikmiş başlıklar
    sonraki turlarda otomatik çevriliyor.
  - **AÇIK SORUN — ÇEVİRİ NEDEN HİÇ ÇALIŞMADI, HENÜZ BİLİNMİYOR:**
    Bahri 19 Ağustos'ta haberlerin geldiğini ama hiç çevrilmediğini
    bildirdi. Elenen ihtimaller: workflow GEMINI_API_KEY'i geçiriyor
    (yml doğrulandı), `requests`/`json`/`feedparser` importları yerinde,
    zaman aşımı değil (98 haber + 14 eşleşme için kaba hesap ~183 sn,
    limit 600 sn). **Kalan en güçlü ihtimal: Gemini çağrısının kendisi
    başarısız** (anahtar geçersiz, model adı, kota). Aynı çağrı
    `_ai_dogrula`'da da kullanılıyor ve "onay bekleyen tespit: 0" olması
    bu şüpheyi güçlendiriyor. **KESİN CEVAP GITHUB ACTIONS LOGUNDA** —
    v2.0.7.161 ile log çıktısı ayrıştırıcı hale getirildi: artık
    "CEVIRI ATLANDI - GEMINI_API_KEY ... BOS", "CEVIRI ATLANDI - gunluk
    AI butcesi doldu", "Toplu ceviri hatasi: <tip>: <mesaj>" veya
    "N baslik cevrildi" satırlarından hangisinin bastığına bakılmalı.
  - **Haberler sayfası metinleri düzeltildi:** "Piyasa etkisi olası"
    ifadesi yanıltıcıydı (ön-filtreye takılmak bir değerlendirme değil,
    kaba bir elemedir). "Anahtar kelime filtresine takılan haberler"
    olarak değiştirildi, altına bunun bir değerlendirme OLMADIĞI açıkça
    yazıldı.


  Bahri'nin talebi — "durumun stabil olduğunu nasıl görebilirim diye
  düşünürken haber sayfası fikri oluşmaya başladı"): HABERLER SAYFASI.**
  - **MİMARİ DEĞİŞİKLİĞİ:** `haber_izleme.py` önceden ön-filtreye
    takılmayan haberin BAŞLIĞINI ATIYORDU (sadece `haber_islenmis`e URL
    yazıp geçiyordu). Artık taranan HER haber yeni `haber_akisi` tablosuna
    yazılıyor. Sebep: "hiçbir şey olmuyor" bilgisi, "bir şey oldu"
    bildirimi kadar değerli — sistem sessizse bu, sistemin bozuk olduğu
    anlamına gelmemeli.
  - **Bahri'nin üç kararı (19 Ağustos 2026):** (1) sayfa TÜM akışı
    gösterir ama ön-filtreye takılanlar AYRICA ÜSTTE işaretli durur,
    (2) SADECE İngilizce kaynaklar (BBC World, Al Jazeera) çevrilir —
    diğer 3 kaynak (AA Ekonomi, Investing.com TR, BloombergHT) zaten
    Türkçe, (3) el kitapları bu turda GÜNCELLENMEDİ (Bahri "şimdilik
    bırak" dedi — **v2.0.7.158/159/160'ın hiçbiri el kitaplarında yok,
    sonraki bir oturumda eklenmeli**).
  - Yeni tablolar: `haber_akisi` (7 gün saklama, `haber_akisi_temizle`
    her turun sonunda çağrılır), `ai_cagri_butcesi` (günlük Gemini
    çağrı sayacı).
  - Menüde "Haberler" **Makro Göstergeler ile Yardım arasına** kondu.
    **DİKKAT:** sidebar navigasyonu `PAGES[:-1] + [el_kitabi_etiketi]`
    şeklinde kuruluyor — yani `PAGES`'in SON elemanı HER ZAMAN "Yardım"
    olmak zorunda. Yeni sayfa eklerken sondan bir önceye ekle, sona DEĞİL.
  - **GEMINI KOTASI ARTIK VARSAYILMIYOR (önemli düzeltme):**
    `haber_izleme.py`'de "günde 250-500 istek ücretsiz limit" yazıyordu —
    bu DOĞRULANMAMIŞ bir iddiaydı, kaldırıldı. 19 Ağustos 2026 araştırması:
    üçüncü taraf kaynaklar `gemini-2.5-flash` için günlük 20 / 50 / 250 /
    500 / 1500 gibi BİRBİRİYLE ÇELİŞEN rakamlar veriyor ve Aralık 2025'te
    limitin bir kez düşürüldüğü bildiriliyor. **Gerçek limit bilinmiyor.**
    Bu yüzden kod kendi sayacını tutuyor: `_GUNLUK_AI_BUTCESI = 120`
    (doğrulama dahil toplam tavan), `_CEVIRI_ONCELIK_ESIGI = 100`
    (bu aşılınca ÇEVİRİ durur, DOĞRULAMA devam eder — çeviri kozmetik,
    tespit sistemin asıl işi). Bütçe dolunca haberler orijinal başlıkla
    görünür, hiçbir şey çökmez. **Bu iki sayı gerçek limit öğrenilince
    güncellenmeli.**
  - **Çeviri TOPLU yapılıyor, başlık başına DEĞİL:** bir turdaki tüm yeni
    İngilizce başlıklar tek Gemini isteğine numaralı liste olarak gidiyor
    (40'lık parçalar halinde). Başlık başına ayrı istek atmak 10 dakikada
    bir çalışan bir script için kotayı hızla tüketirdi.
    Eşleştirme POZİSYONA değil NUMARAYA göre — AI bazı satırları atlarsa
    kayma olmaz, çevrilemeyen başlık orijinal haliyle kalır (test edildi).
  - **BİLİNEN YÜK ARTIŞI (henüz sorun değil, ama izle):** artık her yeni
    haber için `haber_akisi_ekle` + `haber_islendi_isaretle` = tur başına
    2 ayrı Supabase bağlantısı/haber. İlk turda ~150 yeni haber olacağı
    için o tur uzun sürebilir; sonraki turlarda çoğu haber zaten işlenmiş
    olduğu için yeni kayıt sayısı düşük kalır. **Yavaşlık şikayeti gelirse
    bağlantı havuzu ÖNERME — v2.0.7.142'de denendi, iki farklı çöküşe yol
    açtı, geri alındı.** Bunun yerine toplu INSERT (tek çağrıda çok satır)
    düşünülebilir.


  Bahri'nin talebi — "bir mesaj kutusunun çıkmasını tercih ederim,
  mobildeki uygulamayı da düşünmek lazım"): Onay bekleyen otomatik
  tespitler artık MODAL KUTU (`st.dialog`) ile sunuluyor.**
  - Modal, HANGİ SAYFADA olunursa olsun açılır (sadece Ana Sayfa değil) —
    son dakika haberi zaman hassasiyetli. Ana Sayfa'daki liste yerinde
    kalıyor (geçmişe/ertelenene dönmek için).
  - İçerik: AI'nin ürettiği doğal cümle + "Onaylıyor musunuz?" + ONAYLANIRSA
    hangi kategoriye kaç puan gideceğinin ÖNİZLEMESİ + kalıp/şiddet/48 saat
    bilgisi + kaynak bağlantısı + Onayla / Reddet / Daha sonra bak.
  - **`requirements.txt`: `streamlit>=1.35.0` → `>=1.37.0`.** Sebep:
    `st.dialog` 1.37.0'da genel kullanıma açıldı. app.py ayrıca
    `hasattr(st, "dialog")` ile korunuyor — eski bir sürüme düşülürse
    modal atlanır, uygulama ÇÖKMEZ, Ana Sayfa listesi çalışmaya devam eder.
  - **Streamlit'in üç kısıtı, tasarım bunlara göre yapıldı:**
    1. Bir script çalışmasında SADECE TEK dialog açılabilir → tespitler
       sırayla gösteriliyor (en yenisi ilk, `ORDER BY tespit_zamani DESC`),
       başlıkta "1 / N" sayacı, Onayla/Reddet sonrası `st.rerun()` ile
       bir sonraki açılıyor.
    2. Modal X/ESC/dışarı tıklama ile kapatılabilir, ama bir sonraki
       rerun'da geri gelir. Uygulamada 5 dakikada bir sessiz autorefresh
       olduğu için önlem alınmasa modal kullanıcının önüne tekrar tekrar
       düşerdi → **"Daha sonra bak"** düğmesi `tespit_modal_ertelendi`
       session key'ini set edip modalı O OTURUM boyunca susturuyor
       (tespit SİLİNMEZ, üstteki uyarı şeridi ve Ana Sayfa listesi kalır).
    3. `st.dialog` içinde `st.sidebar` çağrılamaz (kullanılmadı).
  - **KAYAN NOKTA TUZAĞI (test sırasında yakalandı, bir daha düşme):**
    Modaldaki puan önizlemesi ile df_uni'ye uygulanan asıl hesap AYNI
    çarpanları kullanmalı VE AYNI ÇARPIM SIRASINDA olmalı. İlk yazımda
    önizleme `(puan × şiddet) × risk`, asıl blok `puan × (şiddet × risk)`
    sırasındaydı — 90 kalıp/şiddet/risk kombinasyonunun **16'sında** bit
    düzeyinde farklı sonuç veriyordu (ekranda tek ondalıkla yuvarlandığı
    için görünmezdi ama kullanıcıya gösterilen sayı ile uygulanan sayı
    teknik olarak farklıydı). Düzeltildi: her iki taraf da önce
    `carpan = şiddet × risk` hesaplayıp sonra puanla çarpıyor —
    90/90 kombinasyon birebir aynı. **Bu iki yeri değiştirirken
    HER ZAMAN ikisini birlikte güncelle.**


  Bahri'nin kararı — "zaten son dakika haberini alıp istatistiksel verilere
  göre hesaplayıp onaya sunuyoruz, bunlara gerek kalmadı ki"): Sidebar'daki
  "Beklenti Modu" bölümü TAMAMEN KALDIRILDI.**
  - Kaldırılanlar: `Beklenti Modunu Aktif Et` anahtarı (`beklenti_aktif`
    session key), 6 kalıbın elle işaretlendiği checkbox'lar (`bk_*`),
    her kalıbın altındaki Şiddet kaydırıcısı (`bk_*_siddet`), ve artık
    okunmayan `_beklenti_kaynak` sözlüğü.
  - **KAldırılmayan (ASLA KALDIRMA): `_KALIP_TABLOSU` / `_KALIP_ISIM` /
    `_KALIP_ACIKLAMA`.** Bunlar arayüz değil, SİSTEMİN MOTORUDUR —
    `haber_izleme.py` gelen haberi tam olarak bu 6 kalıptan birine eşler
    (`_KALIP_KATEGORI_YONU` ile birlikte), hangi kategorinin kaç puan
    etkileneceği `_KALIP_TABLOSU`'ndan gelir. Sidebar gitti diye bunları
    silmeye kalkma, otomatik sistem tamamen işlevsiz kalır.
  - **BU DEĞİŞİKLİĞİN ASIL SEBEBİ OLAN GİZLİ HATA:** Onaylanmış tespitleri
    okuyup uygulayan blok (`get_onaylanmis_tespitler()` + skor ayarlaması)
    `if st.session_state.get("beklenti_aktif"):` içindeydi. Yani anahtar
    KAPALIYKEN (varsayılan) kullanıcı bir tespiti Onayla'sa bile Optima
    Skor'a HİÇ uygulanmıyordu — sessiz işlevsizlik. Sidebar kaldırılırken
    bu kapı da kaldırıldı: **onaylanan tespitler artık HER ZAMAN uygulanır.**
  - Yeni kontrol modeli: tek kontrol ONAY/RED kararının kendisi. Uygulamayı
    durdurmanın yolları: (1) tespiti Reddet, (2) hiçbir şey yapma —
    onaylananlar 48 saat sonra `gecerlilik_bitis` ile kendiliğinden düşer.
  - Metin güncellemeleri: üst şerit artık "Onayladığınız tespitler
    uygulanıyor", Ana Sayfa bölüm başlığı "Onayladığınız Tespitler ve
    Gerekçeleri", log satırından kaynak etiketi ("manuel"/"otomatik")
    çıkarıldı (tek tür kaldı).
  - **Emoji temizliği (kalıcı kural ihlali düzeltildi):** v2.0.7.154-157
    ile eklenen 6 emoji kaldırıldı — bildirimdeki zil, Onayla/Reddet
    düğmelerindeki tik/çarpı, doğal cümle önündeki konuşma balonu, kaynak
    etiketlerindeki kişi/robot işaretleri.
  - **YAN ETKİ — TEST YOLU DEĞİŞTİ:** Beklenti Modu'nu elle işaretleyerek
    test etmek ARTIK MÜMKÜN DEĞİL. Skor ayarlamasını test etmek için ya
    gerçek bir haber tespiti beklenmeli ya da Supabase'deki tespit tablosuna
    elle bir satır eklenip onaylanmalı.

### 🔴 OTURUM DEVİR ÖZETİ (19 Ağustos 2026, sohbet görsel kapasitesi doldu — YENİ SOHBETE BAŞLARKEN ÖNCE BURAYI OKU)

**Son doğrulanmış canlı durum:** `v2.0.7.157`, commit `46fe734`,
GitHub'da doğrulandı (taze klon + `py_compile` ile). Bu, bugünkü (18-19
Ağustos) maraton oturumun SONUNDAKİ commit — birçok özellik art arda
eklendi, çoğu **KOD OLARAK doğru derleniyor ve mantık mock veriyle test
edildi, AMA HİÇBİRİ CANLI ORTAMDA (gerçek Streamlit Cloud üzerinde,
gerçek kullanıcı etkileşimiyle) DOĞRULANMADI.**

**Bu oturumda eklenen/değişen ana özellikler (hepsi teorik olarak
tamam, canlı doğrulama BEKLİYOR):**
1. **Getiri Kıyaslaması + Pozisyon Bazlı grafik** (Portföyüm) - renkler,
   hover, grafik matematiği düzeltildi.
2. **scoring.py birleştirmesi** - TUPRS tutarsızlığı kök nedenine kadar
   izlenip düzeltildi (worker.py'nin Hacim/Düşüş düzeltmesi keşfi dahil).
3. **Fırsat Radarı overlay tek kaynağa taşındı** (`db.get_intraday_overlay`).
4. **Supabase bağlantı havuzu eklendi, SONRA tamamen GERİ ALINDI**
   (iki farklı çöküş türüne yol açtı - v2.0.7.142, basit yönteme dönüldü).
5. **Optima Skor Bileşimi pasta grafikleri** (Ana Sayfa - Kategori
   Dağılımı yanında, tıklamasız; tekil varlık versiyonu KALDIRILDI).
6. **Üst boşluk + sidebar aralık düzeltmeleri** (CSS).
7. **"Beklenti Modu"** - EN BÜYÜK ve EN KARMAŞIK yeni özellik:
   - 6 kalıp (jeopolitik/petrol/fed/kredi_notu/kripto_olay/tcmb_kredibilite),
     hepsi çok-olaylı akademik çalışmalara dayalı, istatistiksel ifadeli
     (tekil tarih referansı YOK, Bahri'nin talebiyle kaldırıldı).
   - Sidebar'da manuel işaretleme + GitHub Actions'ta 10 dk'da bir
     çalışan `haber_izleme.py` (5 RSS kaynağı + anahtar kelime ön-filtre
     + Google Gemini API doğrulama - ÜCRETSİZ katman, GEMINI_API_KEY
     zaten Bahri tarafından eklendi).
   - **KRİTİK tasarım düzeltmesi (v2.0.7.156):** "hemen otomatik uygula"
     YANLIŞ anlaşılmıştı - gerçek istenen akış ONAY BEKLEME: sistem
     tespit eder → kullanıcıya DOĞAL bir cümleyle gösterir ("[Kaynak]'a
     göre..., bu durumda...Optima Skorlarını artırmamız/azaltmamız
     gerekir. Onaylıyor musunuz?") → SADECE onaylanırsa uygulanır.
   - Ayarlama GLOBAL olarak uygulanıyor (df_uni yüklendikten hemen sonra,
     TÜM sayfalardan önce) - önceki "sadece Ana Sayfa'da" tutarsızlığı
     yapısal olarak imkansız hale getirildi.

**Bir sonraki oturumda İLK yapılması gerekenler (öncelik sırasıyla):**
1. **Uygulamanın genel olarak hâlâ çalıştığını doğrula** (BIST/Portföyüm/
   Ana Sayfa gibi birkaç sayfaya gidip çökme olmadığını kontrol et) -
   bu kadar çok değişiklikten sonra bu ilk kontrol.
2. **Beklenti Modu'nun onay akışını gerçek bir senaryoda test et** -
   sidebar'dan bir kalıbı elle işaretleyip Optima Skor'un GERÇEKTEN
   TÜM sayfalarda tutarlı değiştiğini doğrula.
3. **haber_izleme.py'nin GitHub Actions'ta gerçekten çalışıp
   çalışmadığını kontrol et** (Actions sekmesi → "Beklenti Modu Haber
   Izleme" → loglar) - bekleyen bir tespit oluşup oluşmadığına bak.
4. Eğer performans/yavaşlık şikayeti tekrar gelirse: bu oturumda EKLENEN
   özelliklerin (özellikle Beklenti Modu'nun her sayfa yüklemesinde
   yaptığı ekstra DB sorguları - `get_bekleyen_tespitler`/
   `get_onaylanmis_tespitler`) payı olup olmadığı ayrıca değerlendirilmeli
   - bağlantı havuzu denemesinin NEDEN geri alındığını (yukarıdaki not)
   unutma, aynı hataya düşme.

- **[ÇÖZÜLDÜ - 19 Ağustos 2026, taze klonla doğrulandı] Aşağıdaki
  "push edilmemiş" uyarısı ARTIK GEÇERSİZDİR.** GitHub'daki son commit
  `ffeab17`; `46fe734` (v2.0.7.156+157) ve `e1f6a17` (v2.0.7.155)
  ikisi de canlıda, `py_compile` ile doğrulandı. Madde, tarihsel bağlam
  için aşağıda korunuyor ama BİR EYLEM GEREKTİRMİYOR — tekrar push
  etmeye kalkma.

- **[TARİHSEL - ARTIK GEÇERSİZ, YUKARIYA BAK] v2.0.7.156 hâlâ GitHub'a hiç
  push edilmedi (19 Ağustos 2026 itibarıyla doğrulandı) - bu turda
  v2.0.7.157 üzerine inşa edildiği için ikisi BİRLİKTE push
  edilmeli.** GitHub'daki son commit hâlâ v2.0.7.155 (Gemini geçişi).
  Bir önceki mesajda verilen db.py/app.py/haber_izleme.py dosyaları
  (onay bekleme akışı) hiç Git'e gitmemiş - bu oturumdaki
  v2.0.7.157 değişiklikleri o (henüz push edilmemiş) temel üzerine
  inşa edildi. **Push sırası önemli değil çünkü tek bir pakette
  gönderiliyor, ama BU ÜÇ DOSYANIN TAMAMI push edilmeden hiçbiri
  çalışmaz.**

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.157 (18 Ağustos 2026, Bahri'nin
  talebi): Otomatik tespitler artık DOĞAL, AKICI bir Türkçe cümleyle
  sunuluyor - "Onaylıyor musunuz?" ile bitiyor.** Örnek istenen format:
  "XXX haber kaynağından aldığım son dakika haberine göre, XXX Merkez
  bankası politika faizini 25 puan yükseltmiş, bu durumda XXX
  varlıklarının optima skorlarını arttırmamız gerekir, Onaylıyor
  musun?" Uygulama:
  - `haber_izleme.py`'ye `_KALIP_KATEGORI_YONU` eklendi (her kalıbın
    hangi kategoriyi hangi yönde etkilediği - MADEN/DOVIZ/BIST/KRIPTO,
    artış/azalış) - bu bilgi Gemini'ye prompt içinde veriliyor, AI'nin
    kategori isimlerini KENDİ UYDURMASI değil, bizim tanımladığımız
    gerçek kategorilerden seçmesi sağlanıyor.
  - Gemini prompt'u artık `gerekce` alanında TAM OLARAK şu kalıpta bir
    cümle istiyor: "[Kaynak]'a göre, [haberin somut/sayısal detayı -
    varsa], bu durumda [kategori(ler)]'in Optima Skorlarını
    [artırmamız/azaltmamız] gerekir." Haberde sayı yoksa AI'nin sayı
    UYDURMAMASI özellikle belirtildi.
  - `app.py`'nin onay-bekleyen gösterim bloğu bu cümleyi ARTIK teknik
    bir "AI gerekçesi:" alt-etiketi arkasına gizlemiyor - doğrudan ana
    mesaj olarak gösterip sonuna **"Onaylıyor musunuz?"** ekliyor,
    hemen altında Onayla/Reddet düğmeleri.
  **DOĞRULANDI (mock veriyle):** örnek senaryo (Fed 25 baz puan) tam
  istenen formatta üretiliyor.
  **DOĞRULANMAMIŞ** (canlı test gerekiyor - GEMINI_API_KEY zaten ekli
  olduğu için, push sonrası bir sonraki gerçek haber taramasında
  bu formatın doğru üretildiği kontrol edilmeli).

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.155 (18 Ağustos 2026, Bahri'nin
  talebi — "ücretli ise kurmayacağım, ücretsiz alternatif bulalım"):
  AI doğrulama katmanı Anthropic API'den Google Gemini API'ye çevrildi.**
  Google Gemini API'nin kredi kartı GEREKTİRMEYEN gerçek bir ücretsiz
  katmanı olduğu doğrulandı (Ağustos 2026 itibarıyla, `gemini-2.5-flash`
  modeli günde 250-500 istek civarı ücretsiz limit - 10 dakikada bir
  çalışan, çoğu turda hiç AI çağrısı yapmayan bu script için fazlasıyla
  yeterli). `haber_izleme.py`'nin `_ai_dogrula()` fonksiyonu artık
  Anthropic SDK yerine doğrudan `requests` ile Gemini'nin REST
  endpoint'ini çağırıyor (`generativelanguage.googleapis.com`,
  `x-goog-api-key` header) - EKSTRA BİR SDK BAĞIMLILIĞI GEREKMİYOR
  (`requests` zaten projede mevcut). requirements.txt'den `anthropic`
  kaldırıldı, `.github/workflows/haber_izleme.yml` artık
  `GEMINI_API_KEY` bekliyor (ANTHROPIC_API_KEY değil).
  **Canlı test edildi (sahte anahtarla):** endpoint gerçekten yanıt
  veriyor ("API key not valid" - beklenen, doğru hata), kod bu hatayı
  güvenli şekilde yakalayıp False döndürüyor (çökme yok).
  **Bahri'nin push sonrası yapması gereken:** `aistudio.google.com`
  adresinden (Google hesabıyla, kredi kartsız) bir API anahtarı alıp
  GitHub Secrets'a `GEMINI_API_KEY` adıyla eklemesi gerekiyor - ESKİ
  `ANTHROPIC_API_KEY` secret'ı varsa silinebilir (artık kullanılmıyor).
  **DOĞRULANMAMIŞ** (gerçek bir API anahtarıyla uçtan uca test
  gerekiyor - bu ortamda gerçek bir Gemini anahtarı yok, sadece
  istek formatının doğruluğu ve hata yönetiminin güvenli olduğu
  doğrulandı).

- **[UYGULANDI, TEST EDİLMEDİ, YENİ ALTYAPI GEREKTİRİYOR] v2.0.7.154
  (18 Ağustos 2026, Bahri'nin talebi): Beklenti Modu'nun OTOMATİK haber
  izleme katmanı ilk kez inşa edildi.** Bahri'nin seçimleri: (1) haber
  sınıflandırması "anahtar kelime ön-filtre + AI doğrulama" karışımı,
  (2) doğrulanan tespitler ONAY BEKLENMEDEN hemen otomatik uygulanır.
  **Mimari:**
  1. **`haber_izleme.py`** (yeni, standalone script) - 5 GERÇEK, TEST
     EDİLMİŞ RSS kaynağını (AA Ekonomi, BBC World, Al Jazeera,
     Investing.com TR, BloombergHT - hepsi doğrudan curl ile HTTP 200
     doğrulandı) okur, 6 kalıp için anahtar kelime ön-filtresi uygular,
     eşleşenleri Claude API (Sonnet) ile doğrular ("gerçekten önemli mi,
     hangi şiddette - şüphede kal, false de"), doğrulananları
     Supabase'e yazar. **Canlı test edildi:** gerçek RSS'lerden BBC'nin
     "Russia's drone warning" haberini doğru şekilde jeopolitik olarak
     yakaladı; Al Jazeera'nın "Brezilya'da petrol keşfi" haberi anahtar
     kelime ile yanlışlıkla eşleşti (bu TAM OLARAK AI doğrulama adımının
     var olma sebebi - yeni keşif, arz şoku DEĞİL, AI bunu reddetmeli).
  2. **`db.py`** - iki yeni tablo: `beklenti_otomatik_tespit` (tespitler,
     geçerlilik süresi 48 saat varsayılan, kullanıcı iptal bayrağı) ve
     `haber_islenmis` (aynı haberi tekrar işlememe için dedup).
  3. **`.github/workflows/haber_izleme.yml`** - 10 dk'da bir (GitHub'ın
     kendi cron'u best-effort yedek - firsat_radari.yml/send_email.yml
     ile AYNI kısıt, güvenilir zamanlama için cron-job.org harici
     tetikleyicisi KURULMASI ÖNERİLİR ama bu oturumda kurulmadı).
  4. **`app.py`** - manuel (sidebar) seçimler + otomatik tespitler
     BİRLEŞTİRİLİYOR (aynı kalıp için ikisi de varsa YÜKSEK şiddet
     kazanır, mock veriyle doğrulandı). Ana Sayfa'da her otomatik
     tespit için haber linki + AI gerekçesi + **"İptal Et"** butonu -
     "hemen otomatik uygula" ile ÇELİŞMEZ, bu UYGULANDIKTAN SONRA
     düzeltme mekanizmasıdır.
  **KRİTİK - Bahri'nin yapması gerekenler (push'tan SONRA):**
  1. GitHub Secrets'a `ANTHROPIC_API_KEY` eklenmesi gerekiyor (Claude
     API için - EVDS_API_KEY ile AYNI yerde, repo Settings > Secrets >
     Actions). Bu OLMADAN AI doğrulama adımı çalışmaz (sessizce
     `eslesme=False` döner, hiçbir tespit Supabase'e yazılmaz - güvenli
     taraf, ama özellik de çalışmaz).
  2. requirements.txt'ye `feedparser` ve `anthropic` eklendi - Streamlit
     Cloud'un bunları kurması gerekiyor (otomatik olmalı, ama ilk
     deploy'da biraz gecikme olabilir).
  3. (Önerilir, opsiyonel) cron-job.org ile 10 dk'lık güvenilir dış
     tetikleyici kurulması - firsat_radari için zaten yapılmış olan AYNI
     yöntem.
  **AÇIKÇA ERTELENEN (Bahri'nin verdiği örnekler, ayrı bir iş kalemi
  olarak not edildi, henüz kod yazılmadı):**
  - ENAG/TÜİK enflasyon verisi güvenilirlik farkı - bu bir "olay kalıbı"
    değil, veri KALİTESİ meselesi, ayrı ele alınmalı.
  - Sanayi göçü (tekstilin Mısır'a taşınması gibi) - yavaş, yapısal bir
    trend, anlık haber tepkisiyle YAKALANAMAZ, temel analiz (F/K,PD/DD)
    göstergeleriyle ilişkilendirilmeli.
  **DOĞRULANMADI** (canlı test gerekiyor - özellikle ANTHROPIC_API_KEY
  eklendikten sonra gerçek bir AI doğrulama döngüsünün çalıştığı
  kontrol edilmeli).

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.152 (18 Ağustos 2026, Bahri'nin
  talebi — iki yönlü genişletme, derinlemesine araştırma sonrası).**
  (1) **Tekil tarihli referans olaylar KALDIRILDI.** Bahri haklı olarak
  "13 sene önceki bir olayı bugüne örnek göstermek anlamsız" dedi - tek
  bir olay istatistik değil, anekdottur. `_KALIP_REFERANS_OLAY` sözlüğü
  tamamen silindi. Açıklamalar artık DOĞRUDAN istatistiksel ifadeyle
  yazılı ("İstatistiksel dayanak: ... çok sayıda olay/onlarca yıl
  kapsayan akademik panel/olay çalışması...") - tarih anmıyor.
  (2) **Sadece 3 kalıp yetersizdi - araştırma genişletildi, İKİ yeni
  kalıp eklendi (artık 5 kalıp):**
  - **Kredi notu düşürülmesi (S&P/Moody's/Fitch):** 1990-2016 dönemini
    kapsayan, çok sayıda gelişen piyasayı içeren akademik panel çalışması
    - kredi notu düşürülmelerinin hem borsa hem para birimi üzerinde
    istatistiksel olarak anlamlı olumsuz etkisi, asimetrik (düşürmeler
    artırmalardan güçlü). DOVIZ+5/BIST−7.
  - **Kripto düzenleme/halving şoku:** çok sayıda kripto parada (2014-2023,
    halving yaşayan TÜM varlıklar) yapılan akademik olay çalışması,
    olay penceresinde ORTALAMA anormal getirinin istatistiksel olarak
    anlamlı NEGATİF (~-%7,6) olduğunu buluyor - popüler "halving=yükseliş"
    anlatısının AKSİNE (bu kısa vadeli tepki; uzun vadeli "boğa piyasası"
    anlatısı ayrı, çok daha küçük örneklemli - Bitcoin için sadece 4
    halving - ve literatürde tartışmalı, bilinçli olarak KULLANILMADI).
    KRIPTO−8. **KRIPTO kategorisi ilk kez Beklenti Modu kapsamına girdi**
    (önceden hiç kapsanmıyordu).
  Sidebar döngüsü, global uygulama döngüsü, üst şerit bildirimi ve Ana
  Sayfa gerekçe bölümü hepsi `_KALIP_TABLOSU`/`_KALIP_ISIM` üzerinden
  GENEL (hardcoded olmayan) şekilde çalışacak hale getirildi - gelecekte
  yeni bir kalıp eklemek tek bir yerde (üç sözlük) tanımlamak yeterli.
  **DOĞRULANDI (mock veriyle):** 5 kalıbın hepsi + KRIPTO kategorisi
  doğru hesaplanıyor.
  **DOĞRULANMADI** (canlı test gerekiyor).

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.150 (18 Ağustos 2026, Bahri'nin
  bulgusu — "Ort. Optima Skor yine de eskide kalmış"): Beklenti Modu
  NaN-güvenli hale getirildi.** Kök neden: birçok varlığın Optima_Skor'u
  henüz NaN'dı (hiç hesaplanmamış), `NaN + puan = NaN` (pandas'ta NaN
  aritmetiği hep NaN verir) - yani ayarlama bu varlıklar için SESSİZCE
  hiç uygulanmıyordu, sayfa kendi "eksik skoru doldur" mantığıyla
  bunları HAM formülle dolduruyordu. En üstte gösterilen (zaten skoru
  olan) birkaç varlık doğru ayarlanmış görünürken, ortalamayı oluşturan
  çoğu varlık ayarlamayı hiç almıyordu. **Düzeltme:** ayarlama
  uygulanmadan ÖNCE, etkilenen kategorilerdeki TÜM eksik (NaN)
  Optima_Skor'lar önce scoring.py ile tam hesaplanıp dolduruluyor -
  ayarlama artık hiçbir varlığı atlamadan uygulanıyor.

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.151 (18 Ağustos 2026, Bahri'nin
  talebi): "Sistem otomatik belirlesin" isteği için GERÇEK EN İYİ
  ÇÖZÜM uygulandı - tam otomatik değil, ama artık gerçek tarihe dayalı.**
  Önceki oturumda akademik regresyon katsayılarının çalışmadan çalışmaya
  çok değiştiği, TEK güvenilir bir sabit sayı olmadığı tespit edilmişti.
  Bunun yerine ÜÇ GERÇEK, DOĞRULANMIŞ tarihsel olay araştırıldı ve şiddet
  seçicisine (hem sidebar'da help/caption, hem Ana Sayfa'daki gerekçe
  bölümünde) somut referans olarak eklendi:
  - **Jeopolitik:** 24 Şubat 2022 Rusya-Ukrayna işgali — ons altın %3-5
    (birkaç gün), BIST100 gün içi -%9,4 (hafta kapanışı sadece -%1).
  - **Petrol:** 14 Eylül 2019 Suudi Aramco (Abqaiq-Khurais) İHA saldırısı
    — Brent petrol gün içi +%19,5 (1991'den beri en sert).
  - **Fed:** Mayıs-Aralık 2013 "Taper Tantrum" — TL %15 değer kaybı
    (akademik kaynak: ScienceDirect, "Emerging market exchange rates
    during quantitative tapering", Türkiye Endonezya'dan sonra en büyük
    kayıp yaşayan ülkeydi).
  Bu, "kullanıcı tamamen keyfi seçiyor" ile "sistem güvenilmez şekilde
  tam otomatik tahmin ediyor" arasındaki en dürüst orta yol - kullanıcı
  hâlâ "bu olay Yüksek mi" kararını veriyor ama artık SOMUT, gerçek bir
  karşılaştırma noktasıyla, keyfi bir etiketle değil.
  **DOĞRULANMADI** (canlı test gerekiyor).

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.149 (18 Ağustos 2026, Bahri'nin
  bulgusu — KRİTİK mimari düzeltme): Beklenti Modu artık gerçekten
  GLOBAL.** Önceki hali SADECE Ana Sayfa'nın kendi bloğu içindeydi -
  df_uni'yi sadece o an render edilen Ana Sayfa'nın yerel akışında
  değiştiriyordu. Başka bir sayfaya (ör. Döviz) geçildiğinde YENİ bir
  script çalışması başlıyor, df_uni tekrar (önbellekten) yükleniyor ve
  Ana Sayfa'daki ayarlama hiç uygulanmıyordu - "Bütçe tablosunda DOVIZ
  skorları artmış ama Döviz sayfasına gidince artmamış" tam olarak bu
  yüzdendi. **Çözüm:** kontroller SIDEBAR'a taşındı (her sayfada
  kalıcı, session_state ile), gerçek AYARLAMA ise `df_uni=load_universe()`
  satırından HEMEN SONRA, TÜM sayfa yönlendirmesinden ÖNCE uygulanıyor -
  artık Ana Sayfa/Döviz/BIST/TEFAS/Maden/Kripto/Portföyüm/Temettü/Halka
  Arz HEPSİ aynı ayarlanmış Optima_Skor'u görüyor, tutarsızlık yapısal
  olarak imkansız hale geldi. Ayrıca TÜM sayfalarda görünen bir üst
  şerit eklendi (Beklenti Modu aktifken hangi kategori ne kadar
  etkilendiğini gösteriyor, sadece Ana Sayfa'da değil).
  **DOĞRULANMADI** (canlı test gerekiyor): push sonrası bir kalıp
  işaretleyip Ana Sayfa'dan Döviz/BIST gibi başka bir sayfaya geçince
  skorların TUTARLI kaldığı kontrol edilmeli.

- **[AÇIK, KAPSAM BÜYÜK] Bahri'nin "sistem otomatik belirlesin" talebi
  (18 Ağustos 2026) — henüz uygulanmadı, dürüstçe ertelendi.** Bahri,
  kullanıcının şiddet seviyesini elle seçmesi yerine, "hangi haber
  hangi varlık çeşidini yüzde kaç etkiler"in SİSTEM tarafından,
  GERÇEK istatistiksel değerlendirmeyle belirlenmesini istiyor - bu,
  şu anki (benim elle seçtiğim sabit puan tablosu + kullanıcının elle
  seçtiği şiddet) tasarımdan ÇOK daha büyük bir kapsam. Gerçek bir
  çözüm ya (a) gerçek tarihsel haber-fiyat tepkisi veri setiyle
  istatistiksel backtesting yapmayı, ya da (b) yayınlanmış akademik
  makalelerin GERÇEK regresyon katsayılarını/elastikiyet tahminlerini
  (kendi uydurduğum sayılar değil) kullanmayı gerektirir - ikisi de
  ciddi, ayrı bir araştırma oturumu gerektiriyor. Bir sonraki oturumda
  ele alınmalı - Bahri'ye bu net şekilde açıklandı, aceleye
  getirilmedi.

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.147 (18 Ağustos 2026, Bahri'nin
  bulgusu): Optima Skor Bileşimi grafiğindeki etiket çakışması
  DEĞERLERDEN BAĞIMSIZ, kalıcı bir sistemle çözüldü.** 6 dilim olunca
  (RSI/Momentum/Volatilite/F/K/PD/DD/Temettü) komşu küçük dilimlerin
  etiketleri üst üste biniyordu. İki ayrı düzeltme: (1) sıfıra
  yuvarlanan bileşenler (ör. "Temettü Verimi %0,0") artık grafiğe hiç
  dahil edilmiyor - sıfır genişlikte dilim, komşusuyla aynı noktada
  çakışma yaratıyordu (%100 tek dilim hatasıyla AYNI kök sınıf).
  (2) Açıya göre sıralanmış etiketler arasında 28°'den dar boşluk varsa
  o etiket bir sonraki (daha uzak) yarıçap kademesine itiliyor - kaç
  dilim/hangi değerler olursa olsun otomatik uyum sağlıyor (mock veriyle
  doğrulandı: PD/DD ve F/K arasındaki 24° boşluk doğru tespit edilip
  ayrıştırıldı). Uzak kademedeki etiketler için dilime geri bağlayan
  ince bir çizgi eklendi. Ayrıca `_3d_pasta_svg()`'ye `baslangic_aci`
  parametresi eklendi - Optima Skor Bileşimi grafiği artık 90° farklı
  bir açıdan başlıyor (Bahri'nin "90° sola çevirelim" talebi).

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.148 (18 Ağustos 2026, Bahri'nin
  talebi): "Beklenti Modu" ilk kez inşa edildi ve aktif hale getirildi.**
  Ana Sayfa'da yeni bir expander: varsayılan KAPALI (uygulama hiç
  değişmez). Açılınca kullanıcı 3 kalıptan (Jeopolitik gerilim/çatışma,
  Petrol arz şoku, Merkez bankası şahin sürprizi) hangilerinin şu an
  aktif olduğunu + şiddetini (Düşük/Orta/Yüksek) elle işaretler -
  **hiçbir otomatik haber sınıflandırma/AI YOK**, karar tamamen
  kullanıcıda. İşaretlenen kalıplara göre `df_uni`'nin Optima_Skor'u
  (MADEN/DOVIZ/BIST kategorilerinde), kullanıcının Risk Toleransı
  kaydırıcısıyla ORANTILI olarak ayarlanıyor - bu ayarlama `cat_pools`
  oluşturulmadan ÖNCE uygulanıyor, böylece mevcut filtreleme/seçim
  mantığına hiç dokunulmadan doğal olarak akıyor. Ayarlama HER ZAMAN
  şeffaf gösteriliyor (st.warning ile tam puan dökümü) - hiçbir gizli
  etki yok. Pasta grafiklerinin ALTINDA, aktif kalıpların akademik
  kaynaklı gerekçe açıklamaları gösteriliyor (Bahri'nin "pie chart'ın
  altında haber ve açıklamalar" talebi).
  **DOVİZ yönü dikkatle düşünüldü:** TL zayıflarsa USDTRY/EURTRY FİYATI
  YÜKSELİR (DOVIZ varlığının kendisi bu fiyattır) - yani "TL zayıflar"
  senaryosunda DOVIZ skoru artırılıyor (azaltılmıyor) - ilk mesajdaki
  hatalı yönlendirmenin (kendi hayali örneğimdeki gibi) tekrarlanmaması
  için özellikle kontrol edildi.
  **Kalıp puan tablosu (Orta şiddet, Risk=Orta taban değerler):**
  Jeopolitik: MADEN+8/DOVIZ+6/BIST−6; Petrol: MADEN+3/DOVIZ+5/BIST−3;
  Fed şahin: MADEN−5/DOVIZ+6/BIST−5. Mock veriyle doğrulandı (Yüksek
  şiddet + Yüksek risk ≈ 1,95x taban değer).
  **DOĞRULANMADI** (canlı test gerekiyor): push sonrası Beklenti
  Modu'nun açılıp kapanabildiği, işaretlenen kalıplara göre önerilerin
  gerçekten değiştiği ve açıklamaların doğru göründüğü kontrol
  edilmeli.

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.146 (18 Ağustos 2026, Bahri'nin
  ikinci bulgusu — "devasa boşluk" hâlâ duruyordu): kök neden nihayet
  bulundu.** Streamlit'in KENDİ varsayılan `.block-container` üst dolgusu
  (araç çubuğuyla çakışmasın diye tasarımda bırakılan geniş bir değer)
  şimdiye kadar hiç küçültülmemişti - sadece mobil breakpoint'te
  küçültülüyordu, masaüstü/geniş görünümde Streamlit'in varsayılanı aynen
  kalıyordu. Bu CSS GLOBAL olduğu için "her sayfada var" şikayeti tam
  buradan kaynaklanıyordu. `.block-container{padding-top:2rem!important;}`
  eklendi (masaüstü için, mobil kural zaten kendi değerini eziyor).
  **DOĞRULANMADI** - tam değer (2rem) Streamlit'in gerçek varsayılanına
  bağlı, canlıda ince ayar gerekebilir.

  **Ayrıca aynı oturumda: Optima Skor Bileşimi artık Ana Sayfa'da,
  TIKLAMA GEREKTİRMEDEN, Kategori Dağılımı'nın yanında.** Önceki
  (v2.0.7.144) pasta grafiği SADECE bir varlığa tıklanınca (Detay
  sayfasında) görünüyordu - Bahri bunun yerine (ya da buna ek olarak)
  Ana Sayfa'da, önerilen SEPETTEKİ TÜM varlıkların Tutar'a göre
  AĞIRLIKLI ORTALAMA skor bileşimini, hiçbir tıklama olmadan, Kategori
  Dağılımı ile yan yana istedi - "neden bu sepeti önerdik" sorusunun
  toplu/özet cevabı. Uygulandı: `_3d_pasta_svg()`'ye `baslik` parametresi
  eklendi (önceden "Kategori Dağılımı" hardcoded'du, artık iki farklı
  başlıkla yeniden kullanılabiliyor - tek fonksiyon, iki grafik, kod
  tekrarı yok). `st.columns(2)` ile iki grafik yan yana. Mock veriyle
  ağırlıklı ortalama mantığı doğrulandı.
  **NOT:** bu, Detay sayfalarındaki (v2.0.7.144, Plotly tabanlı) TEK
  VARLIK breakdown'ını KALDIRMADI, sadece Ana Sayfa'ya AYRI, TOPLU bir
  görünüm ekledi - ikisi farklı amaçlara hizmet ediyor (biri "bu tek
  hisse neden böyle skorlandı", diğeri "genel olarak bu sepeti neden
  önerdik"). Bahri Detay sayfasındaki Plotly versiyonunu da Kategori
  Dağılımı'nın 3D SVG tarzına çevirmek isterse ayrı bir iş.
  **DOĞRULANMADI** (canlı test gerekiyor).

- **[UYGULANDI] v2.0.7.145 (18 Ağustos 2026, Bahri'nin bulgusu — "Kategori
  Dağılımı" pasta grafiği görünmüyor, sadece "TEFAS %100,0" yazısı
  görünüyor).** Bu, önceden var olan (bugünkü çalışmayla ilgisiz) elle
  yazılmış bir SVG pasta grafiğiydi (Plotly değil) - bugüne kadar hiç
  ortaya çıkmamış bir kenar durum hatasıydı çünkü portföy ilk kez tek bir
  kategoriden (%100 TEFAS) oluştu. **Kesin kanıtlanmış kök neden:** kod,
  SVG koordinatlarını `.2f` (2 ondalık) ile string'e yazıyor - %100 tek
  dilimde başlangıç açısı (-90°) ile bitiş açısı (270°) matematiksel
  olarak AYNI noktaya denk geliyor, ve 2 ondalığa yuvarlanınca bu iki
  nokta BİREBİR AYNI STRING'e dönüşüyor ("294.00,71.75" ==
  "294.00,71.75"). SVG standardına göre bir yayın başlangıç/bitiş
  noktaları aynıysa o yay tamamen atlanır (görünmez olur) - sadece
  `<text>` etiketleri (başlık, kategori adı, yüzde) kalır, tam
  görülen davranış. **Doğrulama (Python ile birebir simülasyon):**
  düzeltme öncesi iki nokta `.2f` sonrası "294.00,71.75" / "294.00,71.75"
  (AYNI) - düzeltme sonrası "294.00,71.75" / "293.97,71.75" (FARKLI).
  **Düzeltme:** herhangi bir dilimin açısal genişliği artık 359,99°'yi
  geçemiyor - matematiksel olarak görünmez bir fark ama SVG'nin "aynı
  nokta" kenar durumunu kesinlikle önlüyor.
  **DOĞRULANMADI** (canlı test gerekiyor): push sonrası tek-kategori
  (%100 TEFAS gibi) durumunda pasta diliminin artık gerçekten göründüğü
  kontrol edilmeli.

- **[NOT - "Beklenti Modu" tasarımı netleşti] Bahri'nin ek detayları
  (18 Ağustos 2026):** "Beklenti Modu" bir buton/anahtar ile devreye
  girecek; devreye girdiğinde Optima Skor Bileşimi pasta grafiğinin
  ALTINDA ilgili haberler/açıklamalar gösterilecek ("bu nedenle
  dağılım şöyle olacaktır" formatında); kullanıcının risk toleransı
  (Ana Sayfa'daki mevcut "Risk Toleransı" kaydırıcısı) ile orantılı
  olarak skor ayarlamasının büyüklüğü de artırılabilir/azaltılabilir.
  Henüz kod yazılmadı - v2.0.7.132'deki akademik kalıp araştırmasıyla
  birlikte bir sonraki oturumda ele alınacak.

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.144 (18 Ağustos 2026, Bahri'nin
  talebi): Optima Skor Bileşimi pasta grafiği — her varlığın Detay
  sayfasının en başına eklendi.**
  **Mimari:** `scoring.py`'ye `optima_score_breakdown()` eklendi -
  `optima_score()` ile TAMAMEN AYNI hesaplamayı yapar (aynı eşik
  değerleri, `_teknik_alt_skor_ayristirilmis`/`_temel_alt_skor_ayristirilmis`
  üzerinden) ama tek bir sayı yerine her bileşeni (RSI Bölgesi, Momentum,
  Volatilite + varsa F/K, PD/DD, Temettü Verimi) AYRI AYRI döndürür -
  toplamı her zaman gösterilen Optima Skor'a eşittir (mock veriyle
  doğrulandı: TUPRS örneğinde breakdown toplamı 63 = optima_score() 63).
  `app.py`'de tek, paylaşılan `_render_skor_pasta_grafigi(d, row,
  key_prefix)` fonksiyonu - Ana Sayfa, Portföyüm ve genel Kategori
  sayfası Detay bloklarının ÜÇÜNDE de (tek kaynak, üç kopya yok) 5
  metrik satırının hemen altına ekleniyor.
  **Bilinçli tasarım kararı:** pasta grafiği, mevcut 5-metrik satırının
  YANINA değil ALTINA, tam genişlikte eklendi (yan yana kolon
  düzenlemesi Bahri'nin "devasa boşluk" tarifiyle daha iyi örtüşebilirdi
  ama üç ayrı bloğu aynı anda kolon yapısına çevirmek riskliydi - önce
  canlıda görüp Bahri'nin tam nasıl bir yerleşim istediğini görmek daha
  güvenli).
  **NOT — Hacim/Düşüş düzeltmesi pasta grafiğe DAHİL DEĞİL:** worker.py/
  firsat_radari.py'nin BIST için uyguladığı `_score_adj + _dd_adj`
  düzeltmesi (TUPRS 63→68 farkının kaynağı, bkz. v2.0.7.141) bu pasta
  grafikte YOK - grafik SADECE temel scoring.py formülünün (RSI/Momentum/
  Volatilite/Temel) bileşenlerini gösteriyor. Bu yüzden BIST varlıklarında
  pasta diliminin toplamı, üstteki "Optima Skor" metriğinden biraz farklı
  çıkabilir (Hacim/Düşüş düzeltmesi kadar). İstenirse ayrı bir dilim/not
  olarak eklenebilir - şimdilik basit tutuldu.
  **DOĞRULANMADI** (canlı test gerekiyor): push sonrası herhangi bir
  varlığın Detay sayfasında pasta grafiğin doğru render olduğu ve
  toplamının üstteki Optima Skor'a (BIST'te düzeltme farkı hariç)
  yaklaşık eşit olduğu kontrol edilmeli.

- **[BEKLEMEDE] "Beklenti Modu" — küresel/Türkiye olaylarının Optima
  Skor'a opsiyonel etkisi.** Bahri'nin onayladığı tasarım: (1) varsayılan
  davranış hiç değişmez, piyasayı etkileyebilecek haberler ayrıca
  gösterilir (skor etkilenmez); (2) kullanıcı "Beklenti Modu" anahtarını
  açarsa, ELLE işaretlediği aktif kalıplara (jeopolitik gerilim, petrol
  arz şoku, merkez bankası sürprizi gibi) göre Optima Skor'da ŞEFFAF bir
  ayarlama gösterilir - hiçbir otomatik haber sınıflandırma/AI YOK, karar
  kullanıcıda kalır. Akademik olarak desteklenen başlangıç kalıp seti
  araştırıldı (Caldara-Iacoviello GPR Index literatürü): jeopolitik
  gerilim → Altın↑/TL↓/BIST kısa vadeli↓; petrol arz şoku → Petrol↑/TL
  enflasyon baskısı↓; merkez bankası şahin sürprizi → USD↑/Altın↓/GOP
  para birimleri↓. Henüz KOD YAZILMADI - sıradaki oturumda ele alınacak.

- **[UYGULANDI] v2.0.7.143 (11 Ağustos 2026, Bahri'nin talebi — TUPRS
  artık üç sayfada da 68,0 ile TUTARLI, sorun kapandı ✓): Getiri
  Kıyaslaması grafiklerinde iki iyileştirme.**
  (1) **Renkler kesin olarak ayrıştırıldı:** Pozisyon Bazlı grafikteki
  eski "Bold + Set2" karışımı, Set2'nin PASTEL tonları yüzünden hâlâ
  birbirine yakın görünüyordu - tamamen kaldırıldı. Her iki grafik de
  artık elle seçilmiş, renk çarkında maksimum ayrılmış, koyu/doygun
  (asla pastel değil) sabit bir renk listesi kullanıyor.
  (2) **Hover artık tek seri gösteriyor:** `hovermode="x unified"`
  (imlecin bulunduğu TARİHTEKİ tüm serileri tek kutuda listeliyordu,
  hangi rengin hangisi olduğunu ayırt etmeyi zorlaştırıyordu) →
  `hovermode="closest"` (imlecin en yakın olduğu TEK çizginin adı/değeri
  gösteriliyor - "bir çizginin üzerinde tuttuğumda hangi seriye ait
  olduğunu göstersin" talebiyle birebir örtüşüyor).
  **DOĞRULANMADI** (canlı test gerekiyor).

- **[GERİ ALINDI - KRİTİK KARAR] v2.0.7.142 (11 Ağustos 2026, Bahri'nin
  bulgusu): Bağlantı havuzlama (v2.0.7.137) TAMAMEN KALDIRILDI.**
  Art arda İKİ FARKLI çöküş türüne yol açtı: (1) havuz tükenmesi
  (v2.0.7.140'ta güvenlik ağıyla ele alınmıştı), (2) **daha ciddisi**:
  havuzdan gelen bir bağlantı "açık" görünse bile (`pg_conn.closed==0`)
  Supabase pooler'ı sunucu tarafında sessizce düşürmüş olabiliyordu - bu,
  bağlantı ALINIRKEN değil, GERÇEK SORGU çalıştırılırken
  (`psycopg2.OperationalError`) çöküyordu, v2.0.7.140'ın güvenlik ağı
  bunu YAKALAYAMIYORDU (o sadece bağlantı alma aşamasını koruyordu).
  **Karar:** iki ayrı çöküş türü art arda gelince, havuzlamanın
  performans kazancı güvenilirlik riskine değmedi. `_CompatConn` ve
  `get_conn()` proje tarihinin TAMAMINDA kanıtlanmış şekilde çalışan
  basit hale (her çağrıda sıfırdan yeni bağlantı) AYNEN geri döndürüldü.
  `get_intraday_overlay()` (v2.0.7.134, Fırsat Radarı overlay - TUPRS
  düzeltmesiyle ilgisiz, ayrı bir özellik) KORUNDU, sadece havuzlama
  kaldırıldı.
  **Performans notu:** "_get_db_url 3-4 kez tekrarlanıyor" bulgusu
  GERÇEKTİ, ama çözümü havuzlama değildi (en azından bu kadar dikkatsiz
  bir uygulamayla değil). İleride tekrar ele alınacaksa ÇOK daha dikkatli
  test edilmeli - özellikle "sunucu tarafında sessizce düşürülmüş
  bağlantı" senaryosuna karşı sağlam bir tasarım (ör. her sorgudan önce
  `SELECT 1` ile canlılık testi, ya da execute() seviyesinde başarısız
  olursa taze bağlantıyla bir kez otomatik tekrar deneme) gerekir. Bu
  oturumda kapsam dışı bırakıldı - şimdilik güvenilirlik önceliklendirildi.
  **DOĞRULANMADI** (canlı test gerekiyor): push sonrası uygulamanın
  tekrar stabil çalıştığı (BIST sayfası dahil hiçbir sayfada çökme
  olmadığı) kontrol edilmeli.

- **[UYGULANDI] v2.0.7.138 (11 Ağustos 2026, Bahri'nin sorusu — "Ben bir
  tek TUPRAS'a baktım, başka hisseler de var mıdır? Düzeltmeler bunları
  da kapsıyor mu?"): TAM KODBAZI TARAMASI yapıldı, AYNI hata sınıfının
  (frozen CSV, Fırsat Radarı overlay'i eksik) DÖRT AYRI yerde daha
  bulunduğu tespit edildi ve hepsi düzeltildi.**
  Netlik için: **scoring.py birleştirmesi (v2.0.7.132) zaten TÜM
  varlıkları/sayfaları kapsıyordu** (TUPRS'a özel değildi) - formül
  hesaplaması evrenseldi. Ama Fırsat Radarı overlay eksikliği TUPRS'a
  ÖZEL değildi, DAHA GENİŞ bir mimari boşluktu; tarama sonucu bulunanlar:
  1. **`halka_arz_client.py`** (Halka Arz sayfası) - Temettü'nün
     düzeltmeden ÖNCEKİ haliyle BİREBİR AYNI iki hataya sahipti: Optima_Skor
     hiç yeniden hesaplanmadan CSV'den kopyalanıyordu, overlay yoktu.
     `_enrich_from_csv()` artık `df_uni_hazir` parametresi alıyor (Temettü
     ile AYNI desen) - hem yeniden hesaplama hem overlay eklendi.
  2. **`emailer.py`** (Zamanlanmış/tetiklenen e-posta raporları) - HEM
     `_optima_score()` fallback formülü (scoring.py'ye bağlandı, ALTINCI
     elle-tutulan kopyaydı) HEM de kendi CSV yükleme dalı (overlay eksikti,
     artık ekli) düzeltildi.
  3. **app.py'deki e-posta TETİKLEME uç noktası** (webhook token ile
     tetiklenen zamanlanmış rapor) - kendi AYRI CSV yükünü yapıyordu,
     `load_universe()`'in overlay'ini hiç uygulamıyordu - artık uyguluyor.
  **Doğrulanıp AYRI olduğu görülen (bu hata sınıfına dahil DEĞİL):**
  `emailer_standalone.py`, `peak_check_standalone.py` - ikisi de
  Optima_Skor hiç kullanmıyor/göstermiyor, ilgisiz.
  **DOĞRULANMADI** (canlı test gerekiyor): push sonrası Halka Arz
  sayfasındaki skorların Ana Sayfa/BIST ile eşleştiği kontrol edilmeli.
  E-posta raporlarının doğruluğu ancak bir sonraki zamanlanmış
  gönderimde görülebilir.

- **[KRİTİK, PUSH EDİLMEMİŞ] v2.0.7.134+135 hiç push edilmedi!** Git
  geçmişi doğrudan v2.0.7.133'ten v2.0.7.136'ya atlıyor. Bu, TUPRS kök
  neden düzeltmesini (Fırsat Radarı overlay'inin `db.get_intraday_overlay()`
  olarak tek kaynağa taşınması + `temettu_client.py`'nin performans
  optimizasyonu) İÇERİYOR - yani bu düzeltme hâlâ canlıda YOK. Dosyalar
  (`db.py`, `app.py`, `temettu_client.py`) zaten hazır, sadece push
  edilmesi gerekiyor. **Bir sonraki oturumda önce bunun push edilip
  edilmediği kontrol edilmeli.**

- **[UYGULANDI, TEST EDİLMEDİ] v2.0.7.137 (11 Ağustos 2026, Bahri'nin
  bulgusu — "sistem çıldırtıcı derecede yavaş" şikayeti için Streamlit
  Cloud loglarından GERÇEK kanıt bulundu): `get_conn()` gerçek bir
  bağlantı havuzuna geçirildi.** Loglar incelendiğinde `[db]
  _get_db_url: secrets[supabase][db_url] OK` mesajının TEK BİR sayfa
  render'ında 3-4 KEZ tekrarlandığı görüldü - `get_conn()` her çağrıda
  SIFIRDAN yeni bir psycopg2 bağlantısı (TCP+TLS+Postgres kimlik
  doğrulama, Supabase uzak sunucu olduğu için 100-500ms+ sürebilir)
  açıyordu, hiç havuzlama/yeniden kullanım yoktu. Tek bir sayfa
  render'ında birden fazla fonksiyon (Sermaye/Nakit, Gerçekleşmiş K/Z,
  Fırsat Radarı overlay, vb.) kendi ayrı `get_conn()` çağrısını yapıyor,
  her biri sırayla yeni bir ağ turu maliyeti biriktiriyordu.
  **Çözüm:** `psycopg2.pool.ThreadedConnectionPool` (1-10 bağlantı,
  modül seviyesinde tembel/lazy oluşturulur) eklendi. `get_conn()` artık
  havuzdan bağlantı ALIYOR (`pool.getconn()`), `_CompatConn.close()`
  artık bağlantıyı GERÇEKTEN KAPATMIYOR - önce rollback yapıp havuza
  GERİ VERİYOR (`pool.putconn()`). Mevcut TÜM `.close()` çağıran kod
  DEĞİŞMEDEN çalışmaya devam eder - davranış dışarıdan aynı görünür,
  sadece art arda gelen çağrılar artık yeni ağ turu gerektirmiyor, hazır
  bir bağlantıyı anında alıyor. Basit bir canlılık kontrolü de eklendi
  (`pg_conn.closed` — havuzdan gelen bağlantı önceki bir kullanımdan
  kapanmışsa taze bir tane açılır).
  **BİLİNEN SINIRLAMA (gelecekte sağlamlaştırılabilir):** eğer bir
  çağıran fonksiyon istisna (exception) fırlatıp `.close()`'a hiç
  ulaşmazsa, o bağlantı havuza geri dönmez ("sızar") - havuz 10
  bağlantıya kadar büyüyebildiği için kısa vadede sorun yaratmaz, ama
  uzun vadede (çok sayıda hata yolu tetiklenirse) havuz tükenebilir. Tam
  çözüm tüm `get_conn()` kullanımlarını `with` (context manager)
  desenine çevirmek olur - bu oturumda kapsam dışı bırakıldı.
  **DOĞRULANMADI** (canlı test gerekiyor): push sonrası (1) Streamlit
  Cloud loglarında `_get_db_url` mesajının artık HER seferinde değil,
  SADECE havuz ilk oluşturulurken (bir kez) göründüğü, (2) sayfa
  geçişlerinin gözle görülür şekilde hızlandığı kontrol edilmeli. Ayrıca
  v2.0.7.136'daki `[timing][AnaSayfa]` logları da bu push ile birlikte
  gelecek zamanlama verisini üretmeye devam edecek - ikisi birlikte
  değerlendirilmeli.

- **[TEŞHİS AŞAMASINDA] v2.0.7.136 (11 Ağustos 2026): Ana Sayfa'nın ilk
  açılış/yenileme yavaşlığı için zamanlama ölçümü eklendi.** Bahri
  yavaşlığın en çok Ana Sayfa'da (Bütçe Optimizasyonu), sayfa ilk
  açılırken/hesaplama sürerken hissedildiğini belirtti. Tahminle devam
  etmek yerine 3 noktaya `print()` zamanlaması eklendi (Streamlit Cloud
  loglarında görünür):
  1. `[timing][AnaSayfa] BIST canli yenileme (40 ticker)` - en güçlü aday,
     kendi belgesine göre 3-5sn sürebilir, SADECE BIST seansı açıkken
     çalışır (bu yüzden akşam testlerinde görünmeyebilir).
  2. `[timing][AnaSayfa] Kategori havuzu skorlama (tum kategoriler)` -
     TEFAS'ın ~1340 satırı için eksik Optima_Skor'ların `.apply()` ile
     satır-satır yeniden hesaplanması potansiyel maliyet.
  3. `[timing][AnaSayfa] Sayfa basindan oneri listesi hazir olana kadar
     TOPLAM` - sayfa başlangıcından öneri listesi hazır olana kadar geçen
     toplam süre.
  Ayrıca `load_universe()`'in KENDİ `[timing] load_universe (cache MISS...)`
  logu zaten mevcuttu (v1.9.3) - bu üçü birlikte tam resmi verir.
  **Sıradaki adım:** Bahri push sonrası Ana Sayfa'yı açıp Streamlit
  Cloud'un "Manage app" → loglarından bu 3-4 satırı okuyup paylaşmalı -
  gerçek sayılara göre en pahalı adım kesin olarak belirlenip
  hedeflenerek optimize edilecek (tahminle değil).

- **[UYGULANDI] v2.0.7.133 (10 Ağustos 2026, Bahri'nin bulgusu — TUPRS
  hâlâ 63,0 (Temettü) vs 83,0 (Ana Sayfa/BIST) gösteriyordu, v2.0.7.132'nin
  scoring.py birleştirmesinden SONRA bile).** Kök neden bu sefer FORMÜL
  değildi (o zaten düzeltilmişti) - **ÖNBELLEK TAZELİĞİ** farkıydı:
  Ana Sayfa/BIST sayfası `load_universe()`'in **10 dakikalık** önbelleğini
  kullanıyor, Temettü sayfası ise `fetch_temettu_list()`'in **4 saatlik**
  önbelleğini - bu önbellek Optima_Skor'u da (pahalı XTMTU üye
  listesi/yfinance temettü verisiyle BİRLİKTE) donduruyordu. İkisi de artık
  aynı hesaplıyor ama farklı zaman noktalarındaki CSV anlık görüntülerine
  bakıyorlardı. **Çözüm:** `fetch_temettu_list()`'in önbellek-isabet
  yolunda bile artık `_enrich()` HER SEFERİNDE yeniden çağrılıyor -
  Optima_Skor/RSI/Ret1M/Son_Fiyat her zaman CSV'den TAZE okunuyor (ucuz
  bir yerel disk okuması, ağ çağrısı DEĞİL - performansı etkilemez).
  Sadece gerçekten pahalı kısımlar (XTMTU üye listesi, yfinance temettü
  verisi) hâlâ 4 saat önbellekli.
  **Ayrıca bulundu ve düzeltildi:** `live_data.py`'de `_teknik_skor_100()`
  diye BEŞİNCİ bir kopya daha vardı (MADEN'in canlı Detay sayfası
  yenilemesinde kullanılıyor, kendi docstring'i "worker.py'yi import etmek
  riskli" diye AÇIKÇA bu tekrarı gerekçelendiriyordu) - artık o da
  scoring.py'ye bağlandı (scoring.py yan etkisiz olduğu için güvenle
  import edilebiliyor, worker.py'nin aksine).
  **DOĞRULANMADI** (canlı test gerekiyor): push sonrası TUPRS'ın üç
  sayfada da (Ana Sayfa, BIST, Temettü) aynı sayıyı gösterdiği kontrol
  edilmeli. Ayrıca Temettü sayfasının hâlâ hızlı açıldığından emin
  olunmalı (yeni `_enrich()` çağrısı ucuz olmalı ama gerçek ortamda
  doğrulanmadı).

- **[İNCELENDİ, BUG DEĞİL] Değerli Madenler'in Bütçe Optimizasyonu'nda
  çıkmaması (10 Ağustos 2026, Bahri'nin sorusu).** Bahri "Değerli
  Madenler sayfasında Skor 81,8/78,0/75,5 görünüyor, neden AL sinyalli
  değiller" diye sordu — ama bu değerler **RSI** sütunuydu, **Optima
  Skor DEĞİL** (sütun sırası: Ticker/Ad/Son Fiyat/RSI/1A Getiri%/Optima
  Skor — gerçek Optima Skor değerleri 45,3/38,7/37,3 idi, 60 eşiğinin
  altında). RSI>70 "aşırı alım" bölgesi olduğu için `_teknik_alt_skor()`
  bu aralıkta 0 puan veriyor (bkz. scoring.py) — momentum iyi olsa bile
  skoru düşürüyor. Matematiksel olarak doğrulandı: `optima_score(81.8,
  12.02, vol=15)` → 52,0. Bu bilinçli bir tasarım (aşırı ısınmış bir
  varlığı "AL" diye önermemek) - bug değil.

- **[UYGULANDI] v2.0.7.132 (10 Ağustos 2026, Bahri'nin bulgusu — üç ayrı
  konu, tek oturumda).**
  (1) **TUPRS 83,0 (Ana Sayfa) vs 68,0 (Temettü) çelişkisi kök nedeniyle
  düzeltildi.** Kök neden: `optima_score()`/`_teknik_alt_skor()`/
  `_temel_alt_skor()`/`get_signal()` mantığının **worker.py,
  firsat_radari.py VE (eskiden) app.py'de ÜÇ AYRI, elle senkronize
  edilen kopyası** vardı (worker.py'nin kendi yorumu: "Bu iki fonksiyon
  senkronize tutulmalı" — yani zaten bilinen bir risk). `temettu_client.py`
  app.py'yi güvenle import edemediği için (Streamlit UI kodu çalıştırırdı)
  Optima_Skor'u CSV'den DONMUŞ haliyle kopyalıyordu, Ana Sayfa ise BIST
  için seans içi canlı fiyat sonrası YENİDEN HESAPLIYORDU. **Çözüm:**
  yeni `scoring.py` modülü — bu 4 fonksiyonun TEK kaynağı. app.py,
  worker.py, firsat_radari.py, temettu_client.py hepsi buradan import
  ediyor (worker.py/firsat_radari.py'de eski isimle - `_bist_optima_score`
  - geriye dönük uyumlu alias). `temettu_client.py._enrich()` artık
  Optima_Skor'u CSV'deki RSI/Ret1M/Vol/PB/PE/DY'den scoring.py ile YENİDEN
  HESAPLIYOR (CSV'den kopyalamak yerine) - en azından formül tutarlılığı
  garanti. **Not:** Temettü sayfasına Ana Sayfa'daki gibi ekstra bir
  canlı fiyat yenilemesi EKLENMEDİ (performans şikayeti nedeniyle bilinçli
  tercih) - yani hâlâ CSV'nin RSI/Ret1M değerlerini kullanıyor, sadece
  FORMÜL artık aynı. Tam anlık eşitlik için CSV taze olmalı.
  (2) **Performans - "sistem çok ağırlaşmış" şikayeti.** Kök neden:
  bugünkü oturumda eklenen 2 yeni grafik (Getiri Kıyaslaması + Pozisyon
  Bazlı Getiri) AYNI portföy ticker'larının geçmiş verisini AYRI AYRI,
  ÖNBELLEKSİZ çekiyordu - Portföyüm sayfası her açıldığında/her widget
  etkileşiminde (Streamlit'in tam script yeniden çalıştırma modeli
  yüzünden) ikisi de baştan çalışıyordu. **Çözüm:** yeni paylaşılan,
  5 dakika önbellekli `_kiyaslama_ticker_serileri_cek()` - iki grafik de
  artık AYNI önbellekten okuyor, veri sadece 1 kez çekiliyor ve 5 dakika
  boyunca tekrar çekilmiyor. `_kiyaslama_gunluk_serileri()`'nin kendisi
  de ayrıca önbellekli.
  **DOĞRULANMADI** (canlı test gerekiyor): hem scoring.py konsolidasyonu
  hem performans düzeltmesi bu ortamda syntax/mantık olarak doğrulandı
  ama push sonrası (a) TUPRS'ın artık iki sayfada da aynı sayıyı
  gösterdiği (b) Portföyüm sayfasının gözle görülür şekilde hızlandığı
  kontrol edilmeli.

- **[UYGULANDI, DENEME] v2.0.7.131 (10 Ağustos 2026, Bahri'nin talebi —
  iki ayrı iyileştirme).**
  (1) **Vadeli Mevduat artık gerçekten "en yüksek banka oranı".** Önceki
  TCMB EVDS serisi (`TP.MT210AGS.TRY.MT01`) bir AĞIRLIKLI ORTALAMA'ydı,
  Bahri'nin istediği "en yüksek" değildi. hesap.com'un "en çok
  kazandıran mevduat" bölümü denendi ama **Cloudflare bot korumasıyla
  engellendi** (doğrudan test edildi: 403 + "Just a moment" sayfası,
  Streamlit Cloud'da da aynı engel beklenir). Alternatif arandı:
  **hesapkurdu.com/mevduat** engelsiz ve sunucu tarafında render ediliyor
  (Next.js SSR) - oranlar `<td class="Table_td__xlSfc">% 46,00</td>`
  biçiminde doğrudan HTML'de, JS çalıştırmaya gerek yok. Yeni
  `_en_yuksek_vadeli_mevduat_cek()` bu sayfadaki TÜM oranları regex'le
  çekip EN YÜKSEĞİNİ döndürüyor (test: %46). "Banka Mevduatı" adı
  "Vadeli Mevduat" olarak değiştirildi (grafik, lejant, özet metni,
  açıklama notu - hepsi). Tahvil/Repo hâlâ TCMB EVDS'ten (değişmedi).
  (2) **Pozisyon Bazlı Getiri Karşılaştırması** - yeni, TAMAMEN BAĞIMSIZ
  ikinci bir grafik (`_render_pozisyon_karsilastirma()`), Getiri
  Kıyaslaması'nın hemen altında. Portföydeki HER POZİSYONUN (dış
  kıyaslama araçları olmadan, sadece kendi varlıklar) kendi alış
  tarihinden bugüne kümülatif getirisi ayrı çizgi. Aynı ticker birden
  fazla kez alınmışsa ("MTG", "MTG #2" gibi) ayrı pozisyon olarak
  gösteriliyor. **Bahri "beğenmezsem kaldırırız" dedi** - bu özellik tek
  bir fonksiyon + tek bir çağrı satırı, kolayca geri alınabilir. Onay
  bekleniyor.
  **DOĞRULANMADI** (canlı test gerekiyor): hesapkurdu.com'un HTML yapısı
  değişirse regex bulamayabilir (hata mesajı gösterir, çökmez) - ilk
  kullanımda Vadeli Mevduat değerinin göründüğü doğrulanmalı.

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

- **[UYGULANDI, CANLI TEST EDİLMEDİ] v2.0.7.194 (25 Ağustos 2026, Bahri'nin
  talebi — "her haberin optima skoruna etki etmesi söz konusu olamaz,
  bazı kriterler belirlemeliyiz"): TOPLU ONAY EKLENDİ, AMA SADECE ÜÇ
  KRİTERİ DE KARŞILAYAN TESPİTLER İÇİN.**
  - **Bahri'nin 3 kriteri somut kurallara çevrildi (onun onayıyla):**
    (1) Şiddet="Yüksek" olmalı. (2) Aynı kalıpta, FARKLI bir kaynaktan,
    son 24 SAAT içinde başka bir tespit olmalı (çoklu kaynak teyidi -
    Bahri'nin seçimiyle 24 saat, 48 değil). (3) Kalıbın gerçek akademik/
    tarihsel dayanağı olduğu Admin Panel'den işaretlenmiş olmalı.
  - **Kriterleri KARŞILAMAYAN tespitlere ne olur (Bahri'nin seçimi):**
    OTOMATİK REDDEDİLİR - skoru etkilemez, listeden çıkar. Bekleyen
    listede bırakılmaz.
  - **Yeni DB şeması:** `haber_kaliplari` tablosuna `istatistiksel_dayanak`
    BOOLEAN sütunu eklendi (idempotent ALTER TABLE - canlı tablo zaten
    var). Yeni fonksiyonlar: `kalip_istatistiksel_dayanak_ayarla()`,
    `coklu_kaynak_teyidi()` (kaba bir vekil/proxy - "aynı kalıpta farklı
    kaynaktan yakın zamanlı tetikleme" kontrol ediyor, "aynı OLAYIN
    farklı kaynaklarca haberleştirilmesi" ile "aynı kalıba uyan FARKLI
    bir olayın aynı gün olması" arasında ayrım YAPMIYOR - ileride daha
    kesin bir eşleştirme, ör. başlık benzerliği, eklenebilir).
  - **Admin Panel:** Kalıp Yönetimi'ne "İstatistiksel/akademik dayanağı
    var (toplu onaya uygun)" anahtarı eklendi. **AÇIK - Bahri'nin
    yapması gereken adım:** Akademik Kaynakça'da gerçek kaynağı olan
    kalıplar (jeopolitik, petrol, fed, kredi_notu, tcmb_kredibilite) bu
    anahtarla işaretlenmeli - henüz araştırılmamış olanlar (kripto_olay,
    pboc_tesvik) işaretsiz bırakılmalı. Bu işaretleme YAPILMADAN hiçbir
    kalıp toplu onaya uygun olmaz (varsayılan FALSE).
  - **UI:** Ana Sayfa'daki "Onay Bekleyen Otomatik Tespitler" listesinin
    üstüne "Tümünü Onayla (kriterleri karşılayanlar)" düğmesi ve
    kriterleri açıklayan bir not eklendi.
  - **İzole test edildi (6 senaryo):** tüm kriterleri karşılayan →
    onaylanır; şiddet Orta → reddedilir; dayanaksız kalıp → reddedilir;
    teyit yok → reddedilir; AYNI kaynaktan "teyit" → GEÇERSİZ SAYILIR
    (doğru); 24 saatten eski teyit → geçersiz. Hepsi doğru sonuç verdi.

- **[UYGULANDI, CANLI TEST EDİLMEDİ] v2.0.7.195 (25 Ağustos 2026, Bahri'nin
  talebi — "Kalıp/Şiddet/Geçerlilik yazısının daha çok görünürlüğünü
  sağla"): sade gri `st.caption` yerine, şiddete göre renklenen (Yüksek=
  kırmızı, Orta=turuncu, Düşük=gri) sol kenarlıklı bir rozet kutusu -
  hem modal dialogda hem Ana Sayfa listesinde (tutarlılık için ikisinde
  de aynı stil).


  bulgusu — "onay butonunu tıklıyorum ama hiçbir buton çalışmıyor"):
  ONAY/RED DÜĞMELERİ VERİTABANI YAZMA HATASINI SESSİZCE YUTUYORDU.**
  - **Kesin kök neden:** `db.py`'deki `tespit_onayla`/`tespit_reddet`
    fonksiyonları veritabanı yazması başarısız olsa bile HATA
    FIRLATMIYOR - sadece arka planda `print` edip `False` döndürüyor.
    `app.py`'deki düğme kodu bu dönüş değerini HİÇ KONTROL ETMİYORDU -
    "except" bloğu bu yüzden hiçbir zaman tetiklenmiyordu, kod her
    zaman "başarılı" varsayıp cache temizleyip rerun ediyordu. Gerçek
    bir yazma hatası olduğunda kullanıcı ne bir hata mesajı görüyordu
    ne de bir ilerleme - sadece aynı pop-up tekrar tekrar açılıyordu.
  - **Çözüm:** Hem modal dialogdaki hem Ana Sayfa listesindeki (4 yer
    toplam) Onayla/Reddet düğmeleri artık dönüş değerini kontrol
    ediyor - başarısızsa AÇIK bir hata mesajı gösteriliyor.

- **[UYGULANDI, CANLI TEST EDİLMEDİ] v2.0.7.193 (25 Ağustos 2026, Bahri'nin
  takip bulgusu — "gerçekte çalıştı ama çok geç çalıştı"): ONAY SONRASI
  YAVAŞLIK - GEREKSİZ GENEL CACHE TEMİZLEME BULUNDU.**
  - **Kesin kök neden:** Onay/Red sonrası `st.cache_data.clear()`
    (GENEL/global temizleme) çağrılıyordu - bu, SADECE ilgili iki küçük
    tespit önbelleğini değil, UYGULAMADAKİ HER ÖNBELLEKLİ FONKSİYONU
    (tüm evren CSV'si, BIST/TEFAS verileri, her şey) tek seferde
    siliyordu. Onay sonrası rerun bu yüzden HER ŞEYİ sıfırdan yeniden
    hesaplamak zorunda kalıyordu - "çok geç çalıştı" hissi buradan
    geliyordu.
  - **Çözüm:** 4 konumun tümünde `st.cache_data.clear()` yerine SADECE
    `_bekleyen_tespitler_onbellekli.clear()` ve
    `_onaylanmis_tespitler_onbellekli.clear()` çağrılıyor - genel
    temizleme sadece bu iki fonksiyon hiç tanımlanmamışsa (try bloğu
    daha ileri gitmeden başarısız olduysa) güvenli yedek olarak kalıyor.
  - **Test EDİLMEDİ (performans iyileştirmesi, canlıda gözlemlenmeli)** -
    bir sonraki onay/red işleminin gözle görülür şekilde daha hızlı
    olması bekleniyor.

- **[UYGULANDI, CANLI TEST EDİLMEDİ] v2.0.7.200 (26 Ağustos 2026, Bahri'nin
  bulgusu — tek kaynaklı bir petrol haberi yine de pop-up olarak çıktı):
  v2.0.7.199'UN KENDİ BELGELEDİĞİ SINIRLAMA GERÇEKLEŞTİ - BAŞLIK
  BENZERLİĞİ KONTROLÜ EKLENDİ.**
  - **Doğrulama:** v2.0.7.199'un GERÇEKTEN canlıda olduğu GitHub'dan
    doğrudan kontrol edildi (kod doğruydu) - sorun v2.0.7.199'un kendi
    dokümantasyonunda ZATEN FLAGLENMIŞ bir sınırlamaydı: kaba kontrol
    "aynı kalıp, farklı kaynak, 24 saat" bakıyordu, "GERÇEKTEN AYNI
    OLAY mı" bakmıyordu - muhtemelen aynı gün "jeopolitik" kalıbına
    uyan ama TAMAMEN FARKLI bir haber kontrolü yanlışlıkla geçirdi.
  - **Çözüm:** `get_bekleyen_tespitler()` artık iki aşamalı - önce SQL
    ile KABA aday listesi çıkarılıyor (aynı kalıp, farklı kaynak, 24
    saat), sonra Python'da `difflib.SequenceMatcher` ile başlıklar
    arasında GERÇEK bir metin benzerliği aranıyor (eşik: 0.35).
  - **İzole test edildi (2 senaryo):** Bahri'nin gördüğü TAM senaryo
    (petrol haberi vs. tamamen farklı bir jeopolitik haber) - benzerlik
    0.189, doğru şekilde REDDEDİLDİ. Gerçek aynı-olay-farklı-ifade
    senaryosu (iki kaynağın aynı petrol haberini farklı kelimelerle
    anlatması) - benzerlik 0.714, doğru şekilde KABUL EDİLDİ.
  - **BİLİNEN SINIRLAMA (hâlâ tam çözülmedi):** düz metin benzerliği
    mükemmel değil - AI'ya iki başlığı karşılaştırtmak daha kesin
    olurdu ama maliyet/karmaşıklık nedeniyle bu turda yapılmadı.

- **[UYGULANDI, CANLI TEST EDİLMEDİ] v2.0.7.202 (26 Ağustos 2026, Bahri'nin
  bulgusu — "iki düğme aynı renk/formatta olmalı"): "Varsayılan Skor"
  düğmesindeki `help=` parametresi, Streamlit'in düğmeyi farklı
  sarmalamasına yol açıp uygulamanın genel buton CSS'ini (`app.py`'deki
  `.stButton>button{...}`) eşleştirmesini engelliyordu - `help=`
  kaldırıldı, açıklama düğmelerin altına `st.caption()` olarak taşındı.
  İki düğme artık birebir aynı stille render oluyor.
  **Ayrıca aynı turda:** "Haberler" sayfası "SonDakika Haberleri" olarak
  yeniden adlandırıldı (PAGES listesi, routing koşulu, st.title() -
  3 yer tutarlı şekilde güncellendi).

- **[KALICI GERÇEK - DÜZELTME, 27 Ağustos 2026] TrendSurf Optima TİCARİ
  BİR ÜRÜN DEĞİLDİR.** Bahri bunu açıkça belirtti ve gelecekte
  hatırlanmasını istedi: uygulama halka açılmayacak, hiçbir zaman
  ticari bir SaaS ürünü olarak sunulmayacak. Aboneleri sadece Bahri'nin
  akrabaları, yakın dostları ve arkadaşlarından oluşacak/oluşmaya
  devam edecek. Bu notun öncesinde bazı kayıtlarda "ticari ürün"/
  "abonelik modeli" gibi ifadeler geçmiş olabilir - bunlar YANLIŞ,
  bundan sonra düzeltilmeli. Bu düzeltme Claude'un kalıcı hafızasına
  da (memory_user_edits) işlendi.
  **Pratik etkisi:** Daha önce bazı haber kaynağı adayları (ör. Fox
  Business, Nikkei Asia) "kişisel/ticari olmayan kullanım" şartı
  ticari kullanımla çeliştiği için reddedilmişti - bu netleşmeyle o
  değerlendirme YENİDEN GÖZDEN GEÇİRİLEBİLİR (ama otomatik olarak
  eklenmiş değiller, Bahri isterse tekrar sorulmalı).

- **[KALICI TERCİH - 27 Ağustos 2026] Haber kaynağı seçim ilkesi:**
  Bahri'nin standing tercihi: yeni kaynak eklerken, hiçbir ülkenin veya
  hükümetin "sesi" olmayan, gerçekten tarafsız/bağımsız habercilik
  yapan yayın organları tercih edilmeli - devlet güdümlü/devlet sesi
  olan kaynaklardan kaçınılmalı. Bu ilke gelecekteki TÜM kaynak
  araştırmalarında uygulanmalı. Bu tercih Claude'un kalıcı hafızasına
  da işlendi.
  **AÇIK GERİYE DÖNÜK GERİLİM (henüz ele alınmadı, Bahri'ye
  sorulmalı):** Mevcut kaynaklardan **AA Ekonomi** Türkiye'nin resmi
  devlet haber ajansı (Anadolu Ajansı) - bu yeni ilkeyle en net
  çelişen mevcut kaynak. Al Jazeera (Katar devlet fonlu) ve BBC/ABC
  Australia (kamu yayıncıları, ama genelde editoryal bağımsızlığı
  daha güçlü kabul edilir) daha gri alanda. Bahri şimdilik SADECE
  "ileriye dönük" uygulanmasını istedi, mevcut kaynakları hemen
  gözden geçirmedi - bu, ayrı bir gündem maddesi olarak açık kalıyor.

- **[UYGULANDI, TEST EDİLDİ] v2.0.7.207 (27 Ağustos 2026, Bahri'nin
  talebi — "AA Ekonomi konusunda kesinlikle haklısın, hükümet yanlısı
  haberler ürettiği için bu kaynağı devre dışı bırakmak daha doğru
  olacaktır"): AA EKONOMİ KALDIRILDI - TARAFSIZLIK İLKESİYLE.**
  Anadolu Ajansı (AA), Türkiye'nin resmi devlet haber ajansı - Bahri'nin
  standing tarafsızlık ilkesiyle ("hiçbir ülkenin veya hükümetinin
  sesi olmaksızın") doğrudan çelişiyordu. `_RSS_KAYNAKLARI`'ndan
  kaldırıldı, `app.py`'deki kaynak listesi metni de güncellendi.

- **[UYGULANDI, TEST EDİLDİ] v2.0.7.213 (29 Ağustos 2026, Bahri'nin
  talebi — "öncelik ABD, İngiltere ve Fransa olmak üzere birkaç sağlam
  kaynak bul"): 2 YENİ KAYNAK EKLENDİ (21 TOPLAM KAYNAK).**
  - **PBS NewsHour** (ABD, Ekonomi akışı) - `pbs.org/newshour/feeds/
    rss/economy` - WETA'nın (kamu yayıncısı) kâr amacı gütmeyen yan
    kuruluşu, saygın vakıflarca (Carnegie, Ford, MacArthur, Hewlett)
    fonlanıyor - doğrudan hükümet ataması/kontrolü yok.
  - **Ouest-France** (Fransa) - `ouest-france.fr/rss/une` - Fransa'nın
    en çok okunan gazetesi (günlük 2,5 milyon okuyucu), bir vakıf/
    dernek yapısı aracılığıyla editoryal bağımsızlığı korunuyor.
    **Fransa için ÇOK SAYIDA başarısız denemeden (France24, Le Monde,
    Les Echos, RFI, Mediapart) sonra bulunan İLK çalışan aday.**
  - İkisi de `_CEVIRI_GEREKEN_KAYNAKLAR`'a eklendi, `app.py`'deki
    kaynak listesi metni güncellendi. İzole test edildi - 21 benzersiz
    kaynak doğrulandı.
  - **AÇIK - canlı doğrulama bekleniyor:** ikisi de kendi test
    ortamında domain kısıtlaması nedeniyle doğrudan test edilemedi
    (birçok başka kaynakla aynı durum) - bir sonraki haber taramasının
    log'unda görülmeli.

- **[UYGULANDI, TEST EDİLDİ] v2.0.7.219 (31 Ağustos 2026, Bahri'nin
  bulgusu — TEFAS workflow'unu elle çalıştırdı, CSV'nin başarıyla
  güncellendiğini doğruladı, ama tarayıcı yenilemesiyle uygulamada
  yeni değer görünmedi, sadece TAM REBOOT sonrası göründü): `load_
  universe()` ÖNBELLEK SÜRESİ 10 DK'DAN 5 DK'YA KISALTILDI.**
  - **KOD HATASI DEĞİLDİ - araştırmayla doğrulandı:** GitHub Actions
    log'u incelendi ("CSV'yi commit + push et" adımı) - "1 file
    changed, 1348 insertions(+), 1340 deletions(-)", "TEFAS CSV
    pushlandi" - gerçek bir güncelleme olmuş. Taze klonlanan CSV'de
    MTG'nin fiyatı (1,740899) TEFAS'ın kendi web sitesindeki değerle
    BİREBİR eşleşiyordu - veri kesinlikle doğru ve günceldi. Sorun,
    `load_universe()`'ün `@st.cache_data(ttl=600)` ile SUNUCU TARAFI,
    TÜM kullanıcılar arası PAYLAŞIMLI bir önbellek kullanmasıydı -
    tarayıcı yenilemesi bu önbelleği TEMİZLEMEZ, sadece TTL süresi
    dolunca (ya da uygulama tam reboot ile yeniden başlayınca, ki
    Bahri'nin "reboot yapınca yeni rakamlar geldi" gözlemi tam olarak
    bunu doğruladı) yeni veri okunur.
  - **Çözüm:** 600sn (10 dk) → 300sn (5 dk) - uygulamanın başka
    birçok yerinde zaten kullanılan standart TTL değeriyle tutarlı.

- **[UYGULANDI, İZOLE TEST EDİLDİ (2 senaryo)] v2.0.7.222 (31 Ağustos
  2026, Bahri'nin netleştirmesi — "maliyetten ziyade işlemleri çok
  yavaşlatıyordu asıl mesele zamanın çok uzamasıydı"): ORTA SAYFA
  OCR'INA GÜVENLİ BİR ÜST SINIR EKLENDİ.**
  - **Gerçek risk:** `update_data.yml` workflow'unun 45 DAKİKALIK SERT
    zaman aşımı var (`timeout-minutes: 45`) - v2.0.7.221'in sınırsız
    orta sayfa OCR'ı, şu an TÜM bekleyen adayların bu veriden yoksun
    olması nedeniyle İLK çalıştırmada hepsi birden pahalı OCR'a
    girecekti - patolojik derecede uzun bir belge (150+ sayfa) tek
    başına dakikalarca sürebilir, toplam süre 45 dakikayı zorlayabilirdi.
  - **Çözüm:** Yeni `ORTA_SAYFA_OCR_MAX_SAYFA = 40` sabiti - mevcut
    `FIYAT_TESPIT_MAX_YENI_ISLEME` ("çalışma süresi patlamasın diye")
    ile AYNI kurulu desen. Sınır SADECE OCR gerektiren (metin katmanı
    olmayan) sayfalar için geçerli - ücretsiz/hızlı metin katmanı
    çıkarma bu sınırdan hiç etkilenmiyor. Sınır aşılırsa kalan görsel
    sayfalar sessizce (log'a not düşülerek) atlanıyor - toplam çalışma
    süresi asla kontrolsüz büyüyemiyor.
  - **İzole test edildi (2 senaryo):** TERA benzeri tipik belge (53
    orta sayfa, sadece 4'ü taranmış) → sınıra HİÇ takılmıyor, 4/4 OCR
    ediliyor. Patolojik uzun belge (200 sayfanın tamamı taranmış) →
    sınır tam olarak 40'ta duruyor, kalan 160 sayfa güvenli şekilde
    atlanıyor.

- **[UYGULANDI] v2.0.7.223 (1 Eylül 2026): Halka Arz Graham/Çarpan için
  açık başarı/başarısızlık teşhis loglaması eklendi** (3 nokta: ilk+son
  sayfa sonrası, orta sayfa sonrası, nihai sonuç). Bu loglama sayesinde
  1 Eylül 2026'da OCR'ın gerçekten çalıştığı ama TÜM adaylarda
  `graham=None, carpan=None` kaldığı kesin olarak doğrulandı - kod
  içinde zaten belgelenmiş "OCR bazı raporlarda rakamları bile bozuyor"
  sorunu v2.0.7.221/222'nin çözmediği DAHA DERİN bir OCR KALİTE sorunu
  olarak teşhis edildi. AÇIK - sonraki oturumda ayrı bir proje olarak
  ele alınacak (görüntü ön-işleme veya farklı OCR motoru/API).

- **[UYGULANDI, İZOLE + CANLI TEST EDİLDİ - DOĞRULANDI] v2.0.7.224
  (1 Eylül 2026, Bahri'nin bulgusu — "Portföyümdeki varlıklarımın karı
  dün 2026 TL üzerindeyken bugün 1801,67 TL, fiyatlar düştüğü halde ve
  uyarı ayarlarım açık olduğu halde hiç uyarı gelmedi"): PEAK TRACKER
  AYNI HİSSENİN BİRDEN FAZLA LOTUNU DOĞRU KONSOLİDE EDİYOR - KRİTİK
  UYARI HATASI DÜZELTİLDİ.**
  - **Kesin kök neden:** GitHub Actions'ta "Peak Check Alert System"
    force modda çalıştırılıp log incelendi:
    `[peak_tracker] batch_upsert hatasi (user=2): ON CONFLICT DO UPDATE
    command cannot affect row a second time`. `_load_user_portfolio()`
    her lotu (alım kaydı) ayrı satır olarak dönüyordu. Bahri'nin aynı
    hisseden (ör. MTG) birden fazla lotu olduğu için,
    `evaluate_user_alerts()`'in per-ticker döngüsü aynı ticker'ı TEK bir
    batch UPSERT komutunun `upserts` listesine İKİ KEZ ekliyordu -
    PostgreSQL bunu tek komutta reddediyordu. **Sonuç: o hisselerin
    `peak_price`'ı veritabanında HİÇ GÜNCELLENMİYORDU** - kayıtlı
    "zirve" donuk/eski kalıyor, gerçek düşüş yüzdesi yanlış
    hesaplanıyor, uyarı hiç tetiklenmiyordu.
  - **Çözüm:** Yeni `_consolidate_portfolio_lots()` fonksiyonu,
    `evaluate_user_alerts()` içinde per-ticker değerlendirmeden ÖNCE
    çağrılıyor - aynı ticker'ın tüm lotları miktar toplanarak + maliyet
    miktar-ağırlıklı ortalama alınarak TEK pozisyona indirgeniyor.
    `_batch_upsert_peaks()`'e de savunma amaçlı ek tekilleştirme
    eklendi (beklenmedik bir çağrı yolundan aynı ticker iki kez gelirse
    en yüksek fiyatı tutan tek kayda indirgeniyor).
  - **İzole test edildi:** Bahri'nin gerçek portföy yapısına benzer
    sahte veriyle (MTG'nin 2 lotu, 100@10 + 50@13) doğru birleşti:
    miktar=150, ağırlıklı ort. maliyet=11.0, upserts listesinde MTG
    sadece 1 kez.
  - **NOT - O&M2→O&M3 kopukluk:** Bu düzeltme O&M2 oturumunda GitHub'a
    hiç PUSH EDİLMEMİŞ olarak bulundu (O&M3'ün ilk taze klonunda
    `peak_tracker.py` hâlâ 28 Haziran 2026 tarihli eski haliydi, fix
    marker'ı yoktu) - dosya kopyalama/push adımı atlanmış. O&M3'te
    GitHub'dan alınan fresh clone üzerinde yeniden uygulanıp push
    edildi.
  - **✅ CANLI DOĞRULANDI (1 Eylül 2026, O&M3):** "Peak Check Alert
    System" workflow'u `main` dalından, force modda yeniden çalıştırıldı.
    Log'da `batch_upsert hatasi` satırı ARTIK HİÇ ÇIKMIYOR. Temiz sonuç:
    `[peak_tracker] evaluate user=2 updated=5 pending=0 skipped=0
    sure=3.84s`. İlk denemede yanlışlıkla eski bir tag (`v2.0.4`, 5
    Temmuz 2026 tarihli) üzerinden çalıştırılmıştı, bu fark edilip
    `main` ile tekrarlandı - ikinci çalıştırma kesin doğrulamayı verdi.
  - **Önemli:** Bu düzeltme İLERİYE DÖNÜKTÜR - geçmişte kaçırılan uyarı
    geri getirilemez (o anki gerçek zirve kayıtlı değildi).
  - **DURUM: KAPANDI.**

- **[UYGULANDI, GERÇEK RAPORLA TEST EDİLDİ - PUSH BEKLİYOR] v2.0.7.225
  (1 Eylül 2026): HALKA ARZ OCR MOTORU DEĞİŞTİRİLDİ - OCR.SPACE ENGINE 3
  (ücretsiz, kartsız).**
  - **Süreç:** Önce ücretsiz görüntü ön-işleme (kontrast/eşikleme/
    keskinleştirme/çözünürlük artırma) denendi - GERÇEK bir sorunlu rapor
    (Kapeks Kimya/TSKB Fiyat Tespit Raporu, 68 sayfa tamamen taranmış)
    üzerinde ölçüldü, **hiçbir varyant güvenilir bir iyileşme sağlamadı**
    (bazıları mevcut sistemden daha kötü sonuç verdi - ör. keskinleştirme
    47 rakamdan 0'ını doğru buldu). Bu yaklaşım terk edildi.
  - **Bulunan gerçek çözüm:** OCR.space (ücretsiz katman: ayda 25.000
    istek Engine 1/2 + ayrıca 2.500 istek Engine 3, KREDİ KARTI
    İSTEMİYOR - Google Cloud Vision'ın aksine). Aynı test sayfasında:
    Tesseract 47 rakamdan 9'unu doğru bulurken, **OCR.space Engine 3
    47/47'sini TAM DOĞRU buldu**, üstelik çıktıyı hazır Markdown tablo
    olarak döndürdü.
  - **Uygulama (`pdf_text_extract.py`):** `_ocr_sayfa()` artık ÖNCELİKLE
    OCR.space Engine 3'ü dener (`OCRSPACE_API_KEY` ortam değişkeni/
    GitHub secret'ı gerekli); anahtar yoksa veya çağrı herhangi bir
    nedenle (ağ/kota/zaman aşımı) başarısız olursa SESSİZCE yerel
    Tesseract'a düşer - sistem hiçbir zaman "OCR hiç yapılamadı" diye
    tamamen durmaz. Yeni `_markdown_tablo_duzlestir()` fonksiyonu,
    Engine 3'ün döndürdüğü Markdown tablo satırlarını (`| a | b |`)
    mevcut regex parser'ların (`fiyat_tespit_parser.py`,
    `temel_deger_hesaplama.py`) beklediği düz, boşlukla ayrılmış metne
    çeviriyor - parser mantığı hiç değişmeden çalışmaya devam ediyor.
    Düzleştirme sonrası test sayfasında hâlâ 47/47 doğru rakam korundu.
  - **`update_data.yml`:** `OCRSPACE_API_KEY` secret'ı worker.py adımına
    env olarak eklendi. Tesseract kurulumu YEDEK yöntem olarak
    kaldırıldı değil, korundu.
  - **AÇIK - PUSH BEKLİYOR:** Bahri kendi ücretsiz OCR.space anahtarını
    aldı ve GitHub repo secret'ı olarak eklemesi gerekiyor
    (`OCRSPACE_API_KEY`). Kod değişiklikleri bu oturumda hazırlandı,
    henüz push edilmedi. Push sonrası GERÇEK bir Halka Arz adayı
    (ör. daha önce `graham=None, carpan=None` kalan biriyle) ile canlı
    doğrulama yapılmalı - test sadece tek bir izole sayfada yapıldı,
    tüm pipeline (KAP'tan indirme → OCR → parser → Supabase yazma)
    henüz uçtan uca canlı çalıştırılmadı.

- **[UYGULANDI, GERÇEK RAPORLA UÇTAN UCA DOĞRULANDI - PUSH BEKLİYOR]
  v2.0.7.226 (1 Eylül 2026): CANLI TESTTE İKİNCİ BİR SORUN BULUNDU VE
  ÇÖZÜLDÜ - FORMAT-3 (TSKB tarzı "Değerleme Özeti" kutuları) eklendi.**
  - **v2.0.7.225'in ilk canlı çalıştırması:** OCR.space çoğu sayfada
    başarıyla çalıştı (log'da onlarca "OCR.space Engine 3 kullanildi"),
    ama işlenen 4 Halka Arz adayının HİÇBİRİNDE Graham/Çarpan sonucu
    çıkmadı - hepsi `graham=None, carpan=None` olarak kaldı. Ayrıca
    çalıştırma ortasında art arda ~10 "OCR.space kullanilamadi" satırı
    görüldü (muhtemelen GitHub Actions'ın paylaşımlı IP'sinden günlük
    istek sınırına yaklaşılması) - bunun kesin nedenini görebilmek için
    hata loglaması detaylandırıldı (HTTP durum kodu / hata mesajı artık
    ayrıca yazılıyor).
  - **Kök neden (Kapeks/TSKB örneğiyle doğrulandı):** OCR artık doğru
    çalışıyor ama `temel_deger_hesaplama.py`'nin regex'leri SADECE daha
    önce görülen 2 rapor formatına göre yazılmıştı (ORZAX'ın kompakt
    "özet kutusu"su, TERA'nın tek-satırlık "FD / FAVOK <çarpan> <FAVÖK>
    <Özkaynak>" deseni). TSKB'nin araci kurumluk yaptığı bu rapor ÜÇÜNCÜ
    bir format kullanıyor: her yöntem (İNA ve Piyasa Çarpanları) kendi
    ayrı "... Değerleme Özeti" kutusuna sahip, kutunun son satırı
    doğrudan "Pay Başına Öz Sermaye Değeri - TL <X>" veriyor - hiçbiri
    eski regex'lerle eşleşmiyordu.
  - **Çözüm - yeni `_format3_hesapla()`:** "Piyasa Çarpanları Değerleme
    Özeti" başlığından sonraki dar bir pencerede (600 karakter) "Pay
    Başına Öz Sermaye Değeri" satırını arayıp doğrudan okuyor. BİLİNÇLİ
    SINIRLAMA: İNA (DCF) kutusundaki değer KULLANILMIYOR - o, raporun
    kendi DCF sonucu, Graham Sayısı (Bahri'nin bağımsız, sqrt(22,5 x EPS
    x BVPS) formülüyle hesapladığı FARKLI bir metrik) ile karıştırılmaması
    için Format-3'te Graham Değeri her zaman None kalıyor (açık notla).
  - **Uçtan uca doğrulandı:** Gerçek sayfa 59 (İNA kutusu, 172,88 TL) VE
    sayfa 64 (Piyasa Çarpanları kutusu, 80,58 TL) birlikte OCR.space
    Engine 3 ile okunup birleştirildi, Format-3 doğru şekilde SADECE
    80,58'i (Piyasa Çarpanları) seçti - 172,88'i (İNA) yanlışlıkla
    almadı. `hedef_fiyat_hesapla()`'ya özet-kutusu ve Format-2'nin İKİSİ
    de başarısız olursa devreye giren üçüncü yedek olarak eklendi.
  - **AÇIK - PUSH BEKLİYOR:** `pdf_text_extract.py` (hata loglaması) ve
    `temel_deger_hesaplama.py` (Format-3) bu oturumda hazırlandı. Push
    sonrası GERÇEK bir çalıştırmayla (TSK/Kapeks veya benzer bir aday)
    Çarpan Bazlı Değer sütununun artık dolu geldiği doğrulanmalı, ayrıca
    detaylı hata loglarıyla önceki hız sınırı şüphesinin gerçekten
    kota/hız sınırı mı olduğu netleştirilmeli.

- **[UYGULANDI - GERÇEK NEDEN CANLI LOGLA DOĞRULANDI] v2.0.7.227 (1 Eylül
  2026): OCR.space GERÇEK KOTA SINIRI BULUNDU - SAATTE 60 İSTEK (E553).**
  - **Detaylı hata loglaması (v2.0.7.226) meyvesini verdi:** Bir sonraki
    canlı çalıştırmada log artık kesin hatayı gösterdi: `E553: Rate limit
    exceeded. Max 60 requests per 3600s for Engine3 for Free Plan`.
    Reklam sayfasındaki "ayda 2.500 istek" rakamı yanıltıcıydı - gerçek
    kısıt SAATLİK. Bir Fiyat Tespit Raporu tek başına 40-70 sayfa OCR
    gerektirebildiğinden, BİR ADAY BİLE kotanın tamamını tüketebiliyor.
  - **Bu çalıştırmada ne oldu:** İlk 3 aday sırayla işlendi (kota henüz
    doluydu, OCR.space çalıştı ama yine de graham/carpan bulunamadı -
    ayrı bir konu, muhtemelen bu adayların formatı hiç tanınmıyor).
    4. aday (TSK/Kapeks - Format-3'ün gerçek doğrulandığı örnek) tam
    sırası geldiğinde kota bitmişti - yani Format-3 bu çalıştırmada HİÇ
    şansını bulamadı, yine eski/kötü Tesseract metniyle çalıştı.
  - **İYİ HABER - ekstra düzeltme gerekmedi:** `force_refresh=True`
    zaten her çalıştırmada aktif (worker.py) ve `graham_degeri` boş
    kalan kayıtları cache'ten silip yeniden deniyor (v2.0.4.18 kuralı,
    önceden mevcuttu) - yani TSK bir sonraki çalıştırmada otomatik
    tekrar denenecek, ayrı bir "yeniden dene" mekanizması eklemeye
    gerek kalmadı.
  - **Eklenen tek düzeltme - gereksiz istek israfını önleme:** Kota
    aşıldıktan sonra sistem yine de HER sayfa için OCR.space'e istek
    atıp 429 alıyordu (onlarca gereksiz ağ gecikmesi + log gürültüsü).
    Artık `_OCRSPACE_KOTA_ASILDI` modül-seviyesi bayrağı ilk 429'da
    kalkıyor, o çalıştırmanın geri kalanında OCR.space HİÇ denenmeden
    doğrudan Tesseract'a düşülüyor. Sahte 429 yanıtıyla test edildi:
    ilk çağrıda bayrak kalkıyor, ikinci çağrıda gerçek HTTP isteği HİÇ
    yapılmıyor.
  - **AÇIK - İZLENECEK:** Kota saatlik sıfırlandığı için, aynı adaylar
    hangi sırayla işleniyorsa (KAP listesi sırası) kota her seferinde
    muhtemelen aynı ilk birkaç adaya gidecek, TSK gibi sıradaki adaylar
    şanslarını yine bulamayabilir. Bu, sıra/öncelik mantığına dair daha
    büyük bir iyileştirme gerektirebilir (şimdilik ele alınmadı - kaç
    çalıştırma sonra TSK'nın gerçekten Format-3 ile denendiği takip
    edilmeli).

- **[UYGULANDI, İKİ GERÇEK RAPORLA DOĞRULANDI] v2.0.7.228 (1 Eylül 2026):
  FORMAT-3 ETİKET VARYASYONU BULUNDU VE DÜZELTİLDİ - "Pay Değeri" (kısa
  form) da destekleniyor.**
  - **Bulgu:** v2.0.7.227'nin canlı çalıştırmasında "48,1 TL / 78 sayfa"
    adayının aslında Kapeks DEĞİL, **Bewen Enerji A.Ş.** olduğu ortaya
    çıktı (ikisi de KAP'ta "TSK, TSKB" kodunu paylaşıyor - kod çakışması
    Halka Arz sayfasında ikisinin de aynı arz fiyatını göstermesine yol
    açıyor). Bewen'in raporu gerçek KAP'tan indirilip incelendi: aynı
    TSKB şablonunu kullanıyor (aynı "Piyasa Çarpanları Değerleme Özeti"
    başlığı, aynı satır düzeni) AMA son satırda Kapeks'in kullandığı
    "Pay Başına Öz Sermaye Değeri - TL" yerine SADECE **"Pay Değeri -
    TL"** yazıyor - Format-3'ün regex'i "Basina"/"Sermaye" kelimelerini
    ZORUNLU aradığı için bu varyantı hiç yakalamıyordu.
  - **Çözüm:** `_F3_PAY_BASINA_DEGER` regex'inde "Basina", "Oz", "Sermaye"
    kelimeleri OPSİYONEL yapıldı - sadece "Pay ... Değeri - TL <sayı>"
    aranıyor artık. Arama zaten dar bir pencereyle ("Piyasa Çarpanları
    Değerleme Özeti" başlığından sonraki 600 karakter) sınırlı olduğu
    için yanlış satırı yakalama riski düşük.
  - **İki gerçek raporla doğrulandı (regresyon yok):** Kapeks'in gerçek
    OCR.space metni → 80,58 (doğru, değişmedi). Bewen'in gerçek OCR.space
    metni → 51,84 (raporun kendi bastığı değerle birebir aynı - artık
    doğru çıkıyor).
  - **✅ CANLI DOĞRULANDI (1 Eylül 2026, 18:32 TRT çalıştırması):** Bewen
    Enerji için log'da `carpan=51.84` çıktı - raporun kendi bastığı
    değerle (51,84 TL) birebir aynı. Uçtan uca zincir (OCR.space Engine 3
    → Format-3 → esnetilmiş etiket regex'i → Supabase) artık gerçek
    üretimde doğrulanmış durumda. Graham Değeri bilinçli olarak boş
    kaldı (bkz. yukarı - bu formatta hesaplanmıyor).
  - **NOT:** Kapeks bu çalıştırmada işlenen 6 aday arasında değildi -
    muhtemelen "yaklaşan halka arz" listesinden düştü (halka arz süreci
    ilerlemiş olabilir). Listede kalan tek "TSK,TSKB" kodlu aday Bewen
    oldu ve o başarıyla düzeldi.
  - **AÇIK - İZLENECEK:** Bu etiket varyasyonu sorununun BAŞKA
    raporlarda da (henüz görülmemiş üçüncü bir etiket biçimi)
    çıkabileceği unutulmamalı - her yeni "gerçek adayda hâlâ None"
    durumu, muhtemelen yeni bir küçük etiket farkı anlamına geliyor,
    OCR kalitesizliği değil. OCR.space'in saatlik 60 istek kotası da
    hâlâ geçerli - bazı sayfalarda ara sıra "Read timed out" görülmeye
    devam ediyor (kota değil, ağ zaman aşımı - zararsız, Tesseract'a
    düşüyor).
  - **DURUM: KAPANDI (Bewen için). Genel Halka Arz OCR/Format konusu
    açık kalmaya devam ediyor - yeni adaylarda yeni etiket varyasyonları
    çıkabilir, göründükçe ele alınacak.**

- **[UYGULANDI, GERÇEK VERİYLE UÇTAN UCA TEST EDİLDİ - KAPSAM SINIRI
  BİLİNİYOR, PUSH BEKLİYOR] v2.0.7.229 (1 Eylül 2026): TEMETTÜ BORU HATTI
  YFINANCE'DEN KAP'A TAŞINDI.**
  - **Önceki engel çözüldü:** Geçen oturumda "KAP kategori kimliği
    (dahili hash) bulunamadı" diye yarım kalmış araştırma tamamlandı.
    KAP'ın bildirim-sorgu sayfasının kendi HTML'ine gömülü tam
    bildirim-türü/subjectOid listesi bulundu - **"Kar Payı Dağıtımı" →
    `4028328d5988e2630159d5fb51c81fe6`**. Bu hash olmadan sorgu
    tamamen filtresiz oluyor (112 farklı bildirim türü karışık dönüyor);
    doğru hash ile SADECE gerçek temettü bildirimleri geliyor.
  - **Beklenenden de iyi çıkan bir bulgu:** Bu bildirimlerin PDF eki
    bile YOK - veri doğrudan KAP API yanıtında yapılandırılmış HTML
    tablosu olarak geliyor. OCR/PDF indirme tamamen gereksiz - sadece
    BeautifulSoup ile tablo parse ediliyor.
  - **`temettu_client.py`'de yapılan değişiklik:** `_fetch_dividend_data`
    yfinance'i TAMAMEN bıraktı. Yeni akış: `_fetch_kar_payi_map()` güncel
    "Kar Payı Dağıtımı" bildirimlerini ticker koduna göre eşler,
    `_kar_payi_bildirimi_parse_et()` her bildirimin HTML gövdesini
    (`SHARE_DIVIDEND_FLEX_TABLE_*` tablolarını başlık metnine göre
    bularak - ID numaralandırmasına güvenmeden) parse edip Brüt(TL)/
    Net(TL)/Kesinleşen-Hak-Kullanım-Tarihi'ni çıkarır. Bildirim detayları
    disclosure_index başına SÜRESİZ önbelleklenir (Fiyat Tespit Raporu
    önbelleğiyle aynı ilke - yayınlanmış bildirim değişmez).
  - **ÖNEMLİ - verim (%) hesabı düzeltildi:** KAP'ın kendi "Brüt(%)"
    alanı **1 TL nominal değere göredir, PİYASA FİYATINA GÖRE DEĞİL**
    (TBORG örneğinde "%952" gibi anlamsız görünen bir sayı çıkıyor -
    aslında 9,52 TL / 1 TL nominal = %952 demek). Bu yüzden verim
    HER ZAMAN kendimiz hesaplanıyor: Brüt TL / güncel piyasa fiyatı.
  - **Gerçek veriyle uçtan uca doğrulandı:** TBORG (gerçek bildirim,
    idx=1654862) → brüt=9,5209 TL, ex_date=02.09.2026 (Kesinleşen Hak
    Kullanım Tarihi) - haber sitelerinde yayınlanan gerçek değerlerle
    birebir eşleşti. KAPLM ve ESCOM (ikisi de "dağıtılmayacak" kararı
    almış) → doğru şekilde 0 döndü, hata vermedi - şirketin gerçekten
    temettü dağıtmama kararını doğru yorumluyor.
  - **⚠️ AÇIK - KAPSAM SINIRI (önemli):** KAP'ın bildirim-sorgu-sonuc uç
    noktası, denenen HİÇBİR parametreyle (fromDate/toDate/ps/pageSize/
    count/limit vb. - hepsi denendi) 29 kaydı aşmadı. KAP'ın kendi
    sitesindeki bir not, arama ÖNERİLERİNİN (autocomplete) varsayılan
    olarak "geçmişe dönük 30 günlük dönem" ile sınırlı olduğunu ve daha
    geniş aralık için "detaylı sorgulama" gerektiğini söylüyor - ama bu
    ayrı sayfa/mekanizma bulunamadı (muhtemelen gerçek form gönderimi
    farklı bir POST/parametre seti kullanıyor, tarayıcı ile form
    doldurup gerçek isteği yakalamak gerekebilir). SONUÇ: Türkiye'de
    temettüler çoğunlukla Mart-Haziran'da açıklandığından, Eylül'de bu
    "son ~30 gün" penceresi çoğu şirketin ilgili bildirimini
    KAÇIRIYOR - canlı testte XTMTU'nun 25 üyesinden 0'ı bu pencereye
    denk geldi. Mekanizma DOĞRU ÇALIŞIYOR (TBORG/KAPLM/ESCOM ile
    doğrulandı) ama PRATİK KAPSAM şu an düşük. Zamanla (yeni bildirimler
    geldikçe, veya gelecek yılın Şub-Haz döneminde) organik olarak
    dolacak. yfinance'e GERİ DÖNÜLMEDİ (Bahri'nin açık talebi) -
    kapsam dışı kalan hisseler satırda sessizce boş kalıyor.
  - **DURUM: v2.0.7.230 ile ÇÖZÜLDÜ (aşağıya bkz.) - kapsam sınırı
    ortadan kalktı.**

- **[UYGULANDI, GERÇEK VERİYLE UÇTAN UCA DOĞRULANDI - PUSH BEKLİYOR]
  v2.0.7.230 (1 Eylül 2026): KAPSAM SINIRI TAMAMEN ÇÖZÜLDÜ - Bahri'nin
  Chrome DevTools ile bulduğu GERÇEK KAP API'si + kritik çoklu-pay-grubu
  hatası düzeltildi.**
  - **Kapsam sınırı çözümü:** Bahri, Chrome DevTools bağlantı sorunları
    nedeniyle KAP'ın "Detaylı Sorgulama" sayfasında Network sekmesini
    kendisi inceledi ve GERÇEK arama API'sini buldu:
    `POST https://www.kap.org.tr/tr/api/disclosure/members/byCriteria`
    - JSON gövdeli, `fromDate`/`toDate` (YYYY-MM-DD) ve `subjectList`
    (subjectOid dizisi) destekli TAM sorgu, sayfalama/kısıtlama YOK.
    v2.0.7.229'da kullanılan GET `bildirim-sorgu-sonuc` uç noktasının
    aslında sitenin arama kutusu OTOMATİK TAMAMLAMA özelliği olduğu
    ortaya çıktı (KAP'ın kendi sayfasındaki bir not bunun "geçmişe
    dönük 30 gün"le sınırlı olduğunu doğruluyordu). Yeni API ile test:
    2026-01-01→2026-09-01 aralığında **1233 kayıt**, XTMTU'nun 25
    üyesinin **TAMAMI (25/25)** bulundu (önceki yöntemde 0/25). Kod
    artık kayan 12 aylık pencere kullanıyor (`KAP_KAR_PAYI_GERI_GUN`).
    Ayrıca bu, geçen oturumun ORİJİNAL araştırmasının bulduğu tam
    başlığı ("Kar Payı Dağıtım İşlemlerine İlişkin Bildirim") API
    yanıtındaki `subject` alanında birebir doğruladı.
  - **Kritik ikinci hata bulundu ve düzeltildi (canlı testte):** İlk
    tam çalıştırmada 25/25 hisse dolu geldi ama ISCTR (Türkiye İş
    Bankası) **%368 verim** gösterdi - açıkça yanlış. Kök neden: İş
    Bankası'nın TEK bir bildiriminde 4 farklı pay grubu var (A/ISATR,
    B/ISBTR, C/ISCTR, ISKUR), HER BİRİNİN kâr payı tutarı FARKLI
    (ISATR: 46,92 TL, ISCTR: sadece 0,54 TL). Eski kod "İşlem
    Görmüyor" olmayan İLK pozitif satırı alıyordu - ISCTR sorgulanırken
    yanlışlıkla ISATR'ın (46,92 TL) değerini alıyordu. **Düzeltme:**
    `_kar_payi_bildirimi_parse_et()` artık `ticker` parametresi alıyor,
    "Pay Grup Bilgileri" hücresinde TİCKER'IN TAM OLARAK eşleştiği
    satırı önceliklendiriyor (virgülle ayrılmış parçalardan biri birebir
    eşleşmeli - kısmi/yanlış eşleşme riski yok), sadece eşleşme
    bulunamazsa eski "ilk pozitif satır" yedeğine düşüyor. Önbellek
    anahtarı da `disclosure_index` yerine `disclosure_index:ticker`
    yapıldı (aynı bildirim farklı ticker'lar için farklı değer verebilir).
  - **Son doğrulama:** Temiz önbellekle sıfırdan çalıştırıldı - XTMTU'nun
    25 üyesinin TAMAMI dolu, verimler %0,49 (BIMAS) ile %9,98 (BRYAT)
    arasında GERÇEKÇİ bir aralıkta. ISCTR düzeltme sonrası %4,23 (bankalar
    için makul). TCELL "Yaklaşıyor" durumunda (09.12.2026), geri kalan
    24'ü "Geçti" (referans/geçmiş bilgi olarak listede kalıyor - sayfanın
    var olan sıralama/durum mantığı hiç değiştirilmedi).
  - **DURUM: Temettü boru hattı artık tam, doğru ve kapsamlı çalışıyor.**

- **[UYGULANDI, CANLI TEST EDİLDİ - PUSH BEKLİYOR] v2.0.7.231 (1 Eylül
  2026, Bahri'nin talebi — "dil önemli değil, önemli olan dünyaca kabul
  gören güvenilir kaynaklardan çok sayıda haber almamız"): HABER
  KAYNAKLARI TEMİZLENDİ VE GENİŞLETİLDİ.**
  - **5 "beklemede" kaynak GERÇEKTEN test edildi, hepsi ÇALIŞMADIĞI
    bulundu:** Kathimerini, El País, Kyodo News, Ouest-France → HTTP 403
    (bot koruması/Cloudflare). PBS NewsHour → HTTP 202 + `x-amzn-waf-
    action: challenge` (AWS WAF JS/CAPTCHA duvarı). Bu 5'i koddan
    ÇIKARILDI - hem yerel test ortamında hem gerçek GitHub Actions
    ortamında (ikisi de bulut/veri merkezi IP'si) aynı şekilde
    engellenecekleri için "eklendi" görünüp sessizce hiç katkı
    sağlamamaları yerine dürüstçe kaldırıldılar. Meduza (aynı turdan)
    CANLI TEST EDİLDİ, çalışıyor - kaldı.
  - **3 yeni kaynak bulundu, canlı test edildi, eklendi:**
    - **CBC Business** (Kanada) - CBC, Broadcasting Act ile yasal
      güvenceli editoryal bağımsızlığa sahip kamu yayıncısı (BBC ile
      aynı model). Gerçek iş dünyası içeriği doğrulandı.
    - **Yle News** (Finlandiya, İngilizce akış) - Yle, ayrı bir "Yle
      vergisi"yle finanse edilen, basın özgürlüğü endekslerinde
      dünyada sürekli ilk sıralarda olan kamu yayıncısı. Fince genel
      akış yerine İngilizce, ekonomiye daha alakalı akış seçildi.
    - **RTÉ Business** (İrlanda) - İrlanda'nın lisans ücretiyle
      finanse edilen, yasal bağımsız kamu yayıncısı. En alakalı yeni
      akışlardan biri (doğrudan enflasyon/merkez bankası/sanayi
      içeriği).
  - **Denenip ELENEN adaylar (bu turda):** Associated Press (rsshub.app
    proxy'si de dahil, 403), The Guardian Business (403), Deutsche Welle
    (3 farklı URL denendi, hepsi 403), NHK World (403), Franceinfo
    Eco (403), Der Spiegel International (403), The Hindu Business
    (403), SWI swissinfo.ch (410 - feed kaldırılmış), Korea Herald
    Business (200 ama 0 kayıt - feed formatı bozuk/boş).
  - **Güncel durum: 19 aktif kaynak** (21'den 5 çıkarıldı, 3 eklendi).
  - **SONRAKİ OTURUMDA (istenirse):** Kapsanmayan büyük bölgeler hâlâ
    var - Güney Amerika, Afrika, Güneydoğu Asya, Hindistan (The Hindu
    denendi/başarısız oldu, başka aday aranabilir), Çin/Arapça
    (Bahri'nin notu: öncelikli değil ama iyi bir bağımsız aday çıkarsa
    eklenebilir - ör. Initium Media (端傳媒, Çince, Hong Kong merkezli
    bağımsız) veya Daraj/Independent Arabia (Arapça) denenebilir).

  EDİLMEDİ] v2.0.7.221 (31 Ağustos 2026, Bahri'nin talebi — "Halka Arz
  sayfasında Graham Değeri ve Çarpan Bazlı Değer sütunlarının boş
  kalması sorun, bu değerlerin tabloda görünmesini sağla"): ORTA
  SAYFALARA DA OCR UYGULANIYOR - KESİN KÖK NEDEN BULUNDU.**
  - **Kesin kök neden:** `upcoming_ipo_client.py`'nin "orta sayfa"
    (Format-2) tarama mantığı, metin katmanı OLMAYAN (taranmış/görsel)
    sayfaları BİLEREK OCR'sız atlıyordu ("maliyet düşük olsun" diye,
    v2.0.6'dan beri). Ama TAM OLARAK Bilanço/Gelir Tablosu gibi kritik
    finansal tablolar (Graham/Çarpan hesaplaması için gereken veri),
    çoğu izahnamede SAYFA GÖRÜNTÜSÜ (taranmış) olarak raporun ORTASINA
    gömülü (ör. TERA'da 83 sayfalık raporun 63-66. sayfaları) - bu
    yüzden bu veri hiç okunamıyordu, sütunlar sürekli boş kalıyordu.
  - **Doğrulama:** `requirements.txt`'te `pytesseract` var, GitHub
    Actions workflow'u (`update_data.yml`) `tesseract-ocr` VE
    `tesseract-ocr-tur` sistem paketlerini doğru şekilde kuruyor -
    OCR ALTYAPISI TAMDI, sadece orta sayfalar için KULLANILMIYORDU.
    OCR fonksiyonunun kendisi (`pdf_text_extract.py`'deki `_ocr_sayfa`)
    zaten "son N sayfa" taramasında kullanılıyordu - aynı fonksiyon
    artık orta sayfalar için de çağrılıyor.
  - **Çözüm:** Orta sayfa döngüsündeki `else: continue` (atla)
    `else: orta_parcalar.append(_ocr_sayfa(sayfa))` ile değiştirildi -
    artık hiçbir sayfa (ilk/orta/son fark etmeksizin) OCR'sız
    atlanmıyor.
  - **Bahri'nin bilerek kabul ettiği maliyet:** Bu, işlem süresini
    artırır (bir raporda onlarca orta sayfa OCR gerektirebilir) -
    Bahri doğruluğun maliyetten/hızdan önemli olduğunu belirtti,
    bilerek bir üst sınır (cap) EKLENMEDİ.
  - **AÇIK - CANLI TEST EDİLMEDİ:** Gerçek bir KAP izahnamesi indirip
    OCR çalıştırmak bu ortamda pratik değildi - sadece kod mantığı
    (son-sayfa mantığıyla birebir aynı desen) ve derleme doğrulandı.
    Etkiyi görmek için `worker.py`'nin bir sonraki çalışmasını (gece
    otomatik ya da elle "Run workflow") beklemek/tetiklemek gerekiyor -
    Graham/Çarpan sütunlarının o çalışmadan sonra dolup dolmadığı
    kontrol edilmeli.


  kendi ortamımdan)] v2.0.7.220 (31 Ağustos 2026, Bahri'nin bulgusu —
  Temettü sayfasında AKBNK, BIMAS, CCOLA gibi bilinen temettü ödeyen
  şirketler bile "0,0000 / %0,00" gösteriyordu, "Zorla Yenile" bile
  düzeltmiyordu): TEMETTÜ VERİSİ ÇEKME MANTIĞI DÜZELTİLDİ, AMA KÖK
  NEDEN TAM KESİNLEŞMEDİ.**
  - **Bulunan 3 sorun (`temettu_client.py`'deki `_fetch_dividend_data`):**
    (1) BİRİM YORUMLAMA HATASI - eski kod yfinance'in `dividendYield`
    alanını bir ORAN (0.03=%3) sanıp `0 < div_yield <= 0.6` kontrolü
    yapıyordu - canlı test (31 Ağustos, kendi ortamımdan) yfinance'in
    bunu ARTIK DOĞRUDAN YÜZDE (3.01=%3,01) döndürdüğünü gösterdi.
    Düzeltildi - artık HER İKİ format da otomatik algılanıyor.
    (2) SESSİZ HATA YUTMA - eski `except: pass` hiçbir iz bırakmıyordu.
    Artık hata `print` ile loglanıyor. (3) YENİDEN DENEME YOK - artık
    2 deneme var, aralarında 2 saniyelik bekleme.
  - **DÜRÜSTLÜK NOTU - kök neden TAM olarak kesinleşmedi:** Kendi
    ortamımdan yapılan canlı test (AKBNK için dividendRate=2.2,
    dividendYield=3.01 başarıyla geldi) BİRİM HATASINI doğruladı, AMA
    matematiksel olarak eski kod BİLE (yedek hesaplama yoluyla)
    dividendRate=2.2 başarıyla çekilmiş olsaydı sıfırdan farklı bir
    sonuç vermeliydi. Bahri'nin gördüğü TAM SIFIR sonucu, `.info`
    çağrısının Streamlit Cloud'dan TAMAMEN BAŞARISIZ OLDUĞUNA
    (Yahoo Finance'in bulut IP'lerini engellemesi - yfinance'in çok
    bilinen bir sorunu) işaret ediyor - bu, benim ortamımdan
    DOĞRULANAMAZ (farklı IP aralığı). Eklenen hata loglama sayesinde,
    sorun DEVAM EDERSE sunucu loglarında gerçek hata görünecek.
  - **AÇIK - Bahri'nin push sonrası tekrar test edip sonucu bildirmesi
    gerekiyor.** Eğer hâlâ sıfır geliyorsa, bir sonraki adım
    muhtemelen yfinance yerine farklı bir veri kaynağına (KAP,
    Investing.com API vb.) geçmek olacaktır.

- **[UYGULANDI, YAML+ZAMAN DÖNÜŞÜMÜ DOĞRULANDI, CANLI TEST EDİLMEDİ]
  v2.0.7.218 (30 Ağustos 2026, Bahri'nin bulgusu — saat 09:03'te ING
  bankadaki gerçek portföy değeri (27.889,12 TL) ile uygulamanın
  gösterdiği değer (27.869,55 TL) arasında ~19,57 TL fark bulundu):
  TEFAS SABAH KONTROL PENCERESİ SIKLAŞTIRILDI.**
  - **Kesin kök neden:** Bahri'nin gözlemi TAM OLARAK 08:00
    çalışmasından SONRA, 10:00 çalışmasından ÖNCE yapılmıştı (v2.0.7.165'te
    kurulan 2 saatlik aralık - TRT 08/10/12/14/16/18/20). TEFAS
    muhtemelen bu ~1 saatlik pencerede yeni NAV yayınlamıştı, sistem
    ancak 10:00'da yakalayacaktı - en fazla ~2 saatlik gecikme riski.
  - **Çözüm (`update_tefas_evening.yml`):** Sabah penceresi (TRT
    07:00-09:30) artık 30 DAKİKADA BİR kontrol ediliyor (6 kontrol:
    07:00, 07:30, 08:00, 08:30, 09:00, 09:30) - Bahri'nin istediği
    "sabah 08:00 civarında bir güncelleme daha" isteği bu şekilde
    fazlasıyla karşılandı. Günün geri kalanı (TRT 10-20) eski 2
    saatlik aralıkta bırakıldı - günde toplam 7 çalışmadan 12
    çalışmaya çıkıldı. Var olan "birincil + 2 dakika offsetli yedek"
    cron çifti mantığı hem sabah hem gündüz pencereleri için korundu.
  - **Maliyet notu:** düşük - `update_tefas_evening.py` zaten SADECE
    değişiklik varsa commit/push atıyor ("git diff --cached --quiet"
    kontrolü) - değişiklik yoksa maliyet sadece ~1 GitHub Actions
    dakikası.
  - **Doğrulandı:** UTC→TRT zaman dönüşümleri Python'da izole test
    edildi - sabah penceresi tam olarak 07:00-09:30 arası 30 dk
    aralıkla, gündüz penceresi tam olarak 10:00-20:00 arası 2 saatte
    bir olduğu doğrulandı. YAML dosyası `yaml.safe_load()` ile
    sözdizimi olarak da doğrulandı.


  (29 Ağustos 2026, Bahri'nin sorusu — "üç, dört, beş, altı kaynak
  olması halinde pop-up bunları da gösterebilecek mi?"): ARTIK
  SINIRSIZ SAYIDA TEYİT EDEN KAYNAK DESTEKLENİYOR.**
  - **Kesin kök neden:** `db.py`'deki eşleştirme döngüsü, ilk eşleşen
    teyidi bulur bulmaz `break` ile aramayı durduruyordu - 5-6 kaynak
    aynı haberi doğrulasa bile SADECE İLKİ yakalanıyordu, `teyit_kaynak`
    tekil bir alandı (en fazla 1 teyit tutabiliyordu).
  - **Çözüm (db.py):** `break` kaldırıldı, döngü artık TÜM eşleşen
    FARKLI kaynakları topluyor (aynı kaynaktan birden fazla makale
    varsa bile o kaynak sadece BİR KEZ sayılıyor - `_teyit_eden_
    kaynaklar` seti ile). Sonuç `teyit_kaynak`/`teyit_baslik`/
    `teyit_url` (tekil alanlar) yerine tek bir `teyit_listesi`
    (sözlük listesi) alanında dönüyor.
  - **Çözüm (app.py):** Yeni `_turkce_liste_birlestir()` yardımcısı -
    ['A'] → "A", ['A','B'] → "A ve B", ['A','B','C'] → "A, B ve C".
    `_cok_kaynakli_cumle_olustur()` artık `teyit_listesi` alıp TÜM
    teyit eden kaynakların isimlerini doğal bir Türkçe listede
    cümleye ekliyor ("...X, Y ve Z kaynaklarından da teyit edilen
    habere göre..."), tekil/çoğul "kaynağından"/"kaynaklarından" eki
    de sayıya göre doğru seçiliyor. `_kaynak_bolumu_goster()` de
    listedeki HER kaynağı 2, 3, 4... şeklinde numaralandırıyor - url'i
    olmayan bir kaynak (v2.0.7.216'nın dayanıklılık düzeltmesi
    korunarak) düz metin, olan link olarak gösteriliyor.
  - **İzole test edildi:** 1 teyitli senaryo (eski davranış
    bozulmadı) ve 3 teyitli senaryo (biri url'siz, karışık) - cümle
    "ABC News Australia, NPR Business ve Sky News kaynaklarından da
    teyit edilen" şeklinde doğru birleşti, Kaynaklar listesi 1'den
    4'e kadar doğru numaralandı, url'siz olan doğru şekilde düz metin
    kaldı.


  2026, Bahri'nin bulgusu — canlıda "Kaynak:" bölümü hâlâ tek kaynak
  gösteriyordu, cümle iki kaynaktan bahsetmesine rağmen): KESİN KÖK
  NEDEN BULUNDU VE DÜZELTİLDİ - KAYNAK LİSTESİ ARTIK DAHA DAYANIKLI.**
  - **Kesin kök neden:** v2.0.7.215'in `_kaynak_bolumu_goster()`
    fonksiyonu hem `teyit_kaynak` HEM `teyit_url` ikisinin de dolu
    olmasını ŞART koşuyordu. Teyit eden makalenin `haber_url`'i
    boşsa (nadir bir veri eksikliği), İKİNCİ KAYNAK TAMAMEN
    GİZLENİYORDU - halbuki ana cümle (`_cok_kaynakli_cumle_olustur`,
    SADECE `teyit_kaynak`'a bakıyor) zaten iki kaynaktan bahsediyordu.
    Bu, cümle "2 kaynak" derken Kaynak listesinin "1 kaynak"
    göstermesi gibi bir TUTARSIZLIK yaratıyordu.
  - **Çözüm:** Artık SADECE `teyit_kaynak` yeterli - `teyit_url`
    varsa link, yoksa DÜZ METİN olarak gösteriliyor ama İKİNCİ
    KAYNAK HER ZAMAN görünüyor. Başlık da "Kaynak" yerine
    **"Kaynaklar"** (çoğul) olarak değiştirildi, 2+ kaynak olduğunda.
  - **Ek düzeltme:** Ana cümledeki "...kaynağından da **tespit
    edilen** habere göre" → "...kaynağından da **teyit edilen**
    habere göre" (Bahri'nin talebi - anlamsal olarak daha doğru,
    ikinci kaynak haberi yeniden TESPİT etmiyor, TEYİT ediyor).
  - **İzole test edildi (3 senaryo):** Bahri'nin GERÇEK yaşadığı durum
    (teyit_kaynak var, teyit_url yok) → artık ikinci kaynak düz metin
    olarak görünüyor (eskiden tamamen gizleniyordu); normal durum
    (ikisi de dolu) → ikisi de tıklanabilir link; teyit yok → tekil
    "Kaynak:" başlığı kullanılıyor. Hem modal hem Ana Sayfa listesi
    AYNI paylaşımlı fonksiyonu kullandığı için tek bir düzeltme
    ikisini de kapsadı.


  (29 Ağustos 2026, Bahri'nin talebi — "ikinci kaynağı sadece 'Ayrıca...'
  yazısında değil, ana cümlenin başında ve Kaynak listesinde numaralı
  olarak görmek istiyorum"): ÇOKLU KAYNAK TEYİDİ ARTIK ANA CÜMLEDE VE
  NUMARALI KAYNAK LİSTESİNDE GÖSTERİLİYOR.**
  - **Sorun:** v2.0.7.209'da teyit eden ikinci kaynak eklenmişti ama
    sadece ayrı, ikincil bir "Ayrıca..." satırında - ana cümle SADECE
    birincil kaynaktan bahsediyordu, Kaynak bölümü de tek link
    gösteriyordu.
  - **Çözüm 1 - Ana cümle:** Yeni `_cok_kaynakli_cumle_olustur()`
    fonksiyonu, AI'nın ürettiği "{kaynak} kaynağından alınan habere
    göre" ifadesini basit bir METİN İKAMESİYLE (AI'ya tekrar
    sormadan) "{kaynak}'den alınan ve {teyit_kaynak} kaynağından da
    tespit edilen habere göre" haline getiriyor.
  - **Çözüm 2 - Kaynak listesi:** Yeni `_kaynak_bolumu_goster()`
    fonksiyonu, teyit varsa "Kaynak: 1- [...] 2- [...]" şeklinde
    NUMARALI, İKİSİ DE TIKLANABİLİR bir liste gösteriyor (eskiden
    sadece birincil kaynak tıklanabilirdi, ikincisi düz metindi).
  - **DB değişikliği:** `get_bekleyen_tespitler()` artık teyit eden
    ikinci makalenin `haber_url`'ini de yakalayıp `teyit_url` olarak
    döndürüyor (eskiden sadece kaynak adı + başlık vardı, link yoktu).
  - **KRİTİK YAPISAL HATA BULUNDU VE DÜZELTİLDİ (kendi hatam):** İlk
    düzenlemede yeni yardımcı fonksiyonlar yanlışlıkla `@st.dialog(...)`
    dekoratörü İLE `_tespit_onay_modali()` fonksiyonu ARASINA
    eklenmişti - bu, dekoratörün YANLIŞ fonksiyona (yeni yardımcı
    fonksiyona) uygulanmasına yol açıyordu, modal tamamen bozulurdu.
    Fark edilip dekoratör doğru fonksiyonun hemen üstüne taşındı.
  - **İzole test edildi (Bahri'nin GERÇEK ekran görüntüsündeki
    örnekle):** "Dünya Gazetesi kaynağından alınan habere göre..."
    cümlesi, "Dünya Gazetesi'den alınan ve ABC News Australia
    kaynağından da tespit edilen habere göre..." haline doğru şekilde
    dönüştü, cümlenin geri kalanı (somut detaylar) bozulmadı. Teyit
    yoksa cümlenin değişmediği de doğrulandı.
  - Hem modal dialog hem Ana Sayfa listesi AYNI iki ortak fonksiyonu
    kullanıyor - kod tekrarı yok, ikisi de tutarlı.


  talebi — "Abonelik Ayarları'na profil bilgileri, iletişim bilgileri,
  şifre değişikliği eklensin, kalıp ayarları eskisi gibi admin
  panelinde kalsın"): ABONELİK SAYFASINA HESAP YÖNETİMİ EKLENDİ.**
  - **ÖNEMLİ NETLEŞME (Bahri'nin kendi düzeltmesi):** İlk istekte
    Kalıp Yönetimi/Haber Akışı Bakımı gibi TÜM admin ayarlarının
    Abonelik Ayarları'na taşınması istenmiş gibi görünüyordu - Bahri'ye
    bunun iki çok farklı anlama gelebileceği (A: sadece admin görsün
    tek sayfada, B: her abone tam düzenleme yetkisi kazansın)
    AÇIKÇA soruldu. Bahri NETLEŞTİRDİ: Kalıp Yönetimi ESKİSİ GİBİ
    admin panelinde kalacak, DEĞİŞMEYECEK - Abonelik Ayarları'na
    SADECE hesaba özel ayarlar (profil/iletişim/şifre) eklenecek.
  - **Yeni DB sütunu:** `users` tablosuna `phone_number` eklendi
    (idempotent migration).
  - **Yeni auth.py fonksiyonları:** `kullanici_profil_guncelle
    (kullanici_id, full_name, phone_number)` ve `kullanici_sifre_
    degistir(kullanici_id, eski_sifre, yeni_sifre)` - ikincisi ÖNCE
    mevcut şifrenin doğru olduğunu `verify_password()` ile doğruluyor,
    sonra `hash_password()` ile yeni şifreyi kaydediyor.
  - **Abonelik sayfasına 3 yeni bölüm:** Profil Bilgileri (ad-soyad +
    telefon, form), İletişim Bilgileri (e-posta SADECE GÖRÜNTÜLENİYOR
    - güvenlik nedeniyle bu sayfadan değiştirilemiyor, admin ile
    iletişime geçilmesi gerekiyor), Şifre Değiştir (mevcut+yeni+tekrar,
    form). Her kullanıcı SADECE KENDİ hesabını yönetiyor.
  - **İzole test edildi:** şifre doğrulama mantığı - doğru eski şifre
    kabul, yanlış eski şifre red, değişim sonrası eski şifre geçersiz/
    yeni şifre geçerli. Tüm dosyalar (`app.py`, `auth.py`, `db.py`,
    `haber_izleme.py`) `py_compile` ile doğrulandı.


  sorusu — "Al Jazeera'yı hep duyuyorum ama bizim kriterlerimize uyan
  güvenilir bir kaynak mıdır bilmiyorum"): AL JAZEERA KALDIRILDI -
  AA EKONOMİ'DEN BİLE DAHA NET BİR DEVLET KONTROLÜ ÖRNEĞİ.**
  - **Araştırma sonucu:** Al Jazeera Media Network doğrudan **Katar
    Emiri Şeyh Tamim bin Hamad Al Thani'ye ait** (kişisel mülkiyetinde).
    Yönetim Kurulu Başkanı hükümdar ailesi Al Thani'nin kıdemli bir
    üyesi. Kurul atamaları Bakanlar Kurulu tarafından yapılıp **Emir
    tarafından onaylanıyor**. ABD Adalet Bakanlığı ağın "Katar hükümeti
    tarafından kontrol edildiği ve finanse edildiği"ni resmi olarak
    tespit etmiş. Wikipedia Al Jazeera Arabic'i doğrudan "state-funded"
    olarak sınıflandırıyor. Bu, BBC'nin bağımsız denetimli lisans
    ücreti modelinden ÇOK FARKLI - fonlama VE yönetim doğrudan hükümdar
    aileye bağlı, yapısal olarak AA Ekonomi'den bile daha net bir
    devlet kontrolü örneği.
  - **Önemli bağlam:** Al Jazeera bu projenin EN BAŞINDAN BERİ (18
    Ağustos 2026, tarafsızlık ilkesi belirlenmeden ÇOK ÖNCE) kaynak
    listesindeydi - bu bulguyla ilk kez gözden geçirildi.
  - **Kod değişikliği:** `_RSS_KAYNAKLARI`'ndan ve
    `_CEVIRI_GEREKEN_KAYNAKLAR`'dan kaldırıldı. `app.py`'deki kaynak
    listesi metni güncellendi.
  - **İzole test edildi:** 19 kaynağın tümü doğru yapılandırılmış, Al
    Jazeera hem RSS listesinde hem çeviri kümesinde tamamen yok, AA
    Ekonomi yanlışlıkla geri gelmemiş, hiçbir tekrar yok.


  talebi — çok dilli tarafsız kaynak araştırmasının İKİNCİ (kalan
  diller) turu): 4 YENİ KAYNAK EKLENDİ (20 TOPLAM KAYNAK).**
  - **Kapsamlı araştırma yapıldı** (Yunanistan, İspanya, Japonya, Çin,
    Arap dünyası, Rusya) - her aday için sahiplik yapısı özellikle
    araştırıldı. **Reddedilenler:** EFE (İspanyol devletine tam bağlı,
    AA Ekonomi ile aynı profil), Al Jazeera Arabic (Katar devlet
    fonlu - Wikipedia'da açıkça "state-funded" yazıyor), Middle East
    Eye (şeffaf olmayan finansman + çok kaynaklı, güvenilir gizli
    Katar/Hamas bağlantısı iddiaları - açık bir devlet ajansından
    bile daha sorunlu), Focus Taiwan (Tayvan hükümetine/Executive
    Yuan'a ait). **Çince için temiz bir aday bulunamadı** - SCMP
    (Alibaba sahipliğinde, İngilizce) en az sorunlu alternatif ama
    Çince değil, eklenmedi.
  - **Eklenen 4 kaynak (Bahri'nin onayıyla):**
    - **Meduza** (Rusça) - `meduza.io/rss/all` - **CANLI TEST EDİLDİ,
      ÇALIŞIYOR**. Rus devleti tarafından TAMAMEN YASAKLANMIŞ,
      Riga'dan (Letonya) sürgünde yayın yapıyor - bağımsızlığı şüphe
      götürmez. Dürüstlük notu: içerik güçlü Kremlin-karşıtı bir
      editoryal duruş taşıyor (anlaşılır, kendisi zulüm görmüş) -
      "hükümetin sesi olmama" testini kesinlikle geçiyor ama "taraf
      tutmama" anlamında tek yönlü.
    - **Kathimerini** (Yunanca) - `ekathimerini.com/infeeds/rss/
      nx-rss-feed.xml` - kendi test ortamında domain kısıtlaması
      nedeniyle DOĞRUDAN test edilemedi (BBC/Sky gibi). Özel aile
      şirketi (Alafouzos) sahipliğinde, Yunanistan'ın en saygın
      "kayıt gazetesi" - Wikipedia "merkez-sağ" olarak tanımlıyor.
    - **El País** (İspanyolca) - `feeds.elpais.com/mrss-s/pages/ep/
      site/elpais.com/portada` - aynı araç kısıtlaması, doğrudan
      test edilemedi. Özel medya grubu (PRISA) sahipliğinde - EFE
      YERİNE seçildi. Wikipedia "merkez-sol" olarak tanımlıyor.
    - **Kyodo News** (Japonca) - `english.kyodonews.net/rss/all.xml` -
      aynı araç kısıtlaması. Kâr amacı gütmeyen kooperatif (56 Japon
      gazetesi + 111 yayın kuruluşunun üye aidatlarıyla finanse
      ediliyor) - eski devlet ajansı Dōmei'nin YERİNE 1945'te
      kurulmuş, devletten bağımsız olması özellikle tasarlanmış.
  - **Kod değişikliği:** 4 kaynak da `_CEVIRI_GEREKEN_KAYNAKLAR`'a
    eklendi (hepsi Türkçe değil). `app.py`'deki kaynak listesi metni
    güncellendi.
  - **İzole test edildi:** 20 kaynağın tümü doğru yapılandırılmış,
    hepsi benzersiz (tekrar yok), 4 yeni kaynağın hepsi hem RSS
    listesinde hem çeviri kümesinde.
  - **AÇIK - canlı doğrulama bekleniyor:** Kathimerini, El País, Kyodo
    News'ün gerçekten çalışıp çalışmadığı bir sonraki haber
    taramasının log'unda görülmeli (Meduza zaten doğrudan doğrulandı).


  (29 Ağustos 2026, Bahri'nin bulgusu — "pop-up'ın en az iki kaynaktan
  doğrulanmış olması VE yüksek şiddette olması kuralıydı, gelen
  pop-up'larda bu kuralların uygulanmadığını görüyorum"): İKİ GERÇEK
  EKSİKLİK BULUNDU VE DÜZELTİLDİ.**
  - **Eksiklik 1 - "Yüksek şiddet" hiçbir zaman pop-up şartı DEĞİLDİ:**
    Bu kural sadece AYRI bir özellik olan toplu onayın ("Tümünü
    Onayla") 3 kriterinden biriydi - tekil pop-up gösterimini hiç
    kısıtlamıyordu. Bahri'nin ORİJİNAL isteği ("çok yüksek risk
    taşıyan... olsun, diğerlerini pop-up yapma") aslında POP-UP'IN
    KENDİSİ için bir şarttı. **Çözüm:** `get_bekleyen_tespitler()`'in
    SQL'ine `AND t1.siddet = 'Yüksek'` eklendi - Orta/Düşük şiddetteki
    tespitler artık HİÇ pop-up olarak çıkmıyor.
  - **Eksiklik 2 - çoklu kaynak teyidi GÖRÜNMEZDİ:** Teyit arka planda
    doğru çalışıyordu (v2.0.7.199/200) ama modal/liste SADECE tespitin
    KENDİ tek kaynağını gösteriyordu - teyit eden İKİNCİ kaynak hiç
    görünmüyordu. Bu, Bahri'ye "teyit hiç yapılmamış" izlenimi
    veriyordu. **Çözüm:** `get_bekleyen_tespitler()` artık her tespit
    sözlüğüne `teyit_kaynak`/`teyit_baslik` alanlarını da ekliyor;
    hem modal dialog hem Ana Sayfa listesi artık "Ayrıca [X] kaynağından
    '...' haberiyle de teyit edildi" satırını gösteriyor.
  - **İzole test edildi:** Yüksek+teyitli iki tespit (gerçekten aynı
    olay, farklı kaynak, doğrulanmış 0.714 benzerlik) → ikisi de
    gösterildi; Orta şiddetli bir tespit → hiç değerlendirilmedi;
    Yüksek ama teyitsiz bir tespit → gösterilmedi. Beklenen sonuç
    tam olarak elde edildi.
  - **Yan etki (zararsız):** Bulk onayın 3 kriterinden ikisi (Yüksek +
    çoklu kaynak) artık bu noktaya ulaşan HER tespit için otomatik
    sağlanmış oluyor - tek gerçek ayırt edici kalan kriter kalıbın
    "istatistiksel dayanak" bayrağı. Bu bir hata değil, doğal bir
    sadeleşme.


  talebi — çok dilli, tarafsız kaynak araştırmasının İLK SONUÇLARI):
  2 YENİ KAYNAK EKLENDİ (16 TOPLAM KAYNAK) - KALAN DİLLER SONRAKİ
  TURA BIRAKILDI.**
  - **Kapsamlı araştırma yapıldı** (Fransa, Yunanistan, İtalya,
    İspanya) - her aday için SAHİPLİK YAPISI özellikle araştırıldı
    (Bahri'nin "hiçbir ülkenin/hükümetin sesi olmaksızın" ilkesi
    gereği). **Reddedilenler:** RFI (Fransa hükümetine ait), EFE
    (İspanya - SEPI/İspanyol hükümetine tam bağlı, başkanını hükümet
    atıyor - AA Ekonomi ile AYNI profil), Mediapart (bağımsız ama
    "sol eğilimli" olarak biliniyor + erişim engelli + büyük ölçüde
    ücretli).
  - **Eklenen 2 kaynak (canlı test edildi, çalışıyor):**
    - **Euronews** (`euronews.com/rss`, İngilizce, pan-Avrupa genel
      akış) - özel yatırım fonu (Alpac Capital) sahipliğinde, HİÇBİR
      TEK HÜKÜMETE ait değil. Güçlü finans içeriği doğrulandı (Fed
      başkanı Jackson Hole konuşması, Almanya gaz depolama krizi,
      İspanya yakıt vergisi indirimi).
    - **ANSA** (`ansa.it/sito/ansait_rss.xml`, İtalyanca, genel akış) -
      İtalya'nın 36 BAĞIMSIZ gazete yayıncısının ortak sahipliğindeki
      kooperatifi (AP'ye benzer yapı) - devlet ajansı DEĞİL, hafif
      kamu desteği alsa da editoryal bağımsızlığı olan bir yapı.
      "FOR PERSONAL USE ONLY" şartı var - v2.0.7.206'daki "TrendSurf
      Optima ticari değil" netleşmesiyle bu şart artık karşılanıyor.
  - **Kod değişikliği:** `_CEVIRI_GEREKEN_KAYNAKLAR`'a ikisi de eklendi
    (Euronews İngilizce, ANSA İtalyanca - ikisi de çeviri gerektiriyor).
    `app.py`'deki kaynak listesi metni güncellendi.
  - **İzole test edildi:** 16 kaynağın tümü doğru yapılandırılmış,
    AA Ekonomi'nin tamamen kaldırıldığı, Euronews+ANSA'nın hem RSS
    listesinde hem çeviri kümesinde olduğu, "Euronews Türkçe" (zaten
    Türkçe, farklı bir kaynak) ile yeni "Euronews"un (İngilizce)
    karışmadığı doğrulandı.
  - **AÇIK - SONRAKİ TURA BIRAKILDI (Bahri'nin kararı):** Yunanca
    (Kathimerini - bulundu ama canlı test edilemedi, araç kısıtlaması),
    İspanyolca (El País - tam RSS URL'si bulunamadı), Japonca, Çince,
    Arapça, Rusça için araştırma HENÜZ YAPILMADI/TAMAMLANMADI.


  (27 Ağustos 2026, Bahri'nin talebi — "diğer aboneler kendi optima
  skorlarını nasıl oluşturabilecekler, ayrı bir abonelik menüsü
  oluşturalım mı"): YENİ "ABONELİK" SAYFASI EKLENDİ.**
  - **Sebep:** v2.0.7.203'te tespit onayı/Optima Skor kişiye özel
    hale getirilmişti ama "Varsayılan Skor" sıfırlama düğmesi SADECE
    Admin Panel'de vardı - admin OLMAYAN aboneler kendi onaylarını
    yönetebilecekleri bir arayüze hiç sahip değildi.
  - **Uygulama:** PAGES listesine "Abonelik" eklendi ("Yardım"dan
    hemen önce, sidebar'daki dinamik etiket değişim mantığı
    bozulmadı). Yeni sayfa TÜM kullanıcılara (admin dahil) açık -
    herkes SADECE KENDİ onaylarını görür/yönetir: (1) şu an aktif
    onay sayısı (metrik), (2) aktif onayların listesi (genişletilebilir
    bölüm), (3) "Varsayılan Skor" düğmesi - admin.py'deki AYNI
    `tum_onaylanan_etkileri_sifirla(kullanici_id)` fonksiyonunu
    kullanıyor, ama HER KULLANICI kendi `_cur_user["id"]`'si ile
    çağırıyor - başka bir kullanıcının onayına asla dokunulamaz.
  - **Doğrulama:** `plan_badge` değişkeninin (sidebar'da `with
    st.sidebar:` bloğu içinde tanımlı) yeni sayfada erişilebilir
    olduğu doğrulandı - Python'da `with` blokları yeni bir kapsam
    OLUŞTURMAZ, bu yüzden sorun yok. Tam dosya hem `py_compile` hem
    `ast.parse()` ile doğrulandı.


  (27 Ağustos 2026, Bahri'nin log paylaşımı — "413 Request too large...
  TPM Limit 8000, Requested 8225"): GROQ ÇEVİRİSİ ARTIK KÜÇÜK GRUPLAR
  HÂLİNDE GÖNDERİLİYOR - TPM (DAKİKA BAŞINA TOKEN) LİMİTİ AŞILMASIN
  DİYE.**
  - **Kesin kök neden:** Groq'un `openai/gpt-oss-120b` modeli
    "on_demand" katmanında dakika başına 8000 token sınırı koyuyor.
    40 haberi TEK istekte çevirmek (girdi + 6000 max_completion_tokens
    rezervasyonu) bu sınırı hafifçe (8225) aşıyordu.
  - **Çözüm:** `_groq_ceviri` artık bir SARMALAYICI - içeride
    `_groq_ceviri_tek_parti`'yi 12'şerli gruplar hâlinde çağırıyor,
    gruplar arasına 15 saniyelik bekleme koyuyor (TPM dakika bazlı
    olduğu için art arda küçük istekler bile toplamda sınırı
    aşabilir). Sonuçlar birleştirilip tek bir sözlük olarak
    döndürülüyor - `main()` bu detaydan habersiz, eski arayüzle aynı
    şekilde kullanmaya devam ediyor.
  - **İzole test edildi:** 40 haber → 4 grup (12+12+12+4), hiçbir
    haber kaybolmuyor; 5 haberlik küçük liste tek grupta kalıyor; boş
    liste doğru şekilde ele alınıyor.
  - **Bonus gözlem:** Aynı log'da `_ucretsiz_yedek_ceviri` (deep-
    translator) bu kez 40/40 başlığı BAŞARIYLA çevirdi - önceki
    oturumlarda sistemik olarak engellendiği gözlemlenmişti (bkz.
    v2.0.7.187). Bu, Google'ın engellemesinin KALICI değil ARALIKLI
    olduğunu gösteriyor - iyi haber, ama Groq hâlâ birincil/güvenilir
    yol olarak kalmalı.

- **[UYGULANDI, CANLI TEST EDİLMEDİ] v2.0.7.204 (27 Ağustos 2026, Bahri'nin
  talebi — "haber kaynaklarımızı özellikle yurtdışı ABD, Almanya,
  İngiltere, Fransa, Japonya, Avustralya gibi ülkelerdeki güvenilir
  kaynaklarla çoğaltalım"): 6 ÜLKE ARAŞTIRILDI, 6 YENİ KAYNAK EKLENDİ
  (15 TOPLAM KAYNAK).**
  - **Eklenen 6 kaynak (Bahri'nin onayıyla):**
    - **NPR Business** (ABD) - `feeds.npr.org/1006/rss.xml` - canlı
      test edildi, güncel, doğrudan tarife/Fed/ticaret içeriği.
    - **Handelsblatt Finanzen** (Almanya) - `feeds.cms.handelsblatt.com/
      finanzen` - Almanya'nın önde gelen finans gazetesi, canlı test
      edildi, çok güçlü içerik (DAX, Fed, Deutsche Bank, tahvil
      getirileri). **ALMANCA** - ilk kez İngilizce olmayan bir yabancı
      kaynak eklendi.
    - **Sky News** (İngiltere, genel) - `feeds.skynews.com/feeds/rss/
      home.xml` - canlı test edildi, çalışıyor.
    - **ABC News Australia** (Avustralya, genel) - `abc.net.au/news/
      feed/45910/rss.xml` - canlı test edildi, çalışıyor.
    - **BBC Business** ve **Sky News Business** (İngiltere) - kendi
      test ortamında domain kısıtlaması nedeniyle DOĞRUDAN test
      edilemedi (BBC/Sky domain'leri özel engelli) - ama BBC World ve
      Sky News (genel) AYNI domain'lerden zaten çalışır durumda,
      çalışma ihtimali yüksek. **Bahri'ye bu risk açıkça bildirildi,
      bilerek onayladı.**
  - **Eklenmeyen adaylar (gerekçeli, hiçbiri Fransa/Japonya için
    bulunamadı):** CNBC, MarketWatch, The Guardian, Le Monde, Les
    Echos, DW - bot tespiti/erişim engeli. AP News - resmi RSS'i
    artık yok. **France24 ve Nikkei Asia** - robots.txt ile otomatik
    erişimi AÇIKÇA yasaklıyor (saygı gösterildi, atlandı; Nikkei ayrıca
    ticari kullanımı da sözleşmeyle yasaklıyor). Japan Times - artık
    ücretli abonelik gerektiriyor (402 hatası). **Sonuç: Fransa ve
    Japonya için hiçbir kaynak eklenemedi.**
  - **Kod değişikliği - önemli genelleme:** `_INGILIZCE_KAYNAKLAR`
    değişkeni `_CEVIRI_GEREKEN_KAYNAKLAR` olarak yeniden adlandırıldı
    ve genelleştirildi - artık sadece İngilizce değil, Almanca
    (Handelsblatt) dahil TÜRKÇE OLMAYAN her kaynağı kapsıyor. Çeviri
    istemi zaten kaynak dilini açıkça belirtmiyordu (modele otomatik
    algılatıyordu) - bu yüzden isim/küme değişikliği dışında BAŞKA
    HİÇBİR KOD DEĞİŞİKLİĞİ gerekmedi.
  - **İzole test edildi:** 15 kaynağın tümünün doğru yapılandırıldığı,
    6 yeni kaynağın hepsinin hem `_RSS_KAYNAKLARI` hem
    `_CEVIRI_GEREKEN_KAYNAKLAR`'da olduğu, Türkçe kaynakların hiçbirinin
    yanlışlıkla çeviri setinde olmadığı doğrulandı.
  - **AÇIK - canlı doğrulama bekleniyor:** BBC Business ve Sky News
    Business'ın gerçekten çalışıp çalışmadığı bir sonraki haber
    taramasının log'unda görülmeli.

- **[UYGULANDI, MANTIK DOĞRULANDI (izole simülasyon), CANLI TEST
  EDİLMEDİ] v2.0.7.203 (26 Ağustos 2026, Bahri'nin talebi — "her abone
  kendi tespitlerini görsün/onaylasın, Optima Skor kişiye özel olsun"):
  KRİTİK MİMARİ DEĞİŞİKLİK - TESPİT ONAYI VE OPTIMA SKOR ARTIK KİŞİYE
  ÖZEL, PAYLAŞIMLI DEĞİL.**
  - **ÖNEMLİ - ÖNCEKİ KARARIN TERSİNE ÇEVRİLMESİ:** 25 Ağustos'ta Bahri
    açıkça "tüm abonelerin görebilmesi/onaylayabilmesi bilerek böyle"
    demiş, paylaşımlı/global davranışı BİLEREK onaylamıştı. 26
    Ağustos'ta bu karar TERS ÇEVRİLDİ - Bahri'ye bu çelişki AÇIKÇA
    belirtildi, "büyük bir değişiklik" olduğu vurgulandı, Bahri
    AÇIKÇA "evet, kişiye özel olsun" diye onayladı. Bu madde
    gelecekte tekrar "hangisiydi?" diye sorgulanırsa: KİŞİYE ÖZEL
    olan GÜNCEL karar, 25 Ağustos'taki paylaşımlı karar ARTIK GEÇERSİZ.
  - **Yeni DB şeması:** `kullanici_tespit_karari` tablosu eklendi
    (kullanici_id, tespit_id, karar, karar_zamani -
    UNIQUE(kullanici_id, tespit_id)). `beklenti_otomatik_tespit`
    tablosu DEĞİŞMEDİ ama artık SADECE paylaşımlı/objektif tespit
    kaydını tutuyor (hangi haber, hangi kalıp) - `onay_durumu` sütunu
    ARTIK YENİ KODDA KULLANILMIYOR (silinmedi, geriye dönük uyumluluk
    için duruyor, vestigial).
  - **Değişen fonksiyonlar (hepsi artık `kullanici_id` ZORUNLU alıyor):**
    `get_bekleyen_tespitler(kullanici_id)` - artık "bu kullanıcının
    HENÜZ kararı olmayan" tespitleri döner (eskiden global
    onay_durumu='bekliyor' kontrolü vardı). `get_onaylanmis_tespitler
    (kullanici_id)` - SADECE bu kullanıcının onayladıkları.
    `tespit_onayla(kullanici_id, tespit_id)` / `tespit_reddet(...)` -
    artık `kullanici_tespit_karari`'na UPSERT yapıyor (paylaşımlı
    tabloya UPDATE değil). `tum_onaylanan_etkileri_sifirla
    (kullanici_id)` - SADECE bu kullanıcının onaylarını siliyor.
  - **Davranış:** Aynı habere Kullanıcı A onay verip Kullanıcı B
    vermemiş olabilir - Optima Skor ikisi için FARKLI görünür.
    Biri onaylasa/reddetse bile DİĞER kullanıcılar için tespit HÂLÂ
    "bekliyor" olarak görünmeye devam eder - herkes kendi kararını
    vermek zorunda.
  - **app.py'deki TÜM çağrı noktaları güncellendi** (modal dialog,
    Ana Sayfa listesi - tekil VE toplu onay/red, önbellek
    fonksiyonları) - `_cur_user["id"]` (mevcut oturum kullanıcısı,
    `get_current_user()`'dan) her çağrıya geçiriliyor. Önbellekleme
    (`st.cache_data`) da kullanıcı ID'sini parametre olarak aldığı
    için OTOMATİK OLARAK kullanıcı bazlı ayrışıyor - ekstra bir şey
    yapmaya gerek kalmadı.
  - **admin.py'deki "Varsayılan Skor" düğmesi** artık `get_current_user()`
    ile admin'in KENDİ id'sini alıp sadece KENDİ onaylarını sıfırlıyor
    - diğer abonelerin onayları hiç etkilenmiyor.
  - **İzole simülasyonla uçtan uca test edildi:** İki farklı kullanıcı
    (A, B) - aynı tespit ikisine de "bekliyor" görünüyor; A onaylayınca
    A'nın listesinden düşüyor ama B'ninkinde hâlâ bekliyor olarak
    kalıyor; SADECE A'nın onaylanan listesinde görünüyor, B'ninkinde
    yok. Tüm senaryolar beklenen sonucu verdi.
  - **AÇIK - CANLI TEST EDİLMEDİ:** Bu, gerçek bir veritabanı şeması
    değişikliği (yeni tablo) içerdiği için ilk canlı çalıştırmada
    dikkatle izlenmeli - özellikle `users(id)` sütununun gerçekten bu
    isimle var olduğu (auth.py'den çıkarım yapıldı, doğrudan
    doğrulanmadı) ve mevcut foreign key referanslarının sorunsuz
    kurulduğu kontrol edilmeli.


  (26 Ağustos 2026, Bahri'nin talebi — "buton adı çok uzun, sadece
  Geçmişi Sil olsun, yanına bir düğme daha istiyorum"): ADMIN PANEL
  DÜĞMELERİ GÜNCELLENDİ.**
  - "Son Günleri Sıfırla ve Yeniden İşlenmeye Aç" → **"Geçmişi Sil"**
    olarak kısaltıldı (işlevi DEĞİŞMEDİ).
  - **YENİ düğme: "Varsayılan Skor"** - yeni `tum_onaylanan_etkileri_
    sifirla()` fonksiyonunu çağırıyor. Şu an aktif (onaylanmış, süresi
    dolmamış) TÜM haber tespiti etkilerinin `gecerlilik_bitis`'ini
    ANINDA `now()`'a çekiyor - bir sonraki okumada artık "aktif"
    sayılmıyorlar, Optima Skor varsayılan (haber etkisi olmayan)
    haline dönüyor. **Geçmiş kayıtlar SİLİNMİYOR** - sadece etkileri
    kapatılıyor, denetim izi korunuyor.
  - **İzole test edildi:** karışık durumdaki (aktif onaylı / süresi
    zaten dolmuş / bekleyen / reddedilmiş) 5 sahte kayıt üzerinde -
    sadece GERÇEKTEN aktif olan 2 kayıt doğru şekilde etkilendi.

- **[UYGULANDI, CANLI TEST EDİLMEDİ] v2.0.7.199 (25 Ağustos 2026, Bahri'nin
  talebi — "birden fazla kaynak tarafından aynı haberin alınması bir
  başka kriter olarak eklenebilir"): ÇOKLU KAYNAK TEYİDİ ARTIK
  POP-UP/GÖSTERİM AŞAMASINA DA UYGULANIYOR - SADECE TOPLU ONAY İÇİN
  DEĞİL.**
  - **Önceki durum:** v2.0.7.194'teki "çoklu kaynak teyidi" (24 saat
    içinde farklı bir kaynaktan aynı kalıp) SADECE toplu onay
    ("Tümünü Onayla") için bir kriterdi - tekil pop-up/liste gösterimi
    bundan etkilenmiyordu, tek kaynaktan gelen her şey görünüyordu.
  - **Değişiklik:** `get_bekleyen_tespitler()` artık SADECE çoklu
    kaynak teyidi olan tespitleri döndürüyor - SQL'e bir `EXISTS`
    alt sorgusu eklendi (aynı `kalip_key`, farklı `haber_kaynak`, son
    24 saat - `coklu_kaynak_teyidi()` ile AYNI mantık/eşik). Tek
    kaynaktan gelen bir tespit artık HİÇ POP-UP OLARAK ÇIKMIYOR -
    veritabanında sessizce "bekliyor" durumunda kalıyor, ikinci bir
    kaynaktan teyit gelene kadar.
  - **ÖNEMLİ DAVRANIŞ DEĞİŞİKLİĞİ - Bahri'ye açıkça bildirildi:** Bu
    değişiklik canlıya alındığında, o an bekleyen tespitlerin ÇOĞU
    (tek kaynaklı olanlar) "Onay Bekleyen Otomatik Tespitler"
    listesinden/pop-up'tan ANİDEN KAYBOLACAK - bu bir hata DEĞİL,
    tam olarak istenen davranış. Sayı büyük ölçüde düşerse şaşırmamalı.
  - **BİLİNEN SINIRLAMA (coklu_kaynak_teyidi ile aynı, miras alındı):**
    kaba bir vekil - "aynı OLAYIN farklı kaynaklarca haberleştirilmesi"
    ile "aynı kalıba uyan FARKLI bir olayın aynı gün olması" arasında
    ayrım yapmıyor. Ayrıca iki kaynak birbirini teyit ettiğinde İKİSİ
    DE ayrı ayrı görünür/onaylanabilir hale geliyor - ikisi de
    onaylanırsa AYNI olayın etkisi TEORİK OLARAK iki kez uygulanabilir
    (bu, v2.0.7.194'teki toplu onayın da zaten taşıdığı bir
    karakteristik, yeni bir sorun değil).


  bulgusu — "risk orta/yüksek denildiği halde Türkiye piyasalarını pek
  etkilemeyecek haberler geliyor, sistemi ağırlaştırıyor"): AI
  DOĞRULAMA İSTEMİ KÖKTEN SIKILAŞTIRILDI - SADECE TÜRKİYE PİYASALARINI
  GERÇEKTEN ETKİLEYECEK HABERLER GEÇSİN.**
  - **Kök neden:** Eski istem sadece genel "piyasa etkisi olası mı"
    diye soruyordu - "HANGİ piyasa" belirtilmediği için AI, dünyanın
    herhangi bir yerindeki bir olayı (Türkiye ile zayıf/dolaylı bir
    bağı olsa bile) "eşleşme=true" işaretleyebiliyordu.
  - **Çözüm (`_ai_dogrula_prompt_olustur` - hem Gemini hem Groq için
    ORTAK, tek kaynak):** Artık İKİ ŞART DA sağlanmalı: (1) olay
    GERÇEKTEN büyük/önemli ölçekte (rutin/küçük/zaten fiyatlanmış
    DEĞİL), (2) Türkiye piyasaları (TL/BIST/Türk tahvilleri-CDS)
    üzerinde DOĞRUDAN VE ANLAMLI bir etki mekanizması açıkça var -
    "dünyada bir yerde bir şey oldu" YETMEZ. Açık RED örnekleri
    eklendi: genel yorum/analiz makaleleri, geçmiş olay hatırlatmaları,
    Türkiye'ye sadece dolaylı/teorik/uzak bağı olan haberler, zaten
    fiyatlanmış rutin açıklamalar. "Şüpheye düşersen KESİNLİKLE
    eşleşme=false" vurgusu güçlendirildi.
  - **Test edildi:** Yeni istemin doğru oluştuğu (tüm yeni katı
    kriterlerin metinde yer aldığı) izole test edildi.
  - **Beklenti:** Bu, "bekleyen tespit" sayısını önemli ölçüde
    azaltmalı - Bahri'nin bir sonraki birkaç haber taramasında
    gözlemleyip geri bildirmesi gerekiyor, gerekirse istem daha da
    ayarlanabilir.


  talebi — "uygulama ilk açıldığında 25.000 TL bütçe default olarak
  girilmiş olsun"): Bütçe (TL) kutusunun varsayılanı 0'dan (boş)
  25.000 TL'ye çevrildi - `_DEFAULT_BUTCE` sabitinden okunuyor, tek
  yerden değiştirilebilir. Değer hâlâ varsayılanla aynıysa (kullanıcı
  henüz değiştirmemiş olabilir) "Bu bir varsayılan değerdir,
  dilediğiniz gibi değiştirebilirsiniz." notu gösteriliyor - kullanıcı
  gerçekten farklı bir değer yazana kadar görünür kalır. Bonus: bu
  değişiklik v2.0.7.196'nın çözdüğü "bütçe boşsa sayfa duruyor"
  sorununun bir daha hiç tetiklenmemesini de garantiliyor (varsayılan
  artık asla 0 değil).

- **[SUPABASE TARAFI ÇÖZÜLDÜ - UYGULAMA TESTİ BEKLENİYOR] 25 Ağustos
  2026 — Supabase güvenlik uyarısı (KRİTİK): 7 TABLODA RLS KAPALI
  BULUNDU.** Security Advisor'da tam liste doğrulandı - hepsi bu
  oturumda/önceki oturumlarda kurulan "Beklenti Modu" (haber izleme)
  sistemine ait, hiçbiri genel kullanıcıya açık olması gereken bir
  tablo değil: `haber_islenmis`, `beklenti_otomatik_tespit`,
  `ai_cagri_butcesi`, `haber_akisi`, `haber_kalip_kelime`,
  `haber_kaliplari`, `haber_kalip_etki`. Sebep: bunlar önceki RLS
  denetiminden (hafızada "8 kritik uyarı çözüldü" notu) SONRA
  oluşturulan yeni tablolar, o denetime hiç girmemişler.
  **Çözüm:** Uygulama Supabase'e `SUPABASE_DB_URL` ile DOĞRUDAN Postgres
  bağlantısı kullanıyor (muhtemelen `postgres` rolüyle, ki bu rol RLS'i
  HER ZAMAN atlar) - bu yüzden bu 7 tabloda RLS'i (hiç policy eklemeden)
  açmak GÜVENLİ: uygulamanın kendi erişimi etkilenmez, sadece dışarıdan
  (anon key/REST API üzerinden) herkese açık erişim kapanır. Bahri'ye
  7 tablo için `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` komutları
  ve push sonrası hemen uygulamayı test etme adımları verildi.
  **CANLIDA DOĞRULANDI:** Bahri SQL'i çalıştırdı, Security Advisor'ı
  yeniden çalıştırdı - "0 errors / No errors detected" (7 hatanın
  tamamı temizlendi). **AÇIK KALAN:** uygulamanın kendi erişiminin
  (haber taraması, tespit oluşturma) hâlâ sorunsuz çalıştığı canlıda
  doğrulanmalı - beklenti öyle (postgres rolü RLS'i atlar) ama gerçek
  bir test henüz yapılmadı.
  **KALICI KURAL - GELECEKTE HATIRLANMALI:** Bundan sonra `db.py`'de
  YENİ bir tablo (`CREATE TABLE IF NOT EXISTS ...`) eklenirken, AYNI
  migration'da hemen `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`
  satırı da eklenmeli - bu sorunun bir daha birikmesini önler.
  Ayrıca gelen GitHub Codespaces silinme uyarısı ("improved orbit"
  codespace'i) - Bahri'nin gerçek iş akışında (Claude'dan dosya indirip
  yerel git push) Codespaces hiç kullanılmıyor, kod/veriyi etkilemez,
  aciliyeti yok, kendiliğinden silinmesine izin verilebilir.


  (25 Ağustos 2026, Bahri'nin bulgusu — "sayfanın devamı yok burada
  bitiyor zaten"): KRİTİK YERLEŞİM HATASI - "ONAY BEKLEYEN OTOMATİK
  TESPİTLER" BÖLÜMÜ BÜTÇE GİRİLMEDİĞİNDE HİÇ ÇALIŞMIYORDU.**
  - **Kesin kök neden:** v2.0.7.194'te eklenen "Tümünü Onayla" bölümü,
    dosyada `if budget<=0: ... st.stop()` kontrolünden SONRA
    konumlanmıştı. Bahri'nin "Bütçe (TL)" kutusu boştu (0 veya boş) -
    bu durumda `st.stop()` TÜM SAYFAYI o noktada durduruyordu, benim
    eklediğim bölüm DAHİL ondan sonraki hiçbir şey hiç çalışmıyordu.
    Kod GitHub'da doğru şekilde push edilmişti (bu doğrulanmıştı) -
    sorun kodun VARLIĞI değil, dosya içindeki YANLIŞ KONUMUYDU.
  - **Çözüm:** "Onay Bekleyen Otomatik Tespitler" + "Onaylanan
    Tespitler" bölümlerinin TAMAMI (164 satır), bütçe kontrolünden
    ÖNCEYE (6 metrik kutusunun hemen altına) taşındı - artık bütçe
    girilmese bile her zaman görünür. Bu mantıken doğru: tespit onay/
    red işlemi, portföy bütçe optimizasyonundan TAMAMEN BAĞIMSIZ bir
    özellik, aynı sayfada olmaları bunları birbirine bağımlı kılmamalı.
  - **Taşıma işlemi Python betiğiyle hassas şekilde yapıldı** (elle
    kopyala-yapıştır yerine) - girinti seviyesi (8 boşluk → 4 boşluk)
    doğru şekilde ayarlandı, "# PORTFÖYÜM" bölüm ayırıcısı ve bir
    yetim kalan açıklama yorumu doğru şekilde temizlendi/yeniden
    yerleştirildi. Hem `py_compile` hem tam `ast.parse()` ile
    doğrulandı - sözdizimi tamamen geçerli.
  - **ACİL - Bahri'nin geçici çözümü hâlâ geçerli:** Push'tan önce bile,
    sol panelden "Bütçe (TL)" kutusuna herhangi bir değer (ör. 100000)
    girmek aynı sorunu anında çözer - bu kalıcı düzeltme, o geçici
    çözüme ihtiyaç duymadan her durumda çalışmasını sağlıyor.


  2026 — "Otomatik tespit" onay pop-up'ı BİLEREK paylaşımlı/global:**
  Bahri'nin sorusu üzerine kod incelendi - `beklenti_otomatik_tespit`
  tablosunda hiçbir kullanıcı/abone sütunu yok, pop-up `is_admin`
  kontrolüne bağlı değil, GİRİŞ YAPAN HERKESE (admin veya herhangi bir
  Premium abone) aynı şekilde görünüyor - kim önce Onayla/Reddet derse
  o, TÜM sistem için (paylaşımlı Optima Skor) geçerli oluyor. **Bahri'ye
  bu netleştirildi ve "sadece admin görsün" seçeneği sunuldu - Bahri
  AÇIKÇA REDDETTİ, mevcut paylaşımlı davranışın BİLEREK böyle
  kalmasını istedi.** Kod DEĞİŞTİRİLMEDİ. Bu madde artık kapalı -
  gelecekte bir "bug" gibi tekrar gündeme getirilmemeli.
  **Geçerlilik süresi de netleştirildi:** 48 saat (tespit anından
  itibaren, onay anından değil) - süre dolunca puan etkisi otomatik
  olarak, manuel müdahale gerekmeden sessizce ortadan kalkıyor (canlı
  sorgu `gecerlilik_bitis > now()` filtresi kullanıyor, kalıcı bir
  veritabanı yazması değil).


  GERÇEKTEN ÇALIŞTI:** v2.0.7.155'te başlayan (18 Ağustos) bu özelliğin,
  onlarca hata/düzeltme turundan sonra (Gemini kota sorunları, Groq
  entegrasyonu, model değişiklikleri, JSON kesilme hatası vb.) sistemin
  TAMAMI ilk kez sorunsuz işledi: RSS taraması → anahtar kelime
  filtresi ("jeopolitik") → AI doğrulama (Groq, gpt-oss-120b) →
  Supabase'e yazma → Portföyüm sayfasında "Otomatik tespit" pop-up'ı →
  Bahri'nin onayı. Haber: "AB, Ukrayna'ya 6,1 milyar euroluk savunma
  paketi onayladı" - uygulanan puanlar: Değerli Maden +8.0, Döviz +6.0,
  BIST -6.0. Bahri onayladı.


  (25 Ağustos 2026, Bahri'nin üçüncü log paylaşımı — Actions çalışması
  #268): GROQ'UN GERÇEK HATA GÖVDESİ ARTIK GÖRÜNÜYOR - KESİN KÖK NEDEN
  BULUNDU.**
  - **v2.0.7.190'daki teşhis iyileştirmesi işe yaradı** - log'da artık
    Groq'un TAM hata gövdesi görüldü: `{"error":{"message":"Failed to
    validate JSON. Please adjust your prompt. See 'failed_generation'
    for more details.","type":"invalid_request_error","code":
    "json_validate_failed","failed_generation":""}}` - **`failed_generation`
    ALANI BOŞTU** - bu, modelin JSON üretmeye başladığını ama
    TAMAMLAYAMADAN kesildiğini gösteren güçlü bir işaret.
  - **Kesin kök neden (hipotez, izole test edildi):** `_groq_ceviri`
    ve `_groq_ai_dogrula`'nın istek gövdesinde `max_completion_tokens`
    HİÇ belirtilmemişti - API'nin varsayılan (muhtemelen düşük, ör.
    1024) limiti, 32-40 haberlik BÜYÜK bir JSON üretirken çıktıyı
    yarıda kesiyor, bu da GEÇERSİZ JSON'a (`json_validate_failed`)
    yol açıyordu. Tek maddelik `_groq_ai_dogrula` bu sorunu ÇOĞUNLUKLA
    yaşamıyordu (küçük JSON, muhtemelen limitin altında kalıyordu) -
    bu yüzden AI doğrulama başarılıyken çeviri başarısız oluyordu.
  - **Çözüm:** İkisine de açık `max_completion_tokens` eklendi -
    `_groq_ai_dogrula` için 2000 (tek madde, zaten büyük ihtimalle
    yeterliydi ama garantiye alındı), `_groq_ceviri` için 6000 (40
    madde x ~50-80 token/madde ~2000-3200 token eder, 6000 cömert bir
    pay bırakır).
  - **İzole test edildi:** Düşük token limitiyle JSON'ın yarıda
    kesilip geçersiz hale geldiği (Groq'un tam olarak bildirdiği
    hatayla birebir eşleşen "Unterminated string" hatası) ve yüksek
    limitle geçerli JSON üretildiği doğrulandı.
  - **AÇIK KALAN:** Bu, güçlü bir hipotez ve mantık testiyle
    doğrulandı, ama gerçek bir Groq API çağrısıyla CANLI TEST
    EDİLMEDİ - eğer bu turda da hata devam ederse (aynı ya da farklı
    bir hatayla), muhtemelen sonraki adım 40 haberi daha küçük
    gruplara (ör. 10'arlı) bölmek olacak.


  ikinci log paylaşımı — Actions çalışması #267): BÜYÜK İLERLEME - AI
  DOĞRULAMA GROQ İLE GERÇEKTEN ÇALIŞTI, ÇEVİRİDE YENİ (FARKLI) BİR HATA
  BULUNDU.**
  - **BAŞARI:** Log'da `"AI DOGRULADI: jeopolitik (Orta) - Euronews
    Türkçe kaynağından alınan habere göre, AB, Ukrayna'ya 6,1 milyar
    euroluk yeni savunma paketini onayladı..."` görüldü - Gemini 429
    aldıktan hemen sonra, hiçbir "Groq AI dogrulama hatasi" satırı
    olmadan bu doğrulama geldi - yani **Groq'un AI doğrulama tarafı
    artık gerçekten, uçtan uca çalışıyor** (v2.0.7.189'daki model
    düzeltmesi işe yaradı).
  - **Çeviri tarafında YENİ bir hata:** `Groq ceviri hatasi: HTTPError:
    400 Client Error: Bad Request` (artık 404 DEĞİL - model doğru,
    başka bir sorun). Model context penceresi araştırıldı
    (openai/gpt-oss-120b: 131K token) - 40 haberlik toplu istek bu
    limitin ÇOK altında, boyut sorunu değil.
  - **Kök neden HENÜZ KESİNLEŞMEDİ - eski kod yetersiz teşhis
    veriyordu:** `raise_for_status()`'un fırlattığı `HTTPError` sadece
    "400 Bad Request" diye yazdırılıyordu, Groq'un GERÇEK hata gövdesini
    (JSON içindeki "message"/"code" alanı, ör. "context_length_exceeded"
    veya "json_validate_failed" gibi) HİÇ göstermiyordu.
  - **Çözüm (bu turda sadece TEŞHİS iyileştirmesi, KÖK NEDEN
    ÇÖZÜLMEDİ):** Hem `_groq_ai_dogrula` hem `_groq_ceviri`'nin hata
    yakalama blokları artık `e.response.text`'i de yazdırıyor - bir
    sonraki log'da Groq'un TAM OLARAK neden reddettiğini göreceğiz.
    İzole test edildi (sahte HTTPError ile) - doğru çalışıyor.
  - **AÇIK KALAN:** Bir sonraki çalışmanın log'u paylaşıldığında, artık
    "| Govde: {...}" kısmında gerçek sebep görünecek - o zaman asıl
    düzeltme yapılabilir.


  (25 Ağustos 2026, Bahri'nin log paylaşımı — Actions çalışması #266):
  GROQ MODELİ KULLANIMDAN KALDIRILMIŞ - 404 HATASI BUNDAN.**
  - **İYİ HABER ÖNCE:** Log, Gemini→Groq geçiş mimarisinin (v2.0.7.185/
    187) ARTIK DOĞRU ÇALIŞTIĞINI kanıtladı - "Gemini AI dogrulama
    hatasi: 429" hemen ardından "Groq AI dogrulama hatasi: 404" ve
    "Groq ile ceviri deneniyor" satırları görüldü. Fallback zinciri
    tam istendiği gibi çalışıyor - sadece Groq'un KENDİSİ 404 veriyordu.
  - **Kesin kök neden (Groq'un resmi dokümantasyonuyla doğrulandı):**
    Groq, `llama-3.3-70b-versatile` modelini 17 Haziran 2026'da
    kullanımdan kaldırmayı duyurmuş ve **16 Ağustos 2026'da TAMAMEN
    KAPATMIŞ** (bugünden 9 gün önce). Groq'un kendi hata dokümantasyonu
    da doğruluyor: Groq, model bulunamadığında (OpenAI'nin 400
    konvansiyonunun aksine) özellikle 404 döndürüyor - "The model
    `X` does not exist or you do not have access to it."
  - **Çözüm:** Groq'un kendi önerdiği resmi migrasyon hedefi
    `openai/gpt-oss-120b`'ye geçildi (iki yerde: `_groq_ai_dogrula` ve
    `_groq_ceviri`). `response_format: json_object` desteğinin bu
    modelde de çalıştığı varsayılıyor (standart bir OpenAI-uyumlu
    özellik) ama GERÇEK bir API anahtarıyla CANLI TEST EDİLMEDİ -
    bir sonraki çalıştırmada doğrulanmalı.
  - **Ders:** Groq gibi hızlı gelişen/model kataloğunu sık değiştiren
    sağlayıcılarda, kod içine gömülen model adları zamanla
    geçersizleşebilir - bu tür entegrasyonlarda periyodik olarak
    sağlayıcının "deprecations" sayfasının kontrol edilmesi faydalı
    olur.


  Bahri'nin bulgusu — "TEFAS'ın kendi sitesinde bu fonların değerleri
  var, ama bizde hâlâ 0"): GERÇEK KÖK NEDEN BULUNDU - pytefas'IN KENDİSİ
  ARA SIRA 503 VERİYOR, RETRY HİÇ YOKTU.**
  - **Bu, v2.0.7.174/186'nın çözdüğü sorundan TAMAMEN FARKLI, DAHA
    DERİN bir kök neden.** Önceki iki düzeltme "önceki geçerli fiyatı
    koru" mantığıydı - ama korunacak geçerli bir önceki fiyat hiç
    oluşmuyorsa (pytefas HTS/HOY için hiç başarılı olmuyorsa) o
    korumaların işe yaramayacağı zaten not edilmişti. Bu turda GERÇEK
    SEBEP bulundu.
  - **Canlı API testiyle KANITLANDI (tahmin değil):** `pytefas`
    kütüphanesi gerçek ağ erişimiyle test edildi -
    `c.fetch(kind="YAT")` 1. denemede `503 Server Error: Service
    Unavailable` ile başarısız oldu, AYNI parametrelerle 2. deneme
    (birkaç saniye sonra, yeni bir Crawler ile) **6112 satırla
    BAŞARILI** oldu. Bu, TEFAS'ın kendi API'sinin ARA SIRA geçici
    503 verdiğini kesin olarak kanıtlıyor - HTS/HOY'a özgü bir sorun
    DEĞİL, TEFAS'ın genel güvenilirlik durumu.
  - **Kesin kod hatası:** `tefas_client.py`'nin `fetch_all_current_prices()`
    fonksiyonunda `c.fetch()` çağrısının HİÇ retry'si yoktu - bir kez
    503 alınca o KIND (YAT - HTS/HOY'un kategorisi) o tur için
    TAMAMEN atlanıyordu, bir daha denenmiyordu.
  - **Çözüm:** `c.fetch()` çağrısı artık 3 deneme yapıyor (aralarda 3
    saniye bekleme) - ilk deneme 503 alsa bile ikinci/üçüncü denemede
    kurtarma şansı var.
  - **İzole test edildi (2 senaryo, sahte Crawler ile):** (1) ilk 2
    deneme 503, 3. başarılı → retry sayesinde HTS/HOY'un fiyatı
    kurtarıldı. (2) 3 deneme de başarısız → düzgün şekilde `None`
    dönüp o tur için atlanıyor, çökme yok.
  - **Beklenti:** Bu, hem HTS/HOY'u hem muhtemelen "1230/1348"
    rakamındaki diğer başarısız fonların bir kısmını da düzeltecek -
    TEFAS'ın genel geçici güvenilmezliği tüm fonları etkiliyor olabilir,
    sadece bu ikisini değil.


  üçüncü canlı log paylaşımı — Actions çalışması #265): KRİTİK BULGU -
  ÜCRETSİZ ÇEVİRİ YEDEĞİ (deep-translator) GITHUB ACTIONS'TA SİSTEMİK
  OLARAK ENGELLENİYOR.**
  - **Kesin gözlem:** İki ayrı çalışmada da (25 Ağustos, sabah ve
    öğlen) 40/40 başlığın TAMAMI "TranslationNotFound" hatası verdi -
    "US Supreme Court sides with Trump administration on mail voting"
    gibi sıradan cümlelerin bile çevrilemez olması istatistiksel
    olarak imkansıza yakın.
  - **Araştırmayla doğrulanan kesin kök neden:** `deep-translator`'ın
    Google Translate kazıma mekanizması, GitHub Actions'ın PAYLAŞILAN
    sunucu IP'lerinde Google'ın "olağandışı trafik" bot-engellemesine
    takılıyor. Birden fazla bağımsız GitHub issue'sunda "~40-50 çeviri
    isteğinden sonra Google engelliyor" doğrulandı - tam bizim istek
    sayımıza denk geliyor. `TranslationNotFound` hatası "bu metin
    çevrilemedi" DEĞİL, "Google bize normal sayfa yerine bir engelleme
    sayfası döndürdü, kütüphane bunu ayrıştıramadı" anlamına geliyor -
    SİSTEMİK bir IP-engeli, tek tek başlıkların sorunu değil. v2.0.7.184
    (tek tek çevirme) bu yüzden yardımcı olamadı - izolasyon sorunu
    çözer, ama engelleme TÜM istekleri aynı anda etkiliyor.
  - **Çözüm:** Groq (resmi, sanctioned bir API - kazıma DEĞİL) çeviri
    zincirine EKLENDİ - artık sıra: Gemini → Groq → deep-translator
    (deep-translator en sona alındı, GitHub'ın IP'si her zaman engelli
    olmayabilir diye tamamen çıkarılmadı ama artık son çare).
  - **İzole test edildi:** Groq'un JSON yanıt formatı sahte veriyle
    ayrıştırıldı - başlık+özet doğru şekilde eşleşti, boş özet
    doğru şekilde `None` olarak işlendi.
  - **AYRI BULGU - v2.0.7.185 HENÜZ CANLIDA DEĞİLDİ:** Bahri'nin
    paylaştığı log'da hâlâ eski "Gemini hatasi: 429..." mesajı
    görülüyordu (v2.0.7.185'in düzelttiği mesaj). Terminal ekran
    görüntüsü incelendi - `git commit` "no changes added to commit"
    demişti, yani güncellenmiş `haber_izleme.py` dosyası proje
    klasörüne hiç KOPYALANMAMIŞTI, git'e eklenecek fark yoktu. Push
    hiç gerçekleşmemişti. Bahri'ye dosyayı yeniden indirip doğru
    klasöre kopyalaması, `git status` ile değişikliği DOĞRULAMASI
    söylendi - bu, gelecekte benzer "düzeltme push edildi ama canlıda
    hâlâ eski davranış görülüyor" karışıklıklarında ilk kontrol
    edilmesi gereken şey olarak not edildi.


  Bahri'nin bulgusu — "HTS ve HOY yine 0 gösteriyor"): v2.0.7.174'ÜN
  KAPSAM EKSİĞİ BULUNDU - KORUMA SADECE YARIM UYGULANMIŞTI.**
  - **Zaman çizelgesiyle doğrulanan kesin kök neden:** Git geçmişi
    satır satır izlendi - 21-24 Ağustos arası (3 gün, hem tam hem
    kısmi çalışmalar) HTS/HOY fiyatları SABİT ve DOĞRUYDU - v2.0.7.174
    koruması ÇALIŞIYORDU. Ama **24 Ağustos 23:23'teki "Veri guncelleme"
    (TAM/gece çalışması)** sırasında HTS/HOY için pytefas/BEFAS ikisi
    de başarısız olunca fiyat SESSİZCE 0'a düştü - o zamandan beri
    HİÇ düzelmedi. Sebep: v2.0.7.174 koruması SADECE
    `update_tefas_evening.py`'ye (günde 7 kez çalışan KISMİ güncelleme)
    eklenmişti - `worker.py`'nin KENDİ TEFAS yükleme adımında (günde 1
    kez çalışan TAM/gece güncellemesi) AYNI koruma HİÇ YOKTU. Tam
    çalışma fiyatı sıfırlayınca, kısmi çalışmanın koruması "önceki
    fiyata" bakmaya devam etti ama önceki fiyat ARTIK KENDİSİ 0'dı -
    kurtaracak bir şey kalmamıştı.
  - **Çözüm:** AYNI "önceki CSV'de geçerli fiyat varsa satırın
    TAMAMINI koru" mantığı `worker.py`'nin TEFAS yükleme bloğuna da
    (pytefas overlay'inden hemen sonra) eklendi - artık iki script
    TUTARLI şekilde davranıyor, ikisi de aynı korumaya sahip.
  - **İzole test edildi:** Gerçek senaryo simüle edildi (HTS/HOY
    önceki CSV'de geçerli fiyata sahip, bu turda ikisi de 0 dönüyor,
    MTG ise başarılı) - doğrulandı: HTS/HOY'un önceki geçerli
    fiyatları korundu, MTG'nin YENİ başarılı fiyatı hiç etkilenmedi.
  - **ACİL - CANLI VERİ HÂLÂ BOZUK, KENDİLİĞİNDEN DÜZELMEYECEK:** Bu
    düzeltme sadece GELECEKTEKİ "önceki fiyat zaten 0 iken tekrar 0
    gelirse" senaryosunu önler - ŞU AN HTS/HOY'un CSV'deki fiyatı
    ZATEN 0, yani korunacak geçerli bir "önceki fiyat" da yok. Bu iki
    fonun fiyatının gerçekten düzelmesi için pytefas veya BEFAS'ın
    bunlar için en az BİR KEZ DAHA gerçek bir fiyat getirmesi
    gerekiyor - 21-24 Ağustos arası günlerce sorunsuz çalıştığına göre
    bunun yakında tekrar olması muhtemel, ama garanti edilemez.
    Bahri'ye push sonrası birkaç çalışma boyunca takip etmesi
    önerildi.


  ikinci canlı log paylaşımı — Actions çalışması #264): KRİTİK BUG -
  GROQ HİÇ DENENMİYORDU, KENDİ v2.0.7.183 EKLEMEM HATALIYDI.**
  - **Log'daki kesin kanıt:** "petrol" kalıbı bir habere eşleşti, ama
    log şunu gösterdi: "Gemini AI dogrulama hatasi: 429..." hemen
    ardından "AI REDDETTI (petrol): Gemini hatasi: 429..." - Groq'un
    denendiğine dair TEK BİR satır bile yok. Groq'un devreye HİÇ
    girmediği kesinleşti.
  - **Kesin kök neden:** `_gemini_ai_dogrula`'nın `except` bloğu,
    exception oluştuğunda `return None` (Groq'a geçişe izin veren
    özel değer) DEĞİL, `return False, None, f"Gemini hatasi: {e}"`
    (GERÇEK BİR SONUÇ TUPLE'I) döndürüyordu. `_ai_dogrula`'daki
    `if sonuc is not None: return sonuc` kontrolü bu tuple'ı GEÇERLİ
    BİR CEVAP sayıp hemen döndürüyordu - Groq'a HİÇ sıra gelmiyordu.
    Yani "anahtar yok" (None) ile "anahtar var ama İSTEK BAŞARISIZ
    OLDU" (yanlışlıkla gerçek bir sonuç) durumları birbirine
    karıştırılmıştı - tam da v2.0.7.169'daki retry bug'ıyla AYNI
    ailede bir "ne zaman durmalı/ne zaman devam etmeli" hatası.
  - **Çözüm:** Hem `_gemini_ai_dogrula` HEM `_groq_ai_dogrula`'nın
    `except` blokları artık `None` döndürüyor - "bu sağlayıcı KESİN
    BİR CEVAP vermedi" anlamında, ister anahtar eksikliğinden ister
    çalışma zamanı hatasından olsun. `_ai_dogrula`'daki nihai red
    mesajı da güncellendi - artık "anahtar eksik" ile "ikisi de
    denendi ama başarısız oldu" durumlarının ikisini de doğru
    yansıtıyor.
  - **İzole test edildi (2 senaryo):** (1) Gemini 429 atıyor, Groq
    başarılı → ARTIK DOĞRU şekilde Groq'un sonucu kullanılıyor (eski
    bug'da bu noktada Gemini'nin 429'u "kesin red" sayılıp Groq'a hiç
    geçilmiyordu). (2) İkisi de başarısız → hâlâ güvenli tarafta
    (red) kalıyor, mesaj ikisinin de denendiğini doğru yansıtıyor.
  - **Ders:** Bu oturumda ikinci kez aynı hata ailesine düşüldü
    (v2.0.7.169: "break" bir başarıyı mı yoksa herhangi bir sonucu mu
    işaretliyor karıştırılmıştı; şimdi: `None` "denenmedi" mi yoksa
    "denendi başarısız oldu" mu karıştırıldı). Fallback zincirleri
    yazarken "bu adımda KESİN bir cevap mı var, yoksa sadece BİR
    DENEME mi başarısız oldu" ayrımı özellikle dikkat gerektiriyor.


  canlı log paylaşımı — Actions çalışması #263): ÜCRETSİZ ÇEVİRİ
  YEDEĞİNDE KRİTİK BİR HATA BULUNDU - TEK SORUNLU BAŞLIK, TÜM 40
  HABERLİK TURU ÇÖKERTİYORDU.**
  - **Log'daki kesin kanıt:** `[haber_izleme] Ucretsiz yedek ceviri
    hatasi: TranslationNotFound: Songs created by AI banned from
    Australia's music charts --> No translation was found using the
    current translator.` - Gemini 429 aldıktan sonra ücretsiz yedeğe
    düşüldü, ama bu turda TESADÜFEN Google Translate'in çeviremediği
    TEK bir başlık ("Songs created by AI banned...") vardı - ve bu TEK
    madde `translate_batch()`'in TÜM 40 HABERLİK LİSTE İÇİN TEK BİR
    exception fırlatmasına sebep oldu. Sonuç: "0 baslik cevrildi
    (Gemini: 0, ucretsiz yedek: 0)" - 39 tanesi gayet çevrilebilir
    olsa bile HİÇBİRİ çevrilmedi.
  - **Çözüm:** `translate_batch()` (toplu, tek-hata-hepsini-çökertir)
    yerine HER başlık/özet ARTIK TEK TEK, KENDİ try/except'i İÇİNDE
    çevriliyor - hatta başlık ve özet bile BİRBİRİNDEN BAĞIMSIZ (biri
    başarısız olsa diğeri etkilenmiyor). Sadece sorunlu madde/alan
    atlanıyor, diğer TÜM haberler normal şekilde çevriliyor.
  - **İzole test edildi:** 3 haberlik sahte bir liste - biri
    (başlığında tetikleyici kelime olan) hata fırlatan bir sahte
    çevirmenle - doğrulandı: sorunlu haberin SADECE başarısız olan
    alanı (başlık) `None` kaldı, AYNI HABERİN özeti bağımsız olarak
    başarıyla çevrildi, DİĞER İKİ HABER TAMAMEN ETKİLENMEDİ. Eski
    kodda bu 3 haberin ÜÇÜ DE kaybolurdu.
  - **AÇIK KALAN - Groq henüz test edilmedi:** Bu turda hiçbir haber
    ön-filtreden geçmediği için ("0 on-filtreden gecti, 0 AI ile
    dogrulandi") AI doğrulama adımı (Gemini/Groq) hiç ÇAĞRILMADI.
    Groq'un gerçek bir API çağrısıyla çalışıp çalışmadığı HÂLÂ
    doğrulanmadı - bir haber gerçekten bir kalıba uyduğunda tekrar
    kontrol edilmeli.


  talebi — "vazgeçtim, ücretsiz başka metod yok mu"): AI DOĞRULAMA İÇİN
  GROQ İKİNCİ (ÜCRETSİZ) SAĞLAYICI OLARAK EKLENDİ.**
  - **Araştırma:** Birden fazla bağımsız kaynak (Ağustos 2026) tarandı -
    kart istemeyen, gerçekten ücretsiz LLM API sağlayıcıları arasında
    Groq en tutarlı şekilde "cömert, güvenilir" olarak öne çıktı
    (günlük limit tahminleri kaynağa göre 1.000-14.400 arası değişse de
    hepsi bizim ihtiyacımızın kat kat üzerinde). GitHub Models
    değerlendirildi ama bazı modellerin yakın zamanda kaldırıldığına
    dair işaretler bulundu - otomatik/gözetimsiz bir arka plan işi
    için daha az güvenli bulundu, seçilmedi.
  - **Mimari:** Çeviri katmanındaki (v2.0.7.176) İKİ KATMANLI mimariyle
    AYNI felsefe - `_ai_dogrula` artık ÖNCE Gemini'yi dener
    (`_gemini_ai_dogrula`), o başarısız/yapılandırılmamışsa Groq'a
    düşer (`_groq_ai_dogrula`), o da yoksa GÜVENLİ TARAF (eşleşme=False,
    haber reddedilir - asla varsayılan olarak kabul edilmez). Prompt
    metni `_ai_dogrula_prompt_olustur` ortak fonksiyonuna çıkarıldı -
    iki sağlayıcı TAM AYNI prompt'u kullanıyor, elle senkron tutma
    riski yok.
  - **Groq'un avantajı:** OpenAI-uyumlu `response_format:json_object`
    desteği sayesinde Gemini'deki gibi ```json` temizleme triklerine
    gerek yok - model doğrudan geçerli JSON döndürüyor.
  - **Test edildi (izole, gerçek network çağrısı OLMADAN):** (1)
    Groq'un JSON yanıt formatı sahte veriyle ayrıştırıldı - doğru
    çalıştı. (2) Geçersiz JSON durumunda exception'a düşüp güvenli
    şekilde reddettiği doğrulandı. (3) Anahtar yokluğu senaryoları -
    hiçbir anahtar yoksa güvenli red, Gemini anahtarı yokken
    `_gemini_ai_dogrula`'nın `None` (Groq'a geçişe izin veren özel
    değer) döndürdüğü doğrulandı.
  - **AÇIK - BAHRİ'NİN YAPMASI GEREKEN ADIMLAR (kod dışı):**
    (1) console.groq.com'da ücretsiz hesap aç (kart istemiyor),
    (2) API anahtarı oluştur, (3) GitHub'da Settings > Secrets and
    variables > Actions'a `GROQ_API_KEY` adıyla ekle. Bu adımlar
    ATILMADAN Groq devreye girmez (sessizce `None` döner, sistem
    eskisi gibi sadece Gemini'yi dener).
  - **GERÇEK API ÇAĞRISI HENÜZ TEST EDİLMEDİ** - Groq'un tam URL/model
    adı/response_format davranışı dokümantasyona dayanıyor, canlı bir
    anahtarla ilk çalıştırmada doğrulanmalı.


  belirsizliği (25 Ağustos 2026):** Google AI Studio'nun Rate Limit
  sayfası incelendi - "Tier 1" etiketi altında görünen rakamlar (RPD
  163/10.000, RPM 5/1.000, TPM 2,55K/1M - hepsi limitin çok altında)
  GERÇEK UYGULANAN limitle ÇELİŞİYOR (sürekli 429 alınıyor, bkz.
  v2.0.7.164/176/178 logları). Kesinleşen açıklama: hesapta
  faturalandırma ("Set up prepay") HENÜZ AKTİVE EDİLMEMİŞ - panel
  muhtemelen "faturalandırma aktive edilirse bu limitler geçerli
  olur" şeklinde iyimser bir önizleme gösteriyor, arka planda hâlâ
  çok daha kısıtlı bir ücretsiz katman uygulanıyor olabilir.
  **Bahri'ye ödeme yöntemi eklemesi önerildi (bu tamamen finansal bir
  karar, tavsiye verilmedi) - Bahri AÇIKÇA REDDETTİ ("hayır, şimdilik
  eklemek istemiyorum").** Bu kabul edilebilir bir karar - küçük bir
  arka plan script'i için kart bilgisi paylaşmaya değmez.
  **SONUÇ: `_GUNLUK_AI_BUTCESI=120` DEĞİŞTİRİLMEDİ** - gerçek limit
  hâlâ bilinmiyor, artırmak bilinmeyen bir sınıra göre kumar olurdu,
  azaltmanın faydası yok çünkü sistem zaten 429'a karşı dayanıklı
  (retry-with-backoff v2.0.7.164, Gemini'den tamamen bağımsız ücretsiz
  çeviri yedeği v2.0.7.176). **Bu madde artık AÇIK DEĞİL - gelecekte
  tekrar gündeme getirilmemeli, Bahri karar verdi.**


  HABER İZLEME ARTIK GÜVENİLİR ŞEKİLDE ÇALIŞIYOR - cron-job.org
  KURULUMU DOĞRULANDI.**
  - Bahri, mevcut "TrendSurf Mail" (send_email.yml için zaten çalışan)
    cron-job.org işini çoğaltarak "TrendSurf Haber Izleme" işini kurdu.
    Test tetiklemesi **"204 No Content"** ile başarılı oldu - GitHub'ın
    dispatches endpoint'i doğru şekilde tetiklendi.
  - **[ÇÖZÜLDÜ - 25 Ağustos 2026] Süresiz token'a geçildi:** İlk kurulumda
    kullanılan fine-grained PAT'ın 6 Ekim 2026'da dolacak bir geçerlilik
    süresi vardı. Araştırıldı - GitHub, fine-grained PAT'lar için de
    (2024 sonundan beri) "No expiration" seçeneği sunuyor (tek şart:
    token en az yılda bir kullanılmalı, aksi halde otomatik silinir -
    cron işleri günde defalarca kullandığı için bu risk yok). Bahri
    "cron-job-tetikleyici" adıyla YENİ, süresiz, sadece trendsurf-optima
    reposuna ve sadece Actions:Read-and-write iznine sahip bir token
    oluşturdu ve **ÜÇ cron işinin de** (TrendSurf Mail, TrendSurf Haber
    Izleme, firsat_radari.yml) Authorization başlığını bu yeni token'la
    güncelledi - üçü de test edildi, üçü de "204 No Content" ile
    başarılı, üçü de aktif/yeşil durumda. Eski (Ekim'de dolacak olan)
    token artık kullanılmıyor. **Bir daha hatırlatma gerekmiyor.**
  - **Kod değişikliği:** `haber_izleme.yml`'deki GitHub'ın kendi
    güvenilmez `schedule` tetikleyicisi (`*/10 * * * *`, "best-effort"
    çalışıyordu - bazen 25-40 dk aralıklarla) TAMAMEN KALDIRILDI.
    Artık `send_email.yml` (v2.0.3.8) ile AYNI mimari: sadece
    `workflow_dispatch`, harici tetikleme cron-job.org'dan geliyor.
    Bu değişiklik SADECE test başarılı olduğu İÇİN yapıldı - aksi
    halde hem GitHub'ın schedule'ı hem cron-job.org devre dışı kalıp
    haber izleme tamamen dururdu.


  talebi — "Anka Haber Ajansı, T24, Euronews, Sözcü, Halk TV, Reuters,
  Xinhua, AFP - hangilerini sisteme dahil edebiliriz"): 8 ADAY CANLI
  TEST EDİLDİ, 3'Ü EKLENDİ.**
  - **Eklenen 3 kaynak (Bahri'nin onayıyla):**
    - **Sözcü Ekonomi** (`sozcu.com.tr/feeds-rss-category-ekonomi`) -
      GENEL akış değil, DOĞRUDAN EKONOMİYE ÖZEL besleme. Canlı test
      edildi (22 Ağustos), yüksek yoğunlukta doğrudan kalıplara giren
      içerik gözlendi ("Fed Başkanı ve Hazine Bakanı karşı karşıya",
      "Merkez Bankası'ndan yastık altı altın kararı", "Bitcoin 3 günde
      %20 yükseldi", "JPMorgan'dan Merkez Bankası analizi: Faiz
      indirimi için tarih belli oldu").
    - **Euronews Türkçe** (`tr.euronews.com/rss`) - canlı, güncel,
      zaten Türkçe, gerçek jeopolitik/makro içerik (ABD-Kanada gümrük
      anlaşmazlığı, ABD borç krizi, Fed/ECB ilişkili haberler).
    - **Halk TV** (`halktv.com.tr/service/rss.php`) - teknik olarak
      çalışıyor, canlı, ama **Bahri'ye açıkça bildirildi**: akışın
      büyük kısmı magazin/asayiş/spor, ekonomi içerik oranı düşük;
      CHP'ye tarihsel bağı olan muhalif çizgide bir yayın organı
      (evenhandedness gereği bu bilgi saklanmadı, Bahri bilerek
      onayladı).
  - **Eklenmeyen 5 aday (gerekçeli, canlı test/araştırmayla
    doğrulandı):**
    - Anka Haber Ajansı: herkese açık bir RSS'i yok, sadece şifreli/
      abonelik gerektiren bir servis sunuyor.
    - T24: eski RSS adresi (`t24.com.tr/rss/haberler`) 404 dönüyor -
      site yenilenmiş, güncel bir RSS adresi bulunamadı.
    - Reuters: resmi RSS'i yıllar önce tamamen kapatılmış (geliştirici
      blog yazısıyla doğrulandı - "Reuters silently killed its RSS
      feed").
    - Xinhua: RSS besleme sayfası hâlâ var ama CANLI TEST EDİLDİ - son
      haber 2017 tarihli, 9 yıldır güncellenmemiş, tamamen donmuş.
    - AFP: halka açık bir haber RSS'i yok - sadece AFP'nin kendi
      kurumsal duyurularını (MediaGen lansmanı, fotoğraf festivalleri
      vb.) yayınlayan ayrı bir RSS'i var, gerçek haber içeriği değil.
  - **Uygulama:** Üçü de `_RSS_KAYNAKLARI`'na eklendi. Üçü de Türkçe
    olduğu için `_INGILIZCE_KAYNAKLAR` setine EKLENMEDİ. Haberler
    sayfasındaki kaynak listesi metni güncellendi (artık 9 kaynak).


  talebi — "başka kaynak bulamıyor muyuz?"): DÜNYA GAZETESİ ALTINCI
  HABER KAYNAĞI OLARAK EKLENDİ.**
  - **Araştırma süreci:** Birden fazla aday test edildi (Reuters resmi
    RSS'i artık genel kullanıma kapalı/üçüncü taraf üretici gerektiriyor,
    Yahoo Finance'ın genel/tüm-piyasa RSS'i net değil - ticker-özel
    formatlar bulundu ama genel akış yok, Hürriyet Ekonomi RSS'i CANLI
    TEST EDİLDİ ve 2021 tarihli eskimiş SEO içeriği ("proforma fatura
    nedir" gibi) döndürdüğü görüldü - GERÇEK ZAMANLI DEĞİL, EKLENMEDİ,
    Investing.com TR'nin market_overview/commodities RSS'leri CANLI TEST
    EDİLDİ ama günlük/haftalık köşe yazısı temposu, gerçek zamanlı haber
    akışı değil - önerilmedi).
  - **Dünya Gazetesi CANLI TEST EDİLDİ** (22 Ağustos 14:31 TRT) - gerçekten
    güncel, akan bir haber kaynağı, Türkiye'nin köklü finans
    gazetelerinden biri. BBC/Al Jazeera gibi GENEL bir akış (ekonomi
    dışı içerik de var - spor, sınav haberleri) ama gerçek ekonomi
    haberleri de içeriyor (test sırasında "ABD'nin 40 trilyon dolarlık
    borcu Avrupa'yı vurdu" gibi doğrudan "fed" kalıbına girebilecek bir
    haber görüldü).
  - **Uygulama:** `_RSS_KAYNAKLARI`'na eklendi. Zaten Türkçe olduğu için
    `_INGILIZCE_KAYNAKLAR` setine EKLENMEDİ (çeviri gerekmiyor - AA
    Ekonomi/Investing.com TR/BloombergHT ile aynı kategori). Haberler
    sayfasındaki kaynak listesi metni güncellendi.


  talebi — "başlıkları çevirebiliyorsak haberin tümünü de çevirebiliriz
  değil mi?"): KISA RSS ÖZETİ DE ÇEVRİLİYOR - TAM METİN BİLEREK
  EKLENMEDİ (telif riski).**
  - **Bahri'ye sunulan ayrım ve onun kararı:** Haberin TAMAMINI
    çekip/çevirip göstermek için her makalenin kendi web sayfasını
    ayrıca kazımak (scrape) gerekir - hem kırılgan bir mühendislik işi
    hem de BBC/Al Jazeera/AA gibi kaynakların TAM metnini kendi
    uygulamamızda göstermek muhtemelen RSS besleme şartlarını aşan bir
    TELİF İHLALİ olur (kullanıcı orijinal siteye hiç gitmeden tam
    haberi okur, kaynağın trafiğini/reklam gelirini biz alırız - "adil
    kullanım" sayılması zor). Bunun yerine RSS'in ZATEN VERDİĞİ kısa
    (1-3 cümlelik) özeti çevirip göstermek önerildi - kullanıcı yine
    kaynağa yönlendiriliyor, standart haber toplayıcı (aggregator)
    pratiği. **Bahri bu ORTA YOLU onayladı, tam metin İSTENMEDİ.**
  - **Şema değişikliği:** `haber_akisi` tablosuna `ozet`/`ozet_tr`
    sütunları eklendi. Tablo CANLIDA ZATEN VAR olduğu için `CREATE
    TABLE IF NOT EXISTS` yetmez - `ALTER TABLE ADD COLUMN IF NOT
    EXISTS` ile idempotent migration eklendi (`init_db()` içinde).
  - **Her iki çeviri katmanı da (Gemini VE ücretsiz yedek) artık HEM
    başlığı HEM özeti çeviriyor** - tek çağrıda ikisi birlikte (Gemini:
    tek JSON isteğinde her madde için "baslik"+"ozet" alanı; ücretsiz
    yedek: iki ayrı `translate_batch` çağrısı, özet bazı haberlerde
    boş olabildiği için index hizalaması karışmasın diye ayrı tutuldu).
  - **HTML temizliği eklendi:** `ozet` artık kullanıcıya DOĞRUDAN
    gösterildiği için (önceden sadece AI prompt'u için perde arkasında
    kullanılıyordu), bazı RSS kaynaklarının özet alanına gömdüğü HTML
    etiketleri (`<p>`, `<a>` vb.) regex ile temizlendi - temizlenmeseydi
    ekranda çıplak etiket görünürdü.
  - **Test edildi (3 senaryo):** (1) ücretsiz yedek ile gerçek başlık+
    özet çevirisi (biri özetli, biri özetsiz) - özetsiz haber doğru
    şekilde `ozet_tr=None` aldı, çökme yok. (2) Gemini JSON ayrıştırma
    mantığı sahte yanıtla - eksik/boş alanlar güvenli ele alındı,
    Gemini'nin hiç yanıt vermediği bir madde doğru şekilde atlandı
    (kayma yok). (3) HTML temizleme regex'i gerçek örnek metinle.
  - **Haberler sayfası** artık başlığın hemen altında kısa özeti
    gösteriyor (çevrilmişse Türkçesi, değilse orijinali).


  bulgusu — "haber başlıkları Türkçe olsun demiştim, neden olmadı"):
  v2.0.7.176'DAKİ ÜCRETSİZ YEDEK ÇEVİRİ HİÇ ÇALIŞMIYORDU - PAKET KURULU
  DEĞİLDİ.**
  - **Kesin kök neden (log ile doğrulandı):** Mantığın kendisi TAM
    DOĞRU çalışıyordu - Gemini 429 aldı, doğru şekilde ücretsiz yedeğe
    düştü, AMA log'da `ModuleNotFoundError: No module named
    'deep_translator'` çıktı. Sebep: `deep-translator` SADECE
    `requirements.txt`'e eklenmişti (v2.0.7.176) - ama
    `haber_izleme.yml` iş akışı `requirements.txt`'e HİÇ BAKMIYOR,
    kendi ayrı/minimal paket listesini (`feedparser requests
    psycopg2-binary`) kuruyor. Bu, `worker.py`/`update_data.yml` gibi
    ağır işlerin TAM `requirements.txt`'i kurmasından FARKLI bir
    mimari - haber taraması bilerek hafif tutulmuş.
  - **Çözüm:** `deep-translator`, `haber_izleme.yml`'in KENDİ pip
    install satırına da eklendi. Tek satırlık, dar bir düzeltme.
  - **DERS - kalıcı not:** Bu projede YENİ bir Python paketi eklerken
    SADECE `requirements.txt`'e eklemek YETMEZ - hangi GitHub Actions
    iş akışının o kodu çalıştıracağını bulup, o iş akışının KENDİ pip
    install listesine de eklemek gerekiyor (worker.py'yi çalıştıran
    `update_data.yml` tam `requirements.txt` kullanıyor, ama
    `haber_izleme.yml`, `update_tefas_evening.yml` gibi "hafif" işler
    kendi minimal listelerini tutuyor - hangi iş akışının hangi
    yöntemi kullandığı push öncesi KONTROL EDİLMELİ).
  - **Yan gözlem (çözülmedi, sadece not edildi):** Bahri'nin ekran
    görüntüsündeki bazı "jeopolitik" eşleşmeleri (İsveçli bakan
    tartışması, liman kapanışı, Batı Şeria hukuku sorusu, Alaska uçak
    kazası) gerçek jeopolitik gerilimden çok Orta Doğu/askeri
    bağlamdaki genel haberler gibi görünüyor - muhtemelen başlıkta
    değil özet metninde geçen bir anahtar kelimeye (ör. "military")
    takılmış olabilirler. Bu ayrı bir kalıp/kelime ince ayarı konusu,
    bu turda dokunulmadı.


  talebi — "sadece Fed mi piyasaları etkiliyor... literatür taraması
  yapman gereği idi"): AKADEMİK KAYNAKÇA + BoE/PBoC GENİŞLETMESİ.**
  - **BoE ve PBoC boşluğu doğrulandı, düzeltme Admin Paneli üzerinden
    Bahri'ye anlatıldı** (kod değil, veri değişikliği): ECB zaten mevcut
    "fed" kalıbında kapsanıyordu (lagarde, ecb kelimeleri) - BoE
    ("bank of england", "boe", "bailey") aynı kalıba eklenmesi, PBoC
    ise FARKLI bir mekanizma (emtia talebi kanalı, Fed'in fonlama
    maliyeti kanalından ayrı) olduğu için AYRI bir kalıp
    ("pboc_tesvik") olarak önerildi - MADEN +4, DOVIZ −3, BIST +5,
    KRIPTO boş (güven düşük).
  - **Gerçek akademik literatür taraması yapıldı** (önceki turdaki
    "araştırma" güncel haber kaynaklarındandı, akademik DEĞİLDİ - Bahri
    haklı olarak bunu ayırt etti). Doğrulanmış, isim/yıl/dergi tam
    kaynaklar: MacKinlay (1997, event study metodolojisinin kurucu
    makalesi), Caldara & Iacoviello (2022, Jeopolitik Risk Endeksi -
    GPR - metodolojisi bizim anahtar-kelime ön-filtremizle AYNI ailede),
    Akçayır (2023, TÜRKİYE'YE ÖZEL - TL üzerinde CDS'in baskın, jeopolitik
    riskin GÖRECELİ ZAYIF olduğu bulgusu - önemli bir denge notu),
    bir dergipark makalesi (BIST100 - jeopolitik risk endeksi ilişkisi,
    1 birim artış ~%4 BIST100 düşüşü), Kilian (2009, petrol şoklarının
    arz/talep ayrımının akademik temeli), Kuttner (2001) + Gürkaynak-
    Sack-Swanson (2005, Fed "sürpriz" kavramının ölçülebilirliğinin
    kökeni), Kaminsky & Schmukler (2002, kredi notu indiriminin
    tahvil+hisse etkisi, ortalama 2 puan spread artışı).
  - **Kaynakça HEM araştırma belgesine (`tefas_kalip_arastirmasi.md`,
    Bölüm 4) HEM UYGULAMANIN KENDİSİNE eklendi** - Admin Paneli >
    Kalıp Yönetimi > "Akademik Kaynakça" genişletilebilir bölümü
    (`admin.py`). Statik/sabit içerik - kalıplar gibi veritabanında
    DEĞİL, doğrudan kodda (yeni bir kalıp eklenirken elle güncellenir).
  - **AÇIK KALAN:** BoE/PBoC değişikliklerinin Bahri tarafından Admin
    Panelinden fiilen uygulanıp uygulanmadığı TEYİT EDİLMEDİ - bu bir
    veri girişi, kod push'u değil.


  iki ayrı talebi): (1) HABERLER İÇİN GENİŞLETİLMİŞ EKONOMETRİK ARAŞTIRMA
  + (2) ÇEVİRİ İÇİN ÜCRETSİZ YEDEK KATMAN.**
  - **Araştırma:** Web araştırmasıyla 5 yeni kalıp önerisi + mevcut "fed"
    kalıbına somut bir belgelenmiş örnek (2013 Taper Tantrum) derlendi -
    `tefas_kalip_arastirmasi.md` dosyası olarak Bahri'ye sunuldu. Yeni
    önerilen kalıplar: (a) Fed/ECB güvercin sürprizi (beklenmedik faiz
    indirimi - mevcut "fed"in tersi yönü), (b) Küresel likidite krizi/
    panik satışı (COVID-Mart-2020 - KARŞI-SEZGİSEL: altın kısa vadede
    DÜŞER, güvenli liman değil nakit ihtiyacı yüzünden), (c) Petrol arz
    fazlası/fiyat savaşı (mevcut "petrol arz şoku"nun tersi), (d)
    Bankacılık krizi/banka iflası (SVB 2023 örneği - KRIPTO yönü
    belirsiz/tutarsız bulundu, puan ÖNERİLMEDİ). Hepsi gerçek, kaynağı
    doğrulanabilir tarihsel olaylarla belgelendi (Brookings, Dallas Fed,
    World Gold Council, Wikipedia, ScienceDirect vb.) - tahmini sayı
    YOK. **Bahri'nin onayı/düzenlemesi bekleniyor, HENÜZ Admin Panelinden
    eklenmedi.**
  - **Çeviri artık İKİ KATMANLI:** Gemini kotasının güvenilmez olduğu
    (v2.0.7.164'te 429 hataları) zaten biliniyordu. `deep-translator`
    kütüphanesi eklendi (`requirements.txt`) - Google Translate'in genel
    web arayüzünü kullanan, API ANAHTARI GEREKTİRMEYEN, ücretsiz bir
    yedek. Akış: Gemini ÖNCE denenir (daha kaliteli - özel isimleri
    Türkçe yaygın haliyle yazıyor); Gemini NEYİ ÇEVİREMEZSE (kota doldu/
    API hatası/anahtar eksik/kısmen başarısız), KALAN başlıklar HER
    ZAMAN ücretsiz yedeğe düşer - bu katman günlük AI bütçesinden
    BAĞIMSIZ. Sonuç log satırı artık hangi katmanın kaç başlık
    çevirdiğini ayrı ayrı gösteriyor ("Gemini: X, ucretsiz yedek: Y").
  - **Test edildi:** Gerçek başlıklarla `translate_batch` çağrısı
    (3 başlık, 0,88 saniye, kaliteli çeviri) VE tam uçtan uca senaryo
    (Gemini kotası dolu/atlanmış gibi davranan sahte `db` modülüyle) -
    ikisi de doğru çalıştı, ücretsiz yedek Gemini olmadan da başlıkları
    doğru çevirdi.
  - **Bilinen sınırlama:** `deep-translator`, Gemini'nin "özel isimleri
    Türkçe yaygın haliyle yaz" gibi ince ayarlarını yapmıyor - daha
    "düz" bir çeviri kalitesi, ama HİÇBİR ZAMAN kota yüzünden tamamen
    durmuyor. Gayri resmi bir sarmalayıcı olduğu için Google'ın kendi
    arayüzünü değiştirmesi durumunda bozulabilir - bu da try/except ile
    güvenli şekilde ele alınıyor (hata verirse sessizce boş döner,
    başlık İngilizce kalır, çökme olmaz).


  bulgusu — "BIST100'ün grafikte olmaması yine devam eden bir sorun"):
  v2.0.7.169'DAKİ RETRY DÜZELTMESİ KENDİSİ HATALIYDI, DÜZELTİLDİ.**
  - **Kesin kök neden:** v2.0.7.169'da eklenen retry döngüsünde
    `break` satırı, exception FIRLAMADIĞI HER DURUMDA çalışıyordu -
    `_bs` (BIST 100 verisi) GERÇEKTEN boş/yetersiz gelse bile. yfinance'ın
    EN YAYGIN başarısızlık şekli tam olarak bu: hata FIRLATMADAN boş bir
    DataFrame döndürmek (rate-limit'te sık görülür). Yani "retry"
    mantığı SADECE sert exception'larda (ağ kopması vb.) devreye
    giriyordu - yfinance'ın asıl sık karşılaşılan "sessizce boş dön"
    davranışında HİÇ yeniden denemiyordu, ilk denemede pes ediyordu.
    Retry'nin kendisi bu en yaygın senaryoda İŞLEVSİZDİ.
  - **Çözüm:** `break` artık SADECE `_sonuc["BIST 100"]` GERÇEKTEN
    atandığında çalışıyor - boş/yetersiz veri de artık normal bir
    başarısızlık sayılıp aynı bekleme/tekrar deneme yoluna düşüyor
    (exception ile aynı davranış).
  - **İzole test edildi (3 senaryo):** (A) ilk 2 deneme sessizce boş
    veri dönüyor, 3. başarılı → ARTIK doğru şekilde 3 kez deneniyor ve
    başarıyla atanıyor (eski bug'da bu senaryo İLK denemede pes
    ediyordu). (B) ilk 2 deneme exception atıyor, 3. başarılı → aynı
    şekilde çalışıyor. (C) 3 deneme de başarısız → sessizce vazgeçiliyor,
    UI'daki uyarı zaten gösteriliyor. Üçü de doğru sonucu verdi.


  Bahri'nin bulgusu — "Portföyümdeki rakamlar gerçeği yansıtmıyor, HTS
  güncellendiği halde neden 0?"): KRİTİK VERİ KAYBI HATASI - GEÇERLİ
  FON FİYATLARI SESSİZCE SIFIRLANIYORDU.**
  - **Doğrulama:** TEFAS'ın kendi resmi sitesinden HTS'nin gerçek
    fiyatının 59,042509 TL olduğu teyit edildi (ekran görüntüsüyle).
    Actions logu incelendi: bu turda pytefas 1348 fonun sadece 1230'u
    için fiyat getirebilmiş ("1230/1348 fon") - HTS dahil 118 fon
    BAŞARISIZ kalmış.
  - **Kesin kök neden:** `update_tefas_evening.py`'de bir "önceki
    geçerli fiyatı koru" mekanizması HİÇ YOKTU. `load_excel_all()`
    her fon için taban Son_Fiyat değerini 0.0 olarak başlatıyor,
    SADECE BEFAS'ın günlük Excel'inde eşleşen fonlara gerçek fiyat
    atıyor. HTS gibi bazı "Serbest Fon" türleri BEFAS'ın Excel'inde hiç
    olmayabiliyor. Bu turda pytefas DA HTS için başarısız olunca,
    Son_Fiyat 0.0 TABAN DEĞERİNDE KALDI - ve script bunu ÖNCEKİ CSV'DEKİ
    GEÇERLİ FİYATLA (59,04) HİÇ KARŞILAŞTIRMADAN doğrudan üzerine
    yazdı. Sonuç: gerçek bir fon bir gecede sahte bir "%100 zarar"
    gösterir hale geldi - portföy verisi GÜVENİLMEZ hale gelmişti.
  - **Çözüm:** `worker.py`'nin MADEN döngüsündeki "Kademe 3: Son
    CSV'den tamamla" ile AYNI felsefe eklendi - bu turda fiyat
    alınamayan (Son_Fiyat<=0) her TEFAS satırı için, önceki CSV'de o
    ticker için geçerli (>0) bir fiyat varsa, SATIRIN TAMAMI (fiyat +
    RSI/Ret1M/Vol) AYNEN korunuyor - sadece bugünkü başarısız çekimin
    üzerine sessizce sıfır yazılmıyor. İzole test edildi: eski geçerli
    fiyat (HTS senaryosu) korunuyor, YENİ başarılı fiyatlar (MTG
    senaryosu) hiç etkilenmiyor.
  - **ACİL - CANLI VERİ HÂLÂ BOZUK, BİR SONRAKİ ÇALIŞMAYA KADAR
    DÜZELMEYECEK:** Bu düzeltme sadece GELECEKTEKİ çalışmaları
    etkiler - `optimized_universe.csv`'de HTS'nin fiyatı ŞU AN hâlâ 0
    yazılı duruyor, kod push edilse bile bir sonraki TEFAS çalışmasına
    (en geç ~2 saat) kadar kendiliğinden düzelmez. Bahri'ye push
    sonrası Actions'tan "Run workflow" ile ELLE tetikleyip hemen
    doğrulaması önerildi.
  - **AÇIK KALAN - GENİŞ ETKİ İHTİMALİ:** Bu turda pytefas'ın
    BAŞARISIZ olduğu 118 fonun TAMAMI (sadece HTS değil) bu hatadan
    aynı şekilde etkilenmiş olabilir - hepsi bu düzeltmeyle otomatik
    kurtarılacak (önceki geçerli fiyatları varsa), ama Bahri'nin
    portföyünde HTS dışında başka etkilenen pozisyon olup olmadığı
    push öncesi/sonrası kontrol edilmeli.


  sorusu — "gram altın günlerdir artıyor, Optima Skoru neden yükselmiyor?
  Yoksa TEFAS/Bigpara değerlerini okuyamıyor mu?"): KRİTİK BUG - ALTIN/
  GÜMÜŞ İÇİN RSI/RET1M HİÇBİR ZAMAN GERÇEK VERİDEN HESAPLANMIYORDU.**
  - **Doğrulama zinciri:** GitHub'dan taze CSV çekildi - `ALTIN_TRY`
    satırı `RSI=50.0`, `Ret1M=0.0` (ikisi de FLAT VARSAYILAN DEĞER),
    `_gecmis_veri_yok=True` gösteriyordu - Aug 19 00:50 TRT'den beri
    (kontrol edilen TÜM commit'lerde, ~1,5 gündür) DEĞİŞMEDEN. Bu,
    `_MADEN_SENTETIK_CEVRIM_YASAK` listesinde OLMAYAN 9 fiziki
    sikke/gram türünden (bkz. o zaten bilinen/kararlaştırılmış madde)
    TAMAMEN AYRI bir sorun - ALTIN_TRY'nin GC=F üzerinden gerçek
    yfinance geçmişi VAR ve olması gerekirdi.
  - **Kesin kök neden (worker.py, MADEN döngüsü):** Kademe 2 (yfinance
    RSI/Ret1M/Vol hesaplama) bloğu `if p == 0.0 or _sentetik_yasak:`
    şartına bağlıydı - yani Bigpara BAŞARIYLA bir fiyat getirdiğinde
    (ki her zaman getiriyor, fiyat gerçek ve hareket ediyor: 6692→6955
    TL) bu blok TAMAMEN ATLANIYORDU. FİYAT KAYNAĞI (Bigpara) İLE TEKNİK
    GÖSTERGE KAYNAĞI (yfinance) YANLIŞLIKLA TEK BİR KOŞULA
    BAĞLANMIŞTI - oysa bunlar bağımsız olmalıydı (fiyat gerçek olabilir
    AMA teknik geçmiş ayrıca çekilmesi gereken farklı bir veri).
  - **Zincirleme etki:** `_gecmis_veri_var` de hiç `True` olamıyordu
    (o da bu bloğun içinde set ediliyor) → `_gecmis_veri_yok=True` →
    Detay sayfasındaki v2.0.7.71/77 kuralı (`if _gecmis_veri_yok==True:
    disp_score_cat=0.0`) devreye girip **Optima Skor'u SIFIRLIYORDU** -
    fiyat tamamen gerçek ve güncel olsa bile. Bu turda daha önce (Değerli
    Madenler RSI mean-reversion tartışmasında) gördüğümüz RSI=75,1/
    Skor=37,3 değerleri muhtemelen bu bug'ın henüz devreye girmediği/
    farklı bir kod yolunun (Portföyüm pozisyon detayı, ayrı bir `enrich()`
    çağrısı) kullanıldığı bir ana aitti - Değerli Madenler KATEGORİ
    sayfasının kendi Detay paneli, bu bug yüzünden muhtemelen 0,0
    gösteriyordu.
  - **Çözüm:** Fiyat ve teknik gösterge kaynakları AYRILDI - Kademe 2
    artık HER ZAMAN çalışır (yfinance RSI/Ret1M/Vol her zaman denenir),
    fiyatın (`p`) KENDİSİ ise hâlâ SADECE Bigpara başarısızsa VEYA
    sentetik çevrim yasaksa (`_sentetik_yasak`) buradan atanır -
    **Bahri'nin "sentetik fiyat asla gösterilmesin" ilkesi (PLATIN ve 9
    sikke için) TAMAMEN KORUNUYOR**, sadece RSI/Ret1M artık bu ilkeden
    BAĞIMSIZ, her zaman gerçek veriden hesaplanıyor.
  - **İzole test edildi (3 senaryo):** (1) Bigpara+yfinance ikisi de
    başarılı → fiyat Bigpara'dan KALDI, RSI/Ret1M artık GERÇEK (97,1/
    4,24 - sabit 50/0 DEĞİL), `_gecmis_veri_var=True`. (2) PLATIN
    (sentetik yasak), Bigpara başarısız → fiyat 0.0 KALDI (sentetik
    ASLA atanmadı, Kademe 3'e düşecek) ama RSI yine gerçek hesaplandı.
    (3) İkisi de başarısız → eski (güvenli) 50/0 varsayılana düşüyor,
    kayıp yok. Üçü de beklenen sonucu verdi.
  - **DÖVİZ döngüsü KONTROL EDİLDİ - AYNI BUG YOK, temiz çıktı:** DÖVİZ
    farklı (doğru) bir yapıda - `_canlidoviz_hesapla()` fiyat VE RSI/
    Ret1M/Vol'u TEK bir fonksiyonda, aynı gerçek geçmiş seriden BİRLİKTE
    hesaplıyor (ya hepsi gerçek gelir ya da fonksiyon `None` döner, tek
    tek "biri geldi diğerini atla" durumu YOK). Sadece EN SON çare
    (Truncgil, sadece iki üst kademe de başarısız olursa) flat/nötr
    değer kullanıyor - bu zaten doğru şekilde `_gecmis_veri_var=False`
    ile işaretleniyor. Bu turda başka bir kod değişikliği GEREKMEDİ.


  talebi): "Pozisyon Bazlı Getiri Karşılaştırması" grafiği (Portföyüm
  sayfası, ikinci/deneme grafik) Ana Getiri Kıyaslaması'ndaki
  (v2.0.7.169) AYNI iki teknikle netleştirildi - her çizgiye renge ek
  olarak kendine özgü bir DESEN (6 desen x 10 renk = 60 kombinasyon,
  pozisyon sayısı sabit olmadığı için desen döngüsü renk döngüsünden
  bağımsız uzunlukta tutuldu) ve her çizginin SAĞ UCUNA doğrudan metin
  etiketi eklendi. Sağ kenar boşluğu 10'dan 90'a çıkarıldı.


  bulgusu — "e-posta geldi ama linke tıklayınca localhost çıktı"):
  v2.0.7.170'İN AÇTIĞI E-POSTA BAŞARIYLA GİTTİ, AMA İÇİNDEKİ LİNK YANLIŞ
  ADRESE GİDİYORDU.**
  - **Kök neden - KOD HATASI DEĞİL, EKSİK SECRETS GİRİŞİ:** `APP_URL`
    Streamlit Cloud Secrets'ta hiç tanımlı değildi, kod bu yüzden
    "http://localhost:8501" varsayılanına düşüyordu - Bahri'nin kendi
    cihazında asla çalışmayan, sadece bir geliştiricinin kendi
    bilgisayarında anlamlı olan bir adres.
  - **Kod tarafında yapılan (savunma amaçlı, ama TEK BAŞINA YETERLİ
    DEĞİL):** localhost varsayılanı kaldırıldı, bilinen gerçek Streamlit
    Cloud adresi varsayılan yapıldı (`auth.py`'deki v2.0.7.170
    düzeltmesiyle aynı desen) - secret hâlâ eksikse en azından GERÇEK
    bir adrese düşer.
  - **ASIL/KALICI ÇÖZÜM - BAHRİ'NİN YAPMASI GEREKEN, KOD DIŞI BİR ADIM:**
    Streamlit Cloud > Manage app > Settings > Secrets'a
    `APP_URL = "https://<güncel-adresin>.streamlit.app"` satırı
    eklenmeli. **Bahri'nin subdomain'i değiştirip değiştirmediği
    BİLİNMİYOR** (bir önceki turda nasıl yapılacağı anlatıldı ama
    yapıp yapmadığı teyit edilmedi) - hangi adresi kullanması
    gerektiğini görmek için tarayıcı adres çubuğuna bakması istendi.
    **Subdomain'i her değiştirdiğinde bu secret satırı da
    güncellenmeli**, yoksa aynı sorun tekrarlanır.

- **[UYGULANDI, CANLI TEST EDİLMEDİ] v2.0.7.170 (20 Ağustos 2026, Bahri'nin
  bulgusu — "şifremi unuttum, sıfırlama bağlantısı bir türlü gelmiyor"):
  KRİTİK GÜVENLİK/İŞLEVSELLİK HATASI - ŞİFRE SIFIRLAMA E-POSTASI
  STREAMLIT CLOUD'DA MUHTEMELEN HİÇ ÇALIŞMAMIŞTI.**
  - **Kök neden:** `auth_reset.py`'nin `_send_reset_email()` fonksiyonu
    SADECE yerel `email_config.json` dosyasına bakıyordu. Bu dosya
    `.gitignore`'da ("Hassas konfigürasyon") - Streamlit Cloud'a HİÇ
    YÜKLENMİYOR. Dosya yoksa fonksiyon `if not os.path.exists(cfg_path):
    return` ile SESSİZCE hiçbir şey yapmadan çıkıyordu - hata YOK, log
    YOK, hiçbir iz yok. Buna rağmen `app.py`'deki çağıran kod HER ZAMAN
    "E-posta adresinize sıfırlama bağlantısı gönderildi." başarı mesajı
    gösteriyordu (bu kısıtlı bir GÜVENLİK ÖNLEMİ olarak BİLEREK böyle -
    "kullanıcı yoksa da başarılı mesaj ver", hesap varlığını e-posta
    enumerasyonuyla sızdırmamak için - BUNA DOKUNULMADI, doğru bir
    tasarım). Sonuç: kullanıcı arayüzü hep "başarılı" dese de, gerçek
    dünyada (Streamlit Cloud'da) e-posta muhtemelen İLK GÜNDEN BERİ HİÇ
    GÖNDERİLMEMİŞTİ.
  - **Çözüm:** `emailer.py`'de ZATEN ÇALIŞAN (planlı e-posta raporları
    bu yolla gidiyor, Bahri'ye daha önce ulaştığı doğrulanmış) TAM OLARAK
    AYNI fallback deseni taşındı: önce yerel `email_config.json`, YOKSA/
    BOŞSA `st.secrets["email"]`. Streamlit Cloud'da bu secrets ZATEN
    yapılandırılı (emailer.py onu kullanıyor) - yani **yeni bir secrets
    girişi GEREKMİYOR**, sadece auth_reset.py artık ona bakıyor.
  - **Acil unblock önerisi (Bahri'ye sunuldu, henüz kullanılıp
    kullanılmadığı bilinmiyor):** Supabase SQL Editor'den `pgcrypto`
    uzantısıyla doğrudan `UPDATE users SET password = crypt(...)`
    komutu - push/redeploy beklemeden şifre sıfırlamanın bir yolu.
    Teknik gerekçe güçlü (pgcrypto bcrypt çıktısı, uygulamanın
    kullandığı Python `bcrypt` ile format uyumlu) ama CANLIDA TEST
    EDİLMEDİ - Bahri normal push+dene akışını mı yoksa bu kısayolu mu
    kullandı, takip edilmeli.
  - **AÇIK MADDE ÇÖZÜLDÜ - aynı hata kontrol edildi, farklı bir sorun
    bulundu:** `_notify_admin_yeni_kayit` (auth.py) `st.secrets`'a zaten
    doğru bakıyordu, `_send_reset_email` ile aynı hatayı TAŞIMIYORDU.
    Ama İNCELERKEN AYRI BİR SORUN BULUNDU: bu fonksiyondaki admin
    bildirim e-postasındaki link SABİT KODLANMIŞTI
    ("https://trendsurf-optima.streamlit.app/?go=admin") - Bahri'nin
    az önce sorduğu "alt alan adını kısaltma" işlemini yaparsa, bu link
    KIRILIRDI (eski, artık var olmayan adrese giderdi). `st.secrets
    ["APP_URL"]`'den okuyacak şekilde düzeltildi - `auth_reset.py`'nin
    zaten kullandığı desenle aynı. Alt alan adı değişse bile artık tek
    bir yerden (Secrets'taki APP_URL) güncellenmesi yeterli.


  bulguları): GETİRİ KIYASLAMASI GRAFİĞİNDEKİ ÜÇ SORUN.**
  - **BIST 100'ün kaybolup gelmesi (KÖK NEDEN bulundu, düzeltildi):**
    `yf.download("XU100.IS", ...)` çağrısı `except Exception: pass` ile
    sessizce başarısız oluyordu - yfinance'ın bilinen geçici ağ/rate-limit
    flakiness'i yüzünden bu SIK oluyordu. Fonksiyon 5 dakika önbellekli
    olduğu için, TAM O ANDA oluşan bir hata "BIST 100 yok" durumunu 5
    dakika boyunca donduruyordu - "bir süre bekleyince geri gelmesi" bu
    yüzdendi. Çözüm: 3 deneme (1,5 sn arayla) eklendi; 3'ü de başarısız
    olursa artık SESSİZCE değil, grafiğin üstünde açık bir uyarı
    ("BIST 100 şu an yüklenemedi...") gösteriliyor.
  - **Çizgi ayırt edilebilirliği (Bahri'nin bulgusu: "renkler ve
    kalınlıklar ayırt edici değil"):** Her çizgiye RENGE EK OLARAK
    kendine özgü bir ÇİZGİ DESENİ (düz/kesikli/noktalı/nokta-çizgi/uzun
    kesikli/uzun nokta-çizgi) verildi. Ayrıca her çizginin SAĞ UCUNA
    doğrudan bir metin etiketi eklendi (`fig.add_annotation`) - artık
    hover'a gerek kalmadan hangi rengin/deseninin hangi varlık olduğu
    grafiğin sağında yazıyor. Sağ kenar boşluğu (margin) etiketlerin
    sığması için 10'dan 90'a çıkarıldı.
    **BİLİNEN SINIRLAMA:** iki varlığın DEĞERİ neredeyse birebir aynıysa
    (bkz. aşağıdaki Devlet Tahvili/Repo maddesi), sağ uçtaki metin
    etiketleri üst üste binip okunması zorlaşabilir - dash deseni yine
    de ayrı çizgiler olduğunu gösteriyor, tam çakışma çözülmedi.
  - **[AÇIK - BAHRİ'NİN KARARI BEKLİYOR] "Devlet Tahvili" veri kaynağı
    muhtemelen YANLIŞ ETİKETLİ:** Bahri'nin "Devlet Tahvili grafikte
    görünmüyor" bulgusunu araştırırken kesinleşti - `TP.BISTTLREF.ORAN`
    ("BIST TLREF") aslında bir tahvil getirisi DEĞİL, GECELİK bir repo
    tabanlı referans faiz oranı - `TP.AOFOBAP` (Repo için kullanılan
    seri) ile FONKSİYONEL OLARAK ÇOK BENZER. Bu yüzden ikisinin
    kümülatif getirisi pratikte AYNI çıkıyor (ekran görüntüsünde ikisi
    de +1,86%) ve çizgileri tam üst üste biniyor - görünmezlik bir
    render hatası değil, VERİ KAYNAĞI SEÇİMİ hatası.
    Türkiye'nin gerçek "gösterge tahvili" 2 yıl vadeli, ikincil piyasada
    işlem gören bir devlet tahvilidir (doviz.com doğrulandı) - ama
    araştırmamda EVDS'te bunun için GÜVENİLİR, DOĞRULANMIŞ bir seri kodu
    BULAMADIM (yalnızca investing.com/TradingView gibi piyasa
    kaynaklarında "Turkey 2Y Bond Yield" olarak görülüyor, TCMB EVDS'ten
    DEĞİL). **Tahmini bir kod yazıp "düzelttim" DENMEDİ** - bu, Bahri'nin
    karar vermesi gereken açık bir konu: (a) mevcut TLREF kaynağını
    "Devlet Tahvili" yerine gerçek adıyla ("TL Gecelik Referans")
    yeniden etiketleyip Repo ile birlikte tutmak, (b) Repo'yu kaldırıp
    sadece TLREF'i tutmak, (c) investing.com/TradingView gibi bir
    kaynaktan gerçek 2 yıllık tahvil getirisini scrape etmek (yeni bir
    entegrasyon, ayrı bir iş).

- **[UYGULANDI, CANLI TEST EDİLMEDİ] v2.0.7.168 (20 Ağustos 2026,
  Bahri'nin bulgusu — "uygulama yeniden çok ağırlaştı"): KÖK NEDEN
  BULUNDU - HER SAYFADA ÇALIŞAN ÖNBELLEKSİZ DB SORGULARI.**
  - **Kesin kök neden:** `get_bekleyen_tespitler()` ve
    `get_onaylanmis_tespitler()` (v2.0.7.156'da eklendi) HİÇ önbelleksizdi
    - sayfa fark etmeksizin HER script rerun'ında (her tıklama, her
    widget etkileşimi, uygulamanın HERHANGİ bir yerinde) Supabase'e
    SIFIRDAN bir bağlantı açıyorlardı. Bu, v2.0.7.156'da eklendiğinde
    zaten vardı ama v2.0.7.159 (modal) ve v2.0.7.160-165 (haber hacminin
    artması) ile fark edilir hale geldi.
  - **Bağlantı havuzu ÖNERİLMEDİ** (v2.0.7.142'de denenmiş, iki farklı
    çöküşe yol açmıştı - PROJE_NOTLARI §6'daki kalıcı karar). Bunun
    yerine HER İKİ fonksiyon 20 saniyelik `st.cache_data` ile sarmalandı
    - haber_izleme.py zaten en hızlı 2 saatte bir çalıştığı için 20
    saniyelik gecikme hiçbir bilgiyi geciktirmiyor, ama art arda
    tıklamalarda (ör. bir sayı kutusuna yazarken her tuşta rerun
    tetiklenmesi) gereksiz onlarca bağlantı açılması engelleniyor.
  - **KRİTİK YAN DÜZELTME - önbellek tutarlılığı:** Onayla/Reddet
    düğmelerine basıldığında (4 farklı yer: modal + Ana Sayfa listesi)
    `st.cache_data.clear()` eklendi - EKLENMESEYDİ, onaylanan/reddedilen
    bir tespit 20 saniye boyunca hâlâ "bekliyor" görünmeye devam ederdi
    (modal tekrar açılabilirdi). admin.py'de zaten kullanılan aynı
    "işlemden sonra global cache temizle" deseni burada da uygulandı.
  - **Bonus (aynı desen, daha küçük etki):** Haberler sayfasındaki
    `get_haber_akisi(saat=48, limit=300)` çağrısı da SADECE o sayfadayken
    ama yine önbelleksizdi - aynı 20 saniyelik önbellek eklendi.
  - **AÇIK KALAN:** Bu düzeltmenin gerçekten hissedilir bir hızlanma
    sağlayıp sağlamadığı CANLIDA doğrulanmadı - kod incelemesiyle
    bulunan, güçlü ama kesin ölçülmemiş bir kök neden. Bahri'nin
    kalıcı olarak tuttuğu "Sistem Tanılama" paneli (bkz. §6, "Sistem
    Tanılama panelini kaldırmak REDDEDİLDİ" kararı) tam olarak bunun
    için var - push sonrası hâlâ yavaşlık hissedilirse, önce o panelden
    hangi adımın (BIST/TEFAS/DOVIZ-MADEN-KRIPTO/Beklenti Modu sorguları)
    en uzun sürdüğüne bakılmalı.


  Bahri'nin üç ayrı talebi/bulgusu): KRIPTO GEREKSIZ IMPORT YAN ETKİSİ
  DÜZELTİLDİ + GETİRİ KIYASLAMASI'NA GÜNLÜK DEĞİŞİM BARLARI EKLENDİ.**
  - **Kök neden (kesin, test edilerek doğrulandı):** `worker.py`'de
    `KRIPTO = _kripto_evrenini_olustur()` MODÜL SEVİYESİNDE (fonksiyon
    dışında) çağrılıyordu - yani `worker.py`'yi SADECE `load_tefas()`
    için import eden `update_tefas_evening.py` bile, Python'ın modül
    initialize etme mekaniği yüzünden bu satırı OTOMATIK çalıştırıyor,
    gereksiz bir canlı BtcTurk/borsapy denemesi yapıyordu (`update_tefas_
    evening.yml` ortamına borsapy hiç kurulmuyor, bu yüzden HER ZAMAN
    `ModuleNotFoundError` ile başarısız olup yedek listeye düşüyordu -
    zararsızdı ama gereksizdi, artık günde 7 kez tekrarlandığı için daha
    da göze batıyordu). **Çözüm: `KRIPTO` artık TEMBEL (lazy)** -
    `_kripto_evren_al()` adlı bir getter, İLK GERÇEK KULLANIMDA hesaplayıp
    önbelleğe alıyor; `load_tefas()` hiç KRIPTO'ya dokunmadığı için
    `update_tefas_evening.py` artık borsapy'yi hiç denemeyecek. 8 kullanım
    noktası `_kripto_evren_al()` çağrısına çevrildi. İzole test edildi:
    `worker.py` import edildikten sonra `KRIPTO is None` doğrulandı
    (borsapy denenmedi).
  - **Getiri Kıyaslaması grafiğine günlük değişim barları eklendi**
    (`_render_karsilastirma`, Portföyüm sayfası): kümülatif çizgilerin
    yanına, İKİNCİL (sağ) eksende, her varlığın günlük (bir önceki güne
    göre puan) değişimini gösteren yarı saydam (opacity 0.55) bar
    grafiği eklendi. Veri KAYNAĞI: ek bir çekim YOK - tüm seriler zaten
    aynı tarih eksenini (`_gun_araligi`) paylaştığı için mevcut kümülatif
    serinin `.diff()`'i alınıyor. Legend'de sadece çizgiler görünüyor
    (barlar `showlegend=False` - aksi halde 7 varlık x 2 = 14 legend
    girdisi olurdu). `barmode="overlay"` seçildi (`"group"` yerine) -
    7 varlık gruplanınca çubuklar okunamayacak kadar incelirdi, yarı
    saydamlık üst üste binmeyi zaten okunur kılıyor.
  - **ING fiyatı sorusuna verilen cevap (kod değişikliği DEĞİL, bilgi
    amaçlı):** TEFAS'ın tasarım ilkesi gereği, hangi bankadan (ING dahil)
    işlem yapılırsa yapılsın, GERÇEKLEŞEN işlem fiyatı TEFAS'ın merkezi
    olarak hesapladığı resmi NAV'dır - ING'nin anlık ekran değeri bir
    gösterge/tahmini olabilir. Bu, Bahri'nin kendi bankasına sorup
    kesinleştirebileceği bir konu, biz garantisini veremeyiz.


  Bahri'nin bulgusu — ING bankadaki gerçek TEFAS fon fiyatlarının
  bizden farklı çıkması, "başka kaynaklardan bilgi alacaksam bu
  uygulamanın ne anlamı var" endişesi): TEFAS ÇEKİM SIKLIĞI ARTIRILDI.**
  - **Kök neden (araştırmayla doğrulandı, tahmin değil):** TEFAS'ın
    genel kuralı "fiyatlar borsalar kapandıktan sonra günde bir kez
    hesaplanır, ERTESİ İŞ GÜNÜNDE ilan edilir" (caziphesap.com,
    iyigelir.net doğrulandı). Yani T günü kapanışıyla hesaplanan NAV,
    T+1'in KENDİSİNDE (muhtemelen sabahtan itibaren) yayınlanıyor, T
    akşamı DEĞİL. Eski tek çekimimiz (~20:00-20:30 TRT) o gün zaten
    SABAHTAN beri TEFAS'ın API'sinde hazır olan bir bilgiyi gereksiz
    yere akşama kadar bekletiyordu - bu, "TEFAS günde bir kez
    fiyatlıyor" gerçeğinden kaynaklanan kaçınılmaz bir gecikme
    DEĞİLDİ, bizim seçtiğimiz saatin (günün en geç saati) yanlış
    olmasından kaynaklanan, tamamen düzeltilebilir bir gecikmeydi.
  - **Çözüm:** `update_tefas_evening.yml` artık günde TEK yerine 7 KEZ
    çalışıyor (TRT 08/10/12/14/16/18/20, 2 saatte bir) - BIST'in
    `peak_check.yml`'inde zaten kullanılan "gün içine yayılmış sık
    kontrol" felsefesi TEFAS'a da uygulandı. TEFAS ne zaman
    yayınlarsa yayınlasın en geç birkaç saat içinde yakalanır - tek
    bir "doğru saat" tahmin etmeye gerek kalmadı. Maliyet düşük:
    `update_tefas_evening.py` zaten SADECE DEĞİŞİKLİK VARSA commit
    atıyor, değişmeyen çalışmalar sadece birkaç dakikalık Actions
    süresi tüketiyor, commit/push yok.
  - **Bahri'nin kararı: zaman damgası (hangi satırın ne zaman
    çekildiğini gösteren sütun) İSTENMEDİ** - sadece zamanlama
    düzeltmesi istendi. İleride bu talep tekrar gelirse: CSV'ye
    `Fiyat_Zamani` sütunu eklenip Portföyüm/TEFAS tablolarında
    gösterilebilir, ama şu an YOK.
  - **Yan düzeltme (kozmetik, aynı dosyaya dokunurken bulundu):**
    Commit mesajı `date +'%Y-%m-%d %H:%M TRT'` ile GitHub runner'ının
    kendi saatini (UTC) yazıp yanlışlıkla "TRT" diye etiketliyordu
    (örnek: gerçekte 20:28 TRT olan bir çalışma, commit mesajında
    "17:28 TRT" görünüyordu - 3 saat yanlış). `TZ='Europe/Istanbul'`
    eklenerek düzeltildi.
  - **AÇIK KALAN:** Bu değişiklik ilk kez bu akşam (20 Ağustos, TRT
    16:00/18:00/20:00 slotlarından biri) canlıda test edilecek. Bahri
    yarın sabah ING'deki değerle karşılaştırıp doğrulamalı - hâlâ
    saatlerce gecikme varsa, gecikmenin TEFAS'ın kendi yayın saatinden
    mi (bizim tahminimiz yanlış: bazı fonlar daha geç yayınlıyor
    olabilir) yoksa başka bir sebepten mi geldiği araştırılmalı.


  "eski" görünmesi (20 Ağustos 2026, Bahri'nin bulgusu — CVL/BAG/HTS
  Portföyüm'de yanlış görünüyor, gerçek değerler farklıydı).**
  GitHub commit geçmişiyle doğrulandı: `optimized_universe.csv`'deki
  TEFAS satırları SADECE `update_tefas_evening.yml` ile günde BİR KEZ
  (~20:00-20:30 TRT) güncelleniyor - TEFAS fonları zaten günde bir kez
  resmi NAV yayınlıyor, gündüz güncelleme YAPILMIYOR (yapılamaz da,
  yayınlanan bir şey yok). Bahri'nin ekran görüntüsü gündüz, o akşamki
  güncelleme çalışmadan ÖNCE alınmıştı - gösterilen fiyatlar BİR ÖNCEKİ
  akşamın (doğru şekilde çekilmiş) NAV'ıydı, arızalı/okunamamış değildi.
  Sonraki gece worker.py tam çalışmaları (23:2x ve 00:4x TRT) TEFAS
  satırlarına HİÇ DOKUNMUYOR/AYNI DEĞERİ VERİYOR - bu da normal, akşam
  güncellemesi zaten günün NAV'ını almış oluyor.
  **Kalıcı kural: Portföyüm/TEFAS'ta "fiyat eski" şikayeti gelirse ÖNCE
  saat kaç sorulmalı - akşam ~20:30 TRT'den ÖNCEYSE bu normaldir, bug
  aramaya gerek yok. Sadece akşam güncellemesi geçtikten SONRA hâlâ eski
  fiyat duruyorsa gerçek bir arıza olabilir, o zaman
  update_tefas_evening.yml'in Actions logu incelenmeli.**
  **Yan bulgu (küçük, kozmetik, DÜZELTİLMEDİ - onay bekliyor):**
  `update_tefas_evening.py`'nin ürettiği commit mesajı saati "TRT" diye
  etiketliyor ama aslında UTC yazıyor (ör. "17:28 TRT" denilen commit,
  gerçekte 17:28 UTC = 20:28 TRT'de atılmış). Yanıltıcı ama zararsız -
  Bahri isterse düzeltilir.


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
| Sistem Tanılama panelini kaldırmak | REDDEDİLDİ (19 Ağustos 2026, Bahri'nin kararı) | Bahri "yük getiriyorsa kaldırılsın" dedi, ölçüldü: 7 blok için sayfa yüklemesi başına ~1,5 mikrosaniye (ölçtüğü ağ çağrıları saniyelerle ölçülüyor — maliyet yüz binde bir bile değil). Panel ayrıca admin-only, abonede hiç render edilmiyor. Ve §5'teki açık performans maddesi (Beklenti Modu + haber akışı yazmalarının yavaşlık yaratıp yaratmadığı) tam da bu panelle ölçülecek. **Karar: olduğu gibi kalsın. Tekrar kaldırmayı önerme.** |
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
