from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "check-skips.py"


def run_check(*tasks: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT), *tasks]
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=merged_env,
    )


def test_passes_when_no_tasks_supplied() -> None:
    result = run_check()
    assert result.returncode == 0
    assert "skip markers" not in result.stderr.lower()


def test_fails_when_active_task_has_skip_marker() -> None:
    target_dir = PROJECT_ROOT / "tests" / "tmp_skip_checks"
    target_dir.mkdir(exist_ok=True)
    skip_file = target_dir / "test_pending_feature.py"
    skip_file.write_text(
        """import pytest

@pytest.mark.skip(reason='Pending via T777')
def test_pending_feature() -> None:
    pass
""",
        encoding="utf-8",
    )

    try:
        result = run_check("T777")
    finally:
        skip_file.unlink(missing_ok=True)
        if not any(target_dir.iterdir()):
            target_dir.rmdir()

    assert result.returncode == 1
    assert "T777" in result.stderr
    assert "Pending via T777" in result.stderr


def test_env_variable_enables_check() -> None:
    result = run_check(env={"SQLITCH_ACTIVE_TASKS": "T888"})
    assert result.returncode == 0
    assert "T888" not in result.stderr
