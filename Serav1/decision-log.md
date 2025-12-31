# Decision Log - Multi-Zone Greenhouse Plan

This file captures the concrete decisions made in the recent planning chat.
It is a short, stable reference for implementation and future changes.

## Zones
- Zone list: SERA (global), KAT1, KAT2, FIDE (seedling box).
- Each zone can have its own sensor/node (SERA optional).
- Seedling box has its own temp/hum sensor and its own heater.

## Per-Zone ESP32 Nodes (Sensors + Camera)
- One ESP32 (ESP32-CAM) per zone where practical (KAT1, KAT2, FIDE; optional SERA).
- If greenhouse heater automation is used, add a SERA temp/hum sensor (or explicitly select a floor sensor as the heater reference).
- Each node reads local sensors and sends telemetry to the Raspberry Pi over Wi‑Fi.
- Each node can expose a camera snapshot/stream; Raspberry Pi receives images and runs all image processing.
- Raspberry Pi remains the main panel host (Flask UI/API), storage, automation logic, and alerting.

## Node IDs (default)
- `kat1-node`, `kat2-node`, `fide-node` (optional: `sera-node`).

## Actuators
- Each floor has a single dimmable light channel (PWM) driving both LED bars together.
- Each floor has 1 canopy fan (air blowing over pots).
- There is 1 exhaust fan that vents the greenhouse to outside.
- There is 1 greenhouse heater (global).
- There is 1 seedling box heater (local to FIDE).
- Seedling box may also have a small circulation fan (recommended when the seedling heater is used).

## GPIO Mapping (UI)
- GPIO pin mapping is editable from the panel UI (no code changes required).
- Any pin change should force the channel OFF and require confirmation.

## Soil Moisture (Capacitive)
- Soil sensors exist only on floors, not in the seedling box.
- One soil sensor per floor (KAT1 + KAT2).
- Soil sensors are wired to the local ESP32 node (not directly to the Raspberry Pi).
- If ESP32 ADC channels are not sufficient (common on ESP32-CAM boards), add a small I2C ADC (e.g., ADS1115) on the node.

## Lux Plan (BH1750 per Zone)
- Each zone can have its own BH1750 wired to the local ESP32 node.
- (Optional) LDRs remain possible, but BH1750 is preferred to avoid calibration drift.

## Light Automation Behavior
- Lux control is PWM dimming-based (single channel per floor):
  - If lux is low: increase duty cycle, wait, re-measure lux.
  - If lux is high: decrease duty cycle, wait, re-measure lux.
  - Clamp to min/max duty and apply a safe step size + delay to avoid oscillation.

## Fan Behavior
- Exhaust fan is the only fan with automation.
- Canopy fans are on/off via a 2‑channel relay board; default ON, with a manual toggle in the panel.

## Sensor Types
- Temp/hum sensors must be swappable from the panel.
- SHT31 is the default plan for stability; keep DHT11/22 as optional legacy support.

## UX Direction
- Pages will be redesigned to be zone-first and simpler.
- Mobile: tabs for zones. Desktop: blocks/grid for zones.
- Sensor and actuator configuration should be editable from the panel.

## Navigation (Serav1 beta)
- Mobile tabbar: Genel Bakış, Zoneler, Kontrol, Geçmiş, Diğer (Ayarlar Diğer içinde).
- Diğer grubu: Raporlar, Güncellemeler, Yardım, Donanım, LCD ve Notlar için hızlı erişim.
- UI etiketleri Türkçe: Genel Bakış, Zoneler, Kontrol, Geçmiş, Ayarlar, Diğer.

## Terminoloji (Serav1 beta)
- Arayüzde “Log” yerine “Kayıt” kullanılır (Geçmiş & Kayıtlar).
