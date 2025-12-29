# Donanım Planı (Yeni Panel) — Başlangıçtan Kurulum Rehberi

Bu doküman; sera sisteminin donanımını (sensörler, röle/driver, güç kaynakları, kablolama ve kutulama) planlamak için hazırlanmıştır.
Amaç: **güvenli**, **karışıklık çıkarmayan**, **sonradan büyütmesi kolay** bir kurulum.

> Güvenlik notu: 230V AC (şehir elektriği) tehlikelidir. Yetkin değilsen AC tarafını bir elektrikçiye yaptır. Bu doküman “ne yapılmalı”yı anlatır; uygulama sorumluluğu kullanıcıdadır.

---

## 1) Sistem Şeması (Zihin Haritası)

Bizim model:
- **SERA (genel)**: tüm seranın iklimi + genel ısıtıcı + egzoz fan
- **KAT1**: 2 sıra LED + 1 kat fanı + 1 toprak sensörü + 1 LDR
- **KAT2**: 2 sıra LED + 1 kat fanı + 1 toprak sensörü + 1 LDR
- **FİDE (kapalı kutu)**: ayrı ısıtıcı + (kutu içi) fan + (kutu içi) temp/nem sensörü

Ana prensip:
- **Kontrol kutusu** tek yerde olur (Pi + sürücüler + güç + sigortalar).
- Katlara **güç** gider (12V) ve kat üzerindeki yükler oradan beslenir.
- Sensör kabloları mümkün olduğunca **güç kablolarından ayrı** taşınır.

---

## 2) Ekipman Listesi (BOM) — Minimum + Önerilen

### 2.1 Zorunlu
- Raspberry Pi 4 + microSD
- 5V/3A Pi adaptörü (resmi önerilir)
- 12V DC güç kaynağı (fanlar + LED’ler için)
  - Güç hesabı: Toplam Watt / 12V = toplam akım (A). Üzerine %30 pay koy.
- **Kanal sürücüler**
  - LED ve 12V fanlar için: **MOSFET driver (önerilir)** veya röle
  - Eğer mutlaka röle: 16 kanal röle kartı (aşağıda kriterleri var)
- I2C sensör modülleri:
  - BH1750 (lux referans)
  - ADS1115 (analog okumalar: toprak + LDR)
  - SHT31 (SERA temp/nem için önerilen) + opsiyonel FİDE için de
- 2 adet kapasitif toprak nem sensörü (Kat1, Kat2)
- 2 adet LDR + 2 adet sabit direnç (kat LDR devresi için)
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
- KAT1: LED1, LED2, KatFan  → **3 çıkış**
- KAT2: LED1, LED2, KatFan  → **3 çıkış**
- FİDE: FideIsıtıcı, FideFan → **2 çıkış**
- SERA: EgzozFan, SeraIsıtıcı → **2 çıkış**

Toplam: **10 kontrol çıkışı**.

Öneri:
- Bugün 10 çıkış lazım ama yarın pompa/valf vb. eklenebilir.
- Bu yüzden **16 çıkış** planlamak “bir daha sök-tak yapmamak” için daha mantıklı.

> Not: Sera ısıtıcıyı Home Assistant akıllı priz ile kontrol edeceksen AC rölesi şart olmayabilir. Bu durumda çıkış ihtiyacı düşer ama yine de “yedek” için 16 mantıklı.

---

## 4) Röle mi MOSFET mi? (Hızlı Karar)

### LED şeritler ve 12V fanlar için (DC yük)
- **MOSFET driver (önerilir)**:
  - Sessiz, hızlı, sık aç-kapa’da yıpranmaz
  - PWM/step kontrol için daha uygun (ileride dimming)
- Röle:
  - Basit ON/OFF için olur ama sık anahtarlamada mekanik ömür kısalır

### Isıtıcı gibi yüksek güç AC yükler için
- En güvenlisi: **Home Assistant akıllı priz** (sertifikalı) veya **kontaktör/SSR** (uygun kutulama + sigorta + topraklama ile)
- 10A “hobi röle kartı” ile 1–2kW ısıtıcı sürmek **riskli** (ark, ısınma, klemens kalitesi).

Bu dokümanda röle kriterlerini de veriyorum; ama tasarım önerisi:
- **DC yükler: MOSFET**,
- **AC ısıtıcı: akıllı priz veya kontaktör**.

---

## 5) Röle Seçimi Kriterleri (Eğer Röle Kullanacaksak)

Minimum kriterler:
- Kanal sayısı: **16 kanal** (10 yük + yedek)
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
- **SERA (genel)**: SHT31 (I2C) önerilir
- **FİDE**: SHT31 veya DHT22/DHT11 (kutu içinde)

