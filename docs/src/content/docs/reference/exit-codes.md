---
title: Exit codes
description: Distinct, documented, stable exit codes — a first-class part of gfly's contract.
sidebar:
  order: 2
---

Exit codes are a first-class contract. `gfly schema` prints the authoritative table; this page
mirrors it.

| Code | Name | Meaning |
|---|---|---|
| `0` | ok | success |
| `2` | usage | bad flags / arguments / dates |
| `3` | empty_results | no flights for this query |
| `4` | auth_required | the serpapi backend needs a key |
| `5` | not_found | e.g. unknown IATA |
| `7` | rate_limited | throttle or upstream 429 (carries `retryAfterSeconds`) |
| `8` | retryable | transient network error |
| `10` | config_error | bad config |
| `13` | input_required | `--no-input` hit a required prompt |
| `20` | **BLOCKED** | CAPTCHA / soft-block; cooling down (carries `retryAfterSeconds`) |
| `21` | **SCHEMA_DRIFT** | the upstream response no longer parses (engine drift) |
| `130` | cancelled | SIGINT |

## Structured errors

Errors print to **stderr** as JSON (under `--json`):

```json
{
  "error": "throttled; next request allowed in ~47s",
  "code": "RATE_LIMITED",
  "remediation": "wait and retry, pass --wait to block until allowed, or --backend serpapi",
  "retryAfterSeconds": 47
}
```

`retryAfterSeconds` appears on `RATE_LIMITED` and `BLOCKED` so an agent can schedule its retry or
switch backend instead of crashing. These codes are **append-only** — they never change meaning.
