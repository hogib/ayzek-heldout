"""select: a test pool's sequences, reserve split and quiet windows (held-out
protocol, sections 3 and 10), written as set configs for probe, pull and
catalog.

    heldout select greece --start 2023-01-01T00:00:00 --end FREEZE --name now \\
        --allow-test-period                  # after the freeze only
    heldout select nz --start 2022-01-01T00:00:00 --end 2023-01-01T00:00:00 \\
        --name dry2022                       # a dry run before the pool

Every step is fixed by the protocol:

1. Usable stations: every station of the group within its region with three HH
   channels at 100 Hz and at least 90% coverage over the whole period, by the
   probe's own rules (fetch.probe_rows).
2. The group's catalogue over the period, every magnitude, in requests of a
   week (GeoNet's monthly answers run to 25 MB of QuakeML and broke off), a
   request the service refuses as too large (HTTP 413) or breaks off
   (IncompleteRead; GeoNet's weekly answers within 1300 km reach 20-30 MB)
   being halved until it answers, after the canary check.
3. Sequences: in time order, each event of M >= 4.5 with at least five usable
   stations within 150 km of its epicentre starts a sequence, replayed from 10
   min before it for 3 h on the 8 nearest of those stations, unless it lies
   within 3 h after the first event of an earlier sequence with which its 8
   stations share one (it then belongs to that sequence).
4. Reserve split (not for a prospective span): random.Random(42), one draw per
   sequence in time order; below 0.5 is "now", otherwise "reserve".
5. Stopping rule: the "now" sequences in time order until their scorable
   catalogue events (within 250 km of the centroid of their 8 stations, within
   the replayed span, as ayzek scores them) reach the target; the sequence that
   crosses it is included whole.
6. Quiet windows: random.Random(43) (prospective: 44); each draw a start on the
   minute, uniform over [start + 30 min, end - 6 h - 30 min), so that the
   margins lie in the period, then one selected sequence's
   stations, uniform; accepted if no catalogue event lies within 250 km of any
   of them from 30 min before the window to 30 min after it, it does not
   overlap an accepted window sharing a station, and every station's
   availability covers 90% of it; until 24 are accepted. If 10,000 draws give
   fewer, the draws start again from the same seed with catalogue events below
   M2 farther than 100 km from every station disregarded.

Writes OUT/<group>_<name>/selection.json (inputs, every qualifying sequence
with its assignment, stations and scorable count, the stopping point, the
quiet draws) and sets/<set>.toml for the selected "now" sequences and the
quiet windows, each with its own station list. Reserve sequences get no set.
"""
import datetime as dt
import json
import math
import random
import sys
from pathlib import Path

from . import availability, catalog, config, dataset, fetch, networks, rules

GROUPS = {
    # name: (networks, region centre, region radius km), as tools/make_tuning_sets.py
    "greece": (("HL", "HT", "HA", "HP", "HC"), (38.5, 23.5), 650.0),
    "nz": (("NZ",), (-41.0, 174.0), 1000.0),
    "ko": (("KO",), (39.0, 35.0), 1100.0),
}
TARGET = {"ko": 240, "greece": 150, "nz": 150}
MIN_MAG, MIN_STATIONS, STATION_RADIUS_KM, N_STATIONS = 4.5, 5, 150.0, 8
LEAD, SPAN, GAP = dt.timedelta(minutes=10), dt.timedelta(hours=3), dt.timedelta(hours=3)
SCORE_RADIUS_KM = 250.0
RESERVE_SEED, QUIET_SEED, PROSPECTIVE_QUIET_SEED = 42, 43, 44
QUIET_N, QUIET_LEN, QUIET_MARGIN = 24, dt.timedelta(hours=6), dt.timedelta(minutes=30)
QUIET_MIN_COVERAGE, QUIET_MAX_DRAWS = 0.9, 10_000
RELAX_BELOW_M, RELAX_BEYOND_KM = 2.0, 100.0
CATALOG_MARGIN_KM = 300.0  # the group catalogue reaches this far beyond the region
CATALOG_CHUNK = dt.timedelta(days=7)


def km(lat1, lon1, lat2, lon2):
    return fetch.km(lat1, lon1, lat2, lon2)


def nearest(stations, lat, lon, radius_km=STATION_RADIUS_KM, n=N_STATIONS):
    """The usable stations within radius_km of (lat, lon), nearest first, one per
    station code (the nearer of two networks' stations with one code), at most n;
    and how many there were in all."""
    near = sorted((km(lat, lon, s["lat"], s["lon"]), s["network"], s["station"], s)
                  for s in stations)
    out, codes = [], set()
    for d, _, code, s in near:
        if d > radius_km or code in codes:
            continue
        codes.add(code)
        out.append(s)
    return out[:n], len(out)


