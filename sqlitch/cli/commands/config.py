"""Implementation of the ``sqlitch config`` command."""

from __future__ import annotations

import configparser
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Callable

import click

from sqlitch.config.loader import ConfigScope
from sqlitch.config import resolver as config_resolver
from sqlitch.utils.fs import ArtifactConflictError, resolve_config_file

from . import CommandError, register_command
from ._context import (
    environment_from,
    project_root_from,
    quiet_mode_enabled,
    require_cli_context,
)

__all__ = ["config_command"]

_CONFIG_FILENAME = "sqitch.conf"


@click.command("config")
@click.option("--global", "global_scope", is_flag=True, help="Operate on the user (global) scope.")
@click.option("--user", "user_scope", is_flag=True, help="Operate on the user scope.")
@click.option("--local", "local_scope", is_flag=True, help="Operate on the project-local scope.")
@click.option(
    "--registry",
    "registry_scope",
    is_flag=True,
    help="Operate on the registry scope (unsupported).",
)
@click.option(
    "--unset", "unset_flag", is_flag=True, help="Remove the specified configuration value."
)
@click.option("--list", "list_flag", is_flag=True, help="List all configuration values.")
@click.option("--json", "json_flag", is_flag=True, help="Render --list output as JSON.")
@click.argument("name", required=False)
@click.argument("value", required=False)
@click.pass_context
def config_command(
    ctx: click.Context,
    *,
    global_scope: bool,
    user_scope: bool,
    local_scope: bool,
    registry_scope: bool,
    unset_flag: bool,
    list_flag: bool,
    json_flag: bool,
    name: str | None,
    value: str | None,
) -> None:
    """Inspect and modify SQLitch configuration values."""

    cli_context = require_cli_context(ctx)
    project_root = project_root_from(ctx)
    env = environment_from(ctx)
    scope, explicit_scope = _resolve_scope(global_scope, user_scope, local_scope, registry_scope)

    if json_flag and not list_flag:
        raise CommandError("--json may only be used together with --list.")

    if list_flag:
        if name or value or unset_flag:
            raise CommandError("--list cannot be combined with positional arguments or --unset.")
        _handle_list(
            project_root=project_root,
            config_root=cli_context.config_root,
            env=env,
            json_output=json_flag,
            quiet=quiet_mode_enabled(ctx),
        )
        return

    if unset_flag:
        if not name:
            raise CommandError("A configuration name must be provided when using --unset.")
        if value is not None:
            raise CommandError("--unset cannot be combined with a value argument.")
        _unset_option(
            name=name,
            scope=scope,
            project_root=project_root,
            config_root=cli_context.config_root,
            env=env,
            quiet=quiet_mode_enabled(ctx),
        )
        return

    if value is not None:
        if not name:
            raise CommandError("A configuration name must be provided when setting a value.")
        _set_option(
            name=name,
            value=value,
            scope=scope,
            project_root=project_root,
            config_root=cli_context.config_root,
            env=env,
            quiet=quiet_mode_enabled(ctx),
        )
        return

    if not name:
        raise CommandError("A configuration name must be provided.")

    resolved_value = _get_option(
        name=name,
        project_root=project_root,
        config_root=cli_context.config_root,
        env=env,
        scope=scope,
        explicit_scope=explicit_scope,
    )
    click.echo(resolved_value)


def _resolve_scope(
    global_scope: bool,
    user_scope: bool,
    local_scope: bool,
    registry_scope: bool,
) -> tuple[ConfigScope, bool]:
    if registry_scope:
        raise CommandError("Registry scope operations are not supported yet.")

    chosen: list[ConfigScope] = []
    if global_scope or user_scope:
        chosen.append(ConfigScope.USER)
    if local_scope:
        chosen.append(ConfigScope.LOCAL)

    if len(chosen) > 1:
        raise CommandError("Only one scope option may be specified.")

    if chosen:
        return chosen[0], True
    return ConfigScope.LOCAL, False


def _handle_list(
    *,
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
    json_output: bool,
    quiet: bool,
) -> None:
    profile = config_resolver.resolve_config(
        root_dir=project_root,
        config_root=config_root,
        env=env,
    )
    flattened = _flatten_settings(profile.settings)

    if json_output:
        payload = json.dumps(flattened, indent=2, sort_keys=True)
        click.echo(payload)
        return

    emitter = _build_emitter(quiet)
    for key in sorted(flattened):
        emitter(f"{key}={flattened[key]}")


