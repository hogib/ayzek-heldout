"""dataset.json records the SHA-256 and size of every file the fetch wrote;
`heldout verify` recomputes them (a re-fetch is checked against the record)."""
import json

import pytest

from heldout import cli, dataset
from test_dataset import good


def make_set(tmp_path):
    """A set directory as pull and catalog leave it, with its file record."""
    d = good(tmp_path)                                   # writes SIMA.mseed
    (tmp_path / "stationxml").mkdir()
    (tmp_path / "stationxml" / "KO.SIMA.xml").write_text("<FDSNStationXML/>\n")
    (tmp_path / "stations.csv").write_text("code,lat,lon,elev_m\nSIMA,39.1,28.2,100\n")
    (tmp_path / "pd_gain.csv").write_text("station,channel,start,end,sensitivity\n")
    (tmp_path / "stations.json").write_text("{}\n")
    (tmp_path / "catalog.csv").write_text("Date,Longitude,Latitude,Depth,Rms,Type,Magnitude\n")
    d["catalog"] = {"file": "catalog.csv"}
    d["files"] = dataset.file_hashes(tmp_path, dataset.set_files(tmp_path, d))
    dataset.write_dataset(tmp_path, d)
    return d


def test_the_record_names_every_file_the_fetch_wrote(tmp_path):
    d = make_set(tmp_path)
    assert sorted(d["files"]) == ["SIMA.mseed", "catalog.csv", "pd_gain.csv",
                                  "stations.csv", "stationxml/KO.SIMA.xml"]
    assert d["files"]["SIMA.mseed"]["bytes"] == 1024
    assert len(d["files"]["SIMA.mseed"]["sha256"]) == 64
    assert dataset.verify(tmp_path) == [(n, "match", "") for n in sorted(d["files"])]


def test_a_changed_file_and_a_missing_one_are_reported(tmp_path, capsys):
    make_set(tmp_path)
    (tmp_path / "SIMA.mseed").write_bytes(b"\1" * 1024)     # same size, other content
    (tmp_path / "stations.csv").unlink()
    got = {n: s for n, s, _ in dataset.verify(tmp_path)}
    assert got["SIMA.mseed"] == "mismatch" and got["stations.csv"] == "missing"
    assert got["catalog.csv"] == "match"
    assert cli.main(["verify", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "mismatch SIMA.mseed" in out and "missing  stations.csv" in out
    assert "3 of 5 files match, 1 differ, 1 missing" in out


def test_verify_exit_codes(tmp_path):
    make_set(tmp_path)
    assert cli.main(["verify", str(tmp_path)]) == 0
    assert cli.main(["verify", str(tmp_path / "nowhere")]) == 2


def test_an_old_dataset_json_without_the_record_still_validates(tmp_path):
    d = good(tmp_path)
    dataset.write_dataset(tmp_path, d)                     # no "files", as before
    dataset.validate(json.loads((tmp_path / "dataset.json").read_text()), tmp_path)
    with pytest.raises(dataset.DatasetError, match="no file hashes"):
        dataset.verify(tmp_path)
    assert cli.main(["verify", str(tmp_path)]) == 2


def test_a_malformed_record_is_refused(tmp_path):
    d = good(tmp_path)
    d["files"] = {"SIMA.mseed": "abc"}
    with pytest.raises(dataset.DatasetError, match="'files'"):
        dataset.validate(d, tmp_path)
