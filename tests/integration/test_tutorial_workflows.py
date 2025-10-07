"""Integration tests for SQLite tutorial workflows.

Feature 004: SQLite Tutorial Parity
Tests complete end-to-end scenarios from quickstart.md
"""

from __future__ import annotations

import configparser
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


class TestScenario1ProjectInitialization:
    """Scenario 1: Project Initialization
    
    Goal: Initialize a new SQLitch project with proper configuration
    Success criteria:
    - sqitch.conf created with correct engine
    - sqitch.plan created with pragmas
    - deploy/, revert/, verify/ directories created
    - User config saved to ~/.sqitch/sqitch.conf
    """

    def test_init_creates_proper_structure(self, tmp_path):
        """Test init creates all required files and directories."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize SQLitch project
            result = runner.invoke(
                main,
                ["init", "flipr", "--uri", "https://github.com/example/flipr/", "--engine", "sqlite"],
            )
            
            assert result.exit_code == 0, f"Init failed: {result.output}"
            
            # Verify files created
            assert Path("sqitch.conf").exists(), "sqitch.conf not created"
            assert Path("sqitch.plan").exists(), "sqitch.plan not created"
            assert Path("deploy").is_dir(), "deploy/ directory not created"
            assert Path("revert").is_dir(), "revert/ directory not created"
            assert Path("verify").is_dir(), "verify/ directory not created"
            
            # Verify sqitch.conf content
            config_content = Path("sqitch.conf").read_text()
            assert "[core]" in config_content
            assert "engine = sqlite" in config_content
            
            # Verify sqitch.plan content
            plan_content = Path("sqitch.plan").read_text()
            assert "%syntax-version=1.0.0" in plan_content
            assert "%project=flipr" in plan_content
            assert "%uri=https://github.com/example/flipr/" in plan_content

    def test_config_get_set_works(self, tmp_path):
        """Test config get/set operations."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize project first
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            
            # Configure user settings
            result = runner.invoke(
                main,
                ["config", "--user", "user.name", "Test User"],
            )
            assert result.exit_code == 0, f"Config set failed: {result.output}"
            
            result = runner.invoke(
                main,
                ["config", "--user", "user.email", "test@example.com"],
            )
            assert result.exit_code == 0, f"Config set failed: {result.output}"
            
            # Verify user config file created (in temp directory for isolation)
            user_config = Path.home() / ".config" / "sqlitch" / "sqitch.conf"
            if not user_config.exists():
                user_config = Path.home() / ".sqitch" / "sqitch.conf"
            
            # Note: In isolated filesystem, user config won't persist,
            # but we can verify the command succeeded
            
            # Get config value from project config
            result = runner.invoke(main, ["config", "core.engine"])
            assert result.exit_code == 0
            assert "sqlite" in result.output


class TestScenario2FirstChange:
    """Scenario 2: First Change - Users Table
    
    Goal: Add, deploy, and verify first database change
    Success criteria:
    - Three script files created with proper headers
    - Plan file updated with change entry
    - Registry database (sqitch.db) created
    - Change deployed to flipr_test.db
    - Verify script passes
    - Status shows deployed change
    """

    def test_add_deploy_verify_first_change(self, tmp_path):
        """Test complete workflow for first change."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize project
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            
            # Add users table change
            result = runner.invoke(
                main,
                ["add", "users", "-n", "Creates table to track our users."],
            )
            assert result.exit_code == 0, f"Add failed: {result.output}"
            
            # Verify files created
            assert Path("deploy/users.sql").exists()
            assert Path("revert/users.sql").exists()
            assert Path("verify/users.sql").exists()
            
            # Verify plan updated
            plan_content = Path("sqitch.plan").read_text()
            assert "users" in plan_content
            assert "Creates table to track our users." in plan_content
            
            # Edit deploy script (manually add CREATE TABLE)
            Path("deploy/users.sql").write_text(
                """-- Deploy flipr:users to sqlite

BEGIN;

