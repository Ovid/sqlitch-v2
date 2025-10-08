"""Functional tests for the ``sqlitch revert`` command.

These tests validate the revert command's ability to revert deployed changes
in reverse order, respecting tag boundaries and dependency constraints.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


@pytest.fixture
def project_with_deployed_changes(tmp_path: Path) -> Path:
    """Create a project with multiple deployed changes for revert testing."""
    project_dir = tmp_path / "revert_test"
    project_dir.mkdir()

    # Create plan file with multiple changes
    plan_content = """%syntax-version=1.0.0
%project=revert_test
%uri=https://example.com/revert_test

users 2025-01-01T12:00:00Z Alice <alice@example.com> # Initial user table
posts [users] 2025-01-02T12:00:00Z Alice <alice@example.com> # Posts table depends on users
comments [posts] 2025-01-03T12:00:00Z Alice <alice@example.com> # Comments depend on posts
"""
    (project_dir / "sqlitch.plan").write_text(plan_content)

    # Create config
    config_content = """[core]
\tengine = sqlite

[user]
\tname = Alice
\temail = alice@example.com
"""
    (project_dir / "sqlitch.conf").write_text(config_content)

    # Create script directories
    for dir_name in ["deploy", "revert", "verify"]:
        (project_dir / dir_name).mkdir()

    # Create deploy/revert/verify scripts for users
    (project_dir / "deploy" / "users.sql").write_text(
        """-- Deploy revert_test:users to sqlite

BEGIN;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE
);

COMMIT;
"""
    )

    (project_dir / "revert" / "users.sql").write_text(
        """-- Revert revert_test:users from sqlite

BEGIN;

DROP TABLE users;

COMMIT;
"""
    )

    (project_dir / "verify" / "users.sql").write_text(
        """-- Verify revert_test:users on sqlite

SELECT id, username FROM users WHERE 0 = 1;
"""
    )

    # Create deploy/revert/verify scripts for posts
    (project_dir / "deploy" / "posts.sql").write_text(
        """-- Deploy revert_test:posts to sqlite

BEGIN;

CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL
);

COMMIT;
"""
    )

    (project_dir / "revert" / "posts.sql").write_text(
        """-- Revert revert_test:posts from sqlite

BEGIN;

DROP TABLE posts;

COMMIT;
"""
    )

    (project_dir / "verify" / "posts.sql").write_text(
        """-- Verify revert_test:posts on sqlite

SELECT id, user_id, title FROM posts WHERE 0 = 1;
"""
    )

    # Create deploy/revert/verify scripts for comments
    (project_dir / "deploy" / "comments.sql").write_text(
        """-- Deploy revert_test:comments to sqlite

BEGIN;

CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts(id),
    content TEXT NOT NULL
);

COMMIT;
"""
    )

    (project_dir / "revert" / "comments.sql").write_text(
        """-- Revert revert_test:comments from sqlite

BEGIN;

DROP TABLE comments;

COMMIT;
"""
    )

    (project_dir / "verify" / "comments.sql").write_text(
        """-- Verify revert_test:comments on sqlite

SELECT id, post_id, content FROM comments WHERE 0 = 1;
"""
    )

    # Deploy all changes
    runner = CliRunner()
    target_db = project_dir / "test.db"

    original_cwd = os.getcwd()
    try:
        os.chdir(project_dir)
        result = runner.invoke(
            main,
            ["deploy", f"db:sqlite:{target_db}"],
        )
        assert result.exit_code == 0, f"Deploy failed: {result.output}"
    finally:
        os.chdir(original_cwd)

    return project_dir


class TestRevertAllChanges:
    """Test reverting all deployed changes."""

    def test_revert_all_changes_in_reverse_order(self, project_with_deployed_changes: Path) -> None:
        """Test that revert reverts all changes in reverse chronological order."""
        runner = CliRunner()
        project_dir = project_with_deployed_changes
        target_db = project_dir / "test.db"

        # Verify all tables exist before revert
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables_before = {row[0] for row in cursor.fetchall()}
        assert "users" in tables_before
        assert "posts" in tables_before
        assert "comments" in tables_before
        conn.close()

        # Run revert command
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["revert", f"db:sqlite:{target_db}", "-y"],
            )
        finally:
            os.chdir(original_cwd)

        # Should succeed
        assert result.exit_code == 0, f"Revert failed: {result.output}"
        assert "  - comments .. ok" in result.output
        assert "  - posts .. ok" in result.output
        assert "  - users .. ok" in result.output

        # Verify output shows reverse order (comments, then posts, then users)
        comments_idx = result.output.index("comments")
        posts_idx = result.output.index("posts")
        users_idx = result.output.index("users")
        assert comments_idx < posts_idx < users_idx

        # Verify all tables are gone
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
        )
        tables_after = {row[0] for row in cursor.fetchall()}
        conn.close()

        # Only registry tables should remain
        for table in ["users", "posts", "comments"]:
            assert table not in tables_after


class TestRevertToTag:
    """Test reverting to a specific tag boundary."""

    def test_revert_to_tag_stops_at_boundary(self, tmp_path: Path) -> None:
        """Test that revert --to-tag stops at the tag boundary."""
        project_dir = tmp_path / "tag_test"
        project_dir.mkdir()

        # Create plan with tag
        plan_content = """%syntax-version=1.0.0
