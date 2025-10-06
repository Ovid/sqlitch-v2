"""Plan validation functions."""

from __future__ import annotations

import re

__all__ = ["validate_change_name", "validate_tag_name"]


def validate_change_name(name: str) -> None:
    """Validate change name follows Sqitch naming rules.
    
    Args:
        name: Change name to validate
        
    Raises:
        ValueError: If name is invalid
        
    Rules:
        - Cannot be empty
        - Cannot contain whitespace
        - Cannot contain @ symbol
        - Should use alphanumeric, underscores, dashes
    """
    if not name:
        raise ValueError("Change name cannot be empty")
    
    if re.search(r"\s", name):
        raise ValueError("Change name cannot contain whitespace")
    
    if "@" in name:
        raise ValueError("Change name cannot contain @ symbol")


def validate_tag_name(name: str) -> None:
    """Validate tag name follows Sqitch naming rules.
    
    Args:
        name: Tag name to validate
        
    Raises:
        ValueError: If name is invalid
        
    Rules:
        - Cannot be empty
        - Cannot start with @
        - Cannot contain whitespace
    """
    if not name:
        raise ValueError("Tag name cannot be empty")
    
    if name.startswith("@"):
        raise ValueError("Tag name cannot start with @ symbol")
    
    if re.search(r"\s", name):
        raise ValueError("Tag name cannot contain whitespace")
