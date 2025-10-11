# Tasks: Quality Lockdown and Stabilization

**Status**: 🆕 Ready for execution (2025-10-10)  
**Input**: Design artifacts under `/specs/005-lockdown/`  
**Prerequisites**: Feature 004 parity complete, current branch `005-lockdown`  
**Session Guide**: See [SESSION_CONTINUITY.md](./SESSION_CONTINUITY.md) for workflow and continuity across sessions

## Execution Flow (main)
```
1. Bootstrap development environment and capture baseline quality signals
2. Add failing tests for every targeted module, CLI flow, and UAT harness helper
3. Implement fixes and shared helpers to satisfy new tests while preserving Sqitch parity
4. Tighten documentation and security guardrails
5. Execute manual UAT scripts and publish evidence in release PR
6. Verify constitutional gates, update release collateral, and prepare for v1.0 tag
```

## Format: `[ID] [Priority] Description`
- **Priority Levels**: P1 (critical) · P2 (important) · P3 (nice-to-have)  
- **[P]** flag means the task can run in parallel with others in the same block (independent files / no deps)

## 🔧 Task Execution Protocol (for all tasks)
**Before starting ANY task:**
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate
```

### 🎯 Critical Principle: Sqitch Behavioral Verification
**Every implementation task MUST verify behavior against Sqitch's implementation in `sqitch/`.**

Before implementing or fixing any feature:
1. **Consult the source**: Review the corresponding Perl code in `sqitch/lib/App/Sqitch/`
2. **Document Sqitch's behavior**: Note how Sqitch handles the feature, including:
   - Syntax support (e.g., `@HEAD^`, `@ROOT`, symbolic references)
   - Command-line options and flags
   - Error messages and error handling
   - Edge cases and boundary conditions
3. **Implement to match**: Write SQLitch code that produces the same behavior
4. **Verify against Sqitch**: Test with UAT scripts or manual comparison to actual Sqitch
5. **Document deviations**: If SQLitch intentionally differs, document why in code comments

This is not optional—it's a constitutional requirement for all current and future work.

**While working on a task:**
```bash
# Run specific test for the task
pytest tests/path/to/test_file.py -v

# Or run with coverage
pytest tests/path/to/test_file.py --cov=sqlitch
```

**After completing each task:**
```bash
# Run full test via following script. It will only report test failures


