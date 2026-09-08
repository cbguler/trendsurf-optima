# Beklenti Modu — Genişletilmiş Olay-Tepki Araştırması

**Amaç:** Mevcut 6 kalıbın ötesinde, gerçek/belgelenmiş tarihsel olaylara dayanan yeni kalıplar önermek. Her madde, kaynak doğrulanabilir bir olay ve ölçülmüş bir piyasa tepkisi içeriyor — tahmini/uydurma sayı yok. Puanlar (etki tablosundaki değerler) benim önerim; kesinleştirme kararı sana ait, Admin Paneli üzerinden uygulanır.

**Kritik uyarı — okumadan geçme:** Aşağıdaki hiçbir örnek "bu olay olursa fiyat şu kadar hareket eder" garantisi değildir. Bunlar TEK VAKA gözlemleridir (n=1 veya birkaç), istatistiksel olarak genellenebilir bir katsayı değildir. Her piyasa tepkisi, olayın büyüklüğüne, o anki piyasa konumlandırmasına (positioning) ve makro bağlama göre büyük ölçüde değişir. Bu kalıplar "yön ve büyüklük mertebesi" fikri vermek içindir, kesin bir formül değildir.

---

## Bölüm 1 — Mevcut "Fed" Kalıbına Eklenecek Somut Örnek

Mevcut `fed` kalıbı (MADEN azalış, DOVIZ artış, BIST azalış) zaten doğru yönde, ama `tcmb_kredibilite` gibi somut bir "belgelenmiş örnek" cümlesi eksikti. Öneri:

> **İstatistiksel dayanak:** 2013 "Taper Tantrum" — Fed Başkanı Bernanke'nin 22 Mayıs 2013'te piyasanın beklemediği bir şekilde tahvil alım programının azaltılabileceğini ima etmesi üzerine, gelişen piyasa para birimleri sonraki 4 ay içinde dolar karşısında ortalama **%6 değer kaybetti**. Türkiye bu şoka **%5,5 puanlık acil faiz artırımı** ile karşılık verdi (Brookings). Gelişen piyasa şirket tahvillerinin ABD tahviline göre risk primi (spread) **60 baz puan** yükseldi (Dallas Fed).

**Kaynak:** Brookings ("Emerging Markets Taper Tantrum"), Federal Reserve Bank of Dallas (2021 analizi).

---

## Bölüm 2 — Önerilen Yeni Kalıplar

### 2.1 — Fed/ECB Güvercin Sürprizi (Beklenmedik Faiz İndirimi)

Mevcut `fed` kalıbının **TAM TERSİ** yönü — piyasanın beklediğinden daha büyük/ani bir indirim.

- **Mekanizma:** Sürpriz indirim, reel getirileri düşürür (altın için elde tutma maliyeti azalır) ve doları zayıflatır. Hisse senedi tepkisi ise **indirim nedenine bağlı** — resesyon korkusuyla yapılan bir indirimse kısa vadede hisse senetleri de düşebilir; "önleyici" bir indirimse hisseler genelde yükselir.
- **Belgelenmiş örnek:** Fed'in 18 Eylül 2024'te piyasa beklentisinin üzerinde **50 baz puanlık** "jumbo" bir indirimle başladığı döngüde, tarihsel örüntüye göre (Trefis analizi) böyle bir sürpriz büyüklükteki indirim S&P 500'de orta vadede **%30'a varan** bir ralliyle ilişkilendirilmiş. 2007-2011 döngüsünde ise (GFC kaynaklı indirimler) altın 2011'e kadar **ons başına $1.900**'ün üzerine çıkmıştı.
- **Önerilen kelimeler (TR):** faiz indirimi sürprizi, güvercin sürpriz, beklenmedik faiz indirimi
- **Önerilen kelimeler (EN):** surprise rate cut, dovish surprise, jumbo rate cut, unscheduled cut
- **Önerilen etki puanı:** MADEN +6, DOVIZ −5 (TL güçlenir yönünde, yani USD/TRY azalış), BIST +3
- **Not:** Hisse etkisi belirsizliğinden dolayı BIST puanını düşük/temkinli önerdim — istersen 0'a da çekebiliriz.

