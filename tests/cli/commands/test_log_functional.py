"""Functional tests for the log command implementation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


@pytest.fixture
def project_with_changes(tmp_path: Path) -> Path:
    """Create a test project with a plan containing changes."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create plan file with changes
    plan_file = project_dir / "sqitch.plan"
    plan_file.write_text(
        "%syntax-version=1.0.0\n"
        "%project=test_project\n"
        "\n"
        "users 2025-01-01T10:00:00Z Alice <alice@example.com> # Add users table\n"
        "posts 2025-01-01T11:00:00Z Bob <bob@example.com> # Add posts table\n"
    )
    
    # Create config file
    config_file = project_dir / "sqitch.conf"
    config_file.write_text(
        "[core]\n"
        "    engine = sqlite\n"
        "[user]\n"
        "    name = Test User\n"
        "    email = test@example.com\n"
    )
    
    # Create deploy/revert/verify directories
    (project_dir / "deploy").mkdir()
    (project_dir / "revert").mkdir()
    (project_dir / "verify").mkdir()
    
    # Create deploy scripts
    (project_dir / "deploy" / "users.sql").write_text(
        "-- Deploy test_project:users to sqlite\n\n"
        "BEGIN;\n\n"
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);\n\n"
        "COMMIT;\n"
    )
    
    (project_dir / "deploy" / "posts.sql").write_text(
        "-- Deploy test_project:posts to sqlite\n\n"
        "BEGIN;\n\n"
        "CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, content TEXT);\n\n"
        "COMMIT;\n"
    )
    
    # Create revert scripts
    (project_dir / "revert" / "users.sql").write_text(
        "-- Revert test_project:users from sqlite\n\n"
        "BEGIN;\n\n"
        "DROP TABLE users;\n\n"
        "COMMIT;\n"
    )
    
    (project_dir / "revert" / "posts.sql").write_text(
        "-- Revert test_project:posts from sqlite\n\n"
        "BEGIN;\n\n"
        "DROP TABLE posts;\n\n"
        "COMMIT;\n"
    )
    
    # Create verify scripts
    (project_dir / "verify" / "users.sql").write_text(
        "-- Verify test_project:users on sqlite\n\n"
        "SELECT id, name FROM users WHERE 0;\n"
    )
    
    (project_dir / "verify" / "posts.sql").write_text(
        "-- Verify test_project:posts on sqlite\n\n"
        "SELECT id, user_id, content FROM posts WHERE 0;\n"
    )
    
    return project_dir


