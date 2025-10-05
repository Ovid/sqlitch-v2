"""Pytest configuration for SQLitch test suite."""

from __future__ import annotations

from typing import Final

import pytest

_UNSUPPORTED_ENGINES: Final[dict[str, str]] = {
    "mysql": "MySQL engine suite skipped: SQLitch ships a parity stub only.",
    "pg": "PostgreSQL engine suite skipped: SQLitch ships a parity stub only.",
    "postgres": "PostgreSQL engine suite skipped: SQLitch ships a parity stub only.",
    "postgresql": "PostgreSQL engine suite skipped: SQLitch ships a parity stub only.",
}


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_engine(name): mark test as requiring a specific database engine",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        marker = item.get_closest_marker("requires_engine")
        if marker is None:
            continue

        if not marker.args:
            continue

        engine_name = str(marker.args[0]).strip().lower()
        reason = _UNSUPPORTED_ENGINES.get(engine_name)
        if reason is None:
            continue

        item.add_marker(pytest.mark.skip(reason=reason))
