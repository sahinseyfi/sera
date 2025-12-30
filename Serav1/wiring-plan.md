# Kablolama Planı (ESP32‑CAM Düğüm + Merkezi Aktüatör) — AKILLI SERA

Bu doküman; yeni mimaride **hangi cihazın hangi pine bağlanacağını** ve **hangi kablonun nereden nereye gideceğini** planlamak için hazırlanmıştır.
Öncelik: **güvenlik**, servis edilebilirlik ve kablo karmaşasını azaltmak.

> Güvenlik: 230V AC tehlikelidir. AC tarafını yetkin değilsen elektrikçiye yaptır. DC tarafta da sigorta/kalın kesit/etiketleme ihmal edilmemeli.

## 0) Varsayımlar (bu planın dayandığı kararlar)
- Her kat/zone için 1 adet **ESP32‑CAM düğümü**: sensör okur + kamera görüntüsü sağlar.
- Sensörler düğüme **kısa kablo** ile bağlanır; Raspberry Pi’ye sensör kablosu taşınmaz.
- Raspberry Pi:
  - Panel (Flask) + veri kaydı + otomasyon + güvenlik (SAFE MODE / emergency stop) merkezidir.
  - ESP32’den telemetri + görüntü alır; **görüntü işlemeyi Pi yapar**.
- Işık kontrolü: **kat başına tek dimmable kanal** (2 LED bar birlikte PWM dim).
- Aktüatör sürme: tek bir kontrolcü (Raspberry Pi) → **8 kanal MOSFET** kartı (ana DC yükler).
  - KAT1/KAT2 canopy fanlar: **2 kanal röle kartı** ile on/off (Pi GPIO).
- LCD (20×4 I2C) Pi I2C hattında.
  - Not: Tek bir MOSFET kartını birden fazla ESP32 ile sürmek mümkündür ama her kanalın “tek sürücüsü” olmalı ve uzun kontrol kabloları/ortak GND/boot anı pin durumları iyi yönetilmelidir. Bu doküman merkezi (Pi kontrollü) yaklaşımı esas alır.

## 0.1) Kullanılan ESP32 modülü (senin aldığın paket)
- Model: **ESP32‑CAM OV2640 (4MP) + CH340 USB‑Serial adapter**
- PSRAM: **4MB** (WROVER sınıfı)
- microSD/TF slot: var (kullanacaksan pin çakışmalarını dikkate al)
- Varsayılan node ID’ler: `kat1-node`, `kat2-node`, `fide-node` (opsiyon: `sera-node`)

Pin notları (pratik):
- Bu planda I2C için `GPIO13/14` kullanılıyor → bu seçimle **microSD kullanmamak** daha temizdir (ESP32‑CAM’de SD slot tipik olarak `GPIO12/13/14/15/2/4` pinlerini kullanır).
- Boot strap pinleri (`GPIO0/2/12/15`) dış devre pull‑up/down ile zorlanırsa kart açılmayabilir; sensör/hat eklerken bu pinlerde ekstra dikkat gerekir.

## 1) Kablo standartları (öneri)
- 12V LED hatları: `2×1.5–2.5 mm²` (kırmızı + siyah)
- 12V fan/valf/pompa hatları: `2×0.75–1.0 mm²`
- Düşük akım/sinyal: `2×0.22–0.5 mm²`
- I2C (düğüm içi): `4×0.22 mm²` (SDA/SCL/3V3/GND), mümkünse kısa (<30–50 cm)
- Uzun hatlarda: CAT5e/CAT6 kablo çok iş görür (çift bükümlü).

Renk önerisi:
- 12V+: kırmızı, 12V GND: siyah
- 5V+: turuncu, 5V GND: siyah
- I2C SDA: yeşil, I2C SCL: sarı, 3V3: kırmızı, GND: siyah
- PWM/Control sinyali: mor, dijital on/off: mavi

