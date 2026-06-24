"""Stable exit-code table and the structured CLI error type. See contract.md §3, §4.

Extends the factory template with gfly's reverse-engineering failure modes:
BLOCKED (20) and SCHEMA_DRIFT (21), plus a `retryAfterSeconds` extra carried on
RATE_LIMITED / BLOCKED so an agent can schedule its retry."""

from __future__ import annotations


class ExitCode:
    OK = 0
    GENERIC = 1
    USAGE = 2
    EMPTY = 3
    AUTH = 4
    NOT_FOUND = 5
    PERM = 6
    RATE = 7
    RETRY = 8
    CONFIG = 10
    MUTATION_BLOCKED = 12
    INPUT_REQUIRED = 13
    # gfly additions
    BLOCKED = 20
    SCHEMA_DRIFT = 21
    CANCELLED = 130


def exit_table() -> dict[str, int]:
    return {
        "ok": ExitCode.OK,
        "generic_error": ExitCode.GENERIC,
        "usage": ExitCode.USAGE,
        "empty_results": ExitCode.EMPTY,
        "auth_required": ExitCode.AUTH,
        "not_found": ExitCode.NOT_FOUND,
        "permission": ExitCode.PERM,
        "rate_limited": ExitCode.RATE,
        "retryable": ExitCode.RETRY,
        "config_error": ExitCode.CONFIG,
        "mutation_blocked": ExitCode.MUTATION_BLOCKED,
        "input_required": ExitCode.INPUT_REQUIRED,
        "blocked": ExitCode.BLOCKED,
        "schema_drift": ExitCode.SCHEMA_DRIFT,
        "cancelled": ExitCode.CANCELLED,
    }


class AppError(Exception):
    """Structured error carrying a machine code, remediation, exit code, and optional
    `extra` fields merged into the JSON error payload (e.g. retryAfterSeconds)."""

    def __init__(self, exit_code: int, code: str, message: str, remediation: str = "",
                 extra: dict | None = None):
        super().__init__(message)
        self.exit = exit_code
        self.code = code
        self.message = message
        self.remediation = remediation
        self.extra = extra or {}


def mutation_blocked(op: str) -> AppError:
    return AppError(
        ExitCode.MUTATION_BLOCKED,
        "MUTATION_BLOCKED",
        f"{op} is a mutating operation and is blocked by default",
        "re-run with --allow-mutations (add --dry-run to preview)",
    )


def not_found(kind: str, ident: str) -> AppError:
    return AppError(
        ExitCode.NOT_FOUND, "NOT_FOUND", f"{kind} {ident} not found",
        f"list available {kind}s to find a valid id",
    )


def input_required(what: str) -> AppError:
    return AppError(
        ExitCode.INPUT_REQUIRED, "INPUT_REQUIRED", f"{what} is required",
        "pass it as a flag/argument (running with --no-input, so prompts are disabled)",
    )


def empty_results(what: str) -> AppError:
    return AppError(
        ExitCode.EMPTY, "EMPTY_RESULTS", f"no {what} found for this query",
        "broaden dates/airports, or try --stops any",
    )


def auth_required(backend: str) -> AppError:
    return AppError(
        ExitCode.AUTH, "AUTH_REQUIRED", f"the {backend} backend needs a credential",
        f"run: gfly auth login --backend {backend} --token-stdin "
        f"(or set GFLY_SERPAPI_KEY)",
    )


def rate_limited(retry_after: int) -> AppError:
    """Our own politeness throttle (or an upstream 429) is in effect."""
    return AppError(
        ExitCode.RATE, "RATE_LIMITED",
        f"throttled; next request allowed in ~{retry_after}s",
        "wait and retry, pass --wait to block until allowed, or --backend serpapi",
        extra={"retryAfterSeconds": retry_after},
    )


def blocked(retry_after: int) -> AppError:
    """Google served a CAPTCHA / soft-block; the circuit breaker is open."""
    return AppError(
        ExitCode.BLOCKED, "BLOCKED",
        f"upstream is blocking requests (CAPTCHA/soft-block); cooling down ~{retry_after}s",
        "back off and retry later, switch --backend serpapi, or supply GFLY_ABUSE_COOKIE",
        extra={"retryAfterSeconds": retry_after},
    )


def schema_drift(detail: str) -> AppError:
    """The upstream response no longer parses — the engine library has drifted."""
    return AppError(
        ExitCode.SCHEMA_DRIFT, "SCHEMA_DRIFT",
        f"could not parse the upstream response: {detail}",
        "upgrade gfly / its engine, switch --backend serpapi, or file an issue",
    )
