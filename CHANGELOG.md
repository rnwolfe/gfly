# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-06-25

Rolls up to **Agent CLI Guidelines v0.4.0, Full**.

### Added
- Machine-readable **conformance block** in `gfly schema --json`:
  `{"spec": "agent-cli-guidelines", "version": "0.4.0", "level": "Full"}` (sourced from the
  package `SPEC` constant), so an agent can verify the contract version from the binary.
- `gfly version --check` — structured, fail-silent update awareness
  (`{current, latest, updateAvailable, upgrade}`); never auto-updates. Plus a human-only,
  daily-cached passive "update available" notice (TTY + plain only; silent for agents).

### Changed
- Pinned the conformance statement to **Agent CLI Guidelines v0.4.0, Full** (was an imprecise
  "v0.3") across the README and the for-agents reference.

### Security
- Update check fetches only a hardcoded PyPI endpoint (`https://pypi.org/pypi/gfly/json`) with a
  fixed `User-Agent`; there is no `*_RELEASES_URL` override, so no SSRF override-guard is needed.

## [0.2.0] - 2026-06-25

Reaches **Agent CLI Guidelines v0.3, Full**.

### Added
- `gfly version --check` — structured, fail-silent update awareness
  (`{current, latest, updateAvailable, upgrade}`); never auto-updates. Plus a human-only,
  daily-cached passive "update available" notice (TTY + plain only; silent for agents).
- `dates` now **declares a capped window in the envelope** (`partial`, `scannedDays`,
  `requestedDays`, `narrowed`) instead of only on stderr.
- Explicit **legitimacy-boundary** disclosure (personal/legitimate scale; reduce-volume, never
  evade) in the README and the embedded `agent` output.

These close the gap to **Agent CLI Guidelines v0.3, Full** (the new v0.2/v0.3 SHOULDs:
update-awareness, declare-narrowed-results, and the legitimacy-boundary statement). Core (the
10 invariants) was already met; backpressure was already exemplary.

## [0.1.0] - 2026-06-23

First public release.

### Added
- `search` (one-way / round-trip), `dates` (price calendar), `multi` (multi-city), and
  `airports search` (offline IATA resolution) commands.
- Swappable backends: `google` (reverse-engineered, zero-auth, default) and `serpapi` (live JSON, keyed).
- Agent-CLI contract: stable versioned JSON envelope (`schemaVersion`), `schema` self-description,
  embedded `agent` SKILL.md, `--select`/`--limit`/`--offset` token bounding, `--format json|plain|tsv`.
- Semantic exit codes incl. `BLOCKED` (20) and `SCHEMA_DRIFT` (21); structured errors with
  `retryAfterSeconds` on throttle/block.
- Persistent, cross-process politeness throttle (min-interval + circuit breaker) with fail-fast
  default and `--wait` opt-in.
- `auth login|status|logout` (OS keyring + `0600` file fallback, stdin-only secrets); real `doctor`.
- Prompt-injection hardening: third-party text sanitized and fenced as untrusted by default.

[Unreleased]: https://github.com/rnwolfe/gfly/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/rnwolfe/gfly/releases/tag/v0.3.0
[0.2.0]: https://github.com/rnwolfe/gfly/releases/tag/v0.2.0
[0.1.0]: https://github.com/rnwolfe/gfly/releases/tag/v0.1.0
