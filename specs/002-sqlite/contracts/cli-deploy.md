# Command Contract: `sqlitch deploy`

## Purpose
Apply planned database changes to a target database registry, ensuring changes run in order with identical behavior to `sqitch deploy`.

## Inputs
- **Invocation**: `sqlitch deploy [--target <target>] [--to-change <change>] [--to-tag <tag>] [--no-verify] [--verify-all] [--mode (change|tag|all)] [--registry <registry_target>] [--log-only] [--set <name=value>]...`
- **Environment**: inherits `SQLITCH_TARGET`, `SQLITCH_REGISTRY`, `SQITCH_TARGET`, `SQITCH_REGISTRY`, and Docker-related overrides.
- **Dependencies**: Requires database access credentials; may start Docker containers for MySQL/PostgreSQL.

## Behavior
1. Load plan and registry state, computing required changes.
2. For each change, execute deploy script within transaction boundaries consistent with Sqitch (per-engine transaction semantics).
3. Record deployment metadata in registry tables, including `change_id`, timestamps, planner info.
4. Optionally run verify scripts (`--no-verify` disables, `--verify-all` re-verifies).
5. Respect `--log-only` by printing actions without executing scripts.
6. Emit progress output step-by-step matching Sqitch (e.g., `Deploying change ...`).

## Outputs
- **STDOUT**: structured log identical to Sqitch with deterministic timestamps.
- **STDERR**: script errors or connection issues as surfaced by engine adapters.
- **Exit Code**: `0` on success; >0 with final error summary on failure.

## Error Conditions
- Missing target → exit 1 `No such target: <name>`.
- Failed deploy script → exit 1 after rolling back change, message identical to Sqitch (includes change name and SQL error snippet).
- Registry unreachable → exit 1 with driver-specific but normalized message.
- Mixed `--to-change`/`--to-tag` usage invalid → exit 1 matching Sqitch validation.

## Parity Checks
- Deploy order, transaction handling, and messaging validated against Sqitch golden runs.
- Registry schema migrations executed automatically before deploy if needed (same SQL as Sqitch).
- Docker-backed engines share same default container names and environment variables as documented.
