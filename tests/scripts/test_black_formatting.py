"""Tooling scaffold for enforcing Black formatting gate."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Pending T035a: enforce Black formatting gate")


def test_black_formatting_gate() -> None:
    """Placeholder test ensuring Black formatting enforcement is wired."""
    ...
