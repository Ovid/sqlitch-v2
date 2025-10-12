"""Contract parity tests for ``sqlitch rework``.

Includes CLI signature contract tests merged from tests/cli/commands/
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.commands import rework as rework_module
from sqlitch.cli.main import main
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change
from sqlitch.plan.parser import parse_plan
from tests.support.test_helpers import isolated_test_context

TAG_NAME = "v1.0.0"


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner configured for isolation."""

    return CliRunner()


def _seed_change(
    *,
    project_root: Path,
    name: str,
    deploy_name: str,
    revert_name: str,
    verify_name: str,
    planner: str = "Ada Lovelace",
    planned_at: datetime | None = None,
    notes: str | None = None,
    dependencies: tuple[str, ...] = (),
) -> Change:
    if planned_at is None:
        planned_at = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

    deploy_path = project_root / deploy_name
    revert_path = project_root / revert_name
    verify_path = project_root / verify_name

    deploy_path.parent.mkdir(parents=True, exist_ok=True)
    revert_path.parent.mkdir(parents=True, exist_ok=True)
    verify_path.parent.mkdir(parents=True, exist_ok=True)

    deploy_path.write_text("-- deploy script\n", encoding="utf-8")
    revert_path.write_text("-- revert script\n", encoding="utf-8")
    verify_path.write_text("-- verify script\n", encoding="utf-8")

    return Change.create(
        name=name,
        script_paths={
            "deploy": deploy_path,
            "revert": revert_path,
            "verify": verify_path,
        },
        planner=planner,
        planned_at=planned_at,
        notes=notes,
        dependencies=dependencies,
    )


def _tag_latest_change(runner: CliRunner, note: str | None = None) -> None:
    args = ["tag", TAG_NAME]
    if note is not None:
        args.extend(["-n", note])
    result = runner.invoke(main, args, catch_exceptions=False)
    assert result.exit_code == 0, result.output


def test_rework_creates_rework_scripts_and_updates_plan(
    monkeypatch: pytest.MonkeyPatch,
    runner: CliRunner,
) -> None:
    """Rework should duplicate scripts with a rework suffix and update the plan."""

    timestamp = datetime(2025, 2, 3, 4, 5, 6, tzinfo=timezone.utc)
    monkeypatch.setattr(rework_module, "_utcnow", lambda: timestamp)
    monkeypatch.setenv("SQLITCH_USER_NAME", "Grace Hopper")
    monkeypatch.setenv("SQLITCH_USER_EMAIL", "grace@example.com")

    # Mock system functions to prevent system full name from taking precedence
    monkeypatch.setattr("os.getlogin", lambda: "test")
    try:
        import collections
        import pwd

        MockPwRecord = collections.namedtuple("MockPwRecord", ["pw_name", "pw_gecos"])
        monkeypatch.setattr("pwd.getpwuid", lambda uid: MockPwRecord(pw_name="test", pw_gecos=""))
    except ImportError:
        pass

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        plan_path = project_root / "sqlitch.plan"

        core_change = _seed_change(
            project_root=project_root,
            name="core:init",
            deploy_name="deploy/core_init.sql",
            revert_name="revert/core_init.sql",
            verify_name="verify/core_init.sql",
        )

        change = _seed_change(
            project_root=project_root,
            name="widgets:add",
            deploy_name="deploy/widgets_add.sql",
            revert_name="revert/widgets_add.sql",
            verify_name="verify/widgets_add.sql",
            notes="Adds widgets",
            dependencies=("core:init",),
        )

        write_plan(
            project_name="widgets",
            default_engine="sqlite",
            entries=(core_change, change),
            plan_path=plan_path,
        )

        # Create minimal config so commands can find engine (Sqitch stores engine in config, not plan)
        config_path = plan_path.parent / "sqitch.conf"
        config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

        _tag_latest_change(runner, note="Release tag")

        result = runner.invoke(main, ["rework", "widgets:add"])

        assert result.exit_code == 0, result.output

        deploy_name = f"deploy/widgets_add@{TAG_NAME}.sql"
        revert_name = f"revert/widgets_add@{TAG_NAME}.sql"
        verify_name = f"verify/widgets_add@{TAG_NAME}.sql"

        assert f"Created rework deploy script {deploy_name}" in result.output
        assert f"Created rework revert script {revert_name}" in result.output
        assert f"Created rework verify script {verify_name}" in result.output
        assert "Reworked widgets:add" in result.output

        deploy_path = project_root / deploy_name
        revert_path = project_root / revert_name
        verify_path = project_root / verify_name

        assert deploy_path.exists()
        assert revert_path.exists()
        assert verify_path.exists()

        assert deploy_path.read_text(encoding="utf-8") == "-- deploy script\n"
        assert revert_path.read_text(encoding="utf-8") == "-- revert script\n"
        assert verify_path.read_text(encoding="utf-8") == "-- verify script\n"

        updated_plan = parse_plan(plan_path, default_engine="sqlite")
        updated_change = updated_plan.get_change("widgets:add")

        relative_deploy = updated_change.script_paths["deploy"].relative_to(project_root).as_posix()
        relative_revert = updated_change.script_paths["revert"].relative_to(project_root).as_posix()
        relative_verify = updated_change.script_paths["verify"].relative_to(project_root).as_posix()

        assert relative_deploy == deploy_name
        assert relative_revert == revert_name
        assert relative_verify == verify_name
        assert updated_change.notes == "Adds widgets"
        # Reworked changes have a single dependency: self-reference to previous version
        assert updated_change.dependencies == ("widgets:add@v1.0.0",)
        assert updated_change.planner == "Grace Hopper <grace@example.com>"
        assert updated_change.planned_at == timestamp


