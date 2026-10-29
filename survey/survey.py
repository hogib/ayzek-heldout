"""Metadata-only survey of the held-out networks: no waveform, no event list.

    uv run python survey/survey.py greece survey/out
    uv run python survey/survey.py nz survey/out
    uv run python survey/survey.py collisions survey/out --ayzek-models PATH

For every station of the network(s) with HH channels open now:
  - coordinates, elevation and the HH channel epochs (fdsnws/station);
  - whether the station's current epoch has three HH channels (Z plus N/E or
    1/2) at exactly 100 Hz at one location code (anything else is excluded:
    ayzek does not resample);
  - the fraction of 2025-01-01 to 2026-10-28 covered by data on each channel:
      Greece  fdsnws/availability at the NOA EIDA node (time spans, not data);
      NZ      GeoNet has no availability service; the open-data bucket's
              object listing (one miniSEED file per channel and UTC day) gives
              the fraction of days with a file. Only object keys are read, not
              sizes or contents, so it is an upper bound on time coverage.
Writes <out>/<region>_stations.csv and <out>/<region>_epochs.csv and prints
the clusters (stations with >= 90% coverage on every channel and >= 5 such
stations within 150 km, greedy as in ayzek's KO scout).

`collisions` compares the station codes with those ayzek looks up by code
alone (its models/stations.csv and models/pd_gain.csv, read from a path given
on the command line, plus every KO station code from KOERI's station service).
"""
import argparse
import csv
import datetime as dt
import re
import sys
import time
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from obspy import UTCDateTime
from obspy.clients.fdsn import Client

T0, T1 = UTCDateTime("2025-01-01"), UTCDateTime("2026-10-28")
NOW = UTCDateTime("2026-10-29")
NOA = "https://eida.gein.noa.gr"
GEONET = "https://service.geonet.org.nz"
BUCKET = "https://geonet-open-data.s3-ap-southeast-2.amazonaws.com"
KOERI = "https://eida.koeri.boun.edu.tr"
GREEK = ("HL", "HT", "HA", "HP", "HC")
AVAIL_CACHE = {}  # station key -> availability text, kept in <out>/greece_availability.json


def inventory(base, nets):
    return Client(base_url=base, timeout=300).get_stations(
        network=",".join(nets), channel="HH?", level="channel", starttime=NOW)


def inventory_all_epochs(base, nets):
    return Client(base_url=base, timeout=300).get_stations(
        network=",".join(nets), channel="HH?", level="channel")


def describe(net, st, all_epochs):
    """One row per station: the current HH epoch and whether it is usable."""
    cur = [c for c in st.channels if c.end_date is None or c.end_date > NOW]
    by_loc = defaultdict(dict)
    for c in cur:
        by_loc[c.location_code][c.code] = c
    usable_locs = []
    for loc, chans in sorted(by_loc.items()):
        horiz = ({"HHN", "HHE"} <= set(chans)) or ({"HH1", "HH2"} <= set(chans))
        if "HHZ" in chans and horiz:
            three = ["HHZ"] + (["HHN", "HHE"] if {"HHN", "HHE"} <= set(chans) else ["HH1", "HH2"])
            if all(chans[k].sample_rate == 100.0 for k in three):
                usable_locs.append((loc, three))
    rates = sorted({f"{c.sample_rate:g}" for c in cur})
    loc, three = usable_locs[0] if usable_locs else ("", [])
    az = {k: by_loc[loc][k].azimuth for k in three} if three else {}
    # ayzek reads 1 as N and 2 as E: a horizontal more than 5 degrees off its
    # nominal azimuth rotates what the geometry head sees.
    def off(a, want):
        d = abs(a - want) % 360
        return min(d, 360 - d)
    odd_az = [k for k, want in zip(three[1:], (0.0, 90.0))
              if az.get(k) is not None and off(az[k], want) > 5]
    hist = [c for c in all_epochs if c.location_code == loc and c.code in three]
    first = min((c.start_date for c in hist), default=None)
    return {
        "network": net.code, "station": st.code,
        "lat": round(st.latitude, 5), "lon": round(st.longitude, 5),
        "elevation_m": st.elevation,
        "location": loc if usable_locs else "",
        "channels": "/".join(three) if three else "/".join(sorted({c.code for c in cur})),
        "rates_hz": "/".join(rates),
        "hh_100hz": bool(usable_locs),
        "n_locations": len(usable_locs),
        "odd_azimuth": "/".join(odd_az),
        "current_epoch_start": (min(by_loc[loc][k].start_date for k in three).isoformat()[:19]
                                if three else ""),
        "first_hh_start": first.isoformat()[:19] if first else "",
        "n_epochs": len({(str(c.start_date), str(c.end_date)) for c in hist}),
    }


