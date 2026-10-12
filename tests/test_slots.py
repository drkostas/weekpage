from weekpage.model import Item
from weekpage.slots import place

I = lambda s, t: Item(start=s, end=s, title=t, source="given")


def test_items_go_in_their_start_hour_sorted():
    rows = place([I("12:30", "b"), I("12:00", "a"), I("09:15", "c")], (7, 22))
    assert [r.hour for r in rows] == list(range(7, 23))
    assert [i.title for i in rows[5].shown] == ["a", "b"] and rows[2].shown[0].title == "c"


def test_more_than_two_shows_plus_n():
    rows = place([I("12:00", x) for x in "abcd"], (7, 22))
    assert [i.title for i in rows[5].shown] == ["a", "b"] and rows[5].more == 2


def test_early_and_late_items_clamp_to_the_edge_rows():
    rows = place([I("06:00", "early"), I("23:00", "late")], (7, 22))
    assert rows[0].shown[0].title == "early" and rows[-1].shown[0].title == "late"


def test_same_start_keeps_the_given_order():
    rows = place([I("12:00", "z"), I("12:00", "a")], (7, 22))
    assert [i.title for i in rows[5].shown] == ["z", "a"]
