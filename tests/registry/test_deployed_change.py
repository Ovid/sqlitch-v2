"""Tests for DeployedChange model (T001)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sqlitch.registry.state import DeployedChange


def _aware(dt: datetime) -> datetime:
    """Make datetime timezone-aware."""
    return dt.replace(tzinfo=timezone.utc)


class TestDeployedChangeFromRegistryRow:
    """Test T001: DeployedChange.from_registry_row() class method."""

    def test_creates_from_valid_row(self):
        """Should create DeployedChange from database row."""
        row = (
            "abc123",  # change_id
            "deadbeef",  # script_hash
            "users",  # change
            "flipr",  # project
            "Creates users table",  # note
            "2025-01-15T10:30:00Z",  # committed_at
            "Ada Lovelace",  # committer_name
            "ada@example.com",  # committer_email
            "2025-01-14T18:00:00Z",  # planned_at
            "Ada Lovelace",  # planner_name
            "ada@example.com",  # planner_email
        )

        deployed = DeployedChange.from_registry_row(row)

        assert deployed.change_id == "abc123"
        assert deployed.script_hash == "deadbeef"
        assert deployed.change == "users"
        assert deployed.project == "flipr"
        assert deployed.note == "Creates users table"
        assert deployed.committed_at == _aware(datetime(2025, 1, 15, 10, 30))
        assert deployed.committer_name == "Ada Lovelace"
        assert deployed.committer_email == "ada@example.com"
        assert deployed.planned_at == _aware(datetime(2025, 1, 14, 18, 0))
        assert deployed.planner_name == "Ada Lovelace"
        assert deployed.planner_email == "ada@example.com"

    def test_handles_null_script_hash(self):
        """Should handle NULL script_hash from database."""
        row = (
            "abc123",
            None,  # script_hash can be NULL
            "users",
            "flipr",
            "Creates users table",
            "2025-01-15T10:30:00Z",
            "Ada Lovelace",
            "ada@example.com",
            "2025-01-14T18:00:00Z",
            "Ada Lovelace",
            "ada@example.com",
        )

        deployed = DeployedChange.from_registry_row(row)

        assert deployed.script_hash is None
        assert deployed.change_id == "abc123"

    def test_timezone_aware_datetime_handling(self):
        """Should ensure datetime fields are timezone-aware."""
        row = (
            "abc123",
            "deadbeef",
            "users",
            "flipr",
            "",
            "2025-01-15T10:30:00+00:00",
            "Ada",
            "ada@example.com",
            "2025-01-14T18:00:00+00:00",
            "Ada",
            "ada@example.com",
        )

        deployed = DeployedChange.from_registry_row(row)

        # Both datetime fields should be timezone-aware
        assert deployed.committed_at.tzinfo is not None
        assert deployed.planned_at.tzinfo is not None
        assert deployed.committed_at.tzinfo == timezone.utc
        assert deployed.planned_at.tzinfo == timezone.utc


class TestDeployedChangeValidation:
    """Test T001: DeployedChange validation rules."""

    def test_is_frozen_dataclass(self):
        """Should be immutable (frozen dataclass)."""
        row = (
            "abc123",
            "deadbeef",
            "users",
            "flipr",
            "",
            "2025-01-15T10:30:00Z",
            "Ada",
            "ada@example.com",
            "2025-01-14T18:00:00Z",
            "Ada",
            "ada@example.com",
        )
        deployed = DeployedChange.from_registry_row(row)

        # Should not be able to modify
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            deployed.change_id = "new_id"  # type: ignore

    def test_has_slots(self):
        """Should use __slots__ for memory efficiency."""
        row = (
            "abc123",
            "deadbeef",
            "users",
            "flipr",
            "",
            "2025-01-15T10:30:00Z",
            "Ada",
            "ada@example.com",
            "2025-01-14T18:00:00Z",
            "Ada",
            "ada@example.com",
        )
        deployed = DeployedChange.from_registry_row(row)

        # Should have __slots__, not __dict__
        assert not hasattr(deployed, "__dict__")
        assert hasattr(deployed, "__slots__")
