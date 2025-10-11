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
**Estimated Time**: 15-30 minutes per iteration (may require multiple sessions)  
**Status**: 🔷 Blocked by T060a  
**Depends On**: T060a complete

**⚠️ HALT STATE PROTOCOL**: This task involves iterative debugging. Each failure MUST be fixed, reviewed, and committed before proceeding. DO NOT mark this task complete until the script exits with code 0 and all steps pass.

**Description**: Run the full side-by-side comparison and fix failures incrementally. Each failure requires a HALT → FIX → COMMIT cycle.

**Acceptance Criteria**:
- [ ] Script completes with exit code 0
- [ ] Log file created at `specs/005-lockdown/artifacts/uat/side-by-side.log`
- [ ] No behavioral differences detected (cosmetic differences acceptable)
- [ ] All tutorial steps execute successfully for both sqitch and sqlitch
- [ ] All fixes committed with descriptive messages

**Incremental Execution Workflow** (MANDATORY):

**Step 1: Initial Run**
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate

# Create output directory
mkdir -p specs/005-lockdown/artifacts/uat

# Run side-by-side comparison
python uat/side-by-side.py --out specs/005-lockdown/artifacts/uat/side-by-side.log

# Check exit code
echo "Exit code: $?"
```

**Step 2: If Exit Code ≠ 0** → **HALT AND FIX**
```bash
# Review log for the FIRST failure
less specs/005-lockdown/artifacts/uat/side-by-side.log

# Identify which step failed and why
# Common issues:
# - Output format mismatch (fix sqlitch formatting)
# - Sanitization pattern missing (update uat/sanitization.py)
# - Behavioral difference (investigate and fix core logic)
```

**Step 3: Fix ONE Failure at a Time**
1. Identify root cause of the failure
2. Implement the minimal fix (update sqlitch code, sanitization, or comparison logic)
3. Run focused tests: `pytest tests/path/to/affected_test.py -v`
4. Re-run side-by-side to verify fix: `python uat/side-by-side.py --stop N` (where N is step that failed + 2)
5. **COMMIT the fix**: `git add . && git commit -m "Fix UAT step N: [description]"`
6. **END SESSION** if fix was complex or context is getting full

**Step 4: Resume Next Session**
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate
# Continue from Step 1 (re-run full script)
```

**Step 5: Repeat Until Exit Code 0**
- Do NOT skip failures
- Do NOT mark task complete until script fully passes
- Each session should fix 1-3 issues maximum

**Expected Issues**:
- Steps may fail due to environment differences
- Output format mismatches between sqitch/sqlitch
- Database state pollution from previous runs
- Sanitization patterns not catching all timestamp/SHA1 formats

**Remediation Strategy**:
- **First Failure**: Fix and commit before looking at second failure
- Clean working directories between runs: `rm -rf uat/sqitch_results uat/sqlitch_results *.db`
- Fix sqlitch output formatting if needed (prioritize behavioral equivalence)
- Update sanitization helpers for new patterns (uat/sanitization.py)
- Document acceptable cosmetic differences in IMPLEMENTATION_REPORT_LOCKDOWN.md

**Debug Commands**:
```bash
# Run only first 5 steps to isolate early failures
python uat/side-by-side.py --stop 5 --out temp.log

# Run with continue flag to see all failures (but still fix one at a time)
python uat/side-by-side.py --continue --out temp.log

# Clean databases before retry
rm -f flipr*.db sqitch.db sqlitch.db
rm -rf uat/sqitch_results uat/sqlitch_results
```

**Session Management**:
- **Short Session**: Fix 1 failure, commit, end
- **Medium Session**: Fix 2-3 failures, commit each, end
- **Long Session**: Only if failures are trivial (e.g., all sanitization pattern updates)

**DO NOT**:
- Mark task complete with exit code ≠ 0
- Fix multiple unrelated failures in one commit
- Continue debugging when context window is getting full
- Skip failures to "come back later"

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
**Estimated Time**: 15-30 minutes per iteration (may require multiple sessions)  
**Status**: 🔷 Blocked by T060c  
**Depends On**: T060c complete

**⚠️ HALT STATE PROTOCOL**: This task involves iterative debugging. Each failure MUST be fixed, reviewed, and committed before proceeding. DO NOT mark this task complete until the script exits with code 0.

**Description**: Run the forward compatibility script (sqlitch → sqitch) and fix failures incrementally using the same HALT → FIX → COMMIT cycle as T060b.

