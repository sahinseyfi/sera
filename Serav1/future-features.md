# Future Features Plan (Post-Refactor)

This document lists the next set of planned features after the redesign.
It is aligned with the decision log and the new zone-first UI.

## Zone Model
- Zones: SERA (global), KAT1, KAT2, FIDE.
- Every actuator and sensor is assigned to a zone.
- UI groups all controls and metrics by zone.

## Node Model (ESP32 per Zone)
- One ESP32 (ESP32-CAM) node per zone where practical (KAT1, KAT2, FIDE; optional SERA).
- Nodes handle local sensor reads (I2C + analog) and provide a camera snapshot/stream endpoint.
- Raspberry Pi polls/receives telemetry + images, stores them, and runs all automation + image processing.

## Sensors
- Temp/hum per zone via SHT31 (default) connected to the zone’s ESP32 node.
- Lux per zone via BH1750 connected to the zone’s ESP32 node.
- Soil moisture (capacitive) per floor connected to the floor’s ESP32 node.
- Note: ESP32‑CAM boards often have limited free ADC pins; if you need multiple analog sensors per node, add an I2C ADC (e.g., ADS1115) on that node.
- Keep DHT11/22 as optional legacy support only if needed.

## Lux and Light Control
- Per-zone PWM dimming light control (single channel per zone):
  - Increase/decrease duty cycle based on lux error, then re-measure after a short delay.
  - Use min/max duty, max step size, and a minimum update interval to avoid oscillation.
- Lux thresholds per zone.
- Safe measurement delay + cooldown rules between duty updates.

## Fans
- Exhaust fan automation only (based on humidity or rules).
- Canopy fans: on/off via relay; default ON with an explicit toggle in UI, SAFE MODE can force OFF.
- FIDE box fan (optional): default to running with the FIDE heater; optionally add an "Always ON" toggle.

## Heating
- Greenhouse heater uses a configurable sensor (default: SERA zone sensor if present).
- Seedling heater uses FIDE sensor.
- Heater sensor type is configurable from UI.

## Notifications
- Keep Telegram and Email support, add zone-specific alert rules.
- Quiet hours and daily digest options.
- Clear UI status for missing env vars.

## Weather & Location (User-Friendly)
- Weather is already used for reports (Open-Meteo); make it configurable from the UI.
- Add **Settings > Location & Weather**:
  - Search by city/address using Open-Meteo Geocoding API (no key).
  - Store `lat/lon/timezone` + a friendly label (e.g., “Silivri Sera”).
  - Show what data is used (sunrise/sunset, outside temp/humidity, precipitation, cloud cover).
- Add an **Overview** weather card:
  - Current outside temp/humidity, precipitation chance, wind, sunrise/sunset.
  - Clear badge if weather data is missing/offline.
- Cache weather responses and support “disable external weather” mode.

## LCD / Display
- Zone-aware LCD templates (SERA + KAT1 + KAT2 + FIDE rotation).
- New tokens: zone-specific temp/hum/soil/lux, data_age, alerts count.
- Optional auto-rotate pages on LCD.

## UX / UI Enhancements
- Mobile tabs for zones, desktop blocks/grid.
- Simplified, zone-first pages.
- Dedicated sensor config and calibration screen.
- Manual control timers: “run for 15 minutes” + visible countdown + automation pause TTL.
- Trend charts include:
  - SERA temp/hum
  - FIDE temp/hum
  - KAT1/KAT2 soil
  - KAT1/KAT2 BH1750 lux
- Interactive charts:
  - Zoom/pan + range selection (brush).
  - Multi-series overlay and compare mode.
  - Event markers (manual actions, alerts, automation changes).

## Cameras & Image Processing
- Each zone node can provide a camera snapshot/stream (ESP32‑CAM).
- Raspberry Pi pulls images on a schedule and runs all processing (plant growth, leaf color/health, condensation/mold detection, “lights actually on?” checks).
- Store only small snapshots by default (retention policy), keep “event snapshots” (alerts) longer.

## Data and Logs
- Storage layer options:
  - Keep SQLite as default (simple backup, works offline) but move to a generic telemetry schema (metric key/value or JSON).
  - Optional: add InfluxDB adapter later if long-range high-frequency analysis becomes important.
  - Downsampling/aggregation endpoints so the UI stays fast on a Raspberry Pi.
- Extend telemetry to include:
  - FIDE temp/hum
  - BH1750 lux per zone
  - KAT1/KAT2 soil (multi-sensor ready)
- Add camera snapshot metadata:
  - last image timestamp per zone, last processing result, confidence/quality.
- Add sensor catalog endpoint for dynamic UI metrics.
- Add event/actuator log query UI (History page) with filters and CSV export.

## Resilience & Data Quality
- Sensor sanity checks (e.g., reject 150°C, negative humidity, impossible jumps).
- Spike/outlier detection and temporary quarantine of faulty sensors.
- Automation must ignore invalid data and fail-safe to OFF where applicable.

## Home Assistant
- Clear HA grouping in the UI (backend badge + entity link).
- Per-zone HA channel mapping.