def sequences(events, stations):
    """The qualifying sequences of a time-ordered catalogue, step 3."""
    out = []
    for e in sorted(events, key=lambda e: e.time):
        if e.magnitude is None or e.magnitude < MIN_MAG:
            continue
        chosen, n_within = nearest(stations, e.lat, e.lon)
        if n_within < MIN_STATIONS:
            continue
        codes = {f"{s['network']}.{s['station']}" for s in chosen}
        owner = next((q for q in reversed(out) if e.time - q["first"].time < GAP
                      and codes & q["codes"]), None)
        if owner is not None:
            owner["joined"].append(e)
            continue
        out.append({"first": e, "start": e.time - LEAD, "end": e.time - LEAD + SPAN,
                    "stations": chosen, "codes": codes, "usable_within": n_within,
                    "joined": []})
    return out


def split(seqs, seed=RESERVE_SEED):
    """Step 4: the coin, one draw per sequence in time order."""
    rng = random.Random(seed)
    for q in seqs:
        q["coin"] = rng.random()
        q["assign"] = "now" if q["coin"] < 0.5 else "reserve"


def centroid(stations):
    """As ayzek's Network::score(): the mean latitude and longitude."""
    return (sum(s["lat"] for s in stations) / len(stations),
            sum(s["lon"] for s in stations) / len(stations))


def scorable(q, events):
    lat, lon = centroid(q["stations"])
    return sum(1 for e in events if q["start"] <= e.time < q["end"]
               and km(lat, lon, e.lat, e.lon) <= SCORE_RADIUS_KM)


def stop(now, events, target):
    """Step 5: the selected "now" sequences, and whether the target was reached."""
    total, out = 0, []
    for q in now:
        q["scorable"] = scorable(q, events)
        total += q["scorable"]
        q["cumulative"] = total
        out.append(q)
        if total >= target:
            return out, True
    return out, False


