# Contributing to gfly

Thanks for helping! gfly is an agent-first, read-only Google Flights CLI. `spec.md` is the source
of truth for what it is; the **agent-CLI contract** (read-only, stable JSON, structured errors,
bounded output) is non-negotiable — keep it intact.

## Setup

```bash
uv sync --extra dev          # Python >= 3.10, uv-managed
uv run pytest -q             # tests must stay green
uv run gfly schema           # machine-readable command tree
```

## Develop

- **Layout:** `src/gfly/cli.py` (Click grammar + runtime), `backend.py` (google/serpapi engines),
  `throttle.py` (persistent politeness), `auth.py` (keyring), `output.py` (output discipline —
  don't break stdout=data/stderr=chatter), `errors.py` (exit-code table). See `AGENTS.md`.
- **Heavy imports stay lazy** (inside the functions that use them) so `--help`/`schema` stay fast.
- **Read-only:** no command may mutate remote state. Don't add mutations without revisiting `spec.md`.
- **Output contract is append-only:** add fields freely; never rename/remove. A breaking shape change
  means bumping `SCHEMA_VERSION` and updating `tests/test_schema_snapshot.py` in the same PR.
- **Secrets:** stdin/env only, never argv (contract §7).

## Tests

```bash
uv run pytest -q
```

Network is mocked in tests (`tests/conftest.py` monkeypatches the two backend entry points). The
**schema-snapshot test is the CI gate** — if it fails, you changed the agent-facing contract; make
that a deliberate, reviewed diff.

## Pull requests

- Use **[Conventional Commits](https://www.conventionalcommits.org/)** (`feat:`, `fix:`, `docs:`,
  `refactor:`, `test:`, `chore:`) — they drive the changelog and semver bump.
- Sign off your commits (**DCO**): `git commit -s`. No CLA.
- Keep PRs focused; update `CHANGELOG.md` (Unreleased) and docs/`SKILL.md` when behavior changes.
- Green CI required: tests + `gfly schema` smoke.

## Reporting bugs / security

- Bugs: open an issue (the form asks for `gfly --version`, OS, backend, repro, and the JSON error).
- Security: **do not** open a public issue — see [SECURITY.md](SECURITY.md).
