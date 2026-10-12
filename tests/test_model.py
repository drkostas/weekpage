import json
from datetime import date
from weekpage.model import Week, Day, Item, Wind, load_week, save_week


def test_a_week_has_seven_days_from_monday_and_a_title():
    w = Week.empty(date(2026, 10, 19))
    assert [d.date.isoformat() for d in w.days][0] == "2026-10-19" and len(w.days) == 7
    assert w.title == "19/10 - 25/10"


def test_monday_is_required():
    import pytest
    with pytest.raises(ValueError, match="Monday"):
        Week.empty(date(2026, 10, 20))


def test_round_trip_keeps_every_field(tmp_path):
    w = Week.empty(date(2026, 10, 19))
    w.days[4].items.append(Item(start="12:00", end="13:00", title="Weekly review", source="calendar:work"))
    w.days[0].off = "Holiday"
    w.days[2].notes.append("Bring the charger")
    w.days[3].wind = Wind(knots=22, side="N", kiteable=True, sky="sun", source="forecast")
    w.notes.append("Book the car")
    p = tmp_path / "week.json"
    save_week(w, p)
    assert load_week(p) == w
    assert json.loads(p.read_text())["monday"] == "2026-10-19"


def test_an_item_without_a_time_is_refused():
    import pytest
    with pytest.raises(ValueError, match="HH:MM"):
        Item(start="9", end="10:00", title="x", source="given")
