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

## UX / UI Enhancements
- Mobile tabs for zones, desktop blocks/grid.
- Simplified, zone-first pages.
- Dedicated sensor config and calibration screen.
- Trend charts include:
  - SERA temp/hum
  - FIDE temp/hum
  - KAT1/KAT2 soil
  - KAT1/KAT2 LDR lux

## Data and Logs
- Extend sensor log schema to include:
  - FIDE temp/hum
  - LDR lux per zone
  - KAT1/KAT2 soil
- Add sensor catalog endpoint for dynamic UI metrics.

## Notifications (Optional Later)
- Zone-aware alerts (e.g., "KAT1 soil dry").
- Fan/heater state notifications for critical events.
