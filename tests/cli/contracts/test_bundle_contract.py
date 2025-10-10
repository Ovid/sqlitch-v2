"""Contract parity tests for ``sqlitch bundle``."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


def _seed_project() -> None:
    plan_path = Path("sqitch.plan")
    plan_path.write_text("%project=widgets\n%default_engine=sqlite\n", encoding="utf-8")

    for directory in ("deploy", "revert", "verify"):
        dir_path = Path(directory)
        dir_path.mkdir(parents=True)
        (dir_path / "widgets.sql").write_text(f"-- {directory} script\n", encoding="utf-8")


def test_bundle_creates_default_bundle_directory() -> None:
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        _seed_project()

        result = runner.invoke(main, ["bundle"])

        assert result.exit_code == 0, result.output
        assert "Bundled project to bundle" in result.output

        bundle_root = Path("bundle")
        assert (
            (bundle_root / "sqitch.plan").read_text(encoding="utf-8").startswith("%project=widgets")
        )
        for directory in ("deploy", "revert", "verify"):
            copied = bundle_root / directory / "widgets.sql"
            assert copied.read_text(encoding="utf-8") == f"-- {directory} script\n"


def test_bundle_honours_dest_option() -> None:
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        _seed_project()

        result = runner.invoke(main, ["bundle", "--dest", "dist/bundles"])

        assert result.exit_code == 0, result.output
        assert "Bundled project to dist/bundles" in result.output

        bundle_root = Path("dist/bundles")
        assert (bundle_root / "deploy" / "widgets.sql").exists()


def test_bundle_errors_when_plan_missing() -> None:
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["bundle"])

        assert result.exit_code != 0
        assert "Cannot read plan file" in result.output


def test_bundle_no_plan_flag_skips_plan_copy() -> None:
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        for directory in ("deploy", "revert", "verify"):
            dir_path = Path(directory)
            dir_path.mkdir(parents=True)
            (dir_path / "widgets.sql").write_text(f"-- {directory} script\n", encoding="utf-8")

        result = runner.invoke(main, ["bundle", "--no-plan", "--dest", "output"])

        assert result.exit_code == 0, result.output
        bundle_root = Path("output")
        assert not (bundle_root / "sqitch.plan").exists()
        assert (bundle_root / "deploy" / "widgets.sql").exists()
