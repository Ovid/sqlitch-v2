"""Functional tests for rework command."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from sqlitch.plan.model import Change
from sqlitch.plan.parser import parse_plan
from tests.support.test_helpers import isolated_test_context

CLI_GOLDEN_ROOT = (
    Path(__file__).resolve().parents[2] / "support" / "golden" / "tutorial_parity" / "rework"
)


TAG_NAME = "v1.0.0"


def _tag_latest_change(runner: CliRunner, note: str | None = None) -> None:
    args = ["tag", TAG_NAME]
    if note is not None:
        args.extend(["-n", note])
    result = runner.invoke(main, args, catch_exceptions=False)
    assert result.exit_code == 0, result.output


class TestReworkCommand:
    """Tests for reworking changes."""

    def test_matches_golden_output_and_plan(  # noqa: D401 - behavior explained inline
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Rework output and plan rewrites must match Sqitch golden fixtures."""

        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            project_dir = Path(td)

            init = runner.invoke(
                main,
                [
                    "init",
                    "flipr",
                    "--engine",
                    "sqlite",
                    "--uri",
                    "https://github.com/sqitchers/sqitch-sqlite-intro/",
                ],
                catch_exceptions=False,
            )
            assert init.exit_code == 0, init.output

            add = runner.invoke(
                main,
                [
                    "add",
                    "users",
                    "-n",
                    "Creates table to track our users.",
                ],
                catch_exceptions=False,
            )
            assert add.exit_code == 0, add.output

            tag = runner.invoke(
                main,
                [
                    "tag",
                    "v1.0.0-dev1",
                    "-n",
                    "Tag v1.0.0-dev1.",
                ],
                catch_exceptions=False,
            )
            assert tag.exit_code == 0, tag.output

            plan_path = project_dir / "sqitch.plan"
            plan_before = (CLI_GOLDEN_ROOT / "plan_before.plan").read_text(encoding="utf-8")
            plan_path.write_text(plan_before, encoding="utf-8")

            fixed_timestamp = datetime(2013, 12, 31, 18, 26, 59, tzinfo=timezone.utc)
            monkeypatch.setattr(
                "sqlitch.cli.commands.rework._utcnow",
                lambda: fixed_timestamp,
            )
            monkeypatch.setattr(
                "sqlitch.cli.commands.rework.resolve_planner_identity",
                lambda env, config: "Marge N. O'Vera <marge@example.com>",
            )

            result = runner.invoke(
                main,
                [
                    "rework",
                    "users",
                    "--note",
                    "Add twitter column to userflips view.",
                ],
                catch_exceptions=False,
            )
            assert result.exit_code == 0, result.output

            expected_output = (CLI_GOLDEN_ROOT / "stdout.txt").read_text(encoding="utf-8")
            assert result.output == expected_output

            updated_plan = plan_path.read_text(encoding="utf-8")
            expected_plan = (CLI_GOLDEN_ROOT / "plan_after.plan").read_text(encoding="utf-8")
            assert updated_plan == expected_plan

    def test_creates_scripts_with_tag_suffix(self, tmp_path: Path) -> None:
        """Rework should create scripts suffixed with the latest tag."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            project_dir = Path(td)

            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add a change
            result = runner.invoke(
                main,
                ["add", "users", "-n", "Create users table"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            _tag_latest_change(runner, note="Tag before rework")

            # Verify original scripts exist
            assert (project_dir / "deploy" / "users.sql").exists()
            assert (project_dir / "revert" / "users.sql").exists()
            assert (project_dir / "verify" / "users.sql").exists()

            # Rework the change
            result = runner.invoke(
                main,
                ["rework", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify rework scripts created
            deploy_path = project_dir / "deploy" / f"users@{TAG_NAME}.sql"
            revert_path = project_dir / "revert" / f"users@{TAG_NAME}.sql"
            verify_path = project_dir / "verify" / f"users@{TAG_NAME}.sql"

            assert deploy_path.exists()
            assert revert_path.exists()
            assert verify_path.exists()

            # Verify output messages
            assert "Created rework deploy script" in result.output
            assert "Created rework revert script" in result.output
            assert "Created rework verify script" in result.output
            assert "Reworked users" in result.output

    def test_copies_existing_scripts_as_starting_point(self, tmp_path: Path) -> None:
        """Test rework copies existing script content."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            project_dir = Path(td)

            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add a change
            result = runner.invoke(
                main,
                ["add", "users", "-n", "Create users table"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Modify the deploy script
            deploy_script = project_dir / "deploy" / "users.sql"
            original_content = "CREATE TABLE users (id INTEGER PRIMARY KEY);"
            deploy_script.write_text(original_content)

            _tag_latest_change(runner)

            # Rework the change
            result = runner.invoke(
                main,
                ["rework", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify rework script contains original content
            rework_script = project_dir / "deploy" / f"users@{TAG_NAME}.sql"
            assert rework_script.read_text() == original_content

    def test_updates_plan_with_rework_entry(self, tmp_path: Path) -> None:
        """Test rework updates plan entry."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            project_dir = Path(td)

            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add a change
            result = runner.invoke(
                main,
                ["add", "users", "-n", "Create users table"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Get original plan
            plan_path = project_dir / "sqitch.plan"
            original_plan = parse_plan(plan_path, default_engine="sqlite")
            original_change = original_plan.get_change("users")

            _tag_latest_change(runner, note="Tag before rework")

            # Rework the change
            result = runner.invoke(
                main,
                ["rework", "users", "--note", "Updated users table"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify plan updated
            updated_plan = parse_plan(plan_path, default_engine="sqlite")
            updated_change = updated_plan.get_change("users")

            # Change name and change_id should be preserved
            assert updated_change.name == original_change.name
            assert updated_change.change_id == original_change.change_id

            # Note should be updated
            assert updated_change.notes == "Updated users table"

            # Verify rework scripts exist
            assert (project_dir / "deploy" / f"users@{TAG_NAME}.sql").exists()
            assert (project_dir / "revert" / f"users@{TAG_NAME}.sql").exists()
            assert (project_dir / "verify" / f"users@{TAG_NAME}.sql").exists()

            relative_deploy = (
                updated_change.script_paths["deploy"].relative_to(project_dir).as_posix()
            )
            relative_revert = (
                updated_change.script_paths["revert"].relative_to(project_dir).as_posix()
            )
            relative_verify = (
                updated_change.script_paths["verify"].relative_to(project_dir).as_posix()
            )

            expected = {
                "deploy": f"deploy/users@{TAG_NAME}.sql",
                "revert": f"revert/users@{TAG_NAME}.sql",
                "verify": f"verify/users@{TAG_NAME}.sql",
            }

            assert relative_deploy == expected["deploy"]
            assert relative_revert == expected["revert"]
            assert relative_verify == expected["verify"]

    def test_validates_change_exists(self, tmp_path: Path) -> None:
        """Test rework fails if change doesn't exist."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Try to rework non-existent change
            result = runner.invoke(
                main,
                ["rework", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 1
            assert 'Unknown change "users"' in result.output

    def test_requires_tag_before_rework(self, tmp_path: Path) -> None:
        """Rework should fail if the change has not been tagged."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, temp_dir):
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            result = runner.invoke(
                main,
                ["add", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            result = runner.invoke(
                main,
                ["rework", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 1
            assert "has not been tagged" in result.output

    def test_preserves_dependencies(self, tmp_path: Path) -> None:
        """Test rework preserves original dependencies by default."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            project_dir = Path(td)

            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add changes with dependencies
            result = runner.invoke(
                main,
                ["add", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            result = runner.invoke(
                main,
                ["add", "posts", "--requires", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            _tag_latest_change(runner, note="Tag posts")

            # Rework posts without specifying dependencies
            result = runner.invoke(
                main,
                ["rework", "posts"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify dependencies: rework creates self-reference (Sqitch behavior)
            plan_path = project_dir / "sqitch.plan"
            plan = parse_plan(plan_path, default_engine="sqlite")
            reworked_change = plan.get_change("posts")
            # Reworked change has single dependency: self-reference to previous version
            assert reworked_change.dependencies == ("posts@v1.0.0",)

    def test_allows_overriding_dependencies(self, tmp_path: Path) -> None:
        """Test rework can override dependencies with --requires."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            project_dir = Path(td)

            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add changes
            for change in ["users", "posts", "comments"]:
                result = runner.invoke(
                    main,
                    ["add", change],
                    catch_exceptions=False,
                )
                assert result.exit_code == 0

            _tag_latest_change(runner, note="Tag comments")

            # Rework comments with new dependencies
            result = runner.invoke(
                main,
                ["rework", "comments", "--requires", "users", "--requires", "posts"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify new dependencies
            plan_path = project_dir / "sqitch.plan"
            plan = parse_plan(plan_path, default_engine="sqlite")
            reworked_change = plan.get_change("comments")
            assert reworked_change.dependencies == ("users", "posts")

    def test_custom_script_paths(self, tmp_path: Path) -> None:
        """Test rework supports custom script paths."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            project_dir = Path(td)

            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add a change
            result = runner.invoke(
                main,
                ["add", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            _tag_latest_change(runner)

            # Rework with custom paths
            result = runner.invoke(
                main,
                [
                    "rework",
                    "users",
                    "--deploy",
                    "deploy/users_v2.sql",
                    "--revert",
                    "revert/users_v2.sql",
                    "--verify",
                    "verify/users_v2.sql",
                ],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify custom scripts created
            assert (project_dir / "deploy" / "users_v2.sql").exists()
            assert (project_dir / "revert" / "users_v2.sql").exists()
            assert (project_dir / "verify" / "users_v2.sql").exists()

            # Note: In compact Sqitch format, the plan doesn't store script paths
            # The custom paths are used but not written to the plan file

    def test_quiet_mode_suppresses_output(self, tmp_path: Path) -> None:
        """Test rework respects quiet mode."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add a change
            result = runner.invoke(
                main,
                ["add", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            _tag_latest_change(runner)

            # Rework in quiet mode
            result = runner.invoke(
                main,
                ["--quiet", "rework", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify no output
            assert result.output.strip() == ""

    def test_fails_if_source_script_missing(self, tmp_path: Path) -> None:
        """Test rework fails if source script is missing."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            project_dir = Path(td)

            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add a change
            result = runner.invoke(
                main,
                ["add", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            _tag_latest_change(runner)

            # Delete the deploy script
            (project_dir / "deploy" / "users.sql").unlink()

            # Try to rework
            result = runner.invoke(
                main,
                ["rework", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 1
            assert "Source script" in result.output
            assert "is missing" in result.output


class TestReworkWithTag:
    """Tests for reworking changes with tags."""

    def test_rework_after_tag(self, tmp_path: Path) -> None:
        """Test rework works after tagging a change."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            project_dir = Path(td)

            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add a change
            result = runner.invoke(
                main,
                ["add", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Tag it
            _tag_latest_change(runner)

            # Rework the change
            result = runner.invoke(
                main,
                ["rework", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify rework succeeded
            assert (project_dir / "deploy" / f"users@{TAG_NAME}.sql").exists()

    def test_preserves_change_id_after_rework(self, tmp_path: Path) -> None:
        """Test rework preserves the original change_id."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            project_dir = Path(td)

            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add a change
            result = runner.invoke(
                main,
                ["add", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Get original change_id
            plan_path = project_dir / "sqitch.plan"
            original_plan = parse_plan(plan_path, default_engine="sqlite")
            original_change_id = original_plan.get_change("users").change_id

            _tag_latest_change(runner)

            # Rework the change
            result = runner.invoke(
                main,
                ["rework", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify change_id preserved
            updated_plan = parse_plan(plan_path, default_engine="sqlite")
            updated_change_id = updated_plan.get_change("users").change_id
            assert updated_change_id == original_change_id


class TestReworkHelpers:
    """Unit coverage for helper utilities in sqlitch.cli.commands.rework.

    Merged from tests/cli/test_rework_helpers.py during Phase 3.7c consolidation.
    """

    @staticmethod
    def _make_change(name: str) -> Change:
        """Helper to create a test Change object."""
        from datetime import datetime, timezone

        timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        return Change.create(
            name=name,
            script_paths={
                "deploy": Path("deploy") / f"{name}.sql",
                "revert": Path("revert") / f"{name}.sql",
                "verify": Path("verify") / f"{name}.sql",
            },
            planner="Planner",
            planned_at=timestamp,
        )

    def test_resolve_new_path_with_override(self, tmp_path: Path) -> None:
        """Test new path resolution with override."""
        from sqlitch.cli.commands import rework as rework_module

        override = tmp_path / "custom.sql"

        result = rework_module._resolve_new_path(
            project_root=tmp_path,
            original=None,
            override=str(override),
            slug="widgets",
            suffix="@v1.0",
        )

        assert result == override

    def test_resolve_new_path_generates_when_original_present(self, tmp_path: Path) -> None:
        """Test new path generation when original is present."""
        from sqlitch.cli.commands import rework as rework_module

        original = tmp_path / "deploy" / "widgets.sql"
        generated = rework_module._resolve_new_path(
            project_root=tmp_path,
            original=original,
            override=None,
            slug="widgets",
            suffix="@v1.0",
        )

        assert generated == original.parent / "widgets@v1.0.sql"

    def test_copy_script_missing_source_errors(self, tmp_path: Path) -> None:
        """Test copy script raises error for missing source."""
        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import rework as rework_module

        target = tmp_path / "deploy" / "rework.sql"

        with pytest.raises(CommandError, match="missing a script"):
            rework_module._copy_script(None, target)

    def test_copy_script_missing_file_errors(self, tmp_path: Path) -> None:
        """Test copy script raises error for missing file."""
        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import rework as rework_module

        source = tmp_path / "missing.sql"
        target = tmp_path / "deploy" / "rework.sql"

        with pytest.raises(CommandError, match="Source script"):
            rework_module._copy_script(source, target)

    def test_copy_script_creates_target(self, tmp_path: Path) -> None:
        """Test copy script creates target file."""
        from sqlitch.cli.commands import rework as rework_module

        source = tmp_path / "source.sql"
        source.write_text("data", encoding="utf-8")
        target = tmp_path / "deploy" / "rework.sql"

        rework_module._copy_script(source, target)

        assert target.read_text(encoding="utf-8") == "data"

    def test_append_rework_change_adds_at_end(self, tmp_path: Path) -> None:
        """Test that rework appends change instead of replacing (Sqitch behavior)."""
        from sqlitch.cli.commands import rework as rework_module

        original = self._make_change("widgets")
        other = self._make_change("gadgets")
        entries = (original, other)
        rework = self._make_change("widgets")

        updated = rework_module._append_rework_change(
            entries=entries, name="widgets", rework=rework
        )

        # Should have original, other, and rework (3 entries total)
        assert len(updated) == 3
        assert updated[0] == original
        assert updated[1] == other
        assert updated[2] == rework

    def test_append_rework_change_missing_raises(self, tmp_path: Path) -> None:
        """Test that reworking non-existent change raises error."""
        from sqlitch.cli.commands import CommandError
        from sqlitch.cli.commands import rework as rework_module

        entries = (self._make_change("widgets"),)
        rework = self._make_change("reports")

        with pytest.raises(CommandError, match='Unknown change "reports"'):
            rework_module._append_rework_change(entries=entries, name="reports", rework=rework)
