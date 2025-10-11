from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sqlitch.utils.time import (
    coerce_datetime,
    coerce_optional_datetime,
    ensure_timezone,
    format_registry_timestamp,
    isoformat_utc,
    parse_iso_datetime,
)


def test_ensure_timezone_converts_to_utc() -> None:
    value = datetime(2025, 1, 1, 7, 45, tzinfo=timezone(timedelta(hours=-5)))

    normalized = ensure_timezone(value, "planned_at")

    assert normalized.tzinfo == timezone.utc
    assert normalized.hour == 12
    assert normalized.minute == 45


def test_ensure_timezone_rejects_naive_values() -> None:
    naive = datetime(2025, 1, 1, 7, 45)

    with pytest.raises(ValueError, match="planned_at must be timezone-aware"):
        ensure_timezone(naive, "planned_at")


def test_coerce_datetime_accepts_iso_strings() -> None:
    result = coerce_datetime("2025-01-01T08:30:00-05:00", "deployed_at")

    assert result.tzinfo == timezone.utc
    assert result.hour == 13
    assert result.minute == 30


def test_coerce_datetime_rejects_naive_strings() -> None:
    with pytest.raises(ValueError, match="deployed_at must be timezone-aware"):
        coerce_datetime("2025-01-01T08:30:00", "deployed_at")


def test_coerce_optional_datetime_handles_none() -> None:
    assert coerce_optional_datetime(None, "optional") is None


def test_parse_iso_datetime_supports_z_suffix() -> None:
    result = parse_iso_datetime("2025-01-01T12:00:00Z", label="planned_at")

    assert result == datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_parse_iso_datetime_assumes_utc_when_requested() -> None:
    result = parse_iso_datetime(
        "2025-01-01T12:00:00",
        label="planned_at",
        assume_utc_if_naive=True,
    )

    assert result == datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_parse_iso_datetime_rejects_naive_without_assumption() -> None:
    with pytest.raises(ValueError, match="planned_at must be timezone-aware"):
        parse_iso_datetime("2025-01-01T12:00:00", label="planned_at")


def test_isoformat_utc_normalizes_offsets() -> None:
    value = datetime(2025, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=5, minutes=45)))

    rendered = isoformat_utc(value, drop_microseconds=True, use_z_suffix=True, label="timestamp")

    assert rendered == "2025-01-01T06:15:00Z"


def test_isoformat_utc_retains_microseconds_when_requested() -> None:
    value = datetime(2025, 1, 1, 12, 0, 1, 123456, tzinfo=timezone.utc)

    rendered = isoformat_utc(value, drop_microseconds=False, use_z_suffix=False)

    assert rendered == "2025-01-01T12:00:01.123456+00:00"


def test_format_registry_timestamp_trims_trailing_microseconds() -> None:
    value = datetime(2025, 1, 1, 12, 0, 1, 123400, tzinfo=timezone.utc)

    rendered = format_registry_timestamp(value)

    assert rendered == "2025-01-01 12:00:01.1234"


def test_format_registry_timestamp_drops_decimal_when_zero_microseconds() -> None:
    value = datetime(2025, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=-5)))

    rendered = format_registry_timestamp(value)

    # Normalized to UTC, no fractional seconds
    assert rendered == "2025-01-01 17:00:00"
