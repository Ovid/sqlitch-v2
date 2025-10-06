"""Functional tests for verify command."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


class TestVerifyExecution:
    """Test verify command execution."""

    def test_executes_verify_scripts_for_deployed_changes(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Verify should execute verify scripts for all deployed changes."""
        # Setup: Create project and deploy a change
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
        
        # Create deploy script
        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);\n"
            "COMMIT;\n"
        )
        
        # Create verify script
        verify_dir = project_dir / "verify"
        verify_dir.mkdir()
        (verify_dir / "users.sql").write_text(
            "-- Verify flipr:users on sqlite\n"
            "BEGIN;\n"
            "SELECT id, name FROM users WHERE 0=1;\n"
            "ROLLBACK;\n"
        )
        
        target_db = tmp_path / "flipr_test.db"
        
        # Deploy first
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert deploy_result.exit_code == 0, "Deploy should succeed"
        
        # Execute: Verify
        try:
            os.chdir(project_dir)
            verify_result = runner.invoke(
                main,
                ["verify", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        # Verify: Should execute verify script successfully
        assert verify_result.exit_code == 0, \
            f"Verify should succeed when verify script passes\nOutput: {verify_result.output}"
        assert "users" in verify_result.output, \
            f"Should show verified change\nOutput: {verify_result.output}"

    def test_reports_success_for_each_change(self, runner: CliRunner, tmp_path: Path) -> None:
        """Verify should report OK for each successfully verified change."""
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
        verify_dir = project_dir / "verify"
        verify_dir.mkdir()
        
        # Create deploy and verify scripts
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        (verify_dir / "users.sql").write_text(
            "-- Verify flipr:users on sqlite\n"
            "BEGIN;\n"
            "SELECT id FROM users WHERE 0=1;\n"
            "ROLLBACK;\n"
        )
        
        (deploy_dir / "posts.sql").write_text(
            "-- Deploy flipr:posts to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE posts (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        (verify_dir / "posts.sql").write_text(
            "-- Verify flipr:posts on sqlite\n"
            "BEGIN;\n"
            "SELECT id FROM posts WHERE 0=1;\n"
            "ROLLBACK;\n"
        )
        
        target_db = tmp_path / "flipr_test.db"
        
        # Deploy both changes
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            runner.invoke(main, ["deploy", f"db:sqlite:{target_db}"])
        finally:
            os.chdir(original_cwd)
        
        # Execute: Verify
        try:
            os.chdir(project_dir)
            verify_result = runner.invoke(
                main,
                ["verify", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        # Verify: Both changes should show as OK
        output = verify_result.output
        assert "users" in output, "Should show users verified"
        assert "posts" in output, "Should show posts verified"
        assert verify_result.exit_code == 0, "Should exit 0 when all pass"

    def test_reports_failure_with_error_details(self, runner: CliRunner, tmp_path: Path) -> None:
        """Verify should report NOT OK with details when a verify script fails."""
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
        verify_dir = project_dir / "verify"
        verify_dir.mkdir()
        
        # Create deploy script
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        
        # Create verify script that will fail (references missing column)
        (verify_dir / "users.sql").write_text(
            "-- Verify flipr:users on sqlite\n"
            "BEGIN;\n"
            "SELECT id, nonexistent_column FROM users WHERE 0=1;\n"
            "ROLLBACK;\n"
        )
        
        target_db = tmp_path / "flipr_test.db"
        
        # Deploy
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            runner.invoke(main, ["deploy", f"db:sqlite:{target_db}"])
        finally:
            os.chdir(original_cwd)
        
        # Execute: Verify
        try:
            os.chdir(project_dir)
            verify_result = runner.invoke(
                main,
                ["verify", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        # Verify: Should report failure
        assert verify_result.exit_code == 1, \
            f"Verify should exit 1 when verification fails\nOutput: {verify_result.output}"
        # Should mention the failed change
        assert "users" in verify_result.output.lower(), \
            f"Should mention failed change\nOutput: {verify_result.output}"

    def test_exit_code_zero_if_all_pass(self, runner: CliRunner, tmp_path: Path) -> None:
        """Verify should exit 0 when all verify scripts pass."""
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
        verify_dir = project_dir / "verify"
        verify_dir.mkdir()
        
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);\n"
            "COMMIT;\n"
        )
        
        # Verify script that will pass
        (verify_dir / "users.sql").write_text(
            "-- Verify flipr:users on sqlite\n"
            "BEGIN;\n"
            "SELECT id, name FROM users WHERE 0=1;\n"
            "ROLLBACK;\n"
        )
        
        target_db = tmp_path / "flipr_test.db"
        
        # Deploy
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            runner.invoke(main, ["deploy", f"db:sqlite:{target_db}"])
        finally:
            os.chdir(original_cwd)
        
        # Execute: Verify
        try:
            os.chdir(project_dir)
            verify_result = runner.invoke(
                main,
                ["verify", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        # Verify: Exit code 0 when all pass
        assert verify_result.exit_code == 0, \
            "Verify should exit 0 when all verify scripts pass"

    def test_exit_code_one_if_any_fail(self, runner: CliRunner, tmp_path: Path) -> None:
        """Verify should exit 1 if any verify script fails."""
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
        verify_dir = project_dir / "verify"
        verify_dir.mkdir()
        
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
            "CREATE TABLE posts (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )
        
        # First verify passes
        (verify_dir / "users.sql").write_text(
            "-- Verify flipr:users on sqlite\n"
            "BEGIN;\n"
            "SELECT id FROM users WHERE 0=1;\n"
            "ROLLBACK;\n"
        )
        
        # Second verify fails
        (verify_dir / "posts.sql").write_text(
            "-- Verify flipr:posts on sqlite\n"
            "BEGIN;\n"
            "SELECT id, missing_column FROM posts WHERE 0=1;\n"
            "ROLLBACK;\n"
        )
        
        target_db = tmp_path / "flipr_test.db"
        
        # Deploy both
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            runner.invoke(main, ["deploy", f"db:sqlite:{target_db}"])
        finally:
            os.chdir(original_cwd)
        
        # Execute: Verify
        try:
            os.chdir(project_dir)
            verify_result = runner.invoke(
                main,
                ["verify", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        # Verify: Exit code 1 if any fail
        assert verify_result.exit_code == 1, \
            "Verify should exit 1 if any verification fails"


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click test runner."""
    return CliRunner()
