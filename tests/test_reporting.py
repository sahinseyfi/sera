from datetime import datetime
from zoneinfo import ZoneInfo

from reporting import azimuth_from_north_to_open_meteo, _summarize_points


def test_azimuth_conversion():
    assert azimuth_from_north_to_open_meteo(144) == -36.0


def test_summarize_points_min_max_and_time():
    tz = ZoneInfo("Europe/Istanbul")
    points = [
        (datetime(2024, 1, 1, 10, 0, tzinfo=tz), 10.0),
        (datetime(2024, 1, 1, 11, 0, tzinfo=tz), 15.0),
        (datetime(2024, 1, 1, 12, 0, tzinfo=tz), 12.0),
    ]
    summary = _summarize_points(points)
    assert summary["min"] == 10.0
    assert summary["max"] == 15.0
    assert summary["median"] == 12.0
    assert summary["avg"] == 12.33
    min_time = datetime.fromisoformat(summary["min_time"])
    max_time = datetime.fromisoformat(summary["max_time"])
    assert min_time.hour == 10 and max_time.hour == 11
