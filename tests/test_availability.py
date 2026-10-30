"""fdsn_coverage asks for at most a year per request and adds the pieces up
without counting a span twice where the service returns it whole on both
sides of a piece's bound."""
import datetime as dt
import urllib.parse

import pytest

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

    def fake_get(url, what=None):
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
    def fake_get(url, what=None):
        # data only in the first half of 2023
        return 200, LINE.format(cha="HHZ", a="2023-01-01T00:00:00", b="2023-07-02T00:00:00").encode()
    monkeypatch.setattr(availability, "_get", fake_get)
    cov = availability.fdsn_coverage("http://x", "HL", "ATH", "", ["HHZ"], t0, t1)
    # 182 days of 730, and the second piece returns the same span, which lies outside it
    assert abs(cov["HHZ"] - 182 / 730) < 1e-9


def test_a_piece_the_service_never_answers_is_halved(monkeypatch, capsys):
    t0, t1 = dt.datetime(2023, 1, 1), dt.datetime(2024, 1, 1)
    monkeypatch.setattr(availability.retry, "_sleep", lambda s: None)
    asked = []

    def fake_get(url, what=None):
        q = urllib.parse.parse_qs(url.split("?")[1])
        a, b = q["starttime"][0], q["endtime"][0]
        asked.append((a[:10], b[:10]))
        if (a[:10], b[:10]) == ("2023-01-01", "2024-01-01"):
            raise TimeoutError("The read operation timed out")   # the whole year, every time
        return 200, LINE.format(cha="HHZ", a=a, b=b).encode()   # the piece, fully covered

    monkeypatch.setattr(availability, "_get",
                        lambda url, what=None: availability.retry.call(fake_get, url, what, what=what))
    cov = availability.fdsn_coverage("http://x", "HL", "MET1", "", ["HHZ"], t0, t1)
    assert cov == {"HHZ": 1.0}
    assert asked.count(("2023-01-01", "2024-01-01")) == len(availability.retry.WAITS) + 1
    assert ("2023-01-01", "2023-07-02") in asked and ("2023-07-02", "2024-01-01") in asked
    err = capsys.readouterr().err
    assert "HL.MET1 availability 2023-01-01..2024-01-01: TimeoutError after every retry; halving" in err


def test_halving_stops_at_the_smallest_piece(monkeypatch):
    t0, t1 = dt.datetime(2023, 1, 1), dt.datetime(2023, 1, 15)
    monkeypatch.setattr(availability.retry, "_sleep", lambda s: None)

    def fake_get(url, what=None):
        raise TimeoutError("timed out")
    monkeypatch.setattr(availability, "_get",
                        lambda url, what=None: availability.retry.call(fake_get, url, what, what=what))
    with pytest.raises(TimeoutError):
        availability.fdsn_coverage("http://x", "HL", "MET1", "", ["HHZ"], t0, t1)


def test_an_answer_is_not_halved(monkeypatch):
    """A refusal (4xx) is raised at once, not split."""
    import urllib.error
    t0, t1 = dt.datetime(2023, 1, 1), dt.datetime(2024, 1, 1)

    def fake_get(url, what=None):
        raise urllib.error.HTTPError(url, 400, "bad", {}, None)
    monkeypatch.setattr(availability, "_get", fake_get)
    with pytest.raises(urllib.error.HTTPError):
        availability.fdsn_coverage("http://x", "HL", "MET1", "", ["HHZ"], t0, t1)
