"""Which items appear in which hour row."""
from __future__ import annotations

from dataclasses import dataclass, field

from .model import Item

PER_ROW = 2


@dataclass
class Row:
    hour: int
    shown: list[Item] = field(default_factory=list)
    more: int = 0


def place(items: list[Item], hours: tuple[int, int]) -> list[Row]:
    first, last = hours
    rows = {h: [] for h in range(first, last + 1)}
    for it in sorted(items, key=lambda i: i.start):          # same start: keep the given order
        rows[min(max(it.hour, first), last)].append(it)
    return [Row(h, xs[:PER_ROW], max(0, len(xs) - PER_ROW)) for h, xs in rows.items()]
