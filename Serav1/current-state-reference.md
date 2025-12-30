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

### Dashboard
- Live sensor cards (DHT22, DS18B20, BH1750, ADS1115 raw channels).
- Summary row: safe mode, last data timestamp + age, alerts count, automation state.
- Automation status card with window, target minutes, override, block, min-off, last off reason.
- Automation badge legend (active, override, lux error, max lux, off).
- Charts: metric selector + 24h/7d range + CSV download.
- Chart footer: min/max/last/count/last update.
- Actuator state list (state, last change, reason).
- Alerts list (latest 5).
- Energy estimate (24h/7d totals + per-channel breakdown; note for timed-only channels).
- Sensor health list (last OK, offline duration, offline limit note).
- Event log (automation + manual events).

### Control
- Manual relay control with SAFE MODE gating.
- Emergency stop (all off).
- Pump/heater confirmation flow with countdown modal.
- Per-channel cooldown notes (pump, heater).
- Recent command list with reasons.

### Settings
- Admin token input + status (stored in browser).
- SAFE MODE toggle.
- Limits: pump max + cooldown, heater max + cutoff.
- Save button with saved status.
- Automation sections:
  - Lux (target minutes, lux OK/max, window, min on/off, manual override).
  - Heater (sensor choice, temp band, max/min, night mode, fan required).
  - Pump (soil channel, dry threshold, pulse, max daily, window, override).
  - Fan (RH high/low, max/min, night mode, periodic mode).
  - Soil calibration table with dry/wet quick capture buttons.
- Alert thresholds (offline, temp/hum high/low).
- Energy price settings (kWh tiers).

### Hardware
- Channel mapping table:
  - name, active, role, GPIO pin, active low.
  - description, power, quantity, total power, voltage, notes.
- Sensor settings:
  - DHT22 GPIO, BH1750 addr, ADS1115 addr, DS18B20 enable.
- Save action sets all channels OFF for safety.

### Logs
- Sensor log table with filter fields (from/to, limit, interval, order).
- Interval options: raw, 1, 5, 15, 30, 60 minutes.
- CSV export for the selected range.
- Log clear (SQLite only; CSV files remain).

### Reports
- Daily report: story summary, comparisons, progress bars, teaching cards.
- Weekly report: summary cards + weekly chart + daily breakdown table.
- Beginner mode toggle hides expert-only details.
- Weather warning banner when external data is missing (if applicable).

### LCD
- I2C LCD settings (enable, mode, address, port, expander, charmap, size).
- Line editor (4x20) with counters.
- Clear lines and template preset buttons.
- Token buttons insert into selected line.
- Preview of resolved output.
- LCD mode: auto / template / manual.

### Updates
- Changelog list read from `config/updates.json` via `/api/updates`.
- Last update date shown at top.
- Empty state message when no updates exist.

### Notes
- Static improvement suggestions grouped by topic.
- Data is rendered server-side and not user-editable.

### Help / FAQ
- FAQ sections for dashboard, control, settings, logs, troubleshooting.
- Explains OK/SIM/HATA/YOK status badges and stale data behavior.

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
