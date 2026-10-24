# demografie-fetch

Demografiedaten für die Immobilien-Ampel Deutschland: **URL rein, Tabelle je Kreis raus.**

Erste Stufe der Pipeline (DVC, Parquet, DuckDB). Die Komponente erkennt die Quelle an der URL, holt die Daten exakt, ohne Rundung oder Schätzung, lädt nur bei Änderung neu und schreibt:

- ein **Langformat** (`data/staging/<quelle_id>.parquet`) für die Pipeline und
- eine **breite Tabelle je Kreis** (`data/staging/<quelle_id>_kreise.csv`).

Spezifikation: `openspec/changes/add-genesis-adapter/` (nach dem Archivieren: `openspec/specs/`). Zugang je Quelle: `docs/zugangsbericht.md`.

## Installation

```bash
uv sync
uv run demografie-fetch --help
```

## Nutzung

```bash
# Struktur ansehen (lädt keine Daten)
demografie-fetch "https://genesis.destatis.de/datenbank/online/statistic/12411/table/12411-0017" --list

# Abrufen, Auswahl ab 2012, Altersgruppe als Zeile statt Spalte
demografie-fetch "https://genesis.destatis.de/datenbank/online/statistic/12411/table/12411-0017" \
    --startyear 2012 --wide zeit,altx20

# Statistik-URL: listet die Tabellen und bricht ab (Exit 2), Wahl mit --table
demografie-fetch "https://genesis.destatis.de/datenbank/online/statistic/12411" --table 12411-0017

demografie-fetch run                              # alle aktiven Quellen aus der Konfiguration
demografie-fetch run --only kbv16_laender --force # ohne Änderungsprüfung
demografie-fetch check                            # Erreichbarkeit der Schnittstelle
```

Weitere Optionen: `--endyear`, `--select DIM=W1,W2` (mehrfach), `--role rahmen|kontext|validierung`, `--max-age <stunden>`, `--data-dir <pfad>` (oder `DEMOGRAFIE_DATA_DIR`), `--config <datei>`, `-v`.

Exit-Codes: `0` ok, unverändert oder aus dem Cache · `1` Teilfehler · `2` Abbruch (Eingabe unklar, Quelle gesperrt oder nicht unterstützt, alle Quellen fehlgeschlagen).

### Python

```python
from demografie_fetch import fetch

r = fetch("https://genesis.destatis.de/datenbank/online/statistic/12421/table/12421-0004")
r.long_df      # Langformat
r.wide_df      # breit je Region (Kreis oder Land) oder None
r.meta         # status, stand, sha256, tabelle, titel, vollstaendigkeit, ggf. veraltet
r.paths        # parquet, wide_csv, raw
```

## Cache

| Stufe | Bedingung | Netzwerk | Ergebnis |
|---|---|---|---|
| 1 Prüfintervall | letzte Prüfung jünger als `--max-age` (Standard 6 h, je Quelle `pruef_intervall_stunden`) | keins | `cache` |
| 2 Stand | `lastChange` der Tabelle unverändert | nur Metadaten (klein) | `unveraendert`, Parquet unberührt |
| 3 Prüfsumme | Daten geladen, SHA-256 gleich der letzten Fassung | Daten | `unveraendert`, keine neue Rohfassung |
| neu | Inhalt geändert | Daten | neue Rohfassung `data/raw/<id>/<UTC>_<sha8>/`, Tabellen neu |

Eine geänderte Auswahl (`--startyear`, `--wide`, …) baut die Tabellen aus der letzten Rohfassung neu auf, ohne erneuten Download. `--force` lädt immer, legt aber keine doppelte Rohfassung an. Rohfassungen werden nie überschrieben.

## Ablage

```
config/sources_demografie.yaml          Quellen (id, url, rolle, aktiv, zugang, auswahl, ...)
config/referenz_kreise.csv              400 Kreise, Gebietsstand 31.12.2024
data/raw/<quelle_id>/<UTC>_<sha8>/      data.json, structure.json, qualitySigns.json, meta.json
data/raw/<quelle_id>/_state.json        Stand, Prüfsumme, letzte Prüfung
data/staging/<quelle_id>.parquet        Langformat (Metadaten: quelle, stand, lizenz, sha256)
data/staging/<quelle_id>_kreise.csv     breite Tabelle je Kreis
data/validation/<quelle_id>.parquet     nur Rolle «validierung»
runs/<UTC>/manifest_demografie.json     je Quelle: neu | unveraendert | cache | fehler
```

Langformat: `quelle_id, tabelle, zeit, ags5|land, <dim>_code, <dim>_label …, merkmal_code, merkmal_label, einheit, wert, sonderzeichen, qualitaet`. Amtliche Sonderzeichen (`-`, `.`, `...`, `/`, `x`) ergeben einen leeren `wert` und stehen in `sonderzeichen`; Kennzeichen wie `p`, `r`, `s`, `e` stehen in `qualitaet`.

## DVC

```yaml
stages:
  demografie_fetch:
    cmd: demografie-fetch run --max-age 0
    deps:
      - config/sources_demografie.yaml
    outs:
      - data/staging/kbv16_laender.parquet:
          persist: true
      - data/staging/bevoelkerung_kreise_alter.parquet:
          persist: true
    always_changed: true
  ampel_kontext:
    cmd: python pipeline/kontext.py
    deps:
      - data/staging/bevoelkerung_kreise_alter.parquet
    outs:
      - data/features/kontext.parquet
```

`always_changed: true` lässt die erste Stufe bei jedem `dvc repro` prüfen. Weil unveränderte Quellen das Parquet nicht anfassen, bleibt dessen Hash gleich, und die Folgestufen rechnen nur bei echten Änderungen neu.

## Quellen und Grenzen

- **GENESIS-Online (Destatis):** Die Daten kommen über die öffentliche, **nicht dokumentierte** Schnittstelle der Web-Oberfläche (`/genesis/api/rest/tables/<code>/...`), ohne Token. Ändert Destatis das Format, schlägt die Quelle mit „Antwortformat unerwartet“ fehl, und das alte Parquet bleibt erhalten. Lizenz: Datenlizenz Deutschland – Namensnennung 2.0, © Statistisches Bundesamt (Destatis).
- **Regionaldatenbank** (Geburten, Sterbefälle, Wanderungen je Kreis): ohne Token nicht abrufbar. Die Quelle wird erkannt und mit Exit 2 abgewiesen. Der Weg über `import` folgt mit `add-file-and-import`.
- **BBSR-Tableau (ROP 2045)** und **Dateien:** werden erkannt, die Adapter folgen in eigenen Changes.

## Entwicklung

```bash
uv run pytest            # ohne Netzwerk
uv run pytest -m live    # gegen Destatis
uv run ruff check src tests probe && uv run mypy src tests probe
```

Lizenz: MIT
