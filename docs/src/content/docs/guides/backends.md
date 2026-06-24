---
title: Backends
description: How gfly's two swappable data sources differ, what each one gives you, and when to switch.
owner: rnwolfe
lastReviewed: 2026-06-24
sidebar:
  order: 2
---

gfly normalizes two data sources behind one stable output contract. You pick one with `--backend`
(or `GFLY_BACKEND`); the fields, exit codes, and JSON envelope stay identical either way.

| | `google` (default) | `serpapi` (opt-in) |
|---|---|---|
| **Auth** | none | API key required |
| **Source** | reverse-engineered Google Flights endpoint via `fast-flights` | SerpApi's live Google Flights JSON over HTTPS |
| **`flightNumbers`** | always `[]` | populated |
| **`bookingToken`** | always `null` | populated |
| **`isBest`** | always `false` | `true` for best-flights group |
| **Round-trip price** | round-trip total, outbound legs only | per direction |
| **`multi` command** | supported | **not supported** |
| **Throttle** | yes — see [Rate Limits](/guides/rate-limits/) | exempt |
| **Reliability** | breaks when Google changes its endpoint | stable paid API |

---

## google (default)

The default backend requires no credentials. It sends a base64-encoded protobuf query (`tfs`) to an
**undocumented** Google Flights endpoint and parses the response via the
[`fast-flights`](https://github.com/AWeirdDev/flights) v3 library.

```bash
# No setup needed — just run it.
gfly search JFK LHR --depart 2026-08-15
```

Because this rides a reverse-engineered internal API, breakage is an inherent risk:

- **`SCHEMA_DRIFT` (exit 21)** — the upstream response no longer parses. The library has drifted.
  Upgrade `gfly` (and `fast-flights`), switch to `--backend serpapi`, or
  [file an issue](https://github.com/rnwolfe/gfly/issues).
- **`BLOCKED` (exit 20)** — Google served a CAPTCHA or soft-block. The circuit breaker opens and
  returns `retryAfterSeconds`. Back off, then retry; or switch to serpapi.
- **`RATE_LIMITED` (exit 7)** — the local politeness throttle (default 12 s minimum interval)
  fired before a network call was made.

:::caution
When the `fast-flights` library drifts, gfly raises a `SCHEMA_DRIFT` error (exit 21) — the
response no longer parses and no results are returned. Always pin a working `gfly` version in
production pipelines.
:::

### Field caveats

The undocumented endpoint does not expose every field the normalized contract defines:

- **`flightNumbers`** is always `[]`. The upstream does not return individual flight numbers.
- **`bookingToken`** is always `null`. Deep-link tokens are not available.
- **`isBest`** is always `false`. The endpoint does not distinguish a "best flights" group from
  other results.
- **Round-trip itineraries** describe the **outbound** legs only. The `price` field is the
  **round-trip total** (both legs combined), not just the outbound fare.

If your downstream code depends on any of these fields, use `--backend serpapi`.

### Routing around IP blocks

The `--proxy` flag (or `GFLY_PROXY`) passes a proxy URL to the underlying `fast-flights` call.
This helps when your machine's IP is already flagged (datacenter IPs are often pre-blocked):

```bash
gfly --proxy http://user:pass@proxy.example.com:3128 search JFK LHR --depart 2026-08-15
```

:::note
A proxy reduces IP-reputation risk; it does not eliminate bot-fingerprint or TLS-fingerprint
detection. serpapi is the reliable escape hatch for sustained automation.
:::

---

## serpapi (opt-in)

[SerpApi](https://serpapi.com/google-flights-api) is a commercial scraping platform that exposes
Google Flights as a clean JSON API. gfly uses only Python's stdlib `urllib` — no extra dependency
is installed.

```bash
# Store the key once (OS keyring or 0600 file fallback):
echo "$SERPAPI_KEY" | gfly auth login --token-stdin

# Or export for a single session:
export GFLY_SERPAPI_KEY=your_key_here

# Then run any search command normally:
gfly --backend serpapi search JFK LHR --depart 2026-08-15
```

SerpApi provides **250 free searches per month**; paid plans scale beyond that. See
[Authentication](/guides/authentication/) for how the key is stored and resolved.

### What serpapi adds

Because SerpApi parses the structured JSON response rather than a raw protobuf:

- **`flightNumbers`** — each leg's carrier code and number (e.g. `["BA 117"]`).
- **`bookingToken`** — an opaque string you can hand back to Google Flights to pre-fill a booking
  form. gfly is read-only and never follows this link itself.
- **`isBest: true`** — flights in SerpApi's `best_flights` group are marked; the rest have
  `isBest: false`. This lets your code sort or filter by Google's own "best" heuristic.

### Limits

- **`multi` is not supported on serpapi.** The `gfly multi` command requires `--backend google`
  (the default). Passing `--backend serpapi` to `multi` exits with `UNSUPPORTED` (exit 10).
- serpapi is a **third-party paid service** with its own Terms of Service. It is the reliability
  escape hatch — treat it as such, not as a replacement for the free google backend in all cases.

---

## Switching backends

### Per-command

```bash
gfly --backend serpapi search JFK LHR --depart 2026-08-15
gfly --backend google  search JFK LHR --depart 2026-08-15  # explicit default
```

### Per-session or globally

```bash
export GFLY_BACKEND=serpapi
gfly search JFK LHR --depart 2026-08-15   # uses serpapi for all commands
```

:::tip
Add `GFLY_BACKEND=serpapi` to your shell profile or `.env` file when you want serpapi as the
persistent default for a project, without typing `--backend` every time.
:::

---

## How breakage surfaces

Both backends map upstream failures to the same structured error on stderr, with a machine-readable
`code` and `retryAfterSeconds` where relevant:

```json
{
  "error": "upstream is blocking requests (CAPTCHA/soft-block); cooling down ~120s",
  "code": "BLOCKED",
  "remediation": "back off and retry later, switch --backend serpapi, or supply GFLY_ABUSE_COOKIE",
  "retryAfterSeconds": 120
}
```

| Situation | Exit | Code | Backend |
|---|---|---|---|
| CAPTCHA / soft-block from Google | 20 | `BLOCKED` | google only |
| Response no longer parses | 21 | `SCHEMA_DRIFT` | google only |
| Throttle interval not elapsed | 7 | `RATE_LIMITED` | google only |
| SerpApi 429 | 7 | `RATE_LIMITED` | serpapi only |
| SerpApi 401 / missing key | 4 | `AUTH_REQUIRED` | serpapi only |
| `multi` called with serpapi | 10 | `UNSUPPORTED` | serpapi only |

Agents should parse the `code` field to decide whether to retry, switch backends, or escalate.
See [Exit Codes](/reference/exit-codes/) for the full table and [For Agents](/reference/for-agents/)
for retry-loop patterns.

---

## Checking backend health

`gfly doctor` probes each configured backend and reports reachability. For google it runs a real
(throttle-exempt) search; for serpapi it checks whether a key is present without burning quota:

```bash
gfly doctor
```

---

## Choosing a backend

Use `google` (the default) for:
- Quick one-off searches with no setup.
- Multi-city itineraries (`gfly multi`).
- Situations where a CAPTCHA or drift is tolerable (you can catch exit 20/21 and retry).

Use `serpapi` when:
- You need `flightNumbers` or `bookingToken` in every record.
- You need the `isBest` flag to be meaningful.
- You are running sustained automation where CAPTCHA risk is unacceptable.
- The google backend has just drifted and a fix isn't yet released.

:::note
serpapi's reliability advantage is real, but its 250 free requests/month limit makes it unsuitable
as the sole backend for high-volume pipelines. Design your agent to default to google and fall back
to serpapi on `BLOCKED` or `SCHEMA_DRIFT`.
:::
