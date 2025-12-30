# Donanım Planı (Yeni Panel) — Başlangıçtan Kurulum Rehberi

Bu doküman; sera sisteminin donanımını (sensörler, röle/driver, güç kaynakları, kablolama ve kutulama) planlamak için hazırlanmıştır.
Amaç: **güvenli**, **karışıklık çıkarmayan**, **sonradan büyütmesi kolay** bir kurulum.

> Güvenlik notu: 230V AC (şehir elektriği) tehlikelidir. Yetkin değilsen AC tarafını bir elektrikçiye yaptır. Bu doküman “ne yapılmalı”yı anlatır; uygulama sorumluluğu kullanıcıdadır.

---

## 1) Sistem Şeması (Zihin Haritası)

Bizim model:
- **SERA (genel)**: tüm seranın iklimi + genel ısıtıcı + egzoz fan
- **KAT1**: 2 sıra LED + 1 kat fanı + kapasitif toprak nem sensörleri + SHT31 + BH1750 + kamera
- **KAT2**: 2 sıra LED + 1 kat fanı + kapasitif toprak nem sensörleri + SHT31 + BH1750 + kamera
- **FIDE (kapalı kutu)**: ayrı ısıtıcı + (kutu içi) fan + SHT31 + BH1750 + kamera

Ana prensip:
- **Kontrol kutusu** tek yerde olur (Pi + sürücüler + güç + sigortalar).
- Katlara **güç** gider (12V) ve kat üzerindeki yükler oradan beslenir.
- Her katta bir **ESP32 düğümü** olur; sensörler düğüme **kısa kablo** ile bağlanır (uzun analog/I2C taşıma yok).
- Kamera görüntüleri ESP32’den Raspberry Pi’ye gider; görüntü işlemeyi Pi yapar.

---

## 2) Ekipman Listesi (BOM) — Minimum + Önerilen

### 2.1 Zorunlu
- Raspberry Pi 4 + microSD
- 5V/3A Pi adaptörü (resmi önerilir)
- 12V DC güç kaynağı (fanlar + LED’ler için)
  - Güç hesabı: Toplam Watt / 12V = toplam akım (A). Üzerine %30 pay koy.
- Her kat için 1 adet ESP32 düğümü (tercihen **ESP32‑CAM**):
  - Her düğüm: SHT31 (temp/nem) + BH1750 (lux) + kamera
  - Kat düğümleri ayrıca kapasitif toprak nem sensörlerini okur (ADC/harici ADC ile)
- Her ESP32 düğümü için 12V→5V **buck converter** (stabil 5V)
- **Kanal sürücüler**
  - LED ve 12V fanlar için: **MOSFET driver (önerilir)** veya röle
  - Eğer mutlaka röle: 16 kanal röle kartı (aşağıda kriterleri var)
- KAT1/KAT2 canopy fanlar için **2 kanal röle kartı** (on/off)
- 20×4 **I2C LCD** (panel dışı hızlı durum göstergesi)
- Kapasitif toprak nem sensörleri (kat başına ihtiyaca göre; yedek ile)
- (Opsiyon) Kat başına I2C ADC (ör. ADS1115): ESP32‑CAM pin/ADC kısıtı varsa analog sensör sayısını büyütmek için
- Klemens/terminal blok (WAGO veya vidalı klemens)
- Sigorta(lar) + sigorta yuvası (DC tarafı için)
- Kablo kanalı/spiral/kılıf + etiketleme bandı
- Proje kutusu (mümkünse IP65), kablo rakoru (cable gland)

### 2.2 Çok önerilen (daha profesyonel/az sorun)
- DIN ray + DIN klemens + DIN sigorta bloğu (kutu içi düzen)
- DC dağıtım için “fuse box” (her çıkış ayrı sigorta)
- RJ45/konnektörlü “kat bağlantı paneli” (katlara giden kabloları sökülebilir yapmak için)
- Isı büzüşmeli makaron + kablo pabuçları + kablo ferrule seti
- TVS diyot/flyback diyot (özellikle fan gibi endüktif yüklerde; MOSFET kullanıyorsan şart)

