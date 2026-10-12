"""A source adds what it knows to a week and returns warnings, never raises for a bad answer."""
from __future__ import annotations

from typing import Protocol

from ..model import Week
from ..settings import Settings


class Source(Protocol):
    name: str

    def fill(self, week: Week, settings: Settings) -> list[str]: ...
