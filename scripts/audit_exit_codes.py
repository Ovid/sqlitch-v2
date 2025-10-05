#!/usr/bin/env python3
"""
Audit T026: Exit Code Usage Across All Commands

Constitutional Requirement: Consult Perl reference before implementation.

Perl References Consulted:
- sqitch/lib/App/Sqitch.pm (lines 200-300): Exit code handling in base class
- sqitch/lib/App/Sqitch/Command.pm (lines 1-100): Command exit patterns
- sqitch/t/*.t: Test files showing expected exit codes (0=success, 1=error, 2=usage)

Audit Objective:
Verify all 19 Sqitch commands follow exit code contract (GC-003):
  - 0: Success (command executed without errors)
  - 1: Operational error (user error, validation failure, resource not found)
  - 2: Usage error (invalid arguments, missing required params, parse errors)

Output: Markdown report at specs/003-ensure-all-commands/audit-exit-codes.md
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Commands to audit (from spec.md FR-001)
COMMANDS = [
    "add", "bundle", "checkout", "config", "deploy", "engine",
    "help", "init", "log", "plan", "rebase", "revert", "rework",
    "show", "status", "tag", "target", "upgrade", "verify"
]


class ExitCodeVisitor(ast.NodeVisitor):
    """AST visitor to find exit code usage in command files."""
    
    def __init__(self):
        self.exit_calls: List[Tuple[int, str, str]] = []  # (lineno, exit_type, code_value)
        self.exceptions_raised: List[Tuple[int, str]] = []  # (lineno, exception_type)
        self.click_exits: List[Tuple[int, str]] = []  # (lineno, code_value)
        
    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to find exit-related calls."""
        # sys.exit(code)
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id == "sys" and 
                node.func.attr == "exit"):
                code = self._extract_exit_code(node)
                self.exit_calls.append((node.lineno, "sys.exit", code))
        
        # click.Exit(code)
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id == "click" and 
                node.func.attr == "Exit"):
                code = self._extract_exit_code(node)
                self.click_exits.append((node.lineno, code))
        
        # raise SystemExit(code)
        if isinstance(node.func, ast.Name):
            if node.func.id == "SystemExit":
                code = self._extract_exit_code(node)
                self.exceptions_raised.append((node.lineno, f"SystemExit({code})"))
        
        self.generic_visit(node)
    
    def visit_Raise(self, node: ast.Raise) -> None:
        """Visit raise statements to find SystemExit."""
        if node.exc:
            if isinstance(node.exc, ast.Call):
                if isinstance(node.exc.func, ast.Name):
                    if node.exc.func.id == "SystemExit":
                        code = self._extract_exit_code(node.exc)
                        self.exceptions_raised.append((node.lineno, f"SystemExit({code})"))
            elif isinstance(node.exc, ast.Name):
                # raise existing exception variable
                self.exceptions_raised.append((node.lineno, node.exc.id))
        
        self.generic_visit(node)
    
    def _extract_exit_code(self, node: ast.Call) -> str:
        """Extract exit code from call arguments."""
        if not node.args:
            return "0 (implicit)"
        
        arg = node.args[0]
        if isinstance(arg, ast.Constant):
            return str(arg.value)
        elif isinstance(arg, ast.Name):
            return f"<var:{arg.id}>"
        elif isinstance(arg, ast.BinOp):
            return "<expression>"
        else:
            return "<complex>"


def audit_command_file(command: str, commands_dir: Path) -> Dict[str, any]:
    """
    Audit a single command file for exit code usage.
    
    Returns:
        Dict with exit code analysis
    """
    file_path = commands_dir / f"{command}.py"
    
    if not file_path.exists():
        print(f"⚠️  Warning: Command file not found: {file_path}", file=sys.stderr)
        return {"error": "file_not_found"}
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(file_path))
        visitor = ExitCodeVisitor()
        visitor.visit(tree)
        
        return {
            "exit_calls": visitor.exit_calls,
            "exceptions": visitor.exceptions_raised,
            "click_exits": visitor.click_exits,
            "has_explicit_exits": len(visitor.exit_calls) > 0 or len(visitor.click_exits) > 0,
            "line_count": len(source.splitlines()),
        }
        
    except Exception as e:
        print(f"❌ Error parsing {file_path}: {e}", file=sys.stderr)
        return {"error": str(e)}


