# Report 07 - Backlog and Sprint Plan

Backlog items are ordered by Impact (high to low), then Risk (low to high), then Effort (S -> M -> L).

## ITEM-001: Fix frontend API base mismatch
Problem / risk:
- UI uses a different API prefix than the backend, so the test panel cannot load data.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 1, Effort S
Recommendation:
- Align `static/app.js` API prefix with `/api` or add a matching backend prefix.
DoD (acceptance criteria):
- UI can load `/api/status` and relay actions with no 404.
Related files:
- `static/app.js`: `const API_PREFIX = "/test/api";`
- `app_legacy.py`: `@app.route("/api/status")`
Notes / assumptions:
- No reverse proxy is defined in this folder.

## ITEM-002: Fix static asset URL builder
Problem / risk:
- Template references `test_panel` blueprint which does not exist, breaking CSS/JS loading.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 1, Effort S
Recommendation:
- Use `url_for('static', ...)` or define the blueprint in the Flask app.
DoD (acceptance criteria):
- CSS and JS load without 404 for `/static/*`.
Related files:
- `templates/index.html`: `url_for('test_panel.static', filename='style.css')`
- `app_legacy.py`: `app = Flask(__name__)`
Notes / assumptions:
- Default Flask static routing is in use.

## ITEM-003: Align safety state naming in UI and API
Problem / risk:
- UI expects `safe_mode` but API returns `safety.test_mode`, so safety status is misleading.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort S
Recommendation:
- Add a `safe_mode` alias in `/api/status` or update the UI to use `safety.test_mode`.
DoD (acceptance criteria):
- Safety indicator displays correct state.
Related files:
- `static/app.js`: `setText("safeModeVal", st.safe_mode ? "ON" : "OFF");`
- `app_legacy.py`: `"safety": { "test_mode": ... }`
Notes / assumptions:
- The UI is the primary operator view.

## ITEM-006: Expand config validation
Problem / risk:
- `validate_config` only checks GPIO conflicts and DHT overlap; safety ranges are unchecked.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort S
Recommendation:
- Add range checks for safety values and ensure relay types are valid.
DoD (acceptance criteria):
- Unsafe values are rejected with clear errors in `/api/config`.
Related files:
- `app_legacy.py`: `def validate_config(cfg: Dict[str, Any]) -> Optional[str]:`
- `config.json`: `"safety": { "heater_max_on_sec": 10, "pump_max_on_sec": 3 }`
Notes / assumptions:
- Config edits are currently accepted without range guards.

## ITEM-007: Make sensor config reload effective
Problem / risk:
- Config updates do not change sensor behavior because the sensor loop does not restart.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort M
Recommendation:
- Restart the sensor thread on config reload or make it read live config.
DoD (acceptance criteria):
- Changing `dht22_enabled` or bus settings takes effect without restart.
Related files:
- `app_legacy.py`: `def reload_runtime(new_cfg: Dict[str, Any]):`
- `app_legacy.py`: `def start(self, cfg: Dict[str, Any]):
    if self._thread and self._thread.is_alive():
        return`
Notes / assumptions:
- The loop uses the config object passed at thread start.

## ITEM-011: Add sensor log persistence
Problem / risk:
- There is no persistence of sensor readings, so troubleshooting and history are impossible.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort L
Recommendation:
- Add CSV or SQLite logging for key sensor values on a fixed interval.
DoD (acceptance criteria):
- A log file or DB table is created and updated during runtime.
Related files:
- `app_legacy.py`: `self.data = { ... }`
Notes / assumptions:
- This folder has no `data/` directory or DB usage.

## ITEM-024: Add tests for auto-off timers
Problem / risk:
- Heater/pump auto-off behavior is safety critical but untested.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort M
Recommendation:
- Add tests using a mocked timer to verify auto-off execution.
DoD (acceptance criteria):
- Tests confirm that auto-off is scheduled and executed.
Related files:
- `app_legacy.py`: `def arm_auto_off(self, relay_key: str, seconds: int, off_fn)`
Notes / assumptions:
- Current tests do not exist in this folder.

## ITEM-005: Validate and clamp relay action inputs
Problem / risk:
- `api_relay` accepts `action` and `sec` values with minimal validation and no error details for edge cases.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort S
Recommendation:
- Add stricter validation and error messages for invalid `action` or `sec`.
DoD (acceptance criteria):
- Invalid inputs return 400 with clear error strings.
Related files:
- `app_legacy.py`: `action = body.get("action", "")`
- `app_legacy.py`: `sec = max(1, min(sec, 15))`
Notes / assumptions:
- Only "off/on/pulse" are supported today.

