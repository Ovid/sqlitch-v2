from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

from sqlitch.engine import base
from sqlitch.engine.sqlite import SQLiteEngineError, validate_sqlite_script


def _make_target(uri: str, *, registry: str | None = None) -> base.EngineTarget:
    return base.EngineTarget(name="db:test", engine="sqlite", uri=uri, registry_uri=registry)


def test_sqlite_engine_registers_itself() -> None:
    module_name = "sqlitch.engine.sqlite"
    previous = base.unregister_engine("sqlite")
    sys.modules.pop(module_name, None)

    module = importlib.import_module(module_name)
    try:
        engine = base.create_engine(_make_target("db:sqlite:memory"))
        assert isinstance(engine, module.SQLiteEngine)
    finally:
        base.unregister_engine("sqlite")
        if previous is not None:
            base.register_engine("sqlite", previous, replace=True)
        else:
            base.register_engine("sqlite", module.SQLiteEngine, replace=True)


def test_sqlite_engine_builds_connect_arguments_with_paths(tmp_path: Path) -> None:
    import sqlitch.engine.sqlite as sqlite_engine

    target = _make_target(
        f"db:sqlite:{tmp_path / 'workspace.db'}",
        registry=f"db:sqlite:{tmp_path / 'registry.db'}",
    )

    engine = sqlite_engine.SQLiteEngine(target, connect_kwargs={"timeout": 2.5})

    registry_args = engine.build_registry_connect_arguments()
    workspace_args = engine.build_workspace_connect_arguments()

    assert registry_args.args == (str(tmp_path / "registry.db"),)
    assert workspace_args.args == (str(tmp_path / "workspace.db"),)

    expected_detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    assert registry_args.kwargs["detect_types"] == expected_detect_types
    assert workspace_args.kwargs["detect_types"] == expected_detect_types
    assert registry_args.kwargs["timeout"] == pytest.approx(2.5)
    assert workspace_args.kwargs["timeout"] == pytest.approx(2.5)
    assert registry_args.kwargs["uri"] is False
    assert workspace_args.kwargs["uri"] is False


def test_sqlite_engine_supports_uri_queries() -> None:
    import sqlitch.engine.sqlite as sqlite_engine

    target = _make_target("db:sqlite:file:workspace.db?mode=ro&cache=shared")
    engine = sqlite_engine.SQLiteEngine(target)

    args = engine.build_workspace_connect_arguments()
    assert args.args == ("file:workspace.db?mode=ro&cache=shared",)
    assert args.kwargs["uri"] is True


def test_sqlite_engine_defaults_to_memory_when_no_path() -> None:
    import sqlitch.engine.sqlite as sqlite_engine

    engine = sqlite_engine.SQLiteEngine(_make_target("db:sqlite:"))

    workspace_args = engine.build_workspace_connect_arguments()
    assert workspace_args.args == (":memory:",)
    assert workspace_args.kwargs["uri"] is False


def test_sqlite_engine_accepts_explicit_memory_identifier() -> None:
    import sqlitch.engine.sqlite as sqlite_engine

    engine = sqlite_engine.SQLiteEngine(_make_target("db:sqlite::memory:"))

    workspace_args = engine.build_workspace_connect_arguments()
    assert workspace_args.args == (":memory:",)
    assert workspace_args.kwargs["uri"] is False


def test_parse_sqlite_uri_rejects_invalid_scheme() -> None:
    from sqlitch.engine.sqlite import SQLiteEngineError, _parse_sqlite_uri

    with pytest.raises(SQLiteEngineError):
        _parse_sqlite_uri("sqlite::memory:")


def test_sqlite_engine_attaches_registry_on_connect_workspace(tmp_path: Path) -> None:
    """Test that connect_workspace attaches the registry database."""
    import sqlitch.engine.sqlite as sqlite_engine

    workspace_db = tmp_path / "workspace.db"
    registry_db = tmp_path / "sqitch.db"

    # Create both databases
    sqlite3.connect(str(workspace_db)).close()
    sqlite3.connect(str(registry_db)).close()

    target = _make_target(
        f"db:sqlite:{workspace_db}",
        registry=f"db:sqlite:{registry_db}",
    )

    engine = sqlite_engine.SQLiteEngine(target)
    connection = engine.connect_workspace()

    try:
        # Verify registry is attached
        cursor = connection.cursor()
        result = cursor.execute("PRAGMA database_list").fetchall()
        cursor.close()

        # Should have main and sqitch databases attached
        database_names = [row[1] for row in result]
        assert "main" in database_names
        assert "sqitch" in database_names
    finally:
        connection.close()


