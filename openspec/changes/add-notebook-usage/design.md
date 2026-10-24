# Design

## Context

Siehe proposal.md. Befund vom 24.10.2026: Das mit `uv build` gebaute Wheel enthält nur `src/demografie_fetch/**/*.py`. Installiert in eine frische Umgebung und außerhalb des Repos aufgerufen, liefert `fetch()` die Daten korrekt, aber `vollstaendigkeit = {"fehler": "Referenzliste config/referenz_kreise.csv fehlt"}`. `run()` findet ohne `config/sources_demografie.yaml` im Arbeitsverzeichnis keine Quellen.

Zielumgebung laut Nutzer: lokales Jupyter (JupyterLab oder VS Code), Installation aus dem dann öffentlichen GitHub-Repo.

## Architektur und Abläufe

### Bausteine

```mermaid
flowchart LR
    subgraph nb["Jupyter-Notebook (lokal)"]
        cell1["%pip install git+…@v0.2.0"]
        cell2["from demografie_fetch import fetch, run"]
    end
    gh[("GitHub-Repo, öffentlich<br/>Tag v0.2.0")]
    subgraph pkg["installiertes Paket demografie_fetch"]
        api["fetch · run · list_source"]
        res["data/<br/>referenz_kreise.csv<br/>sources_demografie.yaml"]
        lookup["Ressourcen-Suche<br/>Projekt vor Paket"]
    end
    proj[("Notebook-Ordner<br/>config/ (optional)<br/>data/ · runs/")]
    destatis[("GENESIS-Online")]

    cell1 --> gh --> pkg
    cell2 --> api
    api --> lookup
    lookup --> proj
    lookup --> res
    api --> destatis
    api --> proj
```

### Installation und erster Abruf im Notebook

```mermaid
sequenceDiagram
    autonumber
    actor N as Nutzer
    participant K as Jupyter-Kernel
    participant G as GitHub
    participant P as demografie_fetch
    participant D as Destatis

    N->>K: %pip install "git+https://github.com/trosinde/demografie-fetch.git@v0.2.0"
    K->>G: Quellstand zum Tag holen (ohne Zugangsdaten)
    alt Python < 3.11
        K-->>N: Abbruch: requires-python >= 3.11
    else
        K->>K: Paket bauen und installieren (inkl. data/)
        K-->>N: installiert, kein Neustart nötig
    end
    N->>P: r = fetch(url, startyear=2024)
    P->>P: Referenzliste suchen: ./config, sonst Paket
    P->>D: structure, data (siehe Cache-Ablauf)
    P-->>N: FetchResult als HTML-Zusammenfassung
    N->>P: r.wide_df, r.long_df
    N->>P: fetch(url, startyear=2024)
    P-->>N: status cache, keine Anfrage
```

### Ressourcen-Suche

```mermaid
sequenceDiagram
    participant F as fetch / run
    participant W as Arbeitsverzeichnis
    participant R as Paketdaten
    F->>W: config/sources_demografie.yaml bzw. config/referenz_kreise.csv?
    alt vorhanden
        W-->>F: Projektdatei (Vorrang)
    else
        F->>R: importlib.resources demografie_fetch/data/...
        R-->>F: mitgelieferte Fassung
    end
    F->>F: Herkunft im Manifest vermerken (projekt oder paket)
```

### Notebook in CI

```mermaid
sequenceDiagram
    participant A as GitHub Actions (notebook)
    participant V as frische venv
    participant J as nbclient
    participant D as Destatis
    A->>A: uv build (Wheel)
    A->>V: Wheel und ipykernel installieren
    A->>J: notebooks/schnellstart.ipynb ausführen (Installationszelle übersprungen)
    J->>D: kleine Tabelle 12411-0015 ab 2024
    alt Zelle wirft Fehler
        J-->>A: Workflow rot
    else
        J-->>A: Workflow grün, ausgeführtes Notebook als Artefakt
    end
```

## Goals / Non-Goals

**Goals:**
- Eine Installationszelle und ein `import` genügen für alle Funktionen.
- Das Beispiel-Notebook ist durch CI abgesichert und veraltet nicht still.

