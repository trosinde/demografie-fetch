"""Lauf, Manifest, Exit-Codes, Rollen, CLI (Pflichtfaelle 5 und 10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from demografie_fetch import cli, core, fetch
from demografie_fetch.errors import InputError
from tests.conftest import BASE, URL_0017, routes_0017


def _cfg(tmp: Path, body: str) -> Path:
    p = tmp / "sources.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def test_statistik_ohne_table(tmp_path: Path, make_http, empty_config: Path) -> None:  # type: ignore[no-untyped-def]
    http, t = make_http(routes_0017())
    url = "https://genesis.destatis.de/datenbank/online/statistic/12411"
    with pytest.raises(InputError, match="12411-0017") as e:
        fetch(url, data_dir=tmp_path, config=empty_config, http=http)
    assert e.value.exit_code == 2 and "[Kreise]" in str(e.value)
    assert t.count("/data") == 0
    r = fetch(url, table="12411-0017", data_dir=tmp_path, config=empty_config, http=http)
    assert r.meta["tabelle"] == "12411-0017"
    with pytest.raises(InputError, match="gehoert nicht"):
        fetch(url, table="12421-0004", data_dir=tmp_path, config=empty_config, http=http)


def test_quell_id_aus_konfiguration(tmp_path: Path, make_http) -> None:  # type: ignore[no-untyped-def]
    cfg = _cfg(tmp_path, f"sources:\n  - id: kreise_alter\n    url: {URL_0017}\n"
                         "    rolle: kontext\n    aktiv: true\n")
    http, _ = make_http(routes_0017())
    r = fetch(URL_0017, data_dir=tmp_path, config=cfg, http=http)
    assert r.meta["quelle_id"] == "kreise_alter"
    assert (tmp_path / "data/staging/kreise_alter.parquet").exists()


def test_10_rollentrennung(tmp_path: Path, make_http) -> None:  # type: ignore[no-untyped-def]
    cfg = _cfg(tmp_path, f"sources:\n  - id: val\n    url: {URL_0017}\n"
                         "    rolle: validierung\n    aktiv: true\n")
    http, _ = make_http(routes_0017())
    fetch(URL_0017, data_dir=tmp_path, config=cfg, http=http)
    assert (tmp_path / "data/validation/val.parquet").exists()
    staging = tmp_path / "data/staging"
    assert not staging.exists() or not any(staging.iterdir())


def test_10_validation_nur_in_store() -> None:
    src = Path(__file__).resolve().parents[1] / "src" / "demografie_fetch"
    treffer = [p.name for p in src.rglob("*.py") if '"validation"' in p.read_text()
               or "data/validation" in p.read_text()]
    assert treffer == ["store.py"]


def test_5_teilfehler_ohne_abbruch(tmp_path: Path, make_http) -> None:  # type: ignore[no-untyped-def]
    cfg = _cfg(tmp_path, f"""sources:
  - id: gut
    url: {URL_0017}
    aktiv: true
  - id: gesperrt
    url: https://genesis.destatis.de/datenbank/online/statistic/12421/table/12421-0004
    aktiv: true
  - id: regio
    url: https://www.regionalstatistik.de/link/statistikInfo/12711
    aktiv: true
  - id: inaktiv
    url: https://example.org
    aktiv: false
""")
    routes = routes_0017()
    routes[BASE + "tables/12421-0004/structure"] = (403, b"")
    http, _ = make_http(routes)
    code, path, entries = core.run(data_dir=tmp_path, config=cfg, http=http)
    st = {e["quelle_id"]: e["status"] for e in entries}
    assert st == {"gut": "neu", "gesperrt": "fehler", "regio": "fehler"}
    assert code == 1
    m = json.loads(path.read_text())
    assert m["exit_code"] == 1
    fehler = {e["quelle_id"]: e["fehler"] for e in m["quellen"] if e["status"] == "fehler"}
    assert "403" in fehler["gesperrt"] and "import" in fehler["regio"]


def test_alle_fehlgeschlagen_exit_2() -> None:
    assert core.exit_code([{"status": "fehler"}]) == 2
    assert core.exit_code([{"status": "neu"}, {"status": "unveraendert"}]) == 0


def test_veraltet(tmp_path: Path, make_http) -> None:  # type: ignore[no-untyped-def]
    cfg = _cfg(tmp_path, f"sources:\n  - id: alt\n    url: {URL_0017}\n"
                         "    max_alter_monate: 1\n    aktiv: true\n")
    http, _ = make_http(routes_0017(stand="2020-01-01T00:00:00Z"))
    r = fetch(URL_0017, data_dir=tmp_path, config=cfg, http=http)
    assert r.meta["veraltet"]["max"] == 1 and r.meta["veraltet"]["alter_monate"] > 60


def test_cli_unbekannte_url(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["https://example.org/x"]) == 2
    assert "nicht erkannt" in capsys.readouterr().err


def test_cli_statistik_exit_2(monkeypatch: pytest.MonkeyPatch, make_http,  # type: ignore[no-untyped-def]
                              tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    http, _ = make_http(routes_0017())
    monkeypatch.setattr(core, "PoliteSession", lambda: http)
    rc = cli.main(["https://genesis.destatis.de/datenbank/online/statistic/12411",
                   "--data-dir", str(tmp_path), "--config", str(tmp_path / "none.yaml")])
    assert rc == 2 and "--table" in capsys.readouterr().err


def test_cli_fetch_und_list(monkeypatch: pytest.MonkeyPatch, make_http,  # type: ignore[no-untyped-def]
                            tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    http, _ = make_http(routes_0017())
    monkeypatch.setattr(core, "PoliteSession", lambda: http)
    args = [URL_0017, "--data-dir", str(tmp_path), "--config", str(tmp_path / "none.yaml")]
    assert cli.main(args + ["--list"]) == 0
    out = capsys.readouterr().out
    assert "KREISE" in out and "BEVSTD" in out and not (tmp_path / "data").exists()
    assert cli.main(args + ["--wide", "zeit,altx20"]) == 0
    out = capsys.readouterr().out
    assert "neu" in out and "Manifest" in out
    csv = (tmp_path / "data/staging/destatis_12411_0017_kreise.csv").read_text()
    assert csv.splitlines()[0] == "ags5,kreise_label,zeit,altx20_code,BEVSTD"
    assert cli.main(args) == 0  # andere --wide-Auswahl: Neuaufbau ohne Download
    assert "unveraendert" in capsys.readouterr().out
    assert cli.main(args) == 0
    assert "cache" in capsys.readouterr().out
    assert cli.main(["check"]) == 0
