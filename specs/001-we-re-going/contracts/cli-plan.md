# Command Contract: `sqlitch plan`

## Purpose
Display, diff, or amend the SQLitch deployment plan without mutating registry state, matching `sqitch plan` behavior.

## Inputs
- **Invocation**: `sqlitch plan [--project <name>] [--change <name>] [--tag <tag>] [--format human|json] [--short] [--no-header]`
- **Environment**: respects `SQLITCH_PLAN_FILE`, `SQITCH_PLAN_FILE`, `SQLITCH_CONFIG_ROOT`.

## Behavior
1. Parse plan file using ported Sqitch grammar (supports comments, dependencies, tags).
2. Output plan entries in requested format; `--short` truncates notes, `--no-header` removes metadata line.
3. `--change` / `--tag` limits output to matching entry along with dependencies if required.
4. JSON output returns sequence of objects with change metadata identical to Sqitch.

## Outputs
- **STDOUT**: plan content; identical wording, indentation, and spacing.
- **STDERR**: parse errors referencing line numbers.
- **Exit Code**: `0` on success; `1` on parse/validation failure.

## Error Conditions
- Missing plan file → exit 1 `Cannot find plan file` with resolved search path.
- Both `sqlitch.plan` and `sqitch.plan` present → exit 1 with conflict warning.
- Malformed entry (e.g., dependency on unknown change) → exit 1 matching Sqitch message.

## Parity Checks
- Golden file comparison ensures identical output for sample plans.
- JSON schema validated against Sqitch reference output.