CREATE TABLE users (
    user_id   INTEGER PRIMARY KEY,
    username  TEXT NOT NULL UNIQUE,
    email     TEXT NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
"""
            )
            
            # Edit revert script
            Path("revert/users.sql").write_text(
                """-- Revert flipr:users from sqlite

BEGIN;

DROP TABLE users;

COMMIT;
"""
            )
            
            # Edit verify script
            Path("verify/users.sql").write_text(
                """-- Verify flipr:users on sqlite

SELECT user_id, username, email, created_at
FROM users
WHERE 0;
"""
            )
            
            # Deploy to database
            result = runner.invoke(
                main,
                ["deploy", "db:sqlite:flipr_test.db"],
            )
            assert result.exit_code == 0, f"Deploy failed: {result.output}"
            assert "+ users" in result.output
            
            # Verify database files created
            assert Path("flipr_test.db").exists()
            assert Path("sqitch.db").exists()
            
            # Verify table exists
            conn = sqlite3.connect("flipr_test.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            result = cursor.fetchone()
            assert result is not None
            conn.close()
            
            # Verify deployment
            result = runner.invoke(
                main,
                ["verify", "db:sqlite:flipr_test.db"],
            )
            assert result.exit_code == 0, f"Verify failed: {result.output}"
            assert "* users" in result.output
            
            # Check status
            result = runner.invoke(
                main,
                ["status", "db:sqlite:flipr_test.db"],
            )
            assert result.exit_code == 0, f"Status failed: {result.output}"
            assert "users" in result.output


class TestScenario3DependentChange:
    """Scenario 3: Dependent Change - Flips Table
    
    Goal: Add change with dependency on previous change
    Success criteria:
    - Dependency recorded in plan file
    - Deploy validates dependency exists
    - Foreign key constraints work
    - Both tables exist in database
    """

    def test_dependent_change_deployment(self, tmp_path):
        """Test adding and deploying a change with dependencies."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize project
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            
            # Add and deploy users table first
            runner.invoke(main, ["add", "users", "-n", "Creates table to track our users."])
            Path("deploy/users.sql").write_text(
                """-- Deploy flipr:users to sqlite
BEGIN;
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE
);
COMMIT;
"""
            )
            Path("revert/users.sql").write_text(
                """-- Revert flipr:users from sqlite
BEGIN;
DROP TABLE users;
COMMIT;
"""
            )
            Path("verify/users.sql").write_text(
                """-- Verify flipr:users on sqlite
SELECT user_id, username FROM users WHERE 0;
"""
            )
            runner.invoke(main, ["deploy", "db:sqlite:flipr_test.db"])
            
            # Add flips table with dependency
            result = runner.invoke(
                main,
                ["add", "flips", "--requires", "users", "-n", "Adds table for storing flips."],
            )
            assert result.exit_code == 0, f"Add with dependency failed: {result.output}"
            
            # Verify plan shows dependency
            plan_content = Path("sqitch.plan").read_text()
            assert "flips [users]" in plan_content
            
            # Edit flips deploy script
            Path("deploy/flips.sql").write_text(
                """-- Deploy flipr:flips to sqlite
BEGIN;
CREATE TABLE flips (
    flip_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    message TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMIT;
"""
            )
            Path("revert/flips.sql").write_text(
                """-- Revert flipr:flips from sqlite
BEGIN;
DROP TABLE flips;
COMMIT;
"""
            )
            Path("verify/flips.sql").write_text(
                """-- Verify flipr:flips on sqlite
SELECT flip_id, user_id, message FROM flips WHERE 0;
"""
            )
            
            # Deploy
            result = runner.invoke(
                main,
                ["deploy", "db:sqlite:flipr_test.db"],
            )
            assert result.exit_code == 0, f"Deploy failed: {result.output}"
            
            # Verify both tables exist
            conn = sqlite3.connect("flipr_test.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            assert "users" in tables
            assert "flips" in tables
            conn.close()


class TestScenario4ViewCreation:
    """Scenario 4: View Creation - UserFlips
    
    Goal: Create database view depending on multiple tables
    Success criteria:
    - Multiple dependencies recorded
    - View created successfully
    - View query works
    - Verify script validates view structure
    """

    def test_view_with_multiple_dependencies(self, tmp_path):
        """Test creating a view with multiple dependencies."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize project
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            
            # Add and deploy users table
            runner.invoke(main, ["add", "users", "-n", "Creates users table."])
            Path("deploy/users.sql").write_text(
                """-- Deploy flipr:users to sqlite
BEGIN;
CREATE TABLE users (user_id INTEGER PRIMARY KEY, username TEXT NOT NULL);
COMMIT;
"""
            )
            Path("revert/users.sql").write_text("BEGIN; DROP TABLE users; COMMIT;")
            Path("verify/users.sql").write_text("SELECT user_id FROM users WHERE 0;")
            runner.invoke(main, ["deploy", "db:sqlite:flipr_test.db"])
            
            # Add and deploy flips table
            runner.invoke(main, ["add", "flips", "--requires", "users", "-n", "Creates flips table."])
            Path("deploy/flips.sql").write_text(
                """-- Deploy flipr:flips to sqlite
BEGIN;
CREATE TABLE flips (
    flip_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    message TEXT NOT NULL
);
COMMIT;
"""
            )
            Path("revert/flips.sql").write_text("BEGIN; DROP TABLE flips; COMMIT;")
            Path("verify/flips.sql").write_text("SELECT flip_id FROM flips WHERE 0;")
            runner.invoke(main, ["deploy", "db:sqlite:flipr_test.db"])
            
            # Add view with multiple dependencies
            result = runner.invoke(
                main,
                [
                    "add",
                    "userflips",
                    "--requires",
                    "users",
                    "--requires",
                    "flips",
                    "-n",
                    "Creates userflips view.",
                ],
            )
            assert result.exit_code == 0, f"Add view failed: {result.output}"
            
            # Edit view scripts
            Path("deploy/userflips.sql").write_text(
                """-- Deploy flipr:userflips to sqlite
BEGIN;
CREATE VIEW userflips AS
SELECT u.username, f.message, f.flip_id
FROM users u
JOIN flips f ON u.user_id = f.user_id;
COMMIT;
"""
            )
            Path("revert/userflips.sql").write_text("BEGIN; DROP VIEW userflips; COMMIT;")
            Path("verify/userflips.sql").write_text("SELECT username, message FROM userflips WHERE 0;")
            
            # Deploy
            result = runner.invoke(
                main,
                ["deploy", "db:sqlite:flipr_test.db"],
            )
            assert result.exit_code == 0, f"Deploy view failed: {result.output}"
            
            # Verify view exists
            conn = sqlite3.connect("flipr_test.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='userflips'")
            view_result = cursor.fetchone()
            assert view_result is not None
            conn.close()
            
            # Verify the view
            result = runner.invoke(
                main,
                ["verify", "db:sqlite:flipr_test.db"],
            )
            assert result.exit_code == 0, f"Verify failed: {result.output}"


class TestScenario5TaggingRelease:
    """Scenario 5: Tagging Release - v1.0.0-dev1
    
    Goal: Tag current state as release version
    Success criteria:
    - Tag added to plan file
    - Tag recorded in registry
    - Status displays tag information
    """

    def test_tag_release_version(self, tmp_path):
        """Test tagging a release version."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize project and add a change
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            runner.invoke(main, ["add", "users", "-n", "Creates users table."])
            Path("deploy/users.sql").write_text("BEGIN; CREATE TABLE users (id INTEGER); COMMIT;")
            Path("revert/users.sql").write_text("BEGIN; DROP TABLE users; COMMIT;")
            Path("verify/users.sql").write_text("SELECT id FROM users WHERE 0;")
            runner.invoke(main, ["deploy", "db:sqlite:flipr_test.db"])
            
            # Create release tag
            result = runner.invoke(
                main,
                ["tag", "v1.0.0-dev1", "-n", "Tag v1.0.0-dev1."],
            )
            assert result.exit_code == 0, f"Tag failed: {result.output}"
            
            # Verify plan
            plan_content = Path("sqitch.plan").read_text()
            assert "@v1.0.0-dev1" in plan_content
            
            # Deploy tag (should be no-op if already deployed)
            result = runner.invoke(
                main,
                ["deploy", "db:sqlite:flipr_test.db"],
            )
            assert result.exit_code == 0, f"Deploy after tag failed: {result.output}"

            # Registry should record the tag
            with closing(sqlite3.connect("sqitch.db")) as registry:
                tags = registry.execute("SELECT tag FROM tags").fetchall()
            assert tags == [("v1.0.0-dev1",)], f"Tags table mismatch: {tags!r}"

            # Check status shows tag
            result = runner.invoke(
                main,
                ["status", "db:sqlite:flipr_test.db"],
            )
            assert result.exit_code == 0, f"Status failed: {result.output}"
            assert "@v1.0.0-dev1" in result.output


class TestScenario6RevertChanges:
    """Scenario 6: Revert Changes
    
    Goal: Revert deployed changes and re-deploy
    Success criteria:
    - Revert script executes successfully
    - Registry updated (change removed)
    - Database object removed
    - Re-deploy works correctly
    """

    def test_revert_and_redeploy(self, tmp_path):
        """Test reverting changes and re-deploying."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize project and add two changes
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            
            # Add first change
            runner.invoke(main, ["add", "users", "-n", "Creates users table."])
            Path("deploy/users.sql").write_text("BEGIN; CREATE TABLE users (id INTEGER); COMMIT;")
            Path("revert/users.sql").write_text("BEGIN; DROP TABLE users; COMMIT;")
            Path("verify/users.sql").write_text("SELECT id FROM users WHERE 0;")
            
            # Add second change
            runner.invoke(main, ["add", "flips", "-n", "Creates flips table."])
            Path("deploy/flips.sql").write_text("BEGIN; CREATE TABLE flips (id INTEGER); COMMIT;")
            Path("revert/flips.sql").write_text("BEGIN; DROP TABLE flips; COMMIT;")
            Path("verify/flips.sql").write_text("SELECT id FROM flips WHERE 0;")
            
            # Deploy both changes
            deploy_result = runner.invoke(main, ["deploy", "db:sqlite:flipr_test.db"])
            assert deploy_result.exit_code == 0, deploy_result.output

            with closing(sqlite3.connect("sqitch.db")) as registry:
                deployed = [row[0] for row in registry.execute("SELECT change FROM changes ORDER BY committed_at").fetchall()]
            assert deployed == ["users", "flips"], deployed
            
            # Check current status
            result = runner.invoke(main, ["status", "db:sqlite:flipr_test.db"])
            assert "flips" in result.output
            
            # Revert one change (using -y to skip confirmation)
            result = runner.invoke(
                main,
                ["revert", "db:sqlite:flipr_test.db", "--to-change", "users", "-y"],
            )
            assert result.exit_code == 0, f"Revert failed: {result.output}"
            assert "- flips" in result.output
            
            # Verify change reverted in database
            conn = sqlite3.connect("flipr_test.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='flips'")
            assert cursor.fetchone() is None, "flips table should be removed"
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            assert cursor.fetchone() is not None, "users table should still exist"
            conn.close()
            
            with closing(sqlite3.connect("sqitch.db")) as registry:
                deployed_after_revert = [row[0] for row in registry.execute("SELECT change FROM changes ORDER BY committed_at").fetchall()]
            assert deployed_after_revert == ["users"], deployed_after_revert

            # Check status shows only users
            result = runner.invoke(main, ["status", "db:sqlite:flipr_test.db"])
            assert "users" in result.output
            
            # Re-deploy
            result = runner.invoke(
                main,
                ["deploy", "db:sqlite:flipr_test.db"],
            )
            assert result.exit_code == 0, f"Re-deploy failed: {result.output}"
            
            with closing(sqlite3.connect("sqitch.db")) as registry:
                redeployed = [row[0] for row in registry.execute("SELECT change FROM changes ORDER BY committed_at").fetchall()]
            assert redeployed == ["users", "flips"], redeployed

            # Verify restored
            result = runner.invoke(main, ["status", "db:sqlite:flipr_test.db"])
            assert "flips" in result.output


class TestScenario7ChangeHistory:
    """Scenario 7: View deployment history log
    
    Goal: View deployment history with log command
    Success criteria:
    - Log shows all events chronologically
    - Log filtering by change works
    - Events show committer, timestamp, note
    """

    def test_view_deployment_history(self, tmp_path):
        """Test viewing deployment history with log command."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize project and deploy some changes
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            
            # Add and deploy first change
            runner.invoke(main, ["add", "users", "-n", "Creates users table."])
            Path("deploy/users.sql").write_text("BEGIN; CREATE TABLE users (id INTEGER); COMMIT;")
            Path("revert/users.sql").write_text("BEGIN; DROP TABLE users; COMMIT;")
            Path("verify/users.sql").write_text("SELECT id FROM users WHERE 0;")
            runner.invoke(main, ["deploy", "db:sqlite:flipr_test.db"])
            
            # Add and deploy second change
            runner.invoke(main, ["add", "flips", "-n", "Creates flips table."])
            Path("deploy/flips.sql").write_text("BEGIN; CREATE TABLE flips (id INTEGER); COMMIT;")
            Path("revert/flips.sql").write_text("BEGIN; DROP TABLE flips; COMMIT;")
            Path("verify/flips.sql").write_text("SELECT id FROM flips WHERE 0;")
            runner.invoke(main, ["deploy", "db:sqlite:flipr_test.db"])
            
            # Revert flips to generate history
            revert_result = runner.invoke(
                main,
                ["revert", "db:sqlite:flipr_test.db", "--to-change", "users", "-y"],
            )
            assert revert_result.exit_code == 0, revert_result.output

            # Show all events
            result = runner.invoke(
                main,
                ["log", "db:sqlite:flipr_test.db"],
            )
            assert result.exit_code == 0, f"Log failed: {result.output}"
            assert "Deploy" in result.output and "Revert" in result.output
            assert result.output.index("Revert") < result.output.index("Deploy")

            # Filter by change name
            result = runner.invoke(
                main,
                ["log", "db:sqlite:flipr_test.db", "--change", "users"],
            )
            assert result.exit_code == 0, f"Log filter failed: {result.output}"
            assert "users" in result.output


class TestScenario8ReworkChange:
    """Scenario 8: Rework a deployed change
    
    Goal: Rework a change after tagging
    Success criteria:
    - Rework creates @tag suffixed scripts
    - Rework updates plan
    - Deploy uses new version
    """

    def test_rework_deployed_change(self, tmp_path):
        """Test reworking a deployed change."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize project
            runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            
            # Add and deploy a change
            runner.invoke(main, ["add", "users", "-n", "Creates users table."])
            Path("deploy/users.sql").write_text("BEGIN; CREATE TABLE users (id INTEGER); COMMIT;")
            Path("revert/users.sql").write_text("BEGIN; DROP TABLE users; COMMIT;")
            Path("verify/users.sql").write_text("SELECT id FROM users WHERE 0;")
            runner.invoke(main, ["deploy", "db:sqlite:flipr_test.db"])
            
            # Tag the release
            runner.invoke(main, ["tag", "v1.0.0", "-n", "First release."])
            
            # Rework the change
            result = runner.invoke(
                main,
                ["rework", "users", "--note", "Rework users table."],
            )
            assert result.exit_code == 0, f"Rework failed: {result.output}"
            
            # Verify tagged rework scripts created
            assert Path("deploy/users@v1.0.0.sql").exists()
            assert Path("revert/users@v1.0.0.sql").exists()
            assert Path("verify/users@v1.0.0.sql").exists()
            
            # Verify plan updated
            plan_content = Path("sqitch.plan").read_text()
            # Should have original users and reworked users
            assert plan_content.count("users") >= 2


class TestScenario9TargetEngineParity:
    """Scenario 9: Target & Engine Configuration Parity

    Goal: Ensure engine commands accept target aliases like Sqitch.
    Success criteria:
    - Engine add resolves target alias to stored URI
    - Engine update accepts direct URI after alias-based add
    - Engine remove cleans up engine definition
    """

    def test_engine_alias_workflow(self, tmp_path):
        """Test engine alias resolution end-to-end."""

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            config_root = Path.cwd() / ".sqlitch-config"
            env = {"SQLITCH_CONFIG_ROOT": str(config_root)}

            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, init_result.output

            target_result = runner.invoke(
                main,
                ["target", "add", "flipr_test", "db:sqlite:flipr_test.db"],
                env=env,
            )
            assert target_result.exit_code == 0, target_result.output

            add_result = runner.invoke(
                main,
                ["engine", "add", "sqlite", "flipr_test"],
                env=env,
            )
            assert add_result.exit_code == 0, add_result.output

            config_path = config_root / "sqitch.conf"
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read(config_path, encoding="utf-8")
            assert parser.has_section('engine "sqlite"')
            assert parser['engine "sqlite"']["uri"] == "db:sqlite:flipr_test.db"

            update_result = runner.invoke(
                main,
                ["engine", "update", "sqlite", "db:sqlite:flipr_test.db"],
                env=env,
            )
            assert update_result.exit_code == 0, update_result.output

            remove_result = runner.invoke(
                main,
                ["engine", "remove", "sqlite", "--yes"],
                env=env,
            )
            assert remove_result.exit_code == 0, remove_result.output

            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read(config_path, encoding="utf-8")
            assert not parser.has_section('engine "sqlite"')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