---

## 3) Kaç Röle (veya kaç çıkış) Gerekli?

Planlanan yükler:
- KAT1: `KAT1_LIGHT` (PWM dim) + `KAT1_FAN` (röle on/off) → **2 çıkış**
- KAT2: `KAT2_LIGHT` (PWM dim) + `KAT2_FAN` (röle on/off) → **2 çıkış**
- FIDE: `FIDE_HEATER`, `FIDE_FAN` → **2 çıkış**
- SERA: `EXHAUST_FAN` → **1 çıkış** (`SERA_HEATER`: Home Assistant akıllı priz önerilir)
- Sulama: `PUMP` + `VALVE_KAT1` + `VALVE_KAT2` → **3 çıkış** (3. hat/valf istersen +1)

Toplam: **10 kontrol çıkışı** (3. valf eklenirse **11**).

Öneri:
- Bugün 10 çıkış lazım ama yarın pompa/valf vb. eklenebilir.
- Bu yüzden **16 çıkış** planlamak “bir daha sök-tak yapmamak” için daha mantıklı.

> Not: Sera ısıtıcıyı Home Assistant akıllı priz ile kontrol edeceksen AC rölesi şart olmayabilir. Bu durumda çıkış ihtiyacı düşer ama yine de “yedek” için 16 mantıklı.

---

## 3.1) Sulama (Tek Pompa, Çok Kat) — “Nereye Ne Kadar?”

Tek bir pompayla KAT1 ve KAT2’yi sulamak istiyorsan iki problem var:
1) **Su nereye gidecek?** (yönlendirme)
2) **Ne kadar gitti?** (miktar)

### 3.1.1 Yönlendirme: Valf şart
Pompayı çalıştırınca su, en az dirençli yola akar. Bu yüzden:
- Katlara giden hatları **ayrı ayrı açıp kapatmak** için en az **2 adet NC (normalde kapalı) solenoid valf** gerekir.
- Sulama anında sadece sulanacak katın valfi açılır, pompa çalışır, sonra kapanır.

> Valf yoksa “tek pompa ile iki kata kontrollü sulama” pratikte olmaz; su rastgele bölüşür.

Seçilen parça notu:
- Sepetteki ürün: **1/4" 12V DC solenoid valf** (NC olduğundan ve bobinin gerçekten 12V DC olduğundan emin ol).
- Adet: 3 (pratikte 2 hat + 1 yedek / ileride 3. hat).

### 3.1.2 Miktar: Debi sensörü ile hacim ölçümü
Debi sensörü “puls” üretir; toplam pulse sayısı → yaklaşık hacim.

Seçilen parça notu:
- Sepetteki ürün: **1/4" liquid flow sensor** (hall/pulse tipinde olduğunu ve çıkış seviyesini doğrula; Pi GPIO 3.3V ister).
- Adet: 3 (hat başına ölçüm + 1 yedek / ileride 3. hat).

Pratik yerleşim:
- **Tek debi sensörü** alırsan: pompa çıkışı + manifold öncesi.
  - Kural: aynı anda sadece **1 valf** açık olacak (böylece ölçülen hacim o kata aittir).
- Daha hassas ama daha maliyetli: her kat hattına **1 debi sensörü** (valften sonra).

### 3.1.3 Kalibrasyon (gerçek dünyada şart)
Her katın hortum uzunluğu/irtifası farklı olacağı için debi değişir.
Bu yüzden her kat için “ml/pulse” veya “ml/saniye” kalibrasyonu yapılır:
- Valf aç → pompayı çalıştır → belirli pulse sayısında bir kaba su doldur → ml ölç → katsayıyı kaydet.

### 3.1.4 Hidrolik küçük ama kritik parçalar
- **Check valve (tek yön)**: geri akış/sifon riskini azaltır.
- **Inline filtre**: damlama uçları tıkanmasın.
- **Damlama ucu / restrictor**: saksılar arasında daha dengeli dağıtım.

### 3.1.5 Güvenlik davranışı (kontrol mantığı)
- Pompa çalışıyor ama debi sensörü pulse üretmiyorsa → **hemen durdur + uyarı** (depo boş, hortum çıktı, tıkandı).
- Pompa için süre limitleri (max saniye, günlük max) korunur.

