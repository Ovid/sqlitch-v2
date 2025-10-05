# Quickstart: Complete Sqitch Command Surface Parity

**Date**: 2025-10-05  
**Feature**: 003-ensure-all-commands

## Overview
This quickstart validates that all 19 Sqitch commands are available in SQLitch with proper CLI signatures, help text, and argument validation. It does NOT test full functionality (that's covered by individual command features), only the command surface.

## Prerequisites
- SQLitch installed: `pip install -e .`
- Test environment: Python 3.9+
- Working directory: Repository root

## Test Scenario 1: Command Discovery

### Objective
Verify all 19 Sqitch commands are registered and discoverable.

### Steps

1. **List available commands**:
   ```bash
   sqlitch --help
   ```

2. **Expected output** (excerpt):
   ```
   Commands:
     add        Add a new change to the plan
     bundle     Bundle a Sqitch project for distribution
     checkout   Revert, checkout another VCS branch, and re-deploy changes
     config     Get and set local, user, or system options
     deploy     Deploy changes to a database
     engine     Manage database engine configuration
     help       Display help information about Sqitch commands
     init       Initialize a project
     log        Show change logs for a database
     plan       Show the contents of a plan
     rebase     Revert and redeploy database changes
     revert     Revert changes from a database
     rework     Duplicate a change in the plan and revise its scripts
     show       Show information about changes and tags
     status     Show the current deployment status of a database
     tag        Add or list tags in the plan
     target     Manage target database configuration
     upgrade    Upgrade the registry to the current version
     verify     Verify changes to a database
   ```

3. **Validation**:
   - [ ] All 19 commands listed
   - [ ] Descriptions present for each
   - [ ] No duplicates
   - [ ] Help exits with code 0

## Test Scenario 2: Command Help Text

### Objective
Verify each command responds to `--help` with proper help output.

### Steps

Test each command's help (sample shown for `add`):

1. **Get command help**:
   ```bash
   sqlitch add --help
   ```

2. **Expected output structure**:
   ```
   Usage: sqlitch add [OPTIONS] CHANGE_NAME

     Add a new change to the plan

   Options:
     --note TEXT       A note describing the change
     --requires TEXT   Changes this change requires
     --conflicts TEXT  Changes with which this change conflicts
     --help            Show this message and exit.
   ```

3. **Validation per command**:
   - [ ] Command name in usage line
   - [ ] Required arguments shown (e.g., CHANGE_NAME)
   - [ ] Optional arguments shown
   - [ ] Options listed with descriptions
   - [ ] `--help` option present
   - [ ] Exits with code 0

4. **Repeat for all commands**:
   ```bash
   for cmd in add bundle checkout config deploy engine help init log plan rebase revert rework show status tag target upgrade verify; do
     echo "=== Testing: sqlitch $cmd --help ==="
     sqlitch $cmd --help
     if [ $? -ne 0 ]; then
       echo "ERROR: $cmd help failed"
     fi
   done
   ```

## Test Scenario 3: Global Options Acceptance

### Objective
Verify all commands accept global options without error.

### Steps

1. **Test global options on each command** (sample with `plan`):
   ```bash
   # Test --quiet
   sqlitch plan --quiet
   
   # Test --verbose
   sqlitch plan --verbose
   
   # Test --chdir (may not affect all commands)
   sqlitch plan --chdir /tmp
   
   # Test --no-pager
   sqlitch plan --no-pager
   ```

2. **Expected behavior**:
   - Commands accept options without "unknown option" error
   - Exit code is NOT 2 (option parsing error)
   - May exit 0 (success), 1 (not implemented), or proceed normally

3. **Validation**:
   - [ ] `--quiet` accepted by all commands
   - [ ] `--verbose` accepted by all commands
   - [ ] `--chdir` accepted by all commands
   - [ ] `--no-pager` accepted by all commands
   - [ ] No "Error: No such option" messages

4. **Automated check**:
   ```bash
   for cmd in add bundle checkout config deploy engine help init log plan rebase revert rework show status tag target upgrade verify; do
     for opt in "--quiet" "--verbose" "--no-pager"; do
       echo "Testing: sqlitch $cmd $opt"
       sqlitch $cmd $opt 2>&1 | grep -q "No such option" && echo "FAIL: $cmd $opt" || echo "PASS: $cmd $opt"
     done
   done
   ```

## Test Scenario 4: Required Argument Validation

### Objective
Verify commands with required arguments reject invocations without them.

### Steps

Commands with required arguments:
- `add`: requires CHANGE_NAME
- `checkout`: requires BRANCH
- `rework`: requires CHANGE_NAME

1. **Test `add` without arguments**:
   ```bash
   sqlitch add
   ```

2. **Expected**:
   - Exit code 2 (Click argument parsing error)
   - Error message: "Error: Missing argument 'CHANGE_NAME'"

3. **Test `checkout` without arguments**:
   ```bash
   sqlitch checkout
   ```

4. **Expected**:
   - Exit code 2
   - Error message about missing branch

5. **Test `rework` without arguments**:
   ```bash
   sqlitch rework
   ```

6. **Expected**:
   - Exit code 2
   - Error message about missing change name

7. **Validation**:
   - [ ] Commands reject missing required arguments
   - [ ] Exit code is 2 (parsing error)
   - [ ] Error messages mention the missing argument

## Test Scenario 5: Positional Target Support

### Objective
Verify commands that accept database targets handle positional arguments.

### Steps

Commands that should accept targets:
- `deploy`
- `revert`
- `verify`
- `status`
- `log`

1. **Test `deploy` with positional target**:
   ```bash
   sqlitch deploy db:sqlite:test.db
   ```

2. **Expected**:
   - NOT exit code 2 (not a parsing error)
   - May exit 0 (success), 1 (not implemented/error), but NOT 2

3. **Test `verify` with positional target** (recently fixed):
   ```bash
   sqlitch verify db:sqlite:test.db
   ```

4. **Expected**:
   - NOT exit code 2
   - Should accept the positional target

5. **Validation**:
   - [ ] `deploy` accepts positional target
   - [ ] `revert` accepts positional target
   - [ ] `verify` accepts positional target
   - [ ] `status` accepts positional target
   - [ ] `log` accepts positional target
   - [ ] No "unexpected extra argument" errors

6. **Automated check**:
   ```bash
   for cmd in deploy revert verify status log; do
     echo "Testing: sqlitch $cmd db:sqlite:test.db"
     sqlitch $cmd db:sqlite:test.db
     exitcode=$?
     if [ $exitcode -eq 2 ]; then
       echo "FAIL: $cmd rejected positional target (exit code 2)"
     else
       echo "PASS: $cmd accepted positional target (exit code $exitcode)"
     fi
   done
   ```

## Test Scenario 6: Unknown Option Rejection

### Objective
Verify commands reject unknown options with appropriate errors.

### Steps

1. **Test with invalid option**:
   ```bash
   sqlitch plan --nonexistent-option
   ```

2. **Expected**:
   - Exit code 2 (option parsing error)
   - Error message: "Error: No such option: --nonexistent-option"

3. **Validation**:
   - [ ] Unknown options are rejected
   - [ ] Exit code is 2
   - [ ] Error message identifies the unknown option

## Test Scenario 7: Stub Command Behavior

### Objective
Verify stub implementations accept arguments before reporting "not implemented".

### Steps

Stub commands (not yet fully implemented):
- Most commands are stubs except: `help`, `plan`, `add`, `config`, `init` (partially implemented)

1. **Test stub with valid arguments**:
   ```bash
   sqlitch bundle --dest /tmp/test
   ```

2. **Expected**:
   - Accepts the `--dest` option (no parsing error)
   - Exits with code 1 (not implemented)
   - Message: "sqlitch bundle is not implemented yet" or similar

3. **Test stub without required args** (if applicable):
   ```bash
   sqlitch rework
   ```

4. **Expected**:
   - Exits with code 2 (parsing error for missing arg)
   - Does NOT reach "not implemented" message

5. **Validation**:
   - [ ] Stubs validate arguments before checking implementation
   - [ ] Valid args → "not implemented" + exit 1
   - [ ] Invalid args → parsing error + exit 2

## Test Scenario 8: Exit Code Consistency

### Objective
Verify all commands follow the 0/1/2 exit code convention.

### Steps

1. **Success case** (if implemented):
   ```bash
   sqlitch help deploy
   echo "Exit code: $?"  # Should be 0
   ```

2. **User error case** (stub):
   ```bash
   sqlitch bundle
   echo "Exit code: $?"  # Should be 1 (not implemented)
   ```

3. **Parsing error case**:
   ```bash
   sqlitch add --nonexistent
   echo "Exit code: $?"  # Should be 2
   ```

4. **Validation**:
   - [ ] Successful operations exit 0
   - [ ] User errors (including "not implemented") exit 1
   - [ ] System/parsing errors exit 2

## Success Criteria

### All scenarios pass when:
- [x] All 19 commands discovered via `--help`
- [ ] Each command has proper help text via `--help`
- [ ] All commands accept global options (`--quiet`, `--verbose`, `--chdir`, `--no-pager`)
- [ ] Commands with required arguments enforce them
- [ ] Commands accepting targets handle positional arguments
- [ ] Unknown options are rejected appropriately
- [ ] Stub commands validate arguments before reporting "not implemented"
- [ ] Exit codes follow 0/1/2 convention consistently

### Manual Execution Time
Approximately 10-15 minutes to run all scenarios manually. Consider automating with a test script.

## Automation Script (Optional)

Create `scripts/check-command-parity.sh`:
```bash
#!/bin/bash
# Automated quickstart validation

set -e

echo "=== Test 1: Command Discovery ==="
sqlitch --help | grep -q "add" && echo "PASS" || echo "FAIL"

echo "=== Test 2: Help Text ==="
for cmd in add bundle checkout config deploy engine help init log plan rebase revert rework show status tag target upgrade verify; do
  sqlitch $cmd --help > /dev/null 2>&1 && echo "PASS: $cmd" || echo "FAIL: $cmd"
done

echo "=== Test 3: Global Options ==="
sqlitch plan --quiet --verbose --no-pager 2>&1 | grep -q "No such option" && echo "FAIL" || echo "PASS"

echo "=== Test 4: Required Arguments ==="
sqlitch add 2>&1 | grep -q "Missing argument" && echo "PASS" || echo "FAIL"

echo "=== Test 5: Positional Targets ==="
sqlitch verify db:sqlite:test.db 2>&1
exitcode=$?
[ $exitcode -ne 2 ] && echo "PASS" || echo "FAIL"

echo "=== All tests complete ==="
```

## Notes
- This quickstart does NOT test full command functionality
- Stub implementations should still validate arguments properly
- Exit codes distinguish parsing errors (2) from user errors (1)
- Recent fix: `verify` command now accepts positional targets
