"""A week view of a calendar, as a screenshot, to items. The geometry is pure and tested; the
text recognition is macOS Vision and only needed when reading a real picture."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from ..lines import DAYS
from ..model import Item

HOUR = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*([AaPp][Mm])?$")
LINKISH = re.compile(r"https?://|zoom\.us|meet\.google|teams\.microsoft", re.I)
CUT = ("...", "…")


@dataclass
class Read:
    items: list[tuple[date, Item]] = field(default_factory=list)
    all_day: list[tuple[date, str]] = field(default_factory=list)
    unseen: list[date] = field(default_factory=list)
    hour_columns: int = 0           # how many columns of hour labels the picture had (two for two time zones)


def _hour(text: str) -> float | None:
    m = HOUR.match(text.replace(" ", ""))
    if not m:
        return None
    h, mins, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
    if ap == "pm" and h != 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return h + mins / 60 if h < 24 and (ap or m.group(2)) else None


HOUR_COLUMNS = ("left", "right", "lower", "higher")


def _hour_axis(found: list[tuple[float, float, float]], hour_column: str) -> tuple[list[tuple[float, float]], int]:
    """The hour labels that make the time axis, from every hour label seen as (y, hour, x). A picture
    that shows two time zones has two columns of labels side by side, so the labels are grouped by row
    and one per row is kept: the leftmost or rightmost column, or the one whose hours are lower (the
    westward zone) or higher. Returns the axis sorted by y, and how many columns the rows had."""
    if hour_column not in HOUR_COLUMNS:
        raise ValueError(f"hour_column must be one of {HOUR_COLUMNS}, not {hour_column!r}")
    rows: list[list[tuple[float, float, float]]] = []
    for y, v, x in sorted(found):
        if rows and abs(y - rows[-1][0][0]) <= 12:
            rows[-1].append((y, v, x))
        else:
            rows.append([(y, v, x)])
    key = {"left": lambda r: r[2], "right": lambda r: -r[2], "lower": lambda r: r[1], "higher": lambda r: -r[1]}[hour_column]
    axis = sorted((min(row, key=key)[0], min(row, key=key)[1]) for row in rows)
    return axis, max((len(row) for row in rows), default=0)


def read_boxes(boxes, monday: date, source: str = "screenshot", hour_column: str = "left") -> Read:
    out = Read()
    heads = {}
    for x, y, w, h, t in boxes:
        k = t.strip().lower()[:3]
        if k in DAYS and len(t.strip()) <= 4 and any(abs(x2 - x) < 40 and 0 < y2 - y < 60 and t2.strip().isdigit()
                                                     for x2, y2, _, _, t2 in boxes):
            heads[DAYS.index(k)] = (x + w / 2, y)
    out.unseen = [monday + timedelta(i) for i in range(7) if i not in heads]
    if not heads:
        return out
    left = min(cx for cx, _ in heads.values()) - 120
    head_y = max(y for _, y in heads.values()) + 40
    # hour labels sit left of the first column; only whole hours count, so a "now" marker such
    # as 7:14PM is never a label
    found = [(y + h / 2, v, x) for x, y, w, h, t in boxes
             if x < left + 120 and (v := _hour(t.strip())) is not None and v == int(v)]
    labels, out.hour_columns = _hour_axis(found, hour_column)
    if len(labels) < 2:
        return out
    first_y = labels[0][0]

    def when(y: float) -> str:
        for (y1, v1), (y2, v2) in zip(labels, labels[1:]):
            if y <= y2 or (y2, v2) == labels[-1]:
                v = v1 + (y - y1) * (v2 - v1) / (y2 - y1)
                break
        mins = max(0, min(23 * 60 + 45, round(v * 60 / 15) * 15))
        return f"{mins // 60:02d}:{mins % 60:02d}"

    def column(x: float) -> int:
        return min(heads, key=lambda i: abs(heads[i][0] - x))

    cells = sorted((b for b in boxes if b[0] >= left + 40 and b[1] > head_y), key=lambda b: (b[0] // 200, b[1]))
    last = None   # (column, y bottom, index in out.items)
    for x, y, w, h, t in cells:
        t = t.strip()
        if not t or LINKISH.search(t) or len(t) < 3 or _hour(t) is not None:   # a time alone is a label
            continue
        col = column(x + 10)
        day = monday + timedelta(col)
        if y + h < first_y - 10:
            out.all_day.append((day, t))
            continue
        if last and last[0] == col and 0 <= y - last[1] < 40:
            d, it = out.items[last[2]]
            out.items[last[2]] = (d, Item(it.start, it.end, f"{it.title} {t}", source))
            last = (col, y + h, last[2])
            continue
        start = when(y)
        end_m = min(23 * 60 + 59, int(start[:2]) * 60 + int(start[3:]) + 60)
        out.items.append((day, Item(start, f"{end_m // 60:02d}:{end_m % 60:02d}", t, source)))
        last = (col, y + h, len(out.items) - 1)
    return out


def ocr(path: Path) -> list[list]:
    """Text boxes [x, y, w, h, text] in pixels from the top left, with macOS Vision."""
    import Quartz
    import Vision
    from Foundation import NSURL
    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(str(path)), None)
    img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    W, H = Quartz.CGImageGetWidth(img), Quartz.CGImageGetHeight(img)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setUsesLanguageCorrection_(False)
    Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None).performRequests_error_([req], None)
    out = []
    for o in req.results():
        b = o.boundingBox()
        out.append([b.origin.x * W, (1 - b.origin.y - b.size.height) * H, b.size.width * W,
                    b.size.height * H, str(o.topCandidates_(1)[0].string())])
    return out


class ScreenshotSource:
    """Adds the events of a week-view screenshot. All-day bars become day notes only when
    `keep_all_day` is set, because on a shared work calendar they are usually other people's."""
    name = "screenshot"

    def __init__(self, path: Path, keep_all_day: bool = False, source: str = "screenshot",
                 hour_column: str = "left"):
        self.path, self.keep_all_day, self.source = Path(path), keep_all_day, source
        self.hour_column = hour_column          # which hour column is the axis when the picture shows two zones
        self.last: Read | None = None

    def fill(self, week, settings) -> list[str]:
        try:
            r = read_boxes(ocr(self.path), week.monday, self.source, hour_column=self.hour_column)
        except ImportError:
            return ["reading a screenshot needs macOS (its built-in text recognition)"]
        self.last = r
        for d, it in r.items:
            if (day := week.day(d)):
                day.items.append(it)
        if self.keep_all_day:
            for d, t in r.all_day:
                if (day := week.day(d)):
                    day.notes.append(t)
        return [f"screenshot does not show {d:%A %d/%m}" for d in r.unseen]
