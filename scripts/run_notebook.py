"""Fuehrt ein Notebook ohne die mit `skip-ci` markierten Zellen aus.

Aufruf: python scripts/run_notebook.py notebooks/schnellstart.ipynb [ausgabe.ipynb]
Exit-Code 1, wenn eine Zelle einen Fehler wirft.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError


def main(argv: list[str]) -> int:
    src = Path(argv[1])
    out = Path(argv[2]) if len(argv) > 2 else None
    nb = nbformat.read(src, as_version=4)  # type: ignore[no-untyped-call]
    nb.cells = [c for c in nb.cells if "skip-ci" not in c.get("metadata", {}).get("tags", [])]
    client = NotebookClient(nb, timeout=600, kernel_name="python3",
                            resources={"metadata": {"path": str(src.parent)}})
    try:
        client.execute()
    except CellExecutionError as e:
        print(e, file=sys.stderr)
        return 1
    finally:
        if out:
            nbformat.write(nb, out)  # type: ignore[no-untyped-call]
    print(f"{src}: {len(nb.cells)} Zellen ohne Fehler ausgefuehrt")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
