"""Regression expectations for credential redaction in structured logs."""

from __future__ import annotations

import io
from datetime import datetime, timezone

from sqlitch.cli.options import LogConfiguration
from sqlitch.utils.logging import StructuredLogger


def test_structured_logs_redact_credentials() -> None:
    buffer = io.StringIO()
    logger = StructuredLogger(
        LogConfiguration(run_identifier="run", verbosity=0, quiet=False, json_mode=True),
        json_stream=buffer,
        clock=lambda: datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    record = logger.info(
        "engine.connect",
        payload={
            "username": "admin",
            "password": "supersecret",
            "nested": {"token": "abc123", "note": "ok"},
            "uri": "postgres://admin:supersecret@localhost/app",
            "sequence": [{"api_key": "abcdef"}, "value"],
        },
    )

    assert record is not None
    payload = dict(record.payload)
    assert payload["password"] == "***REDACTED***"
    assert payload["username"] == "admin"

    nested = payload["nested"]
    assert isinstance(nested, dict)
    assert nested["token"] == "***REDACTED***"
    assert nested["note"] == "ok"

    sequence = payload["sequence"]
    assert isinstance(sequence, list)
    assert sequence[0]["api_key"] == "***REDACTED***"
    assert sequence[1] == "value"

    output = buffer.getvalue()
    assert "supersecret" not in output
    assert "***REDACTED***" in output
