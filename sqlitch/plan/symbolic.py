"""Symbolic reference resolution for Sqitch-compatible change specifications.

Implements the extended SHA1 syntax documented in sqitchchanges.pod:
- @HEAD / HEAD - last change in the plan
- @ROOT / ROOT - first change in the plan
- <change>^ - prior change (e.g., @HEAD^ means one before HEAD)
- <change>^<n> - n changes prior (e.g., @HEAD^3 means 3 before HEAD)
- <change>~ - next change (e.g., @ROOT~ means one after ROOT)
- <change>~<n> - n changes after (e.g., @ROOT~4 means 4 after ROOT)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "SymbolicReference",
    "parse_symbolic_reference",
    "resolve_symbolic_reference",
]


@dataclass(frozen=True, slots=True)
class SymbolicReference:
    """Parsed symbolic reference with base and offset."""

    base: str  # The base reference (e.g., "HEAD", "ROOT", "users_table", "@beta1")
    offset_type: str | None  # "^" (prior) or "~" (after), or None
    offset_count: int  # Number of changes to offset (default 1)

    def is_symbolic(self) -> bool:
        """Return True if this reference uses HEAD or ROOT symbols."""
        return self.base in ("HEAD", "ROOT", "@HEAD", "@ROOT")


def parse_symbolic_reference(ref: str) -> SymbolicReference:
    """Parse a change/tag reference into its components.

    Examples:
        @HEAD -> SymbolicReference(base="@HEAD", offset_type=None, offset_count=0)
        @HEAD^ -> SymbolicReference(base="@HEAD", offset_type="^",
                                     offset_count=1)
        @HEAD^3 -> SymbolicReference(base="@HEAD", offset_type="^",
                                      offset_count=3)
        users_table@beta1 -> SymbolicReference(base="users_table@beta1",
                                                offset_type=None,
                                                offset_count=0)
        @ROOT~ -> SymbolicReference(base="@ROOT", offset_type="~",
                                     offset_count=1)
        @ROOT~4 -> SymbolicReference(base="@ROOT", offset_type="~",
                                      offset_count=4)
    """
    ref = ref.strip()

    # Match patterns like @HEAD^^, @HEAD^3, users@tag^2, etc.
    # Pattern: <base>(<offset_char><count>?)* where offset_char is ^ or ~
    match = re.match(r"^(.+?)(\^+|~+|\^(\d+)|~(\d+))$", ref)

    if not match:
        # No offset - just a plain reference
        return SymbolicReference(base=ref, offset_type=None, offset_count=0)

    base = match.group(1)
    offset_part = match.group(2)

    # Determine offset type and count
    if offset_part.startswith("^"):
        offset_type = "^"
        if match.group(3):  # ^<n> format
            offset_count = int(match.group(3))
        else:  # ^^^ format
            offset_count = len(offset_part)
    elif offset_part.startswith("~"):
        offset_type = "~"
        if match.group(4):  # ~<n> format
            offset_count = int(match.group(4))
        else:  # ~~~ format
            offset_count = len(offset_part)
    else:
        # Shouldn't reach here given the regex, but be defensive
        return SymbolicReference(base=ref, offset_type=None, offset_count=0)

    return SymbolicReference(base=base, offset_type=offset_type, offset_count=offset_count)


def resolve_symbolic_reference(ref: str, change_names: list[str]) -> str:
    """Resolve a symbolic reference to an actual change name.

    Args:
        ref: The symbolic reference to resolve (e.g., "@HEAD^", "@ROOT", "users_table")
        change_names: Ordered list of change names in the plan

    Returns:
        The resolved change name

    Raises:
        ValueError: If the reference cannot be resolved
    """
    if not change_names:
        raise ValueError("Cannot resolve symbolic reference in empty plan")

    parsed = parse_symbolic_reference(ref)

    # Resolve base to an index
    base = parsed.base
    if base in ("HEAD", "@HEAD"):
        base_index = len(change_names) - 1
    elif base in ("ROOT", "@ROOT"):
        base_index = 0
    elif base.startswith("@"):
        # Tag reference - for now, treat as unresolvable at this level
        # Caller should resolve tags to change names first
        raise ValueError(f"Cannot resolve tag reference '{base}' without tag information")
    else:
        # Direct change name
        try:
            base_index = change_names.index(base)
        except ValueError as exc:
            raise ValueError(f"Change '{base}' not found in plan") from exc

    # Apply offset
    if parsed.offset_type == "^":
        # Go backwards (prior changes)
        target_index = base_index - parsed.offset_count
    elif parsed.offset_type == "~":
        # Go forwards (after changes)
        target_index = base_index + parsed.offset_count
    else:
        # No offset
        target_index = base_index

    # Validate bounds
    if target_index < 0:
        raise ValueError(
            f"Symbolic reference '{ref}' resolves to position {target_index} "
            f"(before first change)"
        )
    if target_index >= len(change_names):
        raise ValueError(
            f"Symbolic reference '{ref}' resolves to position {target_index} "
            f"(after last change at position {len(change_names) - 1})"
        )

    return change_names[target_index]
