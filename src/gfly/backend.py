"""PLACEHOLDER backend — returns deterministic STUB data so the skeleton compiles, runs,
and tests offline. `cli-implement` replaces this with the real engines:

  - google  : the `fast-flights` library (base64-protobuf `tfs` query → parse). Wrap its
              output in our normalizer so an upstream field rename surfaces as SCHEMA_DRIFT,
              not a KeyError. Map 429/CAPTCHA → throttle.record_block(); raise errors.blocked().
  - serpapi : direct HTTP to https://serpapi.com/google-flights-api (key from auth/env).

Both return the SAME normalized shapes defined below (the swappable-backend contract). The
CLI layer owns the JSON envelope (schemaVersion, query echo, count, nextCursor); a backend
returns only the domain lists. Heavy imports (fast-flights, httpx) must be lazy — imported
inside the functions, never at module top level — to keep `--help`/`schema` fast.
"""

from __future__ import annotations

SCHEMA_VERSION = "1"

BACKENDS = ("google", "serpapi")

# A tiny built-in IATA table so `airports search` works offline in the skeleton.
# cli-implement may swap this for a fuller dataset / fuzzy resolver.
_AIRPORTS = [
    {"iata": "JFK", "name": "John F. Kennedy International", "city": "New York", "country": "US"},
    {"iata": "LGA", "name": "LaGuardia", "city": "New York", "country": "US"},
    {"iata": "EWR", "name": "Newark Liberty International", "city": "Newark", "country": "US"},
    {"iata": "LHR", "name": "Heathrow", "city": "London", "country": "GB"},
    {"iata": "LGW", "name": "Gatwick", "city": "London", "country": "GB"},
    {"iata": "SFO", "name": "San Francisco International", "city": "San Francisco", "country": "US"},
    {"iata": "LAX", "name": "Los Angeles International", "city": "Los Angeles", "country": "US"},
    {"iata": "CDG", "name": "Charles de Gaulle", "city": "Paris", "country": "FR"},
    {"iata": "NRT", "name": "Narita International", "city": "Tokyo", "country": "JP"},
    {"iata": "HND", "name": "Haneda", "city": "Tokyo", "country": "JP"},
]


def _stub_itinerary(origin: str, depart: str, dest: str, *, price: int, currency: str,
                    best: bool, stops: int) -> dict:
    return {
        "price": price,
        "currency": currency,
        "isBest": best,
        "stops": stops,
        "durationMinutes": 425 + stops * 120,
        "departure": f"{depart}T18:30:00",
        "arrival": f"{depart}T23:55:00",
        "origin": origin,
        "destination": dest,
        "airlines": ["Example Air"] if best else ["Stub Airways"],
        "flightNumbers": ["EX112"] if best else ["ST900", "ST901"],
        "layovers": [] if stops == 0 else [{"airport": "BOS", "minutes": 75}],
        "co2Grams": 412000 + stops * 90000,
        "co2DeltaPct": -8 if best else 5,
        "bookingToken": "STUB-TOKEN",
    }


def search(*, origin: str, dest: str, depart: str, ret: str | None, currency: str,
           cabin: str, stops: str, backend: str) -> list[dict]:
    """One-way / round-trip itinerary search. Returns normalized itineraries."""
    # PLACEHOLDER: real impl calls fast-flights (google) or SerpApi (serpapi).
    return [
        _stub_itinerary(origin, depart, dest, price=642, currency=currency, best=True, stops=0),
        _stub_itinerary(origin, depart, dest, price=531, currency=currency, best=False, stops=1),
    ]


def dates(*, origin: str, dest: str, currency: str, backend: str) -> list[dict]:
    """Price calendar / cheapest dates across a window."""
    # PLACEHOLDER.
    return [
        {"departDate": "2026-08-01", "returnDate": None, "price": 642, "currency": currency},
        {"departDate": "2026-08-02", "returnDate": None, "price": 588, "currency": currency},
        {"departDate": "2026-08-03", "returnDate": None, "price": 705, "currency": currency},
    ]


def multi(*, legs: list[dict], currency: str, backend: str) -> list[dict]:
    """Multi-city search. `legs` = [{from,to,date}, ...]."""
    # PLACEHOLDER.
    if not legs:
        return []
    first, last = legs[0], legs[-1]
    return [_stub_itinerary(first["from"], first["date"], last["to"],
                            price=1280, currency=currency, best=True, stops=len(legs) - 1)]


def airports_search(query: str) -> list[dict]:
    """Resolve a city/name/code to IATA codes. Reference data — not throttled."""
    q = query.strip().lower()
    if not q:
        return []
    return [a for a in _AIRPORTS
            if q in a["iata"].lower() or q in a["name"].lower() or q in a["city"].lower()]