def test_sqlite_engine_registry_filesystem_path_with_file_path(tmp_path: Path) -> None:
    """Test registry_filesystem_path returns correct path for file paths."""
    import sqlitch.engine.sqlite as sqlite_engine

    registry_db = tmp_path / "sqitch.db"
    target = _make_target("db:sqlite::memory:", registry=f"db:sqlite:{registry_db}")

    engine = sqlite_engine.SQLiteEngine(target)
    assert engine.registry_filesystem_path() == registry_db


def test_sqlite_engine_registry_filesystem_path_with_file_uri(tmp_path: Path) -> None:
    """Test registry_filesystem_path works with file: URIs."""
    import sqlitch.engine.sqlite as sqlite_engine

    registry_db = tmp_path / "sqitch.db"
    target = _make_target(
        "db:sqlite::memory:",
        registry=f"db:sqlite:file:{registry_db}",
    )

    engine = sqlite_engine.SQLiteEngine(target)
    assert engine.registry_filesystem_path() == registry_db


def test_sqlite_engine_registry_filesystem_path_rejects_non_file_uri() -> None:
    """Test registry_filesystem_path raises error for file: URI with remote host."""
    import sqlitch.engine.sqlite as sqlite_engine

    # file: URIs with remote hosts are not supported
    target = _make_target(
        "db:sqlite::memory:",
        registry="db:sqlite:file://remote-host/path/to/db.sqlite",
    )

    engine = sqlite_engine.SQLiteEngine(target)
    with pytest.raises(sqlite_engine.SQLiteEngineError, match="do not support remote file hosts"):
        engine.registry_filesystem_path()


def test_sqlite_engine_registry_filesystem_path_with_plain_string(tmp_path: Path) -> None:
    """Test registry_filesystem_path works with plain database strings."""
    import sqlitch.engine.sqlite as sqlite_engine

    # Plain strings (even ones that look like URIs) are treated as filesystem paths
    target = _make_target("db:sqlite::memory:", registry="db:sqlite:memory:shared")

    engine = sqlite_engine.SQLiteEngine(target)
    result = engine.registry_filesystem_path()
    # memory:shared is not recognized as a file: URI, so it's treated as a plain path
    assert result == Path("memory:shared")


def test_resolve_sqlite_filesystem_path_with_plain_database_string() -> None:
    """Test resolve_sqlite_filesystem_path with plain database strings."""
    import sqlitch.engine.sqlite as sqlite_engine

    # Plain database strings (not file: URIs) are returned as-is
    result = sqlite_engine.resolve_sqlite_filesystem_path("db:sqlite:memory:shared")
    assert result == Path("memory:shared")


def test_derive_sqlite_registry_uri_with_registry_override(tmp_path: Path) -> None:
    """Test derive_sqlite_registry_uri respects registry override."""
    import sqlitch.engine.sqlite as sqlite_engine

    override = str(tmp_path / "custom_sqitch.db")
    result = sqlite_engine.derive_sqlite_registry_uri(
        workspace_uri="db:sqlite:workspace.db",
        project_root=tmp_path,
        registry_override=override,
    )

    expected = f"db:sqlite:{(tmp_path / 'custom_sqitch.db').as_posix()}"
    assert result == expected


def test_derive_sqlite_registry_uri_with_memory_workspace(tmp_path: Path) -> None:
    """Test derive_sqlite_registry_uri creates file registry for memory workspace."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.derive_sqlite_registry_uri(
        workspace_uri="db:sqlite::memory:",
        project_root=tmp_path,
    )

    expected = f"db:sqlite:{(tmp_path / 'sqitch.db').as_posix()}"
    assert result == expected


def test_derive_sqlite_registry_uri_with_empty_workspace(tmp_path: Path) -> None:
    """Test derive_sqlite_registry_uri handles empty workspace URI."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.derive_sqlite_registry_uri(
        workspace_uri="db:sqlite:",
        project_root=tmp_path,
    )

    expected = f"db:sqlite:{(tmp_path / 'sqitch.db').as_posix()}"
    assert result == expected


