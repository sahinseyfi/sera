import csv
import ipaddress
import io
import json
import os
import random
import sqlite3
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timedelta, time as dt_time, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

from flask import Blueprint, Flask, Response, jsonify, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
TEST_PANEL_DIR = BASE_DIR / "sera_panel"
DATA_DIR.mkdir(exist_ok=True)
CHANNEL_CONFIG_PATH = CONFIG_DIR / "channels.json"
SENSORS_CONFIG_PATH = CONFIG_DIR / "sensors.json"
DB_PATH = DATA_DIR / "sera.db"
SENSOR_CSV_LOG_DIR = DATA_DIR / "sensor_logs"

SENSOR_STALE_SECONDS = 15
SENSOR_ALERT_COOLDOWN_SECONDS = 120
SENSOR_LOG_INTERVAL_SECONDS = 10
DEFAULT_LIMITS = {
    "pump_max_seconds": 15,
    "pump_cooldown_seconds": 60,
    "heater_max_seconds": 300,
    "heater_cutoff_temp": 30,
    "energy_kwh_low": 2.330,
    "energy_kwh_high": 3.451,
    "energy_kwh_threshold": 240,
}
DEFAULT_ALERTS = {
    "sensor_offline_minutes": 5,
    "temp_high_c": 30,
    "temp_low_c": 0,
    "hum_high_pct": 85,
    "hum_low_pct": 0,
}
DEFAULT_AUTOMATION = {
    "enabled": False,
    "lux_ok": 350,
    "lux_max": 0,
    "target_ok_minutes": 300,
    "window_start": "06:00",
    "window_end": "22:00",
    "reset_time": "00:00",
    "min_on_minutes": 0,
    "min_off_minutes": 0,
    "max_block_minutes": 0,
    "manual_override_minutes": 0,
    "fan_enabled": False,
    "fan_rh_high": 80,
    "fan_rh_low": 70,
    "fan_max_minutes": 3,
    "fan_min_off_minutes": 2,
    "fan_manual_override_minutes": 10,
    "fan_night_enabled": False,
    "fan_night_start": "22:00",
    "fan_night_end": "06:00",
    "fan_night_rh_high": 85,
    "fan_night_rh_low": 75,
    "fan_periodic_enabled": False,
    "fan_periodic_every_minutes": 60,
    "fan_periodic_duration_minutes": 2,
    "fan_periodic_night_enabled": False,
    "fan_periodic_night_every_minutes": 90,
    "fan_periodic_night_duration_minutes": 2,
    "heater_enabled": False,
    "heater_sensor": "dht22",
    "heater_t_low": 18,
    "heater_t_high": 20,
    "heater_max_minutes": 5,
    "heater_min_off_minutes": 2,
    "heater_manual_override_minutes": 10,
    "heater_fan_required": True,
    "heater_night_enabled": False,
    "heater_night_start": "22:00",
    "heater_night_end": "06:00",
    "heater_night_t_low": 17,
    "heater_night_t_high": 19,
    "pump_enabled": False,
    "pump_soil_channel": "ch0",
    "pump_dry_threshold": 0,
    "pump_dry_when_above": False,
    "pump_pulse_seconds": 5,
    "pump_max_daily_seconds": 60,
    "pump_window_start": "06:00",
    "pump_window_end": "22:00",
    "pump_manual_override_minutes": 10,
    "soil_calibration": {
        "ch0": {"dry": None, "wet": None},
        "ch1": {"dry": None, "wet": None},
        "ch2": {"dry": None, "wet": None},
        "ch3": {"dry": None, "wet": None},
    },
}

SIMULATION_MODE = os.getenv("SIMULATION_MODE", "0") == "1"
DISABLE_BACKGROUND_LOOPS = os.getenv("DISABLE_BACKGROUND_LOOPS", "0") == "1"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
LIGHT_CHANNEL_NAME = os.getenv("LIGHT_CHANNEL_NAME")
FAN_CHANNEL_NAME = os.getenv("FAN_CHANNEL_NAME")
PUMP_CHANNEL_NAME = os.getenv("PUMP_CHANNEL_NAME")


def _parse_hhmm(value: str) -> dt_time:
    h, m = value.split(":")
    return dt_time(int(h), int(m))


class ActuationError(Exception):
    pass


class GPIOBackend:
    """Hardware abstraction with simulation fallback."""

    def __init__(self, simulation: bool = False) -> None:
        self.simulation = simulation or SIMULATION_MODE
        self.sim_states: Dict[int, bool] = {}
        if not self.simulation:
            try:
                import RPi.GPIO as GPIO  # type: ignore

                self.GPIO = GPIO
                self.GPIO.setwarnings(False)
                self.GPIO.setmode(self.GPIO.BCM)
            except Exception:
                self.simulation = True
                self.GPIO = None
        else:
            self.GPIO = None

    def setup_channel(self, pin: int, active_low: bool, default_off: bool) -> None:
        if self.simulation:
            self.sim_states[pin] = False
            return
        assert self.GPIO is not None
        self.GPIO.setup(pin, self.GPIO.OUT, initial=self._to_output(False, active_low))
        # enforce default off explicitly
        self.GPIO.output(pin, self._to_output(default_off is False, active_low))

    def set_state(self, pin: int, active_low: bool, on: bool) -> None:
        if self.simulation:
            self.sim_states[pin] = bool(on)
            return
        assert self.GPIO is not None
        self.GPIO.output(pin, self._to_output(on, active_low))

    def cleanup(self) -> None:
        if not self.simulation and self.GPIO is not None:
            self.GPIO.cleanup()

    @staticmethod
    def _to_output(on: bool, active_low: bool) -> int:
        if active_low:
            return 0 if on else 1
        return 1 if on else 0


class ActuatorManager:
    def __init__(self, backend: GPIOBackend, channel_config: List[Dict[str, Any]]) -> None:
        self.backend = backend
        self.channels: Dict[str, Dict[str, Any]] = {}
        self.state: Dict[str, Dict[str, Any]] = {}
        self.timers: Dict[str, threading.Timer] = {}
        self.lock = threading.Lock()
        self.last_pump_stop_ts: float = 0
        self.load_config(channel_config)

    def load_config(self, channel_config: List[Dict[str, Any]]) -> None:
        with self.lock:
            # cancel timers and turn everything off before reloading
            for timer in self.timers.values():
                timer.cancel()
            self.timers.clear()
            for chan in channel_config:
                name = chan["name"].upper()
                self.channels[name] = chan
                pin = int(chan["gpio_pin"])
                active_low = bool(chan.get("active_low", False))
                safe_default = bool(chan.get("safe_default", False))
                self.backend.setup_channel(pin, active_low, False)
                self.backend.set_state(pin, active_low, False)
                self.state[name] = {
                    "state": False,
                    "last_change_ts": None,
                    "reason": "startup",
                }
            # turn all channels off after reload to be safe
            for name in self.channels:
                self._apply(name, False, "config_reload")

    def _apply(self, name: str, on: bool, reason: str, duration: Optional[int] = None) -> None:
        chan = self.channels[name]
        pin = int(chan["gpio_pin"])
        active_low = bool(chan.get("active_low", False))
        self.backend.set_state(pin, active_low, on)
        self.state[name] = {
            "state": on,
            "last_change_ts": time.time(),
            "reason": reason,
            "description": chan.get("description", name),
        }
        if name in self.timers:
            self.timers[name].cancel()
            self.timers.pop(name, None)
        if on and duration:
            timer = threading.Timer(duration, lambda: self._apply(name, False, "auto_off"))
            timer.daemon = True
            timer.start()
            self.timers[name] = timer
        if not on and name.endswith("PUMP") and reason not in ("startup", "config_reload"):
            self.last_pump_stop_ts = time.time()

    def set_state(self, name: str, on: bool, reason: str, duration: Optional[int] = None) -> None:
        with self.lock:
            if name not in self.channels:
                raise ActuationError(f"Unknown actuator: {name}")
            self._apply(name, on, reason, duration)
            if not on and name.endswith("PUMP"):
                self.last_pump_stop_ts = time.time()

    def set_all_off(self, reason: str) -> None:
        with self.lock:
            for timer in self.timers.values():
                timer.cancel()
            self.timers.clear()
            for name in self.channels:
                self._apply(name, False, reason)

    def get_state(self) -> Dict[str, Any]:
        with self.lock:
            return {
                name: {
                    **info,
                    "description": self.channels[name].get("description", name),
                    "active_low": bool(self.channels[name].get("active_low", False)),
                    "gpio_pin": self.channels[name]["gpio_pin"],
                    "role": self.channels[name].get("role", "other"),
                    "power_w": self.channels[name].get("power_w", 0),
                    "quantity": self.channels[name].get("quantity", 1),
                    "voltage_v": self.channels[name].get("voltage_v"),
                    "notes": self.channels[name].get("notes", ""),
                }
                for name, info in self.state.items()
            }

    def reload_channels(self, channel_config: List[Dict[str, Any]]) -> None:
        self.load_config(channel_config)


