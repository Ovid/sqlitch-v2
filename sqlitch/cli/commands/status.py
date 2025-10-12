"""Implementation of the ``sqlitch status`` command."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import click

from sqlitch.config import resolver as config_resolver
from sqlitch.engine import EngineTarget, canonicalize_engine_name, create_engine
from sqlitch.engine.base import UnsupportedEngineError
from sqlitch.engine.sqlite import resolve_sqlite_filesystem_path
from sqlitch.plan.model import Plan
from sqlitch.plan.parser import PlanParseError, parse_plan

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import require_cli_context
from ._plan_utils import resolve_default_engine, resolve_plan_path

__all__ = ["status_command"]


@dataclass(frozen=True)
class CurrentChange:
    """Represents the currently deployed change for a project."""

    project: str
    change_id: str
    change_name: str
    deployed_at: str
    committer_name: str
    committer_email: str
    tag: str | None


@dataclass(frozen=True)
class FailureMetadata:
    """Represents the most recent failure event recorded in the registry."""

    change: str
    note: str
    committed_at: str
    committer_name: str
    committer_email: str


@click.command("status")
@click.argument("target_args", nargs=-1)
@click.option("--target", "target_option", help="Deployment target URI or database path.")
@click.option("--project", "project_filter", help="Restrict output to the specified project.")
@click.option("--show-tags", is_flag=True, help="Show deployment tags in the output.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("human", "json"), case_sensitive=False),
    default="human",
    show_default=True,
    help="Select the output format (human or json).",
)
@global_sqitch_options
@global_output_options
@click.pass_context
def status_command(
    ctx: click.Context,
    *,
    target_args: tuple[str, ...],
    target_option: str | None,
    project_filter: str | None,
    show_tags: bool,
    output_format: str,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Report the current deployment status for the requested target."""

    cli_context = require_cli_context(ctx)
    project_root = cli_context.project_root
    environment = cli_context.env

    # Resolve target from positional args, --target option, or config
    target_value = None
    if target_args:
        if len(target_args) > 1:
            raise CommandError("Only one target may be specified")
        target_value = target_args[0]
    elif target_option:
        target_value = target_option
    else:
        target_value = cli_context.target

    plan_path = _resolve_plan_path(project_root, cli_context.plan_file, environment)
    default_engine = resolve_default_engine(
        project_root=project_root,
        config_root=cli_context.config_root,
        env=environment,
        engine_override=cli_context.engine,
        plan_path=plan_path,
    )

    # If no target from CLI/env, check if the default engine has a target configured
    if not target_value and default_engine:
        config_profile = config_resolver.resolve_config(
            root_dir=project_root,
            config_root=cli_context.config_root,
            env=environment,
        )
        engine_section = f'engine "{default_engine}"'
        engine_target = config_profile.settings.get(engine_section, {}).get("target")
        if engine_target:
            target_value = engine_target

    if not target_value:
        raise CommandError("A target must be provided via --target or configuration.")
    plan = _load_plan(plan_path, default_engine)

    resolved_project = plan.project_name
    if project_filter and project_filter != resolved_project:
        raise CommandError(
            f"Plan project '{resolved_project}' does not match requested project '{project_filter}'"
        )

    engine_target, display_target = _resolve_registry_target(
        target_value,
        project_root,
        plan.default_engine,
        registry_override=cli_context.registry,
    )
    registry_rows, last_failure = _load_registry_state(engine_target, resolved_project)

    if registry_rows:
        registry_project = registry_rows[-1].project
        if registry_project != resolved_project:
            raise CommandError(
                f"Registry project '{registry_project}' does not match "
                f"plan project '{resolved_project}'"
            )

    plan_changes = tuple(change.name for change in plan.changes)
    deployed_changes = tuple(row.change_name for row in registry_rows)

    status = _determine_status(plan_changes, deployed_changes)
    pending = _calculate_pending(plan_changes, deployed_changes)

    normalized_format = output_format.lower()
    if normalized_format == "json":
        payload = _build_json_payload(
            project=resolved_project,
            target=display_target,
            status=status,
            plan=plan,
            rows=registry_rows,
            pending_changes=pending,
            last_failure=last_failure,
        )
        click.echo(json.dumps(payload, indent=2, sort_keys=False))
    else:
        text = _render_human_output(
            project=resolved_project,
            target=display_target,
            rows=registry_rows,
            status=status,
            pending_changes=pending,
            last_failure=last_failure,
        )
        click.echo(text, nl=False)

    if status == "not_deployed":
        ctx.exit(1)


