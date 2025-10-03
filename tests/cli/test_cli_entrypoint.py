"""Smoke tests for the SQLitch CLI entry point."""

from __future__ import annotations

from click.testing import CliRunner

from sqlitch.cli.main import main


def test_cli_group_invokes_successfully() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "sqlitch" in result.output


def test_cli_exposes_version_option() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "sqlitch" in result.output
