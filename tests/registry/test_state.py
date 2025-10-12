from __future__ import annotations

from datetime import UTC, datetime, timezone

import pytest

from sqlitch.registry.state import (
    RegistryEntry,
    RegistryState,
    deserialize_registry_rows,
    serialize_registry_entries,
    sort_registry_entries_by_deployment,
)


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def _entry(**overrides: object) -> RegistryEntry:
    baseline = dict(
        project="widgets",
        change_id="abc123",
        change_name="alpha",
        committed_at=_aware(datetime(2025, 1, 1, 9, 30)),
        committer_name="Ada",
        committer_email="ada@example.com",
        planned_at=_aware(datetime(2024, 12, 31, 18, 0)),
        planner_name="Ada",
        planner_email="ada@example.com",
        script_hash="deadbeef",
        note="Initial deploy",
    )
    baseline.update(overrides)
    return RegistryEntry(**baseline)  # type: ignore[arg-type]


def test_registry_entry_requires_timezone_aware_datetimes() -> None:
    entry = _entry()
    assert entry.committed_at.tzinfo is timezone.utc
    assert entry.planned_at.tzinfo is timezone.utc

    with pytest.raises(ValueError, match="committed_at must be timezone-aware"):
        _entry(committed_at=datetime(2025, 1, 1, 9, 30))

    with pytest.raises(ValueError, match="planned_at must be timezone-aware"):
        _entry(planned_at=datetime(2024, 12, 31, 18, 0))


def test_deserialize_registry_rows_coerces_types_and_sorts() -> None:
    rows = [
        {
            "project": "widgets",
            "change_id": "beta",
            "change": "beta",
            "committed_at": _aware(datetime(2025, 1, 2, 12, 0)),
            "committer_name": "Bea",
            "committer_email": "bea@example.com",
            "planned_at": "2025-01-02T08:00:00+00:00",
            "planner_name": "Bea",
            "planner_email": "bea@example.com",
            "note": "Add beta",
        },
        {
            "project": "widgets",
            "change_id": "alpha",
            "change": "alpha",
            "committed_at": "2025-01-01T08:00:00+00:00",
            "committer_name": "Ada",
            "committer_email": "ada@example.com",
            "planned_at": _aware(datetime(2024, 12, 31, 18, 0)),
            "planner_name": "Ada",
            "planner_email": "ada@example.com",
        },
    ]

    entries = deserialize_registry_rows(rows)

    assert entries[0].change_id == "alpha"
    assert entries[0].note == ""
    assert entries[1].note == "Add beta"
    assert entries[0].committed_at < entries[1].committed_at


def test_serialize_registry_entries_produces_iso_strings() -> None:
    entry = _entry(
        committed_at=_aware(datetime(2025, 1, 1, 10, 15)),
        planned_at=_aware(datetime(2024, 12, 30, 16, 45)),
    )

    serialized = serialize_registry_entries([entry])
    payload = serialized[0]

    assert payload["change"] == "alpha"
    assert payload["committed_at"].endswith("+00:00")
    assert payload["planned_at"].endswith("+00:00")


def test_registry_state_mutations_round_trip() -> None:
    base_entry = _entry(change_id="alpha", change_name="alpha")
    state = RegistryState([base_entry])

    new_entry = _entry(
        change_id="beta",
        change_name="beta",
        committed_at=_aware(datetime(2025, 1, 2, 10, 0)),
        planned_at=_aware(datetime(2024, 12, 31, 20, 0)),
        committer_name="Bea",
        committer_email="bea@example.com",
        planner_name="Bea",
        planner_email="bea@example.com",
    )

    state.record_deploy(new_entry)
    assert state.get_record("beta") == new_entry

    with pytest.raises(ValueError, match="already contains"):
        state.record_deploy(new_entry)

    state.remove_change("beta")
    with pytest.raises(KeyError):
        state.get_record("beta")

    with pytest.raises(KeyError):
        state.remove_change("missing")


