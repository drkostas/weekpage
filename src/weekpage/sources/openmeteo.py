"""A free forecast with no account (open-meteo.com), one request per spot."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Callable

import httpx

from ..model import Week
from ..settings import Settings, Spot
from ..wind import Sample, summarise_day

URL = "https://api.open-meteo.com/v1/forecast"


def params(spot: Spot, start: str, end: str) -> dict:
    return {"latitude": spot.lat, "longitude": spot.lon, "timezone": "auto", "wind_speed_unit": "kn",
            "hourly": "wind_speed_10m,wind_direction_10m,weather_code", "daily": "sunrise,sunset",
            "start_date": start, "end_date": end}


def sky_of(code: int) -> str:
    if code <= 1:
        return "sun"
    if code in (2, 3, 45, 48):
        return "cloud"
    if 51 <= code <= 57 or code in (61, 80):
        return "drizzle"
    return "rain"


def _fetch(spot: Spot, start: str, end: str) -> dict:
    r = httpx.get(URL, params=params(spot, start, end), timeout=30)
    r.raise_for_status()
    return r.json()


class OpenMeteoSource:
    name = "forecast:open-meteo"

    def __init__(self, fetch: Callable[[Spot, str, str], dict] = _fetch):
        self.fetch = fetch

    def fill(self, week: Week, settings: Settings) -> list[str]:
        start, end = week.monday.isoformat(), (week.monday + timedelta(6)).isoformat()
        by_spot, light, warnings = {}, {}, []
        for spot in settings.wind.spots:
            try:
                d = self.fetch(spot, start, end)
            except Exception as e:
                warnings.append(f"forecast {spot.label} could not be read: {e}")
                continue
            h = d["hourly"]
            by_spot[spot.label] = [Sample(datetime.fromisoformat(t), k or 0, g or 0, sky_of(c or 0))
                                   for t, k, g, c in zip(h["time"], h["wind_speed_10m"], h["wind_direction_10m"], h["weather_code"])]
            for day, sr, ss in zip(d["daily"]["time"], d["daily"]["sunrise"], d["daily"]["sunset"]):
                light.setdefault(date.fromisoformat(day), (datetime.fromisoformat(sr).time(), datetime.fromisoformat(ss).time()))
        for day in week.days:
            if day.date not in light:
                continue
            todays = {k: [x for x in v if x.at.date() == day.date] for k, v in by_spot.items()}
            day.wind = summarise_day(todays, settings.wind, *light[day.date], source=self.name)
        return warnings
