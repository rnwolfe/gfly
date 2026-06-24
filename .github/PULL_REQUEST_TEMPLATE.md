<!-- Title must follow Conventional Commits, e.g. `feat: add --max-price filter` -->

## What & why

<!-- What does this change and why? Link any issue: Closes #123 -->

## Checklist

- [ ] Title uses [Conventional Commits](https://www.conventionalcommits.org/) (`feat:` / `fix:` / `docs:` / …)
- [ ] `uv run pytest -q` passes locally
- [ ] Output contract respected: **append-only** fields; stdout=data / stderr=chatter
- [ ] If the agent-facing schema changed: `SCHEMA_VERSION` bumped + `tests/test_schema_snapshot.py` updated
- [ ] No secrets via argv; read-only invariant preserved (no new mutations)
- [ ] `CHANGELOG.md` (Unreleased) and docs / `SKILL.md` updated if behavior changed
- [ ] Commits signed off (`git commit -s`, DCO)
