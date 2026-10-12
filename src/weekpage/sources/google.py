"""Google Calendar through its API, with a refresh token the user already has."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable
from urllib.parse import quote

import httpx

from ..model import Item, Week
from ..settings import Settings

API = "https://www.googleapis.com/calendar/v3/calendars/{cal}/events"
SKIP_TYPES = {"outOfOffice", "workingLocation", "birthday", "focusTime"}


def refresh_token_getter(client_id: str, client_secret: str, refresh_token: str) -> Callable[[], str]:
    def get() -> str:
        r = httpx.post("https://oauth2.googleapis.com/token", timeout=30, data={
            "client_id": client_id, "client_secret": client_secret,
            "refresh_token": refresh_token, "grant_type": "refresh_token"})
        if r.status_code in (400, 401):
            raise PermissionError(r.json().get("error", "refresh refused"))
        r.raise_for_status()
        return r.json()["access_token"]
    return get


def _fetch(cal: str, token: str, start: str, end: str) -> dict:
    r = httpx.get(API.format(cal=quote(cal, safe="")), timeout=30,
                  headers={"Authorization": f"Bearer {token}"},
                  params={"timeMin": start, "timeMax": end, "singleEvents": "true", "orderBy": "startTime",
                          "maxResults": 250})
    if r.status_code in (401, 403):
        raise PermissionError(f"HTTP {r.status_code}")
    r.raise_for_status()
    return r.json()


class GoogleCalendarSource:
    def __init__(self, name: str, calendar_id: str, token: Callable[[], str],
                 fetch: Callable[[str, str, str, str], dict] = _fetch, tz=None):
        self.name, self.cal, self.token, self.fetch, self.tz = f"calendar:{name}", calendar_id, token, fetch, tz
        self.label = name

    def fill(self, week: Week, settings: Settings) -> list[str]:
        start = datetime.combine(week.monday, datetime.min.time()).astimezone(self.tz)
        try:
            data = self.fetch(self.cal, self.token(), start.isoformat(), (start + timedelta(7)).isoformat())
        except Exception as e:
            return [f"calendar {self.label} could not be read: {e}"]
        seen = set()
        for ev in data.get("items", []):
            if ev.get("status") == "cancelled" or ev.get("eventType") in SKIP_TYPES or ev.get("id") in seen:
                continue
            seen.add(ev.get("id"))
            if any(a.get("self") and a.get("responseStatus") == "declined" for a in ev.get("attendees", [])):
                continue
            title = (ev.get("summary") or "").strip() or "(no title)"
            s, e = ev.get("start", {}), ev.get("end", {})
            if "dateTime" in s:
                a = datetime.fromisoformat(s["dateTime"]).astimezone(self.tz)
                b = datetime.fromisoformat(e.get("dateTime", s["dateTime"])).astimezone(self.tz)
                if (day := week.day(a.date())):
                    day.items.append(Item(f"{a:%H:%M}", f"{b:%H:%M}", title, self.name))
            elif "date" in s:
                d, last = date.fromisoformat(s["date"]), date.fromisoformat(e.get("date", s["date"])) - timedelta(1)
                while d <= last:
                    if (day := week.day(d)) and title not in day.notes:
                        day.notes.append(title)
                    d += timedelta(1)
        return []
