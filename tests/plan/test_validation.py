"""Tests for plan validation functions."""

from __future__ import annotations

import pytest

from sqlitch.plan.validation import validate_change_name, validate_tag_name


class TestValidateChangeName:
    """Test validate_change_name function."""

    def test_accepts_valid_alphanumeric(self) -> None:
        """Should accept alphanumeric names."""
        validate_change_name("users")
        validate_change_name("add_users")
        validate_change_name("users123")

    def test_accepts_underscores_and_dashes(self) -> None:
        """Should accept underscores and dashes."""
        validate_change_name("add-users")
        validate_change_name("add_users")
        validate_change_name("add-user_table")

    def test_rejects_whitespace(self) -> None:
        """Should reject names with whitespace."""
        with pytest.raises(ValueError, match="Change name cannot contain whitespace"):
            validate_change_name("add users")

        with pytest.raises(ValueError, match="Change name cannot contain whitespace"):
            validate_change_name("users\ttable")

    def test_rejects_at_symbol(self) -> None:
        """Should reject names with @ symbol."""
        with pytest.raises(ValueError, match="Change name cannot contain"):
            validate_change_name("users@HEAD")

    def test_rejects_empty_name(self) -> None:
        """Should reject empty names."""
        with pytest.raises(ValueError, match="Change name cannot be empty"):
            validate_change_name("")


class TestValidateTagName:
    """Test validate_tag_name function."""

    def test_accepts_valid_tag_names(self) -> None:
        """Should accept valid semantic version tags."""
        validate_tag_name("v1.0")
        validate_tag_name("v1.0.0")
        validate_tag_name("release-1.0")

    def test_rejects_at_prefix(self) -> None:
        """Should reject tags starting with @."""
        with pytest.raises(ValueError, match="Tag name cannot start with"):
            validate_tag_name("@HEAD")

    def test_rejects_whitespace(self) -> None:
        """Should reject tags with whitespace."""
        with pytest.raises(ValueError, match="Tag name cannot contain whitespace"):
            validate_tag_name("v1.0 beta")

    def test_rejects_empty_tag(self) -> None:
        """Should reject empty tags."""
        with pytest.raises(ValueError, match="Tag name cannot be empty"):
            validate_tag_name("")
