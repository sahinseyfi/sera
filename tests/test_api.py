import os
import time

import pytest

os.environ.setdefault("SIMULATION_MODE", "1")
os.environ.setdefault("DISABLE_BACKGROUND_LOOPS", "1")

import app  # noqa: E402  pylint: disable=wrong-import-position


@pytest.fixture(autouse=True)
def reset_node_rate_limits():
    app.NODE_RATE_LIMIT.clear()
    app.NODE_COMMAND_RATE_LIMIT.clear()
    yield
    app.NODE_RATE_LIMIT.clear()
    app.NODE_COMMAND_RATE_LIMIT.clear()


def test_status_endpoint():
    client = app.app.test_client()
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "sensor_readings" in data
    assert "actuator_state" in data
    assert "zones" in data
    assert "sensors" in data
    assert "actuators" in data
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


def test_clear_automation_override():
    engine = app.automation_engine
    original_until = engine.manual_override_until_ts
    original_cancel = engine.manual_override_cancel_ts
    try:
        engine.manual_override_until_ts = time.time() + 120
        engine.manual_override_cancel_ts = 0.0
        client = app.app.test_client()
        resp = client.post("/api/automation/override", json={"scope": "lux", "action": "clear"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert "lux" in (body.get("cleared") or [])
        assert engine.manual_override_until_ts == 0.0
        assert engine.manual_override_cancel_ts > 0
    finally:
        engine.manual_override_until_ts = original_until
        engine.manual_override_cancel_ts = original_cancel


def test_role_based_pump_requires_seconds():
    custom_name = "R9_WATER"
    manager = app.actuator_manager
    try:
        manager.channels[custom_name] = {
            "name": custom_name,
            "gpio_pin": 99,
            "active_low": True,
            "description": "Test Pump",
            "role": "pump",
            "enabled": True,
        }
        manager.state[custom_name] = {
            "state": False,
            "last_change_ts": None,
            "reason": "test",
            "description": "Test Pump",
        }
        manager.last_stop_ts[custom_name] = 0.0
        client = app.app.test_client()
        resp = client.post("/api/settings", json={"safe_mode": False})
        assert resp.status_code == 200
        resp = client.post(f"/api/actuator/{custom_name}", json={"state": "on"})
        assert resp.status_code == 403
        body = resp.get_json()
        assert "seconds" in body.get("error", "").lower()
    finally:
        manager.channels.pop(custom_name, None)
        manager.state.pop(custom_name, None)
        manager.last_stop_ts.pop(custom_name, None)
        app.app_state.safe_mode = True


def test_daily_limit_enforced(tmp_path):
    original_db = app.DB_PATH
    original_catalog = app.catalog_config
    try:
        app.DB_PATH = tmp_path / "sera.db"
        app.init_db()
        app.catalog_config = {
            "actuators": [
                {"id": "R2_FAN_MAIN", "max_daily_s": 1, "role": "fan"},
            ]
        }
        client = app.app.test_client()
        resp = client.post("/api/settings", json={"safe_mode": False})
        assert resp.status_code == 200
        resp = client.post("/api/actuator/R2_FAN_MAIN", json={"state": "on", "seconds": 1})
        assert resp.status_code == 200
        client.post("/api/actuator/R2_FAN_MAIN", json={"state": "off"})
        resp = client.post("/api/actuator/R2_FAN_MAIN", json={"state": "on", "seconds": 1})
        assert resp.status_code == 403
        body = resp.get_json()
        assert "Daily limit" in body.get("error", "")
    finally:
        app.DB_PATH = original_db
        app.catalog_config = original_catalog
        app.init_db()
        app.app_state.safe_mode = True


def test_notifications_test_endpoint_blocked_in_simulation():
    client = app.app.test_client()
    resp = client.post("/api/notifications/test", json={"message": "hello"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["sent"] is False
    assert body["reason"] == "simulation_blocked"


def test_trends_endpoint_telemetry(tmp_path):
    original_db = app.DB_PATH
    try:
        app.DB_PATH = tmp_path / "sera.db"
        app.init_db()
        app._log_telemetry_rows(
            "kat1-node",
            "kat1",
            time.time(),
            [{"id": "kat1-temp", "metric": "temp_c", "value": 24.2}],
        )
        client = app.app.test_client()
        resp = client.get("/api/trends?zone=kat1&metric=temp_c&hours=1")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["metric"] == "temp_c"
        assert body["points"]
    finally:
        app.DB_PATH = original_db
        app.init_db()


def test_trends_endpoint_downsample_max_points(tmp_path):
    original_db = app.DB_PATH
    try:
        app.DB_PATH = tmp_path / "sera.db"
        app.init_db()
        base_ts = time.time() - 1200
        for idx in range(30):
            app._log_telemetry_rows(
                "kat1-node",
                "kat1",
                base_ts + idx,
                [{"id": "kat1-temp", "metric": "temp_c", "value": 20 + idx}],
            )
        client = app.app.test_client()
        resp = client.get("/api/trends?zone=kat1&metric=temp_c&hours=1&max_points=5")
        assert resp.status_code == 200
        body = resp.get_json()
        points = body["points"]
        assert len(points) <= 5
        assert points[-1][1] == 49
    finally:
        app.DB_PATH = original_db
        app.init_db()


def test_trends_endpoint_csv(tmp_path):
    original_db = app.DB_PATH
    try:
        app.DB_PATH = tmp_path / "sera.db"
        app.init_db()
        base_ts = time.time() - 30
        app._log_telemetry_rows(
            "kat1-node",
            "kat1",
            base_ts,
            [{"id": "kat1-temp", "metric": "temp_c", "value": 24.2}],
        )
        app._log_telemetry_rows(
            "kat1-node",
            "kat1",
            base_ts + 10,
            [{"id": "kat1-temp", "metric": "temp_c", "value": 24.8}],
        )
        client = app.app.test_client()
        resp = client.get("/api/trends?zone=kat1&metric=temp_c&hours=1&format=csv")
        assert resp.status_code == 200
        text = resp.data.decode()
        lines = [line for line in text.strip().splitlines() if line]
        assert lines[0].startswith("ts,temp_c")
        assert len(lines) == 3
    finally:
        app.DB_PATH = original_db
        app.init_db()


def test_trends_summary_telemetry(tmp_path):
    original_db = app.DB_PATH
    try:
        app.DB_PATH = tmp_path / "sera.db"
        app.init_db()
        base_ts = time.time() - 60
        app._log_telemetry_rows(
            "kat1-node",
            "kat1",
            base_ts,
            [{"id": "kat1-temp", "metric": "temp_c", "value": 21.5}],
        )
        app._log_telemetry_rows(
            "kat1-node",
            "kat1",
            base_ts + 10,
            [{"id": "kat1-temp", "metric": "temp_c", "value": 24.0}],
        )
        client = app.app.test_client()
        resp = client.get("/api/trends?zone=kat1&metric=temp_c&hours=1&summary=1")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["source"] == "telemetry"
        assert body["count"] == 2
        assert body["min"] == pytest.approx(21.5)
        assert body["max"] == pytest.approx(24.0)
        assert body["last"] == pytest.approx(24.0)
    finally:
        app.DB_PATH = original_db
        app.init_db()


def test_trends_summary_fallback_sensor_log(tmp_path):
    original_db = app.DB_PATH
    try:
        app.DB_PATH = tmp_path / "sera.db"
        app.init_db()
        conn = app.sqlite3.connect(app.DB_PATH)
        cur = conn.cursor()
        now = time.time()
        cur.execute(
            """
            INSERT INTO sensor_log (
                ts, dht_temp, dht_hum, ds18_temp, lux, soil_ch0, soil_ch1, soil_ch2, soil_ch3
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (now, 22.5, 55.0, None, 110.0, 900.0, None, None, None),
        )
        conn.commit()
        conn.close()
        client = app.app.test_client()
        resp = client.get("/api/trends?metric=temp_c&hours=1&summary=1")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["source"] == "sensor_log"
        assert body["count"] == 1
        assert body["last"] == pytest.approx(22.5)
    finally:
        app.DB_PATH = original_db
        app.init_db()


def test_trends_endpoint_fallback_sensor_log(tmp_path):
    original_db = app.DB_PATH
    try:
        app.DB_PATH = tmp_path / "sera.db"
        app.init_db()
        conn = app.sqlite3.connect(app.DB_PATH)
        cur = conn.cursor()
        now = time.time()
        cur.execute(
            """
            INSERT INTO sensor_log (
                ts, dht_temp, dht_hum, ds18_temp, lux, soil_ch0, soil_ch1, soil_ch2, soil_ch3
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (now, 21.5, 55.0, None, 120.0, 1000.0, None, None, None),
        )
        conn.commit()
        conn.close()
        client = app.app.test_client()
        resp = client.get("/api/trends?metric=temp_c&hours=1")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["metric"] == "temp_c"
        assert body["points"]
    finally:
        app.DB_PATH = original_db
        app.init_db()


def test_telemetry_endpoint_accepts_payload():
    client = app.app.test_client()
    payload = {
        "node_id": "kat1-node",
        "zone": "kat1",
        "ts": time.time(),
        "sensors": [
            {"id": "kat1-temp", "metric": "temp_c", "value": 24.1, "quality": "ok"},
            {"id": "kat1-lux", "metric": "lux", "value": 123.0, "quality": "ok"},
        ],
        "status": {"uptime_s": 10, "fw": "0.1.0"},
    }
    resp = client.post("/api/telemetry", json=payload)
    assert resp.status_code == 200
    body = resp.get_json()
    assert "acks" in body
    assert "errors" in body


def test_node_registry_health_in_status():
    client = app.app.test_client()
    payload = {
        "node_id": "kat1-node",
        "zone": "kat1",
        "ts": time.time(),
        "sensors": [
            {"id": "kat1-temp", "metric": "temp_c", "value": 24.1, "quality": "ok"},
        ],
        "status": {"uptime_s": 10, "fw": "0.1.0"},
    }
    resp = client.post("/api/telemetry", json=payload)
    assert resp.status_code == 200
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    nodes = data.get("nodes", [])
    entry = next((node for node in nodes if node.get("node_id") == "kat1-node"), None)
    assert entry is not None
    health = entry.get("health", {})
    assert "status" in health
    assert "data_age_sec" in health


def test_nodes_endpoint_reports_queue_size():
    node_id = "kat1-node"
    original_registry = app.NODE_REGISTRY.get(node_id)
    original_queue = app.NODE_COMMANDS.get(node_id)
    try:
        client = app.app.test_client()
        payload = {
            "node_id": node_id,
            "zone": "kat1",
            "ts": time.time(),
            "sensors": [],
        }
        resp = client.post("/api/telemetry", json=payload)
        assert resp.status_code == 200
        app.NODE_COMMANDS[node_id] = [
            {"cmd_id": "queued", "created_ts": time.time(), "ttl_s": 0},
        ]
        resp = client.get("/api/nodes")
        assert resp.status_code == 200
        data = resp.get_json()
        entry = next((node for node in data.get("nodes", []) if node.get("node_id") == node_id), None)
        assert entry is not None
        assert entry.get("queue_size") == 1
    finally:
        if original_registry is None:
            app.NODE_REGISTRY.pop(node_id, None)
        else:
            app.NODE_REGISTRY[node_id] = original_registry
        if original_queue is None:
            app.NODE_COMMANDS.pop(node_id, None)
        else:
            app.NODE_COMMANDS[node_id] = original_queue


def test_remote_sensor_status_from_telemetry():
    original_catalog = app.catalog_config
    sensor_id = "kat1-env"
    node_id = "kat1-node"
    original_snapshot = app.NODE_SENSOR_STATE.get(sensor_id)
    try:
        app.catalog_config = {
            "version": 1,
            "zones": [{"id": "kat1", "label": "KAT1"}],
            "sensors": [
                {
                    "id": sensor_id,
                    "zone": "kat1",
                    "kind": "sht31",
                    "purpose": "temp_hum",
                    "node_id": node_id,
                }
            ],
            "actuators": [],
        }
        client = app.app.test_client()
        payload = {
            "node_id": node_id,
            "zone": "kat1",
            "ts": time.time(),
            "sensors": [
                {"id": sensor_id, "metric": "temp_c", "value": 23.5, "quality": "ok"},
                {"id": sensor_id, "metric": "rh_pct", "value": 60.0, "quality": "ok"},
            ],
        }
        resp = client.post("/api/telemetry", json=payload)
        assert resp.status_code == 200
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        sensors = data.get("sensors", [])
        entry = next((item for item in sensors if item.get("id") == sensor_id), None)
        assert entry is not None
        assert entry.get("status") == "ok"
        last_value = entry.get("last_value", {})
        assert last_value.get("temperature") == 23.5
        assert last_value.get("humidity") == 60.0
        health = data.get("sensor_health", {})
        health_entry = health.get(sensor_id) or {}
        assert health_entry.get("status") == "ok"
    finally:
        app.catalog_config = original_catalog
        if original_snapshot is None:
            app.NODE_SENSOR_STATE.pop(sensor_id, None)
        else:
            app.NODE_SENSOR_STATE[sensor_id] = original_snapshot


def test_node_commands_empty_returns_204():
    client = app.app.test_client()
    resp = client.get("/api/node_commands?node_id=kat1-node")
    assert resp.status_code in (200, 204)
    if resp.status_code == 200:
        body = resp.get_json()
        assert body["commands"] == []


def test_node_commands_blocked_in_safe_mode():
    client = app.app.test_client()
    resp = client.post(
        "/api/node_commands",
        json={"node_id": "kat1-node", "actuator_id": "kat1-fan", "state": "on"},
    )
    assert resp.status_code == 403


def test_node_commands_rate_limit():
    node_id = "kat1-node"
    original_limit = app.NODE_COMMAND_RATE_LIMIT_SECONDS
    original_map = dict(app.NODE_COMMAND_RATE_LIMIT)
    try:
        app.NODE_COMMAND_RATE_LIMIT_SECONDS = 10.0
        app.NODE_COMMAND_RATE_LIMIT.pop(node_id, None)
        client = app.app.test_client()
        resp = client.get(f"/api/node_commands?node_id={node_id}")
        assert resp.status_code in (200, 204)
        resp = client.get(f"/api/node_commands?node_id={node_id}")
        assert resp.status_code == 429
    finally:
        app.NODE_COMMAND_RATE_LIMIT_SECONDS = original_limit
        app.NODE_COMMAND_RATE_LIMIT.clear()
        app.NODE_COMMAND_RATE_LIMIT.update(original_map)


def test_node_commands_get_blocked_in_safe_mode():
    node_id = "kat1-node"
    original_queue = app.NODE_COMMANDS.get(node_id)
    try:
        app.NODE_COMMANDS[node_id] = [
            {"cmd_id": "queued", "created_ts": time.time(), "ttl_s": 0},
        ]
        client = app.app.test_client()
        resp = client.get(f"/api/node_commands?node_id={node_id}")
        assert resp.status_code == 204
        assert app.NODE_COMMANDS.get(node_id) == []
    finally:
        if original_queue is None:
            app.NODE_COMMANDS.pop(node_id, None)
        else:
            app.NODE_COMMANDS[node_id] = original_queue


def test_node_commands_default_since_filters_old():
    node_id = "kat1-node"
    original = app.NODE_COMMANDS.get(node_id)
    now = time.time()
    try:
        app.NODE_COMMANDS[node_id] = [
            {
                "cmd_id": "old",
                "actuator_id": "kat1-fan",
                "action": "set_state",
                "state": "on",
                "ttl_s": 0,
                "created_ts": now - 120,
            },
            {
                "cmd_id": "new",
                "actuator_id": "kat1-fan",
                "action": "set_state",
                "state": "on",
                "ttl_s": 0,
                "created_ts": now - 5,
            },
        ]
        client = app.app.test_client()
        resp = client.post("/api/settings", json={"safe_mode": False})
        assert resp.status_code == 200
        resp = client.get(f"/api/node_commands?node_id={node_id}")
        assert resp.status_code == 200
        body = resp.get_json()
        ids = [cmd["cmd_id"] for cmd in body["commands"]]
        assert "new" in ids
        assert "old" not in ids
    finally:
        if original is None:
            app.NODE_COMMANDS.pop(node_id, None)
        else:
            app.NODE_COMMANDS[node_id] = original
        app.app_state.safe_mode = True


def test_node_commands_enqueue_and_fetch():
    node_id = "kat1-node"
    original = app.NODE_COMMANDS.get(node_id)
    try:
        app.NODE_COMMANDS[node_id] = []
        client = app.app.test_client()
        resp = client.post("/api/settings", json={"safe_mode": False})
        assert resp.status_code == 200
        resp = client.post(
            "/api/node_commands",
            json={"node_id": node_id, "actuator_id": "kat1-fan", "state": "on"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        cmd_id = body.get("cmd_id")
        assert cmd_id
        resp = client.get(f"/api/node_commands?node_id={node_id}&since=0")
        assert resp.status_code == 200
        body = resp.get_json()
        ids = [cmd["cmd_id"] for cmd in body["commands"]]
        assert cmd_id in ids
    finally:
        if original is None:
            app.NODE_COMMANDS.pop(node_id, None)
        else:
            app.NODE_COMMANDS[node_id] = original
        app.app_state.safe_mode = True


def test_actuator_pwm_queues_node_command():
    original_catalog = app.catalog_config
    node_id = "kat1-node"
    original_queue = app.NODE_COMMANDS.get(node_id)
    try:
        app.catalog_config = {
            "actuators": [
                {"id": "kat1-light", "backend": "esp32", "node_id": node_id, "supports_pwm": True},
            ]
        }
        app.NODE_COMMANDS[node_id] = []
        client = app.app.test_client()
        resp = client.post("/api/settings", json={"safe_mode": False})
        assert resp.status_code == 200
        resp = client.post("/api/actuator/kat1-light", json={"duty_pct": 50})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["queued"] is True
        assert body.get("cmd_id")
        queue = app.NODE_COMMANDS.get(node_id, [])
        assert queue
        assert queue[-1]["action"] == "set_pwm"
        assert queue[-1]["duty_pct"] == 50.0
    finally:
        app.catalog_config = original_catalog
        if original_queue is None:
            app.NODE_COMMANDS.pop(node_id, None)
        else:
            app.NODE_COMMANDS[node_id] = original_queue
        app.app_state.safe_mode = True


def test_actuator_duty_pct_rejected_for_local():
    client = app.app.test_client()
    resp = client.post("/api/actuator/R2_FAN_MAIN", json={"duty_pct": 20})
    assert resp.status_code == 400


def test_remote_actuator_state_updates_on_ack():
    original_catalog = app.catalog_config
    node_id = "kat1-node"
    original_queue = app.NODE_COMMANDS.get(node_id)
    original_state = app.NODE_ACTUATOR_STATE.get("kat1-fan")
    try:
        app.catalog_config = {
            "version": 1,
            "zones": [{"id": "kat1", "label": "KAT1"}],
            "sensors": [],
            "actuators": [
                {"id": "kat1-fan", "zone": "kat1", "role": "fan", "backend": "esp32", "node_id": node_id},
            ],
        }
        app.NODE_COMMANDS[node_id] = []
        client = app.app.test_client()
        resp = client.post("/api/settings", json={"safe_mode": False})
        assert resp.status_code == 200
        resp = client.post("/api/actuator/kat1-fan", json={"state": "on"})
        assert resp.status_code == 200
        cmd_id = resp.get_json().get("cmd_id")
        assert cmd_id
        telemetry = {"node_id": node_id, "ts": time.time(), "sensors": [], "acks": [cmd_id]}
        resp = client.post("/api/telemetry", json=telemetry)
        assert resp.status_code == 200
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        actuators = data.get("actuators", [])
        entry = next((item for item in actuators if item.get("id") == "kat1-fan"), None)
        assert entry is not None
        assert entry.get("state") is True
        assert entry.get("reason") == "remote_ack"
    finally:
        app.catalog_config = original_catalog
        if original_queue is None:
            app.NODE_COMMANDS.pop(node_id, None)
        else:
            app.NODE_COMMANDS[node_id] = original_queue
        if original_state is None:
            app.NODE_ACTUATOR_STATE.pop("kat1-fan", None)
        else:
            app.NODE_ACTUATOR_STATE["kat1-fan"] = original_state
        app.app_state.safe_mode = True


def test_emergency_stop_queues_remote_off():
    original_catalog = app.catalog_config
    node_id = "kat1-node"
    original_queue = app.NODE_COMMANDS.get(node_id)
    try:
        app.catalog_config = {
            "actuators": [
                {"id": "kat1-light", "backend": "esp32", "node_id": node_id, "supports_pwm": True},
                {"id": "kat1-fan", "backend": "esp32", "node_id": node_id},
            ]
        }
        app.NODE_COMMANDS[node_id] = [
            {"cmd_id": "old", "created_ts": time.time(), "ttl_s": 0},
        ]
        client = app.app.test_client()
        resp = client.post("/api/emergency_stop")
        assert resp.status_code == 200
        queue = app.NODE_COMMANDS.get(node_id, [])
        assert queue
        actions = {cmd.get("action") for cmd in queue}
        assert "set_state" in actions
        assert "set_pwm" in actions
        for cmd in queue:
            assert cmd.get("state") == "off"
            assert cmd.get("cmd_id") != "old"
    finally:
        app.catalog_config = original_catalog
        if original_queue is None:
            app.NODE_COMMANDS.pop(node_id, None)
        else:
            app.NODE_COMMANDS[node_id] = original_queue
