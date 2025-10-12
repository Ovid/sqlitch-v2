# Spec Updates: Alpha Release Clarification and Pylint Integration

**Date**: 2025-10-12  
**Branch**: `005-lockdown`  
**Commit**: aa5adec

---

## Summary

Updated the lockdown specification to:
1. **Clarify this is an alpha release, NOT v1.0.0**
2. **Add pylint as an additional code quality tool with systematic issue tracking**

---

## Changes Made

### 1. Alpha Release Clarification

**Files Updated**:
- `specs/005-lockdown/spec.md`
- `specs/005-lockdown/plan.md`
- `specs/005-lockdown/IMPLEMENTATION_COMPLETE.md`

**Key Updates**:
- Added **Target**: "Alpha release (NOT v1.0.0 - this is still alpha software)" to headers
- Updated summary text to explicitly state alpha status
- Added "What's Next for v1.0.0" section documenting requirements before production:
  - Extended real-world usage and feedback from alpha users
  - Additional edge case discovery and resolution
  - Multi-engine validation (PostgreSQL, MySQL)
  - Performance optimization under production loads
  - Additional security hardening based on field usage
  - Community feedback and bug reports

**Rationale**:
- Sets appropriate expectations for early adopters
- Acknowledges additional validation needed before production readiness
- Recognizes that current work establishes a solid foundation but needs field testing

### 2. Pylint Integration

**New Section in spec.md** (Objectives → Code Quality):
```markdown
- **Pylint Analysis**: Use pylint as an additional code quality tool to identify potential issues:
  - Generate pylint report: `pylint sqlitch --output-format=json > pylint_report.json`
  - Each issue in the JSON report should be evaluated and added as a separate task
  - Issues should be categorized (fix, suppress with justification, or defer with ticket)
  - Target: Reduce pylint score to an acceptable threshold (document baseline and improvement goals)
```

**New Section in plan.md** (Phase 1.2: Pylint Analysis Workflow):

**Workflow Steps**:

1. **Generate Baseline Report**:
   ```bash
   pylint sqlitch --output-format=json > specs/005-lockdown/artifacts/baseline/pylint_report.json
   ```

2. **Parse JSON Report** - Each issue contains:
   - `type`: convention, refactor, warning, error, fatal
   - `symbol`: specific pylint check (e.g., `line-too-long`, `unused-import`)
   - `message`: description of the issue
   - `path`: file location
   - `line`: line number
   - `column`: column number

3. **Create Individual Tasks** - For each issue:
   - Evaluate: Should it be fixed, suppressed with justification, or deferred?
   - Create a separate task in `tasks.md` with format:
     ```
     - [ ] **T<ID> [P2]** Fix <symbol> in <file>:<line> - <message>
     ```
   - Categorize by type (high priority for errors/warnings, lower for conventions)

4. **Document Baseline** - Record in `research.md`:
   - Total issue count by type
   - Current pylint score (out of 10.0)
   - Target score and improvement goals
   - Rationale for any issues marked "suppress" or "defer"

5. **Implementation Protocol**:
   - Fix issues in batches by category (e.g., all `unused-import` issues together)
   - Rerun pylint after each batch to verify fixes
   - Update pylint_report.json as baseline improves
   - Add inline `# pylint: disable=<symbol>` only with clear justification comment

**Important Note**: Pylint tasks are **separate from the core 137 lockdown tasks** and should be tracked independently to avoid scope creep. This is a quality improvement initiative parallel to the main release preparation.

**Updated Quality Gates in spec.md**:
```markdown
- Pylint report generated and all issues triaged:
  - Each issue evaluated: fix, suppress with justification, or defer with ticket
  - Baseline score documented in `specs/005-lockdown/artifacts/baseline/pylint_report.json`
  - Improvement goals documented with rationale for any deferred issues
```

---

## Impact

### Alpha Release Clarification
- **User Expectations**: Sets realistic expectations about software maturity
- **Release Strategy**: Allows for field validation before v1.0.0 commitment
- **Risk Management**: Acknowledges need for real-world testing and feedback

### Pylint Integration
- **Code Quality**: Additional layer of quality analysis beyond mypy/flake8
- **Systematic Approach**: Individual task tracking ensures methodical issue resolution
- **Scope Control**: Separate tracking prevents lockdown milestone bloat
- **Documentation**: Clear baseline and improvement path

---

## Next Steps

### For Alpha Release
1. Complete any remaining validation
2. Prepare release notes emphasizing alpha status
3. Document known limitations and areas needing feedback
4. Set up channels for alpha user feedback

### For Pylint Integration
1. Generate baseline report:
   ```bash
   cd /Users/poecurt/projects/sqlitch
   source .venv/bin/activate
   pylint sqlitch --output-format=json > specs/005-lockdown/artifacts/baseline/pylint_report.json
   ```

2. Parse the JSON report and create tasks:
   - Review each issue
   - Categorize by priority
   - Create individual tasks in a new section of `tasks.md` or separate tracking document

3. Document baseline in `research.md`:
   - Current score
   - Issue breakdown by type
   - Proposed target score
   - Timeline for improvements

4. Execute fixes in batches:
   - Start with high-priority errors/warnings
   - Group similar issues together
   - Verify fixes with reruns
   - Update documentation

---

## Files Modified

```
specs/005-lockdown/spec.md               - Alpha clarification + pylint requirements
specs/005-lockdown/plan.md               - Phase 1.2 pylint workflow + alpha notes
specs/005-lockdown/IMPLEMENTATION_COMPLETE.md - Updated to reflect alpha release
```

---

## Git Commit

**Commit Hash**: aa5adec  
**Commit Message**: "Update spec to clarify alpha release and add pylint requirements"

**Verification**:
```bash
cd /Users/poecurt/projects/sqlitch
git show aa5adec --stat
```

---

## Questions for Consideration

1. **Pylint Baseline**: Should we generate the baseline report now or wait for a clean state?
2. **Task Tracking**: Should pylint tasks be in `tasks.md` or a separate `pylint-tasks.md`?
3. **Priority**: Should pylint work block the alpha release or run in parallel?
4. **Target Score**: What's an acceptable pylint score for alpha vs. v1.0.0?

---

**Status**: ✅ Spec updates complete and committed  
**Ready For**: Pylint baseline generation and task creation
