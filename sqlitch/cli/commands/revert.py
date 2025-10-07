"""Implementation of the ``sqlitch revert`` command."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import click

from sqlitch.engine.sqlite import (
    derive_sqlite_registry_uri,
    resolve_sqlite_filesystem_path,
    script_manages_transactions,
)
from sqlitch.plan.model import Change, Plan
from sqlitch.plan.parser import PlanParseError, parse_plan
from sqlitch.utils.time import isoformat_utc

from . import CommandError, register_command
from ._context import (
    environment_from,
    plan_override_from,
    project_root_from,
    quiet_mode_enabled,
    require_cli_context,
)
from ._plan_utils import resolve_default_engine, resolve_plan_path
from ..options import global_output_options, global_sqitch_options

__all__ = ["revert_command"]


@dataclass(frozen=True, slots=True)
class _RevertRequest:
    project_root: Path
    env: Mapping[str, str]
    plan_path: Path
    plan: Plan
    target: str
    to_change: str | None
    to_tag: str | None
    log_only: bool
    skip_prompt: bool
    quiet: bool
    config_root: Path


@click.command("revert")
@click.argument("target_args", nargs=-1)
@click.option("--target", "target_option", help="Deployment target alias or URI.")
@click.option("--to-change", "to_change", help="Revert through the specified change (inclusive).")
@click.option("--to-tag", "to_tag", help="Revert through the specified tag (inclusive).")
@click.option(
    "--log-only",
    is_flag=True,
    help="Show the revert actions without executing any scripts.",
)
@click.option(
    "-y",
    is_flag=True,
    help="Disable the prompt before reverting.",
)
@global_sqitch_options
@global_output_options
@click.pass_context
def revert_command(
    ctx: click.Context,
    *,
    target_args: tuple[str, ...],
    target_option: str | None,
    to_change: str | None,
    to_tag: str | None,
    log_only: bool,
    y: bool,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Revert deployed plan changes on the requested target."""

    cli_context = require_cli_context(ctx)
    project_root = project_root_from(ctx)
    env = environment_from(ctx)
    plan_override = plan_override_from(ctx)

    plan_path_for_engine = _resolve_plan_path(
        project_root=project_root, override=plan_override, env=env
    )

    default_engine = resolve_default_engine(
        project_root=project_root,
        config_root=cli_context.config_root,
        env=env,
        engine_override=cli_context.engine,
        plan_path=plan_path_for_engine,
    )

    target = _resolve_target(
        option_value=target_option,
        configured_target=cli_context.target,
        positional_targets=target_args,
    )

    request = _build_request(
        project_root=project_root,
        env=env,
        plan_override=plan_override,
        to_change=to_change,
        to_tag=to_tag,
        target=target,
        log_only=log_only,
        skip_prompt=y,
        quiet=quiet_mode_enabled(ctx),
        default_engine=default_engine,
        config_root=cli_context.config_root,
    )

    _execute_revert(request)


def _build_request(
    *,
    project_root: Path,
    env: Mapping[str, str],
    plan_override: Path | None,
    to_change: str | None,
    to_tag: str | None,
    target: str,
    log_only: bool,
    skip_prompt: bool,
    quiet: bool,
    default_engine: str,
    config_root: Path,
) -> _RevertRequest:
    if to_change and to_tag:
        raise CommandError("Cannot combine --to-change and --to-tag filters.")

    plan_path = _resolve_plan_path(project_root=project_root, override=plan_override, env=env)
    plan = _load_plan(plan_path, default_engine)

    return _RevertRequest(
        project_root=project_root,
        env=env,
        plan_path=plan_path,
        plan=plan,
        target=target,
        to_change=to_change,
        to_tag=to_tag,
        log_only=log_only,
        skip_prompt=skip_prompt,
        quiet=quiet,
        config_root=config_root,
    )


