"""URL -> Adapter, Datenbank, Tabelle."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from .errors import UnsupportedSourceError

TABLE_RE = re.compile(r"(?<!\d)(\d{5}-\d{2,4}(?:-\d{1,2}){0,2}(?:-[0-9A-Z])?)(?![\d])")
STAT_RE = re.compile(r"(?<![\d-])(\d{5})(?![\d-])")


@dataclass(frozen=True)
class SourceRef:
    url: str
    adapter: str
    db: str
    table: str | None
    statistic: str | None


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def extract_codes(url: str) -> tuple[str | None, str | None]:
    """(tabellencode, statistikcode) aus einer URL."""
    text = unquote(url)
    m = TABLE_RE.search(text)
    if m:
        return m.group(1), m.group(1)[:5]
    m = STAT_RE.search(urlsplit(text).path + "?" + urlsplit(text).query)
    return (None, m.group(1)) if m else (None, None)


def detect(url: str) -> SourceRef:
    """Erkennt die Quelle; wirft UnsupportedSourceError fuer alles ausser Destatis."""
    url = url.strip()
    host = _host(url)
    path = urlsplit(url).path.lower()
    if host in ("genesis.destatis.de", "www-genesis.destatis.de"):
        table, stat = extract_codes(url)
        if not table and not stat:
            raise UnsupportedSourceError(
                f"Destatis-URL ohne Tabellen- oder Statistikcode: {url}"
            )
        return SourceRef(url, "genesis", "destatis", table, stat)
    if host.endswith("regionalstatistik.de"):
        raise UnsupportedSourceError(
            "Regionaldatenbank erkannt. Ohne Token ist sie nicht abrufbar (Gastzugang "
            "gesperrt, robots.txt Disallow). Die Datei bitte im Browser laden und mit "
            "`demografie-fetch import <quelle_id> <datei>` einspielen (folgt mit "
            "add-file-and-import). Viele Kreistabellen gibt es auch bei Destatis, "
            "z. B. 12411-0017."
        )
    if host.startswith("tableau."):
        raise UnsupportedSourceError(
            "Tableau-Quelle erkannt; der Tableau-Adapter ist noch nicht umgesetzt "
            "(add-tableau-adapter)."
        )
    if host == "bbsr.bund.de" or host.endswith(".bbsr.bund.de"):
        raise UnsupportedSourceError(
            "BBSR-Einbettungsseite erkannt; sie wird nicht automatisiert bedient "
            "(Zustimmungsdialog). Bitte die Tableau-URL eintragen: im Dashboard "
            "'Teilen' bzw. den Link 'auf Tableau oeffnen' nutzen, sie beginnt mit "
            "https://tableau.bbsr.bund.de/views/..."
        )
    if path.endswith((".csv", ".xlsx", ".xls", ".zip")):
        raise UnsupportedSourceError(
            "Datei-Link erkannt; der Datei-Adapter ist noch nicht umgesetzt "
            "(add-file-and-import)."
        )
    raise UnsupportedSourceError(f"Quelle nicht erkannt: {url}")
