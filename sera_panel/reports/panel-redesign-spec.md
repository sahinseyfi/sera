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
- Must operate safely when sensors are missing or stale.
- Minimal dependencies; keep performance light.

## 4. Terminology
- SERA: global environment.
- KAT1, KAT2: plant floors.
- FIDE: seedling box.
- CANOPY FAN: floor fan blowing over pots.
- EXHAUST FAN: greenhouse vent fan to outside.

## 5. Information Architecture (Global Nav)
1) Overview
2) Zones
3) Control
4) Automation
5) Sensors
6) LCD / Display
7) Logs & Trends
8) Reports
9) Updates
10) Notes
11) Settings
12) Help

Notes:
- Overview is read-only summary.
- Zones is the main operational hub.
- Control is explicit manual actuation with safety.

## 6. Data Model (Front-End)

### 6.1 Zones
```
Zone = {
  id: 'sera' | 'kat1' | 'kat2' | 'fide',
  label: string,
  sensors: [sensorId],
  actuators: [actuatorId]
}
```

### 6.2 Sensors
```
Sensor = {
  id: string,
  label: string,
  kind: 'dht11' | 'dht22' | 'sht31' | 'bh1750' | 'ldr' | 'ads1115',
  zone: ZoneId,
  purpose: 'temp_hum' | 'lux' | 'soil',
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
  role: 'heater' | 'fan_canopy' | 'fan_exhaust' | 'light_1' | 'light_2' | 'pump',
  backend: 'gpio' | 'homeassistant',
  gpio_pin?: number,
  ha_entity_id?: string,
  active_low: boolean,
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

## 7. Global UI Layout
- Top bar: brand + SAFE MODE indicator + data age.
- Secondary strip: last update time, stale warning, alert count.
- Content width: max 1200px, centered.
- Mobile: single column, tabs for zones.

## 8. Overview Page (Read-Only)

### 8.1 Sections
1) System Summary (safe mode, data age, alerts)
2) Global Sensors (SERA temp/hum + BH1750 lux)
3) Zones Snapshot (KAT1 / FIDE / KAT2)
4) Active Automation Summary
5) Alerts (last 5)

### 8.2 Zone Snapshot Cards
- Header: zone label + health badge.
- Body: main metrics per zone.
- Footer: quick actuator states (LED1/LED2/Fan/Heater).

## 9. Zones Page (Operational Hub)

### 9.1 Layout
- Desktop: three blocks side-by-side if space, else two rows.
- Mobile: tabs (KAT1, FIDE, KAT2).

### 9.2 Per Zone Content
- Metrics card: temp/hum or soil/lux depending on zone.
- Actuator card: states + last change reason.
- Mini trend chart (last 6h) for the main metric.

### 9.3 Zone Notes
- Include short info text so user knows what each zone represents.

## 10. Control Page (Manual Actuation)

### 10.1 Safety
- SAFE MODE blocks all manual control.
- Heater/pump require confirmation + countdown.
- Display actuator cooldown if any.

### 10.2 Grouping
- Group by zone, then by role.
- Each actuator card shows:
  - Current state
  - Last change + reason
  - Quick ON/OFF and duration (if allowed)

## 11. Automation Page

### 11.1 Lux Automation (Per Zone)
- Sensor: select LDR or BH1750.
- Thresholds: lux_ok, lux_max.
- Stepped light behavior toggles:
  - Step delay (seconds)
  - Min on/off (minutes)
- Target minutes per day (optional).

### 11.2 Heater Automation
- SERA heater uses SERA sensor.
- FIDE heater uses FIDE sensor.
- Night mode toggle + schedule.

### 11.3 Exhaust Fan Automation
- Based on humidity or temperature.
- Only applies to EXHAUST FAN.

### 11.4 Canopy Fan Always On
- Per zone toggle: "Always ON".
- If enabled and SAFE MODE off, fan stays ON unless manual override.

## 12. Sensors Page

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

## 13. LCD / Display Page

### 13.1 LCD Settings
- Enable/disable, mode (auto/template/manual), address, port, expander, charmap.

### 13.2 Template Editor
- 4x20 line editor with token buttons.
- Zone-aware tokens (sera/kat1/kat2/fide).
- Preview of the resolved output.

### 13.3 Rotation
- Optional auto-rotate between zone views.

## 14. Logs & Trends Page

### 14.1 Filters
- Zone selector
- Metric selector
- Time range (24h, 7d)

### 14.2 Chart
- Single main chart with legend.
- Tooltip shows value + timestamp.

### 14.3 Export
- CSV download for selected filter.

## 15. Reports Page

### 15.1 Daily Summary
- One page per day with zone summary.
- "Top 3" highlights: good, warning, action.

### 15.2 Weekly Summary
- Trends and improvements per zone.

## 16. Updates Page
- User-friendly changelog from config.
- Latest update date shown at top.

## 17. Notes Page
- Curated improvement ideas grouped by topic.
- Acts as a lightweight roadmap for internal use.

## 18. Settings Page
- Safe mode toggle.
- Limits (pump, heater).
- Alerts thresholds.
- Energy pricing (kWh tiers).
- Notifications (Telegram/Email enable, severity, cooldown, test send).
- Retention (cleanup schedule, manual cleanup).
- Backup/restore (JSON import/export).
- Admin token status + input.

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

## 23. Interaction Details
- Auto-refresh every 2-3 seconds for live pages.
- Manual refresh button available.
- Confirm modals for critical actions.

## 24. API Contracts (Suggested)
- `GET /api/status`: include zones, sensors, actuators, automation summary.
- `GET /api/sensor_catalog`: list sensor definitions + status.
- `POST /api/sensors`: update sensor config.
- `POST /api/calibrate/ldr`: save LDR scale factor.
- `GET /api/trends`: unified trend data by zone/metric.
- `GET /api/updates`: UI updates feed.
- `POST /api/notifications/test`: test send for Telegram/Email.
- `GET /api/backup` and `POST /api/backup/restore`: backup/restore.
- `POST /api/lcd`: LCD config + template lines.

## 25. Migration Notes
- Maintain backward compatibility for old config keys where possible.
- Provide a one-time mapping of existing channels to zones.

---

End of spec.
