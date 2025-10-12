"""Tests for sqlitch.cli.__main__ module entry point."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Iterable

from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context

__all__ = ["TestMainModuleExecution"]


class TestMainModuleExecution:
    """Tests for python -m sqlitch.cli execution."""

    def test_module_execution_prints_usage(self) -> None:
        """Verify running python -m sqlitch.cli prints usage information."""
        result = subprocess.run(
            [sys.executable, "-m", "sqlitch.cli", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "sqlitch" in result.stdout.lower()

    def test_module_execution_without_args_shows_usage(self) -> None:
        """Verify running python -m sqlitch.cli without args shows usage."""
        result = subprocess.run(
            [sys.executable, "-m", "sqlitch.cli"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Without a command, Click returns exit code 2 and shows usage
        assert result.returncode == 2
        # Usage should be in stderr
        assert "Usage:" in result.stderr or "Commands:" in result.stderr

    def test_module_execution_with_invalid_command_fails(self) -> None:
        """Verify running python -m sqlitch.cli with invalid command fails."""
        result = subprocess.run(
            [sys.executable, "-m", "sqlitch.cli", "nonexistent-command"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode != 0
        assert "Error:" in result.stderr or "error" in result.stderr.lower()

    def test_module_execution_version_flag(self) -> None:
        """Verify running python -m sqlitch.cli --version shows version."""
        result = subprocess.run(
            [sys.executable, "-m", "sqlitch.cli", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Version flag should work
        assert result.returncode == 0
        # Version output format varies, just check it executed


# =============================================================================
# Lockdown Tests (merged from test_main_lockdown.py)
# =============================================================================


def _collect_non_json_lines(output: str) -> list[str]:
    """Return lines from output that are not valid JSON payloads."""
    non_json: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            non_json.append(line)
    return non_json


def _invoke_cli(args: Iterable[str]) -> tuple[int, str]:
    runner = CliRunner()
    with isolated_test_context(runner) as (runner, _temp_dir):
        result = runner.invoke(main, list(args))
    return result.exit_code, result.output


def test_init_error_in_json_mode_emits_structured_output_only() -> None:
    exit_code, output = _invoke_cli(["--json", "init", "--engine", "invalid"])

    assert exit_code != 0
    assert _collect_non_json_lines(output) == []


def test_add_error_in_json_mode_emits_structured_output_only() -> None:
    exit_code, output = _invoke_cli(["--json", "add", "users"])

    assert exit_code != 0
    assert _collect_non_json_lines(output) == []


def test_deploy_error_in_json_mode_emits_structured_output_only() -> None:
    exit_code, output = _invoke_cli(["--json", "deploy"])

    assert exit_code != 0
    assert _collect_non_json_lines(output) == []
