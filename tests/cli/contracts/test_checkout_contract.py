"""Contract parity tests for ``sqlitch checkout``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner configured for isolation."""

    return CliRunner()


def _seed_plan(plan_path: Path) -> None:
    change = Change.create(
        name="widgets:init",
        script_paths={
            "deploy": Path("deploy") / "widgets_init.sql",
            "revert": Path("revert") / "widgets_init.sql",
            "verify": Path("verify") / "widgets_init.sql",
        },
        planner="Ada Lovelace",
        planned_at=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        notes="Initialises widgets schema",
    )

    write_plan(
        project_name="widgets",
        default_engine="sqlite",
        entries=(change,),
        plan_path=plan_path,
    )


def test_checkout_requires_vcs_configuration(runner: CliRunner) -> None:
    """Checkout should fail when no VCS command is configured."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "checkout",
                "--log-only",
                "--target",
                "db:sqlite:deploy.db",
            ],
        )

        assert result.exit_code != 0
        assert "No VCS configured" in result.output


def test_checkout_log_only_reports_pipeline(runner: CliRunner) -> None:
    """Log-only mode should describe the checkout pipeline and exit successfully."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "checkout",
                "--log-only",
                "--target",
                "db:sqlite:deploy.db",
                "--mode",
                "tag:v1.0",
            ],
            env={"SQLITCH_VCS_COMMAND": "git checkout feature/login"},
        )

        assert result.exit_code == 0, result.output
        assert "Would revert target 'db:sqlite:deploy.db' using mode 'tag:v1.0'" in result.output
        assert "Would run VCS command: git checkout feature/login" in result.output
        assert "Would deploy pending changes to target 'db:sqlite:deploy.db'" in result.output
        assert "Log-only run; no database changes were applied." in result.output
