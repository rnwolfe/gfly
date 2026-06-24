---
title: Exit codes
description: Every exit code gfly can return, the structured error shape, and the stability guarantee that agents can rely on.
owner: rnwolfe
lastReviewed: 2026-06-24
sidebar:
  order: 2
---

Exit codes are a **first-class contract**. They are documented here, emitted by `gfly schema`
(as `exit_codes`), and guarded by a schema-snapshot test on every release. The table is
**append-only**: no code will ever be renumbered or removed.

Run `gfly schema` at any time to get the live authoritative table alongside the full command
tree and current throttle state.

## Full exit-code table

| Code | Symbolic name | When it fires |
|-----:|---------------|---------------|
| `0` | `ok` | Command succeeded. |
| `1` | `generic_error` | Unexpected error with no dedicated code. |
| `2` | `usage` | Bad flags, arguments, or dates — fails **before** any network call. |
| `3` | `empty_results` | The query was valid but returned no flights. Try broader dates, different airports, or `--stops any`. |
| `4` | `auth_required` | The `serpapi` backend needs an API key. Run `gfly auth login` or set `GFLY_SERPAPI_KEY`. |
| `5` | `not_found` | A resource could not be located — e.g. an unrecognised identifier. |
| `6` | `permission` | Permission denied for the requested operation. |
| `7` | `rate_limited` | The politeness throttle or an upstream HTTP 429 is in effect. Always carries `retryAfterSeconds`. |
| `8` | `retryable` | Transient network error; the request may succeed on a second attempt. |
| `10` | `config_error` | Configuration file is invalid or a required config value is missing. |
| `12` | `mutation_blocked` | A mutating operation was requested. Defined for contract uniformity; **never fires** — gfly is read-only. |
| `13` | `input_required` | An interactive prompt was needed but `--no-input` is active. Pass the value as a flag instead. |
| `20` | `blocked` | Google returned a CAPTCHA or soft-block; the circuit breaker is open. Always carries `retryAfterSeconds`. |
| `21` | `schema_drift` | The upstream response could not be parsed — the `fast-flights` engine has drifted after a Google change. Upgrade gfly or switch to `--backend serpapi`. |
| `130` | `cancelled` | Process received SIGINT (Ctrl-C / `click.Abort`). |

:::note
Codes `1`, `5`, `6`, `8`, `12` are defined in the table and returned by `gfly schema` for
completeness. Some (`12 mutation_blocked`) are effectively dead code because gfly is
read-only; the definitions exist so downstream tooling built on the shared contract
compiles without modification.
:::

## Structured error shape

When stderr is consumed by a machine (i.e. when `--format json` / `--json` is active),
errors are emitted to **stderr** as a single JSON object:

```json
{
  "error": "throttled; next request allowed in ~47s",
  "code": "RATE_LIMITED",
  "remediation": "wait and retry, pass --wait to block until allowed, or --backend serpapi",
  "retryAfterSeconds": 47
}
```

| Field | Type | Always present | Notes |
|-------|------|:--------------:|-------|
| `error` | string | yes | Human-readable message. |
| `code` | string | yes | Uppercase symbolic name — stable, machine-matchable. |
| `remediation` | string | yes | Suggested fix (may be empty string). |
| `retryAfterSeconds` | integer | no | Only on `RATE_LIMITED` (code `7`) and `BLOCKED` (code `20`). Seconds until the next request is permitted. |

Without `--json`, errors are printed as plain text lines to stderr in the form:

```
error: throttled; next request allowed in ~47s
  code: RATE_LIMITED
  fix:  wait and retry, pass --wait to block until allowed, or --backend serpapi
  retryAfterSeconds: 47
```

:::tip
In a script or agent, always parse the `code` field — not the human `error` string. The
`error` text may change in a patch release; the symbolic `code` is stable.
:::

## Agent patterns

### Handling `RATE_LIMITED` and `BLOCKED`

Both carry `retryAfterSeconds`. An agent should read that value and either:

- schedule a retry after the indicated delay, or
- switch backends immediately: `--backend serpapi` is exempt from the
  politeness throttle entirely.

```bash
result=$(gfly search JFK LHR --json --depart 2026-09-01 2>&1)
code=$(echo "$result" | jq -r '.code // empty')

if [ "$code" = "RATE_LIMITED" ] || [ "$code" = "BLOCKED" ]; then
  retry_after=$(echo "$result" | jq -r '.retryAfterSeconds')
  echo "Back off ${retry_after}s or switch to serpapi backend."
fi
```

### Handling `SCHEMA_DRIFT`

Code `21` means the `fast-flights` engine can no longer parse Google's response — a Google
change has broken the reverse-engineered endpoint. The remediation is:

1. Run `uvx gfly@latest` (or `pip install --upgrade gfly`) to pick up a patched engine.
2. Switch to `--backend serpapi` as a reliable fallback while awaiting an engine fix.
3. File an issue at [github.com/rnwolfe/gfly](https://github.com/rnwolfe/gfly) with the
   `SCHEMA_DRIFT` detail string.

### Detecting empty vs. error

Exit code `3` (`empty_results`) is **not** an error — the command succeeded but found no
matching flights. Distinguish it from a real failure:

```bash
gfly search SFO NRT --json --depart 2026-12-01
# exit 0 → flights found
# exit 3 → valid query, no results (broaden search)
# exit 2 → bad flags/dates (fix the command)
# exit 7 → throttled (wait or switch backend)
```

## Stability guarantee

The exit-code table is **append-only**:

- Existing codes never change their numeric value or symbolic name.
- New codes may be added in any release.
- The `gfly schema` output (field `exit_codes`) always reflects the running version's full
  table — agents can ingest it at startup and rely on it for the lifetime of that
  installation.

See also [output schema](/reference/output-schema/) for the stable JSON envelope on stdout,
and [for agents](/reference/for-agents/) for the full agent integration guide including
`SCHEMA_DRIFT` handling and throttle state.
