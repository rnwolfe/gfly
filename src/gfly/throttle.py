"""Persistent, cross-process politeness layer for the reverse-engineered `google` backend.

Why on disk: gfly is invoked as a *fresh process per call* by an agent, so an in-memory
timer is a no-op. State (last-request time, recent-call window, circuit-breaker cooldown)
lives in the XDG state dir and is enforced across invocations. See spec.md
"Rate-limiting & politeness".

Policy (spec-faithful):
- Default is FAIL-FAST: if a request must be delayed (min-interval not elapsed, or inside a
  block cooldown) we raise a structured RATE_LIMITED/BLOCKED with retryAfterSeconds and exit
  non-zero — never silently sleep (a hung CLI deadlocks an agent loop).
- `--wait` opts into blocking sleep up to `--max-wait` seconds, then proceeds (or fails if the
  cooldown still hasn't cleared).
- `--no-throttle`, `min_interval <= 0`, and the `serpapi` backend bypass throttling entirely.

cli-implement wires real upstream signals into `record_block()` (on a 429 / CAPTCHA) and
`record_success()` (to reset backoff). The min-interval guard already works as scaffolded.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .errors import blocked as _blocked
from .errors import rate_limited as _rate_limited

# Circuit-breaker backoff schedule (seconds), indexed by consecutive-block count.
_BACKOFF = [30, 60, 120, 300, 600, 1800]


def state_path() -> Path:
    if p := os.environ.get("GFLY_STATE_DIR"):
        return Path(p) / "ratelimit.json"
    base = os.environ.get("XDG_STATE_HOME")
    root = Path(base) if base else Path.home() / ".local" / "state"
    return root / "gfly" / "ratelimit.json"


def _load() -> dict:
    p = state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text() or "{}")
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def _now() -> float:
    return time.time()


def snapshot(backend: str) -> dict:
    """Live throttle state for `doctor` / `schema --json`."""
    s = _load().get(backend, {})
    now = _now()
    blocked_until = s.get("blocked_until", 0)
    last = s.get("last_request", 0)
    return {
        "backend": backend,
        "lastRequest": last or None,
        "blocked": blocked_until > now,
        "blockedUntil": blocked_until or None,
        "cooldownSeconds": max(0, round(blocked_until - now)) if blocked_until > now else 0,
        "consecutiveBlocks": s.get("consecutive_blocks", 0),
    }


def guard(backend: str, *, min_interval: float, wait: bool, max_wait: float,
          no_throttle: bool) -> None:
    """Enforce politeness before an upstream request. Raises AppError, or records the
    request time and returns. `serpapi` and `--no-throttle` are exempt."""
    if no_throttle or backend == "serpapi" or min_interval <= 0:
        return

    data = _load()
    s = data.get(backend, {})
    now = _now()

    # 1) circuit breaker (block cooldown from a prior 429/CAPTCHA)
    blocked_until = s.get("blocked_until", 0)
    if blocked_until > now:
        remaining = blocked_until - now
        if wait and remaining <= max_wait:
            time.sleep(remaining)
            now = _now()
        else:
            raise _blocked(round(blocked_until - now))

    # 2) min-interval spacing
    last = s.get("last_request", 0)
    elapsed = now - last
    if last and elapsed < min_interval:
        need = min_interval - elapsed
        if wait and need <= max_wait:
            time.sleep(need)
            now = _now()
        else:
            raise _rate_limited(round(need) or 1)

    # record this request
    s["last_request"] = now
    window = [t for t in s.get("window", []) if now - t < 600] + [now]
    s["window"] = window
    data[backend] = s
    _save(data)


def record_block(backend: str) -> int:
    """Open/extend the circuit breaker after an upstream 429/CAPTCHA. Returns the cooldown
    seconds. (Called by cli-implement when the real backend reports a block.)"""
    data = _load()
    s = data.get(backend, {})
    level = min(s.get("consecutive_blocks", 0), len(_BACKOFF) - 1)
    cooldown = _BACKOFF[level]
    s["consecutive_blocks"] = s.get("consecutive_blocks", 0) + 1
    s["blocked_until"] = _now() + cooldown
    data[backend] = s
    _save(data)
    return cooldown


def record_success(backend: str) -> None:
    """Reset the backoff after a clean upstream response."""
    data = _load()
    s = data.get(backend, {})
    if s.get("consecutive_blocks") or s.get("blocked_until"):
        s["consecutive_blocks"] = 0
        s["blocked_until"] = 0
        data[backend] = s
        _save(data)