%project=tag_test
%uri=https://example.com/tag_test

users 2025-01-01T12:00:00Z Alice <alice@example.com> # Initial user table
@v1.0 2025-01-02T12:00:00Z Alice <alice@example.com> # Version 1.0 release
posts [users] 2025-01-03T12:00:00Z Alice <alice@example.com> # Posts after v1.0
"""
        (project_dir / "sqlitch.plan").write_text(plan_content)

        # Create config
        config_content = """[core]
\tengine = sqlite

[user]
\tname = Alice
\temail = alice@example.com
"""
        (project_dir / "sqlitch.conf").write_text(config_content)

        # Create script directories and scripts
        for dir_name in ["deploy", "revert", "verify"]:
            (project_dir / dir_name).mkdir()

        # Users scripts
        (project_dir / "deploy" / "users.sql").write_text(
            """-- Deploy tag_test:users to sqlite
BEGIN;
CREATE TABLE users (id INTEGER PRIMARY KEY);
COMMIT;
"""
        )
        (project_dir / "revert" / "users.sql").write_text(
            """-- Revert tag_test:users from sqlite
BEGIN;
DROP TABLE users;
COMMIT;
"""
        )
        (project_dir / "verify" / "users.sql").write_text(
            """-- Verify tag_test:users on sqlite
SELECT id FROM users WHERE 0 = 1;
"""
        )

        # Posts scripts
        (project_dir / "deploy" / "posts.sql").write_text(
            """-- Deploy tag_test:posts to sqlite
BEGIN;
CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id));
COMMIT;
"""
        )
        (project_dir / "revert" / "posts.sql").write_text(
            """-- Revert tag_test:posts from sqlite
BEGIN;
DROP TABLE posts;
COMMIT;
"""
        )
        (project_dir / "verify" / "posts.sql").write_text(
            """-- Verify tag_test:posts on sqlite
