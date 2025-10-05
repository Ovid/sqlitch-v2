"""Regression tests for structured logging observability."""

from __future__ import annotations

import json

from click.testing import CliRunner

from sqlitch.cli.main import main


def test_structured_logging_emits_run_identifier() -> None:
    """Structured logs should include the run identifier in human and JSON modes."""

    runner = CliRunner()

    human_result = runner.invoke(main, ["help"], env={"SQLITCH_RUN_ID": "human-run"})

    assert human_result.exit_code == 0, human_result.stderr
    human_lines = [line for line in human_result.stderr.splitlines() if line.strip()]
    assert any("human-run" in line and "command.start" in line for line in human_lines)
    assert any("human-run" in line and "command.complete" in line for line in human_lines)

    json_result = runner.invoke(main, ["--json", "help"], env={"SQLITCH_RUN_ID": "json-run"})

    assert json_result.exit_code == 0, json_result.stderr
    payloads = [json.loads(line) for line in json_result.stderr.splitlines() if line.strip()]
    events = {payload["event"]: payload for payload in payloads}

    assert events["command.start"]["run_id"] == "json-run"
    assert events["command.complete"]["run_id"] == "json-run"
