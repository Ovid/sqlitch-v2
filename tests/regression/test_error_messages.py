"""Regression tests asserting Sqitch-parity error messaging."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.sqlite_fixtures import ChangeScript, create_sqlite_project

GOLDEN_ROOT = Path(__file__).resolve().parent.parent / "support" / "golden" / "error_messages"


def _load_golden(name: str) -> str:
    return (GOLDEN_ROOT / name).read_text(encoding="utf-8")


def test_unknown_change_error_matches_sqitch(tmp_path: Path) -> None:
    """Deploying to a non-existent change should mirror Sqitch messaging."""

    runner = CliRunner()
    project = create_sqlite_project(
        tmp_path,
        changes=[
            ChangeScript(
                name="users",
                deploy_sql="SELECT 1;",
                revert_sql="SELECT 1;",
            )
        ],
    )

    target = f"db:sqlite:{project.registry_path}"
    result = runner.invoke(
        main,
        ["--chdir", str(project.project_root), "deploy", target, "--to-change", "flips"],
    )

    assert result.exit_code != 0, result.output
    assert result.output == _load_golden("unknown_change.txt")


def test_unknown_target_error_matches_sqitch(tmp_path: Path) -> None:
    """Referencing an unknown target alias should mirror Sqitch messaging."""

    runner = CliRunner()
    project = create_sqlite_project(
        tmp_path,
        changes=[
            ChangeScript(
                name="users",
                deploy_sql="SELECT 1;",
                revert_sql="SELECT 1;",
            )
        ],
    )

    result = runner.invoke(
        main,
        ["--chdir", str(project.project_root), "engine", "add", "demo", "analytics"],
    )

    assert result.exit_code != 0, result.output
    assert result.output == _load_golden("unknown_target.txt")


def test_missing_dependency_error_matches_sqitch(tmp_path: Path) -> None:
    """Plans referencing unknown dependencies should match Sqitch error text."""

    runner = CliRunner()
    project = create_sqlite_project(
        tmp_path,
        changes=[
            ChangeScript(
                name="alpha",
                deploy_sql="SELECT 1;",
                revert_sql="SELECT 1;",
                dependencies=("beta",),
            )
        ],
    )

    target = f"db:sqlite:{project.registry_path}"
    result = runner.invoke(
        main,
        ["--chdir", str(project.project_root), "deploy", target],
    )

    assert result.exit_code != 0, result.output
    assert result.output == _load_golden("missing_dependency.txt")
