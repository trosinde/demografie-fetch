# Tasks

## 1. Grundgerüst

- [x] 1.1 `pyproject.toml` (Python ≥ 3.11, Paket `demografie_fetch`, Gruppe `probe` mit requests, PyYAML, playwright), `.gitignore`, LICENSE (MIT) anlegen; `uv sync --group probe` läuft durch
- [x] 1.2 `config/sources_demografie.yaml` mit der Startkonfiguration anlegen; `python -c "import yaml; yaml.safe_load(open(...))"` liest 5 Quellen

## 2. Prüfskript

- [x] 2.1 `probe/access_probe.py` mit Testauswahl je Quelltyp, T1–T8, 2-s-Pause, Token-Maskierung, JSON-Bericht und vorläufiger Klasse; `python probe/access_probe.py --dry-run` zeigt den Testplan ohne Netzwerk
- [x] 2.2 Unit-Tests `tests/test_access_probe.py` für Testauswahl, Code-Erkennung aus URL, Maskierung, Klassenableitung und Pause (ohne Netzwerk); `pytest` grün

## 3. Ausführung

- [x] 3.1 Lokal ausführen; `probe/report_local.json` liegt vor
- [x] 3.2 Workflow `.github/workflows/access-probe.yml` (nur `workflow_dispatch`) anlegen, Repo erstellen und pushen, Workflow starten; `probe/report_ci.json` als Artefakt verfügbar und ins Repo übernommen

## 4. Bericht

- [x] 4.1 `docs/zugangsbericht.md` mit Tabelle je Quelle (lokal, CI, Bewertung, vorgeschlagene Klasse) schreiben und dem Nutzer vorlegen

## Workflow follow-up

- Freigabe des Nutzers zu Klasse, Adapter ja/nein und Zeitplan je Quelle einholen.
- Feld `zugang:` je Quelle in `config/sources_demografie.yaml` eintragen.
- README-Überblick inkl. Zugangsprüfung: umgesetzt mit `add-genesis-adapter`, Aufgabe 6.4.
- Change archivieren (`/opsx:archive`).
