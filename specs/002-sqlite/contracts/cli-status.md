# Command Contract: `sqlitch status`

## Purpose
Report the current deployment status for a target database, including plan drift detection, replicating `sqitch status` output.

## Inputs
- **Invocation**: `sqlitch status [--target <target>] [--project <name>] [--quiet] [--verbose] [--format human|json]`
- **Environment**: `SQLITCH_TARGET`, `SQITCH_TARGET`, config overrides.

## Behavior
1. Compare plan head to registry head, determining whether database is ahead/behind/in sync.
2. Provide details on deployed change, project name, registry location, and outstanding changes.
3. JSON format outputs structured status fields identical to Sqitch keys (`status`, `project`, `change`, `timestamp`, `search_path`).
4. `--quiet` reduces output to single line; `--verbose` includes plan summary.

## Outputs
- **STDOUT**: status text exactly matching Sqitch phrasing (e.g., `Project:`, `Change:`, `Deploy ID:`).
- **STDERR**: connection or validation errors.
- **Exit Code**: `0` when database is in sync; `1` when out of sync (matching Sqitch behavior).

## Error Conditions
- Registry unreachable → exit 1 with error message.
- Target missing → exit 1 `Unknown target <name>`.

## Parity Checks
- Golden output comparison for in-sync / ahead / behind scenarios.
- JSON schema validated against Sqitch sample.
- Logging respects verbosity flags and colorization settings.
