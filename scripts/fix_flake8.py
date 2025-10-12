#!/usr/bin/env python3
"""Script to systematically fix flake8 violations.

This script automates the removal of unused imports (F401) and other
straightforward flake8 violations to prepare for T121 completion.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def get_unused_imports() -> list[tuple[str, int, str]]:
    """Get all F401 (unused import) violations.
    
    Returns:
        List of (file_path, line_number, import_statement) tuples
    """
    result = subprocess.run(
        ["flake8", "sqlitch/", "--select=F401"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    
    violations = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        # Format: sqlitch/file.py:line:col: F401 'module' imported but unused
        match = re.match(r"^([^:]+):(\d+):\d+: F401 '([^']+)' imported but unused", line)
        if match:
            file_path, line_num, import_name = match.groups()
            violations.append((file_path, int(line_num), import_name))
    
    return violations


def remove_unused_import(file_path: str, line_num: int, import_name: str) -> None:
    """Remove an unused import from a file.
    
    Args:
        file_path: Path to the file
        line_num: Line number of the import (1-indexed)
        import_name: Name of the import to remove
    """
    full_path = PROJECT_ROOT / file_path
    lines = full_path.read_text().splitlines(keepends=True)
    
    # Line number is 1-indexed
    target_line = lines[line_num - 1]
    
    # Check if this is a multi-import line (e.g., "from x import A, B, C")
    if "," in target_line:
        # Handle multi-import removal
        # This is complex, so skip for now and handle manually
        print(f"SKIP (multi-import): {file_path}:{line_num} - {import_name}")
        return
    
    # Check if it's an "import as" statement
    if " as " in target_line:
        # Need to match the alias name, not the module name
        print(f"SKIP (import as): {file_path}:{line_num} - {import_name}")
        return
    
    # Simple case: entire line is the unused import
    # Just remove the line
    lines.pop(line_num - 1)
    full_path.write_text("".join(lines))
    print(f"REMOVED: {file_path}:{line_num} - {import_name}")


def main() -> None:
    """Main entry point."""
    print("Finding unused imports (F401)...")
    violations = get_unused_imports()
    
    if not violations:
        print("No F401 violations found!")
        return
    
    print(f"Found {len(violations)} unused imports")
    print()
    
    # Group by file to avoid conflicts
    by_file: dict[str, list[tuple[int, str]]] = {}
    for file_path, line_num, import_name in violations:
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append((line_num, import_name))
    
    # Process each file (in reverse line order to avoid line number shifts)
    for file_path, imports in by_file.items():
        print(f"\n{file_path}:")
        # Sort by line number descending
        for line_num, import_name in sorted(imports, key=lambda x: x[0], reverse=True):
            remove_unused_import(file_path, line_num, import_name)


if __name__ == "__main__":
    main()
