# Spec Delta

## MODIFIED Requirements

### Requirement: Einzelabruf per URL
Das System SHALL mit `demografie-fetch "<url>" [--table CODE] [--sheet BLATT] [--member DATEI] [--startyear J] [--endyear J] [--select DIM=W1,W2] [--role ROLLE] [--wide DIMS] [--max-age H] [--force]` genau eine Quelle abrufen, die Tabellen schreiben und eine Zusammenfassung (Status, Zeilen, Pfade) ausgeben. `--sheet` und `--member` gelten nur für Datei-Quellen.

#### Scenario: Erster Abruf
- **WHEN** `demografie-fetch "<12421-0004-URL>"` zum ersten Mal läuft
- **THEN** entstehen Rohfassung, Parquet und Manifest, die Ausgabe meldet `neu`, Exit-Code 0

#### Scenario: Zweiter Abruf
- **WHEN** derselbe Aufruf erneut läuft
- **THEN** meldet die Ausgabe `cache` oder `unveraendert`, Exit-Code 0

#### Scenario: Blatt wählen
- **WHEN** eine XLSX-URL mit `--sheet "Kreisfreie Städte u. Landkreise"` übergeben wird
- **THEN** wird nur dieses Blatt gelesen

### Requirement: Auflisten
Das System SHALL mit `--list` nur die Struktur anzeigen: bei einer Statistik die Tabellen, bei einer Tabelle Titel, Stand, Dimensionen mit Anzahl und Beispielwerten, Zeitraum und Merkmale, bei einer Datei die Blätter bzw. ZIP-Inhalte mit den ersten Zeilen. Dabei SHALL es nichts unter `data/staging` oder `data/validation` schreiben.

#### Scenario: Tabelle auflisten
- **WHEN** `demografie-fetch "<12411-0017-URL>" --list` läuft
- **THEN** zeigt die Ausgabe die Dimensionen `KREISE`, `STAG`, `ALTX20` und das Merkmal `BEVSTD`, ohne Dateien zu schreiben

#### Scenario: Datei auflisten
- **WHEN** `demografie-fetch "<xlsx-URL>" --list` läuft
- **THEN** zeigt die Ausgabe je Blatt Name, Zeilen, Spalten und die ersten fünf nicht leeren Zeilen

### Requirement: Exit-Codes
Das System SHALL mit 0 enden, wenn alle Quellen neu, unverändert, aus dem Cache geliefert oder manuell (`manuell`) waren; mit 1, wenn mindestens eine Quelle fehlschlug und mindestens eine erfolgreich war; mit 2 bei unklarer Eingabe, gesperrter oder nicht unterstützter Quelle, fehlender Bereinigungsregel oder wenn alle abgerufenen Quellen fehlschlugen.

#### Scenario: Unklare Eingabe
- **WHEN** eine Statistik-URL ohne `--table` übergeben wird
- **THEN** ist der Exit-Code 2

#### Scenario: Nur manuelle Quellen ohne Fehler
- **WHEN** ein Lauf eine erfolgreiche Quelle und eine manuelle Quelle enthält
- **THEN** ist der Exit-Code 0

## ADDED Requirements

### Requirement: Import-Befehl
Das System SHALL den Befehl `demografie-fetch import <quelle_id> <datei> [--sheet BLATT] [--member DATEI] [--data-dir PFAD] [--config DATEI]` anbieten und dafür ein Manifest schreiben wie beim Einzelabruf.

#### Scenario: Import mit Manifest
- **WHEN** ein Import erfolgreich ist
- **THEN** gibt die Ausgabe Status, Zeilen und Pfade aus und nennt das Manifest
