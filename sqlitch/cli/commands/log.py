"""Implementation of the ``sqlitch log`` command."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Sequence

import click

from sqlitch.engine import EngineTarget, create_engine
from sqlitch.engine.base import UnsupportedEngineError

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import require_cli_context
from .status import _resolve_registry_target

__all__ = ["log_command"]


@dataclass(frozen=True, slots=True)
class LogEvent:
    """Represents a registry event emitted for log output."""

    event: str
    change_id: str
    change: str
    project: str
    note: str
    tags: tuple[str, ...]
    committed_at: str
    committer_name: str
    committer_email: str


@click.command("log")
@click.argument("target_args", nargs=-1)
@click.option("--target", "target_option", help="Deployment target URI or database path.")
@click.option("--limit", type=int, default=None, help="Limit the number of events returned.")
@click.option(
    "--skip", type=int, default=0, help="Skip the first N events before rendering output."
)
@click.option(
    "--reverse", is_flag=True, help="Return events in chronological order (oldest first)."
)
@click.option("--project", "project_filter", help="Filter events to the specified project name.")
@click.option(
    "--format", "output_format", default="human", help="Select output format: human or json."
)
@click.option("--change", "change_filter", help="Filter events by change name.")
@click.option(
    "--event",
    "event_filter",
    type=click.Choice(("deploy", "deploy_fail", "revert", "fail", "merge"), case_sensitive=False),
    help="Filter events by event type.",
)
@global_sqitch_options
@global_output_options
@click.pass_context
def log_command(
    ctx: click.Context,
    *,
    target_args: tuple[str, ...],
    target_option: str | None,
    limit: int | None,
    skip: int,
    reverse: bool,
    project_filter: str | None,
    output_format: str,
    change_filter: str | None,
    event_filter: str | None,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Render deployment history for the requested target.

    Parameters
    ----------
    ctx : click.Context
        Invocation context provided by Click. Must contain a prepared
        :class:`~sqlitch.cli.main.CLIContext` instance.
    target_option : str | None
        Explicit ``--target`` value supplied on the command line.
    limit : int | None
        Maximum number of events to display. ``None`` means all events.
    skip : int
        Number of events to skip before displaying output.
    reverse : bool
        When ``True``, render events in chronological order instead of
        reverse-chronological.
    project_filter : str | None
        Optional project name filter.
    output_format : str
        Desired output format (``human`` or ``json``). Case-insensitive.
    change_filter : str | None
        Optional change name filter.
    event_filter : str | None
        Optional event type filter.

    Raises
    ------
    CommandError
        If validation fails, the target cannot be resolved, or the registry
        query encounters an error.
    """

    cli_context = require_cli_context(ctx)

    if limit is not None and limit < 0:
        raise CommandError("--limit must be zero or a positive integer")
    if skip < 0:
        raise CommandError("--skip must be zero or a positive integer")

    normalized_format = output_format.lower()
    if normalized_format not in {"human", "json"}:
        raise CommandError(f'Unknown format "{output_format}"')

    # Resolve target from positional args, --target option, or config
    target_value = None
    if target_args:
        if len(target_args) > 1:
            raise CommandError("Only one target may be specified")
        target_value = target_args[0]
    elif target_option:
        target_value = target_option
    else:
        target_value = cli_context.target

    if not target_value:
        raise CommandError("A target must be provided via --target or configuration.")

    default_engine = cli_context.engine or "sqlite"
    engine_target, display_target = _resolve_registry_target(
        target_value,
        cli_context.project_root,
        default_engine,
        registry_override=cli_context.registry,
    )

    records = _load_log_events(
        engine_target,
        limit=limit,
        skip=skip,
        reverse=reverse,
        project_filter=project_filter,
        change_filter=change_filter,
        event_filter=event_filter.lower() if event_filter else None,
    )

    if normalized_format == "json":
        payload = _format_json(records)
        click.echo(payload)
        return

    text = _format_human(display_target, records)
    click.echo(text, nl=False)


