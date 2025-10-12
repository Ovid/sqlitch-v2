"""Automated formatting compliance tests.

This module enforces black and isort formatting standards via pytest.
Any formatting violations will fail the test suite, ensuring consistent
code style across the codebase.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class TestBlackFormatting:
    """Test suite to enforce black code formatting."""

    def test_black_formatting_compliance(self) -> None:
        """Verify all Python files comply with black formatting standards.

        Runs: black --check sqlitch/ tests/

        This ensures no formatting regressions are introduced during development.
        If this test fails, run: black sqlitch/ tests/
        """
        result = subprocess.run(
            ["black", "--check", "sqlitch/", "tests/"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"Black formatting check failed. Run 'black sqlitch/ tests/' to fix.\n"
            f"Output:\n{result.stdout}\n{result.stderr}"
        )


class TestIsortFormatting:
    """Test suite to enforce isort import ordering."""

    def test_isort_import_compliance(self) -> None:
        """Verify all Python files have properly sorted imports.

        Runs: isort --check-only sqlitch/ tests/

        This ensures import statements follow consistent ordering.
        If this test fails, run: isort sqlitch/ tests/
        """
        result = subprocess.run(
            ["isort", "--check-only", "sqlitch/", "tests/"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"Isort import order check failed. Run 'isort sqlitch/ tests/' to fix.\n"
            f"Output:\n{result.stdout}\n{result.stderr}"
        )
