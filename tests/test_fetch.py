"""pull without a network: the guard fires first, and an empty set fails."""
import json

import pytest

from heldout import cli, config, fetch, rules

SMOKE = {"name": "smoke", "network": "NZ", "start": "2012-06-01T12:00:00",
         "end": "2012-06-01T12:01:00", "centre": [-41.284, 174.768], "radius_km": 30.0,
         "max_stations": 1}


class NoData:
    """A client whose archive has nothing."""
    calls = 0

    def get_waveforms(self, *a, **k):
        from obspy.clients.fdsn.header import FDSNNoDataException
        NoData.calls += 1
        raise FDSNNoDataException("no data")


class Forbidden:
    def __getattr__(self, name):
        raise AssertionError("the network was used")


def probed(tmp_path, cfg):
    out = tmp_path / cfg.name
    out.mkdir()
    chosen = [{"network": "NZ", "station": "WEL", "location": "10",
               "channels": ["HHZ", "HHN", "HHE"], "lat": -41.284, "lon": 174.768,
               "elevation_m": 138.0, "distance_km": 0.0, "ok": True, "reason": "",
               "coverage_min": 1.0}]
    (out / "stations.json").write_text(json.dumps(
        {"set": cfg.name, "config": cfg.to_json(), "span": [cfg.start.isoformat(),
         cfg.end.isoformat()], "probed": chosen, "chosen": chosen}))
    return out


def test_empty_pull_fails_and_writes_nothing(tmp_path, monkeypatch):
    cfg = config.parse(SMOKE)
    out = probed(tmp_path, cfg)
    monkeypatch.setattr(fetch, "client", lambda cfg: NoData())
    assert fetch.cmd_pull(cfg, tmp_path) == 2
    assert NoData.calls == 1                       # one hour-long request for 60 s
    assert not (out / "dataset.json").exists()
    assert sorted(p.name for p in out.iterdir()) == ["stations.json"]


def test_cli_exit_code_on_empty_set(tmp_path, monkeypatch):
    p = tmp_path / "smoke.toml"
    p.write_text("\n".join(f"{k} = {json.dumps(v)}" for k, v in SMOKE.items()))
    (tmp_path / "data").mkdir()
    probed(tmp_path / "data", config.load(p))
    monkeypatch.setattr(fetch, "client", lambda cfg: NoData())
    assert cli.main(["pull", str(p), "--data", str(tmp_path / "data")]) == 2


def test_pull_guard_fires_before_any_request(tmp_path, monkeypatch, capsys):
    cfg = config.parse({**SMOKE, "start": "2019-03-01T00:00:00", "end": "2019-03-01T01:00:00"})
    monkeypatch.setattr(fetch, "client", lambda cfg: Forbidden())
    with pytest.raises(rules.TestPeriodError):
        fetch.cmd_pull(cfg, tmp_path)
    p = tmp_path / "t.toml"
    p.write_text("\n".join(f"{k} = {json.dumps(v)}" for k, v in
                           {**SMOKE, "start": "2019-03-01T00:00:00",
                            "end": "2019-03-01T01:00:00"}.items()))
    assert cli.main(["pull", str(p), "--data", str(tmp_path)]) == 2
    assert "test period" in capsys.readouterr().err
    assert not any(tmp_path.glob("smoke/*"))


def test_catalog_guard_covers_the_lead_in(tmp_path, monkeypatch):
    # A span in 2018-01-10 has its 30-day lead-in before 2018 but itself is in.
    cfg = config.parse({**SMOKE, "start": "2018-01-10T00:00:00", "end": "2018-01-10T01:00:00"})
    with pytest.raises(rules.TestPeriodError, match="catalogue window"):
        fetch.cmd_catalog(cfg, tmp_path)
    # A 2012 span whose catalogue window was moved into the test period.
    cfg = config.parse({**SMOKE, "catalog": {"start": "2019-01-01T00:00:00",
                                             "end": "2019-01-02T00:00:00"}})
    with pytest.raises(rules.TestPeriodError):
        fetch.cmd_catalog(cfg, tmp_path)


def test_km_matches_the_old_tool():
    # fetch_ko_data.py: locations2degrees * 111.195; SIMA from demo_ko is 72.1 km.
    assert round(fetch.km(39.22333, 28.16556, 39.0833, 28.9825), 1) == 72.1
