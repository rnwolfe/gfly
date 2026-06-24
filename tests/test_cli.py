import json

import pytest

from gfly.cli import run


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    # Isolate persistent throttle state per test, and disable color.
    monkeypatch.setenv("GFLY_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("NO_COLOR", "1")
    # Throttle OFF by default so most tests don't trip the politeness timer; the
    # throttle tests below re-enable it explicitly.
    monkeypatch.setenv("GFLY_NO_THROTTLE", "1")


# --- reads ------------------------------------------------------------------

def test_search_json_envelope(capsys):
    code = run(["search", "JFK", "LHR", "--depart", "2026-08-01", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    env = json.loads(out)
    assert env["schemaVersion"] == "1"
    assert env["backend"] == "google"
    assert env["query"]["from"] == "JFK"
    assert env["count"] >= 1
    assert env["itineraries"][0]["price"] > 0


def test_search_requires_depart(capsys):
    code = run(["search", "JFK", "LHR", "--json"])
    cap = capsys.readouterr()
    assert code == 2
    assert cap.out.strip() == ""
    assert "depart" in cap.err.lower()


def test_search_no_input_hardfails(capsys):
    code = run(["search", "JFK", "LHR", "--no-input", "--json"])
    cap = capsys.readouterr()
    assert code == 13
    assert "INPUT_REQUIRED" in cap.err


def test_dates_json(capsys):
    code = run(["dates", "JFK", "LHR", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    env = json.loads(out)
    assert env["dates"] and "price" in env["dates"][0]


def test_multi_bad_leg_is_usage_error(capsys):
    code = run(["multi", "--leg", "JFK-CDG-2026-08-01", "--json"])
    cap = capsys.readouterr()
    assert code == 2
    assert "USAGE" in cap.err or "leg" in cap.err.lower()


def test_airports_search_and_empty(capsys):
    code = run(["airports", "search", "london", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert any(a["iata"] == "LHR" for a in json.loads(out)["airports"])

    code = run(["airports", "search", "zzzzz", "--json"])
    cap = capsys.readouterr()
    assert code == 3
    assert "EMPTY_RESULTS" in cap.err


# --- token economy ----------------------------------------------------------

def test_limit_bounds_and_cursor(capsys):
    code = run(["search", "JFK", "LHR", "--depart", "2026-08-01", "--limit", "1", "--json"])
    out = capsys.readouterr().out
    env = json.loads(out)
    assert code == 0
    assert env["count"] >= 2          # total preserved
    assert len(env["itineraries"]) == 1
    assert env["nextCursor"] == "1"


def test_select_projection(capsys):
    code = run(["search", "JFK", "LHR", "--depart", "2026-08-01",
                "--select", "count,backend", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert set(json.loads(out).keys()) == {"count", "backend"}


# --- self-description -------------------------------------------------------

def test_schema_has_safety_and_gfly_exit_codes(capsys):
    code = run(["schema"])
    out = capsys.readouterr().out
    assert code == 0
    s = json.loads(out)
    assert s["safety"]["read_only"] is True
    assert s["exit_codes"]["blocked"] == 20
    assert s["exit_codes"]["schema_drift"] == 21
    assert "throttle" in s


def test_did_you_mean(capsys):
    code = run(["serch", "JFK", "LHR"])
    err = capsys.readouterr().err
    assert code == 2
    assert "did you mean" in err and "search" in err


def test_agent_prints_skill(capsys):
    code = run(["agent"])
    out = capsys.readouterr().out
    assert code == 0
    assert "# gfly" in out


# --- auth -------------------------------------------------------------------

def test_serpapi_auth_required(capsys, monkeypatch):
    monkeypatch.delenv("GFLY_SERPAPI_KEY", raising=False)
    code = run(["auth", "status", "--backend", "serpapi", "--json"])
    cap = capsys.readouterr()
    assert code == 4
    assert "AUTH_REQUIRED" in cap.err


# --- persistent throttle ----------------------------------------------------

def test_throttle_fails_fast_within_interval(capsys, monkeypatch):
    monkeypatch.delenv("GFLY_NO_THROTTLE", raising=False)
    args = ["search", "JFK", "LHR", "--depart", "2026-08-01", "--min-interval", "100", "--json"]
    assert run(args) == 0
    capsys.readouterr()
    code = run(args)                 # second call within the interval
    err = capsys.readouterr().err
    assert code == 7
    payload = json.loads(err)
    assert payload["code"] == "RATE_LIMITED"
    assert payload["retryAfterSeconds"] > 0


def test_no_throttle_bypasses(capsys, monkeypatch):
    monkeypatch.delenv("GFLY_NO_THROTTLE", raising=False)
    args = ["search", "JFK", "LHR", "--depart", "2026-08-01", "--min-interval", "100",
            "--no-throttle", "--json"]
    assert run(args) == 0
    capsys.readouterr()
    assert run(args) == 0            # not throttled
