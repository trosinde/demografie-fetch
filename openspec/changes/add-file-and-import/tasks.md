# Tasks

## 1. Kern

- [ ] 1.1 Adapter-Protokoll (`stand`, `download`, `parse`) und Umbau von `core.fetch` darauf; `genesis` als erste Umsetzung; alle bestehenden Tests unverändert grün
- [ ] 1.2 `http`: `robots.txt` je Host (Disallow → Exit 2 mit Hinweis auf import, Crawl-delay als Mindestabstand je Host), bedingte Header, HTTP 304 als Ergebnis; Tests mit gemocktem Transport
- [ ] 1.3 `detect`: Datei-Links (`.csv`, `.xlsx`, `.zip`, mit Abfrageparametern) → `file`; Meldung Regionaldatenbank mit import-Befehl; Positiv- und Negativtests

## 2. Datei-Adapter

- [ ] 2.1 Fixtures: gekürzte Kreisliste als XLSX (Deckblatt, Titel, Kopf mit Fußnoten, Zwischen-, Summen- und Fußnotenzeilen), CSV mit `;` und deutschem Zahlenformat inkl. Sonderzeichen, ZIP mit zwei Dateien
- [ ] 2.2 `adapters/file`: Download mit ETag/Last-Modified, Rohfassung, Blätter/ZIP-Inhalte auflisten, Wahl über Regel, `--sheet`, `--member`; ohne Regel Aufbau melden und Exit 2; Pflichtfall 7 (HTTP 304) und Test „Server ohne ETag“ grün

## 3. Bereinigung

- [ ] 3.1 Regelschema und Laden aus `config/bereinigung/`; Fehlermeldung mit vorhandenen Spaltenköpfen; Regel-Hash im Auswahl-Schlüssel
- [ ] 3.2 `cleanup`: Kopfzeilen verbinden, verbundene Zellen, Fußnotenzeichen, Datenbeginn, Schlüsselebene, Zeit (Wert, Titel, Spalte), Dimensionen, Merkmale, `breit_ueber`; Werte über `parse_number`, Fundstelle bei unbekanntem Inhalt; Tests mit allen Fixtures
- [ ] 3.3 Namensabgleich über `config/referenz_kreise.csv` und `config/bereinigung/_namen.yaml`, nur eindeutige Treffer, Meldung im Manifest; Test „Rosenheim“ (mehrdeutig) und Test mit Typspalte (eindeutig)

## 4. Import

- [ ] 4.1 `core.import_file` und CLI `import`; nur konfigurierte Quellen mit Regel; Kopie byte-gleich, `meta.json` ohne lokalen Pfad; Tests: erster Import `neu`, zweiter `unveraendert`, unbekannte Quelle Exit 2
- [ ] 4.2 `run`: Quellen mit `adapter: import` als `manuell` mit Stand und `veraltet` im Manifest; Exit-Code-Logik; Test

## 5. Quellen

- [ ] 5.1 Regel `destatis_gv_kreise` und Quelle `gv_kreise` in der Konfiguration; Live-Test: 400 Kreise, 5 Merkmale, Stichtag 2024-12-31, zweiter Lauf `unveraendert` über 304 oder Prüfsumme
- [ ] 5.2 Regel `regio_bewegungen` für die Beispieldatei der Regionaldatenbank (erst nach Eingang der Datei vom Nutzer); Import-Test mit gekürzter Fixture; Quelle `bewegungen_kreise` auf `adapter: import`
- [ ] 5.3 `scripts/referenz_kreise.py` erzeugt `config/referenz_kreise.csv` aus `gv_kreise`; Vergleich mit der bisherigen Liste ergibt 400 gleiche Schlüssel; Kopf nennt die neue Quelle

## 6. Qualität und Doku

- [ ] 6.1 `ruff`, `mypy --strict`, `pytest` grün; CI grün
- [ ] 6.2 README: Quellenstatus (Dateien unterstützt, Regionaldatenbank über import), Abschnitt „Datei-Quelle anbinden“ mit Regelbeispiel, Abschnitt „Datei importieren“, Bausteindiagramm und Sequenzdiagramm Datei/Import aus design.md; alle neuen Befehle lokal geprüft
- [ ] 6.3 design.md mit der Umsetzung abgleichen (Diagramme und Entscheidungen); CHANGELOG 0.2.0

## Workflow follow-up

- PR `feat/add-file-and-import` → `main` (Basis vorher prüfen: #4 muss gemergt sein), Review und Merge durch den Nutzer.
- Danach `/opsx:archive add-file-and-import`.
