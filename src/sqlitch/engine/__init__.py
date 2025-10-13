"""Engine adapters and factories for SQLitch."""

from __future__ import annotations

from .base import (
    ENGINE_REGISTRY,
    Engine,
    EngineError,
    EngineTarget,
    UnsupportedEngineError,
    canonicalize_engine_name,
    connection_factory_for_engine,
    create_engine,
    register_engine,
    registered_engines,
    unregister_engine,
)
from .mysql import MYSQL_STUB_MESSAGE, MySQLEngine
from .postgres import POSTGRES_STUB_MESSAGE, PostgresEngine
from .sqlite import SQLiteEngine, SQLiteEngineError

__all__ = [
    "Engine",
    "EngineError",
    "EngineTarget",
    "ENGINE_REGISTRY",
    "UnsupportedEngineError",
    "canonicalize_engine_name",
    "connection_factory_for_engine",
    "create_engine",
    "register_engine",
    "unregister_engine",
    "registered_engines",
    "MySQLEngine",
    "MYSQL_STUB_MESSAGE",
    "PostgresEngine",
    "POSTGRES_STUB_MESSAGE",
    "SQLiteEngine",
    "SQLiteEngineError",
]
