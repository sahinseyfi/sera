# Panel Redesign Spec (Greenfield)

This is a full greenfield spec for the new panel, written as if the UI and
UX are being built from scratch. It includes data model, information
architecture, layouts, states, and detailed component behavior.

---

## 1. Goals
- Safety first: avoid unsafe toggles and accidental activations.
- Zone-first mental model: user thinks in SERA / KAT1 / KAT2 / FIDE.
- Fast scan: answer "what is happening now" in under 10 seconds.
- Changes are transparent: show cause/effect and recent actions.
- Future-proof sensors: DHT -> SHT swap without code changes.

## 2. Non-Goals
- Cloud multi-tenant management.
- External remote access without explicit admin setup.
- Advanced agronomy models beyond current thresholds.

## 3. Constraints
- Raspberry Pi 4, local network, GPIO/I2C/1-Wire.
- Optional per-zone ESP32 (ESP32-CAM) nodes over Wi‑Fi for sensors/cameras.
- Must operate safely when sensors are missing or stale.
- Minimal dependencies; keep performance light.

## 4. Terminology
- SERA: global environment.
- KAT1, KAT2: plant floors.
- FIDE: seedling box.
- CANOPY FAN: floor fan blowing over pots.
- BOX FAN: small circulation fan inside the seedling box.
- EXHAUST FAN: greenhouse vent fan to outside.

## 5. Information Architecture (Global Nav)
Desktop (top nav, prioritized by daily use)
1) Genel Bakış (okuma odaklı)
2) Zoneler (günlük operasyon)
3) Kontrol (manuel aksiyonlar, güvenlik önce)
4) Geçmiş (trend + kayıt + raporlar)
5) Ayarlar (ileri yapılandırma)

Mobile (bottom nav)
- Genel Bakış, Zoneler, Kontrol, Geçmiş, Diğer
- Diğer: Ayarlar, Raporlar, Yardım, Güncellemeler ve cihaz araçlarını içerir (Donanım, LCD, Notlar)

Notes:
- Genel Bakış sadece özet ekranıdır.
- Zoneler operasyon merkezidir.
- Kontrol sayfası güvenlik odaklı manuel kontrol sunar.
- Üst menü küçük kalır; diğer her şey Diğer veya Ayarlar/Geçmiş altında yaşar.

## 6. Data Model (Front-End)

### 6.1 Zoneler
```
Zone = {
  id: 'sera' | 'kat1' | 'kat2' | 'fide',
  label: string,
  sensors: [sensorId],
  actuators: [actuatorId]
}
```

Note:
- `id` is a stable internal identifier (lowercase).
- `label` is what the UI shows (e.g., `SERA`, `KAT1`, `KAT2`, `FIDE`).
- Default node_id values: `kat1-node`, `kat2-node`, `fide-node` (optional `sera-node`).

### 6.2 Sensors
```
Sensor = {
  id: string,
  label: string,
  kind: 'dht11' | 'dht22' | 'sht31' | 'bh1750' | 'ldr' | 'ads1115',
  zone: ZoneId,
  purpose: 'temp_hum' | 'lux' | 'soil',
  node_id?: string,        // if provided, sensor is read from a remote ESP32 node
  gpio?: number,
  i2c_addr?: string,
  ads_channel?: 'ch0' | 'ch1' | 'ch2' | 'ch3',
  status: 'ok' | 'simulated' | 'missing' | 'error' | 'disabled',
  last_value: object,
  calibration?: { scale: number, offset?: number }
}
```

### 6.3 Actuators
```
Actuator = {
  id: string,
  label: string,
  zone: ZoneId,
  role: 'heater' | 'fan_canopy' | 'fan_box' | 'fan_exhaust' | 'light' | 'pump',
  backend: 'pi_gpio' | 'esp32' | 'homeassistant',
  node_id?: string,        // required when backend = 'esp32'
  gpio_pin?: number,
  ha_entity_id?: string,
  active_low: boolean,
  supports_pwm?: boolean,
  duty_pct?: number,       // 0..100 (used when supports_pwm = true)
  power_w?: number
}
```