def quiet_windows(selected, events, t0, t1, seed, covered, relaxed=False):
    """Step 6 for one pass: (accepted windows, draws made, rejections by reason).
    covered(stations, start, end) tells whether every station's availability
    covers QUIET_MIN_COVERAGE of the window; it is asked only for windows the
    catalogue accepts."""
    rng = random.Random(seed)
    first = t0 + QUIET_MARGIN
    minutes = int((t1 - QUIET_MARGIN - QUIET_LEN - first).total_seconds() // 60)
    accepted, draws, why = [], 0, {"catalogue event": 0, "overlap": 0, "coverage": 0}
    while len(accepted) < QUIET_N and draws < QUIET_MAX_DRAWS:
        draws += 1
        start = first + dt.timedelta(minutes=rng.randrange(minutes))
        q = selected[rng.randrange(len(selected))]
        end = start + QUIET_LEN
        a, b = start - QUIET_MARGIN, end + QUIET_MARGIN
        near = False
        for e in events:
            if not a <= e.time < b:
                continue
            ds = [km(s["lat"], s["lon"], e.lat, e.lon) for s in q["stations"]]
            if min(ds) > SCORE_RADIUS_KM:
                continue
            if (relaxed and e.magnitude is not None and e.magnitude < RELAX_BELOW_M
                    and min(ds) > RELAX_BEYOND_KM):
                continue
            near = True
            break
        if near:
            why["catalogue event"] += 1
            continue
        if any(w["start"] < end and start < w["end"] and w["codes"] & q["codes"]
               for w in accepted):
            why["overlap"] += 1
            continue
        if not covered(q["stations"], start, end):
            why["coverage"] += 1
            continue
        accepted.append({"start": start, "end": end, "stations": q["stations"],
                         "codes": q["codes"], "sequence": q["index"], "draw": draws})
    return accepted, draws, why


def group_catalogue(info, t0, t1, lat, lon, radius_km):
    """Every catalogue event of the region over [t0, t1), in weekly requests;
    one the service refuses as too large (HTTP 413) or breaks off before its
    end (IncompleteRead, not requested again whole) is halved until it answers
    (down to an hour)."""
    import http.client
    import urllib.error
    events, requests = [], []

    def halve(a, b):
        mid = a + (b - a) / 2
        fetch(a, mid)
        fetch(mid, b)

    def fetch(a, b):
        try:
            if info.catalog == "afad":
                evs, url = catalog.fetch_afad(a, b, lat, lon, radius_km)
            else:
                evs, url = catalog.fetch_fdsn(info.event_url, a, b, lat, lon, radius_km,
                                              cut_off_final=True)
        except urllib.error.HTTPError as e:
            if e.code == 413 and b - a > dt.timedelta(hours=1):
                halve(a, b)
                return
            raise
        except http.client.IncompleteRead:
            if b - a > dt.timedelta(hours=1):
                print(f"  event service broke off {a:%Y-%m-%d %H:%M} to {b:%Y-%m-%d %H:%M};"
                      " halving", file=sys.stderr)
                halve(a, b)
                return
            raise
        if len(evs) >= 10_000:
            raise SystemExit(f"{url}: {len(evs)} events in one request, a service limit "
                             "may have cut the list")
        events.extend(e for e in evs if a <= e.time < b)
        requests.append(url)

    a = t0
    while a < t1:
        b = min(a + CATALOG_CHUNK, t1)
        fetch(a, b)
        a = b
    events.sort(key=lambda e: e.time)
    return events, requests


def coverage_check(info, cache):
    """covered(stations, start, end) for quiet windows: fdsnws/availability, or
    for GeoNet the open-data bucket's day files (as the probe)."""
    def covered(stations, start, end):
        for s in stations:
            if info.availability:
                c = availability.fdsn_coverage(info.availability, s["network"], s["station"],
                                               s["location"], s["channels"], start, end)
            else:
                days = list(availability.days_of(start, end))
                for d in days:
                    if d not in cache:
                        cache[d] = availability.day_keys(info.day_listing, d)
                c = availability.day_coverage({d: cache[d] for d in days}, s["network"],
                                              s["station"], s["location"], s["channels"],
                                              start, end)
            if min(c.values()) < QUIET_MIN_COVERAGE:
                return False
        return True
    return covered


def event_json(e):
    return {"time": e.time.isoformat(), "lat": e.lat, "lon": e.lon, "depth_km": e.depth_km,
            "magnitude": e.magnitude, "type": e.mag_type, "id": e.event_id}


def set_toml(name, nets, start, end, centre, radius_km, stations, comment):
    net = f'"{nets[0]}"' if len(nets) == 1 else "[" + ", ".join(f'"{n}"' for n in nets) + "]"
    codes = ", ".join(f'"{s["network"]}.{s["station"]}"' for s in stations)
    return (f"# {comment}\n"
            f'name = "{name}"\nnetwork = {net}\n'
            f'start = "{start.isoformat()}"\nend = "{end.isoformat()}"\n'
            f"centre = [{centre[0]:.5f}, {centre[1]:.5f}]\nradius_km = {radius_km:.1f}\n"
            f"max_stations = {len(stations)}\nmin_coverage = 0.0\nstations = [{codes}]\n"
            f"\n[catalog]\nlead_days = 1.0\nradius_km = {SCORE_RADIUS_KM + 150.0:.1f}\n")


def cmd_select(group, start, end, name, out, prospective=False, target=None, quiet=True,
               allow_test_period=False):
    nets, (glat, glon), gradius = GROUPS[group]
    rules.check_test_period(start, end, allow_test_period, what="selection period",
                            networks=nets)
    target = target or TARGET[group]
    info = networks.get(nets[0])
    period = config.parse({"name": f"select_{group}", "network": list(nets),
                           "start": start.isoformat(), "end": end.isoformat(),
                           "centre": [glat, glon], "radius_km": gradius,
                           "max_stations": 1000, "min_coverage": QUIET_MIN_COVERAGE})
    c = fetch.client(period, "station")
    rows, basis = fetch.probe_rows(period, c)
    usable = [r for r in rows if r["ok"]]
    print(f"[select] {len(usable)} usable of {len(rows)} {'/'.join(nets)} stations "
          f"within {gradius:g} km, {start:%Y-%m-%d} to {end:%Y-%m-%d} ({basis})")
    check = catalog.canary(info)
    events, requests = group_catalogue(info, start, end, glat, glon,
                                       gradius + CATALOG_MARGIN_KM)
    print(f"[select] {len(events)} catalogue events ({len(requests)} requests; canary "
          f"{check['events'] if check else '-'})")
    seqs = sequences(events, usable)
    for i, q in enumerate(seqs, 1):
        q["index"] = i
    if prospective:
        for q in seqs:
            q["assign"] = "now"
    else:
        split(seqs)
    now = [q for q in seqs if q["assign"] == "now"]
    selected, reached = stop(now, events, target)
    print(f"[select] {len(seqs)} qualifying sequences, {len(now)} now; {len(selected)} "
          f"selected, {selected[-1]['cumulative'] if selected else 0} scorable events "
          f"({'target ' + str(target) + ' reached' if reached else 'under the target ' + str(target)})")
    windows, passes = [], []
    if quiet and selected:
        seed = PROSPECTIVE_QUIET_SEED if prospective else QUIET_SEED
        covered = coverage_check(info, {})
        for relaxed in (False, True):
            windows, draws, why = quiet_windows(selected, events, start, end, seed, covered,
                                                relaxed)
            passes.append({"relaxed": relaxed, "draws": draws, "accepted": len(windows),
                           "rejected": why})
            if len(windows) >= QUIET_N:
                break
        print(f"[select] {len(windows)} quiet windows after "
              + "; ".join(f"{p['draws']} draws{' (relaxed)' if p['relaxed'] else ''}"
                          for p in passes))
    base = Path(out) / f"{group}_{name}"
    sets = base / "sets"
    sets.mkdir(parents=True, exist_ok=True)
    tag = f"{group}_{name}"
    for q in selected:
        e = q["first"]
        (sets / f"{tag}_seq{q['index']:03d}.toml").write_text(set_toml(
            f"{tag}_seq{q['index']:03d}", nets, q["start"], q["end"], (e.lat, e.lon),
            STATION_RADIUS_KM, q["stations"],
            f"heldout select {group} {name}: sequence {q['index']} of {len(seqs)}, first "
            f"event {e.time:%Y-%m-%dT%H:%M:%S} {e.mag_type} {e.magnitude} ({e.event_id})"))
    for j, w in enumerate(windows, 1):
        lat, lon = centroid(w["stations"])
        r = max(km(lat, lon, s["lat"], s["lon"]) for s in w["stations"]) + 10.0
        (sets / f"{tag}_quiet{j:02d}.toml").write_text(set_toml(
            f"{tag}_quiet{j:02d}", nets, w["start"], w["end"], (lat, lon), r, w["stations"],
            f"heldout select {group} {name}: quiet window {j} of {len(windows)} (draw "
            f"{w['draw']}), on the stations of sequence {w['sequence']}"))
    record = {
        "group": group, "name": name, "networks": list(nets), "prospective": prospective,
        "period": [start.isoformat(), end.isoformat()], "target": target,
        "rules": {"min_magnitude": MIN_MAG, "min_stations": MIN_STATIONS,
                  "station_radius_km": STATION_RADIUS_KM, "stations": N_STATIONS,
                  "lead_s": LEAD.total_seconds(), "span_s": SPAN.total_seconds(),
                  "gap_s": GAP.total_seconds(), "score_radius_km": SCORE_RADIUS_KM,
                  "reserve_seed": None if prospective else RESERVE_SEED,
                  "quiet_seed": PROSPECTIVE_QUIET_SEED if prospective else QUIET_SEED,
                  "quiet_windows": QUIET_N, "quiet_hours": QUIET_LEN.total_seconds() / 3600,
                  "quiet_margin_s": QUIET_MARGIN.total_seconds(),
                  "quiet_min_coverage": QUIET_MIN_COVERAGE, "quiet_max_draws": QUIET_MAX_DRAWS,
                  "relaxed": [RELAX_BELOW_M, RELAX_BEYOND_KM]},
        "stations": {"basis": basis, "usable": [
            {k: r[k] for k in ("network", "station", "lat", "lon", "location", "channels",
                               "coverage_min")} for r in usable],
            "rejected": [{k: r.get(k) for k in ("network", "station", "reason")}
                         for r in rows if not r["ok"]]},
        "catalogue": {"agency": info.catalog_agency, "requests": requests,
                      "events": len(events), "canary": check},
        "sequences": [{"index": q["index"], "first": event_json(q["first"]),
                       "joined": [event_json(e) for e in q["joined"]],
                       "start": q["start"].isoformat(), "end": q["end"].isoformat(),
                       "usable_within_km": q["usable_within"],
                       "stations": sorted(q["codes"]), "assign": q["assign"],
                       "coin": q.get("coin"), "scorable": q.get("scorable"),
                       "cumulative": q.get("cumulative"), "selected": q in selected}
                      for q in seqs],
        "target_reached": reached,
        "quiet": {"passes": passes, "windows": [
            {"start": w["start"].isoformat(), "end": w["end"].isoformat(),
             "sequence": w["sequence"], "draw": w["draw"], "stations": sorted(w["codes"])}
            for w in windows]},
        "selected_utc": dataset.now_utc(),
        "tool": {"name": "ayzek-heldout", "git_commit": dataset.tool_commit()}}
    dataset.write_json(base / "selection.json", record)
    print(f"[select] {len(selected)} sequence sets and {len(windows)} quiet sets -> {sets}")
    if not selected:
        print("[select] no sequence qualified", file=sys.stderr)
        return 1
    return 0
