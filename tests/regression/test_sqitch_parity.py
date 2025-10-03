"""Regression scaffold comparing SQLitch to Sqitch."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Pending T028: regression parity against Sqitch projects")


def test_sqitch_parity_fixture_alignment() -> None:
    """Placeholder regression test for T028."""
    ...
