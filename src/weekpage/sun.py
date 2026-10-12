"""Sunrise and sunset for a place and a day (NOAA's solar equations, good to a minute or two)."""
from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone


def daylight(lat: float, lon: float, day: date, tz) -> tuple[time, time]:
    """Local sunrise and sunset. Near the poles, where the sun does not rise or set, the whole day
    or none of it."""
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1 + 0.5)     # fractional year at noon
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    phi = math.radians(lat)
    cos_h = (math.cos(math.radians(90.833)) / (math.cos(phi) * math.cos(decl))
             - math.tan(phi) * math.tan(decl))
    if cos_h <= -1:
        return time(0, 0), time(23, 59)
    if cos_h >= 1:
        return time(12, 0), time(12, 0)
    ha = math.degrees(math.acos(cos_h))
    midnight = datetime.combine(day, time(0), tzinfo=timezone.utc)
    rise = midnight + timedelta(minutes=720 - 4 * (lon + ha) - eqt)
    sets = midnight + timedelta(minutes=720 - 4 * (lon - ha) - eqt)
    return rise.astimezone(tz).time().replace(second=0, microsecond=0), sets.astimezone(tz).time().replace(second=0, microsecond=0)
