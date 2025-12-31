import os

os.environ["SERAPANEL_SKIP_INIT"] = "1"

from app_legacy import SafetyManager


def test_blocks_when_test_mode_off():
    sm = SafetyManager()
    ok, msg = sm.can_switch("fan", {"type": "fan"}, True)
    assert not ok
    assert "Test Modu" in msg


def test_allows_when_test_mode_on():
    sm = SafetyManager()
    sm.set_test_mode(True)
    ok, _ = sm.can_switch("fan", {"type": "fan"}, True)
    assert ok


def test_estop_blocks_when_enabled():
    sm = SafetyManager()
    sm.set_test_mode(True)
    sm.set_estop(True)
    ok, msg = sm.can_switch("fan", {"type": "fan"}, True)
    assert not ok
    assert "E-STOP" in msg


def test_pump_lock_requires_unlock():
    sm = SafetyManager()
    sm.set_test_mode(True)
    ok, msg = sm.can_switch("pump", {"type": "pump", "locked": True}, True)
    assert not ok
    assert "Pompa kilitli" in msg

    sm.unlock_pump(True)
    ok, _ = sm.can_switch("pump", {"type": "pump", "locked": True}, True)
    assert ok


def test_pump_allows_when_unlocked_flag_false():
    sm = SafetyManager()
    sm.set_test_mode(True)
    ok, _ = sm.can_switch("pump", {"type": "pump", "locked": False}, True)
    assert ok
