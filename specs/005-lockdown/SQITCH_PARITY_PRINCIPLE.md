# Sqitch Behavioral Parity Principle

**Status**: Constitutional requirement (Constitution v1.11.0)  
**Applies to**: ALL implementation work (005-lockdown and future)  
**Created**: 2025-10-11

## Overview

This document summarizes the critical constitutional requirement that **all SQLitch behavior must align with Sqitch's implementation** as found in the vendored `sqitch/` directory.

## The Principle

SQLitch is a Python reimplementation of Sqitch. To ensure users can seamlessly migrate from Sqitch or use both tools interchangeably, SQLitch MUST behave identically to Sqitch in all observable ways.

This includes:
- Command-line syntax and option handling
- Symbolic references (e.g., `@HEAD^`, `@ROOT`, `@FIRST`)
- Error messages and error handling
- Edge cases and boundary conditions
- Output formatting
- Exit codes
- Configuration handling

## Why This Matters

### The Problem
Currently, SQLitch doesn't recognize syntax like `@HEAD^` even though Sqitch does. This breaks the parity promise and creates a frustrating user experience for those familiar with Sqitch.

### The Solution
Before implementing ANY feature or fix, we must:
1. Check what Sqitch actually does (not what we think it should do)
2. Implement the same behavior
3. Test against actual Sqitch to verify parity

## Implementation Verification Protocol

**MANDATORY for all implementation work:**

### Step 1: Consult Sqitch Source
Review the corresponding Perl code in `sqitch/lib/App/Sqitch/` to understand canonical behavior.

Example: For `revert` command syntax, check:
- `sqitch/lib/App/Sqitch/Command/revert.pm`
- `sqitch/lib/App/Sqitch/Target.pm` (for target resolution)
- `sqitch/lib/App/Sqitch/Plan.pm` (for symbolic reference parsing)

### Step 2: Document Sqitch's Behavior
Note how Sqitch handles:
- Command-line syntax (including symbolic references)
- Options and flags
- Error messages and error handling
- Edge cases and boundary conditions
- Output formatting

### Step 3: Implement to Match
Write SQLitch code that produces identical behavior. Don't add features Sqitch doesn't have. Don't skip features Sqitch does have.

### Step 4: Verify Against Sqitch
Test using:
- UAT scripts (`uat/side-by-side.py`, `uat/scripts/forward-compat.py`, `uat/scripts/backward-compat.py`)
- Manual side-by-side testing
- Integration tests that compare outputs

### Step 5: Document Deviations
If SQLitch MUST differ from Sqitch (e.g., for security or correctness), document:
- Why the deviation is necessary
- What the difference is
- How users should adapt
- Whether/when parity will be restored

## Examples

### ✅ Good: Following the Protocol
```
Feature: Support @HEAD^ syntax in revert command
1. Checked sqitch/lib/App/Sqitch/Plan.pm for symbolic reference parsing
2. Documented that Sqitch supports @HEAD, @HEAD^, @HEAD~2, @ROOT, @FIRST, etc.
3. Implemented change resolution to match Sqitch's algorithm
4. Tested with uat/side-by-side.py to verify identical behavior
5. No deviations needed
```

### ❌ Bad: Skipping the Protocol
```
Feature: Support @HEAD^ syntax in revert command
1. Assumed it should work like git references
2. Implemented what seemed logical
3. Tested in isolation
4. Discovered Sqitch actually uses different syntax for some cases
5. Had to rewrite after users complained
```

## Where This Appears

This principle has been incorporated into:

1. **Constitution** (`.specify/memory/constitution.md` v1.11.0)
   - Section VI: Behavioral Parity with Sqitch
   - Now includes the mandatory 5-step Implementation Verification Protocol

2. **Spec** (`specs/005-lockdown/spec.md`)
   - New section: "Critical Principle: Sqitch Behavioral Parity"
   - Appears in Quick Guidelines with workflow details

3. **Plan** (`specs/005-lockdown/plan.md`)
   - Added to Constitution Check section
   - Includes the critical principle statement

4. **Tasks** (`specs/005-lockdown/tasks.md`)
   - Added to Task Execution Protocol
   - Added to Notes section as CRITICAL reminder
   - Applies to ALL tasks going forward

## For Future Specs

When creating new specs/plans/tasks, include:

### In spec.md (Quick Guidelines or Principles section):
```markdown
### 🎯 Critical Principle: Sqitch Behavioral Parity
All SQLitch behavior MUST align with Sqitch behavior as implemented in the vendored 
`sqitch/` directory. Before implementing features, consult `sqitch/lib/App/Sqitch/` 
for canonical behavior. See Constitution v1.11.0 Section VI for the mandatory 
Implementation Verification Protocol.
```

### In plan.md (Constitution Check section):
```markdown
- **Sqitch Implementation as Source of Truth**: All behavior must be verified against 
  Sqitch's implementation in the `sqitch/` directory per Constitution v1.11.0 Section VI.
```

### In tasks.md (Task Execution Protocol):
```markdown
**Before implementing ANY task:**
1. Consult Sqitch source in `sqitch/lib/App/Sqitch/`
2. Document Sqitch's behavior (syntax, options, errors, edge cases)
3. Implement to match
4. Verify against actual Sqitch
5. Document any deviations with rationale
```

## References

- Constitution v1.11.0, Section VI: Behavioral Parity with Sqitch
- Sqitch source code: `sqitch/lib/App/Sqitch/`
- UAT compatibility scripts: `uat/side-by-side.py`, `uat/scripts/forward-compat.py`, `uat/scripts/backward-compat.py`

---

**Summary**: This is not optional—it's a constitutional requirement for all current and future SQLitch implementation work.