def test_derive_sqlite_registry_uri_with_absolute_file_path(tmp_path: Path) -> None:
    """Test derive_sqlite_registry_uri with absolute file path."""
    import sqlitch.engine.sqlite as sqlite_engine

    workspace_db = tmp_path / "data" / "workspace.db"
    result = sqlite_engine.derive_sqlite_registry_uri(
        workspace_uri=f"db:sqlite:{workspace_db}",
        project_root=tmp_path,
    )

    expected = f"db:sqlite:{(tmp_path / 'data' / 'sqitch.db').as_posix()}"
    assert result == expected


def test_derive_sqlite_registry_uri_with_relative_file_path(tmp_path: Path) -> None:
    """Test derive_sqlite_registry_uri resolves relative paths."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.derive_sqlite_registry_uri(
        workspace_uri="db:sqlite:data/workspace.db",
        project_root=tmp_path,
    )

    expected = f"db:sqlite:{(tmp_path / 'data' / 'sqitch.db').as_posix()}"
    assert result == expected


def test_derive_sqlite_registry_uri_with_file_uri(tmp_path: Path) -> None:
    """Test derive_sqlite_registry_uri handles file: URIs."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.derive_sqlite_registry_uri(
        workspace_uri=f"db:sqlite:file://{tmp_path / 'workspace.db'}",
        project_root=tmp_path,
    )

    # File URIs with absolute paths need three slashes
    expected = f"db:sqlite:file://{(tmp_path / 'sqitch.db').as_posix()}"
    assert result == expected


def test_derive_sqlite_registry_uri_with_relative_file_uri(tmp_path: Path) -> None:
    """Test derive_sqlite_registry_uri resolves relative file: URIs."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.derive_sqlite_registry_uri(
        workspace_uri="db:sqlite:file:data/workspace.db",
        project_root=tmp_path,
    )

    expected = f"db:sqlite:file://{(tmp_path / 'data' / 'sqitch.db').as_posix()}"
    assert result == expected


def test_normalize_registry_override_with_db_prefix(tmp_path: Path) -> None:
    """Test _normalize_registry_override preserves db: prefix."""
    from sqlitch.engine.sqlite import _normalize_registry_override

    override = "db:sqlite:/path/to/registry.db"
    result = _normalize_registry_override(override, tmp_path)
    assert result == "db:sqlite:/path/to/registry.db"


def test_normalize_registry_override_with_file_uri(tmp_path: Path) -> None:
    """Test _normalize_registry_override adds db:sqlite: prefix to file: URIs."""
    from sqlitch.engine.sqlite import _normalize_registry_override

    override = "file:/path/to/registry.db"
    result = _normalize_registry_override(override, tmp_path)
    assert result == "db:sqlite:file:/path/to/registry.db"


def test_normalize_registry_override_with_plain_path(tmp_path: Path) -> None:
    """Test _normalize_registry_override handles plain paths."""
    from sqlitch.engine.sqlite import _normalize_registry_override

    override = "registry.db"
    result = _normalize_registry_override(override, tmp_path)
    expected = f"db:sqlite:{(tmp_path / 'registry.db').as_posix()}"
    assert result == expected


def test_normalize_registry_override_rejects_empty() -> None:
    """Test _normalize_registry_override rejects empty strings."""
    from sqlitch.engine.sqlite import SQLiteEngineError, _normalize_registry_override

    with pytest.raises(SQLiteEngineError, match="cannot be empty"):
        _normalize_registry_override("", Path("/tmp"))

    with pytest.raises(SQLiteEngineError, match="cannot be empty"):
        _normalize_registry_override("   ", Path("/tmp"))


def test_resolve_sqlite_filesystem_path_with_plain_path() -> None:
    """Test resolve_sqlite_filesystem_path handles plain paths."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.resolve_sqlite_filesystem_path("db:sqlite:/path/to/db.sqlite")
    assert result == Path("/path/to/db.sqlite")


def test_resolve_sqlite_filesystem_path_with_memory() -> None:
    """Test resolve_sqlite_filesystem_path handles :memory:."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.resolve_sqlite_filesystem_path("db:sqlite::memory:")
    assert result == Path(":memory:")


def test_resolve_sqlite_filesystem_path_with_file_uri() -> None:
    """Test resolve_sqlite_filesystem_path handles file: URIs."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.resolve_sqlite_filesystem_path("db:sqlite:file:/path/to/db.sqlite")
    assert result == Path("/path/to/db.sqlite")


