# Command Contract: `sqlitch engine`

## Purpose
Manage engine definitions (add, update, remove, list) for SQLitch deployments, mirroring `sqitch engine` semantics and configuration persistence.

## Inputs
- **Invocation**:
  - `sqlitch engine add <name> <uri>`
  - `sqlitch engine update <name> <uri>`
  - `sqlitch engine remove <name>`
  - `sqlitch engine list`
- **Options**: `--registry <uri>`, `--client <path>`, `--plan <plan_file>`, `--verify`, `--no-verify`
- **Environment**: respects `SQLITCH_CONFIG_ROOT`, `SQLITCH_PLAN_FILE`, and engine-specific environment anchors.

## Behavior
1. Parse URIs using same regex/rules as Sqitch (supporting `db:pg:`, `db:mysql:`, `db:sqlite:`).
2. Persist engine definitions into config scope or plan-level engine file.
3. When listing, output tabular representation identical to Sqitch (optional JSON).
4. On add/update, validate engine type is within MVP scope; unsupported types raise immediate error.
5. When removing, confirm deletion unless `--yes` provided.
6. **`engine add` uses upsert semantics** (Sqitch parity): if an engine with the same name already exists, the command succeeds and updates the existing definition rather than raising an error. This allows iterative configuration and matches Sqitch's behavior where `sqitch engine add <name>` can be called multiple times to update the engine URI or options.

## Outputs
- **STDOUT**: success messages matching Sqitch (e.g., `Created engine <name>`).
- **STDERR**: validation errors.
- **Exit Code**: `0` on success; `1` on invalid requests.

## Error Conditions
- Unknown engine on update/remove → exit 1 `Unknown engine "<name>"`.
- Unsupported engine type (outside sqlite/mysql/pg) → exit 1 with parity message.
- **Note**: `engine add` does NOT raise an error for duplicate engine names; it updates the existing definition (upsert behavior).

## Parity Checks
- Formatting of `sqlitch engine list` matches exact Sqitch column widths.
- JSON output structure identical for automation compatibility.
- Config files updated with same key names and quoting as Sqitch.
