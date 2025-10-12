# UAT Tutorial Validation Report

**Branch**: `005-lockdown`  
**Date**: 2025-10-11  
**Task**: T060b2 - Validate UAT Script Against Tutorial  
**Tutorial Source**: `uat/sqitchtutorial-sqlite.pod`

## Overview

This document validates that `uat/side-by-side.py` faithfully reproduces the workflow described in the Sqitch SQLite tutorial, ensuring that sqitch produces tutorial-expected output at every step BEFORE testing sqlitch parity.

**Why This Matters**: During T060b execution, step 30 failed because the UAT script's setup didn't match the tutorial's prerequisites. This validation ensures we're testing "sqlitch vs tutorial-correct sqitch", not "sqlitch vs broken sqitch setup".

---

## Validation Status Summary

**Status Key**: ✅ Validated | ⚠️ Issue Found | 🔧 Fixed | ⏳ Pending

| Step | Description | Tutorial Match | Issues | Status |
|------|-------------|----------------|--------|--------|
| 1 | Initialize Project | ⏳ | TBD | ⏳ |
| 5 | Add 'users' Table | ⏳ | TBD | ⏳ |
| 6 | Deploy 'users' Table | ⏳ | TBD | ⏳ |
| 13-14 | Target/Engine Setup | ⏳ | TBD | ⏳ |
| 18 | Add 'flips' Table | ⏳ | TBD | ⏳ |
| 29 | Tag Release | ⏳ | TBD | ⏳ |
| 30 | Deploy to dev/flipr.db | ⚠️ | Missing project files | ⏳ |
| 32 | Create Bundle | ⏳ | TBD | ⏳ |

---

## Critical Steps Validation

### Step 1: Initialize Project

**Tutorial Section**: Lines 66-83 in sqitchtutorial-sqlite.pod

**Tutorial Context**: 
- Working in a Git repository
- No prior Sqitch initialization

**Tutorial Command**:
```bash
sqitch init flipr --uri https://github.com/sqitchers/sqitch-sqlite-intro/ --engine sqlite
```

**Tutorial Expected Output**:
```
Created sqitch.conf
Created sqitch.plan
Created deploy/
Created revert/
Created verify/
```

**UAT Script Implementation**:
- Command in TUTORIAL_STEPS: `("init", "flipr", "--uri", "https://github.com/sqitchers/sqitch-sqlite-intro/", "--engine", "sqlite")`
- Pre-step setup in side-by-side.py: Lines 311-319
- Post-step state: Creates `sqitch.conf`, `sqitch.plan`, and script directories

**Matches Tutorial**: ⏳ To be validated

**Issues Found**: None known yet

**Resolution**: TBD

---

### Step 5: Add 'users' Table

**Tutorial Section**: Lines 144-152 in sqitchtutorial-sqlite.pod

**Tutorial Context**:
- sqitch.conf and sqitch.plan exist from step 1
- Working in project root directory

**Tutorial Command**:
```bash
sqitch add users -n 'Creates table to track our users.'
```

**Tutorial Expected Output**:
```
Created deploy/users.sql
Created revert/users.sql
Created verify/users.sql
Added "users" to sqitch.plan
```

**UAT Script Implementation**:
- Command in TUTORIAL_STEPS: `("add", "users", "-n", "Creates table to track our users.")`
- Pre-step setup: User manually edits SQL files after this command
- UAT script: Lines 326-374 write SQL file content

**Matches Tutorial**: ⏳ To be validated

**Issues Found**: UAT script writes SQL files instead of expecting user to edit them (acceptable deviation for automation)

**Resolution**: Acceptable - UAT needs to be automated, manual editing not feasible

---

### Step 6: Deploy 'users' Table

**Tutorial Section**: Lines 210-226 in sqitchtutorial-sqlite.pod

**Tutorial Context**:
- sqitch.conf and sqitch.plan exist
- deploy/users.sql, revert/users.sql, verify/users.sql exist with content
- First deploy to new database

**Tutorial Command**:
```bash
sqitch deploy db:sqlite:flipr_test.db
```

**Tutorial Expected Output**:
```
Adding registry tables to db:sqlite:sqitch.db
Deploying changes to db:sqlite:flipr_test.db
  + users .. ok
```

**UAT Script Implementation**:
- Command in TUTORIAL_STEPS: `("deploy", "db:sqlite:flipr_test.db")`
- Pre-step setup: SQL files written by UAT script (lines 326-374)

**Matches Tutorial**: ⏳ To be validated

**Issues Found**: None known yet

