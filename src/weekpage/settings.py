"""One TOML file decides what the page looks like and where its data comes from."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DAY_COLOURS = ["#1f6e8d", "#e87139", "#3f8f6a", "#6c3ec4", "#d9453b", "#f4c22f", "#2f8fb9"]
# the day names, darker where a bar colour is too light to read as text
NAME_COLOURS = ["#1f6687", "#a8471d", "#2f6b4d", "#55309f", "#a8342c", "#826410", "#24688a"]


@dataclass
class Work:
    weekdays: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    core: tuple[int, int] | None = (11, 17)
    flex: list[tuple[int, int]] = field(default_factory=lambda: [(9, 11), (17, 18)])

    def shade(self, weekday: int, hour: int) -> str | None:
        if weekday not in self.weekdays:
            return None
        if self.core and self.core[0] <= hour < self.core[1]:
            return "core"
        return "flex" if any(a <= hour < b for a, b in self.flex) else None


@dataclass
class Tick:
    name: str
    icon: str
    colour: str = "#333333"


@dataclass
class Walks:
    label: str = "Walk"
    count: int = 0
    icon: str = "paw"


@dataclass
class Colours:
    page: str = "#f8f5ee"
    days: list[str] = field(default_factory=lambda: list(DAY_COLOURS))
    names: list[str] = field(default_factory=lambda: list(NAME_COLOURS))
    work_core: str = "#dcebf2"
    work_flex: str = "#edf5f8"


@dataclass
class Picture:
    image: Path | None = None
    caption: str = ""


@dataclass
class Art:
    banner: Path | None = None
    left: Picture = field(default_factory=Picture)
    right: Picture = field(default_factory=Picture)


@dataclass
class Spot:
    label: str
    name: str
    lat: float
    lon: float
    wind_from: tuple[int, int]
    extra: dict = field(default_factory=dict)      # keys a source of your own reads, such as a site's spot id

    def covers(self, deg: float) -> bool:
        a, b = self.wind_from
        d = deg % 360
        return a <= d <= b if a <= b else (d >= a or d <= b)


@dataclass
class WindRule:
    min_knots: int = 15
    min_hours: int = 2
    spots: list[Spot] = field(default_factory=list)


@dataclass
class Calendar:
    name: str
    ics: str
    me: list[str] = field(default_factory=list)
    skip: list[str] = field(default_factory=list)


@dataclass
class Settings:
    title: tuple[str, str] = ("Weekly", "Log")
    hours: tuple[int, int] = (7, 22)
    work: Work = field(default_factory=Work)
    walks: Walks = field(default_factory=Walks)
    ticks: list[Tick] = field(default_factory=list)
    colours: Colours = field(default_factory=Colours)
    art: Art = field(default_factory=Art)
    wind: WindRule = field(default_factory=WindRule)
    calendars: list[Calendar] = field(default_factory=list)


def _path(base: Path, v: str | None) -> Path | None:
    return (base / v) if v else None


def _spot(d: dict) -> Spot:
    known = {"label", "name", "lat", "lon", "wind_from"}
    return Spot(label=d["label"], name=d["name"], lat=d["lat"], lon=d["lon"], wind_from=tuple(d["wind_from"]),
                extra={k: v for k, v in d.items() if k not in known})


def load_settings(path: Path) -> Settings:
    path = Path(path)
    d = tomllib.loads(path.read_text())
    base = path.parent
    w = d.get("work", {})
    work = Work(weekdays=w.get("weekdays", [0, 1, 2, 3, 4]),
                core=tuple(w["core"]) if w.get("core") else (None if "core" in w else (11, 17)),
                flex=[tuple(x) for x in w.get("flex", [(9, 11), (17, 18)])])
    a = d.get("art", {})
    pic = lambda x: Picture(_path(base, (x or {}).get("image")), (x or {}).get("caption", ""))
    wd = d.get("wind", {})
    return Settings(
        title=tuple(d.get("title", ["Weekly", "Log"])),
        hours=tuple(d.get("hours", [7, 22])),
        work=work,
        walks=Walks(**d.get("walks", {})),
        ticks=[Tick(**t) for t in d.get("ticks", [])],
        colours=Colours(**d.get("colours", {})),
        art=Art(_path(base, a.get("banner")), pic(a.get("left")), pic(a.get("right"))),
        wind=WindRule(min_knots=wd.get("min_knots", 15), min_hours=wd.get("min_hours", 2),
                      spots=[_spot(s) for s in wd.get("spots", [])]),
        calendars=[Calendar(**c) for c in d.get("calendars", [])],
    )
