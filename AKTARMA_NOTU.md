# TrendSurf Optima — Aktarma Notu (25 Temmuz 2026)

Bu not, önceki (numaralandırılmış oturumlar şeklinde ilerleyen) sohbetten yeni
"TrendSurf Optima" sohbetine geçiş içindir. Proje artık Bahri'nin istediği
olgunluk seviyesine ulaştı; bundan sonra bu yeni sohbet sadece arıza
müdahalesi ve istisnai/büyük konular için kullanılacak.

## Asıl kaynak: PROJE_NOTLARI.md

Projenin gerçek, kalıcı hafızası bu sohbet değil, **repodaki
PROJE_NOTLARI.md** dosyasıdır — git ile versiyonlanır, sohbet geçmişinden
bağımsızdır, her oturumda güncellenir. Yeni sohbette ilk iş: bu dosyayı
(ve varsa güncel diğer dosyaları) yükleyip oradan devam etmek. Aşağıdaki
özet sadece hızlı bir yönelim sağlamak için, PROJE_NOTLARI.md'nin yerini
tutmaz.

## Güncel durum (25 Temmuz 2026 itibarıyla)

Sürüm: **v2.0.7.102**. Sistem — BIST/TEFAS/Döviz/Değerli Madenler/Kriptolar
(2.379 varlık), Bütçe Optimizasyonu, Portföyüm/muhasebe, Fırsat Radarı,
Admin/Abone El Kitapları — büyük ölçüde stabil ve doğrulanmış durumda.

## Kalıcı kurallar (her zaman geçerli, tekrar sorulmasın)

- Tek app.py, emoji/dekoratif sembol YASAK (kod/UI/chat, checkmark dahil)
- Türkçe UI, her düzeltme PROJE_NOTLARI.md'ye kaydedilir
- Her oturum başında GitHub'dan taze klon; dış API çağrılarına HER ZAMAN
  zaman aşımı koruması eklenir (bugüne kadar iki kez unutulup bulundu)
- git push öncesi git pull --no-rebase (3 workflow'da zaten var)
- Bahri sık sık dosyaları yanlış klasöre indirip git'e eklemeyi unutuyor —
  her push sonrası GitHub'dan taze klonla doğrulamak alışkanlık haline geldi

## Şu an açık/doğrulama bekleyen maddeler (öncelik sırasıyla)

1. **v2.0.7.100 (KRİTİK GÜVENLİK)** — Supabase'in "RLS etkin değil" uyarısına
   karşı 7 tabloya RLS eklendi. Bahri'nin uyarının tekrar gelip gelmediğini
   doğrulaması gerekiyor.
2. **v2.0.7.101/102 (Streamlit Cloud uyku sorunu)** — Playwright tabanlı
   uyandırma botu eklendi, resmi/garantili değil. Ayrıca art arda gelen
   GitHub Actions "Cancelled"/"Internal server error" e-postaları — GitHub
   altyapı kaynaklı görünüyor ama kesin değil, gözlem sürüyor.
3. **v2.0.7.91 (zaman aşımı koruması)** — muhtemelen sorunsuz ama resmi
   "doğrulandı" onayı gelmedi.
4. **El kitapları güncellemesi (18 Temmuz)** — GitHub'dan doğrulandı,
   gerçekten push edilmiş (63 TRY/188 kripto ifadeleri dosyalarda mevcut).
   PROJE_NOTLARI.md'deki "PUSH BEKLİYOR" etiketi eskimiş, düzeltilmeli.

## Kasıtlı olarak ertelenmiş/kapatılmış konular (kendisi açmadıkça açma)

- **TEFAS'ın Liste/Detay skor tutarsızlığı** — pytefas'ın dakikada 6 istek
  limiti yüzünden çözülemiyor, Bahri yorulup ertelemişti
- **9 Truncgil-türü maden varlığı** (Gram Has, Ayar14/18, vb.) — kesin karar
  verildi: olduğu gibi kalacaklar, RSI/Skor boş görünmeye devam edecek
- **PEPE gibi aşırı düşük fiyatlı kripto varlıkların** Bütçe
  Optimizasyonu'nda milyonlarca birim göstermesi — kozmetik, henüz bir
  tercih belirtilmedi

## Bahri hakkında (ilgili olduğunda)

Sistemi kendi yatırımlarını takip etmek için kullanıyor, gerçek parayla.
Fiziksel olarak T7 seviyesinde tam paraplejik (AIS A) — bazen uzun/yorucu
oturumlarda sabrı zorlanabiliyor, bu anlaşılır bir durum. Windows'tan,
C:\Users\bahri\Desktop\TrendSurf_Optima\ klasöründen çalışıyor.
