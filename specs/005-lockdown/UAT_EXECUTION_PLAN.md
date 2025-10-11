# UAT Execution Plan - Detailed Breakdown

**Branch**: `005-lockdown`  
**Date**: 2025-10-11  
**Parent Task**: T060 (broken down into T060a-T060h)  
**Sqitch Version**: v1.5.3 (vendored in `sqitch/` directory)

## Overview

T060 has been broken down into 8 smaller, incremental tasks to ensure careful validation and debugging at each step. Each task is designed to be completable in a single session without overwhelming context.

---

## Task Breakdown

### T060a: Verify side-by-side.py Prerequisites [P1]
**Estimated Time**: 5-10 minutes  
**Status**: 🔷 Ready to start

**Description**: Check that `uat/side-by-side.py` has all prerequisites to run successfully.

**Acceptance Criteria**:
- [ ] `sqitch` binary is available in PATH (check with `which sqitch`)
- [ ] Sqitch version is v1.5.3 (or compatible)
- [ ] `uat/test_steps.py` TUTORIAL_STEPS is complete and valid
- [ ] Helper modules (`sanitization`, `comparison`) import successfully
- [ ] Working directories (`uat/sqitch_results`, `uat/sqlitch_results`) can be created
- [ ] Script runs with `--help` flag without errors

**Commands**:
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate

# Check sqitch availability and version
which sqitch || echo "⚠️  sqitch not found - install required"
sqitch --version || echo "⚠️  sqitch not executable"
# Expected: sqitch (App::Sqitch) v1.5.x

# Check script syntax and imports
python -m py_compile uat/side-by-side.py
python uat/side-by-side.py --help

# Verify helper imports
python -c "from uat import sanitization, comparison, test_steps; print('✅ Imports OK')"
```

**Expected Issues**:
- sqitch may not be installed
- sqitch version may differ from v1.5.3 (minor version differences likely OK)
- Path issues with helper modules

**Remediation**:
- Install sqitch if missing: `brew install sqitch` (macOS) or equivalent
- Version mismatch: Note version in test logs, proceed if v1.5.x
- Fix any import path issues in the script

---

### T060b: Execute side-by-side.py [P1]
**Estimated Time**: 15-30 minutes  
**Status**: 🔷 Blocked by T060a  
**Depends On**: T060a complete

**Description**: Run the full side-by-side comparison and fix any failures.

**Acceptance Criteria**:
- [ ] Script completes with exit code 0
- [ ] Log file created at `specs/005-lockdown/artifacts/uat/side-by-side.log`
- [ ] No behavioral differences detected (cosmetic differences acceptable)
- [ ] All tutorial steps execute successfully for both sqitch and sqlitch

**Commands**:
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate

# Create output directory
mkdir -p specs/005-lockdown/artifacts/uat

# Run side-by-side comparison
python uat/side-by-side.py --out specs/005-lockdown/artifacts/uat/side-by-side.log

# Check exit code
echo "Exit code: $?"

# Review log for issues
less specs/005-lockdown/artifacts/uat/side-by-side.log
```

**Expected Issues**:
- Steps may fail due to environment differences
- Output format mismatches between sqitch/sqlitch
- Database state pollution from previous runs

**Remediation Strategy**:
- Clean working directories before run
- Fix sqlitch output formatting if needed
- Update sanitization helpers for new patterns
- Document acceptable cosmetic differences

**Incremental Approach**:
If full run fails, use `--stop N` to debug step-by-step:
```bash
# Debug first 5 steps
python uat/side-by-side.py --stop 5 --out temp.log

# Continue from where it failed, fix issues, repeat
```

---

### T060c: Implement forward-compat.py Logic [P1]
**Estimated Time**: 30-60 minutes  
**Status**: 🔷 Blocked by T060b  
**Depends On**: T060b complete

**Description**: Replace the stub in `uat/scripts/forward-compat.py` with full implementation that runs sqlitch first, then validates sqitch can continue the workflow.

**Current State**: Script is a stub that returns exit code 1

**Implementation Requirements**:
1. Import and reuse logic from `side-by-side.py`
2. Use shared helpers (`sanitization`, `comparison`, `test_steps`)
3. Execute tutorial steps with sqlitch first
4. Capture database state after each sqlitch step
5. Run next step with sqitch and verify compatibility
6. Sanitize and log all output
7. Exit 0 on success, 1 on failure

**Acceptance Criteria**:
- [ ] Script implements full forward compatibility logic
- [ ] Reuses existing helpers (no duplication)
- [ ] Handles errors gracefully with clear messages
- [ ] Supports `--out` flag for log output
- [ ] Maintains SQLITCH_UAT_SKIP_EXECUTION env var support

