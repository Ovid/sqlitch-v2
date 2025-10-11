from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sqlitch.registry.state import RegistryEntry, RegistryState, deserialize_registry_rows


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
