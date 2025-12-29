# Future Features Plan (Post-Refactor)

This document lists the next set of planned features after the redesign.
It is aligned with the decision log and the new zone-first UI.

## Zone Model
- Zones: SERA (global), KAT1, KAT2, FIDE.
- Every actuator and sensor is assigned to a zone.
- UI groups all controls and metrics by zone.

## Sensors
- Support multiple temp/hum sensors with type selection:
  - DHT11, DHT22, SHT31 (future-ready).
- ADS1115 mapping:
  - CH0 -> KAT1 soil
  - CH1 -> KAT2 soil
  - CH2 -> KAT1 LDR
  - CH3 -> KAT2 LDR
- LDR calibration tool:
  - Place LDR next to BH1750, measure both, store scale factor.
  - Convert raw LDR to lux using scale factor.

## Lux and Light Control
- Per-zone stepped light control:
  - LED1 ON -> re-measure -> LED2 ON if needed.
  - When lux is high, turn off LED2 first, then LED1.
- Lux thresholds per zone.
- Safe min on/off and measurement delay between steps.

## Fans
- Exhaust fan automation only (based on humidity or rules).
- Canopy fans: "Always ON" toggle in UI, with SAFE MODE override.

## Heating
- Greenhouse heater uses global sensor (SERA).
- Seedling heater uses FIDE sensor.
- Heater sensor type is configurable from UI.

## Notifications
- Keep Telegram and Email support, add zone-specific alert rules.
- Quiet hours and daily digest options.
- Clear UI status for missing env vars.

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
  - KAT1/KAT2 LDR lux
- Interactive charts:
  - Zoom/pan + range selection (brush).
  - Multi-series overlay and compare mode.
  - Event markers (manual actions, alerts, automation changes).

## Data and Logs
- Storage layer options:
  - Keep SQLite as default (simple backup, works offline) but move to a generic telemetry schema (metric key/value or JSON).
  - Optional: add InfluxDB adapter later if long-range high-frequency analysis becomes important.
  - Downsampling/aggregation endpoints so the UI stays fast on a Raspberry Pi.
- Extend telemetry to include:
  - FIDE temp/hum
  - LDR lux per zone
  - KAT1/KAT2 soil
- Add sensor catalog endpoint for dynamic UI metrics.
- Add event/actuator log query UI (History page) with filters and CSV export.

## Resilience & Data Quality
- Sensor sanity checks (e.g., reject 150°C, negative humidity, impossible jumps).
- Spike/outlier detection and temporary quarantine of faulty sensors.
- Automation must ignore invalid data and fail-safe to OFF where applicable.

## Home Assistant
- Clear HA grouping in the UI (backend badge + entity link).
- Per-zone HA channel mapping.
