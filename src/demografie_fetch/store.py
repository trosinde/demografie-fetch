"""Ablage: Pfade je Rolle, atomares Schreiben.

Einzige Stelle, die `data/validation` kennt (Rollentrennung).
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

VALIDATION_ROLE = "validierung"


class Store:
    def __init__(self, base: Path | str | None = None) -> None:
        self.base = Path(base or os.environ.get("DEMOGRAFIE_DATA_DIR") or ".")
        self.data = self.base / "data"

    def raw_dir(self, quelle_id: str) -> Path:
        return self.data / "raw" / quelle_id

    def state_path(self, quelle_id: str) -> Path:
        return self.raw_dir(quelle_id) / "_state.json"

    def table_dir(self, rolle: str) -> Path:
        return self.data / ("validation" if rolle == VALIDATION_ROLE else "staging")

    def parquet_path(self, quelle_id: str, rolle: str) -> Path:
        return self.table_dir(rolle) / f"{quelle_id}.parquet"

    def wide_path(self, quelle_id: str, rolle: str) -> Path:
        return self.table_dir(rolle) / f"{quelle_id}_kreise.csv"

    def runs_dir(self, stamp: str) -> Path:
        return self.base / "runs" / stamp


def _atomic(path: Path, write: Callable[[Path], None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)
    try:
        write(Path(tmp))
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_bytes(path: Path, data: bytes) -> None:
    def _w(p: Path) -> None:
        p.write_bytes(data)

    _atomic(path, _w)


def write_json(path: Path, obj: Any) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    def _w(p: Path) -> None:
        p.write_text(text, encoding="utf-8")

    _atomic(path, _w)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_parquet(path: Path, df: pd.DataFrame, meta: dict[str, str]) -> None:
    table = pa.Table.from_pandas(df, preserve_index=False)
    md = dict(table.schema.metadata or {})
    md.update({k.encode(): str(v).encode() for k, v in meta.items()})
    table = table.replace_schema_metadata(md)
    _atomic(path, lambda p: pq.write_table(table, p))


def read_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def parquet_meta(path: Path) -> dict[str, str]:
    md = pq.read_schema(path).metadata or {}
    return {k.decode(): v.decode() for k, v in md.items() if k != b"pandas"}


def write_csv(path: Path, df: pd.DataFrame) -> None:
    _atomic(path, lambda p: df.to_csv(p, index=False, encoding="utf-8"))