## ITEM-014: Improve UI for stale data and errors
Problem / risk:
- The UI does not clearly show stale data or sensor error states beyond small text, which can mislead operators.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort S
Recommendation:
- Add a stale indicator and highlight sensor error blocks when `err` is present.
DoD (acceptance criteria):
- Stale data is visually flagged; sensor errors are prominent.
Related files:
- `static/app.js`: `renderSensors(st.sensors || {})`
- `static/app.js`: `setText("backendOk", st.sensors && st.sensors.ok ? "OK" : "Hata var")`
Notes / assumptions:
- Backend provides `sensors.ok` and per-sensor `err` fields.

## ITEM-015: Make pump lock and limits explicit in UI
Problem / risk:
- Pump lock and max duration exist, but the UI does not fully explain cooldown or safety rules.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort S
Recommendation:
- Add a visible summary of pump safety rules and current limits.
DoD (acceptance criteria):
- UI shows pump lock state and all safety limits in one place.
Related files:
- `static/app.js`: `setText("pumpMax", pumpMax)`
- `templates/index.html`: `id="pumpUnlock"`
Notes / assumptions:
- Cooldown is not yet implemented in the backend.

## ITEM-016: Consolidate config sources (relays vs channels)
Problem / risk:
- Multiple config sources define pin maps, increasing drift risk.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Choose one mapping format and remove or mark the other as legacy.
DoD (acceptance criteria):
- Only one config file is required for relay mapping.
Related files:
- `config.json`: `"relays": { ... }`
- `config/channels.json`: `"channels": { ... }`
Notes / assumptions:
- `app_legacy.py` only loads `config.json`.

## ITEM-010: Add audit/event log for safety and relay actions
Problem / risk:
- There is no record of who or what toggled relays or safety state.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Add an in-memory or file-based event log for relay and safety actions.
DoD (acceptance criteria):
- Every relay action adds a log entry with timestamp and actor.
Related files:
- `app_legacy.py`: `def api_safety():`
- `app_legacy.py`: `def api_relay(relay_key: str):`
Notes / assumptions:
- No event logging exists today.

## ITEM-012: Add log retention/rotation
Problem / risk:
- Any new persistence layer will grow without bounds unless retention is enforced.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Add daily file rotation or DB pruning for old rows.
DoD (acceptance criteria):
- Log storage is capped by days or size.
Related files:
- `app_legacy.py`: `self.data = { ... }`
Notes / assumptions:
- No persistence exists yet; retention should be added when logging is added.

## ITEM-013: Add /api/history endpoint
Problem / risk:
- Without a history endpoint, UI cannot display charts or trends.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Add a read-only history endpoint after persistence is implemented.
DoD (acceptance criteria):
- Clients can request time range and metric list via API.
Related files:
- `app_legacy.py`: `@app.route("/api/status")`
Notes / assumptions:
- History endpoints exist in roadmap docs but not in code.

## ITEM-021: Add unit tests for SafetyManager
Problem / risk:
- SafetyManager is critical and untested.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort M
Recommendation:
- Add tests for test_mode, estop, and pump lock combinations.
DoD (acceptance criteria):
- SafetyManager behavior is covered by at least 5 unit tests.
Related files:
- `app_legacy.py`: `class SafetyManager:`
Notes / assumptions:
- No tests exist in this folder today.

## ITEM-022: Add unit tests for config validation
Problem / risk:
- Configuration validation is untested and could regress silently.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort M
Recommendation:
- Add tests for GPIO conflicts, reserved pins, and DHT collisions.
DoD (acceptance criteria):
- `validate_config` tests cover happy and failure paths.
Related files:
- `app_legacy.py`: `def validate_config(cfg: Dict[str, Any]) -> Optional[str]:`
Notes / assumptions:
- Validation is a pure function, easy to test.

## ITEM-023: Add API contract tests for /api/status and /api/relay
Problem / risk:
- API shape changes can break the UI without detection.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort M
Recommendation:
- Add Flask test client tests to validate response structure and errors.
DoD (acceptance criteria):
- Tests verify required keys in `/api/status` and error handling in `/api/relay`.
Related files:
- `app_legacy.py`: `@app.route("/api/status")`
- `app_legacy.py`: `@app.route("/api/relay/<relay_key>", methods=["POST"])`
Notes / assumptions:
- The UI depends on these fields for rendering.

