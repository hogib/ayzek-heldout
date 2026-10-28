import datetime as dt

import numpy as np
import pytest

from heldout import rules
from heldout.rules import ChannelEpoch as E

T0, T1 = dt.datetime(2012, 6, 1, 12), dt.datetime(2012, 6, 1, 13)
OPEN = dict(start=dt.datetime(2010, 1, 1), end=None)


def three(loc="", rate=100.0, horiz=("HHN", "HHE"), **kw):
    kw = kw or OPEN
    return [E(loc, c, rate, **kw) for c in ("HHZ",) + horiz]


def test_three_hh_at_100_hz():
    c = rules.choose_channels(three(), T0, T1)
    assert c.ok and c.location == "" and c.channels == ("HHZ", "HHN", "HHE")


def test_hh1_hh2_are_accepted_as_north_and_east():
    c = rules.choose_channels(three(loc="10", horiz=("HH1", "HH2")), T0, T1)
    assert c.ok and c.location == "10" and c.channels == ("HHZ", "HH1", "HH2")


@pytest.mark.parametrize("rate", [80.0, 200.0, 50.0])
def test_other_rates_are_refused(rate):
    c = rules.choose_channels(three(rate=rate), T0, T1)
    assert not c.ok and "not 100 Hz" in c.reason


def test_one_channel_at_another_rate_refuses_the_station():
    ep = three()
    ep[2] = E("", "HHE", 200.0, **OPEN)
    assert not rules.choose_channels(ep, T0, T1).ok


def test_rate_change_inside_the_span_refuses():
    ep = three(start=dt.datetime(2010, 1, 1), end=dt.datetime(2012, 6, 1, 12, 30))
    ep += three(rate=200.0, start=dt.datetime(2012, 6, 1, 12, 30), end=None)
    assert not rules.choose_channels(ep, T0, T1).ok


def test_epochs_must_cover_the_span():
    ep = three(start=dt.datetime(2012, 6, 1, 12, 10), end=None)
    c = rules.choose_channels(ep, T0, T1)
    assert not c.ok and "do not cover" in c.reason
    # Two back-to-back epochs cover it.
    ep = three(start=dt.datetime(2010, 1, 1), end=dt.datetime(2012, 6, 1, 12, 30))
    ep += three(start=dt.datetime(2012, 6, 1, 12, 30), end=None)
    assert rules.choose_channels(ep, T0, T1).ok


def test_missing_component_or_band():
    assert not rules.choose_channels(three()[:2], T0, T1).ok
    bh = [E("", c, 100.0, **OPEN) for c in ("BHZ", "BHN", "BHE")]
    assert not rules.choose_channels(bh, T0, T1).ok
    assert "no HH" in rules.choose_channels([], T0, T1).reason


def test_mixed_locations_are_not_combined():
    ep = [E("00", "HHZ", 100.0, **OPEN), E("10", "HHN", 100.0, **OPEN),
          E("10", "HHE", 100.0, **OPEN)]
    assert not rules.choose_channels(ep, T0, T1).ok
    ep += [E("10", "HHZ", 100.0, **OPEN)]
    c = rules.choose_channels(ep, T0, T1)
    assert c.ok and c.location == "10"


def test_check_traces_keeps_only_the_chosen_100_hz_integers():
    from obspy import Stream, Trace

    def tr(cha, rate=100.0, loc="", dtype=np.int32):
        return Trace(np.zeros(10, dtype), header={"channel": cha, "sampling_rate": rate,
                                                 "location": loc})
    st = Stream([tr("HHZ"), tr("HHN", 50.0), tr("HHE", loc="10"), tr("HHE", dtype=np.float32),
                 tr("HNZ")])
    keep, drop = rules.check_traces(st, "", ("HHZ", "HHN", "HHE"))
    assert [t.stats.channel for t in keep] == ["HHZ"]
    assert len(drop) == 4


# ---- the test-period guard ---------------------------------------------------

def test_guard_allows_spans_before_2018():
    rules.check_test_period(dt.datetime(2012, 6, 1, 12), dt.datetime(2012, 6, 1, 12, 1), False)
    rules.check_test_period(dt.datetime(2017, 12, 31), dt.datetime(2018, 1, 1), False)


@pytest.mark.parametrize("start, end", [
    (dt.datetime(2018, 1, 1), dt.datetime(2018, 1, 2)),
    (dt.datetime(2025, 11, 10, 18, 4), dt.datetime(2025, 11, 10, 18, 35)),
    (dt.datetime(2017, 12, 31), dt.datetime(2018, 1, 1, 0, 0, 1)),  # reaches into it
])
def test_guard_refuses_the_test_period(start, end):
    with pytest.raises(rules.TestPeriodError, match="--allow-test-period"):
        rules.check_test_period(start, end, False)
    rules.check_test_period(start, end, True)


def test_azimuth_offsets():
    ep = [E("10", "HHZ", 100.0, azimuth=0.0, **OPEN), E("10", "HH1", 100.0, azimuth=358.0, **OPEN),
          E("10", "HH2", 100.0, azimuth=133.0, **OPEN)]
    assert rules.azimuth_offsets(ep, "10", ("HHZ", "HH1", "HH2"), T0, T1) == \
        {"HH1": 2.0, "HH2": 43.0}