class SensorManager:
    def __init__(self, simulation: bool = False) -> None:
        self.simulation = simulation or SIMULATION_MODE
        self.lock = threading.Lock()
        self.last_readings: Dict[str, Any] = {}
        self.last_ts: float = 0
        self.dht22_history: Deque[Tuple[float, float, float]] = deque()
        self.dht22_sensor = None
        self.ads_channels: List[Any] = []
        self.config: Dict[str, Any] = {}
        # optional hardware libs
        self._init_hardware()

    def reload_config(self, config: Dict[str, Any]) -> None:
        with self.lock:
            self.config = dict(config)
        self._init_hardware()

    def _init_hardware(self) -> None:
        self.dht = None
        self.ads = None
        self.ads_adafruit = None
        self.bus = None
        if self.simulation:
            return
        config = dict(sensors_config)
        config.update(self.config or {})
        try:
            import Adafruit_DHT  # type: ignore

            self.dht = Adafruit_DHT
        except Exception:
            self.dht = None
        try:
            import adafruit_dht  # type: ignore
            import board  # type: ignore

            gpio_pin = int(config.get("dht22_gpio", 17))
            pin_name = f"D{gpio_pin}"
            pin = getattr(board, pin_name, board.D17)
            self.dht22_sensor = adafruit_dht.DHT22(pin, use_pulseio=False)
        except Exception:
            self.dht22_sensor = None
        try:
            from smbus2 import SMBus  # type: ignore

            self.bus = SMBus(1)
        except Exception:
            self.bus = None
        try:
            import Adafruit_ADS1x15  # type: ignore

            self.ads = Adafruit_ADS1x15.ADS1115()
        except Exception:
            self.ads = None
        try:
            import board  # type: ignore
            import busio  # type: ignore
            from adafruit_ads1x15.ads1115 import ADS1115  # type: ignore
            from adafruit_ads1x15.analog_in import AnalogIn  # type: ignore

            addr_raw = config.get("ads1115_addr", "0x48")
            try:
                ads_addr = int(str(addr_raw), 0)
            except Exception:
                ads_addr = 0x48
            i2c = busio.I2C(board.SCL, board.SDA)
            self.ads_adafruit = ADS1115(i2c, address=ads_addr)
            self.ads_adafruit.gain = 1
            self.ads_channels = [
                AnalogIn(self.ads_adafruit, 0),
                AnalogIn(self.ads_adafruit, 1),
                AnalogIn(self.ads_adafruit, 2),
                AnalogIn(self.ads_adafruit, 3),
            ]
        except Exception:
            self.ads_adafruit = None
            self.ads_channels = []

    def read_all(self) -> Dict[str, Any]:
        now = time.time()
        data = {
            "dht22": self._read_dht22(),
            "ds18b20": self._read_ds18b20(),
            "bh1750": self._read_bh1750(),
            "soil": self._read_soil(),
        }
        with self.lock:
            self._update_dht22_history_locked(data.get("dht22", {}), now)
            self.last_readings = data
            self.last_ts = now
        return data

    def _update_dht22_history_locked(self, reading: Dict[str, Any], now: float) -> None:
        status = reading.get("status")
        if status not in ("ok", "simulated"):
            return
        try:
            temp = float(reading.get("temperature"))
            hum = float(reading.get("humidity"))
        except (TypeError, ValueError):
            return
        ts = float(reading.get("ts") or now)
        self.dht22_history.append((ts, temp, hum))
        cutoff = now - 30 * 60
        while self.dht22_history and self.dht22_history[0][0] < cutoff:
            self.dht22_history.popleft()

    def dht22_averages(self) -> Dict[str, Dict[str, Optional[float]]]:
        with self.lock:
            now = time.time()

            def avg(window_seconds: int) -> Dict[str, Optional[float]]:
                cutoff = now - window_seconds
                temps: List[float] = []
                hums: List[float] = []
                for ts, temp, hum in self.dht22_history:
                    if ts >= cutoff:
                        temps.append(temp)
                        hums.append(hum)
                if not temps:
                    return {"temperature": None, "humidity": None}
                return {
                    "temperature": round(sum(temps) / len(temps), 1),
                    "humidity": round(sum(hums) / len(hums), 1),
                }

            return {"1m": avg(60), "5m": avg(300), "30m": avg(1800)}

    def _read_dht22(self) -> Dict[str, Any]:
        if self.simulation:
            return {
                "temperature": round(random.uniform(18, 30), 1),
                "humidity": round(random.uniform(40, 70), 1),
                "ts": time.time(),
                "status": "simulated" if self.simulation else "unavailable",
            }
        if self.dht22_sensor:
            for attempt in range(2):
                try:
                    temperature = self.dht22_sensor.temperature
                    humidity = self.dht22_sensor.humidity
                    return {
                        "temperature": temperature,
                        "humidity": humidity,
                        "ts": time.time(),
                        "status": "ok" if humidity is not None else "error",
                    }
                except RuntimeError:
                    time.sleep(0.2)
                except Exception:
                    break
            return {"temperature": None, "humidity": None, "ts": time.time(), "status": "error"}
        if not self.dht:
            return {
                "temperature": None,
                "humidity": None,
                "ts": time.time(),
                "status": "unavailable",
            }
        gpio_pin = int(self.config.get("dht22_gpio", 17) if self.config else sensors_config.get("dht22_gpio", 17))
        humidity, temperature = self.dht.read_retry(self.dht.DHT22, gpio_pin)
        return {
            "temperature": temperature,
            "humidity": humidity,
            "ts": time.time(),
            "status": "ok" if humidity is not None else "error",
        }

    def _read_ds18b20(self) -> Dict[str, Any]:
        config = dict(sensors_config)
        config.update(self.config or {})
        if not config.get("ds18b20_enabled", True):
            return {"temperature": None, "ts": time.time(), "status": "disabled"}
        if self.simulation:
            return {
                "temperature": round(random.uniform(16, 25), 1),
                "ts": time.time(),
                "status": "simulated",
            }
        base_path = Path("/sys/bus/w1/devices")
        sensors = list(base_path.glob("28-*/w1_slave"))
        if not sensors:
            return {"temperature": None, "ts": time.time(), "status": "missing"}
        try:
            with sensors[0].open() as f:
                lines = f.readlines()
            if "YES" not in lines[0]:
                return {"temperature": None, "ts": time.time(), "status": "crc_error"}
            temp_str = lines[1].split("t=")[-1].strip()
            temp_c = float(temp_str) / 1000.0
            return {"temperature": temp_c, "ts": time.time(), "status": "ok"}
        except Exception:
            return {"temperature": None, "ts": time.time(), "status": "error"}

    def _read_bh1750(self) -> Dict[str, Any]:
        if self.simulation or not self.bus:
            return {
                "lux": round(random.uniform(100, 700), 1),
                "ts": time.time(),
                "status": "simulated" if self.simulation else "unavailable",
            }
        config = dict(sensors_config)
        config.update(self.config or {})
        addr_env = str(config.get("bh1750_addr", "0x23"))
        try:
            primary_addr = int(addr_env, 0)
        except Exception:
            primary_addr = 0x23
        addr_candidates = [primary_addr]
        if primary_addr == 0x23:
            addr_candidates.append(0x5c)
        elif primary_addr == 0x5c:
            addr_candidates.append(0x23)

        last_error = None
        for addr in addr_candidates:
            try:
                # BH1750 needs a short measurement delay; use continuous high-res mode.
                self.bus.write_byte(addr, 0x10)
                time.sleep(0.18)
                data = self.bus.read_i2c_block_data(addr, 0x10, 2)
                raw = (data[1] + (256 * data[0])) / 1.2
                return {"lux": round(raw, 1), "ts": time.time(), "status": "ok"}
            except Exception as exc:
                last_error = exc
                continue
        return {"lux": None, "ts": time.time(), "status": "error"}

    def _read_soil(self) -> Dict[str, Any]:
        if self.simulation:
            return {
                "ch0": round(random.uniform(12000, 20000), 0),
                "ch1": round(random.uniform(12000, 20000), 0),
                "ch2": round(random.uniform(12000, 20000), 0),
                "ch3": round(random.uniform(12000, 20000), 0),
                "ts": time.time(),
                "status": "simulated" if self.simulation else "unavailable",
            }
        config = dict(sensors_config)
        config.update(self.config or {})
        addr_raw = config.get("ads1115_addr", "0x48")
        try:
            ads_addr = int(str(addr_raw), 0)
        except Exception:
            ads_addr = 0x48
        if self.bus:
            try:
                ch0 = self._read_ads1115_raw(self.bus, ads_addr, 0)
                ch1 = self._read_ads1115_raw(self.bus, ads_addr, 1)
                ch2 = self._read_ads1115_raw(self.bus, ads_addr, 2)
                ch3 = self._read_ads1115_raw(self.bus, ads_addr, 3)
                return {
                    "ch0": ch0,
                    "ch1": ch1,
                    "ch2": ch2,
                    "ch3": ch3,
                    "ts": time.time(),
                    "status": "ok",
                }
            except Exception:
                pass
        if self.ads_adafruit and self.ads_channels:
            try:
                ch0 = self.ads_channels[0].value
                ch1 = self.ads_channels[1].value
                ch2 = self.ads_channels[2].value
                ch3 = self.ads_channels[3].value
                return {
                    "ch0": ch0,
                    "ch1": ch1,
                    "ch2": ch2,
                    "ch3": ch3,
                    "ts": time.time(),
                    "status": "ok",
                }
            except Exception:
                pass
        if not self.ads:
            return {
                "ch0": None,
                "ch1": None,
                "ch2": None,
                "ch3": None,
                "ts": time.time(),
                "status": "unavailable",
            }
        try:
            gain = 1
            ch0 = self.ads.read_adc(0, gain)
            ch1 = self.ads.read_adc(1, gain)
            ch2 = self.ads.read_adc(2, gain)
            ch3 = self.ads.read_adc(3, gain)
            return {
                "ch0": ch0,
                "ch1": ch1,
                "ch2": ch2,
                "ch3": ch3,
                "ts": time.time(),
                "status": "ok",
            }
        except Exception:
            return {
                "ch0": None,
                "ch1": None,
                "ch2": None,
                "ch3": None,
                "ts": time.time(),
                "status": "error",
            }

    @staticmethod
    def _read_ads1115_raw(bus: Any, addr: int, channel: int) -> Optional[int]:
        if channel not in (0, 1, 2, 3):
            raise ValueError("ADS1115 channel must be 0-3")
        mux = 0x4 + channel
        config = (
            0x8000  # start single conversion
            | (mux << 12)
            | (0x1 << 9)  # gain = 1 (4.096V)
            | 0x0100  # single-shot
            | (0x4 << 5)  # 128 SPS
            | 0x0003  # disable comparator
        )
        bus.write_i2c_block_data(addr, 0x01, [(config >> 8) & 0xFF, config & 0xFF])
        time.sleep(0.008)
        data = bus.read_i2c_block_data(addr, 0x00, 2)
        raw = (data[0] << 8) | data[1]
        if raw & 0x8000:
            raw -= 1 << 16
        return raw

    def latest(self) -> Dict[str, Any]:
        with self.lock:
            return {"readings": self.last_readings, "ts": self.last_ts}


class LCDManager:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.lock = threading.Lock()
        self.config = dict(config)
        self.lcd = None
        self.last_lines = ["", "", "", ""]
        self._init_hardware()

    def _init_hardware(self) -> None:
        enabled = bool(self.config.get("lcd_enabled", True))
        if not enabled:
            self.lcd = None
            return
        try:
            from RPLCD.i2c import CharLCD  # type: ignore
        except Exception:
            self.lcd = None
            return
        try:
            addr_raw = str(self.config.get("lcd_addr", "0x27"))
            try:
                addr = int(addr_raw, 0)
            except Exception:
                addr = 0x27
            cols = int(self.config.get("lcd_cols", 20))
            rows = int(self.config.get("lcd_rows", 4))
            port = int(self.config.get("lcd_port", 1))
            expander = str(self.config.get("lcd_expander", "PCF8574"))
            charmap = str(self.config.get("lcd_charmap", "A00"))
            self.lcd = CharLCD(
                i2c_expander=expander,
                address=addr,
                port=port,
                cols=cols,
                rows=rows,
                charmap=charmap,
                auto_linebreaks=True,
            )
        except Exception:
            self.lcd = None

    def update_config(self, config: Dict[str, Any]) -> None:
        with self.lock:
            self.config = dict(config)
            self._init_hardware()

    def status(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "enabled": bool(self.config.get("lcd_enabled", True)),
                "mode": self.config.get("lcd_mode", "auto"),
                "lines": list(self.last_lines),
            }

    def set_manual_lines(self, lines: List[str]) -> None:
        with self.lock:
            self.config["lcd_mode"] = "manual"
            self.config["lcd_lines"] = list(lines)
            self._write_lines(lines)

    def render_auto(self, data: Dict[str, Any]) -> None:
        with self.lock:
            if not bool(self.config.get("lcd_enabled", True)):
                return
            if self.config.get("lcd_mode", "auto") != "auto":
                return
            lines = self._build_auto_lines(data)
            self._write_lines(lines)

    def _write_lines(self, lines: List[str]) -> None:
        formatted = self._format_lines(lines)
        self.last_lines = list(formatted)
        if not self.lcd:
            return
        try:
            for idx, line in enumerate(formatted):
                self.lcd.cursor_pos = (idx, 0)
                self.lcd.write_string(line)
        except Exception:
            self.lcd = None

    def _format_lines(self, lines: List[str]) -> List[str]:
        cols = int(self.config.get("lcd_cols", 20))
        rows = int(self.config.get("lcd_rows", 4))
        padded = [(line or "")[:cols].ljust(cols) for line in lines]
        while len(padded) < rows:
            padded.append("".ljust(cols))
        return padded[:rows]

    def _build_auto_lines(self, data: Dict[str, Any]) -> List[str]:
        readings = data.get("sensor_readings", {})
        dht = readings.get("dht22", {}) if isinstance(readings.get("dht22"), dict) else {}
        lux = readings.get("bh1750", {}) if isinstance(readings.get("bh1750"), dict) else {}
        soil = readings.get("soil", {}) if isinstance(readings.get("soil"), dict) else {}

        temp = dht.get("temperature")
        hum = dht.get("humidity")
        if temp is None or hum is None:
            line0 = "T: --.-C  N: --.-%"
        else:
            line0 = f"T:{float(temp):4.1f}C  N:{float(hum):4.1f}%"

        lux_val = lux.get("lux")
        line1 = f"Isik: {int(lux_val):5d} lux" if lux_val is not None else "Isik:  ----- lux"

        soil_raw = soil.get("ch0")
        soil_pct = self._soil_percent("ch0", soil_raw)
        if soil_pct is None:
            line2 = f"Toprak: {int(soil_raw):4d}" if soil_raw is not None else "Toprak:   --"
        else:
            line2 = f"Toprak: {soil_pct:3d} %"

        safe_mode = bool(data.get("safe_mode"))
        line3 = "SAFE MODE" if safe_mode else "Sistem: AKTIF"
        return [line0, line1, line2, line3]

    def _soil_percent(self, channel: str, raw: Any) -> Optional[int]:
        if raw is None:
            return None
        calibration = app_state.automation.config.get("soil_calibration", {}) if app_state else {}
        entry = calibration.get(channel) or {}
        dry = entry.get("dry")
        wet = entry.get("wet")
        try:
            dry_val = float(dry)
            wet_val = float(wet)
            raw_val = float(raw)
        except (TypeError, ValueError):
            return None
        if dry_val == wet_val:
            return None
        pct = (dry_val - raw_val) / (dry_val - wet_val) * 100
        pct = max(0, min(100, pct))
        return int(pct)

