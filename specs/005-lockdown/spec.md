# Feature Specification: Quality Lockdown and Stabilization

**Feature Branch**: `005-lockdown`  
**Created**: 2025-10-10  
**Status**: Draft  
**Prerequisites**: Feature 004 (Tutorial Parity) complete  
**Target**: Alpha release (NOT v1.0.0 - this is still alpha software)

## Execution Flow (main)
```
1. Review current codebase state and identify quality gaps
2. Run comprehensive test coverage analysis
3. Identify missing tests, documentation, and type hints
4. Fix remaining bugs and edge cases
5. Stabilize APIs and lock down interfaces
6. Enhance error messages and user experience
7. Perform security audit
8. Prepare for stable release
```

---

## Clarifications

### Session 2025-10-10
- Q: Which environments must the new compatibility scripts exercise to count as "complete"? → A: Only the existing SQLite tutorial workflow
- Q: How should the three compatibility scripts integrate into our workflows once implemented? → A: Manual runs only (documented checklist)
- Q: Where must results from each manual UAT run be recorded? → A: Post a comment in the release pull request summarizing the outcomes

### Session 2025-10-13
- Q: What pylint score threshold should `tox -e lint` enforce before the gate passes? → A: Fail below 9.00

---

## ⚡ Quick Guidelines
- **NO new features** - Only bug fixes, tests, documentation, and stability improvements
- Achieve and maintain ≥90% test coverage across all modules
- All public APIs MUST have comprehensive docstrings
- All configuration behavior MUST be tested
- All error paths MUST be tested
- All CLI commands MUST have contract tests
- **UAT compatibility tests MUST pass** - Side-by-side, forward, and backward compatibility
- Security audit MUST pass
- Documentation MUST be complete and accurate

### 🎯 Critical Principle: Sqitch Behavioral Parity
**All SQLitch behavior MUST align with Sqitch behavior as implemented in the vendored `sqitch/` directory.**

