"""Functional tests for rework command."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from sqlitch.plan.parser import parse_plan


class TestReworkCommand:
    """Tests for reworking changes."""

    def test_creates_scripts_with_rework_suffix(self, tmp_path: Path) -> None:
        """Test rework creates scripts with _rework suffix."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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
            assert (project_dir / "deploy" / "users_rework.sql").exists()
            assert (project_dir / "revert" / "users_rework.sql").exists()
            assert (project_dir / "verify" / "users_rework.sql").exists()

            # Verify output messages
            assert "Created rework deploy script" in result.output
            assert "Created rework revert script" in result.output
            assert "Created rework verify script" in result.output
            assert "Reworked users" in result.output

    def test_copies_existing_scripts_as_starting_point(self, tmp_path: Path) -> None:
        """Test rework copies existing script content."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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

            # Rework the change
            result = runner.invoke(
                main,
                ["rework", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify rework script contains original content
            rework_script = project_dir / "deploy" / "users_rework.sql"
            assert rework_script.read_text() == original_content

    def test_updates_plan_with_rework_entry(self, tmp_path: Path) -> None:
        """Test rework updates plan entry."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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
            assert (project_dir / "deploy" / "users_rework.sql").exists()
            assert (project_dir / "revert" / "users_rework.sql").exists()
            assert (project_dir / "verify" / "users_rework.sql").exists()

    def test_validates_change_exists(self, tmp_path: Path) -> None:
        """Test rework fails if change doesn't exist."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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

    def test_preserves_dependencies(self, tmp_path: Path) -> None:
        """Test rework preserves original dependencies by default."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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

            # Rework posts without specifying dependencies
            result = runner.invoke(
                main,
                ["rework", "posts"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify dependencies preserved
            plan_path = project_dir / "sqitch.plan"
            plan = parse_plan(plan_path, default_engine="sqlite")
            reworked_change = plan.get_change("posts")
            assert reworked_change.dependencies == ("users",)

    def test_allows_overriding_dependencies(self, tmp_path: Path) -> None:
        """Test rework can override dependencies with --requires."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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
            result = runner.invoke(
                main,
                ["tag", "v1.0.0"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Rework the change
            result = runner.invoke(
                main,
                ["rework", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify rework succeeded
            assert (project_dir / "deploy" / "users_rework.sql").exists()

    def test_preserves_change_id_after_rework(self, tmp_path: Path) -> None:
        """Test rework preserves the original change_id."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
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
