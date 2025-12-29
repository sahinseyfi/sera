# Report 08 - Codex 5.1 Max Item Prompts

Each item below contains a ready-to-run prompt for gpt-5.1-codex-max (reasoning high).

## ITEM-001: Fix frontend API base mismatch
Problem / risk:
- UI uses a different API prefix than the backend so status and relay actions fail.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 1, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-001.
Goal: Align the frontend API base with the backend routes so the test panel can load data.
Scope: /home/sahin/sera_panel/static/app.js (and only touch /home/sahin/sera_panel/app_legacy.py if you add a matching prefix route).
Safety: SAFE-OFF. Do not trigger relays, pumps, heaters, fans, lights, or automation. Do not run relay scripts or gpioset.
Expected diff: Small (1-5 lines).
DoD:
- API base in JS matches backend routes.
- No unrelated refactors.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan current API prefix usage and backend routes.
2) Apply the minimal change to align the prefix.
3) Show git diff.
4) Run the verification command(s).
5) Report results and any limitations.
```
DoD (acceptance criteria):
- UI API prefix and backend routes are aligned.
Related files:
- `static/app.js`: `const API_PREFIX = "/test/api";`
- `app_legacy.py`: `@app.route("/api/status")`
Notes / assumptions:
- No reverse proxy is configured in this folder.

## ITEM-002: Fix static asset URL builder
Problem / risk:
- Template references a blueprint name that does not exist, so CSS/JS fail to load.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 1, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-002.
Goal: Ensure static assets load correctly by fixing url_for usage.
Scope: /home/sahin/sera_panel/templates/index.html (and add a blueprint only if required).
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Small (1-5 lines).
DoD:
- CSS/JS references resolve via the running Flask app.
- No other template changes.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan template static references and Flask app setup.
2) Apply minimal fix.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- Static assets load without 404.
Related files:
- `templates/index.html`: `url_for('test_panel.static', filename='style.css')`
- `app_legacy.py`: `app = Flask(__name__)`
Notes / assumptions:
- Default Flask static folder is used.

## ITEM-003: Align safety state naming in UI and API
Problem / risk:
- UI expects `safe_mode` while API exposes `safety.test_mode`.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-003.
Goal: Make safety state naming consistent between backend and UI.
Scope: /home/sahin/sera_panel/app_legacy.py and/or /home/sahin/sera_panel/static/app.js.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Small (1-10 lines).
DoD:
- UI shows correct safety state.
- API response remains backward compatible if possible.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan current API response and UI usage.
2) Implement the alignment with minimal change.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- Safety state is accurate in the UI.
Related files:
- `static/app.js`: `setText("safeModeVal", st.safe_mode ? "ON" : "OFF");`
- `app_legacy.py`: `"safety": { "test_mode": ... }`
Notes / assumptions:
- The UI is the operator view.

## ITEM-004: Add auth for control endpoints
Problem / risk:
- Any client can toggle relays or change config via POST endpoints.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 3, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-004.
Goal: Require an admin token (or local subnet check) for control endpoints.
Scope: /home/sahin/sera_panel/app_legacy.py and /home/sahin/sera_panel/static/app.js (if token header needs to be used).
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (20-60 lines).
DoD:
- Unauthorized requests to /api/safety, /api/relay, /api/config, /api/i2c-scan, /api/all-off are rejected.
- UI can pass a token header when set.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan existing endpoints and headers used in JS.
2) Implement auth checks with minimal, consistent logic.
3) Show git diff.
4) Run verification command(s).
5) Report results and any compatibility notes.
```
DoD (acceptance criteria):
- Control endpoints require auth; unauthorized calls fail.
Related files:
- `app_legacy.py`: `def api_relay(relay_key: str):`
- `static/app.js`: `headers["X-Admin-Token"] = token`
Notes / assumptions:
- Token storage already exists in JS but is not enforced server-side.

## ITEM-005: Validate and clamp relay action inputs
Problem / risk:
- Relay actions accept minimal validation; invalid values can behave unexpectedly.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-005.
Goal: Add strict validation for relay `action` and `sec` values.
Scope: /home/sahin/sera_panel/app_legacy.py.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Small (10-25 lines).
DoD:
- Invalid action returns 400 with a clear error.
- `sec` values are clamped and validated server-side.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan api_relay current handling.
2) Add validation with minimal behavior change.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- api_relay rejects invalid inputs consistently.
Related files:
- `app_legacy.py`: `def api_relay(relay_key: str):`
Notes / assumptions:
- UI currently only sends off/on/pulse.

