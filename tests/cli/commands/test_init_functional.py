"""Functional tests for the init command.

These tests validate that init creates proper files and directories with correct content,
following the Sqitch SQLite tutorial workflows (lines 66-82).

Tests for T051: Directory and file creation
Tests for T052: Engine validation
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


@pytest.fixture
def runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


class TestInitDirectoryCreation:
    """Test T051: Init creates sqitch.conf, sqitch.plan, and script directories."""

    def test_creates_sqitch_conf_with_engine(self, runner):
        """Init must create sqitch.conf with correct engine setting."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Verify sqitch.conf exists
            config_path = Path("sqitch.conf")
            assert config_path.exists(), "sqitch.conf was not created"

            # Verify engine setting
            config_content = config_path.read_text()
            assert "[core]" in config_content, "Missing [core] section"
            assert "engine = sqlite" in config_content, "Missing engine = sqlite setting"

    def test_creates_sqitch_plan_with_pragmas(self, runner):
        """Init must create sqitch.plan with project pragmas."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(
                main,
                [
                    "init",
                    "flipr",
                    "--engine",
                    "sqlite",
                    "--uri",
                    "https://github.com/sqitchers/sqitch-sqlite-intro/",
                ],
            )

            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Verify sqitch.plan exists
            plan_path = Path("sqitch.plan")
            assert plan_path.exists(), "sqitch.plan was not created"

            # Verify pragmas
            plan_content = plan_path.read_text()
            assert "%syntax-version=" in plan_content, "Missing %syntax-version pragma"
            assert "%project=flipr" in plan_content, "Missing %project pragma"
            assert (
                "%uri=https://github.com/sqitchers/sqitch-sqlite-intro/" in plan_content
            ), "Missing %uri pragma"

    def test_sqitch_conf_omits_core_uri(self, runner):
        """Init must not write core.uri entries even when --uri supplied."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(
                main,
                [
                    "init",
                    "flipr",
                    "--engine",
                    "sqlite",
                    "--uri",
                    "https://github.com/sqitchers/sqitch-sqlite-intro/",
                ],
            )

            assert result.exit_code == 0, f"Init failed: {result.output}"

            config_content = (temp_dir / "sqitch.conf").read_text()
            assert "core.uri" not in config_content
            assert "%core.uri" not in config_content

    def test_creates_script_directories(self, runner):
        """Init must create deploy/, revert/, and verify/ directories."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Verify directories exist
            deploy_dir = Path("deploy")
            revert_dir = Path("revert")
            verify_dir = Path("verify")

            assert deploy_dir.exists() and deploy_dir.is_dir(), "deploy/ directory not created"
            assert revert_dir.exists() and revert_dir.is_dir(), "revert/ directory not created"
            assert verify_dir.exists() and verify_dir.is_dir(), "verify/ directory not created"

    def test_directory_structure_matches_fr001_requirements(self, runner):
        """Init must create complete directory structure per FR-001."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Verify all required artifacts
            required_files = [
                (temp_dir / "sqitch.conf"),
                (temp_dir / "sqitch.plan"),
            ]
            required_dirs = [
                (temp_dir / "deploy"),
                (temp_dir / "revert"),
                (temp_dir / "verify"),
            ]

            for file_path in required_files:
                assert (
                    file_path.exists() and file_path.is_file()
                ), f"Required file {file_path} missing"

            for dir_path in required_dirs:
                assert (
                    dir_path.exists() and dir_path.is_dir()
                ), f"Required directory {dir_path}/ missing"

    def test_file_contents_match_sqitch_format(self, runner):
        """Init must create files with Sqitch-compatible format."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(
                main,
                [
                    "init",
                    "flipr",
                    "--engine",
                    "sqlite",
                    "--uri",
                    "https://github.com/sqitchers/sqitch-sqlite-intro/",
                ],
            )

            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Verify sqitch.conf format
            config_content = (temp_dir / "sqitch.conf").read_text()
            assert config_content.startswith("[core]"), "sqitch.conf must start with [core] section"
            assert "\tengine = sqlite" in config_content, "Engine setting must use tab indentation"

            # Verify sqitch.plan format
            plan_content = (temp_dir / "sqitch.plan").read_text()
            assert plan_content.startswith(
                "%syntax-version="
            ), "sqitch.plan must start with %syntax-version pragma"
            # Plan should end with blank line after pragmas
            assert plan_content.endswith("\n"), "sqitch.plan should end with newline"

    def test_engine_target_is_absent_without_flag(self, runner):
        """Init must not persist engine.target unless --target provided."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            assert result.exit_code == 0, f"Init failed: {result.output}"

            config_content = (temp_dir / "sqitch.conf").read_text()
            assert "\n\ttarget = " not in config_content

    def test_engine_target_written_when_flag_provided(self, runner):
        """Init must persist engine.target when explicit --target supplied."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(
                main,
                [
                    "init",
                    "flipr",
                    "--engine",
                    "sqlite",
                    "--target",
                    "db:sqlite:flipr.db",
                ],
            )

            assert result.exit_code == 0, f"Init failed: {result.output}"

            config_content = (temp_dir / "sqitch.conf").read_text()
            assert '[engine "sqlite"]' in config_content
            assert "target = db:sqlite:flipr.db" in config_content


class TestInitEngineValidation:
    """Test T052: Init validates engine exists in ENGINE_REGISTRY."""

    def test_validates_engine_in_registry(self, runner):
        """Init must accept valid engines from ENGINE_REGISTRY."""
        with isolated_test_context(runner) as (runner, temp_dir):
            # sqlite should be valid
            result = runner.invoke(main, ["init", "test", "--engine", "sqlite"])
            assert result.exit_code == 0, f"Valid engine 'sqlite' rejected: {result.output}"

    def test_fails_with_clear_error_for_invalid_engine(self, runner):
        """Init must fail with clear error message for invalid engine."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "test", "--engine", "notarealengine"])

            # Should fail (exit code 1 for user error)
            assert (
                result.exit_code == 1
            ), f"Should reject invalid engine, got exit {result.exit_code}"

            # Error message should mention the invalid engine
            assert (
                "notarealengine" in result.output.lower() or "unsupported" in result.output.lower()
            ), f"Error message should mention invalid engine: {result.output}"

    def test_defaults_to_sqlite_when_not_specified(self, runner):
        """Init must default to sqlite engine when --engine not provided."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "test"])

            assert result.exit_code == 0, f"Init without engine failed: {result.output}"

            # Verify sqlite is set as default
            config_content = (temp_dir / "sqitch.conf").read_text()
            assert "engine = sqlite" in config_content, "Should default to sqlite engine"


class TestInitOutputFormat:
    """Test that init output matches Sqitch format (for T053 validation)."""

    def test_outputs_creation_messages(self, runner):
        """Init should output 'Created' messages for each artifact."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Should mention created artifacts
            assert "Created sqitch.conf" in result.output, "Missing sqitch.conf creation message"
            assert "Created sqitch.plan" in result.output, "Missing sqitch.plan creation message"
            assert "Created deploy/" in result.output, "Missing deploy/ creation message"
            assert "Created revert/" in result.output, "Missing revert/ creation message"
            assert "Created verify/" in result.output, "Missing verify/ creation message"

    def test_quiet_mode_suppresses_output(self, runner):
        """Init with --quiet should suppress creation messages."""
        with isolated_test_context(runner) as (runner, temp_dir):
            # --quiet is a global option and must come before the subcommand
            result = runner.invoke(main, ["--quiet", "init", "flipr", "--engine", "sqlite"])

            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Output should be empty or minimal
            assert (
                len(result.output.strip()) == 0
            ), f"--quiet should suppress output, got: {result.output}"


