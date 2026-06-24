"""Credential handling for the optional `serpapi` backend and the CAPTCHA-recovery cookie.
The `google` backend needs NO auth (the happy path).

Contract §7: secrets via stdin/env, never argv. Resolution order: env → OS keyring →
0600 XDG file fallback. Headless boxes without a keyring backend degrade gracefully (a
NoKeyringError must never crash the CLI — we fall through to env/file)."""

from __future__ import annotations

import os
import stat
from pathlib import Path

SERVICE = "gfly"
SERPAPI_ENV = "GFLY_SERPAPI_KEY"
ABUSE_COOKIE_ENV = "GFLY_ABUSE_COOKIE"
_KEYS = {"serpapi": "serpapi-key", "abuse-cookie": "abuse-cookie"}


def _file_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "gfly" / "credentials"


def _file_read() -> dict[str, str]:
    p = _file_path()
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    for line in p.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def _file_write(creds: dict[str, str]) -> str | None:
    """Write 0600. Returns a warning string if perms can't be secured."""
    p = _file_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        for k, v in creds.items():
            f.write(f"{k}={v}\n")
    mode = stat.S_IMODE(os.stat(p).st_mode)
    if mode & 0o077:
        return f"WARNING: {p} is {mode:04o}; want 0600. Run: chmod 600 {p}"
    return None


def _keyring_get(name: str) -> str | None:
    try:
        import keyring
        import keyring.errors
        try:
            return keyring.get_password(SERVICE, name)
        except keyring.errors.KeyringError:
            return None
    except Exception:
        return None


def _keyring_set(name: str, value: str) -> bool:
    try:
        import keyring
        import keyring.errors
        try:
            keyring.set_password(SERVICE, name, value)
            return True
        except keyring.errors.KeyringError:
            return False
    except Exception:
        return False


def serpapi_key() -> str | None:
    return (os.environ.get(SERPAPI_ENV)
            or _keyring_get(_KEYS["serpapi"])
            or _file_read().get(_KEYS["serpapi"]) or None)


def abuse_cookie() -> str | None:
    return (os.environ.get(ABUSE_COOKIE_ENV)
            or _keyring_get(_KEYS["abuse-cookie"])
            or _file_read().get(_KEYS["abuse-cookie"]) or None)


def store(kind: str, value: str) -> dict:
    """Persist a credential. Prefers the OS keyring; falls back to a 0600 file. Returns a
    dict with where it landed + any perms warning."""
    name = _KEYS.get(kind)
    if not name:
        raise ValueError(f"unknown credential kind: {kind}")
    if _keyring_set(name, value):
        return {"stored": "keyring", "warning": None}
    creds = _file_read()
    creds[name] = value
    warn = _file_write(creds)
    return {"stored": str(_file_path()), "warning": warn}


def forget(kind: str) -> None:
    name = _KEYS.get(kind)
    try:
        import keyring
        keyring.delete_password(SERVICE, name)
    except Exception:
        pass
    creds = _file_read()
    if name in creds:
        del creds[name]
        _file_write(creds)


def status(backend: str) -> dict:
    """Auth status for a backend, without revealing secrets."""
    if backend == "google":
        return {"backend": "google", "authenticated": True, "method": "none",
                "note": "the google backend requires no authentication"}
    key = serpapi_key()
    return {"backend": "serpapi", "authenticated": bool(key),
            "method": "api_key" if key else None,
            "note": None if key else f"set {SERPAPI_ENV} or run: gfly auth login "
                                     f"--backend serpapi --token-stdin"}


def keyring_available() -> bool:
    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring
        return not isinstance(keyring.get_keyring(), FailKeyring)
    except Exception:
        return False
