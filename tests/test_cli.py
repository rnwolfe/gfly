import json

import pytest

from gfly.cli import run


# --- reads / normalization --------------------------------------------------

def test_search_json_envelope(capsys):
    code = run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    env = json.loads(out)
    assert env["schemaVersion"] == "1"
    assert env["backend"] == "google"
    assert env["query"]["from"] == "JFK"
    assert env["count"] == 2
    assert env["itineraries"][0]["price"] > 0


def test_google_normalization_stops_layovers_co2(capsys):
    code = run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--sort", "price", "--json"])
    env = json.loads(capsys.readouterr().out)
    assert code == 0
    cheapest = env["itineraries"][0]            # one_stop, price 255
    assert cheapest["stops"] == 1
    assert cheapest["layovers"] == [{"airport": "BOS", "minutes": 75}]
    assert cheapest["durationMinutes"] == 75 + 75 + 390   # legs + layover gap
    assert cheapest["co2Grams"] == 455000
    assert cheapest["co2DeltaPct"] == round((455000 - 422000) / 422000 * 100)
    assert cheapest["flightNumbers"] == []      # google does not expose these
    assert cheapest["bookingToken"] is None


def test_lowercase_airports_are_normalized(capsys):
    code = run(["search", "jfk", "lhr", "--depart", "2026-07-25", "--json"])
    env = json.loads(capsys.readouterr().out)
    assert code == 0
    assert env["query"]["from"] == "JFK" and env["query"]["to"] == "LHR"


def test_untrusted_warning_default_on_and_off(capsys):
    run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--json"])
    assert "_warning" in json.loads(capsys.readouterr().out)
    run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--no-wrap-untrusted", "--json"])
    assert "_warning" not in json.loads(capsys.readouterr().out)


def test_search_requires_depart(capsys):
    code = run(["search", "JFK", "LHR", "--json"])
    cap = capsys.readouterr()
    assert code == 2 and cap.out.strip() == "" and "depart" in cap.err.lower()


def test_search_no_input_hardfails(capsys):
    code = run(["search", "JFK", "LHR", "--no-input", "--json"])
    assert code == 13 and "INPUT_REQUIRED" in capsys.readouterr().err


# --- serpapi backend --------------------------------------------------------

def test_serpapi_search(capsys, serpapi_env):
    code = run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--backend", "serpapi", "--json"])
    env = json.loads(capsys.readouterr().out)
    assert code == 0
    assert env["backend"] == "serpapi"
    best = [i for i in env["itineraries"] if i["isBest"]]
    assert best and best[0]["flightNumbers"] == ["BA 112"]
    assert best[0]["bookingToken"] == "TOKEN-XYZ"
    other = [i for i in env["itineraries"] if not i["isBest"]][0]
    assert other["stops"] == 1 and other["layovers"][0]["airport"] == "BOS"


def test_serpapi_auth_required(capsys):
    code = run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--backend", "serpapi", "--json"])
    assert code == 4 and "AUTH_REQUIRED" in capsys.readouterr().err


# --- error classification ---------------------------------------------------

def test_block_maps_to_exit_20_and_records_cooldown(capsys, monkeypatch):
    from gfly import backend, throttle

    def boom(q, proxy=None):
        raise RuntimeError("Our systems have detected unusual traffic — captcha")
    monkeypatch.setattr(backend, "_fetch_google", boom)
    code = run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--json"])
    err = json.loads(capsys.readouterr().err)
    assert code == 20 and err["code"] == "BLOCKED"
    assert err["retryAfterSeconds"] > 0
    assert throttle.snapshot("google")["blocked"] is True   # circuit breaker opened


def test_parse_failure_maps_to_schema_drift(capsys, monkeypatch):
    from gfly import backend
    monkeypatch.setattr(backend, "_fetch_google",
                        lambda q, proxy=None: (_ for _ in ()).throw(KeyError("eQ35Ce")))
    code = run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--json"])
    assert code == 21 and "SCHEMA_DRIFT" in capsys.readouterr().err


def test_no_results_is_empty(capsys, monkeypatch):
    from gfly import backend
    from fast_flights.exceptions import FlightsNotFound

    def none(q, proxy=None):
        raise FlightsNotFound()
    monkeypatch.setattr(backend, "_fetch_google", none)
    code = run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--json"])
    assert code == 3 and "EMPTY_RESULTS" in capsys.readouterr().err


# --- dates / multi / airports ----------------------------------------------

def test_dates_scans_window(capsys):
    code = run(["dates", "JFK", "LHR", "--depart-range", "2026-07-25..2026-07-26", "--json"])
    out, err = capsys.readouterr().out, None
    assert code == 0
    env = json.loads(out)
    assert len(env["dates"]) == 2
    assert env["dates"][0]["price"] <= env["dates"][1]["price"]   # sorted cheapest-first


def test_dates_requires_range(capsys):
    code = run(["dates", "JFK", "LHR", "--json"])
    assert code == 2


def test_multi_needs_two_legs(capsys):
    code = run(["multi", "--leg", "JFK:CDG:2026-08-01", "--json"])
    assert code == 2 and "2 legs" in capsys.readouterr().err


