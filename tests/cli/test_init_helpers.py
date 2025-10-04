"""Unit tests for helper functions in ``sqlitch.cli.commands.init``."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sqlitch.cli.commands import CommandError
import sqlitch.cli.commands.init as init_module


def test_determine_project_name_variants(tmp_path: Path) -> None:
    root = tmp_path
    assert init_module._determine_project_name("flipr", root) == "flipr"
    assert init_module._determine_project_name(None, root) == root.name
    assert init_module._determine_project_name(None, Path("")) == "sqlitch"


def test_normalize_engine_alias_and_rejection() -> None:
    assert init_module._normalize_engine(None) == "sqlite"
    assert init_module._normalize_engine("Postgres") == "pg"

    with pytest.raises(CommandError) as exc:
        init_module._normalize_engine("oracle")
    assert "Unsupported engine" in str(exc.value)


def test_determine_top_dir_sources(tmp_path: Path) -> None:
    project_root = tmp_path

    option_path, option_display = init_module._determine_top_dir(project_root, Path("scripts"), {})
    assert option_path == project_root / "scripts"
    assert option_display == "scripts"

    absolute_env = (tmp_path / "db" / "deploys").resolve()
    env_path, env_display = init_module._determine_top_dir(
        project_root,
        None,
        {"SQLITCH_TOP_DIR": str(absolute_env)},
    )
    assert env_path == absolute_env
    assert env_display == absolute_env.as_posix()

    default_path, default_display = init_module._determine_top_dir(project_root, None, {})
    assert default_path == project_root
    assert default_display == "."


def test_determine_plan_path_precedence(tmp_path: Path) -> None:
    project_root = tmp_path
    plan_option = Path("plans/custom.plan")

    option_path = init_module._determine_plan_path(
        project_root=project_root,
        plan_option=plan_option,
        global_override=None,
        env={},
    )
    assert option_path == project_root / plan_option

    override = project_root / "override.plan"
    override_path = init_module._determine_plan_path(
        project_root=project_root,
        plan_option=None,
        global_override=override,
        env={"SQLITCH_PLAN_FILE": "ignored.plan"},
    )
    assert override_path == override

    env_path = init_module._determine_plan_path(
        project_root=project_root,
        plan_option=None,
        global_override=None,
        env={"SQITCH_PLAN_FILE": "plans/from-env.plan"},
    )
    assert env_path == project_root / "plans/from-env.plan"


def test_determine_plan_path_existing_and_conflict(tmp_path: Path) -> None:
    project_root = tmp_path

    existing = project_root / "sqlitch.plan"
    existing.write_text("", encoding="utf-8")
    chosen = init_module._determine_plan_path(
        project_root=project_root,
        plan_option=None,
        global_override=None,
        env={},
    )
    assert chosen == existing

    # Introduce conflict between sqlitch and sqitch plan files
    sqitch_plan = project_root / "sqitch.plan"
    sqitch_plan.write_text("", encoding="utf-8")
    with pytest.raises(CommandError) as exc:
        init_module._determine_plan_path(
            project_root=project_root,
            plan_option=None,
            global_override=None,
            env={},
        )
    assert "conflicting artifacts" in str(exc.value)


def test_determine_config_path_existing_and_conflict(tmp_path: Path) -> None:
    project_root = tmp_path

    sqitch_conf = project_root / "sqitch.conf"
    sqitch_conf.write_text("", encoding="utf-8")
    chosen = init_module._determine_config_path(project_root)
    assert chosen == sqitch_conf

    sqlitch_conf = project_root / "sqlitch.conf"
    sqlitch_conf.write_text("", encoding="utf-8")
    with pytest.raises(CommandError) as exc:
        init_module._determine_config_path(project_root)
    assert "conflicting artifacts" in str(exc.value)


def test_validation_helpers_raise_when_artifacts_exist(tmp_path: Path) -> None:
    file_path = tmp_path / "existing.plan"
    file_path.write_text("", encoding="utf-8")
    with pytest.raises(CommandError):
        init_module._validate_absent(file_path, "Plan file")

    dir_path = tmp_path / "deploy"
    dir_path.mkdir()
    with pytest.raises(CommandError):
        init_module._validate_directory_absent(dir_path)

    templates_root = tmp_path / "etc" / "templates"
    templates_root.mkdir(parents=True)
    with pytest.raises(CommandError):
        init_module._validate_templates_absent(templates_root)


def test_render_config_and_format_display(tmp_path: Path) -> None:
    project_root = tmp_path
    plan_path = project_root / "sqlitch.plan"
    plan_path.write_text("", encoding="utf-8")

    config = init_module._render_config(
        engine="sqlite",
        plan_path=plan_path,
        project_root=project_root,
        top_dir_display="deployments",
        target="db:sqlite:flipr",
    )

    assert "engine = sqlite" in config
    assert "# plan_file = sqlitch.plan" in config
    assert "# top_dir = deployments" in config
    assert "# target = db:sqlite:flipr" in config
    assert "# registry = sqlitch" in config
    assert "# client = sqlite3" in config

    internal_display = init_module._format_display_path(plan_path, project_root)
    assert internal_display == "sqlitch.plan"

    external = project_root.parent / "shared" / "alt.plan"
    external.parent.mkdir(parents=True, exist_ok=True)
    external.touch()
    external_display = init_module._format_display_path(external, project_root)
    expected = os.path.relpath(external, project_root).replace(os.sep, "/")
    assert external_display == expected
