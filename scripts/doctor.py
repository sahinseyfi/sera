#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class Issue:
    level: str
    message: str
    path: str | None = None

    def format(self) -> str:
        prefix = f"[{self.level}]"
        if self.path:
            return f"{prefix} {self.path}: {self.message}"
        return f"{prefix} {self.message}"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path, issues: list[Issue]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        issues.append(Issue("ERROR", "Dosya bulunamadı.", str(path)))
    except json.JSONDecodeError as exc:
        issues.append(Issue("ERROR", f"JSON parse hatası: {exc}", str(path)))
    except Exception as exc:
        issues.append(Issue("ERROR", f"Okuma hatası: {exc}", str(path)))
    return None


def _parse_hex_addr(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value.startswith(("0x", "0X")):
        return None
    try:
        return int(value, 16)
    except ValueError:
        return None


_HHMM_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _is_hhmm(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_HHMM_RE.match(value.strip()))


def _schema_validate(instance: Any, schema_path: Path, issues: list[Issue]) -> None:
    try:
        import jsonschema
    except Exception:
        issues.append(
            Issue(
                "WARN",
                "jsonschema kurulu değil; şema doğrulaması atlandı (pip install -r requirements.txt).",
                str(schema_path),
            )
        )
        return

    schema = _load_json(schema_path, issues)
    if schema is None:
        return

    try:
        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)
        for err in sorted(validator.iter_errors(instance), key=str):
            loc = ".".join(str(p) for p in err.path) if err.path else ""
            msg = f"{err.message}"
            issues.append(Issue("ERROR", f"Şema hatası{f' ({loc})' if loc else ''}: {msg}", str(schema_path)))
    except Exception as exc:
        issues.append(Issue("ERROR", f"Şema doğrulama hatası: {exc}", str(schema_path)))


def _validate_channels(cfg: Any, issues: list[Issue]) -> None:
    if not isinstance(cfg, list):
        issues.append(Issue("ERROR", "channels.json bir liste (array) olmalı."))
        return

    seen_names: set[str] = set()
    seen_pins: set[int] = set()
    valid_roles = {"heater", "fan", "pump", "light", "other"}

    for i, ch in enumerate(cfg):
        where = f"channels[{i}]"
        if not isinstance(ch, dict):
            issues.append(Issue("ERROR", "Kanal kaydı object olmalı.", where))
            continue

        name = ch.get("name")
        gpio_pin = ch.get("gpio_pin")
        active_low = ch.get("active_low")

        if not isinstance(name, str) or not name.strip():
            issues.append(Issue("ERROR", "name zorunlu (string).", where))
        else:
            if name in seen_names:
                issues.append(Issue("ERROR", f"name tekrarı: {name}", where))
            seen_names.add(name)
            if any(c.isspace() for c in name):
                issues.append(Issue("WARN", "name boşluk içermemeli.", where))

        if not isinstance(gpio_pin, int):
            issues.append(Issue("ERROR", "gpio_pin zorunlu (int).", where))
        else:
            if gpio_pin in seen_pins:
                issues.append(Issue("ERROR", f"gpio_pin tekrarı: {gpio_pin}", where))
            seen_pins.add(gpio_pin)
            if not (0 <= gpio_pin <= 27):
                issues.append(Issue("WARN", f"gpio_pin aralığı şüpheli: {gpio_pin} (0-27 beklenir).", where))

        if not isinstance(active_low, bool):
            issues.append(Issue("ERROR", "active_low zorunlu (bool).", where))

        role = ch.get("role")
        if role is not None and (not isinstance(role, str) or role not in valid_roles):
            issues.append(Issue("WARN", f"role beklenenlerden değil: {role!r}", where))


def _validate_sensors(cfg: Any, issues: list[Issue]) -> None:
    if not isinstance(cfg, dict):
        issues.append(Issue("ERROR", "sensors.json bir object olmalı."))
        return

    for key in ("bh1750_addr", "ads1115_addr", "lcd_addr"):
        if key in cfg:
            parsed = _parse_hex_addr(cfg.get(key))
            if parsed is None:
                issues.append(Issue("ERROR", f"{key} '0x..' formatında olmalı.", f"sensors.{key}"))

    if "dht22_gpio" in cfg and not isinstance(cfg.get("dht22_gpio"), int):
        issues.append(Issue("ERROR", "dht22_gpio int olmalı.", "sensors.dht22_gpio"))

    lcd_enabled = cfg.get("lcd_enabled")
    lcd_rows = cfg.get("lcd_rows")
    lcd_lines = cfg.get("lcd_lines")
    if lcd_enabled is True and isinstance(lcd_rows, int) and isinstance(lcd_lines, list):
        if len(lcd_lines) != lcd_rows:
            issues.append(
                Issue(
                    "WARN",
                    f"lcd_rows={lcd_rows} ama lcd_lines uzunluğu {len(lcd_lines)}.",
                    "sensors.lcd_lines",
                )
            )


