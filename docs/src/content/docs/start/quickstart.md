---
title: Quickstart
description: Fastest path to your first flight search — no API key, no setup, just copy-paste.
owner: rnwolfe
lastReviewed: 2026-06-24
---

The default `google` backend needs **no API key and no account**. Install gfly, and you are
ready to search. Data lands on stdout; progress notes and errors go to stderr — so pipes just
work.

## Your first search

```bash
gfly search JFK LHR --depart 2026-08-15 --sort price --json \
  | jq '.itineraries[] | {price, airlines, stops, durationMinutes}'
```

If stdout is a TTY (your terminal), gfly renders a readable table instead. Pipe it or pass
`--json` and you get the stable JSON envelope every time:

```json
{
  "schemaVersion": "1",
  "backend": "google",
  "query": { "from": "JFK", "to": "LHR", "depart": "2026-08-15", ... },
  "_warning": "fields below originate from a third party ...",
  "currency": "USD",
  "count": 47,
  "offset": 0,
  "itineraries": [ ... ],
  "nextCursor": "25"
}
```

`count` is the total found. `nextCursor` is the `--offset` value for the next page (or `null`
when you are at the end). The `_warning` field is present because airline names and fare labels
come from a third party and are fenced as untrusted by default.

:::note
Airport codes are case-insensitive. `jfk`, `JFK`, and `Jfk` all work.
:::

## Round-trip, business class, nonstop

```bash
gfly search SFO NRT --depart 2026-09-10 --return 2026-09-24 \
  --cabin business --stops nonstop
```

On the default `google` backend, each itinerary describes the **outbound legs** and `price` is
the **round-trip total**. The `flightNumbers` field will be an empty array (`[]`) and
`bookingToken` will be `null` — this is a known limitation of the google backend. Switch to
`--backend serpapi` for those fields.

## Cheapest day across a window (`dates`)

```bash
gfly dates JFK LHR --depart-range 2026-08-01..2026-08-07 --json
```

:::caution
`dates` runs **one upstream search per day** — no date-grid API exists. A 7-day window makes
7 requests, paced ~12 seconds apart by default (about 1.2 minutes total). Keep windows short,
or switch to `--backend serpapi` for faster scanning. Never use a 30-day window in a tight loop.
:::

A BLOCKED or RATE_LIMITED event mid-scan stops early and returns what was gathered so far, with
`"partial": true` and a `failedAt` date in the envelope so you can resume.

## Multi-city

```bash
gfly multi \
  --leg JFK:CDG:2026-08-01 \
  --leg CDG:FCO:2026-08-05 \
  --leg FCO:JFK:2026-08-12
```

Requires at least two `--leg FROM:TO:DATE` entries. Multi-city is **google backend only** — it
will error if you pass `--backend serpapi`.

## Resolve airports offline

Not sure of a code? The lookup is instant and makes no network call:

```bash
gfly airports search london
gfly airports search "charles de gaulle"
gfly airports search CDG
```

Returns `iata`, `name`, `city`, and `country` from a bundled offline dataset (~7,900 airports).
Always do this rather than guessing a code.

## Pagination

Results default to 25 per page. Use `--limit` and `--offset` to page through:

```bash
# Page 1 — note the nextCursor in the response
gfly search JFK LHR --depart 2026-08-15 --limit 10 --json

# Page 2 — pass the nextCursor value as --offset
gfly search JFK LHR --depart 2026-08-15 --limit 10 --offset 10 --json
```

When `nextCursor` is `null`, you have reached the last page. In JSON mode a pagination hint also
appears on stderr:

```
note: itineraries[0:10] of 47 (paginate with --offset 10)
```

:::tip
Use `--select` to project only the fields you need — fewer tokens, faster parsing:

```bash
gfly search JFK LHR --depart 2026-08-15 --select price,airlines,stops,durationMinutes --json
```
:::

## Stdout vs stderr: the discipline

| Stream | What lands there |
|---|---|
| **stdout** | All structured data (JSON envelope, plain table, TSV rows) |
| **stderr** | Progress notes, pagination hints, warnings, and error objects |

This means `gfly ... | jq ...` always works cleanly. Errors are structured too — when output is
JSON, stderr carries `{ "error": "...", "code": "...", "remediation": "..." }`.

## TTY vs pipe: format auto-detection

| Context | Default format |
|---|---|
| stdout is a TTY (interactive terminal) | `plain` — rendered table |
| stdout is piped or redirected | `json` — stable envelope |

Override any time with `--format json`, `--format plain`, `--format tsv`, or the `--json`
shorthand. The stable JSON envelope is the contract; plain/TSV output is not versioned.

## What to do next

- Hitting rate limits? Read [Rate limits and bans](/guides/rate-limits/) — the throttle is on
  by default and keeps you polite, but IP blocks and CAPTCHAs can still happen.
- Want `flightNumbers`, `bookingToken`, or a reliable escape hatch? Read
  [Backends](/guides/backends/).
- Building an agent or script? Read [For agents](/reference/for-agents/) — it covers the full
  JSON contract, exit codes, prompt-injection fencing, and non-interactive flags.
- Full flag reference: [Commands](/reference/commands/).
