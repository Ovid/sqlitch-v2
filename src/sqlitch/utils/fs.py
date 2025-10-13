"""Filesystem utilities for SQLitch drop-in detection and cleanup."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


class ArtifactConflictError(RuntimeError):
    """Raised when both SQLitch and Sqitch artifacts are present."""


@dataclass(frozen=True, slots=True)
class ArtifactResolution:
    """Represents the resolved artifact and whether it is a drop-in fallback."""

    path: Path | None
    is_drop_in: bool
    source_name: str | None


def resolve_plan_file(root: Path) -> ArtifactResolution:
    """Resolve the plan file within ``root`` preferring Sqitch naming."""

    return _resolve_artifact(root, "sqitch.plan", "sqlitch.plan")


def resolve_config_file(root: Path) -> ArtifactResolution:
    """Resolve the configuration file within ``root`` preferring Sqitch naming."""

    return _resolve_artifact(root, "sqitch.conf", "sqlitch.conf")


def cleanup_artifacts(root: Path, names: Sequence[str]) -> tuple[Path, ...]:
    """Remove the given artifacts from ``root``.

    Returns the set of paths that were actually removed. Missing paths are ignored.
    """

    removed: list[Path] = []
    for name in names:
        target = root / name
        if remove_path(target):
            removed.append(target)
    return tuple(removed)


def remove_path(target: Path) -> bool:
    """Best-effort removal of a file, directory, or symlink."""

    existed = target.exists() or target.is_symlink()
    if not existed:
        return False

    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
        return True

    target.unlink(missing_ok=True)
    return existed


def _resolve_artifact(root: Path, preferred: str, fallback: str) -> ArtifactResolution:
    preferred_path = root / preferred
    fallback_path = root / fallback

    has_preferred = preferred_path.exists()
    has_fallback = fallback_path.exists()

    if has_preferred and has_fallback:
        raise ArtifactConflictError(
            f"Found conflicting artifacts in {root}: {preferred} and {fallback}"
        )

    if has_preferred:
        return ArtifactResolution(preferred_path, False, preferred)

    if has_fallback:
        return ArtifactResolution(fallback_path, True, fallback)

    return ArtifactResolution(None, False, None)


__all__ = [
    "ArtifactConflictError",
    "ArtifactResolution",
    "cleanup_artifacts",
    "remove_path",
    "resolve_config_file",
    "resolve_plan_file",
]
