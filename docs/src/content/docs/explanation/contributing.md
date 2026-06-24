---
title: Contributing
description: Setup, the agent-CLI contract rules, and how to propose changes.
---

`gfly` is an agent-first, read-only Google Flights CLI. The full guide lives in
[CONTRIBUTING.md](https://github.com/rnwolfe/gfly/blob/main/CONTRIBUTING.md); the essentials:

## Setup

```bash
git clone https://github.com/rnwolfe/gfly
cd gfly
uv sync --extra dev
uv run pytest -q          # tests must stay green
```

## Rules that matter

- **Read-only.** No command may mutate remote state.
- **Output contract is append-only.** Add fields freely; never rename/remove. A breaking shape change
  bumps `SCHEMA_VERSION` and updates the schema-snapshot test in the same PR.
- **stdout = data, stderr = chatter.** Don't break the split.
- **Secrets via stdin/env, never argv.**
- **Heavy imports stay lazy** so `--help` / `schema` stay fast.

## Docs

These docs live in `docs/` (Astro Starlight). Public-surface changes (commands, flags, exit codes,
output fields) must update the matching page **in the same PR**.

```bash
cd docs && pnpm install && pnpm dev --host 0.0.0.0   # local preview
pnpm build                                            # regenerates llms.txt
```

## Proposing changes

Use [Conventional Commits](https://www.conventionalcommits.org/), sign off (`git commit -s`, DCO), and
keep CI green. Security issues: see
[SECURITY.md](https://github.com/rnwolfe/gfly/blob/main/SECURITY.md) — never a public issue.
