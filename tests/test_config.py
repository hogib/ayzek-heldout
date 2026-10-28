import datetime as dt

import pytest

from heldout import config
from heldout.config import ConfigError

BASE = {"name": "demo_ko", "network": "KO", "start": "2025-11-10T18:04:00",
        "end": "2025-11-10T18:35:00", "centre": [39.22333, 28.16556],
        "radius_km": 150.0, "max_stations": 6}


def test_parses_the_demo_set(tmp_path):
    p = tmp_path / "demo_ko.toml"
    p.write_text('name = "demo_ko"\nnetwork = "KO"\nstart = "2025-11-10T18:04:00"\n'
                 'end = "2025-11-10T18:35:00"\ncentre = [39.22333, 28.16556]\n'
                 "radius_km = 150.0\nmax_stations = 6\n")
    c = config.load(p)
    assert c.networks == ("KO",)
    assert c.start == dt.datetime(2025, 11, 10, 18, 4)
    assert (c.lat, c.lon, c.radius_km, c.max_stations) == (39.22333, 28.16556, 150.0, 6)
    assert c.min_coverage == 0.9
    assert c.catalog_window() == (dt.datetime(2025, 10, 11, 18, 4), c.end)
    assert c.catalog_radius_km() == 300.0


def test_shipped_sets_parse():
    from pathlib import Path
    sets = sorted((Path(__file__).parents[1] / "sets").glob("*.toml"))
    assert sets
    for p in sets:
        c = config.load(p)
        assert c.name == p.stem


def test_unquoted_toml_datetime_and_z_suffix():
    import tomllib
    d = tomllib.loads('start = 2012-06-01T12:00:00Z\nend = "2012-06-01T12:01:00Z"')
    c = config.parse({**BASE, **d})
    assert c.start == dt.datetime(2012, 6, 1, 12) and c.end == dt.datetime(2012, 6, 1, 12, 1)


def test_greek_pair_shares_the_noa_node():
    c = config.parse({**BASE, "network": ["HL", "HT"]})
    assert c.networks == ("HL", "HT")
    with pytest.raises(ConfigError, match="share a service"):
        config.parse({**BASE, "network": ["HL", "NZ"]})


def test_catalog_overrides():
    c = config.parse({**BASE, "catalog": {"start": "2012-06-01T00:00:00",
                                          "end": "2012-06-02T00:00:00", "limit": 3,
                                          "radius_km": 500}})
    assert c.catalog_window() == (dt.datetime(2012, 6, 1), dt.datetime(2012, 6, 2))
    assert c.catalog.limit == 3 and c.catalog_radius_km() == 500


@pytest.mark.parametrize("change, match", [
    ({"network": "XX"}, "unknown network"),
    ({"end": "2025-11-10T18:00:00"}, "not after"),
    ({"start": "yesterday"}, "not an ISO time"),
    ({"centre": [95, 0]}, "out of range"),
    ({"centre": [1]}, r"\[lat, lon\]"),
    ({"radius_km": 0}, "radius_km"),
    ({"radius_km": "150"}, "must be a number"),
    ({"max_stations": 0}, "at least 1"),
    ({"max_stations": 2.5}, "integer"),
    ({"min_coverage": 1.5}, "min_coverage"),
    ({"name": "Demo KO"}, "name"),
    ({"stations": 6}, "unknown keys"),
    ({"catalog": {"start": "2012-06-01T00:00:00"}}, "go together"),
    ({"catalog": {"radius": 3}}, "unknown catalog keys"),
])
def test_rejects(change, match):
    with pytest.raises(ConfigError, match=match):
        config.parse({**BASE, **change})


def test_missing_key():
    d = dict(BASE)
    del d["radius_km"]
    with pytest.raises(ConfigError, match="missing 'radius_km'"):
        config.parse(d)


def test_azimuth_limit():
    assert config.parse(BASE).max_azimuth_offset_deg is None
    assert config.parse({**BASE, "max_azimuth_offset_deg": 5}).max_azimuth_offset_deg == 5.0
    with pytest.raises(ConfigError):
        config.parse({**BASE, "max_azimuth_offset_deg": 200})
