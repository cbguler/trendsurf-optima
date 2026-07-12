# 1. Sistem Mimarisi

## 1.1 Dosya Yapısı

Konum: C:/Users/bahri/Desktop/TrendSurf_Optima/

| **Dosya**                                                                              | **Açıklama**                                                                  |
|----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| app.py                                                                                 | Ana Streamlit uygulaması — tek dosya, tüm sayfalar                            |
| worker.py                                                                              | Gece boyu GitHub Actions üzerinde çalışan veri çekme/evren oluşturma motoru   |
| db.py                                                                                  | Supabase PostgreSQL bağlantısı                                                |
| auth.py / auth_reset.py                                                                | Kimlik doğrulama ve şifre sıfırlama                                           |
| admin.py                                                                               | Admin panel fonksiyonları, abone onaylama                                     |
| emailer.py / emailer_standalone.py                                                     | Günlük e-posta rapor sistemi (manuel + GitHub Actions)                        |
| alert_settings.py / peak_tracker.py / peak_alert_emailer.py / peak_check_standalone.py | Kâr realizasyonu uyarı sistemi (v2.0)                                         |
| live_data.py                                                                           | Canlı veri overlay                                                            |
| bigpara_client.py                                                                      | Altın/gümüş TL fiyat yedek kaynağı                                            |
| halka_arz_client.py / kap_client.py                                                    | KAP XHARZ endeks ve temel analiz verileri                                     |
| upcoming_ipo_client.py                                                                 | Yaklaşan Halka Arzlar modülü — KAP RSC'den PDF indirme, önbellekleme          |
| fiyat_tespit_parser.py                                                                 | Fiyat Tespit Raporu PDF ayrıştırıcı — Tip A/B/C/D + Türkçe OCR normalizasyonu |
| temettu_client.py                                                                      | KAP XTMTU + yfinance temettü verileri                                         |
| tefas_client.py                                                                        | TEFAS fon verileri                                                            |
| tcmb_client.py                                                                         | TCMB döviz kuru yedek kaynağı                                                 |
| signals.py                                                                             | Sinyal/Optima Skoru hesaplama motoru                                          |
| firsat_radari.py                                                                       | Fırsat Radarı — 15 dk'lık tarama + alarm e-postaları (GitHub Actions)         |
| data_health_check.py                                                                   | Veri akışı sağlık kontrolü — kategori tazeliği izleme + admin uyarı maili     |
| update_tefas_evening.py                                                                | TEFAS akşam NAV güncellemesi (TRT 20:00/20:30 cron)                           |
| pdf_text_extract.py                                                                    | PDF → metin (pdfplumber + gerektiğinde Türkçe OCR)                            |
| temel_deger_hesaplama.py                                                               | Graham + Çarpan Bazlı Değer — özet kutusu ve Format-2 (LTM) metodolojisi      |
| data_pipeline.py                                                                       | Veri pipeline orkestratör                                                     |

## 1.2 Veri Dosyaları

- optimized_universe.csv — Worker çıktısı, tüm varlıklar (~2.157 satır)

- upcoming_ipo_cache/upcoming_ipo.json — Yaklaşan halka arz listesi
  önbelleği (12 saat TTL)

