"""Timezone and timestamp helper utilities."""

from __future__ import annotations

from datetime import datetime, timezone

__all__ = [
    "ensure_timezone",
    "coerce_datetime",
    "coerce_optional_datetime",
    "parse_iso_datetime",
    "isoformat_utc",
]


def ensure_timezone(value: datetime, label: str) -> datetime:
    """Ensure the provided datetime is timezone-aware and normalized to UTC."""

    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value.astimezone(timezone.utc)


def parse_iso_datetime(value: str, *, label: str, assume_utc_if_naive: bool = False) -> datetime:
    """Parse an ISO-8601 timestamp, normalizing to UTC.

    When ``assume_utc_if_naive`` is ``True``, timestamps lacking timezone
    information are assumed to be in UTC. Otherwise, a naive timestamp will
    raise ``ValueError`` to signal the caller that timezone metadata is required.
    """

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:  # pragma: no cover - invalid value reported to caller
        raise ValueError(f"Invalid ISO timestamp for {label}: {value}") from exc
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        if assume_utc_if_naive:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            raise ValueError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def coerce_datetime(value: datetime | str, label: str) -> datetime:
    """Coerce a datetime or ISO string into a timezone-aware UTC datetime."""

    if isinstance(value, datetime):
        return ensure_timezone(value, label)
    if isinstance(value, str):
        return parse_iso_datetime(value, label=label)
    raise TypeError(f"{label} must be datetime or ISO string")


def coerce_optional_datetime(value: datetime | str | None, label: str) -> datetime | None:
    """Coerce optional datetime-like values into timezone-aware UTC datetimes."""

    if value is None:
        return None
    return coerce_datetime(value, label)


def isoformat_utc(
    value: datetime,
    *,
    drop_microseconds: bool = False,
    use_z_suffix: bool = False,
    label: str | None = None,
) -> str:
    """Render a timezone-aware datetime as an ISO string in UTC.

    ``drop_microseconds`` will truncate sub-second precision. ``use_z_suffix``
    toggles whether ``+00:00`` should be rendered as ``Z`` for plan files.
    """

    normalized = ensure_timezone(value, label or "value")
    if drop_microseconds:
        normalized = normalized.replace(microsecond=0)
    rendered = normalized.isoformat()
    if use_z_suffix:
        rendered = rendered.replace("+00:00", "Z")
    return rendered
