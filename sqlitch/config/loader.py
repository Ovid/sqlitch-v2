"""Configuration loader supporting layered scopes."""

from __future__ import annotations

import configparser
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

__all__ = [
    "ConfigScope",
    "ConfigConflictError",
    "ConfigProfile",
    "load_config",
    "load_configuration",
]


class ConfigScope(str, Enum):
    """Configuration scope precedence, ordered from lowest to highest."""

    SYSTEM = "system"
    USER = "user"
    LOCAL = "local"


@dataclass(frozen=True)
class ConfigProfile:
    """Materialized configuration data and metadata."""

    root_dir: Path
    files: tuple[Path, ...]
    settings: Mapping[str, Mapping[str, str]]
    active_engine: str | None


class ConfigConflictError(RuntimeError):
    """Raised when conflicting config files are discovered within the same scope."""


_CONFIG_FILENAMES: Sequence[str] = ("sqitch.conf", "sqlitch.conf")


def load_config(
    *,
    root_dir: Path | str,
    scope_dirs: Mapping[ConfigScope, Path | str],
    config_filenames: Sequence[str] | None = None,
) -> ConfigProfile:
    """Load configuration across scopes and merge with precedence.

    Parameters
    ----------
    root_dir:
        The primary project directory associated with the configuration profile.
    scope_dirs:
        Mapping of :class:`ConfigScope` to directories that may contain config files.
        Only scopes present in the mapping are considered.
    config_filenames:
        Optional tuple ordering of config filenames to search within each scope.
    Defaults to ``("sqitch.conf", "sqlitch.conf")`` while retaining support for
    legacy SQLitch-specific filenames.
    """

    search_names: Sequence[str] = config_filenames or _CONFIG_FILENAMES
    root_path = Path(root_dir)
    resolved_scopes = {scope: Path(path) for scope, path in scope_dirs.items()}

    ordered_files: list[Path] = []
    merged_sections: "dict[str, dict[str, str]]" = {}

    for scope in ConfigScope:
        directory = resolved_scopes.get(scope)
        if directory is None:
            continue
        candidates: list[Path]
        if directory.is_file():
            candidates = [directory]
        else:
            candidates = [directory / name for name in search_names if (directory / name).exists()]

        if len(candidates) > 1:
            conflict_list = ", ".join(name.name for name in candidates)
            raise ConfigConflictError(
                f"Multiple configuration files found for {scope.value} scope: {conflict_list}"
            )
        if not candidates:
            continue

        config_path = candidates[0]
        ordered_files.append(config_path)

        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str  # preserve case
        parser.read(config_path, encoding="utf-8")

        if parser.defaults():
            defaults = merged_sections.setdefault("DEFAULT", {})
            for option, value in parser.defaults().items():
                normalized_option = option.lower()
                _assert_no_plan_pragma(normalized_option)
                defaults[option] = value

        for section in parser.sections():
            normalized_section = _normalize_section_name(section)
            target = merged_sections.setdefault(normalized_section, {})
            for option, value in parser.items(section, raw=True):
                normalized_option = option.lower()
                _assert_no_plan_pragma(normalized_option)
                if normalized_section == "env":
                    target[option] = value
                else:
                    target[normalized_option] = value

    active_engine = None
    core_section = merged_sections.get("core")
    if core_section is not None:
        active_engine = core_section.get("engine")

    frozen_settings = {section: dict(values) for section, values in merged_sections.items()}

    return ConfigProfile(
        root_dir=root_path,
        files=tuple(ordered_files),
        settings=frozen_settings,
        active_engine=active_engine,
    )


load_configuration = load_config


def _normalize_section_name(section: str) -> str:
    if "\"" in section:
        head, quote, tail = section.partition("\"")
        return f"{head.lower()}{quote}{tail}"
    return section.lower()


def _assert_no_plan_pragma(option: str) -> None:
    if option.startswith("%"):
        raise ValueError(f"Plan pragmas are not permitted in configuration files (invalid option '{option}')")
