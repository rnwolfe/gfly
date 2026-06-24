# spec.md — gfly

> The build spec for an agent-focused CLI. Written by `cli-plan`; consumed by `cli-scaffold`,
> `cli-implement`, and `cli-publish`. Keep it current — it is the single source of truth.
>
> **gfly** is a read-only, agent-first CLI for searching Google Flights — itinerary search,
> price-calendar (cheapest dates), multi-city, and IATA airport resolution — emitting a
> stable, bounded JSON contract over a swappable data backend.

## Target
- **Service**: Google Flights (consumer flight-shopping product; data lineage = ITA Software / ITA Matrix).
- **Surface**: **Undocumented / reverse-engineered.** No official public API exists — Google's
  **QPX Express** flight API was **retired 2018-04-10** and never replaced with a self-serve
  developer API (enterprise "Travel Partner APIs" are sales-contracted only). Two viable surfaces:
  - **`google` backend (default)** — the reverse-engineered `tfs` endpoint: search params are
    encoded as a **base64 protobuf** in `https://www.google.com/travel/flights?tfs=<b64>&hl=…`,
    fetched unauthenticated, response parsed from Google's serialized data blob. Implemented via
    the **`fast-flights`** library (does the protobuf encode + parse for us).
  - **`serpapi` backend (opt-in)** — SerpApi's Google Flights endpoint returns the same data as
    clean live JSON; trades cost + a key for reliability and volume.
- **Rate limits / pagination**:
  - *google*: no published limits; single-IP scraping hits **HTTP 429** and **CAPTCHA-served-as-200**
    ("soft block") quickly. Recovery relies on a `GOOGLE_ABUSE_EXEMPTION` cookie. Mitigate with
    10–20s spacing, backoff, optional proxy. Google returns the full result set in one response;
    "pagination" is client-side slicing (`--limit`/`--select`), not server cursors.
  - *serpapi*: 250 free successful searches/mo; paid tiers above. Returns `best_flights` /
    `other_flights` in one JSON payload.