class AutomationEngine:
    def __init__(self, actuator_manager: ActuatorManager, sensor_manager: SensorManager):
        self.actuator_manager = actuator_manager
        self.sensor_manager = sensor_manager
        self.config = json.loads(json.dumps(DEFAULT_AUTOMATION))
        self.ok_minutes_today: float = 0.0
        self.last_sample_ts: float = time.time()
        self.last_reset_date = self._reset_key(datetime.now())
        self.last_lux_error_ts: float = 0.0
        self.last_lux_error_active: bool = False
        self.block_until_ts: float = 0.0
        self.manual_override_until_ts: float = 0.0
        self.last_lux_max_alert_ts: float = 0.0
        self.last_auto_off_ts: float = 0.0
        self.last_auto_off_reason: str = ""
        self.last_min_off_alert_ts: float = 0.0
        self.last_target_met_alert_ts: float = 0.0
        self.last_target_met_active: bool = False
        self.fan_manual_override_until_ts: float = 0.0
        self.fan_last_auto_off_ts: float = 0.0
        self.fan_last_auto_off_reason: str = ""
        self.fan_periodic_last_start_ts: float = 0.0
        self.heater_manual_override_until_ts: float = 0.0
        self.heater_last_auto_off_ts: float = 0.0
        self.heater_last_auto_off_reason: str = ""
        self.pump_manual_override_until_ts: float = 0.0
        self.pump_last_auto_ts: float = 0.0
        self.pump_daily_seconds: float = 0.0
        self.pump_block_until_ts: float = 0.0
        self.pump_last_auto_off_ts: float = 0.0
        self.pump_last_auto_off_reason: str = ""

    def reset_daily(self) -> None:
        self.ok_minutes_today = 0.0
        self.block_until_ts = 0.0
        self.manual_override_until_ts = 0.0
        self.last_auto_off_ts = 0.0
        self.last_auto_off_reason = ""
        self.last_target_met_active = False
        self.last_sample_ts = time.time()
        self.fan_manual_override_until_ts = 0.0
        self.fan_last_auto_off_ts = 0.0
        self.fan_last_auto_off_reason = ""
        self.fan_periodic_last_start_ts = 0.0
        self.heater_manual_override_until_ts = 0.0
        self.heater_last_auto_off_ts = 0.0
        self.heater_last_auto_off_reason = ""
        self.pump_manual_override_until_ts = 0.0
        self.pump_last_auto_ts = 0.0
        self.pump_daily_seconds = 0.0
        self.pump_block_until_ts = 0.0
        self.pump_last_auto_off_ts = 0.0
        self.pump_last_auto_off_reason = ""
        _record_threshold_alert(
            "pump_daily_limit",
            False,
            "Pompa otomasyonu durdu: günlük limit doldu.",
            "Pompa günlük limit sıfırlandı.",
        )

    def _window_bounds(self, now: datetime) -> tuple[datetime, datetime]:
        start = _parse_hhmm(self.config.get("window_start", "06:00"))
        end = _parse_hhmm(self.config.get("window_end", "22:00"))
        start_dt = now.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
        end_dt = now.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
            if now < start_dt:
                start_dt -= timedelta(days=1)
        return start_dt, end_dt

    def _within_window(self, now: datetime) -> bool:
        start_dt, end_dt = self._window_bounds(now)
        return start_dt <= now <= end_dt

    def _reset_key(self, now: datetime) -> datetime.date:
        reset_time = _parse_hhmm(self.config.get("reset_time", "00:00"))
        reset_dt = now.replace(hour=reset_time.hour, minute=reset_time.minute, second=0, microsecond=0)
        if now < reset_dt:
            return (now - timedelta(days=1)).date()
        return now.date()

    def _find_light_channel(self) -> Optional[str]:
        if LIGHT_CHANNEL_NAME:
            return LIGHT_CHANNEL_NAME.upper()
        for name, chan in self.actuator_manager.channels.items():
            if str(chan.get("role", "")).lower() == "light":
                return name
        for name in self.actuator_manager.channels:
            if "LIGHT" in name:
                return name
        return None

    def _find_fan_channel(self) -> Optional[str]:
        if FAN_CHANNEL_NAME:
            return FAN_CHANNEL_NAME.upper()
        for name, chan in self.actuator_manager.channels.items():
            if str(chan.get("role", "")).lower() == "fan":
                return name
        for name in self.actuator_manager.channels:
            if "FAN" in name and "POT" not in name:
                return name
        for name in self.actuator_manager.channels:
            if "FAN" in name:
                return name
        return None

    def _find_heater_channel(self) -> Optional[str]:
        for name, chan in self.actuator_manager.channels.items():
            if str(chan.get("role", "")).lower() == "heater":
                return name
        for name in self.actuator_manager.channels:
            if "HEATER" in name:
                return name
        return None

    def _find_pump_channel(self) -> Optional[str]:
        if PUMP_CHANNEL_NAME:
            return PUMP_CHANNEL_NAME.upper()
        for name, chan in self.actuator_manager.channels.items():
            if str(chan.get("role", "")).lower() == "pump":
                return name
        for name in self.actuator_manager.channels:
            if "PUMP" in name:
                return name
        return None

    def _heater_sensor_key(self) -> str:
        sensor = str(self.config.get("heater_sensor", "dht22") or "dht22").lower()
        if sensor == "ds18b20":
            return "ds18b20"
        return "dht22"

    def _window_bounds_custom(self, now: datetime, start_key: str, end_key: str) -> tuple[datetime, datetime]:
        start = _parse_hhmm(self.config.get(start_key, "22:00"))
        end = _parse_hhmm(self.config.get(end_key, "06:00"))
        start_dt = now.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
        end_dt = now.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
            if now < start_dt:
                start_dt -= timedelta(days=1)
        return start_dt, end_dt

    def _fan_thresholds(self, now: datetime) -> tuple[int, int, bool]:
        rh_high = int(self.config.get("fan_rh_high", 80) or 80)
        rh_low = int(self.config.get("fan_rh_low", 70) or 70)
        night_active = False
        if self.config.get("fan_night_enabled"):
            start_dt, end_dt = self._window_bounds_custom(now, "fan_night_start", "fan_night_end")
            night_active = start_dt <= now <= end_dt
            if night_active:
                rh_high = int(self.config.get("fan_night_rh_high", rh_high) or rh_high)
                rh_low = int(self.config.get("fan_night_rh_low", rh_low) or rh_low)
        if rh_low >= rh_high:
            rh_low = max(0, rh_high - 1)
        return rh_high, rh_low, night_active

    def _fan_night_window_active(self, now: datetime) -> bool:
        start_dt, end_dt = self._window_bounds_custom(now, "fan_night_start", "fan_night_end")
        return start_dt <= now <= end_dt

    def _heater_thresholds(self, now: datetime) -> tuple[float, float, bool]:
        t_low = float(self.config.get("heater_t_low", 18) or 18)
        t_high = float(self.config.get("heater_t_high", 20) or 20)
        night_active = False
        if self.config.get("heater_night_enabled"):
            start_dt, end_dt = self._window_bounds_custom(now, "heater_night_start", "heater_night_end")
            night_active = start_dt <= now <= end_dt
            if night_active:
                t_low = float(self.config.get("heater_night_t_low", t_low) or t_low)
                t_high = float(self.config.get("heater_night_t_high", t_high) or t_high)
        if t_low >= t_high:
            t_high = t_low + 1.0
        return t_low, t_high, night_active

    def _pump_within_window(self, now: datetime) -> bool:
        start_dt, end_dt = self._window_bounds_custom(now, "pump_window_start", "pump_window_end")
        return start_dt <= now <= end_dt

    def _pump_dry_check(self, soil_entry: Dict[str, Any]) -> Tuple[bool, Optional[float]]:
        channel = str(self.config.get("pump_soil_channel", "ch0") or "ch0").lower()
        if channel not in ("ch0", "ch1", "ch2", "ch3"):
            channel = "ch0"
        threshold = float(self.config.get("pump_dry_threshold", 0) or 0)
        if threshold <= 0:
            return False, None
        value = soil_entry.get(channel)
        try:
            value_f = float(value)
        except (TypeError, ValueError):
            return False, None
        dry_when_above = bool(self.config.get("pump_dry_when_above"))
        is_dry = value_f >= threshold if dry_when_above else value_f <= threshold
        return is_dry, value_f

    def _automation_off(self, channel: str, reason: str) -> None:
        self.actuator_manager.set_state(channel, False, reason)
        self.last_auto_off_ts = time.time()
        self.last_auto_off_reason = reason
        log_actuation(channel, False, reason, None)

    def _fan_off(self, channel: str, reason: str) -> None:
        self.actuator_manager.set_state(channel, False, reason)
        self.fan_last_auto_off_ts = time.time()
        self.fan_last_auto_off_reason = reason
        log_actuation(channel, False, reason, None)

    def _heater_off(self, channel: str, reason: str) -> None:
        self.actuator_manager.set_state(channel, False, reason)
        self.heater_last_auto_off_ts = time.time()
        self.heater_last_auto_off_reason = reason
        log_actuation(channel, False, reason, None)

    def _pump_off(self, channel: str, reason: str) -> None:
        self.actuator_manager.set_state(channel, False, reason)
        self.pump_last_auto_off_ts = time.time()
        self.pump_last_auto_off_reason = reason
        log_actuation(channel, False, reason, None)

    def status(self) -> Dict[str, Any]:
        now = datetime.now()
        enabled = bool(self.config.get("enabled"))
        manual_until = self.manual_override_until_ts if enabled else 0.0
        block_until = self.block_until_ts if enabled else 0.0
        min_off_minutes = int(self.config.get("min_off_minutes", 0) or 0)
        target = int(self.config.get("target_ok_minutes", 0) or 0)
        target_reached = enabled and target > 0 and self.ok_minutes_today >= target
        lux_paused = self.last_lux_error_active if enabled else False
        fan_enabled = bool(self.config.get("fan_enabled"))
        fan_manual_until = self.fan_manual_override_until_ts if fan_enabled else 0.0
        fan_min_off_minutes = int(self.config.get("fan_min_off_minutes", 0) or 0)
        fan_max_minutes = int(self.config.get("fan_max_minutes", 0) or 0)
        fan_rh_high, fan_rh_low, fan_night_active = self._fan_thresholds(now) if fan_enabled else (0, 0, False)
        fan_periodic_enabled = bool(self.config.get("fan_periodic_enabled"))
        fan_periodic_every = int(self.config.get("fan_periodic_every_minutes", 0) or 0)
        fan_periodic_duration = int(self.config.get("fan_periodic_duration_minutes", 0) or 0)
        fan_periodic_night_enabled = bool(self.config.get("fan_periodic_night_enabled"))
        fan_periodic_night_every = int(self.config.get("fan_periodic_night_every_minutes", 0) or 0)
        fan_periodic_night_duration = int(self.config.get("fan_periodic_night_duration_minutes", 0) or 0)
        fan_periodic_last_start_ts = self.fan_periodic_last_start_ts or None
        heater_enabled = bool(self.config.get("heater_enabled"))
        heater_manual_until = self.heater_manual_override_until_ts if heater_enabled else 0.0
        heater_min_off_minutes = int(self.config.get("heater_min_off_minutes", 0) or 0)
        heater_max_minutes = int(self.config.get("heater_max_minutes", 0) or 0)
        heater_t_low, heater_t_high, heater_night_active = self._heater_thresholds(now) if heater_enabled else (0.0, 0.0, False)
        heater_sensor = self._heater_sensor_key()
        heater_fan_required = bool(self.config.get("heater_fan_required"))
        pump_enabled = bool(self.config.get("pump_enabled"))
        pump_manual_until = self.pump_manual_override_until_ts if pump_enabled else 0.0
        pump_max_daily = int(self.config.get("pump_max_daily_seconds", 0) or 0)
        pump_pulse_seconds = int(self.config.get("pump_pulse_seconds", 0) or 0)
        pump_within_window = self._pump_within_window(now) if pump_enabled else False
        pump_channel = str(self.config.get("pump_soil_channel", "ch0") or "ch0").lower()
        pump_threshold = float(self.config.get("pump_dry_threshold", 0) or 0)
        pump_dry_when_above = bool(self.config.get("pump_dry_when_above"))
        return {
            "enabled": enabled,
            "lux_paused": lux_paused,
            "manual_override_until_ts": manual_until or None,
            "block_until_ts": block_until or None,
            "ok_minutes_today": round(self.ok_minutes_today, 1),
            "target_ok_minutes": target,
            "within_window": self._within_window(now),
            "min_off_minutes": min_off_minutes,
            "last_auto_off_ts": self.last_auto_off_ts or None,
            "last_auto_off_reason": self.last_auto_off_reason or None,
            "target_reached": target_reached,
            "fan": {
                "enabled": fan_enabled,
                "rh_high": fan_rh_high,
                "rh_low": fan_rh_low,
                "max_minutes": fan_max_minutes,
                "min_off_minutes": fan_min_off_minutes,
                "manual_override_until_ts": fan_manual_until or None,
                "last_auto_off_ts": self.fan_last_auto_off_ts or None,
                "last_auto_off_reason": self.fan_last_auto_off_reason or None,
                "night_active": fan_night_active,
                "periodic_enabled": fan_periodic_enabled,
                "periodic_every_minutes": fan_periodic_every,
                "periodic_duration_minutes": fan_periodic_duration,
                "periodic_night_enabled": fan_periodic_night_enabled,
                "periodic_night_every_minutes": fan_periodic_night_every,
                "periodic_night_duration_minutes": fan_periodic_night_duration,
                "periodic_last_start_ts": fan_periodic_last_start_ts,
            },
            "heater": {
                "enabled": heater_enabled,
                "sensor": heater_sensor,
                "t_low": round(heater_t_low, 1) if heater_enabled else None,
                "t_high": round(heater_t_high, 1) if heater_enabled else None,
                "max_minutes": heater_max_minutes,
                "min_off_minutes": heater_min_off_minutes,
                "manual_override_until_ts": heater_manual_until or None,
                "last_auto_off_ts": self.heater_last_auto_off_ts or None,
                "last_auto_off_reason": self.heater_last_auto_off_reason or None,
                "night_active": heater_night_active,
                "fan_required": heater_fan_required,
            },
            "pump": {
                "enabled": pump_enabled,
                "soil_channel": pump_channel,
                "dry_threshold": pump_threshold,
                "dry_when_above": pump_dry_when_above,
                "pulse_seconds": pump_pulse_seconds,
                "max_daily_seconds": pump_max_daily,
                "daily_used_seconds": round(self.pump_daily_seconds, 1),
                "within_window": pump_within_window,
                "block_until_ts": self.pump_block_until_ts or None,
                "manual_override_until_ts": pump_manual_until or None,
                "last_auto_ts": self.pump_last_auto_ts or None,
                "last_auto_off_ts": self.pump_last_auto_off_ts or None,
                "last_auto_off_reason": self.pump_last_auto_off_reason or None,
            },
        }

    def tick(self, safe_mode: bool) -> None:
        now = datetime.now()
        reset_key = self._reset_key(now)
        if reset_key != self.last_reset_date:
            self.reset_daily()
            self.last_reset_date = reset_key
        if self.config.get("enabled"):
            self._tick_lux(now, safe_mode)
        if self.config.get("fan_enabled"):
            self._tick_fan(now, safe_mode)
        if self.config.get("fan_periodic_enabled"):
            self._tick_fan_periodic(now, safe_mode)
        if self.config.get("heater_enabled"):
            self._tick_heater(now, safe_mode)
        if self.config.get("pump_enabled"):
            self._tick_pump(now, safe_mode)

    def _tick_lux(self, now: datetime, safe_mode: bool) -> None:
        latest = self.sensor_manager.latest()
        lux_entry = latest.get("readings", {}).get("bh1750", {})
        if lux_entry.get("status") not in (None, "ok", "simulated"):
            now_ts = time.time()
            if now_ts - self.last_lux_error_ts > SENSOR_ALERT_COOLDOWN_SECONDS:
                alerts.add("warning", "Lux automation paused: BH1750 error")
                self.last_lux_error_ts = now_ts
            self.last_lux_error_active = True
            return
        if self.last_lux_error_active:
            alerts.add("info", "Lux automation resumed: BH1750 OK")
            self.last_lux_error_active = False
        within_window = self._within_window(now)
        start_dt, end_dt = self._window_bounds(now)
        lux_value = lux_entry.get("lux")
        lux_max = int(self.config.get("lux_max", 0) or 0)
        if lux_value is not None:
            elapsed = time.time() - self.last_sample_ts
            if lux_value >= self.config.get("lux_ok", 350):
                self.ok_minutes_today += (elapsed / 60.0)
        self.last_sample_ts = time.time()
        light_channel = self._find_light_channel()
        if not light_channel:
            return
        if safe_mode:
            # avoid touching actuators in safe mode
            return
        state = self.actuator_manager.get_state().get(light_channel, {})
        reason = str(state.get("reason") or "")
        last_change = state.get("last_change_ts")
        manual_override_minutes = int(self.config.get("manual_override_minutes", 0) or 0)
        if manual_override_minutes > 0 and reason in ("manual", "test_panel"):
            override_until = (last_change or time.time()) + manual_override_minutes * 60
            if last_change and time.time() < override_until:
                self.manual_override_until_ts = override_until
                return
        self.manual_override_until_ts = 0.0
        lux_too_high = lux_max > 0 and lux_value is not None and lux_value >= lux_max
        if lux_too_high:
            now_ts = time.time()
            if now_ts - self.last_lux_max_alert_ts > SENSOR_ALERT_COOLDOWN_SECONDS:
                alerts.add("info", "Lux automation paused: lux above LUX_MAX")
                self.last_lux_max_alert_ts = now_ts
            if state.get("state") and reason.startswith("automation"):
                self._automation_off(light_channel, "automation_lux_max")
            return
        target = int(self.config.get("target_ok_minutes", 300) or 0)
        target_reached = target > 0 and self.ok_minutes_today >= target
        desired_on = within_window and not target_reached
        min_off_minutes = int(self.config.get("min_off_minutes", 0) or 0)
        if not desired_on:
            self.block_until_ts = 0.0
        on_since = None
        if state.get("state") and reason.startswith("automation"):
            on_since = last_change or time.time()
        max_block_minutes = int(self.config.get("max_block_minutes", 0) or 0)
        if desired_on and max_block_minutes > 0 and on_since:
            if time.time() - on_since >= max_block_minutes * 60:
                self._automation_off(light_channel, "automation_max_block")
                self.block_until_ts = end_dt.timestamp()
                alerts.add("warning", "Lux automation blocked: max block limit reached")
                return
        if desired_on and self.block_until_ts and time.time() < self.block_until_ts:
            if state.get("state") and reason.startswith("automation"):
                self._automation_off(light_channel, "automation_block")
            return
        if desired_on:
            if min_off_minutes > 0 and self.last_auto_off_ts:
                if time.time() - self.last_auto_off_ts < min_off_minutes * 60:
                    if self.last_auto_off_reason.startswith("automation") and self.last_auto_off_reason != "automation_window":
                        now_ts = time.time()
                        if now_ts - self.last_min_off_alert_ts > SENSOR_ALERT_COOLDOWN_SECONDS:
                            alerts.add("info", "Lux automation paused: min off cooldown")
                            self.last_min_off_alert_ts = now_ts
                        return
            if not state.get("state"):
                self.actuator_manager.set_state(light_channel, True, "automation")
                log_actuation(light_channel, True, "automation", None)
            return
        if state.get("state") and reason.startswith("automation"):
            if not within_window:
                self._automation_off(light_channel, "automation_window")
                return
            min_on_minutes = int(self.config.get("min_on_minutes", 0) or 0)
            if min_on_minutes > 0 and on_since and time.time() - on_since < min_on_minutes * 60:
                return
            self._automation_off(light_channel, "automation_target_met")
            if not self.last_target_met_active:
                now_ts = time.time()
                if now_ts - self.last_target_met_alert_ts > SENSOR_ALERT_COOLDOWN_SECONDS:
                    alerts.add("info", "Lux automation target achieved")
                    self.last_target_met_alert_ts = now_ts
                self.last_target_met_active = True
            return
        if not target_reached:
            self.last_target_met_active = False

    def _tick_fan(self, now: datetime, safe_mode: bool) -> None:
        if safe_mode:
            return
        latest = self.sensor_manager.latest()
        dht_entry = latest.get("readings", {}).get("dht22", {})
        if dht_entry.get("status") not in (None, "ok", "simulated"):
            return
        try:
            humidity = float(dht_entry.get("humidity"))
        except (TypeError, ValueError):
            return
        fan_channel = self._find_fan_channel()
        if not fan_channel:
            return
        state = self.actuator_manager.get_state().get(fan_channel, {})
        reason = str(state.get("reason") or "")
        last_change = state.get("last_change_ts")
        manual_override_minutes = int(self.config.get("fan_manual_override_minutes", 0) or 0)
        if manual_override_minutes > 0 and reason in ("manual", "test_panel"):
            override_until = (last_change or time.time()) + manual_override_minutes * 60
            if last_change and time.time() < override_until:
                self.fan_manual_override_until_ts = override_until
                return
        self.fan_manual_override_until_ts = 0.0
        rh_high, rh_low, _night_active = self._fan_thresholds(now)
        max_minutes = int(self.config.get("fan_max_minutes", 0) or 0)
        min_off_minutes = int(self.config.get("fan_min_off_minutes", 0) or 0)
        is_auto = reason.startswith("fan_auto")
        desired_on = False
        if state.get("state") and is_auto:
            desired_on = humidity > rh_low
        else:
            desired_on = humidity >= rh_high
        if state.get("state") and is_auto:
            on_since = last_change or time.time()
            if max_minutes > 0 and time.time() - on_since >= max_minutes * 60:
                self._fan_off(fan_channel, "fan_auto_max")
                return
        if desired_on:
            if min_off_minutes > 0 and self.fan_last_auto_off_ts:
                if time.time() - self.fan_last_auto_off_ts < min_off_minutes * 60:
                    return
            if not state.get("state"):
                self.actuator_manager.set_state(fan_channel, True, "fan_auto_on")
                log_actuation(fan_channel, True, "fan_auto_on", None)
            return
        if state.get("state") and is_auto:
            self._fan_off(fan_channel, "fan_auto_off")

    def _tick_fan_periodic(self, now: datetime, safe_mode: bool) -> None:
        if safe_mode:
            return
        fan_channel = self._find_fan_channel()
        if not fan_channel:
            return
        state = self.actuator_manager.get_state().get(fan_channel, {})
        reason = str(state.get("reason") or "")
        last_change = state.get("last_change_ts")
        manual_override_minutes = int(self.config.get("fan_manual_override_minutes", 0) or 0)
        if manual_override_minutes > 0 and reason in ("manual", "test_panel"):
            override_until = (last_change or time.time()) + manual_override_minutes * 60
            if last_change and time.time() < override_until:
                self.fan_manual_override_until_ts = override_until
                return
        if self.fan_manual_override_until_ts and time.time() < self.fan_manual_override_until_ts:
            return
        self.fan_manual_override_until_ts = 0.0

        every_minutes = int(self.config.get("fan_periodic_every_minutes", 0) or 0)
        duration_minutes = int(self.config.get("fan_periodic_duration_minutes", 0) or 0)
        night_active = False
        if self.config.get("fan_periodic_night_enabled"):
            night_active = self._fan_night_window_active(now)
            if night_active:
                every_minutes = int(self.config.get("fan_periodic_night_every_minutes", every_minutes) or every_minutes)
                duration_minutes = int(
                    self.config.get("fan_periodic_night_duration_minutes", duration_minutes) or duration_minutes
                )
        if every_minutes <= 0 or duration_minutes <= 0:
            return

        if state.get("state"):
            if reason == "fan_periodic_on":
                on_since = last_change or time.time()
                if time.time() - on_since >= duration_minutes * 60:
                    if self.config.get("fan_enabled"):
                        latest = self.sensor_manager.latest()
                        dht_entry = latest.get("readings", {}).get("dht22", {})
                        if dht_entry.get("status") in (None, "ok", "simulated"):
                            try:
                                humidity = float(dht_entry.get("humidity"))
                            except (TypeError, ValueError):
                                humidity = None
                            if humidity is not None:
                                rh_high, _rh_low, _night = self._fan_thresholds(now)
                                if humidity >= rh_high:
                                    self.actuator_manager.set_state(fan_channel, True, "fan_auto_on")
                                    log_actuation(fan_channel, True, "fan_auto_on", None)
                                    return
                    self._fan_off(fan_channel, "fan_periodic_off")
            return

        now_ts = time.time()
        if self.fan_periodic_last_start_ts and now_ts - self.fan_periodic_last_start_ts < every_minutes * 60:
            return
        self.actuator_manager.set_state(fan_channel, True, "fan_periodic_on")
        log_actuation(fan_channel, True, "fan_periodic_on", None)
        self.fan_periodic_last_start_ts = now_ts

    def _tick_heater(self, now: datetime, safe_mode: bool) -> None:
        if safe_mode:
            return
        sensor_key = self._heater_sensor_key()
        latest = self.sensor_manager.latest()
        sensor_entry = latest.get("readings", {}).get(sensor_key, {})
        if sensor_entry.get("status") not in (None, "ok", "simulated"):
            return
        try:
            temperature = float(sensor_entry.get("temperature"))
        except (TypeError, ValueError):
            return
        heater_channel = self._find_heater_channel()
        if not heater_channel:
            return
        state = self.actuator_manager.get_state().get(heater_channel, {})
        reason = str(state.get("reason") or "")
        last_change = state.get("last_change_ts")
        manual_override_minutes = int(self.config.get("heater_manual_override_minutes", 0) or 0)
        if manual_override_minutes > 0 and reason in ("manual", "test_panel"):
            override_until = (last_change or time.time()) + manual_override_minutes * 60
            if last_change and time.time() < override_until:
                self.heater_manual_override_until_ts = override_until
                return
        self.heater_manual_override_until_ts = 0.0
        t_low, t_high, _night_active = self._heater_thresholds(now)
        max_minutes = int(self.config.get("heater_max_minutes", 0) or 0)
        min_off_minutes = int(self.config.get("heater_min_off_minutes", 0) or 0)
        is_auto = reason.startswith("heater_auto")
        if state.get("state") and is_auto:
            desired_on = temperature < t_high
        else:
            desired_on = temperature <= t_low
        fan_required = bool(self.config.get("heater_fan_required"))
        fan_blocked = False
        if fan_required:
            fan_channel = self._find_fan_channel()
            if fan_channel:
                fan_state = self.actuator_manager.get_state().get(fan_channel, {})
                fan_blocked = not bool(fan_state.get("state")) and desired_on
            else:
                fan_blocked = False
        _record_threshold_alert(
            "heater_fan_block",
            fan_blocked,
            "Isıtıcı otomasyon beklemede: fan kapalı.",
            "Isıtıcı otomasyon fan şartı normale döndü.",
        )
        if fan_blocked:
            if state.get("state") and is_auto:
                self._heater_off(heater_channel, "heater_auto_fan_required")
            return
        if state.get("state") and is_auto:
            on_since = last_change or time.time()
            safety_max = int(app_state.limits.get("heater_max_seconds", 0) or 0)
            auto_max = max_minutes * 60 if max_minutes > 0 else 0
            max_runtime = 0
            if safety_max > 0:
                max_runtime = safety_max
            if auto_max > 0:
                max_runtime = min(max_runtime, auto_max) if max_runtime else auto_max
            if max_runtime and time.time() - on_since >= max_runtime:
                self._heater_off(heater_channel, "heater_auto_max")
                return
        if desired_on:
            if min_off_minutes > 0 and self.heater_last_auto_off_ts:
                if time.time() - self.heater_last_auto_off_ts < min_off_minutes * 60:
                    return
            if not state.get("state"):
                self.actuator_manager.set_state(heater_channel, True, "heater_auto_on")
                log_actuation(heater_channel, True, "heater_auto_on", None)
            return
        if state.get("state") and is_auto:
            self._heater_off(heater_channel, "heater_auto_off")

    def _tick_pump(self, now: datetime, safe_mode: bool) -> None:
        if safe_mode:
            return
        latest = self.sensor_manager.latest()
        soil_entry = latest.get("readings", {}).get("soil", {})
        if soil_entry.get("status") not in (None, "ok", "simulated"):
            return
        pump_channel = self._find_pump_channel()
        if not pump_channel:
            return
        state = self.actuator_manager.get_state().get(pump_channel, {})
        reason = str(state.get("reason") or "")
        last_change = state.get("last_change_ts")
        manual_override_minutes = int(self.config.get("pump_manual_override_minutes", 0) or 0)
        if manual_override_minutes > 0 and reason in ("manual", "test_panel"):
            override_until = (last_change or time.time()) + manual_override_minutes * 60
            if last_change and time.time() < override_until:
                self.pump_manual_override_until_ts = override_until
                return
        self.pump_manual_override_until_ts = 0.0
        if state.get("state"):
            return
        if not self._pump_within_window(now):
            return
        max_daily = int(self.config.get("pump_max_daily_seconds", 0) or 0)
        if max_daily <= 0:
            if self.pump_block_until_ts:
                self.pump_block_until_ts = 0.0
                _record_threshold_alert(
                    "pump_daily_limit",
                    False,
                    "Pompa otomasyonu durdu: günlük limit doldu.",
                    "Pompa günlük limit sıfırlandı.",
                )
        if max_daily > 0 and self.pump_daily_seconds >= max_daily:
            if not self.pump_block_until_ts:
                reset_key = self._reset_key(now)
                reset_dt = datetime.combine(reset_key, _parse_hhmm(self.config.get("reset_time", "00:00")))
                if now >= reset_dt:
                    reset_dt += timedelta(days=1)
                self.pump_block_until_ts = reset_dt.timestamp()
                _record_threshold_alert(
                    "pump_daily_limit",
                    True,
                    "Pompa otomasyonu durdu: günlük limit doldu.",
                    "Pompa günlük limit sıfırlandı.",
                )
            return
        if self.pump_block_until_ts and time.time() < self.pump_block_until_ts:
            return
        if self.pump_block_until_ts and time.time() >= self.pump_block_until_ts:
            self.pump_block_until_ts = 0.0
            _record_threshold_alert(
                "pump_daily_limit",
                False,
                "Pompa otomasyonu durdu: günlük limit doldu.",
                "Pompa günlük limit sıfırlandı.",
            )
        dry, _value = self._pump_dry_check(soil_entry)
        if not dry:
            return
        cooldown = int(app_state.limits.get("pump_cooldown_seconds", 60) or 60)
        if actuator_manager.last_pump_stop_ts and time.time() - actuator_manager.last_pump_stop_ts < cooldown:
            return
        pulse_seconds = int(self.config.get("pump_pulse_seconds", 5) or 5)
        if pulse_seconds <= 0:
            return
        max_pump = int(app_state.limits.get("pump_max_seconds", 15) or 15)
        pulse_seconds = min(pulse_seconds, max_pump)
        if max_daily > 0:
            remaining = max_daily - self.pump_daily_seconds
            if remaining <= 0:
                return
            pulse_seconds = min(pulse_seconds, remaining)
        try:
            apply_actuator_command(pump_channel, True, pulse_seconds, "pump_auto_on")
        except ActuationError:
            return
        self.pump_daily_seconds += pulse_seconds
        self.pump_last_auto_ts = time.time()


