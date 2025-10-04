from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from sqlitch.registry.state import (
    RegistryEntry,
    RegistryState,
    deserialize_registry_rows,
    sort_registry_entries_by_deployment,
    serialize_registry_entries,
)


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def test_registry_entry_requires_timezone_aware_datetimes() -> None:
    change_id = uuid4()
    deployed_at = datetime.now(timezone.utc)

    entry = RegistryEntry(
        engine_target="db:pg",
        change_id=change_id,
        change_name="alpha",
        deployed_at=deployed_at,
        planner="alice",
    )

    assert entry.deployed_at == deployed_at.astimezone(timezone.utc)
    assert entry.reverted_at is None

    with pytest.raises(ValueError, match="deployed_at must be timezone-aware"):
        RegistryEntry(
            engine_target="db:pg",
            change_id=uuid4(),
            change_name="beta",
            deployed_at=datetime.now(),
            planner="bob",
        )


def test_deserialize_registry_rows_coerces_types_and_sorts() -> None:
    first_id = uuid4()
    second_id = uuid4()
    rows = [
        {
            "engine_target": "db:pg",
            "change_id": str(second_id),
            "change_name": "beta",
            "deployed_at": _aware(datetime(2025, 1, 2, 12, 0)),
            "planner": "bob",
            "verify_status": "failed",
            "reverted_at": None,
        },
        {
            "engine_target": "db:pg",
            "change_id": first_id,
            "change_name": "alpha",
            "deployed_at": "2025-01-01T08:00:00+00:00",
            "planner": "alice",
            "verify_status": "success",
            "reverted_at": None,
        },
    ]

    entries = deserialize_registry_rows(rows)

    assert isinstance(entries[0].change_id, UUID)
    assert entries[0].change_id == first_id
    assert entries[1].change_id == second_id
    assert entries[0].change_name == "alpha"
    assert entries[0].verify_status == "success"
    assert entries[1].verify_status == "failed"


def test_serialize_registry_entries_produces_iso_strings() -> None:
    entry = RegistryEntry(
        engine_target="db:pg",
        change_id=uuid4(),
        change_name="alpha",
        deployed_at=_aware(datetime(2025, 1, 1, 9, 30)),
        planner="alice",
        verify_status="skipped",
        reverted_at=_aware(datetime(2025, 1, 2, 11, 0)),
    )

    serialized = serialize_registry_entries([entry])

    assert serialized[0]["deployed_at"].endswith("+00:00")
    assert serialized[0]["verify_status"] == "skipped"
    assert serialized[0]["reverted_at"].endswith("+00:00")


def test_registry_state_mutations_round_trip() -> None:
    base_entry = RegistryEntry(
        engine_target="db:sqlite",
        change_id=uuid4(),
        change_name="alpha",
        deployed_at=_aware(datetime(2025, 3, 4, 10, 0)),
        planner="alice",
    )
    state = RegistryState([base_entry])

    new_entry = RegistryEntry(
        engine_target="db:sqlite",
        change_id=uuid4(),
        change_name="beta",
        deployed_at=_aware(datetime(2025, 3, 4, 11, 0)),
        planner="bob",
    )
    state.record_deploy(new_entry)
    assert state.get_record(new_entry.change_id) == new_entry

    state.record_verify(new_entry.change_id, "failed")
    updated = state.get_record(new_entry.change_id)
    assert updated.verify_status == "failed"

    revert_time = _aware(datetime(2025, 3, 4, 11, 30))
    state.record_revert(new_entry.change_id, revert_time)
    reverted = state.get_record(new_entry.change_id)
    assert reverted.reverted_at == revert_time

    with pytest.raises(KeyError):
        state.record_verify(uuid4(), "success")

    with pytest.raises(ValueError, match="RegistryState already contains change_id"):
        state.record_deploy(base_entry)


def test_registry_state_requires_timezone_on_revert() -> None:
    entry = RegistryEntry(
        engine_target="db:pg",
        change_id=uuid4(),
        change_name="alpha",
        deployed_at=_aware(datetime(2025, 1, 1, 0, 0)),
        planner="alice",
    )
    state = RegistryState([entry])

    with pytest.raises(ValueError, match="reverted_at must be timezone-aware"):
        state.record_revert(entry.change_id, datetime.now())


def test_registry_state_forbids_unknown_verify_status() -> None:
    state = RegistryState()
    entry = RegistryEntry(
        engine_target="db:sqlite",
        change_id=uuid4(),
        change_name="omega",
        deployed_at=_aware(datetime(2025, 5, 5, 5, 5)),
        planner="olivia",
    )
    state.record_deploy(entry)

    with pytest.raises(ValueError, match=r"RegistryEntry\.verify_status"):
        state.record_verify(entry.change_id, "flaky")


def test_sort_registry_entries_by_deployment_orders_deterministically() -> None:
    timestamps = [
        _aware(datetime(2025, 6, 1, 9, 0)),
        _aware(datetime(2025, 6, 1, 10, 0)),
        _aware(datetime(2025, 6, 1, 9, 0)),
    ]
    entries = [
        RegistryEntry(
            engine_target="db:sqlite",
            change_id=uuid4(),
            change_name="bravo",
            deployed_at=timestamps[1],
            planner="brynn",
        ),
        RegistryEntry(
            engine_target="db:sqlite",
            change_id=uuid4(),
            change_name="alpha",
            deployed_at=timestamps[0],
            planner="alex",
        ),
        RegistryEntry(
            engine_target="db:sqlite",
            change_id=uuid4(),
            change_name="charlie",
            deployed_at=timestamps[2],
            planner="casey",
        ),
    ]

    ordered = sort_registry_entries_by_deployment(entries)
    assert [entry.change_name for entry in ordered] == ["alpha", "charlie", "bravo"]

    reversed_order = sort_registry_entries_by_deployment(entries, reverse=True)
    assert [entry.change_name for entry in reversed_order] == ["bravo", "charlie", "alpha"]
