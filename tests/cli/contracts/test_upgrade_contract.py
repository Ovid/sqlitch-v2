"""Contract parity tests for ``sqlitch upgrade``."""

from __future__ import annotations

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner for isolated filesystem tests."""

    return CliRunner()


def test_upgrade_already_up_to_date(runner: CliRunner) -> None:
    """sqlitch upgrade reports when registry is current."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["upgrade"])
        assert result.exit_code == 0
        assert "already at version" in result.output or "Upgraded" in result.output
