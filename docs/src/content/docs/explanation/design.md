---
title: Design & risks
description: Why gfly exists, how the agent-first contract is shaped, and the honest risks of a reverse-engineered backend.
owner: rnwolfe
lastReviewed: 2026-06-24
sidebar:
  order: 1
---

## Why build it

Google has had **no self-serve public flights API since QPX Express shut down on 2018-04-10.** Enterprise "Travel Partner APIs" exist but are sales-contracted and not available to individual developers. The void that remains is filled with two classes of tools:

- **Human-TUI CLIs** — beautiful Rich/terminal tables for people, an unstable JSON shape for agents (if JSON output exists at all). The closest competitor, [fli](https://github.com/punitarani/fli), self-declares its `--format json` as experimental and routes agent use toward a separate MCP server.
- **Library-only scrapers** — `fast-flights` (~1.1k stars) is the best engine but has no CLI surface, no exit codes, and no envelope contract.

Neither is engineered for an autonomous agent. The gap is real. gfly fills it with five properties nothing else delivers together:

| Property | Why it matters to an agent |
|---|---|
| JSON by default, `schemaVersion`-stamped | The agent can trust the shape will not silently change |
| `schema --json` + embedded `agent` SKILL.md | Zero external files needed to discover the interface |
| Semantic exit codes for scraping failure modes | `RATE_LIMITED` / `BLOCKED` / `SCHEMA_DRIFT` so the agent can route, not crash |
| Token-bounded by default (`--limit`, `--select`) | The agent gets a bounded payload, not a 40-itinerary dump |
| Read-only by design | Safe to hand to an autonomous loop without a mutation gate |

gfly is built on top of the existing best engine (`fast-flights` handles the brittle protobuf encode/parse) rather than re-reverse-engineering Google, and does not fork `fli`'s human-TUI bundle. The differentiation is entirely the agent contract.

## The agent-first contract shape

The JSON envelope is owned by the CLI, not the backend:

```json
{
  "schemaVersion": "1",
  "backend": "google",
  "query": { "from": "JFK", "to": "LHR", "depart": "2026-08-01", "return": null, "adults": 1, "cabin": "economy" },
  "currency": "USD",
  "count": 12,
  "offset": 0,
  "itineraries": [ /* current page */ ],
  "nextCursor": null
}
```

Three design choices make this agent-safe:

**Append-only fields.** The contract is a ratchet: fields are only added, never renamed or removed. A `schemaVersion` bump signals a breaking change. A schema-snapshot test (`tests/test_schema_snapshot.py`) gates every release, so drift from the contract surfaces as a CI failure, not a production surprise.

**Structured errors on stderr.** When the upstream fails, the tool does not crash with a Python traceback — it writes a machine-readable error to stderr and exits with a semantic code:

```json
{ "error": "Google served a CAPTCHA or soft-block", "code": "BLOCKED", "remediation": "wait for cooldown or --backend serpapi", "retryAfterSeconds": 120 }
```

An agent reading `retryAfterSeconds` knows exactly when to retry or switch backend. No grep-parsing of human prose required.

**Data on stdout, everything else on stderr.** Warnings, progress notes, and errors never contaminate the JSON stream. The agent can pipe `gfly search … | jq …` without defensive stripping.

See [Output schema](/reference/output-schema/) for the full field reference and [Exit codes](/reference/exit-codes/) for the complete table.

## The swappable-backend interface

Two engines sit behind one normalized output contract. The CLI dispatches by `--backend` (or `GFLY_BACKEND`); callers never see the difference in the envelope.

```
gfly search JFK LHR --depart 2026-09-01          # google (default, no auth)
gfly search JFK LHR --depart 2026-09-01 \
     --backend serpapi                            # serpapi (API key required)
```

The normalization contract is defined in `backend.py`. Both paths produce identical dict shapes; the CLI wraps them in the same envelope. Caveat fields are documented honestly rather than papered over:

| Field | google | serpapi |
|---|---|---|
| `flightNumbers` | `[]` — not exposed by the engine | populated |
| `bookingToken` | `null` — not exposed by the engine | populated |
| `isBest` | always `false` — engine cannot split best/other | set for `best_flights` entries |
| Multi-city | supported | not supported (raises `UNSUPPORTED`) |
| Auth | none | API key required |
| Throttle | persistent min-interval + circuit breaker | exempt (paid quota) |

The split exists because upstream breakage is isolated. When Google changes its response format, only the `google` backend breaks. The `serpapi` backend keeps working. Agent code never changes — only the `--backend` flag.

## The persistent throttle rationale

The default `google` backend scrapes an undocumented endpoint. Rate is the single most **controllable** ban vector. The throttle is on by default because not having one makes bans near-certain at any realistic agent call rate.

The crux for a CLI agent: **gfly is a fresh process per call.** An in-memory timer is a no-op — state from the previous invocation is gone before the next one starts. So the throttle persists to disk:

```
$XDG_STATE_HOME/gfly/ratelimit.json   # default: ~/.local/state/gfly/ratelimit.json
```

State is keyed per backend (google and serpapi do not share a budget). It tracks last-request time, a rolling call window, and a circuit-breaker `blocked_until` timestamp.

**Fail-fast is the default — deliberately.** When a request must wait (min-interval not elapsed, or inside a block cooldown), gfly raises a structured `RATE_LIMITED` or `BLOCKED` error with `retryAfterSeconds` and exits non-zero rather than sleeping silently. A CLI that hangs for 30 seconds without output **deadlocks an agent loop** and trips its timeout. The agent sees the error, reads `retryAfterSeconds`, and decides whether to wait or switch backend. This mirrors the `--no-input` philosophy: hard-fail rather than block indefinitely.

`--wait` / `--max-wait N` opt into blocking sleep for human or script use. `--no-throttle` (or `GFLY_NO_THROTTLE=1`) bypasses the min-interval entirely as an escape hatch — documented as risky.

The circuit-breaker uses an exponential backoff schedule `[30, 60, 120, 300, 600, 1800]` seconds indexed by consecutive-block count. A clean response resets the count. The current state is visible via `gfly doctor` and `gfly schema --json`.

```bash
gfly doctor          # shows blocked, blockedUntil, cooldownSeconds, consecutiveBlocks
```

## The honest risks

### Reverse-engineered breakage (SCHEMA_DRIFT)

The `google` backend rides the `fast-flights` library, which reverse-engineers a **base64-protobuf** `tfs` query string against `https://www.google.com/travel/flights`. That endpoint is undocumented and unsupported. `fast-flights`' own README says: *"get ready to get banned."* Confirmed parsing breakages occurred in March 2026 (#101/#102) and May 2026 (#109).

When Google changes its response structure, `fast-flights`' parser breaks. gfly wraps every `fast-flights` call defensively: any unexpected exception that is not a known network error is classified as `SCHEMA_DRIFT` (exit 21) rather than a bare `KeyError` stack trace. An agent receiving exit 21 should switch to `--backend serpapi` and file a report rather than retrying blindly.

:::caution
Pin `fast-flights` to an exact version in any production deployment. A library upgrade can change the parsed shape. Treat every upgrade as a potential breaking change.
:::

### Ban vectors that politeness cannot fix

Rate is only one of three ban vectors:

| Vector | Controllable? | Mitigation |
|---|---|---|
| **Rate / volume** | Yes — the throttle handles this | `--min-interval`, circuit breaker |
| **Bot fingerprint** | Partially — TLS/HTTP2/header order heuristics | `--proxy`, residential proxy |
| **IP reputation** | No — datacenter ASNs are pre-flagged | `--proxy` with residential IP, or `--backend serpapi` |

A datacenter IP (GitHub Actions runner, AWS Lambda, any VPS) can receive a CAPTCHA on the very first request regardless of how slowly it calls. This is not a rate issue — it is an IP reputation issue that the throttle cannot fix. The `serpapi` backend calls SerpApi's servers (which have their own IP reputation management) and bypasses this entirely.

`--proxy` (or `GFLY_PROXY`) accepts an HTTP/HTTPS/SOCKS proxy URL and is passed through to `fast-flights`. It helps with IP reputation but not with bot fingerprinting.

:::note
When `BLOCKED` (exit 20), the structured error suggests: wait for the cooldown, or `--backend serpapi`. In a CI/CD or datacenter environment, `serpapi` is the correct path — not "tune the min-interval."
:::

### SerpApi third-party continuity risk

`serpapi` is not a first-party Google product. It is a third-party paid service that scrapes Google on your behalf. On 2025-12-19, Google sued SerpApi (N.D. Cal.) for scraping circumvention. That case was unresolved as of this writing.

The practical implication: **do not make `serpapi` the only backend.** The `google` backend exists precisely so the tool keeps working if SerpApi faces service interruption, changes its API, or raises prices. Both backends must stay functional. If you configure `GFLY_BACKEND=serpapi` globally, have a fallback plan.

### Prompt-injection surface

`search`, `dates`, and `multi` return **third-party free text** sourced from Google: airline names, fare-brand strings, layover labels. These arrive as Google sees fit to format them and can contain control characters or adversarially crafted payloads.

gfly's default stance is to treat this text as untrusted. The `_clean()` function in `backend.py` strips control characters and newlines and caps length at 200 characters. When the sanitizer fires, an `_warning` key is added to the envelope. Disable with `--no-wrap-untrusted` only if a downstream consumer has its own hardening.

`airports search`, `schema`, `doctor`, and `agent` emit only gfly-controlled text and are not affected.

## Stance: treat upstream as untrusted

Every design decision flows from this principle: the data source is reverse-engineered, legally grey, and operationally brittle. gfly's job is to present a stable, bounded, honest surface on top of that chaos:

- **Structured errors over crashes** — every failure mode has a named exit code and a machine-readable remediation hint.
- **Fenced text over blind trust** — third-party strings are sanitized by default.
- **Append-only contract over silent breakage** — fields only grow; the schema snapshot test catches regressions before release.
- **Fail-fast over silent hang** — the throttle errors loudly so agents can route, not deadlock.

The result is not "Google Flights, but stable" — the upstream is what it is. The result is "a stable interface that tells you honestly when the upstream is broken."

---

Related pages: [Backends](/guides/backends/) · [Rate limits & politeness](/guides/rate-limits/) · [Exit codes](/reference/exit-codes/) · [Output schema](/reference/output-schema/) · [For agents](/reference/for-agents/)
