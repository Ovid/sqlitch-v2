"""Tests for structured logging helpers."""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone

from rich.console import Console

from sqlitch.cli.options import LogConfiguration
from sqlitch.utils.logging import StructuredLogger


def _clock() -> datetime:
    return datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_structured_logger_suppresses_output_without_opt_in() -> None:
    log_config = LogConfiguration(run_identifier="run-1", verbosity=0, quiet=False, json_mode=False)
    console = Console(record=True, width=120, color_system=None)
    logger = StructuredLogger(log_config, console=console, json_stream=io.StringIO(), clock=_clock)

    record = logger.info("command.start", "Starting command", payload={"target": "dev"})

    assert record is not None
    assert record.payload["target"] == "dev"
    assert console.export_text(clear=True) == ""


def test_structured_logger_emits_human_readable_lines_when_verbose() -> None:
    log_config = LogConfiguration(
        run_identifier="run-verbose", verbosity=1, quiet=False, json_mode=False
    )
    console = Console(record=True, width=120, color_system=None)
    logger = StructuredLogger(log_config, console=console, json_stream=io.StringIO(), clock=_clock)

    record = logger.info("command.start", "Starting command", payload={"target": "dev"})

    output = console.export_text(clear=True)
    assert "command.start" in output
    assert "Starting command" in output
    assert "run-verbose" in output
    assert record is not None
    assert record.payload["target"] == "dev"


def test_structured_logger_respects_log_level_threshold() -> None:
    log_config = LogConfiguration(run_identifier="run-2", verbosity=0, quiet=False, json_mode=False)
    console = Console(record=True, width=120, color_system=None)
    logger = StructuredLogger(log_config, console=console, json_stream=io.StringIO(), clock=_clock)

    dropped = logger.debug("command.debug", "Debug message")
    assert dropped is None
    assert console.export_text(clear=True) == ""

    emitted = logger.info("command.info", "Info message")
    assert emitted is not None
    assert emitted.message == "Info message"
    assert console.export_text(clear=True) == ""


def test_structured_logger_emits_json_when_requested() -> None:
    stream = io.StringIO()
    log_config = LogConfiguration(run_identifier="run-3", verbosity=0, quiet=False, json_mode=True)
    logger = StructuredLogger(
        log_config, console=Console(width=120, color_system=None), json_stream=stream, clock=_clock
    )

    logger.warning("command.warn", "Warning", payload={"code": 42})

    payload = json.loads(stream.getvalue())
    assert payload["run_id"] == "run-3"
    assert payload["event"] == "command.warn"
    assert payload["message"] == "Warning"
    assert payload["data"] == {"code": 42}


def test_structured_logger_quiet_mode_records_errors_without_emit() -> None:
    log_config = LogConfiguration(run_identifier="run-4", verbosity=0, quiet=True, json_mode=False)
    console = Console(record=True, width=120, color_system=None)
    logger = StructuredLogger(log_config, console=console, json_stream=io.StringIO(), clock=_clock)

    suppressed = logger.info("command.info", "Should be hidden")
    assert suppressed is None
    assert console.export_text(clear=True) == ""

    emitted = logger.error("command.fail", "Failure occurred", payload={"reason": "boom"})
    assert emitted is not None
    assert emitted.message == "Failure occurred"
    assert dict(emitted.payload)["reason"] == "boom"
    assert console.export_text(clear=True) == ""


def test_structured_logger_respects_quiet_mode_with_json_output() -> None:
    stream = io.StringIO()
    log_config = LogConfiguration(
        run_identifier="run-quiet-json", verbosity=0, quiet=True, json_mode=True
    )
    logger = StructuredLogger(
        log_config, console=Console(width=120, color_system=None), json_stream=stream, clock=_clock
    )

    record = logger.error("command.fail", "Failure occurred", payload={"reason": "boom"})

    assert record is not None
    payload = json.loads(stream.getvalue())
    assert payload["run_id"] == "run-quiet-json"
    assert payload["event"] == "command.fail"
    assert payload["message"] == "Failure occurred"
    assert payload["data"] == {"reason": "boom"}