## 2) Mimari: “ne nerede duruyor?”
### 2.1 Kontrol Kutusu (merkez)
- 12V PSU (15–20A)
- DC sigorta kutusu (hat başına sigorta)
- Raspberry Pi 4
- 8‑kanal MOSFET sürücü kartı (DC yükler)
- 2‑kanal röle kartı (KAT1/KAT2 canopy fanlar)
- 20×4 I2C LCD (kutu dışı olabilir; I2C hattı buradan çıkar)
- (Opsiyon) 12V→5V buck (Pi’nin 5V beslemesi için ayrı planın varsa)

### 2.2 Katlar / Zone Düğümleri
Her zone (KAT1, KAT2, FIDE) için:
- 1× ESP32‑CAM (Wi‑Fi)
- 1× 12V→5V buck (ESP32 besleme)
- I2C sensörler: SHT31 + BH1750
- Analog sensörler: kapasitif toprak nem sensör(ler)i → **ADS1115 (önerilen)**

> Not: ESP32‑CAM kartlarında kullanılabilir ADC pin sayısı kısıtlı olabilir; bu yüzden analog sensörler için node üzerinde ADS1115 tercih edilir.

## 3) Raspberry Pi pin planı (BCM + fiziksel pin)
Bu bölüm “tüm pin girişlerini” tek yerde toplar.

> Not: Buradaki GPIO/BCM planı “yeni kurulum” içindir; mevcut çalışan sistemindeki `config/channels.json` ile birebir aynı olmak zorunda değil. Kablolama hangi pine göre yapıldıysa yazılım konfigürasyonu da ona göre güncellenmeli.
> Not: GPIO eşlemesi panelden değiştirilebilir olmalı; pin değiştiğinde ilgili kanal **OFF** yapılmalı ve kullanıcı onayı istenmelidir.

### 3.1 MOSFET kartı kontrol pinleri (8 çıkış)
Varsayım: MOSFET kartı “IN1..IN8” şeklinde giriş alıyor ve logic GND ile ortak referans istiyor.

| MOSFET CH | Yük (load) | Pi BCM | Fiziksel pin | Kablo tipi |
|---:|---|---:|---:|---|
| 1 | `KAT1_LIGHT` (PWM dim) | 18 | 12 | 1× sinyal (0.22–0.5) |
| 2 | `KAT2_LIGHT` (PWM dim) | 19 | 35 | 1× sinyal (0.22–0.5) |
| 3 | `EXHAUST_FAN` (on/off) | 23 | 16 | 1× sinyal (0.22–0.5) |
| 4 | `PUMP` (on/off) | 24 | 18 | 1× sinyal (0.22–0.5) |
| 5 | `VALVE_KAT1` (on/off) | 25 | 22 | 1× sinyal (0.22–0.5) |
| 6 | `VALVE_KAT2` (on/off) | 20 | 38 | 1× sinyal (0.22–0.5) |
| 7 | `FIDE_HEATER` (on/off) | 21 | 40 | 1× sinyal (0.22–0.5) |
| 8 | `FIDE_FAN` (on/off) | 16 | 36 | 1× sinyal (0.22–0.5) |

Ortak:
- Pi GND → MOSFET GND (ör. fiziksel pin 6/9/14/20/25/30/34/39’dan biri)
- MOSFET kartı logic beslemesi kartına göre: **3.3V/5V** (kart datasheet’ine göre). I2C sensörlerde **asla 5V pull‑up** yapma.

### 3.1.1 Endüktif yük koruması (fan/pompa/valf) — kritik
- Solenoid valf, pompa ve (özellikle 2 kablolu) fanlar endüktif yüklerdir; kapatırken gerilim sıçraması üretir.
- MOSFET kartında dahili koruma yoksa **her yük için flyback diyot** ekle (en az 3A sınıfı, ör. `1N5408` / Schottky muadili).
- Diyot yönü (low‑side varsayımı ile):
  - **Katot (çizgili uç)** → `+12V`
  - **Anot** → MOSFET kanalının “yük eksi” tarafı (`OUT`)

