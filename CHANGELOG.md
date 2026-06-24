# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/rnwolfe/gfly/commits/main