def test_airports_search_real_resolution(capsys):
    code = run(["airports", "search", "london", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert any(a["iata"] == "LHR" for a in json.loads(out)["airports"])

    code = run(["airports", "search", "zzzzz", "--json"])
    assert code == 3 and "EMPTY_RESULTS" in capsys.readouterr().err


# --- token economy / self-description --------------------------------------

def test_limit_bounds_and_cursor(capsys):
    code = run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--limit", "1", "--json"])
    env = json.loads(capsys.readouterr().out)
    assert code == 0 and env["count"] == 2 and len(env["itineraries"]) == 1
    assert env["nextCursor"] == "1"


def test_select_projects_each_record(capsys):
    code = run(["search", "JFK", "LHR", "--depart", "2026-07-25",
                "--select", "price,airlines", "--json"])
    env = json.loads(capsys.readouterr().out)
    assert code == 0
    assert env["itineraries"] and all(set(it.keys()) == {"price", "airlines"}
                                      for it in env["itineraries"])


def test_offset_pagination(capsys):
    run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--limit", "1", "--json"])
    p1 = json.loads(capsys.readouterr().out)
    assert p1["offset"] == 0 and p1["nextCursor"] == "1" and len(p1["itineraries"]) == 1
    run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--limit", "1",
         "--offset", "1", "--json"])
    p2 = json.loads(capsys.readouterr().out)
    assert p2["offset"] == 1 and p2["nextCursor"] is None
    assert p1["itineraries"][0] != p2["itineraries"][0]


def test_bad_date_is_usage_not_schema_drift(capsys):
    code = run(["search", "JFK", "LHR", "--depart", "08/01/2026", "--json"])
    assert code == 2 and "USAGE" in capsys.readouterr().err


def test_zero_adults_rejected(capsys):
    code = run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--adults", "0", "--json"])
    assert code == 2


def test_version_flag_prints_bare_string(capsys):
    code = run(["--version"])
    out = capsys.readouterr().out.strip()
    assert code == 0 and out and " " not in out


def test_version_check_structured(capsys, monkeypatch):
    from gfly import update
    monkeypatch.setattr(update, "fetch_latest", lambda timeout=2.0: "9.9.9")
    code = run(["version", "--check", "--json"])
    d = json.loads(capsys.readouterr().out)
    assert code == 0
    assert d["latest"] == "9.9.9" and d["updateAvailable"] is True and d["upgrade"]
    assert "current" in d


def test_version_check_fail_silent_and_up_to_date(capsys, monkeypatch):
    from gfly import update
    monkeypatch.setattr(update, "fetch_latest", lambda timeout=2.0: None)  # network down
    code = run(["version", "--check", "--json"])
    d = json.loads(capsys.readouterr().out)
    assert code == 0 and d["latest"] is None and d["updateAvailable"] is False
    monkeypatch.setattr(update, "fetch_latest", lambda timeout=2.0: "0.0.1")  # older
    run(["version", "--check", "--json"])
    assert json.loads(capsys.readouterr().out)["updateAvailable"] is False


def test_dates_window_cap_declared_in_envelope(capsys):
    code = run(["dates", "JFK", "LHR", "--depart-range", "2026-08-01..2026-09-10", "--json"])
    env = json.loads(capsys.readouterr().out)
    assert code == 0
    assert env["partial"] is True            # narrowing declared, not silent
    assert env["scannedDays"] == 30 and env["requestedDays"] == 41
    assert "narrowed" in env


def test_schema_has_safety_and_gfly_exit_codes(capsys):
    code = run(["schema"])
    s = json.loads(capsys.readouterr().out)
    assert code == 0
    assert s["safety"]["read_only"] is True
    assert s["exit_codes"]["blocked"] == 20 and s["exit_codes"]["schema_drift"] == 21
    assert "throttle" in s


def test_did_you_mean(capsys):
    code = run(["serch", "JFK", "LHR"])
    err = capsys.readouterr().err
    assert code == 2 and "did you mean" in err and "search" in err


def test_agent_prints_skill(capsys):
    code = run(["agent"])
    assert code == 0 and "# gfly" in capsys.readouterr().out


# --- persistent throttle ----------------------------------------------------

def test_throttle_fails_fast_within_interval(capsys, monkeypatch):
    monkeypatch.delenv("GFLY_NO_THROTTLE", raising=False)
    args = ["search", "JFK", "LHR", "--depart", "2026-07-25", "--min-interval", "100", "--json"]
    assert run(args) == 0
    capsys.readouterr()
    code = run(args)
    payload = json.loads(capsys.readouterr().err)
    assert code == 7 and payload["code"] == "RATE_LIMITED" and payload["retryAfterSeconds"] > 0


def test_no_throttle_bypasses(capsys, monkeypatch):
    monkeypatch.delenv("GFLY_NO_THROTTLE", raising=False)
    args = ["search", "JFK", "LHR", "--depart", "2026-07-25", "--min-interval", "100",
            "--no-throttle", "--json"]
    assert run(args) == 0
    capsys.readouterr()
    assert run(args) == 0
