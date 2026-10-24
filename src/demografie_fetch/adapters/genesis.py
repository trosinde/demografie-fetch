"""GENESIS-Online (Destatis) ueber die oeffentliche Schnittstelle der Web-Oberflaeche.

Endpunkte (GET, ohne Anmeldung), Basis https://genesis.destatis.de/genesis/api/rest/:
tables/<code>/structure | data | qualitySigns, statistics/<code>/tables, settings/instance.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ..errors import FormatError, InputError
from ..http import PoliteSession

BASE_URL = "https://genesis.destatis.de/genesis/api/rest/"
LIZENZ = "dl-de/by-2-0"
REGION_COLUMNS = {"KREISE": ("ags5", 5), "DLAND": ("land", 2)}
DEFAULT_REPLACING = ("...", "/", ".", "x", "-")


def _de(label: Any) -> str:
    if isinstance(label, dict):
        return str(label.get("de") or label.get("en") or "")
    return "" if label is None else str(label)


@dataclass
class TableInfo:
    code: str
    title: str
    stand: str | None
    copyright: str
    variables: dict[str, dict[str, Any]]
    value_labels: dict[str, str]
    contents: dict[str, dict[str, Any]]

    @classmethod
    def from_structure(cls, s: dict[str, Any]) -> TableInfo:
        try:
            t = s["table"]
            return cls(
                code=str(t["code"]),
                title=_de(t.get("label")).replace("\n", " "),
                stand=t.get("lastChange"),
                copyright=_de(t.get("copyright")),
                variables=dict(s.get("variables") or {}),
                value_labels={k: _de(v.get("label")) for k, v in
                              (s.get("variableValues") or {}).items()},
                contents=dict(s.get("contents") or {}),
            )
        except (KeyError, TypeError, AttributeError) as e:
            raise FormatError(f"Antwortformat unerwartet (structure): {e}") from e

    def time_variables(self) -> set[str]:
        return {k for k, v in self.variables.items()
                if str(v.get("variableType", "")).startswith("TIME")}


class GenesisClient:
    def __init__(self, http: PoliteSession, base_url: str = BASE_URL) -> None:
        self.http = http
        self.base = base_url

    def _get(self, path: str, timeout: float = 60.0) -> bytes:
        return self.http.get(self.base + path, timeout=timeout).content

    @staticmethod
    def _json(raw: bytes, what: str) -> Any:
        try:
            return json.loads(raw)
        except ValueError as e:
            raise FormatError(f"Antwortformat unerwartet ({what}): kein JSON") from e

    def structure(self, code: str) -> tuple[bytes, TableInfo]:
        raw = self._get(f"tables/{code}/structure")
        return raw, TableInfo.from_structure(self._json(raw, "structure"))

    def data(self, code: str) -> bytes:
        return self._get(f"tables/{code}/data", timeout=300.0)

    def quality_signs(self, code: str) -> bytes:
        return self._get(f"tables/{code}/qualitySigns")

    def statistic_tables(self, statistic: str) -> list[dict[str, Any]]:
        lst = self._json(self._get(f"statistics/{statistic}/tables"), "statistics")
        if not isinstance(lst, list):
            raise FormatError("Antwortformat unerwartet (statistics): keine Liste")
        return [
            {"code": t.get("code"), "titel": _de(t.get("name")).replace("\n", " "),
             "kreise": "KREISE" in (t.get("locationVariableCodes") or [])}
            for t in lst
        ]

    def instance(self) -> dict[str, Any]:
        d = self._json(self._get("settings/instance"), "settings")
        return d if isinstance(d, dict) else {}


# ------------------------------------------------------------------ Wuerfel -> Langformat


def _signs(raw_signs: bytes | None) -> tuple[set[str], set[str]]:
    if not raw_signs:
        return set(DEFAULT_REPLACING), set()
    d = json.loads(raw_signs)
    return set(d.get("signsReplacingValue") or DEFAULT_REPLACING), set(
        d.get("signsWithValue") or []
    )


def _status_array(status: Any, n: int) -> np.ndarray:
    out = np.full(n, None, dtype=object)
    if isinstance(status, list):
        if len(status) != n:
            raise FormatError("Antwortformat unerwartet: Anzahl Status ungleich Anzahl Werte")
        out[:] = status
    elif isinstance(status, dict):
        for k, v in status.items():
            out[int(k)] = v
    elif isinstance(status, str):
        out[:] = status
    return out


def cube_to_long(raw_data: bytes, info: TableInfo, raw_signs: bytes | None,
                 quelle_id: str) -> pd.DataFrame:
    """Zerlegt den Datenwuerfel vollstaendig in das Langformat (eine Zeile je Zelle)."""
    try:
        ds = json.loads(raw_data)["data"][0]
        ids: list[str] = list(ds["id"])
        size: list[int] = [int(x) for x in ds["size"]]
        dims: dict[str, Any] = ds["dimension"]
        values = ds["value"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise FormatError(f"Antwortformat unerwartet (data): {e}") from e
    n = math.prod(size)
    if len(ids) != len(size) or not isinstance(values, list) or len(values) != n:
        raise FormatError(
            f"Antwortformat unerwartet: {len(values) if isinstance(values, list) else '?'} "
            f"Werte, erwartet {n}"
        )
    replacing, _with_value = _signs(raw_signs)  # unbekannte Zeichen -> qualitaet
    time_vars = info.time_variables()

    def codes_of(dim: str, k: int) -> list[str]:
        idx = dims[dim]["category"]["index"]
        codes = [""] * k
        if isinstance(idx, dict):
            for code, pos in idx.items():
                codes[int(pos)] = str(code)
        else:
            codes = [str(c) for c in idx]
        if len(codes) != k or "" in codes:
            raise FormatError(f"Antwortformat unerwartet: Dimension {dim}")
        return codes

    cell = np.arange(n, dtype=np.int64)
    cols: dict[str, Any] = {}
    stride = n
    merkmal_codes = None
    merkmal_idx = None
    for dim, k in zip(ids, size, strict=True):
        stride //= k
        pos = (cell // stride) % k
        codes = codes_of(dim, k)
        if dim == "statistic":
            continue
        if dim == "content":
            merkmal_codes, merkmal_idx = codes, pos
            continue
        if dim in time_vars:
            cols["zeit"] = pd.Categorical.from_codes(pos, categories=pd.Index(codes))
            continue
        if dim in REGION_COLUMNS:
            name, width = REGION_COLUMNS[dim]
            padded = [c.zfill(width) if c.isdigit() else c for c in codes]
            cols[name] = pd.Categorical.from_codes(pos, categories=pd.Index(padded))
        low = dim.lower()
        cols[f"{low}_code"] = pd.Categorical.from_codes(pos, categories=pd.Index(codes))
        labels = [info.value_labels.get(c, "") for c in codes]
        cols[f"{low}_label"] = pd.Categorical(np.asarray(labels, dtype=object)[pos])
    if merkmal_codes is None or merkmal_idx is None:
        raise FormatError("Antwortformat unerwartet: Dimension content fehlt")
    m_code, m_label, m_unit = [], [], []
    for c in merkmal_codes:
        base, _, func = c.partition("$")
        content = info.contents.get(base, {})
        m_code.append(base)
        m_label.append(_de(content.get("label")))
        fn = (content.get("functions") or {}).get(func or "QMU", {})
        m_unit.append(_de(fn.get("label")) if fn else "")

    vals = np.array([np.nan if v is None else float(v) for v in values], dtype=np.float64)
    st = _status_array(ds.get("status"), n)
    is_repl = np.array([s in replacing for s in st], dtype=bool)
    sonder = np.where(is_repl, st, None)
    qual = np.where(~is_repl & np.array([s is not None for s in st]), st, None)
    vals[is_repl] = np.nan

    df = pd.DataFrame({"quelle_id": quelle_id, "tabelle": info.code, **cols})
    df["merkmal_code"] = pd.Categorical.from_codes(merkmal_idx, categories=pd.Index(m_code))
    df["merkmal_label"] = pd.Categorical(np.asarray(m_label, dtype=object)[merkmal_idx])
    df["einheit"] = pd.Categorical(np.asarray(m_unit, dtype=object)[merkmal_idx])
    df["wert"] = vals
    df["sonderzeichen"] = pd.Categorical(sonder)
    df["qualitaet"] = pd.Categorical(qual)
    df["quelle_id"] = df["quelle_id"].astype("category")
    df["tabelle"] = df["tabelle"].astype("category")
    front = ["quelle_id", "tabelle"] + (["zeit"] if "zeit" in df else [])
    front += [c for c in ("ags5", "land") if c in df]
    rest = [c for c in df.columns if c not in front]
    return df[front + rest]


def apply_selection(df: pd.DataFrame, auswahl: dict[str, Any]) -> pd.DataFrame:
    """Filtert Zeilen; Werte bleiben unveraendert."""
    mask = pd.Series(True, index=df.index)
    for key, val in auswahl.items():
        if val is None or val == "":
            continue
        if key in ("startyear", "endyear"):
            if "zeit" not in df:
                raise InputError(f"{key}: Tabelle hat keine Zeitdimension")
            year = df["zeit"].astype(str).str[:4].astype(int)
            mask &= (year >= int(val)) if key == "startyear" else (year <= int(val))
            continue
        col = f"{str(key).lower()}_code"
        if col not in df:
            dims = sorted(c[:-5].upper() for c in df.columns if c.endswith("_code")
                          and c != "merkmal_code")
            raise InputError(f"Unbekannte Dimension {key}; vorhanden: {', '.join(dims)}")
        wanted = [v.strip() for v in val.split(",")] if isinstance(val, str) else [
            str(v) for v in val]
        known = set(df[col].cat.categories)
        bad = [w for w in wanted if w not in known]
        if bad:
            raise InputError(f"Unbekannte Werte fuer {key}: {', '.join(bad)}; "
                             f"gueltig: {', '.join(sorted(known))}")
        mask &= df[col].isin(wanted)
    out = df[mask].reset_index(drop=True)
    for c in out.select_dtypes("category").columns:
        out[c] = out[c].cat.remove_unused_categories()
    return out
