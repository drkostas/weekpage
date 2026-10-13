"""The week as data. The page draws only what is in here, and every item says where it came from."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@dataclass
class Item:
    start: str
    end: str
    title: str
    source: str

    def __post_init__(self):
        for t in (self.start, self.end):
            if not HHMM.match(t):
                raise ValueError(f"time must be HH:MM, got {t!r}")

    @property
    def hour(self) -> int:
        return int(self.start[:2])


@dataclass
class Wind:
    knots: int
    side: str          # the spot's label, for example "N" or "S"
    kiteable: bool
    sky: str           # sun | cloud | drizzle | rain
    source: str
    temp: int | None = None   # the day's high in degrees Celsius, when the source has it
    deg: int | None = None    # the wind's bearing (where it comes from) at the day's strongest hour


@dataclass
class Day:
    date: date
    items: list[Item] = field(default_factory=list)
    off: str | None = None          # a holiday name: no work band that day
    notes: list[str] = field(default_factory=list)
    wind: Wind | None = None


@dataclass
class Week:
    monday: date
    days: list[Day]
    notes: list[str] = field(default_factory=list)

    @classmethod
    def empty(cls, monday: date) -> "Week":
        if monday.weekday() != 0:
            raise ValueError(f"a week starts on a Monday, {monday} is not one")
        return cls(monday, [Day(monday + timedelta(i)) for i in range(7)])

    @property
    def title(self) -> str:
        sun = self.monday + timedelta(6)
        return f"{self.monday:%d/%m} - {sun:%d/%m}"

    def day(self, d: date) -> Day | None:
        return next((x for x in self.days if x.date == d), None)


def to_dict(w: Week) -> dict:
    out = asdict(w)
    out["monday"] = w.monday.isoformat()
    for d in out["days"]:
        d["date"] = d["date"].isoformat()
    return out


def from_dict(d: dict) -> Week:
    days = [Day(date=date.fromisoformat(x["date"]),
                items=[Item(**i) for i in x.get("items", [])],
                off=x.get("off"), notes=list(x.get("notes", [])),
                wind=Wind(**x["wind"]) if x.get("wind") else None) for x in d["days"]]
    return Week(date.fromisoformat(d["monday"]), days, list(d.get("notes", [])))


def save_week(w: Week, path: Path) -> None:
    Path(path).write_text(json.dumps(to_dict(w), indent=2, ensure_ascii=False) + "\n")


def load_week(path: Path) -> Week:
    return from_dict(json.loads(Path(path).read_text()))