def test_resolve_sqlite_filesystem_path_with_file_uri_query() -> None:
    """Test resolve_sqlite_filesystem_path strips query parameters."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.resolve_sqlite_filesystem_path(
        "db:sqlite:file:/path/to/db.sqlite?mode=ro"
    )
    assert result == Path("/path/to/db.sqlite")


def test_resolve_sqlite_filesystem_path_rejects_remote_file_hosts() -> None:
    """Test resolve_sqlite_filesystem_path rejects file: URIs with remote hosts."""
    import sqlitch.engine.sqlite as sqlite_engine

    with pytest.raises(sqlite_engine.SQLiteEngineError, match="do not support remote file hosts"):
        sqlite_engine.resolve_sqlite_filesystem_path(
            "db:sqlite:file://remote-host/path/to/db.sqlite"
        )


def test_resolve_sqlite_filesystem_path_with_relative_path() -> None:
    """Test resolve_sqlite_filesystem_path handles relative paths."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.resolve_sqlite_filesystem_path("db:sqlite:./relative/path.db")
    assert result == Path("./relative/path.db")
    assert not result.is_absolute()


def test_resolve_sqlite_filesystem_path_with_relative_file_uri() -> None:
    """Test resolve_sqlite_filesystem_path handles relative file: URIs."""
    import sqlitch.engine.sqlite as sqlite_engine

    result = sqlite_engine.resolve_sqlite_filesystem_path("db:sqlite:file:./relative/path.db")
    assert result == Path("./relative/path.db")
    assert not result.is_absolute()


def test_extract_sqlite_statements_single_statement() -> None:
    """Test extract_sqlite_statements with single statement."""
    from sqlitch.engine.sqlite import extract_sqlite_statements

    result = extract_sqlite_statements("SELECT 1;")
    assert result == ("SELECT 1;",)


def test_extract_sqlite_statements_multiple_statements() -> None:
    """Test extract_sqlite_statements with multiple statements."""
    from sqlitch.engine.sqlite import extract_sqlite_statements

    script = """
    CREATE TABLE users (id INTEGER);
    INSERT INTO users VALUES (1);
    SELECT * FROM users;
    """
    result = extract_sqlite_statements(script)
    assert len(result) == 3
    assert "CREATE TABLE" in result[0]
    assert "INSERT INTO" in result[1]
    assert "SELECT" in result[2]


def test_extract_sqlite_statements_ignores_empty_lines() -> None:
    """Test extract_sqlite_statements ignores empty lines."""
    from sqlitch.engine.sqlite import extract_sqlite_statements

    script = """

    SELECT 1;

    SELECT 2;

    """
    result = extract_sqlite_statements(script)
    assert len(result) == 2
    assert result == ("SELECT 1;", "SELECT 2;")


def test_extract_sqlite_statements_handles_incomplete_statement() -> None:
    """Test extract_sqlite_statements includes incomplete statements."""
    from sqlitch.engine.sqlite import extract_sqlite_statements

    script = """
    SELECT 1;
    SELECT 2
    """
    result = extract_sqlite_statements(script)
    assert len(result) == 2
    assert result[0] == "SELECT 1;"
    assert result[1] == "SELECT 2"


def test_script_manages_transactions_detects_begin() -> None:
    """Test script_manages_transactions detects BEGIN."""
    from sqlitch.engine.sqlite import script_manages_transactions

    assert script_manages_transactions("BEGIN; SELECT 1; COMMIT;") is True
    assert script_manages_transactions("BEGIN TRANSACTION; SELECT 1;") is True


def test_script_manages_transactions_detects_commit() -> None:
    """Test script_manages_transactions detects COMMIT."""
    from sqlitch.engine.sqlite import script_manages_transactions

    # COMMIT as leading keyword of a statement
    assert script_manages_transactions("COMMIT;") is True
    assert script_manages_transactions("COMMIT TRANSACTION;") is True
    # Multiple statements where one starts with COMMIT
    assert script_manages_transactions("INSERT INTO t VALUES (1);\nCOMMIT;") is True


