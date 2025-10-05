"""Implementation of the ``sqlitch status`` command."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import click

from sqlitch.engine import EngineTarget, canonicalize_engine_name, create_engine
from sqlitch.engine.base import UnsupportedEngineError
from sqlitch.plan.model import Plan
from sqlitch.plan.parser import PlanParseError, parse_plan

from . import CommandError, register_command
from ._context import require_cli_context
from ._plan_utils import resolve_default_engine, resolve_plan_path

__all__ = ["status_command"]


@dataclass(frozen=True, slots=True)
class RegistryRow:
    """Represents a deployment entry sourced from the registry."""

    project: str
    change_id: str
    change_name: str
    deployed_at: str
    deployer_name: str
    deployer_email: str
    tag: str | None


@click.command("status")
@click.option("--target", "target_option", help="Deployment target URI or database path.")
@click.option("--project", "project_filter", help="Restrict output to the specified project.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("human", "json"), case_sensitive=False),
    default="human",
    show_default=True,
    help="Select the output format (human or json).",
)
@click.pass_context
def status_command(
    ctx: click.Context,
    *,
    target_option: str | None,
    project_filter: str | None,
    output_format: str,
) -> None:
    """Report the current deployment status for the requested target."""

    cli_context = require_cli_context(ctx)
    project_root = cli_context.project_root
    environment = cli_context.env

    target_value = target_option or cli_context.target
    if not target_value:
        raise CommandError("A target must be provided via --target or configuration.")

    plan_path = _resolve_plan_path(project_root, cli_context.plan_file, environment)
    default_engine = resolve_default_engine(
        project_root=project_root,
        config_root=cli_context.config_root,
        env=environment,
        engine_override=cli_context.engine,
        plan_path=plan_path,
    )
    plan = _load_plan(plan_path, default_engine)

    resolved_project = plan.project_name
    if project_filter and project_filter != resolved_project:
        raise CommandError(
            f"Plan project '{resolved_project}' does not match requested project '{project_filter}'"
        )

    engine_target, display_target = _resolve_registry_target(
        target_value, project_root, plan.default_engine
    )
    registry_rows = _load_registry_rows(engine_target, resolved_project)

    if registry_rows:
        registry_project = registry_rows[-1].project
        if registry_project != resolved_project:
            raise CommandError(
                f"Registry project '{registry_project}' does not match plan project '{resolved_project}'"
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
        )
        click.echo(json.dumps(payload, indent=2, sort_keys=False))
    else:
        text = _render_human_output(
            project=resolved_project,
            target=display_target,
            rows=registry_rows,
            status=status,
            pending_changes=pending,
        )
        click.echo(text, nl=False)

    exit_code = 0
    if status in {"behind", "ahead", "not_deployed"}:
        exit_code = 1

    if exit_code:
        ctx.exit(exit_code)


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
) -> tuple[EngineTarget, str]:
    display_target = target

    if target.startswith("db:"):
        remainder = target[3:]
        engine_token, separator, payload = remainder.partition(":")
        if not separator:
            raise CommandError(f"Malformed target URI: {target}")
        candidate_engine = engine_token or default_engine
        payload_value = payload
    else:
        candidate_engine = default_engine
        payload_value = target

    try:
        engine_name = canonicalize_engine_name(candidate_engine)
    except UnsupportedEngineError as exc:
        raise CommandError(f"Unsupported engine '{candidate_engine}'") from exc

    if engine_name == "sqlite":
        if not payload_value:
            raise CommandError("SQLite targets require an explicit database path")
        if payload_value == ":memory:":
            raise CommandError("In-memory SQLite targets are not supported")

        db_path = Path(payload_value)
        if not db_path.is_absolute():
            db_path = project_root / db_path
        if not db_path.exists():
            raise CommandError(f"Registry database {db_path} is missing")
        registry_uri = f"db:{engine_name}:{db_path.as_posix()}"
    else:
        registry_uri = target if target.startswith("db:") else f"db:{engine_name}:{payload_value}"

    engine_target = EngineTarget(name=display_target, engine=engine_name, uri=registry_uri)
    return engine_target, display_target


def _load_registry_rows(
    engine_target: EngineTarget,
    expected_project: str,
) -> tuple[RegistryRow, ...]:
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
    except Exception as exc:  # pragma: no cover - query failures propagated
        if _registry_schema_missing(exc):
            raise CommandError(
                f"Database {engine_target.registry_uri} has not been initialized for Sqitch"
            ) from exc
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
        return ()

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

    registry_rows: list[RegistryRow] = []
    for raw in rows:
        mapping = _row_mapping(raw)
        tag_value = mapping.get("latest_tag")
        registry_rows.append(
            RegistryRow(
                project=str(mapping.get("project", "")),
                change_id=str(mapping.get("change_id", "")),
                change_name=str(mapping.get("change_name", "")),
                deployed_at=str(mapping.get("committed_at", mapping.get("deployed_at", ""))),
                deployer_name=str(mapping.get("committer_name", mapping.get("deployer_name", ""))),
                deployer_email=str(
                    mapping.get("committer_email", mapping.get("deployer_email", ""))
                ),
                tag=str(tag_value) if tag_value is not None else None,
            )
        )

    return tuple(registry_rows)


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

    pending = _calculate_pending(plan_changes, deployed_changes)

    if pending:
        return "behind"

    extra = [name for name in deployed_changes if name not in plan_changes]
    if extra:
        return "ahead"

    return "in_sync"


def _calculate_pending(
    plan_changes: Sequence[str], deployed_changes: Sequence[str]
) -> tuple[str, ...]:
    if not plan_changes:
        return ()

    if not deployed_changes:
        return tuple(plan_changes)

    last_deployed = deployed_changes[-1]
    if last_deployed not in plan_changes:
        return tuple(plan_changes)

    last_index = plan_changes.index(last_deployed)
    return tuple(plan_changes[last_index + 1 :])


def _render_human_output(
    *,
    project: str,
    target: str,
    rows: Sequence[RegistryRow],
    status: str,
    pending_changes: Sequence[str],
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
            lines.append(f"# Tag:      {current.tag}")
        lines.extend(
            [
                f"# Deployed: {current.deployed_at}",
                f"# By:       {current.deployer_name} <{current.deployer_email}>",
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
    rows: Sequence[RegistryRow],
    pending_changes: Sequence[str],
) -> dict[str, object]:
    change_payload: dict[str, object] | None = None
    if rows:
        current = rows[-1]
        change_payload = {
            "name": current.change_name,
            "deploy_id": current.change_id,
            "deployed_at": current.deployed_at,
            "by": {
                "name": current.deployer_name,
                "email": current.deployer_email,
            },
            "tag": current.tag,
        }

    return {
        "project": project,
        "target": target,
        "status": status,
        "plan_checksum": plan.checksum,
        "change": change_payload,
        "pending_changes": list(pending_changes),
    }
