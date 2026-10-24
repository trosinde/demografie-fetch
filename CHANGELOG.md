# Changelog

## 0.2.0 – 2026-10-24

- Nutzung im Jupyter-Notebook: Installation per `%pip install git+…@v0.2.0`, Beispiel-Notebook `notebooks/schnellstart.ipynb`, Workflow `notebook` führt es aus dem gebauten Paket aus.
- Referenzliste der Kreise und Beispielkonfiguration werden im Paket mitgeliefert; Dateien unter `./config/` haben Vorrang. Behebt die fehlende Vollständigkeitsprüfung außerhalb des Repos.
- `run()` liefert `RunResult` mit `to_frame()` (weiterhin als Tupel entpackbar); `list_source` ist öffentlich; `FetchResult` zeigt im Notebook eine Zusammenfassung.
- Manifest nennt die verwendete Konfiguration, die Vollständigkeit die Herkunft der Referenzliste.

## 0.1.0 – 2026-10-24

- Zugangsprüfung (`probe/access_probe.py`, Workflow `access-probe`, `docs/zugangsbericht.md`).
- Paket `demografie_fetch` mit CLI `demografie-fetch` und API `fetch()`.
- Adapter `genesis` für GENESIS-Online (Destatis) über die öffentliche Schnittstelle der Web-Oberfläche, ohne Token.
- Cache in drei Stufen (Prüfintervall, `lastChange`, SHA-256), versionierte Rohablage.
- Langformat (Parquet), breite Tabelle je Kreis (CSV), Manifest, Vollständigkeit gegen 400 Kreise, Rollentrennung.
- Workflows `ci` (Lint, Typen, Tests) und `monthly` (Abruf mit Cache, Manifest als Artefakt).
