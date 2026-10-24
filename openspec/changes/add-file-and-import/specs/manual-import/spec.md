# Spec Delta

## Purpose

Erlaubt es, Dateien von Quellen ohne automatischen Zugang (z. B. Regionaldatenbank) im Browser zu laden und mit gleicher Ablage, Prüfung und Bereinigung wie einen Download einzuspielen.

## ADDED Requirements

### Requirement: Datei einspielen
Das System SHALL mit `demografie-fetch import <quelle_id> <datei>` eine lokale Datei einer in `config/sources_demografie.yaml` eingetragenen Quelle einspielen: Prüfsumme bilden, bei neuem Inhalt als Rohfassung ablegen, über die Regel der Quelle bereinigen und die Tabellen schreiben. Die Originaldatei SHALL unverändert bleiben.

#### Scenario: Erster Import
- **WHEN** `demografie-fetch import bewegungen_kreise ~/Downloads/12613-01-01-4.csv` läuft
- **THEN** liegt die Datei unverändert unter `data/raw/bewegungen_kreise/<UTC>_<sha8>/`, Parquet und CSV entstehen, Status `neu`, Exit-Code 0

#### Scenario: Gleiche Datei erneut
- **WHEN** dieselbe Datei noch einmal importiert wird
- **THEN** entsteht keine neue Rohfassung, das Parquet bleibt unberührt, Status `unveraendert`

### Requirement: Nur konfigurierte Quellen
Das System SHALL einen Import nur für Quellen-IDs annehmen, die in der Konfiguration stehen und eine Bereinigungsregel haben; sonst SHALL es mit Exit-Code 2 und einer Meldung abbrechen, die einen passenden Konfigurationseintrag zeigt.

#### Scenario: Unbekannte Quelle
- **WHEN** `demografie-fetch import unbekannt datei.csv` läuft
- **THEN** endet das System mit Exit-Code 2 und einem Beispiel für den Eintrag in der Konfiguration

### Requirement: Manuelle Quellen im Lauf
Das System SHALL Quellen mit `adapter: import` bei `demografie-fetch run` nicht abrufen, sondern im Manifest mit Status `manuell`, dem Stand des letzten Imports und, falls `max_alter_monate` überschritten ist, dem Hinweis `veraltet` führen. Eine manuelle Quelle ohne bisherigen Import SHALL den Lauf nicht als fehlgeschlagen werten.

#### Scenario: Monatlicher Lauf
- **WHEN** `run` läuft und `bewegungen_kreise` zuletzt vor 14 Monaten importiert wurde, bei `max_alter_monate: 12`
- **THEN** steht `bewegungen_kreise` mit Status `manuell` und Hinweis `veraltet` im Manifest, und der Exit-Code hängt nur von den übrigen Quellen ab
