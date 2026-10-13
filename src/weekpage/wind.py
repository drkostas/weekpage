"""Hourly forecast for each spot -> one wind box per day."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, time

from .model import Wind
from .settings import WindRule

WETNESS = {"sun": 0, "cloud": 1, "drizzle": 2, "rain": 3}


@dataclass
class Sample:
    at: datetime
    knots: float
    deg: float
    sky: str
    temp: float | None = None       # air temperature in degrees Celsius, when the source has it


def summarise_day(by_spot: dict[str, list[Sample]], rule: WindRule, sunrise: time, sunset: time,
                  source: str = "forecast") -> Wind | None:
    spots = {s.label: s for s in rule.spots}
    light = {k: [x for x in v if sunrise <= x.at.time() <= sunset] for k, v in by_spot.items()}
    if not any(light.values()):
        return None
    best = None   # (strong hours, peak, label)
    for label, xs in light.items():
        inside = [x for x in xs if label in spots and spots[label].covers(x.deg)]
        if not inside:
            continue
        cand = (sum(x.knots >= rule.min_knots for x in inside), max(x.knots for x in inside), label)
        best = max(best, cand) if best else cand
    if best:
        strong, peak, label = best
        kiteable = strong >= rule.min_hours
    else:
        peak, label = max((max(x.knots for x in xs), k) for k, xs in light.items() if xs)
        kiteable = False
    skies = Counter(x.sky for x in light[label])
    sky = max(skies, key=lambda s: (skies[s], WETNESS.get(s, 0)))
    kiteable = kiteable and sky not in ("rain", "drizzle")   # no outline on a wet day, however windy
    temps = [x.temp for v in light.values() for x in v if x.temp is not None]
    temp = round(max(temps)) if temps else None       # the day's high, in daylight
    deg = round(max(light[label], key=lambda x: x.knots).deg)   # bearing at the strongest hour
    return Wind(knots=round(peak), side=label, kiteable=kiteable, sky=sky, temp=temp, deg=deg, source=source)
