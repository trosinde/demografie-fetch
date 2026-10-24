"""Nutzung ausserhalb des Repos (Notebook): Paketdaten, RunResult, Darstellung."""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from demografie_fetch import RunResult, fetch, list_source, run
from demografie_fetch.config import load_sources, package_file, resolve_config
from demografie_fetch.output import load_reference, reference_source
from tests.conftest import URL_0017, routes_0017

ROOT = Path(__file__).resolve().parents[1]


def test_ohne_projektordner_gilt_paket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_config()[1] == "paket"
    assert reference_source()[1] == "paket"
    assert len(load_reference()) == 400
    assert any(s.id == "kbv16_laender" for s in load_sources())


def test_projektordner_hat_vorrang(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "config/sources_demografie.yaml").write_text(
        "sources:\n  - id: eigene\n    url: x\n", encoding="utf-8")
    (tmp_path / "config/referenz_kreise.csv").write_text("ags5,name\n01001,a\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert resolve_config()[1] == "projekt"
    assert [s.id for s in load_sources()] == ["eigene"]
    assert reference_source()[1] == "projekt" and len(load_reference()) == 1


def test_referenzliste_projekt_gleich_paket() -> None:
    assert (ROOT / "config/referenz_kreise.csv").read_bytes() == \
        package_file("referenz_kreise.csv").read_bytes()


def test_vollstaendigkeit_ohne_projektordner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,  # type: ignore[no-untyped-def]
                                             make_http) -> None:
    monkeypatch.chdir(tmp_path)
    http, _ = make_http(routes_0017())
    r = fetch(URL_0017, data_dir=tmp_path, http=http)
    voll = r.meta["vollstaendigkeit"]
    assert "fehler" not in voll and voll["referenz"] == 400
    assert voll["referenz_herkunft"] == "paket"


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv nicht verfuegbar")
def test_wheel_enthaelt_paketdaten(tmp_path: Path) -> None:
    subprocess.run(["uv", "build", "--wheel", "-q", "-o", str(tmp_path)], cwd=ROOT, check=True)
    wheel = next(tmp_path.glob("*.whl"))
    names = zipfile.ZipFile(wheel).namelist()
    assert "demografie_fetch/data/referenz_kreise.csv" in names
    assert "demografie_fetch/data/sources_demografie.yaml" in names


def test_runresult(tmp_path: Path, make_http) -> None:  # type: ignore[no-untyped-def]
    cfg = tmp_path / "s.yaml"
    cfg.write_text(f"sources:\n  - id: k\n    url: {URL_0017}\n    aktiv: true\n"
                   "  - id: r\n    url: https://www.regionalstatistik.de/x\n    aktiv: true\n",
                   encoding="utf-8")
    http, _ = make_http(routes_0017())
    res = run(data_dir=tmp_path, config=cfg, http=http)
    assert isinstance(res, RunResult)
    code, path, entries = res
    assert code == 1 and path == res.manifest_path and entries == res.entries
    df = res.to_frame()
    assert list(df.columns) == ["quelle_id", "status", "tabelle", "stand", "zeilen", "fehler"]
    assert df.set_index("quelle_id").loc["k", "status"] == "neu"
    assert "import" in str(df.set_index("quelle_id").loc["r", "fehler"])
    assert json.loads(path.read_text())["konfiguration"] == str(cfg)


def test_darstellung_ohne_datenzeilen(tmp_path: Path, make_http) -> None:  # type: ignore[no-untyped-def]
    http, _ = make_http(routes_0017())
    r = fetch(URL_0017, data_dir=tmp_path, config=tmp_path / "none.yaml", http=http)
    text, page = repr(r), r._repr_html_()
    for s in (text, page):
        assert "destatis_12411_0017" in s and "neu" in s and "12 Zeilen" in s
        assert "2264" not in s  # kein Datenwert
    assert page.startswith("<table>")


def test_list_source_exportiert(make_http, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    http, _ = make_http(routes_0017())
    assert "BEVSTD" in list_source(URL_0017, http=http)
