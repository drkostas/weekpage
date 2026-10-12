"""Any .ics calendar, from a file or a link, with the generic clean-up."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
import icalendar
import recurring_ical_events

from ..filters import keep_event
from ..model import Item, Week
from ..settings import Calendar, Settings


def _read(ics: str) -> bytes:
    if ics.startswith(("http://", "https://", "webcal://")):
        r = httpx.get(ics.replace("webcal://", "https://"), timeout=30, follow_redirects=True)
        r.raise_for_status()
        return r.content
    return Path(ics).read_bytes()


class IcsSource:
    def __init__(self, cal: Calendar, tz=None):
        self.cal, self.tz = cal, tz
        self.name = f"calendar:{cal.name}"

    def fill(self, week: Week, settings: Settings) -> list[str]:
        try:
            cal = icalendar.Calendar.from_ical(_read(self.cal.ics))
        except Exception:
            return [f"calendar {self.cal.name} could not be read"]
        start, end = week.monday, week.monday + timedelta(7)
        seen = {(d.date, i.start, i.title.lower()) for d in week.days for i in d.items}
        for ev in recurring_ical_events.of(cal).between(start, end):
            if not keep_event(ev, self.cal):
                continue
            title = str(ev.get("SUMMARY", "")).strip()
            s, e = ev.decoded("DTSTART"), ev.decoded("DTEND") if ev.get("DTEND") else None
            if isinstance(s, datetime):
                s = s.astimezone(self.tz) if self.tz else s
                e = (e.astimezone(self.tz) if self.tz else e) if e else s
                day = week.day(s.date())
                key = (s.date(), f"{s:%H:%M}", title.lower())
                if day and key not in seen:
                    seen.add(key)
                    day.items.append(Item(f"{s:%H:%M}", f"{e:%H:%M}", title, self.name))
            else:
                last = (e - timedelta(1)) if e else s
                d = s
                while d <= last:
                    day = week.day(d)
                    if day and title not in day.notes:
                        day.notes.append(title)
                    d += timedelta(1)
        return []
