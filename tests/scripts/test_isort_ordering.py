"""Tooling scaffold for enforcing isort import ordering gate."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Pending T035b: enforce isort import ordering gate")


def test_isort_ordering_gate() -> None:
    """Placeholder test ensuring isort ordering enforcement is wired."""
    ...
