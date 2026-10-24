# Spec Delta

## MODIFIED Requirements

### Requirement: Python-API
Das System SHALL `fetch(url, **opts) -> FetchResult`, `run(**opts) -> RunResult` und `list_source(url, table=None) -> str` bereitstellen, mit denselben Optionen wie die CLI. `FetchResult` SHALL `long_df`, `wide_df` (oder `None` ohne Kreis- bzw. Landesebene), `meta` (Status, Stand, Prüfsumme, Tabelle, Titel, Vollständigkeit) und `paths` enthalten. `RunResult` SHALL `exit_code`, `manifest_path`, `entries` und `to_frame()` enthalten und sich wie bisher als Tupel `(exit_code, manifest_path, entries)` entpacken lassen. Fehler SHALL als Ausnahmen mit Exit-Code-Bezug gemeldet werden.

#### Scenario: Wiederholter Aufruf im Notebook
- **WHEN** `fetch(url)` zweimal hintereinander aufgerufen wird
- **THEN** liefert der zweite Aufruf dieselben Daten aus dem Cache mit `meta["status"] == "cache"`

#### Scenario: Lauf als Tabelle
- **WHEN** `run().to_frame()` aufgerufen wird
- **THEN** entsteht ein DataFrame mit den Spalten `quelle_id`, `status`, `tabelle`, `stand`, `zeilen`, `fehler`

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
