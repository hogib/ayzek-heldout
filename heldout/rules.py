"""The rules a station and a request must pass. Pure functions, no network.

Channels: ayzek replays three HH components at exactly 100 Hz (it skips any
other record and does not resample) and reads the last letter of the channel
code, Z, N or 1, E or 2. A station passes if one location code has HHZ plus
HHN/HHE (or HH1/HH2), every epoch of those three channels overlapping the
span is at 100 Hz, and their epochs cover the whole span.

Test period: the held-out pools of the protocol (ayzek_code
docs/protocol-heldout.md, section 3) start on 2023-01-01 for Greece and New
Zealand and on 2026-08-30 for KO. Until the method is frozen nobody should pull
waveforms or event lists from them, so `pull` and `catalog` refuse a span that
reaches into a pool unless asked explicitly. A network without a pool of its
own is held to the earliest one.
"""
import datetime as dt
import itertools
import math
from dataclasses import dataclass

POOL_START = {"HL": dt.datetime(2023, 1, 1), "HT": dt.datetime(2023, 1, 1),
              "HA": dt.datetime(2023, 1, 1), "HP": dt.datetime(2023, 1, 1),
              "HC": dt.datetime(2023, 1, 1), "NZ": dt.datetime(2023, 1, 1),
              "KO": dt.datetime(2026, 8, 30)}
TEST_PERIOD_START = min(POOL_START.values())
RATE_HZ = 100.0
HORIZONTALS = (("HHN", "HHE"), ("HH1", "HH2"))


class TestPeriodError(RuntimeError):
    pass


def check_test_period(start, end, allow, what="span", networks=()):
    """Raises unless [start, end) lies wholly before the pools of `networks`
    (of every network, if none is given) or `allow`."""
    pool = min((POOL_START.get(n, TEST_PERIOD_START) for n in networks),
               default=TEST_PERIOD_START)
    if end > pool and not allow:
        raise TestPeriodError(
            f"{what} {start:%Y-%m-%dT%H:%M:%S} to {end:%Y-%m-%dT%H:%M:%S} reaches into "
            f"the held-out test period (from {pool:%Y-%m-%d}); pass "
            f"--allow-test-period only after the method is frozen")


@dataclass(frozen=True)
class ChannelEpoch:
    location: str
    code: str
    sample_rate: float
    start: dt.datetime
    end: dt.datetime | None   # None: open
    azimuth: float | None = None
    dip: float | None = None


@dataclass(frozen=True)
class Choice:
    ok: bool
    location: str = ""
    channels: tuple[str, ...] = ()
    reason: str = ""


def _covers(epochs, t0, t1):
    """Whether the union of the epochs covers [t0, t1)."""
    t = t0
    for e in sorted(epochs, key=lambda e: e.start):
        if e.start > t:
            return False
        if e.end is None or e.end >= t1:
            return True
        t = max(t, e.end)
    return t >= t1


def choose_channels(epochs, t0, t1):
    """The location and three HH channels a station is replayed from, or why not."""
    over = [e for e in epochs if e.code.startswith("HH") and e.start < t1
            and (e.end is None or e.end > t0)]
    if not over:
        return Choice(False, reason="no HH channel in the span")
    reasons = []
    for loc in sorted({e.location for e in over}):
        here = [e for e in over if e.location == loc]
        codes = {e.code for e in here}
        horiz = next((h for h in HORIZONTALS if set(h) <= codes), None)
        tag = f"loc {loc or '--'}"
        if "HHZ" not in codes or horiz is None:
            reasons.append(f"{tag}: has {'/'.join(sorted(codes))}, not HHZ with HHN/HHE or HH1/HH2")
            continue
        three = ("HHZ",) + horiz
        rates = sorted({e.sample_rate for e in here if e.code in three})
        if rates != [RATE_HZ]:
            reasons.append(f"{tag}: HH at {'/'.join(f'{r:g}' for r in rates)} Hz, not 100 Hz")
            continue
        gaps = [c for c in three if not _covers([e for e in here if e.code == c], t0, t1)]
        if gaps:
            reasons.append(f"{tag}: {'/'.join(gaps)} epochs do not cover the span")
            continue
        return Choice(True, location=loc, channels=three)
    return Choice(False, reason="; ".join(reasons))


