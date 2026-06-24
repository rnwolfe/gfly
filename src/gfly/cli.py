"""kong-equivalent for Python: Click grammar, runtime context, and exit-code mapping.
main() does nothing but sys.exit(run(...)) so every path is testable in-process.

Global flags are attached to every command (not just the root group) so an agent can place
them in any position (e.g. `gfly search JFK LHR --json`), matching kong's behavior. Values
are merged leaf-first across the context chain.

gfly is READ-ONLY: every command is a read. The `--allow-mutations` gate + `Runtime.guard`
are retained from the contract template (uniform surface; a future gated verb could use them)
but no command currently mutates. The real safety surface here is the persistent throttle
(politeness) and prompt-injection fencing of third-party text.
"""

from __future__ import annotations

import difflib
import json
import os
import sys
from dataclasses import dataclass

import click

from . import __version__
from . import auth as authmod
from . import backend as be
from . import throttle
from .backend import SCHEMA_VERSION
from .errors import (AppError, ExitCode, exit_table, empty_results, input_required,
                     mutation_blocked)
from .output import Writer
from .skill import content as skill_content

# Set when a runtime is built, so the top-level error handler knows the chosen format.
_active: "Runtime | None" = None

_GLOBAL_KEYS = ["fmt", "as_json", "no_color", "allow_mutations", "dry_run", "yes", "force",
                "no_input", "limit", "select", "concise", "detailed", "backend", "currency",
                "wrap_untrusted", "min_interval", "wait", "max_wait", "no_throttle"]


def global_options(f):
    """Attach the universal agent-CLI contract flags + gfly's backend/currency/politeness
    flags to a command (tri-state default=None so we can tell 'not passed here' from
    'passed', and merge across the context chain)."""
    opts = [
        click.option("--format", "fmt", type=click.Choice(["json", "plain", "tsv"]),
                     default=None, help="Output format: json, plain, or tsv."),
        click.option("--json", "as_json", is_flag=True, default=None, help="Shorthand for --format=json."),
        click.option("--no-color", is_flag=True, default=None, help="Disable colored output."),
        click.option("--allow-mutations", is_flag=True, default=None,
                     help="Permit state-changing operations (gfly is read-only; no-op today)."),
        click.option("--dry-run", is_flag=True, default=None,
                     help="Print intended mutations without performing them."),
        click.option("--yes", is_flag=True, default=None, help="Assume yes for confirmations."),
        click.option("--force", is_flag=True, default=None, help="Bypass safety checks."),
        click.option("--no-input", is_flag=True, default=None, help="Never prompt; fail with exit 13."),
        click.option("--limit", type=int, default=None, help="Max results to show (default 25)."),
        click.option("--select", default=None, help="Comma-separated dot-path field projection."),
        click.option("--concise", is_flag=True, default=None, help="Terser output (default)."),
        click.option("--detailed", is_flag=True, default=None, help="Richer output."),
        # gfly additions
        click.option("--backend", type=click.Choice(list(be.BACKENDS)), default=None,
                     help="Data backend: google (default, no auth) or serpapi (needs key)."),
        click.option("--currency", default=None, help="ISO currency for prices (default USD)."),
        click.option("--wrap-untrusted/--no-wrap-untrusted", "wrap_untrusted", default=None,
                     help="Fence third-party free text as untrusted (default on)."),
        click.option("--min-interval", type=float, default=None,
                     help="Min seconds between google requests (default 12; politeness)."),
        click.option("--wait", is_flag=True, default=None,
                     help="Block and sleep until throttle clears (up to --max-wait)."),
        click.option("--max-wait", type=float, default=None,
                     help="Cap for --wait blocking sleep, seconds (default 60)."),
        click.option("--no-throttle", is_flag=True, default=None,
                     help="Bypass the politeness throttle (risky; may get blocked)."),
    ]
    for o in reversed(opts):
        f = o(f)
    return f


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Runtime:
    fmt: str
    allow_mutations: bool
    dry_run: bool
    yes: bool
    force: bool
    no_input: bool
    out: Writer
    backend: str
    currency: str
    wrap_untrusted: bool
    min_interval: float
    wait: bool
    max_wait: float
    no_throttle: bool

    def guard(self, op: str) -> None:
        # Retained contract gate; gfly has no mutating commands today.
        if not self.allow_mutations:
            raise mutation_blocked(op)

    def throttle_guard(self) -> None:
        throttle.guard(self.backend, min_interval=self.min_interval, wait=self.wait,
                       max_wait=self.max_wait, no_throttle=self.no_throttle)


