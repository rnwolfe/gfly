"""Shared fixtures. The CLI tests must never touch the network, so we monkeypatch the two
backend network entry points (`_fetch_google`, `_serpapi_get`) with canned data and build
real fast-flights model objects to exercise the normalizer."""

import pytest

from fast_flights.model import (Airport, CarbonEmission, Flights, SimpleDatetime, SingleFlight)


def leg(frm, to, date, time, dur, plane="Boeing 777", arr=None):
    return SingleFlight(
        from_airport=Airport(name=f"{frm} Airport", code=frm),
        to_airport=Airport(name=f"{to} Airport", code=to),
        departure=SimpleDatetime(date=list(date), time=list(time)),
        arrival=SimpleDatetime(date=list(date), time=list(arr or (time[0] + 7, 0))),
        duration=dur, plane_type=plane)


def nonstop():
    return Flights(type="BA", price=285, airlines=["British Airways"],
                   flights=[leg("JFK", "LHR", (2026, 7, 25), (18, 30), 430, arr=(6, 35))],
                   carbon=CarbonEmission(typical_on_route=422000, emission=339000))


def one_stop():
    # JFK -> BOS (arr 19:45) , layover, BOS -> LHR (dep 21:00) => 75 min layover
    return Flights(type="AA", price=255, airlines=["American"],
                   flights=[leg("JFK", "BOS", (2026, 7, 25), (18, 30), 75, arr=(19, 45)),
                            leg("BOS", "LHR", (2026, 7, 25), (21, 0), 390, arr=(6, 30))],
                   carbon=CarbonEmission(typical_on_route=422000, emission=455000))


CANNED_GOOGLE = [nonstop(), one_stop()]


SERPAPI_RESPONSE = {
    "best_flights": [{
        "flights": [{
            "departure_airport": {"id": "JFK", "time": "2026-07-25 18:30"},
            "arrival_airport": {"id": "LHR", "time": "2026-07-26 06:35"},
            "airline": "British Airways", "flight_number": "BA 112", "duration": 425,
        }],
        "layovers": [], "total_duration": 425, "price": 642,
        "carbon_emissions": {"this_flight": 412000, "difference_percent": -8},
        "booking_token": "TOKEN-XYZ",
    }],
    "other_flights": [{
        "flights": [
            {"departure_airport": {"id": "JFK", "time": "2026-07-25 18:30"},
             "arrival_airport": {"id": "BOS", "time": "2026-07-25 19:45"},
             "airline": "American", "flight_number": "AA 1", "duration": 75},
            {"departure_airport": {"id": "BOS", "time": "2026-07-25 21:00"},
             "arrival_airport": {"id": "LHR", "time": "2026-07-26 06:30"},
             "airline": "American", "flight_number": "AA 2", "duration": 390},
        ],
        "layovers": [{"id": "BOS", "duration": 75, "name": "Boston Logan"}],
        "total_duration": 540, "price": 531,
        "carbon_emissions": {"this_flight": 455000, "difference_percent": 7},
        "booking_token": "TOKEN-ABC",
    }],
}


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GFLY_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("GFLY_NO_THROTTLE", "1")          # throttle tests re-enable explicitly
    monkeypatch.delenv("GFLY_SERPAPI_KEY", raising=False)
    # Default: google fetch returns canned itineraries (offline).
    from gfly import backend
    monkeypatch.setattr(backend, "_fetch_google", lambda q, proxy=None: list(CANNED_GOOGLE))


@pytest.fixture
def serpapi_env(monkeypatch):
    monkeypatch.setenv("GFLY_SERPAPI_KEY", "test-key")
    from gfly import backend
    monkeypatch.setattr(backend, "_serpapi_get", lambda params: dict(SERPAPI_RESPONSE))
