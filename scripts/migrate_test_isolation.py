#!/usr/bin/env python3
"""Migrate test files to use isolated_test_context().

This script automatically migrates test files from using runner.isolated_filesystem()
to using the new isolated_test_context() helper that provides proper config isolation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def migrate_test_file(file_path: Path) -> tuple[bool, str]:
    """Migrate a single test file.
    
    Returns:
        (success, message) tuple
    """
    print(f"Migrating {file_path}...")
    
    content = file_path.read_text()
    original_content = content
    
    # Check if already migrated
    if "from tests.support.test_helpers import isolated_test_context" in content:
        return (True, "Already migrated")
    
    # Check if file uses isolated_filesystem
    if "isolated_filesystem()" not in content and "isolated_filesystem(temp_dir=" not in content:
        return (True, "No isolated_filesystem() usage found")
    
    # Step 1: Add import if not present
    if "from tests.support.test_helpers import" not in content:
        # Find the imports section
        import_pattern = r"(from sqlitch\.cli\.main import.*?\n)"
        match = re.search(import_pattern, content)
        if match:
            insert_pos = match.end()
            content = (content[:insert_pos] + 
                      "from tests.support.test_helpers import isolated_test_context\n" +
                      content[insert_pos:])
        else:
            # Fallback: add after last import
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("from ") or line.startswith("import "):
                    last_import_idx = i
            if 'last_import_idx' in locals():
                lines.insert(last_import_idx + 1, "from tests.support.test_helpers import isolated_test_context")
                content = "\n".join(lines)
    
    # Step 2: Replace isolated_filesystem() usage patterns
    # Pattern 1: with runner.isolated_filesystem():
    pattern1 = r"with runner\.isolated_filesystem\(\):"
    replacement1 = "with isolated_test_context(runner) as (runner, temp_dir):"
    content = re.sub(pattern1, replacement1, content)
    
    # Pattern 2: with runner.isolated_filesystem() as temp_dir_str:
    pattern2 = r"with runner\.isolated_filesystem\(\) as (\w+):"
    def replace_with_tempdir(match):
        var_name = match.group(1)
        return f"with isolated_test_context(runner) as (runner, temp_dir):"
    content = re.sub(pattern2, replace_with_tempdir, content)
    
    # Pattern 3: with runner.isolated_filesystem(temp_dir=tmp_path):
    # This pattern is used with pytest's tmp_path fixture or any variable
    # We need to wrap it to add env var isolation
    pattern3 = r"with runner\.isolated_filesystem\(temp_dir=(\w+)\):"
    def replace_with_base_dir(match):
        var_name = match.group(1)
        return f"with isolated_test_context(runner, base_dir={var_name}) as (runner, temp_dir):"
    content = re.sub(pattern3, replace_with_base_dir, content)
    
    # Pattern 4: with runner.isolated_filesystem(temp_dir=tmp_path) as td:
    pattern4 = r"with runner\.isolated_filesystem\(temp_dir=(\w+)\) as (\w+):"
    def replace_with_base_dir_and_var(match):
        base_var = match.group(1)
        assigned_var = match.group(2)
        return f"with isolated_test_context(runner, base_dir={base_var}) as (runner, {assigned_var}):"
    content = re.sub(pattern4, replace_with_base_dir_and_var, content)
    
    # Step 3: Replace Path(temp_dir_str) with temp_dir
    content = re.sub(r"Path\(temp_dir_str\)", "temp_dir", content)
    
    # Step 4: Replace Path("...") with (temp_dir / "...")
    # Be careful - only replace in context of file operations
    lines = content.split("\n")
    new_lines = []
    in_isolated_context = False
    indent_level = 0
    
    for line in lines:
        # Track when we enter/exit isolated context
        if "with isolated_test_context(runner)" in line:
            in_isolated_context = True
            indent_level = len(line) - len(line.lstrip())
        elif in_isolated_context and line.strip() and not line[indent_level:indent_level+1].isspace():
            # Exited the with block
            in_isolated_context = False
        
        # Only modify lines inside isolated context
        if in_isolated_context:
            # Replace Path("filename") with (temp_dir / "filename")
            line = re.sub(r'Path\("([^"]+)"\)\.write_text', r'(temp_dir / "\1").write_text', line)
            line = re.sub(r'Path\("([^"]+)"\)\.read_text', r'(temp_dir / "\1").read_text', line)
            line = re.sub(r'Path\("([^"]+)"\)\.exists', r'(temp_dir / "\1").exists', line)
            line = re.sub(r'Path\("([^"]+)"\)\.mkdir', r'(temp_dir / "\1").mkdir', line)
            # Also handle cases without method calls
            line = re.sub(r'Path\("([^"]+)"\)([,\)])', r'(temp_dir / "\1")\2', line)
        
        new_lines.append(line)
    
    content = "\n".join(new_lines)
    
    # Step 5: Remove isolated_env fixture usage if present
    # Remove fixture from function signatures
    content = re.sub(r", isolated_env\)", ")", content)
    content = re.sub(r"\(runner, isolated_env\)", "(runner)", content)
    
    # Remove the isolated_env fixture definition
    fixture_pattern = r"@pytest\.fixture\s+def isolated_env.*?return fake_home\s*\n"
    content = re.sub(fixture_pattern, "", content, flags=re.DOTALL)
    
    # Step 6: Remove env={"HOME": ...} from runner.invoke() calls
    # This is now handled by isolated_test_context
    content = re.sub(r', env=\{"HOME": str\(isolated_env\)\}', '', content)
    content = re.sub(r'env=\{"HOME": str\(isolated_env\)\}, ', '', content)
    
    # Step 7: Replace references to isolated_env with temp_dir
    content = re.sub(r'isolated_env /', 'temp_dir /', content)
    content = re.sub(r'str\(isolated_env\)', 'str(temp_dir)', content)
    
    # Only write if changes were made
    if content != original_content:
        file_path.write_text(content)
        return (True, f"Migrated successfully ({content.count('isolated_test_context')} contexts)")
    else:
        return (False, "No changes made")


def main():
    """Migrate all test files that need migration."""
    
    # Get the test files to migrate from command line or use defaults
    if len(sys.argv) > 1:
        files = [Path(arg) for arg in sys.argv[1:]]
    else:
        # Default: migrate the highest priority file first
        files = [
            Path("tests/cli/commands/test_config_functional.py"),
        ]
    
    results = []
    for file_path in files:
        if not file_path.exists():
            print(f"ERROR: File not found: {file_path}")
            continue
        
        success, message = migrate_test_file(file_path)
        results.append((file_path, success, message))
        print(f"  {message}")
    
    print("\n" + "="*60)
    print("Migration Summary:")
    for file_path, success, message in results:
        status = "✓" if success else "✗"
        print(f"{status} {file_path.name}: {message}")
    
    return 0 if all(r[1] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
