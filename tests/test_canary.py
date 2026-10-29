"""The canary: a catalogue service that returns too little for a fixed past
window known to contain events is not trusted, and nothing is written."""
import datetime as dt
import json

import pytest

from heldout import catalog, config, fetch, networks, rules
from heldout.catalog import Event

SMOKE = {"name": "smoke", "network": "NZ", "start": "2012-06-01T12:00:00",
         "end": "2012-06-01T12:01:00", "centre": [-41.284, 174.768], "radius_km": 30.0,
         "max_stations": 1}


def test_every_network_has_a_canary_before_its_pool():
    for code, info in networks.NETWORKS.items():
        c = info.canary
        assert c is not None and c.min_events >= 1, code
        start, end = dt.datetime.fromisoformat(c.start), dt.datetime.fromisoformat(c.end)
        assert start < end <= rules.POOL_START[code], code


def events(n):
    return [Event(time=dt.datetime(2022, 1, 27, 6, 0, i), lat=-41.3, lon=174.8,
                  depth_km=10.0, magnitude=2.0, mag_type="MLv", rms=None, location="",
                  event_id=str(i)) for i in range(n)]


def test_an_empty_canary_stops_the_catalog_step(tmp_path, monkeypatch, capsys):
    cfg = config.parse(SMOKE)
    out = tmp_path / cfg.name
    out.mkdir()
    before = json.dumps({"set": cfg.name})
    (out / "dataset.json").write_text(before)
    calls = []

    def fetch_fdsn(url, t0, t1, *a, **k):
        calls.append((t0, t1))
        return [], url
    monkeypatch.setattr(catalog, "fetch_fdsn", fetch_fdsn)
    assert fetch.cmd_catalog(cfg, tmp_path) == 3
    c = networks.NETWORKS["NZ"].canary
    assert calls == [(dt.datetime.fromisoformat(c.start), dt.datetime.fromisoformat(c.end))]
    assert not (out / "catalog.csv").exists()
    assert (out / "dataset.json").read_text() == before
    assert "not trusted" in capsys.readouterr().err


def test_a_canary_that_answers_is_recorded(monkeypatch):
    info = networks.NETWORKS["NZ"]
    monkeypatch.setattr(catalog, "fetch_fdsn",
                        lambda url, *a, **k: (events(info.canary.min_events), url + "?q"))
    got = catalog.canary(info)
    assert got["events"] == got["min_events"] == info.canary.min_events
    assert got["window"] == [info.canary.start, info.canary.end]
    assert got["request"] == info.event_url + "?q"
    monkeypatch.setattr(catalog, "fetch_fdsn",
                        lambda url, *a, **k: (events(info.canary.min_events - 1), url))
    with pytest.raises(catalog.CanaryError, match="canary window"):
        catalog.canary(info)
