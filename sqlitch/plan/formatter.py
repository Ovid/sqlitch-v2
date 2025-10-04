"""Utilities for formatting plan files and computing checksums."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .model import Change, Plan, PlanEntry, Tag
from sqlitch.utils.time import isoformat_utc


def compute_checksum(content: str) -> str:
    """Return the SHA-256 checksum for the provided content."""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def format_plan(
    *,
    project_name: str,
    default_engine: str,
    entries: Sequence[PlanEntry],
    base_path: Path | str,
    newline: str = "\n",
    syntax_version: str = "1.0.0",
    uri: str | None = None,
) -> str:
    """Render a plan file as text without writing it to disk."""

    header_lines = [f"%syntax-version={syntax_version}", f"%project={project_name}"]
    if uri:
        header_lines.append(f"%uri={uri}")

    lines: list[str] = [*header_lines, ""]
    for entry in entries:
        if isinstance(entry, Change):
            lines.append(_format_change(entry))
        elif isinstance(entry, Tag):
            lines.append(_format_tag(entry))
        else:  # pragma: no cover - defensive, Plan enforces entry types
            raise TypeError(f"Unsupported plan entry type: {type(entry)!r}")
    return newline.join(lines) + newline


def write_plan(
    *,
    project_name: str,
    default_engine: str,
    entries: Sequence[PlanEntry],
    plan_path: Path | str,
    newline: str = "\n",
    syntax_version: str = "1.0.0",
    uri: str | None = None,
) -> Plan:
    """Write a plan file to disk and return the corresponding :class:`Plan`."""

    plan_file = Path(plan_path)
    plan_file.parent.mkdir(parents=True, exist_ok=True)

    content = format_plan(
        project_name=project_name,
        default_engine=default_engine,
        entries=entries,
        base_path=plan_file.parent,
        newline=newline,
        syntax_version=syntax_version,
        uri=uri,
    )
    plan_file.write_text(content, encoding="utf-8")

    checksum = compute_checksum(content)
    return Plan(
        project_name=project_name,
        file_path=plan_file,
        entries=tuple(entries),
        checksum=checksum,
        default_engine=default_engine,
        syntax_version=syntax_version,
        uri=uri,
    )


def _format_change(change: Change) -> str:
    parts = [change.name]
    if change.dependencies:
        parts.append(f"[{ ' '.join(change.dependencies) }]")
    parts.append(_format_timestamp(change.planned_at))
    parts.append(change.planner)
    line = " ".join(parts)
    if change.notes:
        line = f"{line} # {change.notes}"
    return line


def _format_tag(tag: Tag) -> str:
    parts = [f"@{tag.name}", _format_timestamp(tag.tagged_at), tag.planner]
    line = " ".join(parts)
    if tag.note:
        line = f"{line} # {tag.note}"
    return line


def _format_timestamp(value: datetime) -> str:
    return isoformat_utc(value, drop_microseconds=True, use_z_suffix=True)
