"""README: die festen Spalten des Langformats stehen in derselben Reihenfolge wie in fetch()."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from demografie_fetch import fetch
from demografie_fetch.http import PoliteSession
from tests.conftest import URL_0017, FakeTransport, routes_0017

ROOT = Path(__file__).resolve().parents[1]
KOPF = "| Spalte | Typ | Beispiel | Erklärung |"


def _langformat_spalten_readme() -> list[str]:
    """Erste Spalte der Langformat-Tabelle im Abschnitt „Was kommt heraus?“."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    abschnitt = text.split("## Was kommt heraus?", 1)[1].split("\n## ", 1)[0]
    zeilen = abschnitt.splitlines()
    start = zeilen.index(KOPF) + 2  # Kopf und Trennzeile überspringen
    spalten = []
    for zeile in zeilen[start:]:
        if not zeile.startswith("| `"):
            break
        spalten.append(zeile.split("|")[1].strip().strip("`"))
    return spalten


def test_langformat_spalten_stimmen_mit_fetch_ueberein(
    tmp_path: Path,
    make_http: Callable[[dict[str, Any]], tuple[PoliteSession, FakeTransport]],
) -> None:
    http, _ = make_http(routes_0017())
    r = fetch(URL_0017, data_dir=tmp_path, http=http)
    assert _langformat_spalten_readme() == list(r.long_df.columns)
