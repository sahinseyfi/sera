# Tokopedia Alışveriş Listesi (Endonezya) — AKILLI SERA

Bu liste, serayı “bir üst seviye”ye taşımak için **en çok fark yaratacak** parçalara göre önceliklendirildi.
Amaç: daha güvenli güç dağıtımı, daha temiz kablolama, daha iyi sensör kalitesi ve ileride büyümeye hazır mimari.

> Not: Fiyatları sen gireceksin; Tokopedia’da “arama kelimeleri” bıraktım.

---

## P0 — Güç, Güvenlik, Temiz Kablolama (öncelik)

| Ürün | Önerilen özellik | Adet | Neden? | Tokopedia arama |
|---|---|---:|---|---|
| 12V ana güç kaynağı (SMPS) | 12V **15–20A** (180–240W), kısa devre/akım/ısı korumalı, metal kasa | 1 | 4× LED bar + fanlar + PTC ile 8.5A adaptör sınırda kalabilir; headroom güvenlik sağlar | `power supply 12V 20A`, `SMPS 12V 20A` |
| DC sigorta kutusu | ATO/ATC **8–12 hat** sigorta kutusu + sigorta seti (1A/3A/5A/10A) | 1 | Her hattı ayrı korumak (LED1/LED2/fan/pompa/PTC) yangın riskini azaltır | `fuse box ATO`, `fuse holder automotive` |
| IP korumalı kutu | En az IP54/65, kapak contalı; kablo rakoru için düz yüzey | 1 | Nemli ortamda PSU + dağıtım elemanlarını güvenle toplamak | `box enclosure IP65`, `waterproof enclosure` |
| Kablo rakoru / gland seti | M16/M20 set (farklı çaplar) | 1 set | Kutudan çıkan kabloları sıkıp su girişini azaltmak | `cable gland M16`, `cable gland M20` |
| Klemens & bağlantı | Wago 221/222 benzeri, klemens blok, ring pabuç + ferrül seti | 1 set | “Twist‑tape” yerine güvenli ve servis edilebilir bağlantı | `Wago 221`, `ferrule kit`, `terminal block` |
| Krimp pensesi | Ferrül + pabuç için uygun | 1 | Sağlam ve standart bağlantı | `crimping tool ferrule` |
| Kablo seti | 0.5–0.75mm² (fan/LED), 1.5mm² (12V ana hat), sinyal kablosu (2×0.22mm²) | yeterli | Voltaj düşümünü ve ısınmayı azaltır, düzenli demet yapmayı kolaylaştırır | `kabel 0.75mm`, `kabel 1.5mm`, `kabel signal 2 core` |
| Isı ile daralan makaron (ek) | Yapışkanlı (adhesive‑lined) karışık set | 1 | Nemli ortamda izolasyon/koruma daha iyi olur | `heat shrink adhesive` |

---

## P1 — Çıkışları “Doğru” Sürmek (LED/Fan/Pompa için)

| Ürün | Önerilen özellik | Adet | Neden? | Tokopedia arama |
|---|---|---:|---|---|
| MOSFET anahtarlama kartı | **8–16 kanal**, DC 5–36V, kanal başı **≥5A**, “low‑side” N‑MOSFET, 3.3V GPIO ile tetiklenebilir (veya üzerinde driver/opto) | 1 | 12V LED bar/fan/pompa için röleden daha sessiz ve PWM’e uygun | `MOSFET module 8 channel`, `MOSFET module 16 channel` |
| Flyback diyot seti | En az 3A sınıfı (pompa/fan için) | 1 set | Endüktif yüklerde MOSFET’i ve Pi’yi korur | `flyback diode 3A`, `diode 1N5408` |
| TVS diyot (12V hat) | 12V otomotiv sınıfı TVS (transient absorber) | 1–2 | Fan/pompa anahtarlamada oluşan sıçramaları bastırır | `TVS diode 12V` |
| 12V fanlar (tamamlamak) | Tercihen **4‑wire PWM** (hız kontrol istersek), ball bearing; aynı model seç | 3–4 | Hedef kurulum: Kat1 fan + Kat2 fan + egzoz + (opsiyonel) fide fanı; 1 yedek iyi olur | `fan 12V PWM 4 wire`, `fan 12V 120mm` |

### Aday ürün (bulundu): HAT2195R 8‑Channel MOSFET Driver
- Ürün adı: “Module Driver Mosfet 8-Channel 30V 18A RENESAS HAT2195R 8Ch MOS DC PWM Power Switching”
- İlan teknik notları: PC817S optocoupler, “anti‑feedback diode” (flyback), active‑high, 12/24V (max 30V)
- Fiyat örneği: ~`Rp131.000` (satıcıya/kur/indirimlere göre değişebilir)
- Siparişten önce kontrol: “3.3V trigger / 3.3–5V input” ibaresi veya ürün fotoğraflarında giriş pinleri (VCC/GND/IN) netliği

> Röle kartların (1/2/4/8 kanal) var; AC yük/izolasyon gereken yerlerde hâlâ değerli.  
> DC LED/fan işini MOSFET’e taşımak genelde daha temiz oluyor.

