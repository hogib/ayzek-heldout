import copy
import json

import pytest

from heldout import dataset
from heldout.dataset import DatasetError


def good(tmp_path=None):
    d = {"schema": 1, "set": "demo_ko", "config": {}, "networks": ["KO"], "services": {},
         "span": ["2025-11-10T18:04:00", "2025-11-10T18:35:00"], "centre": [39.2, 28.2],
         "radius_km": 150.0, "max_stations": 6, "stations_requested": [],
         "stations_chosen": ["KO.SIMA"], "retrieved_utc": "2026-10-29T00:00:00+00:00",
         "tool": {"git_commit": "abc"}, "citation": ["x"], "licence": ["y"],
         "stations": [{"network": "KO", "station": "SIMA", "location": "",
                       "channels": ["HHZ", "HHN", "HHE"], "file": "SIMA.mseed",
                       "seconds_per_component": {"HHZ": 1847.0, "HHN": 1860.0, "HHE": 1855.0},
                       "bytes": 1024, "megabytes": 0.0}]}
    if tmp_path is not None:
        (tmp_path / "SIMA.mseed").write_bytes(b"\0" * 1024)
    return d


def test_valid(tmp_path):
    dataset.validate(good(tmp_path), tmp_path)


@pytest.mark.parametrize("mutate, match", [
    (lambda d: d.pop("citation"), "missing 'citation'"),
    (lambda d: d.update(radius_km="150"), "radius_km"),
    (lambda d: d.update(schema=2), "schema"),
    (lambda d: d.update(span=["2025-11-10T18:35:00", "2025-11-10T18:04:00"]), "span"),
    (lambda d: d.update(stations=[]), "no station returned data"),
    (lambda d: d["stations"][0].update(bytes=0), "no data"),
    (lambda d: d["stations"][0].update(seconds_per_component={"HHZ": 0.0}), "no data"),
    (lambda d: d["stations"][0].pop("file"), "bad 'file'"),
    (lambda d: d["stations"].append(copy.deepcopy(d["stations"][0])), "twice"),
])
def test_invalid(mutate, match):
    d = good()
    mutate(d)
    with pytest.raises(DatasetError, match=match):
        dataset.validate(d)


def test_files_are_checked(tmp_path):
    d = good(tmp_path)
    (tmp_path / "SIMA.mseed").write_bytes(b"")
    with pytest.raises(DatasetError, match="missing or empty"):
        dataset.validate(d, tmp_path)
    (tmp_path / "SIMA.mseed").write_bytes(b"\0" * 512)
    with pytest.raises(DatasetError, match="bytes"):
        dataset.validate(d, tmp_path)


def test_write_dataset_writes_nothing_when_invalid(tmp_path):
    d = good(tmp_path)
    d["stations"] = []
    with pytest.raises(DatasetError):
        dataset.write_dataset(tmp_path, d)
    assert not (tmp_path / "dataset.json").exists()
    dataset.write_dataset(tmp_path, good(tmp_path))
    assert json.loads((tmp_path / "dataset.json").read_text())["set"] == "demo_ko"


def test_stations_csv_layout(tmp_path):
    p = tmp_path / "stations.csv"
    dataset.stations_csv(p, [{"station": "SIMA", "lat": 39.0833, "lon": 28.9825,
                              "elevation_m": 984.0},
                             {"station": "WEL", "lat": -41.284048, "lon": 174.768184,
                              "elevation_m": 138.5}])
    assert p.read_text().splitlines() == ["code,lat,lon,elev_m", "SIMA,39.0833,28.9825,984",
                                          "WEL,-41.284048,174.768184,138.5"]