SELECT id, user_id FROM posts WHERE 0 = 1;
"""
        )

        # Deploy all changes
        runner = CliRunner()
        target_db = project_dir / "test.db"

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
            assert deploy_result.exit_code == 0

            # Revert to tag v1.0 (should only revert posts, not users)
            revert_result = runner.invoke(
                main,
                ["revert", f"db:sqlite:{target_db}", "--to-tag", "v1.0", "-y"],
            )
        finally:
            os.chdir(original_cwd)

        # Should succeed
        assert revert_result.exit_code == 0
        assert "  - posts .. ok" in revert_result.output
        assert "  - users .. ok" not in revert_result.output

        # Verify posts table is gone but users remains
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "users" in tables
        assert "posts" not in tables


class TestRevertToChange:
    """Test reverting to a specific change."""

    def test_revert_to_change_name(self, project_with_deployed_changes: Path) -> None:
        """Test that revert --to-change reverts up to specified change."""
        runner = CliRunner()
        project_dir = project_with_deployed_changes
        target_db = project_dir / "test.db"

        # Revert to posts (should revert comments only, keep posts and users)
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["revert", f"db:sqlite:{target_db}", "--to-change", "posts", "-y"],
            )
        finally:
            os.chdir(original_cwd)

        # Should succeed
        assert result.exit_code == 0
        assert "  - comments .. ok" in result.output
        assert "  - posts .. ok" not in result.output
        assert "  - users .. ok" not in result.output

        # Verify comments is gone but posts and users remain
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "users" in tables
        assert "posts" in tables
        assert "comments" not in tables


class TestRevertScriptExecution:
    """Test revert script execution details."""

    def test_revert_executes_scripts_in_transaction(
        self, project_with_deployed_changes: Path
    ) -> None:
        """Test that revert scripts are executed within transactions."""
        runner = CliRunner()
        project_dir = project_with_deployed_changes
        target_db = project_dir / "test.db"

        # Run revert (revert all changes)
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["revert", f"db:sqlite:{target_db}", "-y"],
            )
        finally:
            os.chdir(original_cwd)

        assert result.exit_code == 0

        # Verify registry events were recorded (should have 3 revert events)
        registry_db = project_dir / "sqitch.db"
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event, change FROM events WHERE event = 'revert' ORDER BY committed_at ASC"
        )
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 3
        # Changes should be reverted in reverse order: comments, posts, users
        assert [row[1] for row in rows] == ["comments", "posts", "users"]


class TestRevertConfirmationPrompt:
    """Ensure revert prompts the user unless bypassed."""

    def test_prompts_and_aborts_when_declined(
        self, project_with_deployed_changes: Path
    ) -> None:
        runner = CliRunner()
        project_dir = project_with_deployed_changes
        target_db = project_dir / "test.db"

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                [
                    "revert",
                    f"db:sqlite:{target_db}",
                ],
                input="n\n",
            )
        finally:
            os.chdir(original_cwd)

        assert result.exit_code == 1, result.output
        assert "[y/N]:" in result.output
        assert "Revert aborted by user." in result.output

        conn = sqlite3.connect(target_db)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
            )
            assert cursor.fetchone() is not None, "Comments table should still exist"
        finally:
            conn.close()

    def test_yes_flag_skips_prompt_and_executes(
        self, project_with_deployed_changes: Path
    ) -> None:
        runner = CliRunner()
        project_dir = project_with_deployed_changes
        target_db = project_dir / "test.db"

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                [
                    "revert",
                    f"db:sqlite:{target_db}",
                    "-y",
                ],
            )
        finally:
            os.chdir(original_cwd)

        assert result.exit_code == 0, result.output
        assert "[y/N]:" not in result.output
        assert "- comments" in result.output
        assert "- posts" in result.output
        assert "- users" in result.output

    def test_revert_removes_from_registry(self, project_with_deployed_changes: Path) -> None:
        """Test that revert removes change from registry changes table."""
        runner = CliRunner()
        project_dir = project_with_deployed_changes
        target_db = project_dir / "test.db"
        registry_db = project_dir / "sqitch.db"

        # Verify comments is in registry before revert
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT change FROM changes WHERE change = 'comments'")
        assert cursor.fetchone() is not None
        conn.close()

        # Run revert (revert to posts, which reverts comments)
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                ["revert", f"db:sqlite:{target_db}", "--to-change", "posts", "-y"],
            )
        finally:
            os.chdir(original_cwd)

        assert result.exit_code == 0

        # Verify comments is no longer in changes table
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT change FROM changes WHERE change = 'comments'")
        assert cursor.fetchone() is None
        conn.close()

        # But posts and users should still be there
        conn = sqlite3.connect(registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT change FROM changes ORDER BY committed_at")
        remaining = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "users" in remaining
        assert "posts" in remaining
        assert "comments" not in remaining

    def test_revert_fails_on_script_error(self, tmp_path: Path) -> None:
        """Test that revert rolls back on script execution error."""
        project_dir = tmp_path / "error_test"
        project_dir.mkdir()

        # Create plan
        plan_content = """%syntax-version=1.0.0
%project=error_test
%uri=https://example.com/error_test

users 2025-01-01T12:00:00Z Alice <alice@example.com> # User table
"""
        (project_dir / "sqlitch.plan").write_text(plan_content)

        # Create config
        config_content = """[core]
\tengine = sqlite

