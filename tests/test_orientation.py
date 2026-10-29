"""Orientations that cannot be rotated to N/E: the probe refuses them, and a
rotation that fails in pull drops the station, not the set.

Fixture tests/fixtures/NZ.MKTZ.epochs.csv: MKTZ's rows of
survey/out/nz_epochs.csv (GeoNet station metadata already on disk; no request
made): from 2025-09-30T19:58 HH1 has azimuth 0, dip 0 and HH2 azimuth 0, dip 90,
along HHZ.
"""
import csv
import datetime as dt
import json
from pathlib import Path

import pytest
from obspy import UTCDateTime
from obspy.core.inventory import Channel, Inventory, Network, Station

from heldout import config, fetch, rules

FIX = Path(__file__).parent / "fixtures"
T0, T1 = dt.datetime(2025, 1, 1), dt.datetime(2026, 1, 1)
ZNE12 = ("HHZ", "HH1", "HH2")


def ep(code, az, dip, start=T0, end=None):
    return rules.ChannelEpoch("10", code, 100.0, start, end, az, dip)


def mktz_rows():
    with open(FIX / "NZ.MKTZ.epochs.csv", newline="") as f:
        return list(csv.DictReader(f))


def mktz_epochs():
    return [rules.ChannelEpoch(r["location"], r["channel"], float(r["sample_rate"]),
                               dt.datetime.fromisoformat(r["start"]),
                               dt.datetime.fromisoformat(r["end"]) if r["end"] else None,
                               float(r["azimuth"]), float(r["dip"]))
            for r in mktz_rows()]


# ---- orientations -------------------------------------------------------------

def test_orientation_det_synthetic():
    assert abs(rules.orientation_det([ep("HHZ", 0, -90), ep("HH1", 0, 0), ep("HH2", 90, 0)],
                                     "10", ZNE12, T0, T1) - 1.0) < 1e-12
    # Horizontals turned 30 degrees are still independent: rotatable.
    assert abs(rules.orientation_det([ep("HHZ", 0, -90), ep("HH1", 30, 0), ep("HH2", 120, 0)],
                                     "10", ZNE12, T0, T1) - 1.0) < 1e-12
    # Both horizontals along north: degenerate.
    assert rules.orientation_det([ep("HHZ", 0, -90), ep("HH1", 0, 0), ep("HH2", 0, 0)],
                                 "10", ZNE12, T0, T1) < 1e-12
    # A missing dip gives no verdict.
    assert rules.orientation_det([ep("HHZ", 0, None), ep("HH1", 0, 0), ep("HH2", 90, 0)],
                                 "10", ZNE12, T0, T1) is None


def test_mktz_after_its_metadata_change_cannot_be_rotated():
    eps = mktz_epochs()
    before = (dt.datetime(2025, 3, 1), dt.datetime(2025, 9, 1))
    after = (dt.datetime(2025, 10, 1), dt.datetime(2025, 10, 2))
    assert rules.orientation_det(eps, "10", ZNE12, *before) > 0.99
    assert rules.orientation_det(eps, "10", ZNE12, *after) < 1e-12
    # Across the change (and the hour between the epochs) the worst part counts.
    assert rules.orientation_det(eps, "10", ZNE12, before[0], after[1]) < 1e-12
    assert rules.MIN_ORIENTATION_DET == 0.5


def mktz_inventory():
    chans = [Channel(r["channel"], r["location"], -38.0, 176.0, 0.0, 0.0,
                     azimuth=float(r["azimuth"]), dip=float(r["dip"]),
                     sample_rate=float(r["sample_rate"]), start_date=UTCDateTime(r["start"]),
                     end_date=UTCDateTime(r["end"]) if r["end"] else None)
             for r in mktz_rows()]
    return Inventory(networks=[Network("NZ", stations=[
        Station("MKTZ", -38.0, 176.0, 0.0, channels=chans,
                start_date=UTCDateTime("2025-02-20T12:00:00"))])])


class StationsOnly:
    def __init__(self, inv):
        self.inv = inv

    def get_stations(self, **kw):
        return self.inv


def set_on(start, end):
    return config.parse({"name": "mktz", "network": "NZ", "start": start, "end": end,
                         "centre": [-38.0, 176.0], "radius_km": 50.0, "max_stations": 8})


@pytest.fixture
def full_coverage(monkeypatch):
    def cover(cfg, rows):
        for r in rows:
            r["coverage"] = {c: 1.0 for c in r["channels"]}
            r["coverage_min"] = 1.0
        return "test"
    monkeypatch.setattr(fetch, "coverage", cover)


def test_probe_refuses_mktz_after_the_change(full_coverage):
    rows, _ = fetch.probe_rows(set_on("2025-10-01T00:00:00", "2025-10-01T03:00:00"),
                               StationsOnly(mktz_inventory()))
    assert len(rows) == 1 and not rows[0]["ok"]
    assert "not independent" in rows[0]["reason"]


def test_probe_keeps_mktz_before_the_change(full_coverage):
    rows, _ = fetch.probe_rows(set_on("2025-06-01T00:00:00", "2025-06-01T03:00:00"),
                               StationsOnly(mktz_inventory()))
    assert len(rows) == 1 and rows[0]["ok"], rows[0]["reason"]


# ---- pull: a rotation that fails drops the station, not the set ------------------

class Waveforms:
    """A dataselect client with a minute of noise on every channel asked for."""
    def get_waveforms(self, net, sta, loc, chans, t0, t1):
        import numpy as np
        from obspy import Stream, Trace
        rng = np.random.default_rng(1)
        n = round((t1 - t0) * 100)
        return Stream([Trace(rng.integers(-500, 500, n).astype(np.int32),
                             {"network": net, "station": sta, "location": loc,
                              "channel": ch, "sampling_rate": 100.0, "starttime": t0})
                       for ch in chans.split(",")])


def test_pull_leaves_out_a_station_whose_rotation_fails(tmp_path, monkeypatch):
    cfg = set_on("2025-10-01T00:00:00", "2025-10-01T00:01:00")
    out = tmp_path / cfg.name
    (out / "stationxml").mkdir(parents=True)
    mktz_inventory().write(str(out / "stationxml" / "NZ.MKTZ.xml"), format="STATIONXML")
    row = {"location": "10", "lat": -38.0, "lon": 176.0, "elevation_m": 0.0,
           "distance_km": 0.0, "ok": True, "reason": "", "coverage_min": 1.0}
    chosen = [{"network": "NZ", "station": "MKTZ", "channels": list(ZNE12),
               "azimuth_offset_deg": {"HH1": 0.0, "HH2": 90.0}, **row},
              {"network": "NZ", "station": "WEL", "channels": ["HHZ", "HHN", "HHE"],
               "azimuth_offset_deg": {"HHN": 0.0, "HHE": 0.0}, **row}]
    (out / "stations.json").write_text(json.dumps(
        {"set": cfg.name, "config": cfg.to_json(), "probed": chosen, "chosen": chosen}))
    monkeypatch.setattr(fetch, "client", lambda cfg, *need: Waveforms())
    assert fetch.cmd_pull(cfg, tmp_path, allow_test_period=True) == 0
    d = json.loads((out / "dataset.json").read_text())
    assert d["stations_chosen"] == ["NZ.MKTZ", "NZ.WEL"]
    assert [s["station"] for s in d["stations"]] == ["WEL"]
    assert any("NZ.MKTZ: rotation to N/E failed" in f for f in d["request_failures"])
    assert not (out / "MKTZ.mseed").exists()
