from datetime import date
import pytest
from weekpage.lines import parse_line

MON = date(2026, 10, 19)


@pytest.mark.parametrize("text,want", [
    ("Wed 18:00-19:00 Physio", ("2026-10-21", "18:00", "19:00", "Physio")),
    ("fri 9:30 Dentist", ("2026-10-23", "09:30", "10:30", "Dentist")),
    ("Monday 7-8 Swim", ("2026-10-19", "07:00", "08:00", "Swim")),
    ("Sun 20:15 Call with the family", ("2026-10-25", "20:15", "21:15", "Call with the family")),
])
def test_a_line_becomes_an_item(text, want):
    day, item = parse_line(text, MON, source="answer")
    assert (day.isoformat(), item.start, item.end, item.title) == want and item.source == "answer"


@pytest.mark.parametrize("text", ["", "Physio", "Wed Physio", "Xyz 10:00 a"])
def test_a_line_without_a_day_and_time_is_refused(text):
    with pytest.raises(ValueError):
        parse_line(text, MON)
