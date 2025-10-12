"""Type safety compliance tests using mypy.

This module ensures mypy --strict type checking doesn't regress.
We track the current error count as a baseline and fail if new errors appear.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Current baseline of known mypy --strict errors
# This should ONLY decrease over time as we fix type issues
# DO NOT increase this number - fix the new type errors instead!
BASELINE_MYPY_ERROR_COUNT = 24


class TestMypyCompliance:
    """Test suite to enforce mypy type safety without regressions."""

    def test_mypy_no_new_errors(self) -> None:
        """Verify mypy --strict doesn't have more errors than baseline.

        Runs: mypy --strict sqlitch/

        This enforces that new code doesn't introduce type safety issues.
        The baseline count should only decrease as we fix existing issues.

        If this test fails with MORE errors than baseline:
        - Fix the new type errors in your changes
        - DO NOT increase BASELINE_MYPY_ERROR_COUNT

        If this test fails with FEWER errors than baseline:
        - Celebrate! Update BASELINE_MYPY_ERROR_COUNT to the new lower value
        """
        result = subprocess.run(
            ["mypy", "--strict", "sqlitch/"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        # Count actual errors (lines containing "error:")
        error_lines = [line for line in result.stdout.split("\n") if "error:" in line]
        current_error_count = len(error_lines)

        if current_error_count < BASELINE_MYPY_ERROR_COUNT:
            pytest.fail(
                f"Great work! Mypy errors reduced from {BASELINE_MYPY_ERROR_COUNT} "
                f"to {current_error_count}.\n"
                f"Please update BASELINE_MYPY_ERROR_COUNT in tests/test_type_safety.py "
                f"to {current_error_count}"
            )
        elif current_error_count > BASELINE_MYPY_ERROR_COUNT:
            pytest.fail(
                f"Mypy type safety regression detected!\n"
                f"Baseline: {BASELINE_MYPY_ERROR_COUNT} errors\n"
                f"Current: {current_error_count} errors\n"
                f"New errors introduced: {current_error_count - BASELINE_MYPY_ERROR_COUNT}\n\n"
                f"Fix the type errors below:\n{result.stdout}"
            )

        # If equal to baseline, test passes (no regression)
        assert current_error_count == BASELINE_MYPY_ERROR_COUNT
