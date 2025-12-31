# Sera Panel (Legacy/Test UI)

This folder contains a legacy standalone Flask panel used for local monitoring
and manual control. The main panel lives at the repo root (`/home/sahin/app.py`)
and is the single source of truth for new features. This legacy UI still talks
directly to GPIO and I2C devices, so treat it as production hardware code.

## Quick start

- From this folder, run the legacy panel:
  - `python3 app_legacy.py`
- Open the UI at `http://<pi-ip>:5000/`

Notes:
- GPIO access may require sudo on some systems.
- Admin-protected endpoints accept `X-Admin-Token` when `ADMIN_TOKEN` is set.
  - Set in shell: `export ADMIN_TOKEN=...`
  - Set in browser console: `localStorage.setItem("adminToken","...")`

## Systemd service (optional)

Sample unit file: `systemd/sera-panel.service`

Install steps (run as root):
- Copy to `/etc/systemd/system/sera-panel.service`
- Adjust `User=` and `ExecStart=` if needed
- `systemctl daemon-reload`
- `systemctl enable --now sera-panel`

## Dependencies (Python packages)

Core (app_legacy.py):
- Flask
- gpiozero
- smbus2
- adafruit-blinka (board/busio)
- adafruit-circuitpython-bh1750
- adafruit-circuitpython-ads1x15
- adafruit-circuitpython-dht
- w1thermsensor

Optional (tools/sera_hw_panel.py):
- RPi.GPIO

## Configuration

- Runtime config: `config.json`
  - `safety` (pump/heater limits, cooldowns)
  - `sensors` (I2C bus, GPIO pins)
  - `channels_file` points to the relay mapping file
- Relay mapping (single source of truth): `config/channels.json`
  - Each channel maps a GPIO pin and logical role
  - `relay_key` keeps stable API/UI names

If you change relay mappings, make sure all relays are OFF and re-verify
from the UI before connecting loads.

## Safety notes (SAFE-OFF)

- Default posture: all relays OFF, SAFE MODE enabled.
- Do not run long pump or heater sessions without limits.
- If sensors are missing or stale, leave critical relays OFF.
- Avoid GPIO changes when hardware state is unknown.

## Test tools (use with extreme care)

These scripts can toggle relays. Disconnect loads before use.

- `bash relay_polarity_test.sh`
- `bash relay_click_test.sh`

## Data and logs

- Sensor log (CSV): `data/sensor_log.csv`
  - Used by `/api/history` for read-only history queries.

## Common API endpoints (legacy)

- `GET /api/status`
- `POST /api/safety`
- `POST /api/relay/<relay_key>`
- `GET/POST /api/config`
- `POST /api/all-off`
- `GET /api/history`
- `GET /api/audit`

## Troubleshooting

- If the UI shows "unauthorized", set `ADMIN_TOKEN` and a matching
  `adminToken` in localStorage, or access from a local subnet.
- If GPIO pins fail to initialize, verify `config/channels.json` and
  check for pin conflicts with I2C or DHT22.
