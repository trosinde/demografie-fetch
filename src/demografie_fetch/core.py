"""fetch() und run(): Quelle erkennen, Cache pruefen, laden, Tabellen schreiben."""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

import pandas as pd

from . import cache, output, store
from .adapters.genesis import LIZENZ, GenesisClient, TableInfo, apply_selection, cube_to_long
from .config import Source, find_source, load_sources, resolve_config
from .detect import SourceRef, detect
from .errors import FetchError, InputError
from .http import PoliteSession

log = logging.getLogger("demografie_fetch")


@dataclass
class FetchResult:
    long_df: pd.DataFrame
    wide_df: pd.DataFrame | None
    meta: dict[str, Any]
    paths: dict[str, str] = field(default_factory=dict)

    def summary(self) -> dict[str, str]:
        """Kurze Zusammenfassung ohne Datenzeilen (fuer Notebook und repr)."""
        m = self.meta
        voll = m.get("vollstaendigkeit") or {}
        if "zeitpunkte" in voll:
            voll_text = (f"{voll['referenz']} Kreise, {len(voll['zeitpunkte'])} Zeitpunkte, "
                         f"{voll['abweichende_zeitpunkte']} mit Abweichung")
        else:
            voll_text = str(voll.get("fehler", "keine Kreisebene"))
        wide = "-" if self.wide_df is None else f"{len(self.wide_df)} x {self.wide_df.shape[1]}"
        out = {
            "Quelle": str(m.get("quelle_id")),
            "Status": str(m.get("status")),
            "Tabelle": f"{m.get('tabelle')} {m.get('titel') or ''}".strip(),
            "Stand": str(m.get("stand")),
            "Langformat": f"{len(self.long_df)} Zeilen x {self.long_df.shape[1]} Spalten",
            "Breitformat": wide,
            "Vollständigkeit": voll_text,
        }
        if m.get("veraltet"):
            out["Hinweis"] = f"veraltet ({m['veraltet']['alter_monate']} Monate)"
        out.update({f"Pfad {k}": v for k, v in self.paths.items()})
        return out

    def __repr__(self) -> str:
        rows = self.summary()
        width = max(len(k) for k in rows)
        return "FetchResult\n" + "\n".join(f"  {k:<{width}}  {v}" for k, v in rows.items())

    def _repr_html_(self) -> str:
        rows = "".join(
            f"<tr><th style='text-align:left'>{html.escape(k)}</th>"
            f"<td style='text-align:left'>{html.escape(v)}</td></tr>"
            for k, v in self.summary().items()
        )
        return f"<table><caption>FetchResult</caption>{rows}</table>"


class RunResult(NamedTuple):
    """Ergebnis von run(); laesst sich wie (exit_code, manifest_path, entries) entpacken."""

    exit_code: int
    manifest_path: Path
    entries: list[dict[str, Any]]

    def to_frame(self) -> pd.DataFrame:
        cols = ["quelle_id", "status", "tabelle", "stand", "zeilen", "fehler"]
        return pd.DataFrame([{c: e.get(c) for c in cols} for e in self.entries], columns=cols)


@dataclass
class Options:
    table: str | None = None
    auswahl: dict[str, Any] = field(default_factory=dict)
    rolle: str = "kontext"
    wide: list[str] | None = None
    max_age: float = cache.DEFAULT_MAX_AGE_HOURS
    force: bool = False
    max_alter_monate: int | None = None


def _resolve_table(ref: SourceRef, table: str | None, client: GenesisClient) -> str:
    if table:
        if ref.statistic and table[:5] != ref.statistic:
            raise InputError(
                f"Tabelle {table} gehoert nicht zur Statistik {ref.statistic} der URL"
            )
        return table
    if ref.table:
        return ref.table
    assert ref.statistic
    tabs = client.statistic_tables(ref.statistic)
    lines = [f"  {t['code']}  {'[Kreise] ' if t['kreise'] else ''}{t['titel']}" for t in tabs]
    raise InputError(
        f"Die URL zeigt auf die Statistik {ref.statistic} mit {len(tabs)} Tabellen. "
        "Bitte mit --table waehlen:\n" + "\n".join(lines)
    )


