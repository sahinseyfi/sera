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
