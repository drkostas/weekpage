"""Send a PDF to a CUPS printer queue."""
from __future__ import annotations

import subprocess
from pathlib import Path


def lp_command(pdf: Path, printer: str | None) -> list[str]:
    return ["lp", *(["-d", printer] if printer else []), "-o", "media=A4", "-o", "fit-to-page", str(pdf)]


def send(pdf: Path, printer: str | None = None, env=None) -> str:
    r = subprocess.run(lp_command(pdf, printer), capture_output=True, text=True, check=True, env=env)
    return r.stdout.strip()      # "request id is Office-12 (1 file(s))"
