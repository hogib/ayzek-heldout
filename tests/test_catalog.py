import datetime as dt

from heldout import catalog
from heldout.catalog import Event


def ev(**kw):
    d = dict(time=dt.datetime(2025, 11, 9, 18, 13, 37), lat=39.18917, lon=28.23972,
             depth_km=10.15, magnitude=1.1, mag_type="ML", rms=0.26,
             location="Sındırgı (Balıkesir)", event_id="691876")
    d.update(kw)
    return Event(**d)


def test_matches_ayzek_demo_ko_line(tmp_path):
    # The first line of ayzek_code/tests/catalogs/demo_ko.csv, as AFAD writes it.
    p = tmp_path / "catalog.csv"
    n, skipped = catalog.write(p, [ev()])
    assert (n, skipped) == (1, [])
    assert p.read_text(encoding="utf-8").splitlines() == [
        "Date,Longitude,Latitude,Depth,Rms,Type,Magnitude,Location,EventID",
        "09/11/2025 18:13:37,28.23972,39.18917,10.15,0.26,ML,1.1,Sındırgı (Balıkesir),691876"]


def test_read_back_like_ayzek(tmp_path):
    p = tmp_path / "catalog.csv"
    catalog.write(p, [ev(time=dt.datetime(2012, 6, 1, 3, 4, 5, 600000), lat=-41.5,
                         lon=174.25, depth_km=212.4, magnitude=4.3, mag_type="MLv",
                         rms=None, location="20 km north of Wellington, NZ",
                         event_id="smi:nz.org.geonet/2012p123")])
    (t, lat, lon, depth, mag, typ), = catalog.read_back(p)
    assert t == dt.datetime(2012, 6, 1, 3, 4, 6, tzinfo=dt.UTC).timestamp()  # rounded
    assert (lat, lon, depth, mag, typ) == (-41.5, 174.25, 212.4, 4.3, "MLv")
    line = p.read_text().splitlines()[1]
    assert line.count(",") == 8                       # commas in Location replaced
    assert ",," in line                               # missing Rms stays empty


def test_sorted_and_incomplete_events_left_out(tmp_path):
    p = tmp_path / "catalog.csv"
    late = ev(time=dt.datetime(2025, 11, 9, 19, 0), event_id="b")
    early = ev(time=dt.datetime(2025, 11, 9, 18, 0), event_id="a")
    n, skipped = catalog.write(p, [late, early, ev(depth_km=None), ev(magnitude=None),
                                   ev(event_type="not existing")])
    assert n == 2 and len(skipped) == 3
    ids = [r.split(",")[-1] for r in p.read_text().splitlines()[1:]]
    assert ids == ["a", "b"]


def test_date_rounding_carries_into_the_next_minute():
    assert catalog.format_date(dt.datetime(2012, 12, 31, 23, 59, 59, 700000)) == \
        "01/01/2013 00:00:00"


def test_empty_catalogue_is_a_header(tmp_path):
    p = tmp_path / "catalog.csv"
    assert catalog.write(p, [])[0] == 0
    assert p.read_text() == ",".join(catalog.HEADER) + "\n"


def test_from_quakeml_keeps_the_magnitude_type():
    from obspy.core.event import Catalog, Event as QEvent, Magnitude, Origin, OriginQuality
    from obspy import UTCDateTime
    o = Origin(time=UTCDateTime(2012, 6, 1, 1, 2, 3), latitude=-38.5, longitude=176.1,
               depth=150000.0, quality=OriginQuality(standard_error=0.4))
    m = Magnitude(mag=3.2, magnitude_type="MLv")
    e = QEvent(origins=[o], magnitudes=[m], event_type="earthquake")
    e.preferred_origin_id, e.preferred_magnitude_id = o.resource_id, m.resource_id
    (x,) = catalog.from_quakeml(Catalog([e]))
    assert (x.depth_km, x.magnitude, x.mag_type, x.rms) == (150.0, 3.2, "MLv", 0.4)


def test_from_afad_record():
    (x,) = catalog.from_afad([{"date": "2025-11-09T18:13:37", "latitude": "39.18917",
                               "longitude": "28.23972", "depth": "10.15", "rms": "0.26",
                               "type": "ML", "magnitude": "1.1", "location":
                               "Sındırgı (Balıkesir)", "eventID": "691876"}])
    assert x == ev()
