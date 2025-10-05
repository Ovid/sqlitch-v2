"""Tests for the CLI command registry helpers."""

from __future__ import annotations

import types
import sys
from typing import Iterator

import click
import pytest

from sqlitch.cli.commands import (
    CommandError,
    CommandRegistrationError,
    add_command,
    iter_command_registrars,
    load_commands,
    register_command,
    _clear_registry,  # type: ignore[attr-defined]
)


@pytest.fixture(autouse=True)
def clear_command_registry() -> Iterator[None]:
    _clear_registry()
    from sqlitch.cli import commands as command_module

    original_modules = command_module.COMMAND_MODULES
    yield
    _clear_registry()
    # Restore the default command module list after each test.
    command_module.COMMAND_MODULES = original_modules
    sys.modules.pop("sqlitch.cli.commands._test_dummy", None)


def test_register_command_decorator_registers_callable() -> None:
    @register_command()
    def sample(group: click.Group) -> None:  # pragma: no cover - used via registry
        group.help = "updated"

    registrars = tuple(iter_command_registrars())

    assert registrars == (sample,)

    group = click.Group(name="sqlitch")
    registrars[0](group)
    assert group.help == "updated"


def test_register_command_prevents_duplicate_names() -> None:
    @register_command("example")
    def first(_: click.Group) -> None:  # pragma: no cover - registry only
        pass

    with pytest.raises(CommandRegistrationError):

        @register_command("example")
        def _(_: click.Group) -> None:  # pragma: no cover - registry only
            pass


def test_add_command_disallows_duplicate_registration() -> None:
    def registrar(_: click.Group) -> None:  # pragma: no cover - registry only
        pass

    add_command("custom", registrar)

    with pytest.raises(CommandRegistrationError):
        add_command("custom", registrar)


def test_command_error_defaults_to_exit_code_one() -> None:
    error = CommandError("boom")

    assert isinstance(error, click.ClickException)
    assert error.exit_code == 1
    assert "boom" in str(error)


def test_command_error_respects_custom_exit_code() -> None:
    error = CommandError("boom", exit_code=5)

    assert isinstance(error, click.ClickException)
    assert error.exit_code == 5
    assert "boom" in str(error)


def test_load_commands_imports_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    imported: list[str] = []

    def fake_import(name: str) -> types.ModuleType:
        imported.append(name)
        if name == "sqlitch.cli.commands._test_dummy":
            module = types.ModuleType(name)

            @register_command("_dummy")
            def _attach(_: click.Group) -> None:  # pragma: no cover - registry only
                pass

            sys.modules[name] = module
            return module
        raise ImportError(name)

    monkeypatch.setattr("sqlitch.cli.commands.importlib.import_module", fake_import)
    monkeypatch.setattr("sqlitch.cli.commands.COMMAND_MODULES", ("_test_dummy",))

    load_commands()

    registrars = tuple(iter_command_registrars())
    assert len(registrars) == 1
    assert imported == ["sqlitch.cli.commands._test_dummy"]
