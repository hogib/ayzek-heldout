"""probe, pull and catalog: the three steps that build a set directory.

The structure follows ayzek's tools/fetch_ko_data.py (see README.md,
Provenance); what differs is noted where it matters.
"""
import datetime as dt
import json
import math
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import availability, catalog, dataset, retry, rules

R_EARTH_KM = 6371.0


def km(lat1, lon1, lat2, lon2):
    p, q = math.radians(lat1), math.radians(lat2)
    h = (math.sin((q - p) / 2) ** 2 + math.cos(p) * math.cos(q)
         * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * R_EARTH_KM * math.asin(math.sqrt(h))


def utc(t):
    from obspy import UTCDateTime
    return UTCDateTime(t.replace(tzinfo=dt.UTC) if t.tzinfo is None else t)


def client(cfg, *need):
    """An FDSN client of cfg.base_url with the services `need`. obspy discovers
    the services once, when the client is made, and leaves out one whose
    discovery failed; such a client is made again, since asking it again for
    that service cannot succeed."""
    from obspy.clients.fdsn import Client
    from obspy.clients.fdsn.header import FDSNNoServiceException

    def make():
        c = Client(base_url=cfg.base_url, timeout=300)
        missing = [s for s in need if s not in c.services]
        if missing:
            raise FDSNNoServiceException(f"no {', '.join(missing)} service discovered")
        return c
    return retry.call(make, what=f"{cfg.base_url} services")


def services(cfg):
    info = cfg.network_info[0]
    return {"station": info.station_url, "dataselect": info.dataselect_url,
            "availability": info.availability or f"none; day listing of {info.day_listing}",
            "event": info.event_url}


def set_dir(data, cfg):
    return Path(data) / cfg.name


# ---- probe -------------------------------------------------------------------

def merged_stations(inv):
    """(net, sta) -> (latest station epoch, every channel epoch over all of them)."""
    out = {}
    for net in inv:
        for st in net:
            key = (net.code, st.code)
            if key in out:
                prev, chans = out[key]
                out[key] = (st if st.start_date > prev.start_date else prev,
                            chans + list(st.channels))
            else:
                out[key] = (st, list(st.channels))
    return out


def coverage(cfg, rows):
    """Fills r['coverage'] for the rows that passed the channel rule."""
    info = cfg.network_info[0]
    if info.availability:
        def one(r):
            return availability.fdsn_coverage(info.availability, r["network"], r["station"],
                                              r["location"], r["channels"], cfg.start, cfg.end)
        with ThreadPoolExecutor(2) as ex:
            covs = list(ex.map(one, rows))
        basis = "fdsnws/availability"
    else:
        days = list(availability.days_of(cfg.start, cfg.end))
        with ThreadPoolExecutor(8) as ex:
            per_day = dict(zip(days, ex.map(
                lambda d: availability.day_keys(info.day_listing, d), days)))
        covs = [availability.day_coverage(per_day, r["network"], r["station"], r["location"],
                                          r["channels"], cfg.start, cfg.end) for r in rows]
        basis = "day files in the open-data bucket (upper bound)"
    for r, c in zip(rows, covs):
        r["coverage"] = {k: round(v, 4) for k, v in c.items()}
        r["coverage_min"] = round(min(c.values()), 4)
    return basis


def cmd_probe(cfg, data):
    """Metadata and availability only: chooses the stations, writes stations.json."""
    from obspy.clients.fdsn.header import FDSNNoDataException
    out = set_dir(data, cfg)
    c = client(cfg, "station")
    t0, t1 = utc(cfg.start), utc(cfg.end)
    try:
        inv = retry.call(c.get_stations, network=",".join(cfg.networks), channel="HH?",
                         level="channel", starttime=t0, endtime=t1, what="station list")
    except FDSNNoDataException:
        inv = []
    rows = []
    for (net, sta), (st, chans) in merged_stations(inv).items():
        d = km(cfg.lat, cfg.lon, st.latitude, st.longitude)
        if d > cfg.radius_km:
            continue
        st2 = st.copy()
        st2.channels = chans
        eps = rules.epochs_from_station(st2)
        ch = rules.choose_channels(eps, cfg.start, cfg.end)
        az = (rules.azimuth_offsets(eps, ch.location, ch.channels, cfg.start, cfg.end)
              if ch.ok else {})
        rows.append({"network": net, "station": sta, "lat": float(st.latitude),
                     "lon": float(st.longitude), "elevation_m": float(st.elevation),
                     "distance_km": round(d, 1), "location": ch.location,
                     "channels": list(ch.channels), "azimuth_offset_deg": az,
                     "ok": ch.ok, "reason": ch.reason})
        if (ch.ok and cfg.max_azimuth_offset_deg is not None
                and any(v is None or v > cfg.max_azimuth_offset_deg for v in az.values())):
            rows[-1]["ok"] = False
            rows[-1]["reason"] = (f"horizontals {az} off N/E by more than "
                                  f"{cfg.max_azimuth_offset_deg:g} deg")
    rows.sort(key=lambda r: (r["distance_km"], r["network"], r["station"]))
    print(f"[probe] {len(rows)} {'/'.join(cfg.networks)} stations with HH? within "
          f"{cfg.radius_km:g} km, {cfg.start:%Y-%m-%dT%H:%M:%S} to {cfg.end:%Y-%m-%dT%H:%M:%S}")
    passing = [r for r in rows if r["ok"]]
    basis = coverage(cfg, passing) if passing else "-"
    chosen, codes = [], set()
    for r in rows:
        if r["ok"] and r["coverage_min"] < cfg.min_coverage:
            r["ok"] = False
            r["reason"] = f"coverage {r['coverage_min']:.3f} < {cfg.min_coverage:g}"
        if r["ok"] and r["station"] in codes:
            r["ok"] = False
            r["reason"] = "station code already chosen from another network"
        if r["ok"] and len(chosen) < cfg.max_stations:
            chosen.append(r)
            codes.add(r["station"])
        cov = f"cov {r['coverage_min']:.3f}" if "coverage_min" in r else ""
        mark = "chosen" if r in chosen else ("spare" if r["ok"] else r["reason"])
        print(f"  {r['network']}.{r['station']:6s} {r['distance_km']:6.1f} km  "
              f"{r['location'] or '--'}.{'/'.join(r['channels']) or '-':12s} {cov:10s} {mark}")
    out.mkdir(parents=True, exist_ok=True)
    spec = {"set": cfg.name, "config": cfg.to_json(), "span": [cfg.start.isoformat(),
            cfg.end.isoformat()], "services": services(cfg), "coverage_basis": basis,
            "probed_utc": dataset.now_utc(), "tool": {"name": "ayzek-heldout",
            "git_commit": dataset.tool_commit()}, "probed": rows, "chosen": chosen}
    if not chosen:
        dataset.write_json(out / "stations.json", spec)
        print(f"[probe] no usable station -> {out / 'stations.json'}", file=sys.stderr)
        return 1
    # StationXML for the chosen stations, and what ayzek looks up by code.
    xml = out / "stationxml"
    xml.mkdir(exist_ok=True)
    from obspy import Inventory
    full = Inventory(networks=[], source="ayzek-heldout")
    for r in chosen:
        inv_r = retry.call(c.get_stations, network=r["network"], station=r["station"],
                           location=r["location"] or "--", channel="HH?",
                           level="response", starttime=t0, endtime=t1,
                           what=f"{r['network']}.{r['station']} response")
        inv_r.write(str(xml / f"{r['network']}.{r['station']}.xml"), format="STATIONXML")
        full += inv_r
    g = dataset.gains(full, chosen)
    missing = sorted({r["station"] for r in chosen} - {x["station"] for x in g})
    dataset.stations_csv(out / "stations.csv", chosen)
    dataset.gains_csv(out / "pd_gain.csv", g)
    spec["gains_missing"] = missing
    dataset.write_json(out / "stations.json", spec)
    hours = (cfg.end - cfg.start).total_seconds() / 3600
    print(f"[probe] {len(chosen)} chosen -> {out / 'stations.json'}; stations.csv, "
          f"pd_gain.csv ({len(g)} epochs{', none for ' + ' '.join(missing) if missing else ''}), "
          f"stationxml/")
    print(f"[probe] pull estimate: {len(chosen)} stations x {hours:.2f} h "
          f"~ {1.7 * len(chosen) * hours:.1f} MB")
    return 0


# ---- pull --------------------------------------------------------------------

# Horizontals more than this far from north and east (or named 1 and 2) are
# rotated to north and east before they are written (held-out protocol,
# section 2): ayzek reads the second and third channels as N and E.
ROTATE_ABOVE_DEG = 0.5


def needs_rotation(channels, offsets):
    return (any(c[-1] in "12" for c in channels[1:])
            or any(v is None or v > ROTATE_ABOVE_DEG for v in offsets.values()))


def rotate_to_ne(stream, inventory):
    """The stream with its horizontals rotated to north and east, by the
    azimuths and dips of the station's metadata in force at each segment
    (obspy's rotate "->ZNE"), on the stretches where all three components are
    present, and rounded back to integer counts. The vertical passes through
    unchanged when its dip is -90 or 90 degrees."""
    import numpy as np
    out = stream.copy()
    # One combination only: after Z12 is rotated, the new N and E channels are
    # not in the metadata, and a second pass over "ZNE" would look them up.
    named_12 = any(tr.stats.channel[-1] in "12" for tr in out)
    out.rotate(method="->ZNE", inventory=inventory,
               components=("Z12",) if named_12 else ("ZNE",))
    for tr in out:
        tr.data = np.rint(tr.data).astype(np.int64)
    return out


def write_mseed(stream, dest):
    """512-byte big-endian Steim2 records, which is what ayzek's reader takes."""
    import numpy as np
    for tr in stream:
        if tr.data.dtype != np.int32:
            if np.abs(tr.data).max(initial=0) >= 2 ** 31:
                raise ValueError(f"{tr.id}: samples overflow int32")
            tr.data = tr.data.astype(np.int32)
    tmp = dest.with_suffix(".mseed.tmp")
    stream.write(str(tmp), format="MSEED", encoding="STEIM2", reclen=512, byteorder=">")
    if tmp.stat().st_size == 0 or tmp.stat().st_size % 512:
        tmp.unlink()
        raise ValueError(f"{dest}: not a whole number of 512-byte records")
    tmp.replace(dest)


def measure(path, channels):
    from obspy import read
    st = read(str(path))
    secs = defaultdict(float)
    for tr in st:
        secs[tr.stats.channel] += tr.stats.npts / tr.stats.sampling_rate
    return {c: round(secs.get(c, 0.0), 2) for c in channels}


def cmd_pull(cfg, data, allow_test_period=False, force=False):
    rules.check_test_period(cfg.start, cfg.end, allow_test_period, networks=cfg.networks)
    from obspy import Stream
    from obspy.clients.fdsn.header import FDSNNoDataException
    out = set_dir(data, cfg)
    spec_path = out / "stations.json"
    if not spec_path.exists():
        raise SystemExit(f"{spec_path}: run probe first")
    spec = json.loads(spec_path.read_text())
    if spec["config"] != cfg.to_json():
        raise SystemExit(f"{spec_path} was probed with another config; probe again")
    c = client(cfg, "dataselect")
    t0, t1 = utc(cfg.start), utc(cfg.end)
    got, failures = [], []
    for r in spec["chosen"]:
        dest = out / f"{r['station']}.mseed"
        tag = f"{r['network']}.{r['station']}"
        if dest.exists() and not force:
            print(f"  {tag}: present, measured")
        else:
            st, dropped = Stream(), defaultdict(int)
            t = t0
            while t < t1:
                end = min(t + 3600, t1)
                try:
                    part = retry.call(c.get_waveforms, r["network"], r["station"],
                                      r["location"] or "--", ",".join(r["channels"]), t, end,
                                      what=f"{tag} {t.strftime('%Y-%m-%dT%H:%M')}")
                    keep, drop = rules.check_traces(part, r["location"], r["channels"])
                    st += Stream(keep)
                    for _, why in drop:
                        dropped[why] += 1
                except FDSNNoDataException:
                    pass
                except Exception as e:  # noqa: BLE001  one hour lost, not the set
                    failures.append(f"{tag} {t.strftime('%Y-%m-%dT%H:%M')}: {type(e).__name__}")
                    print(f"  {failures[-1]}")
                t = end
            for why, n in dropped.items():
                print(f"  {tag}: dropped {n} traces ({why})")
            if not len(st):
                print(f"  {tag}: nothing")
                continue
            # Merge touching segments, then split again: merge alone gives a
            # masked array across gaps, which miniSEED cannot store; gaps stay
            # gaps (as in fetch_ko_data.py).
            st.trim(t0, t1, nearest_sample=False)
            st.merge(method=1, fill_value=None)
            st = st.split()
            if needs_rotation(r["channels"], r.get("azimuth_offset_deg") or {}):
                from obspy import read_inventory
                inv = read_inventory(str(out / "stationxml" / f"{tag}.xml"))
                st = rotate_to_ne(st, inv)
                print(f"  {tag}: rotated {'/'.join(r['channels'][1:])} to N/E "
                      f"(offsets {r.get('azimuth_offset_deg')})")
            write_mseed(st, dest)
        rotated = needs_rotation(r["channels"], r.get("azimuth_offset_deg") or {})
        channels = [r["channels"][0], "HHN", "HHE"] if rotated else r["channels"]
        secs = measure(dest, channels)
        size = dest.stat().st_size
        got.append({**{k: r[k] for k in ("network", "station", "location", "channels", "lat",
                                         "lon", "elevation_m", "distance_km",
                                         "azimuth_offset_deg")},
                    "rotated_to_ne": rotated, "channels_written": channels,
                    "file": dest.name, "seconds_per_component": secs, "bytes": size,
                    "megabytes": round(size / 1e6, 2),
                    "missing_components": [k for k, v in secs.items() if v == 0]})
        print(f"  {tag}: " + " ".join(f"{k} {v:.0f} s" for k, v in secs.items())
              + f" -> {dest.name} ({got[-1]['megabytes']} MB)")
    d = {"schema": dataset.SCHEMA, "set": cfg.name, "config": cfg.to_json(),
         "networks": list(cfg.networks), "services": services(cfg),
         "span": [cfg.start.isoformat(), cfg.end.isoformat()],
         "centre": [cfg.lat, cfg.lon], "radius_km": cfg.radius_km,
         "max_stations": cfg.max_stations, "coverage_basis": spec.get("coverage_basis"),
         "stations_requested": [{k: r.get(k) for k in ("network", "station", "distance_km",
                                                       "ok", "reason", "coverage_min")}
                                for r in spec["probed"]],
         "stations_chosen": [f"{r['network']}.{r['station']}" for r in spec["chosen"]],
         "stations": got, "request_failures": failures,
         "retrieved_utc": dataset.now_utc(),
         "tool": {"name": "ayzek-heldout", "git_commit": dataset.tool_commit()},
         "citation": sorted({i.citation for i in cfg.network_info}),
         "licence": sorted({i.licence for i in cfg.network_info})}
    old = out / "dataset.json"
    if old.exists():
        prev = json.loads(old.read_text())
        if "catalog" in prev and prev.get("span") == d["span"]:
            d["catalog"] = prev["catalog"]
    try:
        dataset.write_dataset(out, d)
    except dataset.DatasetError as e:
        print(f"[pull] FAILED: {e}; dataset.json not written", file=sys.stderr)
        return 2
    print(f"[pull] {len(got)} of {len(spec['chosen'])} stations -> {out}")
    return 0


# ---- catalog -----------------------------------------------------------------

def cmd_catalog(cfg, data, allow_test_period=False):
    t0, t1 = cfg.catalog_window()
    rules.check_test_period(t0, t1, allow_test_period, what="catalogue window",
                            networks=cfg.networks)
    out = set_dir(data, cfg)
    ds_path = out / "dataset.json"
    if not ds_path.exists():
        raise SystemExit(f"{ds_path}: run pull first")
    d = json.loads(ds_path.read_text())
    info = cfg.network_info[0]
    try:
        check = catalog.canary(info)
    except catalog.CanaryError as e:
        print(f"[catalog] FAILED: {e}; the service is not trusted, nothing written",
              file=sys.stderr)
        return 3
    radius = cfg.catalog_radius_km()
    kw = dict(min_mag=cfg.catalog.min_magnitude, limit=cfg.catalog.limit)
    if info.catalog == "afad":
        events, url = catalog.fetch_afad(t0, t1, cfg.lat, cfg.lon, radius, **kw)
    else:
        events, url = catalog.fetch_fdsn(info.event_url, t0, t1, cfg.lat, cfg.lon, radius, **kw)
    n, skipped = catalog.write(out / "catalog.csv", events)
    types = sorted({e.mag_type for e in events})
    d["catalog"] = {"file": "catalog.csv", "agency": info.catalog_agency,
                    "service": info.event_url, "request": url, "window": [t0.isoformat(), t1.isoformat()],
                    "centre": [cfg.lat, cfg.lon], "radius_km": radius,
                    "min_magnitude": cfg.catalog.min_magnitude, "limit": cfg.catalog.limit,
                    "events": n, "skipped": [f"{e.time:%Y-%m-%dT%H:%M:%S} {why}"
                                             for e, why in skipped],
                    "magnitude_types": types, "retrieved_utc": dataset.now_utc(),
                    "citation": info.catalog_citation, "canary": check}
    dataset.write_dataset(out, d)
    print(f"[catalog] {n} events ({', '.join(types) or 'none'}), {len(skipped)} left out, "
          f"{t0:%Y-%m-%d %H:%M} to {t1:%Y-%m-%d %H:%M} within {radius:g} km -> "
          f"{out / 'catalog.csv'}")
    if check:
        print(f"[catalog] canary: {check['events']} events from {check['window'][0]} to "
              f"{check['window'][1]} (at least {check['min_events']})")
    if n == 0:
        print("[catalog] note: the catalogue window holds no event", file=sys.stderr)
    return 0


def cmd_validate(cfg, data):
    out = set_dir(data, cfg)
    p = out / "dataset.json"
    if not p.exists():
        print(f"{p}: missing", file=sys.stderr)
        return 2
    try:
        d = dataset.validate(json.loads(p.read_text()), out)
    except dataset.DatasetError as e:
        print(f"[validate] {e}", file=sys.stderr)
        return 2
    print(f"[validate] {cfg.name}: {len(d['stations'])} stations"
          + (f", catalogue {d['catalog']['events']} events" if "catalog" in d else
             ", no catalogue"))
    return 0
