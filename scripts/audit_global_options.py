#!/usr/bin/env python3
"""
Audit T025: Global Options Coverage Across All Commands

Constitutional Requirement: Consult Perl reference before implementation.

Perl References Consulted:
- sqitch/lib/App/Sqitch.pm (lines 1-300): Global options defined in base class
- sqitch/lib/sqitch.pod (OPTIONS section): Documents --quiet, --verbose, --chdir, --no-pager
- sqitch/bin/sqitch (lines 1-100): Entry point showing global option parsing

Audit Objective:
Verify all 19 Sqitch commands accept the 4 required global options:
  --chdir <path>
  --no-pager
  --quiet
  --verbose

Output: Markdown report at specs/003-ensure-all-commands/audit-global-options.md
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set

# Commands to audit (from spec.md FR-001)
COMMANDS = [
    "add", "bundle", "checkout", "config", "deploy", "engine",
    "help", "init", "log", "plan", "rebase", "revert", "rework",
    "show", "status", "tag", "target", "upgrade", "verify"
]

# Required global options (from spec.md FR-005)
REQUIRED_GLOBAL_OPTIONS = {"chdir", "no_pager", "quiet", "verbose"}


class GlobalOptionVisitor(ast.NodeVisitor):
    """AST visitor to find Click option decorators in command files."""
    
    def __init__(self):
        self.options: Set[str] = set()
        self.command_function: str | None = None
        
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to find command entry points."""
        # Look for functions decorated with @click.command or similar
        has_command_decorator = any(
            isinstance(d, ast.Call) and 
            isinstance(d.func, ast.Attribute) and
            d.func.attr in ("command", "group")
            for d in node.decorator_list
        )
        
        if has_command_decorator or node.name in ("cli", "main", COMMANDS):
            self.command_function = node.name
            
            # Extract option decorators
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == "option":
                            # Extract option name from first argument
                            if decorator.args:
                                first_arg = decorator.args[0]
                                if isinstance(first_arg, ast.Constant):
                                    opt_name = first_arg.value.lstrip("-").replace("-", "_")
                                    self.options.add(opt_name)
        
        self.generic_visit(node)


def audit_command_file(command: str, commands_dir: Path) -> Dict[str, bool]:
    """
    Audit a single command file for global options.
    
    Returns:
        Dict mapping option name to presence (True) or absence (False)
    """
    file_path = commands_dir / f"{command}.py"
    
    if not file_path.exists():
        print(f"⚠️  Warning: Command file not found: {file_path}", file=sys.stderr)
        return {opt: False for opt in REQUIRED_GLOBAL_OPTIONS}
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(file_path))
        visitor = GlobalOptionVisitor()
        visitor.visit(tree)
        
        # Check which required options are present
        result = {}
        for opt in REQUIRED_GLOBAL_OPTIONS:
            result[opt] = opt in visitor.options
        
        return result
        
    except Exception as e:
        print(f"❌ Error parsing {file_path}: {e}", file=sys.stderr)
        return {opt: False for opt in REQUIRED_GLOBAL_OPTIONS}