**Non-Goals:**
- Kein PyPI-Paket, keine Colab- oder JupyterHub-Anpassungen.
- Keine Diagramme oder Karten im Paket (keine Abhängigkeit von matplotlib); das Notebook nutzt nur pandas.
- Keine Fortschrittsbalken; Meldungen über `logging`.

## Decisions

- **Paketdaten unter `src/demografie_fetch/data/`**, gelesen mit `importlib.resources.files`. Hatchling nimmt Nicht-Python-Dateien im Paketordner automatisch ins Wheel auf; ein Test prüft das am gebauten Wheel. `config/referenz_kreise.csv` bleibt im Repo als Projektdatei; ein Test stellt sicher, dass beide Fassungen identisch sind. Alternative „nur im Paket“ verworfen: Dann ließe sich die Liste im Projekt nicht übersteuern.
- **Suchreihenfolge** für Konfiguration und Referenzliste: expliziter Parameter, dann `./config/…`, dann Paket. Die Herkunft steht im Manifest (`konfiguration: projekt|paket|<pfad>`).
- **Installation per Git-Tag** statt Branch, damit ein Notebook reproduzierbar dieselbe Version nutzt. `%pip` (nicht `!pip`) installiert in die Umgebung des laufenden Kernels.
- **`RunResult` als `NamedTuple`** mit zusätzlicher Methode `to_frame()`. Bestehender Code mit `code, path, entries = run(...)` funktioniert weiter.
- **`FetchResult._repr_html_`** und `__repr__` geben eine kompakte Tabelle aus. Die Datenrahmen bleiben über `long_df` und `wide_df` erreichbar.
- **CI-Workflow `notebook.yml`** für Pull Requests und Pushes auf `main`, die `src/`, `notebooks/` oder `pyproject.toml` ändern. Er baut das Wheel, installiert es mit `ipykernel` und `nbclient` in eine frische venv und führt das Notebook aus. Die Installationszelle trägt den Tag `skip-ci` und wird übersprungen, weil das Wheel des aktuellen Stands getestet werden soll und nicht der letzte Tag. Abgerufen wird nur eine kleine Tabelle (12411-0015 ab 2024, rund 200 kB).
- **Veröffentlichung des Repos (Entscheidungspunkt).** Die Prüfung vom 24.10.2026 ergab:
  - Die Commit-Historie nennt die private Mailadresse als Autor.
  - `docs/zugangsbericht.md` und `probe/report_local.json` nennen Anbieter und Region des Privatanschlusses.
  - Keine Tokens, keine lokalen Pfade, keine IP-Adressen.

  Optionen:
  - (a) so veröffentlichen.
  - (b) Anbieter und Region in beiden Dateien auf „Privatanschluss, DE“ kürzen. Die Historie enthält sie weiterhin.
  - (c) wie (b), dazu die Historie vor der Veröffentlichung neu schreiben, sodass Anbieter, Region und Mailadresse auch in alten Commits fehlen (Force-Push auf `main`, alte PR-Verweise zeigen dann auf andere Commits).

  Empfehlung: (b), und für künftige Commits die GitHub-noreply-Adresse verwenden. Die Mailadresse ist in Commits üblich; Anbieter und Region sind für den Bericht unwichtig. Die Sichtbarkeit wird erst nach der Freigabe in Aufgabe 4.2 umgestellt.

## Risks / Trade-offs

- [Öffentliches Repo macht die Nutzung der nicht dokumentierten Destatis-Schnittstelle sichtbar] → README nennt die Schnittstelle bereits offen, die Kennung ist ehrlich, die Last gering; das ändert sich nicht.
- [Notebook-Test in CI hängt von Destatis ab] → kleine Tabelle; schlägt Destatis fehl, ist der Workflow rot, aber getrennt vom Workflow `ci`.
- [Doppelte Referenzliste (Projekt und Paket)] → Test auf Gleichheit.

## Migration Plan

Keine Datenmigration. Nach dem Merge: Tag `v0.2.0` setzen, danach erst Installation im Notebook mit diesem Tag. Rückweg: Repo wieder privat stellen (Installationen per Git ohne Zugangsdaten schlagen dann fehl).
