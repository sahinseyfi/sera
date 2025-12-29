# Current State Reference - AKILLI SERA Panel

This document summarizes the current state of the codebase and runtime behavior
as a reference before the upcoming redesign.

## Scope
- Main panel lives in repo root (`app.py`, `templates/`, `static/`).
- `sera_panel/` is legacy/test content.
- Raspberry Pi 4 + Flask + GPIO/HA control.

## High-Level Architecture
- Flask app in `app.py`.
- UI templates in `templates/` and JS in `static/main.js`.
- Hardware abstraction for GPIO and Home Assistant.
- Sensor manager reads DHT22, DS18B20, BH1750, ADS1115.
- Automation engine handles lux, heater, pump, fan logic.

## UI Pages (Current)

### Dashboard
- Live sensor cards (DHT22, DS18B20, BH1750, ADS1115).
- Summary row: safe mode, last data timestamp, alerts, automation state.
- Automation status detail with window/override/min-off indicators.
- Charts (metric selector + 24h/7d, CSV download).
- Actuator state list (last change + reason).
- Alerts list (latest 5).
- Energy estimate (24h/7d, per-channel breakdown).
- Sensor health list (last OK/ offline).
- Event log (automation + manual actions).

### Control
- Manual relay control with SAFE MODE gating.
- Emergency stop (all off).
- Pump/heater confirmation flow + cooldown limits.
- Recent command list with reasons.

### Settings
- SAFE MODE + limits (pump/heater max, cooldown, heater cutoff).
- Automation rules:
  - Lux automation (target minutes, lux OK/max, window, min on/off, manual override).
  - Heater automation (sensor choice, temp band, min off, max on, night mode, fan required).
  - Pump automation (soil channel, dry threshold, pulse, daily limit, window).
  - Fan automation (RH high/low, max/min, night mode, periodic mode).
- Alert thresholds (offline, temp/hum high/low).
- Energy price settings (kWh pricing + threshold).
- Notifications (Telegram/Email enable, severity level, cooldown, test send status).
- Retention/cleanup settings + manual cleanup trigger.
- Backup/restore (JSON export/import).
- Admin token input and status.

### Hardware
- Channel mapping table:
  - name, role, backend (GPIO/HA), GPIO pin, active low, entity ID, power, quantity.
- Sensor settings:
  - DHT22 GPIO, BH1750 addr, ADS1115 addr, DS18B20 enable.
- Save action sets all channels OFF for safety.

### Logs
- Sensor log table with filter fields (from/to, limit, interval, order).
- CSV export for the selected range.
- Log clear with admin confirmation.

### Reports
- Daily report: story summary, comparisons, progress bars, teaching cards.
- Weekly report: summary cards + weekly chart + daily breakdown table.
- Beginner mode toggle on reports.

### LCD
- I2C LCD settings (enable, mode, address, port, expander, charmap, size).
- Line editor (4x20) with template tokens.
- Token list + preview output.
- LCD mode: auto / template / manual.

### Updates
- Changelog list read from `config/updates.json` via `/api/updates`.
- User-friendly summary text (non-technical).

### Notes
- Static improvement suggestions grouped by topic (safety, reliability, usability, observability).

### Help / FAQ
- FAQ sections for dashboard, control, settings, logs, troubleshooting.

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
- Telegram and Email supported (enable/disable, severity level, cooldown).
- Status checks for Telegram/Email readiness.
- Test send endpoint: `/api/notifications/test`.

## LCD (Current)
- LCD status is part of `/api/status` and can be updated via `/api/lcd`.
- Template tokens include temp/hum/lux/soil/ds_temp/pump/heater/time/safe.

## Safety
- SAFE MODE default ON: manual control locked, automation blocked.
- Emergency stop: all channels OFF.
- Pump/heater time limits + cooldowns.
- Sensor stale logic triggers alerts and safety behavior.

## Data/Logs
- SQLite database: `data/sera.db`.
- `sensor_log` table (fixed columns for DHT/DS/Lux/Soil).
- Daily CSV logs in `data/sensor_logs/`.

## Config
- `config/channels.json`: channels with role, GPIO, active_low, HA entity.
- `config/sensors.json`: DHT22 GPIO, BH1750 addr, ADS1115 addr, DS18B20 enable, LCD settings.
- `config/notifications.json`: notification settings.
- `config/retention.json`: retention/cleanup settings.
- `config/updates.json`: UI updates feed.

## Home Assistant Integration
- Channels can be `backend: homeassistant` with `ha_entity_id`.
- HA base URL + token via env vars.
- Sync interval for HA state is configurable.

## API (Selected)
- `GET /api/status`: full status payload for UI.
- `POST /api/actuator/<name>`: manual on/off (+ seconds).
- `POST /api/emergency_stop`: all OFF.
- `GET/POST /api/config`: channels + sensors + automation + settings.
- `POST /api/settings`: safe mode + limits + automation.
- `GET /api/sensor_log`: log data and CSV export.
- `GET /api/updates`: UI updates feed.
- `POST /api/notifications/test`: notification test send.
- `GET /api/backup` and `POST /api/backup/restore`: backup/restore.
- `POST /api/retention/cleanup`: manual cleanup.
- `POST /api/lcd`: LCD config + lines.

## Environment Variables (Selected)
- `SIMULATION_MODE`, `DISABLE_BACKGROUND_LOOPS`, `ADMIN_TOKEN`.
- `HA_BASE_URL`, `HA_TOKEN`, `HA_TIMEOUT_SECONDS`, `HA_SYNC_INTERVAL_SECONDS`.
- `LIGHT_CHANNEL_NAME`, `FAN_CHANNEL_NAME`, `PUMP_CHANNEL_NAME`, `HEATER_CHANNEL_NAME`.
- `DHT22_GPIO`, `BH1750_ADDR`.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASS`, `EMAIL_FROM`, `EMAIL_TO`, `EMAIL_SMTP_TLS`.

## Known Limitations (Current)
- Single light/fan/heater/pump assumed in automation.
- Fixed sensor list (DHT22/DS/BH/ADS).
- Sensor log schema is fixed to current sensors.
- No zone/kat abstraction in UI or config.
- LCD template tokens are limited to global sensors only.
