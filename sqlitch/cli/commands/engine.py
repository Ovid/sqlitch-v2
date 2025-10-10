"""Implementation of the ``sqlitch engine`` command group."""

from __future__ import annotations

import configparser
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import click

from sqlitch.cli.main import CLIContext
from sqlitch.config.resolver import resolve_config
from sqlitch.utils.fs import ArtifactConflictError, resolve_config_file

from . import CommandError, register_command
from ._context import quiet_mode_enabled, require_cli_context
from ..options import global_output_options, global_sqitch_options

__all__ = ["engine_group"]

_SUPPORTED_ENGINES = {
    "sqlite": ("db:sqlite:",),
    "mysql": ("db:mysql:",),
    "pg": ("db:pg:", "db:postgres:"),
}


@dataclass(slots=True, frozen=True)
class EngineDefinition:
    """Materialised engine configuration entry."""

    name: str
    uri: str
    registry: str | None
    client: str | None
    verify: str | None
    plan: str | None


@click.group("engine", invoke_without_command=True)
@global_sqitch_options
@global_output_options
@click.pass_context
def engine_group(
    ctx: click.Context,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Manage engine definitions for SQLitch deployments."""

    require_cli_context(ctx)

    # If no subcommand was invoked, run the 'list' command by default
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_engines)


@engine_group.command("add")
@click.argument("name")
@click.argument("uri")
@click.option("--registry", help="Registry URI override to associate with the engine.")
@click.option("--client", help="Client executable path used for shelling out to the engine.")
@click.option("--plan", "plan_file", help="Plan file override tied to this engine definition.")
@click.option(
    "--verify/--no-verify",
    "verify_flag",
    default=None,
    help="Enable or disable post-deploy verification.",
)
@click.pass_context
def add_engine(
    ctx: click.Context,
    *,
    name: str,
    uri: str,
    registry: str | None,
    client: str | None,
    plan_file: str | None,
    verify_flag: bool | None,
) -> None:
    """Create a new engine definition in the configuration root."""

    cli_context = require_cli_context(ctx)
    
    # Resolve to validate, but store the original value if it's a target name
    resolved_uri = _resolve_engine_uri(cli_context=cli_context, candidate=uri)
    _validate_engine_uri(resolved_uri)
    
    # If the original value wasn't a URI, it was a target name - store the name, not the URI
    is_target_alias = not _is_supported_engine_uri(uri)
    target_value = uri if is_target_alias else resolved_uri

    _mutate_engine_definition(
        cli_context=cli_context,
        name=name,
        uri=target_value,  # Store target name if alias, URI if direct
        registry=registry,
        client=client,
        plan_file=plan_file,
        verify_flag=verify_flag,
        allow_existing=True,  # Allow upsert behavior like Sqitch
    )

    _emit(ctx, f"Created engine '{name}'")


@engine_group.command("update")
@click.argument("name")
@click.argument("uri")
@click.option("--registry", help="Registry URI override to associate with the engine.")
@click.option("--client", help="Client executable path used for shelling out to the engine.")
@click.option("--plan", "plan_file", help="Plan file override tied to this engine definition.")
@click.option(
    "--verify/--no-verify",
    "verify_flag",
    default=None,
    help="Enable or disable post-deploy verification.",
)
@click.pass_context
def update_engine(
    ctx: click.Context,
    *,
    name: str,
    uri: str,
    registry: str | None,
    client: str | None,
    plan_file: str | None,
    verify_flag: bool | None,
) -> None:
    """Update an existing engine definition."""

    cli_context = require_cli_context(ctx)
    
    # Resolve to validate, but store the original value if it's a target name
    resolved_uri = _resolve_engine_uri(cli_context=cli_context, candidate=uri)
    _validate_engine_uri(resolved_uri)
    
    # If the original value wasn't a URI, it was a target name - store the name, not the URI
    is_target_alias = not _is_supported_engine_uri(uri)
    target_value = uri if is_target_alias else resolved_uri

    _mutate_engine_definition(
        cli_context=cli_context,
        name=name,
        uri=target_value,  # Store target name if alias, URI if direct
        registry=registry,
        client=client,
        plan_file=plan_file,
        verify_flag=verify_flag,
        allow_existing=True,
    )

    _emit(ctx, f"Updated engine '{name}'")


@engine_group.command("remove")
@click.argument("name")
@click.option("--yes", "confirm", is_flag=True, help="Skip interactive confirmation prompt.")
@click.pass_context
def remove_engine(ctx: click.Context, *, name: str, confirm: bool) -> None:
    """Remove an engine definition from the configuration."""

    cli_context = require_cli_context(ctx)
    config_path = _engine_config_path(cli_context)
    parser = _load_parser(config_path)
    section = _section_name(name)

    if not parser.has_section(section):
        raise CommandError(f"Engine '{name}' is not defined.")

    if not confirm and not click.confirm(f"Remove engine '{name}'?", default=False):
        _emit(ctx, "Removal aborted")
        return

    parser.remove_section(section)
    _write_parser(config_path, parser)
    _emit(ctx, f"Removed engine '{name}'")


@engine_group.command("list")
@click.pass_context
def list_engines(ctx: click.Context) -> None:
    """List configured engines in precedence order."""

    cli_context = require_cli_context(ctx)
    config_path = _engine_config_path(cli_context)
    entries = tuple(_load_engines(config_path))

    if not entries:
        _emit(ctx, "No engines configured.")
        return

    lines = _format_engine_table(entries)
    for line in lines:
        _emit(ctx, line)


def _mutate_engine_definition(
    *,
    cli_context: CLIContext,
    name: str,
    uri: str,
    registry: str | None,
    client: str | None,
    plan_file: str | None,
    verify_flag: bool | None,
    allow_existing: bool,
) -> None:
    config_path = _engine_config_path(cli_context)
    parser = _load_parser(config_path)
    section = _section_name(name)

    if parser.has_section(section) and not allow_existing:
        raise CommandError(f"Engine '{name}' already exists.")
    if not parser.has_section(section):
        if allow_existing:
            # Upsert mode: create section if it doesn't exist
            parser.add_section(section)
        else:
            # Update mode: section must exist
            raise CommandError(f"Engine '{name}' is not defined.")

    # Sqitch uses "target" field in engine sections, not "uri"
    parser.set(section, "target", uri)
    if registry is not None:
        parser.set(section, "registry", registry)

    if client is not None:
        parser.set(section, "client", client)

    if plan_file is not None:
        parser.set(section, "plan", plan_file)

    if verify_flag is not None:
        parser.set(section, "verify", "true" if verify_flag else "false")

    _write_parser(config_path, parser)


def _engine_config_path(cli_context: CLIContext) -> Path:
    """
    Resolve the config file path for engines.
    Prefers project-level config over user config (Sqitch parity).
    """
    # Always prefer project-level config for engine definitions
    try:
        resolution = resolve_config_file(cli_context.project_root)
    except ArtifactConflictError as exc:  # pragma: no cover - defensive guard
        raise CommandError(str(exc)) from exc

    if resolution.path is not None:
        return resolution.path

    return cli_context.project_root / "sqitch.conf"


def _section_name(name: str) -> str:
    return f'engine "{name}"'


def _load_parser(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    if path.exists():
        parser.read(path, encoding="utf-8")
    return parser


def _write_parser(path: Path, parser: configparser.ConfigParser) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle)


def _load_engines(path: Path) -> Iterable[EngineDefinition]:
    parser = _load_parser(path)
    for section in parser.sections():
        if not section.startswith('engine "') or not section.endswith('"'):
            continue
        name = section[len('engine "') : -1]
        data = parser[section]
        yield EngineDefinition(
            name=name,
            uri=data.get("target", ""),  # Sqitch stores this in "target" field
            registry=data.get("registry"),
            client=data.get("client"),
            verify=data.get("verify"),
            plan=data.get("plan"),
        )


def _format_engine_table(entries: Iterable[EngineDefinition]) -> list[str]:
    rows = [
        (
            entry.name,
            entry.uri,
            entry.registry or "",
            entry.client or "",
            entry.verify or "",
            entry.plan or "",
        )
        for entry in entries
    ]
    header = ("NAME", "URI", "REGISTRY", "CLIENT", "VERIFY", "PLAN")
    widths = [len(column) for column in header]

    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    lines = [
        "  ".join(value.ljust(widths[idx]) for idx, value in enumerate(header)),
    ]
    for row in rows:
        lines.append("  ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)))
    return lines


def _resolve_engine_uri(*, cli_context: CLIContext, candidate: str) -> str:
    """Return the engine URI, resolving target aliases when necessary."""

    if _is_supported_engine_uri(candidate):
        return candidate

    profile = resolve_config(
        root_dir=cli_context.project_root,
        config_root=cli_context.config_root,
        env=cli_context.env,
    )

    section = f'target "{candidate}"'
    data = profile.settings.get(section)
    if data is not None:
        target_uri = data.get("uri")
        if target_uri:
            return target_uri

    raise CommandError(f'Unknown target "{candidate}"')


def _is_supported_engine_uri(uri: str) -> bool:
    lowered = uri.lower()
    return any(
        any(lowered.startswith(prefix) for prefix in prefixes)
        for prefixes in _SUPPORTED_ENGINES.values()
    )


def _validate_engine_uri(uri: str) -> None:
    if _is_supported_engine_uri(uri):
        return
    supported = ", ".join(sorted(_SUPPORTED_ENGINES))
    raise CommandError(f"Unsupported engine URI '{uri}'. Supported engines: {supported}.")


def _emit(ctx: click.Context, message: str) -> None:
    if quiet_mode_enabled(ctx):
        return
    click.echo(message)


@register_command("engine")
def _register_engine(group: click.Group) -> None:
    """Attach the engine command group to the root Click group."""

    group.add_command(engine_group)
