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

## Status
**Shipped** — published to PyPI (`gfly`), GitHub (`rnwolfe/gfly`), landing at https://gfly.sh, docs at
https://docs.gfly.sh. The engines (`backend.py`) and auth (`auth.py`) are real.

## Documentation (keep it current — non-negotiable)

Docs live in `docs/` — a standalone Astro Starlight site (its own `package.json`; not a workspace).
Content is Markdown/MDX under `docs/src/content/docs/`. The build emits `llms.txt` / `llms-full.txt`.

- Dev: `cd docs && pnpm install && pnpm dev --host 0.0.0.0`
- Build (regenerates `llms.txt`): `cd docs && pnpm build`

**Docs are part of "done." A change is not complete until its docs are updated in the SAME commit/PR.**

When you change any **public surface**, update the matching `docs/` page in the same change:
- CLI commands, flags, output fields, or exit codes → `reference/` + the relevant guide
- Backends, auth, throttle behavior → `guides/`
- Config keys / environment variables / defaults → `reference/commands.md`

On a **release**: update `CHANGELOG.md`, bump version references in docs, and run `cd docs && pnpm build`
so `llms.txt` regenerates. Each docs page has `owner` / `lastReviewed` frontmatter — refresh
`lastReviewed` when you meaningfully revise a page. If a code change has no doc impact, say so in the PR.