### 6.4 Automation
```
Automation = {
  zone: ZoneId,
  type: 'lux' | 'heater' | 'fan_exhaust' | 'pump',
  enabled: boolean,
  thresholds: object,
  schedule: object,
  safety: object,
  sensor_id: string
}
```

### 6.5 Notifications
```
NotificationConfig = {
  enabled: boolean,
  level: 'info' | 'warning' | 'error',
  cooldown_seconds: number,
  telegram_enabled: boolean,
  email_enabled: boolean
}
```

### 6.6 Telemetry / Logs
```
TelemetryPoint = {
  ts: number,              // unix seconds
  zone: ZoneId,
  metric: string,          // e.g. 'temp_c', 'rh_pct', 'lux', 'soil_raw', 'soil_pct'
  value: number,
  unit?: string,
  source?: string,         // sensorId or actuatorId
  quality?: 'ok' | 'suspect' | 'invalid'
}

EventLog = {
  ts: number,
  level: 'info' | 'warning' | 'error',
  category: string,        // 'sensor' | 'actuator' | 'automation' | 'system'
  message: string,
  meta?: object
}
```

### 6.7 Location & Weather
```
LocationConfig = {
  label: string,           // e.g. "Silivri Sera"
  lat: number,
  lon: number,
  tz: string
}

WeatherSnapshot = {
  status: 'ok' | 'missing' | 'disabled',
  source: string,          // e.g. 'open-meteo'
  updated_ts?: number,
  current?: {
    temp_c?: number,
    rh_pct?: number,
    precipitation_mm?: number,
    cloud_cover_pct?: number,
    wind_ms?: number
  },
  daily?: {
    sunrise?: string,
    sunset?: string
  }
}
```

### 6.8 Nodes (ESP32)
```
Node = {
  id: string,              // e.g. 'kat1-node'
  zone: ZoneId,
  kind: 'esp32',
  ip?: string,             // static IP recommended
  capabilities: {
    i2c: boolean,
    adc: boolean,
    camera: boolean
  },
  status: 'ok' | 'missing' | 'error',
  last_seen_ts?: number
}
```

### 6.9 Cameras / Vision
```
Camera = {
  id: string,
  zone: ZoneId,
  node_id: string,
  kind: 'esp32cam',
  snapshot_url?: string,   // node-local URL; panel may proxy it
  last_snapshot_ts?: number,
  last_result?: {
    label: string,         // e.g. 'ok' | 'needs_water' | 'mold_risk'
    confidence: number
  }
}
```

## 7. Global UI Layout
- Top bar: brand + SAFE MODE indicator + data age.
- Secondary strip: last update time, stale warning, alert count.
- Content width: max 1200px, centered.
- Mobile: single column, tabs for zones.

## 8. Genel Bakış (Sadece Okuma)

### 8.1 Sections
1) System Summary (safe mode, data age, alerts)
2) Outdoor Weather (location-based, cached)
3) Global Sensors (SERA temp/hum)
4) Zoneler özeti (KAT1 / FIDE / KAT2)
5) Active Automation Summary
6) Alerts (last 5)

### 8.2 Zone Snapshot Cards
- Header: zone label + health badge.
- Body: main metrics per zone.
- Footer: quick actuator states (Light/Fan/Heater).

## 9. Zoneler Sayfası (Operasyon Merkezi)

### 9.1 Layout
- Desktop: three blocks side-by-side if space, else two rows.
- Mobile: tabs (KAT1, FIDE, KAT2).

### 9.2 Per Zone Content
- Metrics card: temp/hum or soil/lux depending on zone.
- Actuator card: states + last change reason.
- Mini trend chart (last 6h) for the main metric.
- Optional: latest camera snapshot + last vision result.

### 9.3 Zone Notes
- Include short info text so user knows what each zone represents.