def list_source(url: str, table: str | None = None,
                http: PoliteSession | None = None) -> str:
    """Struktur anzeigen, ohne Daten zu laden oder zu schreiben."""
    ref = detect(url)
    client = GenesisClient(http or PoliteSession())
    if not (table or ref.table):
        assert ref.statistic
        tabs = client.statistic_tables(ref.statistic)
        return "\n".join(
            [f"Statistik {ref.statistic}: {len(tabs)} Tabellen"]
            + [f"  {t['code']}  {'[Kreise] ' if t['kreise'] else ''}{t['titel']}" for t in tabs]
        )
    code = _resolve_table(ref, table, client)
    _, info = client.structure(code)
    out = [f"Tabelle {info.code}: {info.title}", f"Stand: {info.stand}",
           f"Copyright: {info.copyright}", "Dimensionen:"]
    for name, var in info.variables.items():
        vals = list(var.get("variableValues") or [])
        sample = ", ".join(
            f"{v} ({info.value_labels[v]})" if v in info.value_labels else v for v in vals[:4]
        )
        typ = var.get("variableType", "")
        span = f" [{vals[0]} .. {vals[-1]}]" if str(typ).startswith("TIME") and vals else ""
        out.append(f"  {name} ({len(vals)} Werte, {typ}){span}: {sample}"
                   f"{' ...' if len(vals) > 4 else ''}")
    out.append("Merkmale:")
    for code_m, c in info.contents.items():
        fns = c.get("functions") or {}
        unit = next((f.get("label", {}).get("de") for f in fns.values()
                     if isinstance(f, dict)), "")
        out.append(f"  {code_m}: {(c.get('label') or {}).get('de', '')} [{unit}]")
    return "\n".join(out)


def _months_between(earlier: datetime, later: datetime) -> int:
    return (later.year - earlier.year) * 12 + later.month - earlier.month


def _build(st: store.Store, quelle_id: str, raw_path: Path, opts: Options,
           info: TableInfo | None, url: str, digest: str) -> tuple[pd.DataFrame,
                                                                    pd.DataFrame | None,
                                                                    dict[str, str]]:
    if info is None:
        info = TableInfo.from_structure(store.read_json(raw_path / "structure.json"))
    signs_path = raw_path / "qualitySigns.json"
    long_full = cube_to_long((raw_path / "data.json").read_bytes(), info,
                             signs_path.read_bytes() if signs_path.exists() else None,
                             quelle_id)
    long_df = apply_selection(long_full, opts.auswahl)
    wide_df = output.to_wide(long_df, opts.wide)
    pq_path = st.parquet_path(quelle_id, opts.rolle)
    store.write_parquet(pq_path, long_df, {
        "quelle": url, "quelle_id": quelle_id, "tabelle": info.code, "titel": info.title,
        "stand": info.stand or "", "lizenz": LIZENZ, "copyright": info.copyright,
        "sha256": digest, "rohfassung": raw_path.name,
    })
    paths = {"parquet": str(pq_path), "raw": str(raw_path)}
    if wide_df is not None and "ags5" in long_df.columns:
        csv_path = st.wide_path(quelle_id, opts.rolle)
        store.write_csv(csv_path, wide_df)
        paths["wide_csv"] = str(csv_path)
    return long_df, wide_df, paths


def _load_cached(st: store.Store, quelle_id: str, opts: Options,
                 state: cache.State) -> tuple[pd.DataFrame, pd.DataFrame | None,
                                              dict[str, str]]:
    pq_path = st.parquet_path(quelle_id, opts.rolle)
    long_df = store.read_parquet(pq_path)
    wide_df = output.to_wide(long_df, opts.wide)
    paths = {"parquet": str(pq_path), "raw": str(st.raw_dir(quelle_id) / (state.raw_dir or ""))}
    csv_path = st.wide_path(quelle_id, opts.rolle)
    if csv_path.exists():
        paths["wide_csv"] = str(csv_path)
    return long_df, wide_df, paths


