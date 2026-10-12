from datetime import date
from weekpage.gather import gather, next_monday
from weekpage.settings import Settings


class Fake:
    name = "fake"
    def __init__(self, warn): self.warn = warn
    def fill(self, week, s):
        week.notes.append(self.name)
        return self.warn


def test_next_monday():
    assert next_monday(date(2026, 10, 13)) == date(2026, 10, 19)
    assert next_monday(date(2026, 10, 19)) == date(2026, 10, 19)    # on a Monday, that week


def test_every_source_runs_and_warnings_are_collected():
    week, warnings = gather(date(2026, 10, 19), Settings(), [Fake([]), Fake(["x down"])])
    assert week.notes == ["fake", "fake"] and warnings == ["x down"]


def test_a_source_that_raises_becomes_a_warning():
    class Bad:
        name = "bad"
        def fill(self, w, s): raise RuntimeError("boom")
    _, warnings = gather(date(2026, 10, 19), Settings(), [Bad()])
    assert warnings == ["bad failed: boom"]
