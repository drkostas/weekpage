from dataclasses import replace
from pathlib import Path

import pymupdf as fitz
import pytest
from pypdf import PdfReader

from weekpage.model import load_week
from weekpage.render import render_html, render_pdf
from weekpage.settings import Art, load_settings

ROOT = Path(__file__).parents[1]
S = load_settings(ROOT / "examples" / "settings.toml")
WEEKS = ROOT / "tests" / "data" / "weeks"
GOLDEN = ROOT / "tests" / "data" / "golden"


@pytest.mark.parametrize("name", ["empty", "busy", "holiday", "full_hour"])
def test_one_a4_landscape_page_with_real_text(tmp_path, name):
    out = render_pdf(load_week(WEEKS / f"{name}.json"), S, tmp_path / "w.pdf")
    page = PdfReader(out).pages[0]
    assert len(PdfReader(out).pages) == 1
    assert (round(float(page.mediabox.width)), round(float(page.mediabox.height))) == (842, 595)
    text = page.extract_text().replace(" ", "")      # letter-spaced labels come out as "N O T E S"
    assert "Monday" in text and "Sunday" in text and "NOTESFORTHEWEEK" in text


def test_items_holiday_and_overflow_are_on_the_page(tmp_path):
    text = PdfReader(render_pdf(load_week(WEEKS / "holiday.json"), S, tmp_path / "h.pdf")).pages[0].extract_text()
    assert "Public holiday" in text
    text = PdfReader(render_pdf(load_week(WEEKS / "full_hour.json"), S, tmp_path / "f.pdf")).pages[0].extract_text()
    assert "+2" in text


def test_a_holiday_does_not_move_the_hour_rows(tmp_path):
    from weekpage.render import render_html
    import re
    html = render_html(load_week(WEEKS / "holiday.json"), S)
    assert html.index('class="rows"') < html.index('class="off"')     # the label sits inside the rows, positioned


def test_text_is_vector_and_the_only_pictures_are_the_art(tmp_path):
    doc = fitz.open(render_pdf(load_week(WEEKS / "busy.json"), S, tmp_path / "b.pdf"))
    assert len(doc[0].get_images()) == 3      # the banner and the two corner pictures
    assert len(doc[0].get_fonts()) >= 2       # the display serif and the mono
    plain = replace(S, art=Art())
    doc = fitz.open(render_pdf(load_week(WEEKS / "busy.json"), plain, tmp_path / "p.pdf"))
    assert doc[0].get_images() == []          # without art the whole page is vector


@pytest.mark.parametrize("name", ["empty", "busy", "holiday", "full_hour"])
def test_looks_like_the_approved_render(tmp_path, name):
    doc = fitz.open(render_pdf(load_week(WEEKS / f"{name}.json"), S, tmp_path / "x.pdf"))
    got = doc[0].get_pixmap(dpi=60).samples
    want = fitz.Pixmap(str(GOLDEN / f"{name}.png")).samples
    assert len(got) == len(want)
    diff = sum(abs(a - b) > 40 for a, b in zip(got, want)) / len(got)
    assert diff < 0.01, f"{name} differs from its golden image in {diff:.1%} of the bytes"


def test_temperature_and_wind_arrow_are_drawn():
    from datetime import date
    from weekpage.model import Week, Wind
    w = Week.empty(date(2026, 10, 19))
    w.days[0].wind = Wind(knots=22, side="N", kiteable=True, sky="sun", temp=24, deg=45, source="forecast")
    w.days[1].wind = Wind(knots=10, side="S", kiteable=False, sky="cloud", temp=None, deg=None, source="forecast")
    html = render_html(w, S)
    assert "24&deg;" in html                               # the day's temperature
    assert 'class="dir"' in html and "rotate(225deg)" in html   # the arrow, rotated to deg + 180
    assert html.count("rotate(") == 1                      # the day with no bearing draws no arrow


def test_greek_and_cyrillic_use_a_mono_that_has_them(tmp_path):
    from datetime import date
    from weekpage.model import Item, Week
    w = Week.empty(date(2026, 10, 19))
    w.days[1].items.append(Item("17:00", "18:00", "Καλημέρα κόσμε", "given"))
    w.days[2].items.append(Item("10:00", "11:00", "Встреча", "given"))
    doc = fitz.open(render_pdf(w, S, tmp_path / "g.pdf"))
    names = [f[3] for f in doc[0].get_fonts()]
    assert any("FiraMono" in n for n in names) and not any("Times" in n for n in names)
