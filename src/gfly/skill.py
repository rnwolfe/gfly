"""Loads the bundled SKILL.md (packaged data) for the `agent` subcommand. contract.md §5."""

from __future__ import annotations

from importlib import resources


def content() -> str:
    return resources.files("gfly").joinpath("SKILL.md").read_text(encoding="utf-8")
