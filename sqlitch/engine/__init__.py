"""Engine adapters and factories for SQLitch."""

from .base import (
    Engine,
    EngineError,
    EngineTarget,
    UnsupportedEngineError,
    canonicalize_engine_name,
    connection_factory_for_engine,
    create_engine,
    register_engine,
    unregister_engine,
    registered_engines,
)
from .sqlite import SQLiteEngine, SQLiteEngineError

__all__ = [
    "Engine",
    "EngineError",
    "EngineTarget",
    "UnsupportedEngineError",
    "canonicalize_engine_name",
    "connection_factory_for_engine",
    "create_engine",
    "register_engine",
    "unregister_engine",
    "registered_engines",
    "SQLiteEngine",
    "SQLiteEngineError",
]
