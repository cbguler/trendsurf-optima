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
| data_pipeline.py                                                                       | Veri pipeline orkestratör                                                     |

## 1.2 Veri Dosyaları

- optimized_universe.csv — Worker çıktısı, tüm varlıklar (~2.157 satır)

- upcoming_ipo_cache/fiyat_tespit_sonuclari.json — Halka Arz PDF analiz
  önbelleği

- KAP_BIST.xlsx — BIST hisse sembol/slug eşleme

- Endeksler.xlsx — Endeks üye listeleri (fallback)

## 1.3 Varlık Sayıları (Güncel)

| **Kategori** | **Adet**      |
|--------------|---------------|
| BIST         | ~770 hisse    |
| TEFAS        | ~1.348 fon    |
| Kripto       | 18            |
| Maden        | 11            |
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
üç farklı tabloya ayrıştırabilir (Tip A: Gedik/Halk Yatırım kademeli
akış tablosu, Tip B: İnfo Yatırım ağırlıklı özet, Tip C: İntegral/SOHO
doğrudan "Halka Arz Fiyatı" ifadesi, Tip D: anlatım cümlesinden
çıkarım). Raporun metne çevrilmesi önce pdfplumber ile denenir; metin
çıkmazsa (taranmış/görüntü sayfa) Tesseract OCR (Türkçe dil paketi)
devreye girer.

temel_deger_hesaplama mantığı, raporun "özet kutusu"ndan (Gelir Özeti +
Bilanço + Çarpanlar) bağımsız olarak Graham Sayısı ve Çarpan Bazlı Değer
hesaplar — aracı kurumun kendi değerlemesinden tamamen ayrı, ikinci bir
bakış açısı sunar.

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

# 3. GitHub ve Deployment

## 3.1 GitHub Repo

github.com/cbguler/trendsurf-optima — kamuya açık (public) repo. Git
geçmişi, sızan GCP servis hesabı bilgilerini temizlemek için
filter-branch ile yeniden yazılmıştır.

## 3.2 Streamlit Cloud

