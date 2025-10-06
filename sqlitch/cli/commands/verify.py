"""Implementation of the ``sqlitch verify`` command."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import click

from sqlitch.config import resolver as config_resolver
from sqlitch.engine import EngineTarget, canonicalize_engine_name, create_engine
from sqlitch.engine.scripts import Script
from sqlitch.plan.model import Plan
from sqlitch.plan.parser import parse_plan
from sqlitch.registry.state import DeployedChange
from sqlitch.utils.logging import StructuredLogger

from . import CommandError, register_command
from ._context import require_cli_context
from ._plan_utils import resolve_default_engine, resolve_plan_path
from ..options import global_output_options, global_sqitch_options

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
    default_engine: str,
    plan_path: Path,
    registry_override: str | None,
) -> tuple[EngineTarget, str]:
    """Return an EngineTarget for the requested target."""

    candidate = target.strip()
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
    if not target_value:
        raise CommandError("A target must be provided via --target or configuration.")

    # Load plan
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

    # Resolve engine target
    engine_target, display_target = _resolve_engine_target(
        target=target_value,
        project_root=project_root,
        default_engine=plan.default_engine,
        plan_path=plan_path,
        registry_override=cli_context.registry,
    )

    # Get deployed changes from registry
    engine = create_engine(engine_target)

    # Connect to target database and attach registry
    import sqlite3
    from sqlitch.engine.sqlite import SQLiteEngine

    # Check engine type by name instead of isinstance to avoid test isolation issues
    if engine_target.engine != "sqlite":
        raise CommandError("Only SQLite engine is supported for verify in this milestone")

    # Parse URIs to get paths - strip db: and sqlite: prefixes
    workspace_uri = engine_target.uri
    if workspace_uri.startswith("db:sqlite:"):
        workspace_path = workspace_uri[10:]  # Remove "db:sqlite:"
    elif workspace_uri.startswith("sqlite:"):
        workspace_path = workspace_uri[7:]  # Remove "sqlite:"
    else:
        workspace_path = workspace_uri

    registry_uri = engine_target.registry_uri
    if registry_uri.startswith("db:sqlite:"):
        registry_path = registry_uri[10:]  # Remove "db:sqlite:"
    elif registry_uri.startswith("sqlite:"):
        registry_path = registry_uri[7:]  # Remove "sqlite:"
    else:
        registry_path = registry_uri

    # Connect to workspace and attach registry
    connection = sqlite3.connect(workspace_path)
    try:
        connection.execute(f"ATTACH DATABASE '{registry_path}' AS sqitch")

        # Query deployed changes
        cursor = connection.execute(
            "SELECT change FROM sqitch.changes WHERE project = ? ORDER BY committed_at",
            (plan.project_name,),
        )
        deployed_changes = [row[0] for row in cursor.fetchall()]
        cursor.close()
    except Exception as e:
        connection.close()
        raise CommandError(f"Failed to query registry: {e}") from e

    if not deployed_changes:
        connection.close()
        click.echo("No changes to verify.")
        return

    # Execute verify scripts
    verification_failed = False
    cursor = connection.cursor()

    for change_name in deployed_changes:
        # Find verify script
        verify_script_path = project_root / "verify" / f"{change_name}.sql"

        if not verify_script_path.exists():
            click.echo(f"# {change_name} .. SKIP (no verify script)")
            continue

        try:
            # Load and execute verify script
            script = Script.load(verify_script_path)
            _execute_sqlite_verify_script(cursor, script.content)
            click.echo(f"* {change_name} .. ok")
        except Exception as e:
            click.echo(f"# {change_name} .. NOT OK")
            click.echo(f"  Error: {e}", err=True)
            verification_failed = True

    cursor.close()
    connection.close()

    # Exit with appropriate code
    ctx.exit(1 if verification_failed else 0)


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