## 10. Kontrol Sayfası (Manuel Kontrol)

### 10.1 Güvenlik
- SAFE MODE blocks all manual control.
- Heater/pump require confirmation + countdown.
- Enforce dependencies (e.g., FIDE heater ON requires FIDE box fan ON, if present).
- Display actuator cooldown if any.
- Manuel komutlar güvenliyse süreli çalıştırmayı destekler (örn. “15 dakika çalıştır”).

### 10.2 Gruplama
- Group by zone, then by role.
- Each actuator card shows:
  - Current state
  - Last change + reason
  - Quick ON/OFF and duration (if allowed)
  - Light brightness slider (if actuator supports PWM)

### 10.3 Manuel Override Oturumları
- Any manual action can set a temporary override TTL (e.g., 5/15/30 minutes).
- While override is active, automation must not fight the manual state for that actuator.
- UI must show remaining override time and provide a “cancel override” action.

## 11. Otomasyon Sayfası
Bu alan Ayarlar altında bir alt sayfadır: **Ayarlar > Otomasyon**.

### 11.1 Lux Automation (Per Zone)
- Sensor: select LDR or BH1750.
- Thresholds: lux_ok, lux_max.
- PWM dimming behavior toggles:
  - Duty min/max (%)
  - Max duty step per update (%)
  - Measurement delay (seconds)
  - Min update interval (seconds)
- Target minutes per day (optional).

### 11.2 Heater Automation
- SERA heater uses a configurable sensor (default: SERA zone sensor if present).
- FIDE heater uses FIDE sensor.
- If a FIDE box fan exists, require it while the FIDE heater is ON.
- Night mode toggle + schedule.

### 11.3 Exhaust Fan Automation
- Based on humidity or temperature.
- Only applies to EXHAUST FAN.

### 11.4 Canopy Fan Always On
- Per zone toggle: "Always ON".
- If enabled and SAFE MODE off, fan stays ON unless manual override.

## 12. Sensörler Sayfası
Bu alan Ayarlar altında bir alt sayfadır: **Ayarlar > Sensörler & Kalibrasyon**.

### 12.1 Sensor List
- Table or cards with:
  - Label, kind, zone, connection (gpio/i2c/ch)
  - Status + last value
  - Edit button

### 12.2 Sensor Editor
- Change kind (DHT11/22/SHT31).
- Change gpio/i2c address.
- Change ADS channel mapping.

### 12.3 LDR Calibration Tool
- Step 1: Place LDR next to BH1750.
- Step 2: Capture BH1750 and LDR raw.
- Step 3: Compute scale factor and save.
- Step 4: Confirm converted lux value.

## 13. LCD / Ekran Sayfası
Bu alan Ayarlar altında bir alt sayfadır: **Ayarlar > LCD / Ekran**.

### 13.1 LCD Ayarları
- Enable/disable, mode (auto/template/manual), address, port, expander, charmap.

### 13.2 Template Editor
- 4x20 line editor with token buttons.
- Zone-aware tokens (sera/kat1/kat2/fide).
- Preview of the resolved output.

### 13.3 Rotation
- Optional auto-rotate between zone views.

## 14. Geçmiş & Trendler Sayfası
Bu alan üst seviye **Geçmiş** sayfasıdır.

### 14.1 Filters
- Zone selector
- Metric selector
- Time range (24h, 7d)
- Log type selector (sensor log / event log / actuator log)

### 14.2 Chart
- Single main chart with legend.
- Tooltip shows value + timestamp.
- Interactive features:
  - Zoom/pan.
  - Range selection (brush) to focus on a window.
  - Multi-series overlay (compare two metrics or zones).
  - Event markers: actuator actions, alerts, automation state changes.
- Performance requirements:
  - Server-side aggregation/downsampling (1m/5m/15m/1h).
  - Cache for common ranges (last 1h/6h/24h).

### 14.3 Export
- CSV download for selected filter.
- Quick links: last 1h / 6h / 24h.