def _validate_notifications(cfg: Any, issues: list[Issue]) -> None:
    if not isinstance(cfg, dict):
        issues.append(Issue("ERROR", "notifications.json bir object olmalı."))
        return

    level = cfg.get("level")
    if level is not None and level not in {"debug", "info", "warning", "error"}:
        issues.append(Issue("WARN", f"level beklenenlerden değil: {level!r}", "notifications.level"))


def _validate_panel(cfg: Any, issues: list[Issue]) -> None:
    if not isinstance(cfg, dict):
        issues.append(Issue("ERROR", "panel.json bir object olmalı."))
        return

    limits = cfg.get("limits")
    if limits is not None and not isinstance(limits, dict):
        issues.append(Issue("ERROR", "limits object olmalı.", "panel.limits"))
    elif isinstance(limits, dict):
        for key in (
            "pump_max_seconds",
            "pump_cooldown_seconds",
            "heater_max_seconds",
            "heater_cutoff_temp",
            "energy_kwh_low",
            "energy_kwh_high",
            "energy_kwh_threshold",
        ):
            val = limits.get(key)
            if val is None:
                continue
            if not isinstance(val, (int, float)):
                issues.append(Issue("ERROR", f"{key} sayı olmalı.", f"panel.limits.{key}"))
                continue
            if float(val) < 0:
                issues.append(Issue("ERROR", f"{key} negatif olamaz.", f"panel.limits.{key}"))

    alerts = cfg.get("alerts")
    if alerts is not None and not isinstance(alerts, dict):
        issues.append(Issue("ERROR", "alerts object olmalı.", "panel.alerts"))
    elif isinstance(alerts, dict):
        for key in ("temp_high_c", "temp_low_c", "hum_high_pct", "hum_low_pct"):
            val = alerts.get(key)
            if val is None:
                continue
            if not isinstance(val, (int, float)):
                issues.append(Issue("ERROR", f"{key} sayı olmalı.", f"panel.alerts.{key}"))
        offline = alerts.get("sensor_offline_minutes")
        if offline is not None and (not isinstance(offline, int) or offline < 0):
            issues.append(Issue("ERROR", "sensor_offline_minutes int ve >=0 olmalı.", "panel.alerts.sensor_offline_minutes"))

    automation = cfg.get("automation")
    if automation is not None and not isinstance(automation, dict):
        issues.append(Issue("ERROR", "automation object olmalı.", "panel.automation"))
    elif isinstance(automation, dict):
        time_fields = (
            "window_start",
            "window_end",
            "reset_time",
            "fan_night_start",
            "fan_night_end",
            "heater_night_start",
            "heater_night_end",
            "pump_window_start",
            "pump_window_end",
        )
        for key in time_fields:
            if key in automation and not _is_hhmm(automation.get(key)):
                issues.append(Issue("ERROR", "Saat HH:MM formatında olmalı.", f"panel.automation.{key}"))

        heater_sensor = automation.get("heater_sensor")
        if heater_sensor is not None and heater_sensor not in {"dht22", "ds18b20"}:
            issues.append(Issue("WARN", f"heater_sensor beklenenlerden değil: {heater_sensor!r}", "panel.automation.heater_sensor"))

        pump_soil = automation.get("pump_soil_channel")
        if pump_soil is not None and pump_soil not in {"ch0", "ch1", "ch2", "ch3"}:
            issues.append(Issue("WARN", f"pump_soil_channel beklenenlerden değil: {pump_soil!r}", "panel.automation.pump_soil_channel"))

        calib = automation.get("soil_calibration")
        if calib is not None and not isinstance(calib, dict):
            issues.append(Issue("ERROR", "soil_calibration object olmalı.", "panel.automation.soil_calibration"))
        elif isinstance(calib, dict):
            for ch, entry in calib.items():
                if not isinstance(entry, dict):
                    issues.append(Issue("ERROR", "Kalibrasyon kaydı object olmalı.", f"panel.automation.soil_calibration.{ch}"))
                    continue
                for key in ("dry", "wet"):
                    val = entry.get(key)
                    if val is None:
                        continue
                    if not isinstance(val, (int, float)):
                        issues.append(Issue("ERROR", f"{key} sayı veya null olmalı.", f"panel.automation.soil_calibration.{ch}.{key}"))