def generate_report(audit_results: Dict[str, Dict[str, bool]], output_path: Path) -> None:
    """Generate markdown audit report."""
    
    # Calculate summary statistics
    total_commands = len(audit_results)
    commands_missing_any = sum(
        1 for results in audit_results.values() 
        if not all(results.values())
    )
    
    option_gaps = {opt: 0 for opt in REQUIRED_GLOBAL_OPTIONS}
    for results in audit_results.values():
        for opt, present in results.items():
            if not present:
                option_gaps[opt] += 1
    
    # Generate report
    lines = [
        "# Audit T025: Global Options Coverage",
        "",
        f"**Audit Date:** {Path(__file__).stat().st_mtime}",
        f"**Commands Audited:** {total_commands}",
        f"**Commands with Gaps:** {commands_missing_any} ({commands_missing_any/total_commands*100:.1f}%)",
        "",
        "## Summary",
        "",
        "Required global options (from spec.md FR-005):",
        "- `--chdir <path>`: Change working directory before executing command",
        "- `--no-pager`: Disable pager output",
        "- `--quiet`: Suppress informational messages",
        "- `--verbose`: Increase verbosity",
        "",
        "### Gap Summary by Option",
        "",
        "| Option | Commands Missing | Coverage |",
        "|--------|------------------|----------|",
    ]
    
    for opt in sorted(REQUIRED_GLOBAL_OPTIONS):
        missing = option_gaps[opt]
        coverage = (total_commands - missing) / total_commands * 100
        lines.append(f"| `--{opt.replace('_', '-')}` | {missing}/{total_commands} | {coverage:.1f}% |")
    
    lines.extend([
        "",
        "## Detailed Results",
        "",
        "| Command | --chdir | --no-pager | --quiet | --verbose | Status |",
        "|---------|---------|------------|---------|-----------|--------|",
    ])
    
    for command in sorted(audit_results.keys()):
        results = audit_results[command]
        chdir = "✅" if results["chdir"] else "❌"
        no_pager = "✅" if results["no_pager"] else "❌"
        quiet = "✅" if results["quiet"] else "❌"
        verbose = "✅" if results["verbose"] else "❌"
        status = "✅ PASS" if all(results.values()) else "❌ GAPS"
        
        lines.append(f"| `{command}` | {chdir} | {no_pager} | {quiet} | {verbose} | {status} |")
    
    lines.extend([
        "",
        "## Commands Requiring Fixes",
        "",
    ])
    
    commands_needing_fixes = [
        cmd for cmd, results in audit_results.items()
        if not all(results.values())
    ]
    
    if commands_needing_fixes:
        lines.append(f"**{len(commands_needing_fixes)} commands** need global option fixes:")
        lines.append("")
        for cmd in sorted(commands_needing_fixes):
            missing_opts = [
                f"`--{opt.replace('_', '-')}`"
                for opt, present in audit_results[cmd].items()
                if not present
            ]
            lines.append(f"- **{cmd}**: Missing {', '.join(missing_opts)}")
    else:
        lines.append("✅ **All commands support all global options!**")
    
    lines.extend([
        "",
        "## Recommendations",
        "",
    ])
    
    if commands_needing_fixes:
        lines.extend([
            f"1. **Create T028 fix task** to add missing global options to {len(commands_needing_fixes)} commands",
            "2. **Implementation approach**: Add decorators to command functions in `sqlitch/cli/commands/*.py`",
            "3. **Validation**: Re-run regression tests T020-T021 after fixes",
            "",
            "### Perl Reference Pattern",
            "",
            "From `sqitch/lib/App/Sqitch.pm` (base class for all commands):",
            "```perl",
            "has plan_file => (",
            "    is      => 'ro',",
            "    isa     => Str,",
            "    lazy    => 1,",
            "    default => sub { shift->config->get(key => 'core.plan_file') || 'sqitch.plan' },",
            ");",
            "",
            "has verbosity => (",
            "    is      => 'ro',",
            "    isa     => Int,",
            "    default => 1,  # 0=quiet, 1=normal, 2+=verbose",
            ");",
            "```",
            "",
            "Global options are inherited by all commands through base class.",
        ])
    else:
        lines.append("✅ No fixes needed - all commands have full global option support!")
    
    lines.append("")
    
    # Write report
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"✅ Audit report written to: {output_path}")


def main() -> int:
    """Run global options audit."""
    # Find project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    commands_dir = project_root / "sqlitch" / "cli" / "commands"
    output_dir = project_root / "specs" / "003-ensure-all-commands"
    output_path = output_dir / "audit-global-options.md"
    
    if not commands_dir.exists():
        print(f"❌ Commands directory not found: {commands_dir}", file=sys.stderr)
        return 1
    
    print("🔍 Auditing global options across all commands...")
    print(f"📁 Commands directory: {commands_dir}")
    print(f"📋 Output report: {output_path}")
    print()
    
    # Audit each command
    audit_results = {}
    for command in COMMANDS:
        results = audit_command_file(command, commands_dir)
        audit_results[command] = results
        
        status = "✅" if all(results.values()) else "❌"
        missing = [opt for opt, present in results.items() if not present]
        if missing:
            print(f"{status} {command:12s} - Missing: {', '.join(f'--{o.replace('_', '-')}' for o in missing)}")
        else:
            print(f"{status} {command:12s} - All global options present")
    
    print()
    
    # Generate report
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_report(audit_results, output_path)
    
    # Exit with status
    commands_with_gaps = sum(1 for r in audit_results.values() if not all(r.values()))
    if commands_with_gaps > 0:
        print(f"\n⚠️  Found {commands_with_gaps} commands with missing global options")
        return 0  # Not a failure - audit completed successfully
    else:
        print("\n✅ All commands support all global options!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
