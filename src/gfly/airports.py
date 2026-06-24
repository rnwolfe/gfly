"""Offline IATA airport resolution, backed by the `airportsdata` package (~7.9k airports,
no network). Used by `gfly airports search` so agents resolve cities to codes instead of
guessing. Reference data — not throttled, not third-party-untrusted."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _table() -> dict[str, dict]:
    import airportsdata  # lazy: keeps --help/schema fast
    return airportsdata.load("IATA")


def _row(a: dict) -> dict:
    return {"iata": a["iata"], "name": a["name"], "city": a["city"], "country": a["country"]}


def search(query: str, *, limit: int = 25) -> list[dict]:
    """Resolve a city / airport name / IATA code to airports. Exact-code matches rank first,
    then case-insensitive substring matches on code, city, and name."""
    q = (query or "").strip().lower()
    if not q:
        return []
    table = _table()

    # 1) exact IATA code
    exact = table.get(q.upper())
    out: list[dict] = [_row(exact)] if exact and len(q) == 3 else []
    seen = {r["iata"] for r in out}

    # 2) substring matches (code prefix, then city, then name)
    def add(rows):
        for a in rows:
            if a["iata"] in seen or not a["iata"]:
                continue
            out.append(_row(a))
            seen.add(a["iata"])

    vals = list(table.values())
    add(a for a in vals if a["iata"] and a["iata"].lower().startswith(q))
    add(a for a in vals if a["city"] and q in a["city"].lower())
    add(a for a in vals if a["name"] and q in a["name"].lower())
    return out[: max(limit, 1) * 4]  # CLI applies the real --limit bound
