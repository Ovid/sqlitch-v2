# Command Contract: `sqlitch init`

## Purpose
Initialize a new SQLitch project, creating default configuration, directory layout, and plan file consistent with `sqitch init`.

## Inputs
- **Invocation**: `sqlitch init [<project_name>] [--engine sqlite|pg|mysql] [--top-dir <path>] [--plan-file <path>] [--target <target_name>]`
- **Environment**: honors `SQLITCH_TOP_DIR`, `SQITCH_PLAN_FILE`, `SQLITCH_CONFIG_ROOT`.

## Behavior
1. Determine project name (CLI argument or directory name) and create plan file `sqlitch.plan` unless `--plan-file` specified.
2. Create directories `deploy/`, `revert/`, `verify/`, and `etc/` templates with same default contents as Sqitch.
3. Write initial config files with default engine target and registry settings.
4. For compatibility, detect existing `sqitch.*` files—if found without SQLitch equivalents, reuse them; if both sets exist, throw conflict error.
5. Emit summary of created files identical to Sqitch output.

## Outputs
- **STDOUT**: lines describing created plan, directories, config (mirroring Sqitch phrasing).
- **STDERR**: error descriptions.
- **Exit Code**: `0` on success; non-zero otherwise.

## Error Conditions
- Directory not empty and `--force` not supplied (if implemented) → exit 1 as Sqitch.
- Invalid engine selection (outside sqlite/mysql/pg) → exit 1 with parity message.
- Permissions issues writing directories or config → exit 1 with OS error forwarded.

## Parity Checks
- Directory and file layout matches Sqitch baseline (verified via fixture comparison).
- Plan header identical (including project name, timestamp, user info).
- Option parsing and help replicate `sqitch init --help`.
