# Spec Delta

## Purpose

Leitet aus einer einzigen URL ab, welcher Adapter, welche Datenbank und welche Tabelle gemeint sind, und bricht bei unklaren oder nicht unterstützten Eingaben mit einer klaren Meldung ab, statt zu raten.

## ADDED Requirements

### Requirement: Destatis-Tabellen-URL erkennen
Das System SHALL eine URL auf `genesis.destatis.de` oder `www-genesis.destatis.de`, die einen Tabellencode (Muster `NNNNN-NNNN` bzw. `NNNNN-NN-NN-N`) enthält, dem Adapter `genesis` mit Datenbank `destatis` und diesem Tabellencode zuordnen.

#### Scenario: Tabellen-URL der neuen Oberfläche
- **WHEN** die URL `https://genesis.destatis.de/datenbank/online/statistic/12421/table/12421-0004` übergeben wird
- **THEN** ist der Adapter `genesis`, die Datenbank `destatis` und die Tabelle `12421-0004`

#### Scenario: Tabellencode in Abfrageparametern
- **WHEN** die URL den Tabellencode in einem Parameter enthält (z. B. `...?sequenz=tabelleErgebnis&selectionname=12411-0017`)
- **THEN** wird `12411-0017` als Tabelle erkannt

### Requirement: Statistik-URL ohne Tabelle
Das System SHALL bei einer URL, die nur auf eine Statistik zeigt, die Tabellen dieser Statistik auflisten und ohne Abruf mit Exit-Code 2 abbrechen, sofern keine Tabelle per `--table` gewählt ist.

#### Scenario: Mehrere Kandidaten
- **WHEN** die URL `https://genesis.destatis.de/datenbank/online/statistic/12411` ohne `--table` übergeben wird
- **THEN** listet das System die Tabellen der Statistik 12411 mit Code und Titel, markiert solche mit Kreisebene und endet mit Exit-Code 2

#### Scenario: Wahl über --table
- **WHEN** dieselbe URL mit `--table 12411-0017` übergeben wird
- **THEN** wird Tabelle `12411-0017` abgerufen

#### Scenario: Gewählte Tabelle passt nicht zur Statistik
- **WHEN** `--table` einen Code nennt, dessen Statistikteil nicht zur URL passt
- **THEN** bricht das System mit Exit-Code 2 und einer Meldung ab

### Requirement: Erkannte, aber nicht unterstützte Quellen
Das System SHALL URLs der Regionaldatenbank (`regionalstatistik.de`), des BBSR-Tableau-Servers (`tableau.bbsr.bund.de`), BBSR-Einbettungsseiten (`bbsr.bund.de`) und direkte Datei-Links (`.csv`, `.xlsx`, `.zip`) erkennen und mit Exit-Code 2 und einer Meldung abweisen, die den Grund und den vorgesehenen Weg nennt.

#### Scenario: Regionaldatenbank
- **WHEN** eine URL auf `www.regionalstatistik.de` übergeben wird
- **THEN** meldet das System, dass die Regionaldatenbank ohne Token nicht abrufbar ist und die Quelle über `import` eingespielt wird, und endet mit Exit-Code 2

#### Scenario: Datei-Link
- **WHEN** eine URL auf eine `.xlsx`-Datei übergeben wird
- **THEN** meldet das System, dass der Datei-Adapter noch nicht verfügbar ist, und endet mit Exit-Code 2

### Requirement: Unbekannte URL
Das System SHALL für eine URL, die keinem bekannten Muster entspricht, eine klare Meldung ausgeben und mit Exit-Code 2 enden, ohne eine Anfrage zu stellen.

#### Scenario: Fremde Seite
- **WHEN** die URL `https://example.org/statistik` übergeben wird
- **THEN** endet das System mit Exit-Code 2 und der Meldung, dass die Quelle nicht erkannt wurde

### Requirement: Quell-ID
Das System SHALL für eine URL, die in `config/sources_demografie.yaml` eingetragen ist, deren `id` verwenden und sonst eine stabile ID aus Datenbank und Tabellencode bilden (z. B. `destatis_12421_0004`).

#### Scenario: URL aus der Konfiguration
- **WHEN** die URL von `kbv16_laender` übergeben wird
- **THEN** werden Ablage, Parquet und Manifest unter der ID `kbv16_laender` geführt

#### Scenario: Freie URL
- **WHEN** eine nicht konfigurierte Tabellen-URL für `12411-0015` übergeben wird
- **THEN** lautet die ID `destatis_12411_0015`
