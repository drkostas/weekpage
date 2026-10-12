"""Run the sources for one week."""
from __future__ import annotations

from datetime import date, timedelta

from .model import Week
from .settings import Settings


def next_monday(today: date) -> date:
    return today + timedelta((7 - today.weekday()) % 7)


def gather(monday: date, settings: Settings, sources) -> tuple[Week, list[str]]:
    week, warnings = Week.empty(monday), []
    for src in sources:
        try:
            warnings += src.fill(week, settings)
        except Exception as e:
            warnings.append(f"{src.name} failed: {e}")
    return week, warnings


def default_sources(settings: Settings):
    from .sources.ics import IcsSource
    from .sources.openmeteo import OpenMeteoSource
    return [*(IcsSource(c) for c in settings.calendars if c.ics), *([OpenMeteoSource()] if settings.wind.spots else [])]
