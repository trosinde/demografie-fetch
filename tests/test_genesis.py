from __future__ import annotations

import json

import numpy as np
import pytest

from demografie_fetch.adapters.genesis import TableInfo, apply_selection, cube_to_long
from demografie_fetch.errors import FormatError, InputError
from tests.conftest import fixture_bytes


def _long() -> tuple[object, TableInfo]:
    info = TableInfo.from_structure(json.loads(fixture_bytes(
        "genesis_12411-0017_structure.json")))
    df = cube_to_long(fixture_bytes("genesis_12411-0017_data.json"), info,
                      fixture_bytes("genesis_12411-0017_qualitySigns.json"), "q")
    return df, info


def test_alle_zellen_exakt() -> None:
    df, _ = _long()
    raw = json.loads(fixture_bytes("genesis_12411-0017_data.json"))["data"][0]
    assert len(df) == int(np.prod(raw["size"]))  # type: ignore[arg-type]
    erste = df.iloc[0]  # type: ignore[attr-defined]
    assert erste["wert"] == raw["value"][0] == 2264.0


def test_spalten_und_labels() -> None:
    df, _ = _long()
    cols = list(df.columns)  # type: ignore[attr-defined]
    for c in ("quelle_id", "tabelle", "zeit", "ags5", "kreise_code", "kreise_label",
              "altx20_code", "altx20_label", "merkmal_code", "merkmal_label", "einheit",
              "wert", "sonderzeichen", "qualitaet"):
        assert c in cols
    row = df[df["ags5"] == "08111"].iloc[0]  # type: ignore[index]
    assert row["kreise_label"].startswith("Stuttgart")
    assert row["merkmal_code"] == "BEVSTD"
    assert row["einheit"] == "Anzahl"


def test_sonderzeichen_und_qualitaet() -> None:
    df, _ = _long()
    assert df.iloc[1]["qualitaet"] == "p" and df.iloc[1]["wert"] == 17988.0  # type: ignore
    assert df.iloc[2]["sonderzeichen"] == "." and np.isnan(df.iloc[2]["wert"])  # type: ignore
    strich = df[df["sonderzeichen"] == "-"]  # type: ignore[index]
    assert len(strich) > 0 and strich["wert"].isna().all()


def test_auswahl() -> None:
    df, _ = _long()
    sel = apply_selection(df, {"startyear": "2020"})  # type: ignore[arg-type]
    assert set(sel["zeit"].astype(str)) == {"2024-12-31"}
    sel = apply_selection(df, {"ALTX20": "%TOTAL%"})  # type: ignore[arg-type]
    assert set(sel["altx20_code"].astype(str)) == {"%TOTAL%"}
    with pytest.raises(InputError, match="gueltig"):
        apply_selection(df, {"ALTX20": "ALT999"})  # type: ignore[arg-type]
    with pytest.raises(InputError, match="Unbekannte Dimension"):
        apply_selection(df, {"FOO": "x"})  # type: ignore[arg-type]


def test_unvollstaendige_antwort() -> None:
    _, info = _long()
    raw = json.loads(fixture_bytes("genesis_12411-0017_data.json"))
    raw["data"][0]["value"] = raw["data"][0]["value"][:-1]
    with pytest.raises(FormatError, match="erwartet"):
        cube_to_long(json.dumps(raw).encode(), info, None, "q")
    with pytest.raises(FormatError):
        cube_to_long(b'{"foo": 1}', info, None, "q")