### 3.1.2 Röle kartı kontrol pinleri (canopy fanlar)
Varsayım: 2 kanal röle kartı “IN1/IN2” girişli, logic GND ortak ve ayrı 5V besleme ister.

| Röle CH | Yük (load) | Pi BCM | Fiziksel pin | Not |
|---:|---|---:|---:|---|
| 1 | `KAT1_FAN` (on/off) | 27 | 13 | Röle active‑low/active‑high durumunu test et |
| 2 | `KAT2_FAN` (on/off) | 22 | 15 | Röle active‑low/active‑high durumunu test et |

Ortak:
- Pi GND → Röle GND (ortak referans şart)
- Röle VCC: ayrı **5V** besleme (Pi 5V pininden besleme önerilmez)

### 3.2 Debi sensörü + şamandıra (giriş pinleri)
Hedef: pompa çalışıyor ama akış yoksa hızlı durdurma; depo boşsa pompayı kilitleme.

| Sensör | Pi BCM | Fiziksel pin | Not |
|---|---:|---:|---|
| `FLOW_KAT1` | 5 | 29 | Debi sensörü pulse |
| `FLOW_KAT2` | 6 | 31 | Debi sensörü pulse |
| `FLOW_SPARE` (opsiyon) | 26 | 37 | Yedek / ana hat debi |
| `TANK_FLOAT` | 17 | 11 | Depo seviye şamandıra |

Elektrik notu (kritik):
- Debi sensörlerinin çıkışı 5V olabilir; Pi GPIO **3.3V** ister.
- En güvenli yaklaşım: sensör çıkışı **open-collector** ise Pi tarafında **3.3V pull‑up** ile oku.
- Emin değilsen: seviye dönüştürücü/optokuplör veya bölücü kullan (dokümana “ölçmeden bağlama” kuralını ekle).

### 3.3 LCD (20×4 I2C) — Raspberry Pi
- Pi I2C pinleri: `SDA=BCM2 (Pin 3)`, `SCL=BCM3 (Pin 5)`
- LCD besleme: **5V + GND**
- Tipik I2C adresleri: `0x27` veya `0x3F`
- LCD backpack üzerinde 5V pull‑up varsa: **seviye dönüştürücü** kullan veya pull‑up’ları 3.3V’a taşı (Pi I2C 5V toleranslı değildir)

## 4) ESP32‑CAM düğüm pin planı (zone başına aynı)
### 4.1 I2C hattı (tek bus)
Önerilen pinler (AI Thinker ESP32‑CAM için yaygın, kamera ile çakışmayan):
- `GPIO13` → SDA
- `GPIO14` → SCL

> Not: I2C pull‑up dirençleri modüllerin üzerinde olabilir. Modülleri **3.3V** ile besleyerek I2C seviyesini güvenli tut.

### 4.2 Node üzeri I2C cihazları (önerilen adresler)
Her node’da aynı adresler kullanılabilir (node bus’ları ayrı):
- SHT31: `0x44` (ADDR=GND), alternatif `0x45`
- BH1750: `0x23` (ADDR=GND), alternatif `0x5C`
- ADS1115 (opsiyon ama toprak sensörü için önerilir): `0x48` (ADDR=GND)

## 5) Zone bazlı “neyi nereden nereye götürüyoruz?”
Bu bölüm kablo rotasını netleştirir. Rotalar sahadaki mesafeye göre değişir; amaç **kablo demetlerini standardize etmek**.

### 5.1 KAT1
- Kontrol kutusu → KAT1 LED barlar:
  - 12V+ (sigortadan) → LED bar + (her iki bar paralel)
  - LED bar − → MOSFET CH1 OUT (low‑side varsayımı)
  - Kablo: `2×1.5–2.5 mm²`, etiket: `KAT1_LIGHT_12V+`, `KAT1_LIGHT_-`
