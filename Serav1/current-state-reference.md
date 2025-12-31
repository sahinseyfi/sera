# Current State Reference - AKILLI SERA Panel

This document summarizes the current state of the codebase and runtime behavior
as a reference before the upcoming redesign.

## Scope
- Main panel lives in repo root (`app.py`, `templates/`, `static/`).
- `sera_panel/` is legacy/test content.
- Raspberry Pi 4 + Flask + GPIO control (HA integration is planned for the redesign).

## High-Level Architecture
- Flask app in `app.py`.
- UI templates in `templates/` and JS in `static/main.js`.
- Hardware abstraction for GPIO (single backend).
- Sensor manager reads DHT22, DS18B20, BH1750, ADS1115.
- Automation engine handles lux, heater, pump, fan logic.

## UI Pages (Current)

### Serav1 Beta UI (USE_NEW_UI=1)
- Genel Bakış: zon odaklı özet, otomasyon ve node sağlığı görünümü.
- Zoneler: zon kartları + mini trendler.
- Kontrol: zon odaklı manuel kontrol + güvenlik onay akışları.
- Geçmiş: trend grafikleri + olay günlüğü (filtreli) + rapor kısayolları.
- Ayarlar: SAFE MODE ve otomasyon özetleri.
- Diğer: Ayarlar/Raporlar/Güncellemeler/Yardım/Donanım/LCD/Notlar için hızlı erişim.
- Ortak base: `base_v1.html` (Serav1 navigasyon + mobil tabbar).
- UI etiketleri Türkçe (Genel Bakış/Zoneler/Kontrol/Geçmiş/Ayarlar/Diğer); URL’ler İngilizce kalır.

### Dashboard
- Canlı sensör kartları (DHT22, DS18B20, BH1750, ADS1115 ham kanalları).
- Özet satırı: SAFE MODE, son veri zamanı + yaşı, uyarı sayısı, otomasyon durumu.
- Otomasyon durum kartı: pencere, hedef dakika, override, blok, min-off, son kapanma sebebi.
- Otomasyon rozetleri: aktif, override, lux hata, max lux, kapalı.
- Grafikler: metrik seçimi + 24s/7g aralık + CSV indir.
- Grafik altı: min/max/son/sayı/güncelleme.
- Aktüatör durum listesi (durum, son değişim, sebep).
- Uyarı listesi (son 5).
- Enerji tahmini (24s/7g toplamları + kanal kırılımı; süreli kanallar notu).
- Sensör sağlık listesi (son OK, offline süresi, offline limit notu).
- Olay günlüğü (otomasyon + manuel).

### Kontrol
- SAFE MODE kilidiyle manuel röle kontrolü.
- Acil durdurma (hepsi OFF).
- Pompa/ısıtıcı onay akışı (geri sayım modal).
- Kanal bazlı cooldown notları (pompa, ısıtıcı).
- Son komut listesi + sebepler.

### Ayarlar
- Admin token girişi + durum (tarayıcıda saklanır).
- SAFE MODE anahtarı.
- Limitler: pompa max + cooldown, ısıtıcı max + cutoff.
- Kaydet düğmesi + kayıt durumu.
- Otomasyon bölümleri:
  - Lux (hedef dakika, lux OK/max, pencere, min on/off, manuel override).
  - Isıtıcı (sensör seçimi, sıcaklık bandı, max/min, gece modu, fan şartı).
  - Pompa (toprak kanalı, kuru eşik, pulse, günlük max, pencere, override).
  - Fan (RH high/low, max/min, gece modu, periyodik mod).
  - Toprak kalibrasyon tablosu (kuru/ıslak hızlı yakalama).
- Uyarı eşikleri (offline, sıcaklık/nem high/low).
- Enerji fiyat ayarları (kWh katmanları).

### Donanım
- Kanal eşleme tablosu:
  - ad, aktif, rol, GPIO pin, active low.
  - açıklama, güç, adet, toplam güç, voltaj, notlar.
- Sensör ayarları:
  - DHT22 GPIO, BH1750 adresi, ADS1115 adresi, DS18B20 etkin.
- Kaydet aksiyonu tüm kanalları güvenlik için OFF yapar.

### Geçmiş / Kayıtlar
- Sensör kayıt tablosu (from/to, limit, interval, order filtreleri).
- Aralık seçenekleri: raw, 1, 5, 15, 30, 60 dakika.
- Seçili aralık için CSV dışa aktarım.
- Kayıt temizle (sadece SQLite; CSV dosyaları kalır).

### Raporlar
- Günlük rapor: özet hikaye, karşılaştırmalar, ilerleme barları, açıklayıcı kartlar.
- Haftalık rapor: özet kartlar + haftalık grafik + günlük kırılım tablosu.
- Acemi modu ayrıntılı alanları gizler.
- Dış veri yoksa hava durumu uyarı bandı görünür (varsa).

### LCD
- I2C LCD ayarları (enable, mode, address, port, expander, charmap, size).
- Satır editörü (4x20) + sayaçlar.
- Satır temizle ve şablon hazır butonları.
- Token butonları seçili satıra ekler.
- Çözülmüş çıktı önizlemesi.
- LCD modu: auto / template / manual.

### Güncellemeler
- Değişiklik listesi `/api/updates` ile `config/updates.json` içinden okunur.
- Üstte son güncelleme tarihi gösterilir.
- Kayıt yoksa boş durum mesajı görünür.

