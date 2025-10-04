"""Plan file parser producing domain models."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .model import Change, Plan, PlanEntry, Tag
from sqlitch.plan.utils import slugify_change_name
from sqlitch.utils.time import parse_iso_datetime


class PlanParseError(ValueError):
    """Raised when the plan file contains invalid data."""


_CHANGE_PATTERN = re.compile(
    r"""
    ^
    (?P<name>[^\s\[]+)
    (?:\s+\[(?P<deps>[^\]]*)\])?
    \s+(?P<timestamp>\S+)
    \s+(?P<planner>.+?)
    $
    """,
    re.VERBOSE,
)


_TAG_PATTERN = re.compile(
    r"""
    ^
    @(?P<name>\S+)
    \s+(?P<timestamp>\S+)
    \s+(?P<planner>.+?)
    $
    """,
    re.VERBOSE,
)


def parse_plan(path: Path | str, *, default_engine: str | None = None) -> Plan:
    plan_path = Path(path)
    content = plan_path.read_text(encoding="utf-8")
    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

    headers: dict[str, str] = {}
    entries: list[PlanEntry] = []
    last_change: Change | None = None

    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("%"):
            key, value = _parse_header(stripped, line_no)
            headers[key] = value
            continue

        body, note = _split_note(raw_line)
        if not body.strip():
            continue

        if body.lstrip().startswith("@"):
            entry = _parse_tag(body.strip(), note, line_no, last_change)
            entries.append(entry)
            continue

        entry = _parse_change(body.strip(), note, line_no, plan_path.parent)
        entries.append(entry)
        last_change = entry

    project = headers.get("project")
    header_engine = headers.get("default_engine")
    syntax_version = headers.get("syntax-version", "1.0.0")
    uri = headers.get("uri")

    resolved_engine = header_engine or default_engine
    if not project or not resolved_engine:
        raise PlanParseError("plan file is missing project header or default engine header")

    return Plan(
        project_name=project,
        file_path=plan_path,
        entries=entries,
        checksum=checksum,
        default_engine=resolved_engine,
        syntax_version=syntax_version,
        uri=uri,
    )


def _parse_header(line: str, line_no: int) -> tuple[str, str]:
    raw = line[1:]
    if "=" not in raw:
        raise PlanParseError(f"Invalid header on line {line_no}: {line}")
    key, value = raw.split("=", 1)
    return key.strip(), value.strip()


def _parse_change(line: str, note: str | None, line_no: int, base_dir: Path) -> Change:
    match = _CHANGE_PATTERN.match(line)
    if not match:
        raise PlanParseError(f"Invalid change entry on line {line_no}")

    name = match.group("name")
    dependencies = _parse_dependencies(match.group("deps"))
    planned_at = _parse_timestamp(match.group("timestamp"), line_no, "planned_at")
    planner = match.group("planner").strip()

    slug = slugify_change_name(name)
    script_paths = {
        "deploy": base_dir / "deploy" / f"{slug}.sql",
        "revert": base_dir / "revert" / f"{slug}.sql",
        "verify": base_dir / "verify" / f"{slug}.sql",
    }

    return Change.create(
        name=name,
        script_paths=script_paths,
        planner=planner,
        planned_at=planned_at,
        notes=_clean_note(note),
        dependencies=dependencies,
        tags=(),
    )


def _parse_tag(line: str, note: str | None, line_no: int, last_change: Change | None) -> Tag:
    if last_change is None:
        raise PlanParseError(f"Tag on line {line_no} has no preceding change to reference")

    match = _TAG_PATTERN.match(line)
    if not match:
        raise PlanParseError(f"Invalid tag entry on line {line_no}")

    name = match.group("name")
    tagged_at = _parse_timestamp(match.group("timestamp"), line_no, "tagged_at")
    planner = match.group("planner").strip()

    return Tag(
        name=name,
        change_ref=last_change.name,
        planner=planner,
        tagged_at=tagged_at,
        note=_clean_note(note),
    )


def _split_note(raw_line: str) -> tuple[str, str | None]:
    if "#" not in raw_line:
        return raw_line.rstrip(), None
    body, note = raw_line.split("#", 1)
    return body.rstrip(), note.strip() or None


def _clean_note(note: str | None) -> str | None:
    if not note:
        return None
    cleaned = note.strip()
    return cleaned or None


def _parse_dependencies(raw: str | None) -> Sequence[str]:
    if raw is None:
        return ()
    parts = [value.strip() for value in raw.split() if value.strip()]
    return tuple(parts)


def _parse_timestamp(value: str | None, line_no: int, field: str) -> datetime:
    if not value:
        raise PlanParseError(f"Entry on line {line_no} requires {field} metadata")
    try:
        return parse_iso_datetime(value.strip(), label=field, assume_utc_if_naive=True)
    except ValueError as exc:  # pragma: no cover - invalid value reported to caller
        raise PlanParseError(f"Invalid {field} timestamp on line {line_no}") from exc
