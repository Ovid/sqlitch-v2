"""Tests for symbolic reference resolution (Sqitch parity)."""

from __future__ import annotations

import pytest

from sqlitch.plan.symbolic import (
    SymbolicReference,
    parse_symbolic_reference,
    resolve_symbolic_reference,
)


class TestParseSymbolicReference:
    """Test parsing of symbolic references."""

    def test_plain_change_name(self):
        """Plain change names parse without offsets."""
        result = parse_symbolic_reference("users_table")
        assert result == SymbolicReference(base="users_table", offset_type=None, offset_count=0)

    def test_head_without_at(self):
        """HEAD without @ prefix."""
        result = parse_symbolic_reference("HEAD")
        assert result == SymbolicReference(base="HEAD", offset_type=None, offset_count=0)

    def test_head_with_at(self):
        """@HEAD with @ prefix."""
        result = parse_symbolic_reference("@HEAD")
        assert result == SymbolicReference(base="@HEAD", offset_type=None, offset_count=0)

    def test_root_without_at(self):
        """ROOT without @ prefix."""
        result = parse_symbolic_reference("ROOT")
        assert result == SymbolicReference(base="ROOT", offset_type=None, offset_count=0)

    def test_root_with_at(self):
        """@ROOT with @ prefix."""
        result = parse_symbolic_reference("@ROOT")
        assert result == SymbolicReference(base="@ROOT", offset_type=None, offset_count=0)

    def test_head_caret_single(self):
        """@HEAD^ means one prior."""
        result = parse_symbolic_reference("@HEAD^")
        assert result == SymbolicReference(base="@HEAD", offset_type="^", offset_count=1)

    def test_head_caret_double(self):
        """@HEAD^^ means two prior."""
        result = parse_symbolic_reference("@HEAD^^")
        assert result == SymbolicReference(base="@HEAD", offset_type="^", offset_count=2)

    def test_head_caret_with_number(self):
        """@HEAD^3 means three prior."""
        result = parse_symbolic_reference("@HEAD^3")
        assert result == SymbolicReference(base="@HEAD", offset_type="^", offset_count=3)

    def test_root_tilde_single(self):
        """@ROOT~ means one after."""
        result = parse_symbolic_reference("@ROOT~")
        assert result == SymbolicReference(base="@ROOT", offset_type="~", offset_count=1)

    def test_root_tilde_double(self):
        """@ROOT~~ means two after."""
        result = parse_symbolic_reference("@ROOT~~")
        assert result == SymbolicReference(base="@ROOT", offset_type="~", offset_count=2)

    def test_root_tilde_with_number(self):
        """@ROOT~4 means four after."""
        result = parse_symbolic_reference("@ROOT~4")
        assert result == SymbolicReference(base="@ROOT", offset_type="~", offset_count=4)

    def test_tag_reference(self):
        """Tag references parse as plain base."""
        result = parse_symbolic_reference("@beta1")
        assert result == SymbolicReference(base="@beta1", offset_type=None, offset_count=0)

    def test_tag_qualified_change(self):
        """Tag-qualified changes parse correctly."""
        result = parse_symbolic_reference("users_table@beta1")
        assert result == SymbolicReference(
            base="users_table@beta1", offset_type=None, offset_count=0
        )

    def test_tag_with_caret(self):
        """@beta^2 means two changes before the @beta tag."""
        result = parse_symbolic_reference("@beta^2")
        assert result == SymbolicReference(base="@beta", offset_type="^", offset_count=2)

    def test_change_with_caret(self):
        """users_table^ means one change before users_table."""
        result = parse_symbolic_reference("users_table^")
        assert result == SymbolicReference(base="users_table", offset_type="^", offset_count=1)


