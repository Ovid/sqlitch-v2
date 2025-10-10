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

import subprocess
from pathlib import Path

import pytest

__all__ = ["test_no_direct_isolated_filesystem_usage"]


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
            error_message = (
                "\n"
                "❌ CONSTITUTION VIOLATION: Test Isolation Not Enforced\n"
                "\n"
                f"Found {len(violating_files)} test file(s) using isolated_filesystem() directly:\n"
                "\n"
            )
            for file in violating_files:
                error_message += f"  - {file}\n"

            error_message += (
                "\n"
                "This violates Constitution I: Test Isolation and Cleanup (MANDATORY)\n"
                "\n"
                "WHY THIS IS CRITICAL:\n"
                "Direct use of isolated_filesystem() does NOT isolate environment variables.\n"
                "Tests can write config files to ~/.config/sqlitch/ or ~/.sqitch/, polluting\n"
                "the user's home directory and potentially DESTROYING existing Sqitch/SQLitch\n"
                "configuration.\n"
                "\n"
                "HOW TO FIX:\n"
                "1. Import the helper:\n"
                "   from tests.support.test_helpers import isolated_test_context\n"
                "\n"
                "2. Replace:\n"
                "   with runner.isolated_filesystem():\n"
                "       # test code\n"
                "\n"
                "   With:\n"
                "   with isolated_test_context(runner) as (runner, temp_dir):\n"
                "       # test code\n"
                "\n"
                "3. Update paths:\n"
                "   Change Path('file.txt') to (temp_dir / 'file.txt')\n"
                "\n"
                "4. For batch processing:\n"
                "   python scripts/migrate_test_isolation.py <test_file>\n"
                "\n"
                "See tests/support/README.md for detailed migration guide.\n"
            )
            pytest.fail(error_message)

    # Any other return code is an error
    if result.returncode not in (0, 1):
        pytest.fail(
            f"git grep command failed with code {result.returncode}:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