## 15. Raporlar Sayfası
Bu alan **Geçmiş** içinde bir bölüm olarak ele alınır (tab/route): **Geçmiş > Raporlar**.

### 15.1 Günlük Özet
- One page per day with zone summary.
- "Top 3" highlights: good, warning, action.

### 15.2 Weekly Summary
- Trends and improvements per zone.

## 16. Updates Page
Bu alan üst seviye değildir; **Ayarlar > Güncellemeler & Notlar** altında yer alır.
- User-friendly changelog from config (`config/updates.json`).
- Latest update date shown at top.

## 17. Notes Page
Bu alan üst seviye değildir; **Ayarlar > Güncellemeler & Notlar** altında yer alır.
- Curated improvement ideas grouped by topic.
- Acts as a lightweight roadmap for internal use.

## 18. Ayarlar Sayfası
Ayarlar alt sayfalar için bir kabuktur. Varsayılan görünüm en sık kullanılan kontrolleri öne alır.

### 18.1 Ayarlar Bölümleri (Önerilen Sıra)
1) Safety & Limits (SAFE MODE, pump/heater max, heater cutoff, dependencies)
2) Automation (heater, exhaust fan, lux, pump)
3) Sensors & Calibration (DHT/SHT, ADS1115 map, LDR calibration, DS18 enable)
4) Location & Weather (lat/lon/tz, geocoding search, cache status)
5) Devices & Channels (GPIO/HA mapping, roles, zones)
6) Notifications (Telegram/Email enable, severity, cooldown, test send)
7) Backup & Retention (export/import, retention policy, manual cleanup)
8) LCD / Display
9) Integrations (Home Assistant status, mapping hints)
10) Updates & Notes
11) Help / FAQ
12) System (restart, version, diagnostics)

Devices & Channels requirements:
- GPIO pin mapping must be editable from the panel UI (e.g., move a channel from pin 16 to pin 15 without code changes).
- Applying a pin change should default the channel to OFF and require confirmation.

## 19. Notifications & Integrations
- Telegram + Email supported; show readiness in UI.
- Home Assistant channels supported with entity IDs and backend badge.

## 20. Visual Language
- Typography: clear, compact, with strong headings.
- Color: neutral background, strong accent for actions.
- Badges: ok/warn/error colors for quick scan.
- Avoid clutter; prefer 1-2 key metrics per card.

## 21. Responsiveness
- Mobile: tabs for zones + collapsible sections.
- Desktop: multi-column layout with fixed card heights.
- Charts scale down to 240px height on mobile.

## 22. Status & Error States
- Stale data banner when last update exceeds threshold.
- Sensor error badge on cards.
- Disabled sensors show muted UI and help text.
- Data quality states:
  - Sanity checks (min/max ranges, impossible values).
  - Spike/outlier detection (sudden jumps) marked as `suspect`.
  - Quarantine mode for repeatedly failing sensors; automation ignores quarantined data.
  - Clear UI explanation: what is ignored and which safety fallback is active.

## 23. Interaction Details
- Auto-refresh every 2-3 seconds for live pages.
- Manuel yenileme butonu bulunur.
- Confirm modals for critical actions.

## 24. API Contracts (Suggested)
- `GET /api/status`: include zones, sensors, actuators, automation summary.
- `GET /api/sensor_catalog`: list sensor definitions + status.
- `POST /api/sensors`: update sensor config.
- `POST /api/calibrate/ldr`: save LDR scale factor.
- `GET /api/trends`: unified trend data by zone/metric.
- `GET /api/nodes`: list ESP32 nodes + health/last seen.
- `POST /api/nodes`: edit node mapping (zone, ip, capabilities).
- `GET /api/camera/<zone>/snapshot`: proxy/cached snapshot from the zone node.
- `GET /api/camera/<zone>/latest_result`: last image processing result.
- `GET /api/weather`: cached current + daily summary for configured location.
- `GET /api/geocode`: search location (city/address) and return candidates (optional).
- `POST /api/location`: update location config (label/lat/lon/tz).
- `GET /api/updates`: UI updates feed.
- `POST /api/notifications/test`: test send for Telegram/Email.
- `POST /api/actuator/<id>`: PWM için `duty_pct` destekle; `backend=esp32` ise komut node kuyruğuna eklenir.
- `GET /api/backup` and `POST /api/backup/restore`: backup/restore.
- `POST /api/lcd`: LCD config + template lines.

