# Command Contract: `sqlitch target`

## Purpose
Manage target aliases that map to deployment URIs, replicating `sqitch target` command behavior.

## Inputs
- **Invocation**:
  - Add: `sqlitch target add <name> <uri>`
  - Update: `sqlitch target alter <name> <uri>`
  - Show: `sqlitch target show <name>`
  - Remove: `sqlitch target remove <name>`
  - List: `sqlitch target list`
- **Options**: `--registry <uri>`, `--engine <engine>`, `--user <scope>`, `--password-prompt`.
- **Environment**: `SQLITCH_CONFIG_ROOT`, `SQITCH_CONFIG_ROOT`, engine-specific env variables.

## Behavior
1. Persist target definitions in configuration scope using same precedence and file structure as Sqitch.
2. Validate engine compatibility (sqlite/mysql/pg only) and canonicalize URIs.
3. Provide interactive prompts consistent with Sqitch when `--password-prompt` used.
4. Listing outputs columns (`Name`, `Engine`, `Registry`) matching Sqitch formatting; JSON available via `--json`.

## Outputs
- **STDOUT**: success confirmations or listings identical to Sqitch messages.
- **STDERR**: validation errors.
- **Exit Code**: `0` on success; `1` on failure.

## Error Conditions
- Duplicate target name on add → exit 1 `Target "<name>" already exists`.
- Unknown target on show/remove → exit 1 `Unknown target "<name>"`.
- Unsupported engine type → exit 1 parity message.

## Parity Checks
- Config serialization validated against Sqitch using fixture comparisons.
- CLI help text and options identical to `sqitch target --help`.
