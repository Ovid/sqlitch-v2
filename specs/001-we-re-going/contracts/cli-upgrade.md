# Command Contract: `sqlitch upgrade`

## Purpose
Update the registry schema to the latest version, mirroring `sqitch upgrade` behavior.

## Inputs
- **Invocation**: `sqlitch upgrade [--target <target>] [--registry <uri>] [--log-only]`
- **Environment**: `SQLITCH_TARGET`, `SQLITCH_REGISTRY`, `SQITCH_REGISTRY`.

## Behavior
1. Detect current registry version by inspecting metadata tables.
2. Apply sequential migrations using the same SQL scripts Sqitch would execute, adjusted for Python tooling.
3. Log each migration step; `--log-only` prints steps without executing.
4. Handle per-engine differences (SQLite vs MySQL vs PostgreSQL) identically to Sqitch.

## Outputs
- **STDOUT**: `Upgraded registry to version ...` messages identical to Sqitch.
- **STDERR**: migration errors with SQL context.
- **Exit Code**: `0` on success; `1` on failure.

## Error Conditions
- Registry already at latest version with `--log-only`? still exit 0 with message.
- Migration failure (SQL error) → exit 1, rollback where supported, match Sqitch error text.
- Missing registry metadata → exit 1 `Registry not initialized` similar to Sqitch.

## Parity Checks
- Migration scripts diff identical to Sqitch versions.
- Tests validate upgrade from historical fixture registries to ensure parity.