def test_sort_registry_entries_by_deployment_orders_deterministically() -> None:
    timestamps = [
        _aware(datetime(2025, 6, 1, 9, 0)),
        _aware(datetime(2025, 6, 1, 10, 0)),
        _aware(datetime(2025, 6, 1, 9, 0)),
    ]
    entries = [
        _entry(
            change_id="bravo",
            change_name="bravo",
            committed_at=timestamps[1],
            planned_at=_aware(datetime(2025, 5, 31, 12, 0)),
            committer_name="Bran",
            committer_email="bran@example.com",
            planner_name="Bran",
            planner_email="bran@example.com",
        ),
        _entry(
            change_id="alpha",
            change_name="alpha",
            committed_at=timestamps[0],
            planned_at=_aware(datetime(2025, 5, 30, 12, 0)),
            committer_name="Ann",
            committer_email="ann@example.com",
            planner_name="Ann",
            planner_email="ann@example.com",
        ),
        _entry(
            change_id="charlie",
            change_name="charlie",
            committed_at=timestamps[2],
            planned_at=_aware(datetime(2025, 5, 31, 15, 0)),
            committer_name="Cam",
            committer_email="cam@example.com",
            planner_name="Cam",
            planner_email="cam@example.com",
        ),
    ]

    ordered = sort_registry_entries_by_deployment(entries)
    assert [entry.change_name for entry in ordered] == ["alpha", "charlie", "bravo"]

    reversed_order = sort_registry_entries_by_deployment(entries, reverse=True)
    assert [entry.change_name for entry in reversed_order] == ["bravo", "charlie", "alpha"]


def test_registry_entry_requires_project():
    """Verify RegistryEntry raises ValueError when project is empty."""
    with pytest.raises(ValueError, match="project is required"):
        RegistryEntry(
            project="",
            change_id="abc123",
            change_name="test_change",
            committed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            committer_name="Test User",
            committer_email="test@example.com",
            planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            planner_name="Test User",
            planner_email="test@example.com",
        )


def test_registry_entry_requires_change_id():
    """Verify RegistryEntry raises ValueError when change_id is empty."""
    with pytest.raises(ValueError, match="change_id is required"):
        RegistryEntry(
            project="test",
            change_id="",
            change_name="test_change",
            committed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            committer_name="Test User",
            committer_email="test@example.com",
            planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            planner_name="Test User",
            planner_email="test@example.com",
        )


def test_registry_entry_requires_change_name():
    """Verify RegistryEntry raises ValueError when change_name is empty."""
    with pytest.raises(ValueError, match="change_name is required"):
        RegistryEntry(
            project="test",
            change_id="abc123",
            change_name="",
            committed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            committer_name="Test User",
            committer_email="test@example.com",
            planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            planner_name="Test User",
            planner_email="test@example.com",
        )


def test_registry_entry_requires_committer_name():
    """Verify RegistryEntry raises ValueError when committer_name is empty."""
    with pytest.raises(ValueError, match="committer_name is required"):
        RegistryEntry(
            project="test",
            change_id="abc123",
            change_name="test_change",
            committed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            committer_name="",
            committer_email="test@example.com",
            planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            planner_name="Test User",
            planner_email="test@example.com",
        )


def test_registry_entry_requires_committer_email():
    """Verify RegistryEntry raises ValueError when committer_email is empty."""
    with pytest.raises(ValueError, match="committer_email is required"):
        RegistryEntry(
            project="test",
            change_id="abc123",
            change_name="test_change",
            committed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            committer_name="Test User",
            committer_email="",
            planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            planner_name="Test User",
            planner_email="test@example.com",
        )


def test_registry_entry_requires_planner_name():
    """Verify RegistryEntry raises ValueError when planner_name is empty."""
    with pytest.raises(ValueError, match="planner_name is required"):
        RegistryEntry(
            project="test",
            change_id="abc123",
            change_name="test_change",
            committed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            committer_name="Test User",
            committer_email="test@example.com",
            planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            planner_name="",
            planner_email="test@example.com",
        )


def test_registry_entry_requires_planner_email():
    """Verify RegistryEntry raises ValueError when planner_email is empty."""
    with pytest.raises(ValueError, match="planner_email is required"):
        RegistryEntry(
            project="test",
            change_id="abc123",
            change_name="test_change",
            committed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            committer_name="Test User",
            committer_email="test@example.com",
            planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            planner_name="Test User",
            planner_email="",
        )


def test_registry_state_length():
    """Verify __len__ returns the correct number of entries."""
    entry1 = RegistryEntry(
        project="test",
        change_id="abc123",
        change_name="change1",
        committed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        committer_name="Test User",
        committer_email="test@example.com",
        planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        planner_name="Test User",
        planner_email="test@example.com",
    )

    entry2 = RegistryEntry(
        project="test",
        change_id="def456",
        change_name="change2",
        committed_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
        committer_name="Test User",
        committer_email="test@example.com",
        planned_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
        planner_name="Test User",
        planner_email="test@example.com",
    )

    state = RegistryState(entries=(entry1, entry2))

    assert len(state) == 2


