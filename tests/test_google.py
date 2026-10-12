import json
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo
from weekpage.model import Week
from weekpage.settings import Settings
from weekpage.sources.google import GoogleCalendarSource

EV = json.loads((Path(__file__).parent / "data" / "google_events.json").read_text())


def fill(fetch=lambda *a: EV):
    w = Week.empty(date(2026, 10, 19))
    warns = GoogleCalendarSource("home", "primary", token=lambda: "t", fetch=fetch, tz=ZoneInfo("Europe/Lisbon")).fill(w, Settings())
    return w, warns


def test_kept_and_left_out():
    w, warns = fill()
    assert warns == []
    assert [(i.start, i.end, i.title) for i in w.days[1].items] == [("12:00", "13:00", "Dentist")]
    assert all(not d.items for i, d in enumerate(w.days) if i != 1)
    assert w.days[5].notes == ["Trip to Naxos"] and w.days[6].notes == ["Trip to Naxos"]
    assert {i.source for d in w.days for i in d.items} == {"calendar:home"}


def test_a_refused_token_is_a_warning():
    def boom(*a):
        raise PermissionError("invalid_grant")
    _, warns = fill(boom)
    assert warns == ["calendar home could not be read: invalid_grant"]
