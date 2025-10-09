"""Functional tests for the add command.

These tests validate add command functionality following the Sqitch SQLite
tutorial workflows (lines 149-165).

Tests for T054: Add dependency validation
Tests for T055: Add command completion validation
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner
from pathlib import Path

from sqlitch.cli.main import main

CLI_GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "support" / "golden" / "cli"


@pytest.fixture
def runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def initialized_project(runner):
    """Provide an initialized project with sqitch.conf and sqitch.plan."""
    with runner.isolated_filesystem() as temp_dir:
        # Initialize project
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0, f"Init failed: {result.output}"
        yield Path(temp_dir)


class TestAddCreatesScripts:
    """Test T055: Add command creates script files correctly."""

    def test_creates_deploy_revert_verify_scripts(self, runner):
        """Add should create deploy, revert, and verify scripts."""
        with runner.isolated_filesystem():
            # Initialize project
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            # Add a change
            result = runner.invoke(main, ["add", "users", "-n", "Creates users table"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            # Verify scripts were created
            assert Path("deploy/users.sql").exists(), "Should create deploy script"
            assert Path("revert/users.sql").exists(), "Should create revert script"
            assert Path("verify/users.sql").exists(), "Should create verify script"

    def test_script_contents_have_proper_headers(self, runner):
        """Add should create scripts with Sqitch-format headers."""
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            # Check deploy script has header
            deploy_content = Path("deploy/users.sql").read_text()
            assert (
                "-- Deploy flipr:users to sqlite" in deploy_content
            ), "Deploy script should have Sqitch header"

            # Check revert script has header
            revert_content = Path("revert/users.sql").read_text()
            assert (
                "-- Revert flipr:users from sqlite" in revert_content
            ), "Revert script should have Sqitch header"

            # Check verify script has header
            verify_content = Path("verify/users.sql").read_text()
            assert (
                "-- Verify flipr:users on sqlite" in verify_content
            ), "Verify script should have Sqitch header"

    def test_adds_change_to_plan(self, runner):
        """Add should append the change to sqitch.plan."""
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users", "-n", "Creates users table"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            # Verify plan was updated
            plan_content = Path("sqitch.plan").read_text()
            assert "users " in plan_content, "Plan should contain change name"
            assert "Creates users table" in plan_content, "Plan should contain note"

    def test_outputs_creation_messages(self, runner):
        """Add should output messages about created files."""
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users"])

            assert result.exit_code == 0, f"Add failed: {result.output}"
            assert "Created deploy/users.sql" in result.output, "Should report deploy creation"
            assert "Created revert/users.sql" in result.output, "Should report revert creation"
            assert "Created verify/users.sql" in result.output, "Should report verify creation"
            assert 'Added "users" to sqitch.plan' in result.output, "Should report plan update"

    def test_quiet_mode_suppresses_output(self, runner):
        """Add with --quiet should suppress informational messages."""
        with runner.isolated_filesystem():
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
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users-table", "-n", "User management"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            # Should use slug for filenames
            assert Path(
                "deploy/users-table.sql"
            ).exists(), "Should create deploy script with slugified name"

    def test_preserves_original_name_in_plan(self, runner):
        """Add should preserve original change name in plan."""
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users-table"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            plan_content = Path("sqitch.plan").read_text()
            assert "users-table" in plan_content, "Plan should use original change name"


class TestAddDependencies:
    """Test T054: Add command validates dependencies."""

    def test_accepts_valid_requires_dependency(self, runner):
        """Add should accept --requires for existing changes."""
        with runner.isolated_filesystem():
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
        with runner.isolated_filesystem():
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
        with runner.isolated_filesystem():
            # Don't initialize - no plan exists
            result = runner.invoke(main, ["add", "users"])

            assert result.exit_code != 0, "Should fail without plan"
            assert (
                "plan" in result.output.lower() or "init" in result.output.lower()
            ), "Should mention missing plan or suggest init"

    def test_fails_if_change_already_exists(self, runner):
        """Add should fail if change name already exists in plan."""
        with runner.isolated_filesystem():
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
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            # Create a deploy script manually
            Path("deploy").mkdir(parents=True, exist_ok=True)
            Path("deploy/users.sql").write_text("-- Existing script\n")

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
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            result = runner.invoke(main, ["add", "users", "-n", "Creates users table"])

            assert result.exit_code == 0, f"Add with note failed: {result.output}"

            plan_content = Path("sqitch.plan").read_text()
            assert "Creates users table" in plan_content, "Plan should include the note"

    def test_note_with_special_characters(self, runner):
        """Add should handle notes with special characters."""
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            note = "User's table: creates & manages users"
            result = runner.invoke(main, ["add", "users", "-n", note])

            assert result.exit_code == 0, f"Add with special chars failed: {result.output}"

            plan_content = Path("sqitch.plan").read_text()
            # Note should be in plan (exact format may vary)
            assert (
                "users" in plan_content and "User" in plan_content
            ), "Plan should include change with note"


class TestAddTutorialScenario:
    """Test T055: Add command as used in Sqitch tutorial (lines 149-165)."""

    def test_tutorial_add_users_change(self, runner):
        """Replicate tutorial: add users change."""
        with runner.isolated_filesystem():
            # Tutorial step 1: Initialize
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            # Tutorial step 2: Add users change
            result = runner.invoke(
                main, ["add", "users", "-n", "Creates table to track our users."]
            )

            assert result.exit_code == 0, f"Tutorial add failed: {result.output}"

            # Verify all expected files exist
            assert Path("deploy/users.sql").exists()
            assert Path("revert/users.sql").exists()
            assert Path("verify/users.sql").exists()

            # Verify plan updated
            plan_content = Path("sqitch.plan").read_text()
            assert "users " in plan_content
            assert "Creates table to track our users" in plan_content

    def test_tutorial_sequence_multiple_changes(self, runner):
        """Replicate tutorial: add multiple related changes."""
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            # Add users table
            result1 = runner.invoke(main, ["add", "users"])
            assert result1.exit_code == 0

            # Add posts table (could depend on users)
            result2 = runner.invoke(main, ["add", "posts", "--requires", "users"])
            assert result2.exit_code == 0

            # Verify both in plan
            plan_content = Path("sqitch.plan").read_text()
            assert "users" in plan_content
            assert "posts" in plan_content

            # Verify all scripts created
            assert Path("deploy/posts.sql").exists()
            assert Path("revert/posts.sql").exists()
            assert Path("verify/posts.sql").exists()


class TestAddPlanFormatting:
    """Test T010b: Add command writes plan entries in compact format."""

    def test_plan_entries_use_compact_format(self, runner):
        """Plan should not include verbose Sqitch "change" statements."""
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            result = runner.invoke(main, ["add", "users", "-n", "Adds users table"])

            assert result.exit_code == 0, f"Add failed: {result.output}"

            plan_content = Path("sqitch.plan").read_text(encoding="utf-8")
            data_lines = [
                line for line in plan_content.splitlines() if line and not line.startswith("%")
            ]

            assert data_lines, "Plan should include at least one entry"
            assert all(
                not line.lower().startswith("change ") for line in data_lines
            ), "Plan entries must use compact format without 'change' prefix"

    def test_plan_dependency_serialization_matches_compact_format(self, runner):
        """Dependencies should be serialized inline inside brackets."""
        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            first = runner.invoke(main, ["add", "users"])
            assert first.exit_code == 0, f"Initial add failed: {first.output}"

            second = runner.invoke(
                main,
                ["add", "flips", "--requires", "users", "-n", "Adds flips table"],
            )

            assert second.exit_code == 0, f"Second add failed: {second.output}"

            plan_content = Path("sqitch.plan").read_text(encoding="utf-8")

            assert (
                "flips [users]" in plan_content
            ), "Plan entry should embed dependencies in compact bracket syntax"


class TestAddOptionParity:
    """Guard Sqitch parity for add command option combinations (T010e)."""

    def test_requires_conflicts_note_output_matches_golden(self, runner):
        """Combined options should emit Sqitch-identical CLI output and plan entries."""

        with runner.isolated_filesystem():
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

            plan_content = Path("sqitch.plan").read_text(encoding="utf-8")
            assert "flips [users]" in plan_content
            assert "# Adds flips table" in plan_content

    def test_requires_conflicts_render_template_sections(self, runner):
        """Template should include requires and conflicts annotations when provided."""

        with runner.isolated_filesystem():
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

            deploy_content = Path("deploy/flips.sql").read_text(encoding="utf-8")
            assert "-- requires: users" in deploy_content
            assert "-- conflicts: legacy" in deploy_content

    def test_quiet_mode_still_updates_plan(self, runner):
        """Quiet mode should suppress output but still append to the plan."""

        with runner.isolated_filesystem():
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            result = runner.invoke(main, ["--quiet", "add", "users"])

            assert result.exit_code == 0, f"Add --quiet failed: {result.output}"
            assert result.output.strip() == ""

            plan_content = Path("sqitch.plan").read_text(encoding="utf-8")
            assert "users " in plan_content
