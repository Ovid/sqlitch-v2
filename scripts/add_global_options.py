#!/usr/bin/env python3
"""Script to add global options decorators to all command files.

Constitutional requirement: T028 - Add global options infrastructure to all commands.
"""
import re
from pathlib import Path

COMMANDS_DIR = Path(__file__).parent.parent / "sqlitch" / "cli" / "commands"

COMMANDS = [
    "add",
    "bundle",
    "checkout",
    "config",
    "deploy",
    "engine",
    "help",
    "init",
    "log",
    "plan",
    "rebase",
    "revert",
    "rework",
    "show",
    "status",
    "tag",
    "target",
    "upgrade",
    "verify",
]


def add_global_options_to_command(command_file: Path) -> bool:
    """Add global options decorators to a command file."""
    content = command_file.read_text()

    # Check if already has global_sqitch_options
    if "global_sqitch_options" in content:
        print(f"✅ {command_file.name} - Already has global options")
        return False

    # Add import if not present
    if "from ..options import" not in content:
        # Find the last local import
        import_pattern = r"(from \. import [^\n]+)"
        match = re.search(import_pattern, content)
        if match:
            old_import = match.group(0)
            new_imports = (
                old_import + "\nfrom ..options import global_output_options, global_sqitch_options"
            )
            content = content.replace(old_import, new_imports)
    elif "global_output_options" not in content:
        # Update existing import
        content = re.sub(
            r"from \.\.options import ([^\n]+)",
            r"from ..options import \1, global_output_options, global_sqitch_options",
            content,
        )

    # Find @click.pass_context and add decorators before it
    pass_context_pattern = r"(@click\.pass_context\ndef \w+\()"
    match = re.search(pass_context_pattern, content)
    if match:
        old_decorator = match.group(1)
        new_decorators = "@global_sqitch_options\n@global_output_options\n" + old_decorator
        content = content.replace(old_decorator, new_decorators)

        # Add parameters to function signature
        func_sig_pattern = r"(def \w+\(\s*ctx: click\.Context,\s*\*,)"
        content = re.sub(
            func_sig_pattern,
            r"\1\n    json_mode: bool,\n    verbose: int,\n    quiet: bool,",
            content,
        )

        command_file.write_text(content)
        print(f"✅ {command_file.name} - Added global options")
        return True
    else:
        print(f"⚠️  {command_file.name} - Could not find @click.pass_context")
        return False


def main():
    """Add global options to all commands."""
    print("Adding global options to all SQLitch commands...")
    print()

    modified = 0
    skipped = 0
    errors = 0

    for cmd in COMMANDS:
        cmd_file = COMMANDS_DIR / f"{cmd}.py"
        if not cmd_file.exists():
            print(f"❌ {cmd}.py - File not found")
            errors += 1
            continue

        try:
            if add_global_options_to_command(cmd_file):
                modified += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"❌ {cmd}.py - Error: {e}")
            errors += 1

    print()
    print(f"Summary: {modified} modified, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
