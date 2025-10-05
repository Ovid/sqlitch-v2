"""Helpers for plan-related naming conventions."""

from __future__ import annotations

__all__ = ["slugify_change_name"]


def slugify_change_name(name: str) -> str:
    """Return a filesystem-friendly slug for a change name."""

    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)
