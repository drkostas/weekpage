"""Week + Settings -> one HTML page -> an A4 landscape PDF, printed by Chromium."""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .model import Week
from .settings import Settings
from .slots import place

HERE = Path(__file__).parent
TEMPLATES = HERE / "templates"
FONTS = HERE / "fonts"


def _data_uri(p: Path | None) -> str | None:
    if not p:
        return None
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(Path(p).read_bytes()).decode()}"


def render_html(week: Week, s: Settings) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
    css = env.get_template("page.css").render(fonts=FONTS.as_uri())
    return env.get_template("page.html.j2").render(
        week=week, s=s, css=css, icons=env.get_template("icons.svg.j2").render(),
        rows=[place(d.items, s.hours) for d in week.days],
        pics={"banner": _data_uri(s.art.banner), "left": _data_uri(s.art.left.image),
              "right": _data_uri(s.art.right.image)})


def render_pdf(week: Week, s: Settings, out: Path) -> Path:
    from playwright.sync_api import sync_playwright
    out = Path(out)
    html = out.with_suffix(".html")
    html.write_text(render_html(week, s))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html.as_uri())
        page.evaluate("document.fonts.ready")
        page.pdf(path=str(out), width="297mm", height="210mm", print_background=True,
                 margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}, prefer_css_page_size=True)
        browser.close()
    return out
