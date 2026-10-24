from __future__ import annotations

import pandas as pd
import pytest

from demografie_fetch.output import completeness, pad_key, parse_number, to_wide


@pytest.mark.parametrize(("text", "expected"), [
    ("1.234.567,89", (1234567.89, None, None)),
    ("12,5", (12.5, None, None)),
    ("1.234", (1234.0, None, None)),
    ("-3,25", (-3.25, None, None)),
    ("12,5 p", (12.5, None, "p")),
    ("-", (None, "-", None)),
    (".", (None, ".", None)),
    ("...", (None, "...", None)),
    ("…", (None, "...", None)),
    ("/", (None, "/", None)),
    ("x", (None, "x", None)),
    ("", (None, None, None)),
])
def test_parse_number(text: str, expected: tuple[object, ...]) -> None:
    assert parse_number(text) == expected


def test_fuehrende_null() -> None:
    assert pad_key(8111, 5) == "08111"
    assert pad_key("1001", 5) == "01001"
    assert pad_key(8.0, 2) == "08"


def _df() -> pd.DataFrame:
    return pd.DataFrame({
        "zeit": ["2024", "2024", "2024", "2024"],
        "ags5": ["01001", "01001", "08111", "08111"],
        "kreise_code": ["01001", "01001", "08111", "08111"],
        "alt_code": ["A", "B", "A", "B"],
        "merkmal_code": ["M"] * 4,
        "wert": [1.0, 2.0, 3.0, None],
    })


def test_wide_standard() -> None:
    w = to_wide(_df())
    assert w is not None
    assert list(w.columns) == ["ags5", "zeit", "M__A", "M__B"]
    assert len(w) == 2


def test_wide_mit_dimension_als_zeile() -> None:
    w = to_wide(_df(), ["zeit", "alt"])
    assert w is not None
    assert list(w.columns) == ["ags5", "zeit", "alt_code", "M"]
    assert len(w) == 3  # Zeile 08111/B ohne Wert entfaellt


def test_vollstaendigkeit() -> None:
    ref = pd.DataFrame({"ags5": ["01001", "08111", "09162"], "name": ["a", "b", "c"]})
    v = completeness(_df(), ref)
    assert v is not None
    assert v["zeitpunkte"]["2024"] == {"anzahl": 2, "fehlend": ["09162"], "ueberzaehlig": []}
    assert v["abweichende_zeitpunkte"] == 1
