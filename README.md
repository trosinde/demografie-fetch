# demografie-fetch

**URL rein, Tabelle je Kreis raus.** `demografie-fetch` holt amtliche Demografiedaten für die Immobilien-Ampel Deutschland. Du gibst die URL einer Tabelle an. Die Komponente erkennt die Quelle, übernimmt die Werte exakt (ohne Rundung oder Schätzung) und schreibt ein Langformat (Parquet) für die Pipeline und eine breite Tabelle je Kreis (CSV). Ein Cache sorgt dafür, dass nur geladen wird, was sich an der Quelle geändert hat.

- [Schnellstart](#schnellstart)
- [Wie verwende ich die Komponente?](#wie-verwende-ich-die-komponente)
- [So funktioniert es](#so-funktioniert-es)
- [Was kommt heraus?](#was-kommt-heraus)
- [Quellen](#quellen)
- [Neue Quelle eintragen](#neue-quelle-eintragen)
- [Nachschlagen](#nachschlagen): Optionen, Cache, Ablage, Exit-Codes, Entwicklung

## Schnellstart

```bash
git clone https://github.com/trosinde/demografie-fetch.git && cd demografie-fetch
uv sync
uv run demografie-fetch "https://genesis.destatis.de/datenbank/online/statistic/12411/table/12411-0017" --startyear 2024
```

Ausgabe beim ersten Aufruf:

```
bevoelkerung_kreise_alter: neu  Tabelle 12411-0017  Stand 2026-09-21T09:08:47.596Z  17172 Zeilen
  parquet: data/staging/bevoelkerung_kreise_alter.parquet
  raw: data/raw/bevoelkerung_kreise_alter/20261024T132850Z_9762087d
  wide_csv: data/staging/bevoelkerung_kreise_alter_kreise.csv
  Kreise: Referenz 400, 2 Zeitpunkte, 0 mit Abweichung
Manifest: runs/20261024T132854Z/manifest_demografie.json
```

Derselbe Aufruf gleich danach lädt nichts, sondern meldet `cache`. Nach Ablauf des Prüfintervalls kommt `unveraendert`, solange Destatis die Tabelle nicht geändert hat.

Die Quell-ID `bevoelkerung_kreise_alter` stammt aus `config/sources_demografie.yaml`, weil die URL dort eingetragen ist. Für andere URLs bildet die Komponente eine ID aus dem Tabellencode, z. B. `destatis_12411_0015`.

## Wie verwende ich die Komponente?

### 1. Kommandozeile: eine Tabelle holen

```bash
# Erst ansehen, was drin ist (lädt keine Daten, schreibt nichts)
demografie-fetch "<url>" --list

# Holen, mit Auswahl
demografie-fetch "<url>" --startyear 2012 --select ALTX20=ALT000B03,ALT003B06

# Altersgruppe als Zeile statt als Spalte in der CSV
demografie-fetch "<url>" --wide zeit,altx20

# URL zeigt nur auf eine Statistik: Tabellen werden gelistet (Exit 2), dann wählen
demografie-fetch "https://genesis.destatis.de/datenbank/online/statistic/12411"
demografie-fetch "https://genesis.destatis.de/datenbank/online/statistic/12411" --table 12411-0017
```

### 2. Python, z. B. im Notebook

```python
from demografie_fetch import fetch

r = fetch("https://genesis.destatis.de/datenbank/online/statistic/12411/table/12411-0017",
          startyear=2024)
r.meta["status"]   # "neu", "unveraendert" oder "cache"
r.long_df          # Langformat, 17.172 Zeilen x 14 Spalten
r.wide_df          # je Kreis und Stichtag eine Zeile: 800 x 21
r.paths            # {"parquet": ..., "wide_csv": ..., "raw": ...}
```

Wiederholte Aufrufe im Notebook kommen innerhalb von 6 Stunden ohne Netzwerkzugriff aus dem Cache. Fehler werden als Ausnahmen gemeldet (`InputError`, `UnsupportedSourceError`, `BlockedError`, `FormatError`), jede mit `exit_code`.

### 3. Pipeline: alle Quellen aus der Konfiguration

```bash
demografie-fetch run                               # alle Quellen mit aktiv: true
demografie-fetch run --only kbv16_laender --force  # eine Quelle, ohne Änderungsprüfung
demografie-fetch check                             # antwortet die Schnittstelle?
```

`run` ruft die Quellen nacheinander ab. Scheitert eine, laufen die anderen weiter. Das Ergebnis jeder Quelle steht in `runs/<UTC>/manifest_demografie.json`.

In **DVC** als erste Stufe:

```yaml
stages:
  demografie_fetch:
    cmd: demografie-fetch run --max-age 0
    deps:
      - config/sources_demografie.yaml
    outs:
      - data/staging/kbv16_laender.parquet:
          persist: true
      - data/staging/bevoelkerung_kreise_alter.parquet:
          persist: true
    always_changed: true
  ampel_kontext:
    cmd: python pipeline/kontext.py
    deps:
      - data/staging/bevoelkerung_kreise_alter.parquet
    outs:
      - data/features/kontext.parquet
```

`always_changed: true` lässt die erste Stufe bei jedem `dvc repro` prüfen. Unveränderte Quellen fassen das Parquet nicht an, sein Hash bleibt gleich, und die Folgestufen rechnen nur bei echten Änderungen neu.

In **GitHub Actions** läuft `run` monatlich (Workflow `monthly`). Der Cache unter `data/` wird zwischen den Läufen aufbewahrt, Manifest und Tabellen kommen als Artefakt.

## So funktioniert es

### Bausteine

```mermaid
flowchart LR
    user(["Nutzer / DVC / Notebook"])
    subgraph pkg[demografie_fetch]
        cli["cli<br/>demografie-fetch"]
        api["core.fetch / core.run"]
        detect["detect<br/>URL → Quelle"]
        config["config<br/>sources_demografie.yaml"]
        cache["cache<br/>_state.json, Prüflogik"]
        genesis["adapters/genesis<br/>Würfel → Langformat"]
        http["http<br/>≥1 s, Backoff"]
        output["output<br/>Breitformat, Vollständigkeit"]
        store["store<br/>Ablage, Rollentrennung"]
    end
    destatis[("GENESIS-Online<br/>Destatis")]
    files[("data/raw · data/staging<br/>data/validation · runs/")]

    user --> cli --> api
    user -->|Python| api
    api --> detect
    api --> config
    api --> cache
    api --> genesis --> http --> destatis
    api --> output
    cache --> store
    output --> store
    api --> store --> files
```

### Ablauf eines Abrufs mit Cache

```mermaid
sequenceDiagram
    autonumber
    actor N as Nutzer
    participant F as fetch()
    participant D as detect
    participant C as Cache (_state.json)
    participant G as Destatis-Schnittstelle
    participant S as Ablage

    N->>F: fetch(url, Optionen)
    F->>D: Quelle erkennen
    alt nicht Destatis oder unbekannt
        D-->>N: Fehler, Exit 2 (mit Hinweis)
    else nur Statistik, kein --table
        F->>G: GET statistics/{code}/tables
        F-->>N: Tabellenliste, Exit 2
    end
    F->>C: Zustand lesen
    alt Stufe 1: geprüft innerhalb max_age, Auswahl gleich, Parquet da
        F->>S: Parquet lesen
        F-->>N: status = cache (keine Anfrage)
    else
        F->>G: GET tables/{code}/structure
        alt Stufe 2: lastChange unverändert
            opt Auswahl geändert oder Parquet fehlt
                F->>S: Tabellen aus letzter Rohfassung neu bauen
            end
            F->>C: checked_at aktualisieren
            F-->>N: status = unveraendert
        else Stand neu oder --force
            F->>G: GET tables/{code}/data, qualitySigns
            F->>F: SHA-256 der Rohdaten
            alt Stufe 3: Prüfsumme gleich
                F->>C: Stand aktualisieren (keine neue Rohfassung)
                F-->>N: status = unveraendert
            else Inhalt neu
                F->>F: Format prüfen (Zellen = Produkt der Dimensionen)
                F->>S: data/raw/{id}/{UTC}_{sha8}/ anlegen
                F->>S: Parquet + CSV atomar ersetzen
                F->>C: Zustand speichern
                F-->>N: status = neu
            end
        end
    end
```

Weitere Diagramme (Ablauf von `run`, Datenfluss) stehen in [`openspec/changes/archive/2026-10-24-add-genesis-adapter/design.md`](openspec/changes/archive/2026-10-24-add-genesis-adapter/design.md), die Zugangsprüfung in [`openspec/changes/archive/2026-10-24-add-access-probe/design.md`](openspec/changes/archive/2026-10-24-add-access-probe/design.md).

## Was kommt heraus?

**Langformat** (`data/staging/<quelle_id>.parquet`), eine Zeile je Zelle der Quelltabelle:

| quelle_id | tabelle | zeit | ags5 | altx20_code | altx20_label | kreise_code | kreise_label | merkmal_code | merkmal_label | einheit | wert | sonderzeichen | qualitaet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bevoelkerung_kreise_alter | 12411-0017 | 2025-12-31 | 08111 | ALT000B03 | unter 3 Jahre | 08111 | Stuttgart, kreisfreie Stadt | BEVSTD | Bevölkerungsstand | Anzahl | 15099.0 | | e |

- `ags5` ist ein 5-stelliger Text mit führender Null, `land` ein 2-stelliger.
- Amtliche Sonderzeichen (`-`, `.`, `...`, `/`, `x`) lassen `wert` leer und stehen in `sonderzeichen`.
- Kennzeichen wie `p` (vorläufig), `r`, `s` oder `e` stehen in `qualitaet`.
- In den Parquet-Metadaten stehen Quelle, Stand, Lizenz (`dl-de/by-2-0`) und SHA-256 der Rohfassung.

**Breite Tabelle je Kreis** (`data/staging/<quelle_id>_kreise.csv`), eine Zeile je Kreis und Stichtag, eine Spalte je Merkmal und Altersgruppe:

```
ags5,kreise_label,zeit,BEVSTD__ALT000B03,BEVSTD__ALT003B06,BEVSTD__ALT006B10,...
08111,"Stuttgart, kreisfreie Stadt",2025-12-31,15099.0,15839.0,21613.0,...
```

Welche Dimensionen Zeilen bleiben, steuert `--wide` (Standard: `zeit`).

**Manifest** (`runs/<UTC>/manifest_demografie.json`): je Quelle der Status (`neu`, `unveraendert`, `cache`, `fehler`), Stand, Prüfsumme, Zeilen, Pfade, die Vollständigkeit je Stichtag gegen die 400 Kreise und gegebenenfalls ein Hinweis `veraltet`.

## Quellen

| Quelle | Beispiel | Status | Weg |
|---|---|---|---|
| GENESIS-Online (Destatis) | 12421-0004 Bevölkerungsvorausberechnung (Länder), 12411-0017 Bevölkerung nach Kreisen und Altersgruppen | **unterstützt**, auch aus CI | öffentliche Schnittstelle der Web-Oberfläche, ohne Token |
| Regionaldatenbank | 12612/12613/12711 Geburten, Sterbefälle, Wanderungen je Kreis | **gesperrt** ohne Token | erkannt, Exit 2; geplant: `import` einer im Browser geladenen Datei (`add-file-and-import`) |
| BBSR-Tableau | Raumordnungsprognose 2045 | **geplant**, aus CI gesperrt (403) | `add-tableau-adapter`, Tableau-URL fehlt noch |
| Dateien (CSV, XLSX, ZIP) | Länderprognosen, Zensus 2022 | **geplant** | `add-file-and-import` |

Wie die Zugänge geprüft wurden, steht in [`docs/zugangsbericht.md`](docs/zugangsbericht.md). Die Prüfung lässt sich mit `uv run python probe/access_probe.py` lokal und über den Workflow `access-probe` in CI wiederholen.

Die Destatis-Schnittstelle ist nicht dokumentiert. Ändert sich ihr Format, schlägt die Quelle mit „Antwortformat unerwartet“ fehl, und das bisherige Parquet bleibt erhalten. Daten: © Statistisches Bundesamt (Destatis), Datenlizenz Deutschland – Namensnennung 2.0.

## Neue Quelle eintragen

In `config/sources_demografie.yaml`:

```yaml
sources:
  - id: bevoelkerung_kreise_geschlecht       # frei wählbar, wird Dateiname
    url: https://genesis.destatis.de/datenbank/online/statistic/12411/table/12411-0018
    rolle: kontext                           # rahmen | kontext | validierung
    auswahl: {startyear: "2012"}             # optional, auch Dimensionen: {GES: "GESM,GESW"}
    wide: zeit                               # optional, Standard zeit
    pruef_intervall_stunden: 6               # optional
    max_alter_monate: 24                     # optional, Hinweis "veraltet" im Manifest
    zugang: A-cloud                          # aus dem Zugangsbericht
    aktiv: true
```

Danach `demografie-fetch run --only bevoelkerung_kreise_geschlecht`. Welche Tabellen es gibt, zeigt `demografie-fetch "<statistik-url>"`; Tabellen mit Kreisebene sind mit `[Kreise]` markiert.

Quellen mit `rolle: validierung` werden nur unter `data/validation/` abgelegt und von keinem anderen Teil gelesen.

## Nachschlagen

### Optionen

| Option | Bedeutung |
|---|---|
| `--list` | nur Struktur anzeigen |
| `--table CODE` | Tabelle wählen (bei Statistik-URL) |
| `--startyear J`, `--endyear J` | Zeitraum |
| `--select DIM=W1,W2` | Werte einer Dimension, mehrfach möglich |
| `--role rahmen\|kontext\|validierung` | Rolle für eine freie URL |
| `--wide DIMS` | Dimensionen, die in der CSV Zeilen bleiben |
| `--max-age H` | Prüfintervall in Stunden, `0` = immer prüfen |
| `--force` | ohne Änderungsprüfung neu laden |
| `--data-dir PFAD` | Basis für `data/` und `runs/` (auch `DEMOGRAFIE_DATA_DIR`) |
| `--config DATEI` | andere Quellenkonfiguration |
| `-v` | ausführliche Meldungen |

### Cache

| Stufe | Bedingung | Netzwerk | Ergebnis |
|---|---|---|---|
| 1 Prüfintervall | letzte Prüfung jünger als `--max-age` (Standard 6 h) | keins | `cache` |
| 2 Stand | `lastChange` der Tabelle unverändert | nur Metadaten (klein) | `unveraendert`, Parquet unberührt |
| 3 Prüfsumme | Daten geladen, SHA-256 gleich der letzten Fassung | Daten | `unveraendert`, keine neue Rohfassung |
| neu | Inhalt geändert | Daten | neue Rohfassung, Tabellen neu |

Eine geänderte Auswahl baut die Tabellen aus der letzten Rohfassung neu, ohne erneuten Download. `--force` lädt immer, legt aber keine doppelte Rohfassung an. Rohfassungen werden nie überschrieben.

### Ablage

```
config/sources_demografie.yaml          Quellen
config/referenz_kreise.csv              400 Kreise, Gebietsstand 31.12.2024
data/raw/<quelle_id>/<UTC>_<sha8>/      data.json, structure.json, qualitySigns.json, meta.json
data/raw/<quelle_id>/_state.json        Stand, Prüfsumme, letzte Prüfung
data/staging/<quelle_id>.parquet        Langformat
data/staging/<quelle_id>_kreise.csv     breite Tabelle je Kreis
data/validation/<quelle_id>.parquet     nur Rolle validierung
runs/<UTC>/manifest_demografie.json     Ergebnis je Lauf
```

### Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | alle Quellen neu, unverändert oder aus dem Cache |
| 1 | Teilfehler: mindestens eine Quelle gescheitert, mindestens eine ok |
| 2 | Abbruch: Eingabe unklar, Quelle gesperrt oder nicht unterstützt, alle Quellen gescheitert |

### Entwicklung

Änderungen laufen über [OpenSpec](https://github.com/Fission-AI/OpenSpec): Vorschlag (`/opsx:propose`), Freigabe, Umsetzung (`/opsx:apply`), PR, Archiv. Die gültige Spezifikation steht in [`openspec/specs/`](openspec/specs/), offene Changes unter `openspec/changes/`, abgeschlossene mit Design und Diagrammen unter `openspec/changes/archive/`.

```bash
uv run pytest              # ohne Netzwerk
uv run pytest -m live      # gegen Destatis
uv run ruff check src tests probe && uv run mypy src tests probe
```

Lizenz: MIT · Änderungen: [CHANGELOG.md](CHANGELOG.md)
