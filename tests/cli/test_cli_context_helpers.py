"""Additional unit tests for CLI context helper utilities."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import click
import pytest

from sqlitch.cli.commands import CommandError
from sqlitch.cli.commands import _context as context_module


@pytest.fixture()
def dummy_cli_context(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        project_root=tmp_path,
        config_root=tmp_path / "config",
        config_root_overridden=False,
        env={"EXAMPLE": "1"},
        log_config=SimpleNamespace(level="INFO"),
        quiet=False,
        engine=None,
        target=None,
        registry=None,
        verbosity=0,
        json_mode=False,
        plan_file=None,
    )


def test_require_cli_context_prefers_object(dummy_cli_context: SimpleNamespace) -> None:
    ctx = click.Context(click.Command("sample"))
    ctx.obj = dummy_cli_context

    resolved = context_module.require_cli_context(ctx)

    assert resolved is dummy_cli_context


def test_require_cli_context_falls_back_to_meta(dummy_cli_context: SimpleNamespace) -> None:
    parent = click.Context(click.Command("parent"))
    parent.obj = None
    parent.meta[context_module._CLI_CONTEXT_META_KEY] = dummy_cli_context

    child = click.Context(click.Command("child"), parent=parent)
    child.obj = None

    resolved = context_module.require_cli_context(child)

    assert resolved is dummy_cli_context


def test_require_cli_context_missing_raises() -> None:
    ctx = click.Context(click.Command("empty"))

    with pytest.raises(CommandError, match="CLI context is not initialised"):
        context_module.require_cli_context(ctx)


def test_context_from_obj_rejects_incomplete_namespace(tmp_path: Path) -> None:
    incomplete = SimpleNamespace(project_root=tmp_path)

    assert context_module._context_from_obj(incomplete) is None


def test_is_cli_context_like_requires_all_attributes(dummy_cli_context: SimpleNamespace) -> None:
    assert context_module._is_cli_context_like(dummy_cli_context)

    missing_attr = SimpleNamespace(
        **{
            key: getattr(dummy_cli_context, key)
            for key in ("project_root", "config_root", "env", "quiet")
        }
    )

    assert context_module._is_cli_context_like(missing_attr) is False


def test_attribute_helpers_proxy_requirements(dummy_cli_context: SimpleNamespace) -> None:
    ctx = click.Context(click.Command("helpers"))
    ctx.obj = dummy_cli_context

    assert context_module.project_root_from(ctx) == dummy_cli_context.project_root
    assert context_module.environment_from(ctx) is dummy_cli_context.env
    assert context_module.plan_override_from(ctx) is None
    assert context_module.config_root_from(ctx) == dummy_cli_context.config_root
    assert context_module.quiet_mode_enabled(ctx) is False
