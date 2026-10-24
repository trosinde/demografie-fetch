# Zugangsbericht (Schritt 0)

Stand: 2026-10-24. Skript: `probe/access_probe.py`. Rohdaten: `probe/report_local.json`, `probe/report_ci.json`.

| Lauf | Netz | Zeit (UTC) | Tokens |
|---|---|---|---|
| lokal | Privatanschluss, DE | 2026-10-24 12:36 | keine |
| CI | US, California, AS8075 Microsoft (GitHub-Runner `ubuntu-latest`) | 2026-10-24 12:40 | keine (Secrets nicht gesetzt) |

Legende: `ok` = Daten bzw. positiver Nachweis, `erreichbar` = Server antwortet, aber ohne Daten, `kein_token` = ohne Token nicht entscheidbar, `–` = nicht anwendbar.

## kbv16_laender (GENESIS Destatis, 12421-0004, Rolle rahmen)

| Test | lokal | CI | Auszug |
|---|---|---|---|
| T1 robots.txt | 404 | 404 | Keine robots.txt vorhanden, also keine Sperre. |
| T2 Quell-URL | 200 erreichbar | 200 erreichbar | Gibt HTML zurück (Single-Page-App), keine Daten. Das ist erwartet. |
| T6 logincheck | 200 kein_token | 200 kein_token | Ohne Token meldet die API eine Gast-Anmeldung (Username `GA…`). Die API ist erreichbar, Basis-URL `https://genesis.destatis.de/genesisWS/rest/2020/` bestätigt. |
| T7 Katalog | 401 kein_token | 401 kein_token | Code 15: Ohne Anmeldung nicht berechtigt. |

**Bewertung:** Die API antwortet aus beiden Netzen gleich, ein Filter nach Herkunft ist nicht zu sehen. Der Datenzugriff ist erst mit `GENESIS_TOKEN` belegt.
**Vorschlag:** A-cloud (vorläufig, Bestätigung mit Token ausstehend) · Adapter ja (`add-genesis-adapter`) · Zeitplan CI monatlich.

## bevoelkerung_kreise_alter (Regionaldatenbank, 12411-03-03-4, Rolle kontext)

| Test | lokal | CI | Auszug |
|---|---|---|---|
| T1 robots.txt | 200 | 200 | **`User-agent: *` / `Disallow: /`** |
| T2 Quell-URL | 200 erreichbar | 200 erreichbar | Gibt HTML zurück. |
| T6 logincheck | 200 kein_token | 200 kein_token | Gast-Anmeldung. Basis-URL `https://www.regionalstatistik.de/genesisws/rest/2020/` bestätigt. |
| T7 Katalog | 401 kein_token | 401 kein_token | Code 15 (nicht berechtigt). Ob der Code 12411-03-03-4 noch existiert, ist ohne Token offen. |

**Bewertung:** Wie bei Destatis kein Filter nach Herkunft. Allerdings sperrt robots.txt den ganzen Host für Crawler. Ein Adapter darf deshalb **nur die dokumentierte REST-API** mit eigenem Token nutzen und keine HTML-Seiten abrufen. Das ist API-Nutzung im Rahmen der Registrierung, kein Crawling. Bitte trotzdem bewusst freigeben.
**Vorschlag:** A-cloud (vorläufig, mit Token zu bestätigen) · Adapter ja (über `genesis` mit Datenbank `regio`) · CI monatlich · Tabellencode mit Token über den Katalog bestätigen.

## bewegungen_kreise (Regionaldatenbank, Statistik 12711, Rolle kontext)

Testergebnisse wie bei `bevoelkerung_kreise_alter`. Bei T7 lautete die Auswahl `12711*`, weil die URL nur auf eine Statistik zeigt. Der Katalog mit Token wird mehrere Tabellen liefern, dann ist die Wahl über `--table` nötig.
**Vorschlag:** A-cloud (vorläufig) · Adapter ja · CI monatlich · Tabelle nach Katalogabfrage festlegen.

## bbsr_rop2045 (Tableau, Rolle kontext)

| Test | lokal | CI | Auszug |
|---|---|---|---|
| T1 robots.txt (Host `tableau.bbsr.bund.de`) | **404** (Seite „Page Not Found“, Server antwortet) | **403** (CloudFront: „The request could not be satisfied“) | |
| T2–T5 | nicht prüfbar | nicht prüfbar | Die Tableau-URL fehlt in der Konfiguration. |

