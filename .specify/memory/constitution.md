<!--
- Sync Impact Report
- Version change: 1.10.1 → 1.11.0 (MINOR bump)
- Modified sections:
  • VI. Behavioral Parity with Sqitch — Added "Implementation Verification Protocol"
    requiring consultation of sqitch/ directory before implementing features
  • Added mandatory 5-step verification workflow
  • Added examples of syntax requiring verification (e.g., @HEAD^, @ROOT)
- Added sections: None
- Removed sections: None
- Rationale: Codified the critical requirement that all SQLitch implementation work
  must verify behavior against the Perl Sqitch source code in sqitch/ directory, not
  just documentation. This is a material expansion of the behavioral parity principle,
  adding concrete verification steps that must be followed. This is a substantive
  addition to governance workflow, warranting a MINOR version bump.
- Templates requiring updates: All future spec/plan/tasks documents should reference
  this verification protocol when describing implementation work
- Follow-up TODOs: None
- Previous sync report (v1.10.0 → v1.10.1):
  Modified sections:
  • Development Workflow & Quality Gates — Added "Terminal Command Decomposition" requirement
  Rationale: Added workflow principle requiring AI agents to decompose compound shell commands
  into separate sequential steps.
-->

# SQLitch Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)
- Tests MUST be written before implementation (Red→Green→Refactor).
- Every new feature/bugfix PR MUST include failing tests that define behavior.
- Contract/integration tests MUST cover user-visible flows and CLI contracts.
- Unused or untested code MUST NOT be merged.
- **All tests in the codebase MUST pass**. Unimplemented features MUST be marked with
  pytest skip markers (`@pytest.mark.skip(reason="Pending: ...")`), not committed as
  failing tests.
Rationale: Defining behavior in tests first creates living specifications and prevents
regressions while enabling safe refactors. A clean test suite (all passing or explicitly
skipped) ensures confidence in the codebase state at any commit.

**Test Failure Validation Protocol (MANDATORY)**:
When encountering test failures during implementation or refactoring:
1. **Consult Perl Reference**: Check `sqitch/` implementation to confirm expected behavior
2. **Validate Test Correctness**: Verify the test accurately reflects Sqitch's behavior
3. **Fix Code, Not Tests**: If test is correct per Perl reference, fix implementation to pass
4. **Only Modify Tests**: If Perl reference contradicts test, update test with justification

- Before writing new tests or altering existing tests, contributors MUST consult the
  upstream Perl implementation under `sqitch/` to confirm the intended public-facing
  behavior and document any deliberate deviations.
- **When implementing fixes or new features, assume existing tests are correct**. If a
  change appears to require modifying tests, first verify parity with the Perl Sqitch
  behavior; only adjust tests after confirming the upstream semantics truly differ.
- The default expectation is to expand test coverage while leaving current tests
  intact, ensuring alignment with Sqitch behavior and avoiding unnecessary churn.

- Mocks and stubs SHOULD be avoided. Tests MUST exercise real interfaces (CLI
  commands and library entry points) with real files/process boundaries whenever
  feasible.
- Test doubles are permitted ONLY for non-deterministic or external boundaries
  (e.g., network, system time, randomness, external services) and MUST be
  confined behind clear abstraction seams.
- Prefer invoking the actual CLI with temp directories and verifying stdout,
  stderr, and exit codes for end-to-end realism.

**Test Isolation and Cleanup (MANDATORY)**:
- All tests that invoke CLI commands or create filesystem artifacts MUST use Click's
  `runner.isolated_filesystem()` context manager or equivalent isolation mechanisms.
- Tests MUST NOT leave artifacts (config files, plan files, script directories, or any
  other generated content) in the repository working directory after execution.
- The `isolated_filesystem()` context creates a temporary directory that is automatically
  cleaned up when the test completes, ensuring zero pollution of the repository.
- Any test creating files outside an isolated context is a constitution violation and
  MUST be fixed immediately.
Rationale: Test pollution makes the repository state non-deterministic, can interfere
with other tests, and creates confusion about what is intentional project structure
versus accidental leftovers. Isolated filesystems guarantee clean test runs.

### II. CLI-First, Text I/O Contracts
- All functionality MUST be accessible via CLI commands (thin wrappers over libs).
- Inputs: stdin/args; Outputs: stdout; Errors: stderr; Use process exit codes.
- Commands MUST offer human-readable output by default and a `--json` mode.
- CLI commands MUST be composable (no hidden global state, deterministic I/O).
Rationale: Text I/O maximizes composability, scriptability, and debuggability.

### III. Library-First, Single-Responsibility Modules
- Core logic MUST live in importable libraries; CLI remains a thin shell.
- Libraries MUST be self-contained, independently testable, and documented.
- Cross-module coupling MUST be minimized; avoid "organizational-only" libraries.
Rationale: Separation improves reuse, testing, and long-term maintenance.

