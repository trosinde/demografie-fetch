# Spec Delta

## Purpose

Bezieht Tabellen aus GENESIS-Online (Destatis) über die öffentliche Web-Schnittstelle ohne Anmeldung, exakt so, wie sie veröffentlicht sind, und schont dabei den Server.

## ADDED Requirements

### Requirement: Abruf ohne Anmeldung
Das System SHALL Tabellen ausschliesslich über die öffentlich zugängliche Schnittstelle der Web-Oberfläche von GENESIS-Online abrufen und SHALL NOT Anmeldungen, CAPTCHAs, Zustimmungsdialoge oder Sperren umgehen.

#### Scenario: Server verweigert den Zugriff
- **WHEN** die Schnittstelle mit HTTP 401 oder 403 antwortet
- **THEN** gilt die Quelle als gesperrt, es folgt kein weiterer Versuch mit anderen Kennungen, und die Meldung nennt den Statuscode

### Requirement: Exaktheit
Das System SHALL Werte nur aus der Antwort der Schnittstelle übernehmen und SHALL NOT Werte schätzen, runden, interpolieren oder aus Grafiken ablesen. Jede veröffentlichte Zelle der Tabelle SHALL genau einmal im Ergebnis stehen.

#### Scenario: Vollständiger Würfel
- **WHEN** die Tabelle 12421-0004 abgerufen wird
- **THEN** enthält das Langformat vor einer Auswahl genau so viele Zeilen, wie die Antwort Zellen hat (Produkt der Dimensionsgrössen), und jeder Wert stimmt mit dem Wert der Antwort überein

#### Scenario: Anzeige ist gekürzt
- **WHEN** die Web-Oberfläche eine Tabelle zur Ansicht kürzt
- **THEN** ist das Ergebnis trotzdem vollständig, weil nicht die Ansicht, sondern der Datenwürfel gelesen wird

### Requirement: Metadaten der Tabelle
Das System SHALL Titel, Stand (`lastChange`), Lizenz- bzw. Copyright-Angabe, Merkmale mit Einheit, Labels aller Dimensionswerte und die Bedeutung der Qualitäts- und Sonderzeichen aus der Schnittstelle übernehmen.

#### Scenario: Labels und Einheit
- **WHEN** 12421-0004 abgerufen wird
- **THEN** trägt Land `08` das Label „Baden-Württemberg“ und das Merkmal `BEV050` die Einheit `1000`

### Requirement: Auswahl
Das System SHALL die Auswahl `startyear`, `endyear` sowie Werte je Dimension (`<DIMENSION>=<wert>[,<wert>]`) aus CLI oder Konfiguration anwenden, indem es Zeilen des vollständig abgerufenen Würfels filtert, ohne Werte zu verändern.

#### Scenario: Startjahr
- **WHEN** 12411-0017 mit `startyear=2012` abgerufen wird
- **THEN** enthält das Ergebnis nur Stichtage ab dem Jahr 2012

#### Scenario: Unbekannter Dimensionswert
- **WHEN** die Auswahl einen Wert nennt, den die Tabelle nicht kennt
- **THEN** bricht das System mit Exit-Code 2 ab und nennt die gültigen Werte

### Requirement: Höflichkeit
Das System SHALL Anfragen an GENESIS-Online nacheinander stellen, mindestens 1 Sekunde Abstand zwischen zwei Anfragen halten, eine eigene User-Agent-Kennung mit Projektname senden und bei HTTP 429, 5xx oder Netzwerkfehlern höchstens dreimal mit wachsendem Abstand (Backoff) wiederholen.

#### Scenario: Vorübergehender Serverfehler
- **WHEN** die Schnittstelle zweimal mit HTTP 503 und dann mit 200 antwortet
- **THEN** ist der Abruf erfolgreich, und zwischen den Versuchen lagen wachsende Pausen

#### Scenario: Dauerhafter Fehler
- **WHEN** die Schnittstelle auch nach drei Wiederholungen mit 5xx antwortet
- **THEN** schlägt nur diese Quelle mit einer Meldung fehl

### Requirement: Formatänderung erkennen
Das System SHALL eine Antwort, deren Aufbau nicht dem erwarteten Datenwürfel entspricht (fehlende Felder, Anzahl Werte ungleich Produkt der Dimensionsgrössen), als Fehler der Quelle melden und SHALL NOT daraus ein Parquet schreiben.

#### Scenario: Unvollständige Antwort
- **WHEN** die Antwort weniger Werte enthält, als die Dimensionsgrössen verlangen
- **THEN** schlägt die Quelle mit der Meldung „Antwortformat unerwartet“ fehl, und das bestehende Parquet bleibt unverändert
