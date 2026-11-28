import json
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
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


def source(fetch=lambda *a: EV, token=lambda: "t"):
    return GoogleCalendarSource("home", "primary", token=token, fetch=fetch, tz=ZoneInfo("Europe/Lisbon"))


def refused(*a):
    raise PermissionError("invalid_grant")


def no_dns(*a):
    raise httpx.ConnectError("[Errno 8] nodename nor servname provided, or not known")


def test_answers_when_the_calendar_reads():
    asked = []
    assert source(fetch=lambda *a: asked.append(a) or EV).answers(date(2026, 10, 20)) is True
    assert asked[0][0] == "primary" and asked[0][2].startswith("2026-10-20T00:00:00")
    assert asked[0][3].startswith("2026-10-21T00:00:00")


def test_a_refusal_is_false_from_the_token_or_the_calendar():
    assert source(token=refused).answers() is False
    assert source(fetch=refused).answers() is False


def test_a_calendar_that_could_not_be_asked_is_none():
    assert source(token=no_dns).answers() is None
    assert source(fetch=no_dns).answers() is None
    assert source(fetch=lambda *a: (_ for _ in ()).throw(httpx.ReadTimeout("timed out"))).answers() is None


def test_fill_still_warns_in_every_case():
    for f in (refused, no_dns):
        _, warns = fill(f)
        assert len(warns) == 1 and warns[0].startswith("calendar home could not be read: ")
