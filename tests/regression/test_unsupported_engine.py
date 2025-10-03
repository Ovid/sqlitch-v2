"""Regression scaffold for unsupported engine handling."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Pending T031: unsupported engine failure regression")


def test_unsupported_engine_failure() -> None:
    """Placeholder regression test for T031."""
    ...
