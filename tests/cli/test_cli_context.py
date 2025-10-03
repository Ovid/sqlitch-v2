"""Tests for CLI context assembly and global option handling."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Iterator

import click
from click.testing import CliRunner
import pytest

from sqlitch.cli import CLIContext
from sqlitch.cli.commands import CommandError

cli_main = importlib.import_module("sqlitch.cli.main")


@pytest.fixture
def restore_main_commands() -> Iterator[None]:
    original_commands = dict(cli_main.main.commands)
    try:
        yield
    finally:
        cli_main.main.commands = original_commands


def test_build_cli_context_uses_resolver(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sentinel_root = tmp_path / "config"
    monkeypatch.setattr(
        cli_main.config_resolver,
        "determine_config_root",
        lambda env: sentinel_root,
    )

    ctx = cli_main._build_cli_context(
        config_root=None,
        engine="sqlite",
        target="prod",
        registry="registry",
        plan_file=tmp_path / "plan.sqlitch",
        verbosity=2,
        quiet=False,
        env={"EXAMPLE": "1"},
    )

    assert ctx.config_root == sentinel_root
    assert ctx.engine == "sqlite"
    assert ctx.target == "prod"
    assert ctx.registry == "registry"
    assert ctx.plan_file == (tmp_path / "plan.sqlitch").resolve()
    assert ctx.verbosity == 2
    assert ctx.quiet is False
    assert ctx.env["EXAMPLE"] == "1"
    assert ctx.project_root == Path.cwd()


def test_build_cli_context_respects_explicit_config_root(tmp_path: Path) -> None:
    config_root = tmp_path / "explicit"
    ctx = cli_main._build_cli_context(
        config_root=config_root,
        engine=None,
        target=None,
        registry=None,
        plan_file=None,
        verbosity=0,
        quiet=False,
    )

    assert ctx.config_root == config_root


def test_build_cli_context_rejects_quiet_with_verbose() -> None:
    with pytest.raises(CommandError):
        cli_main._build_cli_context(
            config_root=None,
            engine=None,
            target=None,
            registry=None,
            plan_file=None,
            verbosity=1,
            quiet=True,
        )


def test_main_populates_context_for_commands(restore_main_commands, tmp_path: Path) -> None:
    runner = CliRunner()
    captured: dict[str, CLIContext] = {}

    @click.command("inspect")
    @click.pass_context
    def inspect(ctx: click.Context) -> None:
        captured["ctx"] = ctx.obj
        click.echo("ok")

    cli_main.main.add_command(inspect)

    result = runner.invoke(
        cli_main.main,
        ["--config-root", str(tmp_path), "--engine", "sqlite", "inspect"],
    )

    assert result.exit_code == 0
    context = captured["ctx"]
    assert context.engine == "sqlite"
    assert context.config_root == tmp_path
    assert context.quiet is False


def test_main_rejects_conflicting_quiet_and_verbose(restore_main_commands) -> None:
    runner = CliRunner()

    @click.command("noop")
    def noop() -> None:
        raise AssertionError("noop should not run")

    cli_main.main.add_command(noop)

    result = runner.invoke(cli_main.main, ["--quiet", "-v", "noop"])

    assert result.exit_code != 0
    assert "--quiet cannot be combined" in result.output