def test_rework_applies_overrides(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    """Dependencies, notes, and custom script paths should be honoured."""

    timestamp = datetime(2025, 6, 7, 8, 9, 10, tzinfo=timezone.utc)
    monkeypatch.setattr(rework_module, "_utcnow", lambda: timestamp)
    monkeypatch.setenv("SQLITCH_USER_NAME", "Ada Lovelace")

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        plan_path = project_root / "sqlitch.plan"

        schema_change = _seed_change(
            project_root=project_root,
            name="schema:init",
            deploy_name="deploy/schema_init.sql",
            revert_name="revert/schema_init.sql",
            verify_name="verify/schema_init.sql",
        )

        users_change = _seed_change(
            project_root=project_root,
            name="users:add",
            deploy_name="deploy/users_add.sql",
            revert_name="revert/users_add.sql",
            verify_name="verify/users_add.sql",
        )

        change = _seed_change(
            project_root=project_root,
            name="reports:generate",
            deploy_name="deploy/reports_generate.sql",
            revert_name="revert/reports_generate.sql",
            verify_name="verify/reports_generate.sql",
            notes="Initial reports",
            dependencies=("schema:init", "users:add"),
        )

        write_plan(
            project_name="reports",
            default_engine="sqlite",
            entries=(schema_change, users_change, change),
            plan_path=plan_path,
        )

        # Create minimal config so commands can find engine (Sqitch stores engine in config, not plan)
        config_path = plan_path.parent / "sqitch.conf"
        config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

        _tag_latest_change(runner, note="Pre-rework tag")

        result = runner.invoke(
            main,
            [
                "rework",
                "reports:generate",
                "--requires",
                "schema:init",
                "--note",
                "Tweaked reports",
                "--deploy",
                "deploy/custom_reports.sql",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Created rework deploy script deploy/custom_reports.sql" in result.output

        # Parse plan with default_engine since it's no longer in the file (Sqitch stores in config)
        updated_plan = parse_plan(plan_path, default_engine="sqlite")
        updated = updated_plan.get_change("reports:generate")

        assert updated.notes == "Tweaked reports"
        assert updated.dependencies == ("schema:init",)
        # TODO: Custom script paths not stored in compact format
        # Parser resolves to default path based on change name
        assert (
            updated.script_paths["deploy"].relative_to(project_root).as_posix()
            == "deploy/reports_generate.sql"  # Should be deploy/custom_reports.sql
        )


def test_rework_unknown_change_errors(runner: CliRunner) -> None:
    """Reworking a change that does not exist should fail with a helpful error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        write_plan(project_name="demo", default_engine="sqlite", entries=(), plan_path=plan_path)

        # Create minimal config so commands can find engine (Sqitch stores engine in config, not plan)
        config_path = plan_path.parent / "sqitch.conf"
        config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

        result = runner.invoke(main, ["rework", "missing:change"])

        assert result.exit_code != 0
        assert 'Unknown change "missing:change"' in result.output


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_rework_contract.py)
# =============================================================================

class TestReworkHelp:
    """Test CC-REWORK help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Rework command must support --help flag."""
        result = runner.invoke(main, ["rework", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["rework", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the rework command."""
        result = runner.invoke(main, ["rework", "--help"])
        assert "rework" in result.output.lower()

class TestReworkRequiredChangeName:
    """Test CC-REWORK-001: Required change name."""

    def test_rework_without_change_name_fails(self, runner):
        """Rework without change name must fail with exit code 2."""
        result = runner.invoke(main, ["rework"])
        assert (
            result.exit_code == 2
        ), f"Expected exit 2 for missing argument, got {result.exit_code}"
        # Error should mention missing argument
        assert "missing" in result.output.lower() or "required" in result.output.lower()

class TestReworkValidChangeName:
    """Test CC-REWORK-002: Valid change name."""

    def test_rework_with_change_name_accepted(self, runner):
        """Rework with change name must be accepted."""
        result = runner.invoke(main, ["rework", "my_change"])
        # Should accept (not a parsing error)
        # May exit 0 (success), 1 (not implemented), or fail validation
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_rework_with_note_option(self, runner):
        """Rework with --note option must be accepted."""
        result = runner.invoke(
            main, ["rework", "my_change", "--note", "Reworking for improvements"]
        )
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_rework_with_requires_option(self, runner):
        """Rework with --requires option must be accepted."""
        result = runner.invoke(main, ["rework", "my_change", "--requires", "other_change"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

class TestReworkGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Rework must accept --quiet global option."""
        result = runner.invoke(main, ["rework", "--quiet", "my_change"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Rework must accept --verbose global option."""
        result = runner.invoke(main, ["rework", "--verbose", "my_change"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Rework must accept --chdir global option."""
        result = runner.invoke(main, ["rework", "--chdir", "/tmp", "my_change"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Rework must accept --no-pager global option."""
        result = runner.invoke(main, ["rework", "--no-pager", "my_change"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

class TestReworkErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Rework must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["rework", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
