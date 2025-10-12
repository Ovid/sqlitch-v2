#!/usr/bin/env python3
"""
Audit T027: Stub Argument Validation

Constitutional Requirement: Consult Perl reference before implementation.

Perl References Consulted:
- sqitch/lib/App/Sqitch/Command/*.pm: All command implementations
- sqitch/t/*.t: Tests showing stub commands validate args before "not implemented"

Audit Objective:
Verify stub commands (those returning "not implemented" or similar) properly validate
arguments BEFORE showing the "not implemented" message. This ensures:
  - Invalid args exit with code 2 (usage error) - user gets immediate feedback
  - Valid args reach "not implemented" and exit with code 1 (operational error)

Per Sqitch convention, even unimplemented commands should validate their arguments.

Output: Markdown report at specs/003-ensure-all-commands/audit-stub-validation.md
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Commands to audit (from spec.md FR-001)
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

# Patterns indicating "not implemented" stubs
STUB_PATTERNS = [
    "not implemented",
    "not yet implemented",
    "coming soon",
    "todo",
    "placeholder",
    "raise NotImplementedError",
]


class StubVisitor(ast.NodeVisitor):
    """AST visitor to find stub implementations and their validation."""

    def __init__(self):
        self.is_stub = False
        self.stub_line = None
        self.stub_type = None
        self.has_click_decorators = False
        self.click_options: List[str] = []
        self.has_arg_validation = False
        self.validation_line = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to find command entry points."""
        # Check if function has Click decorators (indicates it's a command)
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr in ("command", "option", "argument"):
                        self.has_click_decorators = True
                    if decorator.func.attr == "option":
                        # Extract option name
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            self.click_options.append(decorator.args[0].value)

        # Check function body for stub patterns
        for stmt in ast.walk(node):
            # String literals containing stub messages
            if isinstance(stmt, ast.Constant) and isinstance(stmt.value, str):
                for pattern in STUB_PATTERNS:
                    if pattern.lower() in stmt.value.lower():
                        self.is_stub = True
                        self.stub_line = stmt.lineno
                        self.stub_type = "message"
                        break

            # NotImplementedError raises
            if isinstance(stmt, ast.Raise):
                if isinstance(stmt.exc, ast.Call):
                    if isinstance(stmt.exc.func, ast.Name):
                        if stmt.exc.func.id == "NotImplementedError":
                            self.is_stub = True
                            self.stub_line = stmt.lineno
                            self.stub_type = "exception"

            # Argument access (indicates validation attempt)
            if isinstance(stmt, ast.Attribute):
                if isinstance(stmt.value, ast.Name):
                    # Accessing arguments/parameters
                    if stmt.value.id in ("args", "kwargs", "ctx"):
                        self.has_arg_validation = True
                        if not self.validation_line:
                            self.validation_line = stmt.lineno

        self.generic_visit(node)


def audit_command_file(command: str, commands_dir: Path) -> Dict[str, any]:
    """
    Audit a single command file for stub validation.

    Returns:
        Dict with stub analysis
    """
    file_path = commands_dir / f"{command}.py"

    if not file_path.exists():
        print(f"⚠️  Warning: Command file not found: {file_path}", file=sys.stderr)
        return {"error": "file_not_found"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))
        visitor = StubVisitor()
        visitor.visit(tree)

        # Analyze validation status
        validation_status = "unknown"
        if not visitor.is_stub:
            validation_status = "n/a - fully implemented"
        elif visitor.has_click_decorators:
            # Click decorators provide automatic validation
            validation_status = "automatic (Click decorators)"
        elif visitor.has_arg_validation:
            validation_status = "manual validation present"
        else:
            validation_status = "no validation detected"

        return {
            "is_stub": visitor.is_stub,
            "stub_line": visitor.stub_line,
            "stub_type": visitor.stub_type,
            "has_click_decorators": visitor.has_click_decorators,
            "click_options": visitor.click_options,
            "validation_status": validation_status,
            "validation_line": visitor.validation_line,
        }

    except Exception as e:
        print(f"❌ Error parsing {file_path}: {e}", file=sys.stderr)
        return {"error": str(e)}