def _resolve(ctx) -> dict:
    vals = {k: None for k in _GLOBAL_KEYS}
    c = ctx
    while c is not None:
        for k in _GLOBAL_KEYS:
            if vals[k] is None and c.params.get(k) is not None:
                vals[k] = c.params[k]
        c = c.parent
    return vals


def make_runtime(ctx) -> Runtime:
    global _active
    v = _resolve(ctx)
    fmt = "json" if v["as_json"] else (v["fmt"] or "plain")
    color = (not v["no_color"]) and sys.stdout.isatty() and fmt == "plain"
    sel = [s for s in (v["select"] or "").split(",") if s.strip()]
    limit = v["limit"] if v["limit"] is not None else 25
    out = Writer(fmt=fmt, color=color, limit=limit, select=sel)

    backend = v["backend"] or os.environ.get("GFLY_BACKEND") or "google"
    currency = (v["currency"] or os.environ.get("GFLY_CURRENCY") or "USD").upper()
    wrap = True if v["wrap_untrusted"] is None else bool(v["wrap_untrusted"])
    if v["min_interval"] is not None:
        min_interval = v["min_interval"]
    elif os.environ.get("GFLY_MIN_INTERVAL"):
        min_interval = float(os.environ["GFLY_MIN_INTERVAL"])
    else:
        min_interval = 12.0
    max_wait = v["max_wait"] if v["max_wait"] is not None else 60.0
    no_throttle = bool(v["no_throttle"]) or _truthy_env("GFLY_NO_THROTTLE")

    _active = Runtime(
        fmt=fmt, allow_mutations=bool(v["allow_mutations"]), dry_run=bool(v["dry_run"]),
        yes=bool(v["yes"]), force=bool(v["force"]), no_input=bool(v["no_input"]), out=out,
        backend=backend, currency=currency, wrap_untrusted=wrap, min_interval=min_interval,
        wait=bool(v["wait"]), max_wait=max_wait, no_throttle=no_throttle)
    return _active


def _emit_envelope(rt: Runtime, query: dict, key: str, items: list, *,
                   with_currency: bool = True) -> None:
    """Bound the list to --limit, set count/nextCursor, and emit the stable envelope."""
    total = len(items)
    lim = rt.out.limit
    sliced = items[:lim] if lim and lim > 0 else items
    truncated = total > len(sliced)
    if truncated:
        rt.out.info(f"note: showing {len(sliced)} of {total} {key} (raise --limit for more)")
    env = {"schemaVersion": SCHEMA_VERSION, "backend": rt.backend, "query": query}
    if with_currency:
        env["currency"] = rt.currency
    env["count"] = total
    env[key] = sliced
    env["nextCursor"] = str(lim) if truncated else None
    rt.out.emit(env)


class DYMGroup(click.Group):
    """Adds "did you mean" suggestions for unknown subcommands."""

    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as exc:
            name = args[0] if args else ""
            matches = difflib.get_close_matches(name, self.list_commands(ctx), n=1)
            if matches:
                exc.message = f"{exc.message}\n  did you mean '{matches[0]}'?"
            raise


@click.group(cls=DYMGroup, context_settings={"help_option_names": ["-h", "--help"]})
@global_options
@click.pass_context
def cli(ctx, **_):
    """gfly — read-only CLI for searching Google Flights.

    \b
    Examples:
      gfly search JFK LHR --depart 2026-08-01 --json
      gfly search SFO NRT --depart 2026-09-10 --return 2026-09-24 --cabin business
      gfly dates JFK LHR --json
      gfly airports search london
      gfly schema      # machine-readable command tree + exit codes + live state
    """


# --- search (read) ----------------------------------------------------------

@cli.command("search")
@click.argument("origin")
@click.argument("dest")
@click.option("--depart", help="Outbound date YYYY-MM-DD.")
@click.option("--return", "ret", help="Return date YYYY-MM-DD (omit for one-way).")
@click.option("--adults", type=int, default=1, show_default=True)
@click.option("--children", type=int, default=0, show_default=True)
@click.option("--infants", type=int, default=0, show_default=True)
@click.option("--cabin", type=click.Choice(["economy", "premium", "business", "first"]),
              default="economy", show_default=True)
@click.option("--stops", type=click.Choice(["any", "nonstop", "1"]), default="any",
              show_default=True)
@click.option("--sort", "sort", type=click.Choice(["price", "duration", "best"]),
              default="best", show_default=True)