def _validate_retention(cfg: Any, issues: list[Issue], repo_root: Path) -> None:
    if not isinstance(cfg, dict):
        issues.append(Issue("ERROR", "retention.json bir object olmalı."))
        return

    for key in ("sensor_log_days", "event_log_days", "actuator_log_days"):
        val = cfg.get(key)
        if isinstance(val, int):
            if val < 0:
                issues.append(Issue("ERROR", f"{key} negatif olamaz.", f"retention.{key}"))
        elif val is not None:
            issues.append(Issue("ERROR", f"{key} int olmalı.", f"retention.{key}"))

    archive_enabled = cfg.get("archive_enabled")
    archive_dir = cfg.get("archive_dir")
    if archive_enabled is True and isinstance(archive_dir, str) and archive_dir.strip():
        path = (repo_root / archive_dir).resolve()
        if not path.exists():
            issues.append(Issue("WARN", f"archive_dir mevcut değil: {archive_dir}", "retention.archive_dir"))


def _validate_reporting(cfg: Any, issues: list[Issue]) -> None:
    if not isinstance(cfg, dict):
        issues.append(Issue("ERROR", "reporting.json bir object olmalı."))
        return

    active = cfg.get("ACTIVE_PROFILE")
    profiles = cfg.get("PLANT_PROFILES")
    if isinstance(active, str) and isinstance(profiles, dict):
        if active not in profiles:
            issues.append(Issue("WARN", f"ACTIVE_PROFILE profiller içinde yok: {active!r}", "reporting.ACTIVE_PROFILE"))


def _validate_updates(cfg: Any, issues: list[Issue]) -> None:
    if not isinstance(cfg, list):
        issues.append(Issue("ERROR", "updates.json bir liste (array) olmalı."))
        return

    for i, item in enumerate(cfg):
        where = f"updates[{i}]"
        if not isinstance(item, dict):
            issues.append(Issue("ERROR", "Update kaydı object olmalı.", where))
            continue

        for req in ("date", "title", "summary", "details"):
            if req not in item:
                issues.append(Issue("ERROR", f"{req} zorunlu.", where))

        d = item.get("date")
        if isinstance(d, str):
            try:
                date.fromisoformat(d)
            except ValueError:
                issues.append(Issue("ERROR", f"Tarih ISO formatında olmalı (YYYY-MM-DD): {d!r}", f"{where}.date"))
        elif d is not None:
            issues.append(Issue("ERROR", "date string olmalı.", f"{where}.date"))

        details = item.get("details")
        if isinstance(details, list):
            if not all(isinstance(x, str) for x in details):
                issues.append(Issue("ERROR", "details sadece string elemanlar içermeli.", f"{where}.details"))
        elif details is not None:
            issues.append(Issue("ERROR", "details liste olmalı.", f"{where}.details"))


def main() -> int:
    parser = argparse.ArgumentParser(description="AKILLI SERA repo hızlı doğrulama (config + şema).")
    parser.add_argument("--strict", action="store_true", help="Uyarıları da hata gibi değerlendir.")
    args = parser.parse_args()

    repo_root = _repo_root()
    config_dir = repo_root / "config"
    schema_dir = config_dir / "schema"

    config_files = {
        "channels.json": ("channels.schema.json", _validate_channels),
        "sensors.json": ("sensors.schema.json", _validate_sensors),
        "panel.json": ("panel.schema.json", _validate_panel),
        "notifications.json": ("notifications.schema.json", _validate_notifications),
        "retention.json": ("retention.schema.json", lambda cfg, iss: _validate_retention(cfg, iss, repo_root)),
        "reporting.json": ("reporting.schema.json", _validate_reporting),
        "updates.json": ("updates.schema.json", _validate_updates),
    }

    issues: list[Issue] = []

    for filename, (schema_name, custom_validator) in config_files.items():
        path = config_dir / filename
        cfg = _load_json(path, issues)
        if cfg is None:
            continue

        schema_path = schema_dir / schema_name
        if schema_path.exists():
            _schema_validate(cfg, schema_path, issues)
        else:
            issues.append(Issue("WARN", "Şema dosyası yok (schema validation atlandı).", str(schema_path)))

        try:
            custom_validator(cfg, issues)
        except Exception as exc:
            issues.append(Issue("ERROR", f"Özel doğrulama çöktü: {exc}", filename))

    errors = [i for i in issues if i.level == "ERROR"]
    warns = [i for i in issues if i.level == "WARN"]

    for issue in issues:
        print(issue.format())

    if not issues:
        print("[OK] Her şey temiz.")

    if errors:
        print(f"[FAIL] {len(errors)} hata, {len(warns)} uyarı.")
        return 1

    if args.strict and warns:
        print(f"[FAIL] strict mod: {len(warns)} uyarı hata sayıldı.")
        return 1

    print(f"[OK] {len(warns)} uyarı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
