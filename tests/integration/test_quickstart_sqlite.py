"""Integration tests for Quick Start Scenario 10 (environment overrides)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context

_SUPPORT_DIR = Path(__file__).resolve().parents[1] / "support"
_ENV_OVERRIDES_PATH = _SUPPORT_DIR / "tutorial_parity" / "env_overrides.json"
with _ENV_OVERRIDES_PATH.open(encoding="utf-8") as _env_file:
    TUTORIAL_ENV_OVERRIDES = json.load(_env_file)


def _fetch_events(db_path: Path) -> list[tuple[str, str, str, str, str]]:
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT event, change, note, committer_name, committer_email "
                "FROM events ORDER BY committed_at"
            )
            return cursor.fetchall()
        finally:
            cursor.close()
    finally:
        connection.close()


class TestScenario10EnvironmentOverrides:
    """Validate config and environment override behavior end-to-end."""

    def test_environment_override_workflow(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner = CliRunner()
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        with isolated_test_context(runner, base_dir=workspace, set_env=False) as (runner, temp_dir):
            # Initialize tutorial project and author a baseline change
            result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
            assert result.exit_code == 0, f"init failed: {result.output}"

            result = runner.invoke(
                main,
                ["add", "users", "-n", "Creates users table."],
            )
            assert result.exit_code == 0, f"add users failed: {result.output}"

            Path("deploy/users.sql").write_text(
                """-- Deploy flipr:users to sqlite\n\nBEGIN;\n\nCREATE TABLE users (\n    user_id INTEGER PRIMARY KEY,\n    username TEXT NOT NULL UNIQUE\n);\n\nCOMMIT;\n""",
                encoding="utf-8",
            )
            Path("revert/users.sql").write_text(
                """-- Revert flipr:users from sqlite\n\nBEGIN;\n\nDROP TABLE users;\n\nCOMMIT;\n""",
                encoding="utf-8",
            )
            Path("verify/users.sql").write_text(
                """-- Verify flipr:users on sqlite\n\nSELECT user_id, username FROM users WHERE 0;\n""",
                encoding="utf-8",
            )

            # Copy project config to an override file and mutate via SQITCH_CONFIG
            base_config = Path("sqitch.conf").read_text(encoding="utf-8")
            override_path = Path("sqitch.local.override")
            override_path.write_text(base_config, encoding="utf-8")

            override_env = {
                "SQITCH_CONFIG": str(override_path),
                "HOME": str(home_dir),
            }
            result = runner.invoke(
                main,
                ["config", "--local", "core.plan_file", "custom.plan"],
                env=override_env,
            )
            assert result.exit_code == 0, f"config override failed: {result.output}"
            base_config_text = Path("sqitch.conf").read_text(encoding="utf-8")
            assert "plan_file = custom.plan" not in base_config_text
            assert "plan_file = custom.plan" in override_path.read_text(encoding="utf-8")

            # Deploy using SQLITCH_* overrides for target + identity
            deploy_env = dict(TUTORIAL_ENV_OVERRIDES)
            deploy_env["HOME"] = str(home_dir)
            result = runner.invoke(main, ["deploy"], env=deploy_env)
            assert result.exit_code == 0, f"deploy failed: {result.output}"

            registry_events = _fetch_events(Path("sqitch.db"))
            assert registry_events, "Expected deploy event to be recorded"
            deploy_event = registry_events[-1]
            assert deploy_event[0] == "deploy"
            assert deploy_event[3] == TUTORIAL_ENV_OVERRIDES["SQLITCH_FULLNAME"]
            assert deploy_event[4] == TUTORIAL_ENV_OVERRIDES["SQLITCH_EMAIL"]

            # Author a failing change then deploy with only SQITCH_* overrides
            result = runner.invoke(
                main,
                ["add", "broken", "-n", "Intentional failure"],
            )
            assert result.exit_code == 0, f"add broken failed: {result.output}"

            Path("deploy/broken.sql").write_text(
                """-- Deploy flipr:broken to sqlite\n\nBEGIN;\nSELECT RAISE(ABORT, 'forced failure');\nCOMMIT;\n""",
                encoding="utf-8",
            )
            Path("revert/broken.sql").write_text(
                """-- Revert flipr:broken from sqlite\n\nBEGIN;\nDROP TABLE IF EXISTS broken;\nCOMMIT;\n""",
                encoding="utf-8",
            )
            Path("verify/broken.sql").write_text(
                """-- Verify flipr:broken on sqlite\n\nSELECT 1;\n""",
                encoding="utf-8",
            )

            failure_env = {
                "HOME": str(home_dir),
                "SQLITCH_TARGET": TUTORIAL_ENV_OVERRIDES["SQLITCH_TARGET"],
                "SQITCH_FULLNAME": TUTORIAL_ENV_OVERRIDES["SQITCH_FULLNAME"],
                "SQITCH_EMAIL": TUTORIAL_ENV_OVERRIDES["SQITCH_EMAIL"],
            }
            result = runner.invoke(main, ["deploy"], env=failure_env)
            assert result.exit_code != 0, "Deploy should fail for broken change"

            registry_events = _fetch_events(Path("sqitch.db"))
            assert len(registry_events) >= 2, "Expected deploy_fail event to append"
            failure_event = registry_events[-1]
            assert failure_event[0] == "deploy_fail"
            assert failure_event[1] == "broken"
            assert failure_event[2] == "Intentional failure"
            assert failure_event[3] == TUTORIAL_ENV_OVERRIDES["SQITCH_FULLNAME"]
            assert failure_event[4] == TUTORIAL_ENV_OVERRIDES["SQITCH_EMAIL"]

            # Ensure original sqitch.conf remains untouched by override mutation
            assert (
                Path("sqitch.conf").read_text(encoding="utf-8") == base_config
            ), "Project sqitch.conf must remain unchanged"