def generate_report(audit_results: Dict[str, Dict], output_path: Path) -> None:
    """Generate markdown audit report."""

    total_commands = len(audit_results)
    stub_commands = sum(1 for r in audit_results.values() if r.get("is_stub", False))
    stubs_with_validation = sum(
        1
        for r in audit_results.values()
        if r.get("is_stub", False) and r.get("has_click_decorators", False)
    )

    lines = [
        "# Audit T027: Stub Argument Validation",
        "",
        f"**Audit Date:** {Path(__file__).stat().st_mtime}",
        f"**Commands Audited:** {total_commands}",
        f"**Stub Commands Found:** {stub_commands}",
        f"**Stubs with Validation:** {stubs_with_validation}",
        "",
        "## Validation Contract",
        "",
        "Per Sqitch convention (from Perl reference), stub commands must:",
        "",
        '1. **Validate arguments BEFORE** showing "not implemented" message',
        "2. **Exit with code 2** if arguments are invalid (usage error)",
        "3. **Exit with code 1** if arguments are valid but command not implemented",
        "",
        "This ensures users get immediate feedback on argument problems, even for unimplemented commands.",
        "",
        "## Summary by Implementation Status",
        "",
        "| Command | Status | Validation | Stub Type |",
        "|---------|--------|------------|-----------|",
    ]

    for command in sorted(audit_results.keys()):
        result = audit_results[command]
        if result.get("error"):
            lines.append(f"| `{command}` | ❌ Error | - | - |")
        elif not result.get("is_stub"):
            lines.append(f"| `{command}` | ✅ Implemented | N/A | - |")
        else:
            validation = result.get("validation_status", "unknown")
            stub_type = result.get("stub_type", "unknown")
            status = "✅" if result.get("has_click_decorators") else "⚠️"
            lines.append(f"| `{command}` | {status} Stub | {validation} | {stub_type} |")

    lines.extend(
        [
            "",
            "## Detailed Findings",
            "",
        ]
    )

    # Group by status
    implemented = []
    stubs_with_click = []
    stubs_without_click = []
    errors = []

    for command, result in audit_results.items():
        if result.get("error"):
            errors.append(command)
        elif not result.get("is_stub"):
            implemented.append(command)
        elif result.get("has_click_decorators"):
            stubs_with_click.append((command, result))
        else:
            stubs_without_click.append((command, result))

    lines.extend(
        [
            f"### ✅ Fully Implemented Commands ({len(implemented)})",
            "",
        ]
    )
    if implemented:
        lines.extend([f"- `{cmd}`" for cmd in sorted(implemented)])
    else:
        lines.append("(none)")
    lines.append("")

    lines.extend(
        [
            f"### ✅ Stubs with Click Validation ({len(stubs_with_click)})",
            "",
            "These stubs properly validate arguments via Click decorators:",
            "",
        ]
    )
    if stubs_with_click:
        for command, result in sorted(stubs_with_click):
            stub_line = result.get("stub_line", "?")
            options = result.get("click_options", [])
            opt_info = f" (options: {', '.join(options)})" if options else ""
            lines.append(f"- **{command}** (line {stub_line}){opt_info}")
    else:
        lines.append("(none)")
    lines.append("")

    lines.extend(
        [
            f"### ⚠️ Stubs Needing Validation Review ({len(stubs_without_click)})",
            "",
            "These stubs may not validate arguments properly:",
            "",
        ]
    )
    if stubs_without_click:
        for command, result in sorted(stubs_without_click):
            stub_line = result.get("stub_line", "?")
            validation = result.get("validation_status", "unknown")
            lines.append(f"- **{command}** (line {stub_line}) - {validation}")
    else:
        lines.append("✅ All stubs use Click validation!")
    lines.append("")

    if errors:
        lines.extend(
            [
                f"### ❌ Errors ({len(errors)})",
                "",
            ]
        )
        lines.extend([f"- `{cmd}`" for cmd in sorted(errors)])
        lines.append("")

    lines.extend(
        [
            "## Compliance Analysis",
            "",
        ]
    )

    if not stubs_without_click:
        lines.extend(
            [
                "✅ **All stub commands properly validate arguments via Click decorators!**",
                "",
                "Click automatically validates:",
                "- Required arguments presence",
                "- Option types and formats",
                "- Mutually exclusive options",
                "",
                "Invalid arguments will exit with code 2 (usage error) before reaching stub message.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"⚠️ **{len(stubs_without_click)} stub commands need validation review**",
                "",
                'These commands show "not implemented" but may not validate arguments first.',
                "Users with invalid arguments might see:",
                '- "Not implemented" (exit 1) instead of',
                '- "Invalid argument X" (exit 2)',
                "",
                "This violates the validation contract and confuses users.",
                "",
            ]
        )

    lines.extend(
        [
            "## Recommendations",
            "",
        ]
    )

    if stubs_without_click:
        lines.extend(
            [
                "1. **Add Click decorators** to stubs without them",
                "2. **Use @click.option()** for all expected arguments, even if not implemented",
                "3. **Test stub validation**: Run stubs with invalid args, expect exit code 2",
                "",
                "### Example Fix Pattern",
                "",
                "**Before:**",
                "```python",
                "def my_command():",
                '    click.echo("Not yet implemented")',
                "    sys.exit(1)",
                "```",
                "",
                "**After:**",
                "```python",
                "@click.command()",
                "@click.option('--required-arg', required=True, help='Description')",
                "@click.option('--optional-flag', is_flag=True, help='Description')",
                "def my_command(required_arg: str, optional_flag: bool):",
                '    click.echo("Not yet implemented")',
                "    sys.exit(1)",
                "```",
                "",
                "Now Click validates `--required-arg` before reaching stub message.",
            ]
        )
    else:
        lines.extend(
            [
                "✅ **No action needed** - all stubs properly validate arguments!",
                "",
                "Continue following this pattern for future stub commands:",
                "1. Define Click decorators matching Perl command signature",
                "2. Let Click handle automatic validation",
                "3. Stub message only appears for valid arguments",
            ]
        )

    lines.append("")

    # Write report
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ Audit report written to: {output_path}")


def main() -> int:
    """Run stub validation audit."""
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    commands_dir = project_root / "sqlitch" / "cli" / "commands"
    output_dir = project_root / "specs" / "003-ensure-all-commands"
    output_path = output_dir / "audit-stub-validation.md"

    if not commands_dir.exists():
        print(f"❌ Commands directory not found: {commands_dir}", file=sys.stderr)
        return 1

    print("🔍 Auditing stub argument validation across all commands...")
    print(f"📁 Commands directory: {commands_dir}")
    print(f"📋 Output report: {output_path}")
    print()

    # Audit each command
    audit_results = {}
    for command in COMMANDS:
        results = audit_command_file(command, commands_dir)
        audit_results[command] = results

        if results.get("error"):
            print(f"❌ {command:12s} - Error: {results['error']}")
        elif not results.get("is_stub"):
            print(f"✅ {command:12s} - Fully implemented")
        elif results.get("has_click_decorators"):
            print(f"✅ {command:12s} - Stub with Click validation")
        else:
            print(f"⚠️  {command:12s} - Stub needs validation review")

    print()

    # Generate report
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_report(audit_results, output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