### Notlar
- Konu bazlı statik iyileştirme önerileri.
- Veriler sunucuda render edilir; kullanıcı düzenleyemez.

### Yardım / SSS
- Dashboard, kontrol, ayarlar, kayıtlar, sorun giderme başlıkları.
- OK/SIM/HATA/YOK rozetlerini ve stale davranışını açıklar.

## Sensors (Current)
- DHT22: temp + humidity (GPIO).
- DS18B20: temp (1-Wire).
- BH1750: lux (I2C).
- ADS1115: raw soil moisture (I2C, 4 channels).

## Automation (Current)
- Lux automation (single light channel): target minutes, lux OK/max, window, min on/off.
- Heater automation (single heater): temp band + min off + max on + night mode.
- Pump automation (single pump): soil threshold + pulse + max daily + time window.
- Fan automation (single fan): RH high/low + min off + max on + night + periodic.

## Notifications (Current)
Not implemented in the current (main) codebase.
Planned in `Serav1/future-features.md` and `Serav1/panel-redesign-spec.md`.

## LCD (Current)
- LCD status is part of `/api/status` and can be updated via `/api/lcd`.
- Template tokens include:
  - `{temp}`, `{hum}`, `{lux}`, `{soil_pct}`, `{soil_raw}`, `{ds_temp}`.
  - `{pump}`, `{heater}`, `{safe}`, `{time}`.

## Safety
- SAFE MODE default ON: manual control locked, automation blocked.
- Emergency stop: all channels OFF.
- Pump/heater time limits + cooldowns.
- Sensor stale logic triggers alerts and safety behavior.

## Data/Logs
- SQLite database: `data/sera.db`.
- `sensor_log` table (fixed columns for DHT/DS/Lux/Soil).
- Daily CSV logs in `data/sensor_logs/`.
- Weather cache files in `data/cache/weather/` (per-day JSON, used by reports).

## Config
- `config/channels.json`: channels with role, GPIO, active_low.
- `config/sensors.json`: DHT22 GPIO, BH1750 addr, ADS1115 addr, DS18B20 enable, LCD settings.
- `config/updates.json`: UI updates feed.
- `config/reporting.json`: report thresholds + location (`SERA_LAT`, `SERA_LON`, `SERA_TZ`) for weather-based comparisons.

## Weather (Current)
- Daily/weekly reports fetch external weather via Open-Meteo using `config/reporting.json` location values.
- Data includes sunrise/sunset plus hourly fields like outside temp/humidity, precipitation, cloud cover, wind.
- Weather is cached on disk per day to reduce API calls and keep reports fast.

## Home Assistant Integration
Not implemented in the current (main) codebase.
Planned in `Serav1/future-features.md` and `Serav1/panel-redesign-spec.md`.

## API (Selected)
- `GET /api/status`: full status payload for UI.
- `POST /api/actuator/<name>`: manual on/off (+ seconds).
- `POST /api/emergency_stop`: all OFF.
- `GET/POST /api/config`: channels + sensors + automation + settings.
- `POST /api/settings`: safe mode + limits + automation.
- `GET /api/sensor_log`: log data and CSV export.
- `GET /api/updates`: UI updates feed.
- `POST /api/lcd`: LCD config + lines.

## Environment Variables (Selected)
- `SIMULATION_MODE`, `DISABLE_BACKGROUND_LOOPS`, `ADMIN_TOKEN`.
- `LIGHT_CHANNEL_NAME`, `FAN_CHANNEL_NAME`, `PUMP_CHANNEL_NAME`.
- `DHT22_GPIO`, `BH1750_ADDR`.

## Known Limitations (Current)
- Single light/fan/heater/pump assumed in automation.
- Fixed sensor list (DHT22/DS/BH/ADS).
- Sensor log schema is fixed to current sensors.
- No zone/kat abstraction in UI or config.
- LCD template tokens are limited to global sensors only.
- `sensor_log` tek tablo; Serav1’de key/value telemetri tablosu eklenmeli ve `sensor_log` kademeli olarak read-only’ye alınmalı (hedef: yeni veri sadece telemetri tablosuna, raporlar her iki kaynaktan okuyacak geçiş dönemi).
- UI/JS ve `app.py` tek cihaz sabitlerine (LIGHT_CHANNEL_NAME, PUMP, tek heater) bağlı; refaktörden önce bu bağımlılıkların envanteri çıkarılmalı ve zone-first soyutlama ile yer değiştirme planlanmalı.

## Serav1 Geçiş Notları
- API’ler tek cihaz varsayımıyla tasarlandığı için `/api/status` ve `/api/config` yanıtları zone-first şemaya yumuşak geçiş için paralel alanlar gerektirir (eski alanları `deprecated` işaretleyip kalkış tarihi eklemek gerekiyor).
- `sensor_log` sabit kolonlu; Serav1’de metric/key-value şemasına geçerken mevcut tabloyu okuyan raporlar korunmalı, yazma yeni telemetri tablosuna alınmalı.
- Konfig (channels/sensors) tek sera için; zone katalog formatına göçerken mevcut roller `zone: "sera"` altında tutulmalı ve UI’de pin değişiklikleri “tüm kanallar OFF + SAFE MODE” davranışını korumalı.
- SAFE MODE, emergency stop ve süre limitleri bugün tek backend için var; Serav1’de ESP32 backend geldiğinde bu sinyallerin node komut/ACK yoluyla zorunlu uygulanması gerekiyor.
