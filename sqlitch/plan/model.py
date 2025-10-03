"""Domain models representing plan entities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TypeAlias
from uuid import UUID, uuid4

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
        if not self.name:
            raise ValueError("Change.name is required")
        if not self.planner:
            raise ValueError("Change.planner is required")
        normalized_planned_at = ensure_timezone(self.planned_at, "Change.planned_at")
        object.__setattr__(self, "planned_at", normalized_planned_at)

        if self.change_id is None:
            object.__setattr__(self, "change_id", uuid4())
        elif not isinstance(self.change_id, UUID):
            raise ValueError(f"Change.change_id must be a UUID instance, got: {type(self.change_id).__name__}")

        validated_scripts: dict[str, Path | None] = {}
        deploy_path = self.script_paths.get("deploy") if self.script_paths else None
        revert_path = self.script_paths.get("revert") if self.script_paths else None
        if deploy_path is None:
            raise ValueError("Change.script_paths['deploy'] is required")
        if revert_path is None:
            raise ValueError("Change.script_paths['revert'] is required")
        validated_scripts["deploy"] = _ensure_path(deploy_path)
        validated_scripts["revert"] = _ensure_path(revert_path)
        verify_path = self.script_paths.get("verify") if self.script_paths else None
        if verify_path is not None:
            validated_scripts["verify"] = _ensure_path(verify_path)
        else:
            validated_scripts["verify"] = None
        object.__setattr__(self, "script_paths", validated_scripts)

        normalized_dependencies = tuple(self.dependencies or tuple())
        if len(set(normalized_dependencies)) != len(normalized_dependencies):
            raise ValueError(f"Change.dependencies contains duplicates: {self.dependencies}")
        object.__setattr__(self, "dependencies", normalized_dependencies)

        normalized_tags = tuple(self.tags or tuple())
        if len(set(normalized_tags)) != len(normalized_tags):
            raise ValueError(f"Change.tags contains duplicates: {self.tags}")
        object.__setattr__(self, "tags", normalized_tags)


PlanEntry: TypeAlias = Change | Tag


@dataclass(frozen=True, slots=True)
class Plan:
    """Aggregates ordered plan entries (changes and tags)."""

    project_name: str
    file_path: Path
    entries: Sequence[PlanEntry]
    checksum: str
    default_engine: str

    def __post_init__(self) -> None:
        if not self.project_name:
            raise ValueError("Plan.project_name is required")
        if not self.checksum:
            raise ValueError("Plan.checksum is required")
        if not self.default_engine:
            raise ValueError("Plan.default_engine is required")

        object.__setattr__(self, "file_path", _ensure_path(self.file_path))

        normalized_entries: tuple[PlanEntry, ...] = tuple(self.entries or tuple())
        for entry in normalized_entries:
            if not isinstance(entry, (Change, Tag)):
                raise TypeError(f"Plan.entries must contain Change or Tag instances, got: {type(entry).__name__}")
        object.__setattr__(self, "entries", normalized_entries)

        seen_changes: dict[str, Change] = {}
        for entry in normalized_entries:
            if isinstance(entry, Change):
                if entry.name in seen_changes:
                    raise ValueError(f"Plan contains duplicate change name: {entry.name}")
                for dependency in entry.dependencies:
                    if dependency == entry.name:
                        raise ValueError(f"Change '{entry.name}' cannot depend on itself")
                    if dependency not in seen_changes:
                        raise ValueError(
                            f"Change '{entry.name}' depends on '{dependency}' which is not defined before it"
                        )
                seen_changes[entry.name] = entry
            else:
                if entry.change_ref not in seen_changes:
                    raise ValueError(
                        f"Tag '{entry.name}' references unknown change '{entry.change_ref}'"
                    )

    @property
    def changes(self) -> tuple[Change, ...]:
        return tuple(entry for entry in self.entries if isinstance(entry, Change))

    @property
    def tags(self) -> tuple[Tag, ...]:
        return tuple(entry for entry in self.entries if isinstance(entry, Tag))

    def get_change(self, name: str) -> Change:
        try:
            return next(entry for entry in self.entries if isinstance(entry, Change) and entry.name == name)
        except StopIteration as exc:  # pragma: no cover - defensive API
            raise KeyError(name) from exc

    def has_change(self, name: str) -> bool:
        return any(isinstance(entry, Change) and entry.name == name for entry in self.entries)

    def iter_changes(self) -> Iterable[Change]:
        for entry in self.entries:
            if isinstance(entry, Change):
                yield entry