@register_command("status")
def _register_status(group: click.Group) -> None:
    """Attach the status command to the root Click group."""

    group.add_command(status_command)


def _resolve_plan_path(
    project_root: Path,
    override: Path | None,
    env: Mapping[str, str],
) -> Path:
    """Resolve the plan file path for status helpers."""

    return resolve_plan_path(
        project_root=project_root,
        override=override,
        env=env,
        missing_plan_message="No plan file found. Run `sqlitch init` before inspecting the plan.",
    )


def _load_plan(plan_path: Path, default_engine: str | None = None) -> Plan:
    try:
        kwargs: dict[str, object] = {}
        if default_engine is not None:
            kwargs["default_engine"] = default_engine
        return parse_plan(plan_path, **kwargs)
    except (PlanParseError, ValueError) as exc:
        raise CommandError(str(exc)) from exc
    except OSError as exc:  # pragma: no cover - IO failures propagated to the user
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc


def _resolve_registry_target(
    target: str,
    project_root: Path,
    default_engine: str,
    *,
    registry_override: str | None = None,
) -> tuple[EngineTarget, str]:
    stripped_target = target.strip()
    if not stripped_target:
        raise CommandError("Target value cannot be empty.")

    display_target = stripped_target

    workspace_payload: str

    if stripped_target.startswith("db:"):
        remainder = stripped_target[3:]
        engine_token, separator, payload = remainder.partition(":")
        if not separator:
            raise CommandError(f"Malformed target URI: {stripped_target}")
        candidate_engine = engine_token or default_engine
        workspace_payload = payload
    else:
        candidate_engine = default_engine
        workspace_payload = stripped_target

    try:
        engine_name = canonicalize_engine_name(candidate_engine)
    except UnsupportedEngineError as exc:
        raise CommandError(f"Unsupported engine '{candidate_engine}'") from exc

    if engine_name == "sqlite":
        if not workspace_payload:
            raise CommandError("SQLite targets require an explicit database path")

        if workspace_payload.startswith("file:"):
            workspace_path = resolve_sqlite_filesystem_path(f"db:sqlite:{workspace_payload}")
        else:
            workspace_path = Path(workspace_payload)

        if str(workspace_path) == ":memory:":
            raise CommandError("In-memory SQLite targets are not supported")

        if not workspace_path.is_absolute():
            workspace_path = (project_root / workspace_path).resolve()
        else:
            workspace_path = workspace_path.resolve()

        workspace_path.parent.mkdir(parents=True, exist_ok=True)

        if workspace_payload.startswith("file:"):
            workspace_uri = f"db:sqlite:file:{workspace_path.as_posix()}"
        else:
            workspace_uri = f"db:sqlite:{workspace_path.as_posix()}"

        if stripped_target.startswith("db:"):
            if workspace_payload.startswith("file:"):
                display_target = workspace_uri
            elif workspace_payload not in {":memory:"}:
                if workspace_payload.startswith(("./", "../", ".\\", "..\\")):
                    display_target = workspace_uri

        registry_uri = config_resolver.resolve_registry_uri(
            engine=engine_name,
            workspace_uri=workspace_uri,
            project_root=project_root,
            registry_override=registry_override,
        )
    else:
        workspace_uri = (
            target if target.startswith("db:") else f"db:{engine_name}:{workspace_payload}"
        )
        registry_uri = registry_override if registry_override is not None else workspace_uri

    engine_target = EngineTarget(
        name=display_target,
        engine=engine_name,
        uri=workspace_uri,
        registry_uri=registry_uri,
    )
    return engine_target, display_target


