# Command Contract: `sqlitch config`

## Purpose
Read and modify SQLitch configuration values across system, user, and local scopes, acting as a drop-in replacement for `sqitch config`.

## Inputs
- **Invocation**:
  - Get: `sqlitch config [--global|--user|--local|--registry] <name>`
  - Set: `sqlitch config [--global|--user|--local|--registry] <name> <value>`
  - Unset: `sqlitch config --unset [scope flags] <name>`
  - List: `sqlitch config --list`
- **Environment**: honors `SQLITCH_CONFIG_ROOT`, `SQITCH_CONFIG_ROOT`, and `$XDG_CONFIG_HOME` fallbacks.
- **Files**: interacts with `sqlitch.conf`, `sqitch.conf`, and registry configuration tables.

## Behavior
1. Resolve scope precedence identical to Sqitch (local → user → system → registry).
2. Perform type coercion (bool/int/list) to maintain parity with Sqitch serialization.
3. For set/unset, modify appropriate config file without touching others.
4. Support JSON output via `--json` flag with identical schema.

## Outputs
- **STDOUT**: value retrieval or confirmation messages matching Sqitch verbiage.
- **STDERR**: error descriptions (e.g., unknown key) identical to Sqitch.
- **Exit Code**: `0` on success; `1` on validation errors.

## Error Conditions
- Missing key on get → exit 1 `No such option: <name>`.
- Conflicting scope flags → exit 1 `Only one scope option may be specified`.
- Attempting to mutate read-only registry config without privileges → exit 1 replicating Sqitch message.

## Parity Checks
- Config files remain INI-formatted with exact same section/key names.
- CLI help text and examples match `sqitch config --help`.
- Tests assert the same precedence resolution using golden config scenarios.
