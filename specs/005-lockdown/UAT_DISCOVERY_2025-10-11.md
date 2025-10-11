# UAT Discovery Summary - 2025-10-11

## Problem Statement

During execution of task T060b (running `uat/side-by-side.py`), step 30 failed with error:
```
Plan file sqitch.plan does not exist
```

According to the Sqitch SQLite tutorial (`uat/sqitchtutorial-sqlite.pod`), the command `sqitch deploy db:sqlite:dev/flipr.db` should have produced:
```
Adding registry tables to db:sqlite:dev/sqitch.db
Deploying changes to db:sqlite:dev/flipr.db
  + users ................... ok
  + flips ................... ok
```

## Root Cause

The UAT script `uat/side-by-side.py` removes and recreates test directories at step 30, which deletes essential project files (`sqitch.conf`, `sqitch.plan`) that the tutorial assumes persist throughout the workflow.

Specifically, at lines 536-542:
```python
# Create dev directories
if SQITCH_DIR.exists():
    shutil.rmtree(SQITCH_DIR)  # ⚠️ Removes sqitch.conf and sqitch.plan!
(SQITCH_DIR / "dev").mkdir(parents=True, exist_ok=True)
```

## Fundamental Issue Discovered

This failure revealed a **critical gap in the UAT validation approach**: The script was testing "sqlitch vs sqitch" without first verifying that sqitch's behavior matches the tutorial expectations.

**What we thought we were testing**: "Does sqlitch match sqitch?"  
**What we were actually testing**: "Does sqlitch match a broken sqitch setup?"

## Constitutional Principle Violated

From `.specify/memory/constitution.md` and `specs/005-lockdown/plan.md`:

> **Sqitch Implementation as Source of Truth**: All behavior must be verified against Sqitch's implementation in the `sqitch/` directory. This includes syntax support, error handling, and edge cases.

The UAT scripts must validate that:
1. **First**: Sqitch produces tutorial-expected output (validates our test setup)
2. **Then**: SQLitch matches Sqitch's behavior (validates our implementation)

We were skipping step 1.

## Impact

- **Immediate**: T060b execution is blocked until UAT script is fixed
- **Broader**: All three UAT scripts (side-by-side, forward-compat, backward-compat) may have similar issues
- **Process**: Need a validation step before any comparison testing

## Resolution

### Documents Updated

1. **specs/005-lockdown/tasks.md**
   - Added new task T060b2: "Validate that `uat/side-by-side.py` test steps faithfully reproduce the tutorial workflow"
   - Updated T060b status to document the halt state and root cause
   - Made T060b dependent on T060b2 completion

2. **specs/005-lockdown/plan.md**
   - Added "Critical Discovery (2025-10-11)" section documenting the issue
   - Updated Phase 2 to include UAT validation protocol
   - Reinforced constitutional requirement to validate against tutorial first

3. **specs/005-lockdown/UAT_EXECUTION_PLAN.md**
   - Added T060b2 as a blocking task with full validation procedure
   - Updated T060b dependencies to require T060b2 completion
   - Provided step-by-step validation process including:
     - Step-by-tutorial mapping template
     - Critical steps to validate
     - Sqitch-only test procedure
     - Fix implementation guidance

4. **specs/005-lockdown/UAT_TUTORIAL_VALIDATION.md** (NEW)
   - Created comprehensive validation document
   - Maps each critical UAT step to tutorial section
   - Documents expected vs actual behavior
   - Provides specific fix for step 30 issue
   - Includes validation checklist and sign-off criteria

### New Task: T060b2

**Task**: Validate UAT Script Against Tutorial  
**Priority**: P1 (blocks all UAT comparison testing)  
**Estimated Time**: 60-90 minutes

**Deliverables**:
1. Complete `UAT_TUTORIAL_VALIDATION.md` with all critical steps validated
2. Fix `uat/side-by-side.py` to preserve project files (specific fix provided in validation doc)
3. Run sqitch-only test to verify tutorial-expected output
4. Document any acceptable deviations with rationale
5. Commit fixes before proceeding to T060b

**Acceptance Criteria**:
- Sqitch produces tutorial-expected output at EVERY step
- UAT script preserves project context throughout workflow
- All deviations documented and justified

## Specific Fix Required

**File**: `uat/side-by-side.py`  
**Location**: Lines 536-542 (before step 30)

**Change Type**: Replace `shutil.rmtree()` with selective database cleanup

**Implementation**: See `UAT_TUTORIAL_VALIDATION.md` for detailed code changes

**Key Principle**: Remove database files (`*.db`) but preserve project files (`sqitch.conf`, `sqitch.plan`, script directories)

## Process Improvement

Going forward, all UAT development must follow this sequence:

1. **Design Phase**: Map test steps to tutorial sections
2. **Validation Phase** (T060b2): Verify sqitch produces tutorial output
3. **Comparison Phase** (T060b): Test sqlitch parity
4. **Evidence Phase** (T060g): Document differences

This ensures we're always testing against correct reference behavior.

## Next Actions

1. ✅ Update specs/plan/tasks (COMPLETED in this session)
2. ⏳ Execute T060b2 (validation task) - READY TO START
3. ⏳ Fix UAT script based on validation findings
4. ⏳ Re-run sqitch-only test to verify fix
5. ⏳ Resume T060b execution

## Lessons Learned

1. **Test the test**: UAT scripts are code too and need validation
2. **Trust but verify**: Tutorial documents expected behavior; validate against it
3. **Preserve context**: State accumulates throughout workflows; don't blindly clean
4. **Constitutional compliance**: "Sqitch as source of truth" applies to test setup too

## References

- Tutorial: `uat/sqitchtutorial-sqlite.pod`
- UAT Script: `uat/side-by-side.py`
- Validation Doc: `specs/005-lockdown/UAT_TUTORIAL_VALIDATION.md`
- Execution Plan: `specs/005-lockdown/UAT_EXECUTION_PLAN.md`
- Tasks: `specs/005-lockdown/tasks.md`
- Plan: `specs/005-lockdown/plan.md`

---

**Session End**: All spec/plan/task documents updated per user request.  
**No Implementation Actions Taken**: As requested, only documentation updated.  
**Ready For**: T060b2 execution in next session.