class AlertManager:
    def __init__(self) -> None:
        self.alerts: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

    def add(self, severity: str, message: str) -> None:
        with self.lock:
            ts = datetime.utcnow().isoformat()
            self.alerts.append({"severity": severity, "message": message, "ts": ts})
            self.alerts = self.alerts[-50:]
        log_event("alert", severity, message, None)

    def get(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.alerts)


class AppState:
    def __init__(self, actuator_manager: ActuatorManager, sensor_manager: SensorManager, automation: AutomationEngine, alerts: AlertManager):
        self.actuator_manager = actuator_manager
        self.sensor_manager = sensor_manager
        self.automation = automation
        self.alerts = alerts
        self.safe_mode = True
        self.test_mode = False
        self.estop = False
        self.pump_unlocked = False
        self.sensor_faults = {"pump": False, "heater": False}
        self.limits = dict(DEFAULT_LIMITS)
        self.alerts_config = dict(DEFAULT_ALERTS)
        self.lock = threading.Lock()

    def toggle_safe_mode(self, enabled: bool) -> None:
        with self.lock:
            self.safe_mode = enabled
            if enabled:
                self.actuator_manager.set_all_off("safe_mode")
        log_event("system", "warning" if enabled else "info", f"SAFE MODE {'AÇIK' if enabled else 'KAPALI'}", None)

    def update_limits(self, data: Dict[str, Any]) -> None:
        with self.lock:
            for key in DEFAULT_LIMITS:
                if key in data:
                    if key == "heater_cutoff_temp":
                        self.limits[key] = float(data[key])
                    else:
                        self.limits[key] = int(data[key])

    def update_alerts(self, data: Dict[str, Any]) -> None:
        with self.lock:
            for key in DEFAULT_ALERTS:
                if key in data:
                    if key == "sensor_offline_minutes":
                        self.alerts_config[key] = int(data[key])
                    else:
                        self.alerts_config[key] = float(data[key])

    def set_test_mode(self, enabled: bool) -> None:
        with self.lock:
            self.test_mode = bool(enabled)
            if not enabled:
                self.pump_unlocked = False
        if not enabled:
            self.actuator_manager.set_all_off("test_mode_off")

    def set_estop(self, enabled: bool) -> None:
        with self.lock:
            self.estop = bool(enabled)
            if enabled:
                self.pump_unlocked = False
        if enabled:
            self.actuator_manager.set_all_off("estop")
        log_event("system", "warning" if enabled else "info", f"E-STOP {'AÇIK' if enabled else 'KAPALI'}", None)

    def set_pump_unlocked(self, enabled: bool) -> None:
        with self.lock:
            self.pump_unlocked = bool(enabled)

    def set_sensor_faults(self, pump: Optional[bool] = None, heater: Optional[bool] = None) -> None:
        with self.lock:
            if pump is not None:
                self.sensor_faults["pump"] = bool(pump)
            if heater is not None:
                self.sensor_faults["heater"] = bool(heater)

    def get_sensor_faults(self) -> Dict[str, bool]:
        with self.lock:
            return dict(self.sensor_faults)

    def get_alerts_config(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.alerts_config)

    def test_panel_state(self) -> Dict[str, bool]:
        with self.lock:
            return {
                "test_mode": self.test_mode,
                "estop": self.estop,
                "pump_unlocked": self.pump_unlocked,
            }


