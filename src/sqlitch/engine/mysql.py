"""Stub MySQL engine adapter retained for Sqitch parity messaging."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .base import ConnectArguments, Engine, EngineTarget, register_engine

__all__ = ["MySQLEngine", "MYSQL_STUB_MESSAGE"]

MYSQL_STUB_MESSAGE = (
    "MySQL engine support is not yet implemented. This placeholder matches Sqitch parity."
)


class MySQLEngine(Engine):
    """Stub engine that advertises MySQL support but raises for all operations."""

    def __init__(
        self,
        target: EngineTarget,
        *,
        connect_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(target)
        self._connect_kwargs = dict(connect_kwargs or {})

    def build_registry_connect_arguments(self) -> ConnectArguments:  # pragma: no cover - stub
        raise NotImplementedError(MYSQL_STUB_MESSAGE)

    def build_workspace_connect_arguments(self) -> ConnectArguments:  # pragma: no cover - stub
        raise NotImplementedError(MYSQL_STUB_MESSAGE)

    def connect_registry(self) -> Any:  # pragma: no cover - stub
        raise NotImplementedError(MYSQL_STUB_MESSAGE)

    def connect_workspace(self) -> Any:  # pragma: no cover - stub
        raise NotImplementedError(MYSQL_STUB_MESSAGE)


register_engine("mysql", MySQLEngine, replace=True)
