"""Pflichtfaelle Cache/Ablage (E.8: 1-4) plus Pruefintervall, Auswahl, Force."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from demografie_fetch import fetch
from demografie_fetch.store import parquet_meta
from tests.conftest import URL_0017, fixture_bytes, routes_0017

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _raw_dirs(tmp: Path, qid: str = "destatis_12411_0017") -> list[str]:
    return sorted(p.name for p in (tmp / "data/raw" / qid).iterdir() if p.is_dir())


def _go(tmp: Path, http: object, cfg: Path, now: datetime, **kw: object):  # type: ignore[no-untyped-def]
    return fetch(URL_0017, data_dir=tmp, config=cfg, http=http, now=now, **kw)  # type: ignore[arg-type]


def test_1_erster_lauf(tmp_path: Path, make_http, empty_config: Path) -> None:  # type: ignore[no-untyped-def]
    http, t = make_http(routes_0017())
    r = _go(tmp_path, http, empty_config, T0)
    assert r.meta["status"] == "neu"
    pq = tmp_path / "data/staging/destatis_12411_0017.parquet"
    assert pq.exists() and (tmp_path / "data/staging/destatis_12411_0017_kreise.csv").exists()
    raw = tmp_path / "data/raw/destatis_12411_0017" / _raw_dirs(tmp_path)[0]
    assert (raw / "data.json").read_bytes() == fixture_bytes("genesis_12411-0017_data.json")
    meta = json.loads((raw / "meta.json").read_text())
    assert meta["sha256"] == r.meta["sha256"] and meta["stand"] == r.meta["stand"]
    md = parquet_meta(pq)
    assert md["lizenz"] == "dl-de/by-2-0" and md["sha256"] == r.meta["sha256"]
    assert md["tabelle"] == "12411-0017" and md["stand"]
    assert len(r.long_df) == 12


def test_cache_im_pruefintervall_ohne_anfrage(tmp_path: Path, make_http,  # type: ignore[no-untyped-def]
                                             empty_config: Path) -> None:
    http, t = make_http(routes_0017())
    _go(tmp_path, http, empty_config, T0)
    n = len(t.calls)
    r = _go(tmp_path, http, empty_config, T0 + timedelta(hours=1))
    assert r.meta["status"] == "cache" and len(t.calls) == n
    assert len(r.long_df) == 12


def test_2_zweiter_lauf_unveraendert(tmp_path: Path, make_http, empty_config: Path) -> None:  # type: ignore[no-untyped-def]
    http, t = make_http(routes_0017())
    _go(tmp_path, http, empty_config, T0)
    pq = tmp_path / "data/staging/destatis_12411_0017.parquet"
    mtime, content = pq.stat().st_mtime_ns, pq.read_bytes()
    r = _go(tmp_path, http, empty_config, T0 + timedelta(days=1))
    assert r.meta["status"] == "unveraendert"
    assert t.count("/data") == 1 and t.count("/structure") == 2
    assert pq.stat().st_mtime_ns == mtime and pq.read_bytes() == content
    assert len(_raw_dirs(tmp_path)) == 1


def test_3_gleiche_pruefsumme_nicht_doppelt(tmp_path: Path, make_http,  # type: ignore[no-untyped-def]
                                           empty_config: Path) -> None:
    http, t = make_http(routes_0017())
    _go(tmp_path, http, empty_config, T0)
    http2, t2 = make_http(routes_0017(stand="2026-10-02T00:00:00Z"))
    r = _go(tmp_path, http2, empty_config, T0 + timedelta(days=2))
    assert t2.count("/data") == 1
    assert r.meta["status"] == "unveraendert" and len(_raw_dirs(tmp_path)) == 1
    state = json.loads((tmp_path / "data/raw/destatis_12411_0017/_state.json").read_text())
    assert state["stand"] == "2026-10-02T00:00:00Z"


def test_4_geaenderter_inhalt_neue_fassung(tmp_path: Path, make_http,  # type: ignore[no-untyped-def]
                                          empty_config: Path) -> None:
    http, _ = make_http(routes_0017())
    _go(tmp_path, http, empty_config, T0)
    erste = _raw_dirs(tmp_path)[0]
    alt = (tmp_path / "data/raw/destatis_12411_0017" / erste / "data.json").read_bytes()
    raw = json.loads(fixture_bytes("genesis_12411-0017_data.json"))
    raw["data"][0]["value"][0] = 2265.0
    http2, _ = make_http(routes_0017(stand="2026-11-01T00:00:00Z",
                                     data=json.dumps(raw).encode()))
    r = _go(tmp_path, http2, empty_config, T0 + timedelta(days=31))
    assert r.meta["status"] == "neu"
    dirs = _raw_dirs(tmp_path)
    assert len(dirs) == 2 and erste in dirs
    assert (tmp_path / "data/raw/destatis_12411_0017" / erste / "data.json").read_bytes() == alt
    assert r.long_df.iloc[0]["wert"] == 2265.0


def test_auswahlwechsel_ohne_download(tmp_path: Path, make_http, empty_config: Path) -> None:  # type: ignore[no-untyped-def]
    http, t = make_http(routes_0017())
    _go(tmp_path, http, empty_config, T0)
    r = _go(tmp_path, http, empty_config, T0 + timedelta(minutes=5), startyear=2020)
    assert r.meta["status"] == "unveraendert" and t.count("/data") == 1
    assert set(r.long_df["zeit"].astype(str)) == {"2024-12-31"}


def test_parquet_geloescht(tmp_path: Path, make_http, empty_config: Path) -> None:  # type: ignore[no-untyped-def]
    http, t = make_http(routes_0017())
    _go(tmp_path, http, empty_config, T0)
    pq = tmp_path / "data/staging/destatis_12411_0017.parquet"
    pq.unlink()
    _go(tmp_path, http, empty_config, T0 + timedelta(minutes=5))
    assert pq.exists() and t.count("/data") == 1


def test_force(tmp_path: Path, make_http, empty_config: Path) -> None:  # type: ignore[no-untyped-def]
    http, t = make_http(routes_0017())
    _go(tmp_path, http, empty_config, T0)
    _go(tmp_path, http, empty_config, T0 + timedelta(minutes=5), force=True)
    assert t.count("/data") == 2 and len(_raw_dirs(tmp_path)) == 1


def test_formatfehler_laesst_parquet_unveraendert(tmp_path: Path, make_http,  # type: ignore[no-untyped-def]
                                                 empty_config: Path) -> None:
    import pytest

    from demografie_fetch.errors import FormatError

    http, _ = make_http(routes_0017())
    _go(tmp_path, http, empty_config, T0)
    pq = tmp_path / "data/staging/destatis_12411_0017.parquet"
    before = pq.read_bytes()
    http2, _ = make_http(routes_0017(stand="2026-12-01T00:00:00Z", data=b'{"data": []}'))
    with pytest.raises(FormatError):
        _go(tmp_path, http2, empty_config, T0 + timedelta(days=60))
    assert pq.read_bytes() == before and len(_raw_dirs(tmp_path)) == 1
