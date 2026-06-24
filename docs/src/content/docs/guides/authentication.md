---
title: Authentication
description: The google backend needs no auth. Only serpapi needs a key — stored in the OS keyring.
---

The default `google` backend needs **no authentication**. Auth exists only for the optional
[`serpapi` backend](/guides/backends/) and the rare CAPTCHA-recovery cookie. gfly follows the `gh`
model.

```bash
gfly auth login  --backend serpapi --token-stdin   # secret via STDIN, never argv
gfly auth status --backend serpapi                 # tests + redacts; non-zero on problems
gfly auth logout --backend serpapi                 # removes the LOCAL credential only
```

## Where secrets live

Resolution order: `GFLY_SERPAPI_KEY` env → **OS keyring** → `0600` XDG file fallback. A warning prints
if the file's perms can't be secured. Secrets are **never** accepted as flags (they'd leak to
`ps` / `/proc` / shell history). On a headless box with no keyring backend, gfly degrades to the file
or env — it never crashes, and `gfly doctor` reports which path is in use.

## Revocation

Logout removes only the local copy. To revoke, rotate the key at
[serpapi.com](https://serpapi.com/manage-api-key). If a key leaks: revoke at the provider first,
then `gfly auth logout`, then issue a new one.

## CAPTCHA recovery cookie

If the google backend is soft-blocked, you can supply a `GOOGLE_ABUSE_EXEMPTION` cookie:

```bash
echo "$COOKIE" | gfly auth login --backend google --abuse-cookie-stdin
# or: export GFLY_ABUSE_COOKIE=...
```
