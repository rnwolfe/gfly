# gfly

> Agent-first, **read-only** CLI for searching Google Flights — itineraries, price calendar,
> multi-city, and IATA lookup. JSON-by-default with a stable, versioned schema.

The default backend needs **no API key, no OAuth, no cookies** — just run it:

```bash
uvx gfly search JFK LHR --depart 2026-08-01
```

> **Status: scaffold.** This repo compiles, runs on **stub data**, and passes its contract
> tests. The real Google Flights engine is wired in the `cli-implement` stage. See `spec.md`.

## Why

Existing flight CLIs are built for humans (Rich TUIs) or punt agents to an MCP server with an
explicitly-unstable JSON shape. `gfly` is engineered for an LLM agent in a loop:

- **JSON by default**, stable & versioned (`schemaVersion`).
- **`gfly schema`** — full command tree, exit codes, and live safety/throttle state.
- **`gfly agent`** — the bundled usage contract, embedded in the package (no repo, no network).
- **Semantic exit codes** for the failures that actually happen against Google: `RATE_LIMITED`,
  `BLOCKED` (CAPTCHA), `SCHEMA_DRIFT` — each with remediation an agent can act on.
- **Token-bounded** output (`--limit`, `--select`) + IATA resolution.
- **Swappable backend**: free reverse-engineered `google` (default) ⇄ `serpapi` (live, keyed).

## Install

```bash
uv tool install gfly      # or: pipx install gfly ; or: uvx gfly <cmd>
```

## Usage

```bash
gfly search JFK LHR --depart 2026-08-01 --json
gfly search SFO NRT --depart 2026-09-10 --return 2026-09-24 --cabin business --stops nonstop
gfly dates JFK LHR                                   # cheapest departure dates
gfly multi --leg JFK:CDG:2026-08-01 --leg CDG:JFK:2026-08-12
gfly airports search london                          # resolve IATA codes
gfly doctor --json                                   # backend + throttle state
gfly schema                                          # machine-readable contract
```

### Backends

| Backend | Auth | Data | Notes |
|---|---|---|---|
| `google` (default) | none | reverse-engineered Google Flights | free; fragile; rate-limited |
| `serpapi` | API key | live Google Flights JSON | `GFLY_SERPAPI_KEY` or `gfly auth login --backend serpapi --token-stdin` |

### Rate limits & blocking

The `google` backend is scraped, so `gfly` enforces a **persistent politeness throttle** across
invocations (default `--min-interval 12`s). It **fails fast** rather than hanging: throttle/block
errors carry `retryAfterSeconds`. Pass `--wait` to block up to `--max-wait`, or switch
`--backend serpapi`. Politeness reduces — but does not eliminate — ban risk (datacenter IPs can be
CAPTCHA'd regardless); `serpapi` is the reliability escape hatch.

## Exit codes

`0` ok · `2` usage · `3` empty · `4` auth required · `5` not found · `7` rate limited ·
`8` retryable · `10` config · `13` input required · `20` blocked · `21` schema drift ·
`130` cancelled. Authoritative table: `gfly schema`.

## Development

See [`AGENTS.md`](./AGENTS.md). `uv sync --extra dev && uv run pytest -q`.

## License

MIT
