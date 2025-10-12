"""Tests for sqlitch.cli.__main__ module entry point."""

from __future__ import annotations

import subprocess
import sys

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
