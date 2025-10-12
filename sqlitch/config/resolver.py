"""Resolve configuration directories and load profiles."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from sqlitch.engine import canonicalize_engine_name
from sqlitch.engine.sqlite import derive_sqlite_registry_uri

from .loader import ConfigProfile, ConfigScope, load_config

if TYPE_CHECKING:
    from sqlitch.cli.options import CredentialOverrides

_ENV_SQLITCH_CONFIG_ROOT = "SQLITCH_CONFIG_ROOT"
_ENV_SQITCH_CONFIG_ROOT = "SQITCH_CONFIG_ROOT"
_ENV_XDG_CONFIG_HOME = "XDG_CONFIG_HOME"
_ENV_SQLITCH_CONFIG = "SQLITCH_CONFIG"
_ENV_SQITCH_CONFIG = "SQITCH_CONFIG"
_ENV_SQLITCH_USER_CONFIG = "SQLITCH_USER_CONFIG"
_ENV_SQITCH_USER_CONFIG = "SQITCH_USER_CONFIG"
_ENV_SQLITCH_SYSTEM_CONFIG = "SQLITCH_SYSTEM_CONFIG"
_ENV_SQITCH_SYSTEM_CONFIG = "SQITCH_SYSTEM_CONFIG"

_DEFAULT_SYSTEM_PATH = Path("/etc/sqlitch")
_FALLBACK_SYSTEM_PATH = Path("/etc/sqitch")

_ENV_PREFIXES: tuple[str, ...] = ("SQLITCH", "SQITCH")
_ENV_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "username": ("USERNAME", "USER"),
    "password": ("PASSWORD", "PASS", "PWD"),
}
_CONFIG_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "username": ("username", "user"),
    "password": ("password", "pass"),
}


@dataclass(frozen=True, slots=True)
class CredentialResolution:
    """Resolved credential values alongside their originating sources."""

    username: str | None
    password: str | None
    sources: Mapping[str, str]

    def as_dict(self) -> dict[str, str]:
        """Return a dictionary containing defined credential values."""
        data: dict[str, str] = {}
        if self.username is not None:
            data["username"] = self.username
        if self.password is not None:
            data["password"] = self.password
        return data


def determine_config_root(
    *, env: Mapping[str, str] | None = None, home: Path | None = None
) -> Path:
    """Return the directory containing user-level configuration files."""
    env_map = _normalize_env(env)
    override = _coerce_path(env_map.get(_ENV_SQLITCH_CONFIG_ROOT))
    if override is not None:
        return override

    legacy_override = _coerce_path(env_map.get(_ENV_SQITCH_CONFIG_ROOT))
    if legacy_override is not None:
        return legacy_override

    xdg_root = _coerce_path(env_map.get(_ENV_XDG_CONFIG_HOME))
    if xdg_root is not None:
        return xdg_root / "sqlitch"

    # FR-001b: 100% Configuration Compatibility
    # Always use ~/.sqitch/ for Sqitch compatibility
    # Do NOT create ~/.config/sqlitch/ unless explicitly overridden via environment
    home_dir = Path(home) if home is not None else Path.home()
    return home_dir / ".sqitch"


def resolve_config(
    *,
    root_dir: Path | str,
    config_root: Path | str | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    system_path: Path | str | None = None,
    config_filenames: Sequence[str] | None = None,
) -> ConfigProfile:
    """Resolve configuration scope directories and load a profile."""
    env_map = _normalize_env(env)
    project_root = Path(root_dir)

    user_root = _resolve_user_scope_root(
        env_map=env_map,
        config_root=config_root,
        home=home,
    )
    system_root = _determine_system_root(env=env_map, system_path=system_path)

    local_override = _coerce_path(env_map.get(_ENV_SQLITCH_CONFIG))
    if local_override is None:
        local_override = _coerce_path(env_map.get(_ENV_SQITCH_CONFIG))
    local_root = local_override if local_override is not None else project_root

    scope_dirs = {
        ConfigScope.SYSTEM: system_root,
        ConfigScope.USER: user_root,
        ConfigScope.LOCAL: local_root,
    }

    return load_config(
        root_dir=project_root,
        scope_dirs=scope_dirs,
        config_filenames=config_filenames,
    )


def _resolve_user_scope_root(
    *, env_map: Mapping[str, str], config_root: Path | str | None, home: Path | None
) -> Path:
    override = _coerce_path(env_map.get(_ENV_SQLITCH_USER_CONFIG))
    if override is not None:
        return override

    legacy_override = _coerce_path(env_map.get(_ENV_SQITCH_USER_CONFIG))
    if legacy_override is not None:
        return legacy_override

    if config_root is not None:
        return Path(config_root)

    return determine_config_root(env=env_map, home=home)


def resolve_registry_uri(
    *,
    engine: str,
    workspace_uri: str,
    project_root: Path | str,
    registry_override: str | None = None,
) -> str:
    """Return the canonical registry URI for the given engine target."""
    canonical_engine = canonicalize_engine_name(engine)
    project_path = Path(project_root)

    if canonical_engine == "sqlite":
        return derive_sqlite_registry_uri(
            workspace_uri=workspace_uri,
            project_root=project_path,
            registry_override=registry_override,
        )

    if registry_override:
        return registry_override

    return workspace_uri


def resolve_credentials(
    *,
    target: str | None,
    profile: ConfigProfile | None,
    env: Mapping[str, str] | None = None,
    cli_overrides: "CredentialOverrides" | None = None,
) -> CredentialResolution:
    """Resolve credential values using CLI overrides, environment, and config in order.

    Args:
        target: Optional target alias guiding environment/config section lookups.
        profile: Loaded configuration profile supplying persisted defaults.
        env: Optional environment mapping. Defaults to ``os.environ`` when omitted.
        cli_overrides: Credential values supplied directly via CLI flags.

    Returns:
        A :class:`CredentialResolution` recording resolved credential values and sources.
    """
    env_map = _normalize_env(env)
    sources: dict[str, str] = {}

    username = _resolve_credential_field(
        "username",
        cli_overrides,
        env_map,
        profile,
        target,
        sources,
    )
    password = _resolve_credential_field(
        "password",
        cli_overrides,
        env_map,
        profile,
        target,
        sources,
    )

    return CredentialResolution(
        username=username,
        password=password,
        sources=MappingProxyType(sources),
    )


def _determine_system_root(*, env: Mapping[str, str], system_path: Path | str | None) -> Path:
    if system_path is not None:
        return Path(system_path)

    override = _coerce_path(env.get(_ENV_SQLITCH_SYSTEM_CONFIG))
    if override is not None:
        return override

    legacy_override = _coerce_path(env.get(_ENV_SQITCH_SYSTEM_CONFIG))
    if legacy_override is not None:
        return legacy_override

    if _DEFAULT_SYSTEM_PATH.exists():
        return _DEFAULT_SYSTEM_PATH
    if _FALLBACK_SYSTEM_PATH.exists():
        return _FALLBACK_SYSTEM_PATH
    return _DEFAULT_SYSTEM_PATH


def _coerce_path(value: str | os.PathLike[str] | None) -> Path | None:
    if value is None or value == "":
        return None
    return Path(value)


def _normalize_env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is None:
        return MappingProxyType(dict(os.environ))
    return MappingProxyType({key: str(value) for key, value in env.items()})


def _resolve_credential_field(
    field: str,
    cli_overrides: "CredentialOverrides" | None,
    env_map: Mapping[str, str],
    profile: ConfigProfile | None,
    target: str | None,
    sources: dict[str, str],
) -> str | None:
    cli_value = _cli_override_value(cli_overrides, field)
    if cli_value is not None:
        sources[field] = "cli"
        return cli_value

    env_value = _lookup_env_credential(field, env_map, target)
    if env_value is not None:
        sources[field] = "env"
        return env_value

    config_value = _lookup_config_credential(field, profile, target)
    if config_value is not None:
        sources[field] = "config"
        return config_value

    sources[field] = "unset"
    return None


def _cli_override_value(overrides: "CredentialOverrides" | None, field: str) -> str | None:
    if overrides is None:
        return None
    value = getattr(overrides, field, None)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _lookup_env_credential(
    field: str, env_map: Mapping[str, str], target: str | None
) -> str | None:
    for name in _environment_variable_names(field, target):
        value = env_map.get(name)
        if value is not None:
            return value
    return None


def _environment_variable_names(field: str, target: str | None) -> tuple[str, ...]:
    aliases = _ENV_FIELD_ALIASES.get(field, (field.upper(),))
    names: list[str] = []
    target_fragment = _normalize_env_identifier(target) if target else None

    for prefix in _ENV_PREFIXES:
        if target_fragment:
            for alias in aliases:
                names.append(f"{prefix}_{target_fragment}_{alias}")
        for alias in aliases:
            name = f"{prefix}_{alias}"
            if name not in names:
                names.append(name)

    return tuple(names)


def _lookup_config_credential(
    field: str, profile: ConfigProfile | None, target: str | None
) -> str | None:
    if profile is None:
        return None

    sections: list[str] = []
    if target is not None:
        sections.append(f'target "{target}"')
    if profile.active_engine:
        sections.append(f'engine "{profile.active_engine}"')
    sections.append("core")

    aliases = _CONFIG_FIELD_ALIASES.get(field, (field,))

    for section in sections:
        data = profile.settings.get(section)
        if not data:
            continue
        for alias in aliases:
            value = data.get(alias)
            if value is not None:
                return value
    return None


def _normalize_env_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalised = value.upper()
    return "".join(ch if ch.isalnum() else "_" for ch in normalised)