---

## P2 — Sensörleri Geleceğe Hazır Yapmak (DHT → SHT)

| Ürün | Önerilen özellik | Adet | Neden? | Tokopedia arama |
|---|---|---:|---|---|
| SHT31 sıcaklık/nem sensörü | I2C modül, adres seçilebilir (`0x44/0x45`) | 2 | SERA + FIDE için daha stabil ölçüm; DHT’ye göre daha iyi | `SHT31 I2C` |
| LDR seti | 4× LDR + 10k (1%) direnç seti | 1 set | Kat1/Kat2 LDR + yedek; BH1750 yanında kalibrasyon planı | `LDR sensor`, `photoresistor`, `resistor 10k 1%` |
| DS18B20 prob (ek) | Waterproof, 1‑Wire | 1–2 | Yedek/karşılaştırma | `DS18B20 waterproof` |
| I2C çoklayıcı (opsiyonel) | TCA9548A | 1 | Aynı adreste birden fazla I2C cihazı eklemek istersen büyütür | `TCA9548A I2C multiplexer` |

## P2.5 — Dağıtık Düğüm (Opsiyonel): ESP32

ESP32, serada **kablolamayı azaltmak** ve “kat/kapalı kutu” gibi yerlerde sensör/aktüatörü yerinde yönetmek için iyi.
En güvenli kullanım: önce **sensör düğümü** olarak başla; kritik aktüatörleri (özellikle 230V ısıtıcı) Wi‑Fi’a bağlama.

| Ürün | Önerilen özellik | Adet | Neden? | Tokopedia arama |
|---|---|---:|---|---|
| ESP32 geliştirme kartı | ESP32‑WROOM‑32 / DevKit V1, USB’li, 4MB flash (CH340/CP2102) | 4 | KAT1 + KAT2 + FIDE için 3 düğüm + 1 yedek (Wi‑Fi/sensör/IO dağıtımı) | `ESP32 DevKit V1`, `ESP32 WROOM 32`, `modul ESP32` |
| DC‑DC step‑down (opsiyonel) | 12V→5V **3A** buck (kaliteli) | 3–4 | Her ESP32 düğümünü 12V ana hattan stabil 5V ile beslemek için | `buck converter 12V 5V 3A`, `DC DC step down 12V to 5V` |

## P2.6 — Kamera (Kat Görüntüsü)

2 kat için pratik yaklaşım: **kat başına 1 kamera**.

| Ürün | Önerilen özellik | Adet | Neden? | Tokopedia arama |
|---|---|---:|---|---|
| ESP32‑CAM kamera kiti | ESP32‑CAM (AI Thinker) + OV2640 + **USB‑Serial CH340 adapter** (MB/Downloader) | 2 | Kat1 + Kat2 snapshot/stream | `ESP32-CAM OV2640 CH340`, `ESP32 CAM MB CH340` |
| Harici antenli versiyon (opsiyonel) | IPEX/u.FL konnektörlü ESP32‑CAM + anten | 2 | Sera içinde Wi‑Fi çekimi zayıfsa fark eder | `ESP32-CAM external antenna`, `ESP32 CAM IPEX` |
| 5V besleme (kamera için) | Her kamera için stabil 5V (tercihen 1A+); 12V hattan beslenecekse buck | 2 | ESP32‑CAM güç dalgalanmasına hassas; reset/stream kopmasını azaltır | `buck 12V to 5V 2A`, `power supply 5V 2A` |

---

## P2.7 — Sulama (Tek Pompa, Çok Kat)

Tek pompa ile birden fazla kata sulama yapmak için “su nereye gidecek?” sorusunun cevabı: **valf**.
Debi sensörü ile “ne kadar su gitti?”yi ölçebilirsin; ama doğru bölüşüm için her kat hattını ayrı açıp kapatmak gerekir.

| Ürün | Önerilen özellik | Adet | Neden? | Tokopedia arama |
|---|---|---:|---|---|
| Solenoid valf (NC) | **12V DC**, normalde kapalı (NC), uygun çap (1/4”–1/2”), su için | 2 | KAT1/KAT2 hatlarını ayrı kontrol etmek için (sadece sulanacak kat açılır) | `solenoid valve 12V NC`, `katup solenoid 12V NC` |
| Check valve (tek yön) | Uygun çap, düşük kaçak | 2–4 | Geri akışı ve “üst kattan geri sifon”u azaltır | `check valve`, `one way valve` |
| Manifold / T bağlantı | Pompa çıkışını katlara bölmek için | 1 | Temiz dağıtım | `manifold`, `tee fitting` |
| Sulama hortumu + fitting | Katlara giden hatlar için uygun çap | yeterli | Sızıntısız, servis edilebilir tesisat | `selang air`, `fitting quick`, `barb fitting` |
| Inline filtre | Pompa çıkışında küçük filtre | 1 | Damlama uçlarını tıkamayı azaltır | `inline water filter` |
| Damlama ucu / restrictor | Sabit debi/akış kısıtlayıcı | ihtiyaca göre | Saksılar arasında daha dengeli su dağıtımı | `drip emitter`, `flow restrictor` |
| Debi sensörü (yerleşim notu) | (Opsiyon) Kat başına veya ortak | 1–2 | Hacim ölçümü + “akış yok” hata tespiti | `flow sensor hall` |