**Key Implementation Points**:
```python
# Pattern to follow:
# 1. Clean environment (remove old databases)
# 2. For each step in TUTORIAL_STEPS:
#    a. Execute with sqlitch
#    b. Capture output and sanitize
#    c. Capture database state
#    d. Execute NEXT step with sqitch
#    e. Verify sqitch output is compatible
#    f. Compare database states
#    g. Log differences
# 3. Report final status
```

**Files to Study**:
- `uat/side-by-side.py` (lines 100-400 for execution logic)
- `uat/comparison.py` (database comparison helpers)
- `uat/sanitization.py` (output sanitization)

---

### T060d: Execute forward-compat.py [P1]
**Estimated Time**: 15-30 minutes  
**Status**: 🔷 Blocked by T060c  
**Depends On**: T060c complete

**Description**: Run the forward compatibility script and fix any failures.

**Acceptance Criteria**:
- [ ] Script completes with exit code 0
- [ ] Log file created at `specs/005-lockdown/artifacts/uat/forward-compat.log`
- [ ] Sqitch successfully continues after each sqlitch step
- [ ] No behavioral incompatibilities detected

**Commands**:
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate

# Run forward compatibility test
python uat/scripts/forward-compat.py --out specs/005-lockdown/artifacts/uat/forward-compat.log

# Check exit code
echo "Exit code: $?"

# Review log
less specs/005-lockdown/artifacts/uat/forward-compat.log
```

**Expected Issues**:
- Registry format differences between sqitch and sqlitch
- Command output format incompatibilities
- Database state divergence

**Remediation**:
- Fix sqlitch to match sqitch expectations where needed
- Document acceptable differences
- Update compatibility logic if assumptions were wrong

---

### T060e: Implement backward-compat.py Logic [P1]
**Estimated Time**: 20-40 minutes  
**Status**: 🔷 Blocked by T060d  
**Depends On**: T060d complete

**Description**: Replace the stub in `uat/scripts/backward-compat.py` with full implementation that runs sqitch first, then validates sqlitch can continue the workflow.

**Current State**: Script is a stub that returns exit code 1

**Implementation Requirements**:
Same as T060c, but reversed:
1. Execute tutorial steps with sqitch first
2. Validate sqlitch can continue after each sqitch step
3. Use same helpers and patterns as forward-compat.py

**Acceptance Criteria**:
- [ ] Script implements full backward compatibility logic
- [ ] Mirrors forward-compat.py pattern (reuses helpers)
- [ ] Handles errors gracefully
- [ ] Supports `--out` flag for log output
- [ ] Maintains SQLITCH_UAT_SKIP_EXECUTION env var support

**Efficiency Note**: Much of the code can be copied from forward-compat.py with tool names swapped.

---

### T060f: Execute backward-compat.py [P1]
**Estimated Time**: 15-30 minutes  
**Status**: 🔷 Blocked by T060e  
**Depends On**: T060e complete

**Description**: Run the backward compatibility script and fix any failures.

**Acceptance Criteria**:
- [ ] Script completes with exit code 0
- [ ] Log file created at `specs/005-lockdown/artifacts/uat/backward-compat.log`
- [ ] Sqlitch successfully continues after each sqitch step
- [ ] No behavioral incompatibilities detected

**Commands**:
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate

# Run backward compatibility test
python uat/scripts/backward-compat.py --out specs/005-lockdown/artifacts/uat/backward-compat.log

# Check exit code
echo "Exit code: $?"

# Review log
less specs/005-lockdown/artifacts/uat/backward-compat.log
```

**Expected Issues**:
Similar to T060d but reversed

---

### T060g: Review UAT Logs for Differences [P1]
**Estimated Time**: 20-30 minutes  
**Status**: 🔷 Blocked by T060f  
**Depends On**: T060f complete

**Description**: Systematically review all three UAT logs to identify and categorize any differences between sqitch and sqlitch behavior.

**Acceptance Criteria**:
- [ ] All three logs reviewed line-by-line
- [ ] Behavioral differences documented (if any)
- [ ] Cosmetic differences cataloged and approved
- [ ] Findings summarized in `IMPLEMENTATION_REPORT_LOCKDOWN.md`

**Review Process**:
```bash
cd /Users/poecurt/projects/sqlitch/specs/005-lockdown/artifacts/uat

# Quick sanity check for error markers
grep -i "error\|fail\|mismatch" *.log

# Review each log
less side-by-side.log
less forward-compat.log
less backward-compat.log
```

