# Spec Delta

## Purpose

Bezieht amtliche Tabellen, die als Datei (CSV, XLSX oder ZIP) über einen direkten Link veröffentlicht sind, lädt sie nur bei Änderung und behandelt den Server rücksichtsvoll.

## ADDED Requirements

### Requirement: Bedingter Download
Das System SHALL beim erneuten Abruf einer Datei-Quelle die beim letzten Download erhaltenen Werte von `ETag` und `Last-Modified` als `If-None-Match` bzw. `If-Modified-Since` mitsenden. Antwortet der Server mit HTTP 304, SHALL die Quelle als unverändert gelten. Liefert der Server keine dieser Angaben, SHALL die SHA-256-Prüfsumme der Datei entscheiden.

#### Scenario: Server meldet 304
- **WHEN** eine Datei-Quelle nach Ablauf des Prüfintervalls erneut abgerufen wird und der Server mit HTTP 304 antwortet
- **THEN** wird keine Datei übertragen, keine neue Rohfassung geschrieben, das Parquet nicht angefasst, und der Status lautet `unveraendert`

#### Scenario: Server ohne ETag und Last-Modified
- **WHEN** der Server weder `ETag` noch `Last-Modified` sendet
- **THEN** wird die Datei geladen und nur bei abweichender Prüfsumme als neue Fassung abgelegt

### Requirement: Formate
Das System SHALL CSV-, XLSX- und ZIP-Dateien lesen. Enthält eine XLSX-Datei mehrere Blätter oder eine ZIP-Datei mehrere Dateien, SHALL das System das zu lesende Blatt bzw. die zu lesende Datei aus der Bereinigungsregel, aus `--sheet` bzw. `--member` oder, falls nur ein Kandidat mit Daten existiert, eindeutig bestimmen; sonst SHALL es die Kandidaten auflisten und mit Exit-Code 2 abbrechen.

#### Scenario: Mehrere Blätter ohne Wahl
- **WHEN** eine XLSX-Datei mit den Blättern „Deckblatt“ und „Kreisfreie Städte u. Landkreise“ ohne Regel und ohne `--sheet` abgerufen wird
- **THEN** listet das System beide Blätter mit Zeilen- und Spaltenzahl und endet mit Exit-Code 2

#### Scenario: ZIP mit Wahl
- **WHEN** eine ZIP-Datei mit `--member daten.csv` abgerufen wird
- **THEN** wird nur `daten.csv` aus dem Archiv gelesen; die Rohfassung enthält das unveränderte ZIP

### Requirement: Rücksicht auf den Server
Das System SHALL vor dem ersten Abruf eines Hosts dessen `robots.txt` lesen, Pfade unter `Disallow` für den eigenen User-Agent nicht abrufen und einen dort angegebenen `Crawl-delay` als Mindestabstand zwischen Anfragen an diesen Host einhalten (mindestens 1 Sekunde). Fehlt `robots.txt` (HTTP 404), gelten keine Einschränkungen.

#### Scenario: Gesperrter Pfad
- **WHEN** die Datei-URL unter einem `Disallow`-Pfad liegt
- **THEN** wird sie nicht abgerufen, und die Quelle endet mit Exit-Code 2 und dem Hinweis, die Datei über `import` einzuspielen

#### Scenario: Crawl-delay
- **WHEN** `robots.txt` von destatis.de `Crawl-delay: 30` angibt
- **THEN** liegen zwischen zwei Anfragen an diesen Host mindestens 30 Sekunden

### Requirement: Nur über Regel ins Langformat
Das System SHALL eine Datei nur über eine Bereinigungsregel in das Langformat überführen. Ist für eine Datei-Quelle keine Regel konfiguriert, SHALL es die Rohfassung ablegen, den Aufbau (Blätter, erste Zeilen) melden und mit Exit-Code 2 abbrechen, statt Spalten zu raten.

#### Scenario: Datei ohne Regel
- **WHEN** eine neue Datei-URL ohne Regel abgerufen wird
- **THEN** liegt die Rohfassung unter `data/raw/`, die Ausgabe zeigt Blätter und Kopfzeilen, kein Parquet wird geschrieben, Exit-Code 2