**Bewertung:** Der Filter nach Herkunft ist bestätigt. Mit identischer Anfrage ohne besondere Header antwortet der Server lokal normal und blockt aus der Microsoft-Cloud mit 403 (CloudFront). Ob nach Land (US) oder nach Rechenzentrum gefiltert wird, lässt sich mit diesem Test nicht trennen. Aus CI ist die Quelle jedenfalls nicht erreichbar. Ob Export (T4) oder Datenmodell (T5) lokal funktionieren, bleibt offen, bis die URL eingetragen ist.
**Vorschlag:** höchstens A-lokal bzw. A-browser, sonst B-manuell · Adapter erst nach lokaler Prüfung mit der echten URL · kein CI-Zeitplan.

## laenderprognose_bayern (Datei, Rolle validierung)

Nicht prüfbar, weil der Download-Link fehlt. Keine Anfrage gestellt.
**Vorschlag:** offen. Landesämter liefern XLSX meist direkt, dann wäre A-cloud mit `file`-Adapter wahrscheinlich.

## Gesamtbild und offene Punkte

1. **Tokens fehlen** lokal und als Secret. Ohne `GENESIS_TOKEN`/`REGIO_TOKEN` sind T6/T7 nicht entscheidbar. Bitte lokal exportieren und mit `gh secret set GENESIS_TOKEN` / `gh secret set REGIO_TOKEN` hinterlegen, danach Probe erneut laufen lassen.
2. **Tableau-URL der ROP 2045** (`https://tableau.bbsr.bund.de/views/...`) eintragen. Getestet wird nur die eingetragene URL.
3. **Download-Link Bayern-Prognose** eintragen.
4. **Regionaldatenbank robots.txt `Disallow: /`**: Freigabe, dass der Adapter ausschliesslich die REST-API mit Token nutzt.

## Nachtrag 2026-10-24: Zugang ohne API-Key (Web-Frontend)

Ein API-Key ist nicht zu bekommen, und der dokumentierte Gastzugang (`GAST`/`GAST`) liefert bei beiden Datenbanken 401. Deshalb habe ich geprüft, was die öffentliche Webseite ohne Anmeldung lädt.

**GENESIS Destatis:** Das Frontend `genesis.destatis.de/datenbank/online` lädt die Tabellen ohne Anmeldung über eine interne REST-Schnittstelle. Es gibt keine robots.txt, keinen Login und keinen Zustimmungsdialog. Die Abrufe kamen vom lokalen Rechner, ohne besondere Header:

| Endpunkt (GET, Basis `https://genesis.destatis.de/genesis/api/rest/`) | Inhalt |
|---|---|
| `tables/<code>/data` | alle Werte als JSON-stat-artiges Datenwürfel-Objekt (`id`, `size`, `dimension`, `value`, `status`) |
| `tables/<code>/structure` | Metadaten inkl. `lastChange` (für die Änderungsprüfung; kein ETag) |
| `tables/<code>/qualitySigns` | Bedeutung der Sonderzeichen |
| `statistics/<code>/tables` | Tabellen einer Statistik inkl. `locationVariableCodes` (z. B. `KREISE`) |

Befunde:
- **12421-0004:** 200, 17,8 MB, 2.026.944 Werte (3 Geschlechter × 9 Varianten × 16 Länder × 46 Stichtage 2025–2070 × 102 Altersjahre). Vollständig, nicht auf 900 Zeilen gekürzt wie die Ansicht. Werte in 1000, mit einer Nachkommastelle, also der veröffentlichten Genauigkeit.
- **12411-0017 (Bevölkerung: Kreise, Stichtag, Altersgruppen; 18 Gruppen):** 2,9 MB, Stichtage 1995–2025. Kreise mit Wert: 402 (2011–2015), 401 (2016–2020), **400 (ab 2021)**. Das passt zu den Gebietsreformen. Dazu gibt es 12411-0015, -0016 und -0018 (mit Geschlecht).
- **Geburten, Sterbefälle, Wanderungen (12612, 12613, 12711):** Bei Destatis keine Tabelle auf Kreisebene, die gibt es nur in der Regionaldatenbank.
- **Risiko:** Die Schnittstelle ist intern und nicht dokumentiert, Format und Pfade können sich ohne Ankündigung ändern. Last: Ein Abruf entspricht einem Seitenaufruf, bei monatlichem Lauf vernachlässigbar.

**Regionaldatenbank:** Das Gastkonto ist gesperrt, und robots.txt setzt `Disallow: /`. Die HTML-Seiten habe ich deshalb nicht abgefragt. Ohne Token bleibt dort nur der manuelle Weg (`import`).