def _execute_revert(request: _RevertRequest) -> None:
    changes = _select_changes(
        plan=request.plan,
        to_change=request.to_change,
        to_tag=request.to_tag,
    )

    if request.log_only:
        _render_log_only_revert(request, changes)
        return

    if not changes:
        emitter = _build_emitter(request.quiet)
        emitter(f"Reverting plan '{request.plan.project_name}' on target '{request.target}'.")
        emitter("No changes to revert.")
        return

    # Prompt for confirmation unless -y flag provided
    if not request.skip_prompt:
        change_list = ", ".join(c.name for c in reversed(changes))
        if not click.confirm(
            f"Revert {len(changes)} change(s) from {request.target}? ({change_list})",
            default=False,
        ):
            raise CommandError("Revert aborted by user.")

    # Build engine target
    from sqlitch.engine.sqlite import SQLiteEngine
    from sqlitch.engine.base import EngineTarget

    # For SQLite, derive registry URI
    workspace_uri = request.target
    registry_uri = derive_sqlite_registry_uri(
        workspace_uri=workspace_uri,
        project_root=request.project_root,
        registry_override=None,  # TODO: support registry override
    )

    engine_target = EngineTarget(
        name=workspace_uri,
        engine="sqlite",
        uri=workspace_uri,
        registry_uri=registry_uri,
    )
    engine = SQLiteEngine(engine_target)

    emitter = _build_emitter(request.quiet)
    emitter(f"Reverting plan '{request.plan.project_name}' on target '{request.target}'.")

    # Get committer identity
    committer_name, committer_email = _resolve_committer_identity(
        request.env, request.config_root, request.project_root
    )

    # Connect to workspace (automatically attaches registry)
    try:
        connection = engine.connect_workspace()
    except Exception as exc:
        raise CommandError(
            f"Failed to connect to deployment target {engine_target.uri}: {exc}"
        ) from exc

    # Set manual transaction control
    connection.isolation_level = None
    registry_schema = "sqitch"

    try:
        # Load currently deployed changes
        deployed = _load_deployed_changes(connection, registry_schema, request.plan.project_name)

        # Filter to only revert deployed changes in reverse order
        # If --to-change or --to-tag specified, `changes` contains the target point
        # We revert everything AFTER the target (in deployment order)
        changes_to_keep_set = (
            {c.name for c in changes} if (request.to_change or request.to_tag) else set()
        )

        changes_to_revert = []
        for change in reversed(request.plan.changes):
            if change.name in deployed:
                # If we have a target and this change should be kept, stop
                if changes_to_keep_set and change.name in changes_to_keep_set:
                    break
                changes_to_revert.append(change)

        if not changes_to_revert:
            emitter("No changes to revert (none are currently deployed).")
            return

        # Revert each change
        for change in changes_to_revert:
            _revert_change(
                connection=connection,
                project=request.plan.project_name,
                plan_root=request.plan_path.parent,
                change=change,
                env=request.env,
                committer_name=committer_name,
                committer_email=committer_email,
                deployed=deployed,
                registry_schema=registry_schema,
                emitter=emitter,
            )
            emitter(f"- {change.name}")

    finally:
        connection.close()


def _load_deployed_changes(
    connection: sqlite3.Connection, registry_schema: str, project: str
) -> dict[str, dict[str, str]]:
    """Load deployed changes from registry for the given project."""
    cursor = connection.execute(
        f'SELECT "change", change_id, script_hash FROM {registry_schema}.changes '
        f"WHERE project = ? ORDER BY committed_at DESC",
        (project,),
    )
    try:
        rows = cursor.fetchall()
    finally:
        cursor.close()

    deployed: dict[str, dict[str, str]] = {}
    for change_name, change_id, script_hash in rows:
        deployed[str(change_name)] = {
            "change_id": str(change_id),
            "script_hash": str(script_hash) if script_hash is not None else "",
        }
    return deployed


