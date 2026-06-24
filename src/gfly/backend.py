"""The real data layer: two engines behind one normalized contract.

  - google  (default) : the `fast-flights` library (base64-protobuf `tfs` query → parse).
                        Unauthenticated, free, ban-prone. Maps blocks → errors.blocked(),
                        parse failures → errors.schema_drift().
  - serpapi (opt-in)  : SerpApi's Google Flights JSON API over stdlib urllib (key from auth/env).

Both return the SAME normalized itinerary dicts (the swappable-backend contract). The CLI owns
the JSON envelope (schemaVersion, query echo, count, nextCursor). Heavy imports (fast_flights)
are lazy — inside the functions — to keep `--help`/`schema` fast.

Network entry points are module-level (`_fetch_google`, `_serpapi_get`) so tests monkeypatch
them with fixtures and never touch the network.

Normalization caveats (documented honestly — this rides a reverse-engineered source):
  - google exposes no flight numbers or booking token (→ [] / null); serpapi provides both.
  - google can't reliably split "best" vs "other" (→ isBest False); serpapi sets isBest for
    best_flights.
  - round-trip via google returns the OUTBOUND legs with price = the round-trip total.
  - times are local to each airport, no tz offset (the upstream doesn't provide one).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import urllib.parse
import urllib.request

from . import throttle
from .errors import (AppError, ExitCode, auth_required, blocked as _blocked,
                     rate_limited, schema_drift)

SCHEMA_VERSION = "1"
BACKENDS = ("google", "serpapi")

_SEAT = {"economy": "economy", "premium": "premium-economy",
         "business": "business", "first": "first"}
_SERPAPI_CLASS = {"economy": 1, "premium": 2, "business": 3, "first": 4}
_SERPAPI_STOPS = {"any": 0, "nonstop": 1, "1": 2}
_GOOGLE_MAX_STOPS = {"any": None, "nonstop": 0, "1": 1}

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _clean(s: str | None, *, wrap: bool) -> str | None:
    """Untrusted-text hardening (contract §8). Upstream string fields are short labels, not
    prose, so we sanitize rather than fence: strip control chars / newlines that could break
    out of an agent's context, collapse whitespace, and cap length. `--no-wrap-untrusted`
    disables it."""
    if s is None:
        return None
    if not wrap:
        return s
    return _CONTROL.sub(" ", str(s)).strip()[:200]


# --- datetime helpers (upstream gives naive local date+time tuples) ----------

def _iso(sdt) -> str | None:
    try:
        d = tuple(sdt.date)
        t = tuple(sdt.time)
        if len(d) < 3:
            return None
        hh = t[0] if len(t) >= 1 else 0
        mm = t[1] if len(t) >= 2 else 0
        return f"{d[0]:04d}-{d[1]:02d}-{d[2]:02d}T{hh:02d}:{mm:02d}:00"
    except (TypeError, ValueError, IndexError, AttributeError):
        return None


def _to_dt(sdt) -> _dt.datetime | None:
    iso = _iso(sdt)
    if iso is None:
        return None
    try:
        return _dt.datetime.fromisoformat(iso)
    except ValueError:
        return None


def _gap_minutes(arrival, departure) -> int | None:
    a, b = _to_dt(arrival), _to_dt(departure)
    if a is None or b is None:
        return None
    return max(0, round((b - a).total_seconds() / 60))


# --- google engine (fast-flights) -------------------------------------------

def _fetch_google(query, proxy: str | None):
    """The only network call for google. Returns a fast_flights ResultList.
    Monkeypatched in tests."""
    from fast_flights import get_flights  # lazy
    return get_flights(query, proxy=proxy) if proxy else get_flights(query)


def _build_google_query(legs: list[dict], *, trip: str, seat: str, currency: str,
                        adults: int, children: int, infants: int, max_stops):
    from fast_flights import create_query, FlightQuery, Passengers  # lazy
    fqs = [FlightQuery(date=l["date"], from_airport=l["from"], to_airport=l["to"],
                       max_stops=max_stops) for l in legs]
    return create_query(
        flights=fqs, trip=trip, seat=_SEAT.get(seat, "economy"),
        passengers=Passengers(adults=adults, children=children, infants_in_seat=infants),
        currency=currency, max_stops=max_stops)


def _run_google(query, *, currency: str, wrap: bool, proxy: str | None) -> list[dict]:
    from fast_flights.exceptions import FlightsNotFound  # lazy
    try:
        res = _fetch_google(query, proxy)
    except FlightsNotFound:
        return []                                   # genuinely no results
    except AppError:
        raise
    except Exception as e:                          # classify the messy reverse-eng failures
        msg = str(e).lower()
        if any(k in msg for k in ("captcha", "429", "too many", "blocked", "abuse", "consent")):
            cooldown = throttle.record_block("google")
            raise _blocked(cooldown) from e
        if any(k in msg for k in ("timeout", "timed out", "connection", "temporarily")):
            raise AppError(ExitCode.RETRY, "RETRYABLE", f"transient upstream error: {e}",
                           "retry shortly, or --backend serpapi") from e
        # unknown shape change in the parser → schema drift
        raise schema_drift(f"{type(e).__name__}: {str(e)[:160]}") from e
    throttle.record_success("google")
    return [_norm_google(f, currency, wrap) for f in list(res)]


def _norm_google(f, currency: str, wrap: bool) -> dict:
    legs = list(f.flights)
    layovers = []
    total = 0
    for i, leg in enumerate(legs):
        total += int(getattr(leg, "duration", 0) or 0)
        if i + 1 < len(legs):
            g = _gap_minutes(leg.arrival, legs[i + 1].departure)
            if g is not None:
                total += g
            layovers.append({"airport": _clean(leg.to_airport.code, wrap=wrap),
                             "minutes": g})
    carbon = getattr(f, "carbon", None)
    emission = getattr(carbon, "emission", None)
    typical = getattr(carbon, "typical_on_route", None)
    delta = round((emission - typical) / typical * 100) if emission and typical else None
    return {
        "price": int(f.price) if f.price is not None else None,
        "currency": currency,
        "isBest": False,                            # google can't reliably split best/other
        "stops": max(0, len(legs) - 1),
        "durationMinutes": total or None,
        "departure": _iso(legs[0].departure) if legs else None,
        "arrival": _iso(legs[-1].arrival) if legs else None,
        "origin": _clean(legs[0].from_airport.code, wrap=wrap) if legs else None,
        "destination": _clean(legs[-1].to_airport.code, wrap=wrap) if legs else None,
        "airlines": [_clean(a, wrap=wrap) for a in (f.airlines or [])],
        "flightNumbers": [],                        # not exposed by google engine
        "layovers": layovers,
        "co2Grams": emission,
        "co2DeltaPct": delta,
        "bookingToken": None,                       # not exposed by google engine
    }


# --- serpapi engine ----------------------------------------------------------

def _serpapi_get(params: dict) -> dict:
    """The only network call for serpapi. Returns parsed JSON. Monkeypatched in tests."""
    url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "gfly"})
    last = None
    for attempt in range(3):                        # bounded retry for transient 5xx/timeouts
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                err = json.loads(body).get("error", body)
            except json.JSONDecodeError:
                err = body[:200]
            if e.code == 401:
                raise auth_required("serpapi") from e
            if e.code == 429:
                raise rate_limited(60) from e
            if e.code >= 500:
                last = AppError(ExitCode.RETRY, "RETRYABLE", f"serpapi {e.code}: {err}",
                                "retry shortly"); continue
            raise AppError(ExitCode.GENERIC, "UPSTREAM_ERROR", f"serpapi {e.code}: {err}",
                           "check parameters") from e
        except (urllib.error.URLError, TimeoutError) as e:
            last = AppError(ExitCode.RETRY, "RETRYABLE", f"network error: {e}", "retry shortly")
    raise last or AppError(ExitCode.RETRY, "RETRYABLE", "serpapi unreachable", "retry shortly")


def _serpapi_key() -> str:
    from . import auth
    key = auth.serpapi_key()
    if not key:
        raise auth_required("serpapi")
    return key


def _run_serpapi(params: dict, *, currency: str, wrap: bool) -> list[dict]:
    params = {**params, "engine": "google_flights", "api_key": _serpapi_key(),
              "currency": currency, "hl": "en"}
    data = _serpapi_get(params)
    if isinstance(data, dict) and data.get("error"):
        raise AppError(ExitCode.GENERIC, "UPSTREAM_ERROR", str(data["error"]),
                       "check query parameters")
    out = [_norm_serpapi(o, currency, True, wrap) for o in data.get("best_flights", [])]
    out += [_norm_serpapi(o, currency, False, wrap) for o in data.get("other_flights", [])]
    return out


def _norm_serpapi(o: dict, currency: str, best: bool, wrap: bool) -> dict:
    legs = o.get("flights", []) or []
    airlines, numbers = [], []
    for leg in legs:
        if leg.get("airline") and leg["airline"] not in airlines:
            airlines.append(_clean(leg["airline"], wrap=wrap))
        if leg.get("flight_number"):
            numbers.append(_clean(leg["flight_number"], wrap=wrap))
    layovers = [{"airport": _clean(l.get("id"), wrap=wrap), "minutes": l.get("duration")}
                for l in (o.get("layovers") or [])]
    carbon = o.get("carbon_emissions") or {}
    dep = legs[0].get("departure_airport", {}) if legs else {}
    arr = legs[-1].get("arrival_airport", {}) if legs else {}
    return {
        "price": o.get("price"),
        "currency": currency,
        "isBest": best,
        "stops": max(0, len(legs) - 1),
        "durationMinutes": o.get("total_duration"),
        "departure": _clean(dep.get("time"), wrap=wrap),
        "arrival": _clean(arr.get("time"), wrap=wrap),
        "origin": _clean(dep.get("id"), wrap=wrap),
        "destination": _clean(arr.get("id"), wrap=wrap),
        "airlines": airlines,
        "flightNumbers": numbers,
        "layovers": layovers,
        "co2Grams": carbon.get("this_flight"),
        "co2DeltaPct": carbon.get("difference_percent"),
        "bookingToken": o.get("booking_token"),
    }


# --- public API (dispatch) ---------------------------------------------------

def search(*, origin: str, dest: str, depart: str, ret: str | None, currency: str,
           cabin: str, stops: str, adults: int, children: int, infants: int,
           backend: str, wrap: bool, proxy: str | None) -> list[dict]:
    if backend == "serpapi":
        params = {"departure_id": origin, "arrival_id": dest, "outbound_date": depart,
                  "type": 1 if ret else 2, "travel_class": _SERPAPI_CLASS.get(cabin, 1),
                  "stops": _SERPAPI_STOPS.get(stops, 0), "adults": adults,
                  "children": children, "infants_in_seat": infants}
        if ret:
            params["return_date"] = ret
        return _run_serpapi(params, currency=currency, wrap=wrap)
    legs = [{"from": origin, "to": dest, "date": depart}]
    if ret:
        legs.append({"from": dest, "to": origin, "date": ret})
    q = _build_google_query(legs, trip="round-trip" if ret else "one-way", seat=cabin,
                            currency=currency, adults=adults, children=children,
                            infants=infants, max_stops=_GOOGLE_MAX_STOPS.get(stops))
    return _run_google(q, currency=currency, wrap=wrap, proxy=proxy)


def multi(*, legs: list[dict], currency: str, cabin: str, stops: str, adults: int,
          children: int, infants: int, backend: str, wrap: bool,
          proxy: str | None) -> list[dict]:
    if backend == "serpapi":
        # SerpApi multi-city uses multi_city_json; out of scope for this implementation.
        raise AppError(ExitCode.CONFIG, "UNSUPPORTED",
                       "multi-city is only implemented for the google backend",
                       "drop --backend serpapi for multi")
    q = _build_google_query(legs, trip="multi-city", seat=cabin, currency=currency,
                            adults=adults, children=children, infants=infants,
                            max_stops=_GOOGLE_MAX_STOPS.get(stops))
    return _run_google(q, currency=currency, wrap=wrap, proxy=proxy)


def cheapest_for_day(*, origin: str, dest: str, depart: str, currency: str, backend: str,
                     wrap: bool, proxy: str | None) -> dict | None:
    """Single-day lookup for the `dates` price scan. Returns {departDate, price, currency}
    or None if no flights that day."""
    items = search(origin=origin, dest=dest, depart=depart, ret=None, currency=currency,
                   cabin="economy", stops="any", adults=1, children=0, infants=0,
                   backend=backend, wrap=wrap, proxy=proxy)
    prices = [i["price"] for i in items if i.get("price") is not None]
    if not prices:
        return None
    return {"departDate": depart, "returnDate": None, "price": min(prices), "currency": currency}


def airports_search(query: str) -> list[dict]:
    from . import airports
    return airports.search(query)


def probe(backend: str, *, proxy: str | None) -> dict:
    """Lightweight reachability check for `doctor`. For google this is a real (throttled-exempt)
    search; for serpapi it only checks key presence (a live call would burn quota)."""
    if backend == "serpapi":
        from . import auth
        return {"reachable": bool(auth.serpapi_key()),
                "detail": "serpapi key present" if auth.serpapi_key()
                          else "no serpapi key (set GFLY_SERPAPI_KEY)"}
    try:
        items = search(origin="JFK", dest="LHR",
                       depart=(_dt.date.today() + _dt.timedelta(days=30)).isoformat(),
                       ret=None, currency="USD", cabin="economy", stops="any", adults=1,
                       children=0, infants=0, backend="google", wrap=True, proxy=proxy)
        return {"reachable": bool(items), "detail": f"google returned {len(items)} itineraries"}
    except AppError as e:
        return {"reachable": False, "detail": f"{e.code}: {e.message}"}
