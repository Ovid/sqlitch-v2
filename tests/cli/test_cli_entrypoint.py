"""Smoke tests for the SQLitch CLI entry point."""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path
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


def test_python_m_sqlitch_cli_main_executes_commands(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(repo_root)
        if not existing_pythonpath
        else f"{repo_root}{os.pathsep}{existing_pythonpath}"
    )

    command = [
        sys.executable,
        "-m",
        "sqlitch.cli.main",
        "init",
        "flipr",
        "--uri",
        "https://example.com",
        "--engine",
        "sqlite",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"

    config_path = tmp_path / "sqlitch.conf"
    assert config_path.exists()
    contents = config_path.read_text(encoding="utf-8")
    assert "uri = https://example.com" in contents
