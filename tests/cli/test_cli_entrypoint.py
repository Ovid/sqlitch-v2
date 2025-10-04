"""Smoke tests for the SQLitch CLI entry point."""

from __future__ import annotations

import runpy
import sys
from types import ModuleType

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


def test_python_m_sqlitch_cli_invokes_main(monkeypatch) -> None:
    invoked: list[bool] = []

    def fake_main() -> None:
        invoked.append(True)

    fake_main_module = ModuleType("sqlitch.cli.main")
    setattr(fake_main_module, "main", fake_main)

    monkeypatch.setitem(sys.modules, "sqlitch.cli.main", fake_main_module)
    monkeypatch.delitem(sys.modules, "sqlitch.cli.__main__", raising=False)

    runpy.run_module("sqlitch.cli.__main__", run_name="__main__")

    assert invoked
