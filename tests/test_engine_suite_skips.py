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


# Migrated from tests/regression/test_docker_skip.py
@pytest.mark.skip(reason="Pending T033: Docker unavailability skip regression")
def test_docker_unavailable_skip_behaviour() -> None:
    """Placeholder regression test for T033 - Docker unavailability skip behavior.

    When implemented, this should test that tests requiring Docker are properly
    skipped with appropriate messaging when Docker is not available, similar to
    how engine stub tests are skipped.
    """
    ...
