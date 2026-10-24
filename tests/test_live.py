"""Live-Tests gegen GENESIS-Online (Destatis). Start: pytest -m live"""

from __future__ import annotations

from pathlib import Path

import pytest

from demografie_fetch import fetch

pytestmark = pytest.mark.live
BASE = "https://genesis.destatis.de/datenbank/online/statistic/"


def test_12421_0004_vollstaendig_und_unveraendert(tmp_path: Path) -> None:
    url = BASE + "12421/table/12421-0004"
    r = fetch(url, data_dir=tmp_path, max_age=0)
    assert r.meta["status"] == "neu"
    df = r.long_df
    assert df["land"].nunique() == 16
    assert df["bevpr2_code"].nunique() >= 9
    assert len(df) == df["land"].nunique() * df["zeit"].nunique() * df[
        "bevpr2_code"].nunique() * df["ges_code"].nunique() * df["alt101_code"].nunique()
    r2 = fetch(url, data_dir=tmp_path, max_age=0)
    assert r2.meta["status"] == "unveraendert"


def test_12411_0017_400_kreise(tmp_path: Path) -> None:
    url = BASE + "12411/table/12411-0017"
    r = fetch(url, data_dir=tmp_path, startyear=2012, max_age=0)
    years = sorted({z[:4] for z in r.long_df["zeit"].astype(str)})
    assert years[0] == "2012"
    tp = r.meta["vollstaendigkeit"]["zeitpunkte"]
    for zeit, e in tp.items():
        if zeit >= "2021":
            assert e["anzahl"] == 400 and "fehlend" not in e, zeit
    assert r.long_df["ags5"].astype(str).str.fullmatch(r"\d{5}").all()
