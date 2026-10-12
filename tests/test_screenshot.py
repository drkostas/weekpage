import json
from datetime import date
from pathlib import Path
from weekpage.sources.screenshot import read_boxes

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
