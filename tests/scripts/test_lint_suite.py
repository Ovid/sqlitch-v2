"""Tooling scaffold for aggregated lint gate enforcement."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Pending T035c: enforce aggregated lint gate")


def test_lint_suite_gate() -> None:
    """Placeholder test ensuring lint suite enforcement is wired."""
    ...
