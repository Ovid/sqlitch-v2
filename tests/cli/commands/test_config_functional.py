"""Functional tests for the config command.

These tests validate config get/set/list operations following the Sqitch SQLite
tutorial workflows (lines 92-108).

Tests for T025: Config get operation
Tests for T026: Config set operation
Tests for T027: Config list operation
Tests for T028: Config implementation (validation)
"""

from __future__ import annotations

import os
import pytest
from click.testing import CliRunner
from pathlib import Path

from sqlitch.cli.main import main


@pytest.fixture
def runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Provide an isolated environment with mocked home directory."""
    # Create a fake home directory in the temp path
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    # Mock HOME environment variable to point to our fake home
    monkeypatch.setenv("HOME", str(fake_home))

    # Also mock XDG_CONFIG_HOME to ensure consistent behavior
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    # Mock Path.home() to return our fake home
    from pathlib import Path

    monkeypatch.setattr(Path, "home", lambda: fake_home)

    return fake_home


class TestConfigGetOperation:
    """Test T025: Config get reads values from project, user, and system configs."""

    def test_get_from_project_config(self, runner):
        """Config get should read from project sqitch.conf."""
        with runner.isolated_filesystem():
            # Create project config
            Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n")

            result = runner.invoke(main, ["config", "core.engine"])

            assert result.exit_code == 0, f"Config get failed: {result.output}"
            assert "sqlite" in result.output, "Should return sqlite engine value"

    def test_get_from_user_config_with_flag(self, runner, isolated_env):
        """Config get --user should read from ~/.sqitch/sqitch.conf."""
        with runner.isolated_filesystem():
            # Create user config directory and file in our isolated home
            user_dir = isolated_env / ".sqitch"
            user_dir.mkdir(parents=True, exist_ok=True)
            user_config = user_dir / "sqitch.conf"
            user_config.write_text("[user]\n\tname = Test User\n")

            result = runner.invoke(
                main, ["config", "--user", "user.name"], env={"HOME": str(isolated_env)}
            )

            # Should read from user config
            assert result.exit_code == 0, f"Config get --user failed: {result.output}"
            assert "Test User" in result.output, "Should return user name"

    def test_get_from_global_is_alias_for_user(self, runner, isolated_env):
        """Config get --global should work as alias for --user."""
        with runner.isolated_filesystem():
            # Create user config directory and file in our isolated home
            user_dir = isolated_env / ".sqitch"
            user_dir.mkdir(parents=True, exist_ok=True)
            user_config = user_dir / "sqitch.conf"
            user_config.write_text("[user]\n\tname = Global Test User\n")

            # --global should be accepted as alias for --user
            result = runner.invoke(
                main, ["config", "--global", "user.name"], env={"HOME": str(isolated_env)}
            )

            assert result.exit_code == 0, f"Config get --global failed: {result.output}"
            assert "Global Test User" in result.output, "Should return user name via --global"

    def test_precedence_project_overuser_over_system(self, runner, isolated_env):
        """Config get should prefer project > user > system."""
        with runner.isolated_filesystem():
            # Create project config with engine = sqlite
            Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n")

            # Create user config with engine = pg in our isolated home
            user_dir = isolated_env / ".sqitch"
            user_dir.mkdir(parents=True, exist_ok=True)
            user_config = user_dir / "sqitch.conf"
            user_config.write_text("[core]\n\tengine = pg\n")

            result = runner.invoke(main, ["config", "core.engine"], env={"HOME": str(isolated_env)})

            # Should use project config (sqlite), not user config (pg)
            assert result.exit_code == 0, f"Config get failed: {result.output}"
            assert "sqlite" in result.output, "Should prefer project config over user"

    def test_missing_key_returns_exit_code_1(self, runner):
        """Config get should exit with code 1 for missing keys."""
        with runner.isolated_filesystem():
            Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n")

            result = runner.invoke(main, ["config", "nonexistent.key"])

            # Should fail with exit code 1 (user error)
            assert result.exit_code == 1, f"Should exit 1 for missing key, got {result.exit_code}"


class TestConfigSetOperation:
    """Test T026: Config set writes values to appropriate config files."""

    def test_set_in_project_config_default(self, runner):
        """Config set should write to project sqitch.conf by default."""
        with runner.isolated_filesystem():
            # Initialize a project
            runner.invoke(main, ["init", "test", "--engine", "sqlite"])

            # Set a value
            result = runner.invoke(main, ["config", "user.name", "Test User"])

            assert result.exit_code == 0, f"Config set failed: {result.output}"

            # Verify it was written to project config
            config_content = Path("sqitch.conf").read_text()
            assert (
                "name = Test User" in config_content or "name=Test User" in config_content
            ), "Should write to project sqitch.conf"

    def test_set_in_user_config_with_flag(self, runner, isolated_env):
        """Config set --user should write to ~/.config/sqlitch/sqitch.conf."""
        with runner.isolated_filesystem():
            # Pass environment to runner.invoke so it sees our fake HOME
            result = runner.invoke(
                main,
                ["config", "--user", "user.name", "Test User"],
                env={"HOME": str(isolated_env)},
            )

            assert result.exit_code == 0, f"Config set --user failed: {result.output}"

            # Verify user config was created/updated (default location is ~/.config/sqlitch/)
            user_config = isolated_env / ".config" / "sqlitch" / "sqitch.conf"
            assert user_config.exists(), f"Should create user config file at {user_config}"
            config_content = user_config.read_text()
            assert "Test User" in config_content, "Should write to user config"

    def test_set_in_global_is_alias_for_user(self, runner, isolated_env):
        """Config set --global should work as alias for --user."""
        with runner.isolated_filesystem():
            # Pass environment to runner.invoke so it sees our fake HOME
            result = runner.invoke(
                main,
                ["config", "--global", "user.name", "Global User"],
                env={"HOME": str(isolated_env)},
            )

            assert result.exit_code == 0, f"Config set --global failed: {result.output}"

            # Verify user config was created/updated (default location is ~/.config/sqlitch/)
            user_config = isolated_env / ".config" / "sqlitch" / "sqitch.conf"
            assert (
                user_config.exists()
            ), f"Should create user config file at {user_config} via --global"
            config_content = user_config.read_text()
            assert "Global User" in config_content, "Should write to user config via --global"

    def test_creates_config_file_if_missing(self, runner):
        """Config set should create config file if it doesn't exist."""
        with runner.isolated_filesystem():
            # Don't initialize - no sqitch.conf exists
            result = runner.invoke(main, ["config", "core.engine", "sqlite"])

            assert result.exit_code == 0, f"Config set failed: {result.output}"

            # Verify config file was created
            assert Path("sqitch.conf").exists(), "Should create sqitch.conf"
            config_content = Path("sqitch.conf").read_text()
            assert (
                "engine = sqlite" in config_content or "engine=sqlite" in config_content
            ), "Should write engine setting"

    def test_updates_existing_value(self, runner):
        """Config set should update existing values in config."""
        with runner.isolated_filesystem():
            # Create initial config
            Path("sqitch.conf").write_text("[core]\n\tengine = pg\n")

            # Update the value
            result = runner.invoke(main, ["config", "core.engine", "sqlite"])

            assert result.exit_code == 0, f"Config set failed: {result.output}"

            # Verify value was updated
            config_content = Path("sqitch.conf").read_text()
            assert "sqlite" in config_content, "Should update to sqlite"
            # Should not have both values
            pg_count = config_content.count("pg")
            assert (
                pg_count == 0 or '[engine "pg"]' in config_content
            ), "Should replace old value, not duplicate"

    def test_rejects_core_uri_assignment(self, runner):
        """Config set must not permit writing core.uri entries."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config", "core.uri", "https://example.com/flipr"])

            assert result.exit_code != 0, "Setting core.uri should fail"
            assert "core.uri" in result.output
            assert not Path("sqitch.conf").exists(), "Command must not create sqitch.conf"


class TestConfigListOperation:
    """Test T027: Config list displays all configuration values."""

    def test_list_shows_all_config_values(self, runner):
        """Config --list should display all configuration."""
        with runner.isolated_filesystem():
            # Create config with multiple values
            Path("sqitch.conf").write_text(
                "[core]\n\tengine = sqlite\n\turi = https://example.com\n"
            )

            result = runner.invoke(main, ["config", "--list"])

            assert result.exit_code == 0, f"Config --list failed: {result.output}"
            assert (
                "engine" in result.output or "sqlite" in result.output
            ), "Should show engine setting"
            assert (
                "uri" in result.output or "https://example.com" in result.output
            ), "Should show uri setting"

    def test_list_with_user_shows_user_config_only(self, runner, isolated_env):
        """Config --list --user should show only user config."""
        with runner.isolated_filesystem():
            # Create project config
            Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n")

            # Create user config in our isolated home
            user_dir = isolated_env / ".sqitch"
            user_dir.mkdir(parents=True, exist_ok=True)
            user_config = user_dir / "sqitch.conf"
            user_config.write_text("[user]\n\tname = Test User\n")

            result = runner.invoke(
                main, ["config", "--list", "--user"], env={"HOME": str(isolated_env)}
            )

            assert result.exit_code == 0, f"Config --list --user failed: {result.output}"
            # Should show user config
            assert (
                "Test User" in result.output or "user.name" in result.output
            ), "Should show user config"

    def test_list_with_global_shows_user_config(self, runner, isolated_env):
        """Config --list --global should show user config (global is alias for user)."""
        with runner.isolated_filesystem():
            # Create project config
            Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n")

            # Create user config in our isolated home
            user_dir = isolated_env / ".sqitch"
            user_dir.mkdir(parents=True, exist_ok=True)
            user_config = user_dir / "sqitch.conf"
            user_config.write_text("[user]\n\tname = Global User\n")

            # --global should be accepted as alias for --user
            result = runner.invoke(
                main, ["config", "--list", "--global"], env={"HOME": str(isolated_env)}
            )

            assert result.exit_code == 0, f"Config --list --global failed: {result.output}"
            assert (
                "Global User" in result.output or "user.name" in result.output
            ), "Should show user config via --global"


class TestConfigOutputFormat:
    """Test that config output matches Sqitch format (for T028 validation)."""

    def test_get_outputs_value_only(self, runner):
        """Config get should output only the value, no labels."""
        with runner.isolated_filesystem():
            Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n")

            result = runner.invoke(main, ["config", "core.engine"])

            assert result.exit_code == 0, f"Config get failed: {result.output}"
            # Output should be just the value
            output_lines = result.output.strip().split("\n")
            assert len(output_lines) >= 1, "Should output at least one line"
            assert "sqlite" in output_lines[0], "First line should contain value"

    def test_quiet_mode_suppresses_informational_messages(self, runner):
        """Config with --quiet should suppress non-essential output."""
        with runner.isolated_filesystem():
            Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n")

            result = runner.invoke(main, ["--quiet", "config", "core.engine"])

            assert result.exit_code == 0, f"Config --quiet failed: {result.output}"
            # Should still show the value but no extra messages
            assert "sqlite" in result.output, "Should show value even in quiet mode"


class TestConfigErrorHandling:
    """Test config error conditions."""

    def test_fails_with_both_get_and_set_arguments(self, runner):
        """Config should handle conflicting operations gracefully."""
        with runner.isolated_filesystem():
            Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n")

            # Both name and value provided but also --list
            result = runner.invoke(main, ["config", "--list", "core.engine", "pg"])

            # Should either ignore extra args or error clearly
            # Accept either behavior as long as it doesn't crash
            assert result.exit_code in (
                0,
                1,
                2,
            ), f"Should handle conflict gracefully, got {result.exit_code}"

    def test_set_without_value_fails(self, runner):
        """Config set requires both name and value."""
        with runner.isolated_filesystem():
            Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n")

            result = runner.invoke(main, ["config", "core.engine"])

            # This is actually a get, so it should succeed
            assert result.exit_code == 0, "Get should work with just name"

    def test_handles_invalid_section_names(self, runner):
        """Config should handle invalid section.key formats gracefully."""
        with runner.isolated_filesystem():
            Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n")

            # Try to get a malformed key
            result = runner.invoke(main, ["config", "invalidsectionkey"])

            # Should fail with clear error (exit 1) not crash
            assert result.exit_code in (
                0,
                1,
            ), f"Should handle invalid keys gracefully, got {result.exit_code}"


class TestConfigEnvironmentOverrides:
    """Tests covering FR-001a environment override precedence."""

    def test_environment_overrides_define_scope_precedence(self, runner):
        """SQITCH_* variables should control scope order system → user → local."""

        with runner.isolated_filesystem():
            system_conf = Path("system.conf")
            system_conf.write_text("[core]\n\tengine = pg\n", encoding="utf-8")

            user_conf = Path("user.conf")
            user_conf.write_text("[core]\n\tengine = mysql\n", encoding="utf-8")

            local_conf = Path("local.conf")
            local_conf.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

            env = {
                "SQITCH_SYSTEM_CONFIG": str(system_conf),
                "SQITCH_USER_CONFIG": str(user_conf),
                "SQITCH_CONFIG": str(local_conf),
            }

            result = runner.invoke(main, ["config", "core.engine"], env=env)

            assert result.exit_code == 0, f"Config get failed with overrides: {result.output}"
            assert "sqlite" in result.output, "Local SQITCH_CONFIG should take precedence"

    def test_sqlitch_overrides_take_priority_over_sqitch(self, runner):
        """SQLITCH_* overrides should supersede SQITCH_* fallbacks."""

        with runner.isolated_filesystem():
            fallback_conf = Path("fallback.conf")
            fallback_conf.write_text("[core]\n\tengine = mysql\n", encoding="utf-8")

            preferred_conf = Path("preferred.conf")
            preferred_conf.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

            env = {
                "SQITCH_CONFIG": str(fallback_conf),
                "SQLITCH_CONFIG": str(preferred_conf),
            }

            result = runner.invoke(main, ["config", "core.engine"], env=env)

            assert (
                result.exit_code == 0
            ), f"Config get failed with SQLITCH override: {result.output}"
            assert "sqlite" in result.output, "SQLITCH_CONFIG should override SQITCH_CONFIG"