---

## 4) Röle mi MOSFET mi? (Hızlı Karar)

### LED şeritler ve 12V fanlar için (DC yük)
- **MOSFET driver (önerilir)**:
  - Sessiz, hızlı, sık aç-kapa’da yıpranmaz
  - PWM/step kontrol için daha uygun (ileride dimming)
- Röle:
  - Basit ON/OFF için olur ama sık anahtarlamada mekanik ömür kısalır

Kontrol mimarisi notu (ESP32 düğümleri ile):
- En temiz yaklaşım: **kat başına MOSFET** (kat düğümünün yanında) → kısa kablo, daha az parazit.
- Tek bir 8’li MOSFET kartını birden fazla ESP32 ile sürmek teknik olarak mümkün; ama uzun kontrol kabloları, ortak GND, boot anı pin durumları ve arıza izolasyonu açısından daha riskli/karmaşık.

### Isıtıcı gibi yüksek güç AC yükler için
- En güvenlisi: **Home Assistant akıllı priz** (sertifikalı) veya **kontaktör/SSR** (uygun kutulama + sigorta + topraklama ile)
- 10A “hobi röle kartı” ile 1–2kW ısıtıcı sürmek **riskli** (ark, ısınma, klemens kalitesi).

Bu dokümanda röle kriterlerini de veriyorum; ama tasarım önerisi:
- **DC yükler: MOSFET**,
- **AC ısıtıcı: akıllı priz veya kontaktör**.

---

## 5) Röle Seçimi Kriterleri (Eğer Röle Kullanacaksak)

Minimum kriterler:
- Kanal sayısı: **16 kanal** (8 yük + yedek)
- Röle bobin voltajı: **5V** (yaygın)
- Giriş seviyeleri: Raspberry Pi **3.3V** GPIO ile tetiklenebilir olmalı
  - “3.3V compatible input” veya arada sürücü (ULN2803/transistör) gerekir
- İzolasyon: **opto-izoleli** olması tercih edilir
- Klemens kalitesi: vidalı klemens sağlam olmalı (ısınma için kritik)
- Röle kontak değerleri (etikette):
  - 250VAC 10A yazsa bile bu “teorik”; AC ısıtıcı için yine önerilmez
  - DC yüklerde 10A @ 30VDC gibi değer aranır

Elektriksel not:
- 16 röle aynı anda çekerse 5V tarafı 1A+ akım çekebilir. **Pi’nin 5V pininden röle besleme!**
- Röle kartının 5V’u ayrı bir 5V adaptörden gelsin (ortak GND şart).

---

## 6) Sensör Planı (Sabit ve Anlaşılır)

### 6.1 Temp/Nem
- Her kat için 1 adet **SHT31 (I2C)** ve bunu katın **ESP32 düğümüne** bağla.
  - Minimum: **KAT1**, **KAT2**, **FIDE**.
  - (Opsiyonel) SERA “genel” ölçüm istiyorsan ayrıca bir SHT31 daha ekleyebilirsin.

Neden SHT31?
- Daha stabil ve uzun vadede daha iyi (DHT’ler genelde daha “oynak”).

### 6.2 Lux
- Her kat için 1 adet **BH1750 (I2C)** ve bunu katın **ESP32 düğümüne** bağla.
- Aynı hatta birden fazla BH1750 gerekiyorsa adres konusu var (BH1750 genelde 2 adres). Kat başına ayrı ESP32 düğümü kullandığın için bu çakışma büyük ölçüde çözülür.
- (Opsiyonel) LDR sadece “yedek/deneysel” olarak düşün; kalibrasyon ve drift yönetimi ister.

### 6.3 Toprak Nemi (kapasitif)
- Sadece KAT1 ve KAT2 (FIDE yok), **kat başına 1 sensör**.
- Sensörleri katın **ESP32 düğümüne** bağla (ADC).
- ESP32‑CAM gibi kartlarda ADC pin sayısı yetmiyorsa, kat düğümüne bir **I2C ADC (ADS1115)** ekleyip sensörleri oraya al.

