"""Tests for script models."""

from __future__ import annotations

from pathlib import Path

import pytest

from sqlitch.engine.scripts import Script, ScriptResult


class TestScriptLoad:
    """Test Script.load() class method."""

    def test_loads_valid_script_file(self, tmp_path: Path) -> None:
        """load() should read script content from file."""
        script_file = tmp_path / "deploy.sql"
        script_file.write_text("-- Deploy users\nCREATE TABLE users (id INTEGER);")

        script = Script.load(script_file)
        assert script.path == script_file
        assert script.content == "-- Deploy users\nCREATE TABLE users (id INTEGER);"

    def test_raises_file_not_found_error(self, tmp_path: Path) -> None:
        """load() should raise FileNotFoundError for missing file."""
        missing_file = tmp_path / "nonexistent.sql"
        with pytest.raises(FileNotFoundError):
            Script.load(missing_file)

    def test_is_frozen_dataclass(self, tmp_path: Path) -> None:
        """Script should be immutable."""
        script_file = tmp_path / "test.sql"
        script_file.write_text("SELECT 1;")
        script = Script.load(script_file)

        with pytest.raises(AttributeError):
            script.content = "changed"  # type: ignore[misc]

    def test_has_slots(self, tmp_path: Path) -> None:
        """Script should use __slots__ for memory efficiency."""
        script_file = tmp_path / "test.sql"
        script_file.write_text("SELECT 1;")
        script = Script.load(script_file)

        assert not hasattr(script, "__dict__")


class TestScriptResultFactoryMethods:
    """Test ScriptResult factory methods."""

    def test_ok_creates_success_result(self) -> None:
        """ok() creates successful result."""
        result = ScriptResult.ok()
        assert result.success is True
        assert result.error_message is None

    def test_error_creates_failure_result(self) -> None:
        """error() creates failure result with message."""
        result = ScriptResult.error("Table already exists")
        assert result.success is False
        assert result.error_message == "Table already exists"

    def test_is_frozen_dataclass(self) -> None:
        """ScriptResult should be immutable."""
        result = ScriptResult.ok()
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]

    def test_has_slots(self) -> None:
        """ScriptResult should use __slots__ for memory efficiency."""
        result = ScriptResult.ok()
        assert not hasattr(result, "__dict__")