**Resolution**: TBD

---

### Step 13-14: Target and Engine Setup

**Tutorial Section**: Lines 398-433 in sqitchtutorial-sqlite.pod

**Tutorial Context**:
- Already deployed to flipr_test.db
- sqitch.conf exists

**Tutorial Commands**:
```bash
sqitch target add flipr_test db:sqlite:flipr_test.db
sqitch engine add sqlite flipr_test
```

**Tutorial Expected Output**:
```
(No output shown in tutorial)
```

**Tutorial Result**: Modifies sqitch.conf to add target and set default engine

**UAT Script Implementation**:
- Commands in TUTORIAL_STEPS: Steps 13 and 14
- Pre-step setup: flipr_test.db exists, has been deployed

**Matches Tutorial**: ⏳ To be validated

**Issues Found**: None known yet

**Resolution**: TBD

---

### Step 18: Add 'flips' Table

**Tutorial Section**: Lines 442-473 in sqitchtutorial-sqlite.pod

**Tutorial Context**:
- Users table already deployed
- sqitch.conf has default target set

**Tutorial Command**:
```bash
sqitch add flips --requires users -n 'Adds table for storing flips.'
```

**Tutorial Expected Output**:
```
Created deploy/flips.sql
Created revert/flips.sql
Created verify/flips.sql
Added "flips [users]" to sqitch.plan
```

**UAT Script Implementation**:
- Command in TUTORIAL_STEPS: `("add", "flips", "--requires", "users", "-n", "Adds table for storing flips.")`
- Pre-step setup: SQL files written by UAT script

**Matches Tutorial**: ⏳ To be validated

**Issues Found**: None known yet

**Resolution**: TBD

---

### Step 29: Tag Release v1.0.0-dev1

**Tutorial Section**: Lines 667-683 in sqitchtutorial-sqlite.pod

**Tutorial Context**:
- All changes (users, flips, userflips) deployed
- Working in project with sqitch.plan

**Tutorial Command**:
```bash
sqitch tag v1.0.0-dev1 -n 'Tag v1.0.0-dev1.'
```

**Tutorial Expected Output**:
```
Tagged "userflips" with @v1.0.0-dev1
```

**Tutorial Result**: Modifies sqitch.plan to add tag after userflips

**UAT Script Implementation**:
- Command in TUTORIAL_STEPS: `("tag", "v1.0.0-dev1", "-n", "Tag v1.0.0-dev1.")`
- Pre-step setup: All changes deployed and verified

**Matches Tutorial**: ⏳ To be validated

**Issues Found**: None known yet

**Resolution**: TBD

---

### Step 30: Deploy to dev/flipr.db ⚠️ KNOWN ISSUE

**Tutorial Section**: Lines 683-693 in sqitchtutorial-sqlite.pod

**Tutorial Context**:
- Tag v1.0.0-dev1 exists in sqitch.plan
- sqitch.conf exists
- Working in project root
- dev/ directory needs to be created

**Tutorial Commands**:
```bash
mkdir dev
sqitch deploy db:sqlite:dev/flipr.db
```

**Tutorial Expected Output**:
```
Adding registry tables to db:sqlite:dev/sqitch.db
Deploying changes to db:sqlite:dev/flipr.db
  + users ................... ok
  + flips ................... ok
```

**Note**: Tutorial shows deploying users and flips, not userflips. This is because userflips is tagged with @v1.0.0-dev1, and the tutorial is demonstrating deploying to a specific tag point. *(To verify this interpretation against tutorial text)*

**UAT Script Implementation**:
- Command in TUTORIAL_STEPS: `("deploy", "db:sqlite:dev/flipr.db")`
- Pre-step setup (lines 536-542): 
  ```python
  # Create dev directories
  if SQITCH_DIR.exists():
      shutil.rmtree(SQITCH_DIR)
  (SQITCH_DIR / "dev").mkdir(parents=True, exist_ok=True)
  if SQLITCH_DIR.exists():
      shutil.rmtree(SQLITCH_DIR)
  (SQLITCH_DIR / "dev").mkdir(parents=True, exist_ok=True)
  ```

**Issues Found**:
1. ⚠️ **CRITICAL**: UAT script calls `shutil.rmtree(SQITCH_DIR)` before step 30, removing sqitch.conf and sqitch.plan
2. ⚠️ This causes sqitch to fail with "Plan file sqitch.plan does not exist"
3. ⚠️ Tutorial assumes project files persist throughout the workflow

