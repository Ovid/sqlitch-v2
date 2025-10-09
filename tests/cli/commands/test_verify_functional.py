"""Functional tests for verify command."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from sqlitch.cli.commands import CommandError
from sqlitch.cli.commands.verify import (
    _execute_sqlite_verify_script,
    _resolve_engine_target,
    _resolve_sqlite_workspace_uri,
    _strip_sqlite_uri_prefix,
    _load_plan,
)
from sqlitch.config import resolver as config_resolver


@contextmanager
def pushd(path: Path):
    original_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original_cwd)


def setup_project(
    tmp_path: Path,
    *,
    changes: tuple[str, ...],
    create_verify_scripts: bool = True,
) -> tuple[Path, Path]:
    """Create a minimal SQLitch project with deploy/verify scripts."""

    project_dir = tmp_path / "flipr"
    project_dir.mkdir()

    (project_dir / "sqitch.conf").write_text("[core]\n    engine = sqlite\n")

    plan_lines = ["%syntax-version=1.0.0\n", "%project=flipr\n", "\n"]
    for index, change in enumerate(changes, start=1):
        plan_lines.append(
            f"{change} 2025-01-{index:02d}T00:00:00Z Test User <test@example.com> # {change.capitalize()}\n"
        )
    (project_dir / "sqitch.plan").write_text("".join(plan_lines))

    deploy_dir = project_dir / "deploy"
    verify_dir = project_dir / "verify"
    deploy_dir.mkdir()
    verify_dir.mkdir()

    for change in changes:
        (deploy_dir / f"{change}.sql").write_text(
            f"-- Deploy flipr:{change} to sqlite\n"
            "BEGIN;\n"
            f"CREATE TABLE {change} (id INTEGER PRIMARY KEY, note TEXT);\n"
            "COMMIT;\n"
        )

        if create_verify_scripts:
            (verify_dir / f"{change}.sql").write_text(
                f"-- Verify flipr:{change} on sqlite\n"
                "BEGIN;\n"
                f"SELECT id FROM {change} WHERE 0=1;\n"
                "ROLLBACK;\n"
            )

    target_db = tmp_path / "flipr_test.db"
    return project_dir, target_db


def deploy_project(runner: CliRunner, project_dir: Path, target_uri: str) -> None:
    with pushd(project_dir):
        deploy_result = runner.invoke(main, ["deploy", target_uri])
    assert deploy_result.exit_code == 0, deploy_result.output


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
        assert (
            verify_result.exit_code == 0
        ), f"Verify should succeed when verify script passes\nOutput: {verify_result.output}"
        assert (
            "users" in verify_result.output
        ), f"Should show verified change\nOutput: {verify_result.output}"
        assert "Verify successful" in verify_result.output

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
        assert "Verify successful" in output

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
        assert (
            verify_result.exit_code == 1
        ), f"Verify should exit 1 when verification fails\nOutput: {verify_result.output}"
        # Should mention the failed change
        assert (
            "users" in verify_result.output.lower()
        ), f"Should mention failed change\nOutput: {verify_result.output}"
        assert "Verify Summary Report" in verify_result.output
        assert "Changes: 1" in verify_result.output
        assert "Errors:  1" in verify_result.output
        assert "Verify failed" in verify_result.output

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
        assert verify_result.exit_code == 0, "Verify should exit 0 when all verify scripts pass"
        assert "Verify successful" in verify_result.output

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

        # Verify: Exit code 1 if any fail and summary is printed
        output = verify_result.output
        assert verify_result.exit_code == 1, "Verify should exit 1 if any verification fails"
        assert "  * users .. ok" in output
        assert "  # posts .. NOT OK" in output
        assert "Verify Summary Report" in output
        assert "Changes: 2" in output
        assert "Errors:  1" in output
        assert "Verify failed" in output

    def test_reports_all_failures_before_summary(self, runner: CliRunner, tmp_path: Path) -> None:
        """Verify should continue through all failures and report a summary."""

        project_dir, target_db = setup_project(tmp_path, changes=("users", "posts"))

        # Overwrite verify scripts so both fail
        for change in ("users", "posts"):
            (project_dir / "verify" / f"{change}.sql").write_text(
                f"-- Verify flipr:{change} on sqlite\n"
                "BEGIN;\n"
                f"SELECT nonexistent_column FROM {change};\n"
                "ROLLBACK;\n"
            )

        deploy_project(runner, project_dir, f"db:sqlite:{target_db}")

        with pushd(project_dir):
            result = runner.invoke(main, ["verify", f"db:sqlite:{target_db}"])

        output = result.output
        assert result.exit_code == 1, output
        assert "  # users .. NOT OK" in output
        assert "  # posts .. NOT OK" in output
        assert output.index("  # users .. NOT OK") < output.index("  # posts .. NOT OK")
        assert "Verify Summary Report" in output
        assert "Changes: 2" in output
        assert "Errors:  2" in output
        assert "Verify failed" in output


class TestVerifyUnimplementedOptions:
    """Ensure unimplemented verify flags raise informative errors."""

    @pytest.mark.parametrize(
        "args,message",
        [
            (["--log-only"], "--log-only is not implemented yet."),
            (["--to-change", "users"], "--to-change is not implemented yet."),
            (["--to-tag", "users"], "--to-tag is not implemented yet."),
            (["--event", "deploy"], "--event is not implemented yet."),
            (["--mode", "all"], "--mode is not implemented yet."),
        ],
    )
    def test_unimplemented_option_errors(
        self, runner: CliRunner, args: list[str], message: str
    ) -> None:
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["verify", *args])

            assert result.exit_code == 1
            assert message in result.output


class TestVerifyAdditionalScenarios:
    """Additional edge cases to improve coverage for verify command."""

    def test_reports_skip_when_verify_script_missing(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        project_dir, target_db = setup_project(
            tmp_path, changes=("users",), create_verify_scripts=False
        )

        deploy_project(runner, project_dir, f"db:sqlite:{target_db}")

        with pushd(project_dir):
            result = runner.invoke(main, ["verify", f"db:sqlite:{target_db}"])

        assert result.exit_code == 0, result.output
        assert "  # users .. SKIP (no verify script)" in result.output
        assert "Verify successful" in result.output

    def test_handles_absence_of_deployed_changes(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir, target_db = setup_project(tmp_path, changes=())

        workspace_uri = f"db:sqlite:{target_db}"
        registry_uri = config_resolver.resolve_registry_uri(
            engine="sqlite",
            workspace_uri=workspace_uri,
            project_root=project_dir,
            registry_override=None,
        )

        registry_path_str = registry_uri
        if registry_path_str.startswith("db:sqlite:"):
            registry_path_str = registry_path_str[10:]
        elif registry_path_str.startswith("sqlite:"):
            registry_path_str = registry_path_str[7:]

        registry_path = Path(registry_path_str)
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        registry_conn = sqlite3.connect(registry_path)
        try:
            registry_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS changes (
                    project TEXT NOT NULL,
                    change TEXT NOT NULL,
                    committed_at TEXT,
                    committer_name TEXT,
                    committer_email TEXT
                )
                """
            )
            registry_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    project TEXT,
                    event TEXT
                )
                """
            )
            registry_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tags (
                    project TEXT,
                    tag TEXT
                )
                """
            )
            registry_conn.commit()
        finally:
            registry_conn.close()

        sqlite3.connect(target_db).close()

        with pushd(project_dir):
            result = runner.invoke(main, ["verify", workspace_uri])

        assert result.exit_code == 0, result.output
        assert "No changes to verify." in result.output

    def test_requires_target_when_not_configured(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir, _ = setup_project(tmp_path, changes=("users",))

        with pushd(project_dir):
            result = runner.invoke(main, ["verify"])

        assert result.exit_code == 1
        assert "A target must be provided" in result.output

    def test_rejects_conflicting_target_inputs(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir, target_db = setup_project(tmp_path, changes=())

        with pushd(project_dir):
            result = runner.invoke(
                main,
                [
                    "verify",
                    f"db:sqlite:{target_db}",
                    "--target",
                    f"db:sqlite:{target_db}",
                ],
            )

        assert result.exit_code == 1
        assert "Provide either a positional target" in result.output

    def test_rejects_multiple_positional_targets(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir, _ = setup_project(tmp_path, changes=())

        with pushd(project_dir):
            result = runner.invoke(
                main,
                [
                    "verify",
                    "db:sqlite:first.db",
                    "db:sqlite:second.db",
                ],
            )

        assert result.exit_code == 1
        assert "Multiple positional targets are not supported." in result.output

    def test_rejects_unsupported_engine(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir, _ = setup_project(tmp_path, changes=())

        with pushd(project_dir):
            result = runner.invoke(main, ["verify", "db:pg:flipr"])

        assert result.exit_code == 1
        assert "verification is not supported" in result.output

    def test_execute_sqlite_verify_script_handles_multiple_statements(self) -> None:
        connection = sqlite3.connect(":memory:")
        try:
            cursor = connection.cursor()
            cursor.execute("CREATE TABLE numbers (n INTEGER)")
            script = "INSERT INTO numbers (n) VALUES (1);\nINSERT INTO numbers (n) VALUES (2);\n"
            _execute_sqlite_verify_script(cursor, script)
            cursor.close()
            count = connection.execute("SELECT COUNT(*) FROM numbers").fetchone()[0]
            assert count == 2
        finally:
            connection.close()

    def test_resolve_sqlite_workspace_uri_defaults_to_plan_path(self, tmp_path: Path) -> None:
        project_root = tmp_path / "proj"
        project_root.mkdir()
        plan_path = project_root / "sqitch.plan"
        plan_path.write_text("%syntax-version=1.0.0\n%project=flipr\n")

        workspace_uri, display = _resolve_sqlite_workspace_uri(
            payload="",
            project_root=project_root,
            plan_path=plan_path,
            original_target="",
        )

        expected_path = plan_path.with_suffix(".db").resolve().as_posix()
        expected_uri = f"db:sqlite:{expected_path}"
        assert workspace_uri == expected_uri
        assert display == expected_uri

    def test_resolve_sqlite_workspace_uri_supports_file_uri(self, tmp_path: Path) -> None:
        project_root = tmp_path / "proj"
        project_root.mkdir()
        plan_path = project_root / "sqitch.plan"
        plan_path.write_text("%syntax-version=1.0.0\n%project=flipr\n")

        uri, display = _resolve_sqlite_workspace_uri(
            payload="file:test.db?mode=rwc",
            project_root=project_root,
            plan_path=plan_path,
            original_target="db:sqlite:file:test.db?mode=rwc",
        )

        assert uri == "db:sqlite:file:test.db?mode=rwc"
        assert display == "db:sqlite:file:test.db?mode=rwc"

    def test_resolve_sqlite_workspace_uri_rejects_memory(self, tmp_path: Path) -> None:
        project_dir, _ = setup_project(tmp_path, changes=())
        plan_path = project_dir / "sqitch.plan"

        with pytest.raises(CommandError, match="In-memory SQLite targets are not supported"):
            _resolve_sqlite_workspace_uri(
                payload=":memory:",
                project_root=project_dir,
                plan_path=plan_path,
                original_target="db:sqlite::memory:",
            )

    @pytest.mark.parametrize(
        "uri,expected",
        [
            ("db:sqlite:/tmp/work.db", "/tmp/work.db"),
            ("sqlite:/tmp/work.db", "/tmp/work.db"),
            ("/tmp/work.db", "/tmp/work.db"),
        ],
    )
    def test_strip_sqlite_uri_prefix_variants(self, uri: str, expected: str) -> None:
        assert _strip_sqlite_uri_prefix(uri) == expected

    def test_resolve_engine_target_rejects_malformed_uri(self, tmp_path: Path) -> None:
        project_dir, _ = setup_project(tmp_path, changes=())
        plan_path = project_dir / "sqitch.plan"

        with pytest.raises(CommandError, match="Malformed target URI"):
            _resolve_engine_target(
                target="db:sqlite",
                project_root=project_dir,
                default_engine="sqlite",
                plan_path=plan_path,
                registry_override=None,
            )

    def test_resolve_engine_target_rejects_unknown_engine(self, tmp_path: Path) -> None:
        project_dir, _ = setup_project(tmp_path, changes=())
        plan_path = project_dir / "sqitch.plan"

        with pytest.raises(CommandError, match="Unsupported engine 'madeup'"):
            _resolve_engine_target(
                target="db:madeup:flipr",
                project_root=project_dir,
                default_engine="sqlite",
                plan_path=plan_path,
                registry_override=None,
            )

    def test_resolve_engine_target_handles_relative_target(self, tmp_path: Path) -> None:
        project_dir, _ = setup_project(tmp_path, changes=())
        plan_path = project_dir / "sqitch.plan"

        engine_target, display = _resolve_engine_target(
            target="workspace.db",
            project_root=project_dir,
            default_engine="sqlite",
            plan_path=plan_path,
            registry_override=None,
        )

        expected_path = (project_dir / "workspace.db").resolve().as_posix()
        assert engine_target.uri == f"db:sqlite:{expected_path}"
        assert display == "workspace.db"

    def test_load_plan_wraps_parse_errors(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        plan_path = tmp_path / "sqitch.plan"
        plan_path.write_text("%syntax-version=1.0.0\n%project=flipr\n")

        def boom(_: Path, *, default_engine: str) -> None:
            raise ValueError("boom")

        monkeypatch.setattr("sqlitch.cli.commands.verify.parse_plan", boom)

        with pytest.raises(CommandError, match="Failed to load plan: boom"):
            _load_plan(plan_path, "sqlite")


class TestVerifyErrorHandling:
    def test_verify_rejects_memory_target(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir, _ = setup_project(tmp_path, changes=())

        with pushd(project_dir):
            result = runner.invoke(main, ["verify", "db:sqlite::memory:"])

        assert result.exit_code == 1
        assert "In-memory SQLite targets are not supported" in result.output

    def test_verify_errors_on_malformed_target(self, runner: CliRunner, tmp_path: Path) -> None:
        project_dir, _ = setup_project(tmp_path, changes=())

        with pushd(project_dir):
            result = runner.invoke(main, ["verify", "db:sqlite"])

        assert result.exit_code == 1
        assert "Malformed target URI" in result.output

    def test_connection_failure_produces_command_error(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project_dir, target_db = setup_project(tmp_path, changes=("users",))

        def failing_connect(_: str) -> sqlite3.Connection:
            raise sqlite3.OperationalError("boom")

        monkeypatch.setattr("sqlitch.cli.commands.verify.sqlite3.connect", failing_connect)

        with pushd(project_dir):
            result = runner.invoke(main, ["verify", f"db:sqlite:{target_db}"])

        assert result.exit_code == 1
        assert "Failed to connect to workspace database" in result.output

    def test_attach_failure_produces_command_error(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project_dir, target_db = setup_project(tmp_path, changes=("users",))

        class AttachFailingConnection:
            def execute(self, sql: str, params: tuple[str, ...] = ()) -> None:
                raise sqlite3.OperationalError("attach failed")

            def close(self) -> None:  # pragma: no cover - defensive
                pass

        monkeypatch.setattr(
            "sqlitch.cli.commands.verify.sqlite3.connect",
            lambda _: AttachFailingConnection(),
        )

        with pushd(project_dir):
            result = runner.invoke(main, ["verify", f"db:sqlite:{target_db}"])

        assert result.exit_code == 1
        assert "Failed to attach registry" in result.output

    def test_registry_query_failure_produces_command_error(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project_dir, target_db = setup_project(tmp_path, changes=("users",))

        class QueryFailingConnection:
            class _DummyCursor:
                def close(self) -> None:
                    pass

            def execute(self, sql: str, params: tuple[str, ...] = ()) -> sqlite3.Cursor:
                if "ATTACH" in sql:
                    return self._DummyCursor()
                raise sqlite3.OperationalError("query failed")

            def close(self) -> None:  # pragma: no cover - defensive
                pass

            def cursor(self) -> sqlite3.Cursor:
                raise AssertionError("cursor should not be requested when query fails")

        monkeypatch.setattr(
            "sqlitch.cli.commands.verify.sqlite3.connect",
            lambda path: QueryFailingConnection(),
        )

        with pushd(project_dir):
            result = runner.invoke(main, ["verify", f"db:sqlite:{target_db}"])

        assert result.exit_code == 1
        assert "Failed to query registry" in result.output


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click test runner."""
    return CliRunner()
