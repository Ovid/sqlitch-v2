"""Regression tests ensuring SQLitch matches Sqitch tutorial outputs."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sqlitch.cli.main import main

__all__ = []

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "support" / "golden"
CLI_GOLDEN_ROOT = GOLDEN_ROOT / "cli"
CONFIG_GOLDEN_ROOT = GOLDEN_ROOT / "config"
PLANS_GOLDEN_ROOT = GOLDEN_ROOT / "plans"

INIT_URI = "https://github.com/sqitchers/sqitch-sqlite-intro/"


def test_init_output_matches_sqitch() -> None:
    """`sqlitch init` should emit Sqitch-identical scaffolding."""

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "init",
                "flipr",
                "--uri",
                INIT_URI,
                "--engine",
                "sqlite",
            ],
        )

        assert result.exit_code == 0, result.output

        expected_output = (CLI_GOLDEN_ROOT / "init_output.txt").read_text(encoding="utf-8")
        assert result.output == expected_output

        generated_plan = Path("sqitch.plan").read_text(encoding="utf-8")
        expected_plan = (PLANS_GOLDEN_ROOT / "init.plan").read_text(encoding="utf-8")
        assert generated_plan == expected_plan

        generated_config = Path("sqitch.conf").read_text(encoding="utf-8")
        expected_config = (CONFIG_GOLDEN_ROOT / "init_sqitch.conf").read_text(encoding="utf-8")
        assert generated_config == expected_config

        for directory in ("deploy", "revert", "verify"):
            assert Path(directory).is_dir(), f"Directory {directory} should be created"


def test_add_output_matches_sqitch() -> None:
    """`sqlitch add` should mirror Sqitch output and script headers."""

    runner = CliRunner()
    with runner.isolated_filesystem():
        init_result = runner.invoke(
            main,
            [
                "init",
                "flipr",
                "--uri",
                INIT_URI,
                "--engine",
                "sqlite",
            ],
        )
        assert init_result.exit_code == 0, init_result.output

        result = runner.invoke(
            main,
            [
                "add",
                "users",
                "-n",
                "Creates table to track our users.",
            ],
        )

        assert result.exit_code == 0, result.output

        expected_output = (CLI_GOLDEN_ROOT / "add_users_output.txt").read_text(encoding="utf-8")
        assert result.output == expected_output

        deploy_header, *deploy_rest = Path("deploy/users.sql").read_text(encoding="utf-8").splitlines()
        revert_header, *revert_rest = Path("revert/users.sql").read_text(encoding="utf-8").splitlines()
        verify_header, *verify_rest = Path("verify/users.sql").read_text(encoding="utf-8").splitlines()

        assert deploy_header == "-- Deploy flipr:users to sqlite"
        assert revert_header == "-- Revert flipr:users from sqlite"
        assert verify_header == "-- Verify flipr:users on sqlite"
