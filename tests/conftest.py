"""Pytest configuration for SQLitch test suite."""

from __future__ import annotations

import subprocess
from pathlib import Path
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


def pytest_sessionstart(session: pytest.Session) -> None:
    """
    Run critical sanity checks before test session begins.
    
    This hook runs BEFORE any test collection or execution, ensuring that
    constitutional requirements are met before wasting time on tests that
    would pollute the user's environment.
    
    CRITICAL: Test Isolation Enforcement
    ====================================
    We check that no test files use runner.isolated_filesystem() directly,
    which would violate Constitution I: Test Isolation and Cleanup (MANDATORY).
    
    If violations are found, the entire test session is aborted with a clear
    error message explaining how to fix the issue.
    """
    # Define the repo root
    repo_root = Path(__file__).parent.parent
    
    # Define exceptions - files that are allowed to use isolated_filesystem
    exceptions = {
        "tests/support/test_helpers.py",  # Defines the helper
        "tests/support/test_test_helpers.py",  # Tests the helper
        "tests/support/README.md",  # Documentation
        "tests/conftest.py",  # This file - checks for violations
        "tests/regression/test_test_isolation_enforcement.py",  # Enforcement test
        "tests/regression/MIGRATION_COMPLETE.md",  # Migration documentation
        "tests/regression/README_ENFORCEMENT.md",  # Enforcement documentation
    }
    
    # Search for test files using isolated_filesystem
    result = subprocess.run(
        ["git", "grep", "-l", "isolated_filesystem", "tests/"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    
    # If git grep returns 1, no matches found (which is what we want)
    if result.returncode == 1:
        return  # All tests properly use isolated_test_context()
    
    # If git grep returns 0, matches found - check if they're exceptions
    if result.returncode == 0:
        violating_files = []
        for line in result.stdout.strip().split("\n"):
            if line and line not in exceptions:
                violating_files.append(line)
        
        if violating_files:
            files_list = "\n".join(f"  - {file}" for file in violating_files)
            
            error_message = f"""

╔══════════════════════════════════════════════════════════════════════════════╗
║                   ❌ CONSTITUTION VIOLATION DETECTED                          ║
║                   TEST SESSION ABORTED                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Found {len(violating_files)} test file(s) using isolated_filesystem() directly:

{files_list}

This violates Constitution I: Test Isolation and Cleanup (MANDATORY)

WHY THIS IS CRITICAL:
━━━━━━━━━━━━━━━━━━
Direct use of isolated_filesystem() does NOT isolate environment variables.
Tests can write config files to ~/.config/sqlitch/ or ~/.sqitch/, polluting
the user's home directory and potentially DESTROYING existing Sqitch/SQLitch
configuration.

The test suite will NOT run until this is fixed.

HOW TO FIX:
━━━━━━━━━━━
1. Import the helper:
   from tests.support.test_helpers import isolated_test_context

2. Replace:
   with runner.isolated_filesystem():
       # test code

   With:
   with isolated_test_context(runner) as (runner, temp_dir):
       # test code

3. Update paths:
   Change Path('file.txt') to (temp_dir / 'file.txt')

4. For batch processing:
   python scripts/migrate_test_isolation.py <test_file>

See tests/support/README.md for detailed migration guide.

Constitutional Reference: Constitution I: Test Isolation and Cleanup (MANDATORY)
"""
            pytest.exit(error_message, returncode=1)
    
    # Any other return code is an error
    if result.returncode not in (0, 1):
        error_message = f"""
Git grep command failed with code {result.returncode}:
stdout: {result.stdout}
stderr: {result.stderr}
"""
        pytest.exit(error_message, returncode=1)


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