### 6.4 Kamera (ESP32‑CAM)
- Her katta bir kamera snapshot/stream kaynağı olsun.
- Kamera görüntüsünü Wi‑Fi üzerinden Raspberry Pi’ye gönder/pull ettir; **görüntü işlemeyi Pi yapar**.
- Pratik not: lensin buğulanması/yoğuşma için basit bir koruma (kapak + hava sirkülasyonu) planla.

---

## 7) Kablolama Mimarisi (Kutu İçi / Kutu Dışı)

### 7.1 Kutu İçi (Kontrol Kutusu)
Kutu içinde hedef: “her şey düz, etiketli, sökülebilir”.

Önerilen yerleşim sırası (soldan sağa):
1) AC giriş (varsa) + sigorta/RCD (AC işini elektrikçi yapsın)
2) 12V PSU
3) DC sigorta bloğu (katlara giden her hat ayrı sigorta)
4) Raspberry Pi (panel) + ağ ekipmanı (Wi‑Fi erişimi / opsiyonel küçük switch)
5) MOSFET/relay sürücü kartları (merkezde veya kat düğümlerinin yanında)
6) Terminal bloklar (katlara giden kablolar için “çıkış paneli”)

Altın kurallar:
- **AC ve DC bölmeleri ayrı** (aynı kutu içindeyse bile fiziksel ayrım).
- Kablolar “güç” ve “sinyal” olarak iki demette ilerler.
- Her kablonun iki ucunda etiket: `KAT1_LIGHT`, `KAT2_SOIL`, vb.

### 7.2 Kutu Dışı (Katlara Kablo Gidişi)
Öneri: Sera iskeletinde bir “servis omurgası” seç (arka köşe gibi).
- Kontrol kutusundan çıkan tüm kablolar bu omurgadan yukarı iner/çıkar.
- Her kata gelince küçük bir dağıtım noktası (mini kutu veya klemens) oluştur.

Güç kabloları:
- 12V yüksek akım (LED’ler): daha kalın kesit (aşağıdaki tabloda)
- 12V fanlar: orta kesit

Sensör kabloları:
- Sensörleri mümkün olduğunca katın **ESP32 düğümüne yakın** tut (kısa kablo).
- Analog sensörler (soil): **signal + GND birlikte**, tercihen bükülü çift (twisted pair).
- Güç kablolarından en az 10–15 cm ayrı taşımaya çalış.

---

### 7.3 Kablo Uzayınca “Sensör Verisi Saçmalaması” (Neden + Pratik Çözüm)

Bu çok normal: kablo uzadıkça gürültü artar, voltaj düşümü olur ve bazı protokoller uzun mesafede bozulur.
Özellikle **PWM ile sürülen LED** ve **fan/pompa** gibi yükler devredeyken sensör kabloları “anten” gibi davranabilir.

#### 7.3.1 En sık sebepler
- **Voltaj düşümü:** İnce/uzun kabloda sensörün beslemesi düşer → okuma kayar.
- **Ortak GND’de gerilim sıçraması (ground bounce):** LED/fan akımı aynı GND’den dönüyorsa sensör referansı oynar.
- **EMI (elektromanyetik gürültü):** PWM, motor, röle anahtarlaması sensör hattına gürültü bindirir.
- **Protokol limiti:** I2C gibi bazı hatlar “kısa mesafe” içindir.

#### 7.3.2 Analog sensörler (soil + LDR) için altın kural
- Analog hattı mümkünse **kısa tut** (pratikte hedef: **≤ 50 cm**).
- Uzun mesafe gerekiyorsa “analog taşımak” yerine **ADC’yi sensöre yaklaştır** (kat düğümü/ESP32 gibi).
- Analog kabloyu **signal+GND bükülü çift** yap (CAT5e/CAT6 kablo çok iş görür).
- Kabloyu **LED/fan güç kablolarından ayrı** götür; mecbursa 90° kesiştir.
- ADC girişinde basit filtre işe yarar: girişe **seri 100–470Ω** + ADC pininde **100nF GND’ye** (RC low-pass).