[user]
\tname = Alice
\temail = alice@example.com
"""
        (project_dir / "sqlitch.conf").write_text(config_content)

        # Create script directories
        for dir_name in ["deploy", "revert", "verify"]:
            (project_dir / dir_name).mkdir()

        # Create deploy script
        (project_dir / "deploy" / "users.sql").write_text(
            """-- Deploy error_test:users to sqlite
BEGIN;
CREATE TABLE users (id INTEGER PRIMARY KEY);
COMMIT;
"""
        )

        # Create INVALID revert script (syntax error)
        (project_dir / "revert" / "users.sql").write_text(
            """-- Revert error_test:users from sqlite
BEGIN;
THIS IS NOT VALID SQL;
COMMIT;
"""
        )

        (project_dir / "verify" / "users.sql").write_text(
            """-- Verify error_test:users on sqlite
SELECT id FROM users WHERE 0 = 1;
"""
        )

        # Deploy the change
        runner = CliRunner()
        target_db = project_dir / "test.db"

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            deploy_result = runner.invoke(
                main,
                ["deploy", f"db:sqlite:{target_db}"],
            )
            assert deploy_result.exit_code == 0

            # Attempt revert (should fail)
            revert_result = runner.invoke(
                main,
                ["revert", f"db:sqlite:{target_db}", "-y"],
            )
        finally:
            os.chdir(original_cwd)

        # Should fail with non-zero exit code
        assert revert_result.exit_code != 0
        assert "error" in revert_result.output.lower() or "fail" in revert_result.output.lower()

        # Verify users table still exists (rollback worked)
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None
        conn.close()


class TestRevertValidation:
    """Test revert command validation and error handling."""

    def test_revert_requires_target(self, tmp_path: Path) -> None:
        """Test that revert requires a target to be specified."""
        project_dir = tmp_path / "no_target"
        project_dir.mkdir()

        # Create minimal project with init
        runner = CliRunner()
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            # Init to create proper project structure
            init_result = runner.invoke(main, ["init", "no_target", "--engine", "sqlite"])
            assert init_result.exit_code == 0

            # Try to revert without target
            result = runner.invoke(main, ["revert"])
        finally:
            os.chdir(original_cwd)

        # Should fail with error about missing target
        assert result.exit_code != 0
        assert "target" in result.output.lower()

    def test_revert_rejects_both_to_change_and_to_tag(
        self, project_with_deployed_changes: Path
    ) -> None:
        """Test that revert rejects both --to-change and --to-tag."""
        runner = CliRunner()
        project_dir = project_with_deployed_changes
        target_db = project_dir / "test.db"

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                [
                    "revert",
                    f"db:sqlite:{target_db}",
                    "--to-change",
                    "posts",
                    "--to-tag",
                    "v1.0",
                    "-y",
                ],
            )
        finally:
            os.chdir(original_cwd)

        # Should fail with error about conflicting options
        assert result.exit_code != 0
        assert (
            "cannot combine" in result.output.lower()
            or "mutually exclusive" in result.output.lower()
        )

    def test_revert_validates_change_exists(self, project_with_deployed_changes: Path) -> None:
        """Test that revert validates the specified change exists in the plan."""
        runner = CliRunner()
        project_dir = project_with_deployed_changes
        target_db = project_dir / "test.db"

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = runner.invoke(
                main,
                [
                    "revert",
                    f"db:sqlite:{target_db}",
                    "--to-change",
                    "nonexistent",
                    "-y",
                ],
            )
        finally:
            os.chdir(original_cwd)

        # Should fail with error about change not found
        assert result.exit_code != 0
        assert "nonexistent" in result.output


class TestRevertConfirmation:
    """Test revert confirmation prompts."""

    def test_revert_requires_confirmation(self, project_with_deployed_changes: Path) -> None:
        """Test that revert requires -y flag or interactive confirmation."""
        runner = CliRunner()
        project_dir = project_with_deployed_changes
        target_db = project_dir / "test.db"

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            # Run without -y flag and without stdin input
            result = runner.invoke(
                main,
                ["revert", f"db:sqlite:{target_db}"],
                input="n\n",  # Respond 'no' to confirmation
            )
        finally:
            os.chdir(original_cwd)

        # Should abort without making changes
        assert result.exit_code != 0 or "aborted" in result.output.lower()
