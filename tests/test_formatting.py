"""Automated formatting compliance tests.

This module enforces black and isort formatting standards via pytest.
Any formatting violations will fail the test suite, ensuring consistent
code style across the codebase.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class TestBlackFormatting:
    """Test suite to enforce black code formatting."""

    def test_black_formatting_compliance(self) -> None:
        """Verify all Python files comply with black formatting standards.

        Runs: black --check src/sqlitch/ tests/

        This ensures no formatting regressions are introduced during development.
        If this test fails, run: black src/sqlitch/ tests/
        """
        result = subprocess.run(
            ["black", "--check", "src/sqlitch/", "tests/"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,  # Intentionally check returncode in assertion to provide helpful message
        )

        assert result.returncode == 0, (
            f"Black formatting check failed. Run 'black src/sqlitch/ tests/' to fix.\n"
            f"Output:\n{result.stdout}\n{result.stderr}"
        )


class TestIsortFormatting:
    """Test suite to enforce isort import ordering."""

    def test_isort_import_compliance(self) -> None:
        """Verify all Python files have properly sorted imports.

        Runs: isort --check-only src/sqlitch/ tests/

        This ensures import statements follow consistent ordering.
        If this test fails, run: isort src/sqlitch/ tests/
        """
        result = subprocess.run(
            ["isort", "--check-only", "src/sqlitch/", "tests/"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,  # Intentionally check returncode in assertion to provide helpful message
        )

        assert result.returncode == 0, (
            f"Isort import order check failed. Run 'isort src/sqlitch/ tests/' to fix.\n"
            f"Output:\n{result.stdout}\n{result.stderr}"
        )


class TestFlake8Compliance:
    """Test suite to enforce flake8 linting standards."""

    def test_flake8_compliance(self) -> None:
        """Verify all Python files comply with flake8 linting rules.

        Runs: flake8 src/sqlitch/

        This ensures code follows PEP 8 and project-specific linting rules.
        If this test fails, fix the reported violations manually or via automated tools.
        """
        result = subprocess.run(
            ["flake8", "src/sqlitch/"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,  # Intentionally check returncode in assertion to provide helpful message
        )

        assert result.returncode == 0, (
            f"Flake8 linting check failed. Fix violations reported below.\n"
            f"Output:\n{result.stdout}\n{result.stderr}"
        )
