"""The catalogue next to each set, in the CSV ayzek's --catalog reads.

ayzek (app/ayzek.cpp, load_afad_catalog in src/pipeline/network.cpp) reads
AFAD's export: a header line, then

    Date,Longitude,Latitude,Depth,Rms,Type,Magnitude,Location,EventID
    09/11/2025 18:13:37,28.23972,39.18917,10.15,0.26,ML,1.1,Sındırgı (Balıkesir),691876

with Date as DD/MM/YYYY HH:MM:SS in UTC, Depth in km and Type the magnitude
type. It splits on commas and reads the first seven fields; fractions of a
second are ignored, so times are written to the whole second (rounded). An
event without depth or magnitude would be skipped by ayzek, so it is left
out here and counted instead. Commas in Location become semicolons.
"""
import datetime as dt
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from . import retry


def _read(url):
    with urllib.request.urlopen(url, timeout=300) as f:
        return f.read()

HEADER = ["Date", "Longitude", "Latitude", "Depth", "Rms", "Type", "Magnitude",
          "Location", "EventID"]
NOT_EVENTS = {"not existing", "not reported", "other event"}


@dataclass(frozen=True)
class Event:
    time: dt.datetime     # UTC, naive
    lat: float
    lon: float
    depth_km: float | None
    magnitude: float | None
    mag_type: str
    rms: float | None = None
    location: str = ""
    event_id: str = ""
    event_type: str = ""


def format_date(t):
    t = (t + dt.timedelta(microseconds=500_000)).replace(microsecond=0)
    return t.strftime("%d/%m/%Y %H:%M:%S")


def _num(x, nd):
    """Up to nd decimals, trailing zeros dropped: 28.23972, 10.15, 1.0 -> 1."""
    if x is None:
        return ""
    s = f"{float(x):.{nd}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def rows(events):
    """CSV rows (header first) and the events left out, with reasons."""
    out, skipped = [HEADER], []
    for e in sorted(events, key=lambda e: e.time):
        if e.event_type in NOT_EVENTS:
            skipped.append((e, f"event type {e.event_type!r}"))
            continue
        if e.depth_km is None or e.magnitude is None:
            skipped.append((e, "no depth" if e.depth_km is None else "no magnitude"))
            continue
        out.append([format_date(e.time), _num(e.lon, 5), _num(e.lat, 5), _num(e.depth_km, 2),
                    _num(e.rms, 2), (e.mag_type or "M").replace(",", ";"),
                    _num(e.magnitude, 2), " ".join(e.location.replace(",", ";").split()),
                    e.event_id.replace(",", ";")])
    return out, skipped


def write(path, events):
    table, skipped = rows(events)
    # Plain comma-joined lines, no quoting: ayzek splits on commas.
    path.write_text("".join(",".join(r) + "\n" for r in table), encoding="utf-8")
    return len(table) - 1, skipped


def read_back(path):
    """Parses a catalog.csv the way ayzek does: (epoch, lat, lon, depth, mag, type)."""
    out = []
    with open(path, encoding="utf-8") as f:
        next(f)
        for line in f:
            p = line.rstrip("\n").split(",")
            t = dt.datetime.strptime(p[0], "%d/%m/%Y %H:%M:%S").replace(tzinfo=dt.UTC)
            out.append((t.timestamp(), float(p[2]), float(p[1]), float(p[3]), float(p[6]), p[5]))
    return out


# ---- sources ----------------------------------------------------------------

def from_quakeml(cat):
    """Events from an obspy Catalog, preferred origin and magnitude."""
    out = []
    for ev in cat:
        o = ev.preferred_origin() or (ev.origins[0] if ev.origins else None)
        if o is None:
            continue
        m = ev.preferred_magnitude() or (ev.magnitudes[0] if ev.magnitudes else None)
        rms = o.quality.standard_error if o.quality is not None else None
        desc = next((d.text for d in ev.event_descriptions if d.text), "")
        out.append(Event(
            time=o.time.datetime, lat=float(o.latitude), lon=float(o.longitude),
            depth_km=None if o.depth is None else float(o.depth) / 1000.0,
            magnitude=None if m is None or m.mag is None else float(m.mag),
            mag_type=(m.magnitude_type or "") if m is not None else "",
            rms=rms, location=desc,
            event_id=str(ev.resource_id).rsplit("/", 1)[-1].split("=")[-1],
            event_type=ev.event_type or ""))
    return out


def fdsn_url(event_url, t0, t1, lat, lon, radius_km, min_mag=None, limit=None):
    """The fdsnws/event query. Built by hand: obspy's client reads the
    service's WADL first, which fails when a node is busy, and refuses
    parameters (limit) a WADL does not list without telling the service."""
    q = {"starttime": t0.strftime("%Y-%m-%dT%H:%M:%S"),
         "endtime": t1.strftime("%Y-%m-%dT%H:%M:%S"),
         "latitude": f"{lat:g}", "longitude": f"{lon:g}",
         "maxradius": f"{radius_km / 111.195:.4f}", "orderby": "time-asc"}
    if min_mag is not None:
        q["minmagnitude"] = f"{min_mag:g}"
    if limit is not None:
        q["limit"] = str(limit)
    return f"{event_url}?{urllib.parse.urlencode(q)}"


def fetch_fdsn(event_url, t0, t1, lat, lon, radius_km, min_mag=None, limit=None):
    import io
    import urllib.error
    from obspy import read_events
    url = fdsn_url(event_url, t0, t1, lat, lon, radius_km, min_mag, limit)
    try:
        body = retry.call(_read, url, what="event service")
    except urllib.error.HTTPError as e:
        if e.code in (204, 404):  # 404: some services' "no events"
            return [], url
        raise
    if not body.strip():
        return [], url
    return from_quakeml(read_events(io.BytesIO(body), format="QUAKEML")), url


def afad_url(t0, t1, lat, lon, radius_km, min_mag=None, limit=None):
    q = {"start": t0.strftime("%Y-%m-%dT%H:%M:%S"), "end": t1.strftime("%Y-%m-%dT%H:%M:%S"),
         "lat": f"{lat:g}", "lon": f"{lon:g}", "maxrad": f"{radius_km * 1000:.0f}",
         "format": "json", "orderby": "time"}
    if min_mag is not None:
        q["minmag"] = f"{min_mag:g}"
    if limit is not None:
        q["limit"] = str(limit)
    from .networks import AFAD_EVENTS
    return f"{AFAD_EVENTS}?{urllib.parse.urlencode(q)}"


def from_afad(records):
    out = []
    for r in records:
        t = dt.datetime.fromisoformat(str(r["date"]).removesuffix("Z"))
        loc = r.get("location") or ", ".join(
            x for x in (r.get("district"), r.get("province")) if x)
        out.append(Event(
            time=t.replace(tzinfo=None), lat=float(r["latitude"]), lon=float(r["longitude"]),
            depth_km=None if r.get("depth") in (None, "") else float(r["depth"]),
            magnitude=None if r.get("magnitude") in (None, "") else float(r["magnitude"]),
            mag_type=str(r.get("type") or ""),
            rms=None if r.get("rms") in (None, "") else float(r["rms"]),
            location=str(loc), event_id=str(r.get("eventID", ""))))
    return out


def fetch_afad(t0, t1, lat, lon, radius_km, min_mag=None, limit=None):
    url = afad_url(t0, t1, lat, lon, radius_km, min_mag, limit)
    body = retry.call(_read, url, what="AFAD event service")
    return from_afad(json.loads(body) if body.strip() else []), url
