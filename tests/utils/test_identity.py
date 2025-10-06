"""Tests for identity helpers."""

from __future__ import annotations

import pytest
import hashlib
from datetime import datetime, timezone

from sqlitch.utils.identity import UserIdentity, generate_change_id


class TestUserIdentity:
    """Test UserIdentity helper functions."""

    def test_creates_from_user_config(self) -> None:
        """Should create from user.name and user.email config."""
        identity = UserIdentity(name="Alice Smith", email="alice@example.com")
        assert identity.name == "Alice Smith"
        assert identity.email == "alice@example.com"

    def test_is_frozen_dataclass(self) -> None:
        """UserIdentity should be immutable."""
        identity = UserIdentity(name="Bob", email="bob@example.com")
        with pytest.raises(AttributeError):
            identity.name = "Changed"  # type: ignore[misc]

    def test_has_slots(self) -> None:
        """UserIdentity should use __slots__ for memory efficiency."""
        identity = UserIdentity(name="Carol", email="carol@example.com")
        assert not hasattr(identity, "__dict__")


class TestGenerateChangeId:
    """Test generate_change_id function."""

    def test_generates_sha1_hash(self) -> None:
        """Should return SHA1 hash hex digest."""
        change_id = generate_change_id(
            project="flipr",
            change="users",
            timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        # SHA1 produces 40-character hex string
        assert len(change_id) == 40
        assert all(c in "0123456789abcdef" for c in change_id)

    def test_deterministic_same_inputs(self) -> None:
        """Same inputs should produce same output."""
        timestamp = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        id1 = generate_change_id("flipr", "users", timestamp)
        id2 = generate_change_id("flipr", "users", timestamp)
        
        assert id1 == id2

    def test_different_inputs_different_outputs(self) -> None:
        """Different inputs should produce different outputs."""
        timestamp = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        id1 = generate_change_id("flipr", "users", timestamp)
        id2 = generate_change_id("flipr", "schema", timestamp)
        
        assert id1 != id2

    def test_matches_sqitch_format(self) -> None:
        """Should match Sqitch's SHA1(project + change + timestamp) format."""
        project = "flipr"
        change = "users"
        timestamp = datetime(2025, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        
        # Sqitch uses ISO 8601 format: project:change:YYYY-MM-DDTHH:MM:SSZ
        expected_input = f"{project}:{change}:{timestamp.isoformat()}"
        expected_hash = hashlib.sha1(expected_input.encode("utf-8")).hexdigest()
        
        result = generate_change_id(project, change, timestamp)
        assert result == expected_hash
