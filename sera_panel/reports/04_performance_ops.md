# Report 04 - Performance and Operations

## Finding 04-01: Sensor loop does not enforce per-sensor timeouts
Problem / risk:
- A slow or hung sensor call blocks the entire loop, reducing update frequency for all sensors.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Add per-sensor timeouts or isolate sensors into separate threads.
DoD (acceptance criteria):
- One sensor failure does not stall the overall loop.
Related files:
- `app_legacy.py`: `def _loop(self, cfg: Dict[str, Any]):`
- `app_legacy.py`: `time.sleep(1.2)`
Notes / assumptions:
- All reads occur in the same thread.

## Finding 04-02: DHT22 instance is re-created each loop
Problem / risk:
- Creating a DHT device object every iteration increases overhead and can contribute to transient errors.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort S
Recommendation:
- Reuse the DHT instance or implement a cache with a safe refresh interval.
DoD (acceptance criteria):
- DHT object creation is not repeated every loop iteration.
Related files:
- `app_legacy.py`: `dht = adafruit_dht.DHT22(pin_obj)`
- `app_legacy.py`: `if not cfg.get("sensors", {}).get("dht22_enabled", False):`
Notes / assumptions:
- The DHT block runs inside the loop.

## Finding 04-03: I2C scan may be slow and is unauthenticated
Problem / risk:
- `i2cdetect` is invoked from the API. This can be slow and requires system access. Without auth, it is exposed to any client.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 3, Effort S
Recommendation:
- Protect the endpoint and add a timeout or throttle.
DoD (acceptance criteria):
- I2C scan cannot be triggered by unauthorized users and has an explicit timeout.
Related files:
- `app_legacy.py`: `@app.route("/api/i2c-scan", methods=["POST"])`
- `app_legacy.py`: `subprocess.check_output(["i2cdetect", "-y", str(bus_num)], text=True)`
Notes / assumptions:
- The API does not enforce rate limits.

## Finding 04-04: No structured logging setup
Problem / risk:
- Operational visibility is limited because the code does not configure structured logs or log rotation.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort M
Recommendation:
- Add Python logging with a rotating file handler and log safety events.
DoD (acceptance criteria):
- Logs include sensor errors, relay actions, and safety transitions.
Related files:
- `app_legacy.py`: `import time` (no `import logging`)
Notes / assumptions:
- Logging is currently implicit via print statements or none.

## Finding 04-05: No explicit health endpoint
Problem / risk:
- There is no lightweight health check endpoint for systemd or monitoring tools, which complicates automated restarts or alerts.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 1, Effort S
Recommendation:
- Add a minimal `/api/health` endpoint that returns "ok" and build metadata.
DoD (acceptance criteria):
- Health checks can be performed without sensor reads.
Related files:
- `app_legacy.py`: `@app.route("/api/status")`
Notes / assumptions:
- Only status/config/safety endpoints exist today.

## Finding 04-06: No in-folder service unit or ops guide
Problem / risk:
- There is no systemd unit or ops guide in this folder, so deployment steps are tribal knowledge.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort M
Recommendation:
- Add a systemd service example and a small runbook for start/stop/restart.
DoD (acceptance criteria):
- A documented service unit exists alongside the code.
Related files:
- `app_legacy.py`: `if __name__ == "__main__":` (manual run only)
Notes / assumptions:
- No `systemd/` directory exists under `/home/sahin/sera_panel`.
