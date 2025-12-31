#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", value.lower())
    cleaned = cleaned.strip("-")
    return cleaned or "item"


def _build_actuators(channels: list[dict[str, Any]], zone_id: str) -> list[dict[str, Any]]:
    actuators: list[dict[str, Any]] = []
    for entry in channels:
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        label = str(entry.get("description") or "").strip() or name
        role = str(entry.get("role") or "other").strip().lower()
        actuator = {
            "id": _slugify(name),
            "label": label,
            "zone": zone_id,
            "role": role,
            "backend": "pi_gpio",
            "gpio_pin": entry.get("gpio_pin"),
            "active_low": bool(entry.get("active_low", False)),
        }
        for key in ("power_w", "quantity", "voltage_v", "notes", "description", "safe_default"):
            if key in entry:
                actuator[key] = entry[key]
        actuators.append(actuator)
    return actuators


def _add_sensor(
    sensors: list[dict[str, Any]],
    sensor_id: str,
    label: str,
    zone: str,
    kind: str,
    purpose: str,
    **kwargs: Any,
) -> None:
    payload: dict[str, Any] = {
        "id": sensor_id,
        "label": label,
        "zone": zone,
        "kind": kind,
        "purpose": purpose,
    }
    payload.update({k: v for k, v in kwargs.items() if v is not None})
    sensors.append(payload)


def _build_sensors(sensors_cfg: dict[str, Any], zone_id: str) -> list[dict[str, Any]]:
    sensors: list[dict[str, Any]] = []
    if "dht22_gpio" in sensors_cfg:
        _add_sensor(
            sensors,
            f"{zone_id}-dht22",
            f"{zone_id.upper()} DHT22",
            zone_id,
            "dht22",
            "temp_hum",
            gpio=sensors_cfg.get("dht22_gpio"),
        )
    ds_enabled = sensors_cfg.get("ds18b20_enabled", True)
    if ds_enabled:
        _add_sensor(
            sensors,
            f"{zone_id}-ds18b20",
            f"{zone_id.upper()} DS18B20",
            zone_id,
            "ds18b20",
            "temp",
        )
    if "bh1750_addr" in sensors_cfg:
        _add_sensor(
            sensors,
            f"{zone_id}-bh1750",
            f"{zone_id.upper()} BH1750",
            zone_id,
            "bh1750",
            "lux",
            i2c_addr=sensors_cfg.get("bh1750_addr"),
        )
    if "ads1115_addr" in sensors_cfg:
        for ch in ("ch0", "ch1", "ch2", "ch3"):
            _add_sensor(
                sensors,
                f"{zone_id}-soil-{ch}",
                f"{zone_id.upper()} Soil {ch.upper()}",
                zone_id,
                "ads1115",
                "soil",
                i2c_addr=sensors_cfg.get("ads1115_addr"),
                ads_channel=ch,
            )
    return sensors


def _extract_lcd(sensors_cfg: dict[str, Any]) -> dict[str, Any] | None:
    keys = (
        "lcd_enabled",
        "lcd_addr",
        "lcd_port",
        "lcd_cols",
        "lcd_rows",
        "lcd_expander",
        "lcd_charmap",
        "lcd_mode",
        "lcd_lines",
    )
    lcd = {k: sensors_cfg.get(k) for k in keys if k in sensors_cfg}
    return lcd or None


def _backup_file(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        dest = dest_dir / f"{src.stem}.{stamp}{src.suffix}"
    shutil.copy2(src, dest)
    return dest


def _build_catalog(channels: list[dict[str, Any]], sensors_cfg: dict[str, Any]) -> dict[str, Any]:
    zone_id = "sera"
    catalog: dict[str, Any] = {
        "version": 1,
        "zones": [{"id": zone_id, "label": "SERA"}],
        "sensors": _build_sensors(sensors_cfg, zone_id),
        "actuators": _build_actuators(channels, zone_id),
    }
    lcd = _extract_lcd(sensors_cfg)
    if lcd:
        catalog["lcd"] = lcd
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="channels.json + sensors.json -> catalog.json migrasyonu (dry-run).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="config/catalog.json yaz.")
    mode.add_argument("--dry-run", action="store_true", help="Sadece önizleme (varsayilan).")
    parser.add_argument("--no-backup", action="store_true", help="config/legacy kopyasi alma.")
    args = parser.parse_args()

    repo_root = _repo_root()
    config_dir = repo_root / "config"
    channels_path = config_dir / "channels.json"
    sensors_path = config_dir / "sensors.json"
    catalog_path = config_dir / "catalog.json"

    if not channels_path.exists():
        raise SystemExit(f"channels.json bulunamadi: {channels_path}")
    if not sensors_path.exists():
        raise SystemExit(f"sensors.json bulunamadi: {sensors_path}")

    channels = _load_json(channels_path)
    sensors_cfg = _load_json(sensors_path)
    if not isinstance(channels, list):
        raise SystemExit("channels.json list olmali.")
    if not isinstance(sensors_cfg, dict):
        raise SystemExit("sensors.json object olmali.")

    catalog = _build_catalog(channels, sensors_cfg)
    print(f"catalog: zones={len(catalog['zones'])} sensors={len(catalog['sensors'])} actuators={len(catalog['actuators'])}")

    if args.write:
        if not args.no_backup:
            backup_dir = config_dir / "legacy"
            _backup_file(channels_path, backup_dir)
            _backup_file(sensors_path, backup_dir)
        _write_json_atomic(catalog_path, catalog)
        print(f"wrote: {catalog_path}")
        return 0

    print("dry-run preview:")
    print(json.dumps(catalog, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
