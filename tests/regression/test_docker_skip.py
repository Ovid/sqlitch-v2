"""Regression scaffold for Docker availability skip behaviour."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Pending T033: Docker unavailability skip regression")


def test_docker_unavailable_skip_behaviour() -> None:
    """Placeholder regression test for T033."""
    ...
