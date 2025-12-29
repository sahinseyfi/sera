# Report 01 - Architecture and Flow

## Finding 01-01: Sensor loop is a single threaded poller
Problem / risk:
- All sensor reads happen in one loop thread, so a blocking sensor call delays the entire data refresh path.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Add timeouts or per-sensor isolation to avoid one sensor blocking all others.
DoD (acceptance criteria):
- A blocked sensor no longer stalls BH1750/ADS/DS/DHT updates.
Related files:
- `app_legacy.py`: `def _loop(self, cfg: Dict[str, Any]):`
- `app_legacy.py`: `time.sleep(1.2)`
Notes / assumptions:
- The loop runs every ~1.2s without timeouts.

## Finding 01-02: API status is the primary data contract
Problem / risk:
- `/api/status` bundles relays, safety state, config, and sensor snapshot. If this shape changes, the UI must stay in sync.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort S
Recommendation:
- Define a stable response schema and add a minimal contract test for `/api/status`.
DoD (acceptance criteria):
- API response keys are documented and tested for regressions.
Related files:
- `app_legacy.py`: `@app.route("/api/status")`
- `app_legacy.py`: `return jsonify({ ... "sensors": sensors.snapshot() })`
Notes / assumptions:
- No tests exist in this folder to validate the schema.

## Finding 01-03: Safety gate is enforced only for on/pulse
Problem / risk:
- Safety checks are enforced for "on" and "pulse" actions, but not for config changes or test mode toggles.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 3, Effort M
Recommendation:
- Restrict config and safety endpoints with admin/auth checks.
DoD (acceptance criteria):
- Only authorized users can change safety state, relays, or config.
Related files:
- `app_legacy.py`: `def api_safety():`
- `app_legacy.py`: `def api_relay(relay_key: str):`
Notes / assumptions:
- There is no auth in `app_legacy.py`.

## Finding 01-04: Config reload does not update the sensor loop
Problem / risk:
- `reload_runtime` calls `sensors.start(cfg)` but the sensor thread is not restarted if it already runs, so new config values (like dht22_enabled) do not apply.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort M
Recommendation:
- Stop and restart the sensor loop on config reload or make the loop read live config.
DoD (acceptance criteria):
- Changing config via `/api/config` affects sensor behavior without a full process restart.
Related files:
- `app_legacy.py`: `def reload_runtime(new_cfg: Dict[str, Any]):`
- `app_legacy.py`: `def start(self, cfg: Dict[str, Any]):
    if self._thread and self._thread.is_alive():
        return`
Notes / assumptions:
- The loop uses the config passed at thread start.

## Finding 01-05: Frontend API prefix is mismatched
Problem / risk:
- The JS client calls `/test/api/*`, while the backend defines `/api/*` routes, so the UI will fail without a reverse proxy or blueprint.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 2, Effort S
Recommendation:
- Align the API prefix in the frontend or add a matching backend prefix.
DoD (acceptance criteria):
- The test panel can load status and execute safe actions successfully.
Related files:
- `static/app.js`: `const API_PREFIX = "/test/api";`
- `app_legacy.py`: `@app.route("/api/status")`
Notes / assumptions:
- No blueprint named `test_panel` exists in `app_legacy.py`.

## Finding 01-06: I2C scan flow falls back to shell command
Problem / risk:
- If smbus2 fails, the code runs `i2cdetect`, which can be slow and may require elevated privileges.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort S
Recommendation:
- Guard the endpoint with auth and add timeouts or a clear warning in the UI.
DoD (acceptance criteria):
- I2C scan is restricted and user feedback is explicit on failures.
Related files:
- `app_legacy.py`: `subprocess.check_output(["i2cdetect", "-y", str(bus_num)], text=True)`
- `app_legacy.py`: `@app.route("/api/i2c-scan", methods=["POST"])`
Notes / assumptions:
- The scan is on-demand and not rate limited.
