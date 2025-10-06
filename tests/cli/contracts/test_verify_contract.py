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
    """sqlitch verify reports when no target is provided."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

    result = runner.invoke(main, ["verify"])
    assert result.exit_code != 0
    assert "target must be provided" in result.output


def test_verify_log_only_reports_unimplemented(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["verify", "--log-only"])
        assert result.exit_code != 0
        assert "not implemented" in result.output
