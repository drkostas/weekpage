from datetime import date, datetime, time
from weekpage.settings import Spot, WindRule
from weekpage.wind import Sample, summarise_day

N = Spot("N", "north", 0, 0, (300, 60))
S = Spot("S", "south", 0, 0, (120, 240))
RULE = WindRule(15, 2, [N, S])
DAY = date(2026, 10, 19)
LIGHT = (time(7, 30), time(18, 30))


def hours(spot_knots_dir_sky):
    """{hour: (knots, deg, sky)} -> samples"""
    return [Sample(datetime.combine(DAY, time(h)), k, d, s) for h, (k, d, s) in spot_knots_dir_sky.items()]


def test_two_strong_northerly_hours_at_the_north_spot_are_kiteable():
    north = hours({10: (16, 0, "sun"), 11: (18, 10, "sun"), 12: (12, 10, "cloud")})
    south = hours({10: (10, 0, "sun"), 11: (11, 10, "sun"), 12: (9, 10, "sun")})
    w = summarise_day({N.label: north, S.label: south}, RULE, *LIGHT)
    assert (w.knots, w.side, w.kiteable, w.sky) == (18, "N", True, "sun")


def test_one_strong_hour_is_not_enough():
    north = hours({10: (20, 0, "sun"), 11: (12, 0, "sun")})
    w = summarise_day({"N": north, "S": []}, RULE, *LIGHT)
    assert w.kiteable is False and w.knots == 20


def test_night_wind_does_not_count():
    north = hours({5: (25, 0, "sun"), 6: (25, 0, "sun"), 21: (25, 0, "sun"), 12: (8, 0, "sun")})
    w = summarise_day({"N": north, "S": []}, RULE, *LIGHT)
    assert w.kiteable is False and w.knots == 8


def test_wind_from_the_wrong_side_does_not_count_at_that_spot():
    # a southerly at the north spot is offshore there: not counted, the south spot decides
    north = hours({10: (22, 180, "sun"), 11: (22, 180, "sun")})
    south = hours({10: (17, 180, "cloud"), 11: (19, 180, "cloud")})
    w = summarise_day({"N": north, "S": south}, RULE, *LIGHT)
    assert (w.side, w.knots, w.kiteable, w.sky) == ("S", 19, True, "cloud")


def test_rain_is_not_kiteable_however_windy():
    north = hours({10: (20, 0, "rain"), 11: (24, 10, "rain"), 12: (20, 10, "rain")})
    w = summarise_day({"N": north, "S": []}, RULE, *LIGHT)
    assert w.knots == 24 and w.sky == "rain" and w.kiteable is False


def test_drizzle_is_not_kiteable_either():
    north = hours({10: (20, 0, "drizzle"), 11: (22, 10, "drizzle"), 12: (20, 10, "drizzle")})
    w = summarise_day({"N": north, "S": []}, RULE, *LIGHT)
    assert w.kiteable is False


def test_temperature_is_the_daytime_high():
    north = [Sample(datetime.combine(DAY, time(h)), 16, 0, "sun", temp=t)
             for h, t in {9: 17.2, 13: 21.8, 17: 19.0}.items()]
    w = summarise_day({"N": north, "S": []}, RULE, *LIGHT)
    assert w.temp == 22                      # round(max(17.2, 21.8, 19.0))


def test_direction_is_the_bearing_at_the_strongest_hour():
    north = hours({10: (16, 10, "sun"), 11: (24, 350, "sun"), 12: (18, 40, "sun")})
    w = summarise_day({"N": north, "S": []}, RULE, *LIGHT)
    assert w.knots == 24 and w.deg == 350    # the strongest hour decides the arrow


def test_no_temperature_when_the_samples_have_none():
    north = hours({10: (16, 0, "sun"), 11: (18, 10, "sun")})   # hours() builds samples with temp=None
    w = summarise_day({"N": north, "S": []}, RULE, *LIGHT)
    assert w.temp is None


def test_no_matching_sector_shows_the_strongest_peak_not_kiteable():
    north = hours({10: (21, 90, "cloud")})
    south = hours({10: (14, 90, "cloud")})
    w = summarise_day({"N": north, "S": south}, RULE, *LIGHT)
    assert (w.side, w.knots, w.kiteable) == ("N", 21, False)


def test_no_samples_gives_none():
    assert summarise_day({"N": [], "S": []}, RULE, *LIGHT) is None
