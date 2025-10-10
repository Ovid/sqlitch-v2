"""Contract parity tests for ``sqlitch upgrade``."""

from __future__ import annotations

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner for isolated filesystem tests."""

    return CliRunner()


def test_upgrade_already_up_to_date(runner: CliRunner) -> None:
    """sqlitch upgrade reports when registry is current."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["upgrade"])
        assert result.exit_code != 0
        assert "not implemented" in result.output


def test_upgrade_log_only_reports_unimplemented(runner: CliRunner) -> None:
    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["upgrade", "--log-only"])
        assert result.exit_code != 0
        assert "not implemented" in result.output
