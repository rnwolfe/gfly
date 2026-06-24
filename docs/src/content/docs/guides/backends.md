---
title: Backends
description: The swappable google (default, no auth) and serpapi (live, keyed) backends.
---

gfly normalizes two data sources behind one stable output contract. Pick with `--backend` (or
`GFLY_BACKEND`).

| Backend | Auth | Data | Notes |
|---|---|---|---|
| `google` *(default)* | **none** | reverse-engineered Google Flights (`fast-flights`) | free, fragile, rate-limited |
| `serpapi` | API key | live SerpApi Google Flights JSON | `multi` is google-only |

## google (default)

Unauthenticated — the agent just runs it. It rides an **undocumented** endpoint, so:

- Periodic breakage surfaces as [`SCHEMA_DRIFT`](/reference/exit-codes/) (exit 21), not silent wrong data.
- CAPTCHA / 429 surfaces as `BLOCKED` (20) / `RATE_LIMITED` (7) with `retryAfterSeconds`.
- `--proxy http://host:port` (or `GFLY_PROXY`) routes around IP blocks.

Field caveats: google exposes **no flight numbers or booking token** (`[]` / `null`) and can't split
best/other (`isBest: false`). For a round-trip, the itinerary describes the **outbound** legs and
`price` is the **round-trip total**.

## serpapi (opt-in)

Live JSON via [SerpApi](https://serpapi.com/google-flights-api) — more reliable, costs a key
(250 free searches/mo). It provides `flightNumbers`, `bookingToken`, and a real best/other split.

```bash
echo "$SERPAPI_KEY" | gfly auth login --backend serpapi --token-stdin
gfly --backend serpapi search JFK LHR --depart 2026-08-15
```

See [Authentication](/guides/authentication/). SerpApi is the **reliability escape hatch** — never
the sole path (it's a third-party paid service with its own ToS).
