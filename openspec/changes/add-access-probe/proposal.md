# Proposal

## Why

Bevor ein Adapter gebaut wird, muss feststehen, welche Quellen per URL überhaupt abrufbar sind. Eine Vorabprüfung aus einem Rechenzentrum ergab für `tableau.bbsr.bund.de` 4xx-Antworten, sogar für `robots.txt`. Der Server filtert also vermutlich nach Herkunft. Ohne belastbare Zugangsprüfung von lokal **und** aus der Cloud würden wir Adapter bauen, die nie laufen, oder Zeitpläne (CI vs. lokal) falsch wählen.

## What Changes

- Neues Skript `probe/access_probe.py` (nur `requests`, `playwright`, `PyYAML`): liest `config/sources_demografie.yaml` und führt je Quelle die Tests T1–T8 aus. Höflich: höchstens eine Anfrage je Test, 2 s Pause, keine Umgehung von Sperren.
- Ausgabe als JSON-Bericht (`probe/report_local.json` bzw. `probe/report_ci.json`) mit Statuscodes, Auszügen (gekürzt, ohne Tokens) und einer vorläufigen Zugangsklasse je Quelle.
- Neuer Workflow `.github/workflows/access-probe.yml` (nur `workflow_dispatch`), der dieselben Tests auf einem GitHub-Runner ausführt und den Bericht als Artefakt hochlädt. Tokens kommen aus Repository-Secrets.
- Startkonfiguration `config/sources_demografie.yaml` (Abschnitt 8 des Auftrags).
- Bericht `docs/zugangsbericht.md`: je Quelle Ergebnisse lokal und CI, Bewertung, vorgeschlagene Zugangsklasse (A-cloud, A-lokal, A-browser, B-manuell).
- Nach Freigabe: Feld `zugang:` je Quelle in der Konfiguration.

## Capabilities

### New Capabilities
- `access-probe`: Lesende, höfliche Prüfung der Erreichbarkeit jeder konfigurierten Quelle aus verschiedenen Netzen und Einstufung in eine Zugangsklasse.

### Modified Capabilities
- keine

## Impact

- Neue Dateien: `probe/`, `config/sources_demografie.yaml`, `.github/workflows/access-probe.yml`, `docs/zugangsbericht.md`.
- Neue Entwicklungsabhängigkeiten: `requests`, `PyYAML`, `playwright` (Chromium bzw. lokal installiertes Chrome).
- Repository-Secrets `GENESIS_TOKEN` und `REGIO_TOKEN` (optional; ohne sie werden T6/T7 als „kein Token“ gewertet).
- Entscheidet, welche der Changes `add-genesis-adapter`, `add-file-and-import`, `add-tableau-adapter` folgen.
