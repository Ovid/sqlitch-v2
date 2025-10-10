"""Implementation of the ``sqlitch target`` command."""

from __future__ import annotations

import configparser
from pathlib import Path

import click

from sqlitch.engine.sqlite import (
    SQLITE_SCHEME_PREFIX,
    derive_sqlite_registry_uri,
    resolve_sqlite_filesystem_path,
)
from sqlitch.utils.fs import ArtifactConflictError, resolve_config_file

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import quiet_mode_enabled, require_cli_context

__all__ = ["target_command"]


@click.group("target", invoke_without_command=True)
@global_sqitch_options
@global_output_options
@click.pass_context
def target_command(
    ctx: click.Context,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Manage target aliases that map to deployment URIs."""

    # If no subcommand was invoked, run the 'list' command by default
    if ctx.invoked_subcommand is None:
        ctx.invoke(target_list)


@target_command.command("add")
@click.argument("name")
@click.argument("uri")
@click.option("--engine", help="Engine for the target.")
@click.option("--registry", help="Registry URI for the target.")
@click.pass_context
def target_add(
    ctx: click.Context,
    name: str,
    uri: str,
    engine: str | None,
    registry: str | None,
) -> None:
    """Add a new target."""

    cli_context = require_cli_context(ctx)
    config_path = _resolve_config_path(
        cli_context.project_root,
        cli_context.config_root,
        cli_context.config_root_overridden,
    )

    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    if config_path.exists():
        config.read(config_path, encoding="utf-8")

    section = f'target "{name}"'
    if config.has_section(section):
        raise CommandError(f'Target "{name}" already exists')

    if not config.has_section(section):
        config.add_section(section)

    normalised_uri, inferred_registry = _normalise_target_entry(
        project_root=cli_context.project_root,
        uri=uri,
        registry_override=registry,
    )

    config.set(section, "uri", normalised_uri)
    if engine:
        config.set(section, "engine", engine)
    registry_value = inferred_registry if inferred_registry is not None else registry
    if registry_value:
        config.set(section, "registry", registry_value)
    elif config.has_option(section, "registry"):
        config.remove_option(section, "registry")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        config.write(f)

    if not quiet_mode_enabled(ctx):
        click.echo(f"Added target {name}")


@target_command.command("alter")
@click.argument("name")
@click.argument("uri")
@click.option("--engine", help="Engine for the target.")
@click.option("--registry", help="Registry URI for the target.")
@click.pass_context
def target_alter(
    ctx: click.Context,
    name: str,
    uri: str,
    engine: str | None,
    registry: str | None,
) -> None:
    """Update an existing target."""

    cli_context = require_cli_context(ctx)
    config_path = _resolve_config_path(
        cli_context.project_root,
        cli_context.config_root,
        cli_context.config_root_overridden,
    )

    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    if config_path.exists():
        config.read(config_path, encoding="utf-8")

    section = f'target "{name}"'
    if not config.has_section(section):
        raise CommandError(f'Unknown target "{name}"')

    normalised_uri, inferred_registry = _normalise_target_entry(
        project_root=cli_context.project_root,
        uri=uri,
        registry_override=registry,
    )

    config.set(section, "uri", normalised_uri)
    if engine:
        config.set(section, "engine", engine)
    registry_value = inferred_registry if inferred_registry is not None else registry
    if registry_value:
        config.set(section, "registry", registry_value)

    with config_path.open("w", encoding="utf-8") as f:
        config.write(f)

    if not quiet_mode_enabled(ctx):
        click.echo(f"Updated target {name}")


@target_command.command("show")
@click.argument("name")
@click.pass_context
def target_show(ctx: click.Context, name: str) -> None:
    """Show details of a target."""

    cli_context = require_cli_context(ctx)
    config_path = _resolve_config_path(
        cli_context.project_root,
        cli_context.config_root,
        cli_context.config_root_overridden,
    )

    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    if config_path.exists():
        config.read(config_path, encoding="utf-8")

    section = f'target "{name}"'
    if not config.has_section(section):
        raise CommandError(f'Unknown target "{name}"')

    uri = config.get(section, "uri", fallback="")
    engine = config.get(section, "engine", fallback="")
    registry = config.get(section, "registry", fallback="")

    click.echo(f"Name: {name}")
    click.echo(f"URI: {uri}")
    if engine:
        click.echo(f"Engine: {engine}")
    if registry:
        click.echo(f"Registry: {registry}")


@target_command.command("remove")
@click.argument("name")
@click.pass_context
def target_remove(ctx: click.Context, name: str) -> None:
    """Remove a target."""

    cli_context = require_cli_context(ctx)
    config_path = _resolve_config_path(
        cli_context.project_root,
        cli_context.config_root,
        cli_context.config_root_overridden,
    )

    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    if config_path.exists():
        config.read(config_path, encoding="utf-8")

    section = f'target "{name}"'
    if not config.has_section(section):
        raise CommandError(f'Unknown target "{name}"')

    config.remove_section(section)

    with config_path.open("w", encoding="utf-8") as f:
        config.write(f)

    if not quiet_mode_enabled(ctx):
        click.echo(f"Removed target {name}")


@target_command.command("list")
@click.pass_context
def target_list(ctx: click.Context) -> None:
    """List all targets."""

    cli_context = require_cli_context(ctx)
    config_path = _resolve_config_path(
        cli_context.project_root,
        cli_context.config_root,
        cli_context.config_root_overridden,
    )

    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    if config_path.exists():
        config.read(config_path, encoding="utf-8")

    targets = []
    for section in config.sections():
        if section.startswith('target "') and section.endswith('"'):
            name = section[8:-1]  # Remove 'target "' and '"'
            uri = config.get(section, "uri", fallback="")
            engine = config.get(section, "engine", fallback="")
            registry = config.get(section, "registry", fallback="")
            targets.append((name, uri, engine, registry))

    if targets:
        if quiet_mode_enabled(ctx):
            return
        click.echo("Name\tURI\tEngine\tRegistry")
        for name, uri, engine, registry in targets:
            click.echo(f"{name}\t{uri}\t{engine}\t{registry}")
    else:
        if not quiet_mode_enabled(ctx):
            click.echo("No targets configured.")


def _normalise_target_entry(
    *,
    project_root: Path,
    uri: str,
    registry_override: str | None,
) -> tuple[str, str | None]:
    if not uri.startswith(SQLITE_SCHEME_PREFIX):
        return uri, registry_override

    payload = uri[len(SQLITE_SCHEME_PREFIX) :]
    if payload in {"", ":memory:"}:
        normalised_uri = f"{SQLITE_SCHEME_PREFIX}:memory:"
        registry_uri = derive_sqlite_registry_uri(
            workspace_uri=normalised_uri,
            project_root=project_root,
            registry_override=registry_override,
        )
        return normalised_uri, registry_uri

    filesystem_path = resolve_sqlite_filesystem_path(uri)
    if str(filesystem_path) == ":memory:":
        normalised_uri = f"{SQLITE_SCHEME_PREFIX}:memory:"
        registry_uri = derive_sqlite_registry_uri(
            workspace_uri=normalised_uri,
            project_root=project_root,
            registry_override=registry_override,
        )
        return normalised_uri, registry_uri

    original_path = filesystem_path
    if not filesystem_path.is_absolute():
        resolved_path = (project_root / filesystem_path).resolve()
    else:
        resolved_path = filesystem_path.resolve()

    is_file_uri = payload.startswith("file:")
    is_simple_relative = (
        not is_file_uri and not original_path.is_absolute() and len(original_path.parts) == 1
    )

    if is_file_uri:
        normalised_uri = f"{SQLITE_SCHEME_PREFIX}file:{resolved_path.as_posix()}"
    elif is_simple_relative:
        normalised_uri = uri
    else:
        normalised_uri = f"{SQLITE_SCHEME_PREFIX}{resolved_path.as_posix()}"

    canonical_workspace_uri = (
        f"{SQLITE_SCHEME_PREFIX}file:{resolved_path.as_posix()}"
        if is_file_uri
        else f"{SQLITE_SCHEME_PREFIX}{resolved_path.as_posix()}"
    )

    registry_uri = derive_sqlite_registry_uri(
        workspace_uri=canonical_workspace_uri,
        project_root=project_root,
        registry_override=registry_override,
    )
    return normalised_uri, registry_uri


def _resolve_config_path(
    project_root: Path,
    config_root: Path | None,
    config_override: bool,
) -> Path:
    """Resolve the config file path for targets."""

    search_roots: list[Path] = [project_root]
    if config_override and config_root is not None and config_root != project_root:
        search_roots.insert(0, config_root)

    for root in search_roots:
        try:
            resolution = resolve_config_file(root)
        except ArtifactConflictError as exc:  # pragma: no cover - defensive guard
            raise CommandError(str(exc)) from exc

        if resolution.path is not None:
            return resolution.path

    fallback_root = config_root if (config_override and config_root is not None) else project_root
    return fallback_root / "sqitch.conf"


@register_command("target")
def _register_target(group: click.Group) -> None:
    """Register the target command with the root CLI group."""

    group.add_command(target_command)