def fetch(url: str, *, table: str | None = None, startyear: str | int | None = None,
          endyear: str | int | None = None, select: dict[str, Any] | None = None,
          role: str | None = None, wide: list[str] | str | None = None,
          max_age: float | None = None, force: bool = False,
          data_dir: str | Path | None = None, config: str | Path | None = None,
          quelle_id: str | None = None, http: PoliteSession | None = None,
          now: datetime | None = None) -> FetchResult:
    """Ruft eine Quelle ab; liefert Lang- und Breitformat, Metadaten und Pfade."""
    now = now or cache.utcnow()
    sources = load_sources(Path(config) if config else None)
    src = find_source(sources, url=url, quelle_id=quelle_id)
    ref = detect(url)
    client = GenesisClient(http or PoliteSession())

    opts = _options(src, table, startyear, endyear, select, role, wide, max_age, force)
    code = _resolve_table(ref, opts.table, client)
    qid = quelle_id or (src.id if src else f"{ref.db}_{code.replace('-', '_')}")
    st = store.Store(data_dir)
    state_path = st.state_path(qid)
    state = cache.State.load(state_path)
    key = cache.selection_key(opts.auswahl, opts.wide, code)
    pq_path = st.parquet_path(qid, opts.rolle)
    if state and state.tabelle != code:
        state = None  # andere Tabelle unter gleicher ID: neu beginnen

    meta: dict[str, Any] = {"quelle_id": qid, "url": url, "tabelle": code,
                            "rolle": opts.rolle}

    def finish(status: str, long_df: pd.DataFrame, wide_df: pd.DataFrame | None,
               paths: dict[str, str], s: cache.State) -> FetchResult:
        meta.update(status=status, stand=s.stand, sha256=s.sha256, zeilen=len(long_df),
                    titel=_title(pq_path))
        meta["vollstaendigkeit"] = output.completeness(long_df)
        stand_dt = cache.parse_iso(s.stand)
        if opts.max_alter_monate and stand_dt:
            alter = _months_between(stand_dt, now)
            if alter > opts.max_alter_monate:
                meta["veraltet"] = {"alter_monate": alter, "max": opts.max_alter_monate}
        log.info("%s: %s (%s Zeilen)", qid, status, len(long_df))
        return FetchResult(long_df, wide_df, meta, paths)

    # Stufe 1: Pruefintervall -> ohne Anfrage aus dem Cache
    if (not opts.force and state and state.auswahl_key == key and pq_path.exists()
            and state.checked_within(opts.max_age, now)):
        return finish("cache", *_load_cached(st, qid, opts, state), state)

    # Stufe 2: Stand (lastChange) vergleichen
    raw_structure, info = client.structure(code)
    last_raw = st.raw_dir(qid) / state.raw_dir if state and state.raw_dir else None
    if (not opts.force and state and last_raw and last_raw.exists()
            and info.stand and state.stand == info.stand):
        state.checked_at = cache.iso(now)
        if state.auswahl_key == key and pq_path.exists():
            state.save(state_path)
            return finish("unveraendert", *_load_cached(st, qid, opts, state), state)
        long_df, wide_df, paths = _build(st, qid, last_raw, opts, None, url,
                                         state.sha256 or "")
        state.auswahl_key, state.built_at = key, cache.iso(now)
        state.save(state_path)
        return finish("unveraendert", long_df, wide_df, paths, state)

    # Stufe 3: Daten laden, Pruefsumme vergleichen
    raw_data = client.data(code)
    raw_signs = client.quality_signs(code)
    digest = cache.sha256(raw_data)
    state = state or cache.State(quelle_id=qid, url=url, tabelle=code)
    same = bool(state.sha256 == digest and last_raw and last_raw.exists())
    if same:
        assert last_raw is not None
        raw_path, status = last_raw, "unveraendert"
    else:
        cube_to_long(raw_data, info, raw_signs, qid)  # Format pruefen, bevor abgelegt wird
        raw_path = st.raw_dir(qid) / cache.new_raw_dirname(now, digest)
        raw_path.mkdir(parents=True, exist_ok=False)
        store.write_bytes(raw_path / "data.json", raw_data)
        store.write_bytes(raw_path / "structure.json", raw_structure)
        store.write_bytes(raw_path / "qualitySigns.json", raw_signs)
        store.write_json(raw_path / "meta.json", {
            "quelle_id": qid, "url": url, "tabelle": code, "stand": info.stand,
            "sha256": digest, "abgerufen": cache.iso(now), "lizenz": LIZENZ,
            "copyright": info.copyright,
            "endpunkte": [f"{client.base}tables/{code}/{p}"
                          for p in ("data", "structure", "qualitySigns")],
        })
        status = "neu"
    state.stand, state.sha256, state.raw_dir = info.stand, digest, raw_path.name
    state.checked_at = state.fetched_at = cache.iso(now)
    if same and not opts.force and state.auswahl_key == key and pq_path.exists():
        state.save(state_path)
        return finish(status, *_load_cached(st, qid, opts, state), state)
    long_df, wide_df, paths = _build(st, qid, raw_path, opts, info, url, digest)
    state.auswahl_key, state.built_at = key, cache.iso(now)
    state.save(state_path)
    return finish(status, long_df, wide_df, paths, state)


