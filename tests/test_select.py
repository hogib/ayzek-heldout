"""select's rules (held-out protocol, sections 3 and 10) on made-up catalogues."""
import datetime as dt
import random

import pytest

from heldout import select
from heldout.catalog import Event

T0 = dt.datetime(2022, 6, 1)


def station(code, lat, lon, net="NZ"):
    return {"network": net, "station": code, "lat": lat, "lon": lon, "location": "10",
            "channels": ["HHZ", "HHN", "HHE"]}


# Ten stations around (-41, 174), 0.1 deg (11 km) apart in latitude, and five
# around (-45, 168), 500 km away.
NORTH = [station(f"N{i}", -41.0 + 0.1 * i, 174.0) for i in range(10)]
SOUTH = [station(f"S{i}", -45.0 + 0.1 * i, 168.0) for i in range(5)]


def event(minutes, lat=-41.0, lon=174.0, mag=4.6, eid=None):
    return Event(time=T0 + dt.timedelta(minutes=minutes), lat=lat, lon=lon, depth_km=10.0,
                 magnitude=mag, mag_type="MLv", rms=None, location="",
                 event_id=eid or f"e{minutes}")


def test_nearest_takes_the_eight_nearest_codes_once():
    twin = station("N0", -41.0, 174.0, net="XX")  # the same code in another network
    chosen, n = select.nearest(NORTH + SOUTH + [twin], -41.0, 174.0)
    assert n == 10 and [s["station"] for s in chosen] == [f"N{i}" for i in range(8)]
    assert sum(s["station"] == "N0" for s in chosen) == 1


def test_sequences():
    events = [event(0), event(60, mag=4.7),                      # joins the first
              event(90, lat=-45.0, lon=168.0, mag=4.8),          # far: its own sequence
              event(181, mag=4.9),                               # 3 h 1 min: a new one
              event(300, mag=4.4),                               # too small
              event(400, lat=-30.0, lon=170.0, mag=6.0)]         # no stations near
    seqs = select.sequences(events, NORTH + SOUTH)
    assert [q["first"].event_id for q in seqs] == ["e0", "e90", "e181"]
    assert [e.event_id for e in seqs[0]["joined"]] == ["e60"]
    q = seqs[0]
    assert (q["start"], q["end"]) == (T0 - dt.timedelta(minutes=10),
                                      T0 + dt.timedelta(hours=2, minutes=50))
    assert len(q["stations"]) == 8 and q["usable_within"] == 10
    assert len(seqs[1]["stations"]) == 5          # the five southern stations, enough


def test_too_few_stations_do_not_qualify():
    assert select.sequences([event(0)], NORTH[:4]) == []


def test_the_coin_with_seed_42():
    seqs = [{"i": i} for i in range(6)]
    select.split(seqs)
    rng = random.Random(42)
    assert [q["assign"] for q in seqs] == ["now" if rng.random() < 0.5 else "reserve"
                                           for _ in range(6)]
    assert [q["assign"] for q in seqs][:5] == ["reserve", "now", "now", "now", "reserve"]


def seq(minutes, stations=NORTH[:8]):
    q = {"first": event(minutes), "stations": stations,
         "codes": {f"{s['network']}.{s['station']}" for s in stations}, "index": minutes}
    q["start"], q["end"] = q["first"].time - select.LEAD, q["first"].time - select.LEAD + select.SPAN
    return q


def test_scorable_counts_events_within_250_km_of_the_centroid_in_the_span():
    q = seq(0)
    events = [event(5), event(100, lat=-42.0), event(100, lat=-45.0),   # 0, 111, 444 km
              event(-20), event(171)]                                    # before and after
    assert select.scorable(q, events) == 2


def test_the_stopping_rule_includes_the_crossing_sequence():
    now = [seq(0), seq(1000), seq(2000)]
    events = [event(1 + i) for i in range(3)] + [event(1001 + i) for i in range(4)] \
        + [event(2001)]
    selected, reached = select.stop(now, events, target=5)
    assert reached and [q["cumulative"] for q in selected] == [3, 7]
    selected, reached = select.stop(now, events, target=50)
    assert not reached and len(selected) == 3


def always(stations, a, b):
    return True


def test_quiet_windows_avoid_catalogue_events_and_overlaps():
    t0, t1 = T0, T0 + dt.timedelta(days=60)
    q = seq(0)
    got, draws, why = select.quiet_windows([q], [], t0, t1, 43, always)
    assert len(got) == 24 and draws >= 24
    for w in got:
        assert t0 + select.QUIET_MARGIN <= w["start"]
        assert w["end"] <= t1 - select.QUIET_MARGIN
    assert not any(a["start"] < b["end"] and b["start"] < a["end"]
                   for i, a in enumerate(got) for b in got[i + 1:])
    # An event every 3 h at the stations rejects every window.
    events = [event(180 * k) for k in range(60 * 8)]
    got, draws, why = select.quiet_windows([q], events, t0, t1, 43, always)
    assert got == [] and draws == select.QUIET_MAX_DRAWS
    assert why["catalogue event"] == draws
    # Coverage refuses what the catalogue accepts.
    got, draws, why = select.quiet_windows([q], [], t0, t1, 43, lambda *a: False)
    assert got == [] and why["coverage"] == draws


def test_the_relaxed_rule_disregards_small_distant_events_only():
    t0, t1 = T0, T0 + dt.timedelta(days=60)
    q = seq(0)
    small_far = [event(180 * k, lat=-42.6, mag=1.5) for k in range(60 * 8)]   # ~180 km
    assert select.quiet_windows([q], small_far, t0, t1, 43, always)[0] == []
    assert len(select.quiet_windows([q], small_far, t0, t1, 43, always, relaxed=True)[0]) == 24
    big_far = [event(180 * k, lat=-42.6, mag=2.5) for k in range(60 * 8)]
    assert select.quiet_windows([q], big_far, t0, t1, 43, always, relaxed=True)[0] == []


def test_the_same_seed_draws_the_same_windows():
    t0, t1 = T0, T0 + dt.timedelta(days=60)
    a = select.quiet_windows([seq(0), seq(9000, NORTH[2:])], [], t0, t1, 43, always)[0]
    b = select.quiet_windows([seq(0), seq(9000, NORTH[2:])], [], t0, t1, 43, always)[0]
    assert [(w["start"], w["sequence"]) for w in a] == [(w["start"], w["sequence"]) for w in b]
    c = select.quiet_windows([seq(0), seq(9000, NORTH[2:])], [], t0, t1, 44, always)[0]
    assert [w["start"] for w in a] != [w["start"] for w in c]


def test_select_refuses_a_pool_without_the_flag(tmp_path):
    from heldout import rules
    with pytest.raises(rules.TestPeriodError):
        select.cmd_select("nz", dt.datetime(2023, 6, 1), dt.datetime(2023, 7, 1), "x",
                          tmp_path)
    assert not any(tmp_path.iterdir())
