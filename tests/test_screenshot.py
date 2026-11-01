import json
from datetime import date
from pathlib import Path
from weekpage.sources.screenshot import _hour, read_boxes

D = json.loads((Path(__file__).parent / "data" / "screenshot_boxes.json").read_text())
MON = date(2026, 10, 12)


def test_events_land_on_their_day_and_time():
    got = read_boxes(D["boxes"], MON)
    items = {(d.isoformat(), i.start, i.title) for d, i in got.items}
    assert items == {("2026-10-16", "12:00", "Planning/Review Weekly Sync"),
                     ("2026-10-14", "18:30", "Team Discus...")}


def test_cut_off_titles_and_unseen_days_are_reported():
    got = read_boxes(D["boxes"], MON)
    assert [i.title for _, i in got.items if i.title.endswith("...")] == ["Team Discus..."]
    assert got.unseen == [date(2026, 10, 18)]


def test_all_day_bars_are_kept_apart():
    got = read_boxes(D["boxes"], MON)
    assert sorted(t for _, t in got.all_day) == ["Alex PTO", "sam@ OOTO 12 - 23 October"]


def test_no_headers_means_nothing_is_guessed():
    got = read_boxes([[0, 0, 10, 10, "hello"]], MON)
    assert got.items == [] and len(got.unseen) == 7


def _plus(start, hours):
    h, m = start.split(":")
    return f"{(int(h) + hours) % 24:02d}:{m}"


def test_two_hour_columns_read_the_one_asked_for():
    # a calendar shown in two time zones draws two hour columns side by side, an hour apart here. "lower"
    # takes the column with the smaller hours (the westward zone), "higher" the other, "left" and "right"
    # the sides, whichever side each zone sits on
    two = list(D["boxes"])
    for x, y, w, h, t in D["boxes"]:
        v = _hour(t.strip())
        if v is not None and v == int(v):
            two.append([x + 20, y, w, h, f"{int(v) + 1}:00"])
    base = read_boxes(D["boxes"], MON)
    lower = read_boxes(two, MON, hour_column="lower")
    higher = read_boxes(two, MON, hour_column="higher")
    assert base.hour_columns == 1 and lower.hour_columns == 2
    assert [(d, i.start) for d, i in lower.items] == [(d, i.start) for d, i in base.items]
    assert [(d, i.start) for d, i in higher.items] == [(d, _plus(i.start, 1)) for d, i in base.items]
    assert [i.start for _, i in read_boxes(two, MON, hour_column="left").items] == [i.start for _, i in lower.items]
    assert [i.start for _, i in read_boxes(two, MON, hour_column="right").items] == [i.start for _, i in higher.items]
    assert [i.start for _, i in read_boxes(two, MON).items] == [i.start for _, i in lower.items]