def epochs_rows(net, st):
    for c in st.channels:
        yield {"network": net.code, "station": st.code, "location": c.location_code,
               "channel": c.code, "sample_rate": c.sample_rate,
               "azimuth": c.azimuth, "dip": c.dip,
               "start": c.start_date.isoformat()[:19],
               "end": c.end_date.isoformat()[:19] if c.end_date else ""}


# ---- coverage ---------------------------------------------------------------

def noa_coverage(row):
    """Fraction of [T0, T1) covered on each of the three channels."""
    if not row["hh_100hz"]:
        return {}
    q = urllib.parse.urlencode({
        "net": row["network"], "sta": row["station"],
        "loc": row["location"] or "--", "cha": "HH?",
        "starttime": T0.isoformat()[:19], "endtime": T1.isoformat()[:19],
        "format": "text"})
    key = f"{row['network']}.{row['station']}.{row['location']}"
    if key in AVAIL_CACHE:
        text = AVAIL_CACHE[key]
    else:
        # The node drops connections under load: retry with backoff, one
        # request at a time.
        for attempt in range(6):
            try:
                text = urllib.request.urlopen(f"{NOA}/fdsnws/availability/1/query?{q}",
                                              timeout=300).read().decode()
                break
            except urllib.error.HTTPError as e:
                if e.code in (204, 404):
                    text = ""
                    break
                err = f"HTTP {e.code}"
            except Exception as e:  # noqa: BLE001
                err = str(e)[:60]
            time.sleep(5 * 2 ** attempt)
        else:
            return {"error": err}
        AVAIL_CACHE[key] = text
    spans = defaultdict(float)
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split()
        a, b = max(UTCDateTime(f[6]), T0), min(UTCDateTime(f[7]), T1)
        if b > a:
            spans[f[3]] += b - a
    return {ch: spans.get(ch, 0.0) / (T1 - T0) for ch in row["channels"].split("/")}


def s3_day(day):
    """Object keys of one UTC day in GeoNet's open-data bucket -> (sta, loc, cha)."""
    prefix = f"waveforms/miniseed/{day.year}/{day.year}.{day.julday:03d}/"
    have, token = set(), None
    pat = re.compile(r"/([A-Z0-9]+)\.NZ/\d{4}\.\d{3}\.\1\.(\w*)-(HH.)\.NZ\.D$")
    while True:
        q = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            q["continuation-token"] = token
        url = f"{BUCKET}/?{urllib.parse.urlencode(q)}"
        for attempt in range(4):
            try:
                xml = urllib.request.urlopen(url, timeout=120).read()
                break
            except Exception:  # noqa: BLE001
                if attempt == 3:
                    raise
        root = ET.fromstring(xml)
        ns = {"s": root.tag.split("}")[0][1:]}
        for k in root.iterfind("s:Contents/s:Key", ns):
            m = pat.search(k.text)
            if m:
                have.add(m.groups())
        nxt = root.find("s:NextContinuationToken", ns)
        if nxt is None:
            return have
        token = nxt.text


def nz_coverage(rows):
    days = []
    d = T0
    while d < T1:
        days.append(d)
        d += 86400
    with ThreadPoolExecutor(12) as ex:
        per_day = list(ex.map(s3_day, days))
    count = defaultdict(int)
    for have in per_day:
        for key in have:
            count[key] += 1
    out = {}
    for r in rows:
        if r["hh_100hz"]:
            out[r["station"]] = {ch: count[(r["station"], r["location"], ch)] / len(days)
                                 for ch in r["channels"].split("/")}
    return out, len(days)


# ---- clusters ---------------------------------------------------------------

def km(a, b):
    la1, lo1, la2, lo2 = map(np.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(h))


def clusters(pool, radius=150.0, min_n=5):
    taken, out = set(), []
    cl = sorted(((sum(km(c, o) <= radius for o in pool), c) for c in pool),
                key=lambda x: -x[0])
    for n, c in cl:
        if c["station"] in taken or n < min_n:
            continue
        mem = [o for o in pool if km(c, o) <= radius]
        taken |= {o["station"] for o in mem}
        out.append((c, mem))
    return out


