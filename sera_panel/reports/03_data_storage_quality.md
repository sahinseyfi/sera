# Report 03 - Data Storage and Quality

## Finding 03-01: Sensor data is in-memory only
Problem / risk:
- Sensor readings are stored only in a volatile in-memory dict. No persistence means no history, no recovery, and no auditability.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 3, Effort L
Recommendation:
- Add a lightweight persistence layer (CSV or SQLite) and a basic retention policy.
DoD (acceptance criteria):
- Sensor readings are saved to disk and can be queried after restart.
Related files:
- `app_legacy.py`: `self.data = { ... }`
- `app_legacy.py`: `def snapshot(self):
    return json.loads(json.dumps(self.data))`
Notes / assumptions:
- No file writes or DB usage exist in this folder.

## Finding 03-02: No history or export endpoints
Problem / risk:
- The API does not expose historical data or exports, limiting diagnostics and UX features (charts, trends).
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Add `/api/history` (read) and optional CSV export endpoints once persistence exists.
DoD (acceptance criteria):
- Clients can request time ranges and receive data without blocking the main loop.
Related files:
- `app_legacy.py`: `@app.route("/api/status")`
- `app_legacy.py`: `@app.route("/api/relay/<relay_key>")`
Notes / assumptions:
- Only status/config/safety endpoints exist in `app_legacy.py`.

## Finding 03-03: Sampling interval may be too fast for DHT22
Problem / risk:
- The loop runs every ~1.2s. DHT22 typically requires ~2s between reads, so frequent reads can cause invalid data spikes.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort S
Recommendation:
- Add per-sensor throttling or an interval config for DHT22.
DoD (acceptance criteria):
- DHT reads respect the recommended minimum interval.
Related files:
- `app_legacy.py`: `dht = adafruit_dht.DHT22(pin_obj)`
- `app_legacy.py`: `time.sleep(1.2)`
Notes / assumptions:
- The loop uses one global interval for all sensors.

## Finding 03-04: ADS1115 values are raw voltages only
Problem / risk:
- Soil moisture channels expose raw voltages with no normalization or calibration mapping. This limits data interpretability.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort M
Recommendation:
- Add calibration parameters (dry/wet) and convert to percentage in API output.
DoD (acceptance criteria):
- API includes calibrated soil moisture percent per channel.
Related files:
- `app_legacy.py`: `self.data["ads1115"] = { "a0": v[0], ... }`
Notes / assumptions:
- No calibration config is used in `app_legacy.py`.

## Finding 03-05: Error tracking is shallow and not summarized
Problem / risk:
- Errors are appended to a list without aggregation, rate, or health scoring, making it hard to quantify sensor reliability.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort M
Recommendation:
- Track error counts per sensor and include a rolling health metric in `/api/status`.
DoD (acceptance criteria):
- API returns per-sensor error counts over a recent window.
Related files:
- `app_legacy.py`: `self.data["errors"].append({"where": where, ...})`
Notes / assumptions:
- The error list is capped at 50 items.

## Finding 03-06: Channel definitions are duplicated
Problem / risk:
- Sensor/actuator metadata appears in both `config.json` and `config/channels.json`, which can lead to mismatched labels or pins.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Consolidate metadata into a single config file and reference it consistently.
DoD (acceptance criteria):
- Only one file is required to define channels and metadata.
Related files:
- `config.json`: `"channels": {`
- `config/channels.json`: `"channels": {`
Notes / assumptions:
- No code in `app_legacy.py` reads `config/channels.json`.
