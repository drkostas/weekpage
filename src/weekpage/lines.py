"""One line of text ("Wed 18:00-19:00 Physio") to a day and an item."""
from __future__ import annotations

import re
from datetime import date, timedelta

from .model import Item

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
LINE = re.compile(r"^\s*([a-z]{3})[a-z]*\.?\s+(\d{1,2})(?::(\d{2}))?(?:\s*-\s*(\d{1,2})(?::(\d{2}))?)?\s+(.+?)\s*$", re.I)


def parse_line(text: str, monday: date, source: str = "given") -> tuple[date, Item]:
    m = LINE.match(text or "")
    if not m or m.group(1).lower() not in DAYS:
        raise ValueError(f"expected 'Day HH:MM[-HH:MM] Title', got {text!r}")
    d, h1, m1, h2, m2, title = m.groups()
    start = int(h1) * 60 + int(m1 or 0)
    end = int(h2) * 60 + int(m2 or 0) if h2 else start + 60
    if not (0 <= start < 24 * 60 and start < end <= 24 * 60):
        raise ValueError(f"times out of range in {text!r}")
    fmt = lambda t: f"{min(t, 23 * 60 + 59) // 60:02d}:{min(t, 23 * 60 + 59) % 60:02d}"
    return monday + timedelta(DAYS.index(d.lower())), Item(fmt(start), fmt(end), title, source)
