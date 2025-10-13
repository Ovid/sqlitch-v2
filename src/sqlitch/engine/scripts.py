"""Models for SQL script execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["Script", "ScriptResult"]


@dataclass(frozen=True)
class Script:
    """Represents a SQL script file to be executed.

    Scripts are immutable once loaded from disk.
    """

    path: Path
    content: str

    @classmethod
    def load(cls, path: Path) -> Script:
        """Load script content from file.

        Args:
            path: Path to the SQL script file

        Returns:
            Script instance with loaded content

        Raises:
            FileNotFoundError: If the script file doesn't exist
        """
        content = path.read_text()
        return cls(path=path, content=content)


@dataclass(frozen=True)
class ScriptResult:
    """Represents the result of executing a SQL script.

    Used to track whether script execution succeeded or failed.
    """

    success: bool
    error_message: str | None

    @classmethod
    def ok(cls) -> ScriptResult:
        """Create a successful script execution result.

        Returns:
            ScriptResult with success=True
        """
        return cls(success=True, error_message=None)

    @classmethod
    def error(cls, message: str) -> ScriptResult:
        """Create a failed script execution result.

        Args:
            message: Error message describing the failure

        Returns:
            ScriptResult with success=False and error message
        """
        return cls(success=False, error_message=message)
