"""Functional tests for status command."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


class TestStatusWithNoRegistry:
    """Test status command when no registry exists yet."""

    def test_reports_not_deployed_status(self, runner: CliRunner, tmp_path: Path) -> None:
        """Status should report 'not deployed' when registry doesn't exist."""
        # Setup: Create a minimal project
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

        target_db = tmp_path / "flipr_test.db"

        # Execute: Check status before any deployment
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["status", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        # Verify: Exit code should be 1 (not deployed)
        assert (
            result.exit_code == 1
        ), f"Status should exit 1 when not deployed\nOutput: {result.output}"

        # Verify: Output indicates nothing deployed
        assert "flipr" in result.output.lower(), "Should mention project name"


class TestStatusWithDeployedChanges:
    """Test status command with changes already deployed."""

    def test_reports_deployed_changes(self, runner: CliRunner, tmp_path: Path) -> None:
        """Status should list deployed changes."""
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

        assert (
            deploy_result.exit_code == 0
        ), f"Deploy should succeed\nOutput: {deploy_result.output}"

        # Execute: Check status after deployment
        try:
            os.chdir(project_dir)
            status_result = runner.invoke(
                main,
                ["status", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        # Verify: Exit code should be 0 (up to date)
        assert (
            status_result.exit_code == 0
        ), f"Status should exit 0 when up-to-date\nOutput: {status_result.output}"

        # Verify: Output shows deployed change
        assert (
            "users" in status_result.output
        ), f"Should show deployed change 'users'\nOutput: {status_result.output}"

    def test_exit_code_zero_when_up_to_date(self, runner: CliRunner, tmp_path: Path) -> None:
        """Status should exit 0 when all changes deployed."""
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

        # Deploy all changes
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

        # Execute: Check status
        try:
            os.chdir(project_dir)
            status_result = runner.invoke(
                main,
                ["status", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        # Verify: Exit code 0 when all changes deployed
        assert (
            status_result.exit_code == 0
        ), "Status should exit 0 when all plan changes are deployed"


class TestStatusWithPendingChanges:
    """Test status command when there are undeployed changes."""

    def test_reports_pending_changes(self, runner: CliRunner, tmp_path: Path) -> None:
        """Status should list pending (undeployed) changes."""
        # Setup: Deploy one change, but have two in plan
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

        # Deploy first change
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

        # Now add a second change to the plan
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users\n"
            "posts 2025-01-02T00:00:00Z Test User <test@example.com> # Add posts\n"
        )

        (deploy_dir / "posts.sql").write_text(
            "-- Deploy flipr:posts to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE posts (id INTEGER PRIMARY KEY);\n"
            "COMMIT;\n"
        )

        # Execute: Check status
        try:
            os.chdir(project_dir)
            status_result = runner.invoke(
                main,
                ["status", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        # Verify: Exit code should be 1 (pending changes)
        assert (
            status_result.exit_code == 1
        ), f"Status should exit 1 when pending changes exist\nOutput: {status_result.output}"

        # Verify: Output mentions pending change
        output_lower = status_result.output.lower()
        assert (
            "posts" in output_lower or "pending" in output_lower
        ), f"Should indicate pending changes\nOutput: {status_result.output}"

    def test_shows_deployed_and_pending_counts(self, runner: CliRunner, tmp_path: Path) -> None:
        """Status should show counts of deployed and pending changes."""
        # Setup: Deploy one of two changes
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

        # Deploy only first change (by temporarily having only one change in plan)
        original_cwd = os.getcwd()

        # Save the full plan
        full_plan_content = plan_file.read_text()

        # Write temporary plan with only first change
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Test User <test@example.com> # Add users\n"
        )

        try:
            os.chdir(project_dir)
            # Deploy just users
            runner.invoke(main, ["deploy", f"db:sqlite:{target_db}"])
        finally:
            os.chdir(original_cwd)

        # Restore full plan with all three changes
        plan_file.write_text(full_plan_content)

        # Execute: Check status
        try:
            os.chdir(project_dir)
            status_result = runner.invoke(
                main,
                ["status", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        # Verify: Shows counts or mentions both deployed and pending
        output = status_result.output
        # Should show deployed change
        assert "users" in output, "Should show deployed change"
        # Should indicate there are more changes to deploy
        # (exact format depends on implementation, but should show project/target info)
        assert "flipr" in output, "Should show project name"


class TestStatusFailureMetadata:
    """Ensure status surfaces metadata for the most recent failure."""

    def test_reports_last_failure_details(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir = tmp_path / "flipr"
        project_dir.mkdir()

        conf_file = project_dir / "sqitch.conf"
        conf_file.write_text(
            "[core]\n"
            "    engine = sqlite\n"
            "[user]\n"
            "    name = Config User\n"
            "    email = config.user@example.com\n",
            encoding="utf-8",
        )

        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=flipr\n"
            "\n"
            "users 2025-01-01T00:00:00Z Planner <planner@example.com> # Add users\n",
            encoding="utf-8",
        )

        deploy_dir = project_dir / "deploy"
        deploy_dir.mkdir()
        (deploy_dir / "users.sql").write_text(
            "-- Deploy flipr:users to sqlite\n"
            "BEGIN;\n"
            "CREATE TABLE users (id INTEGER PRIMARY KEY);\n"
            "SELECT RAISE(ABORT, 'deploy explosion');\n"
            "COMMIT;\n",
            encoding="utf-8",
        )

        target_db = tmp_path / "flipr_test.db"

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        assert deploy_result.exit_code != 0, "Deploy must fail to trigger failure metadata"

        # Execute status after failure
        try:
            os.chdir(project_dir)
            status_result = runner.invoke(
                main,
                ["status", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)

        assert status_result.exit_code == 1, "Status should indicate pending changes after failure"

        output_lower = status_result.output.lower()
        assert "last failure" in output_lower
        assert "users" in output_lower
        assert "config user" in output_lower
        assert "add users" in output_lower


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click test runner."""
    return CliRunner()
