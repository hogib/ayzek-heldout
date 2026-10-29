"""Retries for the data services' passing failures.

A request that fails with a server error, a timeout or a dropped connection is
made again after each of WAITS; one the service answers (no data, a malformed
or unauthorised request) is not. A failure that outlasts every wait is raised,
so that a set is complete or reported as failed, never short by what an outage
of a few minutes withheld.
"""
import http.client
import sys
import time
import urllib.error

WAITS = (5, 15, 45, 120, 300)  # s, 8 min 5 s in all
_sleep = time.sleep


def transient(e):
    """Whether a request that raised `e` may succeed if made again."""
    from obspy.clients.fdsn import header as h
    answers = (h.FDSNNoDataException, h.FDSNBadRequestException, h.FDSNUnauthorizedException,
               h.FDSNForbiddenException, h.FDSNRequestTooLargeException,
               h.FDSNNotImplementedException, h.FDSNInvalidRequestException,
               h.FDSNDoubleAuthenticationException, h.FDSNNoAuthenticationServiceException,
               h.FDSNRedirectException)
    if isinstance(e, answers):
        return False
    if isinstance(e, h.FDSNException):
        # 500, 502, 503, 429, timeouts, and obspy's "Unknown Error" for a
        # connection that failed before any HTTP response.
        return True
    if isinstance(e, urllib.error.HTTPError):
        return e.code >= 500 or e.code in (408, 429)
    return isinstance(e, (OSError, http.client.HTTPException))


def call(fn, *args, what="", final=(), **kwargs):
    """fn(*args, **kwargs), made again after each of WAITS while it fails transiently.
    An exception of a type in `final` is raised at once, for a caller that
    answers it otherwise (a catalogue request cut off by its size is halved)."""
    for i in range(len(WAITS) + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001  classified by transient()
            if i == len(WAITS) or isinstance(e, final) or not transient(e):
                raise
            print(f"  {what or getattr(fn, '__name__', 'request')}: {type(e).__name__}"
                  f" ({str(e).splitlines()[0][:80] if str(e) else ''}); again in {WAITS[i]} s",
                  file=sys.stderr)
            _sleep(WAITS[i])
