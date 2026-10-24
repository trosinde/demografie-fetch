# Proposal

## Why

Die README zeigt nur eine Beispielzeile des Langformats und eine CSV-Zeile. Wer die Komponente im Notebook oder in der Pipeline nutzt, muss wissen, welche Spalten zurückkommen, was sie bedeuten und welchen Typ sie haben. Heute steht das nur verstreut in den Specs (`table-output`) und im Code.

## What Changes

- README, Abschnitt „Was kommt heraus?“: Tabelle aller Spalten des Langformats (Name, Typ, Beispiel, Erklärung), inklusive der quellabhängigen Spalten `<dim>_code`/`<dim>_label` mit Beispielen für Kreis- und Länderebene.
- Tabelle der breiten Tabelle je Kreis (Zeilen- und Spaltenaufbau, Spaltennamen).
- Tabelle der Felder von `FetchResult` (`long_df`, `wide_df`, `meta`, `paths`) mit den Schlüsseln von `meta` und `paths`, dazu `RunResult.to_frame()`.
- Tabelle der amtlichen Zeichen in `sonderzeichen` und `qualitaet` mit ihrer Bedeutung laut GENESIS-Online.
- Ein Strukturdiagramm des Rückgabeobjekts.

Keine Änderung an Code oder Verhalten.

## Capabilities

### New Capabilities
- keine

### Modified Capabilities
- keine (reine Dokumentation, `skip_specs: true`)

## Impact

- Nur `README.md`. Grundlage sind die Specs `table-output` und `fetch-interface` sowie eine Prüfung der tatsächlichen Rückgabe am 24.10.2026 (12411-0017 Kreisebene, 12421-0004 Länderebene).
