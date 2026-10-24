"""Gemeinsame Hilfen: Transport-Attrappe und Fixtures ohne Netzwerk."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from demografie_fetch.http import PoliteSession

FIX = Path(__file__).parent / "fixtures"
BASE = "https://genesis.destatis.de/genesis/api/rest/"
URL_0017 = "https://genesis.destatis.de/datenbank/online/statistic/12411/table/12411-0017"


@dataclass
class FakeResponse:
    status_code: int
    content: bytes
    headers: dict[str, str] = field(default_factory=dict)


class FakeTransport:
    """Antworten je URL; eine Liste wird der Reihe nach abgearbeitet."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def __call__(self, url: str, timeout: float) -> FakeResponse:
        self.calls.append(url)
        r = self.routes.get(url)
        if r is None:
            return FakeResponse(404, b"{}")
        if isinstance(r, list):
            r = r.pop(0) if len(r) > 1 else r[0]
        if isinstance(r, Exception):
            raise r
        if isinstance(r, tuple):
            return FakeResponse(r[0], r[1])
        return FakeResponse(200, r)

    def count(self, part: str) -> int:
        return sum(part in c for c in self.calls)


def fixture_bytes(name: str) -> bytes:
    return (FIX / name).read_bytes()


def structure_with_stand(stand: str) -> bytes:
    s = json.loads(fixture_bytes("genesis_12411-0017_structure.json"))
    s["table"]["lastChange"] = stand
    return json.dumps(s).encode()


def routes_0017(stand: str = "2026-09-21T09:08:47.596Z",
                data: bytes | None = None) -> dict[str, Any]:
    t = BASE + "tables/12411-0017/"
    return {
        t + "structure": structure_with_stand(stand),
        t + "data": data or fixture_bytes("genesis_12411-0017_data.json"),
        t + "qualitySigns": fixture_bytes("genesis_12411-0017_qualitySigns.json"),
        BASE + "statistics/12411/tables": fixture_bytes("genesis_statistics_12411_tables.json"),
        BASE + "settings/instance": b'{"operator": {}}',
    }


@pytest.fixture
def make_http() -> Callable[[dict[str, Any]], tuple[PoliteSession, FakeTransport]]:
    def make(routes: dict[str, Any]) -> tuple[PoliteSession, FakeTransport]:
        t = FakeTransport(routes)
        return PoliteSession(min_interval=0, backoff=(0, 0, 0), transport=t,
                             sleep=lambda s: None), t

    return make


@pytest.fixture
def empty_config(tmp_path: Path) -> Path:
    p = tmp_path / "sources.yaml"
    p.write_text("sources: []\n", encoding="utf-8")
    return p