def write(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def report(rows, out, region, write_csv=True):
    if write_csv:
        write(rows, out / f"{region}_stations.csv")
    usable = [r for r in rows if r["hh_100hz"] and r["cov_min"] != "" and r["cov_min"] >= 0.9]
    print(f"{len(rows)} stations with HH open on {NOW.date}; "
          f"{sum(r['hh_100hz'] for r in rows)} with three HH at 100 Hz; "
          f"{len(usable)} of those with >= 90% coverage on every channel")
    for net in sorted({r["network"] for r in rows}):
        a = [r for r in rows if r["network"] == net]
        print(f"  {net}: {len(a)} open, {sum(r['hh_100hz'] for r in a)} at 100 Hz, "
              f"{sum(r in usable for r in a)} usable")
    bad = [r for r in rows if not r["hh_100hz"]]
    if bad:
        print("Not three HH at 100 Hz: " + " ".join(
            f"{r['network']}.{r['station']}[{r['channels']}@{r['rates_hz']}]" for r in bad))
    print("\nClusters within 150 km: centre, count, members")
    for c, mem in clusters(usable):
        print(f"  {c['network']}.{c['station']:5s} ({c['lat']:.2f} {c['lon']:.2f}) "
              f"{len(mem):2d}: " + " ".join(f"{o['network']}.{o['station']}" for o in mem))


def cmd_region(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base, nets = (NOA, GREEK) if args.region == "greece" else (GEONET, ("NZ",))
    inv = inventory(base, nets)
    hist = inventory_all_epochs(base, nets)
    allep = {(n.code, s.code): [c for s2 in n for c in s2.channels if s2.code == s.code]
             for n in hist for s in n}
    rows, ep = [], []
    # A station can come back as several station epochs: pool their channels
    # under the latest epoch's coordinates.
    merged = {}
    for net in inv:
        for st in net:
            key = (net.code, st.code)
            if key in merged:
                prev = merged[key][1]
                keep, other = (st, prev) if st.start_date > prev.start_date else (prev, st)
                keep = keep.copy()
                keep.channels = prev.channels + st.channels
                merged[key] = (net, keep)
            else:
                merged[key] = (net, st)
    for key, (net, st) in sorted(merged.items()):
        rows.append(describe(net, st, allep.get(key, st.channels)))
    for net in hist:
        for st in net:
            ep.extend(epochs_rows(net, st))
    write(ep, out / f"{args.region}_epochs.csv")
    if args.region == "greece":
        cache = out / "greece_availability.json"
        if cache.exists():
            AVAIL_CACHE.update(json.loads(cache.read_text()))
        try:
            covs = [noa_coverage(r) for r in rows]
        finally:
            tmp = cache.with_suffix(".tmp")  # a kill mid-write keeps the old cache
            tmp.write_text(json.dumps(AVAIL_CACHE, indent=0, sort_keys=True))
            tmp.replace(cache)
        ndays = None
    else:
        cov_nz, ndays = nz_coverage(rows)
        covs = [cov_nz.get(r["station"], {}) for r in rows]
    for r, cov in zip(rows, covs):
        r["avail_error"] = cov.pop("error", "") if cov else ""
        chans = r["channels"].split("/") if r["hh_100hz"] else []
        for i, k in enumerate(("cov_z", "cov_h1", "cov_h2")):
            r[k] = round(cov[chans[i]], 4) if chans and chans[i] in cov else ""
        r["cov_min"] = (min(cov[c] for c in chans) if chans and not r["avail_error"]
                        else "")
        if r["cov_min"] != "":
            r["cov_min"] = round(r["cov_min"], 4)
    if ndays:
        print(f"[nz] coverage = fraction of {ndays} UTC days with a file in {BUCKET}")
    report(rows, out, args.region)
    return 0


def codes_from_csv(path, col):
    with open(path) as f:
        return {r[col] for r in csv.DictReader(f)}


def cmd_collisions(args):
    out = Path(args.out)
    models = Path(args.ayzek_models)
    # Every per-station table ayzek keys on the code alone.
    tables = {"stations.csv": codes_from_csv(models / "stations.csv", "code")}
    for name in ("pd_gain.csv", "pd_terms.csv", "pd_noise.csv"):
        if (models / name).exists():
            tables[name] = codes_from_csv(models / name, "station")
    ayzek = set().union(*tables.values())
    q = f"{KOERI}/fdsnws/station/1/query?net=KO&level=station&format=text"
    # (KOERI's station service, every epoch: codes of closed stations too)
    ko = {line.split("|")[1] for line in urllib.request.urlopen(q, timeout=300)
          .read().decode().splitlines() if line and not line.startswith("#")}
    # Every code of the foreign networks, any channel and epoch: a code that is
    # not usable now can still collide in a later replay.
    foreign = defaultdict(set)
    for base, nets in ((NOA, GREEK), (GEONET, ("NZ",))):
        q = f"{base}/fdsnws/station/1/query?net={','.join(nets)}&level=station&format=text"
        for line in urllib.request.urlopen(q, timeout=300).read().decode().splitlines():
            if line and not line.startswith("#"):
                n, s = line.split("|")[:2]
                foreign[s].add(n)
    usable = set()
    for region in ("greece", "nz"):
        p = out / f"{region}_stations.csv"
        if p.exists():
            with open(p) as f:
                usable |= {(r["network"], r["station"]) for r in csv.DictReader(f)
                           if r["hh_100hz"] == "True" and r["cov_min"] and float(r["cov_min"]) >= 0.9}
    rows = []
    for s in sorted(foreign):
        with_ = []
        if s in ko:
            with_.append("KO")
        hit = [n.removesuffix(".csv") for n, codes in tables.items() if s in codes]
        if hit:
            with_.append("ayzek:" + "/".join(hit))
        if len(foreign[s]) > 1:
            with_.append("+".join(sorted(foreign[s])))
        if with_:
            rows.append({"station": s, "networks": "+".join(sorted(foreign[s])),
                         "collides_with": " ".join(with_),
                         "usable": "+".join(n for n in sorted(foreign[s]) if (n, s) in usable)})
    write(rows, out / "collisions.csv")
    print(f"{len(ko)} KO codes (KOERI, all epochs), {len(ayzek)} codes in ayzek models, "
          f"({', '.join(f'{k} {len(v)}' for k, v in tables.items())}), "
          f"{len(foreign)} HL/HT/HA/HP/HC/NZ codes; {len(rows)} collide")
    for r in rows:
        print(f"  {r['station']:6s} {r['networks']:10s} with {r['collides_with']:45s} "
              f"usable: {r['usable'] or '-'}")
    return 0


def cmd_report(args):
    """The summary and clusters again, from <out>/<region>_stations.csv (offline)."""
    with open(Path(args.out) / f"{args.region}_stations.csv") as f:
        rows = [r for r in csv.DictReader(f)
                if not args.networks or r["network"] in args.networks.split(",")]
    for r in rows:
        r["hh_100hz"] = r["hh_100hz"] == "True"
        r["lat"], r["lon"] = float(r["lat"]), float(r["lon"])
        r["cov_min"] = float(r["cov_min"]) if r["cov_min"] else ""
    report(rows, Path(args.out), args.region, write_csv=False)
    return 0


def cmd_tables(args):
    """Markdown tables of the usable stations, for SURVEY.md."""
    out = Path(args.out)
    for region in ("greece", "nz"):
        with open(out / f"{region}_stations.csv") as f:
            rows = list(csv.DictReader(f))
        ok = [r for r in rows if r["hh_100hz"] == "True"]
        print(f"\n#### {region}: {len(ok)} stations with three HH at 100 Hz "
              f"(>= 90%: {sum(r['cov_min'] != '' and float(r['cov_min']) >= 0.9 for r in ok)})\n")
        print("| net | code | lat | lon | elev m | loc.channels | current epoch from "
              "| HH since | epochs | cov min | >=90% | horiz. off N/E |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in sorted(ok, key=lambda r: (r["network"], r["station"])):
            cov = r["cov_min"]
            good = cov != "" and float(cov) >= 0.9
            print(f"| {r['network']} | {r['station']} | {float(r['lat']):.4f} | "
                  f"{float(r['lon']):.4f} | {float(r['elevation_m']):.0f} | "
                  f"{r['location'] or '--'}.{r['channels']} | {r['current_epoch_start'][:10]} | "
                  f"{r['first_hh_start'][:10]} | {r['n_epochs']} | "
                  f"{cov if cov != '' else 'n/a'} | {'yes' if good else 'no'} | "
                  f"{r['odd_azimuth'] or ''} |")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for region in ("greece", "nz"):
        s = sub.add_parser(region)
        s.add_argument("out")
        s.set_defaults(fn=cmd_region, region=region)
    c = sub.add_parser("collisions")
    c.add_argument("out")
    c.add_argument("--ayzek-models", required=True,
                   help="ayzek's models/ directory (read only)")
    c.set_defaults(fn=cmd_collisions)
    r = sub.add_parser("report", help="summary and clusters from the CSV, offline")
    r.add_argument("region", choices=("greece", "nz"))
    r.add_argument("out")
    r.add_argument("--networks", help="comma-separated: only these networks")
    r.set_defaults(fn=cmd_report)
    t = sub.add_parser("tables", help="markdown tables of the stations for SURVEY.md")
    t.add_argument("out")
    t.set_defaults(fn=cmd_tables)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
