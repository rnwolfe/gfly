# AGENTS.md — gfly

Conventions for agents editing this repo. (End users driving the CLI want `gfly agent` /
`src/gfly/SKILL.md` instead.)

## What this is
`gfly` is an agent-first, **read-only** CLI for searching Google Flights. Scaffolded by
agent-cli-factory from the Python (Click) template. `spec.md` is the single source of truth.

## Build / test / run
```bash
uv sync --extra dev          # install (uv-managed; Python >=3.10)
uv run pytest -q             # contract + behavior tests (must stay green)
uv run gfly schema           # machine-readable command tree
uv run gfly search JFK LHR --depart 2026-08-01 --json
python -m gfly --help        # module entry also works
```

## Layout
- `src/gfly/cli.py` — Click grammar, `Runtime`, global-flag merge, exit-code mapping. **Contract
  surface; edit deliberately.** Global flags must work in any position (the `_resolve` walk).
- `src/gfly/output.py` — stdout=data / stderr=chatter, `--format`, `--select`, `--limit`. **Do not edit.**
- `src/gfly/errors.py` — exit-code table + structured `AppError` (incl. `BLOCKED` 20, `SCHEMA_DRIFT` 21).
- `src/gfly/throttle.py` — persistent cross-process politeness/circuit-breaker (real infra).
- `src/gfly/backend.py` — **PLACEHOLDER** stub data. `cli-implement` replaces with fast-flights
  (google) + SerpApi (serpapi), behind the same normalized shapes.
- `src/gfly/auth.py` — **PLACEHOLDER** credential resolution (env only today; keyring later).
- `src/gfly/SKILL.md` — embedded; printed by `gfly agent`. Regenerate when the surface changes.

## Rules
- **Read-only tool.** No command mutates. The `--allow-mutations` gate + `Runtime.guard` are kept
  for contract uniformity but unused; don't add mutations without revisiting `spec.md`.
- **Output contract is append-only** (contract §10). New fields OK; never rename/remove. Bump
  `SCHEMA_VERSION` (in `backend.py`) on any breaking shape change and update the snapshot test.
- **Secrets via stdin/env, never argv** (contract §7).
- **Heavy imports stay lazy** — inside backend functions, never at module top (keeps `--help`/`schema` fast).
- Keep `uv run pytest -q` green before every commit; the `schema` test is the contract gate.

## Handoff state
This is a **scaffold**: it compiles, runs on stub data, and passes contract tests. Next stage is
`cli-implement` — wire the real engines + auth, replacing `backend.py` / `auth.py`.
