from __future__ import annotations

from typing import Any

import pytest

from sqlitch.engine import base


class _DummyEngine(base.Engine):
    def __init__(self, target: base.EngineTarget, **kwargs: Any) -> None:
        super().__init__(target, **kwargs)
        self.registry_args: list[base.ConnectArguments] = []
        self.workspace_args: list[base.ConnectArguments] = []

    def build_registry_connect_arguments(self) -> base.ConnectArguments:
        args = base.ConnectArguments(args=("registry",), kwargs={"sslmode": "require"})
        self.registry_args.append(args)
        return args

    def build_workspace_connect_arguments(self) -> base.ConnectArguments:
        args = base.ConnectArguments(args=("workspace",), kwargs={})
        self.workspace_args.append(args)
        return args


def test_canonicalize_engine_name_supports_aliases() -> None:
    assert base.canonicalize_engine_name("PostgreSQL") == "pg"
    assert base.canonicalize_engine_name("sqlite3") == "sqlite"
    assert base.canonicalize_engine_name("MySQL") == "mysql"


def test_canonicalize_engine_name_rejects_unknown_engine() -> None:
    with pytest.raises(base.UnsupportedEngineError):
        base.canonicalize_engine_name("oracle")


def test_engine_target_normalises_engine_and_variables() -> None:
    target = base.EngineTarget(
        name="db:main",
        engine="Postgres",
        uri="db:pg://localhost/app",
        variables={"PGHOST": "localhost"},
    )

    assert target.engine == "pg"
    assert target.registry_uri == "db:pg://localhost/app"
    assert target.variables["PGHOST"] == "localhost"
    with pytest.raises(TypeError):
        target.variables["PGHOST"] = "other"  # type: ignore[misc]


def test_engine_target_requires_known_engine() -> None:
    with pytest.raises(base.UnsupportedEngineError):
        base.EngineTarget(name="db:oracle", engine="oracle", uri="db:oracle://example")


def test_connection_factory_imports_driver_and_invokes_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = base.connection_factory_for_engine("sqlite")
    args = base.ConnectArguments(args=(":memory:",), kwargs={"timeout": 10})

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    class FakeModule:
        def connect(self, *connect_args: Any, **connect_kwargs: Any) -> str:
            calls.append((connect_args, connect_kwargs))
            return "connection"

    monkeypatch.setattr(base, "_import_module", lambda module_name: FakeModule())

    connection = factory.connect(args)

    assert connection == "connection"
    assert calls == [((":memory:",), {"timeout": 10})]


def test_connection_factory_rejects_unknown_engine() -> None:
    with pytest.raises(base.UnsupportedEngineError):
        base.connection_factory_for_engine("oracle")


def test_engine_connect_methods_use_connection_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    target = base.EngineTarget(name="db:test", engine="sqlite", uri="db:sqlite:app")

    previous = base.register_engine("sqlite", _DummyEngine, replace=True)

    class FakeModule:
        def __init__(self) -> None:
            self.calls = 0

        def connect(self, *args: Any, **kwargs: Any) -> str:
            self.calls += 1
            return f"connection-{self.calls}"

    fake_module = FakeModule()
    monkeypatch.setattr(base, "_import_module", lambda module_name: fake_module)

    try:
        engine = base.create_engine(target)
        assert isinstance(engine, _DummyEngine)

        registry_conn = engine.connect_registry()
        workspace_conn = engine.connect_workspace()

        assert registry_conn == "connection-1"
        assert workspace_conn == "connection-2"
        assert engine.registry_args[-1].args == ("registry",)
        assert engine.workspace_args[-1].args == ("workspace",)
    finally:
        if previous is not None:
            base.register_engine("sqlite", previous, replace=True)
        else:
            base.unregister_engine("sqlite")


def test_create_engine_rejects_unregistered_engine() -> None:
    target = base.EngineTarget(name="db:test", engine="sqlite", uri="db:sqlite:app")

    previous = base.unregister_engine("sqlite")
    try:
        with pytest.raises(base.UnsupportedEngineError):
            base.create_engine(target)
    finally:
        if previous is not None:
            base.register_engine("sqlite", previous, replace=True)


def test_registered_engines_reports_registered_engines() -> None:
    target = base.EngineTarget(name="db:dummy", engine="sqlite", uri="db:sqlite:dummy")

    previous = base.register_engine("sqlite", _DummyEngine, replace=True)
    try:
        available = base.registered_engines()
        assert "sqlite" in available
        assert isinstance(base.create_engine(target), _DummyEngine)
    finally:
        if previous is not None:
            base.register_engine("sqlite", previous, replace=True)
        else:
            base.unregister_engine("sqlite")
