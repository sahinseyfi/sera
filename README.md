# AKILLI SERA – Momo & Nova Station

Flask tabanlı Raspberry Pi 4 kontrol paneli. Sensörleri izler, röleleri güvenli biçimde yönetir, lux tabanlı ışık otomasyonuna altyapı sağlar. Varsayılan mod SAFE MODE (yalnız izleme, açma kapama kilitli).

## Dizim
- `app.py`: Flask app, API, otomasyon, GPIO katmanı (SIMULATION_MODE destekli).
- `templates/`, `static/`: Dashboard, kontrol, ayar, pin mapping sayfaları.
- `config/channels.json`: Röle/gpio mapping (active-low desteği).
- `config/panel.json`: Limitler + otomasyon + uyarı eşikleri (kalıcı panel ayarları).
- `config/catalog.json`: Zone/sensör/aktüatör kataloğu (Serav1 geçişi).
- `config/notifications.json`: Bildirim ayarları (Telegram token config’te tutulmaz; env var ile).
- `config/retention.json`: Veri saklama/temizlik (log retention) ayarları.
- `config/schema/`: Config dosyaları için JSON Schema doğrulamaları.
- `data/sera.db`: Aktüatör + sensör logları (SQLite).
- `data/sensor_logs/`: Günlük sensör CSV logları (git dışı).
- `systemd/sera-panel.service`: Servis örneği.
- `tests/`: SIMULATION_MODE ile temel API kontrolleri.
- `scripts/doctor.py`: Config + şema doğrulama aracı.
- `sera_panel/`: Alternatif giriş (launcher) ve eski sürüm.
- `sera_projesi/`: Eski/alternatif giriş noktası.

## Kurulum
```bash
sudo apt-get update && sudo apt-get install -y python3-venv python3-pip i2c-tools
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Donanımda: pip install --no-binary :all: Adafruit-DHT RPi.GPIO
```
Alternatif: `make install` (venv + requirements).
Donanımda I2C/1-Wire açık olsun (`sudo raspi-config`). SIMULATION_MODE=1 ile donanım olmadan çalışır.

## Çalıştırma (geliştirme)
```bash
# simülasyon
SIMULATION_MODE=1 FLASK_ENV=development python app.py
# gerçek donanım
python app.py
```
Giriş: `http://<pi-ip>:5000`. SAFE MODE başta açık; Ayarlar sekmesinden kapatabilirsiniz. Test paneli: `http://<pi-ip>:5000/test`. `ADMIN_TOKEN` tanımlarsanız admin endpointlerinde `X-Admin-Token` header’ı zorunlu olur.

## Panel Sayfaları
- `Dashboard`: Anlık sensörler, grafikler, uyarılar, otomasyon özeti.
- `Kontrol`: Röleleri güvenli şekilde aç/kapat, pompa süreli çalıştır.
- `Ayarlar`: SAFE MODE, limitler, otomasyon, bildirimler ve veri saklama.
- `Pin Mapping`: Kanal → GPIO eşlemesi.
- `Loglar`: Sensör kayıtlarını listele, CSV indir.
- `Yardım/SSS`: Sayfa açıklamaları ve sık sorulanlar.

## Sensör Logları
- SQLite: `data/sera.db` içinde `sensor_log` tablosu.
- CSV: `data/sensor_logs/sensor_log_YYYY-MM-DD.csv` günlük dosyalar.
- Varsayılan log aralığı: `SENSOR_LOG_INTERVAL_SECONDS = 10`.
- Loglar sayfası SQLite verisini gösterir; CSV indir aynı veriyi dışa aktarır.

## Donanım Test Scriptleri
- `dht_test.py`: DHT22 sıcaklık/nem okuma testi.
- `bh_test.py`: BH1750 lux okuma testi.
- `i2c_sensors_test.py`: BH1750 + ADS1115 I2C testi.
- `lcd_test.py`: 20x4 I2C LCD kısa yazma testi.
- `sensors_test.py`: BH1750 + DHT22 birleşik okuma.
- `moisture_raw.py`: ADS1115 raw toprak nemi okuma.
- `moisture_log.py`: ADS1115 toprak nemi CSV loglama (yerel dosya).
- `relay_test.py`: Röle manuel test sıralaması (pompa hariç).
- `sera_panel/relay_click_test.sh`: Röle tıklama testi.
- `sera_panel/relay_polarity_test.sh`: Röle aktif-low/aktif-high kontrolü.

