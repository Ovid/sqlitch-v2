# Audit T026: Exit Code Usage

**Audit Date:** 1759687355.248572
**Commands Audited:** 19
**Commands with Explicit Exits:** 0

## Exit Code Contract (GC-003)

From Perl reference (`sqitch/lib/App/Sqitch/Command.pm`):

- **Exit 0**: Success - command executed without errors
- **Exit 1**: Operational error - user mistakes, validation failures, resource not found
- **Exit 2**: Usage error - invalid arguments, missing required params, parse errors

## Summary

### Commands with Explicit Exit Handling

| Command | sys.exit() | click.Exit() | Exceptions | Total LOC |
|---------|------------|--------------|------------|-----------|
| `add` | 0 | 0 | 0 | 278 |
| `bundle` | 0 | 0 | 0 | 145 |
| `checkout` | 0 | 0 | 0 | 174 |
| `config` | 0 | 0 | 0 | 552 |
| `deploy` | 0 | 0 | 0 | 1195 |
| `engine` | 0 | 0 | 0 | 306 |
| `help` | 0 | 0 | 0 | 116 |
| `init` | 0 | 0 | 0 | 266 |
| `log` | 0 | 0 | 0 | 345 |
| `plan` | 0 | 0 | 1 | 304 |
| `rebase` | 0 | 0 | 0 | 255 |
| `revert` | 0 | 0 | 0 | 227 |
| `rework` | 0 | 0 | 0 | 212 |
| `show` | 0 | 0 | 0 | 230 |
| `status` | 0 | 0 | 0 | 482 |
| `tag` | 0 | 0 | 0 | 183 |
| `target` | 0 | 0 | 0 | 240 |
| `upgrade` | 0 | 0 | 0 | 46 |
| `verify` | 0 | 0 | 0 | 55 |

## Detailed Findings

### ⚪ add (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ bundle (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ checkout (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ config (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ deploy (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ engine (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ help (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ init (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ log (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### plan

**Exception raises:**
- Line 110: `raise engine_error`

### ⚪ rebase (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ revert (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ rework (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ show (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ status (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ tag (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ target (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ upgrade (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

### ⚪ verify (no explicit exits)

Command relies on Click's default exit behavior (0 on success, non-zero on exception).

## Compliance Analysis

### ✅ Likely Compliant

Commands relying on Click's default behavior (no explicit exits) are likely compliant:
- Click automatically exits with 0 on success
- Click automatically exits with 2 on usage errors (via `click.UsageError`)
- Unhandled exceptions exit with 1

### ⚠️ Needs Manual Review

Commands with explicit exit codes should be reviewed to ensure:
1. Exit code 0 only used for successful completion
2. Exit code 1 used for operational errors (not usage errors)
3. Exit code 2 used for usage/parsing errors

✅ All commands use Click's default exit behavior!

## Recommendations

1. **Manual review** commands with explicit exit codes to verify GC-003 compliance
2. **Convert to Click patterns**: Replace `sys.exit(2)` with `raise click.UsageError(message)`
3. **Use Click exceptions**: Prefer `click.ClickException` over `sys.exit(1)` for operational errors
4. **Test exit codes**: Add regression tests to verify exit code contract (already in T022)

### Perl Reference Pattern

From `sqitch/lib/App/Sqitch/Command.pm`:
```perl
sub execute {
    my $self = shift;
    hurl 'Command not implemented';  # Dies with exit 1
}

# Usage errors (exit 2) are handled by Getopt::Long
# Success (exit 0) is implicit return from execute()
```
