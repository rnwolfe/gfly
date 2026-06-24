"""gfly — agent-first, read-only CLI for searching Google Flights.

Scaffolded by agent-cli-factory from the Python (Click) template. The contract surface
(output, errors, safety gate, schema, agent, throttle) is in place; `backend.py` and
`auth.py` are PLACEHOLDERS that `cli-implement` replaces with the real fast-flights / SerpApi
engines. See spec.md.
"""

from importlib import metadata


def _version() -> str:
    try:
        return metadata.version("gfly")
    except metadata.PackageNotFoundError:
        return "dev"


__version__ = _version()
