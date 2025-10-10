"""CLI contract tests for the forward compatibility UAT harness.

These tests encode the expected command-line surface of ``uat/forward-compat.py``.
They rely on a skip environment variable so the harness can short-circuit during
lockdown unit runs while still exercising CLI parsing, logging, and exit codes.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_forward_compat(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("SQLITCH_UAT_SKIP_EXECUTION", "1")
    out_file = tmp_path / "forward.log"
    cmd = [
        "python",
        "uat/forward-compat.py",
        "--out",
        str(out_file),
    ]
    return subprocess.run(cmd, cwd=Path.cwd(), text=True, capture_output=True, env=env, check=False)


def test_forward_compat_happy_path_short_circuit(tmp_path: Path) -> None:
    """When skip execution is enabled, the harness should exit zero and log output."""

    result = run_forward_compat(tmp_path)

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Forward compatibility" in result.stdout
    assert (tmp_path / "forward.log").exists()


def test_forward_compat_requires_out_argument(tmp_path: Path) -> None:
    """CLI should report a helpful error when required options are missing."""

    env = os.environ.copy()
    env.setdefault("SQLITCH_UAT_SKIP_EXECUTION", "1")
    result = subprocess.run(
        ["python", "uat/forward-compat.py"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert result.returncode != 0
    assert "--out" in result.stderr or result.stdout