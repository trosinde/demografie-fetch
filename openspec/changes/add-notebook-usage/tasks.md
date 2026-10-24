# Tasks

## 1. Paketdaten

- [x] 1.1 `src/demografie_fetch/data/referenz_kreise.csv` und `sources_demografie.yaml` anlegen; Suchreihenfolge (Parameter, `./config`, Paket) für Referenzliste und Konfiguration über `importlib.resources`; Herkunft im Manifest; Tests: ohne `config/` im Arbeitsverzeichnis wird die Paketfassung genutzt, mit `config/` die Projektfassung
- [x] 1.2 Test am gebauten Wheel: `uv build`, Wheel enthält `demografie_fetch/data/*`; Test: Projekt- und Paketfassung der Referenzliste sind identisch

## 2. API für Notebooks

- [x] 2.1 `RunResult` (NamedTuple mit `to_frame()`), `list_source` exportieren, CLI unverändert lauffähig; Tests für Entpacken als Tupel und `to_frame()`
- [x] 2.2 `FetchResult.__repr__` und `_repr_html_` (Quelle, Status, Tabelle, Titel, Stand, Zeilen, Vollständigkeit, Pfade); Test, dass die Ausgabe keine Datenzeilen enthält

## 3. Beispiel-Notebook und CI

- [x] 3.1 `notebooks/schnellstart.ipynb`: Installationszelle (Tag `skip-ci`), Abruf 12411-0015 ab 2024, Zusammenfassung, `wide_df.head()`, zweiter Abruf `cache`, `list_source`, `run(config=…)` mit kleiner Beispielkonfiguration und `to_frame()`; lokal mit `nbclient` vollständig ausgeführt
- [ ] 3.2 Workflow `notebook.yml` (Wheel bauen, frische venv, Notebook ausführen, ausgeführtes Notebook als Artefakt); auf dem Pull Request grün

## 4. Veröffentlichung und Release

- [ ] 4.1 Entscheidung des Nutzers zu Option (a), (b) oder (c) aus design.md einholen und umsetzen; Prüfung erneut ausführen und Ergebnis zeigen
- [ ] 4.2 Nach ausdrücklicher Freigabe: Repo öffentlich stellen (`gh repo edit --visibility public`); Installation per `%pip install git+https://…@<commit>` ohne Zugangsdaten in einem frischen lokalen Kernel geprüft
- [ ] 4.3 Version 0.2.0, CHANGELOG; nach dem Merge Tag `v0.2.0` und Installation mit dem Tag in frischem Kernel geprüft

## 5. Doku

- [x] 5.1 README: Abschnitt „Im Jupyter-Notebook“ (Installation mit Tag, Python ≥ 3.11, `%pip` statt `!pip`, Beispielzellen, `data_dir`, Logging), Verweis auf das Beispiel-Notebook, Bausteindiagramm und Sequenzdiagramm aus design.md
- [x] 5.2 design.md mit der Umsetzung abgleichen

## Workflow follow-up

- PR `feat/add-notebook-usage` → `main`; Basis vorher prüfen (#4 gemergt?).
- Nach dem Merge Tag `v0.2.0` setzen (Aufgabe 4.3) und `/opsx:archive add-notebook-usage`.