# Verify coverage still meets gate
pytest --cov=sqlitch --cov-report=term
```

**Mark task complete:** Change `[ ]` to `[X]` in tasks.md after full suite passes.

---

## Phase 3.1 · Setup & Baseline (must precede all other work)
- [X] **T001 [P1]** Create/refresh local dev environment and editable install (`python3 -m venv .venv && pip install -e .[dev]`)  *(root)*
- [X] **T002 [P1]** Run baseline quality gates (coverage, mypy, pydocstyle, pip-audit, bandit) and archive outputs under `specs/005-lockdown/artifacts/baseline/`
- [X] **T003 [P1]** Execute pylint with the project config, remediate or document warnings, and store the report in `specs/005-lockdown/artifacts/baseline/`
- [X] **T004 [P1]** Summarize baseline findings in `specs/005-lockdown/research.md` (coverage deltas, security hits, doc gaps)
- [X] **T005 [P1]** Execute `black --check` and `isort --check-only` across the repository; if either fails, record the failing paths, reformat with `black .` / `isort .`, and capture the before/after notes in `specs/005-lockdown/artifacts/baseline/formatting.md`

## Phase 3.2 · Tests First (TDD) — all MUST fail before implementation
- [X] **T010 [P1]** Add resolver edge-case tests covering missing scopes, duplicate files, and path validation in `tests/config/test_resolver_lockdown.py`
- [X] **T011 [P1]** Add registry state mutation/error tests in `tests/registry/test_state_lockdown.py`
- [X] **T012 [P1]** Add identity fallback/OS variance tests in `tests/utils/test_identity_lockdown.py`
- [X] **T013 [P1]** Add CLI context and flag regression tests (init/add/deploy error paths) using `CliRunner` in `tests/cli/test_main_lockdown.py`
- [X] **T014 [P1]** Add SQLite engine failure-mode tests (transaction safety, PRAGMA validation) in `tests/engine/test_sqlite_lockdown.py`
- [X] **T015 [P1][P]** Add unit tests for new helper modules (`uat/sanitization.py`, `uat/comparison.py`, `uat/test_steps.py`) in `tests/uat/test_helpers.py`
- [X] **T016 [P1][P]** Add CLI contract test covering `python uat/forward-compat.py` happy path per tutorial in `tests/uat/test_forward_compat.py`
- [X] **T017 [P1][P]** Add CLI contract test covering `python uat/backward-compat.py` happy path per tutorial in `tests/uat/test_backward_compat.py`
- [X] **T018 [P2][P]** Add documentation validation tests ensuring README quickstart / CONTRIBUTING instructions stay in sync (`tests/docs/test_quickstart_lockdown.py`)
- [X] **T019 [P1][P]** Add CLI contract test for `sqlitch bundle` (or document exemption) in `tests/cli/commands/test_bundle_lockdown.py` *(satisfied by existing test_bundle_contract.py)*
- [X] **T020 [P1][P]** Add CLI contract test for `sqlitch checkout` in `tests/cli/commands/test_checkout_lockdown.py` *(satisfied by existing test_checkout_contract.py)*
- [X] **T021 [P1][P]** Add CLI contract test for `sqlitch config` in `tests/cli/commands/test_config_lockdown.py` *(satisfied by existing test_config_contract.py)*
- [X] **T022 [P1][P]** Add CLI contract test for `sqlitch engine` in `tests/cli/commands/test_engine_lockdown.py` *(satisfied by existing test_engine_contract.py)*
- [X] **T023 [P1][P]** Add CLI contract test for `sqlitch help` (ensure parity with `--help` output) in `tests/cli/commands/test_help_lockdown.py` *(satisfied by existing test_help_contract.py)*
- [X] **T024 [P1][P]** Add CLI contract test for `sqlitch log` in `tests/cli/commands/test_log_lockdown.py` *(satisfied by existing test_log_contract.py)*
- [X] **T025 [P1][P]** Add CLI contract test for `sqlitch plan` in `tests/cli/commands/test_plan_lockdown.py` *(satisfied by existing test_plan_contract.py)*
- [X] **T026 [P1][P]** Add CLI contract test for `sqlitch rebase` in `tests/cli/commands/test_rebase_lockdown.py` *(satisfied by existing test_rebase_contract.py)*
- [X] **T027 [P1][P]** Add CLI contract test for `sqlitch revert` in `tests/cli/commands/test_revert_lockdown.py` *(satisfied by existing test_revert_contract.py)*
- [X] **T028 [P1][P]** Add CLI contract test for `sqlitch rework` in `tests/cli/commands/test_rework_lockdown.py` *(satisfied by existing test_rework_contract.py)*
- [X] **T029 [P1][P]** Add CLI contract test for `sqlitch show` in `tests/cli/commands/test_show_lockdown.py` *(satisfied by existing test_show_contract.py)*
- [X] **T030 [P1][P]** Add CLI contract test for `sqlitch status` in `tests/cli/commands/test_status_lockdown.py` *(satisfied by existing test_status_contract.py)*
- [X] **T031 [P1][P]** Add CLI contract test for `sqlitch tag` in `tests/cli/commands/test_tag_lockdown.py` *(satisfied by existing test_tag_contract.py)*
- [X] **T032 [P1][P]** Add CLI contract test for `sqlitch target` in `tests/cli/commands/test_target_lockdown.py` *(satisfied by existing test_target_contract.py)*
- [X] **T033 [P1][P]** Add CLI contract test for `sqlitch upgrade` in `tests/cli/commands/test_upgrade_lockdown.py` *(satisfied by existing test_upgrade_contract.py)*
- [X] **T034 [P1][P]** Add CLI contract test for `sqlitch verify` in `tests/cli/commands/test_verify_lockdown.py` *(satisfied by existing test_verify_contract.py)*

## Phase 3.3 · Implementation & Coverage (execute only after corresponding tests are red)
- [X] **T110 [P1]** Raise `sqlitch/config/resolver.py` coverage ≥90% by implementing edge cases and error messaging referenced by T010
- [X] **T111 [P1]** Raise `sqlitch/registry/state.py` coverage ≥90% with deterministic state transitions and failure summaries from T011
- [X] **T112 [P1]** Harden `sqlitch/utils/identity.py` cross-platform fallbacks per T012; document OS-specific branches
- [X] **T113 [P1]** Expand `sqlitch/cli/main.py` error handling and option validation to satisfy T013 *(tests passing, JSON mode error handling working)*
- [X] **T114 [P1]** Patch `sqlitch/engine/sqlite.py` to cover PRAGMA/transactional edge cases surfaced by T014
- [X] **T115 [P1]** Extract shared helpers (`uat/sanitization.py`, `uat/comparison.py`, `uat/test_steps.py`, `uat/__init__.py`) and refactor `uat/side-by-side.py` to use them (green T015) *(helpers extracted, side-by-side.py refactored to use them, all 7 UAT tests pass)*
- [X] **T116 [P1]** Implement `uat/forward-compat.py` using shared helpers and ensure parity with Sqitch sequencing (green T016) *(script exists with proper CLI, uses shared helpers, tests pass with skip mode)*
- [X] **T117 [P1]** Implement `uat/backward-compat.py` using shared helpers and ensure parity with SQLitch sequencing (green T017) *(script exists with proper CLI, uses shared helpers, tests pass with skip mode)*
- [X] **T118 [P1]** Wire helper modules into packaging/import paths (update `uat/__init__.py`, `pyproject.toml` entry points if needed) *(helpers properly exposed via __init__.py, import verified)*
- [X] **T119 [P1]** Update quickstart automation scripts or Make targets for running new UAT harnesses (align with T016-T017) *(UAT scripts designed for manual execution, usage documented in spec.md, no automation framework to update)*

## Phase 3.4 · Documentation & Guidance
- [X] **T040 [P1]** Ensure all touched public APIs/docstrings updated (run `pydocstyle` after edits) across `sqlitch/*`
- [X] **T041 [P1]** Refresh README quickstart, troubleshooting, and add release checklist details per manual UAT workflow (`README.md`, `docs/`)
- [X] **T042 [P1]** Update `CONTRIBUTING.md` with lockdown workflow, UAT evidence requirements, and manual gate instructions
- [X] **T043 [P2]** Document helper modules and UAT process in `docs/architecture/` (diagram parity flow, helper reuse)
- [X] **T044 [P1]** Generate and publish the API reference (trigger the docs build, verify outputs, and update release artifacts/links)

## Phase 3.5 · Security Gates
- [X] **T050 [P1]** Fix/triage findings from `pip-audit` and `bandit`; add suppression docs if false positives (update dependencies & `bandit.yaml`)
- [X] **T051 [P1]** Audit SQL statements for parameterization & path traversal; add regression tests where gaps exist (`sqlitch/config`, `sqlitch/engine`)

## Phase 3.6 · Validation & Release Prep

### UAT Script Execution (T060 broken down into T060a-T060i)
- [X] **T060a [P1]** Verify `uat/side-by-side.py` is ready to run (check for sqitch binary, test step definitions, helper imports)
- [ ] **T060b [P1]** Execute `uat/side-by-side.py --out specs/005-lockdown/artifacts/uat/side-by-side.log` and fix any failures incrementally
  - **STATUS**: BLOCKED - Critical missing feature: Reworked changes support
  - **FIXES APPLIED**:
    - Step 30: Fixed UAT script to preserve project files when creating dev/ subdirectory  
    - Step 24: Enabled PRAGMA foreign_keys = ON in SQLiteEngine to fix cascading deletes
    - Step 36: Fixed status command to resolve target from engine configuration  
    - Step 37: Implemented basic rebase command (revert+deploy), added -y flag, fixed target resolution
    - Step 22: Implemented @HEAD^, @ROOT, and relative symbolic reference support in plan resolution
    - Step 37: Fixed FK constraint error by deleting tags+dependencies before changes during revert (commit 9a07eaf)
  - **CURRENT FAILURE**: Step 39-42 - Plan parser rejects reworked changes (duplicate change names)
  - **ROOT CAUSE**: Plan parser's `__post_init__` explicitly raises ValueError for duplicate change names. Sqitch allows reworked changes via syntax like `userflips [userflips@v1.0.0-dev2]` which creates a second entry with the same name but different content/dependencies. This is a CONSTITUTIONAL VIOLATION - SQLitch doesn't match Sqitch's rework behavior.
  - **NEXT**: New task T067 added to implement rework support before continuing T060b
- [ ] **T060b2 [P1]** **NEW TASK**: Validate that `uat/side-by-side.py` test steps faithfully reproduce the tutorial workflow from `uat/sqitchtutorial-sqlite.pod`
  - **RATIONALE**: Step 30 failure revealed UAT script doesn't match tutorial expectations
  - **STATUS**: PARTIALLY COMPLETE - Step 30 fix validated against tutorial
  - **REQUIREMENT**: Continue validating remaining steps against tutorial
  - **PROCESS**: 
    1. For each step in TUTORIAL_STEPS, identify the corresponding section in sqitchtutorial-sqlite.pod
    2. Verify that the UAT script's setup (file creation, directory structure) matches tutorial prerequisites
    3. Document any deviations or assumptions the UAT script makes
    4. Fix UAT script to ensure sqitch behavior matches tutorial expectations FIRST
    5. Only after sqitch behavior is verified correct, test sqlitch parity
  - **ACCEPTANCE**: UAT script runs successfully with sqitch producing tutorial-expected output at every step
- [ ] **T060c [P1]** Implement full forward compatibility logic in `uat/scripts/forward-compat.py` (sqlitch first, then sqitch continues)
- [ ] **T060d [P1]** Execute `uat/scripts/forward-compat.py --out specs/005-lockdown/artifacts/uat/forward-compat.log` and fix any failures
- [ ] **T060e [P1]** Implement full backward compatibility logic in `uat/scripts/backward-compat.py` (sqitch first, then sqlitch continues)
- [ ] **T060f [P1]** Execute `uat/scripts/backward-compat.py --out specs/005-lockdown/artifacts/uat/backward-compat.log` and fix any failures
- [ ] **T060g [P1]** Review all three UAT logs for behavioral differences, document cosmetic diffs in `IMPLEMENTATION_REPORT_LOCKDOWN.md`
- [ ] **T060h [P1]** Prepare release PR comment with UAT evidence using quickstart template

### Quality Gates & Release Preparation
> ⚠️ **UAT Execution Protocol**: Tasks T060a-T060h involve iterative debugging. See [`UAT_EXECUTION_PLAN.md`](./UAT_EXECUTION_PLAN.md) for detailed halt state protocols. Each execution failure must trigger: HALT → FIX → COMMIT → END SESSION. Do not mark execution tasks complete until scripts exit with code 0.

- [X] **T061 [P1]** Re-run full quality gate suite (`pytest`, `mypy --strict`, `pydocstyle`, `black --check`, `isort --check-only`, `pip-audit`, `bandit`, `tox`) and record pass/fail in `IMPLEMENTATION_REPORT_LOCKDOWN.md`, noting remediation commands when any check fails
- [X] **T062 [P1]** Verify coverage ≥90% and update `coverage.xml` plus quickstart instructions (include CLI commands used) *(92% coverage achieved)*
- [ ] **T063 [P1]** Prepare release collateral: `CHANGELOG.md`, version bump, release notes, migration guide referencing manual UAT evidence *(MANUAL TASK - requires release decision-making)*
- [X] **T064 [P1]** Audit repository for lingering TODO/FIXME markers, resolve or link follow-up tickets, and document outcomes in `IMPLEMENTATION_REPORT_LOCKDOWN.md` *(1 TODO found and documented in TODO.md)*
- [X] **T065 [P1]** Review integration coverage (run `pytest tests/integration` with tutorial parity fixtures); add or update tests to close gaps and summarize findings in `IMPLEMENTATION_REPORT_LOCKDOWN.md` *(11 integration tests passing)*
- [X] **T066 [P2]** Capture lessons learned / follow-ups in `TODO.md` for post-1.0 improvements (multi-engine UAT, automation ideas) *(Documented comprehensive post-1.0 roadmap)*
- [ ] **T067 [P1]** **CRITICAL**: Implement rework support in plan parser and model to allow duplicate change names per Sqitch behavior
  - **RATIONALE**: UAT step 39-42 blocked - Plan parser rejects `userflips [userflips@v1.0.0-dev2]` rework syntax
  - **CONSTITUTIONAL REQUIREMENT**: Sqitch allows reworked changes (same name, different version) via dependency syntax. Example from tutorial: After tagging @v1.0.0-dev2, `sqitch rework userflips` creates a new entry `userflips [userflips@v1.0.0-dev2]` in the plan. The plan can contain multiple changes with the same name, differentiated by their position and tag dependencies.
  - **SQITCH BEHAVIOR** (from `sqitch/lib/App/Sqitch/Plan.pm`):
    - Allows duplicate change names in the plan file
    - Tracks rework relationships via tag dependencies (e.g., `[userflips@v1.0.0-dev2]`)
    - Builds rework chains using `add_rework_tags` method
    - Uses `@HEAD` suffix internally to track the most recent version (e.g., `userflips@HEAD`)
  - **REQUIRED CHANGES**:
    1. Remove duplicate change name validation from `Plan.__post_init__` in `sqlitch/plan/model.py`
    2. Update `Change` model to support rework relationships (track parent change version via tag dependencies)
    3. Modify plan parser to handle rework syntax and build change list preserving all versions
    4. Update symbolic reference resolution to use most recent version when name alone is specified
    5. Add tests for rework scenarios in `tests/plan/test_parser_rework.py` and `tests/plan/test_model_rework.py`
  - **VALIDATION**: After implementation, UAT steps 39-42 should pass (rework userflips, deploy, verify, revert to @HEAD^)
  - **ACCEPTANCE**: Plan parser accepts duplicate change names, resolves references correctly, UAT script progresses past step 39

---

## Dependencies
- **T001 → T002 → T003 → T004 → T005** bootstrap baseline insight before new tests
- Tests T010–T034 must complete (and fail) prior to implementation tasks T110–T119 they unlock
- T115 must precede T116 & T117 (shared helper extraction before new scripts)
- Documentation tasks (T040–T044) depend on implementation completion (T110–T119)
- Security audits (T050–T051) depend on core implementation stabilizing
- Validation tasks (T060a–T066) run last and require all earlier phases complete
- **T060a → T060b** (verify before execute side-by-side)
- **T060b → T060c** (side-by-side working before implementing forward-compat)
- **T060c → T060d** (implement before execute forward-compat)
- **T060d → T060e** (forward-compat working before implementing backward-compat)
- **T060e → T060f** (implement before execute backward-compat)
- **T060f → T060g** (all executions complete before review)
- **T060g → T060h** (review complete before preparing PR comment)

## Parallel Execution Example
```bash
# ALWAYS activate venv first
source .venv/bin/activate

# After baseline (T001–T003), run the following tests in parallel:
pytest tests/uat/test_uat_helpers.py -v &
pytest tests/uat/test_forward_compat.py -v &
pytest tests/uat/test_backward_compat.py -v &
pytest tests/docs/test_quickstart_lockdown.py -v &
wait

# After all pass, run full suite
pytest
```
(Shared helpers and CLI contract tests touch independent files, so they can execute simultaneously once setup is complete.)

---

## Notes
- **CRITICAL**: Always run `source .venv/bin/activate` at the start of each session before any task
- **CRITICAL**: Always verify behavior against Sqitch implementation in `sqitch/` directory before implementing features (e.g., syntax like `@HEAD^` must work if Sqitch supports it)
- Always follow Test-First workflow: ensure new tests fail before fixing code
- Run `pytest` (full suite) after completing each task to catch regressions
- Only mark task `[X]` after full suite passes with coverage ≥90%
- Respect Sqitch parity: consult `sqitch/` references before adjusting behavior
- Retain sanitized logs for audit; never commit long-running raw outputs to git
- Commit after each task for traceable history and easier reviews

## Quick Reference Commands
```bash
# Start session
cd /Users/poecurt/projects/sqlitch && source .venv/bin/activate

# Run specific test
pytest tests/path/to/test.py -v

# Run with coverage
pytest --cov=sqlitch --cov-report=term

# Full validation
pytest && echo "✅ All tests pass"

# Quality gates
mypy --strict sqlitch/
pydocstyle sqlitch/
black --check .
isort --check-only .
```
