import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def run(*a):
    return subprocess.run([sys.executable, "-m", "weekpage.cli", *a], capture_output=True, text=True, cwd=ROOT)


def test_render_makes_a_pdf(tmp_path):
    r = run("render", "examples/week.json", "-s", "examples/settings.toml", "-o", str(tmp_path / "w.pdf"))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "w.pdf").read_bytes()[:5] == b"%PDF-"


def test_print_dry_run_shows_the_lp_command(tmp_path):
    pdf = tmp_path / "w.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    r = run("print", str(pdf), "--printer", "Office", "--dry-run")
    assert r.returncode == 0 and r.stdout.split() == ["lp", "-d", "Office", "-o", "media=A4", "-o", "fit-to-page", str(pdf)]
