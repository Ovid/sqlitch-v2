"""Unit coverage for the ``sqlitch status`` command helpers."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main
from sqlitch.cli.commands import CommandError
from sqlitch.cli.commands.status import (
    RegistryRow,
    _build_json_payload,
    _calculate_pending,
    _determine_status,
    _render_human_output,
    _resolve_registry_target,
    _resolve_plan_path,
    _load_plan,
    _load_registry_rows,
)
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change
from sqlitch.plan.parser import PlanParseError
from sqlitch.utils.fs import ArtifactConflictError, ArtifactResolution


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner that isolates filesystem side-effects."""

    return CliRunner()


def _create_registry(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE registry (
                project TEXT,
                change_id TEXT,
                change_name TEXT,
                deployed_at TEXT,
                deployer_name TEXT,
                deployer_email TEXT,
                tag TEXT
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def _make_change(name: str) -> Change:
    timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return Change.create(
        name=name,
        script_paths={
            "deploy": Path("deploy") / f"{name}.sql",
            "revert": Path("revert") / f"{name}.sql",
        },
        planner="Tester",
        planned_at=timestamp,
    )


def test_status_requires_explicit_target(runner: CliRunner) -> None:
    """Invoking status without a target should raise a user-facing error."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["status"])

        assert result.exit_code != 0
        assert "A target must be provided" in result.output


def test_status_rejects_project_mismatch(runner: CliRunner) -> None:
    """A mismatched --project filter should raise a CommandError."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        write_plan(project_name="widgets", default_engine="sqlite", entries=(), plan_path=plan_path)

        result = runner.invoke(
            main,
            [
                "status",
                "--target",
                "db:sqlite:registry.db",
                "--project",
                "other",
            ],
        )

        assert result.exit_code != 0
        assert "does not match requested project" in result.output


def test_status_rejects_registry_project_mismatch(runner: CliRunner, tmp_path: Path) -> None:
    """Plan and registry project disagreements should raise a CommandError."""

    plan_path = tmp_path / "sqlitch.plan"
    write_plan(project_name="widgets", default_engine="sqlite", entries=(), plan_path=plan_path)

    db_path = tmp_path / "registry.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE registry (
            project TEXT,
            change_id TEXT,
            change_name TEXT,
            deployed_at TEXT,
            deployer_name TEXT,
            deployer_email TEXT,
            tag TEXT
        )
        """
    )
    connection.execute(
        "INSERT INTO registry VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("other", "abc", "users", "2025-01-01T00:00:00Z", "Ada", "ada@example.com", None),
    )
    connection.commit()
    connection.close()

    with runner.isolated_filesystem() as sandbox:
        sandbox_path = Path(sandbox)
        (sandbox_path / plan_path.name).write_bytes(plan_path.read_bytes())
        (sandbox_path / db_path.name).write_bytes(db_path.read_bytes())

        result = runner.invoke(
            main,
            [
                "status",
                "--target",
                f"db:sqlite:{db_path.name}",
            ],
        )

        assert result.exit_code != 0
        assert "Registry project" in result.output


def test_status_outputs_human_summary_when_in_sync(runner: CliRunner) -> None:
    """Successful human output should be emitted when plan and registry align."""

    with runner.isolated_filesystem():
        write_plan(
            project_name="widgets",
            default_engine="sqlite",
            entries=(),
            plan_path=Path("sqlitch.plan"),
        )
        _create_registry(Path("registry.db"))

        result = runner.invoke(
            main,
            [
                "status",
                "--target",
                "db:sqlite:registry.db",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "# On database db:sqlite:registry.db" in result.output
        assert "Nothing to deploy (up-to-date)" in result.output


def test_status_outputs_json_with_pending_changes(runner: CliRunner) -> None:
    """JSON format should include pending entries and exit non-zero when behind."""

    with runner.isolated_filesystem():
        write_plan(
            project_name="widgets",
            default_engine="sqlite",
            entries=(_make_change("users"),),
            plan_path=Path("sqlitch.plan"),
        )
        _create_registry(Path("registry.db"))

        result = runner.invoke(
            main,
            [
                "status",
                "--target",
                "db:sqlite:registry.db",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 1, result.output
        payload = json.loads(result.output)
        assert payload["status"] == "not_deployed"
        assert payload["pending_changes"] == ["users"]


def test_resolve_registry_target_rejects_empty_sqlite_uri(tmp_path: Path) -> None:
    """SQLite URIs without a payload should fail fast."""

    with pytest.raises(CommandError, match="explicit database path"):
        _resolve_registry_target("db:sqlite:", tmp_path)


def test_resolve_registry_target_rejects_memory_uri(tmp_path: Path) -> None:
    """In-memory SQLite URIs are not supported by status."""

    with pytest.raises(CommandError, match="not supported"):
        _resolve_registry_target("db:sqlite::memory:", tmp_path)


def test_determine_status_handles_ahead_state() -> None:
    """Deployments that include extra changes should report the database as ahead."""

    plan_changes = ("users", "flips")
    deployed_changes = ("legacy", "users", "flips")

    assert _determine_status(plan_changes, deployed_changes) == "ahead"


def test_calculate_pending_when_last_deploy_unknown() -> None:
    """When the deployed head is not in the plan, all plan changes should be pending."""

    plan_changes = ("users", "flips")
    deployed_changes = ("hashtags",)

    assert _calculate_pending(plan_changes, deployed_changes) == plan_changes


def test_render_human_output_includes_ahead_marker() -> None:
    """Human rendering should report ahead status when applicable."""

    rows = (
        RegistryRow(
            project="widgets",
            change_id="abc",
            change_name="users",
            deployed_at="2025-01-01T00:00:00Z",
            deployer_name="Ada",
            deployer_email="ada@example.com",
            tag=None,
        ),
    )

    rendered = _render_human_output(
        project="widgets",
        target="db:sqlite:dev.db",
        rows=rows,
        status="ahead",
        pending_changes=(),
    )

    assert "Database is ahead of the plan" in rendered


def test_render_human_output_handles_not_deployed() -> None:
    """When no registry rows exist, rendering should show the not deployed message."""

    rendered = _render_human_output(
        project="widgets",
        target="db:sqlite:dev.db",
        rows=(),
        status="not_deployed",
        pending_changes=("users",),
    )

    assert "(not deployed)" in rendered
    assert "No deployments have been recorded yet." in rendered


def test_render_human_output_lists_pending_changes() -> None:
    """Behind status should enumerate pending change names."""

    rows = (
        RegistryRow(
            project="widgets",
            change_id="abc",
            change_name="users",
            deployed_at="2025-01-01T00:00:00Z",
            deployer_name="Ada",
            deployer_email="ada@example.com",
            tag=None,
        ),
    )

    rendered = _render_human_output(
        project="widgets",
        target="db:sqlite:dev.db",
        rows=rows,
        status="behind",
        pending_changes=("flips", "hashtags"),
    )

    assert "Undeployed changes:" in rendered
    assert "* flips" in rendered
    assert "* hashtags" in rendered


def test_render_human_output_reports_in_sync() -> None:
    """Default branch should report that nothing remains to deploy."""

    rows = (
        RegistryRow(
            project="widgets",
            change_id="abc",
            change_name="users",
            deployed_at="2025-01-01T00:00:00Z",
            deployer_name="Ada",
            deployer_email="ada@example.com",
            tag="v1.0",
        ),
    )

    rendered = _render_human_output(
        project="widgets",
        target="db:sqlite:dev.db",
        rows=rows,
        status="in_sync",
        pending_changes=(),
    )

    assert "Nothing to deploy (up-to-date)" in rendered


def test_build_json_payload_without_registry_rows(tmp_path: Path) -> None:
    """JSON payload should omit change details when no registry rows are present."""

    plan = write_plan(
        project_name="widgets",
        default_engine="sqlite",
        entries=(),
        plan_path=tmp_path / "plan.plan",
    )

    payload = _build_json_payload(
        project="widgets",
        target="db:sqlite:memory.db",
        status="not_deployed",
        plan=plan,
        rows=(),
        pending_changes=("users",),
    )

    assert payload["change"] is None
    assert payload["pending_changes"] == ["users"]


def test_build_json_payload_with_registry_rows(tmp_path: Path) -> None:
    """JSON payload should include the last registry row when present."""

    plan = write_plan(
        project_name="widgets",
        default_engine="sqlite",
        entries=(),
        plan_path=tmp_path / "sqlitch.plan",
    )
    rows = (
        RegistryRow(
            project="widgets",
            change_id="abc",
            change_name="users",
            deployed_at="2025-01-01T00:00:00Z",
            deployer_name="Ada",
            deployer_email="ada@example.com",
            tag="v1.0",
        ),
    )

    payload = _build_json_payload(
        project="widgets",
        target="db:sqlite:memory.db",
        status="in_sync",
        plan=plan,
        rows=rows,
        pending_changes=(),
    )

    assert payload["change"] == {
        "name": "users",
        "deploy_id": "abc",
        "deployed_at": "2025-01-01T00:00:00Z",
        "by": {"name": "Ada", "email": "ada@example.com"},
        "tag": "v1.0",
    }
    assert payload["status"] == "in_sync"


def test_resolve_plan_path_prefers_override(tmp_path: Path) -> None:
    """Providing an override path should be respected when it exists."""

    plan_path = tmp_path / "override.plan"
    plan_path.write_text("%project=widgets\n%default_engine=sqlite\n", encoding="utf-8")

    result = _resolve_plan_path(tmp_path, override=plan_path, env={})

    assert result == plan_path


def test_resolve_plan_path_raises_when_override_missing(tmp_path: Path) -> None:
    """Missing override paths should raise a CommandError."""

    override = tmp_path / "missing.plan"
    with pytest.raises(CommandError, match="missing"):
        _resolve_plan_path(tmp_path, override=override, env={})


def test_resolve_plan_path_respects_env_variable(tmp_path: Path) -> None:
    """Environment variables should control plan discovery when provided."""

    env_plan = tmp_path / "env.plan"
    env_plan.write_text("%project=env\n%default_engine=sqlite\n", encoding="utf-8")

    result = _resolve_plan_path(tmp_path, override=None, env={"SQLITCH_PLAN_FILE": env_plan.name})

    assert result == env_plan


def test_resolve_plan_path_env_missing_file(tmp_path: Path) -> None:
    """Missing files referenced by environment variables should raise errors."""

    with pytest.raises(CommandError, match="missing"):
        _resolve_plan_path(tmp_path, override=None, env={"SQLITCH_PLAN_FILE": "missing.plan"})


def test_resolve_plan_path_no_plan_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """If resolver cannot locate a plan, a CommandError should surface."""

    def fake_resolver(_: Path) -> ArtifactResolution:
        return ArtifactResolution(path=None, is_drop_in=False, source_name=None)

    monkeypatch.setattr("sqlitch.cli.commands.status.resolve_plan_file", fake_resolver)

    with pytest.raises(CommandError, match="No plan file found"):
        _resolve_plan_path(tmp_path, override=None, env={})


def test_resolve_plan_path_handles_conflicts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Artifact conflicts should be re-raised as CommandError instances."""

    def fake_resolver(_: Path) -> ArtifactResolution:
        raise ArtifactConflictError("conflict detected")

    monkeypatch.setattr("sqlitch.cli.commands.status.resolve_plan_file", fake_resolver)

    with pytest.raises(CommandError, match="conflict detected"):
        _resolve_plan_path(tmp_path, override=None, env={})


def test_load_plan_wraps_parser_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Plan parsing failures should bubble up as CommandError instances."""

    plan_path = tmp_path / "sqlitch.plan"
    plan_path.write_text("%project=widgets\n%default_engine=sqlite\n", encoding="utf-8")

    def fake_parse(_: Path) -> None:
        raise PlanParseError("boom")

    monkeypatch.setattr("sqlitch.cli.commands.status.parse_plan", fake_parse)

    with pytest.raises(CommandError, match="boom"):
        _load_plan(plan_path)


def test_resolve_registry_target_normalizes_relative_path(tmp_path: Path) -> None:
    """Non-prefixed targets should resolve relative to the project root."""

    db_path, target = _resolve_registry_target("registry.sqlite", tmp_path)

    assert db_path == tmp_path / "registry.sqlite"
    assert target == "registry.sqlite"


def test_load_registry_rows_missing_database(tmp_path: Path) -> None:
    """Missing registry databases should surface as CommandError instances."""

    with pytest.raises(CommandError, match="Registry database"):
        _load_registry_rows(tmp_path / "missing.db")


def test_determine_status_handles_not_deployed() -> None:
    """When no deployments exist, status should reflect the appropriate state."""

    assert _determine_status(("users",), ()) == "not_deployed"
    assert _determine_status((), ()) == "in_sync"


def test_calculate_pending_with_empty_plan() -> None:
    """No plan changes should return an empty pending tuple."""

    assert _calculate_pending((), ("users",)) == ()


def test_calculate_pending_with_no_deployments() -> None:
    """When nothing has been deployed, pending should include all plan changes."""

    assert _calculate_pending(("users", "flips"), ()) == ("users", "flips")
