"""PLACEHOLDER auth — credential resolution for the optional `serpapi` backend and the
CAPTCHA-recovery cookie. The `google` backend needs NO auth (the happy path).

Contract §7: secrets via stdin/env, never argv. Persist in the OS keyring; `0600` XDG file
fallback; warn on insecure perms. `cli-implement` wires real keyring storage — this scaffold
resolves from env only (so it runs headless in CI without a keyring backend) and marks where
keyring read/write goes.

Resolution order (intended): env → OS keyring → config file → (never prompt under --no-input).
"""

from __future__ import annotations

import os

SERPAPI_ENV = "GFLY_SERPAPI_KEY"
ABUSE_COOKIE_ENV = "GFLY_ABUSE_COOKIE"


def serpapi_key() -> str | None:
    """Resolve the SerpApi key. PLACEHOLDER: env only; cli-implement adds keyring lookup."""
    return os.environ.get(SERPAPI_ENV) or None


def abuse_cookie() -> str | None:
    return os.environ.get(ABUSE_COOKIE_ENV) or None


def status(backend: str) -> dict:
    """Report auth status for a backend without revealing secrets."""
    if backend == "google":
        return {"backend": "google", "authenticated": True, "method": "none",
                "note": "the google backend requires no authentication"}
    key = serpapi_key()
    return {"backend": "serpapi", "authenticated": bool(key),
            "method": "api_key" if key else None,
            "note": None if key else f"set {SERPAPI_ENV} or run: gfly auth login "
                                     f"--backend serpapi --token-stdin"}


def store_key(backend: str, value: str) -> None:
    """PLACEHOLDER: cli-implement persists to the OS keyring (0600 file fallback)."""
    raise NotImplementedError(
        "credential storage is wired by cli-implement; for now export "
        f"{SERPAPI_ENV} in the environment")
