#!/usr/bin/env python3
import json
import os
import time
import threading
import subprocess
from dataclasses import dataclass
from typing import Dict, Any, Optional

from flask import Flask, jsonify, request, render_template

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

app = Flask(__name__)

# -----------------------------
# Config
# -----------------------------
def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg: Dict[str, Any]) -> None:
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)

def validate_config(cfg: Dict[str, Any]) -> Optional[str]:
    # basic keys
    if "relays" not in cfg or "sensors" not in cfg:
        return "Config eksik: relays/sensors yok."

    relays = cfg["relays"]
    used = {}
    reserved = {2, 3}  # I2C pins (SDA=2, SCL=3) - genelde röleye verilmesin

    for key, r in relays.items():
        if "gpio" not in r:
            return f"{key} için gpio yok."
        try:
            gpio = int(r["gpio"])
        except Exception:
            return f"{key} gpio sayı olmalı."
        if gpio in reserved:
            return f"GPIO{gpio} I2C için ayrılmış (2/3). Röleye atama."
        if gpio in used:
            return f"GPIO{gpio} çakışma: {used[gpio]} ve {key}"
        used[gpio] = key

    # DHT pin çakışması
    dht_pin = int(cfg["sensors"].get("dht22_gpio", 17))
    if dht_pin in used:
        return f"DHT22 GPIO{dht_pin} röle ile çakışıyor ({used[dht_pin]})."

    return None


# -----------------------------
# Relay control with safety
# -----------------------------
class RelayDriver:
    def __init__(self, active_low: bool):
        self.active_low = active_low
        self._devices = {}  # key -> gpiozero DigitalOutputDevice
        self._states = {}   # key -> bool (True=ON)

        # Try gpiozero (preferred)
        try:
            from gpiozero import DigitalOutputDevice
            self.DigitalOutputDevice = DigitalOutputDevice
            self.backend = "gpiozero"
        except Exception as e:
            raise RuntimeError(
                "gpiozero yok. Kur: sudo apt install -y python3-gpiozero"
            ) from e

    def setup(self, relays: Dict[str, Any]):
        self.close_all()
        for key, r in relays.items():
            gpio = int(r["gpio"])
            dev = self.DigitalOutputDevice(
                gpio,
                active_high=(not self.active_low),
                initial_value=False
            )
            self._devices[key] = dev
            self._states[key] = False

    def on(self, key: str):
        dev = self._devices[key]
        dev.on()
        self._states[key] = True

    def off(self, key: str):
        dev = self._devices[key]
        dev.off()
        self._states[key] = False

    def state(self, key: str) -> bool:
        return bool(self._states.get(key, False))

    def close_all(self):
        for key, dev in list(self._devices.items()):
            try:
                dev.off()
                dev.close()
            except Exception:
                pass
        self._devices.clear()
        self._states.clear()


@dataclass
class SafetyState:
    test_mode: bool = False
    estop: bool = False
    pump_unlocked: bool = False


class SafetyManager:
    def __init__(self):
        self.state = SafetyState()
        self._lock = threading.Lock()
        self._timers = {}  # relay_key -> Timer

    def set_test_mode(self, on: bool):
        with self._lock:
            self.state.test_mode = bool(on)

    def set_estop(self, on: bool):
        with self._lock:
            self.state.estop = bool(on)
            if on:
                # cancel all timers
                for t in self._timers.values():
                    try: t.cancel()
                    except Exception: pass
                self._timers.clear()

    def unlock_pump(self, on: bool):
        with self._lock:
            self.state.pump_unlocked = bool(on)

    def can_switch(self, relay_key: str, relay_info: Dict[str, Any], want_on: bool) -> (bool, str):
        with self._lock:
            if self.state.estop and want_on:
                return False, "E-STOP aktif. Önce E-STOP kapat."
            if not self.state.test_mode:
                return False, "Test Modu kapalı."
            if relay_info.get("type") == "pump" and want_on:
                if relay_info.get("locked", True) and not self.state.pump_unlocked:
                    return False, "Pompa kilitli. Unlock etmeden açılmaz."
            return True, "OK"

    def arm_auto_off(self, relay_key: str, seconds: int, off_fn):
        # Cancel existing timer for this relay
        with self._lock:
            if relay_key in self._timers:
                try: self._timers[relay_key].cancel()
                except Exception: pass
                self._timers.pop(relay_key, None)

            t = threading.Timer(seconds, off_fn)
            self._timers[relay_key] = t
            t.start()


