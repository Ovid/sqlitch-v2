"""Tests for CLI command models."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from sqlitch.cli.commands._models import CommandResult, DeployOptions, RevertOptions


class TestCommandResultFactoryMethods:
    """Test CommandResult factory methods."""

    def test_ok_creates_success_result(self) -> None:
        """ok() creates successful result with exit code 0."""
        result = CommandResult.ok()
        assert result.success is True
        assert result.exit_code == 0
        assert result.message == ""
        assert result.data == MappingProxyType({})

    def test_ok_with_message(self) -> None:
        """ok() accepts optional message."""
        result = CommandResult.ok("Deployment successful")
        assert result.success is True
        assert result.message == "Deployment successful"

    def test_ok_with_data(self) -> None:
        """ok() accepts optional data dict."""
        result = CommandResult.ok(data={"changes_deployed": 3})
        assert result.success is True
        assert result.data == MappingProxyType({"changes_deployed": 3})

    def test_error_creates_failure_result(self) -> None:
        """error() creates failure result with exit code 1."""
        result = CommandResult.error("Deployment failed")
        assert result.success is False
        assert result.exit_code == 1
        assert result.message == "Deployment failed"
        assert result.data == MappingProxyType({})

    def test_error_with_custom_exit_code(self) -> None:
        """error() accepts custom exit code."""
        result = CommandResult.error("Parse error", exit_code=2)
        assert result.success is False
        assert result.exit_code == 2

    def test_error_with_data(self) -> None:
        """error() accepts optional data dict."""
        result = CommandResult.error("Failed", data={"attempted": 5, "failed": 2})
        assert result.success is False
        assert result.data == MappingProxyType({"attempted": 5, "failed": 2})


class TestCommandResultValidation:
    """Test CommandResult dataclass validation."""

    def test_is_frozen_dataclass(self) -> None:
        """CommandResult should be immutable."""
        result = CommandResult.ok()
        with pytest.raises(AttributeError):
            result.message = "changed"  # type: ignore[misc]

    def test_has_slots(self) -> None:
        """CommandResult should use __slots__ for memory efficiency."""
        result = CommandResult.ok()
        assert not hasattr(result, "__dict__")

    def test_data_is_mapping_proxy(self) -> None:
        """data field should be immutable MappingProxyType."""
        result = CommandResult.ok(data={"key": "value"})
        assert isinstance(result.data, MappingProxyType)
        # MappingProxyType is immutable
        with pytest.raises(TypeError):
            result.data["new_key"] = "new_value"  # type: ignore[index]

    def test_success_matches_exit_code(self) -> None:
        """success field should reflect exit_code == 0."""
        ok_result = CommandResult(success=True, exit_code=0, message="", data=MappingProxyType({}))
        assert ok_result.success is True
        assert ok_result.exit_code == 0

        error_result = CommandResult(
            success=False, exit_code=1, message="", data=MappingProxyType({})
        )
        assert error_result.success is False
        assert error_result.exit_code != 0


class TestDeployOptionsDefaults:
    """Test DeployOptions default values."""

    def test_creates_with_defaults(self) -> None:
        """DeployOptions should have sensible defaults."""
        options = DeployOptions()
        assert options.to_change is None
        assert options.to_tag is None
        assert options.mode == "all"
        assert options.verify is True
        assert options.log_only is False

    def test_accepts_to_change(self) -> None:
        """DeployOptions should accept to_change parameter."""
        options = DeployOptions(to_change="users")
        assert options.to_change == "users"
        assert options.to_tag is None

    def test_accepts_to_tag(self) -> None:
        """DeployOptions should accept to_tag parameter."""
        options = DeployOptions(to_tag="v1.0")
        assert options.to_tag == "v1.0"
        assert options.to_change is None


class TestDeployOptionsValidation:
    """Test DeployOptions validation logic."""

    def test_rejects_both_to_change_and_to_tag(self) -> None:
        """Should raise ValueError if both to_change and to_tag specified."""
        with pytest.raises(ValueError, match="Cannot specify both to_change and to_tag"):
            DeployOptions(to_change="users", to_tag="v1.0")

    def test_rejects_invalid_mode(self) -> None:
        """Should raise ValueError for invalid mode."""
        with pytest.raises(ValueError, match="mode must be one of"):
            DeployOptions(mode="invalid")  # type: ignore[arg-type]

    def test_accepts_valid_modes(self) -> None:
        """Should accept all, change, tag modes."""
        for mode in ["all", "change", "tag"]:
            options = DeployOptions(mode=mode)  # type: ignore[arg-type]
            assert options.mode == mode

    def test_is_frozen_dataclass(self) -> None:
        """DeployOptions should be immutable."""
        options = DeployOptions()
        with pytest.raises(AttributeError):
            options.mode = "change"  # type: ignore[misc]

    def test_has_slots(self) -> None:
        """DeployOptions should use __slots__ for memory efficiency."""
        options = DeployOptions()
        assert not hasattr(options, "__dict__")


class TestRevertOptionsValidation:
    """Test RevertOptions validation logic."""

    def test_requires_to_change_or_to_tag(self) -> None:
        """Should raise ValueError if neither to_change nor to_tag specified."""
        with pytest.raises(ValueError, match="Must specify either to_change or to_tag"):
            RevertOptions()

    def test_rejects_both_to_change_and_to_tag(self) -> None:
        """Should raise ValueError if both to_change and to_tag specified."""
        with pytest.raises(ValueError, match="Cannot specify both to_change and to_tag"):
            RevertOptions(to_change="users", to_tag="v1.0")

    def test_accepts_to_change_only(self) -> None:
        """Should accept to_change parameter alone."""
        options = RevertOptions(to_change="users")
        assert options.to_change == "users"
        assert options.to_tag is None

    def test_accepts_to_tag_only(self) -> None:
        """Should accept to_tag parameter alone."""
        options = RevertOptions(to_tag="v1.0")
        assert options.to_tag == "v1.0"
        assert options.to_change is None

    def test_is_frozen_dataclass(self) -> None:
        """RevertOptions should be immutable."""
        options = RevertOptions(to_change="users")
        with pytest.raises(AttributeError):
            options.to_change = "other"  # type: ignore[misc]

    def test_has_slots(self) -> None:
        """RevertOptions should use __slots__ for memory efficiency."""
        options = RevertOptions(to_change="users")
        assert not hasattr(options, "__dict__")
