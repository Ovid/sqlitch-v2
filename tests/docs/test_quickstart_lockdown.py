"""Documentation validation tests for lockdown phase.

These tests ensure README quickstart and CONTRIBUTING instructions remain in sync
with the actual project setup and workflow requirements.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"


def test_readme_includes_venv_setup():
    """README quickstart should document virtual environment creation."""
    content = README.read_text()
    assert (
        "python3 -m venv" in content or "python -m venv" in content
    ), "README should include venv setup instructions"


def test_readme_includes_editable_install():
    """README should document the editable install command."""
    content = README.read_text()
    assert "pip install -e" in content, "README should document editable install"


def test_contributing_references_pytest():
    """CONTRIBUTING should mention pytest as the test runner."""
    content = CONTRIBUTING.read_text()
    assert "pytest" in content.lower(), "CONTRIBUTING should reference pytest"


def test_contributing_mentions_coverage_gate():
    """CONTRIBUTING should document the 90% coverage requirement."""
    content = CONTRIBUTING.read_text()
    # Look for coverage percentage mention
    assert re.search(
        r"90%|90 percent|coverage.*90", content, re.IGNORECASE
    ), "CONTRIBUTING should document 90% coverage requirement"


def test_readme_pyproject_version_alignment():
    """README should be consistent about alpha/beta status matching pyproject.toml."""
    import tomli

    pyproject = REPO_ROOT / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomli.load(f)

    version = data["project"]["version"]
    readme_content = README.read_text()

    # Check that README mentions alpha status (appropriate for 0.x versions)
    if version.startswith("0."):
        assert (
            "alpha" in readme_content.lower() or "development" in readme_content.lower()
        ), "README should indicate alpha/development status for 0.x versions"


def test_quickstart_commands_are_executable():
    """Validate that documented quickstart commands can actually run."""
    # Check that pytest can be invoked
    result = subprocess.run(
        ["pytest", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "pytest should be available in dev environment"

    # Check that mypy can be invoked
    result = subprocess.run(
        ["mypy", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "mypy should be available in dev environment"
