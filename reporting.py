import json
import math
import sqlite3
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "sera.db"
WEATHER_CACHE_DIR = DATA_DIR / "cache" / "weather"
ISTANBUL_TZ = ZoneInfo("Europe/Istanbul")

DEFAULT_LOCATION = {
    "SERA_LAT": 41.1877,
    "SERA_LON": 28.7402,
    "SERA_TZ": "Europe/Istanbul",
}

DEFAULT_ORIENTATION = {
    "SERA_FACADE_AZIMUTH_NORTH_DEG": 144,
    "SERA_FACADE_TILT_DEG": 90,
}

DEFAULT_THRESHOLDS = {
    "LUX_DAYLIGHT_THRESHOLD": 300,
    "LIGHT_TARGET_HOURS": 12,
    "TEMP_OK_MIN": 18,
    "TEMP_OK_MAX": 26,
    "TEMP_STRESS_COLD": 12,
    "TEMP_STRESS_HOT": 32,
    "TEMP_SPIKE_DELTA": 3.5,
    "VPD_OK_MIN": 0.6,
    "VPD_OK_MAX": 1.2,
    "GDD_BASE_C": 10,
    "DEWPOINT_MARGIN_HIGH_RISK_C": 1.5,
    "DEWPOINT_MARGIN_MED_RISK_C": 3.0,
}

DEFAULT_PLANT_PROFILES: Dict[str, Dict[str, Any]] = {
    "general": {
        "label": "Genel",
        "description": "Genel sebze/yeşillik için dengeli aralıklar.",
        "TEMP_OK_MIN": 18,
        "TEMP_OK_MAX": 26,
        "TEMP_STRESS_COLD": 12,
        "TEMP_STRESS_HOT": 32,
        "VPD_OK_MIN": 0.6,
        "VPD_OK_MAX": 1.2,
        "GDD_BASE_C": 10,
        "LUX_DAYLIGHT_THRESHOLD": 300,
    },
    "tomato": {
        "label": "Domates",
        "description": "Sıcağı seven, ışık ihtiyacı yüksek.",
        "TEMP_OK_MIN": 18,
        "TEMP_OK_MAX": 28,
        "TEMP_STRESS_COLD": 10,
        "TEMP_STRESS_HOT": 32,
        "VPD_OK_MIN": 0.8,
        "VPD_OK_MAX": 1.2,
        "GDD_BASE_C": 10,
        "LUX_DAYLIGHT_THRESHOLD": 320,
    },
    "pepper": {
        "label": "Biber",
        "description": "Domates kadar sıcak, biraz daha kuru havayı sever.",
        "TEMP_OK_MIN": 20,
        "TEMP_OK_MAX": 30,
        "TEMP_STRESS_COLD": 12,
        "TEMP_STRESS_HOT": 34,
        "VPD_OK_MIN": 0.9,
        "VPD_OK_MAX": 1.3,
        "GDD_BASE_C": 12,
        "LUX_DAYLIGHT_THRESHOLD": 320,
    },
    "lettuce": {
        "label": "Marul",
        "description": "Serinlik ve düşük VPD ister, çiçeklenmeye karşı hassas.",
        "TEMP_OK_MIN": 15,
        "TEMP_OK_MAX": 24,
        "TEMP_STRESS_COLD": 8,
        "TEMP_STRESS_HOT": 28,
        "VPD_OK_MIN": 0.5,
        "VPD_OK_MAX": 1.0,
        "GDD_BASE_C": 5,
        "LUX_DAYLIGHT_THRESHOLD": 250,
    },
    "basil": {
        "label": "Fesleğen",
        "description": "Ilık ve nemli ortamı sever, soğuğa hassastır.",
        "TEMP_OK_MIN": 18,
        "TEMP_OK_MAX": 30,
        "TEMP_STRESS_COLD": 12,
        "TEMP_STRESS_HOT": 34,
        "VPD_OK_MIN": 0.8,
        "VPD_OK_MAX": 1.2,
        "GDD_BASE_C": 10,
        "LUX_DAYLIGHT_THRESHOLD": 300,
    },
}

