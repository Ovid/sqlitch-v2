"""Functional tests for the add command.

These tests validate add command functionality following the Sqitch SQLite
tutorial workflows (lines 149-165).

Tests for T054: Add dependency validation
Tests for T055: Add command completion validation
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context

CLI_GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "support" / "golden" / "cli"


@pytest.fixture
def runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def initialized_project(runner):
    """Provide an initialized project with sqitch.conf and sqitch.plan."""
    with isolated_test_context(runner) as (runner, temp_dir):
        # Initialize project
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0, f"Init failed: {result.output}"
        yield Path(temp_dir)


class TestAddCreatesScripts:
    """Test T055: Add command creates script files correctly."""

    def test_creates_deploy_revert_verify_scripts(self, runner):
        """Add should create deploy, revert, and verify scripts."""
        with isolated_test_context(runner) as (runner, temp_dir):
            # Initialize project
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            # Add a change
            result = runner.invoke(main, ["add", "users", "-n", "Creates users table"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            # Verify scripts were created
            assert (temp_dir / "deploy/users.sql").exists(), "Should create deploy script"
            assert (temp_dir / "revert/users.sql").exists(), "Should create revert script"
            assert (temp_dir / "verify/users.sql").exists(), "Should create verify script"

    def test_script_contents_have_proper_headers(self, runner):
        """Add should create scripts with Sqitch-format headers."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            # Check deploy script has header
            deploy_content = (temp_dir / "deploy/users.sql").read_text()
            assert (
                "-- Deploy flipr:users to sqlite" in deploy_content
            ), "Deploy script should have Sqitch header"

            # Check revert script has header
            revert_content = (temp_dir / "revert/users.sql").read_text()
            assert (
                "-- Revert flipr:users from sqlite" in revert_content
            ), "Revert script should have Sqitch header"

            # Check verify script has header
            verify_content = (temp_dir / "verify/users.sql").read_text()
            assert (
                "-- Verify flipr:users on sqlite" in verify_content
            ), "Verify script should have Sqitch header"

    def test_adds_change_to_plan(self, runner):
        """Add should append the change to sqitch.plan."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users", "-n", "Creates users table"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            # Verify plan was updated
            plan_content = (temp_dir / "sqitch.plan").read_text()
            assert "users " in plan_content, "Plan should contain change name"
            assert "Creates users table" in plan_content, "Plan should contain note"

    def test_outputs_creation_messages(self, runner):
        """Add should output messages about created files."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users"])

            assert result.exit_code == 0, f"Add failed: {result.output}"
            assert "Created deploy/users.sql" in result.output, "Should report deploy creation"
            assert "Created revert/users.sql" in result.output, "Should report revert creation"
            assert "Created verify/users.sql" in result.output, "Should report verify creation"
            assert 'Added "users" to sqitch.plan' in result.output, "Should report plan update"

    def test_quiet_mode_suppresses_output(self, runner):
        """Add with --quiet should suppress informational messages."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            # --quiet is a global option and must come before subcommand
            result = runner.invoke(main, ["--quiet", "add", "users"])

            assert result.exit_code == 0, f"Add --quiet failed: {result.output}"
            assert (
                result.output == "" or result.output.strip() == ""
            ), "Quiet mode should suppress output"


class TestAddChangeNaming:
    """Test T055: Add command handles change names correctly."""

    def test_slugifies_change_name_for_filenames(self, runner):
        """Add should create filename-safe slugs from change names."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users-table", "-n", "User management"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            # Should use slug for filenames
            assert Path(
                "deploy/users-table.sql"
            ).exists(), "Should create deploy script with slugified name"

    def test_preserves_original_name_in_plan(self, runner):
        """Add should preserve original change name in plan."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users-table"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            plan_content = (temp_dir / "sqitch.plan").read_text()
            assert "users-table" in plan_content, "Plan should use original change name"


class TestAddDependencies:
    """Test T054: Add command validates dependencies."""

    def test_accepts_valid_requires_dependency(self, runner):
        """Add should accept --requires for existing changes."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            # Add first change
            runner.invoke(main, ["add", "users"])

            # Add second change that requires first
            result = runner.invoke(main, ["add", "posts", "--requires", "users"])

            # Note: Current implementation may not validate dependencies
            # This test documents expected behavior for T054
            assert result.exit_code == 0, f"Add with valid --requires failed: {result.output}"

    def test_accepts_multiple_dependencies(self, runner):
        """Add should accept multiple --requires flags."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            runner.invoke(main, ["add", "users"])
            runner.invoke(main, ["add", "roles"])

            # Add change requiring both
            result = runner.invoke(
                main, ["add", "user_roles", "--requires", "users", "--requires", "roles"]
            )

            assert result.exit_code == 0, f"Add with multiple --requires failed: {result.output}"


class TestAddErrorHandling:
    """Test T055: Add command error handling."""

    def test_fails_if_plan_missing(self, runner):
        """Add should fail with clear error if no plan exists."""
        with isolated_test_context(runner) as (runner, temp_dir):
            # Don't initialize - no plan exists
            result = runner.invoke(main, ["add", "users"])

            assert result.exit_code != 0, "Should fail without plan"
            assert (
                "plan" in result.output.lower() or "init" in result.output.lower()
            ), "Should mention missing plan or suggest init"

    def test_fails_if_change_already_exists(self, runner):
        """Add should fail if change name already exists in plan."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            runner.invoke(main, ["add", "users"])

            # Try to add the same change again
            result = runner.invoke(main, ["add", "users"])

            assert result.exit_code != 0, "Should fail for duplicate change name"
            assert (
                "already exists" in result.output or "exists" in result.output.lower()
            ), "Should report that change already exists"

    def test_fails_if_script_already_exists(self, runner):
        """Add should fail if script file already exists."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            # Create a deploy script manually
            (temp_dir / "deploy").mkdir(parents=True, exist_ok=True)
            (temp_dir / "deploy/users.sql").write_text("-- Existing script\n")

            # Try to add change with same name
            result = runner.invoke(main, ["add", "users"])

            assert result.exit_code != 0, "Should fail if script exists"
            assert (
                "already exists" in result.output or "exists" in result.output.lower()
            ), "Should report that script already exists"


class TestAddWithNote:
    """Test T055: Add command with notes."""

    def test_includes_note_in_plan(self, runner):
        """Add with -n should include note in plan."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users", "-n", "Creates users table"])

            assert result.exit_code == 0, f"Add with note failed: {result.output}"

            plan_content = (temp_dir / "sqitch.plan").read_text()
            assert "Creates users table" in plan_content, "Plan should include the note"

    def test_note_with_special_characters(self, runner):
        """Add should handle notes with special characters."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            note = "User's table: creates & manages users"
            result = runner.invoke(main, ["add", "users", "-n", note])

            assert result.exit_code == 0, f"Add with special chars failed: {result.output}"

            plan_content = (temp_dir / "sqitch.plan").read_text()
            # Note should be in plan (exact format may vary)
            assert (
                "users" in plan_content and "User" in plan_content
            ), "Plan should include change with note"


class TestAddTutorialScenario:
    """Test T055: Add command as used in Sqitch tutorial (lines 149-165)."""

    def test_tutorial_add_users_change(self, runner):
        """Replicate tutorial: add users change."""
        with isolated_test_context(runner) as (runner, temp_dir):
            # Tutorial step 1: Initialize
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            # Tutorial step 2: Add users change
            result = runner.invoke(
                main, ["add", "users", "-n", "Creates table to track our users."]
            )

            assert result.exit_code == 0, f"Tutorial add failed: {result.output}"

            # Verify all expected files exist
            assert (temp_dir / "deploy/users.sql").exists()
            assert (temp_dir / "revert/users.sql").exists()
            assert (temp_dir / "verify/users.sql").exists()

            # Verify plan updated
            plan_content = (temp_dir / "sqitch.plan").read_text()
            assert "users " in plan_content
            assert "Creates table to track our users" in plan_content

    def test_tutorial_sequence_multiple_changes(self, runner):
        """Replicate tutorial: add multiple related changes."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            # Add users table
            result1 = runner.invoke(main, ["add", "users"])
            assert result1.exit_code == 0

            # Add posts table (could depend on users)
            result2 = runner.invoke(main, ["add", "posts", "--requires", "users"])
            assert result2.exit_code == 0

            # Verify both in plan
            plan_content = (temp_dir / "sqitch.plan").read_text()
            assert "users" in plan_content
            assert "posts" in plan_content

            # Verify all scripts created
            assert (temp_dir / "deploy/posts.sql").exists()
            assert (temp_dir / "revert/posts.sql").exists()
            assert (temp_dir / "verify/posts.sql").exists()