**Categorization**:
- **Behavioral**: Changes in functionality (requires fix or documented exemption)
- **Cosmetic**: Output formatting, whitespace, case differences (acceptable)
- **Timing**: Execution speed differences (acceptable)

**Documentation Template** (add to IMPLEMENTATION_REPORT_LOCKDOWN.md):
```markdown
## UAT Execution Results

### Side-by-Side Comparison
- **Status**: ✅ PASS
- **Log**: `specs/005-lockdown/artifacts/uat/side-by-side.log`
- **Differences Found**: [None | Cosmetic only | See below]
- **Notes**: [Any observations]

### Forward Compatibility (sqlitch → sqitch)
- **Status**: ✅ PASS
- **Log**: `specs/005-lockdown/artifacts/uat/forward-compat.log`
- **Differences Found**: [None | Cosmetic only | See below]
- **Notes**: [Any observations]

### Backward Compatibility (sqitch → sqlitch)
- **Status**: ✅ PASS
- **Log**: `specs/005-lockdown/artifacts/uat/backward-compat.log`
- **Differences Found**: [None | Cosmetic only | See below]
- **Notes**: [Any observations]

### Summary of Cosmetic Differences
- [List any formatting/whitespace differences]
- [Explain why they're acceptable]

### Summary of Behavioral Differences
- [Should be empty, or require exemption documentation]
```

---

### T060h: Prepare Release PR Comment [P1]
**Estimated Time**: 10-15 minutes  
**Status**: 🔷 Blocked by T060g  
**Depends On**: T060g complete

**Description**: Create the release PR comment with UAT evidence using the template from quickstart.md.

**Acceptance Criteria**:
- [ ] Comment text prepared following quickstart template
- [ ] All three log files referenced with file paths
- [ ] Summary of differences included (if any)
- [ ] Ready to post to release PR

**Template** (from quickstart.md):
```markdown
## UAT Compatibility Run (SQLite tutorial)

**Date**: 2025-10-11  
**Branch**: `005-lockdown`  
**Executor**: [Your name]

### Results
- **Side-by-side**: ✅ PASS (log: `specs/005-lockdown/artifacts/uat/side-by-side.log`)
- **Forward compat**: ✅ PASS (log: `specs/005-lockdown/artifacts/uat/forward-compat.log`)
- **Backward compat**: ✅ PASS (log: `specs/005-lockdown/artifacts/uat/backward-compat.log`)

### Notes
[Summary of any cosmetic differences observed]

### Verification Commands
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate

# Reproduce results
python uat/side-by-side.py --out /tmp/side-by-side-verify.log
python uat/scripts/forward-compat.py --out /tmp/forward-compat-verify.log
python uat/scripts/backward-compat.py --out /tmp/backward-compat-verify.log
```

All scripts completed successfully with exit code 0.
```

**Output File**: Save to `specs/005-lockdown/artifacts/uat/RELEASE_PR_COMMENT.md`

---

## Progress Tracking

- [ ] T060a: Verify side-by-side prerequisites
- [ ] T060b: Execute side-by-side.py
- [ ] T060c: Implement forward-compat.py
- [ ] T060d: Execute forward-compat.py
- [ ] T060e: Implement backward-compat.py
- [ ] T060f: Execute backward-compat.py
- [ ] T060g: Review all UAT logs
- [ ] T060h: Prepare release PR comment

**Current Status**: 0/8 tasks complete

---

## Session Continuity

After completing each task:
1. Mark it complete in this file
2. Mark it complete in `tasks.md`
3. Run `pytest` to ensure no regressions
4. Commit progress with descriptive message
5. Update `IMPLEMENTATION_REPORT_LOCKDOWN.md` if findings change

Between sessions:
- Review this file to see where you left off
- Check the last completed task
- Read the "Expected Issues" section for the next task
- Ensure environment is activated before starting

---

## Quick Commands Reference

```bash
# Always start with
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate

# Check sqitch availability
which sqitch
sqitch --version

# Test helper imports
python -c "from uat import sanitization, comparison, test_steps"

# Run individual UAT scripts
python uat/side-by-side.py --out specs/005-lockdown/artifacts/uat/side-by-side.log
python uat/scripts/forward-compat.py --out specs/005-lockdown/artifacts/uat/forward-compat.log
python uat/scripts/backward-compat.py --out specs/005-lockdown/artifacts/uat/backward-compat.log

# Debug step-by-step
python uat/side-by-side.py --stop 5 --out /tmp/debug.log

# Clean up between runs
rm -rf uat/sqitch_results uat/sqlitch_results
rm -f flipr*.db sqitch.db sqlitch.db

# Verify no test regressions
pytest --quiet --tb=no
```

---

**Next Action**: Begin with T060a to verify prerequisites.
