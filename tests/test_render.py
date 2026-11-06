from dataclasses import replace
from pathlib import Path

import pymupdf as fitz
import pytest
from pypdf import PdfReader

from weekpage.model import load_week
from weekpage.render import NOTE_WIDTH, note_rows, render_html, render_pdf
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


def test_a_long_note_goes_on_over_the_next_row_at_a_word():
    assert note_rows(["Beach house", "Boat at nine, the north pier, then the lagoons"]) == [
        "Beach house", "Boat at nine, the north", "pier, then the lagoons"]
    assert note_rows(["short"]) == ["short", "", ""] and note_rows([]) == ["", "", ""]
    assert all(len(r) <= NOTE_WIDTH for r in note_rows(["x" * 60])), "a word longer than a row breaks and stays on the rows"


def test_notes_no_row_is_left_for_say_so():
    got = note_rows(["one", "two", "three", "four"])
    assert got == ["one", "two", "three\u2026"], "the page shows that something is missing"
    assert len(note_rows(["word " * 40])) == 3 and note_rows(["word " * 40])[2].endswith("\u2026")


def test_a_long_note_is_whole_on_the_page():
    week = load_week(WEEKS / "empty.json")
    week.days[0].notes[:] = ["Beach house", "Boat at nine, the north pier, then the lagoons"]
    html = render_html(week, S)
    assert '<div class="ln">Boat at nine, the north</div><div class="ln">pier, then the lagoons</div>' in html


def _note_widths(tmp_path, monkeypatch, rows):
    """How wide each note row's text is against its box, as Chromium draws the page with its own fonts. The
    rows are drawn as given: note_rows, which would wrap them, is set aside for this."""
    from playwright.sync_api import sync_playwright
    import weekpage.render as render
    monkeypatch.setattr(render, "note_rows", lambda notes: list(notes) + [""] * (3 - len(notes)))
    week = load_week(WEEKS / "empty.json")
    for day, row in zip(week.days, rows):
        day.notes[:] = [row]
    html = tmp_path / "n.html"
    html.write_text(render_html(week, S))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html.as_uri())
        page.evaluate("document.fonts.ready.then(() => true)")
        got = page.evaluate("""() => [...document.querySelectorAll('.notes')].map(n => {
            const ln = n.querySelector('.ln'); return [ln.textContent, ln.scrollWidth, ln.clientWidth] })""")
        browser.close()
    return got[:len(rows)]


def test_a_full_note_row_fits_its_box(tmp_path, monkeypatch):
    full, over = "W" * NOTE_WIDTH, "W" * (NOTE_WIDTH + 1)
    (t1, used1, box1), (t2, used2, box2) = _note_widths(tmp_path, monkeypatch, [full, over])
    assert (t1, t2) == (full, over), "the rows are drawn as given"
    assert used1 <= box1, f"a row of {NOTE_WIDTH} characters is cut: {used1}px of text in a {box1}px row"
    assert used2 > box2, f"a row holds more than {NOTE_WIDTH} characters, so NOTE_WIDTH cuts notes too early"


def test_a_day_can_have_its_own_work_band():
    from datetime import date
    from weekpage.model import Week, from_dict, to_dict
    from weekpage.settings import Work
    w = Week.empty(date(2026, 10, 19))
    w.days[3].work = Work(weekdays=[3], core=(8, 18), flex=[])
    back = from_dict(to_dict(w))
    assert back.days[3].work == Work(weekdays=[3], core=(8, 18), flex=[]) and back.days[2].work is None
    days = render_html(back, S).split('<div class="rows">')[1:]
    band = lambda day: (day.count('class="row core"'), day.count('class="row flex"'))
    assert band(days[3]) == (10, 0), f"Thursday has its own band, 08 to 18 and no flex: {band(days[3])}"
    assert band(days[2]) == (6, 3), f"Wednesday keeps the page's band, 11 to 17 and 3 flex hours: {band(days[2])}"
