# Security Policy

## Supported versions

`gfly` is pre-1.0; only the latest released version receives security fixes.

| Version | Supported |
|---------|-----------|
| latest `0.x` | ✅ |
| older | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Use **GitHub Private Vulnerability Reporting** (the repo's *Security → Report a vulnerability*
tab), or email **rn.wolfe@gmail.com** with `gfly security` in the subject.

- **Acknowledgement:** within ~48 hours.
- **Disclosure:** coordinated. We'll agree on a timeline and credit you (opt-in) in the release notes.
- **Safe harbor:** good-faith research that respects others' privacy/data and avoids service
  disruption will not be pursued. Include a minimal reproducible PoC and the `gfly --version`.

When reporting, **never paste live secrets** (SerpApi keys, cookies). Redact them, and rotate any
secret you believe was exposed.

## Secret-handling threat model

`gfly`'s default `google` backend uses **no credentials at all**. Secrets exist only for the optional
`serpapi` backend (an API key) and the optional CAPTCHA-recovery cookie. We design around these risks:

| Threat | Mitigation |
|---|---|
| **Leak via `ps` / `/proc` / shell history** | Secrets are **never** accepted as CLI flags/argv. Input is **stdin-only** (`--token-stdin`) or env. |
| **At-rest exposure** | Stored in the **OS keyring** (Secret Service / Keychain / Credential Manager). Fallback is a `0600` file under `$XDG_CONFIG_HOME/gfly/`; gfly **warns** if it can't secure the perms. |
| **Leak via logs / output** | `auth status` redacts the secret by default. Secrets are never echoed by `auth login`, never written to stdout, and never appear in error messages. |
| **Leak via env in CI logs** | `GFLY_SERPAPI_KEY` is supported for CI (ephemeral) but documented as a CI-only convenience; humans should prefer the keyring. |
| **Headless boxes without a keyring** | A missing keyring backend degrades gracefully to the `0600` file or env — it never crashes, and the fallback is reported by `gfly doctor`. |
| **Third-party content as injection** | Flight text from the upstream (airline names, fare brands, layover labels) is **fenced/sanitized as untrusted by default** (`--wrap-untrusted`): control chars/newlines stripped, length-capped, and an `_warning` marker added. Treat it as data, not instructions. |
| **Upstream tampering / breakage** | The reverse-engineered backend is treated as untrusted: parse failures become `SCHEMA_DRIFT` (exit 21), blocks become `BLOCKED` (exit 20) — never silent wrong data. |

### Rotation & revocation

- **Logout ≠ revocation.** `gfly auth logout` removes the *local* credential only.
- Revoke/rotate a SerpApi key at <https://serpapi.com/manage-api-key>.
- If a key leaks: revoke it at the provider first, then `gfly auth logout`, then issue a new key.
