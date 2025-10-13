---
description: Analyze pylint res    - **Issue analysis and task creation (NO FIXING)**:
      - Parse the `pylint_report.json` file. Each object in the JSON array represents a distinct code quality issue.
      - Categorize each issue by severity: `fatal`, `error`, `warning`, `convention`, `refactor`.
      - **Create individual tasks** for each issue:
        - **ONE ISSUE = ONE TASK**: Each pylint issue must be a separate task entry
        - **Order by difficulty**: Arrange tasks from easiest to hardest within each severity level
        - **Ordering guidelines**:
          - Simple formatting/style issues (easiest)
          - Missing docstrings or documentation
          - Unused variables/imports
          - Complex refactoring (hardest)
          - Architectural changes (hardest)
        - Include in each task:
          - File path and line number
          - Pylint message code (e.g., `W0613`, `C0116`)
          - Full error message
          - **False positive assessment**: Note if this might be a Pylint false positive
          - Suggested resolution (if genuine) OR rationale for suppression (if false positive)fy issues, and update the plan/spec/tasks to ensure they are tracked for later resolution (DO NOT modify code)
---

The user input can be provided directly by the agent or as a command argument — you **MUST** consider it before proceeding with the prompt (if not empty).

User input:

$ARGUMENTS

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from the repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute.

2. Load and analyze the implementation context:
    - **REQUIRED**: Read `constitution.md` for full understanding of what you are and are not allowed to do.
    - **REQUIRED**: Read `plan.md` for tech stack, architecture, and file structure.
    - **IF EXISTS**: Read `data-model.md` for entities and relationships.
    - **IF EXISTS**: Read `contracts/` for API specifications.
    - **IF EXISTS**: Read `research.md` for technical decisions and constraints.
    - **IF EXISTS**: Read `quickstart.md` for integration scenarios.

3. Run and analyze with Pylint:
    - **Environment setup**:
      - Before running any tools, ensure the project’s virtual environment is active:
        ```bash
        source .venv/bin/activate
        ```
      - This guarantees that `pylint` and dependencies are available.

    - **Linting execution**:
      - Run `pylint` on the target package(s) or module(s) and save the output:
        ```bash
        pylint sqlitch tests --output-format=json > pylint_report.json
        ```
        *(Identify the target `<PACKAGE_OR_MODULES>` from the `plan.md` or project structure.)*

    - **Issue analysis (NO FIXING)**:
      - Parse the `pylint_report.json` file. Each object in the JSON array represents a distinct code quality issue. You examine issues, one by one, with `jq '.[0]' pylint_report.json`, `jq '.[1]' pylint_report.json`, and so on.
      - Categorize each issue by severity: `fatal`, `error`, `warning`, `convention`, `refactor`.
      - Instead of modifying code, **document** each issue in the implementation plan and task system:
        - Add or update relevant sections in:
          - `plan.md` — for structural or architectural refactor needs.
          - `spec/tasks/*.md` or task tracker — for actionable fixes (e.g., “Resolve pylint `error` in sqlitch/db.py line 42”).
        - Include context:
          - File path and line number
          - Pylint message and code
          - Suggested resolution or reasoning
        - Group issues by category (fatal/errors first, then warnings/refactors).

4. Documentation and task workflow:
    - For each task entry in the task tracker:
      - Add a **hint section** warning: "⚠️ Pylint sometimes reports false positives. Verify this is a genuine issue before fixing."
      - Include **assessment criteria**:
        - Is the code actually incorrect or just flagged incorrectly?
        - Does the suggested fix align with project architecture and Sqitch parity?
        - Would a suppression comment be more appropriate than code changes?
      - If unclear whether it's a false positive:
        - Document the ambiguity in the task
        - Present both options (fix vs. suppress) to the user
        - Wait for user decision before proceeding
      - Example task format:
        ```
        ## Task T143: Resolve unused-argument in add.py:137
        - File: sqlitch/cli/commands/add.py:137
        - Code: W0613 (unused-argument)
        - Message: Unused argument 'json_mode'
        - ⚠️ Assessment: Likely false positive - Click injects this parameter
        - Options:
          1. Add suppression comment (recommended for Click decorators)
          2. Consume parameter explicitly with helper function
        - User decision required: Which approach?
        ```
    - If a `.pylintrc` file is missing or misconfigured, add a task to create or fix it.

5. Task execution workflow (when fixing issues):
    - **CRITICAL**: Fix only ONE task at a time, then STOP and wait for user confirmation
    - **Workflow per task**:
      1. Identify the next task (should be ordered easiest to hardest)
      2. Present the issue and proposed solution to the user
      3. If false positive status is unclear:
         - Explain why it might be false positive
         - Explain why it might be genuine issue
         - Present options (fix vs. suppress vs. refactor)
         - **WAIT for user decision**
      4. After user confirms approach, implement the fix
      5. Run tests to validate the fix: `python -m pytest -xvs <relevant_test_file>`
      6. Run pylint again to confirm issue is resolved
      7. **STOP and report completion**
      8. Wait for user approval to mark task complete
      9. Only proceed to next task after explicit user confirmation
    - **Never batch fixes**: Each issue must be fixed, validated, and confirmed individually

6. Progress tracking and reporting:
    - After documenting each task, report the total task count and ordering
    - When executing fixes:
      - Report after EACH SINGLE fix is applied
      - Include test results and pylint recheck
      - **HALT and wait** for user approval before proceeding
    - If a `pylint` issue implies deeper architectural or design flaws—update `plan.md` to flag it
    - Provide detailed reasoning when:
      - The root cause is unclear
      - False positive status is ambiguous
      - Multiple fix approaches are viable
    - The score can be fetched with `pylint --score=y sqlitch tests 2>&1 | tail -n 2`

7. Completion validation:
    - Confirm all issues are documented as individual tasks in the spec/task system
    - Verify tasks are ordered from easiest to hardest
    - Ensure each task includes false positive assessment
    - Ensure `plan.md` and related docs remain consistent
    - Report summary:
      - Total number of tasks created (by severity type)
      - Files affected
      - Number of likely false positives identified
      - Any significant technical risks noted
      - Estimated ordering (easiest tasks first)

**Important reminders**:
- **Analysis phase**: Do NOT modify any source code—only document and create tasks
- **Execution phase**: Fix ONE task at a time, validate, get approval, then proceed
- **False positives**: Always consider whether Pylint is correct before making changes
- **User control**: Never proceed to the next task without explicit user approval
