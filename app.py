import csv
import ipaddress
import io
import json
import os
import random
import re
import sqlite3
import subprocess
import threading
import time
import uuid
from collections import deque
from datetime import date, datetime, timedelta, time as dt_time, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for
from reporting import (
    build_daily_report,
    build_weekly_report,
    explainers_catalog,
    load_reporting_config,
)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
TEST_PANEL_DIR = BASE_DIR / "sera_panel"
DATA_DIR.mkdir(exist_ok=True)
CHANNEL_CONFIG_PATH = CONFIG_DIR / "channels.json"
SENSORS_CONFIG_PATH = CONFIG_DIR / "sensors.json"
NOTIFICATIONS_CONFIG_PATH = CONFIG_DIR / "notifications.json"
RETENTION_CONFIG_PATH = CONFIG_DIR / "retention.json"
PANEL_CONFIG_PATH = CONFIG_DIR / "panel.json"
UPDATES_PATH = CONFIG_DIR / "updates.json"
CATALOG_CONFIG_PATH = CONFIG_DIR / "catalog.json"
DB_PATH = DATA_DIR / "sera.db"
SENSOR_CSV_LOG_DIR = DATA_DIR / "sensor_logs"

SENSOR_STALE_SECONDS = 15
SENSOR_ALERT_COOLDOWN_SECONDS = 120
SENSOR_LOG_INTERVAL_SECONDS = 10
PUMP_DAILY_CACHE_SECONDS = 30
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
DEFAULT_NOTIFICATIONS = {
    "enabled": True,
    "level": "warning",
    "cooldown_seconds": 300,
    "telegram_enabled": True,
    "email_enabled": False,
    "allow_simulation": False,
}
DEFAULT_RETENTION = {
    "sensor_log_days": 0,
    "event_log_days": 0,
    "actuator_log_days": 0,
    "archive_enabled": False,
    "archive_dir": "data/archives",
    "cleanup_interval_hours": 24,
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


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _parse_node_tokens(raw: str) -> Dict[str, str]:
    tokens: Dict[str, str] = {}
    for item in (raw or "").split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        node_id, token = item.split(":", 1)
        node_id = node_id.strip()
        token = token.strip()
        if node_id and token:
            tokens[node_id] = token
    return tokens


SIMULATION_MODE = os.getenv("SIMULATION_MODE", "0") == "1"
DISABLE_BACKGROUND_LOOPS = os.getenv("DISABLE_BACKGROUND_LOOPS", "0") == "1"
USE_NEW_UI = os.getenv("USE_NEW_UI", "0") == "1"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
LIGHT_CHANNEL_NAME = os.getenv("LIGHT_CHANNEL_NAME")
FAN_CHANNEL_NAME = os.getenv("FAN_CHANNEL_NAME")
PUMP_CHANNEL_NAME = os.getenv("PUMP_CHANNEL_NAME")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NODE_TOKENS_RAW = os.getenv("NODE_TOKENS", "")
NODE_TOKENS = _parse_node_tokens(NODE_TOKENS_RAW)
NODE_RATE_LIMIT_SECONDS = _env_float("NODE_RATE_LIMIT_SECONDS", 0.2)
NODE_COMMAND_RATE_LIMIT_SECONDS = _env_float("NODE_COMMAND_RATE_LIMIT_SECONDS", NODE_RATE_LIMIT_SECONDS)
NODE_COMMAND_DEFAULT_TTL_SECONDS = _env_int("NODE_COMMAND_TTL_SECONDS", 30)
NODE_COMMAND_MAX_QUEUE = _env_int("NODE_COMMAND_MAX_QUEUE", 50)
NODE_STALE_SECONDS = _env_int("NODE_STALE_SECONDS", 15)
TREND_MAX_POINTS_DEFAULT = 120
TREND_MAX_POINTS_LIMIT = 2000


def _downsample_points(points: List[List[float]], max_points: int) -> List[List[float]]:
    if max_points <= 0 or len(points) <= max_points:
        return points
    if max_points == 1:
        return [points[-1]]
    last_index = len(points) - 1
    step = last_index / float(max_points - 1)
    indices: List[int] = []
    for i in range(max_points):
        idx = int(round(i * step))
        if not indices or idx != indices[-1]:
            indices.append(idx)
    return [points[i] for i in indices]


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
        self.last_stop_ts: Dict[str, float] = {}
        self.load_config(channel_config)

    def _is_pump(self, name: str) -> bool:
        role = str(self.channels.get(name, {}).get("role") or "").lower()
        if role:
            return role == "pump"
        return "PUMP" in name

    def load_config(self, channel_config: List[Dict[str, Any]]) -> None:
        with self.lock:
            # cancel timers and turn everything off before reloading
            for timer in self.timers.values():
                timer.cancel()
            self.timers.clear()
            for chan in channel_config:
                name = chan["name"].upper()
                self.channels[name] = chan
                self.last_stop_ts.setdefault(name, 0.0)
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
        if not on and reason not in ("startup", "config_reload"):
            self.last_stop_ts[name] = time.time()
            if self._is_pump(name):
                self.last_pump_stop_ts = time.time()

    def set_state(self, name: str, on: bool, reason: str, duration: Optional[int] = None) -> None:
        with self.lock:
            if name not in self.channels:
                raise ActuationError(f"Unknown actuator: {name}")
            self._apply(name, on, reason, duration)
            if not on and self._is_pump(name):
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
                    "enabled": bool(self.channels[name].get("enabled", True)),
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
            mode = str(self.config.get("lcd_mode", "auto"))
            if mode == "auto":
                lines = self._build_auto_lines(data)
            elif mode == "template":
                lines = self._build_template_lines(data)
            else:
                return
            self._write_lines(lines)

    def set_template_lines(self, lines: List[str], data: Dict[str, Any]) -> None:
        with self.lock:
            self.config["lcd_mode"] = "template"
            self.config["lcd_lines"] = list(lines)
            templated = self._build_template_lines(data, lines)
            self._write_lines(templated)

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

        def fmt_float(value: Any, width: int, prec: int) -> Optional[str]:
            try:
                return f"{float(value):{width}.{prec}f}"
            except (TypeError, ValueError):
                return None

        def fmt_int(value: Any, width: int) -> Optional[str]:
            try:
                return f"{int(value):{width}d}"
            except (TypeError, ValueError):
                return None

        temp = fmt_float(dht.get("temperature"), 4, 1) or "--.-"
        hum = fmt_float(dht.get("humidity"), 3, 0) or "--"
        line0 = f"Sic:{temp}C Nem:{hum}%"

        lux_val = (fmt_int(lux.get("lux"), 4) or "----").strip()
        soil_raw = soil.get("ch0")
        soil_pct = self._soil_percent("ch0", soil_raw)
        soil_pct_str = (f"{soil_pct:3d}".strip()) if soil_pct is not None else "--"
        line1 = f"Isik:{lux_val}lx Top:{soil_pct_str}%"

        ds_temp = fmt_float((readings.get("ds18b20") or {}).get("temperature"), 4, 1) or "--.-"
        soil_raw_str = (fmt_int(soil_raw, 4) or "----").strip()
        line2 = f"DS:{ds_temp}C Ham:{soil_raw_str}"

        safe_mode = bool(data.get("safe_mode"))
        line3 = "SAFE MODE" if safe_mode else "Sistem: AKTIF"
        return [line0, line1, line2, line3]

    def _build_template_lines(self, data: Dict[str, Any], override_lines: Optional[List[str]] = None) -> List[str]:
        template_lines: List[str] = []
        raw_lines = override_lines if override_lines is not None else self.config.get("lcd_lines", ["", "", "", ""])
        context = self._template_context(data)
        for line in raw_lines:
            template_lines.append(self._apply_template(str(line or ""), context))
        while len(template_lines) < int(self.config.get("lcd_rows", 4)):
            template_lines.append("")
        return template_lines

    def _template_context(self, data: Dict[str, Any]) -> Dict[str, str]:
        readings = data.get("sensor_readings", {})
        dht = readings.get("dht22") or {}
        ds = readings.get("ds18b20") or {}
        lux = readings.get("bh1750") or {}
        soil = readings.get("soil") or {}
        actuators = data.get("actuator_state") or {}
        safe_mode = bool(data.get("safe_mode"))

        def fmt_float(value: Any, precision: int, fallback: str) -> str:
            try:
                return f"{float(value):.{precision}f}"
            except (TypeError, ValueError):
                return fallback

        def fmt_int(value: Any, fallback: str) -> str:
            try:
                return str(int(value))
            except (TypeError, ValueError):
                return fallback

        soil_raw = soil.get("ch0")
        soil_pct_val = self._soil_percent("ch0", soil_raw)

        def relay_label(key: str) -> str:
            entry = actuators.get(key) or {}
            on = bool(entry.get("state"))
            label = (entry.get("description") or key).split(" ")[0].upper()
            return f"{label}:{'ON' if on else 'OFF'}"

        pump_key = next((k for k in actuators if "PUMP" in k), None)
        heater_key = next((k for k in actuators if "HEATER" in k), None)
        return {
            "temp": fmt_float(dht.get("temperature"), 1, "--.-"),
            "hum": fmt_int(dht.get("humidity"), "--"),
            "lux": fmt_int(lux.get("lux"), "----"),
            "soil_pct": fmt_int(soil_pct_val, "--"),
            "soil_raw": fmt_int(soil_raw, "----"),
            "ds_temp": fmt_float(ds.get("temperature"), 1, "--.-"),
            "safe": "SAFE" if safe_mode else "AKTIF",
            "time": datetime.now().strftime("%H:%M"),
            "pump": relay_label(pump_key) if pump_key else "",
            "heater": relay_label(heater_key) if heater_key else "",
        }

    def _apply_template(self, template: str, context: Dict[str, str]) -> str:
        def repl(match: Any) -> str:
            key = match.group(1).strip().lower()
            return str(context.get(key, ""))

        return re.sub(r"{\s*([a-zA-Z0-9_]+)\s*}", repl, template)

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
        self.manual_override_cancel_ts: float = 0.0
        self.last_lux_max_alert_ts: float = 0.0
        self.last_auto_off_ts: float = 0.0
        self.last_auto_off_reason: str = ""
        self.last_min_off_alert_ts: float = 0.0
        self.last_target_met_alert_ts: float = 0.0
        self.last_target_met_active: bool = False
        self.fan_manual_override_until_ts: float = 0.0
        self.fan_manual_override_cancel_ts: float = 0.0
        self.fan_last_auto_off_ts: float = 0.0
        self.fan_last_auto_off_reason: str = ""
        self.fan_periodic_last_start_ts: float = 0.0
        self.heater_manual_override_until_ts: float = 0.0
        self.heater_manual_override_cancel_ts: float = 0.0
        self.heater_last_auto_off_ts: float = 0.0
        self.heater_last_auto_off_reason: str = ""
        self.pump_manual_override_until_ts: float = 0.0
        self.pump_manual_override_cancel_ts: float = 0.0
        self.pump_last_auto_ts: float = 0.0
        self.pump_daily_seconds: float = 0.0
        self.pump_daily_cache_ts: float = 0.0
        self.pump_block_until_ts: float = 0.0
        self.pump_last_auto_off_ts: float = 0.0
        self.pump_last_auto_off_reason: str = ""
        self.auto_block_ts: Dict[str, float] = {}

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
        self.pump_daily_cache_ts = 0.0
        self.pump_block_until_ts = 0.0
        self.pump_last_auto_off_ts = 0.0
        self.pump_last_auto_off_reason = ""
        self.auto_block_ts.clear()
        _record_threshold_alert(
            "pump_daily_limit",
            False,
            "Pompa otomasyonu durdu: günlük limit doldu.",
            "Pompa günlük limit sıfırlandı.",
        )

    def _manual_override_until(
        self,
        reason: str,
        last_change: Optional[float],
        minutes: int,
        cancel_ts: float,
    ) -> float:
        if minutes <= 0 or reason != "manual":
            return 0.0
        if not last_change:
            return 0.0
        if cancel_ts and last_change <= cancel_ts:
            return 0.0
        override_until = last_change + minutes * 60
        if time.time() < override_until:
            return override_until
        return 0.0

    def clear_manual_override(self, scope: str) -> List[str]:
        scope = (scope or "").strip().lower()
        now_ts = time.time()
        cleared: List[str] = []
        if scope in ("all", "lux", "light"):
            self.manual_override_cancel_ts = now_ts
            self.manual_override_until_ts = 0.0
            cleared.append("lux")
        if scope in ("all", "fan"):
            self.fan_manual_override_cancel_ts = now_ts
            self.fan_manual_override_until_ts = 0.0
            cleared.append("fan")
        if scope in ("all", "heater"):
            self.heater_manual_override_cancel_ts = now_ts
            self.heater_manual_override_until_ts = 0.0
            cleared.append("heater")
        if scope in ("all", "pump"):
            self.pump_manual_override_cancel_ts = now_ts
            self.pump_manual_override_until_ts = 0.0
            cleared.append("pump")
        if cleared:
            log_event("automation", "info", "Manual override cleared", {"scopes": cleared})
        return cleared

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

    def _pump_daily_used(self, pump_channel: Optional[str]) -> float:
        if not pump_channel:
            self.pump_daily_seconds = 0.0
            self.pump_daily_cache_ts = time.time()
            return 0.0
        now_ts = time.time()
        if now_ts - self.pump_daily_cache_ts < PUMP_DAILY_CACHE_SECONDS:
            return self.pump_daily_seconds
        used = _actuator_daily_seconds(pump_channel)
        self.pump_daily_seconds = used
        self.pump_daily_cache_ts = now_ts
        return used

    def _log_auto_block(self, channel: str, reason: str, error: Exception) -> None:
        now_ts = time.time()
        last_ts = self.auto_block_ts.get(channel, 0.0)
        if now_ts - last_ts < SENSOR_ALERT_COOLDOWN_SECONDS:
            return
        self.auto_block_ts[channel] = now_ts
        log_event(
            "automation",
            "warning",
            f"{channel} automation blocked ({reason})",
            {"error": str(error)},
        )

    def _try_auto_on(self, channel: str, seconds: Optional[int], reason: str) -> bool:
        try:
            apply_actuator_command(channel, True, seconds, reason)
            return True
        except ActuationError as exc:
            self._log_auto_block(channel, reason, exc)
            return False

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
        pump_soil_channel = str(self.config.get("pump_soil_channel", "ch0") or "ch0").lower()
        pump_threshold = float(self.config.get("pump_dry_threshold", 0) or 0)
        pump_dry_when_above = bool(self.config.get("pump_dry_when_above"))
        pump_actuator = self._find_pump_channel() if (pump_enabled or pump_max_daily > 0) else None
        pump_daily_used = self._pump_daily_used(pump_actuator) if pump_actuator else 0.0
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
                "soil_channel": pump_soil_channel,
                "dry_threshold": pump_threshold,
                "dry_when_above": pump_dry_when_above,
                "pulse_seconds": pump_pulse_seconds,
                "max_daily_seconds": pump_max_daily,
                "daily_used_seconds": round(pump_daily_used, 1),
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
        override_until = self._manual_override_until(
            reason,
            last_change,
            manual_override_minutes,
            self.manual_override_cancel_ts,
        )
        if override_until:
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
                self._try_auto_on(light_channel, None, "automation")
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
        override_until = self._manual_override_until(
            reason,
            last_change,
            manual_override_minutes,
            self.fan_manual_override_cancel_ts,
        )
        if override_until:
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
                self._try_auto_on(fan_channel, None, "fan_auto_on")
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
        override_until = self._manual_override_until(
            reason,
            last_change,
            manual_override_minutes,
            self.fan_manual_override_cancel_ts,
        )
        if override_until:
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
                                        self._try_auto_on(fan_channel, None, "fan_auto_on")
                                        return
                    self._fan_off(fan_channel, "fan_periodic_off")
            return

        now_ts = time.time()
        if self.fan_periodic_last_start_ts and now_ts - self.fan_periodic_last_start_ts < every_minutes * 60:
            return
        if self._try_auto_on(fan_channel, duration_minutes * 60, "fan_periodic_on"):
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
        override_until = self._manual_override_until(
            reason,
            last_change,
            manual_override_minutes,
            self.heater_manual_override_cancel_ts,
        )
        if override_until:
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
                self._try_auto_on(heater_channel, None, "heater_auto_on")
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
        daily_used = self._pump_daily_used(pump_channel)
        state = self.actuator_manager.get_state().get(pump_channel, {})
        reason = str(state.get("reason") or "")
        last_change = state.get("last_change_ts")
        manual_override_minutes = int(self.config.get("pump_manual_override_minutes", 0) or 0)
        override_until = self._manual_override_until(
            reason,
            last_change,
            manual_override_minutes,
            self.pump_manual_override_cancel_ts,
        )
        if override_until:
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
        if max_daily > 0 and daily_used >= max_daily:
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
            remaining = max_daily - daily_used
            if remaining <= 0:
                return
            pulse_seconds = min(pulse_seconds, remaining)
        try:
            applied_seconds = apply_actuator_command(pump_channel, True, pulse_seconds, "pump_auto_on")
        except ActuationError as exc:
            self._log_auto_block(pump_channel, "pump_auto_on", exc)
            return
        if applied_seconds:
            self.pump_daily_seconds = daily_used + applied_seconds
            self.pump_daily_cache_ts = time.time()
        self.pump_last_auto_ts = time.time()


class NotificationManager:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.lock = threading.Lock()
        self.config: Dict[str, Any] = dict(DEFAULT_NOTIFICATIONS)
        self.config.update(config or {})
        self._last_sent_ts: float = 0.0

    def update_config(self, config: Dict[str, Any]) -> None:
        with self.lock:
            merged = dict(DEFAULT_NOTIFICATIONS)
            merged.update(config or {})
            self.config = merged

    def public_status(self) -> Dict[str, Any]:
        with self.lock:
            cfg = dict(self.config)
        return {
            "config": cfg,
            "runtime": {
                "simulation": SIMULATION_MODE,
                "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
            },
        }

    def notify_alert(self, severity: str, message: str) -> None:
        if not message:
            return
        with self.lock:
            cfg = dict(self.config)
            last_ts = float(self._last_sent_ts or 0.0)
        if not cfg.get("enabled", True):
            return
        if SIMULATION_MODE and not cfg.get("allow_simulation", False):
            return
        if not cfg.get("telegram_enabled", False):
            return
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return
        cooldown = int(cfg.get("cooldown_seconds", 0) or 0)
        if cooldown > 0 and time.time() - last_ts < cooldown:
            return
        if not self._level_allows(str(cfg.get("level") or "warning"), str(severity or "info")):
            return

        text = f"AKILLI SERA • {severity.upper()}\n{message}"
        ok, _error = self._send_telegram(text)
        if not ok:
            return
        with self.lock:
            self._last_sent_ts = time.time()

    def send_test(self, message: str) -> Dict[str, Any]:
        msg = (message or "").strip() or "Test bildirimi: AKILLI SERA paneli çalışıyor."
        with self.lock:
            cfg = dict(self.config)
        if not cfg.get("enabled", True):
            return {"sent": False, "reason": "disabled"}
        if SIMULATION_MODE and not cfg.get("allow_simulation", False):
            return {"sent": False, "reason": "simulation_blocked"}
        if not cfg.get("telegram_enabled", False):
            return {"sent": False, "reason": "telegram_disabled"}
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return {"sent": False, "reason": "telegram_not_configured"}
        text = f"AKILLI SERA • TEST\n{msg}"
        ok, error = self._send_telegram(text)
        if not ok:
            return {"sent": False, "reason": "send_failed", "error": error}
        with self.lock:
            self._last_sent_ts = time.time()
        return {"sent": True}

    @staticmethod
    def _level_allows(config_level: str, severity: str) -> bool:
        order = {"debug": 10, "info": 20, "warning": 30, "error": 40}
        cfg = order.get(config_level.strip().lower(), 30)
        sev = order.get(severity.strip().lower(), 20)
        return sev >= cfg

    @staticmethod
    def _send_telegram(text: str) -> Tuple[bool, Optional[str]]:
        import urllib.parse
        import urllib.request

        token = TELEGRAM_BOT_TOKEN
        chat_id = TELEGRAM_CHAT_ID
        if not token or not chat_id:
            return False, "not_configured"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 (expected outbound call)
                resp.read()
        except Exception as exc:
            return False, type(exc).__name__
        return True, None


class AlertManager:
    def __init__(self, notifier: Optional["NotificationManager"] = None) -> None:
        self.alerts: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        self.notifier = notifier

    def add(self, severity: str, message: str) -> None:
        with self.lock:
            ts = datetime.now(timezone.utc).isoformat()
            self.alerts.append({"severity": severity, "message": message, "ts": ts})
            self.alerts = self.alerts[-50:]
        log_event("alert", severity, message, None)
        if self.notifier:
            try:
                self.notifier.notify_alert(severity, message)
            except Exception:
                pass

    def get(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.alerts)


class RetentionManager:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.lock = threading.Lock()
        self.config: Dict[str, Any] = dict(DEFAULT_RETENTION)
        self.config.update(config or {})
        self.last_cleanup_ts: float = 0.0

    def update_config(self, config: Dict[str, Any]) -> None:
        with self.lock:
            merged = dict(DEFAULT_RETENTION)
            merged.update(config or {})
            self.config = merged

    def public_status(self) -> Dict[str, Any]:
        with self.lock:
            return {"config": dict(self.config), "last_cleanup_ts": self.last_cleanup_ts or None}

    def cleanup_if_due(self) -> None:
        with self.lock:
            cfg = dict(self.config)
            last_ts = float(self.last_cleanup_ts or 0.0)
        if (
            int(cfg.get("sensor_log_days", 0) or 0) <= 0
            and int(cfg.get("event_log_days", 0) or 0) <= 0
            and int(cfg.get("actuator_log_days", 0) or 0) <= 0
            and not bool(cfg.get("archive_enabled"))
        ):
            return
        interval_h = int(cfg.get("cleanup_interval_hours", 24) or 24)
        interval_s = max(1, interval_h) * 3600
        if time.time() - last_ts < interval_s:
            return
        self.cleanup_now()

    def cleanup_now(self) -> None:
        with self.lock:
            cfg = dict(self.config)
        now = time.time()
        summary: Dict[str, Any] = {"sensor_log": 0, "event_log": 0, "actuator_log": 0, "csv_files": 0}

        sensor_days = int(cfg.get("sensor_log_days", 0) or 0)
        event_days = int(cfg.get("event_log_days", 0) or 0)
        actuator_days = int(cfg.get("actuator_log_days", 0) or 0)

        archive_enabled = bool(cfg.get("archive_enabled"))
        archive_dir_raw = str(cfg.get("archive_dir") or "data/archives")
        archive_dir = (BASE_DIR / archive_dir_raw).resolve()
        if not str(archive_dir).startswith(str(BASE_DIR.resolve())):
            archive_dir = (DATA_DIR / "archives").resolve()
        if archive_enabled:
            try:
                archive_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                archive_enabled = False

        if archive_enabled:
            try:
                import shutil

                stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                shutil.copy2(DB_PATH, archive_dir / f"sera-{stamp}.db")
            except Exception:
                pass

        if sensor_days > 0 or event_days > 0 or actuator_days > 0:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            if sensor_days > 0:
                cutoff = now - (sensor_days * 86400)
                cur.execute("DELETE FROM sensor_log WHERE ts < ?", (cutoff,))
                summary["sensor_log"] = int(cur.rowcount or 0)
            if event_days > 0:
                cutoff = now - (event_days * 86400)
                cur.execute("DELETE FROM event_log WHERE ts < ?", (cutoff,))
                summary["event_log"] = int(cur.rowcount or 0)
            if actuator_days > 0:
                cur.execute("DELETE FROM actuator_log WHERE ts < datetime('now', ?)", (f"-{actuator_days} days",))
                summary["actuator_log"] = int(cur.rowcount or 0)
            conn.commit()
            conn.close()

        if sensor_days > 0:
            cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=sensor_days)
            for path in SENSOR_CSV_LOG_DIR.glob("sensor_log_*.csv"):
                m = re.search(r"sensor_log_(\\d{4}-\\d{2}-\\d{2})\\.csv$", path.name)
                if not m:
                    continue
                try:
                    file_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                except ValueError:
                    continue
                if file_date >= cutoff_date:
                    continue
                try:
                    if archive_enabled:
                        import shutil

                        shutil.move(str(path), str(archive_dir / path.name))
                    else:
                        path.unlink(missing_ok=True)
                    summary["csv_files"] += 1
                except Exception:
                    continue

        with self.lock:
            self.last_cleanup_ts = time.time()
        log_event("maintenance", "info", "Retention cleanup completed", summary)