- upcoming_ipo_cache/fiyat_tespit_sonuclari.json — Halka Arz PDF analiz
  önbelleği (süresiz; kalıcı kopyası Supabase ipo_valuations'ta)

- health_state.json — sağlık kontrolünün kategori imza/zaman durumu
  (her koşuda Actions tarafından commit edilir)

- KAP_BIST.xlsx — BIST hisse sembol/slug eşleme

- Endeksler.xlsx — Endeks üye listeleri (fallback)

## 1.3 Varlık Sayıları (Güncel)

| **Kategori** | **Adet**      |
|--------------|---------------|
| BIST         | 772 hisse     |
| TEFAS        | ~1.347 fon    |
| Kripto       | 18            |
| Maden        | 9             |
| Döviz        | 12 TRY çapraz |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td style="background-color:#fff4e5;border-left:5px solid #e08a00;padding:14px 16px;border-radius:4px;"><p><strong>⚠ Kaldırılan Varlıklar (v1.9.10)</strong></p>
<p>ONS_ALTIN_TRY ve BNB, USD/TL karışıklığı ve tutarsız çevirim
nedeniyle sistemden çıkarıldı. Bu varlıklar artık
görüntülenmez.</p></td>
</tr>
</tbody>
</table>

# 2. Veri Kaynakları ve Yedek Mekanizmaları

| **Varlık Sınıfı**   | **Birincil Kaynak**               | **Yedek Kaynak**                             |
|---------------------|-----------------------------------|----------------------------------------------|
| BIST                | borsapy (BtcTurk üzerinden canlı) | yfinance (.IS suffix) → son bilinen fiyat    |
| TEFAS               | TEFAS Next.js API                 | pytefas kütüphanesi                          |
| Maden (TL)          | Bigpara HTML scraping             | yfinance (GC=F vb.) × USDTRY                 |
| Döviz               | yfinance (=X suffix)              | TCMB XML API → EVDS API (TCMB_KEY)           |
| Kripto              | BtcTurk (BTC/ETH doğrudan TL)     | yfinance USD × USD/TRY                       |
| Temel Analiz (BIST) | kap_client.py → kap.org.tr        | yfinance info (P/E, beta, temettü verimi)    |
| Halka Arz / Temettü | KAP RSC endpoint (Next.js)        | Endeksler.xlsx                               |
| Fiyat Tespit Raporu | KAP PDF indirme + pdfplumber      | Tesseract OCR (tur) — taranmış sayfalar için |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td style="background-color:#eaf2fb;border-left:5px solid #1b6ef3;padding:14px 16px;border-radius:4px;"><p><strong>ⓘ Worker.py Çalışma Konumu</strong></p>
<p>worker.py, GitHub Actions üzerinde gece (TRT 02:00/03:00) çalışır.
Fiyat Tespit Raporu işleme de aynı worker sürecinde, gece boyu
gerçekleşir; app.py sadece önceden hesaplanmış önbelleği okur (canlı PDF
işleme yapmaz).</p></td>
</tr>
</tbody>
</table>

## 2.1 Fiyat Tespit Raporu Ayrıştırma Mimarisi

fiyat_tespit_parser.py, KAP'ta yayınlanan Fiyat Tespit Raporu PDF'lerini
beş farklı desene ayrıştırabilir (Tip A: Gedik/Halk Yatırım kademeli
akış tablosu — iskonto-ÖNCESİ değer tuzağına karşı korumalı, Tip B:
İnfo Yatırım ağırlıklı özet, Tip C: İntegral/SOHO doğrudan "Halka Arz
Fiyatı" ifadesi, Tip D: anlatım cümlesinden çıkarım, Tip E: "İskonto(su)
Sonrası Pay Değeri" etiketi — TERA örneği). Raporun metne çevrilmesi önce pdfplumber ile denenir; metin
çıkmazsa (taranmış/görüntü sayfa) Tesseract OCR (Türkçe dil paketi)
devreye girer.

temel_deger_hesaplama mantığı, raporun "özet kutusu"ndan (Gelir Özeti +
Bilanço + Çarpanlar) bağımsız olarak Graham Sayısı ve Çarpan Bazlı Değer
hesaplar — aracı kurumun kendi değerlemesinden tamamen ayrı, ikinci bir
bakış açısı sunar.

Özet kutusu olmayan raporlar için Format-2 (v2.0.6): tam finansal
tablolardan LTM (son 12 ay) metodolojisi uygulanır — son 12 ay = son tam
yıl − geçen yıl ara dönem + son ara dönem; kalemler tablo tarih
başlığıyla hizalanmak zorundadır. Çarpan Bazlı Değer, FD/FAVÖK
tablolarının medyan Özkaynak Değeri / Pay Adedi olarak hesaplanır.
Belgenin ortasındaki sayfalar yalnızca metin katmanlıysa taranır (orta
sayfalarda OCR yapılmaz — maliyet kontrolü). Doğrulanmış üretim örneği
(TERA): Arz 70,00 / İskonto %20 / Graham 26,39 / Çarpan 91,27.

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td style="background-color:#fff4e5;border-left:5px solid #e08a00;padding:14px 16px;border-radius:4px;"><p><strong>⚠ Bilinçli Boş Bırakma İlkesi</strong></p>
<p>OCR kalitesi düşük olan raporlarda (örn. GOLDA, TSK, TERA),
Graham/Çarpan alanları bilinçli olarak boş bırakılır — yanlış bir rakam
üretmektense hiç göstermemek tercih edilir. Bu davranışı
değiştirmeyin.</p></td>
</tr>
</tbody>
</table>

# 3. Fırsat Radarı ve Veri Sağlığı

## 3.1 Fırsat Radarı Mimarisi (firsat_radari.py)

Akış: cron-job.org (~15 dk) → GitHub Actions firsat_radari.yml
(workflow_dispatch, PAT ile) → firsat_radari.py taraması → Supabase
intraday_scores tablosuna UPSERT. GitHub'ın kendi cron'u yalnızca yedek
tetikleyicidir (*/20, best-effort). Skor formülü worker.py ile birebir
aynıdır (hacim/DD düzeltmesi + CSV'den PB/PE/DY temel bileşeni) — bu
sayede uygulamadaki skor ile alarm skoru hiçbir zaman ayrışmaz.

Hacim trendi bileşeni (son 5 gün / son 20 gün ortalaması) YALNIZCA
TAMAMLANMIŞ günlerle hesaplanır — bugünün kısmi hacim çubuğu dışlanır
(v2.0.7.1). Aksi halde sabah saatlerinde düşük görünen günlük hacim,
bileşeni −10'a çekip gün boyu biriktikçe +5'e döndürüyor ve hisse
başına 15 puana kadar yapay "sıçrama" alarmı üretiyordu (10 Temmuz
sabahı 8 varlık, tamamı bu desende). Fiyat/RSI/momentum canlı kalır;
aynı koruma worker.py'de de vardır (formül paritesi).

| **Kapsam**          | **Pencere**                                    |
|---------------------|-------------------------------------------------|
| BIST (772)          | Seans içi, hafta içi TRT 10:00-18:30            |
| Döviz/Maden/Kripto  | 7/24                                            |
| TEFAS               | Günde 1 kez, TRT 20:40-21:40 penceresi          |

TEFAS taramasını pencere dışında test etmek için workflow elle
`tefas_zorla=1` girdisiyle çalıştırılır (`RADAR_TEFAS_ZORLA=1`).
TEFAS penceresindeki koşu, diğer koşulardan belirgin uzun sürer
(~4 dk'ya karşı ~1 dk) — Actions listesinde bu süre farkı, TEFAS
taramasının çalıştığının hızlı bir göstergesidir.

## 3.2 Alarm Sistemi

Alarm e-postaları ADMIN_EMAIL'e gider. İki tetik: eşik (skor 75'i
aşağıdan kesince) ve sıçrama (önceki ölçüme göre +10 puan). Üç filtre:

- **Veri kalite kapısı** — 22 günden kısa geçmişle gelen hisse o koşuda
  yazılmaz (yfinance hız sınırı salınımının ürettiği sahte sıçramaları
  keser).

- **Tazelik koruması** — BIST'te önceki ölçüm 6 saatten eskiyse sıçrama
  alarmı üretilmez (seans açılışında dünkü skora kıyas engellenir).

- **Anlamlılık tabanı** — sıçrama yalnızca yeni skor ≥ 55 ise alarm
  üretir (5→18 gibi alçak bölge sıçramaları elenir).

Günlük tekrar koruması: radar_alerts tablosu, ON CONFLICT ile aynı gün
aynı varlık + aynı alarm türünü bir kez geçirir. Hedef alarm hacmi:
günde 0-2.

| **Secret (Actions)** | **Varsayılan** | **Anlamı**                        |
|----------------------|----------------|------------------------------------|
| RADAR_ESIK           | 75             | Eşik alarmı sınırı                 |
| RADAR_SICRAMA        | 10             | Sıçrama alarmı puan farkı          |
| RADAR_SICRAMA_TABAN  | 55             | Sıçramanın alarm sayılacağı taban  |

## 3.3 Keep-Alive

Streamlit Cloud, ziyaret edilmeyen uygulamayı uyutur. Uyandırma, radar
workflow'una gömülü `curl -L` adımıyla yapılır (yönlendirme zincirini
cookie'lerle takip ettiği için auth katmanını geçer; cron-job.org'un
düz GET'i bunu başaramıyordu). Ayrı bir cron-job keep-alive işi YOKTUR —
eski "TrendSurf Keep-Alive" işi silindi.

## 3.4 Veri Akışı Sağlık Kontrolü (data_health_check.py)

health_check.yml her 30 dakikada bir (GitHub schedule) çalışır; bir
kategori beklenenden uzun süre güncellenmiyorsa ADMIN_EMAIL'e uyarı
gönderir. v2.0.6.x itibarıyla kaynak ayrımı:

- BIST / DOVIZ / KRIPTO / MADEN tazeliği Supabase intraday_scores
  tablosundaki updated_at'ten izlenir (eşik 1 saat; BIST yalnızca seans
  içi kontrol edilir, 11:00 öncesi açılış toleransı vardır).

- TEFAS, CSV imzasından izlenir (eşik 30 saat — günde 1 NAV).

Supabase bağlantısı 10 sn / sorgu 15 sn zaman sınırlıdır: Supabase
arızasında iş askıda kalıp GitHub'dan "cancelled" maili üretmek yerine
hızla kendi "ulaşılamadı" uyarısını üretir. Koşu sonunda
health_state.json repoya commit edilir.

## 3.5 Halka Arz Kalıcı Katmanı (ipo_valuations) — v2.0.6.4

Zorla Yenile/worker'ın çıkardığı Arz Fiyatı/İskonto/Graham/Çarpan
değerleri Supabase ipo_valuations tablosuna UPSERT edilir ve okumada
yerel null alanların üzerine bindirilir. Kurallar: null asla dolu
değeri ezmez (SQL COALESCE + alan bazlı merge); Supabase erişilemezse
davranış eskisiyle aynıdır (fail-soft). Bu katman, Streamlit Cloud
yeniden başlatmalarında değerlerin kaybolması sorununu kapattı (gece
worker'ının Actions ortamında PDF çıkarımı başarısız olduğundan repo
cache'i null kalıyordu). Şema: ipo_valuations.sql.

# 4. GitHub ve Deployment

## 4.1 GitHub Repo

github.com/cbguler/trendsurf-optima — kamuya açık (public) repo. Git
geçmişi, sızan GCP servis hesabı bilgilerini temizlemek için
filter-branch ile yeniden yazılmıştır.

## 4.2 Streamlit Cloud

Uygulama URL'si, share.streamlit.io panelinden özelleştirilebilir alt
alan adı ile yayınlanır (örn. https://trendsurfoptima.streamlit.app).
Panel özelliği: Settings → General → App URL.

## 4.3 Streamlit Cloud Secrets

- ADMIN_EMAIL, ADMIN_PASS, ADMIN_NAME — admin otomatik seed

- SUPABASE_DB_URL — pooler connection string (port 6543)

- \[email\] altında: smtp_user, smtp_pass, smtp_host, smtp_port

- TCMB_KEY — TCMB EVDS API anahtarı

GitHub Actions Secrets (repo → Settings → Secrets and variables):

- SUPABASE_DB_URL, SMTP_USER / SMTP_PASS / SMTP_HOST / SMTP_PORT,
  ADMIN_EMAIL — worker/radar/sağlık kontrolü/e-posta işleri için

- GH_TOKEN (PAT) — cron-job.org'un workflow_dispatch tetiklemesi ve
  Actions içi commit/push için. Temmuz 2026'da yenilendi (eskisi sohbet
  kaydına sızdığı için iptal edildi) — sızıntı şüphesinde derhal iptal
  edip yenisini hem GitHub hem cron-job.org tarafında güncelleyin.

- RADAR_ESIK / RADAR_SICRAMA / RADAR_SICRAMA_TABAN — bkz. 3.2

## 4.4 Zamanlanmış Görevler (Scheduler)

GitHub Actions'ın kendi cron zamanlayıcısı, sık aralıklarla (15 dk altı)
tetiklemelerde güvenilir çalışmadığından, harici bir zamanlayıcı
(cron-job.org) benimsenmiştir. Bu servis, ilgili GitHub Actions
workflow'unu dışarıdan tetikler (workflow_dispatch), böylece GitHub'ın
kendi cron throttling'i aşılır.

| **Workflow**                | **Görev**                           | **Sıklık**                                     |
|-----------------------------|-------------------------------------|------------------------------------------------|
| send_email.yml              | Günlük portföy raporu               | Kullanıcı ayarına göre, saatte 4 kontrol slotu |
| peak_check.yml              | Kâr realizasyonu kontrolü           | Her 15 dakika (cron-job.org tetikli)           |
| update_data.yml / worker.py | Evren verisi + Halka Arz PDF işleme | Gece TRT 02:00/03:00 (yedekli çift cron)       |
| firsat_radari.yml           | Fırsat Radarı taraması + keep-alive | ~15 dk cron-job.org; yedek GitHub cron 20 dk   |
| update_tefas_evening.yml    | TEFAS akşam NAV güncellemesi        | TRT 20:00 (yedek 20:30) GitHub cron            |
| health_check.yml            | Veri akışı sağlık kontrolü          | Her 30 dakika (GitHub cron)                    |

## 4.5 Güvenlik Notları

- Supabase Row Level Security (RLS) aktif — her kullanıcı yalnızca kendi
  verisine erişir.

- Sızan GCP servis hesabı bilgileri git geçmişinden filter-branch +
  force-push ile temizlendi.

- .gitignore: venv, cache, secrets, \*.json, live_data.zip, debug/gecici
  dosyalar (golda\_\*.py, \*\_YEDEK.json vb.)

## 4.6 Git Çakışma Çözümü

- Push reddedilirse: git fetch origin → git pull origin main (merge)
  veya gerekiyorsa git reset --hard origin/main

- Her zaman değişikliğe başlamadan önce git pull origin main ile en
  güncel hali çekin.

- Tek dosya politikası: app.py — asla app_v15/v16 gibi kopya dosyalar
  oluşturulmaz.

# 5. Kullanıcı Yönetimi

## 5.1 Kullanıcı Plan Tipleri

| **Tip** | **Açıklama**                         |
|---------|--------------------------------------|
| free    | Sınırlı erişim — temel listeleme     |
| pro     | Tüm sayfalar, e-posta raporu         |
| premium | Pro + kâr realizasyonu uyarı sistemi |
| admin   | Sistem yöneticisi, tüm yetkiler      |

## 5.2 Yeni Abone Onaylama

1.  Admin Paneli → Bekleyen Kullanıcılar bölümüne gidin.

2.  Yeni kaydın e-posta/ad bilgisini kontrol edin.

3.  "Onayla" butonuna basın — is_active = TRUE olur, kullanıcı giriş
    yapabilir.

## 5.3 Supabase Tabloları (Özet)

| **Tablo**       | **İçerik**                                                            |
|-----------------|-----------------------------------------------------------------------|
| users           | Kullanıcı kayıtları (email, password_hash, plan, is_active, is_admin) |
| sessions        | Beni Hatırla session token'ları (90 gün)                              |
| portfolio       | Pozisyonlar (her satır bir varlık)                                    |
| password_resets | Şifre sıfırlama tokenları (24 saat geçerli)                           |
| email_settings  | Günlük rapor saatleri                                                 |
| alert_settings  | Kâr realizasyonu uyarı tercihleri                                     |
| peak_tracker    | Peak (tepe fiyat) takibi — composite key (user_id, ticker)            |
| intraday_scores | Fırsat Radarı gün içi skorları (kategori bazlı updated_at ile)        |
| radar_alerts    | Radar alarm günlük dedupe kaydı (ON CONFLICT)                         |
| ipo_valuations  | Halka Arz değerleme kalıcı katmanı (v2.0.6.4, null dolu değeri ezmez) |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td style="background-color:#eaf2fb;border-left:5px solid #1b6ef3;padding:14px 16px;border-radius:4px;"><p><strong>ⓘ Migrasyon Notu</strong></p>
<p>v1.9.6 öncesi SQLite kullanılıyordu; tüm veri artık Supabase
PostgreSQL'e (Frankfurt eu-central-1, port 6543 pooler)
taşınmıştır.</p></td>
</tr>
</tbody>
</table>

# 6. E-posta Sistemi

## 6.1 Günlük Rapor Sistemi

- emailer.py — Streamlit'ten manuel "Şimdi Gönder"

- emailer_standalone.py — GitHub Actions cron'undan otomatik, saatte 4
  kontrol slotu

- email_send_log tablosu — atomik INSERT ON CONFLICT ile mükerrer
  gönderim koruması

## 6.2 Kâr Realizasyonu Uyarı Maili

- peak_alert_emailer.py — HTML mail formatı + SMTP gönderim

- Her kullanıcının uyarısı yalnızca kendi e-posta adresine gider

- mark_alert_sent — mail gönderildikten sonra peak_tracker'da flag set
  edilir

## 6.3 Gmail App Password Yenileme

1.  myaccount.google.com/apppasswords adresine gidin.

2.  Yeni App Password oluşturun.

3.  Streamlit Cloud Secrets → smtp_pass güncelleyin.

4.  GitHub Actions Secrets → SMTP_PASS güncelleyin (her iki yer de).

# 7. Sık Karşılaşılan Sorunlar

| **Sorun**                           | **Sebep**                                                                  | **Çözüm**                                                               |
|-------------------------------------|----------------------------------------------------------------------------|-------------------------------------------------------------------------|
| BIST hisseleri eksik geliyor        | GitHub Actions yfinance rate limit                                         | worker.py'nin gece işleyişini kontrol edin, gerekirse manuel tetikleyin |
| Altın fiyatı yanlış                 | yfinance ons/gram karışıklığı                                              | Bigpara birincil kaynak — otomatik düzelmeli                            |
| Türkçe karakter bozuk               | KAP API encoding                                                           | fix_encoding (latin-1 → UTF-8) çözümü                                   |
| E-posta gitmiyor                    | SMTP Secrets eksik/yanlış                                                  | Streamlit + GitHub Actions Secrets kontrol                              |
| Login beni unutuyor                 | v2.0.7.7 öncesi: `st.context.cookies` bu Streamlit Cloud kurulumunda HİÇBİR ZAMAN çerezi görmüyordu (kanıtlandı — giriş sonrası bile boş dönüyordu); ayrıca JS/URL-yönlendirme denemeleri sandboxed iframe navigasyon kısıtına takıldı (DevTools: "frame is sandboxed, disallowed from navigating its ancestors") | v2.0.7.8'de KESİN çözüldü — JS/çerez tamamen terk edildi, token doğrudan Python'dan `st.query_params` ile taşınıyor (sandbox'ı bypass eder). Bilinen ödün: token bir süre URL'de görünür kalır |
| Database connection error           | Supabase pooler 6543 yanlış                                                | SUPABASE_DB_URL kontrol                                                 |
| Halka Arz Graham/Çarpan boş         | OCR kalitesi düşük rapor                                                   | Beklenen/güvenli davranış — manuel düzeltme yapılmaz                    |
| Peak check çalışmıyor               | cron-job.org tetiklemesi kesilmiş olabilir                                 | cron-job.org panelinden job durumunu kontrol edin                       |
| Ana Sayfa tablosu mobilde dağılıyor | st.columns() ~640px altında dikey istifleniyor (Streamlit platform kısıtı) | st.dataframe (clickable_table) formatı kullanılır, mobilde dağılmaz     |
| Radar alarmı hiç gelmiyor           | cron-job.org tetiklemesi kesik / Actions hatalı / eşikler yüksek           | cron-job.org paneli → Actions koşuları → radar_alerts tablosu sırasıyla |
| Halka Arz değerleri yeniden başlatınca kayboluyordu | Yerel cache Streamlit Cloud yeniden başlatmasında sıfırlanıyordu | v2.0.6.4'te çözüldü — ipo_valuations kalıcı katmanı (bkz. 3.5)          |
| BNB/CLINK/ICP fiyatı gelmiyor       | BtcTurk 400 hatası (kalıcı görünüyor)                                      | Açık madde — kaynak/kod eşlemesi incelenecek; fiyatsız varlık skoru 0   |
| Uygulama "Oh no" + Segmentation fault | Sürümü sabitlenmemiş bir bağımlılığın bozuk yeni sürümü (örn. 10 Tem 2026: pyarrow 25.0.0, st.dataframe'de segfault) | Stabil ve çöken deploy loglarının paket listelerini karşılaştır; değişen paketi requirements.txt'te eski sürüme sabitle. Kod revert'i işe yaramıyorsa suçlu bağımlılıktır |
| `components.v1.html` içinden JS ile sayfa yönlendirme/URL değiştirme çalışmıyor | Streamlit'in bu iframe'e uyguladığı sabit sandbox, üst çerçeveyi (parent) navigasyon iznini içermiyor (allow-top-navigation yok) — DevTools'ta "frame is sandboxed, disallowed from navigating its ancestors" hatası | Navigasyon gerektiren HİÇBİR JS çözümü kullanılamaz (cerez okuma/yazma JS ile hâlâ mümkün, sadece navigasyon engelli); kalıcılık/URL güncelleme gereken durumlarda doğrudan Python'dan `st.query_params` kullan (bkz. v2.0.7.8, Beni Hatırla) |

## 7.1 Manuel CSV Güncelleme

Eğer worker.py'nin yerel çıktısını manuel push etmek gerekirse:

- cd C:/Users/bahri/Desktop/TrendSurf_Optima

- python worker.py

- git add -f optimized_universe.csv

- git commit -m "veri guncelleme" && git push origin main

# 8. Versiyon Geçmişi (Özet)

### 11 Temmuz 2026 (v2.0.7.4 – v2.0.7.29) — Beni Hatırla Kesin Çözümü, Portföy/Halka Arz/Temettü İyileştirmeleri

- v2.0.7.29: Ana Sayfa başlığına logo eklendi

- v2.0.7.25–28: Portföyüm tablosuna **K/Z (TL)** sütunu eklendi (Toplam
  ile K/Z % arasına); alt "TOPLAM PORTFÖY DEĞERİ" satırı tablo
  sütunlarıyla hizalanacak şekilde yeniden tasarlandı (etiket ayrı üst
  satırda, rakamlar kendi sütunlarının altında, eşit font boyutu);
  "Optima Skor" sütun genişliği otomatik hesaplamaya bırakıldı (manuel
  sabitleme yatay scroll'a yol açıyordu)

- v2.0.7.21–24: Ana Sayfa'da bütçe kullanım verimliliği — lot
  yuvarlamasından kalan bütçe artığı, en yüksek Optima Skorlu seçili
  varlıklara round-robin dağıtılıyor (Max Varlık Sayısı bozulmuyor).
  "Hedef Tutar" sütunu kaldırıldı (kafa karıştırıyordu), tek sütun:
  "Tutar (₺)". Toplam satırında sıralama değişti: Bütçe Kullanımı önce,
  Toplam Tutar sonra (en sağdaki "Tutar" sütununun devamı gibi)

- v2.0.7.23: **Kritik bug düzeltmesi** — `calc_optimization_income`
  fonksiyonu var olmayan `"Lot / Adet"` sütununa bakıyordu (gerçek adı
  `"Birim"`), bu yüzden BIST temettü geliri hesaplamada HER ZAMAN 0
  çıkıyordu; "Tahmini Yıllık Pasif Gelir" pratikte sadece TEFAS'ın
  spekülatif projeksiyonundan geliyordu. Ayrıca metodoloji tutarlı hale
  getirildi: DÖVİZ ve MADEN de artık TEFAS ile aynı yöntemle (1A getiri
  bileşik yıllıklandırma) hesaplanıyor; sadece BIST/KRIPTO gerçek veri

- v2.0.7.14–15: Halka Arz modülü — işlem görmeye başlamış (BIST'e
  XHARZ ile mezun olmuş) şirketler "Yaklaşan Halka Arzlar" listesinden
  otomatik düşürülüyor. İlk versiyon (v2.0.7.14) genel
  optimized_universe.csv'yi kaynak aldığı için hem stub kayıtlar (fiyatı
  0, "(islem gormuyor)") hem de ticker kod çakışmaları (örn. "TERA" hem
  yeni bir IPO'nun KAP referans kodu hem de alakasız, zaten işlem gören
  bir şirketin gerçek ticker'ı) yüzünden yanlış pozitif riski
  taşıyordu; v2.0.7.15'te kaynak SADECE `bist_universe_dynamic`
  (XHARZ-onaylı mezuniyet) tablosuna değiştirildi

- v2.0.7.16–17: Temettü tablosu sıralama hatası düzeltildi —
  yfinance'in `exDividendDate` alanı geçmişteki en son bilinen tarihi
  döner (yaklaşan değil); önceki saf kronolojik artan sıralama, yıl
  önce geçmiş tarihleri listenin tepesine çıkarıyordu. Artık: gelecek
  tarihler en yakından en uzağa, geçmiş tarihler en yeniden en eskiye,
  tarihsiz kayıtlar en sonda. Yeni "Durum" sütunu (Yaklaşıyor/Geçti
  rozetleri) eklendi

- v2.0.7.10–13: "Yeni Pozisyon Ekle" varlık kutusu artık boş açılıyor
  (placeholder + arama); Portföyüm tablosunda çoklu satır seçimi + toplu
  silme eklendi; Uyarı Ayarları panelinde "Kaydet" ve "Tüm Peak'leri
  Sıfırla" blokları görünür sınırlı kutulara alındı (Şimdi Kontrol Et
  ile karışıyordu)

- v2.0.7.9: Yeni-abonelik bildirim maili mobil uyumlu hale getirildi —
  tek sütun, büyük tıklanabilir "Admin Panelini Aç" butonu
  (`?go=admin` URL parametresi, sadece is_admin=True için otomatik
  panele yönlendirir — fizyoterapi gibi saha durumlarında telefondan
  hızlı onay için)

- v2.0.7.4–8: **Beni Hatırla kesin çözümü.** v2.0.7.2'nin
  `st.context.cookies` yaklaşımı hiç çalışmadı — ekran-içi geçici
  tanılama paneliyle kanıtlandı (giriş sonrası bile "cerez anahtarlari:
  []" dönüyordu). Sonraki deneme (JS ile çerez okuyup URL'e ekleyip
  yönlendirme) de sandboxed iframe'in üst çerçeveyi navigasyon
  kısıtına takıldı (DevTools: "Unsafe attempt to initiate navigation...
  frame is sandboxed"). KESİN ÇÖZÜM: JS/çerez tamamen terk edildi,
  token login anında doğrudan Python'dan `st.query_params["_ta"]`'ya
  yazılıyor (sandbox'ı bypass eder, Streamlit'in kendi ana çerçevesinden
  çalışır); F5'te bu URL ile fresh istek gelir, token okunup
  session_state'e yazılır. **Öğrenilen ders:** `components.v1.html`
  iframe'i navigasyon/üst-çerçeve erişimi gerektiren hiçbir JS'i
  çalıştıramaz (sandbox kısıtı Streamlit'in kendi sabit özelliği,
  değiştirilemez) — bu tür kalıcılık ihtiyaçlarında doğrudan
  `st.query_params` tercih edilmeli

### v2.0.5.x – v2.0.7.x (Temmuz 2026) — Fırsat Radarı ve Kalıcılık Dönemi

- v2.0.7.3: pyarrow==24.0.0 ve websockets==16.0 sabitlendi — 10
  Temmuz'da yayınlanan pyarrow 25.0.0, st.dataframe serileştirmesinde
  Segmentation fault üreterek uygulamayı her etkileşimde çökertti
  (giriş ekranı tablosuz olduğu için açılıyordu). Teşhis, stabil ve
  çöken deploy loglarının paket karşılaştırmasıyla kondu; kod
  değişikliklerinin suçu yoktu

- v2.0.7.2: Beni Hatırla kalıcı oturum — 90 günlük token tso_auth
  çerezine yazılır, açılışta st.context.cookies ile sunucu tarafında
  geri okunur (iframe sandbox'a takılan localStorage denemelerinin
  yerine). Sayfa yenileme ve push sonrası redeploy artık oturumu
  düşürmez; çıkışta çerez temizlenir

- v2.0.7.1: Skorun hacim trendi bileşeninde bugünün kısmi çubuğu
  dışlandı — sabah/gün içi yapay sıçrama alarmları giderildi (bkz. 3.1)

- Fırsat Radarı (firsat_radari.py): BIST 772 seans içi 15 dk'da bir,
  döviz/maden/kripto 7/24, TEFAS akşam penceresi — Supabase
  intraday_scores'a UPSERT; skor formülü worker.py ile birebir

- Alarm sistemi: eşik 75 + sıçrama +10 (taban 55); veri kalite kapısı
  (22 gün), tazelik koruması (6 saat), günlük dedupe (radar_alerts)

- Uygulama: skor TEK kaynak (tablo=Top5=AnaSayfa=Portföy=Detay); BIST
  772 tek liste, sayfalama kaldırıldı; fiyatsız varlık skoru 0; get_hist
  5 dk cache (başarısız sonuç cache'lenmez); "Canlı veri" kutusu ve
  "Döviz/Kripto Tanılama" kaldırıldı, "Sistem Tanılama" duruyor

- Keep-alive radar workflow'una gömüldü (curl -L); cron-job
  "TrendSurf Keep-Alive" işi silindi

- data_health_check.py v2.0.6.3: BIST/DOVIZ/KRIPTO/MADEN tazeliği
  Supabase'ten (1 saat eşik), TEFAS CSV'den (30 saat); bağlantı/sorgu
  zaman sınırlı

- worker.py: kripto_end NameError düzeltildi (gece çöküşü bitti);
  PB/PE/DY CSV'ye yazılıyor; yfinance>=0.2.60

- Halka Arz: Tip E fiyat deseni, Tip A iskonto-öncesi tuzak koruması,
  Graham Format-2 (LTM), şirket adı "Anonim Şirketi" düzeltmesi;
  v2.0.6.4 ipo_valuations kalıcı katmanı — değerler yeniden
  başlatmalarda artık kaybolmuyor

- Güvenlik: PAT yenilendi (eskisi sohbete sızdığı için iptal)

### v2.0.4.x (Temmuz 2026) — Halka Arz, Tablo ve Mobil Uyum Dönemi

- Yaklaşan Halka Arzlar modülü: KAP RSC reverse-engineering, PDF
  indirme, Tip A/B/C/D ayrıştırma, Türkçe OCR normalizasyonu

- Fiyat Tespit Raporu'ndan bağımsız Graham Değeri + Çarpan Bazlı Değer
  hesaplama

- Halka Arz ve Temettü sayfaları HTML tabloya çevrildi — renk kodlama,
  Ex-Date vurgusu, mobil yatay kaydırma

- Ana Sayfa tablosu birden fazla revizyon sonrası native st.dataframe
  formatına oturdu — mobil uyumlu, satır tıklamalı

- Ana Sayfa optimizasyon mantığına feasibility/su doldurma algoritması
  eklendi — karşılanamayan varlıklar artık listelenmiyor

- 3D pasta grafik (Kategori Dağılımı) — özel SVG render, bitişik/dolu
  dilim tasarımı

- Mobil uyumluluk düzeltmeleri: sidebar sabit oku, tablo min-width,
  pasta grafik etiket mesafesi

- Güvenlik: Supabase RLS, git geçmişi temizliği (GCP servis hesabı
  sızıntısı), repo public'e açıldı

- cron-job.org harici zamanlayıcıya geçiş — GitHub Actions'ın kendi cron
  throttling'ini aşmak için

### v2.0.1 – v2.0.3.x (Haziran 2026)

- Kâr realizasyonu uyarı sistemi (peak tracking) tam otomasyonu, GitHub
  Actions entegrasyonu

- emailer_standalone.py mükerrer gönderim koruması (email_send_log)

- Teknik göstergeler modülü: MA20/MA50/52H/Max Drawdown/MACD

- Bulanıklaşma fix: autorefresh 60sn → 300sn, dosya temizliği

### v1.9.x ve Öncesi

- SQLite → Supabase PostgreSQL migrasyonu

- TEFAS / KAP entegrasyonu, BIST live data (borsapy)

- v1.0 — İlk yayın: SQLite, manuel portföy girişi, Optima Skor formülü,
  5 varlık sınıfı
