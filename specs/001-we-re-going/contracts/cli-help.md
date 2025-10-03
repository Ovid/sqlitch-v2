# Command Contract: `sqlitch help`

## Purpose
Display command-specific or concept-specific documentation identical to Sqitch’s POD-derived help system, including guide listings and command summaries.

## Inputs
- **Invocation**: `sqlitch help [<command_or_guide>] [--man] [--usage]`
- **Environment**: respects `PAGER`, `MANWIDTH`, and locale variables; aligns with Sqitch fallback logic when pager unavailable.
- **Files**: consumes documentation under `lib/sqlitchdocs/` (mirroring Sqitch `lib/sqitch`).

## Behavior
1. Without arguments, display high-level command list identical to Sqitch (alphabetized, grouped).
2. With `<command>`, output usage, options, and descriptions exactly matching Sqitch text (ported from POD sources).
3. `--usage` prints single-line usage summary, `--man` opens full manual via pager.
4. Guides resolved via alias mapping with parity to Sqitch.

## Outputs
- **STDOUT**: Help text matching Sqitch (spacing, indentation, ANSI codes).
- **STDERR**: error for unknown topic `No help for "<topic>"`.
- **Exit Code**: `0` on success; `1` for unknown topics.

## Error Conditions
- Missing documentation file → exit 1 with message `Cannot load help for <topic>`.
- Pager failure → fallback to direct stdout (log warning identical to Sqitch).

## Parity Checks
- Regression tests compare rendered help output against Sqitch golden files per command.
- Locale-specific behavior (UTF-8 glyphs) verified across CI matrix.