@global_options
@click.pass_context
def search(ctx, origin, dest, depart, ret, adults, children, infants, cabin, stops, sort, **_):
    """Search itineraries between two airports (one-way or round-trip)."""
    rt = make_runtime(ctx)
    if not depart:
        if rt.no_input:
            raise input_required("--depart")
        raise AppError(ExitCode.USAGE, "USAGE", "--depart is required",
                       "gfly search JFK LHR --depart 2026-08-01")
    rt.throttle_guard()
    items = be.search(origin=origin.upper(), dest=dest.upper(), depart=depart, ret=ret,
                      currency=rt.currency, cabin=cabin, stops=stops, backend=rt.backend)
    if sort == "price":
        items.sort(key=lambda i: i["price"])
    elif sort == "duration":
        items.sort(key=lambda i: i["durationMinutes"])
    if not items:
        raise empty_results("itineraries")
    query = {"from": origin.upper(), "to": dest.upper(), "depart": depart, "return": ret,
             "adults": adults, "children": children, "infants": infants, "cabin": cabin,
             "stops": stops}
    _emit_envelope(rt, query, "itineraries", items)


# --- dates (read) -----------------------------------------------------------

@cli.command("dates")
@click.argument("origin")
@click.argument("dest")
@click.option("--depart-range", help="Earliest..latest departure window YYYY-MM-DD..YYYY-MM-DD.")
@click.option("--trip-length", type=int, help="Round-trip length in days.")
@click.option("--months", type=int, default=1, show_default=True, help="Months to scan.")
@global_options
@click.pass_context
def dates(ctx, origin, dest, depart_range, trip_length, months, **_):
    """Price calendar: cheapest departure dates across a window."""
    rt = make_runtime(ctx)
    rt.throttle_guard()
    items = be.dates(origin=origin.upper(), dest=dest.upper(), currency=rt.currency,
                     backend=rt.backend)
    if not items:
        raise empty_results("dates")
    query = {"from": origin.upper(), "to": dest.upper(), "departRange": depart_range,
             "tripLength": trip_length, "months": months}
    _emit_envelope(rt, query, "dates", items)


# --- multi (read) -----------------------------------------------------------

@cli.command("multi")
@click.option("--leg", "legs", multiple=True, required=True,
              help="A leg as FROM:TO:DATE (repeatable, in order).")
@global_options
@click.pass_context
def multi(ctx, legs, **_):
    """Multi-city search across two or more legs."""
    rt = make_runtime(ctx)
    parsed = []
    for raw in legs:
        parts = raw.split(":")
        if len(parts) != 3 or not all(parts):
            raise AppError(ExitCode.USAGE, "USAGE", f"bad --leg '{raw}'",
                           "use FROM:TO:DATE, e.g. --leg JFK:CDG:2026-08-01")
        parsed.append({"from": parts[0].upper(), "to": parts[1].upper(), "date": parts[2]})
    rt.throttle_guard()
    items = be.multi(legs=parsed, currency=rt.currency, backend=rt.backend)
    if not items:
        raise empty_results("itineraries")
    _emit_envelope(rt, {"legs": parsed}, "itineraries", items)


# --- airports (read) --------------------------------------------------------

@cli.group()
def airports():
    """Resolve airports / IATA codes (reference data; not throttled)."""


@airports.command("search")
@click.argument("query")
@global_options
@click.pass_context
def airports_search(ctx, query, **_):
    """Find IATA codes by city, name, or code."""
    rt = make_runtime(ctx)
    items = be.airports_search(query)
    if not items:
        raise empty_results("airports")
    _emit_envelope(rt, {"query": query}, "airports", items, with_currency=False)


# --- auth (read) ------------------------------------------------------------

@cli.group()
def auth():
    """Manage the optional SerpApi key / abuse cookie (google needs none)."""


@auth.command("status")
@global_options
@click.pass_context
def auth_status(ctx, **_):
    """Show authentication status for the active backend."""
    rt = make_runtime(ctx)
    st = authmod.status(rt.backend)
    if rt.backend == "serpapi" and not st["authenticated"]:
        raise AppError(ExitCode.AUTH, "AUTH_REQUIRED", st["note"] or "serpapi key missing",
                       "gfly auth login --backend serpapi --token-stdin")
    rt.out.emit(st)


