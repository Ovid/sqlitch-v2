"""Registry state domain models and helpers."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from sqlitch.utils.time import coerce_datetime, coerce_optional_datetime, isoformat_utc

__all__ = [
    "RegistryEntry",
    "RegistryState",
    "serialize_registry_entries",
    "sort_registry_entries_by_deployment",
]

_VALID_VERIFY_STATUSES = {"success", "failed", "skipped"}


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise TypeError("change_id must be a UUID or string")


def _normalize_verify_status(value: str | None) -> str:
    if value is None:
        return "success"
    normalized = value.lower()
    if normalized not in _VALID_VERIFY_STATUSES:
        raise ValueError(f"Unknown verify status: {value}")
    return normalized


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    """Represents a single registry record for a deployed change."""

    engine_target: str
    change_id: UUID
    change_name: str
    deployed_at: datetime
    planner: str
    verify_status: str = "success"
    reverted_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.engine_target:
            raise ValueError("engine_target is required")
        if not self.change_name:
            raise ValueError("change_name is required")
        if not self.planner:
            raise ValueError("planner is required")

        normalized_id = _coerce_uuid(self.change_id)
        normalized_deployed_at = coerce_datetime(self.deployed_at, "RegistryEntry deployed_at")
        normalized_reverted_at = coerce_optional_datetime(self.reverted_at, "RegistryEntry reverted_at")
        normalized_status = _normalize_verify_status(self.verify_status)

        object.__setattr__(self, "change_id", normalized_id)
        object.__setattr__(self, "deployed_at", normalized_deployed_at)
        object.__setattr__(self, "reverted_at", normalized_reverted_at)
        object.__setattr__(self, "verify_status", normalized_status)

    def with_verify_status(self, status: str) -> "RegistryEntry":
        normalized = _normalize_verify_status(status)
        return replace(self, verify_status=normalized)

    def with_reverted_at(self, reverted_at: datetime | str | None) -> "RegistryEntry":
        normalized = coerce_optional_datetime(reverted_at, "reverted_at")
        return replace(self, reverted_at=normalized)


class RegistryState:
    """In-memory view of registry entries to drive stateful operations."""

    def __init__(self, entries: Iterable[RegistryEntry] | None = None) -> None:
        self._records: dict[UUID, RegistryEntry] = {}
        self._ordered_ids: list[UUID] = []
        for entry in entries or ():
            self._insert_entry(entry)

    def __iter__(self) -> Iterator[RegistryEntry]:
        for change_id in self._ordered_ids:
            yield self._records[change_id]

    def __len__(self) -> int:
        return len(self._ordered_ids)

    def records(self) -> Sequence[RegistryEntry]:
        return tuple(self)

    def _insert_entry(self, entry: RegistryEntry) -> None:
        change_id: UUID = entry.change_id
        if change_id in self._records:
            raise ValueError(f"Registry entry for {change_id} already recorded")
        self._records[change_id] = entry
        self._ordered_ids.append(change_id)
        self._ordered_ids.sort(key=lambda cid: self._records[cid].deployed_at)

    def record_deploy(self, entry: RegistryEntry) -> None:
        """Persist a new deployment record."""

        self._insert_entry(entry)

    def record_verify(self, change_id: UUID, status: str) -> None:
        """Update verify status for an existing record."""

        if change_id not in self._records:
            raise KeyError(change_id)
        normalized = _normalize_verify_status(status)
        updated = self._records[change_id].with_verify_status(normalized)
        self._records[change_id] = updated

    def record_revert(self, change_id: UUID, reverted_at: datetime | str) -> None:
        """Mark an entry as reverted at the provided timestamp."""

        if change_id not in self._records:
            raise KeyError(change_id)
        updated = self._records[change_id].with_reverted_at(reverted_at)
        self._records[change_id] = updated

    def get_record(self, change_id: UUID) -> RegistryEntry:
        return self._records[change_id]


def deserialize_registry_rows(rows: Iterable[Mapping[str, object]]) -> Sequence[RegistryEntry]:
    """Convert raw registry rows (e.g., DB results) into RegistryEntry instances."""

    entries = [
        RegistryEntry(
            engine_target=row["engine_target"],
            change_id=row["change_id"],
            change_name=row["change_name"],
            deployed_at=row["deployed_at"],
            planner=row["planner"],
            verify_status=row.get("verify_status", "success"),
            reverted_at=row.get("reverted_at"),
        )
        for row in rows
    ]
    return tuple(sorted(entries, key=lambda entry: entry.deployed_at))


def serialize_registry_entries(entries: Iterable[RegistryEntry]) -> list[dict[str, object]]:
    """Serialize RegistryEntry instances into plain dictionaries for persistence."""

    serialized: list[dict[str, object]] = []
    for entry in entries:
        serialized.append(
            {
                "engine_target": entry.engine_target,
                "change_id": str(entry.change_id),
                "change_name": entry.change_name,
                "deployed_at": isoformat_utc(entry.deployed_at),
                "planner": entry.planner,
                "verify_status": entry.verify_status,
                "reverted_at": isoformat_utc(entry.reverted_at) if entry.reverted_at else None,
            }
        )
    return serialized
