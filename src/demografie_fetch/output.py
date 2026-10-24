"""Breitformat, Vollstaendigkeit und Zahlenparser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

REFERENZ_KREISE = Path("config") / "referenz_kreise.csv"
_REPO_REFERENZ = Path(__file__).resolve().parents[2] / "config" / "referenz_kreise.csv"
SONDERZEICHEN = ("...", "…", ".", "-", "/", "x")
QUALITAET_RE = re.compile(r"^(?P<num>.*?)\s*(?P<q>[prse])$")


def pad_key(key: Any, width: int) -> str:
    """Kreis- (5) bzw. Landesschluessel (2) als Text mit fuehrenden Nullen."""
    s = str(key).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(width) if s.isdigit() else s


def parse_number(text: Any) -> tuple[float | None, str | None, str | None]:
    """Deutsche Zahl -> (wert, sonderzeichen, qualitaet), ohne Genauigkeitsverlust.

    '1.234.567,89' -> 1234567.89; '-' -> (None, '-', None); '12,5 p' -> (12.5, None, 'p').
    """
    if text is None:
        return None, None, None
    if isinstance(text, int | float):
        return float(text), None, None
    s = str(text).strip()
    if s == "":
        return None, None, None
    if s in SONDERZEICHEN:
        return None, ("..." if s == "…" else s), None
    qual = None
    m = QUALITAET_RE.match(s)
    if m and m.group("num"):
        s, qual = m.group("num").strip(), m.group("q")
    neg = s.startswith("-")
    body = s[1:] if neg else s
    if "," in body:
        body = body.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", body):
        body = body.replace(".", "")
    try:
        val = float(body)
    except ValueError as e:
        raise ValueError(f"Keine Zahl: {text!r}") from e
    return (-val if neg else val), None, qual


def region_column(df: pd.DataFrame) -> str | None:
    for c in ("ags5", "land"):
        if c in df.columns:
            return c
    return None


def to_wide(df: pd.DataFrame, wide: list[str] | None = None) -> pd.DataFrame | None:
    """Eine Zeile je Region und Kombination der `wide`-Dimensionen; Rest als Spalten."""
    region = region_column(df)
    if region is None:
        return None
    wide = [w.strip().lower() for w in (wide or ["zeit"]) if w.strip()]
    row_cols = [region]
    for w in wide:
        col = w if w in df.columns else f"{w}_code"
        if col not in df.columns:
            raise ValueError(f"--wide: unbekannte Dimension {w}")
        if col not in row_cols:
            row_cols.append(col)
    region_code = {"ags5": "kreise_code", "land": "dland_code"}[region]
    region_label = region_code.replace("_code", "_label")
    if region_label in df.columns:
        row_cols.insert(1, region_label)
    col_dims = ["merkmal_code"] + [
        c for c in df.columns
        if c.endswith("_code") and c not in row_cols and c not in ("merkmal_code", region_code)
    ]
    idx = [df[c].astype(str) for c in row_cols + col_dims]
    ser = pd.Series(df["wert"].to_numpy(), index=pd.MultiIndex.from_arrays(idx))
    wide_df = ser.unstack(list(range(len(row_cols), len(row_cols) + len(col_dims))))
    if isinstance(wide_df.columns, pd.MultiIndex):
        wide_df.columns = ["__".join(map(str, t)) for t in wide_df.columns]
    wide_df.columns.name = None
    wide_df.index.names = row_cols
    wide_df = wide_df.dropna(how="all")  # z. B. aufgeloeste Kreise ohne Werte
    return wide_df.reset_index()


def load_reference(path: Path | None = None) -> pd.DataFrame:
    if path is None:
        path = REFERENZ_KREISE if REFERENZ_KREISE.exists() else _REPO_REFERENZ
    return pd.read_csv(path, comment="#", dtype=str)


def completeness(df: pd.DataFrame, ref: pd.DataFrame | None = None) -> dict[str, Any] | None:
    """Kreise mit Wert je Zeitpunkt gegen die Referenzliste."""
    if "ags5" not in df.columns:
        return None
    if ref is None:
        try:
            ref = load_reference()
        except FileNotFoundError:
            return {"fehler": "Referenzliste config/referenz_kreise.csv fehlt"}
    soll = set(ref["ags5"])
    has = df.loc[df["wert"].notna(), ["zeit", "ags5"]] if "zeit" in df else df.loc[
        df["wert"].notna(), ["ags5"]].assign(zeit="-")
    out: dict[str, Any] = {"referenz": len(soll), "zeitpunkte": {}}
    abweichend = 0
    for zeit, grp in has.groupby("zeit", observed=True):
        ist = set(grp["ags5"].astype(str))
        fehlend, extra = sorted(soll - ist), sorted(ist - soll)
        eintrag: dict[str, Any] = {"anzahl": len(ist)}
        if fehlend or extra:
            abweichend += 1
            eintrag.update(fehlend=fehlend, ueberzaehlig=extra)
        out["zeitpunkte"][str(zeit)] = eintrag
    out["abweichende_zeitpunkte"] = abweichend
    return out
