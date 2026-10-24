# change-cache Specification

## Purpose
Sorgt dafür, dass Daten nur geladen und verarbeitet werden, wenn sie sich an der Quelle geändert haben, und dass jede inhaltlich neue Fassung der Rohdaten unverändert und dauerhaft abgelegt wird.

## Requirements

### Requirement: Prüfintervall
Das System SHALL eine Quelle, die innerhalb des Prüfintervalls bereits erfolgreich geprüft wurde und deren Tabellen vorliegen, ohne jede Netzwerkanfrage aus dem Cache liefern. Das Prüfintervall ist je Quelle (`pruef_intervall_stunden`) und per CLI (`--max-age <stunden>`) einstellbar; Standard sind 6 Stunden, `0` schaltet es ab.

#### Scenario: Wiederholter Aufruf kurz hintereinander
- **WHEN** dieselbe URL zweimal innerhalb von 6 Stunden abgerufen wird
- **THEN** stellt der zweite Aufruf keine Anfrage, liefert dieselben Tabellen und meldet `cache`

### Requirement: Änderungsprüfung über den Stand
Das System SHALL nach Ablauf des Prüfintervalls zuerst nur die Metadaten der Tabelle abrufen und den Stand (`lastChange`) mit dem gespeicherten Stand vergleichen. Bei gleichem Stand SHALL es keine Daten laden, keine neue Rohfassung schreiben und das Parquet nicht anfassen.

#### Scenario: Zweiter Lauf, Quelle unverändert
- **WHEN** ein Lauf nach Ablauf des Prüfintervalls stattfindet und der Stand gleich ist
- **THEN** wird nur die Metadaten-Anfrage gestellt, der Status lautet `unveraendert`, und Änderungszeit sowie Inhalt des Parquets bleiben gleich

### Requirement: Prüfsumme
Das System SHALL nach einem Datenabruf die SHA-256-Prüfsumme der Rohantwort bilden. Ist sie gleich der zuletzt abgelegten, SHALL es keine neue Rohfassung schreiben und den Status `unveraendert` melden.

#### Scenario: Neuer Stand, gleicher Inhalt
- **WHEN** sich `lastChange` geändert hat, die Daten aber byte-gleich sind
- **THEN** entsteht keine neue Rohfassung, der gespeicherte Stand wird aktualisiert, und der Status lautet `unveraendert`

### Requirement: Neue Fassung
Das System SHALL bei geändertem Inhalt eine neue Rohfassung unter `data/raw/<quelle_id>/<UTC-zeit>_<sha8>/` mit den unveränderten Antworten und einer `meta.json` (URL, Tabelle, Stand, Prüfsumme, Abrufzeit) anlegen. Bestehende Rohfassungen SHALL NOT überschrieben oder gelöscht werden.

#### Scenario: Geänderter Inhalt
- **WHEN** die Quelle neue Daten liefert
- **THEN** entsteht ein neues Verzeichnis, das vorherige bleibt unverändert erhalten, und der Status lautet `neu`

### Requirement: Zustand je Quelle
Das System SHALL je Quelle in `data/raw/<quelle_id>/_state.json` den letzten Stand, die Prüfsumme, die zuletzt gültige Rohfassung, den Auswahl-Schlüssel sowie Zeitpunkte der letzten Prüfung und des letzten Abrufs speichern und diese Datei atomar ersetzen.

#### Scenario: Abbruch während des Schreibens
- **WHEN** ein Lauf beim Schreiben abbricht
- **THEN** ist `_state.json` entweder im alten oder im neuen Zustand, nie halb geschrieben

### Requirement: Geänderte Auswahl ohne neuen Download
Das System SHALL bei unverändertem Stand, aber geänderter Auswahl die Tabellen aus der letzten Rohfassung neu erzeugen, ohne Daten erneut zu laden.

#### Scenario: Anderes Startjahr
- **WHEN** eine bereits geladene Tabelle mit anderem `startyear` abgerufen wird
- **THEN** wird nur die Metadaten-Anfrage gestellt, und Parquet sowie CSV entsprechen der neuen Auswahl

### Requirement: Erzwingen
Das System SHALL mit `--force` Prüfintervall und Standvergleich überspringen und die Daten neu laden; die Prüfsummen-Regel gegen doppelte Rohfassungen gilt weiterhin.

#### Scenario: Force bei gleichem Inhalt
- **WHEN** `run --only kbv16_laender --force` läuft und die Daten unverändert sind
- **THEN** werden die Daten geladen und die Tabellen neu geschrieben, aber keine zweite Rohfassung mit gleicher Prüfsumme angelegt

### Requirement: Fehlende Tabellen trotz Cache
Das System SHALL eine Quelle als neu zu erzeugen behandeln, wenn der Zustand vorhanden ist, das zugehörige Parquet aber fehlt.

#### Scenario: Parquet gelöscht
- **WHEN** `data/staging/<quelle_id>.parquet` gelöscht wurde und der Stand unverändert ist
- **THEN** wird das Parquet aus der letzten Rohfassung neu erzeugt, ohne die Daten erneut zu laden
