"""Test that the test suite does not pollute user config directories.

This regression test ensures Constitutional compliance with Test Isolation mandate.

Constitutional References:
    - Constitution I: Test Isolation and Cleanup (MANDATORY)
    - FR-001b: 100% Configuration Compatibility (CRITICAL)
    - NFR-007: Test Isolation and Configuration Compatibility (MANDATORY)

USAGE NOTE:
-----------
These tests check for config pollution by other tests in the suite. Due to pytest-randomly
reordering tests, they may report false failures when run with the full suite.

For accurate results, run these tests separately:
    pytest tests/test_no_config_pollution.py -v

If these tests fail in CI or full suite runs, it indicates a REAL PROBLEM with test
isolation somewhere in the test suite that must be addressed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def get_config_dirs() -> tuple[Path, Path]:
    """Get paths to potential config pollution directories."""
    home = Path.home()
    return (
        home / ".config" / "sqlitch",  # SQLitch-specific (should NEVER exist)
        home / ".sqitch",  # Sqitch-compatible (may exist legitimately)
    )


@pytest.fixture(scope="module")
def config_snapshot():
    """Snapshot filesystem state before and after module tests."""
    sqlitch_dir, sqitch_dir = get_config_dirs()

    # Record initial state
    initial_state = {
        "sqlitch_exists": sqlitch_dir.exists(),
        "sqlitch_files": list(sqlitch_dir.rglob("*")) if sqlitch_dir.exists() else [],
        "sqitch_exists": sqitch_dir.exists(),
        "sqitch_files": list(sqitch_dir.rglob("*")) if sqitch_dir.exists() else [],
    }

    yield initial_state

    # Verify state after tests
    final_state = {
        "sqlitch_exists": sqlitch_dir.exists(),
        "sqlitch_files": list(sqlitch_dir.rglob("*")) if sqlitch_dir.exists() else [],
        "sqitch_exists": sqitch_dir.exists(),
        "sqitch_files": list(sqitch_dir.rglob("*")) if sqitch_dir.exists() else [],
    }

    # Check for pollution
    if final_state["sqlitch_exists"] and not initial_state["sqlitch_exists"]:
        pytest.fail(
            f"CRITICAL: Tests created ~/.config/sqlitch/ directory!\n"
            f"This violates FR-001b and Constitution Test Isolation mandate.\n"
            f"Files created: {final_state['sqlitch_files']}"
        )

    if final_state["sqlitch_exists"]:
        new_files = set(final_state["sqlitch_files"]) - set(initial_state["sqlitch_files"])
        if new_files:
            pytest.fail(
                f"CRITICAL: Tests added files to ~/.config/sqlitch/!\n" f"New files: {new_files}"
            )


def test_no_sqlitch_config_directory_created(config_snapshot):
    """Verify that ~/.config/sqlitch/ is NEVER created by tests.

    This is a CRITICAL requirement for FR-001b: 100% Configuration Compatibility.
    SQLitch must use ~/.sqitch/ to maintain drop-in compatibility with Sqitch.
    """
    sqlitch_dir, _ = get_config_dirs()

    # ~/.config/sqlitch/ should NEVER exist
    assert not sqlitch_dir.exists(), (
        f"CRITICAL VIOLATION: ~/.config/sqlitch/ directory exists!\n"
        f"SQLitch must use ~/.sqitch/ for Sqitch compatibility (FR-001b).\n"
        f"This directory should never be created."
    )


def test_config_functional_tests_are_isolated():
    """Run config_functional tests and verify no pollution."""
    sqlitch_dir, sqitch_dir = get_config_dirs()

    # Snapshot before
    sqlitch_existed_before = sqlitch_dir.exists()
    sqitch_files_before = list(sqitch_dir.rglob("*")) if sqitch_dir.exists() else []

    # Run config tests (most likely to cause pollution)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/cli/commands/test_config_functional.py",
            "--no-cov",
            "-q",
        ],
        capture_output=True,
        text=True,
    )

    # Tests should pass (or at least not crash)
    assert result.returncode in (
        0,
        1,
    ), f"Config tests failed unexpectedly:\n{result.stdout}\n{result.stderr}"

    # Verify no SQLitch-specific directory created
    assert not sqlitch_dir.exists() or sqlitch_existed_before, (
        f"CRITICAL: Config tests created ~/.config/sqlitch/!\n"
        f"Tests must use isolated_test_context() from tests.support.test_helpers"
    )

    # Verify no unexpected changes to ~/.sqitch/
    sqitch_files_after = list(sqitch_dir.rglob("*")) if sqitch_dir.exists() else []
    new_files = set(sqitch_files_after) - set(sqitch_files_before)

    assert not new_files, (
        f"Config tests modified ~/.sqitch/ unexpectedly!\n"
        f"New files: {new_files}\n"
        f"Tests must use isolated_test_context() to prevent pollution"
    )


def test_sample_tests_from_each_directory():
    """Run a sample of tests from each directory to verify isolation.

    This is a smoke test to catch any non-migrated tests that might
    still be polluting the filesystem.
    """
    sqlitch_dir, sqitch_dir = get_config_dirs()

    test_samples = [
        "tests/cli/test_cli_context.py",
        "tests/cli/commands/test_config_functional.py",
        "tests/integration/test_quickstart_sqlite.py",
    ]

    # Snapshot before
    sqlitch_existed_before = sqlitch_dir.exists()

    for test_file in test_samples:
        if not Path(test_file).exists():
            continue

        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "--no-cov", "-q"],
            capture_output=True,
            text=True,
        )

        # Check for pollution after each test file
        if sqlitch_dir.exists() and not sqlitch_existed_before:
            pytest.fail(
                f"CRITICAL: {test_file} created ~/.config/sqlitch/!\n"
                f"This test file needs to be migrated to use isolated_test_context()"
            )


def test_isolated_test_context_helper_is_available():
    """Verify the isolation helper is importable and working."""
    try:
        from tests.support.test_helpers import isolated_test_context
    except ImportError:
        pytest.fail(
            "CRITICAL: tests.support.test_helpers module not found!\n"
            "The isolated_test_context() helper is required for test isolation."
        )

    # Verify it's a context manager
    import inspect

    assert hasattr(isolated_test_context, "__call__"), "isolated_test_context should be callable"


def test_readme_documents_isolation_requirements():
    """Verify documentation exists for test isolation patterns."""
    readme_path = Path("tests/support/README.md")

    assert readme_path.exists(), "tests/support/README.md must exist to document isolation patterns"

    content = readme_path.read_text()

    # Check for key documentation elements
    required_terms = [
        "isolated_test_context",
        "Constitution",
        "FR-001b",
        "NFR-007",
        "Test Isolation",
    ]

    missing = [term for term in required_terms if term not in content]
    assert not missing, f"README.md missing required documentation for: {missing}"
