from pathlib import Path
from weekpage.settings import load_settings, Spot

EX = Path(__file__).parents[1] / "examples" / "settings.toml"


def test_the_example_loads():
    s = load_settings(EX)
    assert s.hours == (7, 22) and s.work.core == (11, 17) and s.work.flex == [(9, 11), (17, 18)]
    assert [t.name for t in s.ticks] == ["workout", "run", "kite", "trip"]
    assert s.wind.spots[0].label == "N" and s.wind.min_knots == 15
    assert len(s.colours.days) == 7


def test_a_sector_can_wrap_through_north():
    north = Spot(label="N", name="n", lat=0, lon=0, wind_from=(300, 60))
    assert north.covers(350) and north.covers(10) and not north.covers(180)
    south = Spot(label="S", name="s", lat=0, lon=0, wind_from=(120, 240))
    assert south.covers(180) and not south.covers(10)


def test_art_paths_resolve_next_to_the_settings_file(tmp_path):
    (tmp_path / "b.png").write_bytes(b"x")
    (tmp_path / "s.toml").write_text('[art]\nbanner = "b.png"\n')
    assert load_settings(tmp_path / "s.toml").art.banner == tmp_path / "b.png"


def test_defaults_fill_what_a_file_leaves_out(tmp_path):
    (tmp_path / "s.toml").write_text("")
    s = load_settings(tmp_path / "s.toml")
    assert s.hours == (7, 22) and s.ticks == [] and s.wind.spots == [] and s.art.banner is None


def test_a_spot_keeps_keys_of_its_own(tmp_path):
    (tmp_path / "s.toml").write_text('[[wind.spots]]\nlabel = "N"\nname = "n"\nlat = 1\nlon = 2\n'
                                     'wind_from = [300, 60]\nsite_id = 153\n')
    assert load_settings(tmp_path / "s.toml").wind.spots[0].extra == {"site_id": 153}
