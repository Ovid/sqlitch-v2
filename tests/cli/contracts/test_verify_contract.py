"""Contract parity tests for ``sqlitch verify``."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner for isolated filesystem tests."""

    return CliRunner()


def test_verify_no_changes(runner: CliRunner) -> None:
    """sqlitch verify reports when no target is provided."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["verify"])
        assert result.exit_code != 0
        assert "target must be provided" in result.output


def test_verify_log_only_reports_unimplemented(runner: CliRunner) -> None:
    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["verify", "--log-only"])
        assert result.exit_code != 0
        assert "not implemented" in result.output
