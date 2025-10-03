from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

from sqlitch.engine import base


def _make_target(uri: str) -> base.EngineTarget:
    return base.EngineTarget(name="db:test", engine="sqlite", uri=uri)


def test_sqlite_engine_registers_itself() -> None:
    module_name = "sqlitch.engine.sqlite"
    previous = base.unregister_engine("sqlite")
    sys.modules.pop(module_name, None)

    module = importlib.import_module(module_name)
    try:
        engine = base.create_engine(_make_target("db:sqlite:memory"))
        assert isinstance(engine, module.SQLiteEngine)
    finally:
        base.unregister_engine("sqlite")
        if previous is not None:
            base.register_engine("sqlite", previous, replace=True)
        else:
            base.register_engine("sqlite", module.SQLiteEngine, replace=True)


def test_sqlite_engine_builds_connect_arguments_with_paths(tmp_path: Path) -> None:
    import sqlitch.engine.sqlite as sqlite_engine

    target = _make_target(f"db:sqlite:{tmp_path / 'workspace.db'}")
    object.__setattr__(target, "registry_uri", f"db:sqlite:{tmp_path / 'registry.db'}")

    engine = sqlite_engine.SQLiteEngine(target, connect_kwargs={"timeout": 2.5})

    registry_args = engine.build_registry_connect_arguments()
    workspace_args = engine.build_workspace_connect_arguments()

    assert registry_args.args == (str(tmp_path / "registry.db"),)
    assert workspace_args.args == (str(tmp_path / "workspace.db"),)

    expected_detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    assert registry_args.kwargs["detect_types"] == expected_detect_types
    assert workspace_args.kwargs["detect_types"] == expected_detect_types
    assert registry_args.kwargs["timeout"] == pytest.approx(2.5)
    assert workspace_args.kwargs["timeout"] == pytest.approx(2.5)
    assert registry_args.kwargs["uri"] is False
    assert workspace_args.kwargs["uri"] is False


def test_sqlite_engine_supports_uri_queries() -> None:
    import sqlitch.engine.sqlite as sqlite_engine

    target = _make_target("db:sqlite:file:workspace.db?mode=ro&cache=shared")
    engine = sqlite_engine.SQLiteEngine(target)

    args = engine.build_workspace_connect_arguments()
    assert args.args == ("file:workspace.db?mode=ro&cache=shared",)
    assert args.kwargs["uri"] is True


def test_sqlite_engine_defaults_to_memory_when_no_path() -> None:
    import sqlitch.engine.sqlite as sqlite_engine

    engine = sqlite_engine.SQLiteEngine(_make_target("db:sqlite:"))

    workspace_args = engine.build_workspace_connect_arguments()
    assert workspace_args.args == (":memory:",)
    assert workspace_args.kwargs["uri"] is False


def test_sqlite_engine_accepts_explicit_memory_identifier() -> None:
    import sqlitch.engine.sqlite as sqlite_engine

    engine = sqlite_engine.SQLiteEngine(_make_target("db:sqlite::memory:"))

    workspace_args = engine.build_workspace_connect_arguments()
    assert workspace_args.args == (":memory:",)
    assert workspace_args.kwargs["uri"] is False


def test_parse_sqlite_uri_rejects_invalid_scheme() -> None:
    from sqlitch.engine.sqlite import SQLiteEngineError, _parse_sqlite_uri

    with pytest.raises(SQLiteEngineError):
        _parse_sqlite_uri("sqlite::memory:")