class TestResolveSymbolicReference:
    """Test resolution of symbolic references to actual change names."""

    @pytest.fixture
    def plan_changes(self):
        """Sample plan with 5 changes."""
        return ["schema", "users", "flips", "hashtags", "userflips"]

    def test_resolve_head(self, plan_changes):
        """HEAD resolves to last change."""
        assert resolve_symbolic_reference("HEAD", plan_changes) == "userflips"
        assert resolve_symbolic_reference("@HEAD", plan_changes) == "userflips"

    def test_resolve_root(self, plan_changes):
        """ROOT resolves to first change."""
        assert resolve_symbolic_reference("ROOT", plan_changes) == "schema"
        assert resolve_symbolic_reference("@ROOT", plan_changes) == "schema"

    def test_resolve_head_caret(self, plan_changes):
        """@HEAD^ resolves to second-to-last change."""
        assert resolve_symbolic_reference("@HEAD^", plan_changes) == "hashtags"

    def test_resolve_head_caret_double(self, plan_changes):
        """@HEAD^^ resolves to third-to-last change."""
        assert resolve_symbolic_reference("@HEAD^^", plan_changes) == "flips"

    def test_resolve_head_caret_number(self, plan_changes):
        """@HEAD^3 resolves to fourth-to-last change."""
        assert resolve_symbolic_reference("@HEAD^3", plan_changes) == "users"

    def test_resolve_root_tilde(self, plan_changes):
        """@ROOT~ resolves to second change."""
        assert resolve_symbolic_reference("@ROOT~", plan_changes) == "users"

    def test_resolve_root_tilde_double(self, plan_changes):
        """@ROOT~~ resolves to third change."""
        assert resolve_symbolic_reference("@ROOT~~", plan_changes) == "flips"

    def test_resolve_root_tilde_number(self, plan_changes):
        """@ROOT~3 resolves to fourth change."""
        assert resolve_symbolic_reference("@ROOT~3", plan_changes) == "hashtags"

    def test_resolve_change_name(self, plan_changes):
        """Direct change names resolve to themselves."""
        assert resolve_symbolic_reference("users", plan_changes) == "users"
        assert resolve_symbolic_reference("flips", plan_changes) == "flips"

    def test_resolve_change_with_caret(self, plan_changes):
        """users^ resolves to change before users."""
        assert resolve_symbolic_reference("users^", plan_changes) == "schema"

    def test_resolve_change_with_tilde(self, plan_changes):
        """users~ resolves to change after users."""
        assert resolve_symbolic_reference("users~", plan_changes) == "flips"

    def test_error_on_head_beyond_root(self, plan_changes):
        """@HEAD^10 should fail - goes before first change."""
        with pytest.raises(ValueError, match="before first change"):
            resolve_symbolic_reference("@HEAD^10", plan_changes)

    def test_error_on_root_beyond_head(self, plan_changes):
        """@ROOT~10 should fail - goes after last change."""
        with pytest.raises(ValueError, match="after last change"):
            resolve_symbolic_reference("@ROOT~10", plan_changes)

    def test_error_on_empty_plan(self):
        """Resolving references in empty plan should fail."""
        with pytest.raises(ValueError, match="empty plan"):
            resolve_symbolic_reference("@HEAD", [])

    def test_error_on_nonexistent_change(self, plan_changes):
        """Referencing non-existent change should fail."""
        with pytest.raises(ValueError, match="not found in plan"):
            resolve_symbolic_reference("nonexistent", plan_changes)

    def test_error_on_tag_reference(self, plan_changes):
        """Tag references should fail without tag resolution."""
        with pytest.raises(ValueError, match="Cannot resolve tag reference"):
            resolve_symbolic_reference("@beta1", plan_changes)


class TestSymbolicReferenceIsSymbolic:
    """Test the is_symbolic helper."""

    def test_head_is_symbolic(self):
        """HEAD and @HEAD are symbolic."""
        assert SymbolicReference(base="HEAD", offset_type=None, offset_count=0).is_symbolic()
        assert SymbolicReference(base="@HEAD", offset_type=None, offset_count=0).is_symbolic()

    def test_root_is_symbolic(self):
        """ROOT and @ROOT are symbolic."""
        assert SymbolicReference(base="ROOT", offset_type=None, offset_count=0).is_symbolic()
        assert SymbolicReference(base="@ROOT", offset_type=None, offset_count=0).is_symbolic()

    def test_change_name_not_symbolic(self):
        """Regular change names are not symbolic."""
        assert not SymbolicReference(base="users", offset_type=None, offset_count=0).is_symbolic()

    def test_tag_not_symbolic(self):
        """Tag references are not considered symbolic."""
        assert not SymbolicReference(base="@beta1", offset_type=None, offset_count=0).is_symbolic()
