"""Update awareness (Agent CLI Guidelines v0.3, Self-description).

Pull-based, structured, fail-silent. gfly NEVER auto-updates and never instructs an agent to
update itself — it only reports availability and the human-facing upgrade command. The agent
treats the binary as a fixed, deterministic dependency within a run."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

from . import __version__

# We can't know which installer the user used, so surface the common ones.
UPGRADE_CMD = "uv tool upgrade gfly  (or: pipx upgrade gfly · pip install -U gfly · brew upgrade gfly)"


def _state_path() -> Path:
    if base := os.environ.get("GFLY_STATE_DIR"):
        return Path(base) / "update.json"
    xdg = os.environ.get("XDG_STATE_HOME")
    root = Path(xdg) if xdg else Path.home() / ".local" / "state"
    return root / "gfly" / "update.json"


def _parse(v: str) -> tuple[int, ...]:
    """Lenient PEP440-ish numeric tuple; non-numeric segments → 0 (fail-soft)."""
    out: list[int] = []
    for part in str(v).split("."):
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        out.append(int(digits) if digits else 0)
    return tuple(out)


def _newer(latest: str | None) -> bool:
    return bool(latest) and _parse(latest) > _parse(__version__)


def fetch_latest(timeout: float = 2.0) -> str | None:
    """Latest gfly version from PyPI. Fail-silent (returns None on any error/timeout)."""
    try:
        req = urllib.request.Request("https://pypi.org/pypi/gfly/json",
                                     headers={"User-Agent": "gfly"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))["info"]["version"]
    except Exception:
        return None


def check(timeout: float = 2.0) -> dict:
    """Structured update status for `gfly version --check`."""
    latest = fetch_latest(timeout)
    avail = _newer(latest)
    return {"current": __version__, "latest": latest, "updateAvailable": avail,
            "upgrade": UPGRADE_CMD if avail else None}


def _cached_latest(ttl: int = 86_400) -> str | None:
    """Latest version via a once-per-day on-disk cache, so the passive human notice costs
    nothing in a hot loop. Fail-silent."""
    p = _state_path()
    now = time.time()
    try:
        data = json.loads(p.read_text())
        if now - data.get("checkedAt", 0) < ttl:
            return data.get("latest")
    except Exception:
        pass
    latest = fetch_latest()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"latest": latest, "checkedAt": now}))
    except Exception:
        pass
    return latest


def passive_notice() -> str | None:
    """A one-line human-only 'update available' hint, or None. Cached daily; never called for
    agents (the caller gates on TTY + human format)."""
    latest = _cached_latest()
    if _newer(latest):
        return f"note: gfly {latest} is available (you have {__version__}); upgrade: {UPGRADE_CMD}"
    return None
