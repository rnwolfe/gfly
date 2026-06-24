---
title: Authentication
description: The google backend needs no credentials. Only serpapi requires an API key — here is how to store, inspect, and remove it safely.
owner: rnwolfe
lastReviewed: 2026-06-24
sidebar:
  order: 3
---

The default `google` backend requires **no authentication at all** — you can start searching immediately after install. Auth exists only for two optional cases:

1. The [`serpapi` backend](/guides/backends/) — needs a SerpApi API key.
2. CAPTCHA recovery — an optional `GOOGLE_ABUSE_EXEMPTION` cookie that can lift a soft-block on the `google` backend.

```bash
# Check whether you need to do anything
gfly auth status

# Store a SerpApi key (secret read from stdin, never an arg)
echo "$SERPAPI_KEY" | gfly auth login --token-stdin

# Remove the locally stored key
gfly auth logout --backend serpapi
```

## `auth login`

Stores a credential in the OS keyring (file fallback on headless systems). Secrets are **stdin-only** — passing them as command-line flags is intentionally not supported because flags leak into `ps`, `/proc`, and shell history.

```bash
# SerpApi key
echo "$SERPAPI_KEY" | gfly auth login --token-stdin

# CAPTCHA-recovery cookie (google backend)
echo "$COOKIE_VALUE" | gfly auth login --abuse-cookie-stdin
```

Flags:

| Flag | What it does |
|---|---|
| `--token-stdin` | Read the SerpApi key from stdin |
| `--abuse-cookie-stdin` | Read a `GOOGLE_ABUSE_EXEMPTION` cookie from stdin (CAPTCHA recovery) |

On success gfly emits `{"ok": true, "kind": "...", "stored": "..."}` where `stored` is either `"keyring"` or the path of the file that was written.

:::caution
If neither `--token-stdin` nor `--abuse-cookie-stdin` is passed, the command raises a `USAGE` error (exit 2). An empty stdin also fails fast rather than storing a blank credential.
Note: `--backend` has no effect on which credential is stored — use `--token-stdin` for the SerpApi key and `--abuse-cookie-stdin` for the CAPTCHA-recovery cookie.
:::

## `auth status`

Checks whether the active backend has valid credentials and prints the result without revealing the secret.

```bash
gfly auth status                      # uses the default (google) backend
gfly auth status --backend serpapi    # checks for a SerpApi key
```

For the `google` backend the response is always `authenticated: true` (no key needed). For `serpapi` it resolves the key through the full lookup chain and exits non-zero with `AUTH_REQUIRED` (exit 4) if nothing is found, along with a `remediation` hint.

## `auth logout`

Removes the locally stored credential. It does **not** revoke the key at the provider.

```bash
gfly auth logout --backend serpapi    # removes the stored SerpApi key
gfly auth logout --backend google     # removes the stored abuse cookie
```

:::note
`logout` prints `{"ok": true, "kind": "...", "note": "removed local credential only"}`. To invalidate a leaked key, rotate it at [serpapi.com/manage-api-key](https://serpapi.com/manage-api-key) first, then run `gfly auth logout`, then store the new key.
:::

## Where secrets live

Resolution order (first match wins):

| Priority | Source | How to set |
|---|---|---|
| 1 | Environment variable | `GFLY_SERPAPI_KEY` / `GFLY_ABUSE_COOKIE` |
| 2 | OS keyring | Written by `gfly auth login` |
| 3 | `0600` XDG file | `$XDG_CONFIG_HOME/gfly/credentials` (default `~/.config/gfly/credentials`) |

`auth login` always tries the OS keyring first. If the keyring is unavailable (common on headless servers), it falls through to the file without error. gfly **never crashes** on a missing keyring backend.

If the file is created but its permissions are wider than `0600`, gfly prints a warning on stderr and tells you how to fix it:

```
WARNING: /home/you/.config/gfly/credentials is 0644; want 0600. Run: chmod 600 /home/you/.config/gfly/credentials
```

### Environment variables

You can skip `auth login` entirely by exporting credentials in your shell or CI environment:

```bash
export GFLY_SERPAPI_KEY="your-key-here"
gfly search JFK LHR --depart 2026-07-15 --backend serpapi
```

```bash
# In a CI pipeline (e.g. GitHub Actions)
env:
  GFLY_SERPAPI_KEY: ${{ secrets.SERPAPI_KEY }}
```

The full list of auth-related env vars:

| Variable | Purpose |
|---|---|
| `GFLY_SERPAPI_KEY` | SerpApi API key |
| `GFLY_ABUSE_COOKIE` | `GOOGLE_ABUSE_EXEMPTION` cookie value |
| `GFLY_BACKEND` | Set the default backend (`google` or `serpapi`) |

## CAPTCHA recovery cookie

If the `google` backend is soft-blocked by Google (you see CAPTCHA-related errors), you can supply a `GOOGLE_ABUSE_EXEMPTION` cookie obtained from a logged-in browser session. This is a workaround, not a guarantee.

```bash
# Store via auth login
echo "$COOKIE" | gfly auth login --backend google --abuse-cookie-stdin

# Or export directly
export GFLY_ABUSE_COOKIE="your-cookie-value"
```

The cookie follows the same storage resolution order (env → keyring → file) as the SerpApi key.

:::tip
If you are hitting the `google` backend frequently in production, the [`serpapi` backend](/guides/backends/) is the more reliable path — it has no CAPTCHA exposure and provides richer data (flight numbers, booking tokens, best/other split).
:::

## Headless and CI environments

On machines without a desktop keyring (Docker containers, CI runners, remote servers), gfly detects that no keyring backend is available and degrades gracefully to the `0600` file or the environment variable. It logs this to stderr but never raises an error.

The recommended approach for headless use:

1. Set `GFLY_SERPAPI_KEY` as a secret environment variable in your CI/CD system.
2. Never write the key to disk in CI; rely on the env var alone.
3. Run `gfly doctor` to confirm the key is found and which path is in use.

## Diagnosing with `doctor`

`gfly doctor` reports the full auth state alongside throttle and connectivity checks:

```bash
gfly doctor --backend serpapi
```

Example output (JSON, truncated):

```json
{
  "checks": [
    { "name": "auth",    "ok": true,  "detail": "ok" },
    { "name": "keyring", "ok": false, "detail": "no OS keyring backend; using env / 0600 file fallback" },
    { "name": "throttle","ok": true,  "detail": "clear" }
  ]
}
```

The `auth` check resolves the credential through the full lookup chain and reports `ok` or the exact remediation step needed. `keyring` reports which storage path is active. See [Rate limits & bans](/guides/rate-limits/) for the throttle fields.
