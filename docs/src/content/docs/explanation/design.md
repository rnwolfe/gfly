---
title: Design & risks
description: Why gfly is agent-first, how the contract is shaped, and the honest risks of a reverse-engineered backend.
---

## Why build it

Google has had **no public flights API since QPX shut down in 2018**. The community tools that fill
the gap are built for humans (Rich TUIs) or hand agents an MCP server with a self-declared-unstable
JSON shape. None are engineered for an autonomous agent. gfly fills that gap:

- **JSON by default**, with a stable, versioned `schemaVersion` — not "experimental".
- **Self-describing** via `schema` + an embedded `agent` contract (zero external files).
- **Semantic exit codes** for the failures that actually happen against a scraped source.
- **Token-bounded** output so an agent never drowns in results.
- **Read-only** by design — safe to hand an autonomous agent.

## How the contract is shaped

One swappable backend interface normalizes [google and serpapi](/guides/backends/) into the same
[envelope](/reference/output-schema/). The CLI owns the envelope; backends return only records. This
isolates upstream breakage behind one stable shape — agent code never changes when a backend does.

The [politeness throttle](/guides/rate-limits/) is deliberately **persistent on disk**, because the
agent invokes gfly as a fresh process per call: an in-memory timer would be a no-op. It fails fast
with `retryAfterSeconds` rather than hanging, mirroring the `--no-input` philosophy.

## The honest risks

The default backend rides an **undocumented, reverse-engineered** Google Flights endpoint:

- It **will** break when Google changes its response. gfly surfaces that as `SCHEMA_DRIFT` (exit 21)
  rather than returning silent wrong data — but it is real maintenance debt. Pin the version.
- Single-IP use hits 429 / CAPTCHA. Politeness reduces this; it does not eliminate it. Datacenter IPs
  can be blocked regardless of rate — that's what `--proxy` and `serpapi` are for.
- `serpapi` is a third-party paid service with its own ToS and (as of late 2025) litigation risk with
  Google. It's the reliability escape hatch, never the sole path.

gfly's stance is to treat the upstream as untrusted: structured errors over crashes, fenced text over
blind trust, and an append-only contract over silent breakage.
