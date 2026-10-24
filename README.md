# demografie-fetch

Demografiedaten für die Immobilien-Ampel Deutschland: URL rein, Tabelle je Kreis raus.

Status: Schritt 0, Zugangsprüfung (`probe/access_probe.py`, Bericht in `docs/zugangsbericht.md`).

```bash
uv sync
uv run python probe/access_probe.py --dry-run   # Testplan
uv run python probe/access_probe.py             # lokal -> probe/report_local.json
```

In CI: Workflow `access-probe` (manuell starten), Ergebnis als Artefakt `report_ci`.
