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
- **GÜNCELLEME (17 Temmuz 2026, Oturum XVIII): Yukarıdaki 2. madde artık
  ÇALIŞMIYOR.** `doviz.com`'un kurumsal arşiv API'si (`api.doviz.com/api/
  v12/assets/.../archive`) — hem borsapy'nin kendi canlı token çekme
  mekanizması hem elle denenen 3 farklı sayfadan (www.doviz.com,
  altin.doviz.com, kur.doviz.com) token kazıma denemesi **401 Unauthorized**
  ile karşılaştı. Site artık token'ı sayfa HTML'sine gömmüyor gibi
  görünüyor (muhtemelen JS bundle'ına taşınmış, Ocak 2026'daki kütüphane
  doğrulamasından beri değişmiş). **Harem kurumsal tarihçesi şu an dıştan
  erişilemez durumda** — 51 genişleme dövizi büyük ihtimalle Truncgil'e
  (sadece anlık fiyat, `_gecmis_veri_yok=True`) düşüyor olmalı, canlidoviz
  METAL_IDS/CURRENCY_IDS gibi doğrudan (auth gerektirmeyen) kanallar hâlâ
  çalışıyor. **Bu maddeyi "çalışıyor" varsayıp tekrar test etmeden Harem
  üzerine yeni bir özellik kurma — önce `test_maden_kaynak.py` tarzı bir
  betikle (repoda örneği var) güncel durumu doğrula.**
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
  sadece anlık, canlidoviz'de slug yok, Harem 401). **Bahri'nin kararı
  (17 Temmuz): şimdilik sistemde kalsınlar, RSI/Skor boş görünsün — Paladyum
  gibi kaldırılmaları henüz onaylanmadı, bekleniyor.**
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
| Paladyum (Değerli Madenler) | KALDIRILDI (v2.0.7.76) | RSI/Ret1M için hiçbir kaynakta (canlidoviz'de slug yok, Harem 401) geçmiş veri yok, sonsuza dek 0 skor gösterecekti. |
| Harem/doviz.com kurumsal arşivi (yeni tür eklemek için) | ERİŞİLEMEZ (17 Tem 2026) | Token çıkarma mekanizması (hem borsapy'ninki hem elle deneme) 401 alıyor - site token'ı artık HTML'e gömmüyor. Tekrar denemeden önce güncel durumu test et. |

---

## 6. Versiyon Kilometre Taşları (özet)

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

**Yeni bir oturumda "acaba X daha önce denendi mi" sorusu varsa, önce bu
dosyayı ve `git log --oneline` çıktısını kontrol et.**
