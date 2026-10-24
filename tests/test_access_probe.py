"""Tests fuer probe/access_probe.py ohne Netzwerk."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("access_probe", ROOT / "probe" / "access_probe.py")
assert _spec and _spec.loader
ap = importlib.util.module_from_spec(_spec)
sys.modules["access_probe"] = ap
_spec.loader.exec_module(ap)


def test_testauswahl_je_quelltyp() -> None:
    g = {"id": "a", "url": "https://genesis.destatis.de/datenbank/online/statistic/12421/table/12421-0004"}
    r = {"id": "b", "url": "https://www.regionalstatistik.de/link/statistikInfo/12711"}
    t = {"id": "c", "url": "https://tableau.bbsr.bund.de/views/x/y", "adapter": "tableau"}
    f = {"id": "d", "url": "https://example.org/a.xlsx", "adapter": "file"}
    assert ap.plan_tests(g) == ["T1", "T2", "T6", "T7"]
    assert ap.plan_tests(r) == ["T1", "T2", "T6", "T7"]
    assert ap.plan_tests(t) == ["T1", "T2", "T3", "T4", "T5"]
    assert ap.plan_tests(f) == ["T1", "T2", "T8"]
    assert ap.source_kind({"url": "https://example.org/page"}) == "unbekannt"


def test_code_aus_url() -> None:
    assert ap.extract_code(
        "https://genesis.destatis.de/datenbank/online/statistic/12421/table/12421-0004"
    ) == ("12421-0004", "12421")
    assert ap.extract_code(
        "https://www.regionalstatistik.de/genesis/online?sequenz=tabelleErgebnis"
        "&selectionname=12411-03-03-4"
    ) == ("12411-03-03-4", "12411")
    assert ap.extract_code("https://www.regionalstatistik.de/link/statistikInfo/12711") == (
        None,
        "12711",
    )
    assert ap.genesis_db("https://www.regionalstatistik.de/x") == "regio"
    assert ap.genesis_db("https://genesis.destatis.de/x") == "genesis"


def test_maskierung() -> None:
    assert ap.excerpt("token=ABC123 ok", ["ABC123"]) == "token=*** ok"
    assert len(ap.excerpt("x" * 1000, [])) == ap.EXCERPT_CHARS
    assert ap.excerpt("a\nb\nc\nd", [], lines=3) == "a\nb\nc"


def _t(**st: str) -> dict[str, object]:
    return {k: ap.TestResult(k, v) for k, v in st.items()}


def test_klassen() -> None:
    assert ap.classify(_t(T2="ok"), "ci")[0] == "A-cloud"
    assert ap.classify(_t(T4="ok"), "local")[0] == "A-lokal"
    assert ap.classify(_t(T3="ok", T4="gescheitert"), "ci")[0] == "A-lokal"
    assert ap.classify(_t(T2="erreichbar", T5="ok"), "local")[0] == "A-browser"
    assert ap.classify(_t(T2="gescheitert", T5="gescheitert"), "local")[0] == "B-manuell"
    assert ap.classify(_t(T6="kein_token", T7="kein_token"), "ci")[0] == "nicht_pruefbar"
    assert ap.classify(_t(T6="ok", T7="ok"), "ci")[0] == "A-cloud"


def test_fehlende_url_ohne_anfrage() -> None:
    p = ap.Prober("local", pause=0)
    rep = p.probe_source({"id": "x", "url": "", "adapter": "file"})
    assert rep.klasse == "nicht_pruefbar"
    assert all(t.status in ("nicht_pruefbar", "nicht_anwendbar") for t in rep.tests.values())


def test_einbettungsseite_wird_nicht_bedient() -> None:
    p = ap.Prober("local", pause=0)
    src = {"id": "x", "url": "https://www.bbsr.bund.de/x.html", "adapter": "tableau"}
    rep = p.probe_source(src)
    assert rep.klasse == "nicht_pruefbar"
    assert "Einbettungsseite" in (rep.grund or "")


def test_pause_zwischen_anfragen() -> None:
    slept: list[float] = []
    p = ap.Prober("local", pause=2.0, sleep=slept.append)
    p.wait()
    p.wait()
    assert slept and slept[0] > 1.9


def test_login_erkennung() -> None:
    assert ap.looks_like_login("https://x/auth/login?redirect=1")
    assert not ap.looks_like_login("https://tableau.bbsr.bund.de/views/a/b")
    assert ap.looks_like_csv("a,b\n1,2")
    assert not ap.looks_like_csv("<html><body>")
