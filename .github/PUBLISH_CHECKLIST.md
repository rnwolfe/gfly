# Publish checklist (manual operator steps)

The repo, README, demo, hygiene, landing page, and release pipeline are ready. These steps require
your credentials / a browser and can't be automated from here.

## 1. Create the GitHub repo & push
```bash
gh repo create rnwolfe/gfly --public --source=. --remote=origin --push \
  --description "Google Flights for agents — a read-only, JSON-first flight-search CLI an LLM can drive (no API key)."
```

## 2. Repo settings (Settings → …)
- **Topics** (≤20, lowercase-hyphen): `cli` `google-flights` `flight-search` `agent` `llm`
  `agentic` `python` `uv` `travel` `json` `read-only` `serpapi`.
- **About → website**: the docs/landing URL once hosted.
- **Social preview**: upload a 1280×640 card (reuse the split-flap board aesthetic from `site/`).
- **Security → enable Private Vulnerability Reporting** (required for SECURITY.md's flow).
- **Discussions**: enable (SUPPORT.md and the issue `config.yml` link to it).
- **Branches → protect `main`**: require PR + status checks (`ci`) + **require review from Code Owners**.

## 3. PyPI Trusted Publishing (no stored secrets)
- Register the project on PyPI, then add a **Trusted Publisher**: owner `rnwolfe`, repo `gfly`,
  workflow `release.yml`, environment `pypi`. Must match the workflow exactly.
- Create a repo **Environment** named `pypi`.

## 4. First release (delegate to the `release` skill)
- Run `/release` to: bump version from Conventional Commits, finalize `CHANGELOG.md`, and create an
  **SSH-signed annotated tag** (→ "Verified" badge). Push the tag → `release.yml` builds, attests
  provenance, publishes to PyPI (OIDC), and creates the GitHub Release with `SHA256SUMS`.
- Verify: `gh attestation verify <wheel> -R rnwolfe/gfly`.

## 5. Docs site (delegate)
- `/starlight-docs` — scaffold the Astro Starlight site (Diátaxis IA, `llms.txt`, Pagefind search,
  GitHub Pages deploy + base-path config, AGENTS.md freshness wiring).
- `/harvest-docs` — fill it from the code (multi-agent: scavenge → IA → per-page writers → reviewers).
- Auto-generate the Reference quadrant from Click; add the CI freshness gate (regenerate + `git diff --exit-code`).

## 6. Host the landing page
- `site/index.html` is self-contained (only `gfly.gif` alongside it). Serve via GitHub Pages, or
  `expose` for a quick LAN review. Optionally reserve `gfly.sh`.

## 7. Discoverability (after a tag + >20 stars where required)
- **awesome-cli-apps** (one app/PR, format `[gfly](url) - Description.`).
- **awesome-agent-clis** (ComposioHQ) — folder + the bundled `SKILL.md`.
- **clis.dev** `/submit`; terminaltrove.com.
- Launch: **Show HN** (`Show HN: gfly – Google Flights for agents (no API key)`, link the repo, be
  present the first 30–60 min); r/commandline; Product Hunt 12:01 PT.