# -----------------------------
# Sensor hub
# -----------------------------
class SensorHub:
    def __init__(self):
        self.data = {
            "ok": True,
            "last_update": None,
            "errors": [],
            "bh1750": {"lux": None, "err": None, "ts": None},
            "ads1115": {"a0": None, "a1": None, "a2": None, "a3": None, "err": None, "ts": None},
            "ds18b20": {"sensors": [], "err": None, "ts": None},
            "dht22": {"temp": None, "hum": None, "err": None, "ts": None},
            "i2c_scan": {"found": [], "err": None, "ts": None}
        }
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None

    def start(self, cfg: Dict[str, Any]):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, args=(cfg,), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self, cfg: Dict[str, Any]):
        # Lazy imports
        bh = None
        ads = None
        ads_channels = None

        i2c = None
        i2c_bus = int(cfg.get("sensors", {}).get("i2c_bus", 1))

        while not self._stop.is_set():
            now = time.time()
            try:
                # I2C init
                if i2c is None:
                    try:
                        import board
                        import busio
                        i2c = busio.I2C(board.SCL, board.SDA)
                    except Exception as e:
                        self._set_err("I2C init", str(e))

                # BH1750
                if i2c is not None:
                    try:
                        if bh is None:
                            import adafruit_bh1750
                            bh = adafruit_bh1750.BH1750(i2c)
                        lux = float(bh.lux)
                        self._set_bh(lux, None, now)
                    except Exception as e:
                        self._set_bh(None, str(e), now)

                # ADS1115
                if i2c is not None:
                    try:
                        # ads_channels bazen None kalabiliyor; o durumda yeniden init et
                        if ads is None or ads_channels is None:
                            import adafruit_ads1x15.ads1115 as ADS
                            from adafruit_ads1x15.analog_in import AnalogIn

                            # Bazı sürümlerde P0..P3 ads1115 içinde değil, ads1x15 içinde olur.
                            try:
                                from adafruit_ads1x15.ads1x15 import P0, P1, P2, P3
                                _CH = (P0, P1, P2, P3)
                            except Exception:
                                # Son çare: 0..3 ile dene
                                _CH = (0, 1, 2, 3)

                            ads = ADS.ADS1115(i2c)
                            ads_channels = (
                                AnalogIn(ads, _CH[0]),
                                AnalogIn(ads, _CH[1]),
                                AnalogIn(ads, _CH[2]),
                                AnalogIn(ads, _CH[3]),
                            )

                        v = [ch.voltage for ch in ads_channels]
                        self._set_ads(v, None, now)

                    except Exception as e:
                        # hata olursa bir sonraki turda tekrar denemek için sıfırla
                        ads = None
                        ads_channels = None
                        self._set_ads(None, str(e), now)

                # DS18B20 (1-Wire)
                if cfg.get("sensors", {}).get("ds18b20_enabled", True):
                    try:
                        from w1thermsensor import W1ThermSensor
                        sens = W1ThermSensor.get_available_sensors()
                        out = []
                        for s in sens:
                            out.append({"id": s.id, "c": round(float(s.get_temperature()), 2)})
                        self._set_ds(out, None, now)
                    except Exception as e:
                        self._set_ds([], str(e), now)

                # DHT22 (optional; may require sudo + libgpiod)
                if not cfg.get("sensors", {}).get("dht22_enabled", False):
                    self._set_dht(None, None, "disabled", now)
                else:
                    dht_pin = int(cfg.get("sensors", {}).get("dht22_gpio", 17))
                    try:
                        import board as _b
                        import adafruit_dht
                        pin_obj = getattr(_b, f"D{dht_pin}", None)
                        if pin_obj is None:
                            raise RuntimeError(f"board.D{dht_pin} bulunamadı.")
                        dht = adafruit_dht.DHT22(pin_obj)
                        try:
                            t = dht.temperature
                            h = dht.humidity
                            self._set_dht(t, h, None, now)
                        finally:
                            try: dht.exit()
                            except Exception: pass
                    except Exception as e:
                        self._set_dht(None, None, str(e), now)

                with self._lock:
                    self.data["ok"] = True
                    self.data["last_update"] = now

            except Exception as e:
                self._set_err("SensorHub loop", str(e))

            time.sleep(1.2)

    def i2c_scan(self, bus_num: int = 1):
        # Try python smbus2 probe, fallback to i2cdetect
        now = time.time()
        found = []
        err = None
        try:
            from smbus2 import SMBus
            with SMBus(bus_num) as bus:
                for addr in range(0x03, 0x78):
                    try:
                        bus.write_quick(addr)
                        found.append(hex(addr))
                    except Exception:
                        pass
        except Exception as e:
            # fallback
            try:
                out = subprocess.check_output(["i2cdetect", "-y", str(bus_num)], text=True)
                # parse like: "--" or "23"
                for line in out.splitlines():
                    if ":" not in line:
                        continue
                    parts = line.split(":")[1].strip().split()
                    base = int(line.split(":")[0], 16)
                    for i, p in enumerate(parts):
                        if p != "--":
                            found.append(hex(base + i))
            except Exception as e2:
                err = f"smbus2/i2cdetect fail: {e} / {e2}"

        with self._lock:
            self.data["i2c_scan"] = {"found": found, "err": err, "ts": now}
        return self.data["i2c_scan"]

    def snapshot(self):
        with self._lock:
            return json.loads(json.dumps(self.data))

    def _set_err(self, where: str, msg: str):
        with self._lock:
            self.data["ok"] = False
            self.data["errors"].append({"where": where, "msg": msg, "ts": time.time()})
            self.data["errors"] = self.data["errors"][-50:]

    def _set_bh(self, lux, err, ts):
        with self._lock:
            self.data["bh1750"] = {"lux": lux, "err": err, "ts": ts}

    def _set_ads(self, v, err, ts):
        # v None gelebilir; her durumda güvenli olsun
        if not isinstance(v, (list, tuple)) or len(v) != 4:
            v = [None, None, None, None]
        with self._lock:
            self.data["ads1115"] = {
                "a0": v[0], "a1": v[1], "a2": v[2], "a3": v[3],
                "err": err, "ts": ts
            }

    def _set_ds(self, sensors, err, ts):
        with self._lock:
            self.data["ds18b20"] = {"sensors": sensors, "err": err, "ts": ts}

    def _set_dht(self, t, h, err, ts):
        with self._lock:
            self.data["dht22"] = {"temp": t, "hum": h, "err": err, "ts": ts}