# Flask app factory
app = Flask(__name__)
test_panel = Blueprint(
    "test_panel",
    __name__,
    template_folder=str(TEST_PANEL_DIR / "templates"),
    static_folder=str(TEST_PANEL_DIR / "static"),
    static_url_path="static",
    url_prefix="/test",
)
backend = GPIOBackend()
channel_config = []


def load_channel_config() -> List[Dict[str, Any]]:
    def infer_role(name: str, description: str) -> str:
        label = f"{name} {description}".upper()
        if "PUMP" in label or "POMPA" in label:
            return "pump"
        if "HEATER" in label or "ISITICI" in label or "HEAT" in label:
            return "heater"
        if "FAN" in label:
            return "fan"
        if "LIGHT" in label or "ISIK" in label or "IŞIK" in label:
            return "light"
        return "other"

    def normalize(channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for chan in channels:
            entry = dict(chan)
            entry.setdefault("role", infer_role(entry.get("name", ""), entry.get("description", "")))
            entry.setdefault("power_w", 0)
            entry.setdefault("quantity", 1)
            entry.setdefault("voltage_v", None)
            entry.setdefault("notes", "")
            normalized.append(entry)
        return normalized

    if CHANNEL_CONFIG_PATH.exists():
        with CHANNEL_CONFIG_PATH.open() as f:
            return normalize(json.load(f))
    default_channels = [
        {
            "name": "R1_LIGHT_K1A",
            "gpio_pin": 21,
            "active_low": True,
            "description": "LED Bar",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": None,
        },
        {
            "name": "R2_LIGHT_K1B",
            "gpio_pin": 20,
            "active_low": True,
            "description": "LED Bar 2",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": None,
        },
        {
            "name": "R3_PUMP",
            "gpio_pin": 16,
            "active_low": True,
            "description": "Pump",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": None,
        },
        {
            "name": "R4_HEATER",
            "gpio_pin": 12,
            "active_low": True,
            "description": "Heater",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": None,
        },
        {
            "name": "R5_FAN",
            "gpio_pin": 7,
            "active_low": True,
            "description": "Fan",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": None,
        },
        {
            "name": "R6_POT_FAN",
            "gpio_pin": 8,
            "active_low": True,
            "description": "Pot Fan",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": None,
        },
    ]
    CONFIG_DIR.mkdir(exist_ok=True)
    with CHANNEL_CONFIG_PATH.open("w") as f:
        json.dump(default_channels, f, indent=2)
    return normalize(default_channels)


def load_sensors_config() -> Dict[str, Any]:
    defaults = {
        "dht22_gpio": int(os.getenv("DHT22_GPIO", "17")),
        "bh1750_addr": os.getenv("BH1750_ADDR", "0x23"),
        "ads1115_addr": "0x48",
        "ds18b20_enabled": True,
        "lcd_enabled": True,
        "lcd_addr": "0x27",
        "lcd_port": 1,
        "lcd_cols": 20,
        "lcd_rows": 4,
        "lcd_expander": "PCF8574",
        "lcd_charmap": "A00",
        "lcd_mode": "auto",
        "lcd_lines": ["", "", "", ""],
    }
    if SENSORS_CONFIG_PATH.exists():
        try:
            with SENSORS_CONFIG_PATH.open() as f:
                data = json.load(f)
            merged = dict(defaults)
            merged.update(data or {})
            return merged
        except Exception:
            return defaults
    CONFIG_DIR.mkdir(exist_ok=True)
    with SENSORS_CONFIG_PATH.open("w") as f:
        json.dump(defaults, f, indent=2)
    return defaults


channel_config = load_channel_config()
sensors_config = load_sensors_config()
actuator_manager = ActuatorManager(backend, channel_config)
sensor_manager = SensorManager()
sensor_manager.reload_config(sensors_config)
automation_engine = AutomationEngine(actuator_manager, sensor_manager)
alerts = AlertManager()
app_state = AppState(actuator_manager, sensor_manager, automation_engine, alerts)
lcd_manager = LCDManager(sensors_config)


# Database

def _ensure_column(cur: sqlite3.Cursor, table: str, column: str, col_type: str) -> None:
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS actuator_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            state TEXT,
            reason TEXT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            seconds INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sensor_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            dht_temp REAL,
            dht_hum REAL,
            ds18_temp REAL,
            lux REAL,
            soil_ch0 REAL,
            soil_ch1 REAL,
            soil_ch2 REAL,
            soil_ch3 REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            category TEXT,
            level TEXT,
            message TEXT,
            meta TEXT
        )
        """
    )
    _ensure_column(cur, "sensor_log", "soil_ch2", "REAL")
    _ensure_column(cur, "sensor_log", "soil_ch3", "REAL")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sensor_log_ts ON sensor_log (ts)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_event_log_ts ON event_log (ts)")
    conn.commit()
    conn.close()


def log_actuation(name: str, on: bool, reason: str, seconds: Optional[int]) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO actuator_log (name, state, reason, seconds) VALUES (?, ?, ?, ?)",
        (name, "on" if on else "off", reason, seconds),
    )
    conn.commit()
    conn.close()
    level = "info"
    lowered = (reason or "").lower()
    if any(token in lowered for token in ("error", "emergency", "stale", "safe", "estop", "cutoff")):
        level = "warning"
    log_event(
        "actuator",
        level,
        f"{name} {'ON' if on else 'OFF'} ({reason})",
        {"name": name, "state": "on" if on else "off", "reason": reason, "seconds": seconds},
    )


def log_event(category: str, level: str, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        payload = json.dumps(meta) if meta else None
        cur.execute(
            "INSERT INTO event_log (ts, category, level, message, meta) VALUES (?, ?, ?, ?, ?)",
            (time.time(), category, level, message, payload),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _status_loggable(status: Optional[str]) -> bool:
    return status in ("ok", "simulated")


def log_sensor_readings(readings: Dict[str, Any]) -> bool:
    statuses = [
        readings.get("dht22", {}).get("status"),
        readings.get("ds18b20", {}).get("status"),
        readings.get("bh1750", {}).get("status"),
        readings.get("soil", {}).get("status"),
    ]
    if not any(_status_loggable(status) for status in statuses):
        return False

    dht = readings.get("dht22", {})
    ds18 = readings.get("ds18b20", {})
    bh = readings.get("bh1750", {})
    soil = readings.get("soil", {})
    ts = time.time()

    row = (
        ts,
        _coerce_float(dht.get("temperature")),
        _coerce_float(dht.get("humidity")),
        _coerce_float(ds18.get("temperature")),
        _coerce_float(bh.get("lux")),
        _coerce_float(soil.get("ch0")),
        _coerce_float(soil.get("ch1")),
        _coerce_float(soil.get("ch2")),
        _coerce_float(soil.get("ch3")),
    )

    db_ok = False
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO sensor_log (
                ts, dht_temp, dht_hum, ds18_temp, lux, soil_ch0, soil_ch1, soil_ch2, soil_ch3
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        conn.commit()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    csv_ok = _append_sensor_csv(row)
    return db_ok or csv_ok


def _append_sensor_csv(
    row: Tuple[float, Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]],
) -> bool:
    try:
        SENSOR_CSV_LOG_DIR.mkdir(exist_ok=True)
        day = datetime.now().strftime("%Y-%m-%d")
        path = SENSOR_CSV_LOG_DIR / f"sensor_log_{day}.csv"
        write_header = not path.exists()
        with path.open("a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow([
                    "ts",
                    "dht_temp",
                    "dht_hum",
                    "ds18_temp",
                    "lux",
                    "soil_ch0",
                    "soil_ch1",
                    "soil_ch2",
                    "soil_ch3",
                ])
            writer.writerow(list(row))
        return True
    except Exception:
        return False


init_db()


# Helpers

def _is_local_request() -> bool:
    addr = request.remote_addr or ""
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def require_admin() -> Optional[Any]:
    if ADMIN_TOKEN:
        token = request.headers.get("X-Admin-Token") or request.args.get("token")
        if token != ADMIN_TOKEN:
            return jsonify({"error": "admin token required"}), 403
        return None
    if _is_local_request():
        return None
    return jsonify({"error": "admin access restricted to local network"}), 403


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


_sensor_alert_state: Dict[str, Dict[str, Any]] = {}
_last_sensor_log_ts: float = 0.0
_sensor_last_ok_ts: Dict[str, float] = {}
_sensor_first_seen_ts: Dict[str, float] = {}


def _sensor_health_snapshot() -> Dict[str, Any]:
    now = time.time()
    latest = sensor_manager.latest()
    readings = latest.get("readings", {})
    offline_minutes = int(app_state.alerts_config.get("sensor_offline_minutes", 0) or 0)
    offline_limit_seconds = max(0, offline_minutes) * 60
    sensor_map = {
        "dht22": "DHT22",
        "ds18b20": "DS18B20",
        "bh1750": "BH1750",
        "soil": "ADS1115",
    }
    health: Dict[str, Any] = {}
    for key, label in sensor_map.items():
        entry = readings.get(key) or {}
        status = entry.get("status") or "unknown"
        last_seen_ts = _coerce_float(entry.get("ts"))
        last_ok_ts = _sensor_last_ok_ts.get(key)
        if status in ("ok", "simulated"):
            last_ok_ts = last_seen_ts or last_ok_ts or now
        first_seen_ts = _sensor_first_seen_ts.get(key) or last_seen_ts or now
        offline_seconds = None
        if status in ("ok", "simulated"):
            offline_seconds = 0.0
        else:
            reference = last_ok_ts or first_seen_ts
            if reference:
                offline_seconds = max(0.0, now - reference)
        health[key] = {
            "label": label,
            "status": status,
            "last_seen_ts": last_seen_ts,
            "last_ok_ts": last_ok_ts,
            "first_seen_ts": first_seen_ts,
            "offline_seconds": offline_seconds,
            "offline_limit_seconds": offline_limit_seconds,
        }
    return health


def _energy_summary() -> Dict[str, Any]:
    channel_map = actuator_manager.channels

    def channel_power(entry: Dict[str, Any]) -> Tuple[float, int]:
        power = _coerce_float(entry.get("power_w")) or 0.0
        quantity_raw = entry.get("quantity", 1)
        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            quantity = 1
        if quantity < 0:
            quantity = 0
        return power, quantity

    def cost_try(total_wh: float) -> Dict[str, float]:
        limits = app_state.limits
        low = _coerce_float(limits.get("energy_kwh_low")) or 0.0
        high = _coerce_float(limits.get("energy_kwh_high")) or 0.0
        threshold = _coerce_float(limits.get("energy_kwh_threshold")) or 0.0
        total_kwh = max(0.0, total_wh / 1000.0)
        if threshold <= 0 or high <= 0:
            return {"total_kwh": round(total_kwh, 3), "cost_try": round(total_kwh * low, 2)}
        low_kwh = min(total_kwh, threshold)
        high_kwh = max(0.0, total_kwh - threshold)
        cost = (low_kwh * low) + (high_kwh * high)
        return {
            "total_kwh": round(total_kwh, 3),
            "cost_try": round(cost, 2),
            "low_kwh": round(low_kwh, 3),
            "high_kwh": round(high_kwh, 3),
        }

    windows = {
        "window_24h": "-24 hours",
        "window_7d": "-7 days",
    }
    base_power_w = _coerce_float(os.getenv("PI_BASE_POWER_W", "5.0")) or 0.0
    summary: Dict[str, Any] = {"unit": "Wh", "only_timed": True, "base_power_w": base_power_w}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for key, window in windows.items():
        window_hours = 24 if key == "window_24h" else 7 * 24
        cur.execute(
            """
            SELECT name, SUM(seconds) FROM actuator_log
            WHERE state = 'on'
              AND seconds IS NOT NULL
              AND ts >= datetime('now', ?)
            GROUP BY name
            """,
            (window,),
        )
        rows = cur.fetchall()
        total_wh = 0.0
        channels: Dict[str, Any] = {}
        if base_power_w > 0:
            base_energy = base_power_w * window_hours
            channels["PI_BASE"] = {
                "seconds": window_hours * 3600,
                "power_w": base_power_w,
                "quantity": 1,
                "voltage_v": 5.0,
                "energy_wh": round(base_energy, 3),
            }
            total_wh += base_energy
        for name, seconds in rows:
            if name is None:
                continue
            seconds_val = float(seconds or 0)
            entry = channel_map.get(name, {})
            power_w, quantity = channel_power(entry)
            energy_wh = power_w * quantity * (seconds_val / 3600.0)
            channels[name] = {
                "seconds": round(seconds_val, 1),
                "power_w": power_w,
                "quantity": quantity,
                "voltage_v": entry.get("voltage_v"),
                "energy_wh": round(energy_wh, 3),
            }
            total_wh += energy_wh
        summary[key] = {
            "total_wh": round(total_wh, 3),
            "channels": channels,
            **cost_try(total_wh),
        }
    conn.close()
    return summary


def _parse_ts_param(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(value).timestamp()
    except (TypeError, ValueError):
        return None


def _sensor_status_error(status: Optional[str]) -> bool:
    return bool(status) and status not in ("ok", "simulated")


def _record_sensor_alert(key: str, label: str, status: Optional[str], action: Optional[str] = None) -> None:
    now = time.time()
    state = _sensor_alert_state.get(key, {})
    last_status = state.get("status")
    last_ts = state.get("ts", 0)
    if status == last_status and now - last_ts < SENSOR_ALERT_COOLDOWN_SECONDS:
        return
    suffix = f" ({action})" if action else ""
    alerts.add("warning", f"{label} okuma hatası: {status}{suffix}")
    _sensor_alert_state[key] = {"status": status, "ts": now}


def _record_sensor_recovery(key: str, label: str) -> None:
    now = time.time()
    state = _sensor_alert_state.get(key, {})
    last_status = state.get("status")
    if last_status in (None, "ok", "simulated"):
        return
    alerts.add("info", f"{label} normale döndü.")
    _sensor_alert_state[key] = {"status": "ok", "ts": now}


def _record_threshold_alert(key: str, active: bool, message_on: str, message_off: str) -> None:
    state = _sensor_alert_state.get(key, {})
    last_status = state.get("status")
    if active and last_status != "active":
        alerts.add("warning", message_on)
    elif not active and last_status == "active":
        alerts.add("info", message_off)
    _sensor_alert_state[key] = {"status": "active" if active else "ok", "ts": time.time()}


def _force_off_by_tag(tag: str, reason: str) -> None:
    state_snapshot = actuator_manager.get_state()
    for name, info in state_snapshot.items():
        if tag in name and info.get("state"):
            actuator_manager.set_state(name, False, reason)
            log_actuation(name, False, reason, None)


def _check_sensor_health() -> None:
    latest = sensor_manager.latest()
    readings = latest.get("readings", {})

    dht_status = (readings.get("dht22") or {}).get("status")
    soil_status = (readings.get("soil") or {}).get("status")
    ds_status = (readings.get("ds18b20") or {}).get("status")
    lux_status = (readings.get("bh1750") or {}).get("status")

    dht_error = _sensor_status_error(dht_status)
    soil_error = _sensor_status_error(soil_status)
    ds_error = _sensor_status_error(ds_status)
    heater_sensor = str(automation_engine.config.get("heater_sensor", "dht22") or "dht22").lower()
    heater_error = ds_error if heater_sensor == "ds18b20" else dht_error
    app_state.set_sensor_faults(heater=heater_error, pump=soil_error)

    now_ts = time.time()
    offline_minutes = int(app_state.alerts_config.get("sensor_offline_minutes", 0) or 0)
    offline_seconds = max(0, offline_minutes) * 60
    sensor_map = {
        "dht22": ("DHT22", dht_status),
        "ds18b20": ("DS18B20", ds_status),
        "bh1750": ("BH1750", lux_status),
        "soil": ("ADS1115", soil_status),
    }
    for key, (label, status) in sensor_map.items():
        if key not in _sensor_first_seen_ts:
            _sensor_first_seen_ts[key] = now_ts
        if status in ("ok", "simulated"):
            _sensor_last_ok_ts[key] = now_ts
        if offline_seconds > 0:
            last_ok = _sensor_last_ok_ts.get(key, 0.0)
            reference = last_ok if last_ok else _sensor_first_seen_ts.get(key, now_ts)
            offline_active = status not in ("ok", "simulated") and (now_ts - reference) >= offline_seconds
            _record_threshold_alert(
                f"{key}_offline",
                offline_active,
                f"{label} {offline_minutes} dk içinde okunamadı.",
                f"{label} tekrar OK.",
            )

    heater_cutoff = float(app_state.limits.get("heater_cutoff_temp", 0) or 0)
    heater_over = False
    if not heater_error and heater_cutoff > 0:
        heater_key = "ds18b20" if heater_sensor == "ds18b20" else "dht22"
        heater_label = "DS18B20" if heater_key == "ds18b20" else "DHT22"
        temp_raw = (readings.get(heater_key) or {}).get("temperature")
        try:
            temp_val = float(temp_raw)
        except (TypeError, ValueError):
            temp_val = None
        if temp_val is not None and temp_val >= heater_cutoff:
            heater_over = True
            _force_off_by_tag("HEATER", "heater_cutoff")
        if temp_val is not None:
            message_on = (
                f"Isıtıcı üst limit: {heater_label} {temp_val:.1f}C >= {heater_cutoff:.1f}C, ısıtıcı kapatıldı."
            )
            _record_threshold_alert(
                "heater_cutoff",
                heater_over,
                message_on,
                "Isıtıcı üst limit normale döndü.",
            )

    if dht_error:
        _force_off_by_tag("HEATER", "sensor_error")
        _record_sensor_alert("dht22", "DHT22", dht_status, "heater off")
    else:
        _record_sensor_recovery("dht22", "DHT22")

    if soil_error:
        _force_off_by_tag("PUMP", "sensor_error")
        _record_sensor_alert("soil", "ADS1115", soil_status, "pump off")
    else:
        _record_sensor_recovery("soil", "ADS1115")

    if _sensor_status_error(ds_status):
        _record_sensor_alert("ds18b20", "DS18B20", ds_status)
    else:
        _record_sensor_recovery("ds18b20", "DS18B20")

    if _sensor_status_error(lux_status):
        _record_sensor_alert("bh1750", "BH1750", lux_status)
    else:
        _record_sensor_recovery("bh1750", "BH1750")

    dht_entry = readings.get("dht22") or {}
    if dht_entry.get("status") in ("ok", "simulated"):
        temp_high = float(app_state.alerts_config.get("temp_high_c", 0) or 0)
        temp_low = float(app_state.alerts_config.get("temp_low_c", 0) or 0)
        hum_high = float(app_state.alerts_config.get("hum_high_pct", 0) or 0)
        hum_low = float(app_state.alerts_config.get("hum_low_pct", 0) or 0)
        try:
            temp_val = float(dht_entry.get("temperature"))
        except (TypeError, ValueError):
            temp_val = None
        try:
            hum_val = float(dht_entry.get("humidity"))
        except (TypeError, ValueError):
            hum_val = None
        if temp_val is not None and temp_high > 0:
            _record_threshold_alert(
                "temp_high",
                temp_val >= temp_high,
                f"Sıcaklık yüksek: {temp_val:.1f}C >= {temp_high:.1f}C.",
                "Sıcaklık normale döndü.",
            )
        if temp_val is not None and temp_low > 0:
            _record_threshold_alert(
                "temp_low",
                temp_val <= temp_low,
                f"Sıcaklık düşük: {temp_val:.1f}C <= {temp_low:.1f}C.",
                "Sıcaklık normale döndü.",
            )
        if hum_val is not None and hum_high > 0:
            _record_threshold_alert(
                "hum_high",
                hum_val >= hum_high,
                f"Nem yüksek: {hum_val:.1f}% >= {hum_high:.1f}%.",
                "Nem normale döndü.",
            )
        if hum_val is not None and hum_low > 0:
            _record_threshold_alert(
                "hum_low",
                hum_val <= hum_low,
                f"Nem düşük: {hum_val:.1f}% <= {hum_low:.1f}%.",
                "Nem normale döndü.",
            )


def _check_stale_and_fail_safe() -> None:
    latest = sensor_manager.latest()
    ts = latest.get("ts", 0)
    if not ts:
        return
    if time.time() - ts > SENSOR_STALE_SECONDS:
        risky = [n for n in actuator_manager.channels if "PUMP" in n or "HEATER" in n]
        for name in risky:
            actuator_manager.set_state(name, False, "stale_sensors")
        alerts.add("warning", "Sensor data stale; risky actuators turned off")


def apply_actuator_command(name: str, desired_state: bool, seconds: Optional[int], reason: str) -> None:
    name = name.upper()
    if app_state.estop:
        raise ActuationError("E-STOP active")
    if app_state.safe_mode:
        raise ActuationError("SAFE MODE active")
    if desired_state and "PUMP" in name and app_state.sensor_faults.get("pump"):
        raise ActuationError("Pump locked: soil sensor error")
    if desired_state and "HEATER" in name and app_state.sensor_faults.get("heater"):
        raise ActuationError("Heater locked: temperature sensor error")
    chan = actuator_manager.channels.get(name)
    if not chan:
        raise ActuationError("Unknown actuator")
    current_state = actuator_manager.state.get(name, {}).get("state")
    if desired_state and current_state:
        raise ActuationError("Already on")
    seconds_param = int(seconds) if seconds is not None else None
    if seconds_param is not None and seconds_param <= 0:
        raise ActuationError("Seconds must be positive")
    limits = app_state.limits
    if desired_state and "PUMP" in name:
        if seconds_param is None:
            raise ActuationError("Pump requires seconds")
        if seconds_param <= 0:
            raise ActuationError("Seconds must be positive")
        if seconds_param > limits.get("pump_max_seconds", 15):
            raise ActuationError("Pump duration exceeds max")
        cooldown = limits.get("pump_cooldown_seconds", 60)
        if time.time() - actuator_manager.last_pump_stop_ts < cooldown:
            remaining = int(cooldown - (time.time() - actuator_manager.last_pump_stop_ts))
            raise ActuationError(f"Pump cooldown {remaining}s")
    if desired_state and "HEATER" in name:
        cutoff = float(limits.get("heater_cutoff_temp", 0) or 0)
        if cutoff > 0:
            latest = sensor_manager.latest()
            readings = latest.get("readings", {})
            heater_sensor = str(automation_engine.config.get("heater_sensor", "dht22") or "dht22").lower()
            heater_key = "ds18b20" if heater_sensor == "ds18b20" else "dht22"
            heater_label = "DS18B20" if heater_key == "ds18b20" else "DHT22"
            entry = readings.get(heater_key) or {}
            status = entry.get("status")
            temp_raw = entry.get("temperature")
            if status in ("ok", "simulated"):
                try:
                    temp_val = float(temp_raw)
                except (TypeError, ValueError):
                    temp_val = None
                if temp_val is not None and temp_val >= cutoff:
                    raise ActuationError(
                        f"Heater blocked: {heater_label} {temp_val:.1f}C >= cutoff {cutoff:.1f}C"
                    )
        max_heater = limits.get("heater_max_seconds", 300)
        if seconds_param is None:
            seconds_param = max_heater
        seconds_param = min(seconds_param, max_heater)
    actuator_manager.set_state(name, desired_state, reason, seconds_param)
    log_actuation(name, desired_state, reason, seconds_param)


# Test panel helpers
test_panel_i2c_state: Dict[str, Any] = {"found": [], "err": None, "ts": None}
test_panel_i2c_lock = threading.Lock()


def _infer_relay_type(name: str) -> str:
    upper = name.upper()
    if "PUMP" in upper:
        return "pump"
    if "HEATER" in upper:
        return "heater"
    if "FAN" in upper:
        return "fan"
    if "LIGHT" in upper:
        return "light"
    return "relay"


def _relay_meta(name: str) -> Dict[str, Any]:
    name = name.upper()
    relay_type = _infer_relay_type(name)
    locked = relay_type == "pump"
    for chan in load_channel_config():
        if chan.get("name", "").upper() == name:
            relay_type = chan.get("type") or relay_type
            if "locked" in chan:
                locked = bool(chan["locked"])
            else:
                locked = relay_type == "pump"
            break
    return {"type": relay_type, "locked": locked}


def _test_panel_config() -> Dict[str, Any]:
    channels = load_channel_config()
    relays: Dict[str, Any] = {}
    for chan in channels:
        name = chan["name"].upper()
        relay_type = chan.get("type") or _infer_relay_type(name)
        relay = {
            "gpio": int(chan["gpio_pin"]),
            "name": chan.get("description", name),
            "type": relay_type,
        }
        if relay_type == "pump" or "locked" in chan:
            relay["locked"] = bool(chan.get("locked", relay_type == "pump"))
        relays[name] = relay
    active_low = all(chan.get("active_low", False) for chan in channels) if channels else False
    return {
        "active_low": active_low,
        "relays": relays,
        "safety": {
            "heater_max_on_sec": int(app_state.limits.get("heater_max_seconds", 300)),
            "pump_max_on_sec": int(app_state.limits.get("pump_max_seconds", 15)),
        },
        "sensors": {
            "dht22_gpio": int(os.getenv("DHT22_GPIO", "17")),
            "ds18b20_enabled": True,
            "dht22_enabled": sensor_manager.dht is not None,
            "i2c_bus": 1,
        },
    }


def _build_test_panel_relays() -> Dict[str, Any]:
    channels = load_channel_config()
    channel_map = {chan["name"].upper(): chan for chan in channels}
    relays: Dict[str, Any] = {}
    for name, info in actuator_manager.get_state().items():
        chan = channel_map.get(name, {})
        relay_type = chan.get("type") or _infer_relay_type(name)
        locked = bool(chan.get("locked", relay_type == "pump"))
        relays[name] = {
            "name": info.get("description", name),
            "gpio": info.get("gpio_pin"),
            "type": relay_type,
            "locked": locked,
            "state": bool(info.get("state")),
        }
    return relays


def _build_test_panel_sensors() -> Dict[str, Any]:
    latest = sensor_manager.latest()
    readings = latest.get("readings", {})
    errors: List[Dict[str, Any]] = []
    ok = True

    def status_error(status: Optional[str]) -> Optional[str]:
        if not status or status in ("ok", "simulated"):
            return None
        return str(status)

    dht = readings.get("dht22", {})
    dht_err = status_error(dht.get("status"))
    if dht_err:
        ok = False
        errors.append({"where": "dht22", "msg": dht_err, "ts": dht.get("ts") or time.time()})

    ds = readings.get("ds18b20", {})
    ds_err = status_error(ds.get("status"))
    if ds_err:
        ok = False
        errors.append({"where": "ds18b20", "msg": ds_err, "ts": ds.get("ts") or time.time()})
    ds_sensors: List[Dict[str, Any]] = []
    if ds.get("temperature") is not None:
        try:
            ds_sensors.append({"id": "ds18b20", "c": round(float(ds["temperature"]), 2)})
        except Exception:
            ds_sensors.append({"id": "ds18b20", "c": ds["temperature"]})

    bh = readings.get("bh1750", {})
    bh_err = status_error(bh.get("status"))
    if bh_err:
        ok = False
        errors.append({"where": "bh1750", "msg": bh_err, "ts": bh.get("ts") or time.time()})

    soil = readings.get("soil", {})
    soil_err = status_error(soil.get("status"))
    if soil_err:
        ok = False
        errors.append({"where": "ads1115", "msg": soil_err, "ts": soil.get("ts") or time.time()})

    with test_panel_i2c_lock:
        i2c_scan = dict(test_panel_i2c_state)

    return {
        "ok": ok,
        "last_update": latest.get("ts"),
        "errors": errors,
        "bh1750": {"lux": bh.get("lux"), "err": bh_err, "ts": bh.get("ts")},
        "ads1115": {
            "a0": soil.get("ch0"),
            "a1": soil.get("ch1"),
            "a2": None,
            "a3": None,
            "err": soil_err,
            "ts": soil.get("ts"),
        },
        "ds18b20": {"sensors": ds_sensors, "err": ds_err, "ts": ds.get("ts")},
        "dht22": {"temp": dht.get("temperature"), "hum": dht.get("humidity"), "err": dht_err, "ts": dht.get("ts")},
        "i2c_scan": i2c_scan,
    }


def _build_test_panel_status() -> Dict[str, Any]:
    config = _test_panel_config()
    relays = _build_test_panel_relays()
    config.pop("relays", None)
    return {
        "time": time.time(),
        "safety": app_state.test_panel_state(),
        "safe_mode": app_state.safe_mode,
        "config": config,
        "relays": relays,
        "sensors": _build_test_panel_sensors(),
    }


def _test_panel_can_switch(relay_type: str, locked: bool) -> tuple[bool, str]:
    if app_state.estop:
        return False, "E-STOP active"
    if not app_state.test_mode:
        return False, "Test mode disabled"
    if app_state.safe_mode:
        return False, "SAFE MODE active"
    if relay_type == "pump" and locked and not app_state.pump_unlocked:
        return False, "Pump locked; unlock required"
    return True, "OK"


def _apply_test_panel_config(payload: Dict[str, Any]) -> Optional[str]:
    relays_payload = payload.get("relays", {})
    if relays_payload and not isinstance(relays_payload, dict):
        return "relays must be an object"

    channels = load_channel_config()
    channel_map = {chan["name"].upper(): chan for chan in channels}

    for key, relay in (relays_payload or {}).items():
        name = str(key).upper()
        if name not in channel_map:
            continue
        try:
            channel_map[name]["gpio_pin"] = int(relay.get("gpio", channel_map[name]["gpio_pin"]))
        except Exception:
            return f"{name} gpio must be a number"
        if "type" in relay:
            channel_map[name]["type"] = relay["type"]
        if "locked" in relay:
            channel_map[name]["locked"] = bool(relay["locked"])

    if "active_low" in payload:
        active_low = bool(payload["active_low"])
        for chan in channel_map.values():
            chan["active_low"] = active_low

    updates: Dict[str, Any] = {}
    safety = payload.get("safety", {})
    if isinstance(safety, dict):
        if "pump_max_on_sec" in safety:
            updates["pump_max_seconds"] = int(safety["pump_max_on_sec"])
        if "heater_max_on_sec" in safety:
            updates["heater_max_seconds"] = int(safety["heater_max_on_sec"])
    if updates:
        app_state.update_limits(updates)

    updated_channels = list(channel_map.values())
    CONFIG_DIR.mkdir(exist_ok=True)
    with CHANNEL_CONFIG_PATH.open("w") as f:
        json.dump(updated_channels, f, indent=2)
    actuator_manager.reload_channels(updated_channels)
    return None


def _test_panel_i2c_scan(bus_num: int = 1) -> Dict[str, Any]:
    now = time.time()
    found: List[str] = []
    err = None
    try:
        from smbus2 import SMBus  # type: ignore

        with SMBus(bus_num) as bus:
            for addr in range(0x03, 0x78):
                try:
                    bus.write_quick(addr)
                    found.append(hex(addr))
                except Exception:
                    pass
    except Exception as exc:
        try:
            out = subprocess.check_output(["i2cdetect", "-y", str(bus_num)], text=True)
            for line in out.splitlines():
                if ":" not in line:
                    continue
                parts = line.split(":")[1].strip().split()
                base = int(line.split(":")[0], 16)
                for i, part in enumerate(parts):
                    if part != "--":
                        found.append(hex(base + i))
        except Exception as exc2:
            err = f"smbus2/i2cdetect fail: {exc} / {exc2}"

    with test_panel_i2c_lock:
        test_panel_i2c_state.update({"found": found, "err": err, "ts": now})
        return dict(test_panel_i2c_state)


# Background loops

def _maybe_log_sensor_readings(readings: Dict[str, Any]) -> None:
    global _last_sensor_log_ts
    now = time.time()
    if now - _last_sensor_log_ts < SENSOR_LOG_INTERVAL_SECONDS:
        return
    if log_sensor_readings(readings):
        _last_sensor_log_ts = now


def sensor_loop() -> None:
    while True:
        try:
            readings = sensor_manager.read_all()
            _check_sensor_health()
            _check_stale_and_fail_safe()
            _maybe_log_sensor_readings(readings)
            lcd_manager.render_auto(api_status_payload(readings))
        except Exception as exc:
            alerts.add("error", f"Sensor loop error: {exc}")
        time.sleep(3)


def automation_loop() -> None:
    while True:
        try:
            automation_engine.tick(app_state.safe_mode or app_state.estop)
        except Exception as exc:
            alerts.add("error", f"Automation error: {exc}")
        time.sleep(3)


if not DISABLE_BACKGROUND_LOOPS:
    threading.Thread(target=sensor_loop, daemon=True).start()
    threading.Thread(target=automation_loop, daemon=True).start()


# Routes
@app.route("/")
def index() -> Any:
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard() -> Any:
    return render_template("dashboard.html")


@app.route("/control")
def control() -> Any:
    return render_template("control.html")


@app.route("/settings")
def settings() -> Any:
    return render_template("settings.html")


@app.route("/logs")
def logs() -> Any:
    return render_template("logs.html")


@app.route("/hardware")
def hardware() -> Any:
    return render_template("hardware.html")


@app.route("/lcd")
def lcd_page() -> Any:
    return render_template("lcd.html")


@app.route("/help")
@app.route("/sss")
def help_page() -> Any:
    return render_template("help.html")


def api_status_payload(readings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    latest = sensor_manager.latest()
    if readings is None:
        readings = dict(latest.get("readings", {}))
    dht_averages = sensor_manager.dht22_averages()
    if isinstance(readings.get("dht22"), dict):
        dht_reading = dict(readings["dht22"])
        dht_reading["averages"] = dht_averages
        readings["dht22"] = dht_reading
    else:
        readings["dht22"] = {"averages": dht_averages}
    sensor_ts = latest.get("ts") or None
    data_age_sec = None
    if sensor_ts:
        data_age_sec = max(0.0, time.time() - float(sensor_ts))
    data_stale = data_age_sec is not None and data_age_sec > SENSOR_STALE_SECONDS
    cooldowns: Dict[str, float] = {}
    pump_cooldown = int(app_state.limits.get("pump_cooldown_seconds", 60))
    remaining = 0.0
    if actuator_manager.last_pump_stop_ts:
        remaining = max(0.0, pump_cooldown - (time.time() - actuator_manager.last_pump_stop_ts))
    for name in actuator_manager.channels:
        if "PUMP" in name:
            cooldowns[name] = round(remaining, 1)
    return {
        "timestamp": _timestamp(),
        "sensor_ts": sensor_ts,
        "data_age_sec": data_age_sec,
        "data_stale": data_stale,
        "stale_threshold_sec": SENSOR_STALE_SECONDS,
        "sensor_readings": readings,
        "actuator_state": actuator_manager.get_state(),
        "cooldowns": cooldowns,
        "sensor_faults": app_state.get_sensor_faults(),
        "sensor_health": _sensor_health_snapshot(),
        "energy": _energy_summary(),
        "automation_state": automation_engine.status(),
        "alerts": alerts.get(),
        "alerts_config": app_state.get_alerts_config(),
        "safe_mode": app_state.safe_mode,
        "limits": app_state.limits,
        "automation": automation_engine.config,
        "lcd": lcd_manager.status(),
    }


@app.route("/api/status")
def api_status() -> Any:
    response = api_status_payload()
    return jsonify(response)


@app.route("/api/sensor_log")
def api_sensor_log() -> Any:
    from_raw = request.args.get("from")
    to_raw = request.args.get("to")
    from_ts = _parse_ts_param(from_raw)
    to_ts = _parse_ts_param(to_raw)
    if from_raw and from_ts is None:
        return jsonify({"error": "invalid from timestamp"}), 400
    if to_raw and to_ts is None:
        return jsonify({"error": "invalid to timestamp"}), 400

    limit_raw = request.args.get("limit", "200")
    try:
        limit = int(limit_raw)
    except ValueError:
        return jsonify({"error": "limit must be integer"}), 400
    limit = max(1, min(limit, 2000))

    order = (request.args.get("order") or "desc").strip().lower()
    if order not in ("asc", "desc"):
        return jsonify({"error": "order must be asc|desc"}), 400

    interval_raw = (request.args.get("interval") or "").strip()
    interval_minutes: Optional[int] = None
    if interval_raw:
        try:
            interval_minutes = int(interval_raw)
        except ValueError:
            return jsonify({"error": "interval must be integer minutes"}), 400
        if interval_minutes <= 0:
            interval_minutes = None
        elif interval_minutes not in (1, 5, 15, 30, 60):
            return jsonify({"error": "interval must be one of 1,5,15,30,60"}), 400

    if to_ts is None:
        to_ts = time.time()
    if from_ts is None:
        from_ts = to_ts - 24 * 3600
    if from_ts > to_ts:
        return jsonify({"error": "from must be <= to"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    interval_sec = interval_minutes * 60 if interval_minutes else None
    if interval_sec:
        cur.execute(
            f"""
            SELECT
                CAST(ts / ? AS INTEGER) * ? AS bucket,
                AVG(dht_temp),
                AVG(dht_hum),
                AVG(ds18_temp),
                AVG(lux),
                AVG(soil_ch0),
                AVG(soil_ch1),
                AVG(soil_ch2),
                AVG(soil_ch3)
            FROM sensor_log
            WHERE ts >= ? AND ts <= ?
            GROUP BY bucket
            ORDER BY bucket {order.upper()}
            LIMIT ?
            """,
            (interval_sec, interval_sec, from_ts, to_ts, limit),
        )
        rows = cur.fetchall()
    else:
        cur.execute(
            f"""
            SELECT ts, dht_temp, dht_hum, ds18_temp, lux, soil_ch0, soil_ch1, soil_ch2, soil_ch3
            FROM sensor_log
            WHERE ts >= ? AND ts <= ?
            ORDER BY ts {order.upper()}
            LIMIT ?
            """,
            (from_ts, to_ts, limit),
        )
        rows = cur.fetchall()
    conn.close()

    if request.args.get("format") == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ts",
            "dht_temp",
            "dht_hum",
            "ds18_temp",
            "lux",
            "soil_ch0",
            "soil_ch1",
            "soil_ch2",
            "soil_ch3",
        ])
        writer.writerows(rows)
        filename = "sensor_log.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    payload = [
        {
            "ts": row[0],
            "dht_temp": row[1],
            "dht_hum": row[2],
            "ds18_temp": row[3],
            "lux": row[4],
            "soil_ch0": row[5],
            "soil_ch1": row[6],
            "soil_ch2": row[7],
            "soil_ch3": row[8],
        }
        for row in rows
    ]
    return jsonify({
        "from_ts": from_ts,
        "to_ts": to_ts,
        "order": order,
        "interval_sec": interval_sec,
        "rows": payload,
    })


@app.route("/api/sensor_log/clear", methods=["POST"])
def api_sensor_log_clear() -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    payload = request.get_json(force=True, silent=True) or {}
    if payload.get("confirm") != "yes":
        return jsonify({"error": "confirm required", "hint": {"confirm": "yes"}}), 400
    before_raw = payload.get("before")
    before_ts = _parse_ts_param(before_raw) if before_raw else None
    if before_raw and before_ts is None:
        return jsonify({"error": "invalid before timestamp"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if before_ts is None:
        cur.execute("DELETE FROM sensor_log")
    else:
        cur.execute("DELETE FROM sensor_log WHERE ts < ?", (before_ts,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    log_event("sensor_log", "warning", "Sensor log cleared", {"before": before_ts, "deleted": deleted})
    return jsonify({"ok": True, "deleted": deleted})


@app.route("/api/history")
def api_history() -> Any:
    metric = (request.args.get("metric") or "").strip().lower()
    metric_map = {
        "dht_temp": "dht_temp",
        "dht_hum": "dht_hum",
        "ds18_temp": "ds18_temp",
        "lux": "lux",
        "soil_ch0": "soil_ch0",
        "soil_ch1": "soil_ch1",
        "soil_ch2": "soil_ch2",
        "soil_ch3": "soil_ch3",
    }
    if not metric:
        return jsonify({"error": "metric is required", "allowed": sorted(metric_map)}), 400
    if metric not in metric_map:
        return jsonify({"error": "invalid metric", "allowed": sorted(metric_map)}), 400

    from_raw = request.args.get("from")
    to_raw = request.args.get("to")
    from_ts = _parse_ts_param(from_raw)
    to_ts = _parse_ts_param(to_raw)
    if from_raw and from_ts is None:
        return jsonify({"error": "invalid from timestamp"}), 400
    if to_raw and to_ts is None:
        return jsonify({"error": "invalid to timestamp"}), 400

    if to_ts is None:
        to_ts = time.time()
    if from_ts is None:
        from_ts = to_ts - 24 * 3600
    if from_ts > to_ts:
        return jsonify({"error": "from must be <= to"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    column = metric_map[metric]
    cur.execute(
        f"SELECT ts, {column} FROM sensor_log WHERE ts >= ? AND ts <= ? ORDER BY ts ASC",
        (from_ts, to_ts),
    )
    rows = cur.fetchall()
    conn.close()

    if request.args.get("format") == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ts", metric])
        writer.writerows(rows)
        filename = f"history_{metric}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    points = [[row[0], row[1]] for row in rows]
    return jsonify({"metric": metric, "from_ts": from_ts, "to_ts": to_ts, "points": points})


@app.route("/api/events")
def api_events() -> Any:
    limit_raw = request.args.get("limit", "50")
    try:
        limit = int(limit_raw)
    except ValueError:
        return jsonify({"error": "limit must be integer"}), 400
    limit = max(1, min(limit, 200))
    category = (request.args.get("category") or "").strip().lower()
    since_raw = request.args.get("since")
    since_ts = _parse_ts_param(since_raw)
    if since_raw and since_ts is None:
        return jsonify({"error": "invalid since timestamp"}), 400

    query = "SELECT ts, category, level, message, meta FROM event_log"
    params: List[Any] = []
    clauses = []
    if category:
        clauses.append("LOWER(category) = ?")
        params.append(category)
    if since_ts is not None:
        clauses.append("ts >= ?")
        params.append(since_ts)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    events = []
    for ts, cat, level, message, meta in rows:
        payload = None
        if meta:
            try:
                payload = json.loads(meta)
            except json.JSONDecodeError:
                payload = None
        events.append({
            "ts": ts,
            "category": cat,
            "level": level,
            "message": message,
            "meta": payload,
        })
    return jsonify({"events": events})


@app.route("/api/actuator/<name>", methods=["POST"])
def api_actuator(name: str) -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    payload = request.get_json(force=True, silent=True) or {}
    desired_state = payload.get("state")
    seconds = payload.get("seconds")
    if desired_state not in ("on", "off"):
        return jsonify({"error": "state must be 'on' or 'off'"}), 400
    try:
        apply_actuator_command(name, desired_state == "on", seconds, "manual")
        return jsonify({"ok": True, "state": actuator_manager.get_state().get(name.upper())})
    except ActuationError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception as exc:  # pragma: no cover - unexpected errors
        return jsonify({"error": str(exc)}), 500


@app.route("/api/emergency_stop", methods=["POST"])
def api_emergency_stop() -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    actuator_manager.set_all_off("emergency_stop")
    log_actuation("ALL", False, "emergency_stop", None)
    return jsonify({"ok": True})


@app.route("/api/config", methods=["GET", "POST"])
def api_config() -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    if request.method == "GET":
        return jsonify({
            "channels": load_channel_config(),
            "limits": app_state.limits,
            "automation": automation_engine.config,
            "alerts_config": app_state.get_alerts_config(),
            "safe_mode": app_state.safe_mode,
            "sensors": sensors_config,
        })
    payload = request.get_json(force=True, silent=True) or {}
    channels = payload.get("channels")
    limits = payload.get("limits")
    automation = payload.get("automation")
    alerts_config = payload.get("alerts")
    sensors_payload = payload.get("sensors")
    safe_mode = payload.get("safe_mode")
    if channels:
        CONFIG_DIR.mkdir(exist_ok=True)
        with CHANNEL_CONFIG_PATH.open("w") as f:
            json.dump(channels, f, indent=2)
        actuator_manager.reload_channels(channels)
    if limits:
        app_state.update_limits(limits)
    if automation:
        automation_engine.config.update(automation)
    if alerts_config:
        app_state.update_alerts(alerts_config)
    if sensors_payload:
        CONFIG_DIR.mkdir(exist_ok=True)
        sensors_config.update(sensors_payload)
        with SENSORS_CONFIG_PATH.open("w") as f:
            json.dump(sensors_config, f, indent=2)
        sensor_manager.reload_config(sensors_config)
        lcd_manager.update_config(sensors_config)
    if safe_mode is not None:
        app_state.toggle_safe_mode(bool(safe_mode))
    actuator_manager.set_all_off("config_update")
    return jsonify({"ok": True})


@app.route("/api/pins", methods=["GET", "POST"])
def api_pins_deprecated() -> Any:
    return jsonify({"error": "pins page removed, use /hardware"}), 410


@app.route("/api/settings", methods=["POST"])
def api_settings() -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    payload = request.get_json(force=True, silent=True) or {}
    safe_mode = payload.get("safe_mode")
    limits = payload.get("limits", {})
    automation = payload.get("automation", {})
    alerts_config = payload.get("alerts", {})
    if safe_mode is not None:
        app_state.toggle_safe_mode(bool(safe_mode))
    app_state.update_limits(limits)
    automation_engine.config.update(automation)
    if alerts_config:
        app_state.update_alerts(alerts_config)
    return jsonify({"ok": True})


@app.route("/api/lcd", methods=["GET", "POST"])
def api_lcd() -> Any:
    if request.method == "GET":
        return jsonify({
            "lcd": lcd_manager.status(),
            "config": {
                "lcd_enabled": sensors_config.get("lcd_enabled", True),
                "lcd_addr": sensors_config.get("lcd_addr", "0x27"),
                "lcd_port": sensors_config.get("lcd_port", 1),
                "lcd_cols": sensors_config.get("lcd_cols", 20),
                "lcd_rows": sensors_config.get("lcd_rows", 4),
                "lcd_expander": sensors_config.get("lcd_expander", "PCF8574"),
                "lcd_charmap": sensors_config.get("lcd_charmap", "A00"),
                "lcd_mode": sensors_config.get("lcd_mode", "auto"),
                "lcd_lines": sensors_config.get("lcd_lines", ["", "", "", ""]),
            },
        })
    admin_error = require_admin()
    if admin_error:
        return admin_error
    payload = request.get_json(force=True, silent=True) or {}
    config_update = payload.get("config") or {}
    lines = payload.get("lines")
    if config_update:
        sensors_config.update(config_update)
        with SENSORS_CONFIG_PATH.open("w") as f:
            json.dump(sensors_config, f, indent=2)
        sensor_manager.reload_config(sensors_config)
        lcd_manager.update_config(sensors_config)
    if isinstance(lines, list):
        lcd_manager.set_manual_lines([str(x) if x is not None else "" for x in lines])
        sensors_config["lcd_mode"] = "manual"
        sensors_config["lcd_lines"] = [str(x) if x is not None else "" for x in lines]
        with SENSORS_CONFIG_PATH.open("w") as f:
            json.dump(sensors_config, f, indent=2)
    return jsonify({"ok": True, "lcd": lcd_manager.status()})


# Test panel routes
@test_panel.route("/")
def test_panel_index() -> Any:
    return render_template("index.html")


@test_panel.route("/api/status")
def test_panel_status() -> Any:
    return jsonify(_build_test_panel_status())


@test_panel.route("/api/safety", methods=["POST"])
def test_panel_safety() -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    payload = request.get_json(force=True, silent=True) or {}
    if "test_mode" in payload:
        app_state.set_test_mode(bool(payload["test_mode"]))
    if "estop" in payload:
        app_state.set_estop(bool(payload["estop"]))
    if "pump_unlocked" in payload:
        app_state.set_pump_unlocked(bool(payload["pump_unlocked"]))
    return jsonify({"ok": True, "safety": app_state.test_panel_state()})


@test_panel.route("/api/relay/<relay_key>", methods=["POST"])
def test_panel_relay(relay_key: str) -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    name = relay_key.upper()
    if name not in actuator_manager.channels:
        return jsonify({"ok": False, "error": "relay_key not found"}), 404

    payload = request.get_json(force=True, silent=True) or {}
    action = payload.get("action", "")

    if action == "off":
        actuator_manager.set_state(name, False, "test_panel")
        log_actuation(name, False, "test_panel", None)
        return jsonify({"ok": True, "state": actuator_manager.get_state().get(name)})

    if action not in ("on", "pulse"):
        return jsonify({"ok": False, "error": "unknown action"}), 400

    meta = _relay_meta(name)
    ok, msg = _test_panel_can_switch(meta["type"], meta["locked"])
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400

    seconds = None
    if action == "pulse":
        try:
            seconds = int(payload.get("sec", 2))
        except Exception:
            return jsonify({"ok": False, "error": "sec must be a number"}), 400
        seconds = max(1, min(seconds, 15))
    elif meta["type"] == "pump":
        seconds = int(app_state.limits.get("pump_max_seconds", 15))
    elif meta["type"] == "heater":
        seconds = int(app_state.limits.get("heater_max_seconds", 300))

    if seconds is not None and meta["type"] == "pump":
        seconds = min(seconds, int(app_state.limits.get("pump_max_seconds", 15)))
    if seconds is not None and meta["type"] == "heater":
        seconds = min(seconds, int(app_state.limits.get("heater_max_seconds", 300)))

    try:
        apply_actuator_command(name, True, seconds, "test_panel")
        return jsonify({"ok": True, "state": actuator_manager.get_state().get(name)})
    except ActuationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@test_panel.route("/api/config", methods=["GET", "POST"])
def test_panel_config() -> Any:
    if request.method == "GET":
        return jsonify(_test_panel_config())

    admin_error = require_admin()
    if admin_error:
        return admin_error
    payload = request.get_json(force=True, silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid json"}), 400
    err = _apply_test_panel_config(payload)
    if err:
        return jsonify({"ok": False, "error": err}), 400
    return jsonify({"ok": True})


@test_panel.route("/api/i2c-scan", methods=["POST"])
def test_panel_i2c_scan() -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    payload = request.get_json(force=True, silent=True) or {}
    try:
        bus_num = int(payload.get("bus_num", 1))
    except Exception:
        return jsonify({"ok": False, "error": "bus_num must be a number"}), 400
    result = _test_panel_i2c_scan(bus_num)
    return jsonify({"ok": True, "result": result})


@test_panel.route("/api/all-off", methods=["POST"])
def test_panel_all_off() -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    actuator_manager.set_all_off("test_panel_all_off")
    log_actuation("ALL", False, "test_panel_all_off", None)
    return jsonify({"ok": True})


app.register_blueprint(test_panel)


# Templates for testing convenience
@app.route("/health")
def health() -> Any:
    return jsonify({"ok": True, "simulation": SIMULATION_MODE})


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=SIMULATION_MODE)