@auth.command("login")
@global_options
@click.option("--token-stdin", is_flag=True, help="Read the credential from stdin (never argv).")
@click.pass_context
def auth_login(ctx, token_stdin, **_):
    """Store a backend credential (PLACEHOLDER — wired by cli-implement)."""
    rt = make_runtime(ctx)
    if not token_stdin:
        raise AppError(ExitCode.USAGE, "USAGE", "secrets must come from stdin",
                       "echo $KEY | gfly auth login --backend serpapi --token-stdin")
    _ = sys.stdin.readline().strip()  # consume the secret; never echo it
    raise AppError(ExitCode.CONFIG, "NOT_IMPLEMENTED",
                   "credential storage is wired by cli-implement",
                   f"for now export GFLY_SERPAPI_KEY in the environment")


@auth.command("logout")
@global_options
@click.pass_context
def auth_logout(ctx, **_):
    """Forget stored credentials (PLACEHOLDER)."""
    rt = make_runtime(ctx)
    rt.out.emit({"ok": True, "note": "no stored credentials in this scaffold"})


# --- doctor / schema / agent / version --------------------------------------

@cli.command()
@global_options
@click.pass_context
def doctor(ctx, **_):
    """Diagnose setup, backend, and current throttle/block state."""
    rt = make_runtime(ctx)
    tstate = throttle.snapshot(rt.backend)
    checks = [
        {"name": "backend", "ok": True, "detail": f"{rt.backend} backend selected (stub data)"},
        {"name": "auth", "ok": authmod.status(rt.backend)["authenticated"],
         "detail": "google needs no auth" if rt.backend == "google" else "serpapi key check"},
        {"name": "throttle", "ok": not tstate["blocked"],
         "detail": f"cooldown {tstate['cooldownSeconds']}s" if tstate["blocked"] else "clear"},
    ]
    payload = {"ok": all(c["ok"] for c in checks), "backend": rt.backend, "reachable": True,
               "blocked": tstate["blocked"], "schemaOk": True, "throttle": tstate,
               "checks": checks}
    if not payload["ok"]:
        rt.out.emit(payload)
        raise AppError(ExitCode.CONFIG, "DOCTOR_FAILED", "one or more checks failed",
                       "see the failing check's detail")
    rt.out.emit(payload)


@cli.command()
@global_options
@click.pass_context
def schema(ctx, **_):
    """Print the machine-readable command schema (JSON)."""
    rt = make_runtime(ctx)
    info = cli.to_info_dict(click.Context(cli, info_name="gfly"))
    rt.out.emit_json({
        "tool": "gfly",
        "version": __version__,
        "schemaVersion": SCHEMA_VERSION,
        "commands": info,
        "exit_codes": exit_table(),
        "safety": {"allow_mutations": rt.allow_mutations, "dry_run": rt.dry_run,
                   "no_input": rt.no_input, "read_only": True,
                   "wrap_untrusted": rt.wrap_untrusted},
        "throttle": throttle.snapshot(rt.backend),
    })


@cli.command()
@global_options
@click.pass_context
def agent(ctx, **_):
    """Print the bundled agent SKILL.md."""
    rt = make_runtime(ctx)
    rt.out.stdout.write(skill_content())


@cli.command()
@global_options
@click.pass_context
def version(ctx, **_):
    """Print the version."""
    rt = make_runtime(ctx)
    rt.out.emit({"version": __version__})


# --- entry / exit mapping ---------------------------------------------------

def run(argv: list[str] | None = None) -> int:
    try:
        rv = cli.main(args=argv, standalone_mode=False)
        return rv if isinstance(rv, int) else ExitCode.OK
    except (click.exceptions.Exit, SystemExit) as e:  # --help / --version
        code = getattr(e, "exit_code", getattr(e, "code", 0))
        return int(code or 0)
    except click.UsageError as e:
        click.echo(f"error: {e.format_message()}", err=True)
        return ExitCode.USAGE
    except click.Abort:
        return ExitCode.CANCELLED
    except AppError as e:
        _emit_error(e)
        return e.exit


def _emit_error(e: AppError) -> None:
    if _active is not None and _active.fmt == "json":
        payload = {"error": e.message, "code": e.code, "remediation": e.remediation}
        payload.update(e.extra)
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
    else:
        print(f"error: {e.message}", file=sys.stderr)
        if e.code:
            print(f"  code: {e.code}", file=sys.stderr)
        if e.remediation:
            print(f"  fix:  {e.remediation}", file=sys.stderr)
        for k, val in e.extra.items():
            print(f"  {k}: {val}", file=sys.stderr)


def main() -> None:
    sys.exit(run())
