# notebook-usage Specification

## Purpose
Stellt sicher, dass die Komponente in einem lokalen Jupyter-Notebook installiert und ohne Klon des Repos vollständig genutzt werden kann.

## Requirements

### Requirement: Installation aus dem Repo
Das System SHALL sich in einem Jupyter-Kernel mit Python ≥ 3.11 per `%pip install "git+https://github.com/trosinde/demografie-fetch.git@<tag>"` ohne Zugangsdaten installieren lassen und danach ohne Neustart des Kernels importierbar sein.

#### Scenario: Frischer Kernel
- **WHEN** in einem neuen Kernel die Installationszelle und danach `from demografie_fetch import fetch` ausgeführt werden
- **THEN** gelingt der Import, und `demografie_fetch.__version__` entspricht dem Tag

#### Scenario: Zu altes Python
- **WHEN** der Kernel Python 3.10 nutzt
- **THEN** bricht die Installation mit dem Hinweis auf `requires-python >= 3.11` ab

### Requirement: Lauffähig ohne Repo
Das System SHALL außerhalb eines Klons des Repos alle Funktionen bieten: Abruf, Cache, Langformat, breite Tabelle, Vollständigkeitsprüfung gegen 400 Kreise und `run` mit der mitgelieferten Beispielkonfiguration. Daten SHALL unter `data_dir` (Standard: Arbeitsverzeichnis des Notebooks) liegen.

#### Scenario: Vollständigkeit im Notebook
- **WHEN** im Notebook-Ordner ohne `config/` die Tabelle 12411-0015 mit `startyear=2024` abgerufen wird
- **THEN** meldet `meta["vollstaendigkeit"]` 400 Kreise je Zeitpunkt ohne Abweichung

### Requirement: Darstellung im Notebook
Das System SHALL `FetchResult` im Notebook als kurze Zusammenfassung (Quelle, Status, Tabelle, Titel, Stand, Zeilen, Vollständigkeit, Pfade) darstellen, ohne die Datenrahmen auszugeben, und `RunResult.to_frame()` als Tabelle mit einer Zeile je Quelle liefern.

#### Scenario: Ergebnis als letzte Zeile einer Zelle
- **WHEN** eine Zelle mit `fetch(url)` endet
- **THEN** zeigt das Notebook die Zusammenfassung als HTML-Tabelle und nicht 17.000 Zeilen Daten

### Requirement: Geprüftes Beispiel-Notebook
Das Repo SHALL ein Beispiel-Notebook `notebooks/schnellstart.ipynb` enthalten, das Installation, Abruf, Cache und Lauf zeigt. CI SHALL es in einer frischen Umgebung mit dem aus dem Repo gebauten Paket vollständig ausführen; ein Fehler in einer Zelle SHALL den Workflow fehlschlagen lassen.

#### Scenario: CI führt das Notebook aus
- **WHEN** ein Pull Request Code, Paketdaten oder das Notebook ändert
- **THEN** führt der Workflow `notebook` alle Zellen aus und ist nur grün, wenn keine Zelle einen Fehler wirft
