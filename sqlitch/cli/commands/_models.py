"""Domain models for CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

__all__ = ["CommandResult", "DeployOptions", "RevertOptions"]


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Represents the result of executing a CLI command.
    
    Used to communicate success/failure state and optional data back to the CLI layer.
    The data field is immutable (MappingProxyType) to maintain consistency.
    """
    
    success: bool
    exit_code: int
    message: str
    data: MappingProxyType[str, object]
    
    @classmethod
    def ok(cls, message: str = "", data: dict[str, object] | None = None) -> CommandResult:
        """Create a successful result with exit code 0.
        
        Args:
            message: Optional success message
            data: Optional data dictionary (will be wrapped in MappingProxyType)
            
        Returns:
            CommandResult with success=True and exit_code=0
        """
        return cls(
            success=True,
            exit_code=0,
            message=message,
            data=MappingProxyType(data or {}),
        )
    
    @classmethod
    def error(
        cls,
        message: str,
        exit_code: int = 1,
        data: dict[str, object] | None = None,
    ) -> CommandResult:
        """Create a failure result with specified exit code.
        
        Args:
            message: Error message
            exit_code: Exit code (default 1 for user error)
            data: Optional data dictionary (will be wrapped in MappingProxyType)
            
        Returns:
            CommandResult with success=False and specified exit_code
        """
        return cls(
            success=False,
            exit_code=exit_code,
            message=message,
            data=MappingProxyType(data or {}),
        )


@dataclass(frozen=True, slots=True)
class DeployOptions:
    """Options for deploy command execution.
    
    Validates mutual exclusivity of to_change and to_tag parameters.
    """
    
    to_change: str | None = None
    to_tag: str | None = None
    mode: Literal["all", "change", "tag"] = "all"
    verify: bool = True
    log_only: bool = False
    
    def __post_init__(self) -> None:
        """Validate options."""
        if self.to_change is not None and self.to_tag is not None:
            raise ValueError("Cannot specify both to_change and to_tag")
        
        if self.mode not in ("all", "change", "tag"):
            raise ValueError(f"mode must be one of: all, change, tag (got {self.mode!r})")


@dataclass(frozen=True, slots=True)
class RevertOptions:
    """Options for revert command execution.
    
    Requires exactly one of to_change or to_tag to be specified.
    """
    
    to_change: str | None = None
    to_tag: str | None = None
    
    def __post_init__(self) -> None:
        """Validate options."""
        if self.to_change is None and self.to_tag is None:
            raise ValueError("Must specify either to_change or to_tag")
        
        if self.to_change is not None and self.to_tag is not None:
            raise ValueError("Cannot specify both to_change and to_tag")
