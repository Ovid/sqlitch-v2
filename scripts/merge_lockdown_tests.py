#!/usr/bin/env python3
"""Script to merge *_lockdown.py test files into their base counterparts.

Merges test classes from *_lockdown.py files into base test files by
adding them as new test classes (e.g., class TestResolverLockdown).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def extract_test_content(filepath: Path) -> tuple[list[str], list[str], list[str]]:
    """Extract constants, test classes, and standalone test functions from a file.
    
    Returns:
        Tuple of (constants, classes, functions) as lists of source code strings
    """
    content = filepath.read_text(encoding="utf-8")
    tree = ast.parse(content)
    
    constants = []
    classes = []
    functions = []
    
    for node in tree.body:
        # Skip module docstring and imports
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # Skip docstrings
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue  # Skip imports
            
        if isinstance(node, ast.Assign):
            # Extract module-level constants (uppercase or specific names)
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    start_line = node.lineno - 1
                    end_line = node.end_lineno if node.end_lineno else start_line + 1
                    lines = content.splitlines()
                    const_source = "\n".join(lines[start_line:end_line])
                    constants.append(const_source)
                    break
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            # Get the source code for this class
            start_line = node.lineno - 1  # 0-indexed
            end_line = node.end_lineno if node.end_lineno else start_line + 1
            lines = content.splitlines()
            class_source = "\n".join(lines[start_line:end_line])
            classes.append(class_source)
        elif isinstance(node, ast.FunctionDef):
            # Get test functions and helper functions (starting with _ or test_)
            if node.name.startswith("test_") or node.name.startswith("_"):
                start_line = node.lineno - 1
                end_line = node.end_lineno if node.end_lineno else start_line + 1
                lines = content.splitlines()
                func_source = "\n".join(lines[start_line:end_line])
                functions.append(func_source)
    
    return constants, classes, functions


def merge_lockdown_file(lockdown_path: Path, base_path: Path) -> None:
    """Merge lockdown test file into base test file."""
    if not lockdown_path.exists():
        print(f"Skipping {lockdown_path.name}: file doesn't exist")
        return
    
    # Extract test content from lockdown file
    lockdown_constants, lockdown_classes, lockdown_functions = extract_test_content(lockdown_path)
    
    if not lockdown_constants and not lockdown_classes and not lockdown_functions:
        print(f"No test content found in {lockdown_path.name}")
        return
    
    # Read base file (create if it doesn't exist)
    if base_path.exists():
        base_content = base_path.read_text(encoding="utf-8")
    else:
        # Create minimal base file
        module_name = base_path.stem.replace("test_", "")
        base_content = f'''"""Tests for {module_name} module."""

from __future__ import annotations

import pytest
'''
    
    # Append lockdown content
    separator = "\n\n# " + "=" * 77 + "\n"
    separator += f"# Lockdown Tests (merged from {lockdown_path.name})\n"
    separator += "# " + "=" * 77 + "\n\n"
    
    all_content = lockdown_constants + lockdown_functions + lockdown_classes
    merged_content = base_content.rstrip() + "\n" + separator + "\n\n".join(all_content) + "\n"
    
    # Write merged content
    base_path.write_text(merged_content, encoding="utf-8")
    count_str = f"{len(lockdown_constants)} constants, {len(lockdown_functions)} functions, {len(lockdown_classes)} classes"
    print(f"✓ Merged {lockdown_path.name} into {base_path.name} ({count_str})")


def main() -> int:
    """Merge all lockdown test files."""
    repo_root = Path(__file__).parent.parent
    
    # Define the mapping of lockdown files to their base files
    merges = [
        ("tests/cli/test_main_lockdown.py", "tests/cli/test_main_module.py"),
        ("tests/config/test_resolver_lockdown.py", "tests/config/test_resolver.py"),
        ("tests/docs/test_quickstart_lockdown.py", "tests/docs/test_quickstart.py"),  # May need to create
        ("tests/engine/test_sqlite_lockdown.py", "tests/engine/test_sqlite.py"),
        ("tests/registry/test_state_lockdown.py", "tests/registry/test_state.py"),
        ("tests/utils/test_identity_lockdown.py", "tests/utils/test_identity.py"),
    ]
    
    for lockdown_rel, base_rel in merges:
        lockdown_path = repo_root / lockdown_rel
        base_path = repo_root / base_rel
        
        if lockdown_path.exists():
            try:
                merge_lockdown_file(lockdown_path, base_path)
                # Delete the lockdown file after successful merge
                lockdown_path.unlink()
                print(f"  Deleted {lockdown_path}")
            except Exception as e:
                print(f"✗ Error merging {lockdown_path.name}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return 1
        else:
            print(f"⚠ {lockdown_rel}: file doesn't exist")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
