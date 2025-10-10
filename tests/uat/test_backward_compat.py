"""CLI contract tests for the backward compatibility UAT harness."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_backward_compat(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("SQLITCH_UAT_SKIP_EXECUTION", "1")
    out_file = tmp_path / "backward.log"
    cmd = [
        "python",
        "uat/backward-compat.py",
        "--out",
        str(out_file),
    ]
    return subprocess.run(cmd, cwd=Path.cwd(), text=True, capture_output=True, env=env, check=False)


def test_backward_compat_happy_path_short_circuit(tmp_path: Path) -> None:
    """Skip-enabled runs should still report success and create the log file."""

    result = run_backward_compat(tmp_path)

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Backward compatibility" in result.stdout
    assert (tmp_path / "backward.log").exists()


def test_backward_compat_requires_out_argument(tmp_path: Path) -> None:
    """CLI should demand an --out destination for parity with other harnesses."""

    env = os.environ.copy()
    env.setdefault("SQLITCH_UAT_SKIP_EXECUTION", "1")
    result = subprocess.run(
        ["python", "uat/backward-compat.py"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert result.returncode != 0
    assert "--out" in result.stderr or result.stdout