"""What a set directory holds and the checks it must pass.

    data/<set>/stations.json     the probe: candidates, why each was kept or not
    data/<set>/stationxml/       the chosen stations' StationXML (response level)
    data/<set>/stations.csv      code,lat,lon,elev_m as ayzek's models/stations.csv
    data/<set>/pd_gain.csv       station,channel,start,end,sensitivity as ayzek's
                                 models/pd_gain.csv (vertical channel, every
                                 epoch; counts per m/s)
    data/<set>/<STATION>.mseed   three HH components, 512-byte Steim2 records
    data/<set>/dataset.json      the request and what arrived
    data/<set>/catalog.csv       the network's catalogue, ayzek --catalog format
"""
import datetime as dt
import json
import subprocess
from pathlib import Path

SCHEMA = 1
REQUIRED = {
    "schema": int, "set": str, "config": dict, "networks": list, "services": dict,
    "span": list, "centre": list, "radius_km": (int, float), "max_stations": int,
    "stations_requested": list, "stations_chosen": list, "stations": list,
    "retrieved_utc": str, "tool": dict, "citation": list, "licence": list,
}
STATION_REQUIRED = {
    "network": str, "station": str, "location": str, "channels": list, "file": str,
    "seconds_per_component": dict, "bytes": int, "megabytes": (int, float),
}


class DatasetError(RuntimeError):
    pass


def tool_commit():
    """The tool's own git commit, '+dirty' if it has uncommitted changes."""
    here = Path(__file__).resolve().parent
    try:
        head = subprocess.run(["git", "-C", str(here), "rev-parse", "--short=12", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(here), "status", "--porcelain", "--",
                                str(here.parent / "heldout")],
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return head + ("+dirty" if dirty else "")


def now_utc():
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def validate(d, directory=None):
    """Raises DatasetError unless `d` is a complete dataset.json with data.

    With `directory`, also checks that every listed file exists, is not empty
    and has the size recorded."""
    if not isinstance(d, dict):
        raise DatasetError("dataset.json is not an object")
    for k, t in REQUIRED.items():
        if k not in d:
            raise DatasetError(f"dataset.json: missing {k!r}")
        if not isinstance(d[k], t) or isinstance(d[k], bool):
            raise DatasetError(f"dataset.json: {k!r} has type {type(d[k]).__name__}")
    if d["schema"] != SCHEMA:
        raise DatasetError(f"dataset.json: schema {d['schema']}, expected {SCHEMA}")
    if len(d["span"]) != 2 or d["span"][0] >= d["span"][1]:
        raise DatasetError("dataset.json: span must be [start, end] with start < end")
    if not d["stations"]:
        raise DatasetError(f"set {d['set']}: no station returned data")
    codes = set()
    for s in d["stations"]:
        for k, t in STATION_REQUIRED.items():
            if k not in s or not isinstance(s[k], t) or isinstance(s[k], bool):
                raise DatasetError(f"dataset.json: station entry {s.get('station')!r}: bad {k!r}")
        if s["station"] in codes:
            raise DatasetError(f"dataset.json: station code {s['station']} twice "
                               "(ayzek keys stations on the code alone)")
        codes.add(s["station"])
        secs = s["seconds_per_component"]
        if s["bytes"] <= 0 or not secs or max(secs.values()) <= 0:
            raise DatasetError(f"set {d['set']}: {s['station']} is listed with no data")
        if directory is not None:
            p = Path(directory) / s["file"]
            if not p.is_file() or p.stat().st_size == 0:
                raise DatasetError(f"{p}: missing or empty")
            if p.stat().st_size != s["bytes"]:
                raise DatasetError(f"{p}: {p.stat().st_size} bytes, dataset.json says {s['bytes']}")
    if directory is not None and "catalog" in d:
        p = Path(directory) / d["catalog"]["file"]
        if not p.is_file():
            raise DatasetError(f"{p}: missing")
    return d


def write_json(path, d):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_dataset(directory, d):
    """Validates, then writes dataset.json; nothing is written if it fails."""
    validate(d, directory)
    write_json(Path(directory) / "dataset.json", d)


def _dec(x, nd):
    """Up to nd decimals, trailing zeros dropped (984.0 -> 984)."""
    s = f"{float(x):.{nd}f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def stations_csv(path, rows):
    """ayzek's models/stations.csv layout: code,lat,lon,elev_m."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("code,lat,lon,elev_m\n")
        for r in rows:
            f.write(f"{r['station']},{_dec(r['lat'], 6)},{_dec(r['lon'], 6)},"
                    f"{_dec(r['elevation_m'], 1)}\n")


def gains(inventory, chosen):
    """Every epoch of each chosen station's vertical HH channel at its location.

    Same rule as ayzek's tools/export_pd.py: the instrument sensitivity, input
    units m/s, start and end as epoch seconds (end empty if open)."""
    want = {(r["network"], r["station"]): r["location"] for r in chosen}
    rows = []
    for net in inventory:
        for sta in net:
            loc = want.get((net.code, sta.code))
            if loc is None:
                continue
            for c in sta.channels:
                s = c.response.instrument_sensitivity if c.response is not None else None
                if c.code != "HHZ" or c.location_code != loc or s is None:
                    continue
                if (s.input_units or "").upper().replace(" ", "") != "M/S":
                    continue
                rows.append({"station": sta.code, "channel": c.code,
                             "start": c.start_date.timestamp if c.start_date else 0.0,
                             "end": c.end_date.timestamp if c.end_date else "",
                             "sensitivity": float(s.value)})
    rows.sort(key=lambda r: (r["station"], r["start"]))
    return rows


def gains_csv(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write("station,channel,start,end,sensitivity\n")
        for r in rows:
            end = "" if r["end"] == "" else repr(float(r["end"]))
            f.write(f"{r['station']},{r['channel']},{float(r['start'])!r},{end},"
                    f"{float(r['sensitivity'])!r}\n")
