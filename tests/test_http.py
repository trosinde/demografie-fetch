from __future__ import annotations

import pytest
import requests

from demografie_fetch.errors import BlockedError, FetchError
from demografie_fetch.http import USER_AGENT, PoliteSession
from tests.conftest import FakeTransport


def _session(routes: dict[str, object], slept: list[float]) -> tuple[PoliteSession,
                                                                      FakeTransport]:
    t = FakeTransport(routes)
    return PoliteSession(min_interval=1.0, transport=t, sleep=slept.append), t


def test_backoff_bei_503() -> None:
    slept: list[float] = []
    s, t = _session({"u": [(503, b""), (503, b""), (200, b"ok")]}, slept)
    assert s.get("u").content == b"ok"
    backoffs = [x for x in slept if x >= 2]
    assert backoffs == [2.0, 4.0]


def test_dauerhafter_fehler() -> None:
    s, t = _session({"u": [(500, b"")]}, [])
    with pytest.raises(FetchError, match="Wiederholungen"):
        s.get("u")
    assert len(t.calls) == 4


def test_netzwerkfehler_wird_wiederholt() -> None:
    s, t = _session({"u": [requests.ConnectionError("x"), (200, b"ok")]}, [])
    assert s.get("u").content == b"ok"


@pytest.mark.parametrize("code", [401, 403])
def test_keine_wiederholung_bei_sperre(code: int) -> None:
    s, t = _session({"u": [(code, b"")]}, [])
    with pytest.raises(BlockedError):
        s.get("u")
    assert len(t.calls) == 1


def test_mindestabstand() -> None:
    slept: list[float] = []
    s, _ = _session({"u": b"ok"}, slept)
    s.get("u")
    s.get("u")
    assert slept and 0.9 < slept[0] <= 1.0


def test_kennung() -> None:
    assert USER_AGENT.startswith("demografie-fetch/")
