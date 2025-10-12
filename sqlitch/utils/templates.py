"""Template resolution and rendering helpers for SQLitch."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

__all__ = [
    "DEFAULT_TEMPLATE_BODIES",
    "default_template_body",
    "resolve_template_path",
    "render_template",
    "write_default_templates",
]

DEFAULT_TEMPLATE_BODIES: dict[str, str] = {
    "deploy": (
        "-- Deploy [% project %]:[% change %] to [% engine %]\n"
        "[% FOREACH item IN requires -%]\n"
        "-- requires: [% item %]\n"
        "[% END -%]\n"
        "[% FOREACH item IN conflicts -%]\n"
        "-- conflicts: [% item %]\n"
        "[% END -%]\n\n"
        "BEGIN;\n\n"
        "-- XXX Add DDLs here.\n\n"
        "COMMIT;\n"
    ),
    "revert": (
        "-- Revert [% project %]:[% change %] from [% engine %]\n\n"
        "BEGIN;\n\n"
        "-- XXX Add DDLs here.\n\n"
        "COMMIT;\n"
    ),
    "verify": (
        "-- Verify [% project %]:[% change %] on [% engine %]\n\n"
        "BEGIN;\n\n"
        "-- XXX Add verifications here.\n\n"
        "ROLLBACK;\n"
    ),
}

_FOREACH_PATTERN = re.compile(
    r"\[\%\s*FOREACH\s+(?P<name>\w+)\s+IN\s+(?P<collection>\w+)\s*-?%\]"
    r"(?P<body>.*?)\[\%\s*END\s*-?%\]",
    re.DOTALL,
)
_SIMPLE_TOKEN_PATTERN = re.compile(r"\[\%\s*(?P<name>\w+)\s*%\]")


def default_template_body(kind: str) -> str:
    """Return the default template body for ``kind``."""

    try:
        return DEFAULT_TEMPLATE_BODIES[kind]
    except KeyError as exc:  # pragma: no cover - defensive programming
        raise ValueError(f"Unknown template kind: {kind!r}") from exc


def write_default_templates(destination_root: Path, engine: str) -> tuple[Path, ...]:
    """Materialise default template files for ``engine`` under ``destination_root``."""

    root = Path(destination_root)
    root.mkdir(parents=True, exist_ok=False)

    created: list[Path] = []
    for kind, body in DEFAULT_TEMPLATE_BODIES.items():
        target_dir = root / kind
        target_dir.mkdir(parents=True, exist_ok=False)
        template_path = target_dir / f"{engine}.tmpl"
        template_path.write_text(body, encoding="utf-8")
        created.append(template_path)
    return tuple(created)


def resolve_template_path(
    *,
    kind: str,
    engine: str,
    directories: Sequence[Path],
    template_name: str | None = None,
) -> Path | None:
    """Return the first template path discovered in ``directories``.

    The search honours the provided directory order. When ``template_name`` is
    supplied, it is treated as a relative path beneath each templates directory
    (``.tmpl`` suffix added automatically when omitted). Otherwise the function
    searches for engine-specific files such as ``deploy/sqlite.tmpl`` followed by
    more generic fallbacks.
    """

    name_path: Path | None = None
    if template_name:
        candidate = Path(template_name)
        if candidate.is_absolute():
            return candidate if candidate.exists() else None
        name_path = candidate if candidate.suffix else candidate.with_suffix(".tmpl")

    relative_candidates: tuple[Path, ...]
    if name_path is not None:
        if name_path.parent == Path("."):
            relative_candidates = (
                Path(kind) / name_path,
                name_path,
            )
        else:
            relative_candidates = (name_path,)
    else:
        relative_candidates = (
            Path(kind) / f"{engine}.tmpl",
            Path(kind) / "default.tmpl",
            Path(f"{kind}-{engine}.tmpl"),
            Path(f"{kind}.tmpl"),
        )

    for directory in directories:
        base = Path(directory)
        if not base:
            continue
        for template_dir in _template_dir_candidates(base):
            for candidate in relative_candidates:
                template_path = template_dir / candidate
                if template_path.exists():
                    return template_path
    return None


def render_template(template_text: str, context: Mapping[str, object]) -> str:
    """Render ``template_text`` using a minimal subset of Template Toolkit."""

    rendered = template_text.replace("\r\n", "\n")

    def _render_loop(match: re.Match[str]) -> str:
        iterator_name = match.group("name")
        collection_name = match.group("collection")
        body = match.group("body")
        values = context.get(collection_name)
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            return ""

        parts: list[str] = []
        for value in values:
            segment = body
            segment = segment.replace(f"[% {iterator_name} %]", str(value))
            parts.append(segment)
        return "".join(parts)

    rendered = _FOREACH_PATTERN.sub(_render_loop, rendered)

    def _replace_token(match: re.Match[str]) -> str:
        token = match.group("name")
        value = context.get(token)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return " ".join(str(item) for item in value)
        if value is None:
            return ""
        return str(value)

    rendered = _SIMPLE_TOKEN_PATTERN.sub(_replace_token, rendered)
    return rendered


def _template_dir_candidates(base: Path) -> tuple[Path, ...]:
    """Return candidate directories under ``base`` that may contain templates."""

    candidates = (
        base / "templates",
        base / "etc" / "templates",
    )
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique.append(candidate)
    return tuple(unique)
