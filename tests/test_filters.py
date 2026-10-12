from datetime import date
from pathlib import Path
from weekpage.model import Week
from weekpage.settings import Calendar, Settings
from weekpage.sources.ics import IcsSource

ICS = Path(__file__).parent / "data" / "sample.ics"


def fill():
    w = Week.empty(date(2026, 10, 19))
    cal = Calendar(name="home", ics=str(ICS), me=["me@example.org"], skip=["birthday"])
    warnings = IcsSource(cal).fill(w, Settings(calendars=[cal]))
    return w, warnings


def titles(w, i):
    return [x.title for x in w.days[i].items]


def test_recurring_events_appear_every_day_in_the_week():
    w, _ = fill()
    assert all("Standup" in titles(w, i) for i in range(7))


def test_a_duplicate_is_kept_once():
    w, _ = fill()
    assert titles(w, 1).count("Dentist") == 1


def test_declined_and_cancelled_are_left_out():
    w, _ = fill()
    assert "Team dinner" not in titles(w, 2) and "Old plan" not in titles(w, 3)


def test_all_day_items_become_notes_unless_skipped():
    w, _ = fill()
    assert w.days[4].notes == [] and w.days[5].notes == ["Trip to Naxos"] and w.days[6].notes == ["Trip to Naxos"]


def test_every_item_says_where_it_came_from():
    w, _ = fill()
    assert {i.source for d in w.days for i in d.items} == {"calendar:home"}


def test_an_unreachable_calendar_is_a_warning_not_a_crash():
    w = Week.empty(date(2026, 10, 19))
    cal = Calendar(name="gone", ics="/nonexistent.ics")
    assert IcsSource(cal).fill(w, Settings()) == ["calendar gone could not be read"]