- Kontrol kutusu → KAT1 canopy fan (röle):
  - Röle CH1 COM → 12V+ (sigorta)
  - Röle CH1 NO → fan +
  - Fan − → 12V GND
  - Kablo: `2×0.75–1.0 mm²`, etiket: `KAT1_FAN_12V+`, `KAT1_FAN_GND`
- Kontrol kutusu → KAT1 ESP32 düğümü:
  - 12V+ (sigortadan) → buck IN+
  - 12V− → buck IN−
  - buck 5V → ESP32 5V, buck GND → ESP32 GND
  - Kablo: `2×0.75–1.0 mm²` (12V), düğüm içinde kısa 5V bağlantı
- KAT1 düğümü → sensörler (kısa):
  - I2C 4’lü: `3V3/GND/SDA/SCL` → SHT31 + BH1750 + ADS1115
  - Kapasitif nem sensörü → ADS1115 A0 (3 tel: VCC/GND/SIG)

### 5.2 KAT2
- MOSFET CH2: `KAT2_LIGHT` (KAT2’deki iki bar paralel)
- KAT2 toprak nem sensörü → ADS1115 A0 (3 tel: VCC/GND/SIG)
- Kontrol kutusu → KAT2 canopy fan (röle):
  - Röle CH2 COM → 12V+ (sigorta)
  - Röle CH2 NO → fan +
  - Fan − → 12V GND
  - Kablo: `2×0.75–1.0 mm²`, etiket: `KAT2_FAN_12V+`, `KAT2_FAN_GND`
- KAT2 node sensörleri KAT1 ile aynı (I2C + ADS1115)

### 5.3 FIDE
- MOSFET CH7: `FIDE_HEATER` (12V PTC ise DC MOSFET ile sürülebilir; AC ise bu kanalı kullanma)
- MOSFET CH8: `FIDE_FAN`
- FIDE node: SHT31 + BH1750 (+ kamera)

### 5.4 Sulama (merkez)
- MOSFET CH4: `PUMP`
- MOSFET CH5/CH6: `VALVE_KAT1` / `VALVE_KAT2`
- Debi sensörleri:
  - Tercih 1 (öneri): valften sonra **hat başına** 1 debi sensörü → `FLOW_KAT1`, `FLOW_KAT2`
  - Tercih 2: tek sensör (pompa çıkışı + manifold öncesi) → aynı anda sadece 1 valf açık kuralı
  - Sepet uyumu: 1/4" **DC12 solenoid valf** ve 1/4" **debi sensörü**nden 3’er adet var → bu plan 2 hat (KAT1/KAT2) + 1 yedek / ileride 3. hat için uygundur.

## 6) Etiketleme (zorunlu)
Etiket standardı (örnek):
- Güç: `KAT1_12V+`, `KAT1_GND`
- Aktüatör: `KAT1_LIGHT`, `KAT1_FAN`, `KAT2_FAN`, `VALVE_KAT2`, `PUMP`
- Node: `KAT1_NODE_5V`, `KAT1_NODE_I2C_SDA`
- LCD: `LCD_SDA`, `LCD_SCL`, `LCD_5V`, `LCD_GND`

## 7) Kurulum sonrası hızlı doğrulama (güvenli)
1) Tüm sigortalar takılı, tüm MOSFET kanalları OFF iken 12V hatlarını ölç (kısa devre yok).
2) ESP32 node’ları tek tek besle, Wi‑Fi bağlantısını doğrula.
3) I2C cihazlarını node üzerinde doğrula (adresler çakışıyor mu?).
4) Yük bağlamadan önce MOSFET çıkışlarını multimetre ile doğrula.
5) En son yüklerle kısa süre test (pompa/ısıtıcı süre limitli).

## 8) Görsel Şema (blok diyagram)

> Not: Mermaid diyagramları her görüntüleyicide render olmayabilir. Render yoksa altındaki ASCII “pinout” ve bağlantı şemaları referanstır.

