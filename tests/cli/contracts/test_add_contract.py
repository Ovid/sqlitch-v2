"""Contract parity tests for ``sqlitch add``.

Perl Reference:
- Source: sqitch/lib/App/Sqitch/Command/add.pm
- POD: sqitch/lib/sqitch-add.pod
- Tests: sqitch/t/add.t

Includes CLI signature contract tests merged from tests/cli/commands/
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.commands import add as add_module
from sqlitch.cli.main import main
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change
from sqlitch.utils.templates import default_template_body, render_template
from tests.support.test_helpers import isolated_test_context


def _write_plan(path: Path, entries: tuple[Change, ...] = ()) -> None:
    """Write a plan file and minimal sqitch.conf for tests.

    Sqitch doesn't store engine in plan file - it comes from config.
    """
    # Write plan file (without default_engine header)
    write_plan(
        project_name="demo",
        default_engine="sqlite",  # Used for Plan object but not written to file
        entries=entries,
        plan_path=path,
    )

    # Write minimal config file so commands can find the engine
    config_path = path.parent / "sqitch.conf"
    config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")


def test_add_appends_change_and_creates_scripts(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    timestamp = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(add_module, "_utcnow", lambda: timestamp)
    monkeypatch.setenv("SQLITCH_USER_NAME", "Ada Lovelace")
    monkeypatch.setenv("SQLITCH_USER_EMAIL", "ada@example.com")

    # Mock system functions to prevent system name from taking precedence
    monkeypatch.setattr("os.getlogin", lambda: "test")
    try:
        import collections
        import pwd

        MockPwRecord = collections.namedtuple("MockPwRecord", ["pw_name", "pw_gecos"])
        monkeypatch.setattr("pwd.getpwuid", lambda uid: MockPwRecord(pw_name="test", pw_gecos=""))
    except ImportError:
        pass

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        seed_changes = (
            Change.create(
                name="roles",
                script_paths={
                    "deploy": (temp_dir / "deploy/seed_roles.sql"),
                    "revert": (temp_dir / "revert/seed_roles.sql"),
                    "verify": (temp_dir / "verify/seed_roles.sql"),
                },
                planner="Seeder",
                planned_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            ),
            Change.create(
                name="users",
                script_paths={
                    "deploy": (temp_dir / "deploy/seed_users.sql"),
                    "revert": (temp_dir / "revert/seed_users.sql"),
                    "verify": (temp_dir / "verify/seed_users.sql"),
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

        assert result.exit_code == 0, result.stderr
        deploy_name = "deploy/widgets.sql"
        revert_name = "revert/widgets.sql"
        verify_name = "verify/widgets.sql"

        assert f"Created {deploy_name}" in result.stdout
        assert f"Created {revert_name}" in result.stdout
        assert f"Created {verify_name}" in result.stdout
        assert 'Added "widgets" to sqitch.plan' in result.stdout

        deploy_path = Path(deploy_name)
        revert_path = Path(revert_name)
        verify_path = Path(verify_name)
        assert deploy_path.exists()
        assert revert_path.exists()
        assert verify_path.exists()

        context = {
            "project": "demo",
            "change": "widgets",
            "engine": "sqlite",
            "requires": ["roles", "users"],
            "conflicts": [],
            "tags": ["feature"],
        }

        expected_deploy = render_template(default_template_body("deploy"), context)
        expected_revert = render_template(default_template_body("revert"), context)
        expected_verify = render_template(default_template_body("verify"), context)

        assert deploy_path.read_text(encoding="utf-8") == expected_deploy
        assert revert_path.read_text(encoding="utf-8") == expected_revert
        assert verify_path.read_text(encoding="utf-8") == expected_verify

        plan_content = plan_path.read_text(encoding="utf-8")
        # Compact format: widgets [roles users] 2025-01-02T03:04:05Z Ada Lovelace <ada@example.com> # Adds widgets
        assert "widgets" in plan_content
        assert "[roles users]" in plan_content
        assert "2025-01-02T03:04:05Z" in plan_content
        assert "Ada Lovelace <ada@example.com>" in plan_content
        assert "# Adds widgets" in plan_content


def test_add_rejects_duplicate_change(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    timestamp = datetime(2024, 5, 6, 7, 8, 9, tzinfo=timezone.utc)
    monkeypatch.setattr(add_module, "_utcnow", lambda: timestamp)
    monkeypatch.setenv("SQLITCH_USER_NAME", "Grace Hopper")

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        existing_change = Change.create(
            name="widgets",
            script_paths={
                "deploy": (temp_dir / "deploy/existing.sql"),
                "revert": (temp_dir / "revert/existing.sql"),
                "verify": (temp_dir / "verify/existing.sql"),
            },
            planner="Existing Planner",
            planned_at=datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc),
        )
        _write_plan(plan_path, (existing_change,))
        original_content = plan_path.read_text(encoding="utf-8")

        result = runner.invoke(main, ["add", "widgets"])

        assert result.exit_code != 0
        assert 'Change "widgets" already exists in plan' in result.stderr
        assert plan_path.read_text(encoding="utf-8") == original_content

        expected_deploy = Path("deploy/20240506070809_widgets.sql")
        assert not expected_deploy.exists()


def test_add_uses_explicit_plan_override(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    timestamp = datetime(2025, 7, 8, 9, 10, 11, tzinfo=timezone.utc)
    monkeypatch.setattr(add_module, "_utcnow", lambda: timestamp)
    monkeypatch.setenv("SQLITCH_USER_NAME", "Katherine Johnson")
    monkeypatch.setenv("SQLITCH_USER_EMAIL", "kjohnson@example.com")

    # Mock system functions to prevent system name from taking precedence
    monkeypatch.setattr("os.getlogin", lambda: "test")
    try:
        import collections
        import pwd

        MockPwRecord = collections.namedtuple("MockPwRecord", ["pw_name", "pw_gecos"])
        monkeypatch.setattr("pwd.getpwuid", lambda uid: MockPwRecord(pw_name="test", pw_gecos=""))
    except ImportError:
        pass

    with isolated_test_context(runner) as (runner, temp_dir):
        override_plan = Path("custom.plan")
        _write_plan(override_plan)

        result = runner.invoke(main, ["--plan-file", str(override_plan), "add", "reports"])

        assert result.exit_code == 0, result.stderr
        assert not (temp_dir / "sqlitch.plan").exists()

        plan_content = override_plan.read_text(encoding="utf-8")
        # Compact format: reports 2025-07-08T09:10:11Z Katherine Johnson <kjohnson@example.com>
        assert (
            "reports 2025-07-08T09:10:11Z Katherine Johnson <kjohnson@example.com>" in plan_content
        )


def test_add_honours_project_templates(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    timestamp = datetime(2025, 9, 10, 11, 12, 13, tzinfo=timezone.utc)
    monkeypatch.setattr(add_module, "_utcnow", lambda: timestamp)
    monkeypatch.setenv("SQLITCH_USER_NAME", "Custom User")

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _write_plan(plan_path)

        templates_root = Path("etc/templates")
        (templates_root / "deploy").mkdir(parents=True)
        (templates_root / "revert").mkdir(parents=True)
        (templates_root / "verify").mkdir(parents=True)

        (templates_root / "deploy" / "sqlite.tmpl").write_text(
            "-- Custom deploy [% change %] for [% project %]\n",
            encoding="utf-8",
        )
        (templates_root / "revert" / "sqlite.tmpl").write_text(
            "-- Custom revert [% change %]\n",
            encoding="utf-8",
        )
        (templates_root / "verify" / "sqlite.tmpl").write_text(
            "-- Custom verify [% change %]\n",
            encoding="utf-8",
        )

        result = runner.invoke(main, ["add", "widgets"])

        assert result.exit_code == 0, result.stderr
        deploy_content = (temp_dir / "deploy/widgets.sql").read_text(encoding="utf-8")
        revert_content = (temp_dir / "revert/widgets.sql").read_text(encoding="utf-8")
        verify_content = (temp_dir / "verify/widgets.sql").read_text(encoding="utf-8")

        assert deploy_content == "-- Custom deploy widgets for demo\n"
        assert revert_content == "-- Custom revert widgets\n"
        assert verify_content == "-- Custom verify widgets\n"


def test_add_template_override_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    timestamp = datetime(2025, 11, 1, 2, 3, 4, tzinfo=timezone.utc)
    monkeypatch.setattr(add_module, "_utcnow", lambda: timestamp)

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _write_plan(plan_path)

        templates_root = Path("etc/templates")
        (templates_root / "deploy").mkdir(parents=True)
        (templates_root / "revert").mkdir(parents=True)
        (templates_root / "verify").mkdir(parents=True)

        (templates_root / "deploy" / "custom.tmpl").write_text(
            "deploy [% change %]\n", encoding="utf-8"
        )
        (templates_root / "revert" / "custom.tmpl").write_text(
            "revert [% change %]\n", encoding="utf-8"
        )
        (templates_root / "verify" / "custom.tmpl").write_text(
            "verify [% change %]\n", encoding="utf-8"
        )

        result = runner.invoke(main, ["add", "widgets", "--template", "custom"])

        assert result.exit_code == 0, result.stderr
        assert (temp_dir / "deploy/widgets.sql").read_text(encoding="utf-8") == "deploy widgets\n"
        assert (temp_dir / "revert/widgets.sql").read_text(encoding="utf-8") == "revert widgets\n"
        assert (temp_dir / "verify/widgets.sql").read_text(encoding="utf-8") == "verify widgets\n"


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_add_contract.py)
# =============================================================================


class TestAddCommandContract:
    """Contract tests for 'sqlitch add' command signature and behavior."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # CC-ADD-001: Required change name enforcement
    def test_add_requires_change_name(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' without arguments exits with code 2.

        Contract: CC-ADD-001
        Perl behavior: Missing required argument should exit 2
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["add"])

            assert result.exit_code == 2, (
                f"Expected exit code 2 for missing change_name, got {result.exit_code}. "
                f"Output: {result.output}"
            )
            assert (
                "change_name" in result.output.lower() or "missing" in result.output.lower()
            ), f"Error message should mention missing change_name. Got: {result.output}"

    # CC-ADD-002: Valid change name acceptance
    def test_add_accepts_valid_change_name(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add my_change' accepts the change name.

        Contract: CC-ADD-002
        Perl behavior: Should accept valid change name without parsing error
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            # Note: This will fail if not in a SQLitch project, but should NOT
            # fail with a parsing/argument error (exit code 2)
            result = runner.invoke(main, ["add", "my_test_change"])

            # Should not be exit code 2 (parsing/argument error)
            assert result.exit_code != 2, (
                f"Should accept change name without argument parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

            # Exit code might be 0 (success) or 1 (implementation error like "not in project")
            # but NOT 2 (argument parsing error)
            assert result.exit_code in [
                0,
                1,
            ], f"Expected exit code 0 or 1, got {result.exit_code}. Output: {result.output}"

    # CC-ADD-003: Optional note parameter
    def test_add_accepts_note_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --note option.

        Contract: CC-ADD-003
        Perl behavior: --note is an optional parameter that should be accepted
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["add", "my_change", "--note", "Test note"])

            # Should not fail with "no such option" error (exit code 2)
            assert result.exit_code != 2 or "no such option" not in result.output.lower(), (
                f"Should accept --note option. Exit code: {result.exit_code}, "
                f"Output: {result.output}"
            )

    def test_add_accepts_requires_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --requires option.

        Perl behavior: --requires specifies dependencies
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["add", "my_change", "--requires", "other_change"])

            assert result.exit_code != 2 or "no such option" not in result.output.lower(), (
                f"Should accept --requires option. Exit code: {result.exit_code}, "
                f"Output: {result.output}"
            )

    def test_add_accepts_conflicts_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --conflicts option.

        Perl behavior: --conflicts specifies conflicting changes
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["add", "my_change", "--conflicts", "other_change"])

            assert result.exit_code != 2 or "no such option" not in result.output.lower(), (
                f"Should accept --conflicts option. Exit code: {result.exit_code}, "
                f"Output: {result.output}"
            )


