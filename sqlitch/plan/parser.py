"""Plan file parser producing domain models."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import re
import shlex
from datetime import datetime
from pathlib import Path
from uuid import UUID

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
    change_tags: dict[str, list[str]] = {}
    last_change: Change | None = None

    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("%"):
            key, value = _parse_header(line, line_no)
            headers[key] = value
            continue

        tokens = shlex.split(line, comments=False, posix=True)
        entry: PlanEntry
        if not tokens:
            continue
        entry_type, *rest = tokens
        if entry_type == "change":
            entry = _parse_change(rest, plan_path.parent, line_no)
        elif entry_type == "tag":
            entry = _parse_tag(rest, line_no)
        else:
            entry = _parse_compact_entry(raw_line, plan_path.parent, line_no, last_change)

        entries.append(entry)
        if isinstance(entry, Change):
            last_change = entry
        elif isinstance(entry, Tag):
            change_tags.setdefault(entry.change_ref, []).append(entry.name)

    project = headers.get("project")
    header_engine = headers.get("default_engine")
    syntax_version = headers.get("syntax-version", "1.0.0")
    uri = headers.get("uri")

    resolved_engine = header_engine or default_engine
    if not project or not resolved_engine:
        raise PlanParseError("plan file is missing project header or default engine header")

    adjusted_entries = _apply_rework_metadata(
        entries=tuple(entries),
        change_tags=change_tags,
        base_dir=plan_path.parent,
    )

    return Plan(
        project_name=project,
        file_path=plan_path,
        entries=adjusted_entries,
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
    change_id = (
        _parse_uuid(metadata.get("change_id"), line_no) if metadata.get("change_id") else None
    )

    script_paths: dict[str, str | None] = {
        "deploy": deploy,
        "revert": revert,
    }
    if verify_path is not None:
        script_paths["verify"] = verify_path

    resolved_paths = {
        key: (base_path / value if value is not None else None)
        for key, value in script_paths.items()
    }

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


def _parse_compact_entry(
    raw_line: str,
    base_dir: Path,
    line_no: int,
    last_change: Change | None,
) -> PlanEntry:
    body, note = _split_note(raw_line)
    entry = body.strip()
    if not entry:
        raise PlanParseError(f"Invalid plan entry on line {line_no}")

    if entry.startswith("@"):
        return _parse_compact_tag(entry, note, line_no, last_change)
    try:
        return _parse_compact_change(entry, note, line_no, base_dir)
    except PlanParseError as exc:
        message = str(exc)
        if message.startswith("Invalid change entry"):
            raise ValueError(f"Unknown plan entry '{entry}'") from None
        raise


def _parse_compact_change(line: str, note: str | None, line_no: int, base_dir: Path) -> Change:
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


def _apply_rework_metadata(
    *,
    entries: Sequence[PlanEntry],
    change_tags: dict[str, list[str]],
    base_dir: Path,
) -> tuple[PlanEntry, ...]:
    """Attach tag metadata and reworked script paths to change entries."""

    adjusted: list[PlanEntry] = []
    for entry in entries:
        if not isinstance(entry, Change):
            adjusted.append(entry)
            continue

        tags = tuple(change_tags.get(entry.name, ()))
        script_paths = dict(entry.script_paths)
        if tags:
            script_paths = _resolve_reworked_script_paths(
                change_name=entry.name,
                script_paths=script_paths,
                tags=tags,
                base_dir=base_dir,
            )

        adjusted.append(
            Change.create(
                name=entry.name,
                script_paths=script_paths,
                planner=entry.planner,
                planned_at=entry.planned_at,
                notes=entry.notes,
                change_id=entry.change_id,
                dependencies=entry.dependencies,
                tags=tags or entry.tags,
            )
        )

    return tuple(adjusted)


def _resolve_reworked_script_paths(
    *,
    change_name: str,
    script_paths: dict[str, Path | None],
    tags: Sequence[str],
    base_dir: Path,
) -> dict[str, Path | None]:
    """Compute script paths for reworked changes preferring ``@tag`` suffixes."""

    if not tags:
        return script_paths

    slug = slugify_change_name(change_name)
    suffixes = [f"@{tag}" for tag in tags]

    resolved: dict[str, Path | None] = {}
    for kind, original in script_paths.items():
        if original is None:
            resolved[kind] = None
            continue

        original_path = original if original.is_absolute() else base_dir / original
        parent = original_path.parent
        extension = original_path.suffix

        selected: Path | None = None
        for suffix in reversed(suffixes):
            candidate = parent / f"{slug}{suffix}{extension}"
            if candidate.exists():
                selected = candidate
                break

        resolved[kind] = selected or original_path

    return resolved


def _parse_compact_tag(
    line: str, note: str | None, line_no: int, last_change: Change | None
) -> Tag:
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
