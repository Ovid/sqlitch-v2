"""Contract parity tests for ``sqlitch rebase``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change, Tag


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner configured for isolation."""

    return CliRunner()


def _seed_plan(plan_path: Path) -> tuple[Change, Change, Tag]:
    change_one = Change.create(
        name="core:init",
        script_paths={
            "deploy": Path("deploy") / "20250101000000_core_init.sql",
            "revert": Path("revert") / "20250101000000_core_init.sql",
            "verify": Path("verify") / "20250101000000_core_init.sql",
        },
        planner="Ada Lovelace",
        planned_at=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        notes="Initialises core schema",
    )

    change_two = Change.create(
        name="widgets:add",
        script_paths={
            "deploy": Path("deploy") / "20250102000000_widgets_add.sql",
            "revert": Path("revert") / "20250102000000_widgets_add.sql",
            "verify": Path("verify") / "20250102000000_widgets_add.sql",
        },
        planner="Ada Lovelace",
        planned_at=datetime(2025, 1, 2, 0, 0, tzinfo=timezone.utc),
        notes="Adds widgets table",
        dependencies=("core:init",),
        tags=("v1.0",),
    )

    tag = Tag(
        name="v1.0",
        change_ref=change_two.name,
        planner="Ada Lovelace",
        tagged_at=datetime(2025, 1, 2, 0, 5, tzinfo=timezone.utc),
    )

    write_plan(
        project_name="widgets",
        default_engine="sqlite",
        entries=(change_one, change_two, tag),
        plan_path=plan_path,
    )

    return change_one, change_two, tag


def test_rebase_requires_target(runner: CliRunner) -> None:
    """Rebase should require a target to be provided explicitly or via config."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["rebase", "--log-only"])

        assert result.exit_code != 0
        assert "A deployment target must be provided" in result.output


def test_rebase_log_only_shows_revert_and_deploy_sequences(runner: CliRunner) -> None:
    """Log-only runs should outline both the revert and deploy stages."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        change_one, change_two, _ = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "rebase",
                "--log-only",
                "--target",
                "db:sqlite:rebase.db",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Rebasing plan 'widgets' on target 'db:sqlite:rebase.db' (log-only)." in result.output
        first_revert = result.output.index(f"Would revert change {change_two.name}")
        second_revert = result.output.index(f"Would revert change {change_one.name}")
        assert first_revert < second_revert
        first_deploy = result.output.index(f"Would deploy change {change_one.name}")
        second_deploy = result.output.index(f"Would deploy change {change_two.name}")
        assert first_deploy < second_deploy
        assert "Log-only run; no database changes were applied." in result.output


def test_rebase_from_option_limits_redeploy_scope(runner: CliRunner) -> None:
    """Providing --from should restrict the redeployment set."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        change_one, change_two, _ = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "rebase",
                "--log-only",
                "--target",
                "db:sqlite:rebase.db",
                "--from",
                change_two.name,
            ],
        )

        assert result.exit_code == 0, result.output
        assert f"Would deploy change {change_two.name}" in result.output
        assert f"Would deploy change {change_one.name}" not in result.output


def test_rebase_onto_option_limits_revert_scope(runner: CliRunner) -> None:
    """Providing --onto should keep earlier changes deployed."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        change_one, change_two, tag = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "rebase",
                "--log-only",
                "--target",
                "db:sqlite:rebase.db",
                "--onto",
                tag.name,
            ],
        )

        assert result.exit_code == 0, result.output
        assert f"Would revert change {change_two.name}" in result.output
        assert f"Would revert change {change_one.name}" not in result.output


def test_rebase_unknown_reference_fails(runner: CliRunner) -> None:
    """Unknown change or tag references should surface helpful errors."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "rebase",
                "--log-only",
                "--target",
                "db:sqlite:rebase.db",
                "--from",
                "missing:change",
            ],
        )

        assert result.exit_code != 0
        assert "Plan does not contain change 'missing:change'" in result.output
