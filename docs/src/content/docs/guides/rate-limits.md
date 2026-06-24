---
title: Rate limits & bans
description: How gfly's persistent politeness throttle works, why it lives on disk, and how to avoid getting banned by Google.
owner: rnwolfe
lastReviewed: 2026-06-24
sidebar:
  order: 4
---

The `google` backend is a reverse-engineered, unauthenticated endpoint. That means
Google can and does block aggressive callers — by rate, by bot fingerprint, or by IP
reputation. gfly ships a **persistent, cross-process politeness throttle** that addresses
the first vector. Understanding all three will save you a lot of debugging.

## Why the throttle state lives on disk

An agent invokes gfly as a **fresh process per call**. An in-memory timer would reset
on every invocation and be completely useless. Instead, gfly persists its throttle state
to disk at:

```
$XDG_STATE_HOME/gfly/ratelimit.json   # default (~/.local/state/gfly/ratelimit.json)
$GFLY_STATE_DIR/ratelimit.json        # override with GFLY_STATE_DIR
```

The state file is keyed per-backend (`google` / `serpapi`) and is written with `0600`
permissions. It tracks the timestamp of the last request, a recent-call window, the
circuit-breaker `blocked_until` epoch, and the `consecutiveBlocks` counter.

:::note
The `serpapi` backend is **exempt** from the throttle entirely — it goes through SerpApi's
servers, which handle rate-limiting at the API layer. All of the following applies only to
`--backend google` (the default).
:::

## Fail-fast by default

When a request would arrive too soon, gfly **does not silently sleep**. A hung CLI
deadlocks an agent loop. Instead it raises a structured error on **stderr** and exits
non-zero:

```json
{
  "error": "request too soon; try again in 8s",
  "code": "RATE_LIMITED",
  "remediation": "wait 8s, or pass --wait to block automatically",
  "retryAfterSeconds": 8
}
```

Your caller should read `retryAfterSeconds` and schedule a retry. If you want gfly to
handle the wait itself, pass `--wait`.

## Throttle flags and environment variables

| Flag | Env var | Default | Effect |
|---|---|---|---|
| `--min-interval` | `GFLY_MIN_INTERVAL` | `12` (seconds) | Minimum gap between consecutive google requests |
| `--wait` | — | off | Block (sleep) until the interval or cooldown clears, up to `--max-wait` |
| `--max-wait` | — | `60` (seconds) | Cap on how long `--wait` will sleep before failing |
| `--no-throttle` | `GFLY_NO_THROTTLE` | off | Bypass the throttle entirely (risky) |

```bash
# opt into blocking sleep (gfly will wait up to 60s for the interval to clear)
gfly search JFK LHR --depart 2026-08-15 --wait

# extend the blocking cap to 3 minutes
gfly search JFK LHR --depart 2026-08-15 --wait --max-wait 180

# disable pacing (risky — increases ban probability significantly)
gfly search JFK LHR --depart 2026-08-15 --no-throttle

# set a custom interval globally via env
export GFLY_MIN_INTERVAL=20
gfly search JFK LHR --depart 2026-08-15
```

:::caution
Setting `--min-interval 0` or `GFLY_MIN_INTERVAL=0` also bypasses throttling (the guard
exits early when `min_interval <= 0`). Treat this the same as `--no-throttle`.
:::

The `dates` command runs one upstream request per day in the range. It logs the expected
pacing upfront so you can estimate wall-clock time before committing to a wide window:

```
note: scanning 14 day(s) = 14 upstream request(s), paced ~12s apart (~156s total)
```

## Circuit breaker

When the upstream returns a 429 or CAPTCHA signal, gfly opens a **circuit breaker** and
refuses further requests until the cooldown expires. Subsequent calls inside the cooldown
short-circuit immediately (they never touch the network) and exit with code `20` (`BLOCKED`):

