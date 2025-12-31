import os

os.environ["SERAPANEL_SKIP_INIT"] = "1"

import app_legacy
from app_legacy import app, SafetyManager


class DummyRelayDriver:
    def state(self, key):
        return False


class DummySensors:
    def snapshot(self):
        return {"ok": True, "last_update": None, "errors": []}


def _setup_runtime():
    app_legacy.ADMIN_TOKEN = None
    app_legacy.cfg = {
        "relays": {
            "pump": {"gpio": 24, "type": "pump", "locked": False, "name": "Pump"}
        },
        "active_low": True,
        "safety": {},
        "sensors": {},
    }
    app_legacy.relay_driver = DummyRelayDriver()
    app_legacy.safety = SafetyManager()
    app_legacy.sensors = DummySensors()


def test_status_keys():
    _setup_runtime()
    client = app.test_client()
    res = client.get("/api/status", environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert res.status_code == 200
    data = res.get_json()
    for key in ("time", "safe_mode", "safety", "config", "relays", "sensors"):
        assert key in data
    assert "pump" in data["relays"]


def test_relay_rejects_invalid_action():
    _setup_runtime()
    client = app.test_client()
    res = client.post(
        "/api/relay/pump",
        json={"action": "bad"},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert res.status_code == 400
    data = res.get_json()
    assert "invalid action" in (data.get("error") or "")
