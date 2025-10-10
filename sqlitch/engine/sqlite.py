"""SQLite engine adapter implementation."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, unquote, urlsplit, urlunsplit

from .base import (
    ConnectArguments,
    Engine,
    EngineError,
    EngineTarget,
    canonicalize_engine_name,
    register_engine,
)

SQLITE_SCHEME_PREFIX = "db:sqlite:"
DEFAULT_DETECT_TYPES = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
REGISTRY_ATTACHMENT_ALIAS = "sqitch"
REGISTRY_FILENAME = "sqitch.db"


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

        if self._registry_is_uri:
            if self._registry_path.startswith("file:"):
                split = _split_file_uri(self._registry_path)
                path = _filesystem_path_from_split(split)
                return path
            raise SQLiteEngineError("SQLite registry attachments only support file: URIs.")
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


def derive_sqlite_registry_uri(
    *,
    workspace_uri: str,
    project_root: Path,
    registry_override: str | None = None,
) -> str:
    """Return the canonical registry URI used for SQLite deployments.

    The registry database must live adjacent to the workspace database (mirroring Sqitch)
    unless an explicit override has been provided. Relative filesystem paths are resolved
    against ``project_root`` to maintain deterministic behaviour for CLI commands executed
    from inside a project directory.
    """

    if registry_override:
        return _normalize_registry_override(registry_override, project_root)

    payload = _extract_payload(workspace_uri)

    if payload in {"", ":memory:"}:
        registry_path = (project_root / REGISTRY_FILENAME).resolve()
        return f"{SQLITE_SCHEME_PREFIX}{registry_path.as_posix()}"

    if payload.startswith("file:"):
        split = _split_file_uri(payload)
        path = _filesystem_path_from_split(split)
        if not path.is_absolute():
            path = (project_root / path).resolve()
        registry_path = path.with_name(REGISTRY_FILENAME)
        registry_split = split._replace(path=registry_path.as_posix())
        uri = urlunsplit(registry_split)
        return f"{SQLITE_SCHEME_PREFIX}{uri}"

    path = Path(payload)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    registry_path = path.with_name(REGISTRY_FILENAME)
    return f"{SQLITE_SCHEME_PREFIX}{registry_path.as_posix()}"


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


def _split_file_uri(uri: str) -> SplitResult:
    split = urlsplit(uri, scheme="file")
    if split.scheme != "file":  # pragma: no cover - defensive
        raise SQLiteEngineError(f"unexpected file URI scheme: {uri!r}")
    if split.netloc and split.netloc not in {"", "localhost"}:  # pragma: no cover - parity guard
        raise SQLiteEngineError("SQLite registry attachments do not support remote file hosts")
    return split


def _filesystem_path_from_split(split: SplitResult) -> Path:
    path = unquote(split.path)
    if split.netloc and split.netloc not in {"", "localhost"}:
        path = f"/{split.netloc}{path}"
    if not path:
        path = REGISTRY_FILENAME
    return Path(path)


def _extract_payload(uri: str) -> str:
    if uri.startswith("db:"):
        remainder = uri[3:]
        engine_token, separator, payload = remainder.partition(":")
        if not separator:
            raise SQLiteEngineError(f"unexpected sqlite URI format: {uri!r}")
        canonical = canonicalize_engine_name(engine_token or "sqlite")
        if canonical != "sqlite":
            raise SQLiteEngineError(
                f"SQLite registry derivation requires sqlite targets, received {canonical!r}."
            )
        return payload
    return uri


def _normalize_registry_override(override: str, project_root: Path) -> str:
    value = override.strip()
    if not value:
        raise SQLiteEngineError("Registry override cannot be empty.")

    if value.startswith("db:"):
        return value

    if value.startswith("file:"):
        return f"{SQLITE_SCHEME_PREFIX}{value}"

    path = Path(value)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return f"{SQLITE_SCHEME_PREFIX}{path.as_posix()}"


def resolve_sqlite_filesystem_path(sqlite_uri: str) -> Path:
    """Return the filesystem path pointed to by ``sqlite_uri``.

    The helper understands SQLitch ``db:sqlite:`` URIs and the subset of ``file:``
    URIs that SQLite accepts. The returned path is suitable for directory creation
    prior to opening database connections.
    """

    database, is_uri = _parse_sqlite_uri(sqlite_uri)
    if not is_uri:
        return Path(database)

    if not database.startswith("file:"):
        raise SQLiteEngineError(
            f"SQLite filesystem resolution only supports file: URIs, received {database!r}."
        )

    split = _split_file_uri(database)
    return _filesystem_path_from_split(split)


register_engine("sqlite", SQLiteEngine, replace=True)

__all__ = [
    "SQLiteEngine",
    "SQLiteEngineError",
    "REGISTRY_ATTACHMENT_ALIAS",
    "REGISTRY_FILENAME",
    "derive_sqlite_registry_uri",
    "extract_sqlite_statements",
    "script_manages_transactions",
    "resolve_sqlite_filesystem_path",
]


_TRANSACTION_KEYWORDS: tuple[str, ...] = (
    "BEGIN",
    "END",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT",
    "RELEASE",
)


def extract_sqlite_statements(script_sql: str) -> tuple[str, ...]:
    """Return SQL statements contained within ``script_sql``.

    The helper mirrors the behaviour of ``sqlite3.complete_statement`` so callers can
    reuse the parsed statements for execution or analysis. Empty statements and
    whitespace-only chunks are discarded.
    """
    statements: list[str] = []
    buffer: list[str] = []

    def flush_buffer() -> None:
        nonlocal buffer
        statement = "".join(buffer).strip()
        if statement:
            statements.append(statement)
        buffer = []

    for char in script_sql:
        buffer.append(char)
        if sqlite3.complete_statement("".join(buffer)):
            flush_buffer()

    remainder = "".join(buffer).strip()
    if remainder:
        statements.append(remainder)

    return tuple(statements)


def script_manages_transactions(script_sql: str) -> bool:
    """Return ``True`` when ``script_sql`` contains explicit transaction control."""

    for statement in extract_sqlite_statements(script_sql):
        keyword = _leading_keyword(statement)
        if keyword in _TRANSACTION_KEYWORDS:
            return True
    return False


def _leading_keyword(statement: str) -> str:
    tokens = _tokenize_statement(statement)
    return tokens[0] if tokens else ""


def _tokenize_statement(statement: str) -> list[str]:
    normalized = statement.strip()
    if not normalized:
        return []
    pieces: list[str] = []
    token = []
    in_string = False
    string_quote: str | None = None
    for char in normalized:
        if in_string:
            token.append(char)
            if char == string_quote:
                in_string = False
                string_quote = None
            elif char == "\\":  # pragma: no cover - string escape handling
                continue
            continue

        if char in {'"', "'"}:
            in_string = True
            string_quote = char
            token.append(char)
            continue

        if char.isspace() or char in {",", "(", ")", ";"}:
            if token:
                pieces.append("".join(token).upper())
                token.clear()
            continue

        token.append(char)

    if token:
        pieces.append("".join(token).upper())

    return pieces