class TestAddPlanFormatting:
    """Test T010b: Add command writes plan entries in compact format."""

    def test_plan_entries_use_compact_format(self, runner):
        """Plan should not include verbose Sqitch "change" statements."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            result = runner.invoke(main, ["add", "users", "-n", "Adds users table"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            plan_content = (temp_dir / "sqitch.plan").read_text(encoding="utf-8")
            data_lines = [
                line for line in plan_content.splitlines() if line and not line.startswith("%")
            ]

            assert data_lines, "Plan should include at least one entry"
            assert all(
                not line.lower().startswith("change ") for line in data_lines
            ), "Plan entries must use compact format without 'change' prefix"

    def test_plan_dependency_serialization_matches_compact_format(self, runner):
        """Dependencies should be serialized inline inside brackets."""
        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            first = runner.invoke(main, ["add", "users"])
            assert first.exit_code == 0, f"Initial add failed: {first.output}"

            second = runner.invoke(
                main,
                ["add", "flips", "--requires", "users", "-n", "Adds flips table"],
            )

            assert second.exit_code == 0, f"Second add failed: {second.output}"

            plan_content = (temp_dir / "sqitch.plan").read_text(encoding="utf-8")

            assert (
                "flips [users]" in plan_content
            ), "Plan entry should embed dependencies in compact bracket syntax"


class TestAddOptionParity:
    """Guard Sqitch parity for add command option combinations (T010e)."""

    def test_requires_conflicts_note_output_matches_golden(self, runner):
        """Combined options should emit Sqitch-identical CLI output and plan entries."""

        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            result = runner.invoke(
                main,
                [
                    "add",
                    "flips",
                    "--requires",
                    "users",
                    "--conflicts",
                    "legacy",
                    "--note",
                    "Adds flips table",
                ],
            )

            assert result.exit_code == 0, f"Add failed: {result.output}"

            expected_output = (
                CLI_GOLDEN_ROOT / "add_requires_conflicts_note_output.txt"
            ).read_text(encoding="utf-8")
            assert result.output == expected_output

            plan_content = (temp_dir / "sqitch.plan").read_text(encoding="utf-8")
            assert "flips [users]" in plan_content
            assert "# Adds flips table" in plan_content

    def test_requires_conflicts_render_template_sections(self, runner):
        """Template should include requires and conflicts annotations when provided."""

        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            runner.invoke(
                main,
                [
                    "add",
                    "flips",
                    "--requires",
                    "users",
                    "--conflicts",
                    "legacy",
                ],
            )

            deploy_content = (temp_dir / "deploy/flips.sql").read_text(encoding="utf-8")
            assert "-- requires: users" in deploy_content
            assert "-- conflicts: legacy" in deploy_content

    def test_quiet_mode_still_updates_plan(self, runner):
        """Quiet mode should suppress output but still append to the plan."""

        with isolated_test_context(runner) as (runner, temp_dir):
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            result = runner.invoke(main, ["--quiet", "add", "users"])

            assert result.exit_code == 0, f"Add --quiet failed: {result.output}"
            assert result.output.strip() == ""

            plan_content = (temp_dir / "sqitch.plan").read_text(encoding="utf-8")
            assert "users " in plan_content


class TestAddHelpers:
    """Unit coverage for helper utilities in sqlitch.cli.commands.add.

    Merged from tests/cli/test_add_helpers.py during Phase 3.7c consolidation.
    """

    def test_resolve_planner_prioritises_sqlitch_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that SQLITCH_* env vars work (backward compatibility)."""
        from sqlitch.utils.identity import resolve_planner_identity

        env = {
            "SQLITCH_USER_NAME": "Ada",
            "SQLITCH_USER_EMAIL": "ada@example.com",
            "USER": "fallback",
        }

        # Mock system functions to prevent real system lookups
        monkeypatch.setattr("os.getlogin", lambda: "fallback")
        try:
            import collections
            import pwd

            MockPwRecord = collections.namedtuple("MockPwRecord", ["pw_name", "pw_gecos"])
            monkeypatch.setattr(
                "pwd.getpwuid", lambda uid: MockPwRecord(pw_name="fallback", pw_gecos="")
            )
        except ImportError:
            pass

        assert resolve_planner_identity(env, None) == "Ada <ada@example.com>"

    def test_resolve_planner_fallbacks_when_no_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that email is always synthesized when not provided."""
        from sqlitch.utils.identity import resolve_planner_identity

        env = {
            "GIT_AUTHOR_NAME": "Ada",
            "USERNAME": "backup",
        }

        # Mock system functions to avoid using real user info
        monkeypatch.setattr("socket.gethostname", lambda: "testhost")
        monkeypatch.setattr("os.getlogin", lambda: "backup")

        # Mock pwd module if it exists (Unix/macOS)
        try:
            import collections
            import pwd

            MockPwRecord = collections.namedtuple("MockPwRecord", ["pw_name", "pw_gecos"])
            monkeypatch.setattr(
                "pwd.getpwuid", lambda uid: MockPwRecord(pw_name="backup", pw_gecos="")
            )
        except ImportError:
            pass

        # Should synthesize email
        result = resolve_planner_identity(env, None)
        assert result == "Ada <backup@testhost>"

    def test_resolve_planner_from_config(self) -> None:
        """Test that config file user.name and user.email are used."""
        from sqlitch.config.loader import ConfigProfile
        from sqlitch.utils.identity import resolve_planner_identity

        # Mock config with user.name and user.email
        config = ConfigProfile(
            root_dir=Path("/tmp"),
            files=(),
            settings={
                "user": {
                    "name": "Test User",
                    "email": "test@example.com",
                }
            },
            active_engine=None,
        )

        env = {}  # No env vars

        result = resolve_planner_identity(env, config)
        assert result == "Test User <test@example.com>"

    def test_resolve_script_path_prefers_absolute(self, tmp_path: Path) -> None:
        """Test script path resolution with absolute path."""
        from sqlitch.cli.commands import add as add_module

        default = Path("deploy/default.sql")
        absolute = tmp_path / "custom.sql"

        resolved = add_module._resolve_script_path(tmp_path, str(absolute), default)

        assert resolved == absolute

    def test_resolve_script_path_coerces_relative(self, tmp_path: Path) -> None:
        """Test script path resolution with relative path."""
        from sqlitch.cli.commands import add as add_module

        default = Path("deploy/default.sql")

        resolved = add_module._resolve_script_path(tmp_path, "scripts/run.sql", default)

        assert resolved == tmp_path / "scripts" / "run.sql"

    def test_ensure_script_path_rejects_existing(self, tmp_path: Path) -> None:
        """Test that existing script paths are rejected."""
        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import add as add_module

        target = tmp_path / "deploy" / "exists.sql"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()

        with pytest.raises(CommandError, match="already exists"):
            add_module._ensure_script_path(target)

    def test_format_display_path_relative(self, tmp_path: Path) -> None:
        """Test display path formatting for relative paths."""
        from sqlitch.cli.commands import add as add_module

        target = tmp_path / "deploy" / "script.sql"

        assert add_module._format_display_path(target, tmp_path) == "deploy/script.sql"

    def test_format_display_path_outside_root(self, tmp_path: Path) -> None:
        """Test display path formatting for paths outside root."""
        import os

        from sqlitch.cli.commands import add as add_module

        other = tmp_path.parent / "external.sql"
        other.touch()

        expected = os.path.relpath(other, tmp_path).replace(os.sep, "/")
        assert add_module._format_display_path(other, tmp_path) == expected

    def test_discover_template_directories_orders_and_deduplicates(self, tmp_path: Path) -> None:
        """Test template directory discovery ordering and deduplication."""
        from sqlitch.cli.commands import add as add_module

        config_root = tmp_path / "etc"

        directories = add_module._discover_template_directories(tmp_path, config_root)

        assert directories[0] == tmp_path
        assert directories[1] == tmp_path / "sqitch"
        assert config_root in directories
        assert (config_root / "sqitch") in directories
        # Ensure no duplicates appear
        assert len(directories) == len(set(directories))

    def test_resolve_template_content_prefers_absolute_override(self, tmp_path: Path) -> None:
        """Test template content resolution with absolute override."""
        from sqlitch.cli.commands import add as add_module

        template = tmp_path / "custom.sql"
        template.write_text("-- override", encoding="utf-8")

        content = add_module._resolve_template_content(
            kind="deploy",
            engine="sqlite",
            template_dirs=(tmp_path,),
            template_name=str(template),
        )

        assert content == "-- override"

    def test_resolve_template_content_absolute_missing(self, tmp_path: Path) -> None:
        """Test template content resolution with missing absolute path."""
        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import add as add_module

        missing = tmp_path / "missing.sql"

        with pytest.raises(CommandError, match="does not exist"):
            add_module._resolve_template_content(
                kind="deploy",
                engine="sqlite",
                template_dirs=(tmp_path,),
                template_name=str(missing),
            )

    def test_resolve_template_content_raises_when_named_template_not_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test template content resolution when named template is not found."""
        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import add as add_module

        monkeypatch.setattr(add_module, "resolve_template_path", lambda **_: None)

        with pytest.raises(CommandError, match="could not be located"):
            add_module._resolve_template_content(
                kind="deploy",
                engine="sqlite",
                template_dirs=(tmp_path,),
                template_name="custom",
            )

    def test_resolve_template_content_uses_discovered_template(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test template content resolution with discovered template."""
        from sqlitch.cli.commands import add as add_module

        template = tmp_path / "custom.tmpl"
        template.write_text("-- template", encoding="utf-8")

        monkeypatch.setattr(add_module, "resolve_template_path", lambda **_: template)

        content = add_module._resolve_template_content(
            kind="deploy",
            engine="sqlite",
            template_dirs=(tmp_path,),
            template_name="custom",
        )

        assert content == "-- template"

    def test_resolve_template_content_falls_back_to_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test template content resolution fallback to default."""
        from sqlitch.cli.commands import add as add_module
        from sqlitch.utils.templates import default_template_body

        monkeypatch.setattr(add_module, "resolve_template_path", lambda **_: None)

        content = add_module._resolve_template_content(
            kind="deploy",
            engine="sqlite",
            template_dirs=(tmp_path,),
            template_name=None,
        )

        assert content == default_template_body("deploy")
