"""Plan file parser producing domain models."""

from __future__ import annotations

import hashlib
import shlex
from datetime import datetime
from pathlib import Path
from typing import List, Sequence
from uuid import UUID

from .model import Change, Plan, PlanEntry, Tag
from sqlitch.utils.time import parse_iso_datetime


class PlanParseError(ValueError):
    """Raised when the plan file contains invalid data."""


def parse_plan(path: Path | str) -> Plan:
    plan_path = Path(path)
    content = plan_path.read_text(encoding="utf-8")
    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

    headers: dict[str, str] = {}
    entries: List[PlanEntry] = []

    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("%"):
            key, value = _parse_header(line, line_no)
            headers[key] = value
            continue

        tokens = shlex.split(line, comments=False, posix=True)
        entry_type, *rest = tokens
        if entry_type == "change":
            entries.append(_parse_change(rest, plan_path.parent, line_no))
        elif entry_type == "tag":
            entries.append(_parse_tag(rest, line_no))
        else:
            raise PlanParseError(f"Unknown plan entry '{entry_type}' on line {line_no}")

    project = headers.get("project")
    default_engine = headers.get("default_engine")
    if not project or not default_engine:
        raise PlanParseError("plan file is missing project header or default engine header")

    return Plan(
        project_name=project,
        file_path=plan_path,
        entries=entries,
        checksum=checksum,
        default_engine=default_engine,
    )


def _parse_header(line: str, line_no: int) -> tuple[str, str]:
    raw = line[1:]
    if "=" not in raw:
        raise PlanParseError(f"Invalid header on line {line_no}: {line}")
    key, value = raw.split("=", 1)
    return key.strip(), value.strip()


def _parse_change(tokens: Sequence[str], base_path: Path, line_no: int) -> Change:
    if len(tokens) < 4:
        raise PlanParseError(f"Change entry on line {line_no} is incomplete")
    name = tokens[0]
    deploy = tokens[1]
    revert = tokens[2]
    remaining = tokens[3:]

    metadata = _parse_metadata(remaining, line_no)

    planner = metadata.get("planner")
    if not planner:
        raise PlanParseError(f"Change entry on line {line_no} requires planner metadata")

    planned_at_str = metadata.get("planned_at")
    planned_at = _parse_timestamp(planned_at_str, line_no, "planned_at")

    verify_path = metadata.get("verify")
    notes = metadata.get("notes")
    depends = _split_csv(metadata.get("depends"))
    tags = _split_csv(metadata.get("tags"))
    change_id = _parse_uuid(metadata.get("change_id"), line_no) if metadata.get("change_id") else None

    script_paths: dict[str, str | None] = {
        "deploy": deploy,
        "revert": revert,
    }
    if verify_path is not None:
        script_paths["verify"] = verify_path

    resolved_paths = {key: (base_path / value if value is not None else None) for key, value in script_paths.items()}

    return Change(
        name=name,
        script_paths=resolved_paths,
        planner=planner,
        planned_at=planned_at,
        notes=notes,
        change_id=change_id,
        dependencies=depends,
        tags=tags,
    )


def _parse_tag(tokens: Sequence[str], line_no: int) -> Tag:
    if len(tokens) < 3:
        raise PlanParseError(f"Tag entry on line {line_no} is incomplete")
    name = tokens[0]
    change_ref = tokens[1]
    metadata = _parse_metadata(tokens[2:], line_no)

    planner = metadata.get("planner")
    if not planner:
        raise PlanParseError(f"Tag entry on line {line_no} requires planner metadata")
    tagged_at = _parse_timestamp(metadata.get("tagged_at"), line_no, "tagged_at")

    return Tag(
        name=name,
        change_ref=change_ref,
        planner=planner,
        tagged_at=tagged_at,
    )


def _parse_metadata(tokens: Sequence[str], line_no: int) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            raise PlanParseError(f"Invalid metadata token '{token}' on line {line_no}")
        key, value = token.split("=", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def _split_csv(value: str | None) -> Sequence[str]:
    if not value:
        return ()
    return tuple(part for part in (piece.strip() for piece in value.split(",")) if part)


def _parse_timestamp(value: str | None, line_no: int, field: str) -> datetime:
    if not value:
        raise PlanParseError(f"Entry on line {line_no} requires {field} metadata")
    try:
        return parse_iso_datetime(value.strip(), label=field, assume_utc_if_naive=True)
    except ValueError as exc:  # pragma: no cover - invalid value reported to caller
        raise PlanParseError(f"Invalid {field} timestamp on line {line_no}") from exc


def _parse_uuid(value: str, line_no: int) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:  # pragma: no cover - invalid value reported to caller
        raise PlanParseError(f"Invalid change_id on line {line_no}") from exc