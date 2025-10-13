"""
Regression test: Enforce test isolation patterns.

This test ensures that all test files use the isolated_test_context() helper
instead of directly calling runner.isolated_filesystem(), which can lead to
config pollution and constitutional violations.

Constitutional References:
- Constitution I: Test Isolation and Cleanup (MANDATORY)
- Spec FR-001b: 100% Configuration Compatibility (CRITICAL)
- Spec NFR-007: Test Isolation and Configuration Compatibility (MANDATORY)
"""

from __future__ import annotations

import importlib
import os
import subprocess
from pathlib import Path

import pytest

import tests.support.test_helpers as test_helpers

__all__ = [
    "test_no_direct_isolated_filesystem_usage",
    "test_test_helpers_meets_test_safety_objectives",
]


def test_no_direct_isolated_filesystem_usage() -> None:
    """
    Verify that no test files use runner.isolated_filesystem() directly.

    RATIONALE:
    Direct use of Click's isolated_filesystem() creates temp directories but
    does NOT isolate environment variables. This means tests that invoke
    'sqlitch config --user' will write to the actual ~/.config/sqlitch/ or
    ~/.sqitch/ directories, violating test isolation principles.

    SOLUTION:
    Use isolated_test_context() from tests.support.test_helpers instead, which
    automatically sets SQLITCH_* environment variables to point inside the
    temp directory.

    HOW TO FIX:
    If this test fails, it means a test file is using isolated_filesystem()
    directly. Follow these steps:

    1. Import the helper:
       from tests.support.test_helpers import isolated_test_context

    2. Replace this pattern:
       ```python
       with runner.isolated_filesystem():
           # test code
       ```

       With this pattern:
       ```python
       with isolated_test_context(runner) as (runner, temp_dir):
           # test code
       ```

    3. Update path references:
       - Change Path("file.txt") to (temp_dir / "file.txt")
       - This makes the temp directory explicit and improves readability

    4. Run the migration script for batch processing:
       ```bash
       python scripts/migrate_test_isolation.py tests/path/to/test_file.py
       ```

    EXCEPTIONS:
    The following files are allowed to use isolated_filesystem():
    - tests/support/test_helpers.py (defines the helper)
    - tests/support/test_test_helpers.py (tests the helper implementation)
    - tests/support/README.md (documentation)
    """
    # Define the repo root
    repo_root = Path(__file__).parent.parent.parent

    # Define exceptions - files that are allowed to use isolated_filesystem
    exceptions = {
        "tests/support/test_helpers.py",  # Defines the helper
        "tests/support/test_test_helpers.py",  # Tests the helper
        "tests/support/README.md",  # Documentation
        "tests/conftest.py",  # Session hook - checks for violations
        "tests/test_test_isolation_enforcement.py",  # This file (moved from regression)
        "tests/regression/MIGRATION_COMPLETE.md",  # Migration documentation
        "tests/regression/README_ENFORCEMENT.md",  # Enforcement documentation
    }

    # Search for test files using isolated_filesystem
    result = subprocess.run(
        ["git", "grep", "-l", "isolated_filesystem", "tests/"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,  # Intentionally check returncode manually to handle git grep exit codes
    )

    # If git grep returns 1, no matches found (which is what we want)
    if result.returncode == 1:
        return  # All tests properly use isolated_test_context()

    # If git grep returns 128, not a git repo - skip check
    if result.returncode == 128:
        pytest.skip("Not running in a git repository")

    # If git grep returns 0, matches found - check if they're exceptions
    if result.returncode == 0:
        violating_files = []
        for line in result.stdout.strip().split("\n"):
            if line and line not in exceptions:
                violating_files.append(line)

        if violating_files:
            files_list = "\n".join(f"  - {file}" for file in violating_files)

            error_message = f"""

❌ CONSTITUTION VIOLATION: Test Isolation Not Enforced

Found {len(violating_files)} test file(s) using isolated_filesystem() directly:

{files_list}

This violates Constitution I: Test Isolation and Cleanup (MANDATORY)

WHY THIS IS CRITICAL:
Direct use of isolated_filesystem() does NOT isolate environment variables.
Tests can write config files to ~/.config/sqlitch/ or ~/.sqitch/, polluting
the user's home directory and potentially DESTROYING existing Sqitch/SQLitch
configuration.

HOW TO FIX:
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
"""
            pytest.fail(error_message)

    # Any other return code is an error
    if result.returncode not in (0, 1):
        pytest.fail(
            f"git grep command failed with code {result.returncode}:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )


def test_test_helpers_meets_test_safety_objectives(monkeypatch):
    """Ensure helper import scrubs Sqitch/SQLitch environment variables."""

    sample_keys: list[str] = []

    for prefix in test_helpers.SANITIZED_ENVIRONMENT_PREFIXES:
        key = f"{prefix}TEST_SAFETY_ENFORCEMENT"
        sample_keys.append(key)
        monkeypatch.setenv(key, "value")

    for key in test_helpers.SANITIZED_ENVIRONMENT_VARIABLES:
        sample_keys.append(key)
        monkeypatch.setenv(key, "value")

    reloaded = importlib.reload(test_helpers)
    globals()["test_helpers"] = reloaded

    for key in sample_keys:
        assert key not in os.environ, f"Environment variable {key} must be cleared on import"

    for existing in list(os.environ):
        if existing.startswith(reloaded.SANITIZED_ENVIRONMENT_PREFIXES):
            pytest.fail(
                "tests.support.test_helpers must remove all SQITCH_/SQLITCH_ variables on import; "
                f"found lingering {existing}"
            )