# -----------------------------
# Global runtime objects
# -----------------------------
cfg = load_config()
err = validate_config(cfg)
if err:
    raise RuntimeError(f"Config invalid: {err}")

relay_driver = RelayDriver(active_low=bool(cfg.get("active_low", True)))
relay_driver.setup(cfg["relays"])

safety = SafetyManager()
safety.set_test_mode(bool(cfg.get("test_mode_default", False)))

sensors = SensorHub()
sensors.start(cfg)

# -----------------------------
# Helpers
# -----------------------------
def all_off():
    for k in cfg["relays"].keys():
        try:
            relay_driver.off(k)
        except Exception:
            pass

def reload_runtime(new_cfg: Dict[str, Any]):
    global cfg, relay_driver
    all_off()
    cfg = new_cfg
    relay_driver.close_all()
    relay_driver = RelayDriver(active_low=bool(cfg.get("active_low", True)))
    relay_driver.setup(cfg["relays"])
    sensors.start(cfg)


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    rel = {}
    for k, r in cfg["relays"].items():
        rel[k] = {
            "name": r.get("name", k),
            "gpio": int(r["gpio"]),
            "type": r.get("type", "relay"),
            "locked": bool(r.get("locked", False)),
            "state": relay_driver.state(k)
        }
    return jsonify({
        "time": time.time(),
        "safety": {
            "test_mode": safety.state.test_mode,
            "estop": safety.state.estop,
            "pump_unlocked": safety.state.pump_unlocked
        },
        "config": {
            "active_low": bool(cfg.get("active_low", True)),
            "safety": cfg.get("safety", {}),
            "sensors": cfg.get("sensors", {})
        },
        "relays": rel,
        "sensors": sensors.snapshot()
    })

