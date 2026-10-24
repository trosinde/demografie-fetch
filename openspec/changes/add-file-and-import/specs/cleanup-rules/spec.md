# Spec Delta

## Purpose

Überführt amtliche Tabellen mit mehrzeiligen Köpfen, Fußnoten, Zwischen- und Summenzeilen über deklarative Regeln in das einheitliche Langformat, ohne Code je Quelle und ohne Werte zu verändern.

## ADDED Requirements

### Requirement: Regeln in der Konfiguration
Das System SHALL Bereinigungsregeln als YAML-Dateien unter `config/bereinigung/<regel>.yaml` lesen, die eine Quelle über das Feld `bereinigung: <regel>` referenziert, und SHALL NOT quellspezifische Bereinigung im Code enthalten.

#### Scenario: Ungültige Regel
- **WHEN** eine Regel eine Spalte nennt, die in der Datei nicht vorkommt
- **THEN** schlägt die Quelle mit einer Meldung fehl, die die vorhandenen Spaltenköpfe nennt, und es wird kein Parquet geschrieben

### Requirement: Inhalt einer Regel
Eine Regel SHALL festlegen können: Blatt bzw. ZIP-Datei, Kodierung und Trennzeichen (CSV), Kopfzeilen, erste Datenzeile, Schlüssel- oder Namensspalte mit Ebene, Zeit, Dimensionsspalten und Merkmalsspalten mit Code, Label und Einheit.

#### Scenario: Zeit aus der Titelzeile
- **WHEN** die Regel die Zeit per Muster aus der Titelzeile „… am 31.12.2024 (Jahr)“ liest
- **THEN** steht in `zeit` der Wert `2024-12-31`

#### Scenario: Jahre als Spalten
- **WHEN** eine Prognosetabelle die Jahre als Spalten führt und die Regel sie als Dimension `zeit` ausweist
- **THEN** entsteht je Kreis und Jahr eine Zeile im Langformat

### Requirement: Mehrzeilige Köpfe und Fußnotenzeichen
Das System SHALL mehrere Kopfzeilen spaltenweise zu einem Spaltenkopf verbinden, verbundene Zellen nach rechts fortschreiben und Fußnotenzeichen (hochgestellte Ziffern mit `)` bzw. `⁾`, Sternchen) sowie überzählige Leerzeichen vor dem Vergleich mit der Regel entfernen.

#### Scenario: Kopf mit Fußnote
- **WHEN** der Spaltenkopf ` Fläche km² ¹⁾` lautet und die Regel die Spalte `Fläche km²` nennt
- **THEN** wird die Spalte zugeordnet

### Requirement: Zwischen- und Summenzeilen
Das System SHALL nur Zeilen übernehmen, deren Schlüssel der in der Regel genannten Ebene entspricht (bzw. deren Name eindeutig zugeordnet werden kann). Zeilen für Länder, Regierungsbezirke, Summen, Quellenangaben und Fußnoten SHALL verworfen werden; ihre Anzahl SHALL im Manifest stehen.

#### Scenario: Kreisliste des Gemeindeverzeichnisses
- **WHEN** die Kreisliste von Destatis (Stand 31.12.2024) mit Ebene `kreis` bereinigt wird
- **THEN** enthält das Ergebnis genau 400 Kreise, und Länder-, Bezirks-, Summen- und Fußnotenzeilen fehlen

### Requirement: Werte unverändert übernehmen
Das System SHALL Zahlen aus Zellen ohne Genauigkeitsverlust übernehmen: Zahlenzellen direkt, Textzellen über die deutsche Schreibweise (Dezimalkomma, Tausenderpunkt). Amtliche Sonderzeichen SHALL zu leerem `wert` mit Eintrag in `sonderzeichen`, angehängte Kennzeichen (`p`, `r`, `s`, `e`) in `qualitaet` führen. Eine Zelle, die keine Zahl und kein bekanntes Zeichen ist, SHALL die Quelle mit Angabe von Zeile und Spalte fehlschlagen lassen.

#### Scenario: Text mit deutscher Zahl
- **WHEN** eine CSV-Zelle `1.234,5` enthält
- **THEN** ist `wert` exakt 1234.5

#### Scenario: Unbekannter Zellinhalt
- **WHEN** eine Merkmalszelle `k. A.` enthält
- **THEN** schlägt die Quelle mit der Fundstelle fehl

### Requirement: Zuordnung über Namen
Das System SHALL, wenn eine Regel statt eines Schlüssels eine Namensspalte nennt, Namen über die Referenzliste `config/referenz_kreise.csv` dem Schlüssel zuordnen. Verglichen wird nach Vereinheitlichung (Groß-/Kleinschreibung, Leerzeichen, Zusätze wie „, Stadt“ oder „kreisfreie Stadt“). Nur eindeutige Treffer SHALL zugeordnet werden; nicht oder mehrdeutig zuordenbare Namen SHALL im Manifest gemeldet und nicht übernommen werden. Das System SHALL NOT raten.

#### Scenario: Mehrdeutiger Name
- **WHEN** eine Zeile „Rosenheim“ ohne Zusatz enthält und sowohl die kreisfreie Stadt als auch der Landkreis in Frage kommen
- **THEN** wird die Zeile nicht übernommen, und das Manifest nennt den Namen mit beiden Kandidaten

### Requirement: Ausgabe wie bei anderen Adaptern
Das System SHALL bereinigte Dateien in dasselbe Langformat, dieselbe breite Tabelle je Kreis, dieselbe Vollständigkeitsprüfung und dieselbe Rollentrennung überführen wie Tabellen aus GENESIS-Online. `tabelle` SHALL den Namen der Regel tragen.

#### Scenario: Kreisliste
- **WHEN** die Quelle `gv_kreise` abgerufen wird
- **THEN** entstehen `data/staging/gv_kreise.parquet` mit den Merkmalen Fläche, Bevölkerung (insgesamt, männlich, weiblich) und Dichte sowie `data/staging/gv_kreise_kreise.csv`, und die Vollständigkeit meldet 400 Kreise ohne Abweichung
