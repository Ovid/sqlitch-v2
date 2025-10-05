"""Regression scaffold for engine stub skip messaging."""

from __future__ import annotations

from textwrap import dedent

import pytest

pytest_plugins = ("pytester",)


def test_engine_stub_suites_report_skips(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(
        dedent(
            """
            from tests import conftest as project_conftest


            pytest_configure = project_conftest.pytest_configure
            pytest_collection_modifyitems = project_conftest.pytest_collection_modifyitems
            """
        )
    )

    pytester.makeini(
        dedent(
            """
            [pytest]
            markers =
                requires_engine(name): mark test as requiring a specific database engine
            """
        )
    )

    pytester.makepyfile(
        dedent(
            """
            import pytest


            @pytest.mark.requires_engine("mysql")
            def test_mysql_placeholder() -> None:
                assert False, "should be skipped by pytest configuration"


            @pytest.mark.requires_engine("postgres")
            def test_postgres_placeholder() -> None:
                assert False, "should be skipped by pytest configuration"
            """
        )
    )

    result = pytester.runpytest("-q", "-rs")
    result.assert_outcomes(skipped=2)

    stdout = result.stdout.str()
    assert "MySQL engine suite skipped" in stdout
    assert "PostgreSQL engine suite skipped" in stdout
