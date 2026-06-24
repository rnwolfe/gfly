---
title: Commands
description: Exhaustive reference for every gfly command, flag, and environment variable.
owner: rnwolfe
lastReviewed: 2026-06-24
sidebar:
  order: 1
---

Every command is a **read**. gfly cannot book or modify anything. Run `gfly schema` at any
time for a machine-readable snapshot of the full command tree, exit codes, and live throttle
state.

## Command overview

| Command | Description |
|---|---|
| [`gfly search`](#search) | One-way or round-trip itinerary search |
| [`gfly dates`](#dates) | Cheapest price per departure date over a window |
| [`gfly multi`](#multi) | Multi-city search across two or more legs (google backend only) |
| [`gfly airports search`](#airports-search) | Offline IATA code resolution |
| [`gfly auth login`](#auth-login) | Store a SerpApi key or abuse cookie |
| [`gfly auth status`](#auth-status) | Show credential status for the active backend |
| [`gfly auth logout`](#auth-logout) | Remove the locally stored credential |
| [`gfly doctor`](#doctor) | Auth, keyring, connectivity, and throttle health check |
| [`gfly schema`](#schema) | Machine-readable command tree + exit codes + live state |
| [`gfly agent`](#agent) | Print the embedded SKILL.md (agent usage contract) |
| [`gfly version`](#version) | Print version as JSON (`gfly --version` / `-V` prints bare string) |

---

## Global flags

Every flag below is accepted by **every command**, and can appear in any position on the
command line (e.g. `gfly search JFK LHR --depart 2026-08-01 --json`). Values are merged
leaf-first across the Click context chain.

### Output

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--format json\|plain\|tsv` | choice | auto | Output format. Defaults to `json` when stdout is not a TTY; `plain` (table) at a TTY. |
| `--json` | flag | — | Shorthand for `--format json`. |
| `--no-color` | flag | — | Disable colored output. Also honored via `NO_COLOR` env var. |

### Token bounding and pagination

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--limit N` | int | 25 | Maximum records per page. |
| `--offset N` | int | 0 | Skip N records. Pass the prior response's `nextCursor` value to fetch the next page. |
| `--select a,b.c` | string | — | Comma-separated dot-path projections applied to each record before output. |

### Backend and pricing

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--backend google\|serpapi` | choice | `google` | Data source. `google` needs no auth; `serpapi` needs a key and provides richer data. See [Backends](/guides/backends/). |
| `--currency CODE` | string | `USD` | ISO 4217 currency code for prices. |

### Throttle and network

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--min-interval SECS` | float | `12.0` | Minimum seconds between google backend requests (politeness). Ignored for serpapi. |
| `--wait` | flag | — | Block and sleep until the throttle clears instead of failing fast. |
| `--max-wait SECS` | float | `60.0` | Maximum seconds to block when `--wait` is set. |
| `--no-throttle` | flag | — | Bypass the politeness throttle entirely. Risky — may trigger a CAPTCHA or IP block. |
| `--proxy URL` | string | — | HTTP(S) proxy URL for the google backend (helps with IP-reputation blocks). |

### Prompt-injection hardening

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--wrap-untrusted` / `--no-wrap-untrusted` | bool flag | on | Fence third-party free text (airline names, fare brands, layover labels) by stripping control characters and capping length. An `_warning` key is added to the JSON envelope when active. Disable with `--no-wrap-untrusted`. |

### Agent contract flags (no-ops for gfly)

The flags below exist for **contract uniformity** — a standard CLI surface that agents and
orchestrators can safely pass without knowing whether the underlying tool mutates anything.
Because gfly is read-only, they are accepted and silently ignored.

| Flag | Purpose |
|---|---|
| `--allow-mutations` | Mutation gate (no mutating commands exist today). |
| `--dry-run` | Preview mode (no-op; nothing is written). |
| `--yes` | Auto-confirm prompts (no-op; no destructive prompts exist). |
| `--force` | Override safety checks (no-op). |
| `--no-input` | Never prompt interactively; fail with exit 13 (`INPUT_REQUIRED`) instead. |
| `--concise` | Accepted; no effect today. |
| `--detailed` | Accepted; no effect today. |

:::note
`--allow-mutations` / `--dry-run` / `--yes` / `--force` will remain no-ops as long as gfly
is read-only. The contract guarantees they do not accidentally enable anything dangerous.
:::

---

## `--version` / `-V` vs `gfly version`

| Invocation | Output | Exit |
|---|---|---|
| `gfly --version` or `gfly -V` | Bare version string (e.g. `0.1.0`) to stdout | 0 |
| `gfly version` | JSON object: `{"version": "0.1.0"}` in the stable envelope | 0 |

Use `gfly version` when you need parseable output in a pipeline. Use `-V` / `--version` for
quick human checks.

---

## Commands

### `search`

Search itineraries between two airports (one-way or round-trip).

```bash
gfly search <ORIGIN> <DEST> --depart YYYY-MM-DD [options]
```

**Arguments**

| Argument | Description |
|---|---|
| `ORIGIN` | Departure airport IATA code (case-insensitive). |
| `DEST` | Arrival airport IATA code (case-insensitive). |

**Options**

| Flag | Type | Default | Required | Description |
|---|---|---|---|---|
| `--depart DATE` | YYYY-MM-DD | — | yes | Outbound date. Validated before any network call; bad dates exit 2 (`USAGE`). |
| `--return DATE` | YYYY-MM-DD | — | no | Return date (omit for one-way). |
| `--adults N` | int | `1` | no | Number of adult passengers (minimum 1). |
| `--children N` | int | `0` | no | Number of child passengers. |
| `--infants N` | int | `0` | no | Number of infant passengers (in-seat). |
| `--cabin economy\|premium\|business\|first` | choice | `economy` | no | Cabin class. |
| `--stops any\|nonstop\|1` | choice | `any` | no | Stop filter. |
| `--sort best\|price\|duration` | choice | `best` | no | Sort order applied after fetch. `best` preserves backend order; `price` and `duration` sort ascending. |

**Examples**

```bash
# One-way, all defaults
gfly search JFK LHR --depart 2026-08-01

# Round-trip, business class, piped to jq
gfly search SFO NRT --depart 2026-09-10 --return 2026-09-24 --cabin business --json | jq '.itineraries[0]'

# Nonstop only, cheapest first, serpapi backend
gfly search ORD CDG --depart 2026-07-15 --stops nonstop --sort price --backend serpapi

# Paginate: page 2 (records 25–50)
gfly search JFK LAX --depart 2026-08-01 --offset 25
```

:::caution
On the `google` backend, round-trip results describe the **outbound legs only**. The `price`
field is the **round-trip total**, not a one-way fare. `flightNumbers` is always `[]` and
`bookingToken` is always `null`. Use `--backend serpapi` for those fields.
:::

**See also:** [Searching flights](/guides/searching/), [Backends](/guides/backends/)

---

### `dates`

Price calendar: cheapest fare per departure date over a window.

```bash
gfly dates <ORIGIN> <DEST> --depart-range START..END [options]
```

No upstream exposes a date grid, so gfly runs **one search per day**. On the `google`
backend these are paced at `--min-interval` apart — a 30-day window takes roughly 6 minutes.

**Arguments**

| Argument | Description |
|---|---|
| `ORIGIN` | Departure airport IATA code. |
| `DEST` | Arrival airport IATA code. |

**Options**

| Flag | Type | Required | Description |
|---|---|---|---|
| `--depart-range START..END` | `YYYY-MM-DD..YYYY-MM-DD` | yes | Inclusive date window. Capped at 30 days. |

All global flags apply, including `--min-interval`, `--no-throttle`, and `--backend`.

**Behavior**

- Window is capped at 30 days; a note is printed to stderr if truncated.
- If a `BLOCKED` or `RATE_LIMITED` error occurs mid-scan, the partial results gathered so far
  are returned with `partial: true`, `failedAt`, and `reason` in the envelope.
- Results are sorted ascending by price.
- `serpapi` backend is exempt from pacing (`--min-interval` is ignored for serpapi).

**Example**

```bash
# Price scan across 10 days, JSON output
gfly dates JFK CDG --depart-range 2026-08-01..2026-08-10 --json

# Faster scan with serpapi (uses quota, no throttle)
gfly dates LHR SIN --depart-range 2026-09-01..2026-09-07 --backend serpapi
```

---

### `multi`

Multi-city search across two or more legs.

```bash
gfly multi --leg FROM:TO:DATE --leg FROM:TO:DATE [options]
```

:::caution
**Google backend only.** Passing `--backend serpapi` raises a `CONFIG` error (exit 10).
:::

**Options**

| Flag | Type | Required | Description |
|---|---|---|---|
| `--leg FROM:TO:DATE` | string | yes (×2+) | A single leg. Repeatable; order matters. Minimum 2 legs. |
| `--adults N` | int | no | Default `1`. |
| `--children N` | int | no | Default `0`. |
| `--infants N` | int | no | Default `0`. |
| `--cabin economy\|premium\|business\|first` | choice | no | Default `economy`. |
| `--stops any\|nonstop\|1` | choice | no | Default `any`. |

**Example**

```bash
gfly multi \
  --leg JFK:CDG:2026-08-01 \
  --leg CDG:FCO:2026-08-08 \
  --leg FCO:JFK:2026-08-15 \
  --cabin economy --json
```

---

### `airports search`

Resolve airports by city name, airport name, or IATA code. **Offline** — uses the bundled
`airportsdata` package (~7,900 airports). Not throttled.

```bash
gfly airports search <QUERY>
```

**Arguments**

| Argument | Description |
|---|---|
| `QUERY` | Free-text query (city, name, or code). Case-insensitive. |

**Returns** a list of `airports` records, each with: `iata`, `name`, `city`, `country`.

**Examples**

```bash
gfly airports search london
gfly airports search "new york" --json
gfly airports search NRT
```

---

### `auth login`

Store a SerpApi key or a `GOOGLE_ABUSE_EXEMPTION` cookie. Credentials are read from **stdin
only** — never from command-line arguments (to avoid shell history exposure).

```bash
echo "$SERPAPI_KEY" | gfly auth login --backend serpapi --token-stdin
echo "$COOKIE"      | gfly auth login --backend google  --abuse-cookie-stdin
```

**Options**

| Flag | Description |
|---|---|
| `--token-stdin` | Read the SerpApi API key from stdin. |
| `--abuse-cookie-stdin` | Read a `GOOGLE_ABUSE_EXEMPTION` cookie value from stdin (CAPTCHA recovery). |

At least one of `--token-stdin` or `--abuse-cookie-stdin` is required. Credentials are stored
in the OS keyring, with a `0600` file at `$XDG_CONFIG_HOME/gfly/credentials` as fallback on
headless systems. See [Authentication](/guides/authentication/).

---

### `auth status`

Show the credential state for the active backend. Stored values are **redacted** in output.

```bash
gfly auth status
gfly auth status --backend serpapi --json
```

Exits 4 (`AUTH_REQUIRED`) if the `serpapi` backend is selected and no key is found.

---

### `auth logout`

Remove the locally stored credential. **Does not revoke** the key at the provider — visit
[serpapi.com/manage-api-key](https://serpapi.com/manage-api-key) to do that.

```bash
gfly auth logout --backend serpapi
```

---

### `doctor`

Diagnose your setup: backend selection, auth, keyring availability, live connectivity, and
throttle / circuit-breaker state.

```bash
gfly doctor
gfly doctor --no-check-connectivity   # skip the live upstream probe
gfly doctor --json                     # machine-readable for CI
```

**Options**

| Flag | Default | Description |
|---|---|---|
| `--check-connectivity / --no-check-connectivity` | on | Probe the upstream. For `google` this runs a real (throttle-exempt) search; for `serpapi` it only checks key presence (no quota consumed). Skipped automatically when a cooldown is active. |

Exits 10 (`CONFIG_ERROR`) if any check fails. The JSON payload includes per-check `ok`,
`detail`, and `fix` fields.

---

### `schema`

Print the full machine-readable command schema as JSON. Useful for agents that need to
introspect gfly's capabilities at runtime.

```bash
gfly schema
gfly schema | jq '.exit_codes'
gfly schema | jq '.env'
```

Output includes: `tool`, `version`, `schemaVersion`, `commands` (Click info dict),
`exit_codes`, `safety` flags, `throttle` state snapshot, and `env` variable descriptions.

---

### `agent`

Print the bundled `SKILL.md` — the plain-text agent usage contract describing how an LLM
orchestrator should invoke gfly correctly.

```bash
gfly agent
gfly agent > skill.md
```

---

### `version`

Print the version as a JSON object.

```bash
gfly version
# {"version": "0.1.0"}
```

For a bare string (e.g. in shell scripts), use `gfly --version` or `gfly -V`.

---

## Environment variables

All variables are also listed under `env` in `gfly schema`.

| Variable | Description |
|---|---|
| `GFLY_BACKEND` | Default backend (`google` or `serpapi`). Overridden by `--backend`. |
| `GFLY_CURRENCY` | Default ISO currency for prices. Overridden by `--currency`. |
| `GFLY_MIN_INTERVAL` | Default politeness interval in seconds (float). Overridden by `--min-interval`. |
| `GFLY_NO_THROTTLE` | Set to `1`, `true`, `yes`, or `on` to bypass the throttle. Overridden by `--no-throttle`. |
| `GFLY_PROXY` | HTTP(S) proxy URL for the `google` backend. Overridden by `--proxy`. |
| `GFLY_SERPAPI_KEY` | SerpApi API key. Checked before the OS keyring and credential file. |
| `GFLY_ABUSE_COOKIE` | `GOOGLE_ABUSE_EXEMPTION` cookie value for CAPTCHA recovery. |
| `GFLY_STATE_DIR` | Override the throttle state directory (default: `$XDG_STATE_HOME/gfly/`). |
| `NO_COLOR` | Standard no-color convention. Disables colored terminal output. |

---

## Exit codes

A quick summary for reference; the canonical table is at [Exit codes](/reference/exit-codes/).

| Code | Name | Common cause |
|---|---|---|
| 0 | `ok` | Success |
| 2 | `usage` | Bad flag / argument (e.g. invalid date, missing `--depart`) |
| 3 | `empty_results` | No flights found for the query |
| 4 | `auth_required` | `serpapi` backend selected but no key found |
| 7 | `rate_limited` | Politeness throttle or upstream 429 |
| 10 | `config_error` | `doctor` check failed; `multi` on serpapi |
| 13 | `input_required` | `--no-input` set and a required credential is missing |
| 20 | `blocked` | CAPTCHA / soft-block; circuit breaker open |
| 21 | `schema_drift` | Upstream response changed and could not be parsed |
| 130 | `cancelled` | Ctrl-C |

Structured errors are emitted to **stderr** as `{ "error", "code", "remediation" }` (with
`retryAfterSeconds` on `rate_limited` and `blocked`). Data always goes to **stdout**.
