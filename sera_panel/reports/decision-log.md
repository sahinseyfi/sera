# Decision Log - Multi-Zone Greenhouse Plan

This file captures the concrete decisions made in the recent planning chat.
It is a short, stable reference for implementation and future changes.

## Zones
- Zone list: SERA (global), KAT1, KAT2, FIDE (seedling box).
- DHT sensor is greenhouse-wide (SERA), not per floor.
- Seedling box has its own temp/hum sensor and its own heater.

## Actuators
- Each floor has 2 separate LED rows (LED1 + LED2), each controllable.
- Each floor has 1 canopy fan (air blowing over pots).
- There is 1 exhaust fan that vents the greenhouse to outside.
- There is 1 greenhouse heater (global).
- There is 1 seedling box heater (local to FIDE).

## Soil Moisture (ADS1115)
- Soil sensors exist only on floors, not in the seedling box.
- ADS1115 channel mapping:
  - CH0 -> KAT1 soil sensor
  - CH1 -> KAT2 soil sensor
  - CH2 -> KAT1 LDR
  - CH3 -> KAT2 LDR

## LDR + Lux Plan
- BH1750 remains the reference lux sensor.
- LDRs are calibrated by placing them next to BH1750 and computing a scale factor.
- LDR calibration is done via panel UI (no extra ADC hardware).
- LDR lux values are used per floor.

## Light Automation Behavior
- Lux control is step-based:
  - If lux is low: turn on LED1 for that floor, re-measure lux.
  - If still low: turn on LED2, re-measure lux.
  - If lux is high: turn off LED2 first, re-measure, then LED1 if needed.

## Fan Behavior
- Exhaust fan is the only fan with automation.
- Canopy fans are generally always ON; add an "always on" toggle in the panel.

## Sensor Types
- Temp/hum sensors must be swappable from the panel.
- DHT11/22 now; SHT31 is planned as a supported type.

## UX Direction
- Pages will be redesigned to be zone-first and simpler.
- Mobile: tabs for zones. Desktop: blocks/grid for zones.
- Sensor and actuator configuration should be editable from the panel.
