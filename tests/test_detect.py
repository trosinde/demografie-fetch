from __future__ import annotations

import pytest

from demografie_fetch.detect import detect, extract_codes
from demografie_fetch.errors import UnsupportedSourceError


@pytest.mark.parametrize(("url", "table", "stat"), [
    ("https://genesis.destatis.de/datenbank/online/statistic/12421/table/12421-0004",
     "12421-0004", "12421"),
    ("https://www-genesis.destatis.de/genesis/online?sequenz=tabelleErgebnis"
     "&selectionname=12411-0017", "12411-0017", "12411"),
    ("https://genesis.destatis.de/datenbank/online/statistic/12411", None, "12411"),
])
def test_destatis_positiv(url: str, table: str | None, stat: str) -> None:
    ref = detect(url)
    assert (ref.adapter, ref.db, ref.table, ref.statistic) == ("genesis", "destatis", table, stat)


@pytest.mark.parametrize(("url", "hint"), [
    ("https://www.regionalstatistik.de/genesis/online?selectionname=12411-03-03-4", "import"),
    ("https://tableau.bbsr.bund.de/views/ROP2045/Dashboard", "Tableau"),
    ("https://www.bbsr.bund.de/BBSR/DE/forschung/raumbeobachtung/x.html", "tableau.bbsr"),
    ("https://www.statistik.bayern.de/prognose.xlsx", "Datei"),
    ("https://example.org/statistik", "nicht erkannt"),
    ("https://genesis.destatis.de/datenbank/online", "ohne Tabellen"),
])
def test_negativ(url: str, hint: str) -> None:
    with pytest.raises(UnsupportedSourceError, match=hint) as e:
        detect(url)
    assert e.value.exit_code == 2


def test_codes_lang() -> None:
    assert extract_codes("x?selectionname=12411-03-03-4") == ("12411-03-03-4", "12411")
