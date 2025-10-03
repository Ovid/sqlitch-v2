"""Top-level package for SQLitch."""

from importlib.metadata import version, PackageNotFoundError

try:  # pragma: no cover - handled by ensuring package metadata is present
    __version__ = version("sqlitch")
except PackageNotFoundError:  # pragma: no cover - fallback for local editable installs
    __version__ = "0.1.0"

__all__ = ["__version__"]
