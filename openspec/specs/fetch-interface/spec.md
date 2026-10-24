# fetch-interface Specification

## Purpose
Beschreibt, wie Menschen und Pipeline die Komponente aufrufen: Kommandozeile, Python-API, Lauf über die Konfiguration, Manifest und Exit-Codes.

## Requirements

### Requirement: Einzelabruf per URL
Das System SHALL mit `demografie-fetch "<url>" [--table CODE] [--startyear J] [--endyear J] [--select DIM=W1,W2] [--role ROLLE] [--wide DIMS] [--max-age H] [--force]` genau eine Quelle abrufen, die Tabellen schreiben und eine Zusammenfassung (Status, Zeilen, Pfade) ausgeben.

#### Scenario: Erster Abruf
- **WHEN** `demografie-fetch "<12421-0004-URL>"` zum ersten Mal läuft
- **THEN** entstehen Rohfassung, Parquet und Manifest, die Ausgabe meldet `neu`, Exit-Code 0

#### Scenario: Zweiter Abruf
- **WHEN** derselbe Aufruf erneut läuft
- **THEN** meldet die Ausgabe `cache` oder `unveraendert`, Exit-Code 0

### Requirement: Auflisten
Das System SHALL mit `--list` nur die Struktur anzeigen: bei einer Statistik die Tabellen, bei einer Tabelle Titel, Stand, Dimensionen mit Anzahl und Beispielwerten, Zeitraum und Merkmale. Dabei SHALL es keine Daten laden und nichts schreiben.

#### Scenario: Tabelle auflisten
- **WHEN** `demografie-fetch "<12411-0017-URL>" --list` läuft
- **THEN** zeigt die Ausgabe die Dimensionen `KREISE`, `STAG`, `ALTX20` und das Merkmal `BEVSTD`, ohne Dateien zu schreiben

### Requirement: Lauf über die Konfiguration
Das System SHALL mit `demografie-fetch run` bzw. `run()` alle Quellen mit `aktiv: true` aus der Konfiguration nacheinander abrufen; `--only ID[,ID]` beschränkt den Lauf, `--force` erzwingt den Abruf. Konfiguration ist die angegebene Datei, sonst `config/sources_demografie.yaml` im Arbeitsverzeichnis, sonst die im Paket mitgelieferte Beispielkonfiguration; welche genutzt wurde, steht im Manifest. Eine fehlgeschlagene Quelle SHALL den Lauf nicht abbrechen.

#### Scenario: Eine Quelle schlägt fehl
- **WHEN** von zwei aktiven Quellen eine mit Fehler endet
- **THEN** wird die andere trotzdem abgerufen, beide stehen im Manifest, und der Exit-Code ist 1

#### Scenario: Nicht unterstützte aktive Quelle
- **WHEN** eine aktive Quelle auf die Regionaldatenbank zeigt
- **THEN** steht sie mit Status `fehler` und Begründung im Manifest, der Lauf geht weiter

#### Scenario: Notebook ohne Konfiguration
- **WHEN** `run()` in einem Ordner ohne `config/` aufgerufen wird
- **THEN** werden die aktiven Quellen der mitgelieferten Beispielkonfiguration abgerufen, und das Manifest nennt `konfiguration: paket`

### Requirement: Manifest
Das System SHALL je Lauf `runs/<UTC-zeit>/manifest_demografie.json` schreiben mit: je Quelle `id`, `url`, `tabelle`, `status` (`neu`, `unveraendert`, `cache`, `fehler`), Stand, Prüfsumme, Zeilenzahl, Pfade, Vollständigkeitsbefund, Fehlermeldung und Hinweis auf veraltete Daten.

#### Scenario: Veraltete Quelle
- **WHEN** der Stand einer Quelle älter ist als ihr `max_alter_monate`
- **THEN** enthält ihr Manifest-Eintrag einen Hinweis `veraltet` mit dem Alter in Monaten

### Requirement: Erreichbarkeitsprüfung
Das System SHALL mit `demografie-fetch check` je unterstützter Datenbank prüfen, ob die Schnittstelle antwortet, und das Ergebnis ausgeben, ohne Daten zu laden.

#### Scenario: Destatis erreichbar
- **WHEN** `demografie-fetch check` läuft und die Schnittstelle antwortet
- **THEN** meldet die Ausgabe `destatis: ok` und der Exit-Code ist 0

### Requirement: Exit-Codes
Das System SHALL mit 0 enden, wenn alle Quellen neu, unverändert oder aus dem Cache geliefert wurden; mit 1, wenn mindestens eine Quelle fehlschlug und mindestens eine erfolgreich war; mit 2 bei unklarer Eingabe, gesperrter oder nicht unterstützter Quelle oder wenn alle Quellen fehlschlugen.

#### Scenario: Unklare Eingabe
- **WHEN** eine Statistik-URL ohne `--table` übergeben wird
- **THEN** ist der Exit-Code 2

### Requirement: Python-API
Das System SHALL `fetch(url, **opts) -> FetchResult`, `run(**opts) -> RunResult` und `list_source(url, table=None) -> str` bereitstellen, mit denselben Optionen wie die CLI. `FetchResult` SHALL `long_df`, `wide_df` (oder `None` ohne Kreis- bzw. Landesebene), `meta` (Status, Stand, Prüfsumme, Tabelle, Titel, Vollständigkeit) und `paths` enthalten. `RunResult` SHALL `exit_code`, `manifest_path`, `entries` und `to_frame()` enthalten und sich wie bisher als Tupel `(exit_code, manifest_path, entries)` entpacken lassen. Fehler SHALL als Ausnahmen mit Exit-Code-Bezug gemeldet werden.

#### Scenario: Wiederholter Aufruf im Notebook
- **WHEN** `fetch(url)` zweimal hintereinander aufgerufen wird
- **THEN** liefert der zweite Aufruf dieselben Daten aus dem Cache mit `meta["status"] == "cache"`

#### Scenario: Lauf als Tabelle
- **WHEN** `run().to_frame()` aufgerufen wird
- **THEN** entsteht ein DataFrame mit den Spalten `quelle_id`, `status`, `tabelle`, `stand`, `zeilen`, `fehler`

### Requirement: Datenverzeichnis
Das System SHALL Ablage, Staging, Validierung und Läufe relativ zu einem Basisverzeichnis anlegen, das über `--data-dir` bzw. `DEMOGRAFIE_DATA_DIR` gesetzt wird; Standard ist das aktuelle Arbeitsverzeichnis (`./data`, `./runs`).

#### Scenario: Eigenes Verzeichnis
- **WHEN** `--data-dir /tmp/x` gesetzt ist
- **THEN** liegen alle geschriebenen Dateien unter `/tmp/x/data` und `/tmp/x/runs`
