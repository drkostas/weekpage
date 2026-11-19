from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from weekpage.model import Week
from weekpage.settings import Settings, Spot, WindRule
from weekpage.sources import windguru
from weekpage.sun import daylight

TZ = ZoneInfo("America/Denver")
SETTINGS = Settings(wind=WindRule(15, 2, [Spot("N", "North beach", 40.0, -105.0, (300, 60)),
                                          Spot("S", "South beach", 40.1, -105.0, (120, 240))]))
INIT = datetime(2026, 11, 2, 0, 0)       # a Monday, in UTC
WINDY_DAY = date(2026, 11, 4)
START = INIT.replace(tzinfo=timezone.utc)


def local(h: int) -> datetime:
    return (START + timedelta(hours=h)).astimezone(TZ)


def forecast() -> dict:
    """Five days of hours. On WINDY_DAY the wind is 20 knots from 330 degrees (the north spot's
    sector), and on every other day it is 5 knots from 180."""
    hours = list(range(0, 120))
    windy = [local(h).date() == WINDY_DAY for h in hours]
    return {"initdate": INIT.isoformat(sep=" "), "hours": hours,
            "WINDSPD": [20 if w else 5 for w in windy], "WINDDIR": [330 if w else 180 for w in windy],
            "TCDC": [10] * 120, "APCP1": [0] * 120, "TMP": [10 + (local(h).hour % 12) for h in hours]}


def week() -> Week:
    return Week.empty(date(2026, 11, 2))


def source(**kw) -> windguru.WindguruSource:
    return windguru.WindguruSource({"N": 1, "S": 2}, fetch=lambda sid: forecast(), tz=TZ, **kw)


def test_the_four_weather_boxes():
    assert windguru.sky(10, 0) == "sun" and windguru.sky(80, 0) == "cloud"
    assert windguru.sky(0, 0.5) == "drizzle" and windguru.sky(0, 2) == "rain"


def test_a_windy_day_fills_its_box_from_the_spot_whose_sector_the_wind_comes_from():
    w = week()
    assert windguru.WindguruSource({"N": 1}, fetch=lambda sid: forecast(), tz=TZ).fill(w, SETTINGS) == []
    got = next(d.wind for d in w.days if d.date == WINDY_DAY)
    assert got.knots == 20 and got.side == "N" and got.source == "forecast:windguru"


def test_the_temperature_is_the_daylight_high():
    w = week()
    source().fill(w, SETTINGS)
    got = next(d.wind for d in w.days if d.date == WINDY_DAY)
    rise, sets = daylight(40.0, -105.0, WINDY_DAY, TZ)
    temps = [forecast()["TMP"][h] for h in range(120)
             if local(h).date() == WINDY_DAY and rise <= local(h).time() <= sets]
    assert temps and got.temp == round(max(temps))


def test_spot_of_reads_a_day_from_one_spot_only():
    both, forced = week(), week()
    source().fill(both, SETTINGS)
    source(spot_of=lambda d: "S" if d == WINDY_DAY else None).fill(forced, SETTINGS)
    b = next(d.wind for d in both.days if d.date == WINDY_DAY)
    f = next(d.wind for d in forced.days if d.date == WINDY_DAY)
    assert b.side == "N" and f.side == "S"
    rest = lambda wk: [d.wind for d in wk.days if d.date != WINDY_DAY]
    assert rest(both) == rest(forced)


def test_a_spot_that_does_not_answer_is_a_warning_and_leaves_its_boxes_blank():
    def boom(sid):
        raise OSError("no route")
    w = week()
    assert windguru.WindguruSource({"N": 1, "S": 2}, fetch=boom).fill(w, SETTINGS) == [
        "windguru N could not be read: no route", "windguru S could not be read: no route"]
    assert all(d.wind is None for d in w.days)


def test_the_page_is_asked_the_way_the_page_asks(monkeypatch):
    seen = []

    def fake_get(spot_id, params):
        seen.append((spot_id, params["q"]))
        if params["q"] == "forecast_spot":
            return {"tabs": [{"id_model": 7, "id_model_arr": []},
                             {"id_model": windguru.MODEL, "id_model_arr": [
                                 {"id_model": 3, "rundef": "r", "initstr": "i", "cachefix": "c"}]}]}
        assert params["id_model"] == 3 and params["rundef"] == "r" and params["id_spot"] == 9
        return {"ok": True}
    monkeypatch.setattr(windguru, "_get", fake_get)
    assert windguru.fetch(9) == {"ok": True}
    assert seen == [(9, "forecast_spot"), (9, "forecast")]
