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
- Dashboard: live sensors, summary, automation status, charts, alerts, energy, health.
- Control: safe manual relay control + emergency stop.
- Settings: safe mode, limits, automation rules, alerts, notifications, retention.
- Hardware: channel mapping and sensor config.
- Logs: sensor log table + CSV download.
- Reports: daily/weekly summaries.
- LCD: I2C LCD config and template tokens.
- Help/FAQ and Notes.

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
- `config/sensors.json`: DHT22 GPIO, BH1750 addr, ADS1115 addr, DS18B20 enabled.
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

## Environment Variables (Selected)
- `SIMULATION_MODE`, `DISABLE_BACKGROUND_LOOPS`, `ADMIN_TOKEN`.
- `HA_BASE_URL`, `HA_TOKEN`, `HA_TIMEOUT_SECONDS`, `HA_SYNC_INTERVAL_SECONDS`.
- `LIGHT_CHANNEL_NAME`, `FAN_CHANNEL_NAME`, `PUMP_CHANNEL_NAME`, `HEATER_CHANNEL_NAME`.
- `DHT22_GPIO`, `BH1750_ADDR`.
- Email/Telegram notification env vars.

## Known Limitations (Current)
- Single light/fan/heater/pump assumed in automation.
- Fixed sensor list (DHT22/DS/BH/ADS).
- Sensor log schema is fixed to current sensors.
- No zone/kat abstraction in UI or config.
