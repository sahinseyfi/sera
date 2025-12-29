# Report 02 - Security and Safety Audit

## Finding 02-01: Control endpoints have no authentication
Problem / risk:
- Any network client can call relay, safety, config, I2C scan, or all-off endpoints. This is a direct safety and security risk on a LAN.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 4, Effort M
Recommendation:
- Add an admin token or local-network restriction for all control endpoints.
DoD (acceptance criteria):
- Unauthorized requests to control endpoints are rejected with 401/403.
Related files:
- `app_legacy.py`: `@app.route("/api/relay/<relay_key>", methods=["POST"])`
- `app_legacy.py`: `@app.route("/api/config", methods=["GET", "POST"])`
Notes / assumptions:
- No auth checks exist in `app_legacy.py`.

## Finding 02-02: Test mode is required but publicly toggleable
Problem / risk:
- `test_mode` is the main safety gate, but any client can enable it via `/api/safety` and then control relays.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 4, Effort M
Recommendation:
- Restrict `/api/safety` to admin access; optionally add a physical or local-only requirement.
DoD (acceptance criteria):
- Only authorized users can enable `test_mode` or unlock the pump.
Related files:
- `app_legacy.py`: `def api_safety():`
- `app_legacy.py`: `safety.set_test_mode(bool(body["test_mode"]))`
Notes / assumptions:
- The UI also stores an admin token but the backend ignores it.

## Finding 02-03: E-stop is not persisted
Problem / risk:
- E-stop state is stored only in memory; after a process restart, relays may be controllable again without an explicit reset.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 3, Effort M
Recommendation:
- Persist E-stop state in config or a small state file, and require manual reset on boot.
DoD (acceptance criteria):
- After restart, E-stop state is restored or requires explicit reset.
Related files:
- `app_legacy.py`: `class SafetyState:`
- `app_legacy.py`: `self.state = SafetyState()`
Notes / assumptions:
- No persistence layer is present in this folder.

## Finding 02-04: Pump lock exists but no cooldown enforcement
Problem / risk:
- Pump is lockable and time limited, but there is no cooldown enforcement between runs.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 3, Effort M
Recommendation:
- Add a cooldown timer and reject pump on commands during cooldown.
DoD (acceptance criteria):
- Pump cannot be re-activated within the configured cooldown window.
Related files:
- `app_legacy.py`: `if relay_info.get("type") == "pump" and want_on:`
- `app_legacy.py`: `maxs = int(cfg.get("safety", {}).get("pump_max_on_sec", 3))`
Notes / assumptions:
- Only max duration is enforced today.

## Finding 02-05: Auto-off depends on unvalidated config values
Problem / risk:
- Heater/pump max durations are taken from config without range validation. A bad config could allow unsafe run times.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 3, Effort S
Recommendation:
- Clamp and validate safety values on load and on `/api/config` updates.
DoD (acceptance criteria):
- Unsafe values are rejected or clamped to safe bounds server-side.
Related files:
- `app_legacy.py`: `maxs = int(cfg.get("safety", {}).get("heater_max_on_sec", 10))`
- `app_legacy.py`: `def validate_config(cfg: Dict[str, Any]) -> Optional[str]:`
Notes / assumptions:
- `validate_config` does not check safety ranges today.

## Finding 02-06: Sensor fail-safe is not enforced
Problem / risk:
- There is no logic to turn off pump/heater when sensor data is stale or missing. This increases risk if sensors fail.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 3, Effort M
Recommendation:
- Add stale detection and auto-off for critical actuators.
DoD (acceptance criteria):
- If sensor updates exceed a threshold, pump/heater are disabled and a warning is emitted.
Related files:
- `app_legacy.py`: `self.data["last_update"] = now`
- `app_legacy.py`: `time.sleep(1.2)`
Notes / assumptions:
- No stale check exists in the relay control path.

## Finding 02-07: Relay click test stops services and uses sudo
Problem / risk:
- `relay_click_test.sh` stops services and toggles GPIO with sudo. Running it on a live system can disrupt production services.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 3, Effort S
Recommendation:
- Add a confirmation prompt and document safety steps before executing the script.
DoD (acceptance criteria):
- Script warns and requires confirmation before stopping services and toggling relays.
Related files:
- `relay_click_test.sh`: `systemctl stop "$s" || true`
- `relay_click_test.sh`: `sudo gpioset "${CHIP_ARGS[@]}" "${pin}=${val}" &`
Notes / assumptions:
- The script assumes active-low and does not read config.

## Finding 02-08: Hardware test tool bypasses config and auth
Problem / risk:
- `tools/sera_hw_panel.py` uses hardcoded GPIO pins and manual prompts; it does not use config or safety gate logic.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 3, Effort M
Recommendation:
- Align the tool with the active config or wrap it with explicit safety checks.
DoD (acceptance criteria):
- The tool reads pin mapping from config and enforces active_low consistently.
Related files:
- `tools/sera_hw_panel.py`: `RELAYS = [
    ("relay1_heater_fan", 18),`
- `tools/sera_hw_panel.py`: `OFF = 1 if args.active_low else 0`
Notes / assumptions:
- This tool is separate from Flask runtime safety controls.