def _revert_change(
    *,
    connection: sqlite3.Connection,
    project: str,
    plan_root: Path,
    change: Change,
    env: Mapping[str, str],
    committer_name: str,
    committer_email: str,
    deployed: dict[str, dict[str, str]],
    registry_schema: str,
    emitter: Callable[[str], None],
) -> None:
    """Execute a revert script and update registry state for a change."""
    # Load revert script
    script_path = plan_root / "revert" / f"{change.name}.sql"
    if not script_path.exists():
        raise CommandError(f"Revert script {script_path} is missing for change '{change.name}'.")

    script_body = script_path.read_text(encoding="utf-8")
    manages_transactions = script_manages_transactions(script_body)

    # Get change metadata from deployed state
    change_metadata = deployed.get(change.name)
    if not change_metadata:
        raise CommandError(f"Change '{change.name}' is not deployed.")

    change_id = change_metadata["change_id"]

    # Parse planner identity
    planner_name, planner_email = _resolve_planner_identity(change.planner, env, committer_email)

    committed_at = isoformat_utc(datetime.now(timezone.utc), drop_microseconds=False)
    planned_at = isoformat_utc(change.planned_at, drop_microseconds=False)
    note = change.notes or ""

    def _record(cursor: sqlite3.Cursor) -> None:
        # Delete from changes table
        cursor.execute(
            f"DELETE FROM {registry_schema}.changes WHERE change_id = ?",
            (change_id,),
        )

        # Insert revert event
        cursor.execute(
            f"""
            INSERT INTO {registry_schema}.events (
                event,
                change_id,
                change,
                project,
                note,
                requires,
                conflicts,
                tags,
                committed_at,
                committer_name,
                committer_email,
                planned_at,
                planner_name,
                planner_email
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "revert",
                change_id,
                change.name,
                project,
                note,
                " ".join(change.dependencies),
                "",
                " ".join(change.tags),
                committed_at,
                committer_name,
                committer_email,
                planned_at,
                planner_name,
                planner_email,
            ),
        )

    try:
        _execute_change_transaction(
            connection, script_body, _record, manages_transactions=manages_transactions
        )
    except sqlite3.Error as exc:
        raise CommandError(f"Revert failed for change '{change.name}': {exc}") from exc

    # Remove from deployed dict
    deployed.pop(change.name, None)


def _execute_change_transaction(
    connection: sqlite3.Connection,
    script_body: str,
    record_callback: Callable[[sqlite3.Cursor], None],
    *,
    manages_transactions: bool,
) -> None:
    """Execute script and record registry entries within appropriate transaction scope."""
    if manages_transactions:
        # Script manages its own transactions
        cursor = connection.cursor()
        try:
            _execute_sqlite_script(cursor, script_body)
            cursor.close()

            # Record registry changes in separate transaction
            connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = connection.cursor()
                record_callback(cursor)
                cursor.close()
                connection.execute("COMMIT")
            except Exception:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
        except Exception:
            cursor.close()
            raise
    else:
        # Engine manages transaction
        connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = connection.cursor()
            _execute_sqlite_script(cursor, script_body)
            record_callback(cursor)
            cursor.close()
            connection.execute("COMMIT")
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise


def _execute_sqlite_script(cursor: sqlite3.Cursor, script_sql: str) -> None:
    """Execute script SQL statement-by-statement against cursor."""
    buffer = ""
    for line in script_sql.splitlines():
        buffer += line + "\n"
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                cursor.execute(statement)
            buffer = ""

    remainder = buffer.strip()
    if remainder:
        cursor.execute(remainder)


def _resolve_committer_identity(
    env: Mapping[str, str], config_root: Path, project_root: Path
) -> tuple[str, str]:
    """Resolve committer identity from environment or config."""
    from sqlitch.config.resolver import resolve_config

    # Try to load config to get user.name and user.email
    config_name = None
    config_email = None
    try:
        config = resolve_config(
            root_dir=project_root,
            config_root=config_root,
            env=env,
        )
        user_section = config.settings.get("user", {})
        config_name = user_section.get("name")
        config_email = user_section.get("email")
    except Exception:
        pass

    name = (
        config_name
        or env.get("SQLITCH_USER_NAME")
        or env.get("SQITCH_USER_NAME")
        or env.get("GIT_COMMITTER_NAME")
        or env.get("GIT_AUTHOR_NAME")
        or env.get("USER")
        or env.get("USERNAME")
        or "SQLitch User"
    )

    email = (
        config_email
        or env.get("SQLITCH_USER_EMAIL")
        or env.get("SQITCH_USER_EMAIL")
        or env.get("GIT_COMMITTER_EMAIL")
        or env.get("GIT_AUTHOR_EMAIL")
        or env.get("EMAIL")
    )

    if not email:
        sanitized = "".join(ch for ch in name.lower() if ch.isalnum() or ch in {".", "_"})
        sanitized = sanitized or "sqlitch"
        email = f"{sanitized}@example.invalid"

    return name, email


def _resolve_planner_identity(
    planner: str, env: Mapping[str, str], fallback_email: str
) -> tuple[str, str]:
    """Parse planner identity string into name and email components."""
    name, email = _parse_identity(planner)
    if email is None:
        email = fallback_email
    return name, email


def _parse_identity(identity: str) -> tuple[str, str | None]:
    """Parse an identity string like 'Alice <alice@example.com>' into (name, email)."""
    if "<" in identity and ">" in identity:
        name_part, email_part = identity.rsplit("<", 1)
        name = name_part.strip()
        email = email_part.rstrip(">").strip()
        return name, email
    return identity.strip(), None


def _resolve_target(
    *,
    option_value: str | None,
    configured_target: str | None,
    positional_targets: Sequence[str],
) -> str:
    """Resolve the target URI from command-line options or configuration."""
    if option_value and positional_targets:
        raise CommandError("Provide either --target or a positional target, not both.")

    if len(positional_targets) > 1:
        raise CommandError("Multiple positional targets are not supported yet.")

    if positional_targets:
        target = positional_targets[0]
    elif option_value:
        target = option_value
    else:
        target = configured_target

    if not target:
        raise CommandError(
            "A deployment target must be provided via --target, positional argument, or configuration."
        )

    return target


def _resolve_plan_path(
    *,
    project_root: Path,
    override: Path | None,
    env: Mapping[str, str],
) -> Path:
    return resolve_plan_path(
        project_root=project_root,
        override=override,
        env=env,
        missing_plan_message="Cannot read plan file sqitch.plan",
    )


def _load_plan(plan_path: Path, default_engine: str | None) -> Plan:
    try:
        return parse_plan(plan_path, default_engine=default_engine)
    except (PlanParseError, ValueError) as exc:  # pragma: no cover - delegated to parser tests
        raise CommandError(str(exc)) from exc
    except OSError as exc:  # pragma: no cover - IO failures surfaced to the CLI user
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc


def _select_changes(
    *,
    plan: Plan,
    to_change: str | None,
    to_tag: str | None,
) -> tuple[Change, ...]:
    changes = plan.changes
    if not changes:
        return ()

    if to_change:
        try:
            index = next(i for i, change in enumerate(changes) if change.name == to_change)
        except StopIteration as exc:
            raise CommandError(f"Plan does not contain change '{to_change}'.") from exc
        return changes[: index + 1]

    if to_tag:
        try:
            tag_entry = next(tag for tag in plan.tags if tag.name == to_tag)
        except StopIteration as exc:
            raise CommandError(f"Plan does not contain tag '{to_tag}'.") from exc
        return _select_changes(plan=plan, to_change=tag_entry.change_ref, to_tag=None)

    return changes


def _render_log_only_revert(request: _RevertRequest, changes: Sequence[Change]) -> None:
    emitter = _build_emitter(request.quiet)

    emitter(
        f"Reverting plan '{request.plan.project_name}' on target '{request.target}' (log-only)."
    )

    if not changes:
        emitter("No changes available for reversion.")
        emitter("Log-only run; no database changes were applied.")
        return

    for change in reversed(changes):
        emitter(f"Would revert change {change.name}")

    emitter("Log-only run; no database changes were applied.")


def _build_emitter(quiet: bool) -> Callable[[str], None]:
    def _emit(message: str) -> None:
        if not quiet:
            click.echo(message)

    return _emit


@register_command("revert")
def _register_revert(group: click.Group) -> None:
    """Attach the revert command to the root Click group."""

    group.add_command(revert_command)
