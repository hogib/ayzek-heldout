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