def generate_report(audit_results: Dict[str, Dict], output_path: Path) -> None:
    """Generate markdown audit report."""
    
    total_commands = len(audit_results)
    commands_with_exits = sum(1 for r in audit_results.values() if r.get("has_explicit_exits", False))
    
    lines = [
        "# Audit T026: Exit Code Usage",
        "",
        f"**Audit Date:** {Path(__file__).stat().st_mtime}",
        f"**Commands Audited:** {total_commands}",
        f"**Commands with Explicit Exits:** {commands_with_exits}",
        "",
        "## Exit Code Contract (GC-003)",
        "",
        "From Perl reference (`sqitch/lib/App/Sqitch/Command.pm`):",
        "",
        "- **Exit 0**: Success - command executed without errors",
        "- **Exit 1**: Operational error - user mistakes, validation failures, resource not found",
        "- **Exit 2**: Usage error - invalid arguments, missing required params, parse errors",
        "",
        "## Summary",
        "",
        "### Commands with Explicit Exit Handling",
        "",
        "| Command | sys.exit() | click.Exit() | Exceptions | Total LOC |",
        "|---------|------------|--------------|------------|-----------|",
    ]
    
    for command in sorted(audit_results.keys()):
        result = audit_results[command]
        if result.get("error"):
            lines.append(f"| `{command}` | ❌ Error | ❌ Error | ❌ Error | - |")
        else:
            sys_exits = len(result.get("exit_calls", []))
            click_exits = len(result.get("click_exits", []))
            exceptions = len(result.get("exceptions", []))
            loc = result.get("line_count", 0)
            
            lines.append(f"| `{command}` | {sys_exits} | {click_exits} | {exceptions} | {loc} |")
    
    lines.extend([
        "",
        "## Detailed Findings",
        "",
    ])
    
    for command in sorted(audit_results.keys()):
        result = audit_results[command]
        if result.get("error"):
            lines.append(f"### ❌ {command}")
            lines.append(f"Error: {result['error']}")
            lines.append("")
            continue
        
        exit_calls = result.get("exit_calls", [])
        click_exits = result.get("click_exits", [])
        exceptions = result.get("exceptions", [])
        
        if not exit_calls and not click_exits and not exceptions:
            lines.append(f"### ⚪ {command} (no explicit exits)")
            lines.append("")
            lines.append("Command relies on Click's default exit behavior (0 on success, non-zero on exception).")
            lines.append("")
        else:
            lines.append(f"### {command}")
            lines.append("")
            
            if exit_calls:
                lines.append("**sys.exit() calls:**")
                for lineno, exit_type, code in exit_calls:
                    lines.append(f"- Line {lineno}: `{exit_type}({code})`")
                lines.append("")
            
            if click_exits:
                lines.append("**click.Exit() calls:**")
                for lineno, code in click_exits:
                    lines.append(f"- Line {lineno}: `click.Exit({code})`")
                lines.append("")
            
            if exceptions:
                lines.append("**Exception raises:**")
                for lineno, exc_type in exceptions:
                    lines.append(f"- Line {lineno}: `raise {exc_type}`")
                lines.append("")
    
    lines.extend([
        "## Compliance Analysis",
        "",
        "### ✅ Likely Compliant",
        "",
        "Commands relying on Click's default behavior (no explicit exits) are likely compliant:",
        "- Click automatically exits with 0 on success",
        "- Click automatically exits with 2 on usage errors (via `click.UsageError`)",
        "- Unhandled exceptions exit with 1",
        "",
        "### ⚠️ Needs Manual Review",
        "",
        "Commands with explicit exit codes should be reviewed to ensure:",
        "1. Exit code 0 only used for successful completion",
        "2. Exit code 1 used for operational errors (not usage errors)",
        "3. Exit code 2 used for usage/parsing errors",
        "",
    ])
    
    commands_needing_review = [
        cmd for cmd, result in audit_results.items()
        if result.get("has_explicit_exits", False)
    ]
    
    if commands_needing_review:
        lines.append(f"**{len(commands_needing_review)} commands** need manual review:")
        for cmd in sorted(commands_needing_review):
            lines.append(f"- `{cmd}`")
    else:
        lines.append("✅ All commands use Click's default exit behavior!")
    
    lines.extend([
        "",
        "## Recommendations",
        "",
        "1. **Manual review** commands with explicit exit codes to verify GC-003 compliance",
        "2. **Convert to Click patterns**: Replace `sys.exit(2)` with `raise click.UsageError(message)`",
        "3. **Use Click exceptions**: Prefer `click.ClickException` over `sys.exit(1)` for operational errors",
        "4. **Test exit codes**: Add regression tests to verify exit code contract (already in T022)",
        "",
        "### Perl Reference Pattern",
        "",
        "From `sqitch/lib/App/Sqitch/Command.pm`:",
        "```perl",
        "sub execute {",
        "    my $self = shift;",
        "    hurl 'Command not implemented';  # Dies with exit 1",
        "}",
        "",
        "# Usage errors (exit 2) are handled by Getopt::Long",
        "# Success (exit 0) is implicit return from execute()",
        "```",
        "",
    ])
    
    # Write report
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"✅ Audit report written to: {output_path}")


def main() -> int:
    """Run exit code audit."""
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    commands_dir = project_root / "sqlitch" / "cli" / "commands"
    output_dir = project_root / "specs" / "003-ensure-all-commands"
    output_path = output_dir / "audit-exit-codes.md"
    
    if not commands_dir.exists():
        print(f"❌ Commands directory not found: {commands_dir}", file=sys.stderr)
        return 1
    
    print("🔍 Auditing exit code usage across all commands...")
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
        elif results.get("has_explicit_exits"):
            total_exits = len(results.get("exit_calls", [])) + len(results.get("click_exits", []))
            print(f"⚠️  {command:12s} - {total_exits} explicit exit calls (needs review)")
        else:
            print(f"✅ {command:12s} - Uses Click default behavior")
    
    print()
    
    # Generate report
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_report(audit_results, output_path)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