**Acceptance Criteria**:
- [ ] Script completes with exit code 0
- [ ] Log file created at `specs/005-lockdown/artifacts/uat/forward-compat.log`
- [ ] Sqitch successfully continues after each sqlitch step
- [ ] No behavioral incompatibilities detected
- [ ] All fixes committed with descriptive messages

**Incremental Execution Workflow** (MANDATORY):

**Step 1: Initial Run**
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate

# Clean environment
rm -f flipr*.db sqitch.db sqlitch.db
rm -rf uat/sqitch_results uat/sqlitch_results

# Run forward compatibility test
python uat/scripts/forward-compat.py --out specs/005-lockdown/artifacts/uat/forward-compat.log

# Check exit code
echo "Exit code: $?"
```

**Step 2: If Exit Code ≠ 0** → **HALT AND FIX**
```bash
# Review log for the FIRST incompatibility
less specs/005-lockdown/artifacts/uat/forward-compat.log

# Common issues:
# - Sqitch cannot read sqlitch registry (fix registry format)
# - Sqitch rejects sqlitch plan state (investigate plan compatibility)
# - Database schema mismatch (verify deployment equivalence)
```

**Step 3: Fix ONE Issue, COMMIT, END SESSION**
1. Identify root cause
2. Implement minimal fix
3. Run tests: `pytest tests/engine/test_sqlite*.py -v`
4. Re-run forward-compat to verify
5. **COMMIT**: `git add . && git commit -m "Fix forward-compat: [description]"`
6. **END SESSION**

**Step 4: Resume and Repeat**
- Start new session with clean context
- Continue from Step 1
- Fix next failure

**Expected Issues**:
- Registry format differences between sqitch and sqlitch
- Command output format incompatibilities
- Database state divergence
- Plan file parsing differences

**Remediation**:
- Fix sqlitch registry format to match sqitch expectations
- Document acceptable differences in IMPLEMENTATION_REPORT_LOCKDOWN.md
- Update compatibility logic if assumptions were wrong

**Session Management**:
- **One failure per session** recommended
- Commit after each fix
- Re-run full script each session to catch regressions

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
**Estimated Time**: 15-30 minutes per iteration (may require multiple sessions)  
**Status**: 🔷 Blocked by T060e  
**Depends On**: T060e complete

**⚠️ HALT STATE PROTOCOL**: This task involves iterative debugging. Each failure MUST be fixed, reviewed, and committed before proceeding. DO NOT mark this task complete until the script exits with code 0.

**Description**: Run the backward compatibility script (sqitch → sqlitch) and fix failures incrementally using the same HALT → FIX → COMMIT cycle as T060b and T060d.

**Acceptance Criteria**:
- [ ] Script completes with exit code 0
- [ ] Log file created at `specs/005-lockdown/artifacts/uat/backward-compat.log`
- [ ] Sqlitch successfully continues after each sqitch step
- [ ] No behavioral incompatibilities detected
- [ ] All fixes committed with descriptive messages

**Incremental Execution Workflow** (MANDATORY):

**Step 1: Initial Run**
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate

# Clean environment
rm -f flipr*.db sqitch.db sqlitch.db
rm -rf uat/sqitch_results uat/sqlitch_results

# Run backward compatibility test
python uat/scripts/backward-compat.py --out specs/005-lockdown/artifacts/uat/backward-compat.log

# Check exit code
echo "Exit code: $?"
```

**Step 2: If Exit Code ≠ 0** → **HALT AND FIX**
```bash
# Review log for the FIRST incompatibility
less specs/005-lockdown/artifacts/uat/backward-compat.log

# Common issues:
# - SQLitch cannot read sqitch registry (fix registry reading logic)
# - SQLitch rejects sqitch plan state (investigate plan parsing)
# - Database schema mismatch (verify deployment equivalence)
```

**Step 3: Fix ONE Issue, COMMIT, END SESSION**
1. Identify root cause
2. Implement minimal fix
3. Run tests: `pytest tests/engine/ tests/plan/ -v`
4. Re-run backward-compat to verify
5. **COMMIT**: `git add . && git commit -m "Fix backward-compat: [description]"`
6. **END SESSION**

**Step 4: Resume and Repeat**
- Start new session with clean context
- Continue from Step 1
- Fix next failure

**Expected Issues**:
- SQLitch reading sqitch registry format
- Plan file interpretation differences
- Command output differences
- State management incompatibilities

**Remediation**:
- Fix sqlitch to correctly read sqitch artifacts
- Document acceptable differences in IMPLEMENTATION_REPORT_LOCKDOWN.md
- Update compatibility logic if assumptions were wrong

**Session Management**:
- **One failure per session** recommended
- Commit after each fix
- Re-run full script each session to catch regressions

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
