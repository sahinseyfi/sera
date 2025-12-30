import os
import time

os.environ.setdefault("SIMULATION_MODE", "1")
os.environ.setdefault("DISABLE_BACKGROUND_LOOPS", "1")

import app  # noqa: E402  pylint: disable=wrong-import-position


def test_status_endpoint():
    client = app.app.test_client()
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "sensor_readings" in data
    assert "actuator_state" in data
    assert "notifications" in data
    assert "retention" in data
    assert data["safe_mode"] is True


def test_safe_mode_blocks_manual_control():
    client = app.app.test_client()
    resp = client.post("/api/actuator/R3_PUMP", json={"state": "on", "seconds": 3})
    assert resp.status_code == 403


def test_pump_rules_and_limits():
    client = app.app.test_client()
    # disable safe mode for control
    resp = client.post("/api/settings", json={"safe_mode": False})
    assert resp.status_code == 200

    # missing seconds should fail
    resp = client.post("/api/actuator/R3_PUMP", json={"state": "on"})
    assert resp.status_code == 403

    # valid duration works
    resp = client.post("/api/actuator/R3_PUMP", json={"state": "on", "seconds": 3})
    assert resp.status_code == 200

    # emergency stop updates cooldown timestamp
    client.post("/api/emergency_stop")
    resp = client.post("/api/actuator/R3_PUMP", json={"state": "on", "seconds": 3})
    assert resp.status_code == 403
    time.sleep(1)


def test_notifications_test_endpoint_blocked_in_simulation():
    client = app.app.test_client()
    resp = client.post("/api/notifications/test", json={"message": "hello"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["sent"] is False
    assert body["reason"] == "simulation_blocked"