def _load_registry_state(
    engine_target: EngineTarget,
    expected_project: str,
) -> tuple[tuple[CurrentChange, ...], FailureMetadata | None]:
    try:
        engine = create_engine(engine_target)
    except UnsupportedEngineError as exc:
        raise CommandError(f"Unsupported engine '{engine_target.engine}': {exc}") from exc

    try:
        connection = engine.connect_registry()
    except Exception as exc:  # pragma: no cover - connection failures propagated
        raise CommandError(
            f"Failed to connect to registry target {engine_target.registry_uri}: {exc}"
        ) from exc

    cursor = None
    rows: list[object] = []
    columns: list[str] = []
    failure_row: FailureMetadata | None = None
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT project FROM changes GROUP BY project")
        projects = {str(row[0]) for row in cursor.fetchall() if row and row[0] is not None}
        if projects and expected_project not in projects:
            mismatched = ", ".join(sorted(projects))
            raise CommandError(
                f"Registry project '{mismatched}' does not match plan project '{expected_project}'"
            )

        cursor.execute(
            """
            SELECT
                c.project,
                c.change_id,
                c."change" AS change_name,
                c.committed_at,
                c.committer_name,
                c.committer_email,
                (
                    SELECT tag
                    FROM tags
                    WHERE tags.change_id = c.change_id
                      AND tags.project = c.project
                    ORDER BY tags.committed_at DESC, tags.tag_id DESC
                    LIMIT 1
                ) AS latest_tag
            FROM changes AS c
            WHERE c.project = ?
            ORDER BY c.committed_at ASC, c.change_id ASC
            """,
            (expected_project,),
        )
        rows = cursor.fetchall()
        description = getattr(cursor, "description", None)
        columns = [column[0] for column in description] if description else []

        failure_row = _load_last_failure_event(connection, expected_project)
    except Exception as exc:  # pragma: no cover - query failures propagated
        if _registry_schema_missing(exc):
            rows = []
            columns = []
            failure_row = None
        else:
            raise CommandError(
                f"Failed to read registry database {engine_target.registry_uri}: {exc}"
            ) from exc
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:  # pragma: no cover - best effort cleanup
                pass
        try:
            connection.close()
        except Exception:  # pragma: no cover - best effort cleanup
            pass

    if not rows:
        return (), failure_row

    def _row_mapping(row: object) -> Mapping[str, object]:
        if isinstance(row, Mapping):
            return row
        if not columns:
            raise CommandError(
                f"Registry query for {engine_target.registry_uri} returned no column metadata"
            )
        if not isinstance(row, Sequence):
            raise CommandError(
                f"Registry query for {engine_target.registry_uri} returned unexpected row format"
            )
        return {columns[index]: row[index] for index in range(min(len(columns), len(row)))}

    registry_rows: list[CurrentChange] = []
    for raw in rows:
        mapping = _row_mapping(raw)
        tag_value = mapping.get("latest_tag")
        registry_rows.append(
            CurrentChange(
                project=str(mapping.get("project", "")),
                change_id=str(mapping.get("change_id", "")),
                change_name=str(mapping.get("change_name", "")),
                deployed_at=str(mapping.get("committed_at", mapping.get("deployed_at", ""))),
                committer_name=str(mapping.get("committer_name", mapping.get("deployer_name", ""))),
                committer_email=str(
                    mapping.get("committer_email", mapping.get("deployer_email", ""))
                ),
                tag=str(tag_value) if tag_value is not None else None,
            )
        )

    return tuple(registry_rows), failure_row


def _load_registry_rows(
    engine_target: EngineTarget,
    expected_project: str,
) -> tuple[CurrentChange, ...]:
    rows, _ = _load_registry_state(engine_target, expected_project)
    return rows


def _load_last_failure_event(
    connection: sqlite3.Connection, expected_project: str
) -> FailureMetadata | None:
    failure_cursor: sqlite3.Cursor | None = None
    try:
        failure_cursor = connection.cursor()
        try:
            failure_cursor.execute(
                """
                SELECT change, note, committed_at, committer_name, committer_email
                FROM events
                WHERE project = ? AND lower(event) = 'deploy_fail'
                ORDER BY committed_at DESC, change_id DESC
                LIMIT 1
                """,
                (expected_project,),
            )
        except sqlite3.Error as exc:
            message = str(exc).lower()
            missing_indicators = (
                "no such table: events",
                'relation "events" does not exist',
                'table "events" does not exist',
                'missing from-clause entry for table "events"',
            )
            if any(indicator in message for indicator in missing_indicators):
                return None
            raise

        row = failure_cursor.fetchone()
        if not row:
            return None
        return FailureMetadata(
            change=str(row[0] or ""),
            note=str(row[1] or ""),
            committed_at=str(row[2] or ""),
            committer_name=str(row[3] or ""),
            committer_email=str(row[4] or ""),
        )
    finally:
        if failure_cursor is not None:
            try:
                failure_cursor.close()
            except Exception:  # pragma: no cover - best effort cleanup
                pass


def _registry_schema_missing(error: Exception) -> bool:
    message = str(error).lower()
    missing_indicators = (
        "no such table: changes",
        'relation "changes" does not exist',
        'table "changes" does not exist',
        'missing from-clause entry for table "changes"',
        "no such table: tags",
        'relation "tags" does not exist',
        'table "tags" does not exist',
    )
    return any(indicator in message for indicator in missing_indicators)


