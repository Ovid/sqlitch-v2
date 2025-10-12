#!/usr/bin/env python3
"""Script to merge duplicate contract test files.

Merges tests/cli/commands/test_*_contract.py into tests/cli/contracts/test_*_contract.py
by appending just the test classes and functions, avoiding duplicate imports.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def extract_test_content(filepath: Path) -> tuple[str, list[str]]:
    """Extract docstring and test content from a file.
    
    Returns:
        Tuple of (docstring, list of test class/function definitions as strings)
    """
    content = filepath.read_text(encoding="utf-8")
    tree = ast.parse(content)
    
    # Get module docstring
    docstring = ast.get_docstring(tree) or ""
    
    # Find all test classes and standalone test functions, including helper functions
    test_items = []
    in_test_class = False
    
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            # Include Test classes, test_ functions, and _helper functions
            if (node.name.startswith("Test") or 
                node.name.startswith("test_") or 
                node.name.startswith("_")):
                # Get the source code for this node
                start_line = node.lineno - 1  # 0-indexed
                end_line = node.end_lineno if node.end_lineno else start_line + 1
                lines = content.splitlines()
                item_source = "\n".join(lines[start_line:end_line])
                test_items.append(item_source)
    
    return docstring, test_items


def merge_contract_files(source: Path, target: Path) -> None:
    """Merge source contract file into target contract file."""
    if not source.exists() or not target.exists():
        print(f"Skipping {source.name}: source or target doesn't exist")
        return
    
    # Read target file
    target_content = target.read_text(encoding="utf-8")
    
    # Extract test items from source
    source_docstring, source_items = extract_test_content(source)
    
    if not source_items:
        print(f"No test items found in {source.name}")
        return
    
    # Update target docstring to mention the merge
    if '"""Contract' in target_content or "'''Contract" in target_content:
        # Find and update the module docstring
        tree = ast.parse(target_content)
        target_docstring = ast.get_docstring(tree) or ""
        
        # Create updated docstring
        if "Perl Reference:" not in target_docstring:
            if source_docstring and "Perl Reference:" in source_docstring:
                # Extract Perl Reference section from source
                perl_ref_start = source_docstring.find("\nPerl Reference:")
                if perl_ref_start > 0:
                    perl_ref = source_docstring[perl_ref_start:]
                    target_docstring = target_docstring.rstrip() + "\n" + perl_ref
        
        updated_docstring = target_docstring.rstrip() + "\n\nIncludes CLI signature contract tests merged from tests/cli/commands/"
        
        # Replace the docstring
        if '"""' in target_content[:100]:
            doc_start = target_content.find('"""')
            doc_end = target_content.find('"""', doc_start + 3) + 3
            target_content = target_content[:doc_start] + '"""' + updated_docstring + '\n"""' + target_content[doc_end:]
        elif "'''" in target_content[:100]:
            doc_start = target_content.find("'''")
            doc_end = target_content.find("'''", doc_start + 3) + 3
            target_content = target_content[:doc_start] + "'''" + updated_docstring + "\n'''" + target_content[doc_end:]
    
    # Append the test items from source
    separator = "\n\n# " + "=" * 77 + "\n"
    separator += f"# CLI Contract Tests (merged from tests/cli/commands/{source.name})\n"
    separator += "# " + "=" * 77 + "\n\n"
    
    merged_content = target_content.rstrip() + "\n" + separator + "\n\n".join(source_items) + "\n"
    
    # Write merged content
    target.write_text(merged_content, encoding="utf-8")
    print(f"✓ Merged {source.name} into {target.name}")


def main() -> int:
    """Merge all contract test files."""
    repo_root = Path(__file__).parent.parent
    commands_dir = repo_root / "tests" / "cli" / "commands"
    contracts_dir = repo_root / "tests" / "cli" / "contracts"
    
    commands = [
        "add", "bundle", "checkout", "config", "deploy", "engine", "help",
        "init", "log", "plan", "rebase", "revert", "rework", "show",
        "status", "tag", "target", "upgrade", "verify"
    ]
    
    for cmd in commands:
        source = commands_dir / f"test_{cmd}_contract.py"
        target = contracts_dir / f"test_{cmd}_contract.py"
        
        if source.exists() and target.exists():
            try:
                merge_contract_files(source, target)
                # Delete the source file after successful merge
                source.unlink()
                print(f"  Deleted {source}")
            except Exception as e:
                print(f"✗ Error merging {cmd}: {e}", file=sys.stderr)
                return 1
        else:
            if source.exists():
                print(f"⚠ {cmd}: source exists but no target")
            elif target.exists():
                print(f"⚠ {cmd}: target exists but no source")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
