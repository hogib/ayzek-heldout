"""fdsn_coverage asks for at most a year per request and adds the pieces up
without counting a span twice where the service returns it whole on both
sides of a piece's bound."""
import datetime as dt

from heldout import availability


LINE = "HL ATH -- {cha} M 100.0 {a}Z {b}Z\n"


def test_chunks_cover_the_span_exactly():
    t0, t1 = dt.datetime(2023, 1, 1), dt.datetime(2026, 10, 30, 12, 55, 36)
    cs = list(availability.chunks(t0, t1))
    assert cs[0][0] == t0 and cs[-1][1] == t1
    assert all(a < b and b - a <= availability.CHUNK for a, b in cs)
    assert all(cs[i][1] == cs[i + 1][0] for i in range(len(cs) - 1))
    assert len(cs) == 4


def test_fdsn_coverage_sums_pieces_without_overlap(monkeypatch):
    t0, t1 = dt.datetime(2023, 1, 1), dt.datetime(2025, 1, 1)
    full = "2022-06-01T00:00:00", "2025-06-01T00:00:00"   # one span across every piece
    urls = []

    def fake_get(url):
        urls.append(url)
        # the service returns the whole span, not clipped to the request
        return 200, "".join(LINE.format(cha=c, a=full[0], b=full[1])
                            for c in ("HHZ", "HHN")).encode()

    monkeypatch.setattr(availability, "_get", fake_get)
    cov = availability.fdsn_coverage("http://x", "HL", "ATH", "", ["HHZ", "HHN", "HHE"], t0, t1)
    assert len(urls) == 2
    assert "starttime=2023-01-01T00%3A00%3A00" in urls[0] and "endtime=2025-01-01" in urls[1]
    assert cov == {"HHZ": 1.0, "HHN": 1.0, "HHE": 0.0}


def test_fdsn_coverage_partial_piece(monkeypatch):
    t0, t1 = dt.datetime(2023, 1, 1), dt.datetime(2024, 12, 31)
    def fake_get(url):
        # data only in the first half of 2023
        return 200, LINE.format(cha="HHZ", a="2023-01-01T00:00:00", b="2023-07-02T00:00:00").encode()
    monkeypatch.setattr(availability, "_get", fake_get)
    cov = availability.fdsn_coverage("http://x", "HL", "ATH", "", ["HHZ"], t0, t1)
    # 182 days of 730, and the second piece returns the same span, which lies outside it
    assert abs(cov["HHZ"] - 182 / 730) < 1e-9
