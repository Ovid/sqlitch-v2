"""Regression scaffold ensuring drop-in Sqitch artifacts behave."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Pending T030: drop-in Sqitch artifact parity")


def test_sqitch_dropin_behaviour() -> None:
    """Placeholder regression test for T030."""
    ...