---

### 2.2 — Küresel Likidite Krizi / Panik Satışı (COVID-Mart-2020 Tipi)

**En önemli ve en çok karşı-sezgisel (counter-intuitive) kalıp bu olabilir.**

- **Mekanizma:** Akut bir likidite/panik krizinde, yatırımcılar nakde geçmek için ELLERİNDEKİ HER ŞEYİ satar — **altın dahil.** "Güvenli liman" varsayımı KISA VADEDE çöker, sonra geri döner.
- **Belgelenmiş örnek:** Mart 2020'de, altın önce **$1.700'den $1.450'ye (~%15 düşüş)** geriledi — güvenli liman olarak değil, nakit ihtiyacı yüzünden satıldı (Metalorix/World Gold Council verisi). Aynı dönemde ham petrol tek günde (9 Mart 2020) **%20'den fazla** çöktü, DJIA kümülatif **%26** geriledi (S&P1500 çalışması). Altın ay SONRASINDA toparlanıp yıl genelinde **%25** yükseldi.
- **Önerilen kelimeler (TR):** küresel panik satışı, likidite krizi, piyasa çöküşü, borsa krizi
- **Önerilen kelimeler (EN):** liquidity crisis, panic selling, market crash, flight to cash
- **Önerilen etki puanı:** MADEN **−4** (kısa vadeli, karşı-sezgisel düşüş — DİKKAT: normal mantığın tersi), DOVIZ +8 (dolar güçlenir, TL zayıflar), BIST −10, KRIPTO −8
- **ÖNEMLİ TASARIM NOTU:** Bu kalıbın MADEN için NEGATİF puanı, diğer tüm kalıplardan farklı bir mekanizmayı yansıtıyor (nakit ihtiyacı, güvenli liman değil). AI doğrulamasının bunu doğru sınıflandırması için açıklamada bu ayrım net yazılmalı.

---

### 2.3 — Petrol Arz Fazlası / Fiyat Savaşı (Mevcut "Petrol Arz Şoku"nun TERSİ)

