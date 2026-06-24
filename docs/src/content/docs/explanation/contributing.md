---
title: Contributing
description: How to set up, the non-negotiable contract rules, and what "done" looks like for a gfly change.
owner: rnwolfe
lastReviewed: 2026-06-24
sidebar:
  order: 2
---

`gfly` is an agent-first, read-only Google Flights CLI. The [agent-CLI contract](/reference/for-agents/) — read-only, stable JSON, structured errors, bounded output — is non-negotiable. Everything below exists to keep that contract intact.

## Setup

You need [uv](https://docs.astral.sh/uv/) and Python ≥ 3.10.

```bash
git clone https://github.com/rnwolfe/gfly
cd gfly
uv sync --extra dev    # installs gfly + pytest into a managed venv
uv run pytest -q       # must stay green before every commit
```

Smoke-test your environment:

```bash
uv run gfly schema          # prints the machine-readable command tree
uv run gfly --version       # bare version string
python -m gfly --help       # module entry-point also works
```

## Codebase layout

| File | Role | Editability |
|---|---|---|
| `src/gfly/cli.py` | Click grammar, `Runtime`, global-flag merge, exit-code mapping | **Contract surface — edit deliberately** |
| `src/gfly/backend.py` | google (fast-flights) and serpapi engines; `SCHEMA_VERSION` lives here | Core — change with care |
| `src/gfly/output.py` | stdout=data / stderr=chatter, `--format`, `--select`, `--limit` | **Do not break the split** |
| `src/gfly/errors.py` | `ExitCode` enum + structured `AppError` | Append-only |
| `src/gfly/throttle.py` | Persistent cross-process politeness / circuit-breaker | Real infrastructure |
| `src/gfly/auth.py` | Credential resolution (env → keyring → 0600 file) | Handle with care |
| `src/gfly/SKILL.md` | Embedded agent skill; printed by `gfly agent` | Regenerate when the surface changes |

## Non-negotiable rules

These rules exist to protect the agent-CLI contract. Breaking any of them is a reviewed, deliberate decision — not a drive-by.

### 1. Read-only invariant

No command may mutate remote state. The `--allow-mutations` flag and `Runtime.guard` are kept for contract uniformity but are intentional no-ops. Adding mutations requires revisiting `spec.md` — the single source of truth for what gfly is.

### 2. Append-only output contract

The [output schema](/reference/output-schema/) is append-only (contract §10):

- **Adding** new fields is fine.
- **Renaming or removing** an existing field is a breaking change.

When a breaking shape change is truly necessary, you **must** do all three in the same PR:

1. Bump `SCHEMA_VERSION` in `src/gfly/backend.py`.
2. Update the golden values in `tests/test_schema_snapshot.py`.
3. Update the relevant [reference docs](/reference/output-schema/).

The schema-snapshot test is the CI gate. If it fails, you changed the agent-facing contract — that should be a deliberate, reviewed diff, not a surprise.

### 3. stdout = data, stderr = chatter

Data (JSON, table, TSV) always goes to stdout. Notes, warnings, progress messages, and errors always go to stderr. This is what lets agents pipe `gfly search … | jq …` without filtering noise. See `src/gfly/output.py` — do not break the split.

### 4. Secrets via stdin or env, never argv

Secrets passed as CLI arguments appear in `ps`, `/proc`, and shell history. Accepted forms only:

- `--token-stdin` / `--abuse-cookie-stdin` (reads from stdin)
- Environment variables: `GFLY_SERPAPI_KEY`, `GFLY_ABUSE_COOKIE`
- OS keyring (set via `gfly auth login`)

This is contract §7. Never add a `--token <value>` flag.

### 5. Heavy imports stay lazy

The google (fast-flights) and serpapi imports must stay inside the functions that use them — never at module top level. This keeps `gfly --help`, `gfly schema`, and `gfly agent` fast regardless of whether the heavy dependencies are warm.

## Tests

```bash
uv run pytest -q
```

Network is fully mocked in tests — `tests/conftest.py` monkeypatches both backend entry points. No live credentials or internet access required.

The three snapshot tests in `tests/test_schema_snapshot.py` are the contract gate:

- **`test_command_tree_is_stable`** — asserts the set of top-level commands.
- **`test_exit_code_table_is_stable`** — asserts the full [exit-code table](/reference/exit-codes/).
- **`test_itinerary_fields_are_stable`** — asserts the exact set of [itinerary fields](/reference/output-schema/).

A snapshot failure means your change touches the agent-facing contract. Update the golden deliberately and include the diff in your PR description.

## Documentation

Docs live in `docs/` — a standalone Astro Starlight site. Content is Markdown under `docs/src/content/docs/`.

**Docs are part of "done."** A change is not complete until the matching page is updated in the same commit or PR.

| What you changed | What to update |
|---|---|
| CLI commands, flags, or exit codes | `docs/src/content/docs/reference/` + relevant guide |
| Output fields or schema | `docs/src/content/docs/reference/output-schema/` |
| Backends, auth, or throttle behavior | `docs/src/content/docs/guides/` |
| Any public surface | `src/gfly/SKILL.md` (printed by `gfly agent`) |

Run the docs site locally:

```bash
cd docs
pnpm install
pnpm dev --host 0.0.0.0    # preview at http://localhost:4321
pnpm build                  # regenerates llms.txt / llms-full.txt
```

:::tip
The `--host 0.0.0.0` flag makes the preview reachable from other devices on your LAN — useful when checking mobile layout or testing from a phone.
:::

When you meaningfully revise a docs page, update its `lastReviewed` frontmatter to today's date.

If a code change genuinely has no documentation impact, say so explicitly in your PR description — "no doc impact" is a valid statement; silence is not.

## Pull requests

- **[Conventional Commits](https://www.conventionalcommits.org/)**: use `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, or `chore:`. These drive the changelog and semver bump.
- **DCO sign-off**: `git commit -s`. No CLA required.
- **Keep PRs focused**: one concern per PR makes review faster and rollback cleaner.
- **Update `CHANGELOG.md`**: add an entry under `[Unreleased]` for any user-visible change.
- **Green CI required**: tests (`uv run pytest -q`) and a `gfly schema` smoke run must pass.

## Reporting bugs and security

**Bugs:** Open a [GitHub issue](https://github.com/rnwolfe/gfly/issues). The template asks for `gfly --version`, OS, backend used, a reproduction, and the JSON error block from stderr.

**Security vulnerabilities:** See [SECURITY.md](https://github.com/rnwolfe/gfly/blob/main/SECURITY.md). Do **not** open a public issue — use GitHub Private Vulnerability Reporting or the email listed there. Never paste live secrets in a report; redact and rotate any key you believe was exposed.

:::caution
`gfly auth logout` removes only the **local** credential. To fully revoke a SerpApi key, go to [serpapi.com/manage-api-key](https://serpapi.com/manage-api-key) — logout alone is not enough.
:::
