<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

# `gfly` ✈

**Google Flights for agents.** A read-only, JSON-first flight-search CLI an LLM can drive — **no API key, no account, no OAuth.**

[![ci](https://github.com/rnwolfe/gfly/actions/workflows/ci.yml/badge.svg)](https://github.com/rnwolfe/gfly/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/rnwolfe/gfly?color=F5B70A&label=release)](https://github.com/rnwolfe/gfly/releases)
[![pypi](https://img.shields.io/pypi/v/gfly?color=F5B70A&label=pypi)](https://pypi.org/project/gfly/)
[![python](https://img.shields.io/badge/python-%E2%89%A53.10-F5B70A)](https://pypi.org/project/gfly/)
[![license](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-2ECC71)](#license)

</div>

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│  ✈  G F L Y · D E P A R T U R E S                              READ-ONLY · NO KEY │
├───────────┬──────────────────────────────┬────────────────────┬─────────────────┤
│  GATE     │  DESTINATION                 │  FLIGHT            │  STATUS         │
├───────────┼──────────────────────────────┼────────────────────┼─────────────────┤
│  search   │  JFK → LHR  itineraries      │  gfly search       │  ● ON TIME      │
│  dates    │  cheapest-day price calendar │  gfly dates        │  ● ON TIME      │
│  multi    │  multi-city journeys         │  gfly multi        │  ● ON TIME      │
│  airports │  resolve IATA codes offline  │  gfly airports     │  ● ON TIME      │
│  doctor   │  health + throttle state     │  gfly doctor       │  ● ON TIME      │
│  schema   │  machine-readable contract   │  gfly schema       │  ● ON TIME      │
└───────────┴──────────────────────────────┴────────────────────┴─────────────────┘
```

<div align="center">

![gfly demo](demo/gfly.gif)

</div>

---

## Why gfly

Google has had **no public flights API since QPX shut down in 2018**. The community tools that fill
the gap are built for *humans* (Rich TUIs) or hand agents an MCP server with a self-declared-unstable
JSON shape. `gfly` is engineered for an **LLM agent in a loop**:

| | `gfly` | the others |
|---|:---:|:---:|
| **JSON by default** (stable, versioned `schemaVersion`) | ✅ | ⚠️ "experimental" |
| **`schema` + embedded `agent` contract** (zero external files) | ✅ | ❌ |
| **Semantic exit codes** for the real failures (`BLOCKED`, `SCHEMA_DRIFT`, `RATE_LIMITED`) | ✅ | ❌ |
| **Token-bounded** output (`--limit`, `--offset`, `--select`) | ✅ | ❌ |
| **Read-only by design** — can't book, can't mutate | ✅ | varies |
| **Persistent politeness throttle** (survives the fresh-process-per-call model) | ✅ | ❌ |
| **Zero auth** on the default backend | ✅ | varies |

> [!NOTE]
> The default backend rides a **reverse-engineered, undocumented** endpoint via
> [`fast-flights`](https://github.com/AWeirdDev/flights). It is fragile by nature and **will** break
> when Google changes its response — that's exactly why gfly surfaces `SCHEMA_DRIFT`/`BLOCKED` as
> structured, actionable errors and ships a swappable [SerpApi](#backends) backend as the reliability
> escape hatch. See [SECURITY.md](SECURITY.md) and [Risks](#risks--tos).

## Try it in 10 seconds (no install, no key)

```bash
uvx gfly search JFK LHR --depart 2026-08-15
```

That's the whole onboarding. No account, no API key — the agent (or you) just runs it.

## Install

| Method | Command |
|---|---|
| **uv** (recommended) | `uv tool install gfly` |
| **uvx** (zero-install trial) | `uvx gfly search JFK LHR --depart 2026-08-15` |
| **pipx** | `pipx install gfly` |
| **pip** | `pip install gfly` |

Requires Python ≥ 3.10. Ships `fast-flights` (google engine) + offline IATA data; the `serpapi`
backend needs no extra dependency.

## Quickstart

```bash
# one-way, cheapest first — JSON straight into jq
gfly search JFK LHR --depart 2026-08-15 --sort price --json \
  | jq '.itineraries[] | {price, airlines, stops, durationMinutes}'

# round-trip, business, nonstop only
gfly search SFO NRT --depart 2026-09-10 --return 2026-09-24 --cabin business --stops nonstop

# cheapest day to fly across a window (one search per day — keep it small)
gfly dates JFK LHR --depart-range 2026-08-01..2026-08-07

# multi-city
gfly multi --leg JFK:CDG:2026-08-01 --leg CDG:FCO:2026-08-05 --leg FCO:JFK:2026-08-12

# resolve airports offline (don't make the agent guess codes)
gfly airports search "london"

# paginate: page 2
gfly search JFK LHR --depart 2026-08-15 --limit 5 --offset 5 --json
```

**Output discipline:** data on **stdout**, every note/warning/error on **stderr** — so a pipe stays
clean. At a TTY you get readable tables; piped or `--json`, you get the stable envelope.

## Backends

| Backend | Auth | Data | Notes |
|---|---|---|---|
| `google` *(default)* | **none** | reverse-engineered Google Flights | free, fragile, rate-limited; `--proxy` routes around IP blocks |
| `serpapi` | API key | live SerpApi JSON | `multi` is google-only; set the key once (below) |

```bash
echo "$SERPAPI_KEY" | gfly auth login --backend serpapi --token-stdin   # → OS keyring
gfly --backend serpapi search JFK LHR --depart 2026-08-15
```

## Authenticate (only if you choose `serpapi`)

`gfly` follows the `gh` model. The `google` backend needs **nothing**.

```bash
gfly auth login  --backend serpapi --token-stdin   # secret via STDIN, never argv
gfly auth status --backend serpapi                 # tests + redacts; non-zero on problems
gfly auth logout --backend serpapi                 # removes LOCAL credential only
```

- **Storage order:** `GFLY_SERPAPI_KEY` env → OS keyring → `0600` XDG file fallback (a warning prints
  if perms can't be secured). Secrets are **never** accepted via flags (they'd leak to `ps`/`/proc`).
- **Revocation** is separate from logout — rotate the key at [serpapi.com](https://serpapi.com/manage-api-key).
- Run **`gfly doctor`** anytime to check auth, keyring, connectivity, and throttle state.

## Rate limits & not getting banned

The `google` backend is scraped, so the #1 controllable ban vector is **request rate**. `gfly` ships a
**persistent, cross-process politeness throttle** (default `--min-interval 12`s) — because an agent
invokes the CLI as a fresh process each call, the throttle state lives on disk, not in memory.

It **fails fast** rather than hanging: when a request would be too soon, you get a structured error with
`retryAfterSeconds` — not a silent multi-minute sleep (which would deadlock an agent loop).

```bash
gfly search JFK LHR --depart 2026-08-15 --wait          # opt INTO blocking until clear
gfly search JFK LHR --depart 2026-08-15 --min-interval 0 # disable (riskier)
gfly --backend serpapi ...                               # the reliability escape hatch
```

Politeness reduces ban risk; it doesn't eliminate it (datacenter IPs can be CAPTCHA'd regardless) —
that's what `--proxy` and `serpapi` are for.

## GATE STATUS — exit codes

A first-class contract. `gfly schema` always prints the authoritative table.

```text
┌──────┬──────────────────┬──────┬───────────────────────────────────────────────┐
│ CODE │ NAME             │ CODE │ NAME                                          │
├──────┼──────────────────┼──────┼───────────────────────────────────────────────┤
│  0   │ ok               │  8   │ retryable (transient network)                 │
│  2   │ usage / parse    │ 10   │ config error                                  │
│  3   │ empty results    │ 13   │ input required (--no-input hit a prompt)      │
│  4   │ auth required    │ 20   │ BLOCKED  (CAPTCHA/soft-block; retryAfter)     │
│  5   │ not found        │ 21   │ SCHEMA_DRIFT (upstream parse broke)           │
│  7   │ rate limited     │ 130  │ cancelled (SIGINT)                            │
└──────┴──────────────────┴──────┴───────────────────────────────────────────────┘
```

Errors are structured on stderr: `{ "error", "code", "remediation" }` (+ `retryAfterSeconds` on
throttle/block), so an agent can back off, switch backend, or report instead of crashing.

## For agents

```bash
gfly agent        # prints the embedded SKILL.md — the full usage contract, in the binary
gfly schema       # command tree + flags + exit codes + live safety/throttle state + env vars
```

Itinerary fields are an **append-only** contract: `price`, `currency`, `airlines[]`,
`flightNumbers[]`, `durationMinutes`, `stops`, `layovers[]{airport,minutes}`, `departure`, `arrival`,
`origin`, `destination`, `co2Grams`, `co2DeltaPct`, `isBest`, `bookingToken`. Third-party text is
fenced as untrusted by default (`--no-wrap-untrusted` to disable).

## Risks & ToS

- The default backend uses an **unofficial, undocumented** endpoint. Expect periodic breakage
  (surfaced as `SCHEMA_DRIFT`) and rate-limiting/CAPTCHA (surfaced as `BLOCKED`). Pin the version.
- `gfly` is **read-only** — it searches, it cannot book.
- The `serpapi` backend is a third-party paid service with its own ToS; it's a fallback, never the
  sole path. See [SECURITY.md](SECURITY.md) for the credential threat model.

## Development

```bash
uv sync --extra dev
uv run pytest -q          # contract + behavior tests (incl. the schema-snapshot gate)
vhs demo/gfly.tape        # regenerate the demo GIF
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## License

Dual-licensed under either of [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE) at your option.
