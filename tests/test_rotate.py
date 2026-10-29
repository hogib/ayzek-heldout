"""Rotation of off-north horizontals to N/E before writing (fetch.rotate_to_ne)."""
import numpy as np
from obspy import Stream, Trace, UTCDateTime
from obspy.core.inventory import Channel, Inventory, Network, Station

from heldout import fetch


def inventory(az1):
    t0 = UTCDateTime("2020-01-01")
    chans = [Channel("HHZ", "", 0, 0, 0, 0, azimuth=0, dip=-90, sample_rate=100, start_date=t0),
             Channel("HH1", "", 0, 0, 0, 0, azimuth=az1, dip=0, sample_rate=100, start_date=t0),
             Channel("HH2", "", 0, 0, 0, 0, azimuth=az1 + 90, dip=0, sample_rate=100, start_date=t0)]
    return Inventory(networks=[Network("XX", stations=[Station("ROT", 0, 0, 0, channels=chans,
                                                                 start_date=t0)])], source="test")


def stream(n_amp, e_amp, az1, start="2022-06-01T00:00:00"):
    """Ground motion of N and E amplitudes, recorded on HH1 at az1 and HH2 at az1 + 90."""
    t = np.arange(1000)
    n, e = n_amp * np.sin(t / 7.0), e_amp * np.sin(t / 7.0)
    a = np.radians(az1)
    h1 = n * np.cos(a) + e * np.sin(a)
    h2 = -n * np.sin(a) + e * np.cos(a)
    z = 500 * np.cos(t / 5.0)
    tr = []
    for ch, x in (("HHZ", z), ("HH1", h1), ("HH2", h2)):
        tr.append(Trace(np.rint(x).astype(np.int32),
                        {"network": "XX", "station": "ROT", "channel": ch,
                         "sampling_rate": 100.0, "starttime": UTCDateTime(start)}))
    return Stream(tr), n, e, z


def test_needs_rotation():
    assert fetch.needs_rotation(["HHZ", "HH1", "HH2"], {"HH1": 0.0, "HH2": 0.0})
    assert fetch.needs_rotation(["HHZ", "HHN", "HHE"], {"HHN": 7.0, "HHE": 7.0})
    assert fetch.needs_rotation(["HHZ", "HHN", "HHE"], {"HHN": None, "HHE": 0.0})
    assert not fetch.needs_rotation(["HHZ", "HHN", "HHE"], {"HHN": 0.3, "HHE": 0.0})


def test_rotation_recovers_north_and_east():
    st, n, e, z = stream(3000, -1000, 30.0)
    out = fetch.rotate_to_ne(st, inventory(30.0))
    got = {tr.stats.channel: tr.data for tr in out}
    assert sorted(got) == ["HHE", "HHN", "HHZ"]
    assert all(tr.data.dtype.kind == "i" for tr in out)
    assert np.max(np.abs(got["HHN"] - n)) <= 2
    assert np.max(np.abs(got["HHE"] - e)) <= 2
    assert np.array_equal(got["HHZ"], np.rint(z).astype(np.int64))


def test_misaligned_ne_is_corrected():
    st, n, e, z = stream(2000, 1500, 8.0)
    for tr in st:
        tr.stats.channel = tr.stats.channel.replace("1", "N").replace("2", "E")
    inv = inventory(8.0)
    for ch in inv[0][0]:
        ch.code = ch.code.replace("1", "N").replace("2", "E")
    out = fetch.rotate_to_ne(st, inv)
    got = {tr.stats.channel: tr.data for tr in out}
    assert np.max(np.abs(got["HHN"] - n)) <= 2 and np.max(np.abs(got["HHE"] - e)) <= 2