Uygulama URL'si, share.streamlit.io panelinden özelleştirilebilir alt
alan adı ile yayınlanır (örn. https://trendsurfoptima.streamlit.app).
Panel özelliği: Settings → General → App URL.

## 3.3 Streamlit Cloud Secrets

- ADMIN_EMAIL, ADMIN_PASS, ADMIN_NAME — admin otomatik seed

- SUPABASE_DB_URL — pooler connection string (port 6543)

- \[email\] altında: smtp_user, smtp_pass, smtp_host, smtp_port

- TCMB_KEY — TCMB EVDS API anahtarı

## 3.4 Zamanlanmış Görevler (Scheduler)

GitHub Actions'ın kendi cron zamanlayıcısı, sık aralıklarla (15 dk altı)
tetiklemelerde güvenilir çalışmadığından, harici bir zamanlayıcı
(cron-job.org) benimsenmiştir. Bu servis, ilgili GitHub Actions
workflow'unu dışarıdan tetikler (workflow_dispatch), böylece GitHub'ın
kendi cron throttling'i aşılır.

| **Workflow**                | **Görev**                           | **Sıklık**                                     |
|-----------------------------|-------------------------------------|------------------------------------------------|
| send_email.yml              | Günlük portföy raporu               | Kullanıcı ayarına göre, saatte 4 kontrol slotu |
| peak_check.yml              | Kâr realizasyonu kontrolü           | Her 15 dakika (cron-job.org tetikli)           |
| update_data.yml / worker.py | Evren verisi + Halka Arz PDF işleme | Gece TRT 02:00/03:00                           |

## 3.5 Güvenlik Notları

- Supabase Row Level Security (RLS) aktif — her kullanıcı yalnızca kendi
  verisine erişir.

- Sızan GCP servis hesabı bilgileri git geçmişinden filter-branch +
  force-push ile temizlendi.

- .gitignore: venv, cache, secrets, \*.json, live_data.zip, debug/gecici
  dosyalar (golda\_\*.py, \*\_YEDEK.json vb.)

## 3.6 Git Çakışma Çözümü

- Push reddedilirse: git fetch origin → git pull origin main (merge)
  veya gerekiyorsa git reset --hard origin/main

- Her zaman değişikliğe başlamadan önce git pull origin main ile en
  güncel hali çekin.

- Tek dosya politikası: app.py — asla app_v15/v16 gibi kopya dosyalar
  oluşturulmaz.

# 4. Kullanıcı Yönetimi

## 4.1 Kullanıcı Plan Tipleri

| **Tip** | **Açıklama**                         |
|---------|--------------------------------------|
| free    | Sınırlı erişim — temel listeleme     |
| pro     | Tüm sayfalar, e-posta raporu         |
| premium | Pro + kâr realizasyonu uyarı sistemi |
| admin   | Sistem yöneticisi, tüm yetkiler      |

## 4.2 Yeni Abone Onaylama

1.  Admin Paneli → Bekleyen Kullanıcılar bölümüne gidin.

2.  Yeni kaydın e-posta/ad bilgisini kontrol edin.

3.  "Onayla" butonuna basın — is_active = TRUE olur, kullanıcı giriş
    yapabilir.

## 4.3 Supabase Tabloları (Özet)

| **Tablo**       | **İçerik**                                                            |
|-----------------|-----------------------------------------------------------------------|
| users           | Kullanıcı kayıtları (email, password_hash, plan, is_active, is_admin) |
| sessions        | Beni Hatırla session token'ları (90 gün)                              |
| portfolio       | Pozisyonlar (her satır bir varlık)                                    |
| password_resets | Şifre sıfırlama tokenları (24 saat geçerli)                           |
| email_settings  | Günlük rapor saatleri                                                 |
| alert_settings  | Kâr realizasyonu uyarı tercihleri                                     |
| peak_tracker    | Peak (tepe fiyat) takibi — composite key (user_id, ticker)            |

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

# 5. E-posta Sistemi

## 5.1 Günlük Rapor Sistemi

- emailer.py — Streamlit'ten manuel "Şimdi Gönder"

- emailer_standalone.py — GitHub Actions cron'undan otomatik, saatte 4
  kontrol slotu

- email_send_log tablosu — atomik INSERT ON CONFLICT ile mükerrer
  gönderim koruması

## 5.2 Kâr Realizasyonu Uyarı Maili

- peak_alert_emailer.py — HTML mail formatı + SMTP gönderim

- Her kullanıcının uyarısı yalnızca kendi e-posta adresine gider

- mark_alert_sent — mail gönderildikten sonra peak_tracker'da flag set
  edilir

## 5.3 Gmail App Password Yenileme

1.  myaccount.google.com/apppasswords adresine gidin.

2.  Yeni App Password oluşturun.

3.  Streamlit Cloud Secrets → smtp_pass güncelleyin.

4.  GitHub Actions Secrets → SMTP_PASS güncelleyin (her iki yer de).

# 6. Sık Karşılaşılan Sorunlar

| **Sorun**                           | **Sebep**                                                                  | **Çözüm**                                                               |
|-------------------------------------|----------------------------------------------------------------------------|-------------------------------------------------------------------------|
| BIST hisseleri eksik geliyor        | GitHub Actions yfinance rate limit                                         | worker.py'nin gece işleyişini kontrol edin, gerekirse manuel tetikleyin |
| Altın fiyatı yanlış                 | yfinance ons/gram karışıklığı                                              | Bigpara birincil kaynak — otomatik düzelmeli                            |
| Türkçe karakter bozuk               | KAP API encoding                                                           | fix_encoding (latin-1 → UTF-8) çözümü                                   |
| E-posta gitmiyor                    | SMTP Secrets eksik/yanlış                                                  | Streamlit + GitHub Actions Secrets kontrol                              |
| Login beni unutuyor                 | Her push sonrası Streamlit Cloud redeploy tüm oturumları sıfırlar          | Beklenen davranış — push sonrası ilk girişte normal                     |
| Database connection error           | Supabase pooler 6543 yanlış                                                | SUPABASE_DB_URL kontrol                                                 |
| Halka Arz Graham/Çarpan boş         | OCR kalitesi düşük rapor                                                   | Beklenen/güvenli davranış — manuel düzeltme yapılmaz                    |
| Peak check çalışmıyor               | cron-job.org tetiklemesi kesilmiş olabilir                                 | cron-job.org panelinden job durumunu kontrol edin                       |
| Ana Sayfa tablosu mobilde dağılıyor | st.columns() ~640px altında dikey istifleniyor (Streamlit platform kısıtı) | st.dataframe (clickable_table) formatı kullanılır, mobilde dağılmaz     |

## 6.1 Manuel CSV Güncelleme

Eğer worker.py'nin yerel çıktısını manuel push etmek gerekirse:

- cd C:/Users/bahri/Desktop/TrendSurf_Optima

- python worker.py

- git add -f optimized_universe.csv

- git commit -m "veri guncelleme" && git push origin main

# 7. Versiyon Geçmişi (Özet)

**v2.0.4.x (Temmuz 2026) — Halka Arz, Tablo ve Mobil Uyum Dönemi**

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

**v2.0.1 – v2.0.3.x (Haziran 2026)**

- Kâr realizasyonu uyarı sistemi (peak tracking) tam otomasyonu, GitHub
  Actions entegrasyonu

- emailer_standalone.py mükerrer gönderim koruması (email_send_log)

- Teknik göstergeler modülü: MA20/MA50/52H/Max Drawdown/MACD

- Bulanıklaşma fix: autorefresh 60sn → 300sn, dosya temizliği

**v1.9.x ve Öncesi**

- SQLite → Supabase PostgreSQL migrasyonu

- TEFAS / KAP entegrasyonu, BIST live data (borsapy)

- v1.0 — İlk yayın: SQLite, manuel portföy girişi, Optima Skor formülü,
  5 varlık sınıfı