This means:
- When implementing or fixing features, **consult the Perl Sqitch codebase in `sqitch/`** as the source of truth
- Syntax and features that work in Sqitch (e.g., `@HEAD^`, `@ROOT`, symbolic references) MUST work identically in SQLitch
- Edge cases, error messages, and command-line option handling should mirror Sqitch's behavior
- When behavioral differences are discovered, SQLitch must be updated to match Sqitch (unless there's a documented security or correctness issue in Sqitch)
- All test scenarios should verify behavior against Sqitch's implementation, not assumptions

**Implementation Workflow**:
1. Before implementing any command or feature: Review corresponding Sqitch code in `sqitch/lib/App/Sqitch/` 
2. Document Sqitch's behavior (including edge cases, error paths, special syntax)
3. Implement SQLitch to match that behavior
4. Verify with UAT scripts and/or manual testing against actual Sqitch
5. Document any intentional deviations with clear rationale

This principle applies to ALL future work, not just lockdown tasks.

---

## Objectives

### 1. Code Quality
- **Test Coverage**: Achieve ≥90% coverage in all modules
- **Type Safety**: Eliminate the current 70-error mypy backlog and keep `mypy --strict` green; add an automated guard (pytest or tox) that fails when mypy regresses.
- **Documentation**: Complete docstrings for all public APIs
- **Code Style**: Enforce consistent formatting (Black, isort) and ensure linting (flake8) runs clean via an automated check.
- **Formatting Gates**: Add regression tests/automation that assert `black --check` and `isort --check-only` remain compliant.
- **Pylint Remediation**: Use pylint as an enforceable gate, not just an informational report:
  - Generate and continuously update pylint reports: `pylint sqlitch tests --output-format=json > pylint_report.json`
  - Resolve every `fatal` and `error` item; suppressions require explicit justification in-code and in the implementation report.
  - Reduce or document `warning`, `refactor`, and `convention` findings with assigned follow-up tasks and deadlines.
  - Add an automated guard (tox or pytest) that fails when pylint introduces new `fatal`/`error` entries or the score drops below **9.00**.
  - Target: Zero unhandled pylint errors with remediation evidence captured alongside other quality gates.

### 2. Stability
- **Bug Fixes**: Address all known bugs and edge cases
- **Error Handling**: Improve error messages and recovery
- **Edge Cases**: Test and handle boundary conditions
- **Regression Protection**: Ensure no regressions from features 001-004

### 3. Security
- **Input Validation**: Audit all user inputs for injection risks
- **File Operations**: Audit file handling for path traversal
- **Configuration**: Audit config parsing for security issues
- **Dependencies**: Update dependencies with known vulnerabilities
- **Hashing**: Update any Git-compatible SHA1 usage (e.g., `utils/identity.generate_change_id`) to pass Bandit by marking `usedforsecurity=False` while retaining Sqitch parity.

### 4. User Experience
- **Error Messages**: Clear, actionable error messages
- **Help Text**: Comprehensive --help output for all commands
- **Examples**: Add usage examples to documentation
- **Troubleshooting**: Common issues and solutions documented

### 5. UAT Compatibility Testing
- **Scope**: All compatibility scripts validate the SQLite tutorial workflow only; other engines remain out of scope for lockdown.
- **Halt State Protocol**: UAT execution tasks follow an incremental debugging workflow. Each script failure triggers: HALT → identify root cause → implement minimal fix → run tests → commit → END SESSION. This prevents context overflow and ensures each fix is reviewed independently. See [`UAT_EXECUTION_PLAN.md`](./UAT_EXECUTION_PLAN.md) for detailed protocols.
- **Side-by-Side Testing**: `uat/side-by-side.py` validates functional equivalence between sqitch and sqlitch
  - Follows `sqitch/lib/sqitchtutorial-sqlite.pod` tutorial steps
  - Compares command output (semantically equivalent, minor formatting differences acceptable)
  - Validates user-visible database state (ignores registry metadata)
  - Sanitizes timestamps and SHA1s for comparison
  - Halts on behavioral differences (not cosmetic output differences)
- **Forward Compatibility Testing**: Script runs sqlitch for each step, then validates compatibility by running sqitch as next command
  - Ensures sqlitch → sqitch handoff works correctly
  - Validates that sqitch can continue from sqlitch state
  - Tests production scenario: users can switch to sqlitch without lock-in
- **Backward Compatibility Testing**: Script runs sqitch for each step, then validates compatibility by running sqlitch as next command
  - Ensures sqitch → sqlitch handoff works correctly
  - Validates that sqlitch can continue from sqitch state
  - Tests migration scenario: users can adopt sqlitch from existing sqitch projects
- **Execution Expectation**: All three scripts run as part of the documented release checklist; CI integration is optional.
- **Evidence**: Each manual run must be summarized in a comment on the release pull request with links to sanitized logs.

### 6. Test Safety
- `tests/support/test_helpers.py` MUST, on import, delete every environment variable used by Sqitch or SQLitch (e.g., `SQITCH_*`, `SQLITCH_*`, `SQLITCH_CONFIG`, `SQLITCH_TARGET`) to guarantee tests never read or write user/system configuration outside the isolated workspace. This requirement is critical for constitutional test isolation compliance.

---

## Success Criteria

**Note**: See [`tasks.md`](./tasks.md) for the canonical task tracking and completion status. The criteria below define the quality bar; tasks.md tracks progress toward meeting them.

### Quality Gates
- Test coverage ≥90% in all modules
- All public functions have docstrings
- mypy --strict passes with zero errors
- Black and isort formatting enforced with automated regression tests
- flake8 linting passes with zero violations (no ignored errors)
- Pylint remediation complete and enforced via automation:
  - No remaining `fatal` or `error` diagnostics; any suppression is documented with rationale in code and in `IMPLEMENTATION_REPORT_LOCKDOWN.md`.
  - Warnings/refactors either resolved or tracked with dated follow-up tasks and ownership in `tasks.md`.
  - Lint gate (`tox -e lint` or equivalent) runs in CI and fails the build on new pylint regressions or score < **9.00**.
- `tests/support/test_helpers.py` is validated to clear Sqitch/SQLitch environment variables before any helper logic executes, ensuring tests run against a sanitized environment.
- All TODO comments addressed or ticketed

### Functional Gates
- All CLI commands have contract tests
- All configuration options tested
- All error paths have explicit tests
- Integration tests cover end-to-end workflows
- Regression tests prevent known bugs

### Security Gates
- No SQL injection vulnerabilities
- No path traversal vulnerabilities
- No command injection vulnerabilities
- Dependencies have no critical CVEs
- Configuration validation prevents malicious inputs

### Documentation Gates
- README complete with quickstart
- CONTRIBUTING.md updated
- All CLI commands documented
- API reference generated
- Common troubleshooting scenarios documented
- Implementation report (`specs/005-lockdown/IMPLEMENTATION_REPORT_LOCKDOWN.md`) summarizes final quality gate results, links to logs, and notes any deferred follow-ups

### UAT Gates
- Side-by-side test (`uat/side-by-side.py`) passes all tutorial steps
- Forward compatibility test passes (sqlitch → sqitch handoff)
- Backward compatibility test passes (sqitch → sqlitch handoff)
- UAT scripts detect no behavioral differences
- Minor output formatting differences documented and acceptable

---

## Non-Goals

- **New Features**: No new functionality added in this phase
- **API Changes**: No breaking changes to existing APIs
- **Refactoring**: Only refactor if it improves quality/testability

---

## Constitutional Compliance

This feature directly supports:
- **Constitution I: Test-First Development** - Achieving comprehensive test coverage
- **Constitution II: Documentation Standards** - Complete API documentation
- **Constitution III: Code Quality** - Type safety and style enforcement
- **Constitution IV: Security** - Security audit and validation
- **Constitution V: Behavioral Parity with Sqitch** - Regression protection and UAT compatibility testing

---

## Implementation Details

### UAT Compatibility Scripts

#### 1. Side-by-Side Test (`uat/side-by-side.py`)
**Status**: ✅ Implemented

Tests functional equivalence by running both tools in parallel:
- Runs each tutorial step with both sqitch and sqlitch
- Compares sanitized output (masks SHA1s, timestamps)
- Compares user-visible database state (ignores sqitch registry)
- Continues on failure with `--continue` flag
- Can ignore specific steps with `--ignore` flag
- Outputs comprehensive logs to `sqitch.log` and `sqlitch.log`

**Usage**:
```bash
./uat/side-by-side.py                    # Run full test
./uat/side-by-side.py --continue         # Continue on failures
./uat/side-by-side.py --out results.txt  # Save output to file
./uat/side-by-side.py --ignore 5 10      # Ignore steps 5 and 10
```

#### 2. Forward Compatibility Test (`uat/scripts/forward-compat.py`)
**Status**: ✅ Implemented and validated (T060c, T060d complete — 46/46 steps green on 2025-10-11)

Tests sqlitch → sqitch handoff:
- Run step N with sqlitch
- Run step N+1 with sqitch
- Validate sqitch successfully continues from sqlitch state
- Repeat for all tutorial steps (all steps pass; final log stored at `specs/005-lockdown/artifacts/uat/forward-compat-final.log`)

**Key Validations**:
- Sqitch reads sqlitch registry correctly
- Sqitch handles sqlitch-deployed changes
- Sqitch verify works on sqlitch deployments
- Sqitch status shows correct state
- Database schema matches expectations

**Execution Notes**:
- Shares sanitization helpers with the side-by-side harness
- Alternates tools through the full tutorial sequence and compares end-state parity
- Logs both tools' operations; sanitized transcript archived with the release evidence
- Tested with both tagged and untagged changes, including rework scenarios unlocked by T067
- Documented in the release checklist and PR evidence template (see `IMPLEMENTATION_REPORT_LOCKDOWN.md`)

**Follow-Up**: Continue running as part of the release checklist; only rerun implementation work if UAT uncovers regressions.

#### 3. Backward Compatibility Test (`uat/scripts/backward-compat.py`)
**Status**: ✅ Implemented and validated (T060e, T060f complete — 46/46 steps green on 2025-10-11)

Tests sqitch → sqlitch handoff:
- Run step N with sqitch
- Run step N+1 with sqlitch
- Validate sqlitch successfully continues from sqitch state
- Repeat for all tutorial steps (all steps pass; final log stored at `specs/005-lockdown/artifacts/uat/backward-compat-final.log`)

**Key Validations**:
- Sqlitch reads sqitch registry correctly
- Sqlitch handles sqitch-deployed changes
- Sqlitch verify works on sqitch deployments
- Sqlitch status shows correct state
- Database schema matches expectations

**Execution Notes**:
- Shares sanitization helpers with the side-by-side harness
- Alternates tools through the full tutorial sequence and confirms SQLitch resume capability
- Logs both tools' operations; sanitized transcript archived with the release evidence
- Covers tagged/untagged changes and rework flows now supported by T067
- Documented in the release checklist and PR evidence template (see `IMPLEMENTATION_REPORT_LOCKDOWN.md`)

**Follow-Up**: Keep in the manual release gate; investigate and remediate if future runs regress.

#### Shared Infrastructure
All three scripts should share:
- Common sanitization functions (SHA1, timestamps)
- Database comparison utilities (user tables only)
- Logging and output formatting
- Test step definitions (from tutorial)
- Cleanup and error handling

**Directory Structure**:
```
uat/
  __init__.py                      # ✅ Shared package init
  side-by-side.py                  # ✅ Fully implemented
  sanitization.py                  # ✅ Implemented (extracted)
  comparison.py                    # ✅ Implemented (extracted)
  test_steps.py                    # ✅ Implemented (46 tutorial steps)
  scripts/
    forward-compat.py              # ✅ Implemented
    backward-compat.py             # ✅ Implemented
```

---

## Risks and Mitigation

**Risk**: Scope creep from "just one more feature"  
**Mitigation**: Strict no-new-features policy. Any feature requests get ticketed for post-lockdown.

**Risk**: Test coverage requirements delay release  
**Mitigation**: Prioritize high-value modules first. Allow exemptions with documented rationale.

**Risk**: Security issues found late in process  
**Mitigation**: Security audit early in lockdown phase.

**Risk**: UAT scripts may have false positives from output formatting differences  
**Mitigation**: Sophisticated sanitization (timestamps, SHA1s). Document acceptable cosmetic differences. Focus on behavioral equivalence, not byte-for-byte output matching.

**Risk**: Compatibility testing may reveal deep architectural incompatibilities  
**Mitigation**: Run UAT tests early in lockdown phase. Registry format is already aligned with sqitch. Most compatibility issues should surface in side-by-side testing first.

**Risk**: Tutorial steps may change between sqitch versions  
**Mitigation**: UAT testing validates against **Sqitch v1.5.3** (vendored in `sqitch/` directory). Update UAT scripts when upgrading to new Sqitch versions.

---

**Last Updated**: 2025-10-12  
**Priority**: HIGH - Prepare for alpha release (NOT v1.0.0)  
**Estimated Effort**: 2-4 weeks

**Note**: This lockdown prepares SQLitch for a stable **alpha release**, not v1.0.0. The software is still in alpha stage and requires additional validation and real-world usage before declaring production readiness.