def _load_log_events(
    engine_target: EngineTarget,
    *,
    limit: int | None,
    skip: int,
    reverse: bool,
    project_filter: str | None,
    change_filter: str | None,
    event_filter: str | None,
) -> tuple[LogEvent, ...]:
    try:
        engine = create_engine(engine_target)
    except UnsupportedEngineError as exc:  # pragma: no cover - delegated to create_engine tests
        raise CommandError(f"Unsupported engine '{engine_target.engine}': {exc}") from exc

    try:
        connection = engine.connect_registry()
    except Exception as exc:  # pragma: no cover - connection failures propagated to users
        raise CommandError(
            f"Failed to connect to registry target {engine_target.registry_uri}: {exc}"
        ) from exc

    cursor = None
    try:
        cursor = connection.cursor()
        query, params = _build_query(
            limit=limit,
            skip=skip,
            reverse=reverse,
            project_filter=project_filter,
            change_filter=change_filter,
            event_filter=event_filter,
        )
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [column[0] for column in (cursor.description or [])]
    except Exception as exc:  # pragma: no cover - query failures propagated to the user
        raise CommandError(
            f"Failed to read registry database {engine_target.registry_uri}: {exc}"
        ) from exc
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:  # pragma: no cover - best effort cleanup
                pass
        try:
            connection.close()
        except Exception:  # pragma: no cover - best effort cleanup
            pass

    if not rows:
        return ()

    def _row_mapping(row: object) -> dict[str, object]:
        if isinstance(row, dict):
            return row
        if not columns:
            raise CommandError(
                f"Registry query for {engine_target.registry_uri} returned no column metadata"
            )
        if isinstance(row, Sequence):
            return {columns[index]: row[index] for index in range(min(len(columns), len(row)))}
        raise CommandError(
            f"Registry query for {engine_target.registry_uri} returned unexpected row format"
        )

    events: list[LogEvent] = []
    for raw in rows:
        mapping = _row_mapping(raw)
        events.append(
            LogEvent(
                event=str(mapping.get("event", "")),
                change_id=str(mapping.get("change_id", "")),
                change=str(mapping.get("change", "")),
                project=str(mapping.get("project", "")),
                note=str(mapping.get("note", "")),
                tags=_normalize_tags(mapping.get("tags")),
                committed_at=str(mapping.get("committed_at", "")),
                committer_name=str(mapping.get("committer_name", "")),
                committer_email=str(mapping.get("committer_email", "")),
            )
        )

    return tuple(events)


def _build_query(
    *,
    limit: int | None,
    skip: int,
    reverse: bool,
    project_filter: str | None,
    change_filter: str | None,
    event_filter: str | None,
) -> tuple[str, tuple[object, ...]]:
    clauses: list[str] = []
    params: list[object] = []

    if project_filter:
        clauses.append("project = ?")
        params.append(project_filter)
    if change_filter:
        clauses.append("change = ?")
        params.append(change_filter)
    if event_filter:
        clauses.append("lower(event) = ?")
        params.append(event_filter.lower())

    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    order_sql = "ASC" if reverse else "DESC"

    base_query = (
        "SELECT event, change_id, change, project, note, tags, committed_at, "
        "committer_name, committer_email FROM events"
    )
    sql = f"{base_query}{where_sql} ORDER BY committed_at {order_sql}, change_id {order_sql}"

    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
        if skip:
            sql += " OFFSET ?"
            params.append(skip)
    elif skip:
        sql += " LIMIT -1 OFFSET ?"
        params.append(skip)

    return sql, tuple(params)


def _normalize_tags(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item))
    text = str(value).strip()
    if not text:
        return ()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    parts = [part.strip() for part in text.split(",") if part.strip()]
    normalized: list[str] = []
    for part in parts:
        stripped = part.strip().strip("'").strip('"')
        if stripped:
            normalized.append(stripped)
    return tuple(normalized)


def _format_human(target: str, events: Sequence[LogEvent]) -> str:
    lines = [f"On database {target}"]

    if not events:
        lines.append("No events found.")
        return "\n".join(lines) + "\n"

    for index, event in enumerate(events):
        lines.append(f"{event.event.capitalize()} {event.change_id}")
        lines.append(f"Name:      {event.change}")
        lines.append(f"Committer: {event.committer_name} <{event.committer_email}>")
        lines.append(f"Date:      {event.committed_at}")
        if index == 0:
            lines.append("")

        note_lines = event.note.splitlines() or [""]
        for note_line in note_lines:
            lines.append(f"    {note_line}" if note_line else "")
        lines.append("")

    return "\n".join(lines) + "\n"


def _format_json(events: Sequence[LogEvent]) -> str:
    payload = [
        {
            "event": event.event,
            "change_id": event.change_id,
            "change": event.change,
            "project": event.project,
            "note": event.note,
            "tags": list(event.tags),
            "committed_at": event.committed_at,
            "committer": {
                "name": event.committer_name,
                "email": event.committer_email,
            },
        }
        for event in events
    ]
    return json.dumps(payload, indent=2, sort_keys=False)


@register_command("log")
def _register_log(group: click.Group) -> None:
    """Attach the log command to the root Click group.

    Parameters
    ----------
    group : click.Group
        Root command group managing SQLitch subcommands.
    """

    group.add_command(log_command)
