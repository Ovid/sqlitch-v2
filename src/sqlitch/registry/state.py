"""Registry state domain models and helpers."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from sqlitch.utils.time import coerce_datetime, isoformat_utc, parse_iso_datetime

__all__ = [
    "DeployedChange",
    "DeploymentEvent",
    "DeploymentStatus",
    "RegistryEntry",
    "RegistryState",
    "serialize_registry_entries",
    "sort_registry_entries_by_deployment",
    "deserialize_registry_rows",
]


@dataclass(frozen=True)
class DeployedChange:
    """Represents a change currently deployed to the database.

    This model corresponds to rows from the registry `changes` table and is used
    to track which changes have been deployed to a target database.
    """

    change_id: str
    script_hash: str | None
    change: str  # change name
    project: str
    note: str
    committed_at: datetime
    committer_name: str
    committer_email: str
    planned_at: datetime
    planner_name: str
    planner_email: str

    @classmethod
    def from_registry_row(cls, row: tuple[Any, ...]) -> DeployedChange:
        """Create DeployedChange from database row.

        Args:
            row: Database row tuple with 11 elements:
                (change_id, script_hash, change, project, note,
                 committed_at, committer_name, committer_email,
                 planned_at, planner_name, planner_email)

        Returns:
            DeployedChange instance with timezone-aware datetimes.
        """
        return cls(
            change_id=row[0],
            script_hash=row[1],
            change=row[2],
            project=row[3],
            note=row[4],
            committed_at=parse_iso_datetime(
                row[5],
                label="committed_at",
                assume_utc_if_naive=True,
            ),
            committer_name=row[6],
            committer_email=row[7],
            planned_at=parse_iso_datetime(
                row[8],
                label="planned_at",
                assume_utc_if_naive=True,
            ),
            planner_name=row[9],
            planner_email=row[10],
        )


@dataclass(frozen=True)
class DeploymentEvent:
    """Represents a deployment event in the registry.

    This model corresponds to rows from the registry `events` table and is used
    to track all deployment operations (deploy, revert, fail, merge).
    """

    event: str  # 'deploy', 'revert', 'fail', 'merge'
    change_id: str
    change: str  # change name
    project: str
    note: str
    requires: str  # comma-separated list
    conflicts: str  # comma-separated list
    tags: str  # comma-separated list
    committed_at: datetime
    committer_name: str
    committer_email: str
    planned_at: datetime
    planner_name: str
    planner_email: str

    @classmethod
    def from_registry_row(cls, row: tuple[Any, ...]) -> DeploymentEvent:
        """Create DeploymentEvent from database row.

        Args:
            row: Database row tuple with 14 elements:
                (event, change_id, change, project, note,
                 requires, conflicts, tags,
                 committed_at, committer_name, committer_email,
                 planned_at, planner_name, planner_email)

        Returns:
            DeploymentEvent instance with timezone-aware datetimes.
        """
        return cls(
            event=row[0],
            change_id=row[1],
            change=row[2],
            project=row[3],
            note=row[4],
            requires=row[5],
            conflicts=row[6],
            tags=row[7],
            committed_at=parse_iso_datetime(
                row[8],
                label="committed_at",
                assume_utc_if_naive=True,
            ),
            committer_name=row[9],
            committer_email=row[10],
            planned_at=parse_iso_datetime(
                row[11],
                label="planned_at",
                assume_utc_if_naive=True,
            ),
            planner_name=row[12],
            planner_email=row[13],
        )


@dataclass(frozen=True)
class DeploymentStatus:
    """Represents the deployment status of a project target.

    Tracks which changes are deployed, which are pending, and provides
    convenience properties for checking deployment state.
    """

    project: str
    deployed_changes: tuple[str, ...]
    pending_changes: tuple[str, ...]
    deployed_tags: tuple[str, ...]
    last_deployed_change: str | None

    @property
    def is_up_to_date(self) -> bool:
        """True if there are no pending changes to deploy."""
        return len(self.pending_changes) == 0

    @property
    def deployment_count(self) -> int:
        """Number of changes currently deployed."""
        return len(self.deployed_changes)


def _ordering_key(entry: "RegistryEntry") -> tuple[datetime, str, str]:
    return (entry.committed_at, entry.change_name, entry.change_id)


@dataclass(frozen=True)
class RegistryEntry:
    """Represents the latest deployment state recorded in the Sqitch registry."""

    project: str
    change_id: str
    change_name: str
    committed_at: datetime
    committer_name: str
    committer_email: str
    planned_at: datetime
    planner_name: str
    planner_email: str
    script_hash: str | None = None
    note: str = ""

    def __post_init__(self) -> None:
        """Validate required fields and normalize datetime values."""
        if not self.project:
            raise ValueError("RegistryEntry.project is required")
        if not self.change_id:
            raise ValueError("RegistryEntry.change_id is required")
        if not self.change_name:
            raise ValueError("RegistryEntry.change_name is required")
        if not self.committer_name:
            raise ValueError("RegistryEntry.committer_name is required")
        if not self.committer_email:
            raise ValueError("RegistryEntry.committer_email is required")
        if not self.planner_name:
            raise ValueError("RegistryEntry.planner_name is required")
        if not self.planner_email:
            raise ValueError("RegistryEntry.planner_email is required")

        normalized_committed = coerce_datetime(self.committed_at, "RegistryEntry committed_at")
        normalized_planned = coerce_datetime(self.planned_at, "RegistryEntry planned_at")

        object.__setattr__(self, "committed_at", normalized_committed)
        object.__setattr__(self, "planned_at", normalized_planned)


class RegistryState:
    """In-memory view of registry entries keyed by ``change_id``."""

    def __init__(self, entries: Iterable[RegistryEntry] | None = None) -> None:
        """Initialize registry state with optional entries."""
        self._records: dict[str, RegistryEntry] = {}
        self._ordered: list[tuple[tuple[datetime, str, str], str]] = []
        for entry in entries or ():
            self.record_deploy(entry)

    def __iter__(self) -> Iterator[RegistryEntry]:
        """Iterate over registry entries in deployment order."""
        for _, change_id in self._ordered:
            yield self._records[change_id]

    def __len__(self) -> int:
        """Return the number of entries in the registry."""
        return len(self._ordered)

    def records(self) -> Sequence[RegistryEntry]:
        """Return all entries as a tuple."""
        return tuple(self)

    def record_deploy(self, entry: RegistryEntry) -> None:
        """Add a deployment record to the state.

        Raises:
            ValueError: If an entry with the same ``change_id`` already exists.
        """
        change_id = entry.change_id
        if change_id in self._records:
            raise ValueError(f"RegistryState already contains change_id {change_id}")

        self._records[change_id] = entry
        key = _ordering_key(entry)
        index = bisect_right(self._ordered, (key, change_id))
        self._ordered.insert(index, (key, change_id))

    def remove_change(self, change_id: str) -> None:
        """Remove a change from the state (e.g., after a revert)."""
        if change_id not in self._records:
            raise KeyError(f"RegistryState missing change_id '{change_id}'")
        del self._records[change_id]
        self._ordered = [item for item in self._ordered if item[1] != change_id]

    def get_record(self, change_id: str) -> RegistryEntry:
        """Retrieve the registry entry for the given change_id."""
        return self._records[change_id]


def sort_registry_entries_by_deployment(
    entries: Iterable[RegistryEntry],
    *,
    reverse: bool = False,
) -> tuple[RegistryEntry, ...]:
    """Return entries ordered by commit time, change name, and change ID."""
    ordered = sorted(entries, key=_ordering_key, reverse=reverse)
    return tuple(ordered)


def _require_registry_value(row: Mapping[str, object], *candidates: str) -> object:
    for key in candidates:
        if key in row:
            value = row[key]
            if value is None:
                raise ValueError(f"registry row field '{key}' cannot be None")
            return value
    keys = ", ".join(candidates)
    raise ValueError(f"registry row missing required keys: {keys}")


def _coerce_required_text(value: object, *, field: str) -> str:
    if value is None:
        raise ValueError(f"registry row field '{field}' cannot be None")
    text = str(value)
    if text == "":
        raise ValueError(f"registry row field '{field}' cannot be empty")
    return text


def deserialize_registry_rows(rows: Iterable[Mapping[str, object]]) -> Sequence[RegistryEntry]:
    """Convert registry query rows into :class:`RegistryEntry` instances."""
    entries = []
    for row in rows:
        entry = RegistryEntry(
            project=_coerce_required_text(_require_registry_value(row, "project"), field="project"),
            change_id=_coerce_required_text(
                _require_registry_value(row, "change_id"), field="change_id"
            ),
            change_name=_coerce_required_text(
                _require_registry_value(row, "change", "change_name"), field="change"
            ),
            committed_at=coerce_datetime(
                cast("datetime | str", _require_registry_value(row, "committed_at")),
                label="committed_at",
            ),
            committer_name=_coerce_required_text(
                _require_registry_value(row, "committer_name"), field="committer_name"
            ),
            committer_email=_coerce_required_text(
                _require_registry_value(row, "committer_email"), field="committer_email"
            ),
            planned_at=coerce_datetime(
                cast("datetime | str", _require_registry_value(row, "planned_at")),
                label="planned_at",
            ),
            planner_name=_coerce_required_text(
                _require_registry_value(row, "planner_name"), field="planner_name"
            ),
            planner_email=_coerce_required_text(
                _require_registry_value(row, "planner_email"), field="planner_email"
            ),
            script_hash=(str(value) if (value := row.get("script_hash")) is not None else None),
            note=str(row.get("note", "")),
        )
        entries.append(entry)
    return sort_registry_entries_by_deployment(entries)


def serialize_registry_entries(entries: Iterable[RegistryEntry]) -> list[dict[str, object]]:
    """Render entries as dictionaries matching the Sqitch ``changes`` schema."""
    serialized: list[dict[str, object]] = []
    for entry in entries:
        serialized.append(
            {
                "project": entry.project,
                "change_id": entry.change_id,
                "change": entry.change_name,
                "script_hash": entry.script_hash,
                "note": entry.note,
                "committed_at": isoformat_utc(entry.committed_at),
                "committer_name": entry.committer_name,
                "committer_email": entry.committer_email,
                "planned_at": isoformat_utc(entry.planned_at),
                "planner_name": entry.planner_name,
                "planner_email": entry.planner_email,
            }
        )
    return serialized