@app.route("/api/safety", methods=["POST"])
def api_safety():
    body = request.get_json(force=True, silent=True) or {}
    if "test_mode" in body:
        safety.set_test_mode(bool(body["test_mode"]))
        if not safety.state.test_mode:
            all_off()
            safety.unlock_pump(False)
    if "estop" in body:
        safety.set_estop(bool(body["estop"]))
        if safety.state.estop:
            all_off()
            safety.unlock_pump(False)
    if "pump_unlocked" in body:
        safety.unlock_pump(bool(body["pump_unlocked"]))
    return jsonify({"ok": True, "safety": {
        "test_mode": safety.state.test_mode,
        "estop": safety.state.estop,
        "pump_unlocked": safety.state.pump_unlocked
    }})

@app.route("/api/relay/<relay_key>", methods=["POST"])
def api_relay(relay_key: str):
    if relay_key not in cfg["relays"]:
        return jsonify({"ok": False, "error": "relay_key not found"}), 404

    body = request.get_json(force=True, silent=True) or {}
    action = body.get("action", "")
    rinfo = cfg["relays"][relay_key]

    # Safety checks
    if action in ("on", "pulse"):
        ok, msg = safety.can_switch(relay_key, rinfo, want_on=True)
        if not ok:
            return jsonify({"ok": False, "error": msg}), 400

    # Apply
    if action == "off":
        relay_driver.off(relay_key)
        return jsonify({"ok": True, "state": relay_driver.state(relay_key)})

    if action == "on":
        relay_driver.on(relay_key)

        # auto-off for heater/pump
        if rinfo.get("type") == "heater":
            maxs = int(cfg.get("safety", {}).get("heater_max_on_sec", 10))
            safety.arm_auto_off(relay_key, maxs, lambda: relay_driver.off(relay_key))
        if rinfo.get("type") == "pump":
            maxs = int(cfg.get("safety", {}).get("pump_max_on_sec", 3))
            safety.arm_auto_off(relay_key, maxs, lambda: relay_driver.off(relay_key))

        return jsonify({"ok": True, "state": relay_driver.state(relay_key)})

    if action == "pulse":
        sec = int(body.get("sec", 2))
        sec = max(1, min(sec, 15))
        # heater/pump pulse limit
        if rinfo.get("type") == "heater":
            sec = min(sec, int(cfg.get("safety", {}).get("heater_max_on_sec", 10)))
        if rinfo.get("type") == "pump":
            sec = min(sec, int(cfg.get("safety", {}).get("pump_max_on_sec", 3)))

        relay_driver.on(relay_key)
        safety.arm_auto_off(relay_key, sec, lambda: relay_driver.off(relay_key))
        return jsonify({"ok": True, "state": True, "auto_off_in": sec})

    return jsonify({"ok": False, "error": "unknown action"}), 400

@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        return jsonify(cfg)

    new_cfg = request.get_json(force=True, silent=True)
    if not isinstance(new_cfg, dict):
        return jsonify({"ok": False, "error": "invalid json"}), 400

    err = validate_config(new_cfg)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    # Save + reload
    save_config(new_cfg)
    reload_runtime(new_cfg)

    return jsonify({"ok": True})

@app.route("/api/i2c-scan", methods=["POST"])
def api_i2c_scan():
    bus_num = int(cfg.get("sensors", {}).get("i2c_bus", 1))
    res = sensors.i2c_scan(bus_num)
    return jsonify({"ok": True, "result": res})

@app.route("/api/all-off", methods=["POST"])
def api_all_off():
    all_off()
    return jsonify({"ok": True})

if __name__ == "__main__":
    # Not: GPIO erişimi için çoğu sistemde sudo gerekebilir.
    # Run: sudo ~/sera-venv/bin/python app.py
    app.run(host="0.0.0.0", port=5000, debug=False)