## API
- `GET /api/status` → sensörler, aktüatör durumu, safe_mode, limitler, otomasyon, bildirim/retention durumları.
- `POST /api/actuator/<name>` body: `{"state":"on|off","seconds":optional}`; SAFE MODE açıkken 403. Pompa: `seconds` zorunlu, `pump_max_seconds` + `pump_cooldown_seconds` uygulanır. Isıtıcı `heater_max_seconds` ile sınırlı. `catalog.json` içinde `backend=esp32` ve `supports_pwm` olan aktüatörlerde `duty_pct` ile komut kuyruğa eklenir.
- `POST /api/emergency_stop` → tüm kanalları OFF (SAFE MODE olsa da çalışır). ESP32 aktüatörler için off komutları kuyruğa eklenir.
- `POST /api/settings` → `{safe_mode, limits, automation, alerts, notifications, retention}` admin korumalı.
- `GET/POST /api/config` veya `/api/pins` → kanal mapping oku/yaz; mapping değişince tüm kanallar OFF.
- `GET /api/sensor_log` → sensör log kayıtları (JSON/CSV).
- `POST /api/sensor_log/clear` → sensör loglarını temizle (admin).
- `POST /api/notifications/test` → Telegram test bildirimi (admin).
- `POST /api/maintenance/retention_cleanup` → retention temizliği (admin).
- `POST /api/telemetry` → ESP32 telemetri payload kabul eder (node_token ile).
- `GET /api/node_commands` → ESP32 komut kuyruğunu okur (node_token ile, `since` destekli).
- `POST /api/node_commands` → admin tarafı ESP32 komutu kuyruğa ekler.
- `GET /api/nodes` → ESP32 node durumları (health + queue_size).

## systemd (örnek)
```bash
sudo cp systemd/sera-panel.service /etc/systemd/system/
sudo cp systemd/sera-panel.env.example /etc/sera-panel.env
# /etc/sera-panel.env içinde ADMIN_TOKEN vb. değerleri ayarla
sudo chmod 600 /etc/sera-panel.env
sudo systemctl daemon-reload
sudo systemctl enable --now sera-panel.service
```
`WorkingDirectory` ve `ExecStart` yollarını kendi klasörünüze göre güncelleyin; `Environment` değişkenleriyle SAFE MODE / token / simülasyon ayarlayın.

## Test
```bash
make test
# veya:
# SIMULATION_MODE=1 DISABLE_BACKGROUND_LOOPS=1 pytest -q
```

## Konfig doğrulama (önerilen)
```bash
make doctor
# veya:
# python3 scripts/doctor.py
```

## Ortam Değişkenleri
- `SIMULATION_MODE=1`: Donanım olmadan simülasyon.
- `DISABLE_BACKGROUND_LOOPS=1`: Sensör/otomasyon thread’lerini kapatır.
- `USE_NEW_UI=1`: Serav1 yeni arayüzü (Overview/Zones/Control/History/Settings + More) aktif eder.
- `ADMIN_TOKEN`: Admin endpointleri için token.
- `LIGHT_CHANNEL_NAME`, `FAN_CHANNEL_NAME`, `PUMP_CHANNEL_NAME`: Otomasyon için kanal override.
- `DHT22_GPIO`, `BH1750_ADDR`: Donanım adres/pin override.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: Telegram bildirimleri için (opsiyonel).
- `NODE_TOKENS`: ESP32 node auth listesi (`node_id:token,node2:token2`).
- `NODE_RATE_LIMIT_SECONDS`: `/api/telemetry` rate limit (sn).
- `NODE_COMMAND_RATE_LIMIT_SECONDS`: `/api/node_commands` rate limit (sn).
- `NODE_COMMAND_TTL_SECONDS`: Komut TTL (sn).
- `NODE_COMMAND_MAX_QUEUE`: Node komut kuyruğu sınırı.
- `NODE_STALE_SECONDS`: Node/sensör stale eşiği (sn).

## Güvenlik & Güvenli Varsayılanlar
- Uygulama açılışında tüm aktüatörler OFF; active-low röleler desteklenir.
- Sensör okumaları 15s’ten eskiyse pompa/ısıtıcı otomatik OFF ve uyarı.
- Öncelik: Güvenlik > Manuel > Otomasyon; SAFE MODE kontrolü kilitler, acil durdurma her zaman çalışır.
