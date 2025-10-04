"""Unit coverage for helper utilities in ``sqlitch.cli.commands.config``."""

from __future__ import annotations

import click
import pytest

from sqlitch.cli.commands import CommandError
from sqlitch.cli.commands import config as config_module
from sqlitch.config.loader import ConfigScope


def test_resolve_scope_defaults_to_local() -> None:
    scope, explicit = config_module._resolve_scope(False, False, False, False)

    assert scope == ConfigScope.LOCAL
    assert explicit is False


def test_resolve_scope_user_selected() -> None:
    scope, explicit = config_module._resolve_scope(True, False, False, False)

    assert scope == ConfigScope.USER
    assert explicit is True


def test_resolve_scope_conflicting_flags() -> None:
    with pytest.raises(CommandError, match="Only one scope option may be specified"):
        config_module._resolve_scope(True, False, True, False)


def test_normalize_bool_value_converts_truthy() -> None:
    assert config_module._normalize_bool_value("YES") == "true"
    assert config_module._normalize_bool_value("0") == "false"


def test_normalize_bool_value_rejects_invalid() -> None:
    with pytest.raises(CommandError, match="Invalid boolean value"):
        config_module._normalize_bool_value("maybe")


def test_flatten_settings_handles_default_section() -> None:
    settings = {
        "DEFAULT": {"color": "blue"},
        "core": {"engine": "sqlite"},
    }

    flattened = config_module._flatten_settings(settings)

    assert flattened == {"color": "blue", "core.engine": "sqlite"}


def test_set_config_value_updates_existing_entry() -> None:
    lines = ["[core]", "\tengine = sqlite"]

    updated = config_module._set_config_value(lines, "core", "engine", "postgres")

    assert updated[1] == "\tengine = postgres"


def test_set_config_value_appends_when_missing() -> None:
    lines: list[str] = []

    updated = config_module._set_config_value(lines, "core", "engine", "sqlite")

    assert updated == ["[core]", "\tengine = sqlite"]


def test_remove_config_value_deletes_section_when_empty() -> None:
    lines = ["[core]", "\tengine = sqlite"]

    updated, removed = config_module._remove_config_value(lines, "core", "engine")

    assert removed is True
    assert updated == []


def test_build_emitter_suppresses_output_when_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []

    monkeypatch.setattr(click, "echo", lambda message: captured.append(message))

    loud_emitter = config_module._build_emitter(False)
    quiet_emitter = config_module._build_emitter(True)

    loud_emitter("one")
    quiet_emitter("two")

    assert captured == ["one"]