def test_script_manages_transactions_detects_rollback() -> None:
    """Test script_manages_transactions detects ROLLBACK."""
    from sqlitch.engine.sqlite import script_manages_transactions

    assert script_manages_transactions("ROLLBACK;") is True
    assert script_manages_transactions("ROLLBACK TO SAVEPOINT sp1;") is True
    # Multiple statements where one starts with ROLLBACK
    assert script_manages_transactions("SELECT 1;\nROLLBACK;") is True


def test_script_manages_transactions_detects_savepoint() -> None:
    """Test script_manages_transactions detects SAVEPOINT."""
    from sqlitch.engine.sqlite import script_manages_transactions

    assert script_manages_transactions("SAVEPOINT sp1; SELECT 1;") is True


def test_script_manages_transactions_detects_release() -> None:
    """Test script_manages_transactions detects RELEASE."""
    from sqlitch.engine.sqlite import script_manages_transactions

    assert script_manages_transactions("RELEASE SAVEPOINT sp1;") is True
    assert script_manages_transactions("RELEASE sp1;") is True


def test_script_manages_transactions_detects_end() -> None:
    """Test script_manages_transactions detects END."""
    from sqlitch.engine.sqlite import script_manages_transactions

    assert script_manages_transactions("END;") is True
    assert script_manages_transactions("END TRANSACTION;") is True
    # Multiple statements where one starts with END
    assert script_manages_transactions("SELECT 1;\nEND;") is True


def test_script_manages_transactions_returns_false_for_no_transactions() -> None:
    """Test script_manages_transactions returns False for non-transaction scripts."""
    from sqlitch.engine.sqlite import script_manages_transactions

    assert script_manages_transactions("SELECT 1;") is False
    assert script_manages_transactions("CREATE TABLE t (id INTEGER);") is False
    assert script_manages_transactions("INSERT INTO t VALUES (1);") is False


def test_script_manages_transactions_case_insensitive() -> None:
    """Test script_manages_transactions is case insensitive."""
    from sqlitch.engine.sqlite import script_manages_transactions

    assert script_manages_transactions("begin; SELECT 1;") is True
    assert script_manages_transactions("Begin Transaction;") is True
    assert script_manages_transactions("COMMIT;") is True
    assert script_manages_transactions("commit;") is True


def test_script_manages_transactions_ignores_transactions_in_strings() -> None:
    """Test script_manages_transactions ignores keywords in strings."""
    from sqlitch.engine.sqlite import script_manages_transactions

    # BEGIN in a string should not be detected
    assert script_manages_transactions("SELECT 'BEGIN' AS keyword;") is False
    assert script_manages_transactions('INSERT INTO t VALUES ("COMMIT");') is False


def test_extract_payload_with_standard_uri() -> None:
    """Test _extract_payload handles standard db:sqlite: URIs."""
    from sqlitch.engine.sqlite import _extract_payload

    assert _extract_payload("db:sqlite:/path/to/db.sqlite") == "/path/to/db.sqlite"
    assert _extract_payload("db:sqlite::memory:") == ":memory:"
    assert _extract_payload("db:sqlite:") == ""


def test_extract_payload_with_non_db_uri() -> None:
    """Test _extract_payload handles URIs without db: prefix."""
    from sqlitch.engine.sqlite import _extract_payload

    assert _extract_payload("/path/to/db.sqlite") == "/path/to/db.sqlite"
    assert _extract_payload("file:/path/to/db.sqlite") == "file:/path/to/db.sqlite"


def test_extract_payload_validates_engine_name() -> None:
    """Test _extract_payload validates the engine name."""
    from sqlitch.engine.sqlite import SQLiteEngineError, _extract_payload

    with pytest.raises(SQLiteEngineError, match="requires sqlite targets"):
        _extract_payload("db:postgres:dbname")


def test_extract_payload_rejects_malformed_uri() -> None:
    """Test _extract_payload rejects URIs without colon separator."""
    from sqlitch.engine.sqlite import SQLiteEngineError, _extract_payload

    with pytest.raises(SQLiteEngineError, match="unexpected sqlite URI format"):
        _extract_payload("db:sqlite")


def test_split_file_uri_handles_localhost() -> None:
    """Test _split_file_uri handles localhost netloc."""
    from sqlitch.engine.sqlite import _split_file_uri

    split = _split_file_uri("file://localhost/path/to/db.sqlite")
    assert split.scheme == "file"
    assert split.netloc == "localhost"
    assert split.path == "/path/to/db.sqlite"