class AppState:
    def __init__(self, actuator_manager: ActuatorManager, sensor_manager: SensorManager, automation: AutomationEngine, alerts: AlertManager):
        self.actuator_manager = actuator_manager
        self.sensor_manager = sensor_manager
        self.automation = automation
        self.alerts = alerts
        self.safe_mode = True
        self.estop = False
        self.sensor_faults = {"pump": False, "heater": False}
        self.limits = dict(DEFAULT_LIMITS)
        self.alerts_config = dict(DEFAULT_ALERTS)
        self.lock = threading.Lock()

    def toggle_safe_mode(self, enabled: bool) -> None:
        with self.lock:
            self.safe_mode = enabled
            if enabled:
                self.actuator_manager.set_all_off("safe_mode")
                _clear_all_node_command_queues("safe_mode")
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

    def set_estop(self, enabled: bool) -> None:
        with self.lock:
            self.estop = bool(enabled)
        if enabled:
            self.actuator_manager.set_all_off("estop")
        log_event("system", "warning" if enabled else "info", f"E-STOP {'AÇIK' if enabled else 'KAPALI'}", None)

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

# Flask app factory
app = Flask(__name__)
backend = GPIOBackend()
channel_config = []


def _deep_merge_dict(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in (updates or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json_or_none(path: Path) -> Optional[Any]:
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


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
            entry.setdefault("enabled", True)
            normalized.append(entry)
        return normalized

    default_channels = [
        {
            "name": "R1_HEATER_FAN",
            "gpio_pin": 18,
            "active_low": True,
            "description": "Isıtıcı + Fan",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": 12,
            "role": "heater",
            "enabled": True,
        },
        {
            "name": "R2_FAN_MAIN",
            "gpio_pin": 23,
            "active_low": True,
            "description": "12cm Havalandırma Fanı",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": 12,
            "role": "fan",
            "enabled": True,
        },
        {
            "name": "R3_PUMP",
            "gpio_pin": 24,
            "active_low": True,
            "description": "Pompa",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": 12,
            "role": "pump",
            "enabled": True,
        },
        {
            "name": "R4_FAN_L3",
            "gpio_pin": 25,
            "active_low": True,
            "description": "3.kat Fanı",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": 12,
            "role": "fan",
            "enabled": True,
        },
        {
            "name": "R5_LIGHT_MID",
            "gpio_pin": 20,
            "active_low": True,
            "description": "3.kat Orta Işık",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": 12,
            "role": "light",
            "enabled": True,
        },
        {
            "name": "R6_LIGHT_BACK",
            "gpio_pin": 21,
            "active_low": True,
            "description": "3.kat Arka Işık",
            "power_w": 0,
            "quantity": 1,
            "voltage_v": 12,
            "role": "light",
            "enabled": True,
        },
    ]
    if CHANNEL_CONFIG_PATH.exists():
        try:
            data = _load_json_or_none(CHANNEL_CONFIG_PATH)
            current = normalize(data if isinstance(data, list) else [])
        except Exception:
            current = normalize([])
        current_map = {str(item.get("name", "")).upper(): item for item in current}
        merged = list(current)
        changed = False
        for default in normalize(default_channels):
            name = str(default.get("name", "")).upper()
            if name and name not in current_map:
                merged.append(default)
                changed = True
        if changed:
            CONFIG_DIR.mkdir(exist_ok=True)
            _write_json_atomic(CHANNEL_CONFIG_PATH, merged)
        return merged
    CONFIG_DIR.mkdir(exist_ok=True)
    _write_json_atomic(CHANNEL_CONFIG_PATH, default_channels)
    return normalize(default_channels)


def load_sensors_config() -> Dict[str, Any]:
    defaults = {
        "dht22_gpio": int(os.getenv("DHT22_GPIO", "17")),
        "bh1750_addr": os.getenv("BH1750_ADDR", "0x23"),
        "ads1115_addr": "0x48",
        "ds18b20_enabled": True,
        "lcd_enabled": True,
        "lcd_addr": "0x3F",
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
            data = _load_json_or_none(SENSORS_CONFIG_PATH)
            merged = dict(defaults)
            merged.update(data or {})
            return merged
        except Exception:
            return defaults
    CONFIG_DIR.mkdir(exist_ok=True)
    _write_json_atomic(SENSORS_CONFIG_PATH, defaults)
    return defaults


def load_notifications_config() -> Dict[str, Any]:
    defaults = dict(DEFAULT_NOTIFICATIONS)
    if NOTIFICATIONS_CONFIG_PATH.exists():
        data = _load_json_or_none(NOTIFICATIONS_CONFIG_PATH)
        if isinstance(data, dict):
            merged = dict(defaults)
            merged.update(data)
            return merged
        return defaults
    _write_json_atomic(NOTIFICATIONS_CONFIG_PATH, defaults)
    return defaults


def load_retention_config() -> Dict[str, Any]:
    defaults = dict(DEFAULT_RETENTION)
    if RETENTION_CONFIG_PATH.exists():
        data = _load_json_or_none(RETENTION_CONFIG_PATH)
        if isinstance(data, dict):
            merged = dict(defaults)
            merged.update(data)
            return merged
        return defaults
    _write_json_atomic(RETENTION_CONFIG_PATH, defaults)
    return defaults


def load_panel_config() -> Dict[str, Any]:
    defaults: Dict[str, Any] = {
        "limits": dict(DEFAULT_LIMITS),
        "automation": dict(DEFAULT_AUTOMATION),
        "alerts": dict(DEFAULT_ALERTS),
    }
    if PANEL_CONFIG_PATH.exists():
        data = _load_json_or_none(PANEL_CONFIG_PATH)
        if isinstance(data, dict):
            merged = dict(defaults)
            merged["limits"] = _deep_merge_dict(defaults["limits"], data.get("limits") or {})
            merged["automation"] = _deep_merge_dict(defaults["automation"], data.get("automation") or {})
            merged["alerts"] = _deep_merge_dict(defaults["alerts"], data.get("alerts") or {})
            return merged
        return defaults
    _write_json_atomic(PANEL_CONFIG_PATH, defaults)
    return defaults


def load_catalog_config() -> Optional[Dict[str, Any]]:
    if not CATALOG_CONFIG_PATH.exists():
        return None
    data = _load_json_or_none(CATALOG_CONFIG_PATH)
    if isinstance(data, dict):
        return data
    return None


def _is_hhmm(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        _parse_hhmm(value)
        return True
    except Exception:
        return False


def _is_hex_addr(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not value.lower().startswith("0x"):
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def validate_channels_payload(channels: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(channels, list):
        return ["channels must be a list"]

    seen_names: set[str] = set()
    seen_pins: set[int] = set()
    for idx, chan in enumerate(channels):
        if not isinstance(chan, dict):
            errors.append(f"channels[{idx}] must be an object")
            continue
        name = chan.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"channels[{idx}].name is required")
        else:
            upper = name.strip().upper()
            if upper in seen_names:
                errors.append(f"channels[{idx}].name duplicate: {upper}")
            seen_names.add(upper)
        gpio_pin = chan.get("gpio_pin")
        if not isinstance(gpio_pin, int):
            errors.append(f"channels[{idx}].gpio_pin must be int")
        else:
            if gpio_pin in seen_pins:
                errors.append(f"channels[{idx}].gpio_pin duplicate: {gpio_pin}")
            seen_pins.add(gpio_pin)
        if not isinstance(chan.get("active_low"), bool):
            errors.append(f"channels[{idx}].active_low must be bool")
    return errors


def validate_sensors_payload(sensors: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(sensors, dict):
        return ["sensors must be an object"]
    for key in ("bh1750_addr", "ads1115_addr", "lcd_addr"):
        if key in sensors and not _is_hex_addr(sensors.get(key)):
            errors.append(f"sensors.{key} must be hex string like 0x27")
    if "dht22_gpio" in sensors and not isinstance(sensors.get("dht22_gpio"), int):
        errors.append("sensors.dht22_gpio must be int")
    if "ds18b20_enabled" in sensors and not isinstance(sensors.get("ds18b20_enabled"), bool):
        errors.append("sensors.ds18b20_enabled must be bool")
    if "lcd_enabled" in sensors and not isinstance(sensors.get("lcd_enabled"), bool):
        errors.append("sensors.lcd_enabled must be bool")
    if "lcd_rows" in sensors and not isinstance(sensors.get("lcd_rows"), int):
        errors.append("sensors.lcd_rows must be int")
    if "lcd_lines" in sensors and not isinstance(sensors.get("lcd_lines"), list):
        errors.append("sensors.lcd_lines must be list")
    if isinstance(sensors.get("lcd_rows"), int) and isinstance(sensors.get("lcd_lines"), list):
        rows = int(sensors.get("lcd_rows") or 0)
        lines = sensors.get("lcd_lines") or []
        if rows > 0 and len(lines) != rows:
            errors.append(f"sensors.lcd_lines length must be {rows}")
    return errors


def validate_notifications_payload(cfg: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(cfg, dict):
        return ["notifications must be an object"]
    level = cfg.get("level")
    if level is not None and str(level).lower() not in ("debug", "info", "warning", "error"):
        errors.append("notifications.level must be one of debug|info|warning|error")
    for key in ("enabled", "telegram_enabled", "email_enabled", "allow_simulation"):
        if key in cfg and not isinstance(cfg.get(key), bool):
            errors.append(f"notifications.{key} must be bool")
    if "cooldown_seconds" in cfg:
        try:
            value = int(cfg.get("cooldown_seconds") or 0)
            if value < 0:
                errors.append("notifications.cooldown_seconds must be >= 0")
        except (TypeError, ValueError):
            errors.append("notifications.cooldown_seconds must be int")
    return errors


def validate_retention_payload(cfg: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(cfg, dict):
        return ["retention must be an object"]
    for key in ("sensor_log_days", "event_log_days", "actuator_log_days"):
        if key in cfg:
            try:
                value = int(cfg.get(key) or 0)
                if value < 0:
                    errors.append(f"retention.{key} must be >= 0")
            except (TypeError, ValueError):
                errors.append(f"retention.{key} must be int")
    if "cleanup_interval_hours" in cfg:
        try:
            value = int(cfg.get("cleanup_interval_hours") or 24)
            if value < 1:
                errors.append("retention.cleanup_interval_hours must be >= 1")
        except (TypeError, ValueError):
            errors.append("retention.cleanup_interval_hours must be int")
    if "archive_enabled" in cfg and not isinstance(cfg.get("archive_enabled"), bool):
        errors.append("retention.archive_enabled must be bool")
    if "archive_dir" in cfg and not isinstance(cfg.get("archive_dir"), str):
        errors.append("retention.archive_dir must be string")
    return errors


def validate_automation_payload(cfg: Any) -> List[str]:
    if not isinstance(cfg, dict):
        return ["automation must be an object"]
    errors: List[str] = []
    for key in ("window_start", "window_end", "reset_time", "fan_night_start", "fan_night_end", "heater_night_start", "heater_night_end", "pump_window_start", "pump_window_end"):
        if key in cfg and not _is_hhmm(cfg.get(key)):
            errors.append(f"automation.{key} must be HH:MM")
    return errors


def validate_limits_payload(cfg: Any) -> List[str]:
    if not isinstance(cfg, dict):
        return ["limits must be an object"]
    errors: List[str] = []
    int_keys = {"pump_max_seconds", "pump_cooldown_seconds", "heater_max_seconds", "energy_kwh_threshold"}
    float_keys = {"heater_cutoff_temp", "energy_kwh_low", "energy_kwh_high"}
    for key in DEFAULT_LIMITS:
        if key not in cfg:
            continue
        raw = cfg.get(key)
        if key in float_keys:
            try:
                value = float(raw)
                if value < 0:
                    errors.append(f"limits.{key} must be >= 0")
            except (TypeError, ValueError):
                errors.append(f"limits.{key} must be number")
        elif key in int_keys:
            try:
                value = int(raw)
                if key.endswith("_seconds") and value < 0:
                    errors.append(f"limits.{key} must be >= 0")
                if key == "pump_max_seconds" and value < 1:
                    errors.append("limits.pump_max_seconds must be >= 1")
                if key == "heater_max_seconds" and value < 1:
                    errors.append("limits.heater_max_seconds must be >= 1")
            except (TypeError, ValueError):
                errors.append(f"limits.{key} must be int")
        else:
            errors.append(f"limits.{key} unexpected")
    return errors


def validate_alerts_payload(cfg: Any) -> List[str]:
    if not isinstance(cfg, dict):
        return ["alerts must be an object"]
    errors: List[str] = []
    for key in DEFAULT_ALERTS:
        if key not in cfg:
            continue
        raw = cfg.get(key)
        if key == "sensor_offline_minutes":
            try:
                value = int(raw)
                if value < 0:
                    errors.append("alerts.sensor_offline_minutes must be >= 0")
            except (TypeError, ValueError):
                errors.append("alerts.sensor_offline_minutes must be int")
        else:
            try:
                value = float(raw)
                if value < 0:
                    errors.append(f"alerts.{key} must be >= 0")
            except (TypeError, ValueError):
                errors.append(f"alerts.{key} must be number")
    return errors


def save_panel_config_updates(limits: Optional[Dict[str, Any]] = None, automation: Optional[Dict[str, Any]] = None, alerts_cfg: Optional[Dict[str, Any]] = None) -> None:
    global panel_config
    current = dict(panel_config or load_panel_config())
    if limits:
        current["limits"] = _deep_merge_dict(current.get("limits") or {}, limits)
    if automation:
        current["automation"] = _deep_merge_dict(current.get("automation") or {}, automation)
    if alerts_cfg:
        current["alerts"] = _deep_merge_dict(current.get("alerts") or {}, alerts_cfg)
    _write_json_atomic(PANEL_CONFIG_PATH, current)
    panel_config = current


def save_notifications_config_updates(cfg: Dict[str, Any]) -> None:
    global notifications_config
    merged = dict(DEFAULT_NOTIFICATIONS)
    merged.update(notifications_config or {})
    merged.update(cfg or {})
    _write_json_atomic(NOTIFICATIONS_CONFIG_PATH, merged)
    notifications_config = merged
    notifications.update_config(merged)


def save_retention_config_updates(cfg: Dict[str, Any]) -> None:
    global retention_config
    merged = dict(DEFAULT_RETENTION)
    merged.update(retention_config or {})
    merged.update(cfg or {})
    _write_json_atomic(RETENTION_CONFIG_PATH, merged)
    retention_config = merged
    retention_manager.update_config(merged)


def load_updates() -> List[Dict[str, Any]]:
    defaults = [
        {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "title": "Güncellemeler sayfası eklendi",
            "summary": "Panelde yapılan değişiklikleri artık buradan takip edebilirsin.",
            "details": [
                "Yeni özellikler ve iyileştirmeler kullanıcı dilinde özetlenir.",
                "Bu liste GitHub'a push edildikçe güncellenir.",
            ],
        }
    ]
    if UPDATES_PATH.exists():
        try:
            data = _load_json_or_none(UPDATES_PATH)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    CONFIG_DIR.mkdir(exist_ok=True)
    _write_json_atomic(UPDATES_PATH, defaults)
    return defaults


channel_config = load_channel_config()
sensors_config = load_sensors_config()
notifications_config = load_notifications_config()
retention_config = load_retention_config()
panel_config = load_panel_config()
catalog_config = load_catalog_config()
actuator_manager = ActuatorManager(backend, channel_config)
sensor_manager = SensorManager()
sensor_manager.reload_config(sensors_config)
automation_engine = AutomationEngine(actuator_manager, sensor_manager)
notifications = NotificationManager(notifications_config)
alerts = AlertManager(notifications)
app_state = AppState(actuator_manager, sensor_manager, automation_engine, alerts)
lcd_manager = LCDManager(sensors_config)
retention_manager = RetentionManager(retention_config)
app_state.update_limits(panel_config.get("limits") or {})
app_state.update_alerts(panel_config.get("alerts") or {})
automation_engine.config.update(panel_config.get("automation") or {})

NODE_LOCK = threading.Lock()
NODE_REGISTRY: Dict[str, Dict[str, Any]] = {}
NODE_COMMANDS: Dict[str, List[Dict[str, Any]]] = {}
NODE_RATE_LIMIT: Dict[str, float] = {}
NODE_COMMAND_RATE_LIMIT: Dict[str, float] = {}
NODE_ACTUATOR_STATE: Dict[str, Dict[str, Any]] = {}
NODE_SENSOR_STATE: Dict[str, Dict[str, Any]] = {}


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
        CREATE TABLE IF NOT EXISTS telemetry_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            node_id TEXT,
            zone TEXT,
            metric TEXT NOT NULL,
            value REAL,
            unit TEXT,
            source TEXT,
            quality TEXT
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_log_ts ON telemetry_log (ts)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_log_zone_metric_ts ON telemetry_log (zone, metric, ts)")
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


def _node_token_from_request() -> Optional[str]:
    token = request.headers.get("X-Node-Token") or request.headers.get("Authorization") or ""
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token or None


def _require_node_auth(node_id: str) -> Optional[Tuple[Response, int]]:
    if not NODE_TOKENS and SIMULATION_MODE:
        return None
    if not NODE_TOKENS:
        return jsonify({"error": "node_auth_not_configured"}), 403
    token = _node_token_from_request()
    if not token or NODE_TOKENS.get(node_id) != token:
        return jsonify({"error": "auth_failed"}), 403
    return None


def _rate_limit_node(node_id: str) -> bool:
    if NODE_RATE_LIMIT_SECONDS <= 0:
        return False
    now = time.time()
    with NODE_LOCK:
        last_ts = NODE_RATE_LIMIT.get(node_id, 0.0)
        if now - last_ts < NODE_RATE_LIMIT_SECONDS:
            return True
        NODE_RATE_LIMIT[node_id] = now
    return False


def _rate_limit_node_commands(node_id: str) -> bool:
    if NODE_COMMAND_RATE_LIMIT_SECONDS <= 0:
        return False
    now = time.time()
    with NODE_LOCK:
        last_ts = NODE_COMMAND_RATE_LIMIT.get(node_id, 0.0)
        if now - last_ts < NODE_COMMAND_RATE_LIMIT_SECONDS:
            return True
        NODE_COMMAND_RATE_LIMIT[node_id] = now
    return False


def _register_node(node_id: str, zone: Optional[str], status: Any, remote_addr: Optional[str], ts: float) -> None:
    with NODE_LOCK:
        entry = NODE_REGISTRY.setdefault(node_id, {"node_id": node_id})
        entry["last_seen_ts"] = ts
        if zone:
            entry["zone"] = zone
        if remote_addr:
            entry["last_ip"] = remote_addr
        if isinstance(status, dict):
            entry["status"] = status


def _prune_node_commands(node_id: str, queue: List[Dict[str, Any]], now: float) -> List[Dict[str, Any]]:
    pruned: List[Dict[str, Any]] = []
    for cmd in queue:
        ttl = cmd.get("ttl_s")
        try:
            ttl_s = NODE_COMMAND_DEFAULT_TTL_SECONDS if ttl is None else int(ttl)
        except (TypeError, ValueError):
            ttl_s = NODE_COMMAND_DEFAULT_TTL_SECONDS
        created_raw = cmd.get("created_ts", now)
        try:
            created_ts = float(created_raw)
        except (TypeError, ValueError):
            created_ts = now
        if ttl_s > 0 and now - created_ts > ttl_s:
            log_event("node", "warning", "Node command expired", {"node_id": node_id, "cmd_id": cmd.get("cmd_id")})
            continue
        pruned.append(cmd)
    return pruned


def _apply_node_acks(node_id: str, ack_ids: Any) -> Tuple[List[str], List[Dict[str, str]]]:
    if not ack_ids:
        return [], []
    if not isinstance(ack_ids, list):
        return [], [{"code": "invalid_ack", "detail": "acks must be list"}]
    ack_list = [str(item).strip() for item in ack_ids if str(item).strip()]
    if not ack_list:
        return [], []
    errors: List[Dict[str, str]] = []
    acked_cmds: List[Dict[str, Any]] = []
    with NODE_LOCK:
        queue = NODE_COMMANDS.get(node_id, [])
        now = time.time()
        queue = _prune_node_commands(node_id, queue, now)
        queue_by_id = {str(cmd.get("cmd_id")): cmd for cmd in queue}
        unknown = [ack for ack in ack_list if ack not in queue_by_id]
        for ack in unknown:
            errors.append({"code": "unknown_ack", "detail": f"unknown cmd_id {ack}"})
        for ack in ack_list:
            cmd = queue_by_id.get(ack)
            if cmd:
                acked_cmds.append(cmd)
        queue = [cmd for cmd in queue if str(cmd.get("cmd_id")) not in ack_list]
        NODE_COMMANDS[node_id] = queue
    for cmd in acked_cmds:
        _record_node_actuator_state(node_id, cmd)
    accepted = [ack for ack in ack_list if ack not in unknown]
    return accepted, errors


def _record_node_actuator_state(node_id: str, cmd: Dict[str, Any]) -> None:
    actuator_id = str(cmd.get("actuator_id") or "").strip()
    if not actuator_id:
        return
    action = str(cmd.get("action") or "").strip().lower()
    state_raw = cmd.get("state")
    duty_raw = cmd.get("duty_pct")
    duty_pct = None
    if duty_raw is not None:
        try:
            duty_pct = float(duty_raw)
        except (TypeError, ValueError):
            duty_pct = None
    resolved_state: Optional[str] = None
    if action == "set_pwm":
        if duty_pct is None:
            return
        resolved_state = "on" if duty_pct > 0 else "off"
    else:
        if isinstance(state_raw, bool):
            resolved_state = "on" if state_raw else "off"
        elif isinstance(state_raw, str):
            candidate = state_raw.strip().lower()
            if candidate in ("on", "off"):
                resolved_state = candidate
    if not resolved_state:
        return
    with NODE_LOCK:
        NODE_ACTUATOR_STATE[actuator_id] = {
            "node_id": node_id,
            "state": resolved_state,
            "duty_pct": duty_pct,
            "last_change_ts": time.time(),
        }


def _lookup_node_actuator_state(actuator_id: str) -> Optional[Dict[str, Any]]:
    with NODE_LOCK:
        entry = NODE_ACTUATOR_STATE.get(actuator_id)
        if not entry:
            return None
        return dict(entry)


def _node_actuator_state_on(actuator_id: str) -> bool:
    entry = _lookup_node_actuator_state(actuator_id)
    if not entry:
        return False
    last_change = _coerce_float(entry.get("last_change_ts"))
    if last_change and NODE_STALE_SECONDS > 0:
        if time.time() - last_change > NODE_STALE_SECONDS:
            return False
    return str(entry.get("state")) == "on"


def _record_node_sensor_snapshot(node_id: str, zone: Optional[str], ts: float, sensors: List[Any]) -> None:
    if not sensors:
        return
    for entry in sensors:
        if not isinstance(entry, dict):
            continue
        source = entry.get("id") or entry.get("source")
        if not source:
            continue
        metric = entry.get("metric")
        if not isinstance(metric, str) or not metric.strip():
            continue
        value_raw = entry.get("value")
        value = _coerce_float(value_raw)
        if value_raw is not None and value is None:
            continue
        quality = entry.get("quality")
        if quality is not None and not isinstance(quality, str):
            quality = None
        source_id = str(source)
        metric_key = metric.strip().lower()
        with NODE_LOCK:
            snapshot = NODE_SENSOR_STATE.setdefault(source_id, {"sensor_id": source_id})
            snapshot["node_id"] = node_id
            if zone:
                snapshot["zone"] = zone
            snapshot["last_ts"] = ts
            metrics = snapshot.setdefault("metrics", {})
            metrics[metric_key] = {"value": value, "quality": quality, "ts": ts}


def _lookup_node_sensor_metrics(sensor_id: str) -> Optional[Dict[str, Any]]:
    with NODE_LOCK:
        entry = NODE_SENSOR_STATE.get(sensor_id)
        if not entry:
            return None
        metrics = entry.get("metrics")
        return {
            "metrics": dict(metrics) if isinstance(metrics, dict) else {},
            "last_ts": entry.get("last_ts"),
            "node_id": entry.get("node_id"),
            "zone": entry.get("zone"),
        }


def _snapshot_node_commands(node_id: str, since_ts: Optional[float]) -> List[Dict[str, Any]]:
    with NODE_LOCK:
        queue = NODE_COMMANDS.get(node_id, [])
        now = time.time()
        queue = _prune_node_commands(node_id, queue, now)
        NODE_COMMANDS[node_id] = queue
        filtered: List[Dict[str, Any]] = []
        for cmd in queue:
            created_raw = cmd.get("created_ts", 0.0)
            try:
                created_ts = float(created_raw)
            except (TypeError, ValueError):
                created_ts = 0.0
            if since_ts and created_ts <= since_ts:
                continue
            filtered.append(
                {
                    "cmd_id": cmd.get("cmd_id"),
                    "actuator_id": cmd.get("actuator_id"),
                    "action": cmd.get("action"),
                    "state": cmd.get("state"),
                    "duty_pct": cmd.get("duty_pct"),
                    "ttl_s": cmd.get("ttl_s"),
                }
            )
        return filtered


def _enqueue_node_command(node_id: str, command: Dict[str, Any]) -> Tuple[str, int, List[str]]:
    now = time.time()
    cmd = dict(command)
    cmd["cmd_id"] = uuid.uuid4().hex
    cmd["created_ts"] = now
    if cmd.get("ttl_s") is None:
        cmd["ttl_s"] = NODE_COMMAND_DEFAULT_TTL_SECONDS
    dropped: List[str] = []
    with NODE_LOCK:
        queue = NODE_COMMANDS.get(node_id, [])
        queue = _prune_node_commands(node_id, queue, now)
        queue.append(cmd)
        max_queue = NODE_COMMAND_MAX_QUEUE
        if max_queue > 0 and len(queue) > max_queue:
            overflow = len(queue) - max_queue
            dropped = [str(item.get("cmd_id")) for item in queue[:overflow]]
            queue = queue[overflow:]
        NODE_COMMANDS[node_id] = queue
        queue_size = len(queue)
    log_event(
        "node",
        "info",
        "Node command queued",
        {
            "node_id": node_id,
            "cmd_id": cmd["cmd_id"],
            "actuator_id": cmd.get("actuator_id"),
            "action": cmd.get("action"),
            "state": cmd.get("state"),
            "duty_pct": cmd.get("duty_pct"),
        },
    )
    if dropped:
        log_event(
            "node",
            "warning",
            "Node command queue trimmed",
            {"node_id": node_id, "dropped_ids": dropped},
        )
    return cmd["cmd_id"], queue_size, dropped


def _clear_node_command_queue(node_id: str, reason: str) -> None:
    with NODE_LOCK:
        NODE_COMMANDS[node_id] = []
    log_event("node", "warning", "Node command queue cleared", {"node_id": node_id, "reason": reason})


def _clear_all_node_command_queues(reason: str) -> None:
    cleared = 0
    with NODE_LOCK:
        for node_id, queue in NODE_COMMANDS.items():
            if queue:
                cleared += len(queue)
            NODE_COMMANDS[node_id] = []
    if cleared:
        log_event("node", "warning", "All node command queues cleared", {"reason": reason, "cleared": cleared})


def _queue_remote_emergency_stop() -> Dict[str, Dict[str, Any]]:
    if not isinstance(catalog_config, dict):
        return {}
    catalog_actuators = catalog_config.get("actuators")
    if not isinstance(catalog_actuators, list):
        return {}
    queued: Dict[str, Dict[str, Any]] = {}
    cleared_nodes: set[str] = set()
    for entry in catalog_actuators:
        if not isinstance(entry, dict):
            continue
        backend = str(entry.get("backend") or "").lower()
        if backend != "esp32":
            continue
        node_id = str(entry.get("node_id") or "").strip()
        if not node_id:
            continue
        actuator_id = str(entry.get("id") or entry.get("legacy_name") or entry.get("name") or "").strip()
        if not actuator_id:
            continue
        if node_id not in cleared_nodes:
            _clear_node_command_queue(node_id, "emergency_stop")
            cleared_nodes.add(node_id)
        supports_pwm = bool(entry.get("supports_pwm"))
        action = "set_pwm" if supports_pwm else "set_state"
        duty_pct = 0.0 if supports_pwm else None
        cmd_id, _queue_size, dropped = _enqueue_node_command(
            node_id,
            {
                "actuator_id": actuator_id,
                "action": action,
                "state": "off",
                "duty_pct": duty_pct,
            },
        )
        node_entry = queued.setdefault(node_id, {"queued": 0})
        node_entry["queued"] += 1
        node_entry.setdefault("cmd_ids", []).append(cmd_id)
        if dropped:
            node_entry.setdefault("dropped", []).extend(dropped)
    return queued


def _log_telemetry_rows(node_id: str, zone: Optional[str], ts: float, sensors: List[Any]) -> Tuple[int, List[Dict[str, str]]]:
    rows: List[Tuple[Any, ...]] = []
    errors: List[Dict[str, str]] = []
    for idx, entry in enumerate(sensors):
        if not isinstance(entry, dict):
            errors.append({"code": "invalid_sensor", "detail": f"sensors[{idx}] not object"})
            continue
        metric = entry.get("metric")
        if not isinstance(metric, str) or not metric.strip():
            errors.append({"code": "invalid_sensor", "detail": f"sensors[{idx}] missing metric"})
            continue
        value_raw = entry.get("value")
        value = _coerce_float(value_raw)
        if value_raw is not None and value is None:
            errors.append({"code": "invalid_sensor", "detail": f"sensors[{idx}] value not number"})
            continue
        unit = entry.get("unit")
        if unit is not None and not isinstance(unit, str):
            errors.append({"code": "invalid_sensor", "detail": f"sensors[{idx}] unit not string"})
            continue
        source = entry.get("id") or entry.get("source")
        if source is not None:
            source = str(source)
        quality = entry.get("quality")
        if quality is not None and not isinstance(quality, str):
            errors.append({"code": "invalid_sensor", "detail": f"sensors[{idx}] quality not string"})
            continue
        rows.append((ts, node_id, zone, metric.strip(), value, unit, source, quality))

    if not rows:
        return 0, errors
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO telemetry_log (ts, node_id, zone, metric, value, unit, source, quality)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        errors.append({"code": "db_error", "detail": str(exc)})
        return 0, errors
    return len(rows), errors


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


def _parse_report_date(param: Optional[str], tz: ZoneInfo) -> Optional[date]:
    if not param:
        return None
    try:
        return datetime.strptime(param, "%Y-%m-%d").date()
    except ValueError:
        return None


def _default_report_date(cfg: Dict[str, Any]) -> date:
    tz = ZoneInfo(cfg.get("SERA_TZ", "Europe/Istanbul"))
    return datetime.now(tz).date()


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

    if isinstance(catalog_config, dict):
        catalog_sensors = catalog_config.get("sensors")
        if isinstance(catalog_sensors, list):
            for sensor in catalog_sensors:
                if not isinstance(sensor, dict):
                    continue
                sensor_id = str(sensor.get("id") or "").strip()
                if not sensor_id or sensor_id in health:
                    continue
                backend = str(sensor.get("backend") or "").lower()
                is_remote = backend == "esp32" or bool(sensor.get("node_id"))
                if not is_remote:
                    continue
                snapshot = _lookup_node_sensor_metrics(sensor_id)
                metrics = snapshot.get("metrics") if snapshot else None
                metrics_map = metrics if isinstance(metrics, dict) else {}
                last_seen_ts = _coerce_float(snapshot.get("last_ts")) if snapshot else None
                status = "missing"
                if metrics_map:
                    status = _merge_metric_status(list(metrics_map.values()))
                if last_seen_ts and NODE_STALE_SECONDS > 0 and now - last_seen_ts > NODE_STALE_SECONDS:
                    status = "missing"
                last_ok_ts = _sensor_last_ok_ts.get(sensor_id)
                if status in ("ok", "simulated"):
                    last_ok_ts = last_seen_ts or last_ok_ts or now
                    _sensor_last_ok_ts[sensor_id] = last_ok_ts
                first_seen_ts = _sensor_first_seen_ts.get(sensor_id) or last_seen_ts or now
                _sensor_first_seen_ts.setdefault(sensor_id, first_seen_ts)
                offline_seconds = None
                if status in ("ok", "simulated"):
                    offline_seconds = 0.0
                else:
                    reference = last_ok_ts or first_seen_ts
                    if reference:
                        offline_seconds = max(0.0, now - reference)
                health[sensor_id] = {
                    "label": str(sensor.get("label") or sensor_id),
                    "status": status,
                    "last_seen_ts": last_seen_ts,
                    "last_ok_ts": last_ok_ts,
                    "first_seen_ts": first_seen_ts,
                    "offline_seconds": offline_seconds,
                    "offline_limit_seconds": offline_limit_seconds,
                    "zone": sensor.get("zone"),
                    "node_id": sensor.get("node_id"),
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


def _legacy_catalog_snapshot() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    zone_id = "sera"
    zones = [{"id": zone_id, "label": "SERA"}]

    sensors: List[Dict[str, Any]] = []
    dht_gpio = sensors_config.get("dht22_gpio")
    sensors.append(
        {
            "id": f"{zone_id}-dht22",
            "label": f"{zone_id.upper()} DHT22",
            "zone": zone_id,
            "kind": "dht22",
            "purpose": "temp_hum",
            "gpio": dht_gpio,
        }
    )
    if sensors_config.get("ds18b20_enabled", True):
        sensors.append(
            {
                "id": f"{zone_id}-ds18b20",
                "label": f"{zone_id.upper()} DS18B20",
                "zone": zone_id,
                "kind": "ds18b20",
                "purpose": "temp",
            }
        )
    bh_addr = sensors_config.get("bh1750_addr")
    if bh_addr:
        sensors.append(
            {
                "id": f"{zone_id}-bh1750",
                "label": f"{zone_id.upper()} BH1750",
                "zone": zone_id,
                "kind": "bh1750",
                "purpose": "lux",
                "i2c_addr": bh_addr,
            }
        )
    ads_addr = sensors_config.get("ads1115_addr")
    if ads_addr:
        for ch in ("ch0", "ch1", "ch2", "ch3"):
            sensors.append(
                {
                    "id": f"{zone_id}-soil-{ch}",
                    "label": f"{zone_id.upper()} Soil {ch.upper()}",
                    "zone": zone_id,
                    "kind": "ads1115",
                    "purpose": "soil",
                    "i2c_addr": ads_addr,
                    "ads_channel": ch,
                }
            )

    actuators: List[Dict[str, Any]] = []
    for chan in channel_config:
        name = str(chan.get("name") or "").strip()
        if not name:
            continue
        label = str(chan.get("description") or "").strip() or name
        entry: Dict[str, Any] = {
            "id": name.upper(),
            "label": label,
            "zone": zone_id,
            "role": str(chan.get("role") or "other").lower(),
            "backend": "pi_gpio",
            "gpio_pin": chan.get("gpio_pin"),
            "active_low": bool(chan.get("active_low", False)),
            "legacy_name": name.upper(),
        }
        for key in ("power_w", "quantity", "voltage_v", "notes", "description", "safe_default"):
            if key in chan:
                entry[key] = chan[key]
        actuators.append(entry)

    return zones, sensors, actuators


def _metric_pick(metrics: Dict[str, Any], keys: List[str]) -> Optional[Dict[str, Any]]:
    for key in keys:
        entry = metrics.get(key)
        if isinstance(entry, dict):
            return entry
    return None


def _quality_to_status(quality: Optional[str]) -> str:
    if quality is None or quality in ("ok", "simulated"):
        return "ok"
    if quality in ("missing", "disabled"):
        return quality
    return "error"


def _merge_metric_status(entries: List[Optional[Dict[str, Any]]]) -> str:
    statuses = [_quality_to_status(entry.get("quality")) for entry in entries if entry]
    if not statuses:
        return "missing"
    if "error" in statuses:
        return "error"
    if "missing" in statuses:
        return "missing"
    if "disabled" in statuses:
        return "disabled"
    return "ok"


def _apply_sensor_status(sensor: Dict[str, Any], readings: Dict[str, Any]) -> None:
    sensor_id = str(sensor.get("id") or "").strip()
    node_id = sensor.get("node_id")
    backend = str(sensor.get("backend") or "").lower()
    if sensor_id and (node_id or backend == "esp32"):
        snapshot = _lookup_node_sensor_metrics(sensor_id)
        if snapshot:
            metrics = snapshot.get("metrics") or {}
            last_ts = _coerce_float(snapshot.get("last_ts"))
            if last_ts and NODE_STALE_SECONDS > 0 and time.time() - last_ts > NODE_STALE_SECONDS:
                sensor["status"] = "missing"
                return
            kind = str(sensor.get("kind") or "")
            purpose = str(sensor.get("purpose") or "")
            if kind in ("dht11", "dht22", "sht31") or purpose == "temp_hum":
                temp_entry = _metric_pick(metrics, ["temp_c", "temperature", "temp"])
                hum_entry = _metric_pick(metrics, ["rh_pct", "humidity", "hum"])
                status = _merge_metric_status([temp_entry, hum_entry])
                if temp_entry or hum_entry:
                    sensor["status"] = status
                    sensor["last_value"] = {
                        "temperature": temp_entry.get("value") if temp_entry else None,
                        "humidity": hum_entry.get("value") if hum_entry else None,
                        "ts": last_ts,
                    }
                    return
            elif kind == "ds18b20" or purpose == "temp":
                temp_entry = _metric_pick(metrics, ["temp_c", "temperature", "temp"])
                status = _merge_metric_status([temp_entry])
                if temp_entry:
                    sensor["status"] = status
                    sensor["last_value"] = {"temperature": temp_entry.get("value"), "ts": last_ts}
                    return
            elif kind in ("bh1750", "ldr") or purpose == "lux":
                lux_entry = _metric_pick(metrics, ["lux", "light", "lux_lm"])
                status = _merge_metric_status([lux_entry])
                if lux_entry:
                    sensor["status"] = status
                    sensor["last_value"] = {"lux": lux_entry.get("value"), "ts": last_ts}
                    return
            elif kind == "ads1115" or purpose == "soil":
                raw_entry = _metric_pick(metrics, ["soil_raw", "soil", "raw"])
                status = _merge_metric_status([raw_entry])
                if raw_entry:
                    sensor["status"] = status
                    sensor["last_value"] = {"raw": raw_entry.get("value"), "ts": last_ts}
                    return
            elif metrics:
                metric_name = next(iter(metrics.keys()))
                entry = metrics.get(metric_name) or {}
                sensor["status"] = _merge_metric_status([entry])
                sensor["last_value"] = {"metric": metric_name, "value": entry.get("value"), "ts": last_ts}
                return
        sensor["status"] = "missing"
        return

    kind = str(sensor.get("kind") or "")
    status = None
    last_value: Optional[Dict[str, Any]] = None
    if kind in ("dht11", "dht22"):
        entry = readings.get("dht22") or {}
        status = entry.get("status")
        last_value = {
            "temperature": entry.get("temperature"),
            "humidity": entry.get("humidity"),
            "ts": entry.get("ts"),
        }
    elif kind == "ds18b20":
        entry = readings.get("ds18b20") or {}
        status = entry.get("status")
        last_value = {"temperature": entry.get("temperature"), "ts": entry.get("ts")}
    elif kind == "bh1750":
        entry = readings.get("bh1750") or {}
        status = entry.get("status")
        last_value = {"lux": entry.get("lux"), "ts": entry.get("ts")}
    elif kind == "ads1115":
        entry = readings.get("soil") or {}
        status = entry.get("status")
        channel = str(sensor.get("ads_channel") or "ch0").lower()
        last_value = {"raw": entry.get(channel), "ts": entry.get("ts")}

    if status is None:
        status = "missing"
    sensor["status"] = status
    if last_value is not None:
        sensor["last_value"] = last_value


def _apply_actuator_state(actuator: Dict[str, Any], actuator_state: Dict[str, Any]) -> None:
    candidates: List[str] = []
    for key in ("id", "legacy_name", "name"):
        value = actuator.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())
            candidates.append(value.strip().upper())
    state_entry: Optional[Dict[str, Any]] = None
    for key in candidates:
        if key in actuator_state:
            state_entry = actuator_state.get(key)
            break
    if state_entry is None and "gpio_pin" in actuator:
        pin = actuator.get("gpio_pin")
        for entry in actuator_state.values():
            if entry.get("gpio_pin") == pin:
                state_entry = entry
                break
    if not state_entry:
        for candidate in candidates:
            remote_entry = _lookup_node_actuator_state(candidate)
            if remote_entry:
                actuator["state"] = str(remote_entry.get("state")) == "on"
                actuator["last_change_ts"] = remote_entry.get("last_change_ts")
                actuator["reason"] = "remote_ack"
                if remote_entry.get("duty_pct") is not None:
                    actuator["duty_pct"] = remote_entry.get("duty_pct")
                return
        return
    actuator["state"] = state_entry.get("state")
    actuator["last_change_ts"] = state_entry.get("last_change_ts")
    actuator["reason"] = state_entry.get("reason")


def _node_registry_snapshot() -> List[Dict[str, Any]]:
    now = time.time()
    with NODE_LOCK:
        entries = [dict(entry) for entry in NODE_REGISTRY.values()]
        queue_sizes: Dict[str, int] = {}
        for node_id, queue in NODE_COMMANDS.items():
            pruned = _prune_node_commands(node_id, queue, now)
            NODE_COMMANDS[node_id] = pruned
            queue_sizes[node_id] = len(pruned)
    stale_threshold = NODE_STALE_SECONDS if NODE_STALE_SECONDS > 0 else None
    for entry in entries:
        last_seen = _coerce_float(entry.get("last_seen_ts"))
        data_age = None
        if last_seen:
            data_age = max(0.0, now - last_seen)
        if last_seen is None:
            status = "unknown"
        elif stale_threshold is not None and data_age is not None and data_age > stale_threshold:
            status = "missing"
        else:
            status = "ok"
        entry["health"] = {
            "status": status,
            "data_age_sec": data_age,
            "stale_threshold_sec": stale_threshold,
        }
        node_id = entry.get("node_id")
        if node_id:
            entry["queue_size"] = queue_sizes.get(node_id, 0)
    return entries


def _zone_first_snapshot(readings: Dict[str, Any], actuator_state: Dict[str, Any]) -> Dict[str, Any]:
    source = "legacy"
    zones: List[Dict[str, Any]]
    sensors: List[Dict[str, Any]]
    actuators: List[Dict[str, Any]]
    version = 0
    if isinstance(catalog_config, dict):
        source = "catalog"
        version = int(catalog_config.get("version") or 0)
        zones = [dict(z) for z in catalog_config.get("zones", []) if isinstance(z, dict)]
        sensors = [dict(s) for s in catalog_config.get("sensors", []) if isinstance(s, dict)]
        actuators = [dict(a) for a in catalog_config.get("actuators", []) if isinstance(a, dict)]
    else:
        zones, sensors, actuators = _legacy_catalog_snapshot()

    zone_map: Dict[str, Dict[str, Any]] = {}
    for zone in zones:
        zid = zone.get("id")
        if isinstance(zid, str) and zid.strip():
            zone_entry = dict(zone)
            zone_entry.setdefault("sensors", [])
            zone_entry.setdefault("actuators", [])
            zone_map[zid] = zone_entry

    for sensor in sensors:
        _apply_sensor_status(sensor, readings)
        zid = sensor.get("zone")
        if isinstance(zid, str) and zid in zone_map:
            zone_map[zid]["sensors"].append(sensor.get("id"))

    for actuator in actuators:
        _apply_actuator_state(actuator, actuator_state)
        zid = actuator.get("zone")
        if isinstance(zid, str) and zid in zone_map:
            zone_map[zid]["actuators"].append(actuator.get("id"))

    return {
        "source": source,
        "version": version,
        "zones": list(zone_map.values()),
        "sensors": sensors,
        "actuators": actuators,
        "nodes": _node_registry_snapshot(),
    }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _actuator_daily_seconds(name: str) -> float:
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT SUM(seconds)
            FROM actuator_log
            WHERE name = ?
              AND state = 'on'
              AND seconds IS NOT NULL
              AND ts >= ?
            """,
            (name, cutoff_str),
        )
        row = cur.fetchone()
        return float(row[0] or 0)
    except Exception:
        return 0.0
    finally:
        conn.close()


def _is_actuator_role(name: str, role: str, chan: Dict[str, Any], meta: Optional[Dict[str, Any]]) -> bool:
    target = role.lower()
    if str(chan.get("role") or "").lower() == target:
        return True
    if meta and str(meta.get("role") or "").lower() == target:
        return True
    if target == "pump":
        return "PUMP" in name
    if target == "heater":
        return "HEATER" in name
    return False


def _find_catalog_actuator(name: str) -> Optional[Dict[str, Any]]:
    if not isinstance(catalog_config, dict):
        return None
    candidates = catalog_config.get("actuators")
    if not isinstance(candidates, list):
        return None
    target = name.upper()
    target_pin = None
    chan = actuator_manager.channels.get(target)
    if chan:
        target_pin = chan.get("gpio_pin")
    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        for key in ("id", "legacy_name", "name"):
            value = entry.get(key)
            if isinstance(value, str) and value.strip().upper() == target:
                return entry
        if target_pin is not None and entry.get("gpio_pin") == target_pin:
            return entry
    return None


def _resolve_catalog_channel_name(entry: Dict[str, Any]) -> Optional[str]:
    for key in ("legacy_name", "name", "id"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            candidate = value.strip().upper()
            if candidate in actuator_manager.channels:
                return candidate
    gpio_pin = entry.get("gpio_pin")
    if gpio_pin is None:
        return None
    for name, info in actuator_manager.channels.items():
        if info.get("gpio_pin") == gpio_pin:
            return name
    return None


def _fan_dependency_satisfied(entry: Dict[str, Any]) -> bool:
    if not entry.get("requires_fan_dependency"):
        return True
    role = str(entry.get("role") or "").lower()
    if role.startswith("fan"):
        return True
    zone_id = entry.get("zone")
    if not zone_id or not isinstance(catalog_config, dict):
        return False
    catalog_actuators = catalog_config.get("actuators")
    if not isinstance(catalog_actuators, list):
        return False
    fan_roles = {"fan", "fan_canopy", "fan_box", "fan_exhaust"}
    fan_candidates = [
        act
        for act in catalog_actuators
        if isinstance(act, dict)
        and act.get("zone") == zone_id
        and str(act.get("role") or "").lower() in fan_roles
    ]
    if not fan_candidates:
        return False
    state_snapshot = actuator_manager.get_state()
    for fan_entry in fan_candidates:
        channel_name = _resolve_catalog_channel_name(fan_entry)
        if not channel_name:
            channel_name = None
        if state_snapshot.get(channel_name, {}).get("state"):
            return True
        actuator_id = None
        if isinstance(fan_entry.get("id"), str) and fan_entry.get("id"):
            actuator_id = fan_entry.get("id")
        elif isinstance(fan_entry.get("legacy_name"), str) and fan_entry.get("legacy_name"):
            actuator_id = fan_entry.get("legacy_name")
        elif isinstance(fan_entry.get("name"), str) and fan_entry.get("name"):
            actuator_id = fan_entry.get("name")
        if actuator_id and _node_actuator_state_on(actuator_id):
            return True
    return False


def _record_sensor_alert(key: str, label: str, status: Optional[str], action: Optional[str] = None) -> None:
    now = time.time()
    state = _sensor_alert_state.get(key, {})
    last_status = state.get("status")
    last_ts = state.get("ts", 0)
    if status == "disabled":
        return
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
    target = tag.lower()
    for name, info in state_snapshot.items():
        role = str(info.get("role") or "").lower()
        if (tag in name or role == target) and info.get("state"):
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
        risky = []
        for name, info in actuator_manager.channels.items():
            role = str(info.get("role") or "").lower()
            if role in ("pump", "heater"):
                risky.append(name)
                continue
            if "PUMP" in name or "HEATER" in name:
                risky.append(name)
        for name in risky:
            actuator_manager.set_state(name, False, "stale_sensors")
        alerts.add("warning", "Sensor data stale; risky actuators turned off")


def apply_actuator_command(name: str, desired_state: bool, seconds: Optional[int], reason: str) -> Optional[int]:
    name = name.upper()
    if app_state.estop:
        raise ActuationError("E-STOP active")
    if app_state.safe_mode:
        raise ActuationError("SAFE MODE active")
    chan = actuator_manager.channels.get(name)
    if not chan:
        raise ActuationError("Unknown actuator")
    meta = _find_catalog_actuator(name)
    is_pump = _is_actuator_role(name, "pump", chan, meta)
    is_heater = _is_actuator_role(name, "heater", chan, meta)
    if desired_state and is_pump and app_state.sensor_faults.get("pump"):
        raise ActuationError("Pump locked: soil sensor error")
    if desired_state and is_heater and app_state.sensor_faults.get("heater"):
        raise ActuationError("Heater locked: temperature sensor error")
    max_on_s = _safe_int(meta.get("max_on_s"), 0) if meta else 0
    max_daily_s = _safe_int(meta.get("max_daily_s"), 0) if meta else 0
    cooldown_s = _safe_int(meta.get("cooldown_s"), 0) if meta else 0
    if max_on_s < 0:
        max_on_s = 0
    if max_daily_s < 0:
        max_daily_s = 0
    if cooldown_s < 0:
        cooldown_s = 0
    if desired_state and meta and not _fan_dependency_satisfied(meta):
        raise ActuationError("Fan required by safety policy")
    current_state = actuator_manager.state.get(name, {}).get("state")
    if desired_state and current_state:
        raise ActuationError("Already on")
    seconds_param = int(seconds) if seconds is not None else None
    if seconds_param is not None and seconds_param <= 0:
        raise ActuationError("Seconds must be positive")
    limits = app_state.limits
    if desired_state and is_pump:
        if seconds_param is None:
            raise ActuationError("Pump requires seconds")
        if seconds_param <= 0:
            raise ActuationError("Seconds must be positive")
        max_allowed = limits.get("pump_max_seconds", 15)
        if max_on_s > 0:
            max_allowed = min(max_allowed, max_on_s)
        if seconds_param > max_allowed:
            raise ActuationError("Pump duration exceeds max")
        cooldown = limits.get("pump_cooldown_seconds", 60)
        if cooldown_s > 0:
            cooldown = max(cooldown, cooldown_s)
        last_stop = actuator_manager.last_stop_ts.get(name) or actuator_manager.last_pump_stop_ts
        if last_stop and time.time() - last_stop < cooldown:
            remaining = int(cooldown - (time.time() - last_stop))
            raise ActuationError(f"Pump cooldown {remaining}s")
    if desired_state and is_heater:
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
    if desired_state and max_on_s > 0:
        if seconds_param is None:
            seconds_param = max_on_s
        else:
            seconds_param = min(seconds_param, max_on_s)
    if desired_state and max_daily_s > 0:
        used_seconds = _actuator_daily_seconds(name)
        remaining = max_daily_s - used_seconds
        remaining_seconds = int(remaining)
        if remaining_seconds <= 0:
            raise ActuationError("Daily limit reached")
        if seconds_param is None or seconds_param > remaining_seconds:
            seconds_param = remaining_seconds
    if desired_state and cooldown_s > 0 and not is_pump:
        last_stop = actuator_manager.last_stop_ts.get(name)
        if last_stop and time.time() - last_stop < cooldown_s:
            remaining = int(cooldown_s - (time.time() - last_stop))
            raise ActuationError(f"Cooldown {remaining}s")
    actuator_manager.set_state(name, desired_state, reason, seconds_param)
    log_actuation(name, desired_state, reason, seconds_param)
    return seconds_param


# Test panel helpers
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


def retention_loop() -> None:
    while True:
        try:
            retention_manager.cleanup_if_due()
        except Exception as exc:
            log_event("maintenance", "warning", f"Retention cleanup error: {exc}", None)
        time.sleep(60)


if not DISABLE_BACKGROUND_LOOPS:
    threading.Thread(target=sensor_loop, daemon=True).start()
    threading.Thread(target=automation_loop, daemon=True).start()
    threading.Thread(target=retention_loop, daemon=True).start()


# Routes
@app.route("/")
def index() -> Any:
    if USE_NEW_UI:
        return redirect(url_for("overview"))
    return redirect(url_for("dashboard"))


@app.route("/overview")
def overview() -> Any:
    if not USE_NEW_UI:
        return redirect(url_for("dashboard"))
    return render_template("overview.html")


@app.route("/zones")
def zones() -> Any:
    if not USE_NEW_UI:
        return redirect(url_for("dashboard"))
    return render_template("zones.html")


@app.route("/dashboard")
def dashboard() -> Any:
    if USE_NEW_UI:
        return redirect(url_for("overview"))
    return render_template("dashboard.html")


@app.route("/control")
def control() -> Any:
    if USE_NEW_UI:
        return render_template("control_v1.html")
    return render_template("control.html")


@app.route("/settings")
def settings() -> Any:
    base_template = "base_v1.html" if USE_NEW_UI else "base.html"
    return render_template("settings.html", base_template=base_template)


@app.route("/more")
def more_page() -> Any:
    if not USE_NEW_UI:
        return redirect(url_for("dashboard"))
    return render_template("more.html")


@app.route("/logs")
def logs() -> Any:
    if USE_NEW_UI:
        return render_template("logs_v1.html")
    return render_template("logs.html")


@app.route("/hardware")
def hardware() -> Any:
    base_template = "base_v1.html" if USE_NEW_UI else "base.html"
    return render_template("hardware.html", base_template=base_template)


@app.route("/lcd")
def lcd_page() -> Any:
    base_template = "base_v1.html" if USE_NEW_UI else "base.html"
    return render_template("lcd.html", base_template=base_template)


@app.route("/help")
@app.route("/sss")
def help_page() -> Any:
    base_template = "base_v1.html" if USE_NEW_UI else "base.html"
    return render_template("help.html", base_template=base_template, use_new_ui=USE_NEW_UI)


@app.route("/updates")
def updates_page() -> Any:
    base_template = "base_v1.html" if USE_NEW_UI else "base.html"
    return render_template("updates.html", base_template=base_template)


@app.route("/reports/daily")
def reports_daily_page() -> Any:
    cfg = load_reporting_config()
    tz = ZoneInfo(cfg.get("SERA_TZ", "Europe/Istanbul"))
    date_raw = request.args.get("date")
    profile = request.args.get("profile")
    target_date = _parse_report_date(date_raw, tz)
    if target_date is None:
        target_date = _default_report_date(cfg)
    report = build_daily_report(target_date, profile, cfg)
    base_template = "base_v1.html" if USE_NEW_UI else "base.html"
    return render_template(
        "reports_daily.html",
        report=report,
        target_date=target_date.isoformat(),
        profile=profile or report.get("profile", {}).get("name"),
        base_template=base_template,
        use_new_ui=USE_NEW_UI,
    )


@app.route("/reports/weekly")
def reports_weekly_page() -> Any:
    cfg = load_reporting_config()
    tz = ZoneInfo(cfg.get("SERA_TZ", "Europe/Istanbul"))
    end_raw = request.args.get("end")
    profile = request.args.get("profile")
    end_date = _parse_report_date(end_raw, tz)
    if end_date is None:
        end_date = _default_report_date(cfg)
    report = build_weekly_report(end_date, profile, cfg)
    base_template = "base_v1.html" if USE_NEW_UI else "base.html"
    return render_template(
        "reports_weekly.html",
        report=report,
        end_date=end_date.isoformat(),
        profile=profile or report.get("config", {}).get("ACTIVE_PROFILE"),
        base_template=base_template,
        use_new_ui=USE_NEW_UI,
    )


def api_status_payload(readings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if readings is None and DISABLE_BACKGROUND_LOOPS and sensor_manager.simulation:
        try:
            readings = sensor_manager.read_all()
        except Exception:
            readings = None
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
    now_ts = time.time()
    for name, info in actuator_manager.channels.items():
        role = str(info.get("role") or "").lower()
        is_pump = role == "pump" or "PUMP" in name
        if is_pump:
            last_stop = actuator_manager.last_stop_ts.get(name)
            if not last_stop:
                last_stop = actuator_manager.last_pump_stop_ts
            remaining = 0.0
            if last_stop:
                remaining = max(0.0, pump_cooldown - (now_ts - last_stop))
            cooldowns[name] = round(remaining, 1)
    actuator_state = actuator_manager.get_state()
    zone_snapshot = _zone_first_snapshot(readings, actuator_state)
    return {
        "timestamp": _timestamp(),
        "sensor_ts": sensor_ts,
        "data_age_sec": data_age_sec,
        "data_stale": data_stale,
        "stale_threshold_sec": SENSOR_STALE_SECONDS,
        "sensor_readings": readings,
        "actuator_state": actuator_state,
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
        "notifications": notifications.public_status(),
        "retention": retention_manager.public_status(),
        "zones": zone_snapshot["zones"],
        "sensors": zone_snapshot["sensors"],
        "actuators": zone_snapshot["actuators"],
        "nodes": zone_snapshot["nodes"],
        "catalog": {"source": zone_snapshot["source"], "version": zone_snapshot["version"]},
        "compat": {"deprecated_fields": ["sensor_readings", "actuator_state", "automation_state"]},
    }


@app.route("/api/status")
def api_status() -> Any:
    response = api_status_payload()
    return jsonify(response)


@app.route("/api/nodes")
def api_nodes() -> Any:
    return jsonify({"nodes": _node_registry_snapshot()})


@app.route("/api/updates")
def api_updates() -> Any:
    return jsonify({"items": load_updates()})


@app.route("/api/notifications/test", methods=["POST"])
def api_notifications_test() -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    payload = request.get_json(force=True, silent=True) or {}
    message = str(payload.get("message") or "")
    result = notifications.send_test(message)
    return jsonify({"ok": True, **result})


@app.route("/api/maintenance/retention_cleanup", methods=["POST"])
def api_retention_cleanup() -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    try:
        retention_manager.cleanup_now()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True})


@app.route("/api/telemetry", methods=["POST"])
def api_telemetry() -> Any:
    payload = request.get_json(force=True, silent=True) or {}
    node_id = str(payload.get("node_id") or "").strip()
    if not node_id:
        return jsonify({"error": "node_id required"}), 400
    auth_error = _require_node_auth(node_id)
    if auth_error:
        return auth_error
    if _rate_limit_node(node_id):
        return jsonify({"error": "rate_limited"}), 429

    sensors = payload.get("sensors") or []
    if not isinstance(sensors, list):
        return jsonify({"error": "sensors must be list"}), 400

    ts_raw = payload.get("ts")
    ts = _parse_ts_param(str(ts_raw)) if ts_raw is not None else None
    if ts is None:
        ts = time.time()

    zone_raw = payload.get("zone")
    zone = str(zone_raw).strip() if zone_raw else None

    acks, ack_errors = _apply_node_acks(node_id, payload.get("acks"))
    row_count, errors = _log_telemetry_rows(node_id, zone, ts, sensors)
    errors = ack_errors + errors

    _record_node_sensor_snapshot(node_id, zone, ts, sensors)
    _register_node(node_id, zone, payload.get("status"), request.remote_addr, ts)
    if errors:
        log_event("node", "warning", "Telemetry errors", {"node_id": node_id, "errors": errors})

    status_code = 200
    if errors:
        status_code = 207 if row_count > 0 else 400
    return jsonify({"acks": acks, "errors": errors}), status_code


@app.route("/api/node_commands", methods=["GET", "POST"])
def api_node_commands() -> Any:
    if request.method == "POST":
        admin_error = require_admin()
        if admin_error:
            return admin_error
        payload = request.get_json(force=True, silent=True) or {}
        node_id = str(payload.get("node_id") or "").strip()
        actuator_id = str(payload.get("actuator_id") or "").strip()
        if not node_id:
            return jsonify({"error": "node_id required"}), 400
        if not actuator_id:
            return jsonify({"error": "actuator_id required"}), 400
        meta = _find_catalog_actuator(actuator_id)
        if meta:
            backend = str(meta.get("backend") or "")
            if backend and backend != "esp32":
                return jsonify({"error": "actuator backend not supported"}), 400
            expected_node = str(meta.get("node_id") or "").strip()
            if expected_node and expected_node != node_id:
                return jsonify({"error": "node_id mismatch"}), 400

        action_raw = payload.get("action")
        action = str(action_raw).strip().lower() if action_raw else ""
        duty_raw = payload.get("duty_pct")
        state_raw = payload.get("state")
        if not action:
            action = "set_pwm" if duty_raw is not None else "set_state"
        if action not in ("set_state", "set_pwm"):
            return jsonify({"error": "invalid action"}), 400

        state = None
        if isinstance(state_raw, bool):
            state = "on" if state_raw else "off"
        elif isinstance(state_raw, str):
            candidate = state_raw.strip().lower()
            if candidate in ("on", "off"):
                state = candidate

        duty_pct = None
        if action == "set_state":
            if state is None:
                return jsonify({"error": "state required"}), 400
        else:
            if duty_raw is None:
                return jsonify({"error": "duty_pct required"}), 400
            try:
                duty_pct = float(duty_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "invalid duty_pct"}), 400
            if duty_pct < 0 or duty_pct > 100:
                return jsonify({"error": "duty_pct out of range"}), 400
            state = "on" if duty_pct > 0 else "off"

        if app_state.estop:
            return jsonify({"error": "E-STOP active"}), 403
        if app_state.safe_mode:
            return jsonify({"error": "SAFE MODE active"}), 403

        ttl_raw = payload.get("ttl_s")
        ttl_s = None
        if ttl_raw is not None:
            try:
                ttl_s = int(ttl_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "invalid ttl_s"}), 400
            if ttl_s < 0:
                return jsonify({"error": "invalid ttl_s"}), 400

        cmd_id, queue_size, dropped = _enqueue_node_command(
            node_id,
            {
                "actuator_id": actuator_id,
                "action": action,
                "state": state,
                "duty_pct": duty_pct,
                "ttl_s": ttl_s,
            },
        )
        response = {"ok": True, "cmd_id": cmd_id, "queue_size": queue_size}
        if dropped:
            response["dropped"] = dropped
        return jsonify(response)

    node_id = str(request.args.get("node_id") or "").strip()
    if not node_id:
        return jsonify({"error": "node_id required"}), 400
    auth_error = _require_node_auth(node_id)
    if auth_error:
        return auth_error
    if _rate_limit_node_commands(node_id):
        return jsonify({"error": "rate_limited"}), 429
    if app_state.estop or app_state.safe_mode:
        _clear_all_node_command_queues("estop_active" if app_state.estop else "safe_mode_active")
        return "", 204
    since_raw = request.args.get("since")
    since_ts = _parse_ts_param(since_raw)
    if since_raw and since_ts is None:
        return jsonify({"error": "invalid since timestamp"}), 400
    if since_ts is None:
        window = NODE_COMMAND_DEFAULT_TTL_SECONDS if NODE_COMMAND_DEFAULT_TTL_SECONDS > 0 else 30
        since_ts = time.time() - window
    commands = _snapshot_node_commands(node_id, since_ts)
    if not commands:
        return "", 204
    return jsonify({"commands": commands})


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


@app.route("/api/trends")
def api_trends() -> Any:
    metric = (request.args.get("metric") or "").strip().lower()
    zone = (request.args.get("zone") or "").strip()
    hours_raw = request.args.get("hours", "6")
    max_points_raw = request.args.get("max_points")
    format_raw = (request.args.get("format") or "").strip().lower()
    summary_raw = (request.args.get("summary") or "").strip().lower()
    summary_mode = summary_raw in ("1", "true", "yes")
    try:
        hours = int(hours_raw)
    except ValueError:
        return jsonify({"error": "hours must be integer"}), 400
    hours = max(1, min(hours, 168))
    if summary_mode:
        max_points = 0
    elif max_points_raw is None or max_points_raw == "":
        max_points = 0 if format_raw == "csv" else TREND_MAX_POINTS_DEFAULT
    else:
        try:
            max_points = int(max_points_raw)
        except ValueError:
            return jsonify({"error": "max_points must be integer"}), 400
        max_points = max(1, min(max_points, TREND_MAX_POINTS_LIMIT))

    metric_map = {
        "temp_c": "dht_temp",
        "rh_pct": "dht_hum",
        "lux": "lux",
        "soil_raw": "soil_ch0",
    }
    if not metric:
        return jsonify({"error": "metric is required", "allowed": sorted(metric_map)}), 400
    if metric not in metric_map:
        return jsonify({"error": "invalid metric", "allowed": sorted(metric_map)}), 400

    to_ts = time.time()
    from_ts = to_ts - hours * 3600
    if summary_mode:
        summary = {
            "zone": zone or None,
            "metric": metric,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "count": 0,
            "min": None,
            "max": None,
            "last": None,
            "last_ts": None,
            "source": None,
        }
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if zone:
            cur.execute(
                """
                SELECT MIN(value), MAX(value), COUNT(value)
                FROM telemetry_log
                WHERE zone = ? AND metric = ? AND ts >= ? AND ts <= ? AND value IS NOT NULL
                """,
                (zone, metric, from_ts, to_ts),
            )
            min_val, max_val, count_val = cur.fetchone() or (None, None, 0)
            count_val = int(count_val or 0)
            if count_val > 0:
                cur.execute(
                    """
                    SELECT ts, value
                    FROM telemetry_log
                    WHERE zone = ? AND metric = ? AND ts >= ? AND ts <= ? AND value IS NOT NULL
                    ORDER BY ts DESC LIMIT 1
                    """,
                    (zone, metric, from_ts, to_ts),
                )
                last_row = cur.fetchone()
                if last_row:
                    summary["last_ts"] = last_row[0]
                    summary["last"] = last_row[1]
                summary["min"] = min_val
                summary["max"] = max_val
                summary["count"] = count_val
                summary["source"] = "telemetry"
        if summary["count"] == 0 and (not zone or zone.lower() == "sera"):
            column = metric_map[metric]
            cur.execute(
                f"""
                SELECT MIN({column}), MAX({column}), COUNT({column})
                FROM sensor_log
                WHERE ts >= ? AND ts <= ? AND {column} IS NOT NULL
                """,
                (from_ts, to_ts),
            )
            min_val, max_val, count_val = cur.fetchone() or (None, None, 0)
            count_val = int(count_val or 0)
            if count_val > 0:
                cur.execute(
                    f"""
                    SELECT ts, {column}
                    FROM sensor_log
                    WHERE ts >= ? AND ts <= ? AND {column} IS NOT NULL
                    ORDER BY ts DESC LIMIT 1
                    """,
                    (from_ts, to_ts),
                )
                last_row = cur.fetchone()
                if last_row:
                    summary["last_ts"] = last_row[0]
                    summary["last"] = last_row[1]
                summary["min"] = min_val
                summary["max"] = max_val
                summary["count"] = count_val
                summary["source"] = "sensor_log"
        conn.close()
        return jsonify(summary)
    points: List[List[float]] = []
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if zone:
        cur.execute(
            """
            SELECT ts, value
            FROM telemetry_log
            WHERE zone = ? AND metric = ? AND ts >= ? AND ts <= ?
            ORDER BY ts ASC
            """,
            (zone, metric, from_ts, to_ts),
        )
        rows = cur.fetchall()
        points = [[row[0], row[1]] for row in rows if row[1] is not None]
    if not points and (not zone or zone.lower() == "sera"):
        column = metric_map[metric]
        cur.execute(
            f"SELECT ts, {column} FROM sensor_log WHERE ts >= ? AND ts <= ? ORDER BY ts ASC",
            (from_ts, to_ts),
        )
        rows = cur.fetchall()
        points = [[row[0], row[1]] for row in rows if row[1] is not None]
    conn.close()
    points = _downsample_points(points, max_points)
    if format_raw == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ts", metric])
        writer.writerows(points)
        zone_part = zone or "sera"
        filename = f"trends_{zone_part}_{metric}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    return jsonify({
        "zone": zone or None,
        "metric": metric,
        "from_ts": from_ts,
        "to_ts": to_ts,
        "points": points,
    })


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


def _csv_response(filename: str, headers_row: List[str], rows: List[List[Any]]) -> Response:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers_row)
    for row in rows:
        writer.writerow(row)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/api/reports/daily")
def api_reports_daily() -> Any:
    cfg = load_reporting_config()
    tz = ZoneInfo(cfg.get("SERA_TZ", "Europe/Istanbul"))
    date_raw = request.args.get("date")
    profile = request.args.get("profile")
    target_date = _parse_report_date(date_raw, tz)
    if date_raw and target_date is None:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400
    if target_date is None:
        target_date = _default_report_date(cfg)
    report = build_daily_report(target_date, profile, cfg)
    return jsonify(report)


@app.route("/api/reports/daily.csv")
def api_reports_daily_csv() -> Any:
    cfg = load_reporting_config()
    tz = ZoneInfo(cfg.get("SERA_TZ", "Europe/Istanbul"))
    date_raw = request.args.get("date")
    profile = request.args.get("profile")
    target_date = _parse_report_date(date_raw, tz)
    if date_raw and target_date is None:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400
    if target_date is None:
        target_date = _default_report_date(cfg)
    report = build_daily_report(target_date, profile, cfg)
    headers_row = [
        "time",
        "lux",
        "temp_in",
        "hum_in",
        "dew_point",
        "dew_margin",
        "vpd",
        "temp_out",
        "hum_out",
        "shortwave",
        "gti",
        "cloud_cover",
        "temp_delta",
    ]
    rows = []
    for entry in report.get("hourly", []):
        rows.append([
            entry.get("time"),
            entry.get("lux"),
            entry.get("temp_in"),
            entry.get("hum_in"),
            entry.get("dew_point"),
            entry.get("dew_margin"),
            entry.get("vpd"),
            entry.get("temp_out"),
            entry.get("hum_out"),
            entry.get("shortwave"),
            entry.get("gti"),
            entry.get("cloud_cover"),
            entry.get("temp_delta"),
        ])
    return _csv_response(f"daily_report_{target_date.isoformat()}.csv", headers_row, rows)


@app.route("/api/reports/weekly")
def api_reports_weekly() -> Any:
    cfg = load_reporting_config()
    tz = ZoneInfo(cfg.get("SERA_TZ", "Europe/Istanbul"))
    end_raw = request.args.get("end")
    profile = request.args.get("profile")
    end_date = _parse_report_date(end_raw, tz)
    if end_raw and end_date is None:
        return jsonify({"error": "end must be YYYY-MM-DD"}), 400
    if end_date is None:
        end_date = _default_report_date(cfg)
    report = build_weekly_report(end_date, profile, cfg)
    return jsonify(report)


@app.route("/api/reports/weekly.csv")
def api_reports_weekly_csv() -> Any:
    cfg = load_reporting_config()
    tz = ZoneInfo(cfg.get("SERA_TZ", "Europe/Istanbul"))
    end_raw = request.args.get("end")
    profile = request.args.get("profile")
    end_date = _parse_report_date(end_raw, tz)
    if end_raw and end_date is None:
        return jsonify({"error": "end must be YYYY-MM-DD"}), 400
    if end_date is None:
        end_date = _default_report_date(cfg)
    report = build_weekly_report(end_date, profile, cfg)
    headers_row = [
        "date",
        "light_dose_lux_hours",
        "daylight_hours",
        "temp_min",
        "temp_max",
        "temp_ok_hours",
        "vpd_ok_hours",
        "dew_high_hours",
        "stress_hours",
        "gdd",
        "coverage_note",
    ]
    rows: List[List[Any]] = []
    for day in report.get("days", []):
        rows.append([
            day.get("date"),
            day.get("indoor", {}).get("light", {}).get("light_dose_lux_hours"),
            day.get("indoor", {}).get("light", {}).get("daylight_hours"),
            day.get("indoor", {}).get("temperature", {}).get("min"),
            day.get("indoor", {}).get("temperature", {}).get("max"),
            day.get("indoor", {}).get("temperature", {}).get("ok_hours"),
            day.get("indoor", {}).get("vpd", {}).get("ok_hours"),
            day.get("indoor", {}).get("dewpoint_margin", {}).get("high_risk_hours"),
            day.get("plants", {}).get("stress_hours"),
            day.get("plants", {}).get("gdd"),
            day.get("coverage", {}).get("note"),
        ])
    return _csv_response(f"weekly_report_{report.get('start_date')}_{report.get('end_date')}.csv", headers_row, rows)


@app.route("/api/reports/explainers")
def api_reports_explainers() -> Any:
    return jsonify({"items": explainers_catalog()})


@app.route("/api/actuator/<name>", methods=["POST"])
def api_actuator(name: str) -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    payload = request.get_json(force=True, silent=True) or {}
    seconds = payload.get("seconds")
    desired_state = payload.get("state")
    duty_raw = payload.get("duty_pct")
    state = None
    if isinstance(desired_state, bool):
        state = "on" if desired_state else "off"
    elif isinstance(desired_state, str):
        candidate = desired_state.strip().lower()
        if candidate in ("on", "off"):
            state = candidate
    duty_pct = None
    if duty_raw is not None:
        try:
            duty_pct = float(duty_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "invalid duty_pct"}), 400
        if duty_pct < 0 or duty_pct > 100:
            return jsonify({"error": "duty_pct out of range"}), 400

    meta = _find_catalog_actuator(name)
    backend = str(meta.get("backend") or "").lower() if meta else ""
    supports_pwm = bool(meta.get("supports_pwm")) if meta else False
    if duty_pct is not None:
        if not meta or not supports_pwm:
            return jsonify({"error": "duty_pct not supported"}), 400
        if state == "off" and duty_pct > 0:
            return jsonify({"error": "state conflicts with duty_pct"}), 400
        if state == "on" and duty_pct == 0:
            return jsonify({"error": "state conflicts with duty_pct"}), 400
        if backend and backend != "esp32":
            return jsonify({"error": "duty_pct backend not supported"}), 400

    if meta and backend == "esp32":
        if app_state.estop:
            return jsonify({"error": "E-STOP active"}), 403
        if app_state.safe_mode:
            return jsonify({"error": "SAFE MODE active"}), 403
        if seconds is not None:
            return jsonify({"error": "seconds not supported for esp32"}), 400
        node_id = str(meta.get("node_id") or "").strip()
        if not node_id:
            return jsonify({"error": "node_id required"}), 400
        actuator_id = str(meta.get("id") or name).strip()
        action = "set_state"
        if duty_pct is not None:
            action = "set_pwm"
            state = "on" if duty_pct > 0 else "off"
        if action == "set_state" and state is None:
            return jsonify({"error": "state must be 'on' or 'off'"}), 400
        cmd_id, queue_size, dropped = _enqueue_node_command(
            node_id,
            {
                "actuator_id": actuator_id,
                "action": action,
                "state": state,
                "duty_pct": duty_pct,
            },
        )
        response = {
            "ok": True,
            "queued": True,
            "cmd_id": cmd_id,
            "node_id": node_id,
            "actuator_id": actuator_id,
            "queue_size": queue_size,
        }
        if dropped:
            response["dropped"] = dropped
        return jsonify(response)

    if meta and backend and backend != "pi_gpio":
        return jsonify({"error": "actuator backend not supported"}), 400
    if duty_pct is not None:
        return jsonify({"error": "duty_pct not supported"}), 400
    if state is None:
        return jsonify({"error": "state must be 'on' or 'off'"}), 400
    try:
        apply_actuator_command(name, state == "on", seconds, "manual")
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
    queued = _queue_remote_emergency_stop()
    response = {"ok": True}
    if queued:
        response["remote_queue"] = queued
    return jsonify(response)


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
            "notifications": dict(notifications_config),
            "retention": dict(retention_config),
        })
    payload = request.get_json(force=True, silent=True) or {}
    channels = payload.get("channels")
    limits = payload.get("limits")
    automation = payload.get("automation")
    alerts_config = payload.get("alerts")
    sensors_payload = payload.get("sensors")
    safe_mode = payload.get("safe_mode")
    notifications_payload = payload.get("notifications")
    retention_payload = payload.get("retention")
    if channels:
        errors = validate_channels_payload(channels)
        if errors:
            return jsonify({"error": "invalid channels", "details": errors}), 400
        normalized: List[Dict[str, Any]] = []
        for chan in channels:
            entry = dict(chan)
            if isinstance(entry.get("name"), str):
                entry["name"] = entry["name"].strip().upper()
            normalized.append(entry)
        _write_json_atomic(CHANNEL_CONFIG_PATH, normalized)
        actuator_manager.reload_channels(normalized)
    if limits:
        errors = validate_limits_payload(limits)
        if errors:
            return jsonify({"error": "invalid limits", "details": errors}), 400
        app_state.update_limits(limits)
        save_panel_config_updates(limits=app_state.limits)
    if automation:
        errors = validate_automation_payload(automation)
        if errors:
            return jsonify({"error": "invalid automation", "details": errors}), 400
        automation_engine.config.update(automation)
        save_panel_config_updates(automation=automation_engine.config)
    if alerts_config:
        errors = validate_alerts_payload(alerts_config)
        if errors:
            return jsonify({"error": "invalid alerts", "details": errors}), 400
        app_state.update_alerts(alerts_config)
        save_panel_config_updates(alerts_cfg=app_state.get_alerts_config())
    if sensors_payload:
        errors = validate_sensors_payload(sensors_payload)
        if errors:
            return jsonify({"error": "invalid sensors", "details": errors}), 400
        sensors_config.update(sensors_payload)
        _write_json_atomic(SENSORS_CONFIG_PATH, sensors_config)
        sensor_manager.reload_config(sensors_config)
        lcd_manager.update_config(sensors_config)
    if notifications_payload:
        errors = validate_notifications_payload(notifications_payload)
        if errors:
            return jsonify({"error": "invalid notifications", "details": errors}), 400
        save_notifications_config_updates(notifications_payload)
    if retention_payload:
        errors = validate_retention_payload(retention_payload)
        if errors:
            return jsonify({"error": "invalid retention", "details": errors}), 400
        save_retention_config_updates(retention_payload)
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
    notifications_payload = payload.get("notifications")
    retention_payload = payload.get("retention")
    if safe_mode is not None:
        app_state.toggle_safe_mode(bool(safe_mode))
    if limits:
        errors = validate_limits_payload(limits)
        if errors:
            return jsonify({"error": "invalid limits", "details": errors}), 400
        app_state.update_limits(limits)
        save_panel_config_updates(limits=app_state.limits)
    if automation:
        errors = validate_automation_payload(automation)
        if errors:
            return jsonify({"error": "invalid automation", "details": errors}), 400
        automation_engine.config.update(automation)
        save_panel_config_updates(automation=automation_engine.config)
    if alerts_config:
        errors = validate_alerts_payload(alerts_config)
        if errors:
            return jsonify({"error": "invalid alerts", "details": errors}), 400
        app_state.update_alerts(alerts_config)
        save_panel_config_updates(alerts_cfg=app_state.get_alerts_config())
    if notifications_payload:
        errors = validate_notifications_payload(notifications_payload)
        if errors:
            return jsonify({"error": "invalid notifications", "details": errors}), 400
        save_notifications_config_updates(notifications_payload)
    if retention_payload:
        errors = validate_retention_payload(retention_payload)
        if errors:
            return jsonify({"error": "invalid retention", "details": errors}), 400
        save_retention_config_updates(retention_payload)
    return jsonify({"ok": True})


@app.route("/api/automation/override", methods=["POST"])
def api_automation_override() -> Any:
    admin_error = require_admin()
    if admin_error:
        return admin_error
    payload = request.get_json(force=True, silent=True) or {}
    scope = str(payload.get("scope") or "").strip().lower()
    action = str(payload.get("action") or "clear").strip().lower()
    if action not in ("clear", "cancel"):
        return jsonify({"error": "invalid action"}), 400
    if scope not in ("lux", "light", "fan", "heater", "pump", "all"):
        return jsonify({"error": "invalid scope"}), 400
    cleared = automation_engine.clear_manual_override(scope)
    return jsonify({"ok": True, "cleared": cleared})


@app.route("/api/lcd", methods=["GET", "POST"])
def api_lcd() -> Any:
    if request.method == "GET":
        return jsonify({
            "lcd": lcd_manager.status(),
            "config": {
                "lcd_enabled": sensors_config.get("lcd_enabled", True),
                "lcd_addr": sensors_config.get("lcd_addr", "0x3F"),
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
    mode = str(sensors_config.get("lcd_mode", "auto"))
    if isinstance(lines, list):
        sanitized_lines = [str(x) if x is not None else "" for x in lines]
        sensors_config["lcd_lines"] = sanitized_lines
        if mode == "manual":
            lcd_manager.set_manual_lines(sanitized_lines)
        elif mode == "template":
            latest = sensor_manager.latest()
            data_for_template = api_status_payload(latest.get("readings", {}))
            lcd_manager.set_template_lines(sanitized_lines, data_for_template)
        with SENSORS_CONFIG_PATH.open("w") as f:
            json.dump(sensors_config, f, indent=2)
    return jsonify({"ok": True, "lcd": lcd_manager.status()})


@app.route("/notes")
def notes_page() -> Any:
    note_groups = [
        {
            "title": "Güvenlik",
            "summary": "Erişim ve gizli anahtarlar",
            "items_list": [
                "ADMIN_TOKEN default olarak 'changeme' ile geliyor; güçlü bir değerle değiştir ve UI'dan girilebilmesi için ayar eklemeyi planla.",
                "Servis şu anda Flask dev server ile çalışıyor; prod için gunicorn + reverse proxy (Nginx/Caddy) kullan, yalnızca yerel ağdan erişim varsa firewall kuralı ekle.",
            ],
        },
        {
            "title": "Dayanıklılık",
            "summary": "Servis ve sensör sağlığı",
            "items_list": [
                "Tek process çalışıyor; gunicorn ile en az 2 worker + health check (systemd watchdog veya /health) ekle.",
                "Sensör döngüsü hata aldığında sadece alert kaydı var; disk loguna detay yaz ve alert'i UI'da daha görünür göster.",
            ],
        },
        {
            "title": "Kullanılabilirlik",
            "summary": "Kontrol ve otomasyon deneyimi",
            "items_list": [
                "Kontrol sayfası için 'son yapılan işlemler' kısa listesi (pompa/ışık ne zaman açıldı) ekle.",
                "LCD şablonlarına tarih, veri yaşı {data_age} ve fan gibi ek röleler için token desteği eklenebilir.",
            ],
        },
        {
            "title": "Gözlemlenebilirlik",
            "summary": "Log ve metrikler",
            "items_list": [
                "sensor_logs için basit bir log rotasyonu ekle (gün/hafta dosyaları) ve UI'da indirme filtrelerine 'bugün' kısayolu ekle.",
                "Aktüatör state değişimlerini (kim, ne zaman, sebep) sqlite'a kaydet; böylece geçmiş kontrol edilebilir.",
            ],
        },
    ]
    base_template = "base_v1.html" if USE_NEW_UI else "base.html"
    return render_template("notes.html", notes=note_groups, base_template=base_template)


# Templates for testing convenience
@app.route("/health")
def health() -> Any:
    return jsonify({"ok": True, "simulation": SIMULATION_MODE})


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=SIMULATION_MODE)
