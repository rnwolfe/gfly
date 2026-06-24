"""The output contract: data to stdout, chatter to stderr, stable JSON, --format,
--select projection, --limit bounding. See contract.md §1, §6.

Copied verbatim from the agent-cli-factory Python template — do not edit (contract surface)."""

from __future__ import annotations

import json
import sys
from typing import Any


class Writer:
    def __init__(self, fmt: str = "plain", color: bool = False, limit: int = 50,
                 select: list[str] | None = None, stdout=None, stderr=None):
        self.fmt = fmt
        self.color = color
        self.limit = limit
        self.select = select or []
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr

    def info(self, msg: str) -> None:
        print(msg, file=self.stderr)

    def emit(self, value: Any) -> None:
        g = json.loads(json.dumps(value, default=str))
        if self.select:
            g = _apply_select(g, self.select)
        g = self._apply_limit(g)
        if self.fmt == "json":
            self.emit_json(g)
        elif self.fmt == "tsv":
            self._render(g, "\t", aligned=False)
        else:
            self._render(g, "\t", aligned=True)

    def emit_json(self, value: Any) -> None:
        print(json.dumps(value, indent=2, ensure_ascii=False), file=self.stdout)

    def _apply_limit(self, g: Any) -> Any:
        if self.limit > 0 and isinstance(g, list) and len(g) > self.limit:
            self.info(f"note: output truncated to {self.limit} of {len(g)} items "
                      f"(use --limit to change)")
            return g[: self.limit]
        return g

    def _render(self, g: Any, sep: str, aligned: bool) -> None:
        if isinstance(g, list):
            if not g:
                return
            if isinstance(g[0], dict):
                headers = _union_keys(g)
                rows = [[_scalar(row.get(h)) for h in headers] for row in g]
                self._write_table([headers] + rows, sep, aligned)
            else:
                for e in g:
                    print(_scalar(e), file=self.stdout)
        elif isinstance(g, dict):
            rows = [[k, _scalar(g[k])] for k in sorted(g)]
            self._write_table(rows, sep, aligned)
        else:
            print(_scalar(g), file=self.stdout)

    def _write_table(self, rows: list[list[str]], sep: str, aligned: bool) -> None:
        if aligned and rows:
            widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
            for r in rows:
                print("  ".join(c.ljust(widths[i]) for i, c in enumerate(r)).rstrip(),
                      file=self.stdout)
        else:
            for r in rows:
                print(sep.join(r), file=self.stdout)


def _apply_select(g: Any, sel: list[str]) -> Any:
    if isinstance(g, list):
        return [_select_obj(e, sel) for e in g]
    return _select_obj(g, sel)


def _select_obj(e: Any, sel: list[str]) -> Any:
    if not isinstance(e, dict):
        return e
    out: dict[str, Any] = {}
    for p in sel:
        p = p.strip()
        if not p:
            continue
        ok, v = _get_path(e, p)
        if ok:
            out[p] = v
    return out


def _get_path(m: dict, path: str):
    cur: Any = m
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def _union_keys(arr: list[dict]) -> list[str]:
    keys: set[str] = set()
    for e in arr:
        if isinstance(e, dict):
            keys.update(e.keys())
    return sorted(keys)


def _scalar(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (str, int, float)):
        return str(v)
    return json.dumps(v, ensure_ascii=False)