## ITEM-006: Expand config validation
Problem / risk:
- Safety values in config are not range-validated.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-006.
Goal: Add server-side range validation for safety config values.
Scope: /home/sahin/sera_panel/app_legacy.py and /home/sahin/sera_panel/config.json (only if defaults must be updated).
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Small (15-30 lines).
DoD:
- Invalid safety values are rejected with clear errors.
- Valid configs pass unchanged.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
- python3 -m json.tool /home/sahin/sera_panel/config.json
Process:
1) Scan validate_config behavior.
2) Add bounds checks with clear messages.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- Safety ranges are enforced on config load and updates.
Related files:
- `app_legacy.py`: `def validate_config(cfg: Dict[str, Any]) -> Optional[str]:`
- `config.json`: `"safety": { ... }`
Notes / assumptions:
- Existing values are expected to remain valid.

## ITEM-007: Make sensor config reload effective
Problem / risk:
- Config updates do not change SensorHub behavior without restart.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-007.
Goal: Ensure sensor loop applies updated config on /api/config reload.
Scope: /home/sahin/sera_panel/app_legacy.py.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (20-50 lines).
DoD:
- Config changes take effect without process restart.
- Sensor thread restarts cleanly without leaks.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan SensorHub.start and reload_runtime.
2) Implement safe restart or live config read.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- Sensor config changes apply immediately.
Related files:
- `app_legacy.py`: `def reload_runtime(new_cfg: Dict[str, Any]):`
- `app_legacy.py`: `def start(self, cfg: Dict[str, Any]):`
Notes / assumptions:
- The loop uses the initial cfg argument.

## ITEM-008: Add stale sensor fail-safe
Problem / risk:
- No auto-off happens when sensor data stops updating.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 3, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-008.
Goal: Add stale detection and auto-off for heater/pump when sensor data is old.
Scope: /home/sahin/sera_panel/app_legacy.py.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (30-70 lines).
DoD:
- Stale data triggers an automatic OFF for critical relays.
- Stale threshold is configurable with safe defaults.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan sensor update timestamps and relay control paths.
2) Implement stale detection and auto-off logic.
3) Show git diff.
4) Run verification command(s).
5) Report results and any new config fields.
```
DoD (acceptance criteria):
- Heater/pump are disabled when sensor data is stale.
Related files:
- `app_legacy.py`: `self.data["last_update"] = now`
- `app_legacy.py`: `def api_relay(relay_key: str):`
Notes / assumptions:
- No stale check exists today.

## ITEM-009: Add pump/heater cooldown enforcement
Problem / risk:
- Repeated activations can happen without cooldown.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 3, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-009.
Goal: Enforce cooldown intervals for pump and heater actions.
Scope: /home/sahin/sera_panel/app_legacy.py and /home/sahin/sera_panel/config.json (if adding defaults).
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (30-70 lines).
DoD:
- Cooldown blocks repeated ON within the configured window.
- API returns remaining cooldown seconds.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
- python3 -m json.tool /home/sahin/sera_panel/config.json
Process:
1) Scan current safety flow for pump/heater.
2) Add cooldown tracking and config defaults.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- Cooldown is enforced and visible in API response.
Related files:
- `app_legacy.py`: `if rinfo.get("type") == "pump":`
- `config.json`: `"safety": { ... }`
Notes / assumptions:
- Max duration exists; cooldown does not.

## ITEM-010: Add audit/event log for relay and safety actions
Problem / risk:
- There is no record of relay or safety actions.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-010.
Goal: Add a minimal audit log for relay and safety actions.
Scope: /home/sahin/sera_panel/app_legacy.py.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (30-70 lines).
DoD:
- Each relay action and safety change is logged with timestamp and actor (if known).
- Log is accessible via a read-only endpoint or status payload.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan relay and safety endpoints.
2) Add audit log structure and append entries.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- Audit log is visible and updates on actions.
Related files:
- `app_legacy.py`: `def api_safety():`
- `app_legacy.py`: `def api_relay(relay_key: str):`
Notes / assumptions:
- This folder has no logging module usage today.

## ITEM-011: Add sensor log persistence
Problem / risk:
- Sensor readings are not stored on disk.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort L
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-011.
Goal: Persist sensor readings to a CSV or SQLite file with a small schema.
Scope: /home/sahin/sera_panel/app_legacy.py (and create /home/sahin/sera_panel/data if needed).
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Large (80-160 lines).
DoD:
- Sensor readings are written on a fixed interval.
- Writes do not block the sensor loop.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan SensorHub data structure and update loop.
2) Implement safe persistence with minimal overhead.
3) Show git diff.
4) Run verification command(s).
5) Report results and file paths.
```
DoD (acceptance criteria):
- Data persists across restarts.
Related files:
- `app_legacy.py`: `self.data = { ... }`
Notes / assumptions:
- No data storage exists today.