def test_filesystem_path_from_split_with_localhost() -> None:
    """Test _filesystem_path_from_split handles localhost."""
    from sqlitch.engine.sqlite import _filesystem_path_from_split, _split_file_uri

    split = _split_file_uri("file://localhost/path/to/db.sqlite")
    path = _filesystem_path_from_split(split)
    assert path == Path("/path/to/db.sqlite")


def test_filesystem_path_from_split_with_empty_path() -> None:
    """Test _filesystem_path_from_split handles empty path."""
    from urllib.parse import SplitResult

    from sqlitch.engine.sqlite import _filesystem_path_from_split

    split = SplitResult(scheme="file", netloc="", path="", query="", fragment="")
    path = _filesystem_path_from_split(split)
    assert path == Path("sqitch.db")


def test_filesystem_path_from_split_with_url_encoded_chars() -> None:
    """Test _filesystem_path_from_split handles URL encoding."""
    from urllib.parse import SplitResult

    from sqlitch.engine.sqlite import _filesystem_path_from_split

    # Path with spaces encoded as %20
    split = SplitResult(
        scheme="file", netloc="", path="/path/with%20spaces/db.sqlite", query="", fragment=""
    )
    path = _filesystem_path_from_split(split)
    assert path == Path("/path/with spaces/db.sqlite")


# ==============================================================================
# Deploy Behavior and Transaction Tests (from regression tests)
# ==============================================================================


def test_failed_deploy_does_not_persist_workspace_mutations(tmp_path) -> None:
    """Failed deployments must not leave partial changes in workspace database.

    Regression test for atomicity guarantees in SQLite deployments.
    """
    from contextlib import chdir, closing

    from click.testing import CliRunner

    from sqlitch.cli.main import main
    from tests.support.sqlite_fixtures import ChangeScript, create_sqlite_project

    project = create_sqlite_project(
        tmp_path,
        changes=[
            ChangeScript(
                name="alpha",
                deploy_sql="""
                CREATE TABLE alpha_data (id INTEGER PRIMARY KEY);
                INSERT INTO alpha_data DEFAULT VALUES;
                SELECT RAISE(ABORT, 'deploy failure');
                """,
            )
        ],
    )

    workspace_db = project.project_root / "workspace.db"

    runner = CliRunner()
    with chdir(project.project_root):
        result = runner.invoke(
            main,
            [
                "deploy",
                "--target",
                workspace_db.as_posix(),
            ],
            catch_exceptions=False,
        )

    assert result.exit_code != 0, "Deploy should fail when the deploy script raises"

    assert workspace_db.exists(), "Workspace database should still be created for inspection"

    with closing(sqlite3.connect(workspace_db)) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("alpha_data",),
        )
        tables = {row[0] for row in cursor.fetchall()}

    assert not tables, "Failed deploy must not leave change tables behind in the workspace database"


def test_deploy_respects_script_managed_transactions(tmp_path) -> None:
    """Deploy scripts can manage their own transactions using BEGIN/COMMIT/ROLLBACK.

    Regression test for script-managed transaction support in SQLite.
    """
    from contextlib import chdir, closing

    from click.testing import CliRunner

    from sqlitch.cli.main import main
    from tests.support.sqlite_fixtures import ChangeScript, create_sqlite_project

    project = create_sqlite_project(
        tmp_path,
        changes=[
            ChangeScript(
                name="script_transactions_commit",
                deploy_sql="""
                BEGIN;
                CREATE TABLE committed_data (id INTEGER PRIMARY KEY, value TEXT);
                INSERT INTO committed_data (value) VALUES ('ok');
                COMMIT;
                """,
            ),
            ChangeScript(
                name="script_transactions_rollback",
                deploy_sql="""
                BEGIN;
                CREATE TABLE rollback_data (id INTEGER PRIMARY KEY, value TEXT);
                INSERT INTO rollback_data (value) VALUES ('should rollback');
                ROLLBACK;
                SELECT * FROM nonexistent_table;
                """,
            ),
        ],
    )

    workspace_db = project.project_root / "workspace.db"

    runner = CliRunner()
    with chdir(project.project_root):
        result = runner.invoke(
            main,
            [
                "deploy",
                "--target",
                workspace_db.as_posix(),
            ],
            catch_exceptions=False,
        )

    assert result.exit_code != 0, "Deploy should fail after the script-triggered rollback"
    assert "no such table: nonexistent_table" in result.output

    assert workspace_db.exists(), "Workspace database should exist for inspection"

    with closing(sqlite3.connect(workspace_db)) as connection:
        committed_cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("committed_data",),
        )
        committed_tables = {row[0] for row in committed_cursor.fetchall()}
        committed_cursor.close()

        row_cursor = connection.execute("SELECT COUNT(*) FROM committed_data")
        committed_rows = row_cursor.fetchone()[0]
        row_cursor.close()

        rollback_cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("rollback_data",),
        )
        rollback_tables = {row[0] for row in rollback_cursor.fetchall()}
        rollback_cursor.close()

    assert committed_tables == {"committed_data"}, "Manual transaction change should commit data"
    assert committed_rows == 1, "Committed change should persist inserted rows"
    assert not rollback_tables, "Rolled-back change must not leave tables behind"

    assert (
        project.registry_path.exists()
    ), "Registry database should be created even when a later change fails"

    with closing(sqlite3.connect(project.registry_path)) as connection:
        cursor = connection.execute(
            "SELECT change FROM changes ORDER BY committed_at ASC",
        )
        recorded_changes = [row[0] for row in cursor.fetchall()]
        cursor.close()

    assert recorded_changes == [
        "script_transactions_commit"
    ], "Registry must only record successfully committed changes"


