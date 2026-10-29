"""A service's passing failures are retried; its answers are not."""
import http.client
import urllib.error

import pytest
from obspy.clients.fdsn.header import (FDSNBadGatewayException, FDSNBadRequestException,
                                       FDSNException, FDSNNoDataException,
                                       FDSNServiceUnavailableException, FDSNTimeoutException)

from heldout import retry


@pytest.fixture
def waits(monkeypatch):
    slept = []
    monkeypatch.setattr(retry, "_sleep", slept.append)
    return slept


def failing(*errors):
    """A request that raises `errors` in turn, then succeeds."""
    errors = list(errors)

    def request(*a, **k):
        if errors:
            raise errors.pop(0)
        return a, k
    return request


def http_error(code):
    return urllib.error.HTTPError("https://service/query", code, "status", {}, None)


def test_passing_failures_are_retried_with_the_arguments(waits):
    request = failing(ConnectionResetError("reset by peer"),
                      FDSNBadGatewayException("502 Proxy Error"),
                      FDSNException("Unknown Error (RemoteDisconnected): Remote end closed"),
                      FDSNTimeoutException("Timed Out"),
                      FDSNServiceUnavailableException("503"),
                      http.client.IncompleteRead(b""))
    with pytest.raises(http.client.IncompleteRead):
        retry.call(request, "HL", what="x")
    assert waits == list(retry.WAITS)
    waits.clear()
    request = failing(http_error(503), http_error(429), TimeoutError())
    assert retry.call(request, "HL", "ATH", level="response", what="x") == (
        ("HL", "ATH"), {"level": "response"})
    assert waits == list(retry.WAITS[:3])


@pytest.mark.parametrize("answer", [FDSNNoDataException("no data"), FDSNBadRequestException("bad"),
                                    http_error(404), http_error(400), ValueError("parse")])
def test_answers_and_other_errors_are_raised_at_once(waits, answer):
    with pytest.raises(type(answer)):
        retry.call(failing(answer))
    assert waits == []


def test_a_client_without_a_needed_service_is_made_again(waits, monkeypatch):
    """obspy leaves out a service whose discovery failed; asking that client
    again cannot help, so the client itself is made again."""
    import types
    from heldout import fetch
    made = []

    class Client:
        def __init__(self, base_url, timeout):
            made.append(base_url)
            self.services = {"dataselect": {}, "event": {}} if len(made) == 1 else \
                {"dataselect": {}, "event": {}, "station": {}}

    monkeypatch.setattr("obspy.clients.fdsn.Client", Client)
    c = fetch.client(types.SimpleNamespace(base_url="https://service"), "station")
    assert "station" in c.services and len(made) == 2
    assert waits == [retry.WAITS[0]]