#### 7.3.3 I2C (BH1750, SHT31, ADS1115) için
- I2C genelde **kısa mesafe** (kartlar arası) içindir; mümkünse **≤ 50 cm** hedefle.
- Uzatacaksan:
  - I2C hızını **100 kHz** (veya daha düşük) tut.
  - Pull‑up dirençlerini (SDA/SCL) kablo uzunluğuna göre ayarla (tipik 4.7k → bazen 2.2k gerekebilir).
  - Daha profesyonel çözüm: **I2C extender/differential** (PCA9615 gibi) veya kat başına düğüm.

#### 7.3.4 DS18B20 (1‑Wire) için
- 1‑Wire kabloya daha toleranslıdır ama “yıldız topoloji” sorun çıkarır.
- Tek hat (bus) gibi dolaştır; mümkünse 3‑wire (VCC+DATA+GND) kullan.
- DATA için **4.7k pull‑up** (bazı durumlarda 2.2k) gerekebilir.

#### 7.3.5 DHT11/DHT22 için
- DHT’ler uzun kabloda daha çok hata verir (checksum / “not found”).
- Kısa kablo, doğru pull‑up ve stabil besleme şarttır; uzak ölçüm için SHT31 + düğüm yaklaşımı genelde daha iyi.

#### 7.3.6 Seçilen mimari: Kat başına ESP32 düğümü (+ kamera)
- Kat başına bir **ESP32‑CAM düğümü** koy:
  - SHT31 + BH1750 + toprak nem sensörleri düğüme **çok kısa kablo** ile bağlanır.
  - Kamera snapshot/stream kaynağı da düğümde olur.
  - Düğüm veriyi ve görüntüyü Pi’ye **Wi‑Fi (HTTP/MQTT)** ile yollar.
- Katlara sadece **12V güç** götür (kalın kablo), düğümde **12V→5V buck** ile besle.

---

## 8) Kablo Seçimi ve Kesit (Pratik Rehber)

Kesin değer için yüklerin Watt’ını bilmek gerekir; burada pratik kural veriyorum:

- 12V LED hattı (kat başına): genelde 2–8A arası olabilir (şerit uzunluğuna bağlı)
  - Kısa mesafe: 1.0–1.5 mm²
  - Uzun mesafe: 1.5–2.5 mm²
- 12V fan hattı: genelde 0.1–0.5A
  - 0.5 mm² yeterli olur
- Sensör kabloları: 0.22–0.5 mm² (ince, bükülü)

Pratik formül:
- Akım (A) = Güç (W) / 12V

Örnek:
- 24W LED → 24/12 = 2A (kat başına bu artabilir)

Bu projedeki LED bar için (senin verdiğin değerlere göre):
- 1 adet 1m LED bar: **12V, 1,4–2A** → yaklaşık **17–24W**
- 4 adet bar tamamı açık (worst-case): **5,6–8A** (yalnızca LED’ler)
  - 12V 8,5A adaptör, LED’ler full açıkken fan/PTC eklenirse sınırda kalabilir; PSU’yu headroom ile seçmek daha güvenli.

---

## 9) (Opsiyonel) LDR Devresi (Basit Anlatım)

LDR tek başına ölçülmez; bir “gerilim bölücü” kurarız:
- 3.3V → LDR → (ölçüm noktası) → Direnç → GND
- Ölçüm noktası katın ESP32 düğümünün ADC’sine (veya düğümdeki ADS1115 gibi bir ADC’ye) gider.

Başlangıç direnç değeri:
- **10kΩ** iyi bir başlangıçtır (sonra kalibrasyonla düzelir).

Kural:
- LDR ışıkta direnci düşer/yükselir; kurduğun düzene göre voltaj artar veya azalır.
- Panel kalibrasyonu ile “hangi voltaj kaç lux”u normalize edeceğiz; bu yüzden en önemli şey **stabil bağlantı**.

---

## 10) Breadboard Nedir? (Sıfırdan Anlatım)

Breadboard, lehim yapmadan devre kurabileceğin plastik bir prototipleme tahtasıdır.
Üstünde delikler vardır; bazı delikler içeriden birbirine bağlıdır.

