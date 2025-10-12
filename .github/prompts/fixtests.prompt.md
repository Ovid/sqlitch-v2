---
description: Execute the implementation plan by running the full test suite, ensuring all tests pass and minimum coverage requirements are met
---

The user input can be provided directly by the agent or as a command argument - you **MUST** consider it before proceeding with the prompt (if not empty).

User input:

$ARGUMENTS

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute.


2. Load and analyze the implementation context:
   - **REQUIRED**: Read constitution.md for full understanding of what you are and are not allowed to do.
   - **REQUIRED**: Read plan.md for tech stack, architecture, and file structure.
   - **IF EXISTS**: Read data-model.md for entities and relationships.
   - **IF EXISTS**: Read contracts/ for API specifications and test requirements.
   - **IF EXISTS**: Read research.md for technical decisions and constraints.
   - **IF EXISTS**: Read quickstart.md for integration scenarios.

3. Run and validate the test suite:
   - **Environment setup**:
     - Before running any tests, ensure the project’s virtual environment is active by running:
       ```bash
       source .venv/bin/activate
       ```
       This guarantees that `pytest` and other dependencies are available in the current environment.
   - **Test execution**:
     - Run the full test suite using:
       ```bash
       pytest
       ```
       from the repository root.
   - **Coverage enforcement**:
     - Use `pytest --cov` (or project-specific coverage configuration) to ensure minimum required coverage is achieved.
     - Example:
       ```bash
       pytest --cov --cov-fail-under=<MINIMUM_PERCENT>
       ```
   - **Failure resolution**:
     - Identify and fix all failing tests.
     - Analyze stack traces and error messages for root causes.
     - Apply fixes while maintaining consistency with the technical plan and contracts.
   - **Coverage improvement**:
     - If total coverage is below the required threshold, prioritize adding or improving tests in files with the **lowest coverage** first.
     - Focus on critical components such as models, services, and integrations before utility or CLI layers.
   - **Verification**:
     - Re-run `pytest` after each round of fixes until all tests pass.
     - Confirm that coverage reports meet or exceed the required minimum.

4. Implementation execution rules:
   - **Setup first**: Initialize project structure, dependencies, and configuration as needed.
   - **Tests before code**: If missing or outdated tests exist, add or update them before implementing fixes.
   - **Avoid mocks and doubles**: Mocked or doubled code can hide real errors. Do not use them unless necessary.
   - **Core development**: Apply fixes and improvements following TDD principles where possible.
   - **Integration validation**: Ensure database connections, API contracts, and external service mocks/stubs are correctly handled.
   - **Polish and validation**: Perform refactoring, test optimizations, and ensure style and lint checks pass.

5. Progress tracking and error handling:
   - Report progress after resolving each major test failure or coverage improvement.
   - Halt execution if blocking test failures occur that prevent continued progress.
   - Provide detailed error messages and debugging context.
   - Suggest next steps if implementation cannot proceed (e.g., missing dependencies or invalid configuration).

6. Completion validation:
   - Verify **all tests pass**.
   - Check that **coverage meets or exceeds** the project’s minimum threshold.
   - Ensure implementation remains consistent with plan.md and any relevant specifications.
   - Report final summary with:
     - Total test count
     - Failures resolved
     - Final coverage percentage
     - Files or areas improved for coverage

Note: This command assumes that the repository contains a valid pytest configuration and coverage setup.  
If missing, suggest initializing tests with `/init-tests` or equivalent setup commands.