Debi sensörü yerleşimi (pratik):
- **Sadece 1 sensör alacaksan:** pompa çıkışı + manifold öncesi (ve aynı anda sadece 1 valf açık).
- Daha doğru (ama daha çok parça): her kat hattına 1 debi sensörü (valften sonra).

---

## P3 — “Arıza Olunca Fark Et” Katmanı

| Ürün | Önerilen özellik | Adet | Neden? | Tokopedia arama |
|---|---|---:|---|---|
| Depo su seviye sensörü | Şamandıra switch (NC/NO) | 1 | Pompanın kuru çalışmasını engeller | `float switch` |
| Debi sensörü (opsiyonel) | Hall effect flow sensor | 1 | Pompa çalışıyor ama akış yok mu? anlaşılır | `flow sensor hall` |
| Dayanıklı depolama | High Endurance microSD 32/64GB veya küçük USB SSD | 1 | Log/trend yazımı için daha güvenilir | `high endurance microsd`, `usb ssd` |

---

## P4 — PWM (Dimming/Hız Kontrol) için Mantıklı mı?

Evet, **özellikle LED barlarda PWM mantıklı**:
- Lux hedefini daha “yumuşak” tutturur (LED1/LED2 kademesine ek ince ayar).
- Enerji ve ısı yükünü düşürebilir.

Ama birkaç kritik not:
- **LED için**: PWM frekansı görünür titreme olmaması için genelde **≥1 kHz** iyi başlangıçtır (çok düşük PWM gözle titrer).
- **2 kablolu DC fan**: PWM ile çalışabilir ama bazen **vınlama** yapar veya düşük duty’de durabilir. Eğer hız kontrol istiyorsan, mümkünse **4‑wire PWM fan** tercih etmek daha temiz olur.
- **Pompa**: PWM yerine “kısa darbeli ON/OFF” (pulse) genelde daha güvenli ve basittir.

PWM’i “opsiyonel” tutmak için:
- Donanım tarafında MOSFET kart seçerken PWM destekli ve 3.3V uyumlu olmasına dikkat et.
- Yazılımda her kanal için “Mode: on/off vs pwm” şeklinde konfigürasyon mantığı planlanabilir.

---

## Sepet Snapshot (Tokopedia) — 2025-12-30

Bu bölüm, “şu an sepette olanlar”ı kaybetmemek için.

| Ürün | Birim (Rp) | Adet | Ara Toplam (Rp) | Not |
|---|---:|---:|---:|---|
| BH1750 Light Sensor | 17.500 | 3 | 52.500 | 3 adet aynı I2C hatta kullanılacaksa adres/çoklayıcı konusu var (BH1750 genelde 2 adres). Kat başına ayrı ESP düğümü ise sorun yok. |
| Solenoid Valve 12V DC 3/4" (NC?) | 59.000 | 3 | 177.000 | “NC” ve gerçekten “12V DC coil” olduğundan emin ol. Bazı valfler minimum basınç ister; 3/4" küçük pompa/ince hortumla uyumsuz olabilir. |
| Case ESP32‑CAM + shield programmer box | 24.700 | 3 | 74.100 | Kutu içinde ısı/nem birikmesine dikkat; lens önü buğulanmasın. |
| GY‑SHT31 sıcaklık/nem modülü | 27.900 | 2 | 55.800 | 2 sensör aynı hatta olacaksa adres jumper’ı (0x44/0x45) kontrol et. |
| Flow sensor YF‑S401 1/8" | 45.500 | 2 | 91.000 | Kalibrasyon şart; pulse çıkışını ESP32’ye 3.3V seviyede okuma planı yap. |
| Float switch (water level) | 20.468 | 1 | 20.468 | Depo “kuru çalışma” engeli. |
| ESP32‑CAM OV2640 + CH340 adapter | 118.500 | 3 | 355.500 | CH340 kartı programlamak içindir; final kurulumda her kart için stabil 5V besleme gerekir (buck ile). |
| MOSFET Driver 8‑Channel HAT2195R | 131.000 | 1 | 131.000 | 8 kanal toplam çıkışa yetiyor mu kontrol et (valf/pompa/fan/LED sayısı). |
|  |  |  | **957.368** | (kargo hariç) |

### Sepette olmayan ama “unutulmaması” gerekenler
- 12V ana PSU: **15–20A** (LED+fan+valf+PTC için headroom).
- Her ESP32/ESP32‑CAM için stabil 5V: `12V→5V` buck (en az 2A; mümkünse 3A).
- DC sigorta kutusu + sigortalar, kablo rakorları, klemens/ferrül/pabuç, kalın kesit kablo.
- Sulama için: manifold/T bağlantı, check valve, inline filtre, hortum + fitting, damlama uçları.
