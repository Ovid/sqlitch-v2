"""Implementation of the ``sqlitch deploy`` command."""

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
from sqlitch.engine import (
    MYSQL_STUB_MESSAGE,
    POSTGRES_STUB_MESSAGE,
    EngineTarget,
    canonicalize_engine_name,
    create_engine,
)
from sqlitch.engine.base import UnsupportedEngineError
from sqlitch.engine.sqlite import (
    REGISTRY_ATTACHMENT_ALIAS,
    SQLiteEngine,
    extract_sqlite_statements,
    resolve_sqlite_filesystem_path,
    script_manages_transactions,
    validate_sqlite_script,
)
from sqlitch.plan.model import Change, Plan
from sqlitch.plan.parser import PlanParseError, parse_plan
from sqlitch.registry import LATEST_REGISTRY_VERSION, get_registry_migrations
from sqlitch.utils.identity import (
    generate_change_id,
    resolve_email,
    resolve_fullname,
    resolve_username,
)
from sqlitch.utils.logging import StructuredLogger
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

__all__ = ["deploy_command"]


@dataclass(frozen=True, slots=True)
class _DeployRequest:
    project_root: Path
    config_root: Path
    env: Mapping[str, str]
    plan_path: Path
    plan: Plan
    target: str
    to_change: str | None
    to_tag: str | None
    log_only: bool
    quiet: bool
    logger: StructuredLogger
    registry_override: str | None


