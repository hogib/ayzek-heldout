"""How much of a span each channel covers, from time-span listings only.

KO and the Greek networks: fdsnws/availability (format=text), which lists the
spans the archive holds. NZ: GeoNet has no availability service, so the open
data bucket's object listing (one miniSEED file per channel and UTC day) is
used: a day counts if its file exists. Only object keys are read, never sizes
or contents, so for NZ coverage is an upper bound at day resolution.
"""
import datetime as dt
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict


def _get(url, tries=5):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=300) as f:
                return f.status, f.read()
        except urllib.error.HTTPError as e:
            if e.code in (204, 404):
                return e.code, b""
            if attempt == tries - 1:
                raise
        except OSError:
            if attempt == tries - 1:
                raise
        time.sleep(3 * 2 ** attempt)


def parse_spans(text, t0, t1):
    """Seconds of [t0, t1) covered per (location, channel), from availability text."""
    cover = defaultdict(float)
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split()
        loc = "" if f[2] == "--" else f[2]
        a = dt.datetime.fromisoformat(f[6].removesuffix("Z")).replace(tzinfo=None)
        b = dt.datetime.fromisoformat(f[7].removesuffix("Z")).replace(tzinfo=None)
        a, b = max(a, t0), min(b, t1)
        if b > a:
            cover[(loc, f[3])] += (b - a).total_seconds()
    return cover


def fdsn_coverage(url, net, sta, loc, channels, t0, t1):
    """Fraction of [t0, t1) covered on each channel, from fdsnws/availability."""
    q = urllib.parse.urlencode({
        "net": net, "sta": sta, "loc": loc or "--", "cha": ",".join(channels),
        "starttime": t0.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": t1.strftime("%Y-%m-%dT%H:%M:%S"), "format": "text"})
    _, body = _get(f"{url}?{q}")
    cover = parse_spans(body.decode(), t0, t1)
    span = (t1 - t0).total_seconds()
    return {c: min(1.0, cover.get((loc, c), 0.0) / span) for c in channels}


DAY_KEY = re.compile(r"/([A-Z0-9]+)\.(\w+)/\d{4}\.\d{3}\.\1\.(\w*)-(\w{3})\.\2\.D$")


def day_keys(bucket, day):
    """(net, sta, loc, cha) of every object for one UTC day in GeoNet's bucket."""
    prefix = f"waveforms/miniseed/{day:%Y}/{day:%Y}.{day.timetuple().tm_yday:03d}/"
    have, token = set(), None
    while True:
        q = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            q["continuation-token"] = token
        _, xml = _get(f"{bucket}/?{urllib.parse.urlencode(q)}")
        root = ET.fromstring(xml)
        ns = {"s": root.tag.split("}")[0][1:]}
        for k in root.iterfind("s:Contents/s:Key", ns):
            m = DAY_KEY.search(k.text)
            if m:
                sta, net, loc, cha = m.groups()
                have.add((net, sta, loc, cha))
        nxt = root.find("s:NextContinuationToken", ns)
        if nxt is None:
            return have
        token = nxt.text


def days_of(t0, t1):
    d = dt.datetime(t0.year, t0.month, t0.day)
    while d < t1:
        yield d
        d += dt.timedelta(days=1)


def day_coverage(per_day, net, sta, loc, channels, t0, t1):
    """Fraction of [t0, t1) on days whose file exists, per channel."""
    span = (t1 - t0).total_seconds()
    out = {}
    for c in channels:
        s = 0.0
        for d, have in per_day.items():
            if (net, sta, loc, c) in have:
                a, b = max(d, t0), min(d + dt.timedelta(days=1), t1)
                s += max(0.0, (b - a).total_seconds())
        out[c] = s / span
    return out
