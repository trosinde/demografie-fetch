"""Kommandozeile `demografie-fetch`."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from . import core
from .errors import FetchError

EPILOG = """Beispiele:
  demografie-fetch "<url>"                         Quelle erkennen, holen, Tabellen schreiben
  demografie-fetch "<url>" --list                  nur Struktur anzeigen
  demografie-fetch "<url>" --table 12411-0017 --startyear 2012
  demografie-fetch run                             alle aktiven Quellen
  demografie-fetch run --only kbv16_laender --force
  demografie-fetch check                           Erreichbarkeit der Schnittstelle

Exit-Codes: 0 ok/unveraendert, 1 Teilfehler, 2 Abbruch.
"""


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--data-dir", help="Basisverzeichnis fuer data/ und runs/ (Standard: .)")
    p.add_argument("--config", help="Quellenkonfiguration (Standard: "
                                    "config/sources_demografie.yaml)")
    p.add_argument("--max-age", type=float, help="Pruefintervall in Stunden (0 = immer pruefen)")
    p.add_argument("--force", action="store_true", help="ohne Aenderungspruefung neu laden")
    p.add_argument("-v", "--verbose", action="store_true")


def _parse_select(items: list[str] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"--select erwartet DIM=W1,W2, nicht {item!r}")
        k, v = item.split("=", 1)
        out[k.strip().upper()] = v
    return out


def _print_result(res: core.FetchResult) -> None:
    m = res.meta
    print(f"{m['quelle_id']}: {m['status']}  Tabelle {m['tabelle']}  Stand {m.get('stand')}  "
          f"{m['zeilen']} Zeilen")
    for k, v in res.paths.items():
        print(f"  {k}: {v}")
    voll = m.get("vollstaendigkeit")
    if voll and "zeitpunkte" in voll:
        print(f"  Kreise: Referenz {voll['referenz']}, {len(voll['zeitpunkte'])} Zeitpunkte, "
              f"{voll['abweichende_zeitpunkte']} mit Abweichung")
    if m.get("veraltet"):
        print(f"  Hinweis: veraltet ({m['veraltet']['alter_monate']} Monate)")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("run", "check"):
        cmd, rest = argv[0], argv[1:]
        p = argparse.ArgumentParser(prog=f"demografie-fetch {cmd}")
        _common(p)
        if cmd == "run":
            p.add_argument("--only", help="Quell-IDs, kommagetrennt")
        a = p.parse_args(rest)
        _logging(a.verbose)
        if cmd == "check":
            status = core.check()
            for db, st in status.items():
                print(f"{db}: {st}")
            return 0 if all(v == "ok" for v in status.values()) else 2
        try:
            code, path, entries = core.run(
                only=a.only.split(",") if a.only else None, force=a.force,
                max_age=a.max_age, data_dir=a.data_dir, config=a.config)
        except FetchError as e:
            print(f"Fehler: {e}", file=sys.stderr)
            return e.exit_code
        for entry in entries:
            print(f"{entry['quelle_id']}: {entry['status']}"
                  + (f"  {entry.get('fehler')}" if entry["status"] == "fehler" else ""))
        print(f"Manifest: {path}")
        return code

    p = argparse.ArgumentParser(prog="demografie-fetch", epilog=EPILOG,
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                description="Demografiedaten: URL rein, Tabelle je Kreis raus.")
    p.add_argument("url", help="URL der Datenquelle")
    p.add_argument("--list", action="store_true", help="nur Struktur anzeigen")
    p.add_argument("--table", help="Tabellencode, z. B. 12411-0017")
    p.add_argument("--startyear")
    p.add_argument("--endyear")
    p.add_argument("--select", action="append", metavar="DIM=W1,W2",
                   help="Auswahl je Dimension (mehrfach)")
    p.add_argument("--role", choices=("rahmen", "kontext", "validierung"))
    p.add_argument("--wide", help="Dimensionen, die als Zeilen bleiben (Standard: zeit)")
    _common(p)
    a = p.parse_args(argv)
    _logging(a.verbose)
    try:
        if a.list:
            print(core.list_source(a.url, a.table))
            return 0
        res = core.fetch(a.url, table=a.table, startyear=a.startyear, endyear=a.endyear,
                         select=_parse_select(a.select), role=a.role, wide=a.wide,
                         max_age=a.max_age, force=a.force, data_dir=a.data_dir,
                         config=a.config)
    except FetchError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return e.exit_code
    _print_result(res)
    from . import store

    path = core.write_manifest(store.Store(a.data_dir),
                               [core.manifest_entry(res, res.meta["quelle_id"], a.url)])
    print(f"Manifest: {path}")
    return 0


def _logging(verbose: bool) -> None:
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING,
                        format="%(levelname)s %(message)s")


if __name__ == "__main__":
    sys.exit(main())