def _set_option(
    *,
    name: str,
    value: str,
    scope: ConfigScope,
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
    quiet: bool,
) -> None:
    section, option = _split_key(name)
    config_path = _config_file_path(scope, project_root, config_root, env)

    parser = _load_parser(config_path)
    if section == "DEFAULT":
        parser["DEFAULT"][option] = value
    else:
        if not parser.has_section(section):
            parser.add_section(section)
        parser.set(section, option, value)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        parser.write(handle)

    emitter = _build_emitter(quiet)
    emitter(f"Set {section}.{option} in {scope.value} scope")


def _unset_option(
    *,
    name: str,
    scope: ConfigScope,
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
    quiet: bool,
) -> None:
    section, option = _split_key(name)
    config_path = _config_file_path(scope, project_root, config_root, env)

    if not config_path.exists():
        raise CommandError(f"Configuration option {name} is not set in {scope.value} scope.")

    parser = _load_parser(config_path)
    removed = False

    if section == "DEFAULT":
        defaults = parser.defaults()
        removed = option in defaults
        defaults.pop(option, None)
    else:
        if parser.has_section(section) and parser.remove_option(section, option):
            removed = True
        if parser.has_section(section) and not parser.items(section):
            parser.remove_section(section)

    if not removed:
        raise CommandError(f"Configuration option {name} is not set in {scope.value} scope.")

    with config_path.open("w", encoding="utf-8") as handle:
        parser.write(handle)

    emitter = _build_emitter(quiet)
    emitter(f"Unset {section}.{option} in {scope.value} scope")


def _get_option(
    *,
    name: str,
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
    scope: ConfigScope,
    explicit_scope: bool,
) -> str:
    section, option = _split_key(name)
    profile = config_resolver.resolve_config(
        root_dir=project_root,
        config_root=config_root,
        env=env,
    )
    settings = profile.settings

    if explicit_scope:
        config_path = _config_file_path(scope, project_root, config_root, env)
        if not config_path.exists():
            raise CommandError(f"No such option: {name}")
        parser = _load_parser(config_path)
        if section == "DEFAULT":
            defaults = parser.defaults()
            if option in defaults:
                return defaults[option]
        elif parser.has_section(section) and parser.has_option(section, option):
            return parser.get(section, option)
    else:
        if section == "DEFAULT":
            defaults = settings.get("DEFAULT", {})
            if option in defaults:
                return defaults[option]
        else:
            section_values = settings.get(section)
            if section_values and option in section_values:
                return section_values[option]

    raise CommandError(f"No such option: {name}")


def _config_file_path(
    scope: ConfigScope,
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
) -> Path:
    if scope == ConfigScope.LOCAL:
        directory = project_root
    elif scope == ConfigScope.USER:
        directory = config_root
    else:
        raise CommandError("System scope modifications are not supported yet.")

    try:
        resolution = resolve_config_file(directory)
    except ArtifactConflictError as exc:  # pragma: no cover - defensive guard
        raise CommandError(str(exc)) from exc

    if resolution.path is not None:
        return resolution.path

    return directory / _CONFIG_FILENAME


def _split_key(name: str) -> tuple[str, str]:
    if "." not in name:
        raise CommandError("Configuration names must use section.option format.")
    section, option = name.split(".", 1)
    if not section or not option:
        raise CommandError("Configuration names must include both section and option components.")
    return section, option


def _load_parser(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    if path.exists():
        parser.read(path, encoding="utf-8")
    return parser


def _flatten_settings(settings: Mapping[str, Mapping[str, str]]) -> dict[str, str]:
    flattened: dict[str, str] = {}
    for section, values in settings.items():
        for option, value in values.items():
            if section == "DEFAULT":
                flattened[option] = value
            else:
                flattened[f"{section}.{option}"] = value
    return flattened


def _build_emitter(quiet: bool) -> Callable[[str], None]:
    def _emit(message: str) -> None:
        if not quiet:
            click.echo(message)

    return _emit


@register_command("config")
def _register_config(group: click.Group) -> None:
    """Attach the config command to the root Click group."""

    group.add_command(config_command)
