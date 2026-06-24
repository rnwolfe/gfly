---
title: Quickstart
description: Search flights, paginate, and pipe gfly's JSON into jq in under a minute.
---

The default backend is unauthenticated — no setup. Output is **data on stdout, notes/errors on
stderr**: at a TTY you get readable tables; piped or with `--json`, you get the stable envelope.

## One-way, cheapest first

```bash
gfly search JFK LHR --depart 2026-08-15 --sort price --json \
  | jq '.itineraries[] | {price, airlines, stops, durationMinutes}'
```

## Round-trip, business, nonstop

```bash
gfly search SFO NRT --depart 2026-09-10 --return 2026-09-24 --cabin business --stops nonstop
```

## Cheapest day across a window

```bash
gfly dates JFK LHR --depart-range 2026-08-01..2026-08-07
```

:::note
`dates` runs **one search per day** (no upstream date grid exists) — keep the window small, or use
the [`serpapi` backend](/guides/backends/).
:::

## Multi-city

```bash
gfly multi --leg JFK:CDG:2026-08-01 --leg CDG:FCO:2026-08-05 --leg FCO:JFK:2026-08-12
```

## Resolve airports offline

```bash
gfly airports search "london"
```

## Paginate

```bash
gfly search JFK LHR --depart 2026-08-15 --limit 5 --json            # page 1, returns nextCursor
gfly search JFK LHR --depart 2026-08-15 --limit 5 --offset 5 --json # page 2
```

Next: [Backends](/guides/backends/) · [Rate limits & bans](/guides/rate-limits/) ·
[For agents](/reference/for-agents/).