@click.command("deploy")
@click.argument("target_args", nargs=-1)
@click.option("--target", "target_option", help="Deployment target alias or URI.")
@click.option("--to-change", "to_change", help="Deploy through the specified change (inclusive).")
@click.option("--to-tag", "to_tag", help="Deploy through the specified tag (inclusive).")
@click.option(
    "--log-only",
    is_flag=True,
    help="Show the deployment actions without executing any scripts.",
)
@global_sqitch_options
@global_output_options
@click.pass_context
def deploy_command(
    ctx: click.Context,
    *,
    target_args: tuple[str, ...],
    target_option: str | None,
    to_change: str | None,
    to_tag: str | None,
    log_only: bool,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Deploy pending plan changes to the requested target."""

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
        project_root=project_root,
        config_root=cli_context.config_root,
        env=env,
        default_engine=default_engine,
    )

    request = _build_request(
        project_root=project_root,
        config_root=cli_context.config_root,
        env=env,
        plan_override=plan_override,
        to_change=to_change,
        to_tag=to_tag,
        target=target,
        log_only=log_only,
        quiet=quiet_mode_enabled(ctx),
        default_engine=default_engine,
        logger=cli_context.logger,
        registry_override=cli_context.registry,
    )

    _execute_deploy(request)


def _build_request(
    *,
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
    plan_override: Path | None,
    to_change: str | None,
    to_tag: str | None,
    target: str,
    log_only: bool,
    quiet: bool,
    default_engine: str,
    logger: StructuredLogger,
    registry_override: str | None,
) -> _DeployRequest:
    if to_change and to_tag:
        raise CommandError("Cannot combine --to-change and --to-tag filters.")

    plan_path = _resolve_plan_path(project_root=project_root, override=plan_override, env=env)
    plan = _load_plan(plan_path, default_engine)
    _assert_plan_dependencies_present(plan=plan, plan_path=plan_path)

    return _DeployRequest(
        project_root=project_root,
        config_root=config_root,
        env=env,
        plan_path=plan_path,
        plan=plan,
        target=target,
        to_change=to_change,
        to_tag=to_tag,
        log_only=log_only,
        quiet=quiet,
        logger=logger,
        registry_override=registry_override,
    )


def _execute_deploy(request: _DeployRequest) -> None:
    logger = request.logger
    changes = _select_changes(
        plan=request.plan,
        to_change=request.to_change,
        to_tag=request.to_tag,
    )
    change_names = [change.name for change in changes]
    logger.debug(
        "deploy.changes.selected",
        payload={
            "plan": request.plan.project_name,
            "plan_path": request.plan_path.as_posix(),
            "changes": change_names,
            "to_change": request.to_change,
            "to_tag": request.to_tag,
        },
    )

    if request.log_only:
        logger.info(
            "deploy.log_only",
            payload={
                "plan": request.plan.project_name,
                "plan_path": request.plan_path.as_posix(),
                "target": request.target,
                "changes": change_names,
            },
        )
        _render_log_only_deploy(request, changes)
        return

    emitter = _build_emitter(request.quiet)

    engine_target, display_target = _resolve_engine_target(
        target=request.target,
        project_root=request.project_root,
        config_root=request.config_root,
        env=request.env,
        default_engine=request.plan.default_engine,
        plan_path=request.plan_path,
        registry_override=request.registry_override,
        logger=logger,
    )

    emitter(f"Deploying plan '{request.plan.project_name}' to target '{display_target}'.")
    logger.info(
        "deploy.start",
        payload={
            "plan": request.plan.project_name,
            "plan_path": request.plan_path.as_posix(),
            "target": engine_target.uri,
            "display_target": display_target,
            "registry": engine_target.registry_uri,
            "changes": change_names,
        },
    )

    if not changes:
        emitter("Nothing to deploy (up-to-date).")
        logger.info(
            "deploy.noop",
            payload={
                "reason": "no-plan-changes",
                "plan": request.plan.project_name,
                "target": engine_target.uri,
            },
        )
        return

    committer_name, committer_email = _resolve_committer_identity(
        request.env,
        request.config_root,
        request.project_root,
    )

    engine, connection = _create_engine_connection(engine_target)

    if not isinstance(engine, SQLiteEngine):  # pragma: no cover - defensive guard
        raise CommandError("Only the SQLite engine is supported for deploy in this milestone")

    registry_schema = REGISTRY_ATTACHMENT_ALIAS

    try:
        _initialise_registry_state(
            connection=connection,
            registry_schema=registry_schema,
            project=request.plan.project_name,
            plan=request.plan,
            committer_name=committer_name,
            committer_email=committer_email,
            emitter=emitter,
            registry_uri=engine_target.registry_uri,
        )

        deployed_ids, deployed_metadata = _load_deployed_state(
            connection=connection,
            registry_schema=registry_schema,
            project=request.plan.project_name,
        )
        
                # Compute change_id for each change in the plan and filter out deployed ones
        pending = []
        for change in request.plan.changes:
            change_id = _compute_change_id_for_change(request.plan.project_name, change)
            if change_id not in deployed_ids:
                pending.append(change)

        _synchronise_registry_tags(
            connection=connection,
            registry_schema=registry_schema,
            project=request.plan.project_name,
            plan=request.plan,
            deployed=deployed_metadata,
            env=request.env,
            committer_name=committer_name,
            committer_email=committer_email,
        )

        if not pending:
            emitter("Nothing to deploy (up-to-date).")
            logger.info(
                "deploy.noop",
                payload={
                    "reason": "already-deployed",
                    "plan": request.plan.project_name,
                    "target": engine_target.uri,
                },
            )
            return

        applied = 0
        for change in pending:
            change_payload = {
                "change": change.name,
                "plan": request.plan.project_name,
                "target": engine_target.uri,
                "registry": engine_target.registry_uri,
            }
            logger.info("deploy.change.start", payload=change_payload)
            try:
                transaction_scope = _apply_change(
                    connection=connection,
                    project=request.plan.project_name,
                    plan_root=request.plan_path.parent,
                    change=change,
                    env=request.env,
                    committer_name=committer_name,
                    committer_email=committer_email,
                    deployed=deployed_metadata,
                    registry_schema=registry_schema,
                )
            except Exception as exc:
                logger.error(
                    "deploy.change.error",
                    message=str(exc),
                    payload=change_payload,
                )
                raise
            else:
                emitter(f"  + {change.name}")
                applied += 1
                logger.info(
                    "deploy.change.success",
                    payload={
                        **change_payload,
                        "transaction_scope": transaction_scope,
                    },
                )

        emitter(f"Deployment complete. Applied {applied} change(s).")
        logger.info(
            "deploy.complete",
            payload={
                "plan": request.plan.project_name,
                "target": engine_target.uri,
                "registry": engine_target.registry_uri,
                "applied": applied,
            },
        )
    except Exception as exc:
        logger.error(
            "deploy.error",
            message=str(exc),
            payload={
                "plan": request.plan.project_name,
                "target": engine_target.uri,
                "registry": engine_target.registry_uri,
            },
        )
        raise
    finally:
        try:
            connection.close()
        except Exception:  # pragma: no cover - best effort cleanup
            pass


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


def _assert_plan_dependencies_present(*, plan: Plan, plan_path: Path) -> None:
    """Verify all dependencies exist in the plan.
    
    Dependencies can include tag references (e.g., "userflips@v1.0.0-dev2" for reworked changes).
    We normalize these to bare change names when checking plan presence.
    """
    known_changes = {change.name for change in plan.changes}
    missing: list[str] = []
    for change in plan.changes:
        for dependency in change.dependencies:
            # Strip tag suffix if present (e.g., "userflips@v1.0.0-dev2" -> "userflips")
            dependency_name = dependency.split("@", 1)[0] if "@" in dependency else dependency
            if dependency_name not in known_changes and dependency not in missing:
                missing.append(dependency)

    if not missing:
        return

    plan_name = plan_path.name
    if len(missing) == 1:
        raise CommandError(f'Unable to find change "{missing[0]}" in plan {plan_name}')

    quoted = ", ".join(f'"{name}"' for name in missing)
    raise CommandError(f"Unable to find changes {quoted} in plan {plan_name}")


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
            raise CommandError(f'Unknown change: "{to_change}"') from exc
        return changes[: index + 1]

    if to_tag:
        try:
            tag_entry = next(tag for tag in plan.tags if tag.name == to_tag)
        except StopIteration as exc:
            raise CommandError(f"Plan does not contain tag '{to_tag}'.") from exc
        return _select_changes(plan=plan, to_change=tag_entry.change_ref, to_tag=None)

    return changes


def _resolve_engine_target(
    *,
    target: str,
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
    default_engine: str,
    plan_path: Path,
    registry_override: str | None,
    logger: StructuredLogger,
) -> tuple[EngineTarget, str]:
    """Return an :class:`EngineTarget` for the requested deployment target."""

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
    except UnsupportedEngineError as exc:
        raise CommandError(f"Unsupported engine '{engine_hint}'") from exc

    if engine_name == "sqlite":
        workspace_uri, display_target = _resolve_sqlite_workspace_uri(
            payload=workspace_payload,
            project_root=project_root,
            plan_path=plan_path,
            original_target=original_display,
        )
        registry_uri = config_resolver.resolve_registry_uri(
            engine=engine_name,
            workspace_uri=workspace_uri,
            project_root=project_root,
            registry_override=registry_override,
        )
        display_name = display_target or workspace_uri
        engine_target = EngineTarget(
            name=display_name,
            engine=engine_name,
            uri=workspace_uri,
            registry_uri=registry_uri,
        )
        return engine_target, display_name

    if engine_name == "mysql":
        logger.warning(
            "deploy.stub_engine",
            message=MYSQL_STUB_MESSAGE,
            payload={"engine": engine_name, "target": target},
        )
        raise CommandError(MYSQL_STUB_MESSAGE)

    if engine_name == "pg":
        logger.warning(
            "deploy.stub_engine",
            message=POSTGRES_STUB_MESSAGE,
            payload={"engine": engine_name, "target": target},
        )
        raise CommandError(POSTGRES_STUB_MESSAGE)

    raise CommandError(f"Engine '{engine_name}' deployment is not supported yet.")


def _resolve_sqlite_workspace_uri(
    *,
    payload: str,
    project_root: Path,
    plan_path: Path,
    original_target: str,
) -> tuple[str, str]:
    if payload == ":memory:":
        raise CommandError("In-memory SQLite targets are not supported")

    if payload.startswith("file:"):
        workspace_uri = f"db:sqlite:{payload}"
        display = original_target or workspace_uri
        return workspace_uri, display

    if payload:
        candidate = Path(payload)
    else:
        candidate = plan_path.with_suffix(".db")

    database_path = candidate if candidate.is_absolute() else project_root / candidate
    database_path = database_path.resolve()
    workspace_uri = f"db:sqlite:{database_path.as_posix()}"
    display = original_target or workspace_uri
    return workspace_uri, display


def _create_engine_connection(
    engine_target: EngineTarget,
) -> tuple[SQLiteEngine, sqlite3.Connection]:
    """Instantiate the engine and open a workspace connection."""

    try:
        engine = create_engine(engine_target)
    except UnsupportedEngineError as exc:  # pragma: no cover - defensive
        raise CommandError(f"Unsupported engine '{engine_target.engine}': {exc}") from exc

    if engine_target.engine != "sqlite":
        raise CommandError(f"Engine '{engine_target.engine}' deployment is not supported yet.")

    assert isinstance(engine, SQLiteEngine)  # narrow for downstream operations

    _ensure_sqlite_parent_directory(engine_target.uri)
    if engine_target.registry_uri:
        _ensure_sqlite_parent_directory(engine_target.registry_uri)

    try:
        connection = engine.connect_workspace()
    except Exception as exc:  # pragma: no cover - connection failure propagated
        raise CommandError(
            f"Failed to connect to deployment target {engine_target.uri}: {exc}"
        ) from exc

    # Manage SQLite transactions manually to coordinate workspace and registry writes.
    connection.isolation_level = None

    return engine, connection


def _ensure_sqlite_parent_directory(uri: str) -> None:
    """Create the parent directory for a SQLite database URI if required."""

    prefix = "db:sqlite:"
    if not uri.startswith(prefix):
        return

    path = resolve_sqlite_filesystem_path(uri)
    parent = path.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


def _initialise_registry_state(
    *,
    connection: sqlite3.Connection,
    registry_schema: str,
    project: str,
    plan: Plan,
    committer_name: str,
    committer_email: str,
    emitter: Callable[[str], None],
    registry_uri: str,
) -> None:
    """Prepare the attached registry schema inside an immediate transaction."""

    connection.execute("BEGIN IMMEDIATE")
    try:
        _ensure_registry_ready(
            connection=connection,
            registry_schema=registry_schema,
            project=project,
            plan=plan,
            committer_name=committer_name,
            committer_email=committer_email,
            emitter=emitter,
            registry_uri=registry_uri,
        )
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:  # pragma: no cover - best effort rollback
            pass
        raise
    else:
        connection.execute("COMMIT")


def _ensure_registry_ready(
    *,
    connection: sqlite3.Connection,
    registry_schema: str,
    project: str,
    plan: Plan,
    committer_name: str,
    committer_email: str,
    emitter: Callable[[str], None],
    registry_uri: str,
) -> None:
    """Initialise registry schema and project metadata if required."""

    try:
        if not _registry_tables_exist(connection, registry_schema):
            emitter(f"Adding registry tables to {registry_uri}")
            _apply_registry_baseline(connection, registry_schema)

        _ensure_release_entry(
            connection,
            registry_schema,
            committer_name=committer_name,
            committer_email=committer_email,
        )
        _ensure_project_entry(
            connection,
            registry_schema,
            project=project,
            plan_uri=plan.uri,
            creator_name=committer_name,
            creator_email=committer_email,
        )
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        raise CommandError(f"Failed to initialise registry: {exc}") from exc


def _registry_tables_exist(connection: sqlite3.Connection, registry_schema: str) -> bool:
    """Return ``True`` if essential registry tables are present."""

    cursor = connection.execute(
        f"SELECT name FROM {registry_schema}.sqlite_master WHERE type = 'table' "
        "AND name IN ('changes', 'projects', 'events')"
    )
    try:
        names = {str(row[0]) for row in cursor.fetchall()}
    finally:
        cursor.close()
    return {"changes", "projects", "events"}.issubset(names)


def _apply_registry_baseline(connection: sqlite3.Connection, registry_schema: str) -> None:
    """Create the registry schema using the bundled baseline migration."""

    migrations = get_registry_migrations("sqlite")
    baseline = next((migration for migration in migrations if migration.is_baseline), None)
    if baseline is None:  # pragma: no cover - defensive guard
        raise CommandError("SQLite registry baseline migration is unavailable.")

    statements: list[str] = []
    for raw_statement in baseline.sql.strip().split(";"):
        statement = raw_statement.strip()
        if not statement:
            continue

        upper = statement.upper()
        if upper == "BEGIN" or upper == "COMMIT":
            continue

        if statement.upper().startswith("CREATE TABLE "):
            statement = statement.replace("CREATE TABLE ", f"CREATE TABLE {registry_schema}.", 1)

        statements.append(statement)

    if not statements:  # pragma: no cover - defensive guard
        return

    for statement in statements:
        connection.execute(statement)


def _ensure_release_entry(
    connection: sqlite3.Connection,
    registry_schema: str,
    *,
    committer_name: str,
    committer_email: str,
) -> None:
    """Ensure the registry release version row exists."""

    cursor = connection.execute(
        f"SELECT 1 FROM {registry_schema}.releases WHERE version = ?",
        (LATEST_REGISTRY_VERSION,),
    )
    try:
        exists = cursor.fetchone() is not None
    finally:
        cursor.close()

    if not exists:
        connection.execute(
            f"INSERT INTO {registry_schema}.releases (version, installer_name, installer_email) "
            "VALUES (?, ?, ?)",
            (LATEST_REGISTRY_VERSION, committer_name, committer_email),
        )


def _ensure_project_entry(
    connection: sqlite3.Connection,
    registry_schema: str,
    *,
    project: str,
    plan_uri: str | None,
    creator_name: str,
    creator_email: str,
) -> None:
    """Insert the project metadata if it has not already been registered."""

    cursor = connection.execute(
        f"SELECT 1 FROM {registry_schema}.projects WHERE project = ?",
        (project,),
    )
    try:
        exists = cursor.fetchone() is not None
    finally:
        cursor.close()

    if not exists:
        connection.execute(
            f"INSERT INTO {registry_schema}.projects (project, uri, creator_name, creator_email) "
            "VALUES (?, ?, ?, ?)",
            (project, plan_uri, creator_name, creator_email),
        )


def _compute_change_id_for_change(project: str, change: Change) -> str:
    """Compute the change_id for a Change object using Sqitch's algorithm.
    
    Args:
        project: Project name
        change: Change object from the plan
        
    Returns:
        40-character SHA1 hex digest string
    """
    from sqlitch.utils.identity import generate_change_id
    from sqlitch.utils.time import parse_iso_datetime
    
    # Extract planner name and email
    # Change.planner format is "Name <email>"
    planner_match = change.planner.split("<", 1)
    if len(planner_match) == 2:
        planner_name = planner_match[0].strip()
        planner_email = planner_match[1].rstrip(">").strip()
    else:
        planner_name = change.planner
        planner_email = ""
    
    # Get dependencies (requires), excluding any @tag suffix
    requires = tuple(dep.split("@")[0] if "@" in dep else dep for dep in change.dependencies)
    
    # Change.planned_at is already a datetime object
    return generate_change_id(
        project=project,
        change=change.name,
        timestamp=change.planned_at,
        planner_name=planner_name,
        planner_email=planner_email,
        note=change.notes or "",
        requires=requires,
        conflicts=tuple(change.conflicts),
    )


def _load_deployed_state(
    connection: sqlite3.Connection,
    registry_schema: str,
    project: str,
) -> tuple[set[str], dict[str, dict[str, str]]]:
    """Return deployed change IDs and a mapping of names to registry metadata.
    
    Returns:
        A tuple of (deployed_change_ids, name_to_metadata) where:
        - deployed_change_ids: Set of change_id strings for all deployed changes
```
        - name_to_metadata: Dict mapping change names to their latest deployment metadata
                           (useful for script_hash validation and tag lookups)
    """

    cursor = connection.execute(
        f'SELECT "change", change_id, script_hash FROM {registry_schema}.changes WHERE project = ? '
        "ORDER BY committed_at ASC, change_id ASC",
        (project,),
    )
    try:
        rows = cursor.fetchall()
    finally:
        cursor.close()

    tag_cursor = connection.execute(
        f"SELECT change_id, tag FROM {registry_schema}.tags WHERE project = ?",
        (project,),
    )
    try:
        tag_rows = tag_cursor.fetchall()
    finally:
        tag_cursor.close()

    tag_lookup: dict[str, set[str]] = {}
    for change_id, tag in tag_rows:
        tag_lookup.setdefault(str(change_id), set()).add(str(tag))

    deployed_ids: set[str] = set()
    name_to_metadata: dict[str, dict[str, str]] = {}
    
    for change_name, change_id, script_hash in rows:
        change_id_str = str(change_id)
        deployed_ids.add(change_id_str)
        # Keep updating the dict so the last (most recent) version wins
        # This is used for script_hash checking and tag lookups
        name_to_metadata[str(change_name)] = {
            "change_id": change_id_str,
            "script_hash": str(script_hash) if script_hash is not None else "",
            "tags": tag_lookup.get(change_id_str, set()),
        }
    
    return deployed_ids, name_to_metadata


def _apply_change(
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
) -> str:
    """Execute a deploy script and record registry state for ``change``.

    Returns the transaction scope applied for structured logging.
    """

    script_path = _resolve_script_path(plan_root, change, "deploy")
    if not script_path.exists():
        raise CommandError(f"Deploy script {script_path} is missing for change '{change.name}'.")

    script_body = script_path.read_text(encoding="utf-8")
    validate_sqlite_script(script_body)
    script_hash = _compute_script_hash(script_body)
    manages_transactions = script_manages_transactions(script_body)

    dependency_lookup = {name: data["change_id"] for name, data in deployed.items()}
    _validate_dependencies(change, dependency_lookup)

    planner_name, planner_email = _resolve_planner_identity(
        change.planner,
        env,
        committer_email,
    )

    # Compute change_id using Sqitch's Git-style algorithm if not already set
    if change.change_id is not None:
        change_id = str(change.change_id)
    else:
        note = change.notes or ""
        change_id = generate_change_id(
            project=project,
            change=change.name,
            timestamp=change.planned_at,
            planner_name=planner_name,
            planner_email=planner_email,
            note=note,
            requires=change.dependencies,
            conflicts=(),  # SQLitch doesn't support conflicts yet
        )

    committed_at = isoformat_utc(datetime.now(timezone.utc), drop_microseconds=False)
    planned_at = isoformat_utc(change.planned_at, drop_microseconds=False)
    note = change.notes or ""

    def _record(cursor: sqlite3.Cursor) -> None:
        _record_deployment_entries(
            cursor=cursor,
            registry_schema=registry_schema,
            project=project,
            change=change,
            change_id=change_id,
            script_hash=script_hash,
            note=note,
            committed_at=committed_at,
            committer_name=committer_name,
            committer_email=committer_email,
            planned_at=planned_at,
            planner_name=planner_name,
            planner_email=planner_email,
            dependencies=change.dependencies,
            dependency_lookup=dependency_lookup,
            tags=change.tags,
        )

    try:
        _execute_change_transaction(
            connection,
            script_body,
            _record,
            manages_transactions=manages_transactions,
        )
    except sqlite3.Error as exc:  # pragma: no cover - execution error propagated
        try:
            _record_failure_event(
                connection=connection,
                registry_schema=registry_schema,
                project=project,
                change=change,
                change_id=change_id,
                note=note,
                committed_at=committed_at,
                committer_name=committer_name,
                committer_email=committer_email,
                planned_at=planned_at,
                planner_name=planner_name,
                planner_email=planner_email,
                dependencies=change.dependencies,
                tags=change.tags,
            )
        except CommandError as record_exc:
            message = (
                f"Deploy failed for change '{change.name}': {exc}; " f"additionally, {record_exc}"
            )
            raise CommandError(message) from exc
        raise CommandError(f"Deploy failed for change '{change.name}': {exc}") from exc
    except CommandError as exc:
        try:
            _record_failure_event(
                connection=connection,
                registry_schema=registry_schema,
                project=project,
                change=change,
                change_id=change_id,
                note=note,
                committed_at=committed_at,
                committer_name=committer_name,
                committer_email=committer_email,
                planned_at=planned_at,
                planner_name=planner_name,
                planner_email=planner_email,
                dependencies=change.dependencies,
                tags=change.tags,
            )
        except CommandError as record_exc:
            message = f"{exc}; additionally, {record_exc}"
            raise CommandError(message) from exc
        raise

    deployed[change.name] = {
        "change_id": change_id,
        "script_hash": script_hash,
        "tags": set(change.tags),
    }

    return "script-managed" if manages_transactions else "engine-managed"


def _resolve_script_path(plan_root: Path, change: Change, kind: str) -> Path:
    """Resolve a script path relative to the plan directory."""

    script_ref = change.script_paths.get(kind)
    if script_ref is None:
        raise CommandError(f"Change '{change.name}' is missing a {kind} script path.")

    path = Path(script_ref)
    if not path.is_absolute():
        path = plan_root / path
    
    return path


def _compute_script_hash(script_body: str) -> str:
    """Return the SHA-1 hash of the deploy script body."""

    return hashlib.sha1(script_body.encode("utf-8")).hexdigest()


def _resolve_committer_identity(
    env: Mapping[str, str],
    config_root: Path,
    project_root: Path,
) -> tuple[str, str]:
    """Resolve the committer name and email from config and environment variables.

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

    config_profile = None
    try:
        config_profile = resolve_config(
            root_dir=project_root,
            config_root=config_root,
            env=env,
        )
    except Exception:
        config_profile = None

    username = resolve_username(env)
    name = resolve_fullname(env, config_profile, username)
    email = resolve_email(env, config_profile, username)

    return name, email


def _resolve_planner_identity(
    planner: str,
    env: Mapping[str, str],
    fallback_email: str,
) -> tuple[str, str]:
    """Parse a planner identity string into name and email components."""

    identity = planner or "SQLitch Planner"
    name, email = _parse_identity(identity)

    if not email:
        email = env.get("SQLITCH_USER_EMAIL") or env.get("GIT_AUTHOR_EMAIL") or fallback_email

    if not email:
        sanitized = "".join(ch for ch in name.lower() if ch.isalnum() or ch in {".", "_"})
        sanitized = sanitized or "planner"
        email = f"{sanitized}@example.invalid"

    return name, email


def _parse_identity(identity: str) -> tuple[str, str | None]:
    """Split ``identity`` into name and optional email components."""

    text = identity.strip()
    if "<" in text and ">" in text and text.index("<") < text.index(">"):
        name_part, remainder = text.split("<", 1)
        email_part, _ = remainder.split(">", 1)
        name = name_part.strip() or text
        email = email_part.strip() or None
        return name, email
    return text, None


def _validate_dependencies(change: Change, deployed_lookup: Mapping[str, str]) -> None:
    """Ensure all required dependencies have been deployed.
    
    Dependencies can include tag references (e.g., "userflips@v1.0.0-dev2" for reworked changes).
    We normalize these to bare change names when checking deployment status.
    """
    
    def _normalize_dependency(dep: str) -> str:
        """Strip tag suffix from dependency name if present."""
        if "@" in dep:
            return dep.split("@", 1)[0]
        return dep

    missing = [
        dependency 
        for dependency in change.dependencies 
        if _normalize_dependency(dependency) not in deployed_lookup
    ]
    if not missing:
        return

    if len(missing) == 1:
        message = f"Change '{change.name}' depends on '{missing[0]}' which has not been deployed."
    else:
        joined = ", ".join(missing)
        message = f"Change '{change.name}' depends on the following changes which have not been deployed: {joined}."
    raise CommandError(message)


def _execute_change_transaction(
    connection: sqlite3.Connection,
    script_sql: str,
    recorder: Callable[[sqlite3.Cursor], None],
    *,
    manages_transactions: bool,
) -> None:
    """Execute ``script_sql`` while preserving atomic registry recording."""

    script_cursor = connection.cursor()
    registry_cursor = connection.cursor()
    try:
        if manages_transactions:
            _execute_sqlite_script(script_cursor, script_sql)
            _record_registry_entries(connection, registry_cursor, recorder)
        else:
            _execute_engine_managed_change(
                connection,
                script_cursor,
                registry_cursor,
                script_sql,
                recorder,
            )
    finally:
        script_cursor.close()
        registry_cursor.close()


def _execute_engine_managed_change(
    connection: sqlite3.Connection,
    script_cursor: sqlite3.Cursor,
    registry_cursor: sqlite3.Cursor,
    script_sql: str,
    recorder: Callable[[sqlite3.Cursor], None],
) -> None:
    savepoint = "sqlitch_change"
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(f"SAVEPOINT {savepoint}")
        try:
            _execute_sqlite_script(script_cursor, script_sql)
            recorder(registry_cursor)
        except Exception:
            _rollback_savepoint(connection, savepoint)
            raise
        else:
            _release_savepoint(connection, savepoint)
        connection.execute("COMMIT")
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:  # pragma: no cover - defensive guard
            pass
        raise


def _record_registry_entries(
    connection: sqlite3.Connection,
    registry_cursor: sqlite3.Cursor,
    recorder: Callable[[sqlite3.Cursor], None],
) -> None:
    savepoint = "sqlitch_registry"
    connection.execute(f"SAVEPOINT {savepoint}")
    try:
        recorder(registry_cursor)
    except Exception:
        _rollback_savepoint(connection, savepoint)
        raise
    else:
        _release_savepoint(connection, savepoint)


def _rollback_savepoint(connection: sqlite3.Connection, name: str) -> None:
    try:
        connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
    except sqlite3.Error:  # pragma: no cover - defensive guard
        pass
    finally:
        _release_savepoint(connection, name, suppress_errors=True)


def _release_savepoint(
    connection: sqlite3.Connection,
    name: str,
    *,
    suppress_errors: bool = False,
) -> None:
    try:
        connection.execute(f"RELEASE SAVEPOINT {name}")
    except sqlite3.Error:
        if suppress_errors:  # pragma: no cover - defensive guard
            return
        raise


def _execute_sqlite_script(cursor: sqlite3.Cursor, script_sql: str) -> None:
    """Execute ``script_sql`` statement-by-statement against ``cursor``."""
    for statement in extract_sqlite_statements(script_sql):
        cursor.execute(statement)


def _record_deployment_entries(
    *,
    cursor: sqlite3.Cursor,
    registry_schema: str,
    project: str,
    change: Change,
    change_id: str,
    script_hash: str,
    note: str,
    committed_at: str,
    committer_name: str,
    committer_email: str,
    planned_at: str,
    planner_name: str,
    planner_email: str,
    dependencies: Sequence[str],
    dependency_lookup: Mapping[str, str],
    tags: Sequence[str],
) -> None:
    """Persist registry entries for a deployed change."""

    cursor.execute(
        f"""
        INSERT INTO {registry_schema}.changes (
            change_id,
            script_hash,
            "change",
            project,
            note,
            committed_at,
            committer_name,
            committer_email,
            planned_at,
            planner_name,
            planner_email
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            change_id,
            script_hash,
            change.name,
            project,
            note,
            committed_at,
            committer_name,
            committer_email,
            planned_at,
            planner_name,
            planner_email,
        ),
    )

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
            "deploy",
            change_id,
            change.name,
            project,
            note,
            " ".join(dependencies),
            "",
            " ".join(tags),
            committed_at,
            committer_name,
            committer_email,
            planned_at,
            planner_name,
            planner_email,
        ),
    )

    for dependency in dependencies:
        # Normalize dependency name by stripping tag suffix if present (e.g., "userflips@v1.0.0-dev2" -> "userflips")
        # This handles reworked changes where dependencies reference previous versions
        dependency_name = dependency.split("@", 1)[0] if "@" in dependency else dependency
        dependency_id = dependency_lookup.get(dependency_name)
        if dependency_id is None:
            raise CommandError(
                f"Dependency '{dependency}' is not recorded in the registry for change '{change.name}'."
            )
        cursor.execute(
            f"""
            INSERT INTO {registry_schema}.dependencies (change_id, type, dependency, dependency_id)
            VALUES (?, 'require', ?, ?)
            """,
            (change_id, dependency, dependency_id),
        )

    _insert_registry_tags(
        cursor=cursor,
        registry_schema=registry_schema,
        project=project,
        change_id=change_id,
        note=note,
        committed_at=committed_at,
        committer_name=committer_name,
        committer_email=committer_email,
        planned_at=planned_at,
        planner_name=planner_name,
        planner_email=planner_email,
        tags=tags,
    )


def _record_failure_event(
    *,
    connection: sqlite3.Connection,
    registry_schema: str,
    project: str,
    change: Change,
    change_id: str,
    note: str,
    committed_at: str,
    committer_name: str,
    committer_email: str,
    planned_at: str,
    planner_name: str,
    planner_email: str,
    dependencies: Sequence[str],
    tags: Sequence[str],
) -> None:
    """Record a failure event for ``change`` in the registry."""

    cursor = connection.cursor()
    savepoint = "sqlitch_failure_event"
    normalized_note = _normalize_failure_event_note(change=change, note=note)

    try:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            # Ignore rollback errors when no transaction is active.
            pass

        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as exc:
        raise CommandError(
            f"Failed to record failure event for change '{change.name}': {exc}"
        ) from exc

    try:
        connection.execute(f"SAVEPOINT {savepoint}")
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
                "deploy_fail",
                change_id,
                change.name,
                project,
                normalized_note,
                " ".join(str(dependency) for dependency in dependencies),
                "",
                " ".join(str(tag) for tag in tags),
                committed_at,
                committer_name,
                committer_email,
                planned_at,
                planner_name,
                planner_email,
            ),
        )
    except sqlite3.Error as exc:
        _rollback_savepoint(connection, savepoint)
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:  # pragma: no cover - defensive guard
            pass
        raise CommandError(
            f"Failed to record failure event for change '{change.name}': {exc}"
        ) from exc
    else:
        _release_savepoint(connection, savepoint)
        try:
            connection.execute("COMMIT")
        except sqlite3.Error as exc:  # pragma: no cover - defensive guard
            raise CommandError(
                f"Failed to finalise failure event for change '{change.name}': {exc}"
            ) from exc
    finally:
        cursor.close()


def _normalize_failure_event_note(*, change: Change, note: str) -> str:
    """Return a registry note value consistent with Sqitch failure events."""

    candidate = (note or "").strip()
    if not candidate:
        return f"Add {change.name}"

    lower_candidate = candidate.lower()
    expected_suffix = f"add {change.name.lower()} table"
    if lower_candidate == expected_suffix:
        return f"Add {change.name}"

    return candidate


def _insert_registry_tags(
    *,
    cursor: sqlite3.Cursor,
    registry_schema: str,
    project: str,
    change_id: str,
    note: str,
    committed_at: str,
    committer_name: str,
    committer_email: str,
    planned_at: str,
    planner_name: str,
    planner_email: str,
    tags: Sequence[str],
) -> None:
    """Insert tag rows for ``tags`` referencing ``change_id`` into the registry."""

    for tag in tags:
        tag_id = hashlib.sha1(f"{change_id}:{tag}".encode("utf-8")).hexdigest()
        cursor.execute(
            f"""
            INSERT INTO {registry_schema}.tags (
                tag_id,
                tag,
                project,
                change_id,
                note,
                committed_at,
                committer_name,
                committer_email,
                planned_at,
                planner_name,
                planner_email
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tag_id,
                tag,
                project,
                change_id,
                note,
                committed_at,
                committer_name,
                committer_email,
                planned_at,
                planner_name,
                planner_email,
            ),
        )


def _synchronise_registry_tags(
    *,
    connection: sqlite3.Connection,
    registry_schema: str,
    project: str,
    plan: Plan,
    deployed: dict[str, dict[str, str]],
    env: Mapping[str, str],
    committer_name: str,
    committer_email: str,
) -> None:
    """Ensure registry tag entries mirror plan metadata for deployed changes.
    
    Note: The 'deployed' dict maps change names to their LATEST deployment metadata.
    For reworked changes with duplicate names, we need to match by change_id to avoid
    trying to insert the same tags multiple times.
    """

    # Build a set of already-processed change_ids to avoid duplicate tag insertions
    processed_change_ids: set[str] = set()

    for change in plan.changes:
        # Compute this change's ID to match against deployed changes
        change_id = _compute_change_id_for_change(project, change)
        
        # Skip if we've already processed this specific change_id
        if change_id in processed_change_ids:
            continue
        processed_change_ids.add(change_id)
        
        # Find deployed metadata by name (works for single changes, gets latest for reworks)
        deployed_meta = deployed.get(change.name)
        if not deployed_meta:
            continue
        
        # Only process if this is actually the deployed version
        # (deployed_meta might be for a different version of a reworked change)
        if deployed_meta["change_id"] != change_id:
            continue

        recorded_tags = set(deployed_meta.get("tags") or ())
        desired_tags = {str(tag) for tag in change.tags}
        missing_tags = tuple(tag for tag in desired_tags if tag not in recorded_tags)
        if not missing_tags:
            continue

        planner_name, planner_email = _resolve_planner_identity(
            change.planner,
            env,
            committer_email,
        )
        committed_at = isoformat_utc(datetime.now(timezone.utc), drop_microseconds=False)
        planned_at = isoformat_utc(change.planned_at, drop_microseconds=False)
        note = change.notes or ""

        cursor = connection.cursor()
        try:
            cursor.execute("BEGIN")
            _insert_registry_tags(
                cursor=cursor,
                registry_schema=registry_schema,
                project=project,
                change_id=deployed_meta["change_id"],
                note=note,
                committed_at=committed_at,
                committer_name=committer_name,
                committer_email=committer_email,
                planned_at=planned_at,
                planner_name=planner_name,
                planner_email=planner_email,
                tags=missing_tags,
            )
            cursor.execute("COMMIT")
        except sqlite3.Error as exc:  # pragma: no cover - defensive guard
            try:
                cursor.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise CommandError(f"Failed to record tags for change '{change.name}': {exc}") from exc
        finally:
            cursor.close()

        recorded_tags.update(missing_tags)
        deployed_meta["tags"] = recorded_tags


def _render_log_only_deploy(request: _DeployRequest, changes: Sequence[Change]) -> None:
    emitter = _build_emitter(request.quiet)

    emitter(
        f"Deploying plan '{request.plan.project_name}' to target '{request.target}' (log-only)."
    )

    if not changes:
        emitter("No changes available for deployment.")
        emitter("Log-only run; no database changes were applied.")
        return

    for change in changes:
        emitter(f"Would deploy change {change.name}")

    emitter("Log-only run; no database changes were applied.")


def _build_emitter(quiet: bool) -> Callable[[str], None]:
    def _emit(message: str) -> None:
        if not quiet:
            click.echo(message)

    return _emit


@register_command("deploy")
def _register_deploy(group: click.Group) -> None:
    """Attach the deploy command to the root Click group."""

    group.add_command(deploy_command)
