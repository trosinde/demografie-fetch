"""demografie-fetch: Demografiedaten fuer die Immobilien-Ampel."""

__version__ = "0.1.0"

from .core import FetchResult, fetch, run  # noqa: E402

__all__ = ["FetchResult", "fetch", "run", "__version__"]
