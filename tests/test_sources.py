import json
from datetime import date
from pathlib import Path
from weekpage.model import Week
from weekpage.settings import load_settings
from weekpage.sources.given import GivenSource
from weekpage.sources.openmeteo import OpenMeteoSource, sky_of

DATA = Path(__file__).parent / "data"
S = load_settings(Path(__file__).parents[1] / "examples" / "settings.toml")


def test_given_items_land_on_their_day(tmp_path):
    p = tmp_path / "given.json"
    p.write_text(json.dumps({"items": [{"date": "2026-10-21", "start": "18:30", "end": "19:30", "title": "Call"}],
                             "notes": [{"date": "2026-10-22", "text": "Pay rent"}], "week": ["Book flights"]}))
    w = Week.empty(date(2026, 10, 19))
    assert GivenSource(p).fill(w, S) == []
    assert w.days[2].items[0].title == "Call" and w.days[2].items[0].source == "given"
    assert w.days[3].notes == ["Pay rent"] and w.notes == ["Book flights"]


def test_weather_codes_map_to_four_skies():
    assert [sky_of(c) for c in (0, 2, 51, 63, 95)] == ["sun", "cloud", "drizzle", "rain", "rain"]


def test_openmeteo_fills_wind_from_a_recorded_answer():
    recorded = json.loads((DATA / "openmeteo.json").read_text())   # {"N": {...}, "S": {...}}
    w = Week.empty(date(2026, 10, 19))
    src = OpenMeteoSource(fetch=lambda spot, start, end: recorded[spot.label])
    assert src.fill(w, S) == []
    assert all(d.wind is not None for d in w.days)
    assert {d.wind.source for d in w.days} == {"forecast:open-meteo"}


def test_openmeteo_down_leaves_the_boxes_blank_with_a_warning():
    def boom(*a):
        raise OSError("no route")
    w = Week.empty(date(2026, 10, 19))
    assert OpenMeteoSource(fetch=boom).fill(w, S) == ["forecast N could not be read: no route",
                                                     "forecast S could not be read: no route"]
    assert all(d.wind is None for d in w.days)
