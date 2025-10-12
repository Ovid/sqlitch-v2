from __future__ import annotations

from datetime import UTC, datetime, timezone
from pathlib import Path

import pytest

from sqlitch.plan import model


def _make_change(**overrides):
    defaults: dict[str, object] = {
        "name": "widgets:add",
        "script_paths": {
            "deploy": Path("deploy/widgets.sql"),
            "revert": Path("revert/widgets.sql"),
            "verify": Path("verify/widgets.sql"),
        },
        "dependencies": ["core:init"],
        "tags": ["v1.0"],
        "planner": "alice@example.com",
        "planned_at": datetime(2025, 10, 3, 12, 34, 56, tzinfo=timezone.utc),
        "notes": "Add widgets table.",
    }
    defaults.update(overrides)
    return model.Change(**defaults)  # type: ignore[arg-type]


def _make_tag(**overrides) -> model.Tag:
    defaults: dict[str, object] = {
        "name": "v1.0",
        "change_ref": "widgets:add",
        "planner": "alice@example.com",
        "tagged_at": datetime(2025, 10, 3, 12, 34, 56, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return model.Tag(**defaults)  # type: ignore[arg-type]


def test_change_requires_deploy_and_revert_scripts():
    with pytest.raises(ValueError, match=r"script_paths\['deploy'\] is required"):
        _make_change(script_paths={"revert": Path("revert.sql")})

    with pytest.raises(ValueError, match=r"script_paths\['revert'\] is required"):
        _make_change(script_paths={"deploy": Path("deploy.sql")})


def test_change_accepts_optional_verify_script():
    change = _make_change(script_paths={"deploy": Path("deploy.sql"), "revert": Path("revert.sql")})
    assert change.script_paths["verify"] is None


def test_change_normalizes_string_script_paths():
    change = _make_change(
        script_paths={
            "deploy": "deploy/widgets.sql",
            "revert": "revert/widgets.sql",
            "verify": "verify/widgets.sql",
        }
    )

    assert isinstance(change.script_paths["deploy"], Path)
    assert isinstance(change.script_paths["revert"], Path)
    assert isinstance(change.script_paths["verify"], Path)


def test_change_factory_applies_normalization():
    change = model.Change.create(
        name="widgets:add",
        script_paths={"deploy": "deploy/widgets.sql", "revert": "revert/widgets.sql"},
        planner="alice@example.com",
        planned_at=datetime(2025, 10, 3, 12, 34, 56, tzinfo=timezone.utc),
        dependencies=["core:init"],
        tags=["v1.0"],
    )

    assert isinstance(change, model.Change)
    assert change.script_paths["deploy"].name == "widgets.sql"
    assert change.dependencies == ("core:init",)
    assert change.tags == ("v1.0",)
    assert change.change_id is None


def test_change_rejects_duplicate_dependencies():
    with pytest.raises(ValueError, match=r"dependencies contains duplicates"):
        _make_change(dependencies=["core:init", "core:init"])


def test_change_rejects_invalid_change_id_type():
    with pytest.raises(ValueError, match="UUID"):
        _make_change(change_id="not-a-uuid")


def test_plan_rejects_tags_without_change():
    change = _make_change(name="widgets:add", dependencies=[])
    orphan_tag = _make_tag(change_ref="unknown")

    with pytest.raises(ValueError, match="references unknown change"):
        model.Plan(
            project_name="widgets",
            file_path=Path("plan"),
            entries=[change, orphan_tag],
            checksum="abc123",
            default_engine="pg",
        )


def test_plan_exposes_changes_and_tags():
    change = _make_change(name="widgets:add", dependencies=[])
    tag = _make_tag()

    plan = model.Plan(
        project_name="widgets",
        file_path=Path("plan"),
        entries=[change, tag],
        checksum="abc123",
        default_engine="pg",
    )

    assert plan.changes == (change,)
    assert plan.tags == (tag,)


def test_plan_allows_duplicate_change_names_for_rework():
    """Test that Plans allow duplicate change names (reworked changes)."""
    change = _make_change(name="widgets:add", dependencies=[])
    rework = _make_change(name="widgets:add", dependencies=["widgets:add@v1.0"])

    # Should not raise - reworked changes are allowed
    plan = model.Plan(
        project_name="widgets",
        file_path=Path("plan"),
        entries=[change, rework],
        checksum="abc123",
        default_engine="pg",
    )

    # Verify both versions are preserved
    assert len(plan.changes) == 2
    assert plan.get_latest_version("widgets:add") == rework
    assert plan.get_all_versions("widgets:add") == (change, rework)
    assert plan.is_reworked("widgets:add") is True


def test_plan_rejects_dependency_defined_after_change():
    first = _make_change(name="widgets:add", dependencies=[])
    second = _make_change(name="widgets:index", dependencies=["widgets:add"])
    third = _make_change(name="widgets:cleanup", dependencies=["widgets:index"])

    plan = model.Plan(
        project_name="widgets",
        file_path=Path("plan"),
        entries=[second, first, third],
        checksum="abc123",
        default_engine="pg",
    )

    assert plan.entries[0] is second
    assert plan.entries[1] is first
    assert plan.entries[2] is third
    assert plan.missing_dependencies == (
        "widgets:index->widgets:add",
        "widgets:cleanup->widgets:index",
    )


def test_change_preserves_missing_change_id():
    change = _make_change()

    assert change.change_id is None


def test_change_script_paths_are_immutable():
    change = _make_change()

    with pytest.raises(TypeError):
        change.script_paths["deploy"] = Path("other.sql")


def test_change_requires_timezone_aware_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        _make_change(planned_at=datetime(2025, 10, 3, 12, 34, 56))


def test_tag_requires_timezone_aware_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        _make_tag(tagged_at=datetime(2025, 10, 3, 12, 34, 56))


def test_plan_lookup_helpers():
    change = _make_change(name="widgets:add", dependencies=[])
    tag = _make_tag()
    plan = model.Plan(
        project_name="widgets",
        file_path="plan",
        entries=[change, tag],
        checksum="abc123",
        default_engine="pg",
    )

    assert plan.get_change("widgets:add") is change
    assert plan.has_change("widgets:add") is True
    assert plan.has_change("widgets:missing") is False
    assert list(plan.iter_changes()) == [change]
    with pytest.raises(KeyError):
        plan.get_change("unknown")


def test_plan_rejects_non_plan_entries():
    change = _make_change(name="widgets:add", dependencies=[])
    with pytest.raises(TypeError, match="Plan.entries must contain Change or Tag"):
        model.Plan(
            project_name="widgets",
            file_path=Path("plan"),
            entries=[change, object()],
            checksum="abc123",
            default_engine="pg",
        )


def test_tag_requires_non_empty_fields():
    with pytest.raises(ValueError, match="Tag.name is required"):
        _make_tag(name="")
    with pytest.raises(ValueError, match="Tag.change_ref is required"):
        _make_tag(change_ref="")
    with pytest.raises(ValueError, match="Tag.planner is required"):
        _make_tag(planner="")


def test_change_is_rework_returns_true_when_rework_of_is_set():
    """Verify is_rework returns True when rework_of is populated."""
    change = model.Change.create(
        name="test_change",
        script_paths={
            "deploy": Path("deploy/test_change.sql"),
            "revert": Path("revert/test_change.sql"),
            "verify": None,
        },
        planner="Test User <test@example.com>",
        planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        dependencies=tuple(),
        notes=None,
        rework_of="test_change@v1.0.0",
    )
    assert change.is_rework() is True


def test_change_is_rework_returns_true_when_self_referencing_dependency():
    """Verify is_rework returns True when dependencies reference self with tag."""
    change = model.Change.create(
        name="test_change",
        script_paths={
            "deploy": Path("deploy/test_change.sql"),
            "revert": Path("revert/test_change.sql"),
            "verify": None,
        },
        planner="Test User <test@example.com>",
        planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        dependencies=("test_change@v1.0.0",),
        notes=None,
        rework_of=None,
    )
    assert change.is_rework() is True


def test_change_is_rework_returns_false_for_normal_change():
    """Verify is_rework returns False for non-reworked changes."""
    change = model.Change.create(
        name="test_change",
        script_paths={
            "deploy": Path("deploy/test_change.sql"),
            "revert": Path("revert/test_change.sql"),
            "verify": None,
        },
        planner="Test User <test@example.com>",
        planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        dependencies=tuple(),
        notes=None,
        rework_of=None,
    )
    assert change.is_rework() is False


def test_change_get_rework_tag_from_rework_of_field():
    """Verify get_rework_tag extracts tag from rework_of field."""
    change = model.Change.create(
        name="test_change",
        script_paths={
            "deploy": Path("deploy/test_change.sql"),
            "revert": Path("revert/test_change.sql"),
            "verify": None,
        },
        planner="Test User <test@example.com>",
        planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        dependencies=tuple(),
        notes=None,
        rework_of="test_change@v1.0.0",
    )
    assert change.get_rework_tag() == "v1.0.0"


def test_change_get_rework_tag_from_self_dependency():
    """Verify get_rework_tag extracts tag from self-referencing dependency."""
    change = model.Change.create(
        name="test_change",
        script_paths={
            "deploy": Path("deploy/test_change.sql"),
            "revert": Path("revert/test_change.sql"),
            "verify": None,
        },
        planner="Test User <test@example.com>",
        planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        dependencies=("test_change@v2.0.0",),
        notes=None,
        rework_of=None,
    )
    assert change.get_rework_tag() == "v2.0.0"


def test_change_get_rework_tag_returns_none_for_normal_change():
    """Verify get_rework_tag returns None for non-reworked changes."""
    change = model.Change.create(
        name="test_change",
        script_paths={
            "deploy": Path("deploy/test_change.sql"),
            "revert": Path("revert/test_change.sql"),
            "verify": None,
        },
        planner="Test User <test@example.com>",
        planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        dependencies=tuple(),
        notes=None,
        rework_of=None,
    )
    assert change.get_rework_tag() is None


def test_plan_requires_project_name():
    """Verify Plan raises ValueError when project_name is empty."""
    with pytest.raises(ValueError, match="project_name is required"):
        model.Plan(
            project_name="",
            checksum="abc123",
            default_engine="sqlite",
            syntax_version="core",
            uri=None,
            entries=tuple(),
            file_path=Path("sqitch.plan"),
        )


def test_plan_requires_checksum():
    """Verify Plan raises ValueError when checksum is empty."""
    with pytest.raises(ValueError, match="checksum is required"):
        model.Plan(
            project_name="test",
            checksum="",
            default_engine="sqlite",
            syntax_version="core",
            uri=None,
            entries=tuple(),
            file_path=Path("sqitch.plan"),
        )


def test_plan_requires_default_engine():
    """Verify Plan raises ValueError when default_engine is empty."""
    with pytest.raises(ValueError, match="default_engine is required"):
        model.Plan(
            project_name="test",
            checksum="abc123",
            default_engine="",
            syntax_version="core",
            uri=None,
            entries=tuple(),
            file_path=Path("sqitch.plan"),
        )


def test_plan_requires_syntax_version():
    """Verify Plan raises ValueError when syntax_version is empty."""
    with pytest.raises(ValueError, match="syntax_version is required"):
        model.Plan(
            project_name="test",
            checksum="abc123",
            default_engine="sqlite",
            syntax_version="",
            uri=None,
            entries=tuple(),
            file_path=Path("sqitch.plan"),
        )


def test_plan_rejects_invalid_entry_types():
    """Verify Plan raises TypeError when entries contain invalid types."""
    with pytest.raises(TypeError, match="must contain Change or Tag instances"):
        model.Plan(
            project_name="test",
            checksum="abc123",
            default_engine="sqlite",
            syntax_version="core",
            uri=None,
            entries=("invalid_entry",),  # type: ignore
            file_path=Path("sqitch.plan"),
        )


def test_plan_rejects_self_dependent_change():
    """Verify Plan raises ValueError when change depends on itself."""
    change = model.Change.create(
        name="test_change",
        script_paths={
            "deploy": Path("deploy/test_change.sql"),
            "revert": Path("revert/test_change.sql"),
            "verify": None,
        },
        planner="Test User <test@example.com>",
        planned_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        dependencies=("test_change",),  # Self-dependency without tag
        notes=None,
        rework_of=None,
    )
    with pytest.raises(ValueError, match="cannot depend on itself"):
        model.Plan(
            project_name="test",
            checksum="abc123",
            default_engine="sqlite",
            syntax_version="core",
            uri=None,
            entries=(change,),
            file_path=Path("sqitch.plan"),
        )