- **ToS / risk** *(state loudly)*:
  - The default backend **scrapes an undocumented endpoint** — fragile by design. `fast-flights`'
    own README warns *"get ready to get banned."* Multiple **2026 breakage issues** confirm parsing
    drifts when Google changes its response (#101/#102 Mar 2026, #109 May 2026). Treat schema-drift
    and blocking as **first-class structured-error surfaces**, not crashes. **Pin the library version.**
    Ban risk has three vectors — **rate/volume** (controllable: see *Rate-limiting & politeness* below),
    **bot-fingerprint** (TLS/HTTP2/header order — can CAPTCHA on request #1), and **IP reputation**
    (datacenter ASNs pre-flagged — only fixed by `serpapi`/residential proxy). The politeness layer is
    **harm reduction, not immunity**; `serpapi` remains the reliability escape hatch.
  - No credentials are sent on the default path (low credential-sensitivity), but the data is
    **third-party free text** → prompt-injection surface (airline/layover/fare-brand strings).
  - **SerpApi continuity risk**: Google **sued SerpApi (2025-12-19, N.D. Cal.)** over scraping
    circumvention; outcome unresolved in 2026. Do not make `serpapi` the *only* backend.
- **Prior art / competitive landscape**:
  | Tool | Lang | Stars | Source | Agentic gaps vs contract |
  |---|---|---|---|---|
  | **`fli`** (punitarani) | Python | ~2.9k | reverse-eng direct API | Closest competitor: ships CLI **and** MCP — but **punts agents to the MCP server**; `--format json` is **explicitly experimental/unstable**; **no `schema` cmd, no documented exit codes, no structured error format, no bounded-output story**; human Rich-TUI oriented. |
  | **`fast-flights`** (AWeirdDev) | Python | ~1.1k | base64-protobuf scrape | **Library only — no CLI, no agent surface.** Best *engine*, not a competitor product. |
  | jaebradley/flights-search-cli | JS | 22 | dead QPX API | Abandoned (API gone). |
  | giuseppecampanelli, hugoglvs, Olafs-World | Python | <15 | Selenium/scrape | Stale/tiny human scripts. |
  | ITA Matrix CLI (mayanez) | Python | 84 | ITA Matrix | **Archived since 2014.** |

  No Rust crate exists; no tool from the steipete/agent-CLI cluster covers flights. The
  *agent-engineered CLI* niche is **unclaimed**.
- **Build verdict**: **BUILD** (on top of an existing engine — do **not** re-reverse-engineer
  Google, and do **not** fork `fli`'s human-TUI bundle). Differentiators an agent needs that no
  existing tool delivers:
  1. **JSON-by-default, stable & versioned output contract** (`schemaVersion`) — vs `fli`'s
     self-declared-unstable JSON and `fast-flights`' no-CLI.
  2. **`schema --json` + bundled `agent` SKILL.md** — zero-external-file self-description; nothing
     in the crop has it.
  3. **Structured errors + semantic exit codes for the failure modes that actually happen here** —
     `RATE_LIMITED`, `BLOCKED` (CAPTCHA), `SCHEMA_DRIFT` (upstream parse broke) — so an agent can
     back off / switch backend / report instead of seeing a bare stack trace.
  4. **Token-bounded by default** (`--limit`, `--select`, `--concise`) + IATA resolution so the
     agent isn't handed a 40-itinerary dump.
  5. **Swappable backend behind one contract** (`google` ⇄ `serpapi`) — isolates upstream
     breakage; agent code never changes.
  - **Mine for mechanics**: `fast-flights` (the protobuf encode/parse engine — use as a dependency)
    and `fli`'s CLI command grammar (for naming inspiration only).

## Language & framework
- **Language**: **Python** (>=3.10).
- **Rationale (SDK gravity > distribution > performance)**: The only mature, actively-maintained
  engines that hide Google's brittle protobuf encode + response parsing are Python (`fast-flights`
  v3.0.2 @ 2026-06-17; `fli` ~2.9k★) — re-implementing that churn in Go/TS means owning the breakage
  ourselves, which the build verdict explicitly rejects. This is the classic reverse-eng-API → Python
  pick (same as `mmoney`). Workload is network-bound (a Google fetch can take ~30s), so Python
  cold-start is irrelevant.
- **Framework**: **Click 8.4+** (built-in recursive `to_info_dict()` → `schema --json` in ~10 lines;
  8.4 did-you-mean suggestions; 8.2 split stdout/stderr).
- **SDK/library used**: **`fast-flights`** (pin exact version) for the `google` backend
  (<https://github.com/AWeirdDev/flights> · <https://pypi.org/project/fast-flights/>); direct HTTP to
  SerpApi for the `serpapi` backend (<https://serpapi.com/google-flights-api>).
- **Blueprint**: references/research/blueprint-python.md
- **Language-specific gotchas to honor**:
  - Heavy/optional imports (`fast-flights`, any browser fallback) live in `client.py`/the backend
    module, **lazy-imported** — never at top level (keeps `--help`/`schema` fast).
  - Human output via **Rich on a `Console(stderr=True)`** only; stdout stays machine-clean.
  - Pin `fast-flights` to an exact version; treat its parse output defensively (wrap in our own
    normalizer so an upstream field rename surfaces as `SCHEMA_DRIFT`, not a `KeyError`).
  - `fast-flights` may pull a Playwright/serverless fallback path — gate it behind an explicit
    `--fetch-mode`/extra so the default install stays light and headless-safe.

## Auth
- **Model**: **None on the default path.** The `google` backend is **unauthenticated** — no API key,
  no OAuth, no cookies in the happy path. This is the **best possible agent-auth story**: the agent
  just runs the command. Two narrow credential cases exist:
  - **`serpapi` backend** → an API key (dashboard-provisioned, self-onboardable headlessly; 250 free/mo).
  - **CAPTCHA recovery** → an optional `GOOGLE_ABUSE_EXEMPTION` cookie value when Google soft-blocks.
- **Provider constraints**: SerpApi key has no TTL/refresh (static key). `GOOGLE_ABUSE_EXEMPTION`
  cookie is short-lived and host-issued. No HTTPS-callback / device-flow / PKCE concerns — there is
  no OAuth anywhere.
- **Feasible path to usability (end-to-end)**:
  - **Default (zero-auth)**: agent runs `gfly search …` → results. Nothing to provision. ✅
  - **SerpApi**: user creates a free SerpApi account once, copies the key, provides it headlessly via
    `gfly auth login --backend serpapi --token-stdin` (reads key from **stdin**, stores in OS keyring)
    or `GFLY_SERPAPI_KEY` env. Fully headless thereafter. ✅
  - **CAPTCHA recovery (rare)**: when a call returns `BLOCKED`, the structured error tells the agent
    to either back off / retry later, switch `--backend serpapi`, or (human onboarding) solve the
    challenge once in a browser and pass the exemption cookie via `GFLY_ABUSE_COOKIE` / `--abuse-cookie-stdin`.
  - **Never browser-only as the sole path** (contract §7) — the zero-auth default is the primary path.
- **Secret storage**: OS keyring + `0600` XDG file fallback; warn on insecure perms. Secrets only via
  **stdin/env, never argv** (contract §7).
- **Subcommands**: `auth login | status | logout` (per-backend; `refresh` is a no-op/absent — no
  refreshable tokens). `doctor` probes reachability + whether the upstream is currently blocking/drifted.

## Rate-limiting & politeness (persistent)
The default `google` backend scrapes an undocumented endpoint; uncontrolled call rate is the
**single most controllable** ban vector, so gfly ships a politeness layer by default.

- **Persistent state (the crux for a CLI):** the agent invokes `gfly` as a **fresh process per call**,
  so an in-memory timer is a no-op. Rate state is persisted to the **XDG state dir**
  (`$XDG_STATE_HOME/gfly/ratelimit.json`, default `~/.local/state/gfly/`): last-request timestamp,
  a rolling window of recent call times, and a `blocked_until` cooldown — enforced **across processes**.
  Keyed per-backend (google vs serpapi don't share a budget).
- **Min-interval throttle:** enforce `--min-interval` seconds between upstream `google` calls
  (default ~12–15s; env `GFLY_MIN_INTERVAL`). serpapi is exempt (paid, has its own quota).
- **Circuit breaker:** on `429` or CAPTCHA-soft-block, write `blocked_until` with **exponential
  backoff + jitter**. Calls inside that window short-circuit without hitting Google (avoids deepening
  the block). A successful call resets the backoff.
- **Fail-fast by default, opt-in wait (agent ergonomics):** inside a cooldown the default is to
  **return a structured `RATE_LIMITED`/`BLOCKED` error with a `retryAfterSeconds` field and exit
  non-zero** — never silently sleep (a hung CLI deadlocks an agent loop / trips its timeout; same
  rationale as `--no-input` hard-failing). `--wait` / `--max-wait N` opt into blocking sleep up to a
  cap for human/script use. `--no-throttle` bypasses the min-interval (escape hatch; documented as risky).
- **Surfaced in `doctor` and `schema --json`:** `doctor` reports current cooldown / next-allowed time;
  `schema --json` includes the live throttle state alongside the safety state.

## Command surface (noun-verb)
All commands are **reads** — gfly cannot book or mutate anything. The `--allow-mutations` gate is
present (scaffold-provided) but trivially satisfied; the real safety surface is **prompt-injection
fencing** of third-party text and **rate-limit/blocking errors**.

| Command | Read/Mutation | Description | Key output fields |
|---|---|---|---|
| `gfly search <from> <to>` | read | One-way/round-trip itinerary search. Flags: `--depart`, `--return`, `--adults/--children/--infants`, `--cabin economy\|premium\|business\|first`, `--stops any\|nonstop\|1`, `--sort price\|duration\|best`, `--currency`. | `itineraries[]`: `price`, `currency`, `airlines[]`, `flightNumbers[]`, `durationMinutes`, `stops`, `layovers[]{airport,minutes}`, `departure`, `arrival`, `origin`, `destination`, `co2Grams`, `co2DeltaPct`, `isBest`, `bookingToken` |
| `gfly dates <from> <to>` | read | Price calendar / cheapest dates across a window (`--depart-range`, `--trip-length`, `--months`). | `dates[]`: `departDate`, `returnDate`, `price`, `currency` |
| `gfly multi <leg…>` | read | Multi-city search; repeatable `--leg FROM:TO:DATE`. | same itinerary shape as `search`, with per-leg breakdown |
| `gfly airports search <query>` | read | Resolve a city/name to IATA code(s) so agents don't guess. | `airports[]`: `iata`, `name`, `city`, `country` |
| `gfly auth login\|status\|logout` | read* | Manage the optional SerpApi key / abuse cookie. `status` redacts secrets, exits non-zero on problems. | `backend`, `authenticated`, `method` |
| `gfly doctor` | read | Probe upstream reachability; detect block/drift; report active backend + safety state. | `backend`, `reachable`, `blocked`, `schemaOk`, `checks[]` |
| `gfly schema --json` | read | Full command tree + flags + exit-code table + live safety state. | (contract §5) |
| `gfly agent` | read | Print bundled SKILL.md. | (raw text) |

*`auth` writes only local credential storage, not remote state.

## Exit codes
Start from contract §4; gfly-specific additions for the reverse-eng failure modes:
```
0   ok                     5  not found (e.g. unknown IATA)     12 mutation blocked (defined; unused — read-only tool)
1   generic error          6  permission denied                 13 input required (--no-input hit a prompt)
2   usage/parse            7  rate limited (HTTP 429)            130 cancelled (SIGINT)
3   empty results          8  retryable/transient (network)
4   auth required          10 config error
                          ── gfly additions ──
20  BLOCKED        — Google served a CAPTCHA / soft-block; back off, retry later, or --backend serpapi
21  SCHEMA_DRIFT   — upstream response no longer parses (library breakage); switch backend / upgrade / report
```

## Output schema
Stable, append-only, `schemaVersion`-stamped. Top level:
```jsonc
{
  "schemaVersion": "1",
  "backend": "google",                 // or "serpapi"
  "query": { "from": "JFK", "to": "LHR", "depart": "2026-08-01", "return": null, "adults": 1, "cabin": "economy" },
  "currency": "USD",
  "count": 12,
  "itineraries": [
    {
      "price": 642,
      "currency": "USD",
      "isBest": true,
      "stops": 0,
      "durationMinutes": 425,
      "departure": "2026-08-01T18:30:00-04:00",
      "arrival":   "2026-08-02T06:35:00+01:00",
      "origin": "JFK",
      "destination": "LHR",
      "airlines": ["British Airways"],
      "flightNumbers": ["BA112"],
      "layovers": [],                  // [{ "airport": "BOS", "minutes": 75 }]
      "co2Grams": 412000,
      "co2DeltaPct": -8,
      "bookingToken": "…"              // opaque, for downstream deep-fetch
    }
  ],
  "nextCursor": null                   // client-side slice marker if --limit truncated
}
```
`dates`, `multi`, and `airports search` define their own append-only shapes (see command table).
All free-text fields originating from the target (airline names, fare brands, layover labels) are
**fenced as untrusted in agent mode** (contract §8).

## Universal contract surface (provided by scaffold — confirm no conflicts)
`--format json|plain|tsv` · `--allow-mutations` *(present, unused — read-only tool)* · `--dry-run`
*(degenerate: no mutations to plan)* · `--yes`/`--force` · `--no-input` · `--limit` (default 25) ·
`--select` · `--concise`/`--detailed` · `schema --json` · `agent`. **No conflicts** — gfly adds
`--backend google|serpapi` as a root flag, `--currency` on search/dates/multi, and the politeness
flags `--min-interval` / `--wait` / `--max-wait` / `--no-throttle` (see *Rate-limiting & politeness*).
`RATE_LIMITED`/`BLOCKED` errors extend the contract §3 shape with a **`retryAfterSeconds`** field so an
agent can schedule its retry or switch backend.

## Distribution
- **Targets**: `uv build` + `uv publish` to PyPI (Trusted Publishing/OIDC); installable via
  `uv tool install gfly`, `uvx gfly`, and `pipx install gfly`. No single-binary (rely on uv/pipx).
- **Trial path**: `uvx gfly search JFK LHR --depart 2026-08-01` — zero-install, no auth.
- **Agent hot-loop path**: `uv tool install gfly` once, then call the bare `gfly` binary
  (avoids per-call `uvx` resolution overhead).

## Publish
- **Flag**: **full**
- **If full**: docs site (starlight-docs) · doc content (harvest-docs) · release pipeline (release
  skill) · README + VHS demo · hygiene files · discoverability (PyPI, agent-cli-guidelines, Show HN).
  Lead the README with the **zero-auth** trial line — it is gfly's strongest hook.

## Prompt-injection surface
`search`, `dates`, and `multi` return **third-party free text** (airline names, fare-brand strings,
layover/airport labels) sourced from Google → **fence as untrusted by default in agent mode**
(`--wrap-untrusted`, default-ON for agents, per contract §8). `airports search` returns reference data
(IATA/city/country) — lower risk but still wrapped for consistency. `doctor`/`schema`/`agent` emit only
gfly-controlled text.
