"""Utilities for formatting plan files and computing checksums."""

from __future__ import annotations

import hashlib
import os
import shlex
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .model import Change, Plan, PlanEntry, Tag
from sqlitch.utils.time import isoformat_utc

_SHELL_SAFE_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:@+-/,:"
)


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
) -> str:
    """Render a plan file as text without writing it to disk."""

    base_dir = Path(base_path)
    lines = [f"%project={project_name}", f"%default_engine={default_engine}"]
    for entry in entries:
        if isinstance(entry, Change):
            lines.append(_format_change(entry, base_dir))
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
    )
    plan_file.write_text(content, encoding="utf-8")

    checksum = compute_checksum(content)
    return Plan(
        project_name=project_name,
        file_path=plan_file,
        entries=tuple(entries),
        checksum=checksum,
        default_engine=default_engine,
    )


def _format_change(change: Change, base_path: Path) -> str:
    tokens = [
        "change",
        change.name,
        _format_script_path(change.script_paths["deploy"], base_path),
        _format_script_path(change.script_paths["revert"], base_path),
    ]

    verify_path = change.script_paths.get("verify")
    metadata: list[str] = []
    if verify_path is not None:
        metadata.append(_metadata("verify", _format_script_path(verify_path, base_path)))
    metadata.append(_metadata("planner", change.planner))
    metadata.append(_metadata("planned_at", _format_timestamp(change.planned_at)))
    if change.notes:
        metadata.append(_metadata("notes", change.notes))
    if change.dependencies:
        metadata.append(_metadata("depends", ",".join(change.dependencies)))
    if change.tags:
        metadata.append(_metadata("tags", ",".join(change.tags)))
    if change.change_id is not None:
        metadata.append(_metadata("change_id", str(change.change_id)))

    tokens.extend(metadata)
    return " ".join(tokens)


def _format_tag(tag: Tag) -> str:
    tokens = [
        "tag",
        tag.name,
        tag.change_ref,
        _metadata("planner", tag.planner),
        _metadata("tagged_at", _format_timestamp(tag.tagged_at)),
    ]
    return " ".join(tokens)


def _format_timestamp(value: datetime) -> str:
    return isoformat_utc(value, drop_microseconds=True, use_z_suffix=True)


def _format_script_path(value: Path | None, base_path: Path) -> str:
    if value is None:
        return ""
    path = Path(value)
    if path.is_absolute():
        try:
            return path.relative_to(base_path).as_posix()
        except ValueError:
            return os.path.relpath(path, base_path).replace(os.sep, "/")
    return path.as_posix()


def _metadata(key: str, value: str) -> str:
    return f"{key}={_quote_value(value)}"


def _quote_value(value: str) -> str:
    if not value:
        return value
    if set(value).issubset(_SHELL_SAFE_CHARS):
        return value
    return shlex.quote(value)
