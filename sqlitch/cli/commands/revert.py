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

from sqlitch.config import resolver as config_resolver
from sqlitch.engine import EngineTarget, canonicalize_engine_name
from sqlitch.engine.sqlite import (
    derive_sqlite_registry_uri,
    extract_sqlite_statements,
    resolve_sqlite_filesystem_path,
    script_manages_transactions,
    validate_sqlite_script,
)
from sqlitch.plan.model import Change, Plan
from sqlitch.plan.parser import PlanParseError, parse_plan
from sqlitch.plan.symbolic import resolve_symbolic_reference
from sqlitch.utils.time import isoformat_utc

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import (
    environment_from,
    plan_override_from,
    project_root_from,
    quiet_mode_enabled,
    require_cli_context,
)
from ._plan_utils import resolve_default_engine, resolve_plan_path

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
@click.option("--to", "to", help="Revert through the specified change or tag (inclusive).")
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
    to: str | None,
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

    # Validate --to option usage
    if to and (to_change or to_tag):
        raise CommandError("Cannot specify both --to and --to-change/--to-tag options.")

    # If --to is provided, determine if it's a tag or change
    # First, check if it contains symbolic references like @HEAD^, @ROOT, etc.
    if to:
        # Try to handle symbolic references early (before assuming it's a tag)
        # Tags in Sqitch start with '@', but so do symbolic references like @HEAD, @ROOT
        if to.startswith("@"):
            # Could be @HEAD^, @ROOT, @tag_name
            # We'll resolve this after loading the plan
            to_tag = to[1:]  # Strip @ for potential tag lookup
            to_change = None
        else:
            to_change = to
            to_tag = None

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
        project_root=project_root,
        config_root=cli_context.config_root,
        env=env,
        default_engine=default_engine,
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

    # Resolve symbolic references (e.g., @HEAD^, @ROOT, HEAD^2)
    resolved_to_change = to_change
    resolved_to_tag = to_tag
    
    if to_tag or to_change:
        # Get list of change names from plan for symbolic resolution
        change_names = [c.name for c in plan.changes]
        
        # Reconstruct the original reference
        original_ref = f"@{to_tag}" if to_tag else to_change
        
        try:
            # Try to resolve as symbolic reference
            resolved_name = resolve_symbolic_reference(original_ref, change_names)
            # If successful, it's a change reference (not a tag)
            resolved_to_change = resolved_name
            resolved_to_tag = None
        except ValueError:
            # Not a symbolic reference - could be a plain tag or change name
            # Keep the original classification
            pass

    return _RevertRequest(
        project_root=project_root,
        env=env,
        plan_path=plan_path,
        plan=plan,
        target=target,
        to_change=resolved_to_change,
        to_tag=resolved_to_tag,
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

    emitter = _build_emitter(request.quiet)

    # Prompt for confirmation unless -y flag provided
    if not request.skip_prompt:
        change_list = ", ".join(c.name for c in reversed(changes))
        if not click.confirm(
            f"Revert {len(changes)} change(s) from {request.target}? ({change_list})",
            default=False,
        ):
            raise CommandError("Revert aborted by user.")

    # Resolve engine target
    from sqlitch.engine.sqlite import SQLiteEngine

    engine_target, display_target = _resolve_engine_target(
        target=request.target,
        project_root=request.project_root,
        config_root=request.config_root,
        env=request.env,
        default_engine=request.plan.default_engine,
        registry_override=None,  # TODO: support registry override
    )
    engine = SQLiteEngine(engine_target)

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
        # Load currently deployed changes (keyed by change_id for rework support)
        deployed = _load_deployed_changes(connection, registry_schema, request.plan.project_name)

        # Import here to avoid circular dependency
        from sqlitch.cli.commands.deploy import (
            _compute_change_id_for_change,
            _resolve_parent_id_for_change,
        )

        # Build a cache of change IDs as we process the plan sequentially
        # This allows us to resolve parent IDs (previous change chronologically)
        change_id_cache: dict[int, str] = {}
        
        # Pre-compute all change IDs with correct parent resolution
        change_ids_by_index: dict[int, str] = {}
        for i, change in enumerate(request.plan.changes):
            parent_id = _resolve_parent_id_for_change(request.plan, i, change_id_cache)
            change_id = _compute_change_id_for_change(
                request.plan.project_name,
                change,
                request.plan.uri,
                parent_id,
            )
            change_id_cache[i] = change_id
            change_ids_by_index[i] = change_id

        # Filter to only revert deployed changes in reverse order
        # If --to-change or --to-tag specified, `changes` contains the target point
        # We revert everything AFTER the target (in deployment order)
        # 
        # Important: For reworked changes, we match by change_id, not name.
        changes_to_keep_indices = set()
        if request.to_change or request.to_tag:
            # Build a set of indices of changes to keep
            for i, change in enumerate(changes):
                changes_to_keep_indices.add(i)

        changes_to_revert = []
        for i in range(len(request.plan.changes) - 1, -1, -1):
            change = request.plan.changes[i]
            # Get the pre-computed change_id for this plan entry
            change_id = change_ids_by_index[i]
            
            # Check if this specific instance is deployed
            if change_id in deployed:
                # If we have a target and this change (by position) should be kept, stop
                if changes_to_keep_indices and i in changes_to_keep_indices:
                    break
                # Store both the change and its computed ID for the revert step
                changes_to_revert.append((change, change_id))

        target_change = changes[-1] if (request.to_change or request.to_tag) and changes else None

        if not changes_to_revert:
            if request.to_change or request.to_tag:
                label = (
                    request.to_change
                    or request.to_tag
                    or (target_change.name if target_change else "target")
                )
                emitter(f'No changes deployed since: "{label}"')
            else:
                emitter("Nothing to revert (nothing deployed)")
            return

        intro_message = _introductory_message(
            target=request.target,
            target_change=target_change,
            to_change=request.to_change,
            to_tag=request.to_tag,
        )
        emitter(intro_message)

        # Revert each change
        for change, change_id in changes_to_revert:
            try:
                _revert_change(
                    connection=connection,
                    project=request.plan.project_name,
                    plan_root=request.plan_path.parent,
                    change=change,
                    change_id=change_id,
                    env=request.env,
                    committer_name=committer_name,
                    committer_email=committer_email,
                    deployed=deployed,
                    registry_schema=registry_schema,
                    emitter=emitter,
                    uri=request.plan.uri,
                )
            except CommandError:
                emitter(f"  - {change.name} .. not ok")
                raise
            except Exception as exc:  # pragma: no cover - defensive guard
                emitter(f"  - {change.name} .. not ok")
                raise CommandError(f"Revert failed for change '{change.name}': {exc}") from exc
            else:
                emitter(f"  - {change.name} .. ok")

    finally:
        connection.close()


def _load_deployed_changes(
    connection: sqlite3.Connection, registry_schema: str, project: str
) -> dict[str, dict[str, str]]:
    """Load deployed changes from registry for the given project.
    
    Returns a dict mapping change_id to metadata. For reworked changes
    (same name, different instances), each instance has a unique change_id.
    """
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
        change_id_str = str(change_id)
        # Map by change_id, not name, to support reworked changes
        deployed[change_id_str] = {
            "change_name": str(change_name),
            "change_id": change_id_str,
            "script_hash": str(script_hash) if script_hash is not None else "",
        }
    return deployed


def _revert_change(
    *,
    connection: sqlite3.Connection,
    project: str,
    plan_root: Path,
    change: Change,
    change_id: str,
    env: Mapping[str, str],
    committer_name: str,
    committer_email: str,
    deployed: dict[str, dict[str, str]],
    registry_schema: str,
    emitter: Callable[[str], None],
    uri: str | None = None,
) -> None:
    """Execute a revert script and update registry state for a change."""
    # Load revert script using the script_paths from the parser
    script_ref = change.script_paths.get("revert")
    if script_ref is None:
        raise CommandError(f"Change '{change.name}' is missing a revert script path.")
    
    script_path = Path(script_ref)
    if not script_path.is_absolute():
        script_path = plan_root / script_path
    
    if not script_path.exists():
        raise CommandError(f"Revert script {script_path} is missing for change '{change.name}'.")

    script_body = script_path.read_text(encoding="utf-8")
    validate_sqlite_script(script_body)
    manages_transactions = script_manages_transactions(script_body)

    # Get change metadata from deployed state (keyed by change_id for rework support)
    change_metadata = deployed.get(change_id)
    if not change_metadata:
        raise CommandError(f"Change '{change.name}' is not deployed.")

    # Use the change_id from metadata (should match computed one)
    registry_change_id = change_metadata["change_id"]

    # Parse planner identity
    planner_name, planner_email = _resolve_planner_identity(change.planner, env, committer_email)

    committed_at = isoformat_utc(datetime.now(timezone.utc), drop_microseconds=False)
    planned_at = isoformat_utc(change.planned_at, drop_microseconds=False)
    note = change.notes or ""

    def _record(cursor: sqlite3.Cursor) -> None:
        # Delete tags first (if this change has any tags pointing to it)
        cursor.execute(
            f"DELETE FROM {registry_schema}.tags WHERE change_id = ?",
            (registry_change_id,),
        )

        # Delete dependencies FROM this change (where this is the source)
        cursor.execute(
            f"DELETE FROM {registry_schema}.dependencies WHERE change_id = ?",
            (registry_change_id,),
        )

        # Delete dependencies TO this change (where this is the target)
        # This is necessary because dependency_id FK doesn't have ON DELETE CASCADE
        cursor.execute(
            f"DELETE FROM {registry_schema}.dependencies WHERE dependency_id = ?",
            (registry_change_id,),
        )

        # Delete from changes table
        cursor.execute(
            f"DELETE FROM {registry_schema}.changes WHERE change_id = ?",
            (registry_change_id,),
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
                registry_change_id,
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
    for statement in extract_sqlite_statements(script_sql):
        cursor.execute(statement)


def _resolve_committer_identity(
    env: Mapping[str, str], config_root: Path, project_root: Path
) -> tuple[str, str]:
    """Resolve committer identity from environment or config.

    Resolution order for the name:
    1. SQLITCH_USER_NAME / SQITCH_USER_NAME / Git committer or author values
    2. Config file (``user.name``)
    3. System defaults (``USER`` / ``USERNAME``)
    4. Generated fallback

    Resolution order for the email:
    1. SQLITCH_USER_EMAIL / SQITCH_USER_EMAIL / Git committer or author values
    2. Config file (``user.email``)
    3. EMAIL environment variable
    4. Generated fallback based on the resolved name
    """
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
        env.get("SQLITCH_USER_NAME")
        or env.get("SQITCH_USER_NAME")
        or env.get("GIT_COMMITTER_NAME")
        or env.get("GIT_AUTHOR_NAME")
        or config_name
        or env.get("USER")
        or env.get("USERNAME")
        or "SQLitch User"
    )

    email = (
        env.get("SQLITCH_USER_EMAIL")
        or env.get("SQITCH_USER_EMAIL")
        or env.get("GIT_COMMITTER_EMAIL")
        or env.get("GIT_AUTHOR_EMAIL")
        or config_email
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


def _resolve_engine_target(
    *,
    target: str,
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
    default_engine: str,
    registry_override: str | None,
) -> tuple[EngineTarget, str]:
    """Return an EngineTarget for the requested target."""

    candidate = target.strip()

    # Check if the candidate is a target alias and resolve it
    if not candidate.startswith("db:"):
        # Might be a target alias - try to resolve it
        config_profile = config_resolver.resolve_config(
            root_dir=project_root,
            config_root=config_root,
            env=env,
        )
        target_section = f'target "{candidate}"'
        target_data = config_profile.settings.get(target_section)
        if target_data is not None:
            target_uri = target_data.get("uri")
            if target_uri:
                # Found a target alias - use the resolved URI
                candidate = target_uri
                original_display = target  # Keep the original alias name for display
            else:
                # Target section exists but no URI - treat as plain value
                original_display = candidate
        else:
            # Not a target alias - treat as plain value
            original_display = candidate
    else:
        original_display = candidate

    if candidate.startswith("db:"):
        remainder = candidate[3:]
        engine_token, separator, payload = remainder.partition(":")
        if not separator:
            raise CommandError(f"Malformed target URI: {target}")
        engine_hint = engine_token or default_engine
        workspace_payload = payload
        original_display = candidate
    else:
        engine_hint = default_engine
        workspace_payload = candidate
        original_display = candidate

    try:
        engine_name = canonicalize_engine_name(engine_hint)
    except Exception as exc:
        raise CommandError(f"Unsupported engine '{engine_hint}'") from exc

    if engine_name == "sqlite":
        # For SQLite, resolve the workspace path
        workspace_uri = f"db:sqlite:{workspace_payload}"
        registry_uri = config_resolver.resolve_registry_uri(
            engine=engine_name,
            workspace_uri=workspace_uri,
            project_root=project_root,
            registry_override=registry_override,
        )
        display_name = original_display
        engine_target = EngineTarget(
            name=display_name,
            engine=engine_name,
            uri=workspace_uri,
            registry_uri=registry_uri,
        )
        return engine_target, display_name

    raise CommandError(f"Engine '{engine_name}' revert is not supported yet.")


def _resolve_target(
    *,
    option_value: str | None,
    configured_target: str | None,
    positional_targets: Sequence[str],
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
    default_engine: str | None,
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

    # If no target from CLI/env, check if the default engine has a target configured
    if not target and default_engine:
        from sqlitch.config import resolver as config_resolver

        config_profile = config_resolver.resolve_config(
            root_dir=project_root,
            config_root=config_root,
            env=env,
        )
        engine_section = f'engine "{default_engine}"'
        engine_target = config_profile.settings.get(engine_section, {}).get("target")
        if engine_target:
            target = engine_target

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
    target_change = changes[-1] if (request.to_change or request.to_tag) and changes else None
    intro_message = _introductory_message(
        target=request.target,
        target_change=target_change,
        to_change=request.to_change,
        to_tag=request.to_tag,
    )

    emitter(f"{intro_message} (log-only)")

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


def _introductory_message(
    *,
    target: str,
    target_change: Change | None,
    to_change: str | None,
    to_tag: str | None,
) -> str:
    """Return the Sqitch-style introductory message for a revert operation."""

    if to_change or to_tag:
        label = target_change.name if target_change else (to_change or to_tag or "target")
        return f"Reverting changes to {label} from {target}"

    return f"Reverting all changes from {target}"


@register_command("revert")
def _register_revert(group: click.Group) -> None:
    """Attach the revert command to the root Click group."""

    group.add_command(revert_command)
