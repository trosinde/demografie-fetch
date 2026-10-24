# Changelog

## 0.1.0 – 2026-10-24

- Zugangsprüfung (`probe/access_probe.py`, Workflow `access-probe`, `docs/zugangsbericht.md`).
- Paket `demografie_fetch` mit CLI `demografie-fetch` und API `fetch()`.
- Adapter `genesis` für GENESIS-Online (Destatis) über die öffentliche Schnittstelle der Web-Oberfläche, ohne Token.
- Cache in drei Stufen (Prüfintervall, `lastChange`, SHA-256), versionierte Rohablage.
- Langformat (Parquet), breite Tabelle je Kreis (CSV), Manifest, Vollständigkeit gegen 400 Kreise, Rollentrennung.
- Workflows `ci` (Lint, Typen, Tests) und `monthly` (Abruf mit Cache, Manifest als Artefakt).