def test_registry_isolated_from_workspace(tmp_path) -> None:
    """Registry tables must be stored in a separate sqitch.db, not in workspace.

    Regression test for SQLite registry attachment behavior.
    """
    from contextlib import chdir, closing

    from click.testing import CliRunner

    from sqlitch.cli.main import main
    from tests.support.sqlite_fixtures import ChangeScript, create_sqlite_project

    project = create_sqlite_project(
        tmp_path,
        changes=[
            ChangeScript(
                name="alpha",
                deploy_sql="""
                CREATE TABLE workspace_data (id INTEGER PRIMARY KEY);
                INSERT INTO workspace_data DEFAULT VALUES;
                """,
            )
        ],
    )

    workspace_db = project.project_root / "workspace.db"

    runner = CliRunner()
    with chdir(project.project_root):
        result = runner.invoke(
            main,
            [
                "deploy",
                "--target",
                workspace_db.as_posix(),
            ],
            catch_exceptions=False,
        )

    assert result.exit_code == 0, result.output

    assert (
        project.registry_path.exists()
    ), "SQLite deployment should create a dedicated sqitch.db registry database"

    with closing(sqlite3.connect(workspace_db)) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN (?, ?)",
            ("changes", "releases"),
        )
        workspace_tables = {row[0] for row in cursor.fetchall()}

    assert (
        not workspace_tables
    ), "Workspace database must remain free of registry tables when deploy completes"

    with closing(sqlite3.connect(project.registry_path)) as registry_conn:
        cursor = registry_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("changes",),
        )
        registry_tables = {row[0] for row in cursor.fetchall()}

    assert registry_tables == {"changes"}, "Registry database should contain the Sqitch schema"


# =============================================================================
# Lockdown Tests (merged from test_sqlite_lockdown.py)
# =============================================================================


def test_validate_sqlite_script_rejects_disabling_foreign_keys() -> None:
    """Foreign key enforcement must stay enabled during deployments."""
    script = """
    PRAGMA foreign_keys = OFF;
    CREATE TABLE users(id INTEGER PRIMARY KEY);
    """

    with pytest.raises(SQLiteEngineError, match="foreign_keys pragma must remain enabled"):
        validate_sqlite_script(script)


def test_validate_sqlite_script_rejects_unfinished_transaction() -> None:
    """Scripts that open transactions must close them explicitly."""
    script = """
    BEGIN;
    CREATE TABLE stuff(id INTEGER PRIMARY KEY);
    -- missing COMMIT/ROLLBACK on purpose
    """

    with pytest.raises(SQLiteEngineError, match="must end with COMMIT or ROLLBACK"):
        validate_sqlite_script(script)


def test_validate_sqlite_script_ignores_leading_comments() -> None:
    """Comments before statements should not break transaction balancing."""
    script = """
    -- Deploy flipr:users to sqlite

    BEGIN;
    CREATE TABLE users (id INTEGER PRIMARY KEY);
    COMMIT;
    """

    validate_sqlite_script(script)