def epochs_from_station(station):
    """ChannelEpochs from an obspy Station (channel level)."""
    return [ChannelEpoch(c.location_code, c.code, float(c.sample_rate),
                         c.start_date.datetime, c.end_date.datetime if c.end_date else None,
                         None if c.azimuth is None else float(c.azimuth),
                         None if c.dip is None else float(c.dip))
            for c in station.channels]


# Below this |det| of the three components' unit vectors the horizontals cannot
# be rotated to north and east (NZ.MKTZ from 2025-09-30: HH2 dips 90 degrees,
# along HHZ).
MIN_ORIENTATION_DET = 0.5


def _unit(azimuth, dip):
    """Unit vector (north, east, down) of a component, SEED angles in degrees."""
    a, d = math.radians(azimuth), math.radians(dip)
    return (math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d))


def orientation_det(epochs, location, channels, t0, t1):
    """Smallest |det| of the three components' unit vectors at any time of the
    span when all three have an epoch in force (1 for vertical, north and east),
    or None where an angle is missing."""
    eps = [e for e in epochs if e.location == location and e.code in channels
           and e.start < t1 and (e.end is None or e.end > t0)]
    cuts = sorted({t0, t1, *(e.start for e in eps if t0 < e.start < t1),
                   *(e.end for e in eps if e.end is not None and t0 < e.end < t1)})
    worst = None
    for a, b in itertools.pairwise(cuts):
        t = a + (b - a) / 2
        rows = []
        for code in channels:
            now = [e for e in eps if e.code == code and e.start <= t and (e.end is None or e.end > t)]
            if not now:
                break                       # a gap between epochs: nothing recorded
            if now[0].azimuth is None or now[0].dip is None:
                return None
            rows.append(_unit(now[0].azimuth, now[0].dip))
        if len(rows) < 3:
            continue
        (a1, a2, a3), (b1, b2, b3), (c1, c2, c3) = rows
        det = abs(a1 * (b2 * c3 - b3 * c2) - a2 * (b1 * c3 - b3 * c1) + a3 * (b1 * c2 - b2 * c1))
        worst = det if worst is None else min(worst, det)
    return worst


def azimuth_offsets(epochs, location, channels, t0, t1):
    """Largest offset in degrees of each horizontal from its nominal azimuth
    (N or 1: 0, E or 2: 90) over the epochs in the span. ayzek reads 1 as N
    and 2 as E without rotating, so an offset turns what it sees."""
    out = {}
    for code, want in zip(channels[1:], (0.0, 90.0)):
        offs = []
        for e in epochs:
            if (e.location == location and e.code == code and e.azimuth is not None
                    and e.start < t1 and (e.end is None or e.end > t0)):
                d = abs(e.azimuth - want) % 360
                offs.append(min(d, 360 - d))
        out[code] = round(max(offs), 1) if offs else None
    return out


def check_traces(traces, location, channels):
    """Splits obspy traces into those ayzek can replay and the rest, with reasons."""
    keep, drop = [], []
    for tr in traces:
        s = tr.stats
        if s.location != location or s.channel not in channels:
            drop.append((tr, f"{s.location}.{s.channel} not the chosen channels"))
        elif s.sampling_rate != RATE_HZ:
            drop.append((tr, f"{s.channel} at {s.sampling_rate:g} Hz"))
        elif tr.data.dtype.kind != "i":
            drop.append((tr, f"{s.channel} has {tr.data.dtype} samples, not integers"))
        else:
            keep.append(tr)
    return keep, drop
