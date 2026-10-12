"""Items given directly: a JSON file with items, day notes and week notes."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..model import Item, Week
from ..settings import Settings


class GivenSource:
    name = "given"

    def __init__(self, path: Path, source: str = "given"):
        self.path, self.source = Path(path), source

    def fill(self, week: Week, settings: Settings) -> list[str]:
        d = json.loads(self.path.read_text())
        for x in d.get("items", []):
            day = week.day(date.fromisoformat(x["date"]))
            if day:
                day.items.append(Item(x["start"], x.get("end", x["start"]), x["title"], x.get("source", self.source)))
        for x in d.get("notes", []):
            day = week.day(date.fromisoformat(x["date"]))
            if day:
                day.notes.append(x["text"])
        for x in d.get("off", []):
            day = week.day(date.fromisoformat(x["date"]))
            if day:
                day.off = x["name"]
        week.notes.extend(d.get("week", []))
        return []