- **Mekanizma:** Üretici ülkeler arasında anlaşmazlık/aşırı üretim → petrol arzı patlar → fiyat çöker. Enerji ihracatçısı olmayan Türkiye gibi ülkeler için genelde OLUMLU (ithalat maliyeti düşer, cari açık iyileşir).
- **Belgelenmiş örnek:** 8 Mart 2020, Suudi Arabistan-Rusya fiyat savaşı başlangıcında ham petrol TEK GÜNDE **%25-30** çöktü (1991'den beri en büyük tek günlük düşüş, Wikipedia/GulfNews). Daha yavaş, yapısal örnek: 2014-2016 arz fazlası döneminde petrol **18 ayda %70-75** geriledi (Dünya Bankası, CER Kanada).
- **Önerilen kelimeler (TR):** petrol fiyat savaşı, arz fazlası, üretim artışı OPEC, petrol çöküşü
- **Önerilen kelimeler (EN):** oil price war, oil glut, oversupply, production surge
- **Önerilen etki puanı:** MADEN −2 (hafif, enerji-emtia korelasyonu üzerinden), DOVIZ −4 (TL güçlenir — enerji ithalatçısı avantajı), BIST +4

---

### 2.4 — Bankacılık Krizi / Büyük Banka İflası

- **Mekanizma:** Bir bankanın (özellikle sistemik önemi olan) aniden çökmesi, "bulaşma" (contagion) korkusu yaratır → tahvil getirileri sert düşer (Fed'in gevşeyeceği beklentisiyle) → altın yükselir → bankacılık hisseleri çöker.
- **Belgelenmiş örnek:** Silicon Valley Bank'ın 10 Mart 2023 çöküşünde, altın 3 gün içinde **$1.818'den $1.918'e (~%5,5)** yükseldi. 2 yıllık ABD tahvil getirisi **1987'den beri en büyük 3 günlük düşüşünü** yaşadı (80 baz puan). Dolar endeksi zayıfladı, EUR/USD ayda en yüksek seviyesine çıktı. SVB hissesi **%60'ın üzerinde** çöktü, ABD bankaları toplamda **$100 milyardan fazla** piyasa değeri kaybetti (Reuters).
- **Kripto tepkisi TUTARSIZ:** Bir akademik çalışma (ScienceDirect) Bitcoin için ANLAMLI NEGATİF etki bulurken, güncel piyasa haberleri Bitcoin'in aynı hafta sonu **%8 yükseldiğini** gösteriyor (Fed'in gevşek duruşu bahis konusu olunca). **Bu yüzden KRIPTO için puan ÖNERMİYORUM — yön belirsiz.**
- **Önerilen kelimeler (TR):** banka iflası, banka çöküşü, bankacılık krizi, mevduat krizi
- **Önerilen kelimeler (EN):** bank collapse, bank failure, banking crisis, bank run
- **Önerilen etki puanı:** MADEN +6, DOVIZ −4 (TL güçlenir — küresel risk-off'ta ilginç şekilde büyük bankacılık krizlerinde dolar bazen zayıflar, çünkü kriz ABD kaynaklı oluyor), BIST −3, KRIPTO **boş bırakılmalı**

---

## Bölüm 3 — Özet Karar Tablosu

| # | Kalıp | MADEN | DOVIZ | BIST | KRIPTO | Güven düzeyi |
|---|---|---|---|---|---|---|
| 1 | Fed güvercin sürprizi (indirim) | +6 | −5 | +3 | — | Orta |
| 2 | Küresel likidite krizi/panik | **−4** | +8 | −10 | −8 | Orta (yön karşı-sezgisel, dikkatli izlenmeli) |
| 3 | Petrol arz fazlası/fiyat savaşı | −2 | −4 | +4 | — | Orta-Yüksek |
| 4 | Bankacılık krizi/banka iflası | +6 | −4 | −3 | boş | Yüksek (MADEN/DOVIZ), belirsiz (KRIPTO) |

Bunların hiçbiri kesinleşmedi — senin onayını/düzenlemeni bekliyor.

---

## Bölüm 4 — Akademik Kaynakça

**Bahri'nin haklı uyarısı üzerine eklendi:** Önceki turdaki araştırma güncel haber kaynaklarından (Bloomberg, Reuters, World Gold Council vb.) derlenmişti — akademik literatür değildi. Bu bölüm, olay-tepki (event study) yaklaşımının dayandığı gerçek, doğrulanmış akademik kaynakları listeliyor. Hiçbiri uydurulmadı — her biri arama motorlarında (Google Scholar, SSRN, AEA, ScienceDirect) doğrudan bulunabilir.

### Temel Metodoloji
- **MacKinlay, A.C. (1997).** "Event Studies in Economics and Finance." *Journal of Economic Literature*, 35(1), 13-39. — Olay çalışması (event study) yönteminin kurucu/kanonik referansı. Bizim "kalıp" sistemimizin temel mantığı (bir olayın etrafındaki fiyat tepkisini ölçmek) doğrudan bu metodolojiye dayanıyor.

### Jeopolitik Risk
- **Caldara, D., & Iacoviello, M. (2022).** "Measuring Geopolitical Risk." *American Economic Review*, 112(4), 1194-1225. — Jeopolitik Risk Endeksi'nin (GPR) kurucu makalesi. Metodoloji: önde gelen gazetelerdeki jeopolitik gerilim kelimelerinin sayımına dayanıyor — bizim anahtar-kelime tabanlı ön-filtre yaklaşımımızla doğrudan aynı ailede bir yöntem.
- **Akçayır, Ö. (2023).** "Ulusal Riskler, Jeopolitik Riskler ve Küresel Belirsizliklerin Türk Lirasının Değeri Üzerindeki Etkileri." *Alanya Akademik Bakış*, 7(2), 649-669. — **Türkiye'ye özel bulgu:** TL değeri üzerinde CDS primi baskın faktör; jeopolitik risk göreceli olarak EN ZAYIF etkili değişken çıkmış. Bu, "jeopolitik" kalıbının DOVIZ etkisini abartmamak için önemli bir denge notu.
- **(Yazarı dergipark makalesinde belirtilmemiş).** "Türkiye'nin Jeopolitik Riskinin Borsa İstanbul Endeks Getirileri Üzerine Etkisinin İncelenmesi" — **Somut, sayısal bulgu:** jeopolitik risk endeksindeki 1 birimlik artış, BIST100 getirilerini yaklaşık **%4** azaltıyor (2009-2018 dönemi, ARDL sınır testi).

### Petrol Şokları
- **Kilian, L. (2009).** "Not All Oil Price Shocks Are Alike: Disentangling Demand and Supply Shocks in the Crude Oil Market." *American Economic Review*, 99(3), 1053-1069. — Petrol şoklarının arz kaynaklı mı yoksa talep kaynaklı mı olduğuna göre TAMAMEN FARKLI etkiler yarattığını gösteren temel çalışma. Bizim "petrol arz şoku" ile önerdiğim "petrol arz fazlası" kalıplarının ayrı tutulmasının akademik gerekçesi burada.

### Merkez Bankası Sürprizleri
- **Kuttner, K.N. (2001).** "Monetary Policy Surprises and Interest Rates: Evidence from the Fed Funds Futures Market." *Journal of Monetary Economics*, 47(3), 523-544.
- **Gürkaynak, R.S., Sack, B., & Swanson, E.T. (2005).** "Do Actions Speak Louder Than Words? The Response of Asset Prices to Monetary Policy Actions and Statements." *International Journal of Central Banking*, 1(1), 55-93. — Yüksek frekanslı olay çalışması yöntemiyle, Fed kararlarının SÜRPRİZ bileşeninin (piyasa beklentisinden sapmanın) varlık fiyatlarına etkisini ölçen temel çalışmalar. "Sürpriz" kavramının ölçülebilir bir şey olduğu fikrinin akademik kökeni.

### Kredi Notu Değişiklikleri
- **Kaminsky, G., & Schmukler, S.L. (2002).** "Emerging Market Instability: Do Sovereign Ratings Affect Country Risk and Stock Returns?" *World Bank Economic Review*, 16(2), 171-195. — **Somut bulgu:** bir kademelik not indirimi, gelişen piyasa tahvil risk primini ortalama **2 puan** artırıyor; etki hem tahvillere hem hisse senetlerine yayılıyor, krizli dönemlerde daha güçlü.

---



## Bölüm 5 — Bilerek Araştırmadığım/Eklemediğim Konular

Şeffaflık için: aşağıdaki konuları da düşündüm ama bu turda derinlemesine araştırmadım, istersen bir sonraki turda ekleyebilirim:
- Egemen borç krizi (Yunanistan 2010-2012, Arjantin) — TL için dolaylı etki, doğrudan ilişki zayıf olabilir
- Ticaret savaşı/gümrük tarifesi şokları (2018-19 ABD-Çin) — BIST için dolaylı, ölçmesi zor
- İsviçre Frangı sabitlemesinin kaldırılması (2015) gibi kur-sabitleme şokları — Türkiye'ye doğrudan uygulanabilirliği düşük
- Kripto özelinde pozitif katalizörler (ör. Bitcoin ETF onayı) — mevcut `kripto_olay` kalıbı zaten negatif yönlü, ayrı bir "pozitif kripto katalizörü" kalıbı ayrı bir tartışma konusu olabilir

---

*Bu belge 21 Ağustos 2026'da, web araştırmasıyla derlenmiştir. Puan önerileri Claude'un yorumudur, garanti edilmiş bir tahmin değildir — TrendSurf Optima yatırım tavsiyesi vermez.*