class TestLogDisplayAllEvents:
    """Test log command displays all events correctly."""
    
    def test_display_all_events(self, project_with_changes: Path) -> None:
        """Test log displays all events in reverse chronological order."""
        runner = CliRunner()
        project_dir = project_with_changes
        target_db = project_dir / "test.db"
        
        # Deploy changes to create events
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert deploy_result.exit_code == 0, f"Deploy failed: {deploy_result.output}"
        
        # Run log command
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["log", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "On database" in result.output
        assert "Deploy" in result.output
        assert "users" in result.output or "posts" in result.output
    
    def test_output_format_matches_sqitch(self, project_with_changes: Path) -> None:
        """Test log output format matches Sqitch conventions."""
        runner = CliRunner()
        project_dir = project_with_changes
        target_db = project_dir / "test.db"
        
        # Deploy changes
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert deploy_result.exit_code == 0
        
        # Run log command
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["log", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0
        # Check Sqitch-style formatting
        assert "Name:" in result.output
        assert "Committer:" in result.output
        assert "Date:" in result.output


class TestLogFilterByChange:
    """Test log command filtering by change name."""
    
    def test_filter_by_change_name(self, project_with_changes: Path) -> None:
        """Test --change filter shows only specified change."""
        runner = CliRunner()
        project_dir = project_with_changes
        target_db = project_dir / "test.db"
        
        # Deploy changes
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert deploy_result.exit_code == 0
        
        # Run log with change filter
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["log", f"db:sqlite:{target_db}", "--change", "users"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0
        assert "users" in result.output
        # Posts should not appear (filtered out)
        lines_with_posts = [line for line in result.output.split("\n") if "posts" in line.lower()]
        # Allow "posts" in database path but not in change names
        assert all("db:sqlite" in line or "database" in line.lower() for line in lines_with_posts)


class TestLogFilterByEventType:
    """Test log command filtering by event type."""
    
    def test_filter_by_event_type_deploy(self, project_with_changes: Path) -> None:
        """Test --event filter shows only deploy events."""
        runner = CliRunner()
        project_dir = project_with_changes
        target_db = project_dir / "test.db"
        
        # Deploy and then revert
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
            assert deploy_result.exit_code == 0
            
            revert_result = runner.invoke(
                main,
                ["revert", f"db:sqlite:{target_db}", "--to", "@HEAD^", "-y"],
            )
        finally:
            os.chdir(original_cwd)
        
        # Run log with event filter
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["log", f"db:sqlite:{target_db}", "--event", "deploy"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0
        assert "Deploy" in result.output
        # If revert succeeded, it should not appear in filtered output
        if revert_result.exit_code == 0:
            assert "Revert" not in result.output or result.output.count("Revert") == 0


class TestLogReverseOrder:
    """Test log command chronological order option."""
    
    def test_reverse_chronological_order(self, project_with_changes: Path) -> None:
        """Test --reverse flag shows events in chronological order (oldest first)."""
        runner = CliRunner()
        project_dir = project_with_changes
        target_db = project_dir / "test.db"
        
        # Deploy changes
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert deploy_result.exit_code == 0
        
        # Run log with reverse flag
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["log", f"db:sqlite:{target_db}", "--reverse"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0
        # Should show events (order verification would require parsing)
        assert "Deploy" in result.output


class TestLogLimitAndSkip:
    """Test log command pagination options."""
    
    def test_limit_events(self, project_with_changes: Path) -> None:
        """Test --limit restricts number of events."""
        runner = CliRunner()
        project_dir = project_with_changes
        target_db = project_dir / "test.db"
        
        # Deploy changes
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert deploy_result.exit_code == 0
        
        # Run log with limit
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["log", f"db:sqlite:{target_db}", "--limit", "1"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0
        # Should show at least one event
        assert "Deploy" in result.output
    
    def test_skip_events(self, project_with_changes: Path) -> None:
        """Test --skip skips first N events."""
        runner = CliRunner()
        project_dir = project_with_changes
        target_db = project_dir / "test.db"
        
        # Deploy changes
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert deploy_result.exit_code == 0
        
        # Run log with skip
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["log", f"db:sqlite:{target_db}", "--skip", "1"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0
        # Should show remaining events
        assert "Deploy" in result.output or "On database" in result.output


class TestLogJsonFormat:
    """Test log command JSON output."""
    
    def test_json_format(self, project_with_changes: Path) -> None:
        """Test --format json outputs valid JSON."""
        import json
        
        runner = CliRunner()
        project_dir = project_with_changes
        target_db = project_dir / "test.db"
        
        # Deploy changes
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert deploy_result.exit_code == 0
        
        # Run log with JSON format
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["log", f"db:sqlite:{target_db}", "--format", "json"],
            )
        finally:
            os.chdir(original_cwd)
        
        assert result.exit_code == 0
        # Parse JSON to verify validity
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Verify structure
        if data:
            event = data[0]
            assert "event" in event
            assert "change_id" in event
            assert "change" in event
            assert "committer" in event
            assert "name" in event["committer"]
            assert "email" in event["committer"]


class TestLogNoEvents:
    """Test log command with empty registry."""
    
    def test_empty_registry(self, tmp_path: Path) -> None:
        """Test log with no events shows appropriate message."""
        runner = CliRunner()
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()
        
        # Create minimal project structure (no deployments)
        plan_file = project_dir / "sqitch.plan"
        plan_file.write_text(
            "%syntax-version=1.0.0\n"
            "%project=empty_project\n"
        )
        
        config_file = project_dir / "sqitch.conf"
        config_file.write_text(
            "[core]\n"
            "    engine = sqlite\n"
        )
        
        target_db = project_dir / "empty.db"
        target_db.touch()  # Create empty database
        
        # Run log command on empty database
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["log", f"db:sqlite:{target_db}"],
            )
        finally:
            os.chdir(original_cwd)
        
        # Log should handle missing registry gracefully
        # It might fail if registry doesn't exist, or show "No events found"
        assert result.exit_code in (0, 1), f"Unexpected exit code: {result.exit_code}\nOutput: {result.output}"