### 8.1 Sistem blok diyagramı (Mermaid)
```mermaid
flowchart TB
  subgraph CB[Kontrol Kutusu]
    PSU[12V PSU (15–20A)]
    FUSE[DC Sigorta Kutusu]
    PI[Raspberry Pi 4]
    MOSFET[8ch MOSFET Driver\n(low-side varsayımı)]
    RELAY[2ch Relay Board\n(canopy fans)]
    LCD[LCD 20x4 (I2C)]
  end

  PSU --> FUSE
  PI -- GPIO PWM/Digital --> MOSFET
  PI --- GND --- MOSFET
  PI -- GPIO Digital --> RELAY
  PI --- GND --- RELAY
  PI -- I2C --> LCD

  %% Loads (12V+ from fuse, - switched by MOSFET channel)
  FUSE -->|12V+| K1L[KAT1 LED Bars\n(2 bar paralel)]
  MOSFET -->|CH1 (low-side)| K1L

  FUSE -->|12V+| K2L[KAT2 LED Bars\n(2 bar paralel)]
  MOSFET -->|CH2 (low-side)| K2L

  FUSE -->|12V+| K1F[KAT1_FAN]
  RELAY -->|CH1| K1F

  FUSE -->|12V+| K2F[KAT2_FAN]
  RELAY -->|CH2| K2F

  FUSE -->|12V+| EXF[EXHAUST_FAN]
  MOSFET -->|CH3| EXF

  FUSE -->|12V+| PUMP[PUMP]
  MOSFET -->|CH4| PUMP

  FUSE -->|12V+| V1[VALVE_KAT1]
  MOSFET -->|CH5| V1

  FUSE -->|12V+| V2[VALVE_KAT2]
  MOSFET -->|CH6| V2

  FUSE -->|12V+| FH[FIDE_HEATER\n(DC ise)]
  MOSFET -->|CH7| FH

  FUSE -->|12V+| FF[FIDE_FAN]
  MOSFET -->|CH8| FF

  %% Inputs to Pi
  FLOW1[FLOW_KAT1\n(pulse)] --> PI
  FLOW2[FLOW_KAT2\n(pulse)] --> PI
  FLOWX[FLOW_SPARE\n(opsiyon)] -.-> PI
  TANK[TANK_FLOAT] --> PI

  %% ESP32 nodes
  subgraph KAT1[Zone: KAT1]
    K1BUCK[12V->5V Buck]
    K1ESP[ESP32-CAM]
    K1I2C[I2C Bus]
    K1SHT[SHT31]
    K1BH[BH1750]
    K1ADC[ADS1115 (öneri)]
    K1SOIL[Capacitive Soil Sensors]
  end

  subgraph KAT2[Zone: KAT2]
    K2BUCK[12V->5V Buck]
    K2ESP[ESP32-CAM]
    K2I2C[I2C Bus]
    K2SHT[SHT31]
    K2BH[BH1750]
    K2ADC[ADS1115 (öneri)]
    K2SOIL[Capacitive Soil Sensors]
  end

  subgraph FIDE[Zone: FIDE]
    FBUCK[12V->5V Buck]
    FESP[ESP32-CAM]
    FI2C[I2C Bus]
    FSHT[SHT31]
    FBH[BH1750]
  end

  FUSE -->|12V+| K1BUCK -->|5V| K1ESP
  FUSE -->|12V+| K2BUCK -->|5V| K2ESP
  FUSE -->|12V+| FBUCK -->|5V| FESP

  K1ESP --- Wi-Fi Telemetry/Images --- PI
  K2ESP --- Wi-Fi Telemetry/Images --- PI
  FESP --- Wi-Fi Telemetry/Images --- PI

  K1ESP --> K1I2C --> K1SHT
  K1I2C --> K1BH
  K1I2C --> K1ADC --> K1SOIL

  K2ESP --> K2I2C --> K2SHT
  K2I2C --> K2BH
  K2I2C --> K2ADC --> K2SOIL

  FESP --> FI2C --> FSHT
  FI2C --> FBH
```