class TestAddGlobalContracts:
    """Test global contracts (GC-001, GC-002) for 'add' command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # GC-001: Help flag support
    def test_add_help_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add --help' displays help and exits 0.

        Contract: GC-001
        Global contract: All commands must support --help
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["add", "--help"])

            assert result.exit_code == 0, (
                f"Expected exit code 0 for --help, got {result.exit_code}. "
                f"Output: {result.output}"
            )

            # Help output should contain key elements
            assert "add" in result.output.lower(), "Help should mention 'add' command"
            assert (
                "usage" in result.output.lower() or "synopsis" in result.output.lower()
            ), "Help should include usage/synopsis section"

            # Should mention the change_name argument
            assert (
                "change" in result.output.lower()
            ), "Help should describe the change_name argument"

    # GC-002: Global options recognition
    def test_add_accepts_quiet_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --quiet global option.

        Contract: GC-002
        Global contract: All commands must accept global options
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["add", "--quiet", "my_change"])

            # Should not fail with "no such option" error
            assert (
                "no such option" not in result.output.lower()
            ), f"Should accept --quiet option. Output: {result.output}"

            # Exit code should not be 2 (option parsing error)
            assert result.exit_code != 2, (
                f"Should accept --quiet without parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    def test_add_accepts_verbose_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --verbose global option.

        Contract: GC-002
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["add", "--verbose", "my_change"])

            assert (
                "no such option" not in result.output.lower()
            ), f"Should accept --verbose option. Output: {result.output}"
            assert result.exit_code != 2, (
                f"Should accept --verbose without parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    def test_add_accepts_chdir_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --chdir global option.

        Contract: GC-002
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["add", "--chdir", "/tmp", "my_change"])

            assert (
                "no such option" not in result.output.lower()
            ), f"Should accept --chdir option. Output: {result.output}"
            assert result.exit_code != 2, (
                f"Should accept --chdir without parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    def test_add_accepts_no_pager_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --no-pager global option.

        Contract: GC-002
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["add", "--no-pager", "my_change"])

            assert (
                "no such option" not in result.output.lower()
            ), f"Should accept --no-pager option. Output: {result.output}"
            assert result.exit_code != 2, (
                f"Should accept --no-pager without parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    # GC-005: Unknown option rejection
    def test_add_rejects_unknown_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' rejects unknown options with exit code 2.

        Contract: GC-005
        Global contract: Unknown options must be rejected
        """
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["add", "--nonexistent-option", "my_change"])

            assert result.exit_code == 2, (
                f"Expected exit code 2 for unknown option, got {result.exit_code}. "
                f"Output: {result.output}"
            )

            assert (
                "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
            ), f"Error message should mention unknown option. Got: {result.output}"
