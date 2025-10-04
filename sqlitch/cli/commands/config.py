"""Implementation of the ``sqlitch config`` command."""

from __future__ import annotations

import configparser
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
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
    "--bool",
    "bool_flag",
    is_flag=True,
    help="Interpret values as booleans when getting or setting options.",
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
    bool_flag: bool,
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
    request = _parse_config_request(
        name=name,
        value=value,
        list_flag=list_flag,
        unset_flag=unset_flag,
        bool_flag=bool_flag,
        json_flag=json_flag,
    )

    quiet = quiet_mode_enabled(ctx)

    if request.operation is ConfigOperation.LIST:
        _handle_list(
            project_root=project_root,
            config_root=cli_context.config_root,
            env=env,
            json_output=request.json_output,
            quiet=quiet,
        )
        return

    if request.operation is ConfigOperation.UNSET:
        _unset_option(
            name=_require_name(request.name),
            scope=scope,
            project_root=project_root,
            config_root=cli_context.config_root,
            env=env,
            quiet=quiet,
        )
        return

    if request.operation is ConfigOperation.SET:
        value_to_store = (
            _normalize_bool_value(_require_value(request.value))
            if request.bool_mode
            else _require_value(request.value)
        )
        _set_option(
            name=_require_name(request.name),
            value=value_to_store,
            scope=scope,
            project_root=project_root,
            config_root=cli_context.config_root,
            env=env,
            quiet=quiet,
        )
        return

    resolved_value = _get_option(
        name=_require_name(request.name),
        project_root=project_root,
        config_root=cli_context.config_root,
        env=env,
        scope=scope,
        explicit_scope=explicit_scope,
    )
    output_value = _normalize_bool_value(resolved_value) if request.bool_mode else resolved_value
    click.echo(output_value)


class ConfigOperation(Enum):
    LIST = "list"
    SET = "set"
    UNSET = "unset"
    GET = "get"


@dataclass(frozen=True)
class ConfigRequest:
    operation: ConfigOperation
    name: str | None = None
    value: str | None = None
    bool_mode: bool = False
    json_output: bool = False


def _parse_config_request(
    *,
    name: str | None,
    value: str | None,
    list_flag: bool,
    unset_flag: bool,
    bool_flag: bool,
    json_flag: bool,
) -> ConfigRequest:
    if json_flag and not list_flag:
        raise CommandError("--json may only be used together with --list.")

    if list_flag:
        if bool_flag:
            raise CommandError("--bool cannot be combined with --list.")
        if name or value or unset_flag:
            raise CommandError("--list cannot be combined with positional arguments or --unset.")
        return ConfigRequest(operation=ConfigOperation.LIST, json_output=json_flag)

    if unset_flag:
        if not name:
            raise CommandError("A configuration name must be provided when using --unset.")
        if value is not None:
            raise CommandError("--unset cannot be combined with a value argument.")
        return ConfigRequest(operation=ConfigOperation.UNSET, name=name)

    if value is not None:
        if not name:
            raise CommandError("A configuration name must be provided when setting a value.")
        return ConfigRequest(
            operation=ConfigOperation.SET,
            name=name,
            value=value,
            bool_mode=bool_flag,
        )

    if not name:
        raise CommandError("A configuration name must be provided.")

    return ConfigRequest(operation=ConfigOperation.GET, name=name, bool_mode=bool_flag)


def _require_name(name: str | None) -> str:
    if name is None:
        raise CommandError("Configuration name is required.")
    return name


def _require_value(value: str | None) -> str:
    if value is None:
        raise CommandError("Configuration value is required.")
    return value


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

    existing_lines = _read_config_lines(config_path)
    updated_lines = _set_config_value(existing_lines, section, option, value)
    _write_config_lines(config_path, updated_lines)

    if quiet:
        return

    click.echo(f"Set {name} in {scope.value} scope")


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

    existing_lines = _read_config_lines(config_path)
    updated_lines, removed = _remove_config_value(existing_lines, section, option)
    if not removed:
        raise CommandError(f"Configuration option {name} is not set in {scope.value} scope.")

    _write_config_lines(config_path, updated_lines)

    if quiet:
        return

    click.echo(f"Unset {name} in {scope.value} scope")


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


