# AKILLI SERA – Momo & Nova Station

Flask tabanlı Raspberry Pi 4 kontrol paneli. Sensörleri izler, röleleri güvenli biçimde yönetir, lux tabanlı ışık otomasyonuna altyapı sağlar. Varsayılan mod SAFE MODE (yalnız izleme, açma kapama kilitli).

## Dizim
- `app.py`: Flask app, API, otomasyon, GPIO katmanı (SIMULATION_MODE destekli).
- `templates/`, `static/`: Dashboard, kontrol, ayar, pin mapping sayfaları.
- `config/channels.json`: Röle/gpio mapping (active-low desteği).
- `data/sera.db`: Aktüatör logları (SQLite).
- `systemd/sera-panel.service`: Servis örneği.
- `tests/`: SIMULATION_MODE ile temel API kontrolleri.

## Kurulum
```bash
sudo apt-get update && sudo apt-get install -y python3-venv python3-pip i2c-tools
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Donanımda: pip install --no-binary :all: Adafruit-DHT RPi.GPIO
```
Donanımda I2C/1-Wire açık olsun (`sudo raspi-config`). SIMULATION_MODE=1 ile donanım olmadan çalışır.

## Çalıştırma (geliştirme)
```bash
# simülasyon
SIMULATION_MODE=1 FLASK_ENV=development python app.py
# gerçek donanım
python app.py
```
Giriş: `http://<pi-ip>:5000`. SAFE MODE başta açık; Ayarlar sekmesinden kapatabilirsiniz. Test paneli: `http://<pi-ip>:5000/test`. `ADMIN_TOKEN` tanımlarsanız admin endpointlerinde `X-Admin-Token` header’ı zorunlu olur.

## API
- `GET /api/status` → sensörler, aktüatör durumu, safe_mode, limitler, otomasyon.
- `POST /api/actuator/<name>` body: `{"state":"on|off","seconds":optional}`; SAFE MODE açıkken 403. Pompa: `seconds` zorunlu, `pump_max_seconds` + `pump_cooldown_seconds` uygulanır. Isıtıcı `heater_max_seconds` ile sınırlı.
- `POST /api/emergency_stop` → tüm kanalları OFF (SAFE MODE olsa da çalışır).
- `POST /api/settings` → `{safe_mode, limits, automation}` admin korumalı.
- `GET/POST /api/config` veya `/api/pins` → kanal mapping oku/yaz; mapping değişince tüm kanallar OFF.

## systemd (örnek)
```bash
sudo cp systemd/sera-panel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sera-panel.service
```
`WorkingDirectory` ve `ExecStart` yollarını kendi klasörünüze göre güncelleyin; `Environment` değişkenleriyle SAFE MODE / token / simülasyon ayarlayın.

## Test
```bash
SIMULATION_MODE=1 DISABLE_BACKGROUND_LOOPS=1 pytest -q
```

## Güvenlik & Güvenli Varsayılanlar
- Uygulama açılışında tüm aktüatörler OFF; active-low röleler desteklenir.
- Sensör okumaları 15s’ten eskiyse pompa/ısıtıcı otomatik OFF ve uyarı.
- Öncelik: Güvenlik > Manuel > Otomasyon; SAFE MODE kontrolü kilitler, acil durdurma her zaman çalışır.
