"""Functional tests for tag command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sqlitch.cli.main import main
from sqlitch.plan.parser import parse_plan
from tests.support.test_helpers import isolated_test_context

CLI_GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "support" / "golden" / "cli"


def load_cli_golden(name: str) -> str:
    return (CLI_GOLDEN_ROOT / name).read_text(encoding="utf-8")


class TestTagParity:
    """Regression tests asserting tag command output parity."""

    def test_tag_output_matches_sqitch_golden(self, tmp_path: Path) -> None:
        """Tagging emits Sqitch-identical stdout."""

        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, temp_dir):
            result = runner.invoke(
                main,
                ["init", "flipr", "--engine", "sqlite"],
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
                ["tag", "v1.0.0-dev1"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            assert result.output == load_cli_golden("tag_users_output.txt")

    def test_quiet_mode_suppresses_output(self, tmp_path: Path) -> None:
        """Quiet mode suppresses tag command output."""

        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, temp_dir):
            result = runner.invoke(
                main,
                ["init", "flipr", "--engine", "sqlite"],
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
                ["--quiet", "tag", "v1.0.0-dev1"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            assert result.output == "" or result.output.strip() == ""


class TestTagCreation:
    """Tests for creating tags in the plan."""

    def test_adds_tag_to_plan_file(self, tmp_path: Path) -> None:
        """Test tag is added to plan file."""
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

            # Create tag
            result = runner.invoke(
                main,
                ["tag", "v1.0.0", "-n", "First release"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify plan file contains tag
            plan_path = project_dir / "sqitch.plan"
            plan = parse_plan(plan_path, default_engine="sqlite")

            assert len(plan.tags) == 1
            tag = plan.tags[0]
            assert tag.name == "v1.0.0"
            assert tag.change_ref == "users"
            assert tag.note == "First release"

    def test_tag_references_last_change(self, tmp_path: Path) -> None:
        """Test tag references the last change when no change specified."""
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

            # Add multiple changes
            for change_name in ["users", "posts", "comments"]:
                result = runner.invoke(
                    main,
                    ["add", change_name, "-n", f"Create {change_name} table"],
                    catch_exceptions=False,
                )
                assert result.exit_code == 0

            # Create tag without specifying change
            result = runner.invoke(
                main,
                ["tag", "v1.0.0"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify tag references last change
            plan_path = project_dir / "sqitch.plan"
            plan = parse_plan(plan_path, default_engine="sqlite")

            assert len(plan.tags) == 1
            tag = plan.tags[0]
            assert tag.change_ref == "comments"

    def test_tag_specific_change(self, tmp_path: Path) -> None:
        """Test tag can reference a specific change."""
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

            # Add multiple changes
            for change_name in ["users", "posts", "comments"]:
                result = runner.invoke(
                    main,
                    ["add", change_name, "-n", f"Create {change_name} table"],
                    catch_exceptions=False,
                )
                assert result.exit_code == 0

            # Create tag for middle change using positional arg
            result = runner.invoke(
                main,
                ["tag", "v1.0.0", "posts", "-n", "After posts"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify tag references specified change
            plan_path = project_dir / "sqitch.plan"
            plan = parse_plan(plan_path, default_engine="sqlite")

            assert len(plan.tags) == 1
            tag = plan.tags[0]
            assert tag.change_ref == "posts"

    def test_tag_specific_change_with_option(self, tmp_path: Path) -> None:
        """Test tag can reference a specific change using --change option."""
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
            for change_name in ["users", "posts"]:
                result = runner.invoke(
                    main,
                    ["add", change_name, "-n", f"Create {change_name} table"],
                    catch_exceptions=False,
                )
                assert result.exit_code == 0

            # Create tag using --change option
            result = runner.invoke(
                main,
                ["tag", "v1.0.0", "--change", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify tag references specified change
            plan_path = project_dir / "sqitch.plan"
            plan = parse_plan(plan_path, default_engine="sqlite")

            assert len(plan.tags) == 1
            tag = plan.tags[0]
            assert tag.change_ref == "users"

    def test_validates_tag_name(self, tmp_path: Path) -> None:
        """Test tag validates tag names (Sqitch convention: starts with 'v')."""
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

            # Create tag (SQLitch is permissive about tag names)
            result = runner.invoke(
                main,
                ["tag", "v1.0.0"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

    def test_fails_on_duplicate_tag(self, tmp_path: Path) -> None:
        """Test tag fails if tag name already exists."""
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

            # Create tag
            result = runner.invoke(
                main,
                ["tag", "v1.0.0"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Try to create duplicate tag
            result = runner.invoke(
                main,
                ["tag", "v1.0.0"],
                catch_exceptions=False,
            )
            assert result.exit_code == 1
            assert 'Tag "v1.0.0" already exists' in result.output

    def test_fails_on_unknown_change(self, tmp_path: Path) -> None:
        """Test tag fails if specified change doesn't exist."""
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

            # Try to tag non-existent change
            result = runner.invoke(
                main,
                ["tag", "v1.0.0", "posts"],
                catch_exceptions=False,
            )
            assert result.exit_code == 1
            assert 'Unknown change "posts"' in result.output

    def test_fails_on_empty_plan(self, tmp_path: Path) -> None:
        """Test tag fails if no changes exist in plan."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Try to create tag with no changes
            result = runner.invoke(
                main,
                ["tag", "v1.0.0"],
                catch_exceptions=False,
            )
            assert result.exit_code == 1
            assert "No changes found in plan to tag" in result.output

    def test_output_format_matches_sqitch(self, tmp_path: Path) -> None:
        """Test tag output format matches Sqitch convention."""
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

            # Create tag
            result = runner.invoke(
                main,
                ["tag", "v1.0.0", "-n", "First release"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify output format
            assert "Tagged users with @v1.0.0" in result.output


class TestTagListing:
    """Tests for listing tags in the plan."""

    def test_lists_all_tags_with_no_arguments(self, tmp_path: Path) -> None:
        """Test tag with no arguments lists all tags."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add changes and tags
            for i, change_name in enumerate(["users", "posts", "comments"], 1):
                result = runner.invoke(
                    main,
                    ["add", change_name],
                    catch_exceptions=False,
                )
                assert result.exit_code == 0

                result = runner.invoke(
                    main,
                    ["tag", f"v1.{i}.0"],
                    catch_exceptions=False,
                )
                assert result.exit_code == 0

            # List tags
            result = runner.invoke(
                main,
                ["tag"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Verify all tags shown
            assert "@v1.1.0" in result.output
            assert "@v1.2.0" in result.output
            assert "@v1.3.0" in result.output

    def test_lists_tags_with_list_flag(self, tmp_path: Path) -> None:
        """Test tag --list shows all tags."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add changes and tags
            result = runner.invoke(
                main,
                ["add", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            result = runner.invoke(
                main,
                ["tag", "v1.0.0"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # List tags with --list flag
            result = runner.invoke(
                main,
                ["tag", "--list"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            assert "@v1.0.0" in result.output

    def test_list_shows_tag_names(self, tmp_path: Path) -> None:
        """Test list shows tag names in expected format."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add change and tag
            result = runner.invoke(
                main,
                ["add", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            result = runner.invoke(
                main,
                ["tag", "v1.0.0", "-n", "First release"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # List tags
            result = runner.invoke(
                main,
                ["tag"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Tag name shown with @ prefix
            assert "@v1.0.0" in result.output

    def test_list_empty_plan_shows_nothing(self, tmp_path: Path) -> None:
        """Test listing tags on plan with no tags shows nothing."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Add change but no tag
            result = runner.invoke(
                main,
                ["add", "users"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # List tags
            result = runner.invoke(
                main,
                ["tag"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # No tags shown
            assert result.output.strip() == ""

    def test_list_flag_rejects_other_arguments(self, tmp_path: Path) -> None:
        """Test --list cannot be combined with other arguments."""
        runner = CliRunner()

        with isolated_test_context(runner, base_dir=tmp_path) as (runner, td):
            # Initialize project
            result = runner.invoke(
                main,
                ["init", "test_project", "--engine", "sqlite"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Try to use --list with other arguments
            result = runner.invoke(
                main,
                ["tag", "--list", "v1.0.0"],
            )
            assert result.exit_code == 2
            assert "--list cannot be combined with other arguments" in result.output
