# Spec Delta

## MODIFIED Requirements

### Requirement: Neue Fassung
Das System SHALL bei geändertem Inhalt eine neue Rohfassung unter `data/raw/<quelle_id>/<UTC-zeit>_<sha8>/` mit den unveränderten Antworten bzw. der unveränderten Datei und einer `meta.json` (URL bzw. bei Importen Dateiname, Tabelle bzw. Regel, Stand, `ETag`/`Last-Modified` falls vorhanden, Prüfsumme, Abrufzeit) anlegen. Bestehende Rohfassungen SHALL NOT überschrieben oder gelöscht werden.

#### Scenario: Geänderter Inhalt
- **WHEN** die Quelle neue Daten liefert
- **THEN** entsteht ein neues Verzeichnis, das vorherige bleibt unverändert erhalten, und der Status lautet `neu`

#### Scenario: Import
- **WHEN** eine Datei per `import` eingespielt wird
- **THEN** nennt `meta.json` den ursprünglichen Dateinamen und `herkunft: import`, aber keinen lokalen Pfad des Nutzers

## ADDED Requirements

### Requirement: Stand bei Dateien
Das System SHALL für Datei-Quellen `ETag` und `Last-Modified` der letzten Antwort im Zustand speichern und als Stand führen; fehlen beide, ist der Stand der Zeitpunkt des Abrufs bzw. Imports. Die Stufen Prüfintervall, Prüfsumme und Neuaufbau aus der letzten Rohfassung bei geänderter Auswahl SHALL für Dateien und Importe genauso gelten wie für GENESIS-Tabellen.

#### Scenario: Andere Regel, gleiche Datei
- **WHEN** sich nur die Bereinigungsregel einer Quelle ändert
- **THEN** werden die Tabellen aus der letzten Rohfassung neu erzeugt, ohne die Datei erneut zu laden
