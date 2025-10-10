"""Lockdown regression tests for CLI global flag handling and context."""

from __future__ import annotations

import json
from typing import Iterable

from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


def _collect_non_json_lines(output: str) -> list[str]:
    """Return lines from output that are not valid JSON payloads."""
    non_json: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            non_json.append(line)
    return non_json


def _invoke_cli(args: Iterable[str]) -> tuple[int, str]:
    runner = CliRunner()
    with isolated_test_context(runner) as (runner, _temp_dir):
        result = runner.invoke(main, list(args))
    return result.exit_code, result.output


def test_init_error_in_json_mode_emits_structured_output_only() -> None:
    exit_code, output = _invoke_cli(["--json", "init", "--engine", "invalid"])

    assert exit_code != 0
    assert _collect_non_json_lines(output) == []


def test_add_error_in_json_mode_emits_structured_output_only() -> None:
    exit_code, output = _invoke_cli(["--json", "add", "users"])

    assert exit_code != 0
    assert _collect_non_json_lines(output) == []


def test_deploy_error_in_json_mode_emits_structured_output_only() -> None:
    exit_code, output = _invoke_cli(["--json", "deploy"])

    assert exit_code != 0
    assert _collect_non_json_lines(output) == []
