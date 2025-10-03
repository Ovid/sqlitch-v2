"""Implementation of the ``sqlitch status`` command."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import click

from sqlitch.plan.model import Plan
from sqlitch.plan.parser import PlanParseError, parse_plan
from sqlitch.utils.fs import ArtifactConflictError, resolve_plan_file

from . import CommandError, register_command
from ._context import environment_from, plan_override_from, project_root_from, require_cli_context

__all__ = ["status_command"]

_SQLITE_PREFIX = "db:sqlite:"


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
    project_root = project_root_from(ctx)
    environment = environment_from(ctx)
    plan_override = plan_override_from(ctx)

    target_value = target_option or cli_context.target
    if not target_value:
        raise CommandError("A target must be provided via --target or configuration.")

    plan_path = _resolve_plan_path(project_root, override=plan_override, env=environment)
    plan = _load_plan(plan_path)

    resolved_project = plan.project_name
    if project_filter and project_filter != resolved_project:
        raise CommandError(
            f"Plan project '{resolved_project}' does not match requested project '{project_filter}'"
        )

    db_path, display_target = _resolve_registry_target(target_value, project_root)
    registry_rows = _load_registry_rows(db_path)

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
    *,
    override: Path | None,
    env: Mapping[str, str],
) -> Path:
    if override is not None:
        if not override.exists():
            raise CommandError(f"Plan file {override} is missing")
        return override

    env_value = env.get("SQITCH_PLAN_FILE") or env.get("SQLITCH_PLAN_FILE")
    if env_value:
        env_path = Path(env_value)
        resolved = env_path if env_path.is_absolute() else project_root / env_path
        if not resolved.exists():
            raise CommandError(f"Plan file {resolved} is missing")
        return resolved

    try:
        resolution = resolve_plan_file(project_root)
    except ArtifactConflictError as exc:
        raise CommandError(str(exc)) from exc

    if resolution.path is None:
        raise CommandError("No plan file found. Run `sqlitch init` before inspecting the plan.")
    return resolution.path


def _load_plan(plan_path: Path) -> Plan:
    try:
        return parse_plan(plan_path)
    except (PlanParseError, ValueError) as exc:
        raise CommandError(str(exc)) from exc
    except OSError as exc:  # pragma: no cover - IO failures propagated to the user
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc


def _resolve_registry_target(target: str, project_root: Path) -> tuple[Path, str]:
    if target.startswith(_SQLITE_PREFIX):
        payload = target[len(_SQLITE_PREFIX) :]
        if not payload:
            raise CommandError("SQLite targets require an explicit database path")
        if payload == ":memory:":
            raise CommandError("In-memory SQLite targets are not supported")
        db_path = Path(payload)
    else:
        db_path = Path(target)

    if not db_path.is_absolute():
        db_path = project_root / db_path

    return db_path, target


def _load_registry_rows(db_path: Path) -> tuple[RegistryRow, ...]:
    if not db_path.exists():
        raise CommandError(f"Registry database {db_path} is missing")

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        cursor = connection.execute(
            """
            SELECT project, change_id, change_name, deployed_at, deployer_name, deployer_email, tag
            FROM registry
            ORDER BY rowid
            """
        )
        rows = cursor.fetchall()
    except sqlite3.Error as exc:  # pragma: no cover - error propagation
        raise CommandError(f"Failed to read registry database {db_path}: {exc}") from exc
    finally:
        connection.close()

    return tuple(
        RegistryRow(
            project=row["project"],
            change_id=row["change_id"],
            change_name=row["change_name"],
            deployed_at=row["deployed_at"],
            deployer_name=row["deployer_name"],
            deployer_email=row["deployer_email"],
            tag=row["tag"],
        )
        for row in rows
    )


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


def _calculate_pending(plan_changes: Sequence[str], deployed_changes: Sequence[str]) -> tuple[str, ...]:
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

