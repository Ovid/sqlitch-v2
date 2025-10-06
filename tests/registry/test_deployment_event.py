"""Tests for DeploymentEvent model (T003)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sqlitch.registry.state import DeploymentEvent


def _aware(dt: datetime) -> datetime:
    """Make datetime timezone-aware."""
    return dt.replace(tzinfo=timezone.utc)


class TestDeploymentEventFromRegistryRow:
    """Test T003: DeploymentEvent.from_registry_row() class method."""

    def test_creates_from_valid_deploy_event(self):
        """Should create DeploymentEvent from database row."""
        row = (
            "deploy",  # event type
            "abc123",  # change_id
            "users",  # change
            "flipr",  # project
            "Creates users table",  # note
            "users_base",  # requires (comma-separated)
            "",  # conflicts (comma-separated)
            "v1.0",  # tags (comma-separated)
            "2025-01-15T10:30:00Z",  # committed_at
            "Ada Lovelace",  # committer_name
            "ada@example.com",  # committer_email
            "2025-01-14T18:00:00Z",  # planned_at
            "Ada Lovelace",  # planner_name
            "ada@example.com",  # planner_email
        )
        
        event = DeploymentEvent.from_registry_row(row)
        
        assert event.event == "deploy"
        assert event.change_id == "abc123"
        assert event.change == "users"
        assert event.project == "flipr"
        assert event.note == "Creates users table"
        assert event.requires == "users_base"
        assert event.conflicts == ""
        assert event.tags == "v1.0"
        assert event.committed_at == _aware(datetime(2025, 1, 15, 10, 30))
        assert event.committer_name == "Ada Lovelace"
        assert event.committer_email == "ada@example.com"
        assert event.planned_at == _aware(datetime(2025, 1, 14, 18, 0))
        assert event.planner_name == "Ada Lovelace"
        assert event.planner_email == "ada@example.com"

    def test_handles_revert_event_type(self):
        """Should handle 'revert' event type."""
        row = (
            "revert",  # event type
            "abc123", "users", "flipr", "Reverting users",
            "", "", "",
            "2025-01-15T10:30:00Z", "Ada", "ada@example.com",
            "2025-01-14T18:00:00Z", "Ada", "ada@example.com",
        )
        
        event = DeploymentEvent.from_registry_row(row)
        assert event.event == "revert"

    def test_handles_fail_event_type(self):
        """Should handle 'fail' event type."""
        row = (
            "fail",  # event type
            "abc123", "users", "flipr", "Deploy failed",
            "", "", "",
            "2025-01-15T10:30:00Z", "Ada", "ada@example.com",
            "2025-01-14T18:00:00Z", "Ada", "ada@example.com",
        )
        
        event = DeploymentEvent.from_registry_row(row)
        assert event.event == "fail"

    def test_parses_comma_separated_requires(self):
        """Should store comma-separated requires list."""
        row = (
            "deploy",
            "abc123", "posts", "flipr", "",
            "users,profiles",  # multiple requires
            "", "",
            "2025-01-15T10:30:00Z", "Ada", "ada@example.com",
            "2025-01-14T18:00:00Z", "Ada", "ada@example.com",
        )
        
        event = DeploymentEvent.from_registry_row(row)
        assert event.requires == "users,profiles"

    def test_parses_comma_separated_conflicts(self):
        """Should store comma-separated conflicts list."""
        row = (
            "deploy",
            "abc123", "new_users", "flipr", "",
            "",
            "old_users,legacy_users",  # multiple conflicts
            "",
            "2025-01-15T10:30:00Z", "Ada", "ada@example.com",
            "2025-01-14T18:00:00Z", "Ada", "ada@example.com",
        )
        
        event = DeploymentEvent.from_registry_row(row)
        assert event.conflicts == "old_users,legacy_users"

    def test_parses_comma_separated_tags(self):
        """Should store comma-separated tags list."""
        row = (
            "deploy",
            "abc123", "users", "flipr", "",
            "", "",
            "v1.0,beta,release",  # multiple tags
            "2025-01-15T10:30:00Z", "Ada", "ada@example.com",
            "2025-01-14T18:00:00Z", "Ada", "ada@example.com",
        )
        
        event = DeploymentEvent.from_registry_row(row)
        assert event.tags == "v1.0,beta,release"

    def test_timezone_aware_datetime_handling(self):
        """Should ensure datetime fields are timezone-aware."""
        row = (
            "deploy",
            "abc123", "users", "flipr", "",
            "", "", "",
            "2025-01-15T10:30:00+00:00",
            "Ada", "ada@example.com",
            "2025-01-14T18:00:00+00:00",
            "Ada", "ada@example.com",
        )
        
        event = DeploymentEvent.from_registry_row(row)
        
        # Both datetime fields should be timezone-aware
        assert event.committed_at.tzinfo is not None
        assert event.planned_at.tzinfo is not None
        assert event.committed_at.tzinfo == timezone.utc
        assert event.planned_at.tzinfo == timezone.utc


class TestDeploymentEventValidation:
    """Test T003: DeploymentEvent validation rules."""

    def test_is_frozen_dataclass(self):
        """Should be immutable (frozen dataclass)."""
        row = (
            "deploy",
            "abc123", "users", "flipr", "",
            "", "", "",
            "2025-01-15T10:30:00Z", "Ada", "ada@example.com",
            "2025-01-14T18:00:00Z", "Ada", "ada@example.com",
        )
        event = DeploymentEvent.from_registry_row(row)
        
        # Should not be able to modify
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            event.event = "revert"  # type: ignore

    def test_has_slots(self):
        """Should use __slots__ for memory efficiency."""
        row = (
            "deploy",
            "abc123", "users", "flipr", "",
            "", "", "",
            "2025-01-15T10:30:00Z", "Ada", "ada@example.com",
            "2025-01-14T18:00:00Z", "Ada", "ada@example.com",
        )
        event = DeploymentEvent.from_registry_row(row)
        
        # Should have __slots__, not __dict__
        assert not hasattr(event, '__dict__')
        assert hasattr(event, '__slots__')