## ITEM-012: Add log retention/rotation
Problem / risk:
- Log storage can grow without limits.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-012.
Goal: Add retention rules for sensor logs (by days or size).
Scope: /home/sahin/sera_panel/app_legacy.py (and log storage path).
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (20-60 lines).
DoD:
- Old logs are pruned or rotated automatically.
- Retention settings are configurable.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan how logs are stored (from ITEM-011).
2) Add retention logic that is safe and fast.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- Log growth is bounded.
Related files:
- `app_legacy.py`: (log write code added in ITEM-011)
Notes / assumptions:
- Depends on ITEM-011 implementation.

## ITEM-013: Add /api/history endpoint
Problem / risk:
- No history endpoint means no charts or trends.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-013.
Goal: Expose a read-only history endpoint for persisted sensor data.
Scope: /home/sahin/sera_panel/app_legacy.py.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (30-80 lines).
DoD:
- API supports time range and returns ordered samples.
- Endpoint is read-only and safe.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan persistence layout from ITEM-011.
2) Implement history endpoint with filters.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- History endpoint returns data for a specified range.
Related files:
- `app_legacy.py`: `@app.route("/api/status")`
Notes / assumptions:
- Depends on persisted logs.

## ITEM-014: Improve UI for stale data and errors
Problem / risk:
- Sensor errors are not prominent; stale data is not indicated.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-014.
Goal: Improve UI signal for stale data and sensor errors.
Scope: /home/sahin/sera_panel/static/app.js and /home/sahin/sera_panel/static/style.css.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Small (10-30 lines).
DoD:
- Stale data is visually flagged.
- Sensor errors are emphasized.
Tests/verification:
- No runtime tests required; update UI logic and styles.
Process:
1) Scan current UI rendering.
2) Add stale/error indicators with minimal UI changes.
3) Show git diff.
4) Report results.
```
DoD (acceptance criteria):
- Operators can spot stale/error states at a glance.
Related files:
- `static/app.js`: `renderSensors(st.sensors || {})`
- `static/style.css`: `.sensor-err{...}`
Notes / assumptions:
- Backend provides err fields already.

## ITEM-015: Make pump lock and limits explicit in UI
Problem / risk:
- Pump safety rules are not fully visible on the panel.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-015.
Goal: Show pump lock state, max duration, and (future) cooldown in the UI.
Scope: /home/sahin/sera_panel/static/app.js and /home/sahin/sera_panel/templates/index.html.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Small (10-25 lines).
DoD:
- Pump safety info is visible without scrolling.
- Text is clear and concise.
Tests/verification:
- No runtime tests required.
Process:
1) Scan pump card in HTML and JS.
2) Add UI fields and populate from /api/status.
3) Show git diff.
4) Report results.
```
DoD (acceptance criteria):
- Pump safety details are visible and accurate.
Related files:
- `templates/index.html`: `id="pumpUnlock"`
- `static/app.js`: `setText("pumpMax", pumpMax)`
Notes / assumptions:
- Cooldown will be added in ITEM-009.

## ITEM-016: Consolidate config sources (relays vs channels)
Problem / risk:
- Duplicate config sources can drift and cause incorrect pin maps.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-016.
Goal: Make a single source of truth for channel/relay mapping.
Scope: /home/sahin/sera_panel/config.json, /home/sahin/sera_panel/config/channels.json, and /home/sahin/sera_panel/app_legacy.py.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (20-80 lines).
DoD:
- Only one mapping file is required.
- App reads from the chosen source consistently.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
- python3 -m json.tool /home/sahin/sera_panel/config.json
Process:
1) Scan current config usage.
2) Choose the canonical source and update code/docs accordingly.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- Mapping drift is eliminated.
Related files:
- `config.json`: `"relays": { ... }`
- `config/channels.json`: `"channels": { ... }`
Notes / assumptions:
- Avoid touching files outside /home/sahin/sera_panel.