class TestInitErrorHandling:
    """Test init error conditions."""

    def test_fails_if_sqitch_conf_exists(self, runner):
        """Init must fail if sqitch.conf already exists."""
        with isolated_test_context(runner) as (runner, temp_dir):
            # Create existing config
            (temp_dir / "sqitch.conf").write_text("[core]\n")

            result = runner.invoke(main, ["init", "test"])

            assert result.exit_code == 1, "Should fail when sqitch.conf exists"
            assert "sqitch.conf" in result.output.lower(), "Error should mention sqitch.conf"

    def test_fails_if_sqitch_plan_exists(self, runner):
        """Init must fail if sqitch.plan already exists."""
        with isolated_test_context(runner) as (runner, temp_dir):
            # Create existing plan
            (temp_dir / "sqitch.plan").write_text("%syntax-version=1.0.0\n")

            result = runner.invoke(main, ["init", "test"])

            assert result.exit_code == 1, "Should fail when sqitch.plan exists"
            assert "sqitch.plan" in result.output.lower(), "Error should mention sqitch.plan"

    def test_fails_if_deploy_directory_exists(self, runner):
        """Init must fail if deploy/ directory already exists."""
        with isolated_test_context(runner) as (runner, temp_dir):
            # Create existing directory
            (temp_dir / "deploy").mkdir()

            result = runner.invoke(main, ["init", "test"])

            assert result.exit_code == 1, "Should fail when deploy/ exists"
            assert "deploy" in result.output.lower(), "Error should mention deploy directory"


# Migrated from tests/regression/test_artifact_cleanup.py
@pytest.mark.skip(reason="Pending T035: artifact cleanup regression coverage")
def test_artifact_cleanup_guarantees() -> None:
    """Placeholder regression test for T035 - artifact cleanup guarantees.

    When implemented, this should test that SQLitch commands properly clean up
    temporary files, partial artifacts, and database connections after execution,
    especially in error scenarios. Should verify no leaked resources remain after
    init, add, deploy, revert, and other state-modifying operations.
    """
    ...
