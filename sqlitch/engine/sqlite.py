"""SQLite engine adapter implementation."""

from __future__ import annotations

from collections.abc import Mapping
import sqlite3
from pathlib import Path
from typing import Any

from .base import ConnectArguments, Engine, EngineError, EngineTarget, register_engine

SQLITE_SCHEME_PREFIX = "db:sqlite:"
DEFAULT_DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
REGISTRY_ATTACHMENT_ALIAS = "sqitch"


class SQLiteEngineError(EngineError):
    """Raised when a SQLite engine target cannot be interpreted."""


class SQLiteEngine(Engine):
    """Engine adapter for sqlite3 targets."""

    def __init__(
        self, target: EngineTarget, *, connect_kwargs: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__(target)
        self._connect_kwargs = dict(connect_kwargs or {})
        self._workspace_path, self._workspace_is_uri = _parse_sqlite_uri(target.uri)
        registry_uri = target.registry_uri or target.uri
        self._registry_path, self._registry_is_uri = _parse_sqlite_uri(registry_uri)

    def build_registry_connect_arguments(self) -> ConnectArguments:
        """Return connection arguments pointing to the registry database."""
        return self._build_connect_arguments(self.target.registry_uri)

    def build_workspace_connect_arguments(self) -> ConnectArguments:
        """Return connection arguments pointing to the workspace database."""
        return self._build_connect_arguments(self.target.uri)

    def connect_workspace(self) -> sqlite3.Connection:
        connection = super().connect_workspace()
        self._attach_registry(connection)
        return connection

    def registry_filesystem_path(self) -> Path:
        """Return the filesystem path backing the attached registry database."""

        if self._registry_is_uri and self._registry_path.startswith("file:"):
            return Path(self._registry_path[5:])
        return Path(self._registry_path)

    def _build_connect_arguments(self, uri: str) -> ConnectArguments:
        database, is_uri = _parse_sqlite_uri(uri)
        kwargs: dict[str, Any] = dict(self._connect_kwargs)
        kwargs.setdefault("detect_types", DEFAULT_DETECT_TYPES)
        kwargs["uri"] = is_uri
        return ConnectArguments(args=(database,), kwargs=kwargs)

    def _attach_registry(self, connection: sqlite3.Connection) -> None:
        registry_argument = self._registry_path
        # When the registry path is a filesystem location, normalise to POSIX.
        if not self._registry_is_uri:
            registry_argument = Path(registry_argument).as_posix()

        cursor = connection.cursor()
        try:
            cursor.execute(
                f"ATTACH DATABASE ? AS {REGISTRY_ATTACHMENT_ALIAS}", (registry_argument,)
            )
        finally:
            cursor.close()


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

__all__ = ["SQLiteEngine", "SQLiteEngineError", "REGISTRY_ATTACHMENT_ALIAS"]