**Actual Output** (from `uat/sqitch_results/uat.log`):
```
Plan file sqitch.plan does not exist
```

**Expected Output** (from tutorial):
```
Adding registry tables to db:sqlite:dev/sqitch.db
Deploying changes to db:sqlite:dev/flipr.db
  + users ................... ok
  + flips ................... ok
```

**Root Cause**: The UAT script incorrectly removes the entire test directory structure, losing accumulated project state (config files, plan file, script directories).

**Resolution**: ⏳ UAT script must be fixed to preserve project files when creating dev/ subdirectory

**Fix Strategy**:
1. Option A: Don't remove SQITCH_DIR, just create the dev/ subdirectory
2. Option B: Preserve project files before removal, restore after recreation
3. Option C: Use a helper function to selectively clean (remove DBs but keep configs)

**Recommended Fix**: Option C - Create `clean_databases()` helper that removes `*.db` files but preserves sqitch.conf, sqitch.plan, and script directories.

---

### Step 32: Create Bundle

**Tutorial Section**: Lines 700-715 in sqitchtutorial-sqlite.pod

**Tutorial Context**:
- Full project deployed (users, flips, userflips with tag)
- sqitch.conf and sqitch.plan exist
- All script directories and files exist

**Tutorial Command**:
```bash
sqitch bundle
```

**Tutorial Expected Output**:
```
Bundling into bundle
Writing config
Writing plan
Writing scripts
  + users
  + flips
  + userflips @v1.0.0-dev1
```

**UAT Script Implementation**:
- Command in TUTORIAL_STEPS: `("bundle",)`
- Pre-step setup: Assumes project files exist

**Matches Tutorial**: ⏳ To be validated (likely affected by step 30 issue)

**Issues Found**: Will likely fail if step 30 fix isn't applied (missing project files)

**Resolution**: Should be resolved by fixing step 30

---

## UAT Script Fixes Required

### Fix 1: Preserve Project Context

**Location**: `uat/side-by-side.py`, before step 30 (around lines 536-542)

**Current Code**:
```python
# Create dev directories
if SQITCH_DIR.exists():
    shutil.rmtree(SQITCH_DIR)
(SQITCH_DIR / "dev").mkdir(parents=True, exist_ok=True)
if SQLITCH_DIR.exists():
    shutil.rmtree(SQLITCH_DIR)
(SQLITCH_DIR / "dev").mkdir(parents=True, exist_ok=True)
```

**Proposed Fix**:
```python
# Create dev directories while preserving project files
def clean_databases_only(base_dir: Path):
    """Remove database files but preserve project configuration and scripts."""
    if not base_dir.exists():
        base_dir.mkdir(parents=True, exist_ok=True)
        return
    
    # Remove only .db files, preserve everything else
    for db_file in base_dir.glob("*.db"):
        db_file.unlink()
    for db_file in base_dir.glob("**/*.db"):
        db_file.unlink()

# Clean DBs but keep project files
clean_databases_only(SQITCH_DIR)
clean_databases_only(SQLITCH_DIR)

# Create dev subdirectories
(SQITCH_DIR / "dev").mkdir(parents=True, exist_ok=True)
(SQLITCH_DIR / "dev").mkdir(parents=True, exist_ok=True)
```

**Status**: ⏳ To be implemented

---

## Sqitch-Only Validation Test

**Purpose**: Run tutorial steps with sqitch alone (no sqlitch comparison) to verify that the UAT script setup produces tutorial-expected sqitch output.

**Status**: ⏳ Not yet executed

**Procedure**:
```bash
# Create clean test environment
mkdir -p uat/tutorial_validation
cd uat/tutorial_validation

# Execute critical steps manually with sqitch
# Document output at each step
# Compare with tutorial sections
```

**Results**: TBD

---

## Recommendations

1. **Immediate Action**: Fix step 30 to preserve project files (Fix 1 above)
2. **Validation**: Run sqitch-only test after applying Fix 1
3. **Documentation**: Update side-by-side.py docstring to note tutorial fidelity requirements
4. **Future**: Consider adding tutorial validation as an automated test (optional)

---

## Sign-Off

**Task T060b2 Complete When**:
- [ ] All critical steps validated against tutorial
- [ ] Fix 1 implemented and tested
- [ ] Sqitch-only validation test passes with tutorial-expected output
- [ ] All issues documented in this file
- [ ] Changes committed with descriptive message

**Next Task**: T060b (Execute side-by-side.py)

---

*Last Updated*: 2025-10-11  
*Validated By*: [To be filled by agent completing T060b2]