DEFAULT_REPORTING_CONFIG: Dict[str, Any] = {
    **DEFAULT_LOCATION,
    **DEFAULT_ORIENTATION,
    **DEFAULT_THRESHOLDS,
    "BEGINNER_MODE_DEFAULT": True,
    "ACTIVE_PROFILE": "general",
    "PLANT_PROFILES": DEFAULT_PLANT_PROFILES,
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def azimuth_from_north_to_open_meteo(azimuth_from_north: float) -> float:
    """Convert azimuth measured clockwise from North to Open-Meteo convention (0=South)."""
    return float(azimuth_from_north) - 180.0


def load_reporting_config() -> Dict[str, Any]:
    CONFIG_DIR.mkdir(exist_ok=True)
    path = CONFIG_DIR / "reporting.json"
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                user_cfg = json.load(f)
        except Exception:
            user_cfg = {}
    else:
        user_cfg = {}
    merged = _deep_merge(DEFAULT_REPORTING_CONFIG, user_cfg)
    changed = (not path.exists()) or merged != user_cfg
    # Fill missing lat/lon with defaults and emit a small note via stdout (UI'ye mesaj eklenir)
    notes: List[str] = []
    if not merged.get("SERA_LAT"):
        merged["SERA_LAT"] = DEFAULT_LOCATION["SERA_LAT"]
        notes.append("SERA_LAT eksikti, varsayılan Arnavutköy değeri kullanıldı.")
    if not merged.get("SERA_LON"):
        merged["SERA_LON"] = DEFAULT_LOCATION["SERA_LON"]
        notes.append("SERA_LON eksikti, varsayılan Arnavutköy değeri kullanıldı.")
    if notes:
        print("[reporting] config düzeltildi:", "; ".join(notes))
    merged.setdefault("PLANT_PROFILES", DEFAULT_PLANT_PROFILES)
    merged.setdefault("ACTIVE_PROFILE", "general")
    merged.setdefault("BEGINNER_MODE_DEFAULT", True)
    if changed:
        with path.open("w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


def _safe_mean(values: Iterable[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return round(mean(vals), 2) if vals else None


def _safe_median(values: Iterable[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return round(median(vals), 2) if vals else None


def _calc_dew_point(temp_c: float, humidity: float) -> Optional[float]:
    try:
        if humidity <= 0:
            return None
        a = 17.27
        b = 237.7
        alpha = ((a * temp_c) / (b + temp_c)) + math.log(humidity / 100.0)
        dp = (b * alpha) / (a - alpha)
        return round(dp, 2)
    except Exception:
        return None


def _calc_vpd(temp_c: float, humidity: float) -> Optional[float]:
    try:
        es = 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
        ea = es * (humidity / 100.0)
        vpd = max(es - ea, 0.0)
        return round(vpd, 3)
    except Exception:
        return None


def _calc_gdd(tmax: Optional[float], tmin: Optional[float], base_c: float) -> float:
    if tmax is None or tmin is None:
        return 0.0
    avg = (tmax + tmin) / 2.0
    return max(0.0, round(avg - base_c, 3))


@dataclass
class SensorSample:
    ts: float
    dt: datetime
    lux: Optional[float]
    temp_c: Optional[float]
    humidity: Optional[float]
    ds_temp_c: Optional[float]
    dew_point_c: Optional[float]
    vpd_kpa: Optional[float]


def _derive_dew_and_vpd(temp: Optional[float], hum: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    if temp is None or hum is None:
        return None, None
    return _calc_dew_point(temp, hum), _calc_vpd(temp, hum)


def load_sensor_samples(start_dt: datetime, end_dt: datetime, tz: ZoneInfo) -> List[SensorSample]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts, dht_temp, dht_hum, ds18_temp, lux
        FROM sensor_log
        WHERE ts >= ? AND ts < ?
        ORDER BY ts ASC
        """,
        (start_dt.timestamp(), end_dt.timestamp()),
    )
    rows = cur.fetchall()
    conn.close()
    samples: List[SensorSample] = []
    for ts, dht_temp, dht_hum, ds_temp, lux in rows:
        temp_val = dht_temp
        hum_val = dht_hum
        dew, vpd = _derive_dew_and_vpd(temp_val, hum_val)
        samples.append(
            SensorSample(
                ts=float(ts),
                dt=datetime.fromtimestamp(ts, tz),
                lux=lux if lux is not None else None,
                temp_c=temp_val if temp_val is not None else None,
                humidity=hum_val if hum_val is not None else None,
                ds_temp_c=ds_temp if ds_temp is not None else None,
                dew_point_c=dew,
                vpd_kpa=vpd,
            )
        )
    return samples


def _prepare_cache_dir() -> None:
    WEATHER_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _split_weather_response(resp: Dict[str, Any], tz: ZoneInfo) -> Dict[date, Dict[str, Any]]:
    per_day: Dict[date, Dict[str, Any]] = {}
    hourly = resp.get("hourly") or {}
    times = hourly.get("time") or []
    hourly_fields = {k: v for k, v in hourly.items() if k != "time"}
    for idx, ts in enumerate(times):
        dt_obj = datetime.fromtimestamp(ts, tz)
        d = dt_obj.date()
        bucket = per_day.setdefault(d, {"hourly": {"time": []}})
        bucket["hourly"]["time"].append(ts)
        for key, arr in hourly_fields.items():
            bucket["hourly"].setdefault(key, []).append(arr[idx] if idx < len(arr) else None)
    daily = resp.get("daily") or {}
    daily_times = daily.get("time") or []
    for idx, ts in enumerate(daily_times):
        d = datetime.fromtimestamp(ts, tz).date()
        bucket = per_day.setdefault(d, {})
        bucket["daily"] = {k: (v[idx] if idx < len(v) else None) for k, v in daily.items() if k != "time"}
        bucket["daily_ts"] = ts
    return per_day


def fetch_weather(start: date, end: date, config: Dict[str, Any]) -> Dict[date, Dict[str, Any]]:
    tz = ZoneInfo(config.get("SERA_TZ") or DEFAULT_LOCATION["SERA_TZ"])
    lat = float(config.get("SERA_LAT", DEFAULT_LOCATION["SERA_LAT"]))
    lon = float(config.get("SERA_LON", DEFAULT_LOCATION["SERA_LON"]))
    az = azimuth_from_north_to_open_meteo(config.get("SERA_FACADE_AZIMUTH_NORTH_DEG", DEFAULT_ORIENTATION["SERA_FACADE_AZIMUTH_NORTH_DEG"]))
    tilt = float(config.get("SERA_FACADE_TILT_DEG", DEFAULT_ORIENTATION["SERA_FACADE_TILT_DEG"]))
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "timezone": config.get("SERA_TZ", DEFAULT_LOCATION["SERA_TZ"]),
        "timeformat": "unixtime",
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "dew_point_2m",
            "precipitation",
            "cloud_cover",
            "wind_speed_10m",
            "wind_gusts_10m",
            "shortwave_radiation",
            "global_tilted_irradiance",
        ]),
        "daily": "sunrise,sunset",
        "tilt": tilt,
        "azimuth": az,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return _split_weather_response(data, tz)
    except Exception:
        return {}


def load_cached_weather(target_dates: List[date], config: Dict[str, Any]) -> Tuple[Dict[date, Dict[str, Any]], List[date]]:
    _prepare_cache_dir()
    cached: Dict[date, Dict[str, Any]] = {}
    missing: List[date] = []
    for d in target_dates:
        path = WEATHER_CACHE_DIR / f"{d.isoformat()}.json"
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    cached[d] = json.load(f)
                continue
            except Exception:
                path.unlink(missing_ok=True)
        missing.append(d)
    if missing:
        start = min(missing)
        end = max(missing)
        fetched = fetch_weather(start, end, config)
        for d in missing:
            payload = fetched.get(d)
            if payload:
                path = WEATHER_CACHE_DIR / f"{d.isoformat()}.json"
                with path.open("w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False)
                cached[d] = payload
    return cached, missing


def dewpoint_margin(temp: Optional[float], dew: Optional[float]) -> Optional[float]:
    if temp is None or dew is None:
        return None
    return round(temp - dew, 2)


def _as_iso(dt_obj: Optional[datetime]) -> Optional[str]:
    return dt_obj.isoformat() if dt_obj else None


def _hour_bucket(dt_obj: datetime) -> datetime:
    return dt_obj.replace(minute=0, second=0, microsecond=0)


def _summarize_points(points: List[Tuple[datetime, Optional[float]]]) -> Dict[str, Any]:
    values = [(dt, val) for dt, val in points if val is not None]
    if not values:
        return {"min": None, "max": None, "avg": None, "median": None, "min_time": None, "max_time": None}
    nums = [val for _, val in values]
    min_dt, min_val = min(values, key=lambda x: x[1])
    max_dt, max_val = max(values, key=lambda x: x[1])
    return {
        "min": round(min_val, 2),
        "max": round(max_val, 2),
        "avg": _safe_mean(nums),
        "median": _safe_median(nums),
        "min_time": _as_iso(min_dt),
        "max_time": _as_iso(max_dt),
    }


def _profile_thresholds(config: Dict[str, Any], profile_name: Optional[str]) -> Dict[str, Any]:
    thresholds = dict(DEFAULT_THRESHOLDS)
    for key in thresholds.keys():
        if key in config:
            thresholds[key] = config[key]
    profiles = config.get("PLANT_PROFILES") or {}
    profile = profiles.get(profile_name or config.get("ACTIVE_PROFILE") or "general") or {}
    for key, value in profile.items():
        if key in thresholds:
            thresholds[key] = value
    thresholds["profile_name"] = profile_name or config.get("ACTIVE_PROFILE", "general")
    thresholds["profile_label"] = profile.get("label", profile_name or "general")
    thresholds["profile_description"] = profile.get("description", "")
    return thresholds


def _extract_weather_hourly(weather: Dict[str, Any], tz: ZoneInfo) -> Dict[datetime, Dict[str, Any]]:
    out: Dict[datetime, Dict[str, Any]] = {}
    hourly = weather.get("hourly") or {}
    times = hourly.get("time") or []
    for idx, ts in enumerate(times):
        dt_obj = datetime.fromtimestamp(ts, tz)
        bucket = _hour_bucket(dt_obj)
        out[bucket] = {
            "temperature_2m": hourly.get("temperature_2m", [None])[idx] if len(hourly.get("temperature_2m", [])) > idx else None,
            "relative_humidity_2m": hourly.get("relative_humidity_2m", [None])[idx] if len(hourly.get("relative_humidity_2m", [])) > idx else None,
            "dew_point_2m": hourly.get("dew_point_2m", [None])[idx] if len(hourly.get("dew_point_2m", [])) > idx else None,
            "precipitation": hourly.get("precipitation", [None])[idx] if len(hourly.get("precipitation", [])) > idx else None,
            "cloud_cover": hourly.get("cloud_cover", [None])[idx] if len(hourly.get("cloud_cover", [])) > idx else None,
            "wind_speed_10m": hourly.get("wind_speed_10m", [None])[idx] if len(hourly.get("wind_speed_10m", [])) > idx else None,
            "wind_gusts_10m": hourly.get("wind_gusts_10m", [None])[idx] if len(hourly.get("wind_gusts_10m", [])) > idx else None,
            "shortwave_radiation": hourly.get("shortwave_radiation", [None])[idx] if len(hourly.get("shortwave_radiation", [])) > idx else None,
            "global_tilted_irradiance": hourly.get("global_tilted_irradiance", [None])[idx] if len(hourly.get("global_tilted_irradiance", [])) > idx else None,
        }
    return out


def _coverage_note(total_seconds: float) -> Optional[str]:
    full_day = 24 * 3600
    if total_seconds <= 0:
        return "Günlük veri yok."
    ratio = total_seconds / full_day
    if ratio < 0.4:
        return "Veri kapsamı düşük (<%40). Yorumlar sınırlı."
    if ratio < 0.7:
        return "Veri kapsamı orta (>%40)."
    return None


def _status_from_ratio(ratio: float) -> str:
    if ratio >= 0.85:
        return "iyi"
    if ratio >= 0.6:
        return "orta"
    return "dikkat"


def _build_story(temp_ok_ratio: float, light_ratio: float, dew_risk_high_hours: float, worst_margin: Optional[float]) -> List[str]:
    story: List[str] = []
    story.append(f"Sıcaklık hedef aralığında geçen süre: %{int(temp_ok_ratio * 100)}.")
    story.append(f"Işık eşiği üstü süre: %{int(light_ratio * 100)} (proxy aydınlık).")
    if dew_risk_high_hours > 0:
        margin_txt = f" (en düşük marj {worst_margin}°C)" if worst_margin is not None else ""
        story.append(f"Yoğuşma yüksek risk süresi: {dew_risk_high_hours:.2f} saat{margin_txt}.")
    else:
        story.append("Yoğuşma yüksek risk görülmedi.")
    return story


def compute_day_metrics(target_date: date, config: Optional[Dict[str, Any]] = None, profile_name: Optional[str] = None) -> Dict[str, Any]:
    cfg = config or load_reporting_config()
    tz = ZoneInfo(cfg.get("SERA_TZ") or DEFAULT_LOCATION["SERA_TZ"])
    thresholds = _profile_thresholds(cfg, profile_name)
    day_start = datetime.combine(target_date, datetime.min.time(), tz)
    day_end = day_start + timedelta(days=1)

    samples = load_sensor_samples(day_start, day_end, tz)
    weather_map, _ = load_cached_weather([target_date], cfg)
    weather = weather_map.get(target_date) or {}
    weather_hourly = _extract_weather_hourly(weather, tz)

    lux_points: List[Tuple[datetime, Optional[float]]] = []
    temp_points: List[Tuple[datetime, Optional[float]]] = []
    humidity_points: List[Tuple[datetime, Optional[float]]] = []
    dew_points: List[Tuple[datetime, Optional[float]]] = []
    vpd_points: List[Tuple[datetime, Optional[float]]] = []
    margin_points: List[Tuple[datetime, Optional[float]]] = []

    hourly_internal: Dict[datetime, Dict[str, List[float]]] = {}

    daylight_threshold = float(thresholds.get("LUX_DAYLIGHT_THRESHOLD", DEFAULT_THRESHOLDS["LUX_DAYLIGHT_THRESHOLD"]))
    light_target_hours = float(thresholds.get("LIGHT_TARGET_HOURS", DEFAULT_THRESHOLDS["LIGHT_TARGET_HOURS"]))
    temp_ok_min = float(thresholds.get("TEMP_OK_MIN", DEFAULT_THRESHOLDS["TEMP_OK_MIN"]))
    temp_ok_max = float(thresholds.get("TEMP_OK_MAX", DEFAULT_THRESHOLDS["TEMP_OK_MAX"]))
    stress_cold = float(thresholds.get("TEMP_STRESS_COLD", DEFAULT_THRESHOLDS["TEMP_STRESS_COLD"]))
    stress_hot = float(thresholds.get("TEMP_STRESS_HOT", DEFAULT_THRESHOLDS["TEMP_STRESS_HOT"]))
    spike_delta = float(thresholds.get("TEMP_SPIKE_DELTA", DEFAULT_THRESHOLDS["TEMP_SPIKE_DELTA"]))
    vpd_ok_min = float(thresholds.get("VPD_OK_MIN", DEFAULT_THRESHOLDS["VPD_OK_MIN"]))
    vpd_ok_max = float(thresholds.get("VPD_OK_MAX", DEFAULT_THRESHOLDS["VPD_OK_MAX"]))
    gdd_base = float(thresholds.get("GDD_BASE_C", DEFAULT_THRESHOLDS["GDD_BASE_C"]))
    dew_high = float(thresholds.get("DEWPOINT_MARGIN_HIGH_RISK_C", DEFAULT_THRESHOLDS["DEWPOINT_MARGIN_HIGH_RISK_C"]))
    dew_med = float(thresholds.get("DEWPOINT_MARGIN_MED_RISK_C", DEFAULT_THRESHOLDS["DEWPOINT_MARGIN_MED_RISK_C"]))

    total_duration = 0.0
    daylight_seconds = 0.0
    light_dose = 0.0
    temp_ok_seconds = 0.0
    stress_cold_seconds = 0.0
    stress_hot_seconds = 0.0
    vpd_ok_seconds = 0.0
    dew_high_seconds = 0.0
    dew_med_seconds = 0.0
    spike_count = 0

    prev_temp = None
    worst_margin_val: Optional[float] = None
    worst_margin_time: Optional[datetime] = None

    for idx, sample in enumerate(samples):
        next_ts = samples[idx + 1].ts if idx + 1 < len(samples) else None
        delta = max(1.0, min((next_ts - sample.ts) if next_ts else 60.0, 300.0))
        total_duration += delta

        hour_key = _hour_bucket(sample.dt)
        bucket = hourly_internal.setdefault(hour_key, {"lux": [], "temp": [], "humidity": [], "dew": [], "vpd": [], "margin": []})

        if sample.lux is not None:
            lux_points.append((sample.dt, sample.lux))
            bucket["lux"].append(sample.lux)
            if sample.lux >= daylight_threshold:
                daylight_seconds += delta
            light_dose += sample.lux * (delta / 3600.0)

        if sample.temp_c is not None:
            temp_points.append((sample.dt, sample.temp_c))
            bucket["temp"].append(sample.temp_c)
            if temp_ok_min <= sample.temp_c <= temp_ok_max:
                temp_ok_seconds += delta
            if sample.temp_c < stress_cold:
                stress_cold_seconds += delta
            if sample.temp_c > stress_hot:
                stress_hot_seconds += delta
            if prev_temp is not None and abs(sample.temp_c - prev_temp) >= spike_delta:
                spike_count += 1
            prev_temp = sample.temp_c

        if sample.humidity is not None:
            humidity_points.append((sample.dt, sample.humidity))
            bucket["humidity"].append(sample.humidity)

        if sample.dew_point_c is not None:
            dew_points.append((sample.dt, sample.dew_point_c))
            bucket["dew"].append(sample.dew_point_c)
        if sample.vpd_kpa is not None:
            vpd_points.append((sample.dt, sample.vpd_kpa))
            bucket["vpd"].append(sample.vpd_kpa)
            if vpd_ok_min <= sample.vpd_kpa <= vpd_ok_max:
                vpd_ok_seconds += delta

        margin = dewpoint_margin(sample.temp_c, sample.dew_point_c)
        margin_points.append((sample.dt, margin))
        if margin is not None:
            bucket["margin"].append(margin)
            if worst_margin_val is None or margin < worst_margin_val:
                worst_margin_val = margin
                worst_margin_time = sample.dt
            if margin <= dew_high:
                dew_high_seconds += delta
            elif margin <= dew_med:
                dew_med_seconds += delta

    lux_summary = _summarize_points(lux_points)
    temp_summary = _summarize_points(temp_points)
    hum_summary = _summarize_points(humidity_points)
    dew_summary = _summarize_points(dew_points)
    vpd_summary = _summarize_points(vpd_points)
    margin_vals = [v for _, v in margin_points if v is not None]
    margin_min = min(margin_vals) if margin_vals else None
    margin_max = max(margin_vals) if margin_vals else None

    coverage_note = _coverage_note(total_duration)
    stress_hours = (stress_cold_seconds + stress_hot_seconds) / 3600.0
    daylight_ratio = daylight_seconds / (light_target_hours * 3600.0) if light_target_hours > 0 else 0.0
    temp_ok_ratio = temp_ok_seconds / total_duration if total_duration else 0.0
    vpd_ok_ratio = vpd_ok_seconds / total_duration if total_duration else 0.0
    dew_risk_high_hours = dew_high_seconds / 3600.0

    hourly_series: List[Dict[str, Any]] = []
    for hour_key, bucket in sorted(hourly_internal.items(), key=lambda x: x[0]):
        ext = weather_hourly.get(hour_key, {})
        avg_temp = _safe_mean(bucket["temp"])
        ext_temp = ext.get("temperature_2m")
        hourly_series.append({
            "time": _as_iso(hour_key),
            "lux": _safe_mean(bucket["lux"]),
            "temp_in": avg_temp,
            "hum_in": _safe_mean(bucket["humidity"]),
            "dew_point": _safe_mean(bucket["dew"]),
            "vpd": _safe_mean(bucket["vpd"]),
            "dew_margin": _safe_mean(bucket["margin"]),
            "temp_out": ext_temp,
            "hum_out": ext.get("relative_humidity_2m"),
            "shortwave": ext.get("shortwave_radiation"),
            "gti": ext.get("global_tilted_irradiance"),
            "cloud_cover": ext.get("cloud_cover"),
            "temp_delta": (avg_temp - ext_temp) if (avg_temp is not None and ext_temp is not None) else None,
        })

    sunrise = weather.get("daily", {}).get("sunrise")
    sunset = weather.get("daily", {}).get("sunset")
    if isinstance(sunrise, list):
        sunrise = sunrise[0]
    if isinstance(sunset, list):
        sunset = sunset[0]

    status_badges = {
        "light": _status_from_ratio(daylight_ratio),
        "heat": _status_from_ratio(temp_ok_ratio),
        "condensation": "dikkat" if dew_high_seconds > 1800 else ("orta" if dew_med_seconds > 3600 else "iyi"),
    }

    story = _build_story(temp_ok_ratio, daylight_ratio, dew_risk_high_hours, worst_margin_val)

    report = {
        "date": target_date.isoformat(),
        "tz": str(tz),
        "profile": {
            "name": thresholds.get("profile_name"),
            "label": thresholds.get("profile_label"),
            "description": thresholds.get("profile_description"),
        },
        "coverage": {
            "seconds": round(total_duration, 1),
            "note": coverage_note,
        },
        "summary": {
            "badges": status_badges,
            "progress": {
                "temp_ok_pct": round(temp_ok_ratio * 100, 1),
                "vpd_ok_pct": round(vpd_ok_ratio * 100, 1),
                "light_ok_pct": round(min(daylight_ratio, 1.2) * 100, 1),
                "dew_safe_pct": round(max(0.0, 1.0 - (dew_high_seconds / total_duration if total_duration else 0.0)) * 100, 1),
            },
            "story": story,
        },
        "indoor": {
            "light": {
                **lux_summary,
                "daylight_seconds": daylight_seconds,
                "daylight_hours": round(daylight_seconds / 3600.0, 2),
                "light_dose_lux_hours": round(light_dose, 2),
                "threshold": daylight_threshold,
            },
            "temperature": {
                **temp_summary,
                "ok_seconds": temp_ok_seconds,
                "ok_hours": round(temp_ok_seconds / 3600.0, 2),
                "stress_cold_hours": round(stress_cold_seconds / 3600.0, 2),
                "stress_hot_hours": round(stress_hot_seconds / 3600.0, 2),
            },
            "humidity": hum_summary,
            "dew_point": dew_summary,
            "dewpoint_margin": {
                "min": margin_min,
                "max": margin_max,
                "worst_time": _as_iso(worst_margin_time),
                "high_risk_hours": round(dew_high_seconds / 3600.0, 2),
                "med_risk_hours": round(dew_med_seconds / 3600.0, 2),
                "high_threshold": dew_high,
                "med_threshold": dew_med,
            },
            "vpd": {
                **vpd_summary,
                "ok_hours": round(vpd_ok_seconds / 3600.0, 2),
            },
        },
        "plants": {
            "gdd": _calc_gdd(temp_summary["max"], temp_summary["min"], gdd_base),
            "stress_hours": round(stress_hours, 2),
        },
        "weather": {
            "status": "ok" if weather else "missing",
            "sunrise": _as_iso(datetime.fromtimestamp(sunrise, tz)) if sunrise else None,
            "sunset": _as_iso(datetime.fromtimestamp(sunset, tz)) if sunset else None,
            "source": "open-meteo" if weather else None,
        },
        "hourly": hourly_series,
        "data_quality": {
            "spike_count": spike_count,
        },
        "thresholds": {
            "TEMP_OK_MIN": temp_ok_min,
            "TEMP_OK_MAX": temp_ok_max,
            "TEMP_STRESS_COLD": stress_cold,
            "TEMP_STRESS_HOT": stress_hot,
            "TEMP_SPIKE_DELTA": spike_delta,
            "VPD_OK_MIN": vpd_ok_min,
            "VPD_OK_MAX": vpd_ok_max,
            "LUX_DAYLIGHT_THRESHOLD": daylight_threshold,
            "LIGHT_TARGET_HOURS": light_target_hours,
            "GDD_BASE_C": gdd_base,
            "DEWPOINT_MARGIN_HIGH_RISK_C": dew_high,
            "DEWPOINT_MARGIN_MED_RISK_C": dew_med,
        },
    }
    return report


def _range_metrics(start_date: date, end_date: date, cfg: Dict[str, Any], profile_name: Optional[str]) -> Dict[str, Any]:
    current = start_date
    items: List[Dict[str, Any]] = []
    while current <= end_date:
        items.append(compute_day_metrics(current, cfg, profile_name))
        current += timedelta(days=1)
    if not items:
        return {"light_dose": 0.0, "temp_min": None, "temp_max": None, "dew_risk_hours": 0.0, "stress_hours": 0.0, "gdd_total": 0.0}
    light_dose = _safe_mean([it["indoor"]["light"]["light_dose_lux_hours"] for it in items]) or 0.0
    temp_min_list = [it["indoor"]["temperature"]["min"] for it in items if it["indoor"]["temperature"]["min"] is not None]
    temp_max_list = [it["indoor"]["temperature"]["max"] for it in items if it["indoor"]["temperature"]["max"] is not None]
    dew_risk = sum([it["indoor"]["dewpoint_margin"]["high_risk_hours"] for it in items])
    stress = sum([it["plants"]["stress_hours"] for it in items])
    gdd_total = sum([it["plants"]["gdd"] for it in items])
    return {
        "light_dose": light_dose,
        "temp_min": min(temp_min_list) if temp_min_list else None,
        "temp_max": max(temp_max_list) if temp_max_list else None,
        "dew_risk_hours": dew_risk,
        "stress_hours": stress,
        "gdd_total": gdd_total,
    }


def build_daily_report(target_date: date, profile_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = config or load_reporting_config()
    today_report = compute_day_metrics(target_date, cfg, profile_name)
    yesterday = target_date - timedelta(days=1)
    prev_week_start = target_date - timedelta(days=7)
    prev_week_end = target_date - timedelta(days=1)
    yesterday_metrics = _range_metrics(yesterday, yesterday, cfg, profile_name)
    week_metrics = _range_metrics(prev_week_start, prev_week_end, cfg, profile_name)
    comparisons = {
        "vs_yesterday": {
            "light_dose_delta": today_report["indoor"]["light"]["light_dose_lux_hours"] - yesterday_metrics.get("light_dose", 0.0),
            "temp_min_delta": _delta(today_report["indoor"]["temperature"]["min"], yesterday_metrics.get("temp_min")),
            "temp_max_delta": _delta(today_report["indoor"]["temperature"]["max"], yesterday_metrics.get("temp_max")),
            "dew_risk_hours_delta": today_report["indoor"]["dewpoint_margin"]["high_risk_hours"] - yesterday_metrics.get("dew_risk_hours", 0.0),
            "stress_hours_delta": today_report["plants"]["stress_hours"] - yesterday_metrics.get("stress_hours", 0.0),
            "gdd_delta": today_report["plants"]["gdd"] - yesterday_metrics.get("gdd_total", 0.0),
        },
        "vs_last7_avg": {
            "light_dose_delta": today_report["indoor"]["light"]["light_dose_lux_hours"] - week_metrics.get("light_dose", 0.0),
            "temp_min_delta": _delta(today_report["indoor"]["temperature"]["min"], week_metrics.get("temp_min")),
            "temp_max_delta": _delta(today_report["indoor"]["temperature"]["max"], week_metrics.get("temp_max")),
            "dew_risk_hours_delta": today_report["indoor"]["dewpoint_margin"]["high_risk_hours"] - (week_metrics.get("dew_risk_hours", 0.0) / 7.0),
            "stress_hours_delta": today_report["plants"]["stress_hours"] - (week_metrics.get("stress_hours", 0.0) / 7.0),
            "gdd_delta": today_report["plants"]["gdd"] - (week_metrics.get("gdd_total", 0.0) / 7.0),
        },
    }
    today_report["comparisons"] = comparisons
    today_report["config"] = {
        "BEGINNER_MODE_DEFAULT": cfg.get("BEGINNER_MODE_DEFAULT", True),
        "SERA_LAT": cfg.get("SERA_LAT"),
        "SERA_LON": cfg.get("SERA_LON"),
        "SERA_TZ": cfg.get("SERA_TZ", DEFAULT_LOCATION["SERA_TZ"]),
        "ACTIVE_PROFILE": cfg.get("ACTIVE_PROFILE", "general"),
        "orientation": {
            "SERA_FACADE_AZIMUTH_NORTH_DEG": cfg.get("SERA_FACADE_AZIMUTH_NORTH_DEG"),
            "SERA_FACADE_TILT_DEG": cfg.get("SERA_FACADE_TILT_DEG"),
            "azimuth_open_meteo": azimuth_from_north_to_open_meteo(cfg.get("SERA_FACADE_AZIMUTH_NORTH_DEG", DEFAULT_ORIENTATION["SERA_FACADE_AZIMUTH_NORTH_DEG"])),
        },
    }
    return today_report


def _delta(cur: Optional[float], prev: Optional[float]) -> Optional[float]:
    if cur is None or prev is None:
        return None
    return round(cur - prev, 3)


def build_weekly_report(end_date: date, profile_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = config or load_reporting_config()
    start_date = end_date - timedelta(days=6)
    current = start_date
    days: List[Dict[str, Any]] = []
    while current <= end_date:
        days.append(compute_day_metrics(current, cfg, profile_name))
        current += timedelta(days=1)
    if not days:
        return {"date": end_date.isoformat(), "days": [], "summary": {}}
    light_dose_sum = sum(d["indoor"]["light"]["light_dose_lux_hours"] for d in days)
    stress_sum = sum(d["plants"]["stress_hours"] for d in days)
    gdd_sum = sum(d["plants"]["gdd"] for d in days)
    dew_risk_sum = sum(d["indoor"]["dewpoint_margin"]["high_risk_hours"] for d in days)
    summary = {
        "light_dose_lux_hours": round(light_dose_sum, 2),
        "stress_hours": round(stress_sum, 2),
        "gdd_total": round(gdd_sum, 2),
        "dew_risk_high_hours": round(dew_risk_sum, 2),
    }
    return {
        "end_date": end_date.isoformat(),
        "start_date": start_date.isoformat(),
        "days": days,
        "summary": summary,
        "config": {
            "BEGINNER_MODE_DEFAULT": cfg.get("BEGINNER_MODE_DEFAULT", True),
            "ACTIVE_PROFILE": cfg.get("ACTIVE_PROFILE", "general"),
        },
    }


def explainers_catalog() -> Dict[str, Dict[str, Any]]:
    return {
        "lux": {
            "title": "Lux",
            "one_liner_meaning": "Gözün algıladığı ışık miktarı (parlaklık).",
            "why_it_matters": "Fotosentez için ışık gerekir; düşük lux büyümeyi yavaşlatır.",
            "what_to_watch": "Gün içinde ışık eşiği üstünde yeterli süre var mı?",
            "thresholds_used": {"LUX_DAYLIGHT_THRESHOLD": DEFAULT_THRESHOLDS["LUX_DAYLIGHT_THRESHOLD"]},
            "data_source": "BH1750 (iç), Open-Meteo güneş ışınımı (dış).",
        },
        "light_dose_proxy": {
            "title": "Işık dozu (proxy)",
            "one_liner_meaning": "Lux verisinden türetilen kabaca günlük 'lux-saat' toplamı.",
            "why_it_matters": "Toplam ışık miktarı bitkinin günlük enerji bütçesini belirler.",
            "what_to_watch": "Önceki günlere göre azalma var mı? Gerekirse yapay ışık süresini artır.",
            "thresholds_used": {"LIGHT_TARGET_HOURS": DEFAULT_THRESHOLDS["LIGHT_TARGET_HOURS"]},
            "data_source": "BH1750 lux ölçümleri.",
        },
        "gdd": {
            "title": "GDD (Growing Degree Days)",
            "one_liner_meaning": "Gelişim için biriken sıcaklık puanı.",
            "why_it_matters": "Büyüme hızı ve fenolojik aşamalar GDD ile takip edilir.",
            "what_to_watch": "Günlük GDD sıfırlanıyorsa ortam fazla serin olabilir.",
            "thresholds_used": {"GDD_BASE_C": DEFAULT_THRESHOLDS["GDD_BASE_C"]},
            "data_source": "DHT22 sıcaklık verisi.",
        },
        "vpd": {
            "title": "VPD",
            "one_liner_meaning": "Vapor Pressure Deficit: havanın nem alma kapasitesi.",
            "why_it_matters": "Düşük VPD stomayı kapatır, yüksek VPD yaprak kurutabilir.",
            "what_to_watch": "VPD hedef aralığı dışına çıkan saatler artarsa nem/ısı dengesini kontrol et.",
            "thresholds_used": {"VPD_OK_MIN": DEFAULT_THRESHOLDS["VPD_OK_MIN"], "VPD_OK_MAX": DEFAULT_THRESHOLDS["VPD_OK_MAX"]},
            "data_source": "DHT22 sıcaklık+nem, hesaplanan.",
        },
        "dew_point": {
            "title": "Dew point (çiğ noktası)",
            "one_liner_meaning": "Havanın doygunluğa ulaştığı sıcaklık.",
            "why_it_matters": "Yüzey sıcaklığı bu noktaya yaklaşırsa yoğuşma ve mantar riski artar.",
            "what_to_watch": "Dew point ile ortam sıcaklığı arasındaki marj düşükse havalandırma düşün.",
            "thresholds_used": {},
            "data_source": "DHT22 sıcaklık+nem, hesaplanan.",
        },
        "dewpoint_margin": {
            "title": "Dew point marjı",
            "one_liner_meaning": "Ortam sıcaklığı ile çiğ noktası arasındaki fark.",
            "why_it_matters": "Marj 1-3°C altına inerse yoğuşma/ küf riski yükselir.",
            "what_to_watch": "Yüksek risk saatlerini ve en düşük marj zamanını takip et.",
            "thresholds_used": {
                "DEWPOINT_MARGIN_HIGH_RISK_C": DEFAULT_THRESHOLDS["DEWPOINT_MARGIN_HIGH_RISK_C"],
                "DEWPOINT_MARGIN_MED_RISK_C": DEFAULT_THRESHOLDS["DEWPOINT_MARGIN_MED_RISK_C"],
            },
            "data_source": "DHT22 sıcaklık+nem, hesaplanan.",
        },
        "cloud_cover": {
            "title": "Bulutluluk",
            "one_liner_meaning": "Gökyüzünün bulutla kaplı yüzdesi.",
            "why_it_matters": "Bulut, gelen güneş ışığını düşürür; iç ışık trendiyle karşılaştırılır.",
            "what_to_watch": "Bulutluluk yüksekken iç ışıkta sert düşüş var mı?",
            "thresholds_used": {},
            "data_source": "Open-Meteo (dış).",
        },
        "gti": {
            "title": "GTI (Global Tilted Irradiance)",
            "one_liner_meaning": "Eğimli yüzeye gelen toplam güneş ışınımı.",
            "why_it_matters": "Seranın yöneliminden bağımsız ışık enerjisi tahmini verir.",
            "what_to_watch": "GTI trendi ile iç lux arasında kopukluk varsa sensörü kontrol et.",
            "thresholds_used": {"SERA_FACADE_AZIMUTH_NORTH_DEG": DEFAULT_ORIENTATION["SERA_FACADE_AZIMUTH_NORTH_DEG"], "SERA_FACADE_TILT_DEG": DEFAULT_ORIENTATION["SERA_FACADE_TILT_DEG"]},
            "data_source": "Open-Meteo global_tilted_irradiance (dış).",
        },
    }
