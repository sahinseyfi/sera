# Sprint 00 Inventory and Risk Map (Serav1)

## Scope
- Objective: list current single-zone assumptions and the files they live in.
- Scope confirmation: zone-first UI + multi-zone sensors/actuators + ESP32 nodes + telemetry + safe-mode gating.

## Single-zone dependencies (current)
### Backend (Python)
- `app.py`: env vars assume one light/fan/pump channel (`LIGHT_CHANNEL_NAME`, `FAN_CHANNEL_NAME`, `PUMP_CHANNEL_NAME`). `app.py:134` to `app.py:139`.
- `app.py`: `SensorManager` reads fixed sensors (`dht22`, `ds18b20`, `bh1750`, `soil`) with no zone id. `app.py:292`.
- `app.py`: `AutomationEngine` assumes single light/fan/heater/pump and uses global thresholds. `app.py:846`.
- `app.py`: `api_status_payload` returns a single `sensor_readings` object and a single `automation_state`. `app.py:3087`.
- `app.py`: DB schema is fixed columns in `sensor_log` (dht/ds/lux/soil). `app.py:2355`.
- `app.py`: `/api/sensor_log` queries fixed columns. `app.py:3174`.
- `app.py`: safety/fault handling is keyed to a single pump/heater (`sensor_faults` has only `pump` and `heater`). `app.py:1786`.
- `app.py`: manual actuation safety uses actuator name includes `PUMP`/`HEATER` for limits, cooldown, cutoff. `app.py:2896`.
- `app.py`: stale sensor fail-safe turns off only `PUMP`/`HEATER` by name. `app.py:2884`.

### Config
- `config/sensors.json`: single DHT22/BH1750/ADS1115/DS18B20 settings and LCD tokens.
- `config/panel.json`: single automation and alerts keys (no per-zone sections).
- `config/channels.json`: roles exist, but no zone mapping.

### Reporting
- `reporting.py`: reports read from fixed `sensor_log` columns and compute a single indoor summary. `reporting.py:224`.
- `templates/reports_daily.html`: uses `report.indoor.*` (single indoor model).
- `templates/reports_weekly.html`: uses `report.summary` and single indoor rollups.

### Frontend (templates + JS)
- `static/main.js`: `HISTORY_METRICS` is fixed to dht/ds/lux/soil channels; UI expects `sensor_readings.dht22`, `bh1750`, `soil`. `static/main.js:1`.
- `static/main.js`: control page treats pump/heater by name (`PUMP`/`HEATER`) for lock, cooldown, and forced duration. `static/main.js:595`.
- `templates/dashboard.html`: cards and chart selectors are fixed to DHT22/DS18B20/BH1750/ADS1115.
- `templates/settings.html`: automation sections are single-instance (lux/heater/pump/fan).
- `templates/hardware.html`: sensor inputs are single DHT/BH/ADS/DS fields.
- `templates/lcd.html`: tokens are global only (`{temp}`, `{hum}`, `{lux}`, `{soil_pct}`, `{soil_raw}`, `{ds_temp}`).

## Risk map (Serav1 impact)
- High: `AutomationEngine` logic, actuator control, SAFE MODE gating, pump/heater limits.
- Medium: DB schema migration (`sensor_log` -> telemetry), `/api/status` compatibility, UI JS refactor.
- Low: text and doc updates.

## Notes / decisions needed
- Define initial zone mapping for existing channels (likely `zone: "sera"`).
- Define how history metrics become zone-scoped (UI selector and API format).
- Confirm report model: single indoor vs per-zone report outputs.
