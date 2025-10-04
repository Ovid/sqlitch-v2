"""Resolve configuration directories and load profiles."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType

from .loader import ConfigProfile, ConfigScope, load_config

_ENV_SQLITCH_CONFIG_ROOT = "SQLITCH_CONFIG_ROOT"
_ENV_SQITCH_CONFIG_ROOT = "SQITCH_CONFIG_ROOT"
_ENV_XDG_CONFIG_HOME = "XDG_CONFIG_HOME"
_ENV_SQLITCH_SYSTEM_CONFIG = "SQLITCH_SYSTEM_CONFIG"
_ENV_SQITCH_SYSTEM_CONFIG = "SQITCH_SYSTEM_CONFIG"

_DEFAULT_SYSTEM_PATH = Path("/etc/sqlitch")
_FALLBACK_SYSTEM_PATH = Path("/etc/sqitch")


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

    home_dir = Path(home) if home is not None else Path.home()
    config_default = home_dir / ".config" / "sqlitch"
    sqitch_default = home_dir / ".sqitch"

    config_exists = config_default.exists()
    sqitch_exists = sqitch_default.exists()

    if config_exists or not sqitch_exists:
        return config_default

    return sqitch_default


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

    user_root = (
        Path(config_root)
        if config_root is not None
        else determine_config_root(env=env_map, home=home)
    )
    system_root = _determine_system_root(env=env_map, system_path=system_path)

    scope_dirs = {
        ConfigScope.SYSTEM: system_root,
        ConfigScope.USER: user_root,
        ConfigScope.LOCAL: project_root,
    }

    return load_config(
        root_dir=project_root,
        scope_dirs=scope_dirs,
        config_filenames=config_filenames,
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
    if value in (None, ""):
        return None
    return Path(value)


def _normalize_env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is None:
        return MappingProxyType(dict(os.environ))
    return MappingProxyType({key: str(value) for key, value in env.items()})
