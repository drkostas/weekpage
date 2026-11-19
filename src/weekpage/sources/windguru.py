"""The Windguru forecast for your spots, read the way a spot page reads it.

A spot page loads its numbers from its own JSON address, and that address answers without signing
in. This source makes the same two requests the page makes (the model list, then the GFS run) for
each spot id, with the page as the Referer. It is a source like the others: it fills the week and
returns warnings, and a spot that does not answer leaves its boxes blank. Windguru also sells an API
with an account, which this does not use. Keep the requests few (once a week per spot is enough)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

import httpx

from ..model import Week
from ..settings import Settings
from ..sun import daylight
from ..wind import Sample, summarise_day

API = "https://www.windguru.cz/int/iapi.php"
MODEL = 3                       # GFS 13 km, the model a spot page shows first
UTC = ZoneInfo("UTC")


def _get(spot_id: int, params: dict) -> dict:
    r = httpx.get(API, params=params, timeout=30, follow_redirects=True,
                  headers={"User-Agent": "Mozilla/5.0", "Referer": f"https://www.windguru.cz/{spot_id}"})
    r.raise_for_status()
    return r.json()


def fetch(spot_id: int) -> dict:
    """The newest GFS run for one spot, as the page loads it."""
    index = _get(spot_id, {"q": "forecast_spot", "id_spot": spot_id})
    tab = next(t for t in index["tabs"] if t["id_model"] == MODEL)
    m = tab["id_model_arr"][0]
    return _get(spot_id, {"q": "forecast", "id_model": m["id_model"], "rundef": m["rundef"],
                          "initstr": m["initstr"], "id_spot": spot_id, "WGCACHEABLE": 21600,
                          "cachefix": m["cachefix"]})


def sky(cloud: float | None, rain: float | None) -> str:
    """One of the four weather boxes, from cloud cover (%) and rain in the hour (mm)."""
    if (rain or 0) >= 1:
        return "rain"
    if (rain or 0) > 0.1:
        return "drizzle"
    return "cloud" if (cloud or 0) >= 60 else "sun"


def samples(fc: dict, tz=UTC) -> list[Sample]:
    f = fc.get("fcst", fc)
    t0 = datetime.fromisoformat(f["initdate"]).replace(tzinfo=timezone.utc)
    n = len(f["hours"])
    col = lambda k: f.get(k) or [None] * n
    return [Sample((t0 + timedelta(hours=h)).astimezone(tz), k or 0, d or 0, sky(c, r), temp=t)
            for h, k, d, c, r, t in zip(f["hours"], col("WINDSPD"), col("WINDDIR"), col("TCDC"),
                                        col("APCP1"), col("TMP"))]


class WindguruSource:
    name = "forecast:windguru"

    def __init__(self, spot_ids: dict[str, int], fetch: Callable[[int], dict] = fetch, tz=UTC,
                 spot_of: Callable | None = None):
        """`spot_ids` maps a spot label of the settings to its Windguru id. `tz` is the zone the
        week's days are read in. `spot_of(date)` names the one spot a day is read from (a trip's day
        is at one place, and its spots can be hours apart). With None, or for a day it answers None
        for, the day takes the best of all the spots."""
        self.spot_ids, self.fetch, self.tz, self.spot_of = spot_ids, fetch, tz, spot_of

    def fill(self, week: Week, settings: Settings) -> list[str]:
        by_spot, warnings = {}, []
        spots = {s.label: s for s in settings.wind.spots}
        for label, sid in self.spot_ids.items():
            try:
                by_spot[label] = samples(self.fetch(sid), self.tz)
            except Exception as e:
                warnings.append(f"windguru {label} could not be read: {e}")
        if not spots:
            return warnings
        first = next(iter(spots.values()))       # spots a few km apart share one daylight
        for day in week.days:
            only = self.spot_of(day.date) if self.spot_of else None
            todays = {k: [x for x in v if x.at.date() == day.date] for k, v in by_spot.items()
                      if only is None or k == only}
            if any(todays.values()):
                ref = spots.get(only, first)
                rise, sets = daylight(ref.lat, ref.lon, day.date, self.tz)
                day.wind = summarise_day(todays, settings.wind, rise, sets, source=self.name)
        return warnings
