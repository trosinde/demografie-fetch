# access-probe Specification

## Purpose
Stellt vor dem Bau eines Adapters fest, ob die Daten jeder konfigurierten Quelle per URL abrufbar sind, und ordnet jede Quelle einer Zugangsklasse zu.

## Requirements

### Requirement: Quellen aus der Konfiguration prüfen
Das System SHALL alle Quellen aus `config/sources_demografie.yaml` prüfen und je Quelle anhand von Host und Adapter die passenden Tests T1–T8 auswählen.

#### Scenario: Tests nach Quelltyp
- **WHEN** eine Quelle auf `genesis.destatis.de` oder `regionalstatistik.de` zeigt
- **THEN** werden T1, T2, T6 und T7 ausgeführt und T3–T5 sowie T8 als „nicht anwendbar“ markiert

#### Scenario: Tableau-Quelle
- **WHEN** eine Quelle den Adapter `tableau` hat oder auf `tableau.bbsr.bund.de` zeigt
- **THEN** werden T1 bis T5 ausgeführt

#### Scenario: Datei-Quelle
- **WHEN** eine Quelle den Adapter `file` hat
- **THEN** werden T1, T2 und T8 ausgeführt

### Requirement: Fehlende URL
Das System SHALL eine Quelle ohne URL als „nicht prüfbar“ markieren und keine Anfrage für sie stellen.

#### Scenario: Leere URL
- **WHEN** das Feld `url` einer Quelle leer ist
- **THEN** steht die Quelle im Bericht mit Status `nicht_pruefbar` und dem Hinweis, dass die URL nachzutragen ist

### Requirement: Höfliche, lesende Prüfung
Das System SHALL je Test höchstens eine Anfrage stellen, zwischen zwei Anfragen mindestens 2 Sekunden warten und nur lesende Methoden verwenden (GET, HEAD; bei GENESIS das von der API vorgeschriebene POST auf Lese-Endpunkte).

#### Scenario: Pause zwischen Anfragen
- **WHEN** zwei Tests nacheinander laufen
- **THEN** liegen zwischen den Anfragen mindestens 2 Sekunden

### Requirement: Keine Umgehung von Sperren
Das System SHALL NOT Logins, CAPTCHAs, Zustimmungsdialoge oder Sperren umgehen; ein Test, der nur so zum Ziel käme, gilt als gescheitert.

#### Scenario: Weiterleitung auf Login
- **WHEN** eine Anfrage auf eine Anmelde- oder Zustimmungsseite weitergeleitet wird
- **THEN** wird der Test als gescheitert mit Grund `login_oder_zustimmung` gewertet und nicht weiter verfolgt

#### Scenario: Einbettungsseite statt Tableau-URL
- **WHEN** die konfigurierte Tableau-URL auf `bbsr.bund.de` statt auf den Tableau-Server zeigt
- **THEN** wird die Seite nicht automatisiert bedient, und der Bericht nennt den Grund

### Requirement: Token-Schutz
Das System SHALL Tokens nur aus Umgebungsvariablen lesen und SHALL NOT Tokens oder personenbezogene Daten in Berichte oder Logs schreiben.

#### Scenario: Token in Antwort
- **WHEN** eine Antwort den Token-Wert enthält
- **THEN** wird er im Auszug durch `***` ersetzt

#### Scenario: Token fehlt
- **WHEN** die Umgebungsvariable für eine Datenbank fehlt
- **THEN** wird T6 ohne Anmeldung ausgeführt, als `kein_token` gekennzeichnet und T7 nicht als Erfolg gewertet

### Requirement: Maschinenlesbarer Bericht
Das System SHALL einen JSON-Bericht schreiben, der je Quelle und Test Status, HTTP-Code, Dauer, Weiterleitungsziel und einen gekürzten Auszug enthält, dazu Laufumgebung (lokal/CI) und Zeitstempel.

#### Scenario: Lokaler Lauf
- **WHEN** das Skript ohne `--env` auf einem Rechner läuft
- **THEN** entsteht `probe/report_local.json`

#### Scenario: CI-Lauf
- **WHEN** das Skript in GitHub Actions läuft
- **THEN** entsteht `probe/report_ci.json` und wird als Artefakt hochgeladen

### Requirement: Vorläufige Zugangsklasse
Das System SHALL je Quelle aus den Testergebnissen eine vorläufige Zugangsklasse ableiten: `A-cloud`, `A-lokal`, `A-browser`, `B-manuell` oder `nicht_pruefbar`.

#### Scenario: Daten über einfache Anfrage
- **WHEN** T2, T4, T6/T7 oder T8 Daten liefern
- **THEN** lautet die Klasse für diese Umgebung `A-cloud`, falls der Lauf aus CI kommt, sonst `A-lokal` bis zum Abgleich mit CI

#### Scenario: Nur Browser
- **WHEN** nur T5 Daten liefert
- **THEN** lautet die Klasse `A-browser`

#### Scenario: Alles gescheitert
- **WHEN** alle anwendbaren Tests scheitern
- **THEN** lautet die Klasse `B-manuell`
