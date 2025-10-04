"""Shared helpers for plan file resolution within CLI commands."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from sqlitch.config import resolver as config_resolver
from sqlitch.utils.fs import ArtifactConflictError, resolve_plan_file

from . import CommandError

__all__ = ["resolve_plan_path", "resolve_default_engine"]


def resolve_plan_path(
    *,
    project_root: Path,
    override: Path | None,
    env: Mapping[str, str],
    missing_plan_message: str,
) -> Path:
    """Resolve the plan file path honouring overrides and environment hints."""

    if override is not None:
        if not override.exists():
            raise CommandError(f"Plan file {override} is missing")
        return override

    env_value = env.get("SQITCH_PLAN_FILE") or env.get("SQLITCH_PLAN_FILE")
    if env_value:
        env_path = Path(env_value)
        resolved = env_path if env_path.is_absolute() else project_root / env_path
        if not resolved.exists():
            raise CommandError(f"Plan file {resolved} is missing")
        return resolved

    try:
        resolution = resolve_plan_file(project_root)
    except ArtifactConflictError as exc:
        raise CommandError(str(exc)) from exc

    if resolution.path is None:
        raise CommandError(missing_plan_message)
    return resolution.path


def resolve_default_engine(
    *,
    project_root: Path,
    config_root: Path,
    env: Mapping[str, str],
    engine_override: str | None,
) -> str:
    """Determine the effective default engine for plan operations."""

    if engine_override:
        return engine_override

    profile = config_resolver.resolve_config(
        root_dir=project_root,
        config_root=config_root,
        env=env,
    )

    if profile.active_engine:
        return profile.active_engine

    raise CommandError(
        "No default engine configured. Specify an engine via --engine or configure [core].engine."
    )
