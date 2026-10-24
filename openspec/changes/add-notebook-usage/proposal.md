# Proposal

## Why

Die Komponente soll in einem lokalen Jupyter-Notebook (JupyterLab oder VS Code) installiert und ausgeführt werden. Ein Test am 24.10.2026 hat gezeigt, dass das heute nicht vollständig funktioniert: Das Wheel enthält `config/referenz_kreise.csv` nicht, deshalb fehlt außerhalb des Repos die Vollständigkeitsprüfung („Referenzliste fehlt“). Außerdem ist das Repo privat, eine Installation per `%pip install git+…` scheitert ohne Zugangsdaten, und `run()` braucht eine Konfiguration im Arbeitsverzeichnis.

## What Changes

- **Installation im Notebook:** `%pip install "git+https://github.com/trosinde/demografie-fetch.git@v0.2.0"` aus dem öffentlichen Repo, Version über Git-Tag festgelegt. Voraussetzung: Python ≥ 3.11 im Kernel.
- **Repo öffentlich machen**, nach einer Prüfung auf persönliche Daten und deiner ausdrücklichen Freigabe (Entscheidungspunkt, siehe design.md).
- **Mitgelieferte Ressourcen:** Referenzliste der Kreise und eine Beispielkonfiguration der Quellen liegen im Paket. Lokale Dateien unter `config/` haben Vorrang.
- **Notebook-freundliche API:**
  - `FetchResult` zeigt im Notebook eine kurze Zusammenfassung (Status, Tabelle, Zeilen, Vollständigkeit, Pfade) statt der ganzen Datenrahmen.
  - `run()` liefert ein `RunResult` mit `exit_code`, `manifest_path`, `entries` und `to_frame()`; Entpacken als Tupel bleibt möglich.
  - `list_source(url)` ist Teil der öffentlichen API.
- **Beispiel-Notebook** `notebooks/schnellstart.ipynb`: Installation, Abruf, Cache-Verhalten, breite Tabelle, Lauf über die Konfiguration. Es wird in CI in einer frischen Umgebung aus dem gebauten Paket ausgeführt.
- **Release** 0.2.0 mit Git-Tag und CHANGELOG; README-Abschnitt „Im Jupyter-Notebook“.

## Capabilities

### New Capabilities
- `notebook-usage`: Installation aus dem Repo, Lauffähigkeit außerhalb des Repos und Darstellung im Notebook, abgesichert durch ein in CI ausgeführtes Beispiel-Notebook.

### Modified Capabilities
- `table-output`: Die Referenzliste wird aus dem Projekt oder, falls dort nicht vorhanden, aus dem Paket gelesen.
- `fetch-interface`: Python-API mit `RunResult`, `list_source` und Notebook-Darstellung; `run` nutzt ohne lokale Konfiguration die mitgelieferte Beispielkonfiguration.

## Impact

- Code: `store`/`output` (Ressourcen über `importlib.resources`), `config` (Suchreihenfolge), `core` (`RunResult`, `_repr_html_`), `__init__` (Exporte).
- Neue Dateien: `src/demografie_fetch/data/referenz_kreise.csv`, `src/demografie_fetch/data/sources_demografie.yaml`, `notebooks/schnellstart.ipynb`, Workflow `notebook.yml`.
- Neue Entwicklungsabhängigkeiten: `nbclient`, `ipykernel` (nur für CI und Tests).
- GitHub: Sichtbarkeit des Repos wird öffentlich; Tag `v0.2.0`.
- Reihenfolge: Dieser Change sollte vor `add-file-and-import` umgesetzt werden, weil dort die Bereinigungsregeln über denselben Ressourcen-Mechanismus mitgeliefert werden.
