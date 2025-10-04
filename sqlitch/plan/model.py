"""Domain models representing plan entities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import TypeAlias
from uuid import UUID

from sqlitch.utils.time import ensure_timezone

__all__ = [
    "Change",
    "Tag",
    "Plan",
    "PlanEntry",
]


def _ensure_path(value: Path | str) -> Path:
    if isinstance(value, Path):
        return value
    return Path(value)


@dataclass(frozen=True, slots=True)
class Tag:
    """Represents a tag entry within a plan."""

    name: str
    change_ref: str
    planner: str
    tagged_at: datetime
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Tag.name is required")
        if not self.change_ref:
            raise ValueError("Tag.change_ref is required")
        if not self.planner:
            raise ValueError("Tag.planner is required")
        normalized = ensure_timezone(self.tagged_at, "Tag tagged_at")
        object.__setattr__(self, "tagged_at", normalized)


@dataclass(frozen=True, slots=True)
class Change:
    """Represents a deployable change entry within a plan."""

    name: str
    script_paths: Mapping[str, Path | str | None]
    planner: str
    planned_at: datetime
    notes: str | None = None
    change_id: UUID | None = None
    dependencies: Sequence[str] = field(default_factory=tuple)
    tags: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        normalized = _normalize_change_fields(
            name=self.name,
            planner=self.planner,
            planned_at=self.planned_at,
            script_paths=self.script_paths,
            change_id=self.change_id,
            dependencies=self.dependencies,
            tags=self.tags,
        )

        object.__setattr__(self, "planned_at", normalized.planned_at)
        object.__setattr__(self, "change_id", normalized.change_id)
        object.__setattr__(self, "script_paths", MappingProxyType(normalized.script_paths))
        object.__setattr__(self, "dependencies", normalized.dependencies)
        object.__setattr__(self, "tags", normalized.tags)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        script_paths: Mapping[str, Path | str | None],
        planner: str,
        planned_at: datetime,
        notes: str | None = None,
        change_id: UUID | None = None,
        dependencies: Sequence[str] | None = None,
        tags: Sequence[str] | None = None,
    ) -> "Change":
        """Factory method that applies validation prior to instantiation."""

        normalized = _normalize_change_fields(
            name=name,
            planner=planner,
            planned_at=planned_at,
            script_paths=script_paths,
            change_id=change_id,
            dependencies=dependencies,
            tags=tags,
        )

        return cls(
            name=name,
            script_paths=normalized.script_paths,
            planner=planner,
            planned_at=normalized.planned_at,
            notes=notes,
            change_id=normalized.change_id,
            dependencies=normalized.dependencies,
            tags=normalized.tags,
        )


PlanEntry: TypeAlias = Change | Tag


@dataclass(frozen=True, slots=True)
class Plan:
    """Aggregates ordered plan entries (changes and tags)."""

    project_name: str
    file_path: Path
    entries: Sequence[PlanEntry]
    checksum: str
    default_engine: str
    syntax_version: str = "1.0.0"
    uri: str | None = None
    missing_dependencies: tuple[str, ...] = field(default_factory=tuple, init=False)

    def __post_init__(self) -> None:
        if not self.project_name:
            raise ValueError("Plan.project_name is required")
        if not self.checksum:
            raise ValueError("Plan.checksum is required")
        if not self.default_engine:
            raise ValueError("Plan.default_engine is required")
        if not self.syntax_version:
            raise ValueError("Plan.syntax_version is required")

        object.__setattr__(self, "file_path", _ensure_path(self.file_path))

        normalized_entries: tuple[PlanEntry, ...] = tuple(self.entries or tuple())
        for entry in normalized_entries:
            if not isinstance(entry, (Change, Tag)):
                raise TypeError(
                    f"Plan.entries must contain Change or Tag instances, got: {type(entry).__name__}"
                )
        object.__setattr__(self, "entries", normalized_entries)

        seen_changes: dict[str, Change] = {}
        missing_dependencies: list[str] = []
        for entry in normalized_entries:
            if isinstance(entry, Change):
                if entry.name in seen_changes:
                    raise ValueError(f"Plan contains duplicate change name: {entry.name}")
                for dependency in entry.dependencies:
                    if dependency == entry.name:
                        raise ValueError(f"Change '{entry.name}' cannot depend on itself")
                    if dependency not in seen_changes:
                        missing_dependencies.append(f"{entry.name}->{dependency}")
                seen_changes[entry.name] = entry
            else:
                if entry.change_ref not in seen_changes:
                    raise ValueError(
                        f"Tag '{entry.name}' references unknown change '{entry.change_ref}'"
                    )

        object.__setattr__(self, "missing_dependencies", tuple(missing_dependencies))

    @property
    def changes(self) -> tuple[Change, ...]:
        return tuple(entry for entry in self.entries if isinstance(entry, Change))

    @property
    def tags(self) -> tuple[Tag, ...]:
        return tuple(entry for entry in self.entries if isinstance(entry, Tag))

    def get_change(self, name: str) -> Change:
        try:
            return next(
                entry for entry in self.entries if isinstance(entry, Change) and entry.name == name
            )
        except StopIteration as exc:  # pragma: no cover - defensive API
            raise KeyError(name) from exc

    def has_change(self, name: str) -> bool:
        return any(isinstance(entry, Change) and entry.name == name for entry in self.entries)

    def iter_changes(self) -> Iterable[Change]:
        for entry in self.entries:
            if isinstance(entry, Change):
                yield entry


@dataclass(frozen=True)
class _NormalizedChange:
    planned_at: datetime
    change_id: UUID | None
    script_paths: dict[str, Path | None]
    dependencies: tuple[str, ...]
    tags: tuple[str, ...]


def _normalize_change_fields(
    *,
    name: str,
    planner: str,
    planned_at: datetime,
    script_paths: Mapping[str, Path | str | None] | None,
    change_id: UUID | None,
    dependencies: Sequence[str] | None,
    tags: Sequence[str] | None,
) -> _NormalizedChange:
    if not name:
        raise ValueError("Change.name is required")
    if not planner:
        raise ValueError("Change.planner is required")

    normalized_planned_at = ensure_timezone(planned_at, "Change.planned_at")
    normalized_change_id = _normalize_change_id(change_id)
    normalized_scripts = _normalize_script_paths(script_paths)
    normalized_dependencies = _normalize_unique_sequence(dependencies, "Change.dependencies")
    normalized_tags = _normalize_unique_sequence(tags, "Change.tags")

    return _NormalizedChange(
        planned_at=normalized_planned_at,
        change_id=normalized_change_id,
        script_paths=normalized_scripts,
        dependencies=normalized_dependencies,
        tags=normalized_tags,
    )


def _normalize_change_id(value: UUID | None) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    raise ValueError(f"Change.change_id must be a UUID instance, got: {type(value).__name__}")


def _normalize_script_paths(
    script_paths: Mapping[str, Path | str | None] | None,
) -> dict[str, Path | None]:
    provided = dict(script_paths or {})

    deploy_path = provided.get("deploy")
    revert_path = provided.get("revert")
    if deploy_path is None:
        raise ValueError("Change.script_paths['deploy'] is required")
    if revert_path is None:
        raise ValueError("Change.script_paths['revert'] is required")

    normalized: dict[str, Path | None] = {
        "deploy": _ensure_path(deploy_path),
        "revert": _ensure_path(revert_path),
    }

    verify_path = provided.get("verify")
    normalized["verify"] = _ensure_path(verify_path) if verify_path is not None else None
    return normalized


def _normalize_unique_sequence(values: Sequence[str] | None, label: str) -> tuple[str, ...]:
    if not values:
        return ()
    normalized = tuple(values)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} contains duplicates: {values}")
    return normalized
