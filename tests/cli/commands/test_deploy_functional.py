"""Functional tests for deploy command."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from sqlitch.cli.main import main
from sqlitch.plan.model import Change, Plan, Tag
from sqlitch.utils.logging import StructuredLogger

_SUPPORT_DIR = Path(__file__).resolve().parents[2] / "support"
_TUTORIAL_ENV_OVERRIDES_PATH = _SUPPORT_DIR / "tutorial_parity" / "env_overrides.json"
with _TUTORIAL_ENV_OVERRIDES_PATH.open(encoding="utf-8") as _env_file:
    TUTORIAL_ENV_OVERRIDES = json.load(_env_file)


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
        assert (
            "Adding registry tables" in result.output
        ), f"Should show registry initialization message\nOutput: {result.output}"
        assert (
            "sqitch.db" in result.output
        ), f"Should mention registry database name\nOutput: {result.output}"


class TestDeployWithSingleChange:
    """Test deploy functionality for a single change."""

    def test_loads_and_executes_deploy_script(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should load and execute the deploy script."""
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
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users table\n"
        )

        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        deploy_script = deploy_dir / "users.sql"
        deploy_script.write_text(
            "-- Deploy flipr:users to sqlite\n"
            "\n"
            "BEGIN;\n"
            "CREATE TABLE users (\n"
            "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "    name TEXT NOT NULL,\n"
            "    email TEXT NOT NULL UNIQUE\n"
            ");\n"
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

        assert result.exit_code == 0, f"Deploy should succeed\nOutput: {result.output}"

        # Verify: Table was actually created in target database
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()

        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None, "users table should exist in target database"

        # Check table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type
        assert "id" in columns, "Should have id column"
        assert "name" in columns, "Should have name column"
        assert "email" in columns, "Should have email column"

        conn.close()


class TestDeployIdentityPrecedence:
    """Validate full SQLITCH → SQITCH → GIT identity precedence chain."""

    @staticmethod
    def _create_project(tmp_path: Path) -> tuple[Path, Path, Path]:
        project_dir = tmp_path / "flipr"
        project_dir.mkdir()

        (project_dir / "sqitch.conf").write_text("[core]\n    engine = sqlite\n", encoding="utf-8")

        (project_dir / "sqitch.plan").write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users table\n",
            encoding="utf-8",
        )

        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n",
            encoding="utf-8",
        )

        target_db = tmp_path / "flipr_target.db"
        registry_db = tmp_path / "sqitch.db"
        return project_dir, target_db, registry_db

    @staticmethod
    def _invoke_deploy(runner: CliRunner, project_dir: Path, target_db: Path) -> Result:
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            return runner.invoke(main, ["deploy", f"db:sqlite:{target_db}"])
        finally:
            os.chdir(original_cwd)

    @staticmethod
    def _fetch_identity(registry_db: Path) -> tuple[str, str]:
        conn = sqlite3.connect(registry_db)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT committer_name, committer_email FROM events WHERE change = 'users'"
            )
            row = cursor.fetchone()
            assert row is not None, "Deployment event should exist"
            return row[0], row[1]
        finally:
            conn.close()

    @staticmethod
    def _clear_identity_env(monkeypatch: pytest.MonkeyPatch) -> None:
        for key in (
            "SQLITCH_FULLNAME",
            "SQLITCH_EMAIL",
            "SQITCH_FULLNAME",
            "SQITCH_EMAIL",
            "GIT_AUTHOR_NAME",
            "GIT_AUTHOR_EMAIL",
        ):
            monkeypatch.delenv(key, raising=False)

    def test_prefers_sqlitch_fullname_and_email(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir, target_db, registry_db = self._create_project(tmp_path)
        self._clear_identity_env(monkeypatch)

        monkeypatch.setenv("SQLITCH_FULLNAME", TUTORIAL_ENV_OVERRIDES["SQLITCH_FULLNAME"])
        monkeypatch.setenv("SQLITCH_EMAIL", TUTORIAL_ENV_OVERRIDES["SQLITCH_EMAIL"])
        monkeypatch.setenv("SQITCH_FULLNAME", TUTORIAL_ENV_OVERRIDES["SQITCH_FULLNAME"])
        monkeypatch.setenv("SQITCH_EMAIL", TUTORIAL_ENV_OVERRIDES["SQITCH_EMAIL"])
        monkeypatch.setenv("GIT_AUTHOR_NAME", TUTORIAL_ENV_OVERRIDES["GIT_AUTHOR_NAME"])
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", TUTORIAL_ENV_OVERRIDES["GIT_AUTHOR_EMAIL"])

        result = self._invoke_deploy(runner, project_dir, target_db)

        assert result.exit_code == 0, f"Deploy failed: {result.output}"

        name, email = self._fetch_identity(registry_db)
        assert name == TUTORIAL_ENV_OVERRIDES["SQLITCH_FULLNAME"]
        assert email == TUTORIAL_ENV_OVERRIDES["SQLITCH_EMAIL"]

    def test_falls_back_to_sqitch_fullname_and_email(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir, target_db, registry_db = self._create_project(tmp_path)
        self._clear_identity_env(monkeypatch)

        monkeypatch.setenv("SQITCH_FULLNAME", TUTORIAL_ENV_OVERRIDES["SQITCH_FULLNAME"])
        monkeypatch.setenv("SQITCH_EMAIL", TUTORIAL_ENV_OVERRIDES["SQITCH_EMAIL"])
        monkeypatch.setenv("GIT_AUTHOR_NAME", TUTORIAL_ENV_OVERRIDES["GIT_AUTHOR_NAME"])
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", TUTORIAL_ENV_OVERRIDES["GIT_AUTHOR_EMAIL"])

        result = self._invoke_deploy(runner, project_dir, target_db)

        assert result.exit_code == 0, f"Deploy failed: {result.output}"

        name, email = self._fetch_identity(registry_db)
        assert name == TUTORIAL_ENV_OVERRIDES["SQITCH_FULLNAME"]
        assert email == TUTORIAL_ENV_OVERRIDES["SQITCH_EMAIL"]

    def test_falls_back_to_git_author_when_no_sqitch_vars(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_dir, target_db, registry_db = self._create_project(tmp_path)
        self._clear_identity_env(monkeypatch)

        monkeypatch.setenv("GIT_AUTHOR_NAME", TUTORIAL_ENV_OVERRIDES["GIT_AUTHOR_NAME"])
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", TUTORIAL_ENV_OVERRIDES["GIT_AUTHOR_EMAIL"])

        result = self._invoke_deploy(runner, project_dir, target_db)

        assert result.exit_code == 0, f"Deploy failed: {result.output}"

        name, email = self._fetch_identity(registry_db)
        assert name == TUTORIAL_ENV_OVERRIDES["GIT_AUTHOR_NAME"]
        assert email == TUTORIAL_ENV_OVERRIDES["GIT_AUTHOR_EMAIL"]

    def test_inserts_change_record_in_registry(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should insert change record into registry changes table."""
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
            "users 2025-01-01T12:34:56Z Alice <alice@example.com> # Add users table\n"
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

        # Verify: Change record exists in registry
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT change_id, change, project, note, planner_name, planner_email, script_hash "
            "FROM changes WHERE change = 'users'"
        )
        change_record = cursor.fetchone()

        assert change_record is not None, "Should have change record for 'users'"
        change_id, change_name, project, note, planner_name, planner_email, script_hash = (
            change_record
        )

        assert change_name == "users", f"Change name should be 'users', got {change_name}"
        assert project == "flipr", f"Project should be 'flipr', got {project}"
        assert note == "Add users table", f"Note should match plan, got {note}"
        assert planner_name == "Alice", f"Planner name should be 'Alice', got {planner_name}"
        assert (
            planner_email == "alice@example.com"
        ), f"Planner email should match, got {planner_email}"
        assert script_hash is not None, "Script hash should be calculated and stored"
        assert len(script_hash) > 0, "Script hash should not be empty"

        conn.close()

    def test_inserts_event_record(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should insert event record into registry events table."""
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

        # Verify: Event record exists
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event, change, project, note, committer_name, committer_email "
            "FROM events WHERE change = 'users' AND event = 'deploy'"
        )
        event_record = cursor.fetchone()

        assert event_record is not None, "Should have deploy event record for 'users'"
        event, change, project, note, committer_name, committer_email = event_record

        assert event == "deploy", f"Event type should be 'deploy', got {event}"
        assert change == "users", f"Change should be 'users', got {change}"
        assert project == "flipr", f"Project should be 'flipr', got {project}"
        assert note == "Add users", f"Note should match plan, got {note}"
        assert committer_name is not None, "Committer name should be set"
        assert committer_email is not None, "Committer email should be set"

        conn.close()

    def test_calculates_script_hash(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should calculate and store script hash for the deploy script."""
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

        # Create a specific script with known content
        deploy_script = deploy_dir / "users.sql"
        script_content = (
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        deploy_script.write_text(script_content)

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

        # Verify: Script hash is stored and is a valid SHA-1 hash
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT script_hash FROM changes WHERE change = 'users'")
        result_row = cursor.fetchone()

        assert result_row is not None, "Should have change record"
        script_hash = result_row[0]

        assert script_hash is not None, "Script hash should not be NULL"
        # SHA-1 hash should be 40 hex characters
        assert len(script_hash) == 40, f"Script hash should be 40 chars, got {len(script_hash)}"
        assert all(
            c in "0123456789abcdef" for c in script_hash.lower()
        ), "Script hash should be valid hex"

        conn.close()

    def test_outputs_deployment_success_message(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should output success message for deployed change."""
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

        assert result.exit_code == 0, f"Deploy should succeed\nOutput: {result.output}"

        # Verify: Output shows successful deployment
        assert (
            "+ users" in result.output
        ), f"Should show '+ users' for deployed change\nOutput: {result.output}"
        assert (
            "Deployment complete" in result.output or "Applied" in result.output
        ), f"Should show deployment completion message\nOutput: {result.output}"


class TestDeployWithMultipleChanges:
    """Test deploy functionality with multiple changes."""

    def test_deploys_changes_in_plan_order(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should apply changes in the order they appear in the plan."""
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
            "posts 2025-01-02T00:00:00Z Test User <test@example.com> # Add posts\n"
            "comments 2025-01-03T00:00:00Z Test User <test@example.com> # Add comments\n"
        )

        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()

        # Create deploy scripts
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        (deploy_dir / "posts.sql").write_text(
            "-- Deploy flipr:posts to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id));\n"
            "COMMIT;\n"
        )
        (deploy_dir / "comments.sql").write_text(
            "-- Deploy flipr:comments to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE comments (id INTEGER PRIMARY KEY, post_id INTEGER REFERENCES posts(id));\n"
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

        # Verify: All three changes were deployed in order
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT change, committed_at FROM changes ORDER BY committed_at")
        changes = [row[0] for row in cursor.fetchall()]

        assert changes == [
            "users",
            "posts",
            "comments",
        ], f"Changes should be deployed in plan order, got {changes}"

        # Verify: All tables exist in target database
        target_conn = sqlite3.connect(target_db)
        target_cursor = target_conn.cursor()
        target_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in target_cursor.fetchall()}

        assert "users" in tables, "users table should exist"
        assert "posts" in tables, "posts table should exist"
        assert "comments" in tables, "comments table should exist"

        target_conn.close()
        conn.close()

    def test_skips_already_deployed_changes(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should skip changes that are already deployed."""
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
            "posts 2025-01-02T00:00:00Z Test User <test@example.com> # Add posts\n"
        )

        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()

        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        (deploy_dir / "posts.sql").write_text(
            "-- Deploy flipr:posts to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE posts (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )

        target_db = tmp_path / "flipr_test.db"
        registry_db = tmp_path / "sqitch.db"

        # Execute: First deploy (both changes)
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result1 = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        assert result1.exit_code == 0, f"First deploy should succeed\nOutput: {result1.output}"
        assert "+ users" in result1.output, "Should deploy users"
        assert "+ posts" in result1.output, "Should deploy posts"

        # Get deployment count after first deploy
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events WHERE event = 'deploy'")
        first_deploy_count = cursor.fetchone()[0]
        conn.close()

        # Execute: Second deploy (should skip both changes)
        try:
            os.chdir(project_dir)
            result2 = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        assert result2.exit_code == 0, f"Second deploy should succeed\nOutput: {result2.output}"

        # Verify: No new deploy events were created
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events WHERE event = 'deploy'")
        second_deploy_count = cursor.fetchone()[0]
        conn.close()

        assert (
            second_deploy_count == first_deploy_count
        ), "No new deploy events should be created when all changes already deployed"

    def test_stops_on_script_failure(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should stop processing changes if a script fails."""
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
            "bad_change 2025-01-02T00:00:00Z Test User <test@example.com> # Bad SQL\n"
            "posts 2025-01-03T00:00:00Z Test User <test@example.com> # Add posts\n"
        )

        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()

        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        # Create a script with invalid SQL
        (deploy_dir / "bad_change.sql").write_text(
            "-- Deploy flipr:bad_change to sqlite\n"
            "BEGIN;\n"
            "THIS IS INVALID SQL THAT WILL FAIL;\n"
            "COMMIT;\n"
        )
        (deploy_dir / "posts.sql").write_text(
            "-- Deploy flipr:posts to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE posts (id INTEGER PRIMARY KEY);\n"
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

        # Verify: Deploy should fail
        assert result.exit_code != 0, f"Deploy should fail on bad SQL\nOutput: {result.output}"

        # Verify: Only first change was deployed
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT change FROM changes ORDER BY committed_at")
        deployed_changes = [row[0] for row in cursor.fetchall()]

        assert "users" in deployed_changes, "First change should be deployed"
        assert "bad_change" not in deployed_changes, "Failed change should not be in registry"
        assert "posts" not in deployed_changes, "Changes after failure should not be deployed"

        conn.close()

    def test_rollback_on_error(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should roll back change if script execution fails."""
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
            "bad_change 2025-01-01T00:00:00Z Test User <test@example.com> # Bad SQL\n"
        )

        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()

        # Create a script that creates a table then fails
        (deploy_dir / "bad_change.sql").write_text(
            "-- Deploy flipr:bad_change to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "INVALID SQL HERE;\n"
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

        # Verify: Deploy should fail
        assert result.exit_code != 0, f"Deploy should fail\nOutput: {result.output}"

        # Verify: No change record in registry
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM changes WHERE change = 'bad_change'")
        change_count = cursor.fetchone()[0]
        assert change_count == 0, "Failed change should not be in registry"
        conn.close()

        # Verify: Table was not created in target (rollback worked)
        target_conn = sqlite3.connect(target_db)
        target_cursor = target_conn.cursor()
        target_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = target_cursor.fetchone() is not None
        target_conn.close()

        assert (
            not table_exists
        ), "Table from failed transaction should not exist (rollback should have occurred)"


class TestDeployDependencyValidation:
    """Test deploy dependency validation."""

    def test_validates_dependencies_before_deploy(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should validate that required dependencies are deployed first."""
        # Setup
        project_dir = tmp_path / "flipr"
        project_dir.mkdir()

        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text("[core]\n    engine = sqlite\n")

        # Create plan with posts depending on users
        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users\n"
            "posts [users] 2025-01-02T00:00:00Z Test User <test@example.com> # Add posts\n"
        )

        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()

        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        (deploy_dir / "posts.sql").write_text(
            "-- Deploy flipr:posts to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id));\n"
            "COMMIT;\n"
        )

        target_db = tmp_path / "flipr_test.db"
        registry_db = tmp_path / "sqitch.db"

        # Execute: Deploy both changes
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        assert (
            result.exit_code == 0
        ), f"Deploy should succeed when dependencies deployed\nOutput: {result.output}"

        # Verify: Both changes deployed
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT change FROM changes ORDER BY committed_at")
        changes = [row[0] for row in cursor.fetchall()]

        assert changes == ["users", "posts"], "Both changes should be deployed in dependency order"

        # Verify: Dependency recorded in registry
        cursor.execute(
            "SELECT dependency FROM dependencies WHERE change_id = "
            "(SELECT change_id FROM changes WHERE change = 'posts')"
        )
        dependencies = [row[0] for row in cursor.fetchall()]

        assert "users" in dependencies, "posts dependency on users should be recorded"

        conn.close()

    def test_fails_if_required_dependency_not_deployed(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Deploy should fail if a required dependency has not been deployed yet."""
        # Setup: Create project with posts but try to deploy only posts (missing users dependency)
        project_dir = tmp_path / "flipr"
        project_dir.mkdir()

        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text("[core]\n    engine = sqlite\n")

        # Plan has posts depending on users, but we'll deploy users first, then manually
        # try to deploy only a change that depends on something not yet deployed
        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users\n"
            "posts [users] 2025-01-02T00:00:00Z Test User <test@example.com> # Add posts\n"
            "comments [posts nonexistent] 2025-01-03T00:00:00Z Test User <test@example.com> # Add comments\n"
        )

        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()

        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        (deploy_dir / "posts.sql").write_text(
            "-- Deploy flipr:posts to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE posts (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        (deploy_dir / "comments.sql").write_text(
            "-- Deploy flipr:comments to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE comments (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )

        target_db = tmp_path / "flipr_test.db"
        registry_db = tmp_path / "sqitch.db"

        # Execute: Deploy all changes (comments depends on nonexistent change)
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        # Verify: Deploy should fail due to missing dependency
        assert (
            result.exit_code != 0
        ), f"Deploy should fail with missing dependency\nOutput: {result.output}"
        assert (
            "nonexistent" in result.output.lower() or "dependency" in result.output.lower()
        ), f"Error message should mention missing dependency\nOutput: {result.output}"

        # Verify: Comments was not deployed (registry may not be initialised on failure)
        if not registry_db.exists():
            return

        conn = sqlite3.connect(registry_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='changes'")
            if cursor.fetchone() is None:
                return

            cursor.execute("SELECT change FROM changes")
            changes = [row[0] for row in cursor.fetchall()]

            assert (
                "comments" not in changes
            ), "Change with missing dependency should not be deployed"
        finally:
            conn.close()


class TestDeployScriptExecution:
    """Test deploy script execution and transaction management."""

    def test_wraps_script_in_transaction_when_needed(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Deploy should wrap script in transaction if it doesn't manage its own."""
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

        # Create script WITHOUT BEGIN/COMMIT (engine should wrap it)
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
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

        assert result.exit_code == 0, f"Deploy should succeed\nOutput: {result.output}"

        # Verify: Table was created (script executed successfully)
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert (
            cursor.fetchone() is not None
        ), "Table should be created even without explicit transaction"
        conn.close()

    def test_respects_script_managed_transactions(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should not wrap script if it manages its own transactions."""
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

        # Create script WITH BEGIN/COMMIT (script manages own transaction)
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "\n"
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

        assert result.exit_code == 0, f"Deploy should succeed\nOutput: {result.output}"

        # Verify: Table was created (script with own transactions works)
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert (
            cursor.fetchone() is not None
        ), "Table should be created with script-managed transaction"
        conn.close()


class TestDeployUserIdentity:
    """Test that deploy correctly reads user identity from config."""

    def test_uses_user_identity_from_config_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploy should read user.name and user.email from config file."""
        # Setup: Create a project with user identity in config
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create sqitch.conf with user identity
        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text(
            "[core]\n"
            "    engine = sqlite\n"
            "[user]\n"
            "    name = Config User\n"
            "    email = config.user@example.com\n"
        )

        # Create sqitch.plan (note: planner identity in plan doesn't matter for deploy)
        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=test_project\n"
            "\n"
            "users 2025-01-01T00:00:00Z Plan User <plan@example.com> # Add users table\n"
        )

        # Create deploy script
        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        deploy_script = deploy_dir / "users.sql"
        deploy_script.write_text(
            "-- Deploy test_project:users to sqlite\n"
            "\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )

        # Target databases
        target_db = tmp_path / "test.db"
        registry_db = tmp_path / "sqitch.db"

        # Execute: Deploy with config file present
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

        # Verify: Check that the event record has the correct deployer identity from config
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()

        cursor.execute("SELECT committer_name, committer_email FROM events WHERE change = 'users'")
        row = cursor.fetchone()
        assert row is not None, "Event record should exist"

        deployer_name, deployer_email = row
        assert (
            deployer_name == "Config User"
        ), f"Deployer name should come from config file, got: {deployer_name}"
        assert (
            deployer_email == "config.user@example.com"
        ), f"Deployer email should come from config file, got: {deployer_email}"

        conn.close()

    def test_falls_back_to_env_when_no_config(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deploy should fall back to environment variables when config has no user section."""
        # Setup: Create a project without user identity in config
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create sqitch.conf WITHOUT user section
        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text("[core]\n    engine = sqlite\n")

        # Create sqitch.plan
        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=test_project\n"
            "\n"
            "users 2025-01-01T00:00:00Z Plan User <plan@example.com> # Add users\n"
        )

        # Create deploy script
        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        deploy_script = deploy_dir / "users.sql"
        deploy_script.write_text(
            "-- Deploy test_project:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )

        # Target databases
        target_db = tmp_path / "test.db"
        registry_db = tmp_path / "sqitch.db"

        # Set environment variables for user identity
        monkeypatch.setenv("SQLITCH_USER_NAME", "Env User")
        monkeypatch.setenv("SQLITCH_USER_EMAIL", "env.user@example.com")

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

        # Verify: Check that the event record has identity from environment
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()

        cursor.execute("SELECT committer_name, committer_email FROM events WHERE change = 'users'")
        row = cursor.fetchone()
        assert row is not None, "Event record should exist"

        deployer_name, deployer_email = row
        assert (
            deployer_name == "Env User"
        ), f"Deployer name should come from environment, got: {deployer_name}"
        assert (
            deployer_email == "env.user@example.com"
        ), f"Deployer email should come from environment, got: {deployer_email}"

        conn.close()

    def test_prefers_sqlitch_environment_over_sqitch(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deploy should prioritise SQLITCH_* env vars over SQITCH_* fallbacks."""
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
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )

        target_db = tmp_path / "flipr_test.db"
        registry_db = tmp_path / "sqitch.db"

        monkeypatch.setenv("SQITCH_USER_NAME", "Sqitch User")
        monkeypatch.setenv("SQITCH_USER_EMAIL", "sqitch.user@example.com")
        monkeypatch.setenv("SQLITCH_USER_NAME", "Sqlitch Preferred")
        monkeypatch.setenv("SQLITCH_USER_EMAIL", "sqlitch.preferred@example.com")

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

        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT committer_name, committer_email FROM events WHERE change = 'users'")
        row = cursor.fetchone()
        assert row is not None, "Event record should exist"

        committer_name, committer_email = row
        assert committer_name == "Sqlitch Preferred"
        assert committer_email == "sqlitch.preferred@example.com"

        conn.close()


class TestDeployFailureHandling:
    """Validate deploy error paths and registry bookkeeping."""

    def test_records_failure_event_on_script_error(self, runner: CliRunner, tmp_path: Path) -> None:
        """A failing deploy script should record a fail event and leave no changes deployed."""

        project_dir = tmp_path / "flipr"
        project_dir.mkdir()

        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text(
            "[core]\n"
            "    engine = sqlite\n"
            "[user]\n"
            "    name = Config User\n"
            "    email = config.user@example.com\n"
        )

        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Planner <planner@example.com> # Add users\n"
        )

        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "SELECT RAISE(ABORT, 'deploy explosion');\n"
        )

        target_db = tmp_path / "flipr_test.db"
        registry_db = tmp_path / "sqitch.db"

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        assert result.exit_code == 1
        assert "Deploy failed for change 'users'" in result.output

        # Target schema should be rolled back (table not created)
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is None
        conn.close()

        # Registry should contain a fail event but no change record
        assert registry_db.exists(), "Registry database should exist after failure"
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM changes")
        assert cursor.fetchone() == (0,)

        cursor.execute(
            "SELECT event, note, committer_name, committer_email FROM events WHERE change = 'users'"
        )
        rows = cursor.fetchall()
        assert rows == [("deploy_fail", "Add users", "Config User", "config.user@example.com")]

        conn.close()


class TestDeployErrorMessages:
    """Tests for deploy error message formatting and Sqitch parity.

    Regression tests from tests/regression/test_error_messages.py.
    """

    def test_unknown_change_error_matches_sqitch(self, runner: CliRunner, tmp_path: Path) -> None:
        """Deploying to a non-existent change should mirror Sqitch messaging."""
        from tests.support.sqlite_fixtures import ChangeScript, create_sqlite_project

        project = create_sqlite_project(
            tmp_path,
            changes=[
                ChangeScript(
                    name="users",
                    deploy_sql="SELECT 1;",
                    revert_sql="SELECT 1;",
                )
            ],
        )

        target = f"db:sqlite:{project.registry_path}"
        result = runner.invoke(
            main,
            ["--chdir", str(project.project_root), "deploy", target, "--to-change", "flips"],
        )

        assert result.exit_code != 0, result.output

        golden_root = Path(__file__).resolve().parents[2] / "support" / "golden" / "error_messages"
        expected_output = (golden_root / "unknown_change.txt").read_text(encoding="utf-8")
        assert result.output == expected_output

    def test_unknown_target_error_matches_sqitch(self, runner: CliRunner, tmp_path: Path) -> None:
        """Referencing an unknown target alias should mirror Sqitch messaging."""
        from tests.support.sqlite_fixtures import ChangeScript, create_sqlite_project

        project = create_sqlite_project(
            tmp_path,
            changes=[
                ChangeScript(
                    name="users",
                    deploy_sql="SELECT 1;",
                    revert_sql="SELECT 1;",
                )
            ],
        )

        result = runner.invoke(
            main,
            ["--chdir", str(project.project_root), "engine", "add", "demo", "analytics"],
        )

        assert result.exit_code != 0, result.output

        golden_root = Path(__file__).resolve().parents[2] / "support" / "golden" / "error_messages"
        expected_output = (golden_root / "unknown_target.txt").read_text(encoding="utf-8")
        assert result.output == expected_output

    def test_missing_dependency_error_matches_sqitch(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Plans referencing unknown dependencies should match Sqitch error text."""
        from tests.support.sqlite_fixtures import ChangeScript, create_sqlite_project

        project = create_sqlite_project(
            tmp_path,
            changes=[
                ChangeScript(
                    name="alpha",
                    deploy_sql="SELECT 1;",
                    revert_sql="SELECT 1;",
                    dependencies=("beta",),
                )
            ],
        )

        target = f"db:sqlite:{project.registry_path}"
        result = runner.invoke(
            main,
            ["--chdir", str(project.project_root), "deploy", target],
        )

        assert result.exit_code != 0, result.output

        golden_root = Path(__file__).resolve().parents[2] / "support" / "golden" / "error_messages"
        expected_output = (golden_root / "missing_dependency.txt").read_text(encoding="utf-8")
        assert result.output == expected_output


class TestDeployHelpers:
    """Unit coverage for helper functions in sqlitch.cli.commands.deploy.

    Merged from tests/cli/test_deploy_helpers.py during Phase 3.7c consolidation.
    """

    @staticmethod
    def _make_change(name: str) -> Change:
        """Helper to create a test Change object."""
        from datetime import datetime, timezone

        timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        return Change.create(
            name=name,
            script_paths={"deploy": Path("deploy.sql"), "revert": Path("revert.sql")},
            planner="Tester",
            planned_at=timestamp,
        )

    @staticmethod
    def _make_plan(changes: tuple[Change, ...], tags: tuple[Tag, ...] = ()) -> Plan:
        """Helper to create a test Plan object."""
        entries = changes + tags
        return Plan(
            project_name="demo",
            file_path=Path("sqlitch.plan"),
            entries=entries,
            checksum="checksum",
            default_engine="sqlite",
        )

    @staticmethod
    def _make_logger(*, quiet: bool = False) -> StructuredLogger:
        """Helper to create a test StructuredLogger."""
        from sqlitch.cli.options import LogConfiguration
        from sqlitch.utils.logging import StructuredLogger

        config = LogConfiguration(
            run_identifier="test",
            verbosity=0,
            quiet=quiet,
            json_mode=False,
        )
        return StructuredLogger(config)

    def test_resolve_target_prefers_option_over_config(self) -> None:
        """Test target resolution prefers CLI option over config."""
        from types import MappingProxyType

        from sqlitch.cli.commands import deploy as deploy_module

        assert (
            deploy_module._resolve_target(
                option_value="cli",
                configured_target="config",
                positional_targets=(),
                project_root=Path.cwd(),
                config_root=Path.cwd(),
                env=MappingProxyType({}),
                default_engine="sqlite",
            )
            == "cli"
        )

    def test_resolve_target_accepts_positional_target(self) -> None:
        """Test target resolution accepts positional argument."""
        from types import MappingProxyType

        from sqlitch.cli.commands import deploy as deploy_module

        assert (
            deploy_module._resolve_target(
                option_value=None,
                configured_target=None,
                positional_targets=("db:sqlite:demo",),
                project_root=Path.cwd(),
                config_root=Path.cwd(),
                env=MappingProxyType({}),
                default_engine="sqlite",
            )
            == "db:sqlite:demo"
        )

    def test_resolve_target_rejects_both_option_and_positional(self) -> None:
        """Test target resolution rejects both option and positional."""
        from types import MappingProxyType

        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import deploy as deploy_module

        with pytest.raises(CommandError, match="either --target or a positional"):
            deploy_module._resolve_target(
                option_value="cli",
                configured_target=None,
                positional_targets=("db:sqlite:demo",),
                project_root=Path.cwd(),
                config_root=Path.cwd(),
                env=MappingProxyType({}),
                default_engine="sqlite",
            )

    def test_resolve_target_rejects_multiple_positional_targets(self) -> None:
        """Test target resolution rejects multiple positional targets."""
        from types import MappingProxyType

        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import deploy as deploy_module

        with pytest.raises(CommandError, match="Multiple positional targets"):
            deploy_module._resolve_target(
                option_value=None,
                configured_target=None,
                positional_targets=("db:sqlite:one", "db:sqlite:two"),
                project_root=Path.cwd(),
                config_root=Path.cwd(),
                env=MappingProxyType({}),
                default_engine="sqlite",
            )

    def test_resolve_target_requires_value(self) -> None:
        """Test target resolution requires a value."""
        from types import MappingProxyType

        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import deploy as deploy_module

        with pytest.raises(CommandError, match="must be provided"):
            deploy_module._resolve_target(
                option_value=None,
                configured_target=None,
                positional_targets=(),
                project_root=Path.cwd(),
                config_root=Path.cwd(),
                env=MappingProxyType({}),
                default_engine="sqlite",
            )

    def test_select_changes_by_change_filters(self) -> None:
        """Test change selection by change name filter."""
        from sqlitch.cli.commands import deploy as deploy_module

        first = self._make_change("one")
        second = self._make_change("two")
        plan = self._make_plan((first, second))

        selected = deploy_module._select_changes(plan=plan, to_change="two", to_tag=None)

        assert selected == (first, second)

    def test_select_changes_by_tag_filters(self) -> None:
        """Test change selection by tag filter."""
        from datetime import datetime, timezone

        from sqlitch.cli.commands import deploy as deploy_module

        first = self._make_change("one")
        second = self._make_change("two")
        tag = Tag(
            name="v1.0",
            change_ref=second.name,
            planner="Tester",
            tagged_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        plan = self._make_plan((first, second), (tag,))

        selected = deploy_module._select_changes(plan=plan, to_change=None, to_tag="v1.0")

        assert selected == (first, second)

    def test_select_changes_missing_change_raises(self) -> None:
        """Test change selection raises for missing change."""
        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import deploy as deploy_module

        plan = self._make_plan((self._make_change("one"),))

        with pytest.raises(CommandError, match="Unknown change"):
            deploy_module._select_changes(plan=plan, to_change="missing", to_tag=None)

    def test_select_changes_missing_tag_raises(self) -> None:
        """Test change selection raises for missing tag."""
        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import deploy as deploy_module

        plan = self._make_plan((self._make_change("one"),))

        with pytest.raises(CommandError, match="does not contain tag"):
            deploy_module._select_changes(plan=plan, to_change=None, to_tag="v1.0")

    def test_render_log_only_deploy_respects_quiet(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test log-only deploy respects quiet mode."""
        import click

        from sqlitch.cli.commands import deploy as deploy_module

        captured: list[str] = []
        monkeypatch.setattr(click, "echo", lambda message: captured.append(message))

        plan = self._make_plan((self._make_change("one"),))
        request = deploy_module._DeployRequest(
            project_root=tmp_path,
            config_root=tmp_path,
            env={},
            plan_path=tmp_path / "sqlitch.plan",
            plan=plan,
            target="db:sqlite:demo",
            to_change=None,
            to_tag=None,
            log_only=True,
            quiet=True,
            logger=self._make_logger(quiet=True),
            registry_override=None,
        )

        deploy_module._render_log_only_deploy(request, plan.changes)

        assert captured == []

    def test_render_log_only_deploy_outputs_messages(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test log-only deploy outputs messages when not quiet."""
        import click

        from sqlitch.cli.commands import deploy as deploy_module

        captured: list[str] = []
        monkeypatch.setattr(click, "echo", lambda message: captured.append(message))

        plan = self._make_plan((self._make_change("one"),))
        request = deploy_module._DeployRequest(
            project_root=tmp_path,
            config_root=tmp_path,
            env={},
            plan_path=tmp_path / "sqlitch.plan",
            plan=plan,
            target="db:sqlite:demo",
            to_change=None,
            to_tag=None,
            log_only=True,
            quiet=False,
            logger=self._make_logger(),
            registry_override=None,
        )

        deploy_module._render_log_only_deploy(request, ())

        assert "No changes available for deployment." in captured
        assert any("Log-only run" in line for line in captured)

    def test_build_emitter_obeys_quiet_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test emitter respects quiet flag."""
        import click

        from sqlitch.cli.commands import deploy as deploy_module

        captured: list[str] = []
        monkeypatch.setattr(click, "echo", lambda message: captured.append(message))

        loud = deploy_module._build_emitter(False)
        quiet = deploy_module._build_emitter(True)

        loud("hello")
        quiet("ignored")

        assert captured == ["hello"]


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click test runner."""
    return CliRunner()
