# Spec Delta

## Purpose

Legt fest, in welcher Form die abgerufenen Daten an die Pipeline übergeben werden: ein einheitliches Langformat, eine breite Tabelle je Kreis, Metadaten, Vollständigkeitsprüfung und die physische Trennung der Validierungsdaten.

## ADDED Requirements

### Requirement: Langformat
Das System SHALL je Quelle ein Langformat mit den Spalten `quelle_id, tabelle, zeit, <dim>_code, <dim>_label …, merkmal_code, merkmal_label, einheit, wert, sonderzeichen, qualitaet` erzeugen und unter `data/staging/<quelle_id>.parquet` atomar ersetzen. `<dim>` ist der kleingeschriebene Dimensionscode der Quelle. Bei Kreisebene SHALL zusätzlich die Spalte `ags5`, bei Landesebene die Spalte `land` stehen.

#### Scenario: Länderprognose
- **WHEN** 12421-0004 abgerufen wird
- **THEN** hat das Parquet die Spalten `land`, `dland_code`, `dland_label`, `bevpr2_code`, `ges_code`, `alt101_code` (jeweils mit Label), `zeit` im Format `JJJJ-MM-TT`, `merkmal_code` `BEV050`, `einheit` `1000`

### Requirement: Schlüssel
Das System SHALL Kreisschlüssel als 5-stelligen Text mit führender Null (`ags5`) und Landesschlüssel als 2-stelligen Text führen.

#### Scenario: Führende Null
- **WHEN** ein Kreisschlüssel als `1001` oder Zahl `1001` vorliegt
- **THEN** steht in `ags5` der Text `01001`

### Requirement: Werte, Sonderzeichen und Qualität
Das System SHALL Werte in voller veröffentlichter Genauigkeit als Zahl übernehmen. Amtliche Sonderzeichen, die einen Wert ersetzen (`.`, `-`, `...`, `/`, `x`), SHALL zu einem leeren Wert führen und in `sonderzeichen` stehen. Kennzeichen, die einen Wert begleiten (z. B. `p`, `r`, `s`, `e`), SHALL in `qualitaet` stehen. Zahlentexte mit Dezimalkomma und Tausenderpunkt SHALL verlustfrei umgerechnet werden.

#### Scenario: Strich statt Wert
- **WHEN** eine Zelle das Zeichen `-` trägt
- **THEN** ist `wert` leer und `sonderzeichen` gleich `-`

#### Scenario: Vorläufiger Wert
- **WHEN** eine Zelle den Wert `1234.5` mit Kennzeichen `p` trägt
- **THEN** ist `wert` 1234.5 und `qualitaet` gleich `p`

#### Scenario: Deutsche Zahlschreibweise
- **WHEN** der Text `1.234.567,89` umgerechnet wird
- **THEN** ergibt sich exakt 1234567.89

### Requirement: Parquet-Metadaten
Das System SHALL Quelle (URL), Tabelle, Titel, Stand, Lizenz (`dl-de/by-2-0`), Copyright-Angabe und SHA-256 der Rohfassung in die Schlüssel-Wert-Metadaten des Parquets schreiben.

#### Scenario: Metadaten lesen
- **WHEN** das Parquet mit einem Parquet-Leser geöffnet wird
- **THEN** sind die Felder `quelle`, `tabelle`, `stand`, `lizenz` und `sha256` lesbar

### Requirement: Breite Tabelle je Kreis
Das System SHALL für Quellen mit Kreisebene eine breite Tabelle unter `data/staging/<quelle_id>_kreise.csv` schreiben: eine Zeile je `ags5` und je Kombination der Dimensionen, die per `--wide` als Zeilen bleiben (Standard: `zeit`); alle übrigen Dimensionen und das Merkmal bilden die Spalten. Leere Werte bleiben leer.

#### Scenario: Standard
- **WHEN** 12411-0017 mit Standardeinstellung abgerufen wird
- **THEN** hat die CSV eine Zeile je Kreis und Stichtag und je Altersgruppe eine Spalte

#### Scenario: Altersgruppe als Zeile
- **WHEN** `--wide zeit,altx20` gesetzt ist
- **THEN** hat die CSV eine Zeile je Kreis, Stichtag und Altersgruppe und eine Spalte je Merkmal

### Requirement: Vollständigkeit auf Kreisebene
Das System SHALL für Quellen mit Kreisebene je Zeitpunkt die Kreise mit Wert gegen die eingecheckte Referenzliste `config/referenz_kreise.csv` (400 Kreise, Gebietsstand 31.12.2024) prüfen und fehlende sowie überzählige Schlüssel im Manifest nennen. Die Prüfung SHALL das Ergebnis nicht verändern und den Lauf nicht abbrechen.

#### Scenario: Aktueller Gebietsstand
- **WHEN** 12411-0017 für den Stichtag 2024-12-31 vorliegt
- **THEN** meldet das Manifest 400 Kreise ohne Abweichung

#### Scenario: Älterer Gebietsstand
- **WHEN** für 2015-12-31 402 Kreise vorliegen
- **THEN** nennt das Manifest die zwei überzähligen und ggf. fehlenden Schlüssel für diesen Zeitpunkt

### Requirement: Rollentrennung
Das System SHALL Tabellen von Quellen mit Rolle `validierung` ausschliesslich unter `data/validation/` schreiben und SHALL NOT sie unter `data/staging/` ablegen. Kein Modul ausser der Ablage SHALL Pfade unter `data/validation/` lesen.

#### Scenario: Validierungsquelle
- **WHEN** eine Quelle mit Rolle `validierung` abgerufen wird
- **THEN** liegt das Parquet unter `data/validation/<quelle_id>.parquet`, und unter `data/staging/` gibt es keine Datei dieser Quelle

#### Scenario: Codeprüfung
- **WHEN** die Testsuite läuft
- **THEN** prüft ein Test, dass `data/validation` nur in der Ablage-Komponente vorkommt
