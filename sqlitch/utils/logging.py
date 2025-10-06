"""Structured logging helpers for SQLitch CLI commands."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from types import MappingProxyType
from typing import Any, TextIO

from rich.console import Console
from rich.text import Text

from sqlitch.cli.options import LogConfiguration

_LEVEL_ORDER: dict[str, int] = {
    "TRACE": 10,
    "DEBUG": 20,
    "INFO": 30,
    "WARNING": 40,
    "ERROR": 50,
    "CRITICAL": 60,
}

_LEVEL_STYLES: dict[str, str] = {
    "TRACE": "dim",
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold red",
}

_JSON_SEPARATORS = (",", ":")

REDACTED_PLACEHOLDER = "***REDACTED***"

_SENSITIVE_KEYWORDS: tuple[str, ...] = (
    "password",
    "passwd",
    "passphrase",
    "secret",
    "token",
    "apikey",
    "api_key",
    "access_key",
    "access_token",
    "refresh_token",
    "credential",
    "credentials",
    "auth_token",
)

_URL_PASSWORD_PATTERN = re.compile(r":([^@]*)@")


def _is_sensitive_key(key: str | None) -> bool:
    if key is None:
        return False

    normalised = key.replace("-", "_").lower()
    if normalised in _SENSITIVE_KEYWORDS:
        return True
    return any(keyword in normalised for keyword in _SENSITIVE_KEYWORDS)


def _redact_string(value: str) -> str:
    if "@" not in value or ":" not in value:
        return value
    if "://" not in value and value.count(":") == 1:
        return value
    return _URL_PASSWORD_PATTERN.sub(f":{REDACTED_PLACEHOLDER}@", value)


def _redact_value(value: Any, *, key: str | None = None) -> Any:
    if _is_sensitive_key(key):
        return REDACTED_PLACEHOLDER

    if isinstance(value, Mapping):
        return {
            sub_key: _redact_value(sub_value, key=sub_key) for sub_key, sub_value in value.items()
        }

    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, set):  # pragma: no cover - uncommon, preserved for completeness
        return {_redact_value(item) for item in value}

    if isinstance(value, str):
        return _redact_string(value)

    return value


def _redact_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _redact_value(value, key=key) for key, value in payload.items()}


@dataclass(slots=True, frozen=True)
class StructuredLogRecord:
    """Immutable representation of an emitted log record."""

    timestamp: datetime
    run_identifier: str
    level: str
    event: str
    message: str | None
    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable payload for JSON sinks."""

        data: dict[str, Any] = {
            "ts": self.timestamp.isoformat(),
            "run_id": self.run_identifier,
            "level": self.level,
            "event": self.event,
        }
        if self.message is not None:
            data["message"] = self.message
        if self.payload:
            data["data"] = dict(self.payload)
        return data


