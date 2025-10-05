"""Unit tests for ``sqlitch.utils.templates``."""

from __future__ import annotations

from pathlib import Path

import pytest

from sqlitch.utils.templates import (
    DEFAULT_TEMPLATE_BODIES,
    default_template_body,
    render_template,
    resolve_template_path,
    write_default_templates,
)


def test_write_default_templates_materialises_engine_templates(tmp_path: Path) -> None:
    """write_default_templates should create the full template tree."""

    destination = tmp_path / "templates"

    created = write_default_templates(destination, "sqlite")

    assert {path.relative_to(destination) for path in created} == {
        Path("deploy/sqlite.tmpl"),
        Path("revert/sqlite.tmpl"),
        Path("verify/sqlite.tmpl"),
    }

    for path in created:
        assert path.read_text(encoding="utf-8") == DEFAULT_TEMPLATE_BODIES[path.parent.name]


def test_write_default_templates_requires_empty_destination(tmp_path: Path) -> None:
    """The destination directory must not already exist."""

    destination = tmp_path / "templates"
    destination.mkdir()

    with pytest.raises(FileExistsError):
        write_default_templates(destination, "pg")


def test_resolve_template_path_prefers_custom_name(tmp_path: Path) -> None:
    """Relative template names should prefer engine directories then bare files."""

    base_a = tmp_path / "base_a"
    base_b = tmp_path / "base_b"
    (base_b / "templates" / "deploy").mkdir(parents=True)
    custom = base_b / "templates" / "deploy" / "custom.tmpl"
    custom.write_text("content", encoding="utf-8")

    result = resolve_template_path(
        kind="deploy",
        engine="sqlite",
        directories=(base_a, base_b),
        template_name="custom",
    )

    assert result == custom


def test_resolve_template_path_handles_absolute_override(tmp_path: Path) -> None:
    """Absolute template names should be returned directly when they exist."""

    absolute = tmp_path / "override.tmpl"
    absolute.write_text("absolute", encoding="utf-8")

    result = resolve_template_path(
        kind="deploy",
        engine="sqlite",
        directories=(),
        template_name=str(absolute),
    )

    assert result == absolute


def test_resolve_template_path_falls_back_to_default(tmp_path: Path) -> None:
    """Engine fallbacks should discover default template names."""

    base = tmp_path / "base"
    default_dir = base / "templates" / "deploy"
    default_dir.mkdir(parents=True)
    default_template = default_dir / "default.tmpl"
    default_template.write_text("default", encoding="utf-8")

    result = resolve_template_path(
        kind="deploy",
        engine="sqlite",
        directories=(base,),
    )

    assert result == default_template


def test_resolve_template_path_returns_none_when_missing(tmp_path: Path) -> None:
    """Missing templates should yield ``None``."""

    base = tmp_path / "empty"
    base.mkdir()

    result = resolve_template_path(
        kind="deploy",
        engine="sqlite",
        directories=(base,),
    )

    assert result is None


def test_render_template_handles_loops_and_tokens() -> None:
    """render_template should expand simple tokens and foreach loops."""

    template = (
        "Hello [% name %]!\n"
        "[% FOREACH item IN requires %]- [% item %]\n[% END %]"
        "Tags: [% tags %]\n"
    )

    rendered = render_template(
        template,
        {
            "name": "SQLitch",
            "requires": ("core:init", "widgets:add"),
            "tags": ("release", "v1"),
        },
    )

    assert "Hello SQLitch!" in rendered
    assert "- core:init" in rendered
    assert "- widgets:add" in rendered
    assert "Tags: release v1" in rendered


def test_render_template_ignores_invalid_loop_collections() -> None:
    """Non-sequence loop values should render as empty segments."""

    template = "[% FOREACH item IN requires %]*[% item %][% END %]"

    rendered = render_template(template, {"requires": None})

    assert rendered == ""


def test_default_template_body_unknown_kind() -> None:
    """Unknown template kinds should raise ValueError."""

    with pytest.raises(ValueError, match="Unknown template kind"):
        default_template_body("invalid")
