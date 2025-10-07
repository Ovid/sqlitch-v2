"""Contract parity tests for ``sqlitch revert``."""

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
            "deploy": Path("deploy") / "core_init.sql",
            "revert": Path("revert") / "core_init.sql",
            "verify": Path("verify") / "core_init.sql",
        },
        planner="Ada Lovelace",
        planned_at=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        notes="Initialises core schema",
    )

    change_two = Change.create(
        name="widgets:add",
        script_paths={
            "deploy": Path("deploy") / "widgets_add.sql",
            "revert": Path("revert") / "widgets_add.sql",
            "verify": Path("verify") / "widgets_add.sql",
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


    # Create minimal config so commands can find engine (Sqitch stores engine in config, not plan)
    config_path = plan_path.parent / "sqitch.conf"
    config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

    return change_one, change_two, tag


def test_revert_requires_target(runner: CliRunner) -> None:
    """Revert should require a target to be provided explicitly or via config."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["revert", "--log-only"])

        assert result.exit_code != 0
        assert "A deployment target must be provided" in result.output


def test_revert_log_only_outputs_changes_in_reverse(runner: CliRunner) -> None:
    """Log-only mode should list changes in reverse deployment order."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        change_one, change_two, _ = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "revert",
                "--log-only",
                "--target",
                "db:sqlite:deploy.db",
            ],
        )

        assert result.exit_code == 0, result.output
        first_index = result.output.index(f"Would revert change {change_two.name}")
        second_index = result.output.index(f"Would revert change {change_one.name}")
        assert first_index < second_index
        assert "Log-only run; no database changes were applied." in result.output


def test_revert_conflicting_filters_error(runner: CliRunner) -> None:
    """Providing both --to-change and --to-tag should raise an error."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        change_one, _, tag = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "revert",
                "--log-only",
                "--target",
                "db:sqlite:deploy.db",
                "--to-change",
                change_one.name,
                "--to-tag",
                tag.name,
            ],
        )

        assert result.exit_code != 0
        assert "Cannot combine --to-change and --to-tag" in result.output