Neden SHT31?
- Daha stabil ve uzun vadede daha iyi (DHT’ler genelde daha “oynak”).

### 6.2 Lux
- BH1750: referans lux sensörü (I2C)
- Kat LDR’leri: KAT1 ve KAT2 için ayrı (ADS1115 analog)

LDR yaklaşımı:
- Her kat LDR’si “kendi” ışığı görür.
- Kalibrasyon: LDR’yi BH1750 yanına koyup bir katsayı çıkarırız (panelden).

### 6.3 Toprak Nemi (kapasitif)
- Sadece KAT1 ve KAT2 (FİDE yok).
- ADS1115 analog kanallarına bağlanır.

### 6.4 ADS1115 Kanal Eşlemesi (Kararlaştırdık)
- CH0 → KAT1 soil
- CH1 → KAT2 soil
- CH2 → KAT1 LDR
- CH3 → KAT2 LDR

---

## 7) Kablolama Mimarisi (Kutu İçi / Kutu Dışı)

### 7.1 Kutu İçi (Kontrol Kutusu)
Kutu içinde hedef: “her şey düz, etiketli, sökülebilir”.

Önerilen yerleşim sırası (soldan sağa):
1) AC giriş (varsa) + sigorta/RCD (AC işini elektrikçi yapsın)
2) 12V PSU
3) DC sigorta bloğu (katlara giden her hat ayrı sigorta)
4) Raspberry Pi + I2C sensör kartları (BH1750, ADS1115, SHT31)
5) MOSFET/relay sürücü kartları
6) Terminal bloklar (katlara giden kablolar için “çıkış paneli”)

Altın kurallar:
- **AC ve DC bölmeleri ayrı** (aynı kutu içindeyse bile fiziksel ayrım).
- Kablolar “güç” ve “sinyal” olarak iki demette ilerler.
- Her kablonun iki ucunda etiket: `KAT1_LED1`, `KAT2_SOIL`, vb.

### 7.2 Kutu Dışı (Katlara Kablo Gidişi)
Öneri: Sera iskeletinde bir “servis omurgası” seç (arka köşe gibi).
- Kontrol kutusundan çıkan tüm kablolar bu omurgadan yukarı iner/çıkar.
- Her kata gelince küçük bir dağıtım noktası (mini kutu veya klemens) oluştur.

Güç kabloları:
- 12V yüksek akım (LED’ler): daha kalın kesit (aşağıdaki tabloda)
- 12V fanlar: orta kesit

Sensör kabloları:
- Analog sensörler (soil, LDR): **signal + GND birlikte**, tercihen bükülü çift (twisted pair)
- Güç kablolarından en az 10–15 cm ayrı taşımaya çalış

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

## 9) LDR Devresi (Basit Anlatım)

LDR tek başına ölçülmez; bir “gerilim bölücü” kurarız:
- 3.3V → LDR → (ölçüm noktası) → Direnç → GND
- Ölçüm noktası ADS1115 kanalına gider.

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

1) **Masa testi (breadboard)**\n
   - Pi + ADS1115 + BH1750 + SHT31 bağla.\n
   - Sensör okuması stabil mi kontrol et.\n
2) **Kontrol kutusu montajı**\n
   - PSU + sigorta bloğu + terminal bloklar yerleşsin.\n
   - Kutu içi kablo düzeni ve etiketleme yapılsın.\n
3) **Kat kablolaması**\n
   - Omurga kanalı çek.\n
   - KAT1 güç + LED1/LED2 + fan hatlarını çek.\n
   - KAT2 aynı.\n
4) **Sensör kabloları**\n
   - Kat soil + kat LDR sinyallerini ayrı demetten çek.\n
5) **Yük testleri**\n
   - Önce düşük risk: LED/fan.\n
   - Sonra egzoz.\n
   - En son ısıtıcı (özellikle AC ise).\n
6) **SAFE MODE / acil durdur kontrolü**\n
   - İlk günlerde her şey SAFE MODE ile izlenip doğrulansın.\n

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
   - Toplam 4 bar (Kat1 LED1/LED2 + Kat2 LED1/LED2)
2) Fanların voltajı ve yaklaşık Watt/Ampere değeri? (Kat1 fan, Kat2 fan, egzoz fan, fide fan)
3) Sera ısıtıcı ve fide ısıtıcı **AC mi DC mi**, kaç Watt?

Bu üç bilgi gelince:
- 12V PSU gücünü net seçeriz,
- kablo kesitini “tam” belirleriz,
- sigorta değerlerini netleştiririz.