def _determine_status(plan_changes: Sequence[str], deployed_changes: Sequence[str]) -> str:
    if not deployed_changes:
        return "not_deployed" if plan_changes else "in_sync"

    # Check for extra deployed changes first (ahead takes precedence)
    extra = [name for name in deployed_changes if name not in plan_changes]
    if extra:
        return "ahead"

    pending = _calculate_pending(plan_changes, deployed_changes)

    if pending:
        return "behind"

    return "in_sync"


def _calculate_pending(
    plan_changes: Sequence[str], deployed_changes: Sequence[str]
) -> tuple[str, ...]:
    if not plan_changes:
        return ()

    if not deployed_changes:
        return tuple(plan_changes)

    # For rework support: find where deployed and plan sequences diverge
    # This handles cases where the same change name appears multiple times
    deployed_count = len(deployed_changes)
    plan_count = len(plan_changes)

    # Find the first position where they differ
    matching_count = 0
    for i in range(min(deployed_count, plan_count)):
        if deployed_changes[i] == plan_changes[i]:
            matching_count = i + 1
        else:
            break

    # If all deployed changes match the plan prefix, return the remaining plan changes
    if matching_count == deployed_count:
        return tuple(plan_changes[deployed_count:])

    # If they diverge, the database is ahead or inconsistent
    # Return all remaining plan changes after the last match
    return tuple(plan_changes[matching_count:])


def _render_human_output(
    *,
    project: str,
    target: str,
    rows: Sequence[CurrentChange],
    status: str,
    pending_changes: Sequence[str],
    last_failure: FailureMetadata | None = None,
) -> str:
    lines: list[str] = [
        f"# On database {target}",
        f"# Project:  {project}",
    ]

    if rows:
        current = rows[-1]
        lines.extend(
            [
                f"# Change:   {current.change_id}",
                f"# Name:     {current.change_name}",
            ]
        )
        if current.tag:
            tag_display = current.tag if current.tag.startswith("@") else f"@{current.tag}"
            lines.append(f"# Tag:      {tag_display}")
        lines.extend(
            [
                f"# Deployed: {current.deployed_at}",
                f"# By:       {current.committer_name} <{current.committer_email}>",
            ]
        )
    else:
        lines.extend(
            [
                "# Change:   (not deployed)",
                "# Name:     (not deployed)",
                "# Deployed: (n/a)",
                "# By:       (n/a)",
            ]
        )

    if last_failure is not None:
        lines.append("# Last failure:")
        lines.append(f"#   Change:   {last_failure.change}")
        if last_failure.note:
            lines.append(f"#   Note:     {last_failure.note}")
        if last_failure.committed_at:
            lines.append(f"#   At:       {last_failure.committed_at}")
        lines.append(
            f"#   By:       {last_failure.committer_name} <{last_failure.committer_email}>"
        )
        lines.append("# ")
    else:
        lines.append("# ")

    if status == "behind":
        header = "Undeployed change:" if len(pending_changes) == 1 else "Undeployed changes:"
        lines.append(header)
        lines.extend(f"  * {name}" for name in pending_changes)
    elif status == "ahead":
        lines.append("Database is ahead of the plan")
    elif status == "not_deployed":
        lines.append("No deployments have been recorded yet.")
    else:
        lines.append("Nothing to deploy (up-to-date)")

    return "\n".join(lines) + "\n"


def _build_json_payload(
    *,
    project: str,
    target: str,
    status: str,
    plan: Plan,
    rows: Sequence[CurrentChange],
    pending_changes: Sequence[str],
    last_failure: FailureMetadata | None = None,
) -> dict[str, object]:
    change_payload: dict[str, object] | None = None
    if rows:
        current = rows[-1]
        change_payload = {
            "name": current.change_name,
            "deploy_id": current.change_id,
            "deployed_at": current.deployed_at,
            "by": {
                "name": current.committer_name,
                "email": current.committer_email,
            },
            "tag": current.tag,
        }

    payload: dict[str, object] = {
        "project": project,
        "target": target,
        "status": status,
        "plan_checksum": plan.checksum,
        "change": change_payload,
        "pending_changes": list(pending_changes),
    }

    if last_failure is not None:
        payload["last_failure"] = {
            "change": last_failure.change,
            "note": last_failure.note,
            "committed_at": last_failure.committed_at,
            "by": {
                "name": last_failure.committer_name,
                "email": last_failure.committer_email,
            },
        }

    return payload
