# T028 Implementation Guide: Global Options Infrastructure

**Status**: PARTIAL - `add` command complete, 18 commands remaining  
**Date**: 2025-10-05  
**Constitutional Requirement**: Fix code to make tests pass (Principle I)

---

## Summary

Successfully implemented global options (`--chdir`, `--no-pager`, `--quiet`, `--verbose`) for the `add` command. Pattern validated and working - all 11 contract tests for `add` now pass.

**Remaining Work**: Apply same pattern to 18 other commands.

---

## Implementation Pattern (Validated)

### Step 1: Update `sqlitch/cli/options.py` ✅ COMPLETE

Added `global_sqitch_options` decorator:
```python
def global_sqitch_options(func: F) -> F:
    """Apply global Sqitch-compatible options."""
    func = click.option("-C", "--chdir", ...)(func)
    func = click.option("--no-pager", ...)(func)
    return cast(F, func)
```

### Step 2: Update `sqlitch/cli/main.py` ✅ COMPLETE

Added global options to main CLI group:
- `--chdir` with `os.chdir()` handling
- `--no-pager` stored in context meta

### Step 3: Apply to Each Command (1/19 complete)

**Pattern for each command file** (`sqlitch/cli/commands/*.py`):

1. **Add imports**:
   ```python
   from ..options import global_output_options, global_sqitch_options
   ```

2. **Add decorators** (before `@click.pass_context`):
   ```python
   @global_sqitch_options
   @global_output_options
   @click.pass_context
   ```

3. **Add parameters** to function signature:
   ```python
   def command_name(
       ctx: click.Context,
       *,  # existing positional args
       json_mode: bool,  # from global_output_options
       verbose: int,     # from global_output_options
       quiet: bool,      # from global_output_options
       # ... rest of parameters
   ) -> None:
   ```

---

## Commands Status

### ✅ Complete (1/19)
- `add` - All 11 tests passing

### ⏸️ Pending (18/19)
- `bundle`
- `checkout` (stub)
- `config`
- `deploy`
- `engine`
- `help`
- `init`
- `log`
- `plan`
- `rebase` (stub)
- `revert` (stub)
- `rework`
- `show`
- `status`
- `tag`
- `target`
- `upgrade` (stub)
- `verify` (stub)

---

## Test Results After Partial Implementation

### Before T028
- **Failing**: 10 tests (all global options related)
- **Passing**: 26 tests
- **Skipped**: 12 tests

### After Partial T028 (`add` only)
- **Failing**: 5 tests (other commands still need global options)
- **Passing**: 31 tests (+5 from `add` command)
- **Skipped**: 12 tests

**Remaining Failures**:
1. `test_gc_002_all_commands_accept_chdir` - bundle,  checkout, config, etc.
2. `test_gc_002_all_commands_accept_no_pager` - bundle, checkout, config, etc.
3. `test_gc_002_all_commands_accept_verbose` - bundle, checkout, config, etc.
4. `test_gc_002_all_commands_accept_quiet` - bundle, checkout, config, etc.
5. `test_global_options_do_not_cause_parsing_errors` - plan command

---

## Quick Implementation Script

For each command in `COMMANDS_DIR/sqlitch/cli/commands/`:

```bash
# Template for manual updates (repeat for each command)
COMMAND="bundle"  # Change for each command

# 1. Add imports after existing imports
# Add: from ..options import global_output_options, global_sqitch_options

# 2. Find the @click.command() decorator block
# Add before @click.pass_context:
#   @global_sqitch_options
#   @global_output_options

# 3. Update function signature to accept:
#   json_mode: bool, verbose: int, quiet: bool
```

---

## Validation

After updating each command, run:
```bash
# Test specific command
pytest tests/cli/commands/test_<command>_contract.py -v

# Test all global options
pytest tests/regression/test_global_options_parity.py -v

# Full regression
pytest tests/regression/ tests/cli/commands/test_add_contract.py
```

**Expected Final State**:
- 0 failures related to global options
- All 19 commands accept `--chdir`, `--no-pager`, `--quiet`, `--verbose`

---

## Constitutional Compliance

✅ **Following Test Failure Validation Protocol**:
1. ✅ Perl reference consulted (audit T025 complete)
2. ✅ Tests validated as correct
3. ⏸️ **Fixing code** (T028 in progress - 1/19 commands complete)
4. N/A - No test modifications needed

✅ **TDD Red → Green Cycle**:
- Red: Tests written and failing (T001, T020-T024)
- **Green (in progress)**: Implementing to make tests pass (T028 - 5% complete)
- Refactor: After all tests pass

---

## Time Estimate

- **Per command**: ~5 minutes (find decorators, add imports, update signature)
- **Total remaining**: ~90 minutes for 18 commands
- **Testing time**: ~30 minutes (incremental validation)
- **Total**: ~2 hours to complete T028

---

## Recommendation

Complete T028 by applying the validated pattern to all 18 remaining commands. The pattern is proven (add command tests all pass), implementation is straightforward, and will immediately fix all remaining global options test failures.

**Next Command to Update**: `plan` (causes parsing error test failure)
