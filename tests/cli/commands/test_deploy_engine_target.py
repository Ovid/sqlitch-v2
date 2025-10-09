"""Test deploy command using engine target configuration."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


class TestDeployWithEngineTarget:
    """Test deploy command using engine target configuration (T010c)."""

    def test_deploy_uses_engine_target_when_no_explicit_target(self, runner: CliRunner) -> None:
        """Deploy should use engine.sqlite.target when no explicit target is given."""

        with runner.isolated_filesystem():
            env = os.environ.copy()
            env["SQLITCH_CONFIG_ROOT"] = str(Path.cwd())
            env["HOME"] = str(Path.cwd())
            env.pop("XDG_CONFIG_HOME", None)

            # Initialize project
            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, f"Init failed: {init_result.output}"

            # Add a target alias
            target_result = runner.invoke(
                main,
                ["target", "add", "flipr_test", "db:sqlite:flipr_test.db"],
                env=env,
            )
            assert target_result.exit_code == 0, f"Target add failed: {target_result.output}"

            # Configure engine to use the target alias
            engine_result = runner.invoke(main, ["engine", "add", "sqlite", "flipr_test"], env=env)
            assert engine_result.exit_code == 0, f"Engine add failed: {engine_result.output}"

            # Add a change
            add_result = runner.invoke(main, ["add", "users", "-n", "Add users table"], env=env)
            assert add_result.exit_code == 0, f"Add failed: {add_result.output}"

            # Create simple deploy/revert/verify scripts
            Path("deploy/users.sql").write_text(
                "BEGIN; CREATE TABLE users (id INTEGER PRIMARY KEY); COMMIT;"
            )
            Path("revert/users.sql").write_text("BEGIN; DROP TABLE users; COMMIT;")
            Path("verify/users.sql").write_text("SELECT id FROM users WHERE 0;")

            # Deploy WITHOUT specifying a target - should use engine.sqlite.target
            deploy_result = runner.invoke(main, ["deploy"], env=env)
            assert deploy_result.exit_code == 0, f"Deploy failed: {deploy_result.output}"
            assert "+ users" in deploy_result.output
            assert "flipr_test.db" in deploy_result.output

            # Verify database was created
            assert Path("flipr_test.db").exists()
            assert Path("sqitch.db").exists()

            # Verify table exists
            conn = sqlite3.connect("flipr_test.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            result = cursor.fetchone()
            conn.close()
            assert result is not None, "users table should exist"

    def test_deploy_errors_when_no_target_and_no_engine_target(self, runner: CliRunner) -> None:
        """Deploy should error when no target is specified and engine has no target configured."""

        with runner.isolated_filesystem():
            env = os.environ.copy()
            env["SQLITCH_CONFIG_ROOT"] = str(Path.cwd())
            env["HOME"] = str(Path.cwd())
            env.pop("XDG_CONFIG_HOME", None)

            # Initialize project without configuring engine target
            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, f"Init failed: {init_result.output}"

            # Add a change
            add_result = runner.invoke(main, ["add", "users", "-n", "Add users table"], env=env)
            assert add_result.exit_code == 0, f"Add failed: {add_result.output}"

            # Create simple deploy/revert/verify scripts
            Path("deploy/users.sql").write_text(
                "BEGIN; CREATE TABLE users (id INTEGER PRIMARY KEY); COMMIT;"
            )
            Path("revert/users.sql").write_text("BEGIN; DROP TABLE users; COMMIT;")
            Path("verify/users.sql").write_text("SELECT id FROM users WHERE 0;")

            # Deploy WITHOUT specifying a target and WITHOUT engine target configured
            deploy_result = runner.invoke(main, ["deploy"], env=env)
            assert deploy_result.exit_code != 0
            assert "deployment target must be provided" in deploy_result.output.lower()

    def test_explicit_target_overrides_engine_target(self, runner: CliRunner) -> None:
        """Explicit target argument should override engine.sqlite.target."""

        with runner.isolated_filesystem():
            env = os.environ.copy()
            env["SQLITCH_CONFIG_ROOT"] = str(Path.cwd())
            env["HOME"] = str(Path.cwd())
            env.pop("XDG_CONFIG_HOME", None)

            # Initialize project
            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, f"Init failed: {init_result.output}"

            # Add a target alias
            target_result = runner.invoke(
                main,
                ["target", "add", "default_target", "db:sqlite:default.db"],
                env=env,
            )
            assert target_result.exit_code == 0, f"Target add failed: {target_result.output}"

            # Configure engine to use the target alias
            engine_result = runner.invoke(main, ["engine", "add", "sqlite", "default_target"], env=env)
            assert engine_result.exit_code == 0, f"Engine add failed: {engine_result.output}"

            # Add a change
            add_result = runner.invoke(main, ["add", "users", "-n", "Add users table"], env=env)
            assert add_result.exit_code == 0, f"Add failed: {add_result.output}"

            # Create simple deploy/revert/verify scripts
            Path("deploy/users.sql").write_text(
                "BEGIN; CREATE TABLE users (id INTEGER PRIMARY KEY); COMMIT;"
            )
            Path("revert/users.sql").write_text("BEGIN; DROP TABLE users; COMMIT;")
            Path("verify/users.sql").write_text("SELECT id FROM users WHERE 0;")

            # Deploy with an explicit different target
            deploy_result = runner.invoke(main, ["deploy", "db:sqlite:explicit.db"], env=env)
            assert deploy_result.exit_code == 0, f"Deploy failed: {deploy_result.output}"
            assert "+ users" in deploy_result.output
            assert "explicit.db" in deploy_result.output

            # Verify the explicit database was created, not the default one
            assert Path("explicit.db").exists()
            assert not Path("default.db").exists()