### IV. Semantic Versioning and Compatibility
- Follow SemVer: MAJOR.MINOR.PATCH for public contracts (CLI flags/format/APIs).
- Breaking changes REQUIRE a MAJOR bump and a documented migration plan.
- Additive, backward-compatible changes are MINOR; fixes/clarifications are PATCH.
- Deprecations SHOULD provide at least one MINOR release of overlap when feasible.
Rationale: Predictable versioning builds trust and reduces upgrade risk.

### V. Observability and Determinism
- Structured logging infrastructure MUST exist but default CLI invocations (no
  `--verbose`, `--json`, or other logging flags) MUST emit only Sqitch-parity human
  output and MUST NOT stream structured payloads to stdout/stderr.
- Structured records MAY be persisted inside the registry, but no standalone log
  files or alternate sinks may appear unless a logging flag explicitly enables it.
- `--verbose`/`--quiet` flags MUST be supported, and `--json` mode MUST emit
  machine-parseable records containing run identifiers and outcomes.
- All logging modes MUST redact secrets and include run IDs to correlate events
  across tools.
- Given identical inputs and environments, outputs MUST be reproducible.
Rationale: Opt-in observability preserves Sqitch-parity defaults while keeping
diagnostics rich when explicitly requested.

### VI. Behavioral Parity with Sqitch (Guiding Star)
- The `sqitch/` directory in this repository is the authoritative reference for
  behavior, interfaces, flags, messages, and semantics.
- SQLitch MUST match Sqitch behavior 1:1 unless a documented deviation exists
  with rationale and a migration path.
- Parity includes: plan semantics, deploy/revert/verify behavior, exit codes,
  CLI syntax and help text, and output formats (human and JSON when applicable).
- Tests MUST be derived from or validated against the upstream Sqitch behavior
  to ensure 100% compliance.

**Implementation Verification Protocol (MANDATORY)**:
Before implementing or fixing ANY command, feature, or syntax handling:
1. **Consult Sqitch Source**: Review the corresponding Perl implementation in
   `sqitch/lib/App/Sqitch/` to understand the canonical behavior
2. **Document Sqitch Behavior**: Note how Sqitch handles:
   - Command-line syntax (including symbolic references like `@HEAD^`, `@ROOT`)
   - Options and flags
   - Error messages and error handling patterns
   - Edge cases and boundary conditions
   - Output formatting
3. **Implement to Match**: Write SQLitch code that produces identical behavior
4. **Verify Against Sqitch**: Test the implementation against actual Sqitch behavior
   using UAT scripts or manual comparison
5. **Document Deviations**: Any intentional difference MUST be documented in code
   comments with clear rationale

**Examples requiring verification**:
- If Sqitch supports `sqlitch revert --to @HEAD^`, SQLitch MUST support it identically
- If Sqitch accepts certain flag combinations, SQLitch MUST accept the same
- If Sqitch produces specific error messages, SQLitch SHOULD match them closely

This verification protocol applies to ALL implementation work, not just new features.

Rationale: Treating Sqitch as a golden source guarantees predictable behavior and
user familiarity while reducing ambiguity. Verifying against implementation (not just
documentation) ensures we match actual behavior including undocumented edge cases.

### VII. Simplicity-First, No Duplication
- Each change MUST be the simplest thing that can possibly work while maintaining
  100% compatibility with Sqitch behavior and test coverage.
- Features MUST NOT exceed what upstream Sqitch supports; do not add extra flags,
  modes, or behaviors unless a documented deviation exists with migration.
- Simplicity MUST NOT introduce code duplication; prefer reuse, extraction, or
  refactoring over copy-paste.
- Any necessary complexity MUST be justified in Complexity Tracking with rejected
  simpler alternatives.
Rationale: Simplicity reduces risk and maintenance cost while preserving parity
and clarity of intent.

### VIII. Documented Public Interfaces
- Every publicly exposed module, class, function, CLI command, configuration surface,
  or environment variable MUST include a docstring that captures purpose, inputs,
  outputs, side effects, and error modes.
- Public docstrings SHOULD follow a consistent style (Google/Numpy acceptable) and
  MUST remain accurate when behavior changes.
- Private helpers MAY omit docstrings when intent is obvious but SHOULD include
  concise inline comments if readability would otherwise suffer.
- All public modules SHOULD define `__all__` exports to explicitly declare their
  public API surface and control wildcard import behavior.
Rationale: Clear documentation protects consumers, reviewers, and future maintainers
by making behavior discoverable without reverse-engineering the implementation.

### Behavioral Constraints

- **Default Logging Confinement:** Without explicit logging flags, SQLitch MUST
  refrain from writing structured logs to stdout/stderr or standalone files and
  MUST limit audit trails to the attached registry.
- **Advisory Clarity:** Always clarify when responses are guidance, hypotheses,
  or unverifiable speculation.
- **Inquiry Non-Destructiveness:** When the user asks a question, respond
  with analysis or guidance only. Do not modify the workspace or repository
  unless explicitly directed afterward.

## Additional Constraints

- Security: Never log secrets or PII; redact by default and require `--allow-secrets`
  only for explicit debugging use-cases.
- Portability: Tools MUST run on macOS and Linux; avoid OS-specific behavior unless
  guarded and documented.
