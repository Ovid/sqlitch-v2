"""Shared helpers for plan file resolution within CLI commands."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from sqlitch.utils.fs import ArtifactConflictError, resolve_plan_file

from . import CommandError

__all__ = ["resolve_plan_path"]


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
