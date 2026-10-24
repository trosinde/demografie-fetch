# Tasks

## 1. Grundlagen

- [x] 1.1 Abhängigkeiten (`requests`, `pandas`, `pyarrow`, `PyYAML`) und Entry-Point `demografie-fetch` in `pyproject.toml`; `uv sync` und `uv run demografie-fetch --help` laufen
- [x] 1.2 `detect`: URL → Adapter/Datenbank/Tabelle/Statistik inkl. Abweisung von Regionaldatenbank, Tableau, BBSR-Einbettung, Dateien und unbekannten URLs; Quell-ID aus Konfiguration oder Code; Positiv- und Negativtests je Muster grün
- [x] 1.3 `http`: höfliche Session (Kennung, ≥1 s Abstand, Backoff bei 429/5xx/Netzwerk, keine Wiederholung bei 401/403); Tests mit gemocktem Transport grün

## 2. GENESIS-Adapter

- [x] 2.1 Fixtures aus echten Antworten (gekürzte `structure`, `data`, `qualitySigns`, `statistics/.../tables`) in `tests/fixtures/` ablegen
- [x] 2.2 Client für `structure`, `data`, `qualitySigns`, `statistics/<code>/tables`, `settings/instance`; Fehler für 401/403 und unerwartetes Format; Tests grün
- [x] 2.3 Würfel → Langformat (Codes, Labels, `zeit`, `ags5`/`land`, Merkmal/Einheit, `sonderzeichen`, `qualitaet`), Zellenzahl = Produkt der Dimensionen; Auswahl (`startyear`, `endyear`, `--select`) mit Fehler bei unbekannten Werten; Tests grün
- [x] 2.4 Zahlenparser für deutsche Schreibweise und Sonderzeichen (für spätere Datei-Quellen, im Kern); Tests: Dezimalkomma, Tausenderpunkt, Sonderzeichen, führende Null

## 3. Cache und Ablage

- [x] 3.1 `store`: Pfade je Rolle (nur hier `data/validation`), atomares Schreiben von Parquet (mit Metadaten), CSV, JSON
- [x] 3.2 `cache`: Zustand `_state.json`, Prüfintervall, `lastChange`-Vergleich, Prüfsumme, versionierte Rohfassung, Neuaufbau aus Rohfassung bei geänderter Auswahl oder fehlendem Parquet, `--force`; Pflichttests 1–4 (erster Lauf, zweiter Lauf unverändert, gleiche Prüfsumme nicht doppelt, neuer Inhalt neue Fassung) plus Prüfintervall und Auswahlwechsel grün

## 4. Ausgabe

- [x] 4.1 Breitformat je Kreis mit `--wide`; Test mit Kreis-Fixture grün
- [x] 4.2 `config/referenz_kreise.csv` (400 Kreise, Stand 31.12.2024, aus 12411-0015) erzeugen und einchecken; Vollständigkeitsprüfung je Zeitpunkt; Test grün
- [x] 4.3 Test Rollentrennung: Validierungsquelle schreibt nur nach `data/validation/`, und `data/validation` kommt im Code nur in `store` vor

## 5. Schnittstellen

- [x] 5.1 `core.fetch()` mit `FetchResult`, `core.run()` mit Fehlertoleranz, Manifest inkl. `veraltet`-Hinweis, Exit-Code-Logik; Tests: Teilfehler → 1, nicht unterstützte aktive Quelle im Manifest
- [x] 5.2 CLI (`<url>`, `--list`, `--table`, `--startyear`, `--endyear`, `--select`, `--role`, `--wide`, `--max-age`, `--force`, `--data-dir`, `run`, `run --only/--force`, `check`); Test für Statistik-URL ohne `--table` → Exit 2
- [x] 5.3 Live-Tests (`@pytest.mark.live`) für 12421-0004 und 12411-0017; lokal ausgeführt: 12421-0004 vollständig, zweiter Lauf `cache`/`unveraendert`; 12411-0017 ab 2012 mit 400 Kreisen ab 2021

## 6. Qualität und Betrieb

- [x] 6.1 `ruff check` und `mypy --strict` über `src`, `tests`, `probe` sauber
- [ ] 6.2 Workflows `ci.yml` (Lint und Tests bei Push) und `monthly.yml` (cron, `demografie-fetch run --max-age 0`, Manifest als Artefakt); `monthly` einmal per `workflow_dispatch` aus CI erfolgreich
- [x] 6.3 README (Nutzung, Cache, Grenzen, DVC-Stage mit `always_changed: true`), CHANGELOG

## Workflow follow-up

- PR `feat/add-genesis-adapter` → `main`, Review und Merge durch den Nutzer.
- Nach dem Merge `/opsx:archive add-genesis-adapter` (und `add-access-probe`).
