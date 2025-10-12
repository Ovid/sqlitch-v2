"""Top-level package for SQLitch."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:  # pragma: no cover - handled by ensuring package metadata is present
    __version__ = version("sqlitch")
except PackageNotFoundError:  # pragma: no cover - fallback for local editable installs
    __version__ = "1.0.0"

__all__ = ["__version__"]
