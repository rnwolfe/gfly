---
title: Commands
description: The full gfly command surface — all read-only.
sidebar:
  order: 1
---

Every command is a **read**. `gfly schema` always prints the authoritative, machine-readable tree.

| Command | Description |
|---|---|
| `gfly search <from> <to>` | One-way / round-trip itinerary search |
| `gfly dates <from> <to>` | Cheapest price per departure date (one search per day) |
| `gfly multi --leg …` | Multi-city (≥2 legs; google backend only) |
| `gfly airports search <q>` | Offline IATA resolution |
| `gfly auth login\|status\|logout` | Manage the optional serpapi key / abuse cookie |
| `gfly doctor` | Auth, keyring, connectivity, and throttle health |
| `gfly schema` | Command tree + flags + exit codes + live state + env vars |
| `gfly agent` | Print the embedded SKILL.md (the usage contract) |
| `gfly version` | Version as JSON (`gfly --version` prints the bare string) |

## Global flags (any position)

| Flag | Purpose |
|---|---|
| `--json` / `--format json\|plain\|tsv` | Output format (JSON by default when piped) |
| `--select a,b` | Project these dot-path fields from each record |
| `--limit N` / `--offset N` | Bound and paginate results (`nextCursor` = next offset) |
| `--backend google\|serpapi` | Choose the data source |
| `--currency` | ISO currency for prices |
| `--min-interval` / `--wait` / `--max-wait` / `--no-throttle` | [Throttle control](/guides/rate-limits/) |
| `--proxy` | HTTP(S) proxy for the google backend |
| `--no-wrap-untrusted` | Disable fencing of third-party text (on by default) |
| `--no-input` | Never prompt; fail with exit 13 instead |

`--allow-mutations` / `--dry-run` / `--yes` / `--force` exist for contract uniformity but are
**no-ops** — gfly is read-only.

## Environment variables

`GFLY_BACKEND`, `GFLY_CURRENCY`, `GFLY_MIN_INTERVAL`, `GFLY_NO_THROTTLE`, `GFLY_PROXY`,
`GFLY_SERPAPI_KEY`, `GFLY_ABUSE_COOKIE`, `GFLY_STATE_DIR`, `NO_COLOR`. All are listed under `env` in
`gfly schema`.
