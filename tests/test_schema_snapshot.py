"""Schema-snapshot gate (contract §10): the agent-facing command tree, exit codes, and
itinerary field set are append-only. A rename/removal here is a REVIEWED diff, not a silent
break — update the golden deliberately and bump SCHEMA_VERSION for shape changes."""

import json

from gfly.cli import run

EXPECTED_COMMANDS = sorted(
    ["search", "dates", "multi", "airports", "auth", "doctor", "schema", "agent", "version"])

EXPECTED_EXIT_CODES = {
    "ok": 0, "generic_error": 1, "usage": 2, "empty_results": 3, "auth_required": 4,
    "not_found": 5, "permission": 6, "rate_limited": 7, "retryable": 8, "config_error": 10,
    "mutation_blocked": 12, "input_required": 13, "blocked": 20, "schema_drift": 21,
    "cancelled": 130,
}

EXPECTED_ITINERARY_FIELDS = {
    "price", "currency", "isBest", "stops", "durationMinutes", "departure", "arrival",
    "origin", "destination", "airlines", "flightNumbers", "layovers", "co2Grams",
    "co2DeltaPct", "bookingToken",
}


def test_command_tree_is_stable(capsys):
    run(["schema"])
    s = json.loads(capsys.readouterr().out)
    names = sorted(c for c in s["commands"]["commands"])
    assert names == EXPECTED_COMMANDS


def test_exit_code_table_is_stable(capsys):
    run(["schema"])
    s = json.loads(capsys.readouterr().out)
    assert s["exit_codes"] == EXPECTED_EXIT_CODES


def test_itinerary_fields_are_stable(capsys):
    run(["search", "JFK", "LHR", "--depart", "2026-07-25", "--json"])
    env = json.loads(capsys.readouterr().out)
    assert set(env["itineraries"][0].keys()) == EXPECTED_ITINERARY_FIELDS
