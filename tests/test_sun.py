import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from weekpage.sun import daylight

OM = json.loads((Path(__file__).parent / "data" / "openmeteo.json").read_text())["N"]
LISBON = ZoneInfo("Europe/Lisbon")


def minutes(t):
    return t.hour * 60 + t.minute


def test_matches_a_recorded_forecast_within_two_minutes():
    # compared in UTC: the recorded answer uses one fixed offset for the whole week, and this week
    # has the autumn clock change in it
    fixed = timezone(timedelta(seconds=OM["utc_offset_seconds"]))
    for i in range(7):
        d = date.fromisoformat(OM["daily"]["time"][i])
        rise, sets = daylight(OM["latitude"], OM["longitude"], d, timezone.utc)
        want_r = datetime.fromisoformat(OM["daily"]["sunrise"][i]).replace(tzinfo=fixed).astimezone(timezone.utc).time()
        want_s = datetime.fromisoformat(OM["daily"]["sunset"][i]).replace(tzinfo=fixed).astimezone(timezone.utc).time()
        assert abs(minutes(rise) - minutes(want_r)) <= 2 and abs(minutes(sets) - minutes(want_s)) <= 2


def test_the_clock_change_moves_local_sunrise_an_hour_earlier():
    before = daylight(38.72, -9.14, date(2026, 10, 24), LISBON)[0]
    after = daylight(38.72, -9.14, date(2026, 10, 25), LISBON)[0]
    assert 55 <= minutes(before) - minutes(after) <= 62


def test_summer_days_are_long():
    rise, sets = daylight(38.72, -9.14, date(2026, 6, 21), LISBON)
    assert (rise.hour, sets.hour) == (6, 20)
