---
title: Searching flights
description: Complete reference for the search, dates, multi, and airports commands — every flag, default, and gotcha.
owner: rnwolfe
lastReviewed: 2026-06-24
sidebar:
  order: 1
---

All gfly commands are **reads** — it searches Google Flights, it never books or mutates anything.

## `search` — one-way and round-trip

```bash
gfly search <FROM> <TO> --depart YYYY-MM-DD [--return YYYY-MM-DD] [flags]
```

`FROM` and `TO` are IATA airport codes (case-insensitive — `jfk` becomes `JFK`). Use
[`airports search`](#airports-search--resolve-iata-codes) if you need to look one up.

### Required flag

`--depart` is the only required flag. Omitting it exits with code `2` (USAGE) before any network
call is made. Combine with `--return` for a round-trip.

:::caution[Round-trip prices on the google backend]
When you add `--return`, the google backend describes the **outbound legs only** and the `price`
field is the **round-trip total** (not one direction). The serpapi backend returns a proper per-itinerary breakdown.
:::

### All flags

| Flag | Values | Default | Notes |
|---|---|---|---|
| `--depart` | `YYYY-MM-DD` | — | **Required.** Outbound date. |
| `--return` | `YYYY-MM-DD` | — | Omit for one-way. |
| `--adults` | integer ≥ 1 | `1` | At least one adult is always required. |
| `--children` | integer ≥ 0 | `0` | |
| `--infants` | integer ≥ 0 | `0` | |
| `--cabin` | `economy` · `premium` · `business` · `first` | `economy` | |
| `--stops` | `any` · `nonstop` · `1` | `any` | |
| `--sort` | `best` · `price` · `duration` | `best` | `price` and `duration` are sorted client-side after the fetch; `best` preserves the upstream order. |
| `--currency` | ISO code | `USD` | Also reads `GFLY_CURRENCY`. |

Date and passenger flags are validated **before** any network call. A bad date string or
`--adults 0` exits immediately with code `2` (USAGE) — no quota is consumed.

### Examples

```bash
# One-way, defaults
gfly search JFK LHR --depart 2026-08-01

# Round-trip, business class, JSON output
gfly search SFO NRT --depart 2026-09-10 --return 2026-09-24 --cabin business --json

# Nonstop only, sorted by price, two adults
gfly search LAX CDG --depart 2026-07-15 --stops nonstop --sort price --adults 2

# Pipe to jq — JSON is the default when stdout is not a TTY
gfly search ORD LHR --depart 2026-08-20 | jq '.itineraries[0]'

# Override backend for more reliable data (requires SerpApi key)
gfly search JFK LHR --depart 2026-08-01 --backend serpapi --json
```

### Backend differences for `search`

| Field | `google` (default) | `serpapi` |
|---|---|---|
| `flightNumbers` | `[]` (not exposed) | populated |
| `bookingToken` | `null` (not exposed) | populated |
| `isBest` | always `false` | `true` for best flights |
| Auth required | none | API key |

See [Backends](/guides/backends/) for a full comparison.

---

## `dates` — cheapest price per day

```bash
gfly dates <FROM> <TO> --depart-range START..END
```

Builds a price calendar: the cheapest one-way economy fare for each departure date in the window.

### How it works

No upstream API exposes a date grid, so gfly runs **one search per day** across your window. On the
`google` backend it paces these requests politely — one per `--min-interval` (default `12s`) — so a
10-day window takes roughly two minutes. Results are sorted by price (cheapest first) before output.

### Flags

| Flag | Values | Default | Notes |
|---|---|---|---|
| `--depart-range` | `YYYY-MM-DD..YYYY-MM-DD` | — | **Required.** Inclusive start..end. |

All [global flags](/reference/commands/) apply, including `--backend`, `--currency`, `--min-interval`,
`--no-throttle`, and `--proxy`.

:::caution[30-day cap]
The window is capped at **30 days**. If your range is wider, gfly logs a note to stderr and scans
only the first 30 days.
:::

### Partial results on rate limit or block

If gfly hits a `BLOCKED` or `RATE_LIMITED` error mid-scan and has already gathered at least one day,
it stops early and returns the days gathered so far. The envelope includes:

```json
{
  "partial": true,
  "failedAt": "2026-08-12",
  "reason": "BLOCKED"
}
```

If the block happens on the very first day (nothing salvaged), the error is surfaced as a normal
structured error instead. Resume by adjusting `--depart-range` to start from `failedAt`.

### Examples

```bash
# Scan 10 days, JSON output
gfly dates JFK LHR --depart-range 2026-08-01..2026-08-10 --json

# Faster with serpapi (no pacing needed — serpapi is throttle-exempt)
gfly dates JFK LHR --depart-range 2026-08-01..2026-08-30 --backend serpapi --json

# Disable pacing (risky on google — may trigger blocks)
gfly dates JFK LHR --depart-range 2026-08-01..2026-08-07 --no-throttle

# See the estimated time before it starts
gfly dates SFO LHR --depart-range 2026-09-01..2026-09-14
# → stderr: "scanning 14 day(s) = 14 upstream request(s), paced ~12s apart (~156s total)"
```

---

## `multi` — multi-city

```bash
gfly multi --leg FROM:TO:DATE --leg FROM:TO:DATE [--leg ...] [flags]
```

Search multi-city itineraries across two or more legs in one query.

:::caution[google backend only]
Multi-city is **not supported on the serpapi backend**. Passing `--backend serpapi` exits with
exit code `10` (config error). The default `google` backend is used automatically.
:::

### Leg format

Each `--leg` is `FROM:TO:DATE` — origin code, destination code, and departure date joined by colons:

```
--leg JFK:CDG:2026-08-01
```

You must pass `--leg` at least **twice** (minimum two legs). The legs are processed in order.

### Flags

| Flag | Values | Default | Notes |
|---|---|---|---|
| `--leg` | `FROM:TO:DATE` | — | **Repeatable, required.** At least 2. |
| `--adults` | integer ≥ 1 | `1` | |
| `--children` | integer ≥ 0 | `0` | |
| `--infants` | integer ≥ 0 | `0` | |
| `--cabin` | `economy` · `premium` · `business` · `first` | `economy` | |
| `--stops` | `any` · `nonstop` · `1` | `any` | |

Date and passenger validation happens **before** any network call (same early-exit behaviour as
`search`).

### Examples

```bash
# Three-city trip: New York → Paris → Tokyo
gfly multi \
  --leg JFK:CDG:2026-08-01 \
  --leg CDG:NRT:2026-08-10 \
  --leg NRT:JFK:2026-08-20 \
  --json

# Two legs, business class
gfly multi \
  --leg SFO:LHR:2026-09-05 \
  --leg LHR:SFO:2026-09-15 \
  --cabin business --json
```

---

## `airports search` — resolve IATA codes

```bash
gfly airports search <query>
```

Look up airports by city name, airport name, or IATA code. This is the right way for an agent
(or a human) to turn "london" into `LHR`, `LGW`, `STN`, `LCY`, or `LTN` before passing a code to
`search`.

### How it works

The lookup is **fully offline** — it searches the bundled `airportsdata` dataset (~7.9 k airports)
with no network call and no throttle. Matching priority:

1. Exact 3-letter IATA code
2. Code prefix
3. City substring
4. Airport name substring

Returns `iata`, `name`, `city`, and `country` per record.

### Examples

```bash
# Find airports in London
gfly airports search london

# Exact code lookup
gfly airports search NRT

# City name (case-insensitive)
gfly airports search tokyo

# JSON for scripting
gfly airports search paris --json | jq '.[].iata'
```

Sample output (table at a TTY):

```
IATA  Name                               City    Country
LHR   Heathrow Airport                   London  GB
LGW   Gatwick Airport                    London  GB
STN   London Stansted Airport            London  GB
LCY   London City Airport                London  GB
LTN   London Luton Airport               Luton   GB
```

:::tip[Always resolve before searching]
Agents should call `gfly airports search <city>` before `gfly search` whenever the airport code is
not certain. The offline lookup costs zero quota and prevents cryptic "no results" errors caused
by a wrong code.
:::

---

## Flags shared by all search commands

These global flags work on `search`, `dates`, `multi`, and `airports search`:

| Flag | Default | Notes |
|---|---|---|
| `--backend` | `google` | `google` or `serpapi`. Also `GFLY_BACKEND`. |
| `--currency` | `USD` | ISO code. Also `GFLY_CURRENCY`. |
| `--format` / `--json` | plain at TTY, JSON otherwise | Output format: `json`, `plain`, `tsv`. |
| `--limit` | `25` | Max records per page. |
| `--offset` | `0` | Skip N records; pass the prior `nextCursor` to paginate. |
| `--select` | — | Comma-separated dot-path projection applied to each record. |
| `--min-interval` | `12.0` | Seconds between google requests. Also `GFLY_MIN_INTERVAL`. |
| `--wait` | off | Block until throttle clears (up to `--max-wait`). |
| `--max-wait` | `60` | Cap for `--wait`, in seconds. |
| `--no-throttle` | off | Bypass pacing entirely. Also `GFLY_NO_THROTTLE`. |
| `--proxy` | — | HTTP(S) proxy URL for the google backend. Also `GFLY_PROXY`. |
| `--no-wrap-untrusted` | off | Disable sanitization of third-party free text fields. |

---

## Output format

By default, gfly prints a human-readable table at a TTY and switches to the stable JSON envelope
when stdout is piped or captured. Use `--json` (or `--format json`) to force JSON anywhere.

The JSON envelope for `search` and `multi` looks like:

```json
{
  "schemaVersion": "1",
  "backend": "google",
  "query": { "from": "JFK", "to": "LHR", "depart": "2026-08-01", ... },
  "_warning": "fields below originate from a third party ...",
  "currency": "USD",
  "count": 42,
  "offset": 0,
  "itineraries": [ ... ],
  "nextCursor": "25"
}
```

`nextCursor` is the value to pass as `--offset` for the next page, or `null` when you have
reached the end. `count` is the total number of results, not the number in the current page.

See [Output schema](/reference/output-schema/) for the full itinerary field reference and
[For agents](/reference/for-agents/) for pagination guidance.