## ITEM-017: Add local README for this folder
Problem / risk:
- No in-folder runbook exists for this module.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 1, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-017.
Goal: Create a README with run instructions, safety notes, and test tool usage.
Scope: /home/sahin/sera_panel/README.md (new).
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Small (new file, 60-120 lines).
DoD:
- README covers run, config, and safety basics.
- Includes warnings about relay scripts.
Tests/verification:
- No tests required.
Process:
1) Scan existing docs in this folder.
2) Write a concise README using ASCII text.
3) Show git diff.
4) Report results.
```
DoD (acceptance criteria):
- README explains how to run and stay safe.
Related files:
- `app_legacy.py`: `if __name__ == "__main__":`
Notes / assumptions:
- Keep content consistent with app_legacy behavior.

## ITEM-018: Add dependency list for this folder
Problem / risk:
- Dependencies are not documented in this folder.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 1, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-018.
Goal: Add a requirements.txt or document dependencies in README.
Scope: /home/sahin/sera_panel/requirements.txt or /home/sahin/sera_panel/README.md.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Small (new file or doc update).
DoD:
- Dependencies required by app_legacy.py are listed clearly.
Tests/verification:
- No tests required.
Process:
1) Scan imports in app_legacy.py and tools.
2) Add dependency list.
3) Show git diff.
4) Report results.
```
DoD (acceptance criteria):
- Dependency list is present and accurate.
Related files:
- `app_legacy.py`: `import adafruit_bh1750` and other hardware libs
Notes / assumptions:
- Do not install packages in this step.

## ITEM-019: Add systemd unit example
Problem / risk:
- Service management is manual and not documented.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-019.
Goal: Add a sample systemd unit file for app_legacy.py.
Scope: /home/sahin/sera_panel/systemd/sera-panel.service (new) and /home/sahin/sera_panel/README.md.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (new file + doc).
DoD:
- Unit file uses correct WorkingDirectory and ExecStart.
- README explains how to install it.
Tests/verification:
- No systemctl commands in this step.
Process:
1) Scan current run instructions.
2) Add a sample unit file with placeholders.
3) Show git diff.
4) Report results.
```
DoD (acceptance criteria):
- Service unit example is available for ops.
Related files:
- `app_legacy.py`: `if __name__ == "__main__":`
Notes / assumptions:
- Do not enable or start services in this step.

## ITEM-020: Add /api/health endpoint
Problem / risk:
- No lightweight health endpoint exists for monitoring.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 1, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-020.
Goal: Add a minimal health endpoint that returns ok without sensor reads.
Scope: /home/sahin/sera_panel/app_legacy.py.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Small (5-15 lines).
DoD:
- /api/health returns a JSON ok response.
Tests/verification:
- python3 -m py_compile /home/sahin/sera_panel/app_legacy.py
Process:
1) Scan existing routes.
2) Add a simple health route.
3) Show git diff.
4) Run verification command(s).
5) Report results.
```
DoD (acceptance criteria):
- Health endpoint exists and is fast.
Related files:
- `app_legacy.py`: `@app.route("/api/status")`
Notes / assumptions:
- Health should not depend on hardware.