## 25. Migration Notes
- Maintain backward compatibility for old config keys where possible.
- Provide a one-time mapping of existing channels to zones.

## 26. Future-Proofing Checklist
- Catalog-first config: sensors, actuators, and zones are defined in a single catalog with metadata.
- Config versioning: store `config_version` and run migrations on load.
- Generic telemetry log: avoid fixed columns; use metric key/value rows or JSON blobs.
- Rule-driven automation: add a rule engine instead of hard-coded flows.
- Schema-driven UI: render forms from capability metadata, not hard-coded inputs.
- Unified calibration: scale/offset/polynomial for all analog sensors (LDR, soil).
- Safety policy engine: one place for max-on, min-off, dependencies, stale fallback.
- Zone templates: create a zone from a template (light/fan/soil/BH1750) in one action.
- Integration adapters: GPIO/HA/MQTT/Webhook behind a common interface.
- Diagnostics page: I2C scan, HA status, last error, uptime, and data age.
- Notification rules: per-zone alert rules, quiet hours, daily digest.
- Audit and rollback: track config edits with who/when + allow rollback.

## 27. ESP32 Node Telemetry / Command Protokolü
- **Transport**: ESP32 düğümleri belirli aralıklarla Raspberry Pi’ye `POST /api/telemetry` (JSON) gönderir; Pi düğüme bekleyen komutları `GET /api/node_commands?node_id=<id>&since=<ts>` ile sunar. İletişim LAN içi, TLS isteğe bağlı, en azından paylaşılan bir `node_token` ile auth yapılır.
- **Telemetri payload** (örnek):
  ```
  {
    "node_id": "kat1-node",
    "zone": "kat1",
    "ts": 1712345678,
    "sensors": [
      {"id": "kat1-temp", "metric": "temp_c", "value": 24.1, "quality": "ok"},
      {"id": "kat1-rh", "metric": "rh_pct", "value": 52.3, "quality": "ok"},
      {"id": "kat1-lux", "metric": "lux", "value": 1800, "quality": "ok"},
      {"id": "kat1-soil", "metric": "soil_raw", "value": 17200, "quality": "ok"}
    ],
    "status": {"uptime_s": 12345, "fw": "0.1.0", "last_snapshot_ts": 1712345600}
  }
  ```
