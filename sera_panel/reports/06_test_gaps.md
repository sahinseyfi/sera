# Report 06 - Test Gaps

## Finding 06-01: No automated tests in this folder
Problem / risk:
- There is no `tests/` directory or test files in `/home/sahin/sera_panel`, which leaves safety-critical logic unverified.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 3, Effort M
Recommendation:
- Add a small pytest suite with unit tests for SafetyManager and config validation.
DoD (acceptance criteria):
- `python -m pytest -q` runs at least a few safety tests.
Related files:
- `app_legacy.py`: `class SafetyManager:`
- `.pytest_cache/README.md`: `This directory contains data from the pytest's cache plugin.`
Notes / assumptions:
- Presence of `.pytest_cache` suggests tests were run elsewhere, but no test files exist here.

## Finding 06-02: Safety gates are not tested
Problem / risk:
- The safety gate logic (test_mode, estop, pump lock) is not covered by automated tests.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 3, Effort M
Recommendation:
- Add unit tests for `SafetyManager.can_switch` covering all safety states.
DoD (acceptance criteria):
- Tests cover test_mode false, estop true, and pump locked cases.
Related files:
- `app_legacy.py`: `def can_switch(self, relay_key: str, relay_info: Dict[str, Any], want_on: bool)`
Notes / assumptions:
- No tests exist for SafetyManager in this folder.

## Finding 06-03: Config validation is not tested
Problem / risk:
- `validate_config` is a critical guardrail but lacks automated tests, increasing risk of misconfig regressions.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Add tests for duplicate GPIO, reserved pins, and DHT conflicts.
DoD (acceptance criteria):
- Validation rejects invalid configs with clear error strings.
Related files:
- `app_legacy.py`: `def validate_config(cfg: Dict[str, Any]) -> Optional[str]:`
Notes / assumptions:
- Validation logic is purely code-based and not exercised by tests.

## Finding 06-04: API contract is not tested
Problem / risk:
- There is no test to validate `/api/status` output shape or `/api/relay` error handling.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Add Flask test client tests for status and relay endpoints using a mocked RelayDriver.
DoD (acceptance criteria):
- Tests cover success and error paths for key endpoints.
Related files:
- `app_legacy.py`: `@app.route("/api/status")`
- `app_legacy.py`: `@app.route("/api/relay/<relay_key>", methods=["POST"])`
Notes / assumptions:
- The Flask app uses global state which will need test isolation.

## Finding 06-05: Data quality and sensor loop are untested
Problem / risk:
- The sensor loop is complex (I2C, DS18B20, DHT) but has no unit tests or simulation harness.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 3, Effort L
Recommendation:
- Add a simulation mode or dependency injection to test the loop without hardware.
DoD (acceptance criteria):
- SensorHub can run in a mocked environment and produce deterministic output.
Related files:
- `app_legacy.py`: `class SensorHub:`
- `app_legacy.py`: `import adafruit_bh1750`
Notes / assumptions:
- Hardware access is required for the current implementation.

## Finding 06-06: Roadmap documents tests but none exist here
Problem / risk:
- Docs list expected validation checks for `/api/status` and safety behavior, but there are no implemented tests in this folder.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort M
Recommendation:
- Convert roadmap test bullets into executable tests in a `tests/` directory.
DoD (acceptance criteria):
- At least 3 roadmap test bullets are mapped to automated tests.
Related files:
- `yol_haritasi.md`: `"/api/status"`
- `yol_haritasi.md`: `"/api/actuator"`
Notes / assumptions:
- The roadmap references API endpoints that are not in `app_legacy.py`.
