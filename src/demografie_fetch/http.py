"""Hoefliche HTTP-Session: sequentiell, Mindestabstand, Backoff."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import requests

from . import __version__
from .errors import BlockedError, FetchError

USER_AGENT = f"demografie-fetch/{__version__} (+https://github.com/trosinde/demografie-fetch)"
RETRY_STATUS = {429, 500, 502, 503, 504}


class Response(Protocol):
    @property
    def status_code(self) -> int: ...
    @property
    def content(self) -> bytes: ...
    @property
    def headers(self) -> Any: ...


Transport = Callable[[str, float], Response]


def _requests_transport() -> Transport:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})

    def get(url: str, timeout: float) -> Response:
        return session.get(url, timeout=timeout)

    return get


@dataclass
class PoliteSession:
    min_interval: float = 1.0
    backoff: tuple[float, ...] = (2.0, 4.0, 8.0)
    transport: Transport | None = None
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    requests_made: list[str] = field(default_factory=list)
    _last: float | None = None

    def _wait(self) -> None:
        if self._last is not None:
            delta = self.clock() - self._last
            if delta < self.min_interval:
                self.sleep(self.min_interval - delta)

    def get(self, url: str, timeout: float = 60.0) -> Response:
        if self.transport is None:
            self.transport = _requests_transport()
        last_error = ""
        for attempt in range(len(self.backoff) + 1):
            if attempt:
                self.sleep(self.backoff[attempt - 1])
            self._wait()
            try:
                self.requests_made.append(url)
                resp = self.transport(url, timeout)
            except requests.RequestException as e:
                last_error = f"Netzwerkfehler: {type(e).__name__}"
                continue
            finally:
                self._last = self.clock()
            if resp.status_code in (401, 403):
                raise BlockedError(
                    f"Zugriff verweigert (HTTP {resp.status_code}) fuer {url}; "
                    "wird nicht umgangen."
                )
            if resp.status_code in RETRY_STATUS:
                last_error = f"HTTP {resp.status_code}"
                continue
            if resp.status_code >= 400:
                raise FetchError(f"HTTP {resp.status_code} fuer {url}")
            return resp
        raise FetchError(f"Abruf fehlgeschlagen nach {len(self.backoff)} Wiederholungen "
                         f"({last_error}): {url}")
