---
title: Rate limits & bans
description: gfly's persistent politeness throttle, fail-fast behavior, and how to avoid getting blocked.
---

The `google` backend is scraped, so the #1 **controllable** ban vector is request rate. gfly ships a
**persistent, cross-process politeness throttle** — because an agent invokes the CLI as a fresh
process each call, the throttle state lives on disk (`$XDG_STATE_HOME/gfly/`), not in memory.

## Fail-fast, not hang

When a request would be too soon, gfly returns a structured error with `retryAfterSeconds` — it does
**not** silently sleep (a hung CLI would deadlock an agent loop).

```bash
gfly search JFK LHR --depart 2026-08-15 --wait          # opt IN to blocking until clear
gfly search JFK LHR --depart 2026-08-15 --min-interval 0 # disable pacing (riskier)
```

| Flag / env | Default | Effect |
|---|---|---|
| `--min-interval` / `GFLY_MIN_INTERVAL` | 12s | min spacing between google requests |
| `--wait` | off | block (sleep) until allowed, up to `--max-wait` |
| `--max-wait` | 60s | cap for `--wait` |
| `--no-throttle` / `GFLY_NO_THROTTLE` | off | bypass the throttle entirely |

## Circuit breaker

On a 429 / CAPTCHA the breaker opens with exponential backoff; calls inside the cooldown short-circuit
(so you don't deepen the block) and return [`BLOCKED`](/reference/exit-codes/) (exit 20) with
`retryAfterSeconds`. A clean response resets it. Check state anytime:

```bash
gfly doctor --json | jq .throttle
```

## Ban vectors (be honest)

Politeness only addresses **rate**. Two vectors it can't fix:

- **Bot fingerprint** — TLS/HTTP2/header signatures can CAPTCHA you on request #1.
- **IP reputation** — datacenter/cloud IPs are pre-flagged regardless of rate.

For those, use `--proxy` (residential) or switch `--backend serpapi`. Politeness reduces ban risk; it
does not eliminate it.
