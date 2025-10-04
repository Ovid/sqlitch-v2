"""SQLite engine adapter implementation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import sqlite3

from .base import ConnectArguments, Engine, EngineError, EngineTarget, register_engine

SQLITE_SCHEME_PREFIX = "db:sqlite:"
DEFAULT_DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES


class SQLiteEngineError(EngineError):
    """Raised when a SQLite engine target cannot be interpreted."""


class SQLiteEngine(Engine):
    """Engine adapter for sqlite3 targets."""

    def __init__(
        self, target: EngineTarget, *, connect_kwargs: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__(target)
        self._connect_kwargs = dict(connect_kwargs or {})

    def build_registry_connect_arguments(self) -> ConnectArguments:
        """Return connection arguments pointing to the registry database."""
        return self._build_connect_arguments(self.target.registry_uri)

    def build_workspace_connect_arguments(self) -> ConnectArguments:
        """Return connection arguments pointing to the workspace database."""
        return self._build_connect_arguments(self.target.uri)

    def _build_connect_arguments(self, uri: str) -> ConnectArguments:
        database, is_uri = _parse_sqlite_uri(uri)
        kwargs: dict[str, Any] = dict(self._connect_kwargs)
        kwargs.setdefault("detect_types", DEFAULT_DETECT_TYPES)
        kwargs["uri"] = is_uri
        return ConnectArguments(args=(database,), kwargs=kwargs)


def _parse_sqlite_uri(uri: str) -> tuple[str, bool]:
    """Return (database, is_uri) parsed from a SQLitch-style SQLite URI."""
    if not uri.startswith(SQLITE_SCHEME_PREFIX):
        raise SQLiteEngineError(f"unexpected sqlite URI format: {uri!r}")

    payload = uri[len(SQLITE_SCHEME_PREFIX) :].strip()
    if not payload:
        return ":memory:", False

    if payload == ":memory:":
        return ":memory:", False

    if payload.startswith("file:"):
        return payload, True

    return payload, False


register_engine("sqlite", SQLiteEngine, replace=True)

__all__ = ["SQLiteEngine", "SQLiteEngineError"]
