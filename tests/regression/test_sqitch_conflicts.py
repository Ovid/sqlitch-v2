"""Regression scaffold for conflict detection between Sqitch and SQLitch artifacts."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Pending T030a: enforce blocking conflicts between Sqitch and SQLitch artifacts"
)


def test_sqitch_sqlitch_conflict_detection() -> None:
    """Placeholder regression test for T030a."""
    ...
