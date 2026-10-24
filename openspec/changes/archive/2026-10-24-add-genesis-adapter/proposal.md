# Proposal

## Why

Laut Zugangsbericht gibt es keinen GENESIS-API-Key, und der Gastzugang der REST-API ist gesperrt. Die öffentliche Web-Oberfläche von GENESIS-Online (Destatis) lädt Tabellen aber ohne Anmeldung vollständig und exakt über ihre eigene Schnittstelle, auch aus der Cloud. Damit lassen sich die Rahmenprognose 12421-0004 und die Bevölkerung nach Kreisen und Altersgruppen (12411-0017) automatisch beziehen. Diese Change baut den Kern der Komponente und den ersten Adapter darauf. Ein Cache sorgt dafür, dass nur bei geänderten Daten neu geladen wird.

## What Changes

- Paket `demografie_fetch` mit CLI `demografie-fetch` und Python-API `fetch(url, **opts) -> FetchResult`.
- URL-Erkennung: Destatis-URLs (Tabelle oder Statistik) gehen an den Adapter `genesis`. Regionaldatenbank, Tableau und Dateien werden erkannt, aber mit klarer Meldung und Exit 2 abgewiesen, bis ihre Changes folgen. Unbekannte URLs ebenfalls Exit 2.
- Adapter `genesis` über die öffentliche Web-Schnittstelle von GENESIS-Online, ohne Token, höflich (sequenziell, max. 1 Anfrage/s, Backoff).
- Mehrstufiger Cache: Prüfintervall, `lastChange`-Vergleich, SHA-256 der Rohdaten; unveränderte Quellen erzeugen weder Download noch neue Rohfassung noch neues Parquet.
- Versionierte Rohablage, Langformat als Parquet (atomar), breite Tabelle je Kreis als CSV, Manifest je Lauf, Vollständigkeitsprüfung gegen eine eingecheckte Kreisliste (400).
- Rollentrennung: Quellen mit Rolle `validierung` landen nur unter `data/validation/`.
- Befehle `demografie-fetch "<url>"`, `--list`, `--table`, `run`, `run --only/--force`, `check`.
- GitHub Actions: Lint und Tests bei jedem Push, monatlicher `run` mit Manifest als Artefakt.

Nicht enthalten (eigene Changes): Datei-Adapter und `import`, Tableau-Adapter, Rahmencheck gegen die ROP 2045, Umschlüsselung bei Gebietsreformen, Zugriff auf die Regionaldatenbank.

## Capabilities

### New Capabilities
- `source-detection`: Ableitung von Adapter, Datenbank und Tabelle aus einer URL; Abweisen unbekannter oder noch nicht unterstützter Quellen.
- `genesis-source`: Exakter, höflicher Abruf von GENESIS-Online-Tabellen (Destatis) ohne Token, inkl. Fehlerbehandlung.
- `change-cache`: Erkennung unveränderter Quellen, versionierte Rohablage und Wiederverwendung bereits erzeugter Tabellen.
- `table-output`: Langformat, breite Tabelle je Kreis, Parquet-Metadaten, Vollständigkeitsprüfung und Rollentrennung.
- `fetch-interface`: CLI, Python-API, Konfigurationslauf, Manifest und Exit-Codes.

### Modified Capabilities
- keine

## Impact

- Neuer Code unter `src/demografie_fetch/`, Tests unter `tests/` mit aufgezeichneten Antworten in `tests/fixtures/`.
- Neue Abhängigkeiten: `requests`, `pandas`, `pyarrow`, `PyYAML`.
- Neue Dateien: `config/referenz_kreise.csv`, `.github/workflows/ci.yml`, `.github/workflows/monthly.yml`, README mit DVC-Beispiel, CHANGELOG.
- Konfiguration: `bevoelkerung_kreise_alter` zeigt auf Destatis 12411-0017 statt auf die Regionaldatenbank.
- Abhängigkeit von einer nicht dokumentierten Schnittstelle (siehe design.md, Risiken).
