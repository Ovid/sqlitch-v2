"""Contract parity tests for ``sqlitch add``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from click.testing import CliRunner
import pytest

from sqlitch.cli.commands import add as add_module
from sqlitch.cli.main import main
from sqlitch.plan.model import Change
from sqlitch.plan.formatter import write_plan


def _write_plan(path: Path, entries: tuple[Change, ...] = ()) -> None:
    write_plan(
        project_name="demo",
        default_engine="sqlite",
        entries=entries,
        plan_path=path,
    )


def test_add_appends_change_and_creates_scripts(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    timestamp = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(add_module, "_utcnow", lambda: timestamp)
    monkeypatch.setenv("SQLITCH_USER_NAME", "Ada Lovelace")
    monkeypatch.setenv("SQLITCH_USER_EMAIL", "ada@example.com")

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        seed_changes = (
            Change.create(
                name="roles",
                script_paths={
                    "deploy": Path("deploy/seed_roles.sql"),
                    "revert": Path("revert/seed_roles.sql"),
                    "verify": Path("verify/seed_roles.sql"),
                },
                planner="Seeder",
                planned_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            ),
            Change.create(
                name="users",
                script_paths={
                    "deploy": Path("deploy/seed_users.sql"),
                    "revert": Path("revert/seed_users.sql"),
                    "verify": Path("verify/seed_users.sql"),
                },
                planner="Seeder",
                planned_at=datetime(2024, 1, 1, 1, 0, tzinfo=timezone.utc),
            ),
        )
        _write_plan(plan_path, seed_changes)

        result = runner.invoke(
            main,
            [
                "add",
                "widgets",
                "--requires",
                "roles",
                "--requires",
                "users",
                "--tags",
                "feature",
                "--note",
                "Adds widgets",
            ],
        )

        assert result.exit_code == 0, result.output
        deploy_name = "deploy/20250102030405_widgets.sql"
        revert_name = "revert/20250102030405_widgets.sql"
        verify_name = "verify/20250102030405_widgets.sql"

        assert f"Created deploy script {deploy_name}" in result.output
        assert f"Created revert script {revert_name}" in result.output
        assert f"Created verify script {verify_name}" in result.output
        assert "Added widgets" in result.output

        deploy_path = Path(deploy_name)
        revert_path = Path(revert_name)
        verify_path = Path(verify_name)
        assert deploy_path.exists()
        assert revert_path.exists()
        assert verify_path.exists()
        assert (
            deploy_path.read_text(encoding="utf-8")
            == "-- SQLitch generated deploy script for widgets\n"
        )
        assert (
            revert_path.read_text(encoding="utf-8")
            == "-- SQLitch generated revert script for widgets\n"
        )
        assert (
            verify_path.read_text(encoding="utf-8")
            == "-- SQLitch generated verify script for widgets\n"
        )

        plan_content = plan_path.read_text(encoding="utf-8")
        assert "change widgets" in plan_content
        assert deploy_name in plan_content
        assert revert_name in plan_content
        assert verify_name in plan_content
        assert "planner='Ada Lovelace <ada@example.com>'" in plan_content
        assert "planned_at=2025-01-02T03:04:05Z" in plan_content
        assert "notes='Adds widgets'" in plan_content
        assert "depends=roles,users" in plan_content
        assert "tags=feature" in plan_content


def test_add_rejects_duplicate_change(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    timestamp = datetime(2024, 5, 6, 7, 8, 9, tzinfo=timezone.utc)
    monkeypatch.setattr(add_module, "_utcnow", lambda: timestamp)
    monkeypatch.setenv("SQLITCH_USER_NAME", "Grace Hopper")

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        existing_change = Change.create(
            name="widgets",
            script_paths={
                "deploy": Path("deploy/existing.sql"),
                "revert": Path("revert/existing.sql"),
                "verify": Path("verify/existing.sql"),
            },
            planner="Existing Planner",
            planned_at=datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc),
        )
        _write_plan(plan_path, (existing_change,))
        original_content = plan_path.read_text(encoding="utf-8")

        result = runner.invoke(main, ["add", "widgets"])

        assert result.exit_code != 0
        assert 'Change "widgets" already exists in plan' in result.output
        assert plan_path.read_text(encoding="utf-8") == original_content

        expected_deploy = Path("deploy/20240506070809_widgets.sql")
        assert not expected_deploy.exists()


def test_add_uses_explicit_plan_override(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    timestamp = datetime(2025, 7, 8, 9, 10, 11, tzinfo=timezone.utc)
    monkeypatch.setattr(add_module, "_utcnow", lambda: timestamp)
    monkeypatch.setenv("SQLITCH_USER_NAME", "Katherine Johnson")

    with runner.isolated_filesystem():
        override_plan = Path("custom.plan")
        _write_plan(override_plan)

        result = runner.invoke(main, ["--plan-file", str(override_plan), "add", "reports"])

        assert result.exit_code == 0, result.output
        assert not Path("sqlitch.plan").exists()

        plan_content = override_plan.read_text(encoding="utf-8")
        assert "change reports" in plan_content
        assert "deploy/20250708091011_reports.sql" in plan_content
        assert "verify/20250708091011_reports.sql" in plan_content