def _read_config_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    return content.splitlines()


def _write_config_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines)
    if content and not content.endswith("\n"):
        content += "\n"
    elif not content:
        content = ""
    path.write_text(content, encoding="utf-8")


def _set_config_value(
    lines: list[str], section: str, option: str, value: str
) -> list[str]:
    new_lines = list(lines)
    start, end, header_index = _find_section_bounds(new_lines, section)

    if start is None:
        if section != "DEFAULT":
            new_lines.append(f"[{section}]")
            indent = "\t"
            new_lines.append(f"{indent}{option} = {value}")
        else:
            new_lines.append(f"{option} = {value}")
        return new_lines

    indent_default = "" if section == "DEFAULT" else "\t"
    indent = _detect_indent(new_lines[start:end], indent_default)

    for idx in range(start, end):
        stripped = new_lines[idx].strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        key, sep, _ = stripped.partition("=")
        if sep and key.strip() == option:
            new_lines[idx] = f"{indent}{option} = {value}"
            return new_lines

    insertion_index = start
    for idx in range(start, end):
        stripped = new_lines[idx].strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            insertion_index = idx
            break
        insertion_index = idx + 1
    else:
        insertion_index = end
    new_lines.insert(insertion_index, f"{indent}{option} = {value}")
    return new_lines


def _remove_config_value(
    lines: list[str], section: str, option: str
) -> tuple[list[str], bool]:
    new_lines = list(lines)
    start, end, header_index = _find_section_bounds(new_lines, section)
    if start is None:
        return new_lines, False

    target_index = None
    for idx in range(start, end):
        stripped = new_lines[idx].strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        key, sep, _ = stripped.partition("=")
        if sep and key.strip() == option:
            target_index = idx
            break

    if target_index is None:
        return new_lines, False

    del new_lines[target_index]

    if section != "DEFAULT" and header_index is not None:
        section_has_entries = _section_has_entries(new_lines, header_index)
        if not section_has_entries:
            end_index = _find_next_section(new_lines, header_index + 1)
            del new_lines[header_index:end_index]

    return new_lines, True


def _find_section_bounds(
    lines: list[str], section: str
) -> tuple[int | None, int | None, int | None]:
    if section == "DEFAULT":
        start = 0
        if lines and lines[0].strip().lower() == "[default]":
            start = 1
        end = _find_next_section(lines, start)
        return start, end, None

    header = f"[{section}]"
    for idx, line in enumerate(lines):
        if line.strip() == header:
            end = _find_next_section(lines, idx + 1)
            return idx + 1, end, idx
    return None, None, None


def _find_next_section(lines: list[str], start: int) -> int:
    for idx in range(start, len(lines)):
        stripped = lines[idx].strip()
        if stripped.startswith("[") and stripped.endswith("]") and not stripped.startswith("#"):
            return idx
    return len(lines)


def _detect_indent(lines: list[str], default: str) -> str:
    for line in lines:
        stripped = line.lstrip("\t ")
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        return line[: len(line) - len(stripped)]
    return default


def _section_has_entries(lines: list[str], header_index: int) -> bool:
    start = header_index + 1
    end = _find_next_section(lines, start)
    for idx in range(start, end):
        stripped = lines[idx].strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith(";"):
            return True
    return False


def _normalize_bool_value(value: str) -> str:
    truthy = {"1", "true", "yes", "on"}
    falsy = {"0", "false", "no", "off"}
    normalized = value.strip().lower()
    if normalized in truthy:
        return "true"
    if normalized in falsy:
        return "false"
    raise CommandError(f"Invalid boolean value: {value}")


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