- **Frekans ve TTL**: varsayılan 5–10 sn heartbeat; Pi 15 sn (konfigürable) içinde telemetri gelmezse düğümü `missing` işaretler, sensörleri `missing/suspect` olarak işaretler ve ilgili otomasyonlar güvenli moda geçer.
- **Komutlar**: Pi, admin tarafında `POST /api/node_commands` ile komut kuyruğunu doldurur ve düğüm `GET /api/node_commands` ile çeker. Komut örneği: `{"cmd_id": "...", "actuator_id": "...", "action": "set_state"|"set_pwm", "state": "on"|"off", "duty_pct": 0-100, "ttl_s": 30}`. Düğüm uyguladıktan sonra `POST /api/telemetry` içinde `acks: ["cmd_id"]` döner. TTL aşılırsa Pi komutu iptal eder; kuyruk sınırı dolarsa en eski komutlar düşer.
- **Güvenlik**: SAFE MODE açıkken Pi düğüme aktüatör komutu göndermemeli; emergency_stop tüm düğümlere `off` komutu gönderir ve beklenen ACK’leri takip eder. Düğüm boot olduğunda tüm çıkışlar **OFF** başlar ve ilk telemetriyi gönderir.
- **Hata durumları**: Telemetri eksik veya `quality="suspect"` ise ilgili otomasyon kendini bloklar ve UI’de “düğüm off/stale” uyarısı gösterir. Yeniden deneme/backoff: 3 hatadan sonra 30 sn bekle ve tekrar dene, her başarısız denemeyi event log’a yaz.
- **HTTP sözleşmesi**:
  - `POST /api/telemetry` yanıtları: `200` (ok), `207` (kısmi kabul + hatalar listesi), `400` (şema), `401`/`403` (node_token yok/hatalı), `429` (rate limit), `500` (beklenmedik). Cevap gövdesi: `{ "acks": [...], "errors": [{code, detail}] }`.
  - `GET /api/node_commands`: `200` (komut listesi), `204` (komut yok), `401`/`403` auth hatası, `429` (rate limit). Pi tarafında `since` parametresi boşsa son 30 sn içindeki komutlar döner.
  - `POST /api/node_commands`: `200` (ok, `cmd_id` döner), `400` (payload), `403` (admin/auth). Cevap: `{ "ok": true, "cmd_id": "...", "queue_size": 3, "dropped": ["old_id"] }`.
  - Hata kodu standardı: `code` değerleri sabit string (`invalid_sensor`, `stale`, `auth_failed`, `rate_limited`, `busy`); hepsi event log’a yazılır.
  - Rate limit/backpressure: düğüm ardışık `429` alırsa 30 sn bekler, Pi tarafı da node başına istek/saniye limitini kontrol eder ve loglar.
- **Keşif/yeniden bağlanma**: Düğüm IP değiştirirse token ile `POST /api/telemetry` kabul edilir ve Pi `node_id`→`last_ip` günceller; Pi’de opsiyonel ARP/I2C scan yok, tek güvenilir kimlik `node_id` + `node_token`. Firmware versiyonu `status.fw` üzerinden kontrol edilir, uyumsuz sürümlerde hata kodu `fw_incompatible` döner.
- **Alternatif kanal**: Push/WebSocket opsiyonel; varsayılan polling. WebSocket kullanılırsa aynı auth token’ı header’da taşır, komutlar stream ile iner, telemetri yine `POST /api/telemetry` olarak kalır (tek kaynak log).

## 28. Geçiş Planı (Mevcut Panel → Serav1)
- **API uyumluluğu**: Mevcut `/api/status`, `/api/config`, `/api/settings`, `/api/sensor_log` uçları korunur; yeni uçlar (örn. `/api/nodes`, `/api/trends`, `/api/sensors`) eklenir. Geçiş süresince `/api/status` hem yeni zone-first yapı (zones/sensors/actuators) hem de eski alanları (single light/pump/heater) döndürür; eski alanlar `deprecated` işareti ve kalkış tarihi ile döner.
- **Konfig migrasyonu**: `config/channels.json` ve `config/sensors.json` içeriği tek bir katalog yapısına taşınır (`zones`, `sensors`, `actuators`). İlk iterasyonda mevcut kanal/rol isimleri `zone: "sera"` altında tutulur; KAT1/KAT2/FIDE eklenince bu katalog genişler. Uygulama, eski dosyalar varsa okuyup yeni kataloğu üretir ve uyarı verir; yeni yazımlar yalnızca katalog formatını kalıcı yazar.
- **Veri katmanı**: Şu anki `sensor_log` (sabit kolon) yazmaya devam ederken yeni bir telemetri tablosu (metric key/value + zone) paralel açılır. Okumalar için öncelik: yeni telemetri tablosu; yoksa eski tablo. Downsampling önbellekleri yeni şemaya göre oluşturulur.
- **UI geçişi**: Mevcut UI çalışmaya devam eder; yeni zone-first UI sayfaları eklenirken eski UI rota/JS bundl’ı bir süre tutulur. Bayrak: `USE_NEW_UI=1` ile yeni sayfalar, aksi halde eski sayfalar gösterilir. Bu bayrak default `off`; simülasyonda açılarak regresyon testleri yapılır.
- **Güvenlik kontrolleri**: PIN değişiklikleri ve backend seçimi UI’den yapılınca tüm aktüatörler OFF’a çekilir ve SAFE MODE açılır; bu davranış her iki API şeması için de zorunlu kalır. Otomasyonlar, zone telemetrisine geçerken sensor-id değişikliklerinde bir kez `OFF + clear override` uygular.
  - Deprecation takvimi: Eski `/api/status` alanları 2 sürüm sonra kaldırılır (örn. v1.2’ye kadar `deprecated`, v1.3’te yok); bu takvim UI’da ve changelog’da belirtilir. Test matrisi: simülasyon (USE_NEW_UI=1/0) + gerçek donanım için smoke (SAFE MODE açık).