```json
{
  "error": "blocked by upstream; cooldown 300s",
  "code": "BLOCKED",
  "remediation": "wait for cooldown, use --proxy, or --backend serpapi",
  "retryAfterSeconds": 300
}
```

The cooldown grows exponentially with each consecutive block, indexed against this
schedule (seconds):

| Block # | Cooldown |
|---|---|
| 1st | 30 s |
| 2nd | 60 s |
| 3rd | 120 s |
| 4th | 300 s (5 min) |
| 5th | 600 s (10 min) |
| 6th+ | 1800 s (30 min) |

A clean successful response resets the counter back to zero.

### Inspect the current throttle state

`doctor` exposes a live snapshot of the throttle without touching the upstream:

```bash
gfly doctor --json | jq .throttle
```

```json
{
  "backend": "google",
  "lastRequest": 1750000000.0,
  "blocked": false,
  "blockedUntil": null,
  "cooldownSeconds": 0,
  "consecutiveBlocks": 0
}
```

If `blocked` is `true`, `cooldownSeconds` tells you exactly how long to wait before the
circuit clears. The `schema` command includes the same snapshot under the `throttle` key.

## The three ban vectors

Politeness helps with **rate** only. Google uses three distinct signals to identify and
block scrapers:

### 1. Rate (controllable)

Too many requests in a short window → 429 or soft CAPTCHA. The throttle directly
addresses this. Keep `--min-interval` at 12 s or higher for sustained workloads.

### 2. Bot fingerprint (not addressable by rate alone)

Google inspects TLS/HTTP2 fingerprints, header ordering, and other request signatures. A
sufficiently distinctive fingerprint can trigger a CAPTCHA **on the very first request**
regardless of rate. This is a property of the `fast-flights` library's request shape, not
of how frequently you call it.

:::caution
If you see a CAPTCHA on request #1, the fingerprint is the likely cause — slowing down
will not help. Switch to `--backend serpapi` or use a residential `--proxy`.
:::

### 3. IP reputation (not addressable by rate alone)

Datacenter and cloud IPs (AWS, GCP, Azure, Hetzner, etc.) are pre-flagged in Google's IP
reputation databases. Your account may get blocked before any request completes.

## Escape hatches

### Use a proxy

`--proxy` (or `GFLY_PROXY`) passes an HTTP(S) proxy URL to the google backend. A
residential proxy with a clean IP reputation can bypass IP-based blocks:

```bash
gfly search JFK LHR --depart 2026-08-15 --proxy http://user:pass@residential-proxy:8080
```

The proxy flag has no effect on the `serpapi` backend.

### Switch to SerpApi

`--backend serpapi` routes requests through [SerpApi](https://serpapi.com/), which handles
fingerprinting, IP reputation, and CAPTCHA solving on their infrastructure. It requires an
API key (see [Authentication](/guides/authentication/)) but is the **reliable escape hatch**
when the google backend is blocked:

```bash
export GFLY_SERPAPI_KEY=your_key_here
gfly search JFK LHR --depart 2026-08-15 --backend serpapi
```

SerpApi is throttle-exempt in gfly, but SerpApi itself enforces per-plan quota limits
(HTTP 429 → exit code `7` with `retryAfterSeconds: 60`).

## Summary: which problem needs which fix

| Problem | Fix |
|---|---|
| Too-soon error (`RATE_LIMITED`) | Use `--wait`, increase `--min-interval`, or schedule retries with `retryAfterSeconds` |
| Circuit breaker open (`BLOCKED`) | Wait out `cooldownSeconds`, use `--proxy`, or switch to `--backend serpapi` |
| CAPTCHA on first request | Switch to `--backend serpapi` or use a residential `--proxy` |
| Datacenter IP blocked | Switch to `--backend serpapi` or use a residential `--proxy` |

See also: [Backends](/guides/backends/) · [Authentication](/guides/authentication/) · [Exit codes](/reference/exit-codes/)