### 8.2 Raspberry Pi 40-pin header (kullanılan pinler) — ASCII
```
Raspberry Pi 40-pin (Physical pin numbers)

 (Top view; SD card side)
 1  2      3  4      5  6      7  8      9 10
3V3 5V    SDA 5V    SCL GND   GPIO4 TXD   GND RXD
            LCD          LCD

 11 12     13 14     15 16     17 18     19 20
GPIO17 GPIO18 GPIO27 GND   GPIO22 GPIO23 3V3  GPIO24 MOSI GND
 TANK   KAT1_LIGHT KAT1_FAN     KAT2_FAN EXHAUST       PUMP
 FLOAT     (PWM)    (RELAY)      (RELAY)

 21 22     23 24     25 26     27 28     29 30
MISO GPIO25 SCLK  CE0   GND  CE1   ID_SD ID_SC GPIO5 GND
     VALVE_KAT1                          FLOW_KAT1

 31 32     33 34     35 36     37 38     39 40
GPIO6 GPIO12 GPIO13 GND   GPIO19 GPIO16 GPIO26 GPIO20 GND  GPIO21
FLOW_KAT2                KAT2_LIGHT FIDE_FAN FLOW_SPARE VALVE_KAT2   FIDE_HEATER
                          (PWM)             (opsiyon)
```

### 8.3 Sulama hattı (hidrolik + sinyal) — Mermaid
```mermaid
flowchart LR
  %% Hydraulic path (left -> right)
  TANK[(Depo)] --> P[PUMP]
  P --> FIL[Inline Filter]
  FIL --> M[Manifold / Tee]

  M --> V1[VALVE_KAT1 (NC)]
  V1 --> FS1[FLOW_KAT1]
  FS1 --> L1[KAT1 hat / drippers]

  M --> V2[VALVE_KAT2 (NC)]
  V2 --> FS2[FLOW_KAT2]
  FS2 --> L2[KAT2 hat / drippers]

  %% Spare line (optional)
  M -. opsiyon .-> V3[VALVE_SPARE]
  V3 -. opsiyon .-> FS3[FLOW_SPARE]

  %% Signals to Pi
  subgraph PI[Raspberry Pi Inputs]
    I1[BCM5 / Pin29\nFLOW_KAT1]
    I2[BCM6 / Pin31\nFLOW_KAT2]
    I3[BCM26 / Pin37\nFLOW_SPARE]
    I4[BCM17 / Pin11\nTANK_FLOAT]
  end

  FS1 -- pulse --> I1
  FS2 -- pulse --> I2
  FS3 -. pulse .-> I3
  TANK_SW[(Float switch)] --> I4
```

### 8.4 Tipik ESP32‑CAM düğüm bağlantısı (zone içi) — Mermaid
```mermaid
flowchart TB
  subgraph NODE[Zone Node (KAT1 / KAT2 / FIDE)]
    P12[12V (sigortadan)] --> BUCK[Buck 12V->5V]
    BUCK -->|5V| ESP[ESP32-CAM]

    ESP --- Wi-Fi Telemetry/Images --- PI[Raspberry Pi]

    ESP -->|SDA GPIO13| I2C[I2C Bus]
    ESP -->|SCL GPIO14| I2C

    I2C --> SHT[SHT31\n0x44/0x45]
    I2C --> BH[BH1750\n0x23/0x5C]
    I2C --> ADC[ADS1115 (opsiyon)\n0x48]
    ADC --> SOIL[Capacitive Soil Sensors\n(A0/A1/...)]
  end
```

### 8.5 Tek kanal low-side MOSFET + sigorta + flyback diyot — ASCII
```
                    (endüktif yükler: fan/pompa/valf)

12V+ (Sigorta) -----> [LOAD + ]  LOAD  [LOAD -] -----> MOSFET_CHx_OUT -----> GND
                         |                           |
                         +-----------|<|-------------+
                                   Flyback diyot
                          (Katot/çizgi -> +12V, Anot -> OUT)
```

> Not: MOSFET kartın low-side değilse (high-side gibi), şema değişir.
