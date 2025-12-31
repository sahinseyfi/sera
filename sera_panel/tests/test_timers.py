import os

os.environ["SERAPANEL_SKIP_INIT"] = "1"

import app_legacy
from app_legacy import SafetyManager


class FakeTimer:
    def __init__(self, seconds, fn):
        self.seconds = seconds
        self.fn = fn
        self.cancelled = False
        self.started = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        if not self.cancelled:
            self.fn()


def test_arm_auto_off_triggers_callback():
    original_timer = app_legacy.threading.Timer
    app_legacy.threading.Timer = FakeTimer
    try:
        sm = SafetyManager()
        fired = []

        def off_fn():
            fired.append(True)

        sm.arm_auto_off("pump", 2, off_fn)
        timer = sm._timers["pump"]
        assert timer.started is True
        timer.fire()
        assert fired == [True]
    finally:
        app_legacy.threading.Timer = original_timer


def test_arm_auto_off_replaces_existing_timer():
    original_timer = app_legacy.threading.Timer
    app_legacy.threading.Timer = FakeTimer
    try:
        sm = SafetyManager()
        fired = []

        def off_fn_1():
            fired.append("first")

        def off_fn_2():
            fired.append("second")

        sm.arm_auto_off("pump", 2, off_fn_1)
        first_timer = sm._timers["pump"]
        sm.arm_auto_off("pump", 3, off_fn_2)
        second_timer = sm._timers["pump"]

        assert first_timer is not second_timer
        assert first_timer.cancelled is True
        assert second_timer.started is True

        first_timer.fire()
        second_timer.fire()
        assert fired == ["second"]
    finally:
        app_legacy.threading.Timer = original_timer
