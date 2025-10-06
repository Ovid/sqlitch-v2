"""Functional tests for deploy command."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


class TestDeployWithNoRegistry:
    """Test deploy when registry database doesn't exist yet (first deploy)."""

    def test_creates_registry_database_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should create sqitch.db file on first run."""
        # Setup: Create a minimal project
        project_dir = tmp_path / "flipr"
        project_dir.mkdir()
        
        # Create sqitch.conf
        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text("[core]\n    engine = sqlite\n")
        
        # Create sqitch.plan
        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users table\n"
        )
        
        # Create deploy script
        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        deploy_script = deploy_dir / "users.sql"
        deploy_script.write_text(
            "-- Deploy flipr:users to sqlite\n"
            "\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        
        # Target databases
        target_db = tmp_path / "flipr_test.db"
        registry_db = tmp_path / "sqitch.db"
        
        # Verify registry doesn't exist yet
        assert not registry_db.exists()
        
        # Execute: Deploy to new database
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        # Verify: Registry database was created
        assert registry_db.exists(), f"Registry database should be created\nOutput: {result.output}"
        assert result.exit_code == 0, f"Deploy should succeed\nOutput: {result.output}"

    def test_creates_all_registry_tables(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should create all required registry tables."""
        # Setup: Create minimal project
        project_dir = tmp_path / "flipr"
        project_dir.mkdir()
        
        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text("[core]\n    engine = sqlite\n")
        
        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users\n"
        )
        
        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        deploy_script = deploy_dir / "users.sql"
        deploy_script.write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        
        target_db = tmp_path / "flipr_test.db"
        registry_db = tmp_path / "sqitch.db"
        
        # Execute: Deploy
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0, f"Deploy should succeed\nOutput: {result.output}"
        
        # Verify: Check all registry tables exist
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {"releases", "projects", "changes", "tags", "dependencies", "events"}
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"
        
        conn.close()

    def test_inserts_project_record(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should insert project record into projects table."""
        # Setup
        project_dir = tmp_path / "flipr"
        project_dir.mkdir()
        
        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text("[core]\n    engine = sqlite\n")
        
        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "%uri=https://github.com/example/flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users\n"
        )
        
        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        deploy_script = deploy_dir / "users.sql"
        deploy_script.write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        
        target_db = tmp_path / "flipr_test.db"
        registry_db = tmp_path / "sqitch.db"
        
        # Execute
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0, f"Deploy should succeed\nOutput: {result.output}"
        
        # Verify: Project record exists
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT project, uri FROM projects")
        projects = cursor.fetchall()
        
        assert len(projects) == 1, "Should have one project record"
        project_name, uri = projects[0]
        assert project_name == "flipr", f"Project name should be 'flipr', got {project_name}"
        assert uri == "https://github.com/example/flipr", f"URI should match plan, got {uri}"
        
        conn.close()

    def test_inserts_release_record(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should insert registry version into releases table."""
        # Setup
        project_dir = tmp_path / "flipr"
        project_dir.mkdir()
        
        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text("[core]\n    engine = sqlite\n")
        
        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users\n"
        )
        
        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        deploy_script = deploy_dir / "users.sql"
        deploy_script.write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        
        target_db = tmp_path / "flipr_test.db"
        registry_db = tmp_path / "sqitch.db"
        
        # Execute
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0, f"Deploy should succeed\nOutput: {result.output}"
        
        # Verify: Release record exists with version 1.1
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM releases ORDER BY version DESC LIMIT 1")
        result_row = cursor.fetchone()
        
        assert result_row is not None, "Should have a release record"
        version = result_row[0]
        assert version == 1.1, f"Registry version should be 1.1, got {version}"
        
        conn.close()

    def test_outputs_adding_registry_message(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should output 'Adding registry tables' message on first run."""
        # Setup
        project_dir = tmp_path / "flipr"
        project_dir.mkdir()
        
        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text("[core]\n    engine = sqlite\n")
        
        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users\n"
        )
        
        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        deploy_script = deploy_dir / "users.sql"
        deploy_script.write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        
        target_db = tmp_path / "flipr_test.db"
        
        # Execute
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        # Verify: Output contains registry initialization message
        assert result.exit_code == 0, f"Deploy should succeed\nOutput: {result.output}"
        assert "Adding registry tables" in result.output, \
            f"Should show registry initialization message\nOutput: {result.output}"
        assert "sqitch.db" in result.output, \
            f"Should mention registry database name\nOutput: {result.output}"


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click test runner."""
    return CliRunner()