- Performance: For typical inputs, core commands SHOULD complete in <200ms; long-
  running operations MUST stream progress or provide `--no-progress` for CI.
- AI Enablement: All tooling integrations and automation clients MUST enable
  Claude Sonnet 4 by default for every supported client. Alternative models MAY
  be offered as opt-in fallbacks, and any temporary disablement MUST be
  documented with an incident record and restoration plan.
- Configuration: Respect environment variables and config files under
  `$XDG_CONFIG_HOME/sqlitch/` or `~/.config/sqlitch/`.
- Type Hints: All code MUST use modern Python 3.9+ built-in type annotations
  (`dict`, `list`, `tuple`, `type`) rather than typing module equivalents
  (`Dict`, `List`, `Tuple`, `Type`) except where backwards compatibility is
  explicitly required. Union types MUST use `X | None` syntax rather than
  `Optional[X]`. All modules SHOULD include `from __future__ import annotations`
  for forward reference support.
- Error Handling: Exception hierarchies SHOULD follow semantic consistency:
  `ValueError` for invalid input data, `RuntimeError` for system/state errors.
  Domain-specific exceptions SHOULD extend the appropriate base class.
- State Management: Global mutable state MUST be minimized. Registries and
  singletons SHOULD be immutable after initialization or provide clear lifecycle
  documentation. Prefer dependency injection over global lookups where feasible.
- Abstract Interfaces: Classes designed for subclassing MUST use `abc.ABC` and
  `@abstractmethod` to declare their contract explicitly.
- Validation Patterns: Complex validation logic SHOULD be extracted from
  `__post_init__` methods into separate, testable factory methods or validators
  to improve clarity and testability.
- Skip Lifecycle Discipline: Tests for unimplemented features MAY be committed
  with skip markers, but removing those skips is a mandatory pre-implementation
  gate. Before any implementation task begins, the responsible engineer MUST
  delete the related skip marker(s), confirm the test fails, and treat the
  unskipped failure as part of the Red→Green→Refactor loop.
- Exception Handling: No exception should ever be silently ignored. All `except` blocks
  MUST either:

  1. Re-raise the exception after cleanup/logging, OR
  2. Log the exception at an appropriate level (error/warning/debug based on severity), OR
  3. Handle the exception with explicit recovery logic
  
  Bare `except Exception: pass` statements are prohibited as they hide bugs and security
  issues. Use specific exception types when possible, and always provide context about
  why an exception is being caught and what recovery action (if any) is being taken.

## Development Workflow & Quality Gates

- Workflow: Spec → Plan → Design (contracts, data model, quickstart) → Tasks →
  Implementation → Validation.
- Constitution Check: Plans MUST document an initial and post-design constitution
  check. Violations MUST be justified in Complexity Tracking or removed.
- PR Gate: CI MUST run tests and enforce formatting/linting; reviewers MUST check
  compliance with principles and governance.
- Test Realism: Tests SHOULD prefer real CLI invocation and real filesystem
  operations; avoid mocking unless covering non-deterministic/external boundaries.
- Simplicity Gate: Implementation MUST be minimal, avoid duplication, and add no
  capability beyond Sqitch unless explicitly justified and approved.
- Documentation: Each feature MUST update quickstart and, when applicable,
  contracts and data-model docs, and MUST ensure public docstrings stay in sync
  with observable behavior.
- Do not commit code when you finish. Give the user a brief summary of changes
  and allow them to review and commit on their own.
- Code Style Gate: All code MUST pass formatting (black, isort), linting
  (flake8, pylint), type checking (mypy), and security scanning (bandit) with
  zero warnings before merge. Import grouping MUST follow PEP 8 (stdlib,
  third-party, local with blank lines between groups).
- Terminal Command Decomposition: AI agents MUST decompose compound shell
  commands (those using `&&`, `;`, or `|`) into separate sequential commands.
  Environment setup commands (e.g., `source .venv/bin/activate`) MUST be run
  once as a standalone command, followed by subsequent commands that rely on
  that environment state. This allows users to approve environment setup once
  and automatically run subsequent commands without repeated approval.
  Rationale: Compound commands require user approval for each execution,
  creating workflow friction. Decomposed commands improve automation flow and
  reduce repeated approvals for identical environment setup steps.

## Governance

- Authority: This constitution supersedes other conventions in this repository.
- Amendment Procedure: Amend via PR updating `.specify/memory/constitution.md`.
  The PR MUST include a Sync Impact Report (as an HTML comment) summarizing the
  version change, modified/added/removed sections, template update status, and
  any deferred TODOs.
- Versioning Policy: Use SemVer for the constitution itself.
  • MAJOR: Backward-incompatible governance/principle removals or redefinitions.
  • MINOR: Add or materially expand a principle/section.
  • PATCH: Clarifications, wording, or non-semantic refinements.
- Compliance: All specs, plans, tasks, and PRs MUST reference and adhere to this
  document. Non-compliance is a change request, not a discretionary choice.

**Version**: 1.11.0 | **Ratified**: 2025-10-03 | **Last Amended**: 2025-10-11

```
