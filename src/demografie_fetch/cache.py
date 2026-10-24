"""Zustand je Quelle und Entscheidungen des Caches."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import store

DEFAULT_MAX_AGE_HOURS = 6.0


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str | None) -> datetime | None:
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def selection_key(auswahl: dict[str, Any], wide: list[str] | None, table: str) -> str:
    payload = json.dumps({"auswahl": auswahl, "wide": wide, "tabelle": table},
                         sort_keys=True, default=str)
    return sha256(payload.encode())[:16]


@dataclass
class State:
    quelle_id: str
    url: str
    tabelle: str
    stand: str | None = None
    sha256: str | None = None
    raw_dir: str | None = None  # relativ zu data/raw/<quelle_id>
    auswahl_key: str | None = None
    checked_at: str | None = None
    fetched_at: str | None = None
    built_at: str | None = None

    @classmethod
    def load(cls, path: Path) -> State | None:
        if not path.exists():
            return None
        d = store.read_json(path)
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})

    def save(self, path: Path) -> None:
        store.write_json(path, asdict(self))

    def checked_within(self, hours: float, now: datetime) -> bool:
        ts = parse_iso(self.checked_at)
        return hours > 0 and ts is not None and (now - ts).total_seconds() < hours * 3600


def new_raw_dirname(now: datetime, digest: str) -> str:
    return f"{now.strftime('%Y%m%dT%H%M%SZ')}_{digest[:8]}"
