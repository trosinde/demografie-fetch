# Proposal

## Why

Mehrere Quellen liegen nicht in GENESIS-Online, sondern als Dateien vor: Länderprognosen (z. B. Bayern), das Gemeindeverzeichnis, Zensus-Tabellen. Geburten, Sterbefälle und Wanderungen je Kreis gibt es nur in der Regionaldatenbank; ohne Token bleibt dort nur der Download im Browser (Zugangsklasse B-manuell). Für beide Wege fehlt bisher ein Adapter: Datei-Links und die Regionaldatenbank werden heute erkannt und mit Exit 2 abgewiesen.

## What Changes

- Neuer Adapter `file` für direkte Links auf `.csv`, `.xlsx` und `.zip`: bedingter Download (`If-None-Match`/`If-Modified-Since`, HTTP 304 = unverändert), sonst Prüfsumme; Blätter und ZIP-Inhalte auflisten, Wahl mit `--sheet` bzw. `--member`.
- Höflichkeit für Datei-Server: `robots.txt` wird beachtet, inklusive `Crawl-delay` (destatis.de verlangt 30 s).
- **Bereinigungsregeln** je Quelle als YAML unter `config/bereinigung/`: Blatt, Kopfzeilen, Datenbeginn, Schlüsselspalte und Ebene, Zeit, Merkmalsspalten mit Code, Label und Einheit. Damit werden mehrzeilige Köpfe, Fußnotenzeichen, Zwischen- und Summenzeilen amtlicher Excel-Dateien ohne Code behandelt.
- Zuordnung über Namen, wenn eine Datei keinen Kreisschlüssel hat: nur eindeutige Treffer in der Referenzliste, unklare Namen werden gemeldet, nie geraten.
- Befehl `demografie-fetch import <quelle_id> <datei>` für im Browser geladene Dateien, mit gleicher Ablage, Prüfsumme und Bereinigung wie beim Download. Die Quelle `bewegungen_kreise` (Regionaldatenbank) wird darauf umgestellt.
- Gemeinsames Adapter-Protokoll im Kern (`stand`, `download`, `parse`), damit `genesis` und `file` dieselbe Cache- und Ablagelogik nutzen; das Verhalten von `genesis` ändert sich nicht.
- `config/referenz_kreise.csv` wird aus dem Gemeindeverzeichnis (Destatis, Kreise nach Fläche und Bevölkerung, Stand 31.12.2024) erzeugt statt aus GENESIS 12411-0015, also aus einer unabhängigen Quelle.

Nicht enthalten: Tableau-Adapter, Rahmencheck, Umschlüsselung bei Gebietsreformen, Zugriff auf die Regionaldatenbank per Token.

## Capabilities

### New Capabilities
- `file-source`: Abruf von Dateien per URL inklusive bedingtem Download, Formaten CSV/XLSX/ZIP und Höflichkeit gegenüber dem Server.
- `cleanup-rules`: deklarative Bereinigung amtlicher Tabellen in ein Langformat über Regeln in `config/bereinigung/`, inklusive Namenszuordnung.
- `manual-import`: Einspielen lokal vorliegender Dateien unter einer konfigurierten Quell-ID.

### Modified Capabilities
- `source-detection`: Datei-Links werden angenommen; die Meldung zur Regionaldatenbank verweist auf den nun vorhandenen Befehl `import`.
- `fetch-interface`: Optionen `--sheet`, `--member`, Befehl `import`; Auflisten von Blättern und ZIP-Inhalten.
- `change-cache`: HTTP 304 und gleiche Prüfsumme bei Dateien bzw. Importen gelten als unverändert; `meta.json` nennt bei Importen den Dateinamen.

## Impact

- Neuer Code: `adapters/file.py`, `cleanup.py`, Protokoll in `adapters/__init__.py`, Umbau von `core.fetch` auf das Protokoll, `cli` (import, --sheet, --member), robots-Prüfung in `http`.
- Neue Abhängigkeit: `openpyxl`.
- Neue Dateien: `config/bereinigung/*.yaml`, Fixtures (gekürzte Kreisliste als XLSX, CSV mit deutschem Zahlenformat, ZIP).
- Konfiguration: `bewegungen_kreise` mit `adapter: import`; neue Quelle `gv_kreise` (Gemeindeverzeichnis: Fläche, Bevölkerung, Dichte je Kreis; Rolle `kontext`).
- **Voraussetzung vom Nutzer:** eine im Browser geladene Datei der Regionaldatenbank (z. B. 12613-01-01-4 als CSV) für die Regel `bewegungen_kreise`, und der Download-Link der Bayern-Prognose, falls sie in diesem Change aktiviert werden soll.