## 29. Konfig Kataloğu (Serav1 JSON Taslağı)
- Dosya: `config/catalog.json` (tek kaynak). İçerik:
  ```
  {
    "version": 1,
    "zones": [
      {"id": "sera", "label": "SERA"},
      {"id": "kat1", "label": "KAT1"},
      {"id": "kat2", "label": "KAT2"},
      {"id": "fide", "label": "FIDE"}
    ],
    "sensors": [
      {"id": "sera-temp", "zone": "sera", "kind": "sht31", "purpose": "temp_hum", "backend": "esp32", "node_id": "sera-node", "i2c_addr": "0x44"},
      {"id": "kat1-lux", "zone": "kat1", "kind": "bh1750", "purpose": "lux", "backend": "esp32", "node_id": "kat1-node", "i2c_addr": "0x23"},
      {"id": "kat1-soil", "zone": "kat1", "kind": "ads1115", "purpose": "soil", "backend": "esp32", "node_id": "kat1-node", "ads_channel": "ch0"}
    ],
    "actuators": [
      {"id": "kat1-light", "zone": "kat1", "role": "light", "backend": "esp32", "node_id": "kat1-node", "supports_pwm": true, "active_low": false},
      {"id": "kat1-fan", "zone": "kat1", "role": "fan_canopy", "backend": "esp32", "node_id": "kat1-node", "active_low": true},
      {"id": "exhaust", "zone": "sera", "role": "fan_exhaust", "backend": "pi_gpio", "gpio_pin": 16, "active_low": true}
    ]
  }
  ```
- Şema kuralları: `id` benzersiz; `zone` zorunlu; backend’e göre alanlar (pi_gpio → `gpio_pin`+`active_low`, esp32 → `node_id`, homeassistant → `ha_entity_id`). PWM destekleyenler `supports_pwm: true`, duty başlangıcı `duty_pct` ile tutulur.
- Migrasyon scripti: eski `channels.json` + `sensors.json` okunur, `zone: "sera"` altında katalog üretilir, `config/catalog.json` yazılır, eski dosyalar opsiyonel yedek olarak `config/legacy/` altına kopyalanır. Çalıştırma: `python3 scripts/migrate_catalog.py --dry-run` ile fark raporu, `--write` ile kalıcı yazım. Test: `make doctor` güncellenerek yeni şema doğrulanır ve eski dosya tutarsızlıkları için uyarı verir.
- Geri dönüş: `config/catalog.json.bak` tutulur; rollback için eski dosyalar geri taşınır ve servis restart öncesi `make doctor` çalıştırılır.
- Kapabilite/safety alanları: HA backend için `ha_entity_id` + `ha_domain` zorunlu; PWM aktüatörlerde `max_current_a`, `duty_step_max`, `requires_fan_dependency` gibi sınırlar katalogda tutulur. Tüm kritik aktüatörler (heater/pump) için `cooldown_s`, `max_on_s`, `max_daily_s` metadata olarak gelir ve runtime’da enforce edilir.

---

End of spec.
