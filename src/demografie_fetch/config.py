"""Quellen aus config/sources_demografie.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path("config/sources_demografie.yaml")


def package_file(name: str) -> Traversable:
    """Im Paket mitgelieferte Datei unter demografie_fetch/data/."""
    return files("demografie_fetch") / "data" / name


def resolve_config(path: Path | None = None) -> tuple[Path | Traversable, str]:
    """Konfiguration: Parameter, sonst ./config/, sonst Paket. Liefert (Datei, Herkunft)."""
    if path is not None:
        return path, str(path)
    if DEFAULT_CONFIG.exists():
        return DEFAULT_CONFIG, "projekt"
    return package_file("sources_demografie.yaml"), "paket"


@dataclass
class Source:
    id: str
    url: str
    rolle: str = "kontext"
    aktiv: bool = False
    adapter: str | None = None
    table: str | None = None
    auswahl: dict[str, Any] = field(default_factory=dict)
    wide: list[str] | None = None
    zugang: str | None = None
    max_alter_monate: int | None = None
    pruef_intervall_stunden: float | None = None


def load_sources(path: Path | None = None) -> list[Source]:
    source, _ = resolve_config(path)
    if not source.is_file():
        return []
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    out = []
    for s in data.get("sources") or []:
        wide = s.get("wide")
        out.append(
            Source(
                id=str(s["id"]),
                url=str(s.get("url") or ""),
                rolle=str(s.get("rolle") or "kontext"),
                aktiv=bool(s.get("aktiv", False)),
                adapter=s.get("adapter"),
                table=s.get("table"),
                auswahl=dict(s.get("auswahl") or {}),
                wide=wide.split(",") if isinstance(wide, str) else wide,
                zugang=s.get("zugang"),
                max_alter_monate=s.get("max_alter_monate"),
                pruef_intervall_stunden=s.get("pruef_intervall_stunden"),
            )
        )
    return out


def find_source(sources: list[Source], url: str | None = None,
                quelle_id: str | None = None) -> Source | None:
    for s in sources:
        if quelle_id and s.id == quelle_id:
            return s
        if url and s.url and s.url.strip() == url.strip():
            return s
    return None
