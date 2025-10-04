"""Registry state domain models and helpers."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlitch.utils.time import coerce_datetime, isoformat_utc

__all__ = [
    "RegistryEntry",
    "RegistryState",
    "serialize_registry_entries",
    "sort_registry_entries_by_deployment",
    "deserialize_registry_rows",
]


def _ordering_key(entry: "RegistryEntry") -> tuple[datetime, str, str]:
    return (entry.committed_at, entry.change_name, entry.change_id)


@dataclass(frozen=True, slots=True)
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

        normalized_committed = coerce_datetime(
            self.committed_at, "RegistryEntry committed_at"
        )
        normalized_planned = coerce_datetime(self.planned_at, "RegistryEntry planned_at")

        object.__setattr__(self, "committed_at", normalized_committed)
        object.__setattr__(self, "planned_at", normalized_planned)


class RegistryState:
    """In-memory view of registry entries keyed by ``change_id``."""

    def __init__(self, entries: Iterable[RegistryEntry] | None = None) -> None:
        self._records: dict[str, RegistryEntry] = {}
        self._ordered: list[tuple[tuple[datetime, str, str], str]] = []
        for entry in entries or ():
            self.record_deploy(entry)

    def __iter__(self) -> Iterator[RegistryEntry]:
        for _, change_id in self._ordered:
            yield self._records[change_id]

    def __len__(self) -> int:
        return len(self._ordered)

    def records(self) -> Sequence[RegistryEntry]:
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
            raise KeyError(change_id)
        del self._records[change_id]
        self._ordered = [item for item in self._ordered if item[1] != change_id]

    def get_record(self, change_id: str) -> RegistryEntry:
        return self._records[change_id]


def sort_registry_entries_by_deployment(
    entries: Iterable[RegistryEntry],
    *,
    reverse: bool = False,
) -> tuple[RegistryEntry, ...]:
    """Return entries ordered by commit time, change name, and change ID."""

    ordered = sorted(entries, key=_ordering_key, reverse=reverse)
    return tuple(ordered)


def _resolve_value(row: Mapping[str, object], *candidates: str) -> object:
    for key in candidates:
        if key in row:
            return row[key]
    raise KeyError(f"Row is missing required keys: {', '.join(candidates)}")


def deserialize_registry_rows(rows: Iterable[Mapping[str, object]]) -> Sequence[RegistryEntry]:
    """Convert registry query rows into :class:`RegistryEntry` instances."""

    entries = []
    for row in rows:
        entry = RegistryEntry(
            project=str(_resolve_value(row, "project")),
            change_id=str(_resolve_value(row, "change_id")),
            change_name=str(_resolve_value(row, "change", "change_name")),
            committed_at=_resolve_value(row, "committed_at"),
            committer_name=str(_resolve_value(row, "committer_name")),
            committer_email=str(_resolve_value(row, "committer_email")),
            planned_at=_resolve_value(row, "planned_at"),
            planner_name=str(_resolve_value(row, "planner_name")),
            planner_email=str(_resolve_value(row, "planner_email")),
            script_hash=(
                str(value)
                if (value := row.get("script_hash")) is not None
                else None
            ),
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