### 10.1 Breadboard bağlantı mantığı
- Ortada uzun bir yarık vardır (IC’ler buraya oturur).
- Yarığın iki yanında, delikler genellikle **5’li gruplar** halinde birbirine bağlıdır.
- Kenarlarda uzun “+ / -” güç hatları (rail) olur.

Basit şema (genel fikir):
```
 +++++  (3.3V rail)   ----------------
 -----  (GND rail)    ----------------

 [a b c d e] | [f g h i j]   <-- aynı satır 5'li bağlı
 [a b c d e] | [f g h i j]
     (orta yarık)
```

### 10.2 Breadboard’da “karışıklık çıkmaması” için kurallar
- Tek renk kuralı:
  - 3.3V = kırmızı
  - GND = siyah
  - I2C SDA = yeşil
  - I2C SCL = sarı
  - Analog sinyal = mavi
- Güç rail’lerini baştan ayır: sol rail 3.3V, sağ rail GND gibi.
- Modülleri (ADS1115, BH1750, SHT31) aynı hizada koy.
- Kabloyu mümkün olduğunca kısa tut; uzun kablo = karmaşa + hata.
- Her modülün yanına minik etiket: “ADS”, “BH”, “SHT”.

### 10.3 Breadboard ile neyi test etmeliyim?
- Sensörleri ve I2C haberleşmesini test et (BH1750/ADS1115/SHT31).
- Röle/MOSFET kartını breadboard’a değil; terminal/klemens ile test et (yük akımı yüksek).

---

## 11) Adım Adım Kurulum Sırası (Önerilen)

1) **Masa testi (breadboard)**
   - 1 adet kat düğümü kur: **ESP32‑CAM + SHT31 + BH1750** (opsiyon: ADS1115).
   - Wi‑Fi üzerinden Raspberry Pi’ye telemetry + kamera snapshot akışını doğrula.
2) **Kontrol kutusu montajı**
   - PSU + sigorta bloğu + terminal bloklar yerleşsin.
   - Kutu içi kablo düzeni ve etiketleme yapılsın.
3) **Kat kablolaması**
   - Omurga kanalı çek.
   - KAT1 güç + LED (tek kanal PWM) + fan hatlarını çek.
   - KAT2 aynı.
4) **Sensör kabloları**
   - Kat içi sensör kablolarını (soil + I2C) kısa tut; güç kablolarından ayrı taşı.
5) **Yük testleri**
   - Önce düşük risk: LED/fan.
   - Sonra egzoz.
   - En son ısıtıcı (özellikle AC ise).
6) **SAFE MODE / acil durdur kontrolü**
   - İlk günlerde her şey SAFE MODE ile izlenip doğrulansın.

---

## 12) En Sık Yapılan Hatalar (Önlemek için)

- Röle kartını Pi’den beslemek (Pi reset atar / port yanar).
- GND ortaklamamak (ADS okumaları “uçuşur”).
- Sensör kablolarını LED güç kablolarıyla aynı demetten taşımak (gürültü).
- Breadboard’u kalıcı sistem gibi kullanmak (nem + titreşim = temas problemi).
- AC yükleri küçük röle kartıyla sürmek (ısınma/yangın riski).

---

## 13) Netleştirmemiz Gereken 3 Veri (donanımı kesinleştirmek için)

1) LED bar bilgisi geldi:
   - 1m bar, 72 LED/m, 1000–1800 lm, **12V 1,4–2A** (≈17–24W)
   - Toplam 4 bar (KAT1: 2 bar tek kanal PWM, KAT2: 2 bar tek kanal PWM)
2) Fanların voltajı ve yaklaşık Watt/Ampere değeri? (Kat1 fan, Kat2 fan, egzoz fan, fide fan)
3) Sera ısıtıcı ve fide ısıtıcı **AC mi DC mi**, kaç Watt?

Bu üç bilgi gelince:
- 12V PSU gücünü net seçeriz,
- kablo kesitini “tam” belirleriz,
- sigorta değerlerini netleştiririz.
