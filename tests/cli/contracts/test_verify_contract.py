"""Contract parity tests for ``sqlitch verify``."""

from __future__ import annotations

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner for isolated filesystem tests."""

    return CliRunner()


def test_verify_no_changes(runner: CliRunner) -> None:
    """sqlitch verify reports when no changes to verify."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["verify"])
        assert result.exit_code == 0
        assert "No changes to verify" in result.output or "ok" in result.output
