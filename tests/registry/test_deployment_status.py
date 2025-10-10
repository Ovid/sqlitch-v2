"""Tests for DeploymentStatus model."""

from __future__ import annotations

import pytest

from sqlitch.registry.state import DeployedChange, DeploymentStatus
from datetime import datetime, timezone


class TestDeploymentStatusProperties:
    """Test computed properties of DeploymentStatus."""

    def test_is_up_to_date_when_no_pending(self) -> None:
        """Status is up-to-date when no pending changes."""
        status = DeploymentStatus(
            project="flipr",
            deployed_changes=("users", "schema"),
            pending_changes=(),
            deployed_tags=("v1.0",),
            last_deployed_change="schema",
        )
        assert status.is_up_to_date is True

    def test_not_up_to_date_when_pending(self) -> None:
        """Status is not up-to-date when pending changes exist."""
        status = DeploymentStatus(
            project="flipr",
            deployed_changes=("users",),
            pending_changes=("schema", "indexes"),
            deployed_tags=(),
            last_deployed_change="users",
        )
        assert status.is_up_to_date is False

    def test_is_up_to_date_with_empty_deployed(self) -> None:
        """Status is up-to-date when both deployed and pending are empty."""
        status = DeploymentStatus(
            project="flipr",
            deployed_changes=(),
            pending_changes=(),
            deployed_tags=(),
            last_deployed_change=None,
        )
        assert status.is_up_to_date is True

    def test_deployment_count_returns_deployed_length(self) -> None:
        """deployment_count returns length of deployed_changes."""
        status = DeploymentStatus(
            project="flipr",
            deployed_changes=("users", "schema", "indexes"),
            pending_changes=(),
            deployed_tags=("v1.0",),
            last_deployed_change="indexes",
        )
        assert status.deployment_count == 3

    def test_deployment_count_zero_when_empty(self) -> None:
        """deployment_count is zero when no deployments."""
        status = DeploymentStatus(
            project="flipr",
            deployed_changes=(),
            pending_changes=("users", "schema"),
            deployed_tags=(),
            last_deployed_change=None,
        )
        assert status.deployment_count == 0


class TestDeploymentStatusValidation:
    """Test dataclass validation."""

    def test_is_frozen_dataclass(self) -> None:
        """DeploymentStatus should be immutable."""
        status = DeploymentStatus(
            project="flipr",
            deployed_changes=("users",),
            pending_changes=(),
            deployed_tags=(),
            last_deployed_change="users",
        )
        with pytest.raises(AttributeError):
            status.project = "other"  # type: ignore[misc]

    def test_has_slots(self) -> None:
        """DeploymentStatus should use __slots__ for memory efficiency."""
        status = DeploymentStatus(
            project="flipr",
            deployed_changes=(),
            pending_changes=(),
            deployed_tags=(),
            last_deployed_change=None,
        )
        assert not hasattr(status, "__dict__")

    def test_uses_tuples_for_immutability(self) -> None:
        """Fields should use tuples for immutable sequences."""
        status = DeploymentStatus(
            project="flipr",
            deployed_changes=("users", "schema"),
            pending_changes=("indexes",),
            deployed_tags=("v1.0",),
            last_deployed_change="schema",
        )
        # Tuples don't have append method
        assert not hasattr(status.deployed_changes, "append")
        assert not hasattr(status.pending_changes, "append")
        assert not hasattr(status.deployed_tags, "append")
