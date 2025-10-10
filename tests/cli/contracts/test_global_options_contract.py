"""Contract tests covering SQLitch global verbosity and output options."""

from __future__ import annotations

import importlib
from typing import Iterator
from uuid import UUID

import click
import pytest
from click.testing import CliRunner

cli_main = importlib.import_module("sqlitch.cli.main")


@pytest.fixture(autouse=True)
def restore_main_commands() -> Iterator[None]:
    """Reset registered commands on the CLI group after each test."""

    original_commands = dict(cli_main.main.commands)
    try:
        yield
    finally:
        cli_main.main.commands = original_commands


def _invoke_with_capture(args: list[str], *, env: dict[str, str] | None = None):
    runner = CliRunner()
    captured: dict[str, object] = {}

    @click.command("introspect")
    @click.pass_context
    def introspect(ctx: click.Context) -> None:
        captured["ctx"] = ctx.obj
        click.echo("ok")

    cli_main.main.add_command(introspect)
    result = runner.invoke(cli_main.main, [*args, "introspect"], env=env)
    assert result.exit_code == 0, result.output
    return captured["ctx"], result


def test_verbose_flags_adjust_log_configuration() -> None:
    ctx, result = _invoke_with_capture(["-vv"])

    assert "ok" in result.output
    assert ctx.verbosity == 2
    assert ctx.log_config.verbosity == 2
    assert ctx.log_config.quiet is False
    assert ctx.log_config.level in {"DEBUG", "TRACE"}


def test_quiet_flag_supersedes_verbosity() -> None:
    ctx, _ = _invoke_with_capture(["--quiet"])

    assert ctx.quiet is True
    assert ctx.verbosity == 0
    assert ctx.log_config.quiet is True
    assert ctx.log_config.level == "ERROR"


def test_json_flag_enables_structured_output() -> None:
    ctx, _ = _invoke_with_capture(["--json"])

    assert ctx.json_mode is True
    assert ctx.log_config.json_mode is True
    assert ctx.log_config.level == "INFO"


def test_run_identifier_uses_environment_override() -> None:
    ctx, _ = _invoke_with_capture([], env={"SQLITCH_RUN_ID": "run-identifier"})

    assert ctx.run_identifier == "run-identifier"
    assert ctx.log_config.run_identifier == "run-identifier"


def test_run_identifier_defaults_to_uuid() -> None:
    ctx, _ = _invoke_with_capture([])

    UUID(ctx.run_identifier)