def test_registry_state_iteration():
    """Verify __iter__ returns entries in deployment order."""
    entry1 = RegistryEntry(
        project="test",
        change_id="abc123",
        change_name="change1",
        committed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        committer_name="Test User",
        committer_email="test@example.com",
        planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        planner_name="Test User",
        planner_email="test@example.com",
    )

    entry2 = RegistryEntry(
        project="test",
        change_id="def456",
        change_name="change2",
        committed_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
        committer_name="Test User",
        committer_email="test@example.com",
        planned_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
        planner_name="Test User",
        planner_email="test@example.com",
    )

    state = RegistryState(entries=(entry1, entry2))

    entries = list(state)
    assert len(entries) == 2
    assert entries[0].change_id == "abc123"
    assert entries[1].change_id == "def456"


def test_registry_state_records_method():
    """Verify records() returns all entries as a tuple."""
    entry1 = RegistryEntry(
        project="test",
        change_id="abc123",
        change_name="change1",
        committed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        committer_name="Test User",
        committer_email="test@example.com",
        planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        planner_name="Test User",
        planner_email="test@example.com",
    )

    state = RegistryState(entries=(entry1,))

    records = state.records()
    assert isinstance(records, tuple)
    assert len(records) == 1
    assert records[0].change_id == "abc123"


# =============================================================================
# Lockdown Tests (merged from test_state_lockdown.py)
# =============================================================================

def _aware(timestamp: datetime) -> datetime:
    return timestamp.replace(tzinfo=timezone.utc)

def _entry_kwargs(**overrides: object) -> dict[str, object]:
    attrs: dict[str, object] = {
        "project": "widgets",
        "change_id": "alpha",
        "change_name": "alpha",
        "committed_at": _aware(datetime(2025, 3, 1, 12, 0)),
        "committer_name": "Ada",
        "committer_email": "ada@example.com",
        "planned_at": _aware(datetime(2025, 2, 28, 18, 0)),
        "planner_name": "Ada",
        "planner_email": "ada@example.com",
    }
    attrs.update(overrides)
    return attrs

def test_deserialize_registry_rows_rejects_missing_required_fields() -> None:
    rows = [
        {
            "project": "widgets",
            "change_id": "alpha",
            # the upstream Sqitch view exposes both `change` and `change_name`
            # fields; omitting both should surface a descriptive failure.
            "committed_at": _aware(datetime(2025, 3, 1, 12, 0)),
            "committer_name": "Ada",
            "committer_email": "ada@example.com",
            "planned_at": _aware(datetime(2025, 2, 28, 18, 0)),
            "planner_name": "Ada",
            "planner_email": "ada@example.com",
        }
    ]

    with pytest.raises(ValueError) as excinfo:
        deserialize_registry_rows(rows)

    message = str(excinfo.value)
    assert "change" in message
    assert "registry row" in message

def test_deserialize_registry_rows_rejects_none_values() -> None:
    rows = [
        {
            "project": None,
            "change_id": "alpha",
            "change": "alpha",
            "committed_at": _aware(datetime(2025, 3, 1, 12, 0)),
            "committer_name": "Ada",
            "committer_email": "ada@example.com",
            "planned_at": _aware(datetime(2025, 2, 28, 18, 0)),
            "planner_name": "Ada",
            "planner_email": "ada@example.com",
        }
    ]

    with pytest.raises(ValueError) as excinfo:
        deserialize_registry_rows(rows)

    assert "project" in str(excinfo.value)

def test_registry_state_remove_change_surfaces_missing_key() -> None:
    entry = RegistryEntry(
        **_entry_kwargs(
            change_id="alpha",
            change_name="alpha",
            committed_at=_aware(datetime(2025, 3, 1, 12, 0)),
            planned_at=_aware(datetime(2025, 2, 28, 18, 0)),
        )
    )
    state = RegistryState([entry])

    with pytest.raises(KeyError) as excinfo:
        state.remove_change("missing")

    assert "missing" in str(excinfo.value)
    assert "RegistryState" in str(excinfo.value)
