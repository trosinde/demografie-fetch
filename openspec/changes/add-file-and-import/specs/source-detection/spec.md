# Spec Delta

## MODIFIED Requirements

### Requirement: Erkannte, aber nicht unterstützte Quellen
Das System SHALL URLs der Regionaldatenbank (`regionalstatistik.de`), des BBSR-Tableau-Servers (`tableau.bbsr.bund.de`) und BBSR-Einbettungsseiten (`bbsr.bund.de`) erkennen und mit Exit-Code 2 und einer Meldung abweisen, die den Grund und den vorgesehenen Weg nennt.

#### Scenario: Regionaldatenbank
- **WHEN** eine URL auf `www.regionalstatistik.de` übergeben wird
- **THEN** meldet das System, dass die Regionaldatenbank ohne Token nicht abrufbar ist, und zeigt den Befehl `demografie-fetch import <quelle_id> <datei>` mit dem Hinweis auf eine Bereinigungsregel; Exit-Code 2

#### Scenario: Datei-Link
- **WHEN** eine URL auf eine `.xlsx`-Datei übergeben wird
- **THEN** wird sie nicht abgewiesen, sondern dem Adapter `file` zugeordnet

#### Scenario: Tableau
- **WHEN** eine URL auf `tableau.bbsr.bund.de` übergeben wird
- **THEN** meldet das System, dass der Tableau-Adapter noch nicht verfügbar ist, und endet mit Exit-Code 2

## ADDED Requirements

### Requirement: Datei-Links erkennen
Das System SHALL eine URL, deren Pfad auf `.csv`, `.xlsx` oder `.zip` endet (Abfrageparameter wie `?__blob=publicationFile` werden ignoriert), dem Adapter `file` zuordnen; ein Eintrag `adapter: file` in der Konfiguration SHALL dies auch für andere Pfade erzwingen.

#### Scenario: Destatis-Download
- **WHEN** die URL `https://www.destatis.de/.../04-kreise.xlsx?__blob=publicationFile&v=14` übergeben wird
- **THEN** ist der Adapter `file` und das Format `xlsx`

#### Scenario: Keine Datei
- **WHEN** die URL `https://example.org/statistik.html` übergeben wird
- **THEN** wird sie nicht als Datei erkannt und mit Exit-Code 2 als unbekannt abgewiesen