class StructuredLogger:
    """Emit structured log records to Rich or JSON sinks."""

    def __init__(
        self,
        config: LogConfiguration,
        *,
        console: Console | None = None,
        json_stream: TextIO | None = None,
        clock: Callable[[], datetime] | None = None,
        json_dumps: Callable[[Mapping[str, Any]], str] | None = None,
    ) -> None:
        self._config = config
        self._console = console or Console(
            stderr=True,
            markup=config.rich_markup,
            force_terminal=False,
            highlight=False,
            record=False,
        )
        self._json_stream = json_stream
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._json_dumps = json_dumps or (
            lambda value: json.dumps(value, separators=_JSON_SEPARATORS, sort_keys=True)
        )
        level_name = config.level.upper()
        self._threshold = _LEVEL_ORDER.get(level_name, _LEVEL_ORDER["INFO"])
        self._structured_logging_enabled = config.structured_logging_enabled

    def trace(
        self,
        event: str,
        message: str | None = None,
        *,
        payload: Mapping[str, Any] | None = None,
        **extra: Any,
    ) -> StructuredLogRecord | None:
        return self.emit("TRACE", event, message, payload=payload, **extra)

    def debug(
        self,
        event: str,
        message: str | None = None,
        *,
        payload: Mapping[str, Any] | None = None,
        **extra: Any,
    ) -> StructuredLogRecord | None:
        return self.emit("DEBUG", event, message, payload=payload, **extra)

    def info(
        self,
        event: str,
        message: str | None = None,
        *,
        payload: Mapping[str, Any] | None = None,
        **extra: Any,
    ) -> StructuredLogRecord | None:
        return self.emit("INFO", event, message, payload=payload, **extra)

    def warning(
        self,
        event: str,
        message: str | None = None,
        *,
        payload: Mapping[str, Any] | None = None,
        **extra: Any,
    ) -> StructuredLogRecord | None:
        return self.emit("WARNING", event, message, payload=payload, **extra)

    def error(
        self,
        event: str,
        message: str | None = None,
        *,
        payload: Mapping[str, Any] | None = None,
        **extra: Any,
    ) -> StructuredLogRecord | None:
        return self.emit("ERROR", event, message, payload=payload, **extra)

    def critical(
        self,
        event: str,
        message: str | None = None,
        *,
        payload: Mapping[str, Any] | None = None,
        **extra: Any,
    ) -> StructuredLogRecord | None:
        return self.emit("CRITICAL", event, message, payload=payload, **extra)

    def emit(
        self,
        level: str,
        event: str,
        message: str | None = None,
        *,
        payload: Mapping[str, Any] | None = None,
        **extra: Any,
    ) -> StructuredLogRecord | None:
        """Emit a structured log record when severity meets configured threshold."""

        level_name = level.upper()
        severity = _LEVEL_ORDER.get(level_name)
        if severity is None:
            raise ValueError(f"Unknown log level '{level}'")
        if severity < self._threshold:
            return None

        combined_payload: dict[str, Any] = {}
        if payload:
            combined_payload.update(payload)
        if extra:
            combined_payload.update(extra)
        if combined_payload:
            combined_payload = _redact_payload(combined_payload)

        timestamp = self._clock()
        record = StructuredLogRecord(
            timestamp=timestamp,
            run_identifier=self._config.run_identifier,
            level=level_name,
            event=event,
            message=message,
            payload=MappingProxyType(combined_payload),
        )

        if not self._structured_logging_enabled:
            return record

        if self._config.json_mode:
            self._emit_json(record)
        else:
            self._emit_human(record)

        return record

    def _emit_human(self, record: StructuredLogRecord) -> None:
        text = self._format_text(record)
        self._console.print(text)

    def _emit_json(self, record: StructuredLogRecord) -> None:
        stream = self._json_stream
        if stream is None:
            stream = self._console.file
        payload = self._json_dumps(record.to_dict())
        stream.write(f"{payload}\n")
        stream.flush()

    @staticmethod
    def _format_text(record: StructuredLogRecord) -> Text:
        text = Text()
        text.append(record.timestamp.isoformat(), style="dim")
        text.append(" ")
        text.append(record.run_identifier, style="cyan")
        text.append(" ")
        style = _LEVEL_STYLES.get(record.level, "white")
        text.append(record.level, style=style)
        text.append(" ")
        text.append(record.event, style="bold")
        if record.message:
            text.append(" - ")
            text.append(record.message)
        if record.payload:
            text.append(" ")
            text.append(
                json.dumps(dict(record.payload), separators=_JSON_SEPARATORS, sort_keys=True)
            )
        return text


def create_logger(
    config: LogConfiguration,
    *,
    console: Console | None = None,
    json_stream: TextIO | None = None,
    clock: Callable[[], datetime] | None = None,
) -> StructuredLogger:
    """Convenience helper that instantiates :class:`StructuredLogger`."""

    return StructuredLogger(config, console=console, json_stream=json_stream, clock=clock)


__all__ = [
    "StructuredLogRecord",
    "StructuredLogger",
    "create_logger",
    "REDACTED_PLACEHOLDER",
]