## ITEM-021: Add unit tests for SafetyManager
Problem / risk:
- Safety logic is not covered by tests.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-021.
Goal: Add pytest tests for SafetyManager behavior.
Scope: /home/sahin/sera_panel/tests/test_safety.py (new) and /home/sahin/sera_panel/app_legacy.py (importable).
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (new test file, 40-120 lines).
DoD:
- Tests cover test_mode, estop, and pump lock cases.
- Tests run without hardware.
Tests/verification:
- python3 -m pytest -q /home/sahin/sera_panel/tests
Process:
1) Scan SafetyManager code and design tests with no hardware.
2) Add tests with clear assertions.
3) Show git diff.
4) Run pytest.
5) Report results.
```
DoD (acceptance criteria):
- SafetyManager tests pass locally.
Related files:
- `app_legacy.py`: `class SafetyManager:`
Notes / assumptions:
- Tests should not import gpiozero or hardware libs.

## ITEM-022: Add unit tests for config validation
Problem / risk:
- validate_config has no automated coverage.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-022.
Goal: Add pytest tests for validate_config edge cases.
Scope: /home/sahin/sera_panel/tests/test_config.py (new) and /home/sahin/sera_panel/app_legacy.py.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (new test file, 40-120 lines).
DoD:
- Tests cover duplicate GPIO, reserved pins, and DHT conflicts.
Tests/verification:
- python3 -m pytest -q /home/sahin/sera_panel/tests
Process:
1) Scan validate_config behavior.
2) Add unit tests with explicit expected errors.
3) Show git diff.
4) Run pytest.
5) Report results.
```
DoD (acceptance criteria):
- validate_config tests pass locally.
Related files:
- `app_legacy.py`: `def validate_config(cfg: Dict[str, Any]) -> Optional[str]:`
Notes / assumptions:
- Use minimal config fixtures in tests.

## ITEM-023: Add API contract tests for /api/status and /api/relay
Problem / risk:
- API contract changes can break the UI silently.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 1, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-023.
Goal: Add Flask test client tests for key API routes.
Scope: /home/sahin/sera_panel/tests/test_api.py (new) and /home/sahin/sera_panel/app_legacy.py.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (new test file, 60-150 lines).
DoD:
- /api/status returns required keys.
- /api/relay rejects invalid actions.
Tests/verification:
- python3 -m pytest -q /home/sahin/sera_panel/tests
Process:
1) Scan routes and define expected schema.
2) Add tests using Flask test client and mocks.
3) Show git diff.
4) Run pytest.
5) Report results.
```
DoD (acceptance criteria):
- API tests pass and validate contract.
Related files:
- `app_legacy.py`: `@app.route("/api/status")`
- `app_legacy.py`: `@app.route("/api/relay/<relay_key>")`
Notes / assumptions:
- Mock RelayDriver to avoid hardware access.

## ITEM-024: Add tests for auto-off timers
Problem / risk:
- Auto-off timers are safety critical and untested.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort M
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-024.
Goal: Add tests verifying timer-based auto-off behavior.
Scope: /home/sahin/sera_panel/tests/test_timers.py (new) and /home/sahin/sera_panel/app_legacy.py.
Safety: SAFE-OFF. Do not trigger hardware actions.
Expected diff: Medium (new test file, 60-150 lines).
DoD:
- Tests simulate timer callbacks without waiting real time.
- Auto-off triggers are verified.
Tests/verification:
- python3 -m pytest -q /home/sahin/sera_panel/tests
Process:
1) Scan SafetyManager.arm_auto_off.
2) Design tests using a mock timer or injected timer factory.
3) Show git diff.
4) Run pytest.
5) Report results.
```
DoD (acceptance criteria):
- Timer tests pass and validate auto-off.
Related files:
- `app_legacy.py`: `def arm_auto_off(self, relay_key: str, seconds: int, off_fn)`
Notes / assumptions:
- Tests must not sleep in real time.

## ITEM-025: Align relay test scripts with active_low config
Problem / risk:
- Relay test scripts assume active-low behavior and do not consult config.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort S
Recommendation:
```
You are gpt-5.1-codex-max (reasoning high). Task: ITEM-025.
Goal: Make relay test scripts aware of active_low or require explicit confirmation.
Scope: /home/sahin/sera_panel/relay_click_test.sh and /home/sahin/sera_panel/relay_polarity_test.sh.
Safety: SAFE-OFF. Do not run the scripts during implementation.
Expected diff: Small (10-30 lines).
DoD:
- Scripts warn clearly about active_low assumptions.
- Optional: read active_low from config.json.
Tests/verification:
- Shell check only: `bash -n /home/sahin/sera_panel/relay_click_test.sh`
Process:
1) Scan current script assumptions.
2) Add warnings or config read.
3) Show git diff.
4) Run shell syntax check.
5) Report results.
```
DoD (acceptance criteria):
- Scripts are safer to run with correct polarity.
Related files:
- `relay_click_test.sh`: `PINS=(18 23 24 25 20 21)`
- `config.json`: `"active_low": true`
Notes / assumptions:
- Do not execute hardware toggles in this change.