def _title(pq_path: Path) -> str | None:
    try:
        return store.parquet_meta(pq_path).get("titel")
    except Exception:
        return None


def _options(src: Source | None, table: str | None, startyear: Any, endyear: Any,
             select: dict[str, Any] | None, role: str | None, wide: list[str] | str | None,
             max_age: float | None, force: bool) -> Options:
    auswahl: dict[str, Any] = dict(src.auswahl) if src else {}
    if startyear is not None:
        auswahl["startyear"] = str(startyear)
    if endyear is not None:
        auswahl["endyear"] = str(endyear)
    auswahl.update(select or {})
    wide_list = wide.split(",") if isinstance(wide, str) else wide
    if max_age is None:
        max_age = (src.pruef_intervall_stunden if src and src.pruef_intervall_stunden
                   is not None else cache.DEFAULT_MAX_AGE_HOURS)
    return Options(
        table=table or (src.table if src else None),
        auswahl=auswahl,
        rolle=role or (src.rolle if src else "kontext"),
        wide=wide_list or (src.wide if src else None) or ["zeit"],
        max_age=float(max_age),
        force=force,
        max_alter_monate=src.max_alter_monate if src else None,
    )


# ------------------------------------------------------------------ Lauf und Manifest


def manifest_entry(result: FetchResult | None, src_id: str, url: str,
                   error: Exception | None = None) -> dict[str, Any]:
    if result is not None:
        m = dict(result.meta)
        m["pfade"] = result.paths
        return m
    return {"quelle_id": src_id, "url": url, "status": "fehler",
            "fehler": str(error), "fehlerart": type(error).__name__}


def exit_code(entries: list[dict[str, Any]]) -> int:
    failed = [e for e in entries if e.get("status") == "fehler"]
    if not failed:
        return 0
    return 2 if len(failed) == len(entries) else 1


def write_manifest(st: store.Store, entries: list[dict[str, Any]],
                   now: datetime | None = None, konfiguration: str | None = None) -> Path:
    now = now or cache.utcnow()
    path = st.runs_dir(now.strftime("%Y%m%dT%H%M%SZ")) / "manifest_demografie.json"
    body: dict[str, Any] = {"zeit_utc": cache.iso(now), "exit_code": exit_code(entries)}
    if konfiguration:
        body["konfiguration"] = konfiguration
    body["quellen"] = entries
    store.write_json(path, body)
    return path


def run(only: list[str] | None = None, force: bool = False, max_age: float | None = None,
        data_dir: str | Path | None = None, config: str | Path | None = None,
        http: PoliteSession | None = None,
        now: datetime | None = None) -> RunResult:
    """Alle aktiven (bzw. per `only` gewaehlten) Quellen; Fehler je Quelle isoliert."""
    sources = load_sources(Path(config) if config else None)
    chosen = [s for s in sources if (s.id in only if only else s.aktiv)]
    if only:
        unknown = set(only) - {s.id for s in sources}
        if unknown:
            raise InputError(f"Unbekannte Quell-IDs: {', '.join(sorted(unknown))}")
    http = http or PoliteSession()
    entries = []
    for s in chosen:
        try:
            if not s.url:
                raise InputError("URL fehlt in der Konfiguration")
            res = fetch(s.url, quelle_id=s.id, force=force, max_age=max_age,
                        data_dir=data_dir, config=config, http=http, now=now)
            entries.append(manifest_entry(res, s.id, s.url))
        except FetchError as e:
            log.error("%s: %s", s.id, e)
            entries.append(manifest_entry(None, s.id, s.url, e))
        except Exception as e:  # unerwartet: Quelle scheitert, Lauf geht weiter
            log.exception("%s: unerwarteter Fehler", s.id)
            entries.append(manifest_entry(None, s.id, s.url, e))
    herkunft = resolve_config(Path(config) if config else None)[1]
    path = write_manifest(store.Store(data_dir), entries, now, konfiguration=herkunft)
    return RunResult(exit_code(entries), path, entries)


def check(http: PoliteSession | None = None) -> dict[str, str]:
    client = GenesisClient(http or PoliteSession())
    try:
        inst = client.instance()
        return {"destatis": "ok" if inst else "unerwartete Antwort"}
    except FetchError as e:
        return {"destatis": f"fehler: {e}"}
