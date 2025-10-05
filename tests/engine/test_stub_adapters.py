"""Expectations for stubbed MySQL and PostgreSQL engine adapters."""

from __future__ import annotations

import importlib
from contextlib import ExitStack

import pytest

from sqlitch.engine import ENGINE_REGISTRY, EngineTarget, unregister_engine


@pytest.mark.parametrize(
    "module_name",
    (
        "sqlitch.engine.mysql",
        "sqlitch.engine.postgres",
    ),
)
def test_stub_adapter_registers_and_raises_not_implemented(module_name: str) -> None:
    previous = {}
    with ExitStack() as stack:
        for key in ("mysql", "pg"):
            if key in ENGINE_REGISTRY:
                previous[key] = ENGINE_REGISTRY[key]
                stack.callback(unregister_engine, key)

        module = importlib.import_module(module_name)
        assert module is not None  # pragma: no cover - sanity guard once stubs exist

        if module_name.endswith("mysql"):
            engine_key = "mysql"
            uri = "db:mysql://example"
        else:
            engine_key = "pg"
            uri = "db:pg://example"

        engine_cls = ENGINE_REGISTRY[engine_key]
        target = EngineTarget(name="stub", engine=engine_key, uri=uri)
        engine = engine_cls(target)

        with pytest.raises(NotImplementedError):
            engine.connect_registry()

    for key, engine_cls in previous.items():
        ENGINE_REGISTRY[key] = engine_cls
