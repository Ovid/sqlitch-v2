"""Contract parity tests for ``sqlitch deploy``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

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

    return change_one, change_two, tag


def _write_change_scripts(
    base_dir: Path,
    change: Change,
    *,
    deploy_sql: str,
    revert_sql: str = "-- revert placeholder",
    verify_sql: str = "SELECT 1;",
) -> None:
    """Create deploy, revert, and verify scripts for ``change``."""

    for kind, sql in (
        ("deploy", deploy_sql),
        ("revert", revert_sql),
        ("verify", verify_sql),
    ):
        script_path = change.script_paths.get(kind)
        if script_path is None:
            continue
        path = base_dir / script_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sql, encoding="utf-8")


def test_deploy_requires_target(runner: CliRunner) -> None:
    """Deploy should require a target to be provided explicitly or via config."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["deploy", "--log-only"])

        assert result.exit_code != 0
        assert "A deployment target must be provided" in result.output


def test_deploy_log_only_outputs_changes(runner: CliRunner) -> None:
    """Log-only mode should list the changes without executing them."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        change_one, change_two, _ = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            ["deploy", "--log-only", "--target", "db:sqlite:deploy.db"],
        )

        assert result.exit_code == 0, result.output
        assert f"Would deploy change {change_one.name}" in result.output
        assert f"Would deploy change {change_two.name}" in result.output
        assert "Log-only run; no database changes were applied." in result.output


def test_deploy_to_change_limits_scope(runner: CliRunner) -> None:
    """Using --to-change should restrict the deployment set."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        change_one, change_two, _ = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "deploy",
                "--log-only",
                "--target",
                "db:sqlite:deploy.db",
                "--to-change",
                change_one.name,
            ],
        )

        assert result.exit_code == 0, result.output
        assert f"Would deploy change {change_one.name}" in result.output
        assert f"Would deploy change {change_two.name}" not in result.output


def test_deploy_rejects_conflicting_filters(runner: CliRunner) -> None:
    """Providing both --to-change and --to-tag should raise an error."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        change_one, _, tag = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "deploy",
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


def test_deploy_executes_scripts_and_updates_registry(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deploy should execute scripts and record registry state for SQLite."""

    monkeypatch.setenv("SQLITCH_USER_NAME", "Grace Hopper")
    monkeypatch.setenv("SQLITCH_USER_EMAIL", "grace@example.com")

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        change_one, change_two, _ = _seed_plan(plan_path)

        _write_change_scripts(
            plan_path.parent,
            change_one,
            deploy_sql="""
            CREATE TABLE widgets (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            """,
            revert_sql="DROP TABLE IF EXISTS widgets;",
        )

        _write_change_scripts(
            plan_path.parent,
            change_two,
            deploy_sql="INSERT INTO widgets (name) VALUES ('gizmo');",
            revert_sql="DELETE FROM widgets WHERE name = 'gizmo';",
        )

        result = runner.invoke(
            main,
            ["deploy", "--target", "db:sqlite:deploy.db"],
        )

        assert result.exit_code == 0, result.output
        assert "Deploying plan 'widgets'" in result.output
        assert "core:init" in result.output
        assert "widgets:add" in result.output

        connection = sqlite3.connect("deploy.db")
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'widgets'"
            )
            assert cursor.fetchone() is not None

            cursor.execute("SELECT COUNT(*) FROM widgets")
            assert cursor.fetchone() == (1,)

            cursor.execute("SELECT change, event FROM events ORDER BY committed_at, change_id")
            events = cursor.fetchall()
            assert events == [
                ("core:init", "deploy"),
                ("widgets:add", "deploy"),
            ]
        finally:
            connection.close()

        rerun = runner.invoke(
            main,
            ["deploy", "--target", "db:sqlite:deploy.db"],
        )

        assert rerun.exit_code == 0, rerun.output
        assert "Nothing to deploy" in rerun.output
