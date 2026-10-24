"""demografie-fetch: Demografiedaten fuer die Immobilien-Ampel."""

__version__ = "0.2.0"

from .core import FetchResult, RunResult, fetch, list_source, run  # noqa: E402

__all__ = ["FetchResult", "RunResult", "fetch", "list_source", "run", "__version__"]
