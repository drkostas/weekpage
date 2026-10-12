"""Generic calendar clean-up. Choices about one person's life belong to whoever runs the package."""
from __future__ import annotations

from datetime import datetime

from .settings import Calendar


def keep_event(ev, cal: Calendar) -> bool:
    if str(ev.get("STATUS", "")).upper() == "CANCELLED":
        return False
    me = {m.lower() for m in cal.me}
    attendees = ev.get("ATTENDEE", [])
    for a in attendees if isinstance(attendees, list) else [attendees]:
        if str(a).lower().removeprefix("mailto:") in me and str(a.params.get("PARTSTAT", "")).upper() == "DECLINED":
            return False
    all_day = not isinstance(ev.decoded("DTSTART"), datetime)
    title = str(ev.get("SUMMARY", "")).lower()
    return not (all_day and any(w.lower() in title for w in cal.skip))
