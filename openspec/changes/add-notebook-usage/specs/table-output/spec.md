# Spec Delta

## MODIFIED Requirements

### Requirement: Vollständigkeit auf Kreisebene
Das System SHALL für Quellen mit Kreisebene je Zeitpunkt die Kreise mit Wert gegen eine Referenzliste (400 Kreise, Gebietsstand 31.12.2024) prüfen und fehlende sowie überzählige Schlüssel im Manifest nennen. Die Referenzliste SHALL aus `config/referenz_kreise.csv` im Arbeitsverzeichnis gelesen werden, falls vorhanden, sonst aus der im Paket mitgelieferten Fassung. Die Prüfung SHALL das Ergebnis nicht verändern und den Lauf nicht abbrechen.

#### Scenario: Aktueller Gebietsstand
- **WHEN** 12411-0017 für den Stichtag 2024-12-31 vorliegt
- **THEN** meldet das Manifest 400 Kreise ohne Abweichung

#### Scenario: Älterer Gebietsstand
- **WHEN** für 2015-12-31 402 Kreise vorliegen
- **THEN** nennt das Manifest die zwei überzähligen und ggf. fehlenden Schlüssel für diesen Zeitpunkt

#### Scenario: Installiertes Paket ohne Projektordner
- **WHEN** das Arbeitsverzeichnis keine `config/referenz_kreise.csv` enthält
- **THEN** wird die mitgelieferte Referenzliste verwendet, und `vollstaendigkeit` enthält kein Feld `fehler`
