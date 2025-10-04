from __future__ import annotations

from pathlib import Path

import pytest

from sqlitch.utils import fs


def test_resolve_plan_file_prefers_sqlitch(tmp_path: Path) -> None:
    plan = tmp_path / "sqlitch.plan"
    plan.write_text("-- sqlitch plan\n", encoding="utf-8")

    result = fs.resolve_plan_file(tmp_path)

    assert result.path == plan
    assert result.is_drop_in is False
    assert result.source_name == "sqlitch.plan"


def test_resolve_plan_file_supports_sqitch_drop_in(tmp_path: Path) -> None:
    plan = tmp_path / "sqitch.plan"
    plan.write_text("-- sqitch plan\n", encoding="utf-8")

    result = fs.resolve_plan_file(tmp_path)

    assert result.path == plan
    assert result.is_drop_in is True
    assert result.source_name == "sqitch.plan"


def test_resolve_plan_file_conflict(tmp_path: Path) -> None:
    (tmp_path / "sqlitch.plan").write_text("sqlitch\n", encoding="utf-8")
    (tmp_path / "sqitch.plan").write_text("sqitch\n", encoding="utf-8")

    with pytest.raises(fs.ArtifactConflictError, match="sqlitch.plan"):
        fs.resolve_plan_file(tmp_path)


def test_resolve_config_file_supports_drop_in(tmp_path: Path) -> None:
    config = tmp_path / "sqitch.conf"
    config.write_text("[core]\nengine=pg\n", encoding="utf-8")

    result = fs.resolve_config_file(tmp_path)

    assert result.path == config
    assert result.is_drop_in is True
    assert result.source_name == "sqitch.conf"


def test_resolve_config_file_missing_returns_none(tmp_path: Path) -> None:
    result = fs.resolve_config_file(tmp_path)

    assert result.path is None
    assert result.is_drop_in is False
    assert result.source_name is None


def test_cleanup_artifacts_removes_files_and_directories(tmp_path: Path) -> None:
    file_path = tmp_path / "sqlitch.plan"
    file_path.write_text("plan\n", encoding="utf-8")

    dir_path = tmp_path / "deploy"
    (dir_path / "alpha.sql").parent.mkdir()
    (dir_path / "alpha.sql").write_text("SELECT 1;\n", encoding="utf-8")

    removed = fs.cleanup_artifacts(tmp_path, ["sqlitch.plan", "deploy", "missing.file"])

    assert set(removed) == {file_path, dir_path}
    assert not file_path.exists()
    assert not dir_path.exists()
