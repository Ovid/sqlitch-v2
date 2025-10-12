"""Implementation of the ``sqlitch verify`` command."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path

import click

from sqlitch.engine import EngineTarget, canonicalize_engine_name
from sqlitch.engine.scripts import Script
from sqlitch.plan.model import Plan
from sqlitch.plan.parser import parse_plan

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import require_cli_context
from ._plan_utils import resolve_default_engine, resolve_plan_path

__all__ = ["verify_command"]


def _execute_sqlite_verify_script(cursor: sqlite3.Cursor, script_sql: str) -> None:
    """Execute verification SQL statements."""
    buffer = ""
    for line in script_sql.splitlines():
        buffer += line + "\n"
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                cursor.execute(statement)
            buffer = ""


def _resolve_sqlite_workspace_uri(
    *,
    payload: str,
    project_root: Path,
    plan_path: Path,
    original_target: str,
) -> tuple[str, str]:
    """Resolve SQLite workspace URI from target payload."""
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


def _resolve_engine_target(
    *,
    target: str,
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
    default_engine: str,
    plan_path: Path,
    registry_override: str | None,
) -> tuple[EngineTarget, str]:
    """Return an EngineTarget for the requested target."""

    candidate = target.strip()

    # Check if the candidate is a target alias and resolve it
    if not candidate.startswith("db:"):
        # Might be a target alias - try to resolve it
        from sqlitch.config import resolver as config_resolver

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
        from sqlitch.config import resolver as config_resolver

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

    raise CommandError(f"Engine '{engine_name}' verification is not supported yet.")


def _strip_sqlite_uri_prefix(uri: str) -> str:
    if uri.startswith("db:sqlite:"):
        return uri[10:]
    if uri.startswith("sqlite:"):
        return uri[7:]
    return uri


@click.command("verify")
@click.argument("target_args", nargs=-1)
@click.option("--target", "target_option", help="Target to verify against.")
@click.option("--to-change", help="Verify up to this change.")
@click.option("--to-tag", help="Verify up to this tag.")
@click.option("--event", type=click.Choice(["deploy", "revert", "fail"]), help="Event type.")
@click.option("--mode", type=click.Choice(["all", "change", "tag"]), help="Verification mode.")
@click.option("--log-only", is_flag=True, help="Only log what would be done.")
@global_sqitch_options
@global_output_options
@click.pass_context
def verify_command(
    ctx: click.Context,
    target_args: tuple[str, ...],
    target_option: str | None,
    to_change: str | None,
    to_tag: str | None,
    event: str | None,
    mode: str | None,
    log_only: bool,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Execute verification scripts against deployed changes."""

    # Check for unimplemented features
    if log_only:
        raise CommandError("--log-only is not implemented yet.")
    if to_change:
        raise CommandError("--to-change is not implemented yet.")
    if to_tag:
        raise CommandError("--to-tag is not implemented yet.")
    if event:
        raise CommandError("--event is not implemented yet.")
    if mode:
        raise CommandError("--mode is not implemented yet.")

    cli_context = require_cli_context(ctx)
    project_root = cli_context.project_root
    environment = cli_context.env

    # Resolve target from positional args or --target option
    if target_args and target_option:
        raise CommandError("Provide either a positional target or --target, not both.")
    if len(target_args) > 1:
        raise CommandError("Multiple positional targets are not supported.")

    target_value = target_args[0] if target_args else target_option
    if not target_value:
        target_value = cli_context.target

    # Load plan and default engine first to check for engine.target config
    plan_path = resolve_plan_path(
        project_root=project_root,
        override=cli_context.plan_file,
        env=environment,
        missing_plan_message="No plan file found",
    )
    default_engine = resolve_default_engine(
        project_root=project_root,
        config_root=cli_context.config_root,
        env=environment,
        engine_override=cli_context.engine,
        plan_path=plan_path,
    )
    plan = _load_plan(plan_path, default_engine)

    # If no target from CLI/env, check if the default engine has a target configured
    if not target_value and default_engine:
        from sqlitch.config import resolver as config_resolver

        config_profile = config_resolver.resolve_config(
            root_dir=project_root,
            config_root=cli_context.config_root,
            env=environment,
        )
        engine_section = f'engine "{default_engine}"'
        engine_target_value = config_profile.settings.get(engine_section, {}).get("target")
        if engine_target_value and isinstance(engine_target_value, str):
            target_value = engine_target_value

    if not target_value:
        raise CommandError("A target must be provided via --target or configuration.")
    plan_change_names = [change.name for change in plan.changes]

    # Resolve engine target
    engine_target, display_target = _resolve_engine_target(
        target=target_value,
        project_root=project_root,
        config_root=cli_context.config_root,
        env=environment,
        default_engine=plan.default_engine,
        plan_path=plan_path,
        registry_override=cli_context.registry,
    )

    # EngineTarget.__post_init__ guarantees registry_uri is never None
    assert engine_target.registry_uri is not None

    workspace_path = _strip_sqlite_uri_prefix(engine_target.uri)
    registry_path = _strip_sqlite_uri_prefix(engine_target.registry_uri)
    workspace_display = Path(workspace_path).name
    if workspace_display.endswith(".db"):
        workspace_display = Path(workspace_display).stem
    if not workspace_display:
        workspace_display = display_target

    try:
        # Use isolation_level=None to enable autocommit mode.
        # This allows verify scripts to manage their own transactions (BEGIN/ROLLBACK).
        connection = sqlite3.connect(workspace_path, isolation_level=None)
    except sqlite3.Error as exc:
        raise CommandError(f"Failed to connect to workspace database: {exc}") from exc

    processed_changes = 0
    error_count = 0
    pending_changes: list[str] = []
    with closing(connection):
        try:
            connection.execute("ATTACH DATABASE ? AS sqitch", (registry_path,))
        except sqlite3.Error as exc:
            raise CommandError(f"Failed to attach registry: {exc}") from exc

        try:
            # Query registry with change_id to match against plan for rework detection
            with closing(
                connection.execute(
                    "SELECT change, change_id FROM sqitch.changes "
                    "WHERE project = ? ORDER BY committed_at",
                    (plan.project_name,),
                )
            ) as query_cursor:
                deployed_changes = list(query_cursor.fetchall())
        except sqlite3.Error as exc:
            raise CommandError(f"Failed to query registry: {exc}") from exc

        click.echo(f"Verifying {workspace_display}")

        if not deployed_changes:
            click.echo("No changes to verify.")
            return

        deployed_names = [name for name, _ in deployed_changes]
        pending_changes = [name for name in plan_change_names if name not in deployed_names]

        # Build a map of change occurrences to handle reworked changes
        # Track which occurrence of each change name we're processing
        change_occurrence_index: dict[str, int] = {}

        with closing(connection.cursor()) as cursor:
            for change_name, change_id in deployed_changes:
                processed_changes += 1

                # Track occurrence count for this change name
                occurrence = change_occurrence_index.get(change_name, 0)
                change_occurrence_index[change_name] = occurrence + 1

                # Find the matching Change object in the plan for this occurrence
                matching_change = None
                current_occurrence = 0
                for change_obj in plan.changes:
                    if change_obj.name == change_name:
                        if current_occurrence == occurrence:
                            matching_change = change_obj
                            break
                        current_occurrence += 1

                # Determine verify script filename
                if matching_change and matching_change.is_rework():
                    rework_tag = matching_change.get_rework_tag()
                    if rework_tag:
                        verify_filename = f"{change_name}@{rework_tag}.sql"
                    else:
                        verify_filename = f"{change_name}.sql"
                else:
                    verify_filename = f"{change_name}.sql"

                verify_script_path = project_root / "verify" / verify_filename

                if not verify_script_path.exists():
                    click.echo(f"  # {change_name} .. SKIP (no verify script)")
                    continue

                try:
                    script = Script.load(verify_script_path)
                    _execute_sqlite_verify_script(cursor, script.content)
                    click.echo(f"  * {change_name} .. ok")
                except Exception as exc:
                    click.echo(f"  # {change_name} .. NOT OK")
                    click.echo(f"  Error: {exc}", err=True)
                    error_count += 1

    if pending_changes:
        header = "Undeployed change:" if len(pending_changes) == 1 else "Undeployed changes:"
        click.echo(header)
        for change_name in pending_changes:
            click.echo(f"  * {change_name}")

    if error_count:
        click.echo()
        summary_title = "Verify Summary Report"
        click.echo(summary_title)
        click.echo("-" * len(summary_title))
        click.echo(f"Changes: {processed_changes}")
        click.echo(f"Errors:  {error_count}")
        raise CommandError("Verify failed")

    click.echo("Verify successful")


def _load_plan(plan_path: Path, default_engine: str) -> Plan:
    """Load and parse the plan file."""
    try:
        return parse_plan(plan_path, default_engine=default_engine)
    except Exception as e:
        raise CommandError(f"Failed to load plan: {e}") from e


@register_command("verify")
def _register_verify(group: click.Group) -> None:
    """Register the verify command with the root CLI group."""

    group.add_command(verify_command)
