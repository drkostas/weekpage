"""weekpage gather | render | print"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .gather import default_sources, gather, next_monday
from .model import load_week, save_week
from .printer import lp_command, send
from .render import render_pdf
from .settings import load_settings
from .sources.given import GivenSource


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="weekpage")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gather", help="collect a week into week.json")
    g.add_argument("-s", "--settings", required=True)
    g.add_argument("--monday", type=date.fromisoformat, default=None)
    g.add_argument("--given", action="append", default=[], help="a JSON file of items to add")
    g.add_argument("-o", "--out", default="week.json")
    r = sub.add_parser("render", help="draw week.json as a PDF")
    r.add_argument("week")
    r.add_argument("-s", "--settings", required=True)
    r.add_argument("-o", "--out", default="week.pdf")
    p = sub.add_parser("print", help="send a PDF to a printer")
    p.add_argument("pdf")
    p.add_argument("--printer", default=None)
    p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "gather":
        s = load_settings(Path(a.settings))
        week, warnings = gather(a.monday or next_monday(date.today()), s,
                                [*default_sources(s), *(GivenSource(Path(x)) for x in a.given)])
        save_week(week, Path(a.out))
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        print(a.out)
    elif a.cmd == "render":
        print(render_pdf(load_week(Path(a.week)), load_settings(Path(a.settings)), Path(a.out)))
    else:
        if a.dry_run:
            print(" ".join(lp_command(Path(a.pdf), a.printer)))
        else:
            print(send(Path(a.pdf), a.printer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