## ITEM-020: Add /api/health endpoint
Problem / risk:
- There is no lightweight health endpoint for monitoring or systemd checks.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 1, Effort S
Recommendation:
- Add a minimal endpoint that returns a static "ok" and version info.
DoD (acceptance criteria):
- Health endpoint responds without triggering sensor reads.
Related files:
- `app_legacy.py`: `@app.route("/api/status")`
Notes / assumptions:
- `/api/status` triggers full data assembly.

## ITEM-017: Add a local README for this folder
Problem / risk:
- There is no localized runbook inside `/home/sahin/sera_panel`, which can confuse contributors.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 1, Effort S
Recommendation:
- Create a README that explains how to run `app_legacy.py`, safety notes, and test scripts.
DoD (acceptance criteria):
- README includes run, safety, and hardware test sections.
Related files:
- `app_legacy.py`: `if __name__ == "__main__":`
- `relay_click_test.sh`: `set -euo pipefail`
Notes / assumptions:
- Existing docs are at the repo root, not in this folder.

## ITEM-018: Add dependency list for this folder
Problem / risk:
- There is no requirements file in this folder, which makes setup ambiguous.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 1, Effort S
Recommendation:
- Add `requirements.txt` or reference a shared dependency file in a README.
DoD (acceptance criteria):
- Dependencies required by `app_legacy.py` are listed clearly.
Related files:
- `app_legacy.py`: `import adafruit_bh1750` (and other hardware libs)
Notes / assumptions:
- Current venv lives under `/home/sahin/sera_panel/venv`.

## ITEM-019: Add systemd unit example for app_legacy
Problem / risk:
- No service unit exists in this folder, so startup is manual and not resilient.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort M
Recommendation:
- Add a sample unit file and instructions for installing it.
DoD (acceptance criteria):
- A unit file is present and references `app_legacy.py`.
Related files:
- `app_legacy.py`: `if __name__ == "__main__":`
Notes / assumptions:
- No systemd directory exists under this folder.

## ITEM-025: Align relay test scripts with active_low config
Problem / risk:
- Relay test scripts assume active-low, which can be wrong for some hardware and lead to unsafe toggling.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort S
Recommendation:
- Read active_low from config or print a clear warning and prompt before running.
DoD (acceptance criteria):
- Scripts either load config or require explicit confirmation of active_low.
Related files:
- `relay_click_test.sh`: `PINS=(18 23 24 25 20 21)`
- `config.json`: `"active_low": true`
Notes / assumptions:
- `relay_polarity_test.sh` exists but is not enforced.

## ITEM-004: Add auth for control endpoints
Problem / risk:
- Anyone on the network can toggle relays or change config.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 3, Effort M
Recommendation:
- Require an admin token or local subnet check for POST endpoints.
DoD (acceptance criteria):
- Unauthorized calls return 401/403; UI can send a token header.
Related files:
- `app_legacy.py`: `def api_relay(relay_key: str):`
- `static/app.js`: `headers["X-Admin-Token"] = token`
Notes / assumptions:
- UI already stores an admin token but backend ignores it.

## ITEM-008: Add stale sensor fail-safe
Problem / risk:
- If sensor updates stop, the system can continue running heater/pump without safety cut-off.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 3, Effort M
Recommendation:
- Track last update time and auto-off critical actuators when stale.
DoD (acceptance criteria):
- Stale sensor data disables heater/pump automatically.
Related files:
- `app_legacy.py`: `self.data["last_update"] = now`
- `app_legacy.py`: `def api_relay(relay_key: str):`
Notes / assumptions:
- No stale check exists today.

## ITEM-009: Add pump/heater cooldown enforcement
Problem / risk:
- There is no cooldown between repeated pump/heater activations.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 3, Effort M
Recommendation:
- Add cooldown timers per relay type with clear error messages.
DoD (acceptance criteria):
- Requests during cooldown are rejected and a remaining time is returned.
Related files:
- `app_legacy.py`: `if rinfo.get("type") == "pump":`
- `config.json`: `"safety": { ... }`
Notes / assumptions:
- Only max duration is enforced.

## Sprint Plan

Sprint 1 (low risk, high impact):
- ITEM-001, ITEM-002, ITEM-003, ITEM-005, ITEM-006, ITEM-014, ITEM-015

Sprint 2 (safety and runtime correctness):
- ITEM-004, ITEM-007, ITEM-008, ITEM-009, ITEM-010, ITEM-016

Sprint 3 (data + ops):
- ITEM-011, ITEM-012, ITEM-013, ITEM-019, ITEM-020, ITEM-025

Sprint 4 (tests + docs + deps):
- ITEM-017, ITEM-018, ITEM-021, ITEM-022, ITEM-023, ITEM-